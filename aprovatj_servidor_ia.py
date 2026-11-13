"""Servidor local AprovaTJ: usa GEMINI_API_KEY no ambiente, nunca no HTML."""
import json, os, re, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE = Path(__file__).resolve().parent
HTML = BASE / 'AprovaTJ_site_v30_ia_redacao.html'
MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(HTML.read_bytes());return
        self.send_error(404)
    def reply(self, code, payload):
        raw=json.dumps(payload,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        if self.path!='/api/corrigir-redacao':return self.reply(404,{'erro':'Rota não encontrada'})
        if int(self.headers.get('Content-Length','0'))>30000:return self.reply(413,{'erro':'Texto muito longo'})
        try:
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));tema=str(data.get('tema',''))[:300];texto=str(data.get('texto',''))
            if not 80<=len(texto.split())<=2500:return self.reply(400,{'erro':'A redação deve ter entre 80 e 2500 palavras'})
            key=os.getenv('GEMINI_API_KEY');
            if not key:return self.reply(503,{'erro':'Configure GEMINI_API_KEY no servidor para ativar a IA'})
            instruction='''Você é um professor de redação para concursos. Analise criticamente uma redação dissertativo-argumentativa em português do Brasil. Não presuma critérios oficiais específicos da Vunesp sem rubrica fornecida. Seja construtivo, rigoroso, cite trechos reais e não invente citações. Retorne APENAS um objeto JSON com: nota_estimada (inteiro 0 a 100), resumo (string), estrutura (string), argumentacao (string), coesao (string), gramatica (string), adequacao_ao_tema (string), trechos (array de objetos trecho, problema, sugestao), proximos_passos (array de strings).''' 
            payload={'system_instruction':{'parts':[{'text':instruction}]},'contents':[{'parts':[{'text':'TEMA: '+tema+'\n\nREDAÇÃO:\n'+texto}]}],'generationConfig':{'responseMimeType':'application/json','temperature':0.2}}
            url='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent'
            req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
            with urllib.request.urlopen(req,timeout=55) as response: result=json.load(response)
            body=result['candidates'][0]['content']['parts'][0]['text'];feedback=json.loads(body)
            return self.reply(200,feedback)
        except urllib.error.HTTPError as e:
            return self.reply(502,{'erro':'Serviço de IA retornou HTTP '+str(e.code)+'. Confira a chave, o modelo e a cota gratuita.'})
        except Exception:
            return self.reply(502,{'erro':'Não foi possível corrigir agora. Confira a conexão e tente novamente.'})

if __name__=='__main__':
    print('Acesse http://127.0.0.1:8765 (não publique este servidor sem autenticação e limites de uso)')
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
