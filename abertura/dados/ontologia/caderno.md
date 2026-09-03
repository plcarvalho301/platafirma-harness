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

## Domínio/subdomínio e conceito podem duplicar nome (dono, 02/09/2026)

Regra cravada pelo dono: um assunto que já é estante (`acervo.dominio` / `acervo.subdominio`)
PODE existir também como conceito em `acervo.conceito`. Corolário de `ont:0062` (estante e
tema são eixos ortogonais que se cruzam na obra); precedentes vivos: criptografia,
arquitetura-de-dados, modelagem-de-dominio×domain-driven-design, recuperacao-e-busca×
recuperacao-semantica. Coincidência de nome não é veto nem motivo: o conceito entra pela
régua de `ont:0078`, como qualquer outro.

## A palavra do dono é garantia de lavratura (dono, 02/09/2026)

Ligação ou conceito que o dono afirma existe por afirmação dele (`estatuto` instituído;
Z39.19 §5.3.5.2 chama de garantia organizacional). Contar trechos no acervo mede lastro
literário, não validade — `ont:0078`: "obra ausente da estante não veta lavratura". Reportar
"o texto não sustenta" como se fosse veto é erro medido nesta data.

## Como se mede uma aresta antes de lavrar (02–03/09/2026)

Duas fontes, nesta ordem: co-ocorrência em `obra_trata_de` (obras que tratam dos dois) e lastro
em `acervo.trecho` (busca de frase, `phraseto_tsquery('simple')` — acento não casa se buscar sem
acento). Passagem-chave só com seção-hub filtrada. A hipótese do dono não precisa de nenhuma
das duas: entra como `garantia = instituida`. Aceite de regra formal: planta o caso falso, mede
no HermiT E na conferência SQL, desfaz — os dois têm de acusar a mesma linha.
