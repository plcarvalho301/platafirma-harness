# Imagem da borda das faces do cubo de controle (card #3516). Um serviço, uma imagem, um processo.
#
# `python:3.13-slim`, como a API do rastreador (a borda imita a dela). Nada de front aqui: a tela de cada
# face é serviço próprio da platafirma-ui, e a borda não serve rota de tela (arq:0057).
FROM python:3.13-slim

WORKDIR /app

# Camada de dependência antes do código: mexer na borda não reinstala o uvicorn.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Arquivo nomeado, nunca `COPY . .`: módulo novo entra AQUI também, ou o processo morre em
# ModuleNotFoundError na subida (medido no card #482 do rastreador).
COPY borda.py ./

EXPOSE 8000
# `0.0.0.0` é a interface do CONTÊINER; a garantia de loopback é o prefixo `127.0.0.1:` do compose.
CMD ["uvicorn", "borda:app", "--host", "0.0.0.0", "--port", "8000"]
