# tool-manifest — claudinha-produto

Ambiente: Linux Mint 22.3 (base Ubuntu 24.04), usuário `claudinho` (uid 1001).
Sem sudo direto. Binários próprios em `~/AI/bin`, já no PATH das sessões
`run_command`.

Verificação: `[exec]` executado · `[func]` usado em trabalho real · `[inst]`
presente, sem prova. `[inst]` é confissão, não aval.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool.
> Afirmar de memória o que uma busca recupera é o erro que este manifesto
> existe para cortar. Para FORMA de produto — heurística, régua, métrica de
> fluxo — o `rag_search` vem antes da memória, inclusive antes de propor forma
> nova.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/GERAL.md`.

## Conectores

**platafirma-ops** (`ops.platafirma.org`) — a máquina onde tudo executa.
- `monta_sessao` `[func]` — contexto de abertura numa chamada. Chamar em vez de
  encadear leitura.
- `run_command` `[exec]` — shell como claudinho. É por aqui que sai render,
  upload e git.
- `write_file` `[exec]` / `read_file` `[inst]` — arquivos sob `~/AI`.

**PlataFirma Wiki** (`mcp.platafirma.org`) — canônico, acervo e repos.
- `get_page` / `search_pages` / `edit_page` `[func]` — prosa da wiki. Spec de
  frente e minuta moram aqui.
- `rag_search` / `rag_facets` `[inst]` — forma de produto e de tela. Conferir
  faceta antes de filtrar: faceta despovoada devolve zero sem erro.
- `repo_read` / `repo_grep` `[inst]` — leitura de repo pelo espelho. Frescor
  crítico: ler o clone local por `run_command`, o espelho defasa.
- `upload_file` `[inst]` — **não usar para imagem de tela.** Ver armadilhas.

**Figma** (`mcp.figma.com`) `[inst]` — bloqueado por assento. Ver pendências.

**Google Drive** `[inst]` — só conteúdo de texto passado como argumento;
binário não cabe. Ver armadilhas.

## design — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `design/tokens.css` | fonte de verdade de tipo, cor, espaço, forma, foco. Nenhuma superfície repete valor | `[func]` |
| `design/componentes.md` · `diagramas.md` | os sete componentes e a gramática vetorial, antes de inventar peça nova | `[func]` |
| Chrome headless via `puppeteer-core` | renderizar wireframe HTML em PNG. Script e uso em `platafirma-arquitetura/design/wireframes/render.mjs`; acusa vazamento horizontal, que o screenshot esconde cortando | `[exec]` |
| `python3 -c "from PIL import Image"` | quantizar o PNG antes de subir; wireframe tem poucas cores e cai a 1/5 | `[exec]` |
| `fc-list \| grep Inter` | conferir que a Inter existe no host antes de render — sem ela o wireframe sai em fonte genérica e a régua tipográfica não se prova | `[exec]` |

## produtizacao — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `tarefas ler` · `listar` · `listar-tudo` | estado do card antes de escrever spec. `listar-tudo` inclui fechados, e é como se acha fóssil de card | `[exec]` |
| `tarefas comentar` | ajuste fino e achado que não muda escopo. Card, nunca mensagem | `[exec]` |
| `fila enviar --tipo pedido` | o que trava meu trabalho e depende de outra cadeira. Só isso | `[exec]` |
| `conferir repo --staged` | antes de commitar, é o gate do `arq:0042` | `[exec]` |

## canais — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `curl` + Action API do MediaWiki (`~/AI/platafirma-conhecimento/.env`) | publicar imagem que o dono precisa abrir no celular | `[exec]` |
| `python3` heredoc via `run_command` | substituição multi-ocorrência em markdown commitado | `[exec]` |

## Armadilhas medidas

- `fila enviar` sem `PF_CADEIRA=<cadeira>` ou `--eu` sai com exit 2 e não abre
  caixa nenhuma. Não é bug: já houve caixa alheia sobrescrita.
- **Binário não sobe por tool.** `upload_file` da wiki e `create_file` do Drive
  recebem o conteúdo como argumento, ou seja o base64 atravessa a saída do
  modelo — e um PNG de 66 KB vira ~88 mil caracteres, acima do teto de saída por
  giro. O caminho é `curl` da própria máquina, onde os bytes nunca passam por
  mim. Medido em 10/08/2026.
- **Wireframe em PDF pesa mais que em PNG** (217 KB contra 66 KB na mesma tela):
  o Chrome embute a Inter inteira. Para leitura em tela, PNG quantizado.
- `rag_facets` antes de filtrar `rag_search`: valor legítimo com corpus vazio
  devolve zero sem erro, e zero por faceta despovoada é indistinguível de zero
  por ausência de cobertura.

## Pendências declaradas

- **Figma bloqueado.** `create_new_file` devolve `No approval received`;
  `whoami` mostra `seat: View` no plano starter. Serviria para entregar peça de
  apresentação; para wireframe o HTML sobre `tokens.css` é melhor, porque é o
  artefato que a fábrica implementa sem tradução no meio. Falta: assento Editor.
- **Verbo de render de wireframe.** A receita Chrome + PIL + upload está em três
  passos manuais. Candidata a verbo em `bin/`; dono seria claudinho-TI.
- **Saída legível por máquina nos verbos que alimentam tela.** Exigência escrita
  em `spec_plano-de-controle-harness.md` §7; decisão de claudinho-TI.
