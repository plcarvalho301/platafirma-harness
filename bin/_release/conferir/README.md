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
- `verbo`: verbos instalados no PATH contra o acervo e o repositório da release.
- `skill`: skills servidas contra as fontes no harness.
- `procedencia`: caminhos executáveis contra o inventário declarado.
- `superficie`: conformidade dos arquivos de superfície e conectores MCP.
- `ferramental`: golden record `acervo.ferramental` contra o host.
- `front`: telas e aplicações web contra regras de fronteira.
- `sessao`: pacote de abertura servido e frescor por peça.
- `chapeu`: conformidade de chapéus das personas.
- `pdp`: conformidade de políticas de acesso.
- `alcance`: inventário de alcance de recursos.
- `card`: integridade de cards citados.
- `jobs`: timers do systemd --user contra declarantes da release.
- `acervo`: predicados de fidelidade e invariantes I1..I13 contra os bancos rag e motor.
- `dependencias`: travas e inventário de dependências das famílias.
- `sessao-orfa` (card #3375): contagem de `sessao_id` gravados no acervo e na fita sem sessão canônica em `sessao.sessao` (legado de fontes recicláveis e gravações com o banco de sessão fora), comparada contra a linha de base.
