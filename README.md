# platafirma-harness

Módulo do harness (`arq:0019`): a superfície de contato entre as personas
(claudinhos/claudinhas) e a plataforma. Dono: claudinho-IA.

## Entra

- **Fontes das skills** entregues ao claude.ai (a cópia entregue é classe B —
  copiada-pra-fora — e carrega carimbo de frescor).
- **Tooling de export e carimbo** — script que gera o artefato de upload com
  `origem: <repo>@<blob_sha>`, `fonte: <path>`, `sincronizado_em: <ISO 8601>`.
  Carimbo à mão é proibido pela spec: mente por construção.
- **MCP do harness** — predicado do mapa de entrypoints e `identity_check(persona)`.
- **Verbos de operação** (`bin/`) — o que toda cadeira chama por `run_command`:
  `fila`, `monta-sessao`, `tarefas` (rastreador), `infra` (contêiner, unit,
  timer), `acervo escada`, `longjob`, `seg`. Fonte única: `~/AI/bin` e
  `~/.local/bin` são symlink, e `conferir procedencia` reprova quando deixa de
  ser verdade.
- **Identidade e plano de controle** (`agente/`, `ops-server/`) — o pacote de
  conta da fábrica e o fonte do MCP de operação, trazidos do `platafirma-core`
  no #396: quem serve a plataforma às personas mora no módulo do harness.

## Não entra

- MCP de outro serviço — mora no repo que roda o serviço. O `ops-server` não é
  exceção a isso e sim aplicação: o serviço que ele serve é o próprio harness,
  a superfície de contato. Quem o **sobe** segue no core (`deploy/setup-ops.sh`).
- `CLAUDE.md`/`AGENTS.md` de outros repos — voz de cada repo.
- Fila v0 (`fila/`) — runtime, sem repo por design.

## Relação com o motor

O harness é **cliente** da malha de mensageria (`platafirma-motor`, `arq:0017`/`arq:0018`).

## Diretórios de topo

Declarados por `arq:0042`; `conferir repo platafirma-harness` mede contra esta lista.

| Diretório | O que é |
|---|---|
| `bin/` | verbos de operação chamados por toda cadeira; fonte única, `~/AI/bin` é symlink |
| `hooks/` | gate de commit da `arq:0042` (`pre-commit`); instala-se com `git config core.hooksPath` |
| `personas/` | texto canônico de cada cadeira, mais template e higiene de redação |
| `tool-manifest/` | manifesto de ferramental por cadeira, mais o `GERAL.md` comum |
| `skills/` | fontes das skills entregues ao claude.ai |
| `tooling/` | script de export e carimbo, e o preparo de lote de avaliação |
| `avaliacao/` | instrumentos e conjunto rotulado de avaliação do harness |
| `distribuicao/` | deliberação que reparte o acervo entre as cadeiras, por rodada |
| `experimentos/` | experimento com hipótese declarada e resultado, um diretório cada |
| `registro/` | o declarado que os verbos leem — hoje `stacks.json`, fonte do `deploy` |
| `docs/` | documentação do módulo |
| `diagramas/` | figuras do módulo: fonte `.mmd`/`.d2` e render `<fonte>.svg` |
| `mcp/` | MCP do harness, previsto por `arq:0019`, ainda sem implementação |
| `controle/` | plano de controle do harness: agregador de estado e tela de leitura |
| `caderno/` | caderno durável por cadeira, particionado por chapéu |
| `deploy-harness/` | o que instala o próprio harness num ambiente: units do `sinal` e o instalador |
| `agente/` | pacote de conta da fábrica: `CLAUDE.md`, `settings.json` e o instalador; `~/.claude/*` é symlink daqui |
| `ops-server/` | fonte do MCP de operação (`platafirma-ops`); sobe por `platafirma-core:deploy/setup-ops.sh`, fora do compose |
| `.claude/` | configuração do Claude Code na estação emprestada |

Spec de referência: [PlataFirma:Produto/harness/spec](https://wiki.platafirma.org/index.php/PlataFirma:Produto/harness/spec).

- Abrir a PlataFirma de uma estação emprestada: `docs/estacao-emprestada.md`
- Instanciar a fábrica no Claude Code: `docs/instanciacao-fabrica.md`
