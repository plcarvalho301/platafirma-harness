# Minuta — Gold set por modo de falha de uso do acervo

**Objetivo (do dono):** montar perguntas ÚTEIS para **detectar** os modos de falha de uso
do acervo pelas cadeiras. Não é atribuir culpa — é detectar. Ponto.

**Assinam (sign-off pendente):** produto · IA · gestão-estratégica · dados.

**Anexo:** `gold-proposto-modos.jsonl` — gold set proposto, ~20 por modo, do material existente.

---

## Posição e objetivo do dono (Pedro) — os seis modos

Modos de falha ao longo da cadeia `prompt → pensar em consultar → procurar → recuperar → usar → responder`:

- **(a)** leu o prompt e sequer parou pra pensar se tinha algo no acervo.
- **(b)** leu o prompt, montou a sessão e tirou do nada uma solução sem procurar no acervo,
  **mesmo com insumo injetado** (o próprio chapéu e conceito canônico dele).
- **(c)** interpretou o prompt e procurou errado.
- **(d)** procurou certo e não achou algo que já está no acervo.
- **(e)** procurou certo, recuperou certo, e a resposta ignorou o que achou e respondeu de treino.
- **(f)** procurou certo, recuperou certo, usou o texto e ainda assim a resposta saiu ruim
  (por outro motivo qualquer, avaliado pelo dono).

## Posição inicial de dados (Olga Corujeira)

Os seis são **uma cadeia**, e a natureza da falha muda em cada elo — separá-los é o que
impede de chamar tudo de "recuperação ruim". Como cada um se detecta (que evidência):

- **(a)** ausência de disparo de busca no log pra aquela ordem.
- **(b)** ausência de disparo **e** o insumo injetado (chapéu/conceito canônico) cobria o tema.
- **(c)** a query emitida vs. o que o prompt pedia.
- **(d)** gold com **alvo conhecido** (sabe-se que o acervo tem) e a busca não trouxe — recall.
- **(e)** resposta final vs. contexto recuperado (citou? usou?).
- **(f)** julgamento humano.

Cada modo exige uma **evidência diferente** (log de disparo, a query, alvo conhecido,
resposta-vs-contexto, olho do dono) — não se mede os seis com um runner de recall só. Foi por
isso que o gold anterior era lixo: media (d) e chamava de "a recuperação".

> Ressalva registrada pelo dono: minha primeira leitura enquadrou os seis por "de quem é a
> culpa". O objetivo não é atribuir culpa, é detectar. Fica como divergência de partida.

## Proposta de gold set (o que o material existente dá)

Montado de: ordens reais (typed/synapse), buscas reais (ops), T2/T3 do gabarito, 5 ordens-consulta.
Sem fabricar pergunta (buscas e ordens são reais e citam origem).

| modo | perguntas | cobertura |
|---|---|---|
| a | 9 | déficit |
| b | 0 | déficit |
| c | 8 | déficit |
| d | 20 | ok (T2 com alvo) |
| e | 20 | ok (conceito com obra) |
| f | 20 | ok (T3 multistep) |

**Por que a/b/c ficam em déficit — e não é preguiça, é estrutura:**

- **a/b não se separam pela pergunta.** As ordens reais dizem "faz o cron", "roda o reasoner" —
  nunca citam o conceito canônico. O que separa (a) de (b) é **instrumentação de contexto**
  (o conceito estava no frontload da sessão?), não o texto. → a e b compartilham o mesmo
  conjunto de perguntas-ordem; o discriminador é medição, não curadoria de texto.
- **Ordens reais fora de mensageria são escassas** (fila/caixa o dono já disse não avaliar).
- **c depende do par (prompt → query emitida)**, que não está no material — precisa ser colhido
  do log de disparo com a query real.

**Recomendação de dados:** d/e/f podem rodar já. a/b/c exigem **coleta dirigida** — ordens reais
com contexto de sessão (para a/b) e pares prompt→query do log (para c) — não dá pra tirar 20
limpos do legado. Fabricar para "encher 20" reintroduz o lixo que esta minuta existe para matar.

## Para as cadeiras decidirem

1. a/b viram **um** grupo de perguntas com dois testes (disparo; disparo+insumo-cobria), ou ficam
   separados exigindo coleta com contexto?
2. quem produz o log de disparo + query real (o `ordem_id` do refino em curso) — IA/harness?
3. o alvo de (d) precisa de validação humana do dono (recall só vale com alvo real).

## Posição de IA (Elias Elefante) — sign-off: APROVADO (ressalva de mecanismo, não bloqueante)

Chapéu: engenharia-de-harness. Aprovo a estrutura: os seis modos exigem seis evidências
distintas, e d/e/f rodam já enquanto a/b/c pedem coleta dirigida. A ressalva é o mecanismo
que produz a evidência de a/b/c — matéria minha (contrato de tool, loop), e hoje ele não existe.

### Diagnóstico — o presente medido
- **A1** Não há log de disparo estruturado hoje. `motor <inst> buscar` é o verbo de busca e
  não emite registro próprio: grep em `bin/motor` por `ordem_id|var/log/ops|rag_disparo` = 0.
- **A2** O que existe: (i) a ORDEM, gravada por `monta_sessao` — evento `sessao_aberta`
  (campos `sessao`, `ordem_id`, `pergunta_bytes`); já é IA/harness. (ii) a QUERY, só incidental
  no campo `comando` do audit de `run_command` quando a busca passa pela shell — string opaca,
  não registro `{ordem_id, query, k, n_hits}`.
- **A3** Log de hoje (`var/log/ops/ops-2026-08-27.jsonl`) tem dois tipos de evento: `http_req`
  e `sessao_aberta`. Nenhum evento de busca. A não-chamada (a/b) só é inferível por AUSÊNCIA de
  linha — frágil, e só vale se todo caminho de busca passou por `run_command`.

### Proposta — o que fazer
- **B1** (sustenta A1/A3) Instrumentar o próprio `motor <inst> buscar` a emitir evento
  `rag_disparo` em `var/log/ops`, no choke point — não parsear `comando`. Campos:
  `{evento:"rag_disparo", ts, sessao, ordem_id, cadeira, chapeu, query, k, conceito, n_hits, dur_ms}`.
  `sessao`/`ordem_id` do env, como `monta_sessao` já faz. Meu, reversível, cabe no turno de execução.
- **B2** (mede a não-chamada) O que separa "chamou" de "não chamou" é JOIN: para cada
  `sessao_aberta` (ordem_id+pergunta) da fita, houve ≥1 `rag_disparo` com o mesmo `sessao`?
  Zero → candidato (a)/(b). B1 + o `sessao_aberta` que já existe fecham o par sem coleta nova.
  (c) sai do próprio `rag_disparo`: prompt (da ordem) × query emitida.
- **B3** (discriminador a↔b) Separar (a) de (b) NÃO sai do disparo: exige saber se o frontload
  da sessão cobria o tema (conceito/chapéu injetado). É instrumentação de CONTEXTO (peças
  servidas na abertura daquele `sessao` × tópico) — segundo chapéu dentro de IA. Sinalizo o
  cruzamento; não fecho sob engenharia-de-harness. Casa com a leitura da Olga ("o que separa
  (a) de (b) é instrumentação de contexto").

### Respostas às perguntas da minuta
- **Q2 (quem produz o log de disparo + query real — IA/harness?)** SIM, IA/harness. A ordem já
  é minha (`monta_sessao`); o disparo+query eu construo (B1), formato acima.
- **Q1 (a/b um grupo ou separados?)** UM conjunto de perguntas-ordem, DOIS testes (disparo
  presente; disparo ausente + frontload cobria). O discriminador é medição (B1+B3), não
  curadoria — é o que resolve o "b=0": não faltam 20 perguntas de b, falta a instrumentação.
- **Q3 (validação humana do alvo de d)** Matéria de dados/dono, não minha. Concordo: recall só
  vale com alvo real.

### O que não sei
- **C1** Se `motor buscar` na fita/claude.ai SEMPRE passa por `run_command` (verbo shell) ou se
  há porta que chama o motor sem logar. Havendo, B1 instrumenta DENTRO do motor (Python), não no
  verbo — cobre as duas superfícies. Confirmo no dispatch de `bin/motor` antes de implementar.
