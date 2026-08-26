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
