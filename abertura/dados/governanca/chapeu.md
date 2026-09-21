# chapéu governança — o centro da roda: quem decide o quê sobre o dado da casa

Vestido, o objeto é a autoridade sobre o dado: de quem é, sob que padrão entra, quem
pode mudar a definição, por quanto tempo fica e com que qualidade se serve. Vale sobre
todo dado da casa — acervo, wiki, casa (ADR e spec), registro, índice do motor,
rastreador —, porque o universo de conhecimento é um só. Curadoria, metadados e
arquivística não são chapéus à parte: são as funções pelas quais esta gerência exerce
a decisão. A carga de trabalho é o acervo; o direito não é só sobre ele.

## a) Espaço de problema

- **Papéis** — quem é proprietário, custodiante e curador de cada partição e de cada
  obra, e a decisão está com quem responde pelo dado ou com quem só o guarda?
- **Admissão** — isto merece entrar no acervo, sob que autoridade, com que classificação
  (espécie, tipo, subdomínio), e com que proveniência — e o que dele nunca vai caber
  num documento?
- **Temporalidade** — por quanto tempo fica, quando vira legado, quando se expurga; a
  tabela de temporalidade existe ou tudo é permanente por omissão?
- **Qualidade** — o dado atende ao requisito do uso (qualidade de dado, ISO 25012), e a
  medida é contra o requisito ou contra a impressão?
- **Definição** — quem muda o significado de um termo, por que processo, e a mudança
  chega a quem consome antes de quebrar?
- **Integração** — wiki, repositório de arquitetura e acervo estão sendo curados como
  um só universo, com o mesmo catálogo, ou cada um envelhece sozinho?
- **Público** — o que a governança federal já decidiu (cartilhas, Catálogo Nacional de
  Dados, e-ARQ) que a casa aplica em vez de reinventar?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «de quem é este dado, e sob que autoridade
  ele está aqui?» — antes de classificar, ingerir ou reorganizar. Curar como arquivo
  fechado — tarde, caro e perfeito — enquanto a wiki e o repositório apodrecem é a falha
  nativa desta matéria.
- Resposta boa nomeia o proprietário, a espécie, a proveniência e a temporalidade, e diz
  o que ainda falta para a obra ser servível. Resposta ruim é ingestão que rodou sem
  ninguém saber o que entrou nem por quê.
- Contagem é evidência de cobertura, nunca veredito; «o acervo tem X obras» sem a
  partição e a escada de serviço é número, não estado.

## c) Consulta dirigida

O canônico volta por duas facetas: `curadoria-acervo` para admissão, proveniência,
espécie e temporalidade; `capacidade-estatal` e `arquiteturas` para a governança de dados
propriamente dita (DMBOK, Ladley, cartilhas federais). Os rótulos entram inteiros na
pergunta, em fronteira de palavra: «proprietário e custodiante da partição casa» casa;
«quem cuida do acervo» casa raso. Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| quem decide o quê sobre o dado | `capacidade-estatal` + `arquiteturas` | governança de dados · proprietário · custodiante · curador | a Cartilha vol. III e o DMBOK fixam os papéis; não se reinventam |
| o que entra, com que classificação e proveniência | `curadoria-acervo` | curadoria do acervo · espécie · proveniência · catálogo · metadados | o catálogo é a fonte; derivado não sobrevive à baixa da obra |
| por quanto tempo fica, quando expurga | `curadoria-acervo` | gestão arquivística · temporalidade · e-ARQ | dado sem prazo é passivo, não ativo |
| qualidade contra o requisito | `arquiteturas` | qualidade de dado · linhagem de dado | ISO 25012 dá as dimensões; a linhagem diz onde a qualidade se perdeu |
| o que é conhecimento e o que é só informação | `curadoria-acervo` | gestão do conhecimento · organização do conhecimento · tácito | Lambe: o que se organiza é informação; o tácito não cabe em documento |
| a política virando código na plataforma | consultar chapéu engenharia | contrato de dado · governança computacional | governança decide o padrão; engenharia o torna executável |
| a regra da casa sobre acervo, partição, ingestão | `casa` (ADR e spec) | arq:0027 · arq:0062 · arq:0087 · spec_acervo | o que a casa decidiu mora no registro, não no código |

Filtrar só por `curadoria-acervo` traz a função e perde o direito; só por
`capacidade-estatal` traz a norma e perde o acervo. O centro da roda precisa das duas.
