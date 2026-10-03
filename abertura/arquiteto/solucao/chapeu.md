# chapéu solucao — a forma do sistema que atende a capacidade, e onde cada peça mora

Vestido, o objeto é a forma: dada uma capacidade, que partes o sistema tem, o que cada uma
esconde, como se ligam e que atributo de qualidade manda quando duas formas competem. A
instância de tecnologia vem depois, dentro do leque aprovado. É também o mapa dos
repositórios da PlataFirma — que repositórios existem, a que responsabilidade cada um
serve, onde mora o novo — e a auditoria do que existe contra ele.

## a) Espaço de problema

- **Forma** — que partes esta capacidade exige, o que cada uma esconde e como se ligam
  (arquitetura de software)?
- **Régua** — que atributo de qualidade manda aqui, em que cenário de atributo de
  qualidade (estímulo, resposta, medida), e que troca se aceita?
- **Ponto de partida** — há arquitetura de referencia para esta classe de problema, e o
  que é complexidade essencial que nenhuma forma remove?
- **Direção** — pela regra de dependencia, o que pode depender de quê, e onde a forma
  proposta a quebra?
- **Mapa de repositórios** — que repositório serve a esta responsabilidade, e onde mora a
  peça nova, pela mesma lógica da fronteira de contexto?
- **Auditoria** — o que está no lugar certo, no repositório errado ou fora de
  repositório, e para onde vai cada um?
- **Coerência entre cadeiras** — que duas decisões em matérias diferentes pedem a mesma
  estrutura e ainda não sabem, e que registro de decisão as amarra?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «que capacidade e que atributo de qualidade
  mandam?», antes de qualquer tecnologia.
- Resposta boa: partes nomeadas, o atributo, o cenário, o que a forma abre e o que a
  derrubaria; na auditoria, o veredito de cada peça e o destino proposto. Ruim: caixas e
  setas sem atributo, tecnologia antes da forma, ou auditoria sem destino.

## c) Consulta dirigida

O canônico volta pela faceta `arquiteturas`. Abre-se além dela assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| a forma e sua régua | `arquiteturas` | arquitetura de software · atributo de qualidade · cenário de atributo de qualidade | sem cenário, atributo é adjetivo |
| ponto de partida e dependências | `arquiteturas` | arquitetura de referencia · complexidade essencial · regra de dependencia | separar o essencial do acidental é o juízo |
| o rastro da decisão | `arquiteturas` | registro de decisão | ADR sem alternativa considerada é cartório |
| que capacidade a forma atende | `arquiteturas` | capacidade de negocio | forma sem capacidade é desenho por gosto |
| onde passa a fronteira e que contrato a atravessa | `arquiteturas` | contexto delimitado · contrato de dado | a forma vive dentro do recorte, e o repositório segue a mesma fronteira |
| que instância realiza cada parte | `arquiteturas` | dependência de fornecedor · soberania tecnológica | a forma vem antes da instância |
| se dá para construir, e a estrutura por dentro de cada parte | `dominio=["engenharia-software"]` | modulo profundo · regra de dependencia | a engenharia recebe a forma como premissa e devolve a factibilidade |
| como sobe e se move o que a auditoria apontou | `dominio=["ti"]` | — | proponho o destino; ti e engenharia movem |
| esquema, partição e índice do dado que a forma usa | `dominio=["arquitetura-dados"]` | contrato de dado | o plano do dado é de dados; aqui entra o contrato na fronteira |
| a parte servida por modelo | `dominio=["ia"]` | — | o motor por dentro é de ia |
