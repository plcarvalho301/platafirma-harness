# caderno — ontologia (dados)

## Ganchos de leitura (quando puxar o quê)

- **Antes de nomear entidade, tipo ou rótulo**: `acervo listar conceitos` — é o
  golden record de `acervo.conceito`. Rótulo dito de memória casa zero na (b) do
  chapéu; confere no golden record primeiro.
- **Antes de afirmar de memória o conteúdo de um conceito de modelagem**:
  `motor rag buscar "<rótulos inteiros da (b)>" --texto trecho` — rótulo INTEIRO no
  texto (parcial casa zero), e `--texto trecho` (com `secao` o retorno vem
  `texto: null`).

## Armadilhas de ferramenta medidas aqui

- **`--conceito` não confirma existência** — parece que `motor rag buscar --conceito
  <slug>` valida se o conceito existe; é busca semântica que devolve o MESMO
  resultado para slugs reais e inventados, com cobertura fraca e sinal abaixo do
  piso. Sinal: três slugs distintos devolveram o mesmo hit (Frege),
  `sim 0.537 < piso 0.55`. Existência se confere em `acervo listar conceitos`, não
  aqui. (23/08)
