"""AprovaTJ: servidor Flask para Render. Chave GEMINI_API_KEY somente no ambiente."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30_000
BASE = Path(__file__).resolve().parent
HTML = BASE / 'AprovaTJ_site_v30_ia_redacao.html'
MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

@app.get('/health')
def health():
    return jsonify(status='ok', html_disponivel=HTML.is_file())

@app.get('/')
@app.get('/index.html')
def index():
    if not HTML.is_file():
        return ('Servidor online. Para abrir o AprovaTJ, envie também '
                'AprovaTJ_site_v30_ia_redacao.html ao repositório.', 200,
                {'Content-Type': 'text/plain; charset=utf-8'})
    return send_file(HTML, mimetype='text/html')

@app.post('/api/corrigir-redacao')
def corrigir():
    if not request.is_json:
        return jsonify(erro='Envie JSON com tema e texto.'), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(erro='Dados inválidos.'), 400
    tema = str(data.get('tema') or '')[:300]
    texto = str(data.get('texto') or '')
    if not 80 <= len(texto.split()) <= 2500:
        return jsonify(erro='A redação deve ter entre 80 e 2500 palavras.'), 400
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        return jsonify(erro='GEMINI_API_KEY não configurada no Render.'), 503
    instruction = ("Você é professor de redação para concursos brasileiros. Analise criticamente "
        "a redação dissertativo-argumentativa. Não presuma critérios oficiais específicos "
        "da Vunesp sem rubrica. Não invente trechos. Retorne SOMENTE JSON com campos: "
        "nota_estimada (inteiro 0 a 100), resumo, estrutura, argumentacao, coesao, "
        "gramatica, adequacao_ao_tema (strings), trechos (array de objetos com trecho, "
        "problema e sugestao), proximos_passos (array de strings).")
    payload = {'system_instruction': {'parts': [{'text': instruction}]},
               'contents': [{'parts': [{'text': 'TEMA: '+tema+'\n\nREDAÇÃO:\n'+texto}]}],
               'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.2}}
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + MODEL + ':generateContent'
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': key}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=55) as response:
            result = json.load(response)
        feedback = json.loads(result['candidates'][0]['content']['parts'][0]['text'])
        if not isinstance(feedback, dict):
            raise ValueError('Resposta inesperada')
        return jsonify(feedback)
    except urllib.error.HTTPError as exc:
        return jsonify(erro=f'Gemini retornou HTTP {exc.code}. Confira chave, modelo e limites gratuitos.'), 502
    except (ValueError, KeyError, IndexError, TimeoutError, urllib.error.URLError):
        return jsonify(erro='Não foi possível corrigir agora. Tente novamente.'), 502

@app.errorhandler(413)
def too_large(_):
    return jsonify(erro='Texto muito longo.'), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
