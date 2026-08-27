# caderno arquiteto — lições duráveis do desenho arquitetural

Durável: continua verdadeiro depois que o assunto morrer, e a próxima fita pagaria
para re-derivar. Entrada nova substitui a que contradiz; o histórico é o git.

## Capacidade na cadeia capacidade:verbo:ferramenta É a capability de negócio BIZBOK

O termo "capacidade" da lógica `capacidade : verbo : ferramenta` SEMPRE foi a
**business capability do BIZBOK** — a mesma coisa do mapa em
`platafirma-arquitetura/docs/arquitetura-negocio-operacao.md` (§1, 20 capacidades em
4 tiers, régua `arq:0059`). Não é taxonomia própria do ferramental.

- Diferença é só de nomenclatura, não de conceito: `iam == acesso`,
  `gestao-de-motores == motor`. Ao casar verbo/stack com capacidade, o alvo é o rótulo
  BIZBOK do mapa de negócio, não um vocabulário paralelo do golden record.
- Modo de falha observado (fita 26/08/2026): tratar o golden record de
  `acervo.ferramental` como se a coluna "capacidade" fosse taxonomia interna do
  tooling, e não a capability de negócio. Causa: distância semântica no RAG. Sintoma:
  procurar correspondência dentro do catálogo de ferramental em vez de no mapa BIZBOK.
- Regra prática: capacidade órfã de stack/verbo resolve-se contra o mapa de negócio
  (`§1` e os níveis 2), nunca inventando capability nova sem passar pela régua de
  `arq:0059` (capacidade é única na org; duplicada funde, ambígua parte — ato da mesa
  gerência `negocio`).
- Corolário BIZBOK princípio 1: sistema não é capacidade. Tela, corpo de colaborador,
  artefato de front são INSTÂNCIA que serve uma capability existente — não capability
  nova. (Ex.: jaiminho serve `mensagem-externa`; toda "tela" é `canal/exposicao` sobre
  o objeto de outra capacidade.)

## Resolução de identidade de cadeira: um ponto canônico, uma fonte (o ledger)

A tradução "nome do ator → cadeira" tem UM ponto canônico correto:
`chat/comum/cadeiras.py::sufixo_canonico`. É o único resolvedor que lê a fonte
canônica (ledger de vínculo, `registro/eventos-org.jsonl`, arq:0073) e aceita todas
as formas de entrada — sufixo, slug com prefixo, MXID/localpart e, desde #2431, o
nome humano (alias). Qualquer outro resolvedor é candidato a divergir.

- Fonte única de "quem é cadeira" é o LEDGER DE VÍNCULO, nunca um arquivo de roster
  mantido à mão. Hazard medido (fita 27/08/2026): existiam 3 resolvedores divergentes
  (`monta-sessao::_sufixo_sem_prefixo`, `fila::canoniza_persona`, `comum::sufixo_canonico`)
  e 2 fontes (ledger vs `fila/.personas`). A fonte paralela envelhece em silêncio e a
  divergência vira caixa fantasma — destinatário aceito que ninguém lê.
- Nome humano (alias) é a ÚLTIMA forma tentada, atrás de sufixo/slug/MXID reais, para
  que uma forma já válida nunca seja sequestrada. Primeiro-nome só resolve se único
  entre os aliases; homônimo exige o nome inteiro. Acento e caixa se dobram.
- Colapsar os 3 resolvedores em 1 lib compartilhada cruza venv (empacotamento) e é
  decisão canônica → do dono; adiado. Até lá, o mínimo que mata a divergência sem
  refatorar é unificar a FONTE: todo resolvedor lê o ledger (feito na fila, #2431).
- Corolário: participante (jaiminho) não é cadeira e não está no ledger de vínculo;
  fica em constante local do consumidor até a lib compartilhada existir.
