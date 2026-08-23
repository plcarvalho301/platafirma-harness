# ferramental dados/ontologia

## Em todo giro

| chamo | quando |
|---|---|
| `acervo listar conceitos` | antes de nomear qualquer entidade, tipo ou rótulo — é o golden record de `acervo.conceito`; rótulo dito de memória casa zero na (b) do chapéu |
| `motor rag buscar "<rótulos inteiros da (b)>" --texto trecho` | antes de afirmar de memória o conteúdo de um conceito de modelagem — rótulo inteiro no texto (senão casa zero), e `--texto trecho` (com `secao` volta `texto: null`) |

## Armadilhas de ferramenta medidas aqui

- **`--conceito` não confirma existência** — parece que buscar `motor rag buscar --conceito <slug>` valida se o conceito existe; é busca semântica que devolve o MESMO resultado para slugs reais e inventados, com cobertura fraca e sinal abaixo do piso. Sinal: três slugs distintos devolveram o mesmo hit (Frege), `sim 0.537 < piso 0.55`. Existência se confere em `acervo listar conceitos`, não aqui. (23/08)
