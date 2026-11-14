# Arquitetura de domínios

Entidade: chapeu

## Espaço de problema

- O que muda junto, e que palavra vive diferente dos dois lados da fronteira?
- Onde passa a fronteira deste contexto delimitado, e ela se justifica pela linguagem e pelo que muda junto, ou por conveniência técnica?
- Dentro da fronteira a linguagem é uma só, sem sinônimo, em modelo, código e conversa, ou vaza para o vizinho?
- Este contexto cresceu demais e pede extrair, passou a mudar junto com outro e pede fundir, ou virou dominio central, onde a firma vence?
- Na topologia de integração, que partes se ligam, quem se adapta a quem, e onde a camada anticorrupcao traduz o que não deve se contaminar?
- Quanto uma mudança de negócio aqui propaga para o vizinho, e esse acoplamento está onde o negócio muda junto ou é dívida a desfazer?
- Entre contextos que falham independentes, o que a integração tolera: consistencia eventual, mensagem duplicada (idempotencia de consumo), ordem que não vem de graça (ordenação causal de eventos)?

## Régua de resposta

Resposta boa propõe o movimento e o meio de integração com o motivo: esses dois passaram a mudar junto e se fundem; aquele se liga por tradução, porque a firma não controla o modelo dele.

Resposta ruim desenha caixas e setas sem linguagem, ou usa verbo defensivo, como proteger e blindar, onde cabe verbo de projeto: recortar, mover, traduzir, integrar.

## Consulta dirigida

- Recorte e linguagem: Evans, Domain-Driven Design, na parte de projeto estratégico, e Khononov, Learning Domain-Driven Design.
- Relação entre contextos: Khononov, no capítulo de integração de contextos delimitados, traz o mapa de contextos e os padrões de cooperação.
- Onde cortar: a busca vai por fronteira por custo de transação e lei de Conway.
- Integração sob falha: a busca vai por sistemas distribuídos, consistencia eventual, idempotencia de consumo e ordenação causal de eventos.
- Que capacidade o contexto realiza: a busca vai por capacidade de negocio e fluxo de valor; contexto sem capacidade é fronteira técnica sem razão de negócio.

## Rótulos de busca

- rótulos: contexto delimitado · Domain-Driven Design · dominio central · topologia de integração · camada anticorrupcao · lei de Conway · consistencia eventual · idempotencia de consumo · ordenação causal de eventos · resiliência de sistemas
- recorte de domínio: arquiteturas · gestao-organizacional
- homônimos: domínio, que fora deste ramo é o domínio do acervo, a prateleira em que a obra mora · contexto, que fora dele é a janela de contexto do modelo
