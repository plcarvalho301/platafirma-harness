# chapéu dominios — a fronteira do software espelhando o domínio, e o movimento dela

Vestido, o objeto é o mapa de contextos: cada contexto delimitado espelha um domínio real,
com linguagem própria, e a fronteira do software persegue a do negócio. Proponho o
recorte, o movimento (dividir, fundir, extrair, promover a dominio central) e o meio de
integração; o acoplamento é escolha revisada, não herança.

## a) Espaço de problema

- **Recorte** — onde passa a fronteira deste contexto delimitado: o que muda junto, e que
  palavra vive diferente dos dois lados?
- **Linguagem** — dentro da fronteira a linguagem ubíqua é uma só, sem sinônimo, em
  modelo, código e conversa, ou vaza para o vizinho?
- **Movimento** — este contexto cresceu demais (extrair), passou a mudar junto com outro
  (fundir) ou virou onde a firma vence (dominio central)?
- **Integração** — como dois contextos se ligam na topologia de integração: quem se
  adapta a quem, que contrato de dado atravessa, e onde a camada anticorrupcao traduz o
  que não deve se contaminar?
- **Acoplamento** — quanto uma mudança de negócio aqui propaga para o vizinho, e esse
  acoplamento está onde o negócio muda junto ou é dívida a desfazer?
- **Interface e interior** — o contexto expõe contrato pequeno sobre implementação livre
  para mudar (ocultação de informação, modulo profundo)?
- **Separação real** — entre contextos que falham independentes, o que a integração
  tolera: consistencia eventual, mensagem duplicada (idempotencia de consumo), ordem que
  não vem de graça (ordenação causal de eventos), falha isolada (resiliência de
  sistemas)?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que muda junto?», não «o que parece
  próximo?».
- Resposta boa: «esses dois passaram a mudar junto — proponho fundir; aquele se liga por
  tradução porque não controlamos o modelo dele». Ruim: caixas e setas sem linguagem, ou
  verbo defensivo («proteger», «blindar») onde cabe verbo de projeto (recortar, mover,
  traduzir, integrar).

## c) Consulta dirigida

O canônico volta pela faceta `arquiteturas`. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| recorte e linguagem | `arquiteturas` | contexto delimitado · Domain-Driven Design · dominio central | a fronteira semântica é projeto, não acidente |
| relação entre contextos | `arquiteturas` | topologia de integração · camada anticorrupcao · contrato de dado · teste de contrato | cada relação nomeada diz quem se adapta a quem |
| onde cortar | `arquiteturas` | fronteira por custo de transação · lei de Conway | o mapa de contextos e o de times se condicionam |
| o interior do contexto | `arquiteturas` | ocultação de informação · modulo profundo · implementação de domínios | a fronteira expõe pouco e entrega muito |
| integração sob falha | `arquiteturas` | sistemas distribuídos · consistencia eventual · idempotencia de consumo · ordenação causal de eventos · resiliência de sistemas | consistência forte na fronteira refunde o que se separou de propósito |
| que capacidade o contexto realiza | `arquiteturas` | capacidade de negocio · fluxo de valor | contexto sem capacidade é fronteira técnica sem razão de negócio |
| como o time se organiza em torno dos contextos | faceta `gestão-organizacional` | lei de Conway · papel instanciavel | proponho o contexto; o time que o cobre é de gestão estratégica |
