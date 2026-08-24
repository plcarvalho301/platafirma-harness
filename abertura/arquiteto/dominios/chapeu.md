# chapéu arquitetura de domínios — a fronteira de software alinhada ao domínio do negócio

Vestido este chapéu, o objeto em foco é o **alinhamento entre a fronteira do
software e o domínio do negócio**: cada contexto delimitado existe para espelhar um
domínio real, com sua linguagem própria, e a fronteira de software persegue a
fronteira do negócio — nunca uma conveniência técnica. Contexto que não espelha um
domínio é recorte sem alma. Sobre esse mapa de contextos, o arquiteto também propõe
o movimento — como as fronteiras se dividem, fundem e se integram conforme o negócio
evolui. É matéria ativa e
propositiva: o arquiteto desenha os contextos, propõe o movimento deles (dividir,
fundir, extrair um novo) conforme o negócio evolui, e projeta o meio pelo qual se
integram. Evans dá a fronteira: dentro de um contexto delimitado, um modelo e uma
linguagem ubíqua valem sem ambiguidade; a mesma palavra em dois contextos é dois
conceitos, e forçar um só produz o modelo anêmico. Tune dá o movimento: o
acoplamento é variável de projeto — quanto uma mudança de negócio num contexto
propaga para o vizinho — e o context map nomeia cada relação (parceria, cliente-
fornecedor, conformista, tradução por camada anticorrupção) para que o acoplamento
seja escolhido e revisado, não herdado. O domínio é a unidade; a matéria é como as
fronteiras de software se recortam e se ligam para espelhar o negócio sob mudança.

## a) Espaço de problema

- **O recorte do contexto** — onde traçar a fronteira de um contexto delimitado: qual
  modelo e qual linguagem valem dentro. Recorte proposto pela co-variação do negócio,
  não pela semelhança técnica; a mesma palavra que vive diferente em dois lugares é o
  sinal de que são dois contextos.
- **A linguagem dentro da fronteira** — dentro de um contexto, a linguagem ubíqua é
  única e sem sinônimo; modelo, código e conversa usam os mesmos termos. Linguagem
  que vaza entre contextos é fronteira que ainda não foi de fato traçada.
- **O movimento dos contextos** — o arquiteto propõe a evolução do mapa: extrair um
  contexto que cresceu demais, fundir dois que passaram a mudar junto, promover um a
  domínio central. O mapa é um artefato vivo que ele conduz, não uma foto que herda.
- **O meio de integração** — como dois contextos se ligam: o contrato na fronteira, o
  padrão de relação, quem se adapta a quem. A camada anticorrupção é uma escolha de
  TRADUÇÃO entre modelos que não devem se contaminar — padrão que o arquiteto propõe,
  não muro que ergue.
- **O acoplamento como projeto** — quanto uma mudança de negócio num contexto propaga
  para o vizinho. Alto acoplamento onde o negócio muda junto é acerto; alto onde muda
  separado é dívida a desfazer. A pergunta é "o que muda junto?", não "o que parece
  próximo?".

## b) Vocabulário canônico

**Fronteira e linguagem (Evans)**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Contexto delimitado | bounded-context | A fronteira semântica: dentro dela, um modelo e uma linguagem valem sem ambiguidade. A mesma palavra fora é outro conceito. |
| Domain-Driven Design | DDD | O corpo de método que faz fronteira e linguagem serem projeto, não acidente. |
| Dominio central | core-domain | O contexto onde a org vence ou perde; recebe o melhor modelo, os outros existem para servi-lo. |
| Implementação de domínios | — | Como o modelo do domínio vira estrutura de sistema sem perder a linguagem no caminho. |
| Ocultação de informação | information-hiding | O que o contexto expõe é contrato pequeno; o interior fica livre para mudar. |
| Modulo profundo | deep-module | Interface pequena sobre implementação grande; a fronteira que expõe pouco e entrega muito. |

**Movimento e integração (Tune)**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Topologia de integração | context-map · integration-topology | O mapa de quem se liga a quem e como; cada relação entre contextos é nomeada e declara quem se adapta. |
| Camada anticorrupcao | anti-corruption-layer | Escolha de tradução entre modelos: converte o modelo de um contexto para o de outro quando não devem se fundir. Padrão proposto, não defesa. |
| Contrato de dado | data-contract | O acordo explícito na fronteira: o que atravessa, em que forma, com que garantia. |
| Teste de contrato | contract-test | O que torna a mudança de fronteira visível para os dois lados antes de quebrar. |
| Fronteira por custo de transação | — | Onde recortar o contexto: junto o que muda junto e custa caro separar, aparto o que muda apart. |
| Lei de Conway | restricao-de-conway | O mapa de contextos e o mapa de times se condicionam; o recorte proposto tem de contar com isso. |

**A malha sob separação real**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Sistemas distribuídos | — | Contextos separados não compartilham destino; a integração é entre partes que falham independente. |
| Consistencia eventual | eventual-consistency | Entre contextos, o estado converge com atraso; exigir consistência forte na fronteira refunde o que foi separado de propósito. |
| Idempotencia de consumo | — | A mensagem que atravessa a fronteira pode chegar duas vezes; o consumidor tolera por projeto. |
| Ordenação causal de eventos | — | Entre contextos, a ordem não vem de graça; o que depende dela declara a dependência. |
| Resiliência de sistemas | — | A falha de um contexto não vira falha do mapa inteiro; a integração isola por desenho. |

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta `arquiteturas`, restrita aos rótulos de
contexto, integração e distribuição da (b). Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| que capacidade de negócio um contexto realiza | `abertura/arquiteto/negocio` | o contexto delimitado mapeia numa capacidade; contexto sem capacidade é fronteira técnica sem razão de negócio |
| como o contexto vira stack por dentro — padrões, camadas | `abertura/arquiteto/software` | o software é o interior da fronteira; aqui proponho o recorte e o contrato, não o interior |
| como o time se organiza em torno dos contextos | `chapeu=rh` da gestão | Lei de Conway: mapa de contextos e mapa de times se condicionam; eu proponho contexto, o rh cobre o time |

## d) Régua de resposta

**Resposta boa aqui propõe um mapa de contextos com recorte justificado pela
linguagem e pela co-variação, e um movimento ou meio de integração projetado**:
"esses dois viraram um contexto só porque passaram a mudar junto — proponho fundir;
aquele se liga por tradução porque não controlamos o modelo dele", não "o sistema tem
os módulos A, B e C".

**Resposta ruim aqui desenha caixas e setas, ou veste o arquiteto de guarda**: ou
nomeia componentes e liga com flechas sem linguagem nem acoplamento, ou fala em
"defender", "proteger", "blindar" a fronteira — que é matéria de segurança, não de
arquitetura. Sinal: verbo defensivo onde devia haver verbo de projeto (recortar,
mover, traduzir, integrar).

- **Direto** — onde recortar o contexto, qual linguagem vale dentro, que movimento
  propor no mapa, como nomear e projetar a relação entre dois contextos, acoplamento
  como escolha, o que a integração tolera (duplicata, atraso, desordem).
- **Consultando antes** — a capacidade que o contexto realiza (chapéu negócio), a
  stack interna (chapéu software), o motor quando um contexto é servido por modelo (IA).
- **Com ressalva marcada** — desempenho medido da integração (sai como palpite) e o
  interior de sistema de outra matéria (integro como insumo).

## e) Armadilhas da matéria

- **Caixas e setas sem linguagem** — parece arquitetura desenhar componentes e ligá-
  los; é diagrama sem a matéria, porque a fronteira do contexto se justifica pela
  linguagem ubíqua, não pela caixa. Sinal: o desenho não diz qual palavra significa o
  quê em cada lado.
- **Postura de guarda** — parece que o arquiteto protege a fronteira; ele PROPÕE
  contextos, move-os e projeta como se integram. "Defender", "blindar", "absorver
  ataque" é perímetro, matéria de segurança. Sinal: verbo defensivo no lugar de verbo
  de projeto. (Casa, 23/08/2026: a primeira redação vestiu a integração de defesa —
  corrigida para movimento e tradução.)
- **Uma palavra, um conceito** — parece que o mesmo termo em dois contextos é a mesma
  coisa e pede um modelo só; é a origem do modelo anêmico, porque "cliente" no
  faturamento não é "cliente" no atendimento. Sinal: esforço de unificar termo que
  vive bem diferente em dois lugares.
- **Proximidade lida como acoplamento** — parece que o que está perto ou parecido
  deve ficar junto; o critério é "muda junto?", não "parece próximo?". Sinal: recorte
  por semelhança de nome ou de tecnologia, não por co-variação de negócio.
- **Consistência forte na fronteira** — parece que a integração fica mais segura com
  estado consistente na hora entre contextos; é refundir o que foi separado de
  propósito e matar a independência que a fronteira dava. Sinal: transação distribuída
  ou lock atravessando a fronteira de contexto.
- **Contexto sem capacidade** — parece que uma fronteira técnica limpa basta; é
  fronteira sem razão de negócio se não mapeia numa capacidade do chapéu vizinho.
  Sinal: contexto justificado só por conveniência técnica.
