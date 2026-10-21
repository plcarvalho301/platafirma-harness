# Conferencia de Release (`release conferir <classe>`)

Mede o que está servido em produção contra o que está declarado, por classe de alvo.
Sub-ato do verbo canônico `release` (`bin/release`).

## Contrato de saída e exit code

Todas as classes do servido retornam uma lista de itens avaliados com a estrutura `Veredito` (`resultado.py`):
- `conforme`
- `divergente` (com motivo)
- `indeterminavel` (com motivo)

O exit code agrega a lista de itens:
- `0`: todos os itens conforme.
- `1`: pelo menos um item divergente (pesa mais que indeterminável).
- `2`: uso incorreto / argumentos inválidos.
- `5`: nenhum item divergente e ao menos um indeterminável (banco/serviço fora).

A primeira linha do texto impresso é a âncora colável:
`release conferir <classe> [<alvo>]: <C> conforme · <D> divergente · <I> não consegui olhar — release <sha>`

Com `--json`, retorna objeto com `ancora`, `classe`, `alvo`, `release` e lista de `itens` com `nome`, `estado`, `desde` e `motivo`.

## Classes servidas

- `servico`: contêineres e stacks em execução contra o declarado no compose e nos pontos de deploy.
- `verbo`: verbos instalados no PATH contra o acervo e o repositório da release. Ato que o cabeçalho põe numa face (`# face: <ato>=<face>`) sem `# rotulo:` ou sem `# volta:` sai como **aviso** (`avisos` no `--json`, linha `AVISO` no texto): não pesa no exit e não reprova o gate, porque hoje nenhum cabeçalho declara os campos (arq:0124 §3, R7). Vira divergente depois da carga dos três donos (#3446, #3447, #3448), por decisão escrita.
- `skill`: skills servidas contra as fontes no harness.
- `procedencia`: caminhos executáveis contra o inventário declarado.
- `superficie`: conformidade dos arquivos de superfície e conectores MCP.
- `ferramental`: golden record `acervo.ferramental` contra o host.
- `front`: telas e aplicações web contra regras de fronteira (arq:0057) e, desde o card #3426, o pacote de `platafirma-ui` lido da árvore dela, um item por peça, tela e retrato: **peça sem página** (`src/pf/<tag>.js` sem `<tag` em nenhum `.html` de `exemplo/`, R13); **tela com versão diferente do pacote** (`COPY --from=platafirma/ui:<versão>` de `app/<tela>/Dockerfile` contra `version` de `src/base/package.json`, R1: as telas de hoje que copiam em versão antiga saem divergentes); **retrato do dicionário de atos** (`src/retrato/atos.json`, campo `sha_registro`) contra o sha do registro do ferramental (R45). Sem retrato, ou enquanto o registro não serve o sha (dependência de dados no #3409), o item sai «não consegui olhar», nunca conforme.
- `sessao`: pacote de abertura servido e frescor por peça.
- `chapeu`: conformidade de chapéus das personas.
- `pdp`: conformidade de políticas de acesso.
- `alcance`: inventário de alcance de recursos.
- `card`: integridade de cards citados.
- `jobs`: timers do systemd --user contra declarantes da release.
- `acervo`: predicados de fidelidade e invariantes I1..I13 contra os bancos rag e motor.
- `dependencias`: travas e inventário de dependências das famílias.
- `sessao-orfa` (card #3375): contagem de `sessao_id` gravados no acervo e na fita sem sessão canônica em `sessao.sessao` (legado de fontes recicláveis e gravações com o banco de sessão fora), comparada contra a linha de base.
- `copia [balde|banco|indice]` (card #3763; arq:0022 §6.3, arq:0130 D4): toda materialização viva tem declaração de cópia, por substrato. A declaração mora no schema, por COMMENT `copia-de:` na tabela (fonte, chave, atributos copiados, ato que repõe, modo, reprodutibilidade com método e insumos). `banco` percorre as tabelas do schema `acervo` do rag, `indice` as do schema `motor` do banco do motor, e `balde` os espelhos de leitura (declarado é o que uma impressão reclama; o órfão sai na lista). Tabela que o catálogo da raiz nomeia como substrato golden é fonte e fica à parte; o prefixo de fóssil (`_backup_`, `_mig_`, `_fusao_`, `_osint`) é assinalado. A primeira linha traz o total, as declaradas, as não declaradas e as famílias sem coletor (modelo formal gerado, unit gerada pelo bot, CLAUDE.md da fita, instruções de Project e preferências do claude.ai, projeção de card); as famílias declaradas não reprodutíveis saem em linha à parte. Sai 0 com tudo declarado, 1 com materialização sem declaração ou declaração com defeito, 5 se um substrato não responde. Não expurga nada; o formato da declaração está na spec `entidade-raiz-da-casa`.
