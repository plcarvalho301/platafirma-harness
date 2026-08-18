# Modelo de suite — controle/tests

Card #178 (modelo + gatilho) e #204 item 2 (contrato do monta-sessao morto). Medido
em 17/08: 28 failed, 38 passed, 3 errors, rodando `uvx --with redis pytest tests/`.

## Por que a coleta quebrava (entregável c)

`uvx --with redis pytest` sobe um venv efêmero com só pytest+redis — **dependência
adivinhada na linha de comando**, não a declarada em `pyproject.toml`. Três arquivos
importam `starlette`/`httpx` (dependências do projeto, não do dev-group) e por isso
não coletavam. Rodando com `uv run pytest`, que resolve o ambiente a partir de
`pyproject.toml` + `uv.lock` — a dependência declarada, nunca adivinhada — os três
coletam e passam:

```
cd controle
uv sync --locked --group dev
uv run pytest tests/ -q
```

Isto substitui `uvx --with redis pytest`. Nenhum código de produção mudou para
zerar os 3 erros — era o comando de invocação que estava errado.

## Por módulo/verbo — dependência declarada, não adivinhada

| arquivo | verbo/módulo testado | dependência externa real |
|---|---|---|
| `test_contrato_conferir.py` | `conferir` | nenhuma (subprocess + fixtures) |
| `test_contrato_infra.py` | `infra` | nenhuma |
| `test_contrato_monta_sessao.py` | `bin/monta-sessao` | `git` real contra bare local (sem rede); stub de `mesa` em `<raiz>/bin` |
| `test_contrato_tarefas.py` | `tarefas listar --json` | nenhuma nova; **10 falhas pré-existentes, fora de escopo — ver abaixo** |
| `test_contrato_fila.py` | `fila status --json` | pacote `redis` (dev-group); **1 falha pré-existente, fora de escopo** |
| `test_agregador.py` | `harness_controle.agregador` | `starlette`/`httpx` (`[project.dependencies]`) |
| `test_feito_agrupamento.py` | agrupamento do `/feito` | `starlette`/`httpx` |
| `test_web_fumaca.py` | fumaça da tela (`web.py`) | `starlette.testclient` (`[project.dependencies]`) |

Nenhuma dependência aqui é nova: todas já estavam em `pyproject.toml`
(`[project.dependencies]` ou `[dependency-groups].dev`). O que faltava era rodar a
suíte de um jeito que as respeitasse.

## Vermelho conhecido, não desta fatia

`test_contrato_fila.py::test_status_sem_persona_e_sem_todas_vira_uso_incorreto` (1) e
os 10 de `test_contrato_tarefas.py` (LOTE 1, flag `--json` em `tarefas listar`) são
pré-existentes e **fora do escopo do #178/#204** — o card pede os 3 erros de coleta
zerados e a suíte de contrato do monta-sessao reescrita, não a suíte inteira verde.
Ficam vermelhos no gatilho abaixo, e ficam DECLARADOS aqui em vez de mascarados
(`xfail`/`skip`/`continue-on-error`): mascarar um defeito real é pior do que
declará-lo — era exatamente o problema que motivou este card (`quem rodar a suíte
lê falhas como ruído`). Card próprio, se/quando existir, os fecha.

## Gatilho de execução (entregável b)

`.github/workflows/controle-tests.yml`, na raiz do repo — roda em push/PR que
tocam `controle/**`. Sem ele o modelo acima é documento, não regra.
