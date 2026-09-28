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
