# --------------------------------------------------------
# Classificador de E-mails — Fernando Andrade
# - Recebe texto ou arquivo (.txt / .pdf)
# - Classifica como "Produtivo" ou "Improdutivo"
# - Sugere uma resposta automática
# Observação:
# - Tenta usar OpenAI (se API key estiver configurada).
# - Se OpenAI não estiver disponível, usa fallback por palavras-chave.
# - Log simples para registrar classificações (arquivo classificador.log).
# --------------------------------------------------------

import os
import re
import json
import logging
import datetime
from flask import Flask, render_template, request, flash, send_from_directory
from werkzeug.utils import secure_filename

# Tentativa de importação opcional: openai (se não existir, executa sem ele)
try:
    import openai
except Exception:
    openai = None

# Tentativa de importação opcional: pdfminer para extrair texto de PDFs
try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:
    pdf_extract_text = None

# -------------------- Configurações básicas --------------------
APP_NAME = "Classificador de E-mails — Fernando Andrade"
UPLOAD_FOLDER = "uploads"
LOG_FILE = "classificador.log"
ALLOWED_EXTENSIONS = {"txt", "pdf"}

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET", "trocar_por_uma_chave_secreta")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

# Garante que a pasta de uploads exista
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Configura logging básico para debug e para arquivo de log simples
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("email_classifier")

# Função que registra uma entrada simples no log do classificador
def registrar_log(texto, categoria):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().isoformat()
            snippet = (texto or "")[:200].replace("\n", " ")
            f.write(f"{ts} | {categoria} | {snippet}\n")
    except Exception as e:
        logger.warning("Falha ao gravar log local: %s", e)

# -------------------- Verificações --------------------
def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def ler_arquivo(caminho):
    """
    Lê o conteúdo de .txt ou .pdf (se pdfminer disponível).
    Retorna string vazia em caso de erro ou tipo não suportado.
    """
    try:
        extensao = os.path.splitext(caminho)[1].lower()
        if extensao == ".txt":
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif extensao == ".pdf" and pdf_extract_text:
            try:
                return pdf_extract_text(caminho)
            except Exception as e:
                logger.warning("Erro ao extrair PDF: %s", e)
                return ""
        else:
            return ""
    except Exception as e:
        logger.exception("ler_arquivo falhou: %s", e)
        return ""

# -------------------- Classificador por palavras-chave (fallback) --------------------
def classificar_fallback(texto):
    """
    Classificação simples por palavras-chave.
    Retorna (categoria, resposta_sugerida).
    Código simples e transparente para ser um fallback confiável.
    """
    if not texto or not texto.strip():
        registrar_log(texto or "", "Improdutivo")
        return "Improdutivo", "Obrigado pela mensagem!"

    t = texto.lower()

    palavras_produtivas = [
        "status", "erro", "problema", "ajuda", "solicitação", "solicitacao",
        "anexo", "relatório", "relatorio", "suporte", "ticket", "falha",
        "incidente", "reunião", "reuniao", "agendar", "urgente", "pendente"
    ]
    palavras_improdutivas = [
        "obrigado", "obrigada", "feliz natal", "boas festas", "parabéns", "parabens", "abraços"
    ]

    # Se encontrar qualquer palavra produtiva, classificamos como Produtivo
    for p in palavras_produtivas:
        if p in t:
            categoria = "Produtivo"
            resposta = (
                "Olá, recebemos seu e-mail. Agradecemos o contato e iremos verificar sua solicitação. "
                "Retornaremos no prazo de um dia útil. Se possível, envie mais detalhes ou anexe arquivos relevantes."
            )
            registrar_log(texto, categoria)
            return categoria, resposta

    # Se encontrar palavras de cortesia, marcamos como Improdutivo
    for p in palavras_improdutivas:
        if p in t:
            categoria = "Improdutivo"
            resposta = "Agradeço a mensagem e o contato!"
            registrar_log(texto, categoria)
            return categoria, resposta

    # Padrão conservador: improdutivo
    registrar_log(texto, "Improdutivo")
    return "Improdutivo", "Agradeço o contato!"

# -------------------- Classificação com OpenAI (opcional) --------------------
def classificar_com_openai(texto):
    """
    Tenta usar a API da OpenAI para classificar e gerar resposta.
    Retorna (categoria, resposta) em caso de sucesso, ou None em caso de erro.
    Nota: a chamada espera que OPENAI_API_KEY esteja definida no ambiente.
    """
    if not openai:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        openai.api_key = api_key

        # Prompt claro para o modelo: JSON com category e reply
        prompt = (
            "Classifique o e-mail abaixo em 'Produtivo' ou 'Improdutivo' "
            "e gere uma resposta apropriada em português. "
            "Retorne a saída no formato JSON com chaves: category e reply.\n\n"
            f"E-mail:\n{texto}\n\n"
            "Exemplo de saída: {\"category\": \"Produtivo\", \"reply\": \"...\"}"
        )

        # Chamada de ChatCompletion (SDKs que suportam chat)
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300
        )

        conteudo = resp["choices"][0]["message"]["content"]
        # Extração de um JSON da resposta (texto extra)
        m = re.search(r"\{.*\}", conteudo, re.DOTALL)
        if m:
            parsed = json.loads(m.group(0))
            category = parsed.get("category", "Produtivo")
            reply = parsed.get("reply", "")
            # registra e retorna
            registrar_log(texto, category)
            return category, reply
        else:
            # Se não retorna JSON, devolve tudo como reply e define Produtivo
            registrar_log(texto, "Produtivo")
            return "Produtivo", conteudo

    except Exception as e:
        logger.exception("Erro ao chamar OpenAI: %s", e)
        return None

# -------------------- Função pública de classificação --------------------
def classificar_email(texto):
    """
    Função que tenta usar OpenAI (se disponível) e, se falhar, usa fallback.
    Sempre retorna (categoria, resposta).
    """
    # Primeira tentativa: OpenAI (se tudo estiver configurado)
    res = classificar_com_openai(texto)
    if res:
        return res
    # Caso contrário, fallback simples
    return classificar_fallback(texto)

# -------------------- Rotas do Flask --------------------
@app.route("/", methods=["GET", "POST"])
def index():
    """
    Página principal com formulário:
    - GET: mostra formulário
    - POST: recebe texto ou arquivo, classifica e retorna resultado
    """
    resultado = None

    if request.method == "POST":
        # Pega texto do formulário (campo 'email_text')
        email_texto = request.form.get("email_text", "").strip()

        # Se não colou texto, verifica envio de arquivo (campo 'email_file')
        if not email_texto and "email_file" in request.files:
            arquivo = request.files["email_file"]
            if arquivo and arquivo.filename:
                # Valida a extensão
                if not allowed_file(arquivo.filename):
                    flash("Formato de arquivo não permitido. Use .txt ou .pdf", "danger")
                    return render_template("index.html", resultado=None)
                # Salva o arquivo no diretório uploads com nome seguro
                filename = secure_filename(arquivo.filename)
                caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                try:
                    arquivo.save(caminho)
                    email_texto = ler_arquivo(caminho)
                except Exception as e:
                    logger.exception("Erro ao salvar/ler arquivo: %s", e)
                    flash("Erro ao processar o arquivo enviado.", "danger")
                    return render_template("index.html", resultado=None)

        # Se nenhum texto foi enviado, pede ao usuário
        if not email_texto:
            flash("Por favor, insira texto ou envie um arquivo válido (.txt ou .pdf).", "warning")
            return render_template("index.html", resultado=None)

        # Classifica o texto e prepara resultado para a tela
        categoria, resposta = classificar_email(email_texto)
        resultado = {"texto": email_texto, "categoria": categoria, "resposta": resposta}

    # Renderiza template (index.html)
    return render_template("index.html", resultado=resultado, app_name=APP_NAME)

# Rota para baixar arquivo enviado (depuração)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

# -------------------- Executa o servidor --------------------
if __name__ == "__main__":
    # Para dev, debug=True ajuda a ver erros; em produção usar servidor WSGI (gunicorn) sem debug.
    app.run(debug=True, host="0.0.0.0", port=5000)