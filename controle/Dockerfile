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

# --- front da PlataFirma: copia em tempo de build de imagem (arq:0056) -------
#
# Ate o card #476 esta tela lia platafirma-arquitetura/design/tokens.css do
# HOST, em tempo de requisicao, por bind mount (TOKENS_CSS_PATH). Isso violava
# o arq:0056 duas vezes: artefato de front morando fora da imagem, e resolvido
# em runtime — nada aqui dizia que versao a tela servia.
#
# Agora o front vem do release platafirma/ui, por COPY --from, e a imagem passa
# a ser autossuficiente: sem o mount do host a tela continua servindo CSS, JS e
# fontes. pf-ui.css ja traz os tokens inteiros (as mesmas declaracoes de
# design/tokens.css) mais Inter e Geist Mono auto-hospedadas por @font-face
# relativo (./fontes/...) — por isso `fontes` precisa ficar irmao do CSS.
#
# Mora dentro do pacote (harness_controle/estatico/pf-ui) de proposito: o
# modulo o encontra por __file__, sem variavel de ambiente e sem caminho
# absoluto, do mesmo jeito que ja encontra estatico/tela.css.
COPY --from=platafirma/ui:0.1.0 /usr/share/nginx/html/pf-ui.js   ./harness_controle/estatico/pf-ui/
COPY --from=platafirma/ui:0.1.0 /usr/share/nginx/html/pf-ui.css  ./harness_controle/estatico/pf-ui/
COPY --from=platafirma/ui:0.1.0 /usr/share/nginx/html/fontes     ./harness_controle/estatico/pf-ui/fontes
COPY --from=platafirma/ui:0.1.0 /usr/share/nginx/html/versao.txt ./harness_controle/estatico/pf-ui/

# arq:0031 — o derivado grava a versao. Mesma forma do carimbo da casa
# (platafirma-conhecimento/wiki/montar-wiki): origem, sha256, em. Editar o
# copiado e erro; o proximo build sobrescreve sem avisar. Vai servido pela
# rota /estatico/pf-ui/origem.txt, para auditar de fora sem abrir a imagem.
RUN set -eu; { \
      echo "origem: platafirma/ui:0.1.0"; \
      echo "sha256: $(sha256sum harness_controle/estatico/pf-ui/pf-ui.css | cut -d' ' -f1)"; \
      echo "em: $(date -Iseconds)"; \
    } > harness_controle/estatico/pf-ui/origem.txt

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 8000
