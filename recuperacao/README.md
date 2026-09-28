# recuperacao

Pasta do harness com a biblioteca do Recuperador: lê as seis fontes de estado (registro, fila, mesa,
wiki, acervo, board) e devolve um envelope com procedência, disjuntor, PEP por fonte e cache.
Importada pelos verbos da release (`monta-sessao`, `situacao`); não é o PDP, que mora em `politica-acesso/`.

Por que existe: Recuperação, o Recuperador e o envelope de falha — `acervo ler casa adr arq:0064`;
O Recuperador mora no plano de comando — `acervo ler casa adr arq:0067`.

## Como sobe

Não roda sozinha. Entra em produção com a família, e a promoção constrói o venv `recuperacao` a
partir de `recuperacao/uv.lock`:

```
release promover platafirma-harness <sha>
```

Para trabalhar nela num clone, desta pasta:

```
uv sync --locked --group dev
```

## Como se testa

Pré-requisito: o tokenizador `qwen2.5.json` (vocabulário de 151.643 entradas) em
`terceiros/tokenizers/` da árvore, ou apontado por `PLATAFIRMA_TOKENIZADOR`. Ele não mora no repo;
a fonte é `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/resolve/main/tokenizer.json`.

```
teste rodar recuperacao
```

Passou quando sai `suite VERDE` e exit 0. Sem o tokenizador, quatro testes de teto de envelope
falham com «tokenizador ausente» e o resto passa: é falta de pré-requisito, não regressão. De fora
da casa, desta pasta, como faz `.github/workflows/recuperacao-tests.yml`:

```
PLATAFIRMA_TOKENIZADOR=<caminho>/qwen2.5.json uv run --group dev pytest . -q
```

## Onde está o quê

| arquivo | o que tem |
|---|---|
| `envelope.py`, `fontes.py` | o envelope e seus enums; as seis fontes, classe e timeout |
| `adaptadores/` | um adaptador por fonte, sobre o contrato de `adaptadores/base.py` |
| `disjuntor.py`, `pep.py`, `cache.py` | disjuntor por fonte, imposição da política por fonte, cache por fonte |
| `gold.py` | gerador de gold das fontes exatas |
| `roteador_chapeu.py`, `situacao.py` | rota de chapéu da abertura e o estado que `situacao` serve |
| `docs/recuperador.md` (raiz do repo) | contrato do envelope, dos adaptadores, do PEP e do cache, com o medido |
