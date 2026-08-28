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


## Sign-off de gestão-estratégica (Carla Cangurina, chapéu rh) — APROVADO, condicionado

Aprovo a estrutura. Condição de cobertura, não de prioridade: **a/b andam como UM grupo** até
abrir o discriminador a↔b — o "segundo chapéu dentro de IA" que o próprio Elias nomeia em B3 e
não fecha. Sem esse chapéu, (a) e (b) não se separam por curadoria nenhuma; é pré-condição de
papel, não de texto. Responde a Q1 da minuta.

Raiz, para a instrumentação não medir sintoma: a/b/c não são "cadeira preguiçosa" — são a saída
previsível de dois portões em série na montagem/resposta (rótulo canônico ausente no prompt =
Portão 1 não abre o chapéu certo; gate de recuperação escrito como enunciado, ou enterrado no
meio da janela = Portão 2 não dispara). B1/B2 (Elias) capturam o disparo; para separar causa de
sintoma, o log precisa registrar também **se o pacote servido tinha o handle** e **onde o gate
caiu na janela** daquela sessão — sem isso o eval mede o efeito e perde a causa.

Sequenciamento d/e/f-já vs. a/b/c: matéria de portfólio, fora deste chapéu. A ordem não é livre
de qualquer forma — d/e/f estão prontos por cobertura completa; a/b/c esperam o 2º chapéu de IA.

Régua de redação derivada (peso dos elementos de persona/prompt na decisão de buscar), publicada
como referência de domínio, não amarrada a esta minuta: wiki `Abertura de sessão/Redação da
montagem` (pageid 665, http://localhost:8080/index.php/Abertura_de_sessão/Redação_da_montagem).
Achado lateral rastreado em card próprio: #2905 (viés da 1ª linha "HEAD DE ..." das personas desta
casa — atribuição de persona em 3ª pessoa medida como supressor de recuperação, correção fora do
escopo desta minuta).

Sign-off formal também registrado via `tarefas assinar 2904` (aprovado, mesmo motivo, resumido).


## Sign-off de produto (Lygia Bem-te-vi, chapéu discovery) — APROVADO, com três condições de instrumento

Aprovo a estrutura: seis modos, seis evidências distintas, d/f rodam já. As condições são de
validade de instrumento — o que cada conjunto de perguntas de fato mede — lidas com a régua de
entrevista: pergunta boa aqui reproduz a ordem real (comportamento); pergunta escrita para
acertar o alvo mede outra coisa.

### Respostas às perguntas da minuta

- **Q1 (a/b):** UM grupo, dois testes — concordo com IA e gestão. Condição: o discriminador
  "insumo cobria" não sai só de medição. B3 diz o que foi SERVIDO; dizer que o servido COBRIA
  o tema da ordem exige anotação por item (campo `insumo_aplicavel`: conceito/peça que cobria,
  ou vazio explícito). O gold hoje não tem esse campo (todos os a-* com alvo nulo) — sem ele o
  teste de (a) marca como falha toda ordem sem disparo, inclusive as em que o acervo não tinha
  nada a dizer, e o detector afoga em falso positivo.
- **Q-produto (falta cenário?):** falta UM com evidência mecânica própria: **recuperou
  plausível-mas-errado e USOU** — busca razoável, hit errado, resposta ancorada no ruído. Não é
  c (a query estava certa), não é d (recall), não é e (o contexto FOI usado). Hoje cai no
  catch-all de f, mas é detectável por máquina (afirmação da resposta × sustentação no trecho
  citado), e o princípio desta minuta é: evidência distinta = modo distinto. Proponho (g), no
  mesmo runner de e.
- Sobre-uso (disparo em ordem que não pedia acervo) também é falha de uso para quem consome a
  resposta — latência e poluição de janela — mas não bloqueia a minuta; fica registrado para a
  fila de instrumentação.

### Análise de instrumento por modo (endereça o modo? é prompt que humano escreveria?)

- **a (9):** os melhores itens do conjunto — ordens literais do dono, com typo e tudo.
  Naturalidade máxima; evidência de comportamento, não de opinião. Ressalvas: (1) sem
  `insumo_aplicavel`, ver Q1; (2) a-06/a-07 são turnos do MEIO de conversa ("deleta as linhas
  da aba") — em replay avulso perdem o contexto que os tornava inteligíveis; marcar quais itens
  são auto-contidos.
- **c (8):** como está, NÃO roda — e a própria minuta diz por quê: c se detecta pelo par
  prompt→query, e os 8 itens têm só a query. "governança de dados" no campo `pergunta` é a
  evidência-metade rotulada como pergunta. Reclassificar como SEMENTE (a origem file:line
  permite reconstruir o par via join de `ordem_id` quando B1 existir), não como gold executável.
- **d (20):** endereça recall com alvo conhecido; cobertura ok. Ressalva de sensibilidade:
  parte dos itens carrega no enunciado o vocabulário do alvo ("BT/NT/RT, notas de escopo") — a
  pergunta entrega os termos de indexação e o recall medido vira sobreposição de string. O
  registro é o oposto da ordem real (compare com os a-*: curto, torto, contextual). Serve para
  recall; não prediz recuperação sob prompt humano — ler os dois números separados.
- **e (18 ops + 2 T2):** elo certo (resposta × contexto), insumo errado. 18 itens são strings
  de busca, não tarefas: "quality documentation teams more likely…" não tem resposta certa
  definível, e prompt-sopa-de-palavras dá ao modelo NADA além do contexto — o caso em que
  ignorar contexto é MENOS provável. O modo e existe para pegar o modelo preferindo treino a
  contexto, e isso acontece na pergunta rica que o treino sabe responder: sensibilidade baixa
  por construção. Condição: re-parear os itens ops com a ordem que os gerou (mesma coleta de c)
  ou migrar o conjunto para o registro de e-06/e-07/e-19/e-20 (pergunta respondível).
- **f (20):** endereça — cenário situado com aposta em jogo ("você assina?") é a técnica certa
  para julgamento humano; vinheta, não entrevista, e aqui é o instrumento adequado. Ninguém
  escreve (a)(b)(c)(d) num pedido real: o scaffolding serve à comparabilidade do juiz e afasta
  do prompt humano — aceitável em f, não exportar o formato para os outros modos.
- **Cobertura de cadeira:** zero itens do domínio de produto (discovery/design/canais) em
  d/e/f. Se o gold detecta falha "das cadeiras", as minhas não aparecem no espelho. Ofereço
  coleta T2/T3 do meu domínio como sequência, sem travar esta minuta.

Sign-off formal também registrado via `tarefas assinar 2904` (aprovado, condições resumidas).

### Refino — piso de cobertura por cadeira (ordem do dono, 27/08)

Condição de cobertura, não de significância (20/degrau não sustenta taxa por cadeira — ver
análise acima). Objetivo: nenhuma cadeira invisível no espelho.

1. **Piso: ≥1 item por cadeira em cada modo coletável (d, e, f).** Frame = 8 cadeiras de
   abertura (arquiteto, dados, fábrica, gestão-estratégica, ia, produto, segurança, ti).
2. **a/b/c ficam com a cobertura do material real** — são ordens e queries reais; NÃO se
   fabrica item para bater piso (reintroduz o lixo). Gap de cadeira em a/b/c fecha pela coleta
   dirigida já roteada, não por curadoria de texto.
3. **Custo: ~14 itens autorados** para zerar os buracos, dentro dos 60 slots de d/e/f,
   deslocando o excesso de TI (16 hoje). Buracos atuais: fábrica/produto/segurança (faltam os
   três modos); arquiteto/ia (falta d); dados/gestão/ti (falta e autorado — o e de hoje é
   query de log sem cadeira, casa com a condição de re-parear e).

Produto autora o próprio recorte (d/e/f de produto — matéria minha). O restante é insumo de
cada cadeira / coleta dirigida; produto não escreve parecer de matéria alheia.
