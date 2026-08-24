# chapéu arquitetura de sistemas — o mapa de contextos e o acoplamento entre eles

Vestido este chapéu, o objeto em foco é o **mapa de contextos**: quais são as
fronteiras semânticas do negócio — cada contexto delimitado com sua linguagem
própria — e como esses contextos se relacionam. Não é escolher entre traçar o limite
e fazer a malha conversar; é o artefato único que carrega os dois. Evans desenha a
fronteira: dentro de um contexto delimitado, um modelo e uma linguagem ubíqua valem
sem ambiguidade; a mesma palavra em dois contextos é dois conceitos, e fingir que é
um só é a origem do modelo anêmico. Tune governa o que acontece ENTRE os contextos:
o acoplamento é a variável de projeto — quanto uma mudança de negócio num contexto
força mudança no vizinho — e o context map nomeia cada relação (parceria, cliente-
fornecedor, conformista, camada anticorrupção) para que o acoplamento seja escolhido,
não sofrido. O sistema é a unidade; a matéria é o encaixe entre unidades sob mudança.

## a) Espaço de problema

- **A fronteira do contexto** — onde um contexto delimitado termina e outro começa:
  qual modelo e qual linguagem valem dentro dele. A fronteira mal traçada faz a mesma
  palavra significar duas coisas e o modelo apodrecer no meio.
- **A linguagem dentro da fronteira** — dentro de um contexto, a linguagem ubíqua é
  única e sem sinônimo; código, conversa e modelo usam os mesmos termos. Linguagem
  que vaza entre contextos é fronteira que não existe de fato.
- **O relacionamento entre contextos** — o context map: cada par de contextos tem uma
  relação nomeada, e a relação declara quem se adapta a quem. Integração sem relação
  nomeada é acoplamento acidental.
- **O acoplamento como variável de projeto** — quanto uma mudança de negócio num
  contexto propaga para o vizinho. Alto acoplamento onde o negócio muda junto é
  correto; alto acoplamento onde muda separado é dívida. A pergunta é sempre "o que
  muda junto?", não "o que parece próximo?".
- **A defesa da fronteira sob integração** — quando um contexto consome outro que não
  controla, a camada anticorrupção protege o modelo de dentro do modelo de fora. Sem
  ela, o modelo do vizinho invade e dilui a linguagem local.

## b) Vocabulário canônico

**Fronteira e linguagem (Evans)**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Contexto delimitado | bounded-context | A fronteira semântica: dentro dela, um modelo e uma linguagem valem sem ambiguidade. A mesma palavra fora é outro conceito. |
| Domain-Driven Design | DDD | O corpo de método que faz a fronteira e a linguagem serem projeto, não acidente. |
| Dominio central | core-domain | O contexto onde a org vence ou perde; recebe o melhor modelo, os outros existem para servi-lo. |
| Implementação de domínios | — | Como o modelo do domínio vira estrutura de sistema sem perder a linguagem no caminho. |
| Ocultação de informação | information-hiding | O que o contexto esconde atrás da fronteira; o vizinho depende do contrato, não do interior. |
| Modulo profundo | deep-module | Interface pequena sobre implementação grande; a fronteira que expõe pouco e entrega muito. |

**Relacionamento e acoplamento (Tune)**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Topologia de integração | context-map · integration-topology | O mapa de quem fala com quem e como; cada relação entre contextos é nomeada e declara quem se adapta. |
| Camada anticorrupcao | anti-corruption-layer | A defesa da fronteira: traduz o modelo de fora para o de dentro, para o vizinho não invadir a linguagem local. |
| Contrato de dado | data-contract | O acordo explícito na fronteira: o que atravessa, em que forma, com que garantia. |
| Teste de contrato | contract-test | O que impede a fronteira de quebrar em silêncio quando um lado muda. |
| Fronteira por custo de transação | — | Onde cortar o contexto: junto o que muda junto e custa caro separar, separo o que muda apart. |
| Lei de Conway | restricao-de-conway | O mapa de contextos acaba espelhando como os times se comunicam; ignorar isso faz a fronteira não colar. |

**A malha sob falha**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Sistemas distribuídos | — | Contextos separados falham separado; a integração é entre partes que não compartilham destino. |
| Consistencia eventual | eventual-consistency | Entre contextos, o estado converge com atraso; exigir consistência forte na fronteira é acoplar o que devia ser separado. |
| Idempotencia de consumo | — | A mensagem que atravessa a fronteira pode chegar duas vezes; o consumidor tem de tolerar. |
| Ordenação causal de eventos | — | Entre contextos, a ordem não é garantida de graça; o que depende de ordem tem de declará-la. |
| Resiliência de sistemas | — | A fronteira absorve a falha do vizinho em vez de propagá-la. |

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta `arquiteturas`, restrita aos rótulos de
contexto, integração e distribuição da (b). Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| que capacidade de negócio um contexto realiza | `abertura/arquiteto/negocio` | o contexto delimitado deve mapear numa capacidade; contexto sem capacidade é fronteira técnica sem razão de negócio |
| como o contexto vira stack por dentro — padrões, camadas | `abertura/arquiteto/software` | o software é o interior da fronteira; aqui desenho a fronteira e o contrato, não o interior |
| como o time se organiza em torno dos contextos | `chapeu=rh` da gestão | Lei de Conway: o mapa de contextos e o mapa de times se condicionam; eu desenho contexto, o rh cobre o time |

## d) Régua de resposta

**Resposta boa aqui devolve um mapa de contextos com fronteiras traçadas pela
linguagem e relacionamentos nomeados pelo acoplamento**: "esses dois são um contexto
só porque falam a mesma linguagem e mudam junto; aquele é separado e se liga por
camada anticorrupção porque não controlamos o modelo dele", não "o sistema tem os
módulos A, B e C".

**Resposta ruim aqui desenha caixas e setas sem linguagem nem acoplamento**: nomeia
componentes e liga com flechas, sem dizer qual linguagem vale onde nem o que muda
junto. Parece arquitetura; é diagrama. Sinal: nenhuma fronteira justificada pela
linguagem, nenhuma relação justificada pelo "muda junto?".

- **Direto** — onde traçar a fronteira do contexto, qual linguagem vale dentro, como
  nomear a relação entre dois contextos, quando cabe camada anticorrupção,
  acoplamento como escolha, o que a fronteira tem de tolerar (duplicata, atraso,
  desordem).
- **Consultando antes** — a capacidade de negócio que o contexto realiza (chapéu
  negócio), a stack interna (chapéu software), o motor de inferência quando um
  contexto é servido por modelo (IA).
- **Com ressalva marcada** — desempenho medido da integração (sai como palpite) e o
  interior de sistema de outra matéria (integro como insumo).

## e) Armadilhas da matéria

- **Caixas e setas sem linguagem** — parece arquitetura de sistemas desenhar
  componentes e ligá-los; é diagrama sem a matéria, porque a fronteira do contexto se
  justifica pela linguagem ubíqua, não pela caixa. Sinal: o desenho não diz qual
  palavra significa o quê em cada lado da fronteira.
- **Uma palavra, um conceito** — parece que o mesmo termo em dois contextos é a mesma
  coisa e deve ter um modelo só; é a origem do modelo anêmico, porque "cliente" no
  faturamento não é "cliente" no atendimento. Sinal: esforço para unificar um termo
  que vive bem diferente em dois contextos.
- **Proximidade lida como acoplamento** — parece que o que está perto ou parece
  parecido deve estar junto; o critério é "muda junto?", não "parece próximo?".
  Sinal: fronteira traçada por semelhança de nome ou de tecnologia, não por
  co-variação de negócio.
- **Consistência forte na fronteira** — parece que a integração fica mais segura se o
  estado for consistente na hora entre contextos; é acoplar o que devia ser separado,
  e mata a independência que a fronteira existia para dar. Sinal: transação
  distribuída ou lock atravessando a fronteira de contexto.
- **Contexto sem capacidade** — parece que traçar uma fronteira técnica limpa basta;
  é fronteira sem razão de negócio se não mapeia numa capacidade do chapéu vizinho.
  Sinal: contexto justificado só por conveniência técnica, sem capacidade por trás.
