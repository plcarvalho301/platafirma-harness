# chapéu comportamento — o canal agêntico: o que leva o agente a agir

Vestido, o objeto é o texto que o agente lê para agir. Cobre o que ele é (persona,
chapéu, postura, viés), o que está em volta dele (cenário, circunstância, ritual), o que
o faz começar (gatilho) e cada peça que ele lê como instrução: o passo do processo, a
frase de roteamento da skill («leia X quando Y»), a descrição da tool, a mensagem de
delegação ao subagente, a forma da nota que fica na mesa e no caderno, e o texto de
erro, recusa ou aviso da porta quando ele faz papel de instrução. A pessoa entra como
dado externo. A engenharia de prompt mora aqui, como o ofício de escrever cada uma
dessas peças dentro do envelope que a ia mede.

## a) Espaço de problema

- **Persona ou cena** — mudando a situação, a frase continua valendo (persona, postura,
  chapéu) ou deixa de valer (cenário, circunstância, ritual)? Escrita no lado errado, ela
  puxa a persona em toda situação onde não devia valer, ou some onde devia.
- **Induz ou instrui** — tirado o imperativo, o texto ainda muda o que o agente faz? A
  inclinação se escreve como assinatura se-então, em primeira pessoa e com o motivo; a
  regra que vale para todos e se confere por portão é norma, e não entra na persona.
- **O começo** — o gatilho reconhece um começo pelo sinal que aparece de fato, no turno
  do dono, no retorno da tool ou no estado do serviço, sem disparo falso nem disparo
  perdido, e não colide com outro gatilho que reconhece o mesmo sinal?
- **O rastro entre tools** — a toolstring e a descrição da tool deixam um rastro bom para
  o agente forragear entre as tools da porta, ou duas se sobrepõem e o nome não diz qual
  serve?
- **Quem lê sem poder perguntar** — a mensagem de delegação e a nota de mesa chegam a um
  leitor que não tem a quem perguntar: dizem o que ele precisa reconhecer, o que fica de
  fora e quando parar?
- **O comportamento real** — o que as fitas mostram que o agente fez, e o comportamento
  aguenta a fita longa, quando o começo da janela já perdeu peso?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que o agente precisa reconhecer, e o que
  ele faz quando reconhece?», antes de escrever qualquer linha.
- Resposta boa diz se o texto é constitutivo ou de cena e se induz ou instrui; no
  gatilho, diz quando ele dispara, quando cala e com que outro gatilho pode colidir, e
  confere contra o disparo esperado e o proibido que a jornada escreveu. Resposta ruim
  acrescenta instrução para o agente obedecer, ou escreve na persona o que só vale num
  cenário.
- O efeito de um texto novo sai como hipótese até a avaliação que a ia gera mostrar o
  antes e o depois. Não escrevo os casos que avaliam o gatilho que escrevi.

## c) Consulta dirigida

Boa parte das obras deste chapéu ainda não tem domínio no acervo: a consulta vai sem
filtro de domínio, pelo conceito ou pela frase com o rótulo inteiro. «Persona ou cena
na assinatura se-então» casa; «melhorar o prompt» casa raso. Gatilho, assinatura
se-então, texto indutivo e instrutivo, disparo falso e perdido e seleção de ferramenta
ainda não têm conceito no tesauro; o roteador casa este chapéu por personalidade
situada, abordagem dramatúrgica, hábito, intenção de implementação, decisão por
reconhecimento, encenação de papel, restrição de formato e engenharia de prompt.

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a frase mora na persona ou na cena | `conceito=["personalidade-situada","abordagem-dramaturgica"]` | disposição e papel · personalidade situada · assinatura se-então · abordagem dramatúrgica · circunstâncias dadas | Mischel e Shoda dão a assinatura se-então; Burke, a razão entre cena e agente; Stanislavski, em An Actor's Work, as circunstâncias dadas em que o ator age em vez de representar o resultado |
| a situação como quem age a define | `conceito=["analise-de-quadros","papel-social"]` | análise de quadros · definição da situação · papel social · status | Goffman, em A representação do eu e Frame Analysis; DaMatta, Carnavais, Malandros e Heróis, para o papel que muda com a situação; Johnstone, Impro, para o status que se faz e não se é |
| o modelo como ator | `conceito=["encenacao-de-papel","deriva-de-persona"]` | encenação de papel por modelo de linguagem · vetor de persona · deriva de persona | Shanahan e outros (o simulador e a superposição de personagens); Persona Vectors; Claude's character, para o traço escrito como inclinação e não como regra |
| a personagem com poucos traços | `conceito=["personagem-de-ficcao","papel-instanciavel"]` | personagem de ficção · papel instanciavel | Candido e outros, A personagem de ficção, para a seleção de traços que o leitor completa; Thomasson, Fiction and Metaphysics, e Boal, Teatro do Oprimido |
| induzir ou mandar | `conceito=["habito","intencao-de-implementacao"]` | texto indutivo e instrutivo · hábito · deixa de contexto · intenção de implementação | Wood e Neal (a deixa do contexto dispara sem passar pelo objetivo); Gollwitzer e Sheeran (o se-então que entrega o controle à deixa); Problems with Rules e Playing by the Rules, para quando a regra vale mais que o padrão |
| o gatilho e o começo | `conceito=["decisao-por-reconhecimento","memoria-prospectiva","nivel-srk"]` | decisão por reconhecimento · memória prospectiva · níveis habilidade-regra-conhecimento · regra condição-ação · resolução de conflito entre gatilhos | Klein, Sources of Power; McDaniel e Einstein; Rasmussen; Soar e CoALA para a regra que dispara e o conflito entre as que casam; Fogg para o gatilho que chega na hora em que se pode agir |
| o plano diante da situação | frase com «ação situada» | — | Suchman, Plans and Situated Actions: o plano é recurso da ação, não programa que a controla |
| a descrição da tool e da skill | `dominio=["ia"]` | seleção de ferramenta · descrição como disparo · disparo falso e perdido · engenharia de prompt | Writing effective tools for agents, Equipping agents with Agent Skills, SkillJuror e The Prompt Report |
| quanto cabe e onde pega | consultar ia, chapéu contexto | menor conjunto de alto sinal · restrição de formato | o envelope se mede lá; aqui se decide o que vai dentro |
| o que o agente fez de fato | consultar ia, chapéu avaliacao, e `abertura/produto/pesquisa` | — | a ia gera a avaliação; a pesquisa a questiona |
| o passo de um processo | consultar gestão estratégica, chapéu processos | processo de negocio | o desenho do passo é de lá; a escrita para o agente é daqui |

Homonímias a afastar: no chapéu processos, gatilho é o evento que inicia o processo de
negócio; aqui é o que faz o agente começar. Em pesquisa, comportamento (entrevista por
comportamento passado, mudança de comportamento) é o da pessoa; aqui é o do agente. Em
pesquisa com usuário, persona é o arquétipo de quem usa; aqui é a cadeira.
