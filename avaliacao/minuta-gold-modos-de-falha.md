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
