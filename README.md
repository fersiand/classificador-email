```Classificador de E-mails

Autor: Fernando Andrade

Descrição:
Aplicação para classificar e-mails em Produtivo ou Improdutivo e sugerir uma resposta automática.

Conteúdo do repositório
- app.py — backend (Flask).
- templates/index.html — frontend HTML.
- static/style.css — estilos CSS.
- requirements.txt — dependências.
- Dockerfile, docker-compose.yml — para rodar em container.
- sample_emails/ — exemplos de e-mails.
- classificador.log — criado em runtime para registrar classificações.

Como executar localmente:

1. Crie e ative um virtualenv:
   bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   # venv\Scripts\activate     # Windows
   
2. Instale dependências:
pip install -r requirements.txt

!!OBS: pdfminer.six e openai são opcionais!!

3. Adicione sua chave OpenAI:
export OPENAI_API_KEY="sua_chave_aqui"   # macOS/Linux
setx OPENAI_API_KEY "sua_chave_aqui"     # Windows (cmd)


4. Execute:
python app.py


5. Abra no navegador:
http://127.0.0.1:5000
