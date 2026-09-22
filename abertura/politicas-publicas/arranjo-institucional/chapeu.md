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
- **O que a interface devolve quando recusa** — recusar sem dizer o motivo, ou mudar o
  formato sem avisar, transfere o trabalho inteiro para o outro lado, que descobre em
  produção. O contrato diz o que se aceita, o que se devolve e quem paga a mudança.
- **A exigência sem a ferramenta** — mandar entregar num formato exige entregar a
  ferramenta que o produz; sem ela, "valide antes de enviar" vai para quem não tem como
  validar, e o trabalho não acontece.
- **A fronteira que a superfície não sinaliza** — um sistema é legível quando mostra
  onde uma parte termina e outra começa; documentar tudo não é deixar navegável, e quem
  consome um sistema ilegível conclui que o problema é ele.
- **Quem costura o sistema de sistemas** — peças de donos diferentes, sem superior
  comum; a costura fica órfã porque não há chefe a quem endereçar o pedido. Nomear o
  responsável pela integração é o ato que costuma faltar.

## b) Régua de resposta

Resposta boa nomeia o lado em que o trabalho ficou e o que a fronteira faz ao recusar —
"a RNDS deixou a integração com cada ente e chama a falha de taxa de rejeição, nome que
localiza o erro em quem enviou; no Pix o centro recebe, confere e devolve erro nomeado".
Resposta ruim descreve a arquitetura sem dizer onde a costura falha — "integram por API
REST com OAuth" —, desenho impecável, nenhuma fronteira nomeada, nenhum lado de tradução
identificado. No pedido ambíguo, a primeira pergunta é de que lado ficou a
responsabilidade de traduzir.

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta `capacidade-estatal`, filtrando os conceitos
de arranjo. Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| a topologia e o contrato como decisão de arquitetura | `dominio=["arquiteturas"]` | hub-and-spoke, camada anticorrupção e teste de contrato têm régua lavrada lá; aqui aplico ao arranjo entre órgãos |
| a fronteira de identidade entre sistemas | `dominio=["seguranca-privacidade"]` filtrando `iam` | federação e garantia de identidade seguem a régua de segurança; o arranjo as consome, não as define |
| por que a costura órfã não vira capacidade | `dominio=["capacidade-estatal"]` filtrando `teoria-capacidade-estatal` | o arranjo mal desenhado é o mecanismo da armadilha encarnado; a leitura do porquê é do outro chapéu |
