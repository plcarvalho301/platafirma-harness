FROM python:3.12-slim

RUN pip install --no-cache-dir "starlette==0.41.3" "uvicorn==0.32.1" "httpx==0.28.1"

WORKDIR /app
COPY app.py /app/app.py

# Sem root: o corpo do colaborador externo nao precisa de privilegio nenhum.
RUN useradd -u 10001 -m jaiminho
USER jaiminho

EXPOSE 8021
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8021"]
