# Imagem única, dois serviços (agregador e tela) no mesmo compose — ver
# compose.yaml pro comando de cada um. Python 3.12 (decidido pelo card),
# venv por uv.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      && rm -rf /var/lib/apt/lists/*
# git: monta-sessao/conferir chamam `git` de verdade.
#
# docker CLI NAO vem por apt: o docker.io do slim nao deixou binario nenhum e o
# build passou em silencio. Vem por bind mount do CLI do host (compose.yaml),
# junto com o socket — mesma versao que o daemon, por construcao.
#
# Os verbos do host tem shebang /home/claudinho/AI/.venv-harness/bin/python, que
# e symlink para /usr/bin/python3. A imagem oficial instala em /usr/local/bin,
# entao sem este link todo verbo Python morre com "No such file or directory" —
# erro que aponta para o interpretador, nao para o script, e custa caro de ler.
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY harness_controle ./harness_controle
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
