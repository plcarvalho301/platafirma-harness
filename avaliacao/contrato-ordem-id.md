# Contrato de `ordem_id` — chave de join da fase D (épico #283)

Card #2902 (dados). Fecha o buraco que trava o #2908 (medir D) e o #2894 (e2e).

## Problema, provado no log (28/08)

O join de D precisa casar DOIS eventos em var/log/ops:
- `sessao_aberta` (lado ordem, emitido por monta_sessao)
- `consulta`      (lado disparo, emitido por motor buscar)

Não há UMA chave estável comum. Medido na fonte:
- `sessao_aberta`: sessao='-' (100%, 32697/32697), ordem_id ausente.
- `consulta`: sessao='s<hex>' MAS o valor vem de `id(objeto)` (server.py:152),
  que muda a cada subprocesso — não é estável nem DENTRO de uma fita.
  ordem_id='-'.

Conclusão: `sessao` (mcp-session-id / id do objeto) NÃO serve de chave. É por
conexão e volátil. A chave tem de ser `ordem_id`, e ele não é gerado por ninguém.

## Contrato (decisão de dados — isto é o que os dois lados implementam)

`ordem_id` = identificador de UMA fita (uma ordem do dono), estável do início ao
fim da fita, gravado idêntico nos dois eventos.

Forma: `o<AAAAMMDDTHHMMSS>-<6hex>` — timestamp de abertura da fita + sufixo
aleatório. Gerado UMA vez, na abertura, por `monta_sessao`.

Propagação (o mecanismo que já existe, reaproveitado):
1. `monta_sessao` gera `ordem_id` na abertura e o grava no evento `sessao_aberta`
   (hoje o `_audit` da linha ~863 não passa ordem_id — passa a passar).
2. O mesmo valor é exportado como `PF_ORDEM_ID` no env do subprocesso de
   run_command (server.py:328 já injeta PF_SESSAO ali — adicionar PF_ORDEM_ID
   do lado, mesma linha).
3. `motor buscar` já lê `os.environ["PF_ORDEM_ID"]` (bin/motor:281) e grava no
   evento `consulta`. Esse lado JÁ ESTÁ pronto — só recebe '-' porque o env não
   é populado.

Então o trabalho residual é só (1) e (2), ambos no server (monta_sessao).

## Fronteira — quem faz o quê

- Contrato e chave: DADOS (este documento). Fechado.
- Gerar+gravar ordem_id em sessao_aberta e exportar PF_ORDEM_ID: toque em
  server.py = deploy sob TI, com a IA (dona do monta_sessao lógico). Roteado.
- Consumir no join: DADOS (mede_d.py já ancora em sessao; troca para ordem_id
  numa linha quando os dois lados gravarem — a função mede_d() já isola a chave).

## Por que ordem_id e não sessao (a régua)

`ordem_id` é 1-por-fita por construção. `sessao` é 1-por-conexão e volátil.
D = "a ordem do dono gerou consulta ao acervo?" é uma pergunta por-fita.
Ancorar em sessao mediria "a conexão gerou consulta", agregando abas distintas —
o limite superior que o Elias (R1) já apontou. ordem_id remove a ambiguidade.
