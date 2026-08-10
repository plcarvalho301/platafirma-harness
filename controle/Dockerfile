# Imagem única, dois serviços (agregador e tela) no mesmo compose — ver
# compose.yaml pro comando de cada um. Python 3.12 (decidido pelo card),
# venv por uv.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      docker.io \
      && rm -rf /var/lib/apt/lists/*
# git: monta-sessao/conferir chamam `git` de verdade. docker.io: só o cliente
# — o socket vem por bind mount (compose.yaml), o daemon é o do host.

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY harness_controle ./harness_controle
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
