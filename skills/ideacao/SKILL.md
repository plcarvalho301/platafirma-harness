---
name: ideacao
description: Use quando o dono disser idear, ideação, brainstorm ou abre o leque, ou pedir ideias novas para um alvo antes de existir solução escolhida; e quando ele trouxer o link de um painel e disser colabora neste painel. Conduz a sessão em sete passos: alvo, ideias do dono, busca na casa, primeira rodada, busca de análogos, segunda rodada e fecho com três finalistas. NÃO dispare para estudo do que já existe, para parecer sobre solução escrita, nem para escolher entre opções já postas.
---

# Ideação

A sessão abre um leque de ideias para um alvo do dono e fecha com três finalistas, cada
uma com a condição que precisa ser verdade e o teste mais barato que a derrubaria. Roda
com uma cadeira. Outra cadeira entra quando o dono leva o link do painel à fita dela.

Antes do passo 1, abra o arquivo da sua cadeira em `lentes/`: produto, arquiteto ou
gestão estratégica. Ele diz o tipo de alvo, a ficha da ideia, as lentes e onde você
busca. O painel é opcional: a seção «Onde a sessão fica registrada» diz o que a sessão registra e como fazê-lo sem painel.

## Onde a sessão fica registrada

A sessão precisa de um registro, e o meio é o que o ambiente tem:

- com artefato publicável (claude.ai), o registro é um painel publicado, que o dono e as
  outras cadeiras abrem pelo link;
- sem artefato (outro provedor, API, terminal), o registro é o próprio texto da
  conversa, ou um arquivo de texto quando o ambiente grava arquivos, com as mesmas
  partes na mesma ordem.

O painel é opcional, e nada na sessão depende dele além do que o registro já traz. As
partes, em ordem: a contagem do topo (ideias por rodada, ideias da convidada que
repetem as já postas, buscas feitas); o alvo devolvido em pergunta; o que fica fora; o
registro de busca; as ideias da primeira rodada, com a ficha; os achados de análogos,
um por linha; a segunda rodada; e, no fecho, os grupos, as descartadas com o motivo e
as três finalistas, cada uma com a condição e o teste.

Sem painel, o dono não escreve ao lado: a ordem do passo 2 se inverte para proteger o
que ela protege. Você gera a primeira rodada primeiro e só então lê as ideias que o
dono manda numa mensagem.

## O que vale enquanto a sessão dura

A sessão começa quando o dono diz «idear», «ideação», «brainstorm» ou «abre o leque», ou
quando chega com o link de um painel e «colabora neste painel». Termina quando ele diz
«fecha» ou quando o painel sai com as finalistas.

Enquanto ela dura, três regras da conduta afrouxam, e só elas:

- a ideia não precisa de fonte; vai marcada como ideia, nunca como fato, e quando tem
  fonte a fonte vai junto; o achado de busca sempre leva a fonte;
- a lista é a forma da resposta;
- o turno pode terminar em escolha, porque escolher as finalistas é o ato do dono.

O resto da conduta segue valendo. A cadeira não executa ideia, não abre card e não sai
do alvo. Na geração ninguém julga: a ideia serve de degrau para a próxima, e a objeção
que aparece se reescreve como condição («isto exige que…») e espera o fecho.

Sem a palavra do ritual, «alternativas» e «me ajuda a pensar» são estudo, e esta skill
não roda. Quando o dono chega com uma solução única para um alvo novo, a cadeira faz o
que ele pediu e oferece a sessão em uma linha no fim, sem abri-la sozinha.

## Os sete passos

1. **Alvo.** O dono escreve o alvo num parágrafo: quem tenta o quê, o que quebra hoje e
   o que ele já sabe que não quer. Abra o registro da sessão, com o alvo devolvido
   numa pergunta («como X poderia Y?») e a lista do que fica fora. Se o alvo é tema
   («melhorar o RH»), devolva-o ao dono antes de qualquer ideia, porque tema não tem
   onde quebrar.
2. **O dono escreve.** Enquanto você faz o passo 3, o dono anota as ideias dele direto
   no registro (no painel, ou numa mensagem quando não há painel) e, quando termina, diz «vai». Não leia essas ideias antes da segunda
   rodada: ideia lida antes de gerar se repete na lista.
3. **Busca na casa.** No mesmo turno em que abre o registro, procure o que a casa já
   decidiu ou já tem sobre o alvo, pelos lugares do seu arquivo de lentes. O que achar
   vira restrição ou entra no que fica fora, e não vira ideia.
4. **Primeira rodada.** Com o «vai», gere dez ideias na sua matéria, nesta conversa, em
   três tempos, e escreva no registro só no fim do terceiro:
   1. liste os dez títulos;
   2. releia a lista, troque os que se parecem e empurre os tímidos;
   3. escreva a ficha de cada ideia pelo seu arquivo de lentes.

   Use pelo menos três lentes. Não reescreva a lista para deixá-la «mais ousada» em
   rodadas seguidas: o modelo converge para os mesmos enfeites.
5. **Busca de análogos.** Procure quem já resolveu problema parecido, primeiro na
   biblioteca e depois na web, pela regra de busca abaixo. Cada achado entra no registro
   em uma linha: quem resolve, como, e a fonte.
6. **Segunda rodada.** Leia os achados e as ideias do dono e gere pelo menos seis ideias
   que não existiam antes, com lentes que a primeira rodada não usou. Pode construir em
   cima de um achado ou de uma ideia do dono, ou cruzar dois; a ideia nova aponta de
   onde nasceu.
7. **Fecho.** Agrupe as ideias por semelhança e separe as descartadas, cada uma com o
   motivo: não responde ao alvo, ou bate numa decisão da casa que o dono não quer
   reabrir. Leve os grupos ao dono, que escolhe três finalistas que não se pareçam
   entre si. Para cada finalista, escreva a condição que precisa ser verdade e o teste
   mais barato que a derrubaria.

A sessão acaba com o registro completo e a contagem do topo preenchida. O registro é
insumo: quando o alvo já tem card, ele entra no card como comentário de insumo; quando
não tem, criar o card é ato do dono.

## A regra de busca

A busca tem dois momentos: na casa, no passo 3, e de análogos, no passo 5. Nenhuma busca
entra no meio de uma rodada.

Cada busca abre mais que a anterior. São cinco movimentos, do mais perto ao mais longe:

1. **Perto.** As palavras do alvo, como o dono escreveu.
2. **Lente.** O alvo reescrito por uma das suas lentes.
3. **Aresta.** A busca devolve o conceito que reconheceu na pergunta. Liste as ligações
   dele com `acervo listar biblioteca relacao <conceito>` e busque pelo vizinho, com o
   filtro de conceito.
4. **Termo colhido.** Um termo que apareceu num achado anterior e que o alvo não usava,
   como o nome que o mercado dá ao problema.
5. **Salto.** A função do alvo dita sem as palavras do ramo. «Ver o que falta contra o
   que se declarou precisar» também descreve estoque, escala de plantão e orçamento.

Suba um movimento quando a busca volta vazia ou repete o que já tinha. Fique no mesmo
quando ele ainda traz coisa nova.

Pare por teto ou por saturação, o que vier primeiro:

- **Na casa:** até três buscas, pelas palavras do alvo, pelo nome da peça que ele toca e
  pelo que já foi descartado. Pare quando achar o documento que decide sobre o alvo, ou
  em duas buscas vazias seguidas.
- **Na biblioteca:** até quatro buscas, na ordem perto, lente, aresta e salto. Pare com
  três análogos de obras diferentes, ou em duas buscas seguidas sem obra nova.
- **Na web:** até quatro consultas, só depois da biblioteca, começando pelo termo
  colhido e terminando no salto. Pare com três soluções de ramos diferentes. Vale a
  página lida; resumo de buscador não conta como achado.

O teto da sessão é de onze buscas por cadeira.

Toda busca vai ao registro de busca da sessão, a vazia também, numa linha: a consulta, o
lugar, o movimento, a cobertura que a busca devolveu, quantos achados entraram no painel
e que ideias os usaram. O registro serve de caso de teste quando a busca da casa for
refeita, e por isso a linha vazia vale tanto quanto a cheia.

## Quando você é a convidada

O dono abriu a sua fita, trouxe o link de um painel de outra cadeira e escreveu
«colabora neste painel». Siga quatro passos. Sem painel, o dono cola o texto do registro da outra cadeira, e o resto vale igual:

1. Leia do painel só o alvo e o que fica fora. As ideias ficam sem ler.
2. Faça a sua busca na casa e gere as suas dez ideias da primeira rodada, na sua
   matéria, nos três tempos do passo 4.
3. Só então leia o painel inteiro e responda às ideias que encontrou de três jeitos, e
   só desses:
   - construa em cima («sim, e…»);
   - cruze duas ideias de cadeiras diferentes;
   - escreva a condição na sua matéria («isto exige que…»).
4. Gere pelo menos quatro ideias que não existiam antes da leitura e publique tudo no
   painel, com a sua marca, os cruzamentos na parte própria.

A ordem dos dois primeiros passos é o que dá valor à convidada: quem lê as ideias antes
de gerar repete o que leu. A crítica e o descarte esperam o fecho, que é da cadeira que
abriu a sessão. Some à contagem do topo quantas ideias suas repetem as que já estavam
no painel.

## Quando você abriu e outra cadeira entrou

- Se o dono disser «lê o painel», responda às ideias da convidada pelos mesmos três
  jeitos e gere de novo se algo novo aparecer.
- No fecho, releia o painel inteiro antes de agrupar. Na finalista que depende da
  matéria de outra cadeira, marque de quem é a condição que falta.
