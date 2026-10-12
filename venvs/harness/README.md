# harness

Pasta de `venvs/` que declara o ambiente Python `harness` da release: as bibliotecas que os verbos em
Python e as units do harness importam (banco de sessão, cache, tokenizador, política de acesso,
pesquisa). Não tem código; consumidores e porquê de cada pacote no `pyproject.toml`.

## Como sobe

`release promover` constrói o ambiente sozinho, a partir do `uv.lock`, em
`/opt/platafirma/venv/harness-<hash do lock>`, e o aponta em
`/opt/platafirma/current/venv/harness`:

```
release promover platafirma-harness <sha>
```

Para construir o mesmo ambiente num clone, a partir da raiz:

```
uv sync --frozen --no-dev --no-install-project --project venvs/harness
```

Mudou dependência: edite `pyproject.toml`, rode `uv lock --project venvs/harness` e commite o
`uv.lock` junto. Lock novo é ambiente novo na promoção seguinte; pacote instalado à mão no
ambiente servido some na próxima.

## Como se testa

Sem suíte. Confere-se que o ambiente servido importa o que declara:

```
/opt/platafirma/current/venv/harness/bin/python -c "import psycopg, redis, tokenizers, yaml, httpx, crawl4ai"
```

Passou quando sai com exit 0, sem saída. Depois, um verbo que depende dele de ponta a ponta:
`mesa ver` responde sem `ModuleNotFoundError`.

## nltk fora do ambiente (#3461)

`nltk` não está no lock: `[tool.uv] exclude-dependencies` o tira, com `joblib`, `cloudpickle` e
`defusedxml`, que só ele puxava. Motivo: GHSA-8mgp-746c-j5xp (HIGH, sem versão corrigida até
3.10.3); o crawl4ai o declara, mas o `pesquisar` só usa `DefaultMarkdownGenerator` e
`PruningContentFilter`, que não o tocam. Ficam sem funcionar, e a casa não os chama,
`NlpSentenceChunking`, `TopicSegmentationChunking` e `load_nltk_punkt` do crawl4ai.

Confere-se no ambiente servido, depois de promover um lock novo:

```
/opt/platafirma/current/venv/harness/bin/python -c "import nltk"
```

Tem de falhar com `ModuleNotFoundError`. Depois, um `pesquisar ler <url>` de verdade sobre uma
página pública tem de devolver markdown, e `release conferir dependencias --avisos` não pode mais
acusar `nltk`.
