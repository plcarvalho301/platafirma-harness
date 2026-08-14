# Prototipo do adaptador headless — achados medidos (14/08/2026)

Prova de mecanismo do card 448, feita fora da stack enquanto a fabrica constroi o
447. Claude Code 2.1.220 no host, conta do dono (`apiKeySource: none`, OAuth).

## O que ficou provado por execucao

- **O chamador escolhe o id da sessao** (`--session-id <uuid>`). Nao e preciso
  capturar id gerado nem guardar mapa sala->fita em lugar nenhum.
- **`-r <uuid>` retoma o contexto**: gravado "banana 41" no giro 1, o giro 2
  respondeu "41" sem receber o numero de novo.
- **Fita inexistente falha limpo**: `No conversation found with session ID: ...`.
  E o gancho de recuperacao, nao um erro a tratar como incidente.
- **`--output-format stream-json --verbose`** entrega um JSON por linha:
  `system/init`, `assistant`, `rate_limit_event`, `result`.
- **`rate_limit_event` traz `resetsAt` e `overageStatus`** — a sala pode dizer ao
  dono quando a janela volta, em vez de so falhar.
- **`result` traz `total_cost_usd`, `usage` e `is_error`** — custo por giro sai de
  graca, sem instrumentacao nossa.

## Decisao de desenho que isto habilita

**A sala E a fita.** `session-id = uuid5(NS, room_id)`: nenhum estado
intermediario, e a rotacao de sala do card 449 troca a fita como efeito colateral
de trocar de sala. Sem tabela, sem arquivo, sem limpeza casada de mapa.

## Fronteira com claudinho-IA

O prototipo descarta `thinking`, `tool_use` e `tool_result` no transporte — o
criterio "sem raciocinio intermediario na sala" e mecanico, nao depende de
prompt. O que a fita DIZ (abertura por monta-sessao, texto de cada anel de erro,
compactacao visivel) pluga sobre a interface `despacha()` sem tocar isto.

## O que este prototipo NAO e

Nao e o verbo `chat`, nao tem cabecalho de arq:0037, nao entra em `bin/` e nao
tem AS nenhum do outro lado. Vive em branch propria (`ti/448-adaptador-headless`)
e nao vai a main antes do 447 fechar — o merge da fabrica tem prioridade sobre a
mesma arvore.
