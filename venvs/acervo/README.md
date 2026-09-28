# acervo

Pasta de `venvs/` que declara o ambiente Python `acervo` da release: as bibliotecas que os verbos do
acervo importam (`boto3` para o objeto da obra no MinIO; `owlready2` e `rdflib` para a projeção
formal da ontologia). Não tem código; consumidores e porquê de cada pacote no `pyproject.toml`.

## Como sobe

`release promover` constrói o ambiente sozinho, a partir do `uv.lock`, em
`/opt/platafirma/venv/acervo-<hash do lock>`, e o aponta em
`/opt/platafirma/current/venv/acervo`:

```
release promover platafirma-harness <sha>
```

Para construir o mesmo ambiente num clone, a partir da raiz:

```
uv sync --frozen --no-dev --no-install-project --project venvs/acervo
```

Mudou dependência: edite `pyproject.toml`, rode `uv lock --project venvs/acervo` e commite o
`uv.lock` junto. Lock novo é ambiente novo na promoção seguinte; pacote instalado à mão no
ambiente servido some na próxima.

O HermiT roda no Java do sistema (`/usr/bin/java`), que não vem daqui.

## Como se testa

Sem suíte. Confere-se que o ambiente servido importa o que declara:

```
/opt/platafirma/current/venv/acervo/bin/python -c "import boto3, owlready2, rdflib"
```

Passou quando sai com exit 0, sem saída.
