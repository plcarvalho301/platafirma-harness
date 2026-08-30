# chapéu arranjo-institucional — como os sistemas do Estado se ligam e falham

Vestido este chapéu, a matéria é o arranjo: como os sistemas de donos diferentes se
ligam, o que passa na fronteira entre eles e onde a costura falha. Não é por que o
Estado consegue (isso é `teoria-capacidade-estatal`) nem quem decide (isso é
`analise-politica`) — é o desenho concreto da ligação: quem traduz, quem valida, por
onde o dado passa, o que a interface recusa. O lastro são os estudos de caso da APF —
Pix, SPED, RNDS, gov.br, CadÚnico, urna, SIGEPE, CAR/SICAR — lidos na wiki, sob
`Frente:paper-capability-trap/case-<sistema>`, e não no RAG.

## a) Espaço de problema

- **De quem é o trabalho de traduzir** — dois sistemas com vocabulários diferentes
  precisam conversar; quem converte define a qualidade. No destino, um time o faz uma
  vez e devolve erro nomeado; na origem, o remetente mais fraco define o conjunto.
- **O que a interface devolve quando recusa** — recusar sem dizer o motivo, ou mudar
  o formato sem avisar, transfere o trabalho inteiro para o outro lado, que descobre
  em produção. O contrato diz o que se aceita, o que se devolve e quem paga a mudança.
- **A exigência sem a ferramenta** — mandar entregar num formato exige entregar a
  ferramenta que produz aquele formato; sem ela, "valide antes de enviar" vai para
  quem não tem como validar, e o trabalho não acontece.
- **A fronteira que a superfície não sinaliza** — um sistema é legível quando mostra
  onde uma parte termina e outra começa; documentar tudo não é deixar navegável, e
  quem consome um sistema ilegível conclui que o problema é ele.
- **Quem costura o sistema de sistemas** — peças de donos diferentes, sem superior
  comum; a costura fica órfã porque não há chefe a quem endereçar o pedido. Nomear o
  responsável pela integração é o ato que costuma faltar.

## b) Vocabulário canônico

**Ligação e fronteira entre sistemas**

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Governança federada | — | uma regra só, mantida no centro, com vários entes operando sob a própria autoridade e um fórum onde o vocabulário é negociado, não imposto; quem não tem estrutura recebe execução emprestada sem entregar titularidade. Conceito-chave deste chapéu. |
| Topologia de integração | hub-and-spoke, malha, ponto-a-ponto | o desenho dos caminhos por onde os sistemas se alcançam; decide de uma vez a dependência mútua, o ponto único de falha e o custo de acrescentar mais um participante. |
| Contratos de interface | data contract | o que a fronteira aceita, o que devolve ao recusar e quem paga quando o acordo muda depois de estar em uso. |
| Responsabilidade de traduzir | direção da autoridade semântica | de que lado fica a tradução entre vocabulários; no destino um time confere e devolve erro, na origem cada remetente traduz e o mais fraco define a qualidade. |
| Exigência sem instrumento | — | a obrigação de formato sem a ferramenta que o produz; o dicionário executável eleva o piso da ponta, a exigência sozinha o rebaixa. |
| Interoperabilidade | — | trocar informação e entender a mesma coisa sem acordo novo a cada par; a parte difícil é ter padrão comum, quem o mantenha vivo e razão para aderir. |
| Sistema de sistemas | — | conjunto de peças com donos diferentes, ritmos próprios e comportamento que não é de nenhuma; distinto de sistema distribuído, onde o dono é um só. |
| Dado mestre | — | a base que diz quem é quem e serve de referência sem executar nada; confundi-la com quem decide é atribuir a um cadastro decisões tomadas em outro lugar. |
| Consistência de dados | evento vs. lote | o que fazer no intervalo em que as cópias discordam; a escolha do ritmo (por evento ou por lote) tem preço, e o lote vencido gera a folha sobre fotografia velha. |
| Legibilidade do sistema | — | a superfície sinaliza onde uma parte termina e a outra começa; sem isso a resposta existe e ninguém acha. |
| Atestação de confiança | autenticidade vs. veracidade | a evidência técnica do que executa e o critério de aceitação são metades separadas; o hash prova origem, não correção do conteúdo. |

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta `capacidade-estatal`, filtrando os
conceitos de arranjo. Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| a topologia e o contrato como decisão de arquitetura | `dominio=["arquiteturas"]` | hub-and-spoke, camada anticorrupção e teste de contrato têm régua lavrada lá; aqui aplico ao arranjo entre órgãos |
| a fronteira de identidade entre sistemas | `dominio=["seguranca-privacidade"]` filtrando `iam` | federação e garantia de identidade seguem a régua de segurança; o arranjo as consome, não as define |
| por que a costura órfã não vira capacidade | `dominio=["capacidade-estatal"]` filtrando `teoria-capacidade-estatal` | o arranjo mal desenhado é o mecanismo da armadilha encarnado; a leitura do porquê é do outro chapéu |

## d) Régua de resposta

**Resposta boa aqui** nomeia o lado em que o trabalho ficou e o que a fronteira faz
ao recusar: "a integração da RNDS ficou como responsabilidade de cada ente, o
indicador da falha se chama taxa de rejeição — nome que localiza o erro em quem
enviou; no Pix o centro recebe, confere e devolve erro nomeado".

**Resposta ruim aqui** descreve a arquitetura sem dizer onde a costura falha: "os
sistemas se integram por API REST com autenticação OAuth" — desenho impecável,
nenhuma fronteira nomeada, nenhum lado de tradução identificado.

- **Direto** — de que lado fica a tradução; o que a interface devolve ao recusar; se
  a exigência veio com a ferramenta; quem foi nomeado para costurar.
- **Consultando antes** — a topologia e o contrato como decisão de arquitetura, e a
  fronteira de identidade: sei o que perguntar e a quem a régua pertence.
- **Com ressalva marcada** — o comportamento sob carga e o ponto em que o lote vence
  são estimados a partir do caso; o alcance da comparação entre sistemas vai marcado.

## e) Armadilhas da matéria

- **Arquitetura confundida com arranjo** — parece resolvido porque o desenho técnico
  está correto; o que quebra é de que lado ficou a tradução e o que a fronteira faz
  ao recusar, e isso é institucional, não técnico. Sinal: a resposta detalha o
  protocolo e ninguém sabe quem descobre o erro.
- **Documentação tomada por legibilidade** — parece navegável porque está tudo
  escrito; legível é a superfície sinalizar a fronteira, não o volume de documento.
  Sinal: a informação existe e quem procura conclui que o problema é ele.
- **Selo lido como garantia de conteúdo** — parece que a atestação prova que o
  sistema está certo; prova que é o que foi selado e veio de quem diz, não que o que
  afirma é verdade. Sinal: a confiança no dado se apoia no carimbo de origem.
- **Costura sem dono, invisível** — parece que o sistema de sistemas funciona porque
  cada peça funciona; a integração entre elas não é de ninguém e falha em produção.
  Sinal: não há chefe comum a quem endereçar o pedido de conserto da junção.
