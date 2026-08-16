FROM python:3.12-slim

# O PAP e o PDP NAO entram na imagem: vem por bind read-only de
# `politica-acesso/`, para que merge no PAP valha sem rebuild — mesma
# propriedade que o ops-server tem por rodar do clone.
WORKDIR /opt/pf/jaiminho-server

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

RUN useradd -r -u 10001 jaiminho-server
USER jaiminho-server

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
