# b2 — propostas de conceito · capacidade-estatal

Domínio `capacidade-estatal`. Propõe: `claudinho-politicas-publicas`. Slug e
inclusão decididos pelo dono.

Formato conforme `distribuicao/rodada-2/PROMPT-rodada-2.md` (passo 6); definição
conforme `distribuicao/rodada-2/PROMPT-reescrita-slug-definicao.md`.

## Lote

54 obras com `dominio_atual = capacidade-estatal` em
`distribuicao/rodada-1/obras.csv`. O domínio não foi reivindicado na rodada 1:
nenhuma obra do lote aparece em `reivindicacoes/` ou em `conflitos.csv`. Sem
derrota de arbitragem, logo sem réplica.

| bloco | obras | uso |
|---|---|---|
| estudos de caso de sistemas da APF | 10 | lastro principal — lidos na wiki |
| manuais operacionais SIAPE / eSocial / SIASS | 10 | lastro de modelo publicado |
| compliance e controle interno (COSO, ISO 31000) | 9 | provável colisão externa |
| normativos (LAI, 8.112, 8.159, 14.063, INs) | 8 | lastro de forma normativa |
| teoria (APW, Cohen & Levinthal, Scott, Coase, Walsh & Ungson) | 6 | lastro de mecanismo |
| demais | 11 | a triar |

### Instrumento de leitura dos estudos de caso

Os 10 `Estudo de caso: <sistema>` não estão no índice vetorial: três consultas
em ângulos distintos não retornaram nenhum deles. Eles moram na wiki, em
`Frente:paper-capability-trap/case-<sistema>`, e são lidos por `get_page`. As
âncoras marcadas **[wiki]** abaixo foram lidas ali, não no RAG.

A frente tem 14 páginas — as 10 catalogadas mais `case-petrvs`,
`case-reforma-administrativa`, `case-sei` e `referencias`, que não constam de
`obras.csv`.

## Conceitos

`outros-rotulos` corresponde a `acervo.conceito.outros_rotulos` (`text[]`), que
existe no schema e não no template da rodada. Carrega o slug anterior e o termo
estrangeiro, para que a troca de rótulo não perca a busca.


### armadilha-de-capacidade

```
rotulo: Armadilha de capacidade
natureza: fenomeno
estatuto: doutrinario
```

**definição.** Um órgão só consegue comprar bem aquilo que já saberia fazer.
Para contratar um sistema, julgar a proposta e cobrar o resultado é preciso
entender do assunto — e é justamente esse entendimento que falta em quem
terceirizou tudo. A saída aparente é contratar mais, e cada contrato afasta o
dia em que o órgão saberia fazer.

O que fecha a armadilha é a competência ausente ser a mesma nos dois lados:
quem não sabe especificar também não sabe reconhecer que especificou mal, então
o órgão não percebe o que está perdendo. Sai-se dela trazendo para dentro quem
já tem a competência, nunca comprando a solução.

- obras-âncora: `84ee87ce-3cb8-4807-8c6e-33171aa8ed6e` (Building State
  Capability), `aa5d0cda-3a60-4f2c-b28f-0a17f2d450c7` (Fichamento: Andrews,
  Pritchett & Woolcock)
- caso falseador: um órgão sem competência técnica interna que, de tanto
  contratar, passe a especificar e avaliar bem — a competência entraria pela
  compra e não haveria fecho.
- pai proposto: —
- substitui: `armadilha-de-capacidade` (base)

Filhos que já declaram este pai na base e continuam válidos sob a régua nova:
`carga-prematura`, `retencao-estrutural`, `titularidade-do-core`.

### titularidade-do-core

```
rotulo: Titularidade do core
natureza: modelo
estatuto: doutrinario
```

**definição.** Todo órgão faz uma coisa que mais ninguém faz — reconhecer um
vínculo de trabalho, lançar um tributo, liquidar um pagamento — e faz muita
coisa que todo mundo faz: folha, protocolo, login. A titularidade do core é a
decisão de qual dessas partes o órgão continua entendendo por dentro, mesmo
quando outro a executa.

Delegar a execução do que é comum não custa nada. O que quebra é entregar a
parte exclusiva sob contrato de escopo fechado: as regras dela ninguém de fora
conhece de antemão, elas se descobrem enquanto o sistema é construído, e quem
descobre é quem fica sabendo. No Pix a separação está de pé — o Banco Central
opera ele mesmo o diretório de chaves e a liquidação, e terceiriza transporte e
execução periférica.

- obras-âncora: `0d146df8-af09-4c5b-8c41-f983b481b407` (Manual do eSocial),
  `2b4a31fd-447a-4a32-a417-33c3ce00cdb4` (Manual de Padrões para Iniciação do
  Pix v2.6.2), `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: um órgão que entregue a regra exclusiva sob escopo fechado e,
  encerrado o contrato, saiba especificar e evoluir essa regra tão bem quanto
  quem a construiu.
- pai proposto: `armadilha-de-capacidade`
- substitui: `titularidade-do-core` (base)

### legibilidade-do-sistema

```
rotulo: Legibilidade do sistema
natureza: disposicao
estatuto: doutrinario
```

**definição.** Documentar tudo não é o mesmo que deixar navegável. Um sistema é
legível quando a própria superfície mostra onde uma parte termina e a outra
começa: qual porta dá no mesmo dado que qual outra, o que é tela e o que é base
por baixo. Sem isso, a resposta está lá e ninguém acha — e quem procura conclui
que o problema é ele.

Quem consome um sistema ilegível não extrai o modelo dele por mais que leia.
SIAPE, Sigepe e SouGov são três nomes de camadas de acesso sobre a mesma base
de dados, e nem servidor nem integrador consegue dizer com segurança se são um
ou três: a informação existe e está escrita, o que falta é a superfície
sinalizar a fronteira.

- obras-âncora: `60b18ee3-b1e9-400f-8119-98dbe14560b4` (Estudo de caso: SIGEPE)
  **[wiki]**, `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: consumidores que reconstroem o modelo de um sistema cuja
  superfície não sinaliza fronteira nenhuma, na mesma taxa e no mesmo tempo em
  que reconstroem o de um sistema que sinaliza.
- pai proposto: —
- substitui: `legibilidade-do-sistema` (base)

### carga-prematura

```
rotulo: Carga prematura
natureza: fenomeno
estatuto: doutrinario
```

**definição.** A obrigação chega antes do meio de cumpri-la. Liga-se o prazo, a
sanção ou a escala enquanto o instrumento que tornaria o cumprimento possível
ainda está sendo inventado — e quem tem que cumprir descobre isso sozinho. O
estrago não é só a regra descumprida: a estrutura que já funcionava é posta a
carregar peso que não aguenta, e cede.

O sinal costuma estar legível no próprio papel, num instante só: a norma que
obriga e, no mesmo texto, remete a ato futuro o que faria a obrigação
funcionar. Na Rede Nacional de Dados em Saúde o envio virou obrigatório antes
de existir a regulamentação da consequência do descumprimento, e o modelo de
dados seguia sendo corrigido a partir dos erros que apareciam em produção.

- obras-âncora: `84ee87ce-3cb8-4807-8c6e-33171aa8ed6e` (Building State
  Capability), `c66f85c1-d731-4c61-b17b-0f3bf590563e` (Estudo de caso: RNDS)
  **[wiki]**
- caso falseador: uma obrigação ligada antes do instrumento cujo cumprimento se
  dê na mesma taxa e no mesmo prazo que o de obrigação ligada depois — a
  antecipação não faria diferença.
- pai proposto: `armadilha-de-capacidade`
- substitui: `carga-prematura` (base)

### responsabilidade-de-traduzir

```
rotulo: Responsabilidade de traduzir
natureza: modelo
estatuto: doutrinario
```

**definição.** Quando dois sistemas com vocabulários diferentes precisam
conversar, alguém tem que traduzir — e o que decide o resultado é de quem é
esse trabalho. No destino, um time só o faz uma vez, confere o que entra e
devolve erro dizendo o que faltou. Na origem, cada um dos muitos remetentes
traduz por conta própria, e o mais fraco deles define a qualidade do conjunto.

Não se trata de culpa, e sim de onde o trabalho fica — e ele quase sempre é
atribuído por omissão: o centro publica o vocabulário canônico, obriga seu uso
e não diz quem converte. Na Rede Nacional de Dados em Saúde a integração ficou
escrita como responsabilidade do gestor de cada ente, e o indicador da falha se
chama taxa de rejeição, nome que localiza o erro em quem enviou. No Pix e no
login gov.br o trabalho está do outro lado: o centro recebe, confere e responde
com erro nomeado.

- obras-âncora: `c66f85c1-d731-4c61-b17b-0f3bf590563e` (Estudo de caso: RNDS)
  **[wiki]**, `49b89d8c-a8d0-478b-b803-b3819aad0ed1` (Estudo de caso: gov.br)
  **[wiki]**, `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: um arranjo em que cada remetente traduz por conta própria e a
  qualidade do dado recebido seja igual à de um arranjo em que o destino traduz
  e valida.
- outros-rótulos: `direcao-da-autoridade-semantica`, `lado-da-traducao`
- pai proposto: —
- substitui: `direcao-da-autoridade-semantica` (base)

Slug proposto no lugar do da base: o rótulo antigo não diz de que trata e o
novato não o chuta. A entrada é linkada na wiki sob
`Ontologias/`, e a fronteira com `estudos-ontologias` também é dele.

### exigencia-sem-instrumento

```
rotulo: Exigência sem instrumento
natureza: fenomeno
estatuto: doutrinario
```

**definição.** Mandar alguém entregar num formato exige entregar também a
ferramenta que produz aquele formato — e é essa segunda metade que costuma
faltar. Sem ela, a norma diz "valide antes de enviar" para quem não tem como
validar, e o trabalho simplesmente não acontece.

A diferença é visível em dois sistemas do mesmo Estado. Na escrituração fiscal
digital, a Receita distribui de graça um programa que confere o arquivo do
contribuinte antes do envio: a régua vai junto com a obrigação, executável. Na
Rede Nacional de Dados em Saúde, a orientação é conferir a conformidade ao
modelo antes de enviar, sem que exista programa equivalente — e no Cadastro
Ambiental Rural o ajuste fino do polígono volta para um agricultor que não tem
como fazê-lo. Entregar o dicionário executável eleva o piso de quem está na
ponta; entregar só a exigência o rebaixa.

- obras-âncora: `cb45fef0-4e88-4abb-8f17-e8f8648d5afc` (Estudo de caso: SPED)
  **[wiki]**, `c66f85c1-d731-4c61-b17b-0f3bf590563e` (Estudo de caso: RNDS)
  **[wiki]**, `f051def6-1fd0-4c2b-8246-0d669ae66e2e` (Estudo de caso: CAR/SICAR)
  **[wiki]**
- caso falseador: pontas de baixa capacidade entregando com a mesma qualidade
  quando recebem só a norma e quando recebem norma mais ferramenta — o
  instrumento não faria trabalho.
- pai proposto: `responsabilidade-de-traduzir`
- substitui: —

### autenticidade-vs-veracidade

```
rotulo: Autenticidade vs. veracidade
natureza: fenomeno
estatuto: doutrinario
```

**definição.** Uma garantia pode cobrir duas coisas muito diferentes: que o
objeto é mesmo o que foi selado e veio de quem diz ter vindo, ou que o que ele
afirma está certo. Quase todo mecanismo de confiança entrega a primeira, e é
lido como se entregasse a segunda.

Na urna eletrônica, conferir o resumo digital prova que o programa em execução
é o que foi lacrado na cerimônia pública — não prova que o programa lacrado faz
o que diz fazer. Na nota fiscal eletrônica, a autorização de uso devolvida pela
Secretaria da Fazenda confere assinatura, leiaute e numeração; o mérito do que
está declarado continua sendo responsabilidade de quem emitiu. Confundir as
duas é atribuir ao selo uma garantia que ninguém deu.

- obras-âncora: `700724ce-589a-430f-8800-31dab21b3cbb` (Estudo de caso: Urna)
  **[wiki]**, `cb45fef0-4e88-4abb-8f17-e8f8648d5afc` (Estudo de caso: SPED)
  **[wiki]**
- caso falseador: um mecanismo de atestação cuja verificação de origem implique,
  por construção, a correção do conteúdo atestado.
- outros-rótulos: `procedencia-vs-corretude`, `garantia-de-origem`
- pai proposto: —
- substitui: `procedencia-vs-corretude` (base)



### cegueira-relacional

```
rotulo: Cegueira relacional
natureza: fenomeno
estatuto: doutrinario
```

**definição.** A ferramenta deixa a pessoa produzir um registro perfeitamente
válido sozinho, sem nunca mostrar o que já está registrado e vai colidir com
ele. Cada um acerta a sua parte e o conjunto sai errado — e o erro só aparece
muito depois, na conferência.

No Cadastro Ambiental Rural o programa oficial baixa a foto aérea e deixa o
técnico desenhar o limite da propriedade orientado pelo terreno, sem trazer os
limites dos vizinhos já cadastrados. O polígono fica fechado e válido, e invade
o do lado. Não é fraude nem incompetência de quem desenha: é desenhar limite de
vizinhança no escuro, porque a ferramenta foi construída sem enxergar o
vizinho.

- obras-âncora: `f051def6-1fd0-4c2b-8246-0d669ae66e2e` (Estudo de caso:
  CAR/SICAR) **[wiki]**, `d17c8ab4-a0e2-4e3e-ac6c-6494f33895c3` (Estudo de caso:
  CadÚnico) **[wiki]**
- caso falseador: uma ferramenta que não expõe o estado já registrado e cujos
  artefatos colidem entre si na mesma taxa de uma que o expõe no momento da
  produção.
- pai proposto: —
- substitui: `cegueira-relacional` (base)

## Réguas reescritas — conceitos que já existiam no domínio

Definição apenas. Natureza, estatuto, âncoras e falseador dessas entradas não
são tocados aqui.

### plano-de-gabinete
Substitui o slug `alto-modernismo`. Outros rótulos: `alto-modernismo`,
`high modernism`.

A crença de que um plano bem desenhado no gabinete vale mais que o jeito que as
pessoas já achavam de fazer no lugar — e que, por isso, dá para reorganizar
cidade, lavoura ou repartição segundo o desenho, ignorando o que estava lá. Não
é a técnica que define, é a fé de que a técnica basta. O sinal é a solução que
chega pronta, idêntica para contextos diferentes, com o saber local tratado
como atraso a corrigir.

### capacidade-absortiva
Uma organização só enxerga o que já tem repertório para enxergar. Conhecimento
novo que chega — um relatório, uma tecnologia, um modelo publicado — não é
rejeitado por quem não tem base para entendê-lo: passa despercebido, como
ruído. Por isso aprender coisa nova depende de já saber coisa próxima, e quem
parou de acuminar repertório perde primeiro a capacidade de notar que está
perdendo alguma coisa.

### retencao-estrutural
O conhecimento caro pode ficar em dois lugares: na cabeça de quem o produziu ou
inscrito em algo que outra pessoa consegue consultar sozinha — um modelo
publicado, um contrato de interface, uma ferramenta distribuída. Quando fica
inscrito, quem chega depois não precisa reconstruí-lo do zero nem achar quem o
construiu. Reter na estrutura não é o mesmo que ter instituição que sustente: o
artefato pode estar de pé enquanto a equipe que o mantinha se esvazia.

### dependencia-de-fornecedor
Chega um ponto em que trocar de fornecedor custa mais do que aguentar o
fornecedor que se tem, e a partir daí o preço e o prazo deixam de ser
negociados. A dependência não nasce do contrato, e sim do que ficou só do lado
de lá: o formato dos dados, o conhecimento de como o sistema funciona, a
capacidade de operá-lo. Contratar não cria dependência; contratar sem reter
nada, sim.

### soberania-tecnologica
Poder decidir sozinho sobre a tecnologia que sustenta funções públicas — onde o
dado fica, quem opera a infraestrutura, quem pode mudar as regras do sistema —
sem depender da permissão ou da continuidade de um ator que responde a outro
país ou a outro dono. Não é fazer tudo em casa: é ter alternativa real quando o
fornecedor atual sai, sobe o preço ou é impedido de operar.

### adaptacao-iterativa
Um jeito de construir capacidade que começa por um problema que as pessoas ali
sentem de verdade, e avança em ciclos curtos com a solução sendo desenhada por
quem vai conviver com ela. O contrário é chegar com a solução pronta de fora e
pedir que a organização se molde a ela: aí a forma é adotada, ninguém aprendeu
nada, e o problema original continua onde estava.

### avaliacao-politicas-publicas
Perguntar, com método, se uma ação do governo fez o que prometia — e responder
com evidência, não com relatório de atividade. Cobre desde saber se o problema
foi bem identificado até medir o que mudou na vida de quem devia ser atendido,
passando por quanto custou e se a execução aconteceu como desenhada. O que
distingue avaliação de prestação de contas é a pergunta: uma quer saber se
funcionou, a outra se foi executado.

### governanca-federada
Uma regra só, escrita e mantida no centro, com vários entes operando a execução
sob a própria autoridade — e um fórum onde o vocabulário comum é negociado, não
imposto. Quem não tem estrutura para operar recebe do centro a capacidade de
execução emprestada, sem entregar a titularidade. O SPED funciona assim: a
Receita e as secretarias estaduais mantêm o leiaute em colegiado, e a Sefaz
Virtual autoriza documento para o estado que não opera ambiente próprio.

### independencia-gerencial
Slug proposto: `donos-independentes`; outros rótulos: `independencia-gerencial`.

Cada sistema de um conjunto é comprado, financiado e operado por um dono
diferente, e continuaria funcionando se fosse desligado do conjunto. É essa
independência de cada peça que torna o todo interdependente sem ser
hierárquico — e é por isso que a costura entre elas fica órfã quando ninguém é
nomeado para fazê-la: não existe chefe comum a quem endereçar o pedido.

### sistema-de-sistemas
Um conjunto cujas peças têm donos diferentes, evoluem em ritmos próprios e
produzem, juntas, um comportamento que não é de nenhuma delas. Não é a mesma
coisa que sistema distribuído: lá os pedaços estão espalhados e o dono é um só;
aqui os donos são vários, e é essa a fonte da dificuldade. O ecossistema do
Cadastro Único é o exemplo: ministério, empresa pública de tecnologia e banco
operam peças da mesma jornada sem superior comum.

### topologia-de-integracao
O desenho dos caminhos por onde os sistemas se alcançam — todos passando por um
ponto central, cada um falando com cada um, ou algo entre os dois. A escolha
decide três coisas de uma vez: o quanto um depende do outro para funcionar, se
existe um ponto cuja queda derruba tudo, e quanto custa acrescentar mais um
participante depois que já está tudo montado.

### contratos-de-interface
O acordo escrito sobre o que uma fronteira aceita, o que ela devolve quando
recusa e quem paga a conta quando o acordo muda depois de já estar em uso.
Recusar sem dizer o motivo, ou mudar o formato sem avisar, transfere o trabalho
inteiro para o outro lado — que descobre o problema em produção. O diretório de
chaves do Pix é o oposto disso: cada operação tem nome, e o erro volta dizendo
o que faltou.

### consistencia-de-dados
Quando a mesma informação existe em mais de um lugar, alguém tem que decidir o
que fazer no intervalo em que as cópias discordam. A escolha aparece no ritmo
da atualização: por evento, no instante em que o fato acontece, ou por lote, uma
vez por mês. O Cadastro Único mostra o preço do segundo caminho: quando o lote
mensal atrasou, a folha de pagamento foi gerada sobre uma fotografia vencida.

### dado-mestre
A base que diz quem é quem, e serve de referência para os outros sistemas sem
executar nada. O Cadastro Único identifica e caracteriza famílias; não concede
benefício nem paga ninguém — isso acontece depois, em sistema de outro dono, que
consome a base. Confundir os dois é atribuir a um cadastro as decisões que
foram tomadas em outro lugar.

### interoperabilidade
Dois sistemas de donos diferentes trocarem informação e entenderem a mesma coisa
com ela, sem precisar de um acordo novo a cada par que se conecta. A parte
difícil raramente é técnica: é ter um padrão comum, alguém encarregado de
mantê-lo vivo e uma razão para os outros aderirem. Sem essas três, o que se
chama de integração é uma coleção de conexões feitas uma a uma.

### atestacao-confianca
Um componente produz evidência verificável sobre o que está de fato executando,
e quem recebe decide, por critério próprio, se aquilo basta. As duas metades são
separadas e devem ser lidas separadas: a evidência é técnica, o critério de
aceitação é político. Na urna eletrônica, o hash é a evidência; o partido que o
confere com ferramenta própria é quem aplica o critério.

### escrituracao-eletronica
Prestar informação fiscal, contábil ou trabalhista ao Estado em arquivo digital
com valor jurídico, em leiaute definido e assinado. Substitui o livro e a nota
em papel, e desloca o trabalho: em vez de guardar documento, o obrigado passa a
manter seus sistemas capazes de gerar o arquivo exatamente como o leiaute pede.
SPED e eSocial são os dois casos federais.

### meta-governanca-normativa
Antes de decidir o que fazer, alguém decide como se vai decidir: por ordem de
quem manda, por contrato com quem entrega, ou por acordo entre iguais que não
mandam uns nos outros. Cada um desses caminhos serve a um tipo de problema, e a
maioria das organizações usa os três ao mesmo tempo fingindo que usa só o
primeiro. Uma norma que manda os órgãos "pactuarem" um plano está escolhendo o
terceiro caminho; se depois cobra o resultado como se tivesse mandado, misturou
os dois e o comando não pega.

### gradiente-de-isomorfismo-na-importacao
Quando uma organização importa um modelo de fora, o que chega varia entre dois
extremos: a cópia da forma, que rende legitimidade sem mudar nada do trabalho,
e a adaptação real, que muda o trabalho e por isso custa caro. Quase toda
adoção fica em algum ponto entre os dois, e o ponto exato é medível — pelo que
mudou na prática, não pelo que foi anunciado.

### cadastro-territorial
Registro sistemático de quem ocupa e o que existe em cada pedaço do território,
com a geometria junto. Serve de base para planejamento, cobrança e controle
ambiental — e é onde a qualidade do dado depende inteiramente de quem desenhou
o limite, porque o limite de um é o limite do outro.

### governanca-corporativa
Quem manda na diretoria, e para quem a diretoria tem que explicar o que fez. É
o conselho que aprova o rumo, cobra resultado e troca quem não entrega — em
nome dos donos, dos que fiscalizam e de quem depende da organização. Não se
confunde com gestão: gestão é fazer, governança é dizer o que se espera de quem
faz e conferir depois se veio.

### plano-de-gabinete
Substitui `alto-modernismo` (base): rótulo que não diz nada fora da academia.

A crença de que um plano bem desenhado no gabinete vale mais que o jeito que as
pessoas já achavam de fazer no lugar — e que, por isso, dá para reorganizar
cidade, lavoura ou repartição segundo o desenho, ignorando o que estava lá. Não
é a técnica que define, é a fé de que a técnica basta. O sinal é a solução que
chega pronta, idêntica para contextos diferentes, com o saber local tratado
como atraso a corrigir.

### prevencao-a-fraude
Impedir, detectar e responder a quem obtém vantagem indevida por engano ou
falsidade. A parte que costuma ser esquecida é a primeira: prevenir é desenhar o
processo de modo que a mentira não passe, e não apenas caçar depois quem passou.

### servico-compartilhado-generico-cross
Serviço que várias áreas usam e nenhuma delas produz de forma diferente — folha,
protocolo, login, compras — reunido num lugar só em vez de refeito em cada
canto. É a fronteira do que se delega sem perda: como não carrega regra
exclusiva de ninguém, entregá-lo ao mercado ou a um operador central é uso
correto, não abdicação. Slug proposto: `servico-comum`; outros rótulos:
`servico-compartilhado-generico-cross`.

## Candidatos sem lastro suficiente

Não propostos — a cota do passo 5 exige duas âncoras do lote.

- **`congelamento-por-criticidade`** — o sistema que não pode parar também não
  pode ser reorganizado, então a desordem deixa de ser corrigível e passa a ser
  apenas documentada; documentação abundante vira sintoma da imobilidade, não
  sinal de ordem. Âncora: Estudo de caso: SIGEPE **[wiki]**. Sem segunda
  âncora no corpus da frente.

- **`fronteira-de-versionamento`** — quem muda o contrato de interface e quem
  arca com o custo de acompanhar a mudança é decisão separada de quem executa a
  tradução: o login gov.br acerta a execução e transfere por escrito o
  acompanhamento às pontas. Âncora: Estudo de caso: gov.br **[wiki]**. O próprio
  case rebaixa o eixo a higiene de API; entra como candidato, não como proposta.

- **`bifurcacao-arquitetural`** — a plataforma central absorve a heterogeneidade
  de quem a consome, ou obriga o órgão a manter dois jeitos de construir
  sistema, o normal e o conformado a ela. Âncora: Estudo de caso: Estaleiro
  **[wiki]**, que é pergunta formulada sem resposta — responder exige relato de
  órgão contratante.

## Aguardando ingestão

Repenning & Sterman (2001/2002) está no Project do dono e fora do índice: a fila
de ingestão está segurada até o fim da reclassificação. As duas entradas abaixo
foram lidas em primária pelo texto, e recebem `obras-ancora` quando a obra tiver
UUID no acervo.

### armadilha-de-competencias

Uma equipe fecha o buraco de desempenho de dois jeitos: trabalhando mais ou
melhorando o jeito de trabalhar. O primeiro entrega hoje, o segundo só depois —
então, sob pressão, todo mundo escolhe o primeiro e corta o tempo da melhoria.
A capacidade não cai na hora, o que faz parecer que deu certo; quando cai, o
buraco fica maior, a pressão sobe e corta-se mais melhoria ainda.

Não é a mesma coisa que a armadilha de capacidade, embora as duas tenham o
mesmo nome em inglês: aqui a competência existia e definha por falta de
investimento; lá ela nunca existiu, e é a tentativa de adquiri-la que falha por
faltar o que ela pressupõe. Um órgão pode estar preso numa sem estar na outra.

- outros-rótulos: `armadilha-de-competencias`, `capability trap`
- caso falseador: uma organização sob pressão sustentada de entrega cujo
  desempenho não degrade apesar de anos sem tempo dedicado a melhoria — o
  estoque de capacidade não se consumiria.

### erro-de-atribuicao-autoconfirmante

O chefe conclui que o problema é falta de empenho, aperta, e o número sobe — o
que parece dar razão a ele. Só que parte da subida veio do que ele não vê: as
pessoas pararam de fazer manutenção, treinamento e melhoria para dar conta.
O ganho é real e imediato; o estrago é lento, difuso e chega meses depois, longe
demais para ser ligado ao aperto que o causou.

Por isso o erro se confirma sozinho, e cada rodada o reforça: a conclusão de que
o pessoal não se esforça produz a evidência de que o pessoal não se esforçava. O
mesmo desenho aparece quando o indicador de uma falha de sistema é batizado com
o nome de quem está na ponta.

- caso falseador: um aperto de cobrança cujo ganho de curto prazo seja
  integralmente rastreável a mais esforço, sem redução mensurável de manutenção,
  treinamento ou melhoria.

## Colisões vigiadas

Conceitos que ocorrem em `capacidade-estatal` com régua lavrada por outra
cadeira. Não são propostos nem editados aqui:

`governanca-dados` · `lei-de-conway` · `sistemas-distribuidos` ·
`gestao-de-risco` · `gestao-pessoas` · `escalabilidade-sistemas` ·
`extracao-dados`

`federacao-de-identidade` e `garantia-de-identidade` ocorrem neste domínio e
seguem a régua de segurança, sob `iam` e `autenticacao`. Vizinhas de
`prova-de-identidade`, proposta por `claudinho-seguranca` na rodada 2: aquela é
o ato de estabelecer que a conta corresponde a uma pessoa real; `garantia-de-
identidade` é o grau de confiança que esse ato produz.
