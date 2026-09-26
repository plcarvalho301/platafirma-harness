## conhecimento curado

- Exit 1 tem sentido oposto em lote encadeado e em esteira de promoção: no lote
  encadeado (spec ambiente-de-desenvolvimento §6, #3149), exit 0 e exit 1 SEGUEM a
  cadeia (1 é mérito: já feito, não existe, já em dia); na esteira do `release
  promover` (#3150), exit 1 no gate é reprovação e PARA. É a mesma tabela de exit
  (arq:0110 §4) lida com regra de parada oposta por contexto — não generalizar uma
  regra de "exit 1 sempre continua" ou "sempre para" sem checar se é lote ou gate.
- A lógica de iterar lote (CAP, lote_next, omitido_por_teto, auditoria por item) está
  hoje triplicada em ops-server/server.py: run_command, read_file (paths[]) e a tool
  de verbo cada uma reimplementa o próprio laço. Dívida técnica conhecida; extrair um
  iterador comum (`_itera_lote`) é o módulo profundo óbvio quando alguém tocar o lote
  encadeado do #3149, porque aí as três tools ganham a mesma regra de parada de graça.

## diário de bordo

- 2026-09-26 — fui commitar o guia desenvolvimento em platafirma-casa (#3148):
  `repo commitar` avisou em stderr "worktree wt/platafirma-casa/engenharia nao existe
  — usando fallback /home/claudinho/AI/platafirma-casa" (o clone compartilhado da
  conta, não uma bancada da cadeira). Rodei `repo git platafirma-casa worktree list`
  e achei o ramo do card preso numa worktree por sessão de outra fita
  (wt/platafirma-casa/96c4c6a2-.../, ramo fabrica/3148-guia-desenvolvimento). Sem
  bancada própria da cadeira, escrevi e commitei a partir daquele caminho de sessão
  alheia — funcionou porque o ramo era o certo, mas é o cenário que o #3149 existe
  para fechar (bancada por cadeira e card, sem fallback). Nenhum contorno definitivo:
  quando #3149 subir, a próxima fita de engenharia em platafirma-casa já deve abrir
  com `repo abrir platafirma-casa <card> --slug <s>` e cair no caminho certo direto.