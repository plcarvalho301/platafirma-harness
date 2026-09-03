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

## A teia cresce por `curar --relacionar` (dono, 03/09/2026)

Aresta entre conceitos se lavra pelo verbo, nunca por SQL avulso: `curar --relacionar <de> <para>
--tipo --garantia --motivo [--lastro]` é plano seco (conferências SQL com a aresta dentro, no
servidor; HermiT com a aresta em memória, no cliente); `--apply` grava com `curador = cadeira` e
regenera o export no clone de conhecimento em `main` — commit é de quem lavrou. Cartilha:
`--relacionar --help` e guia §4.5. Regras cravadas: pai de navegação fica na coluna, 2º pai na
tabela; pai e lateral no mesmo par é recusado; aresta cruzando domínio lavra a cadeira do `de`.
Fila `ont:0080` zerada em 03/09 (14 reparos caso a caso, `colheita/2026-09-03-reparo-…sql`);
`conf_conceito_generica_categoria` (041) acusa em SQL o que o HermiT tornaria insatisfazível.
Motor: `vizinhos()` lê `conceito_aresta` (1 salto, sem encadear, sem devolver quem já está na
pergunta) e `expandir()` sobe também pelo 2º pai. O bloco sai em `ontologia.vizinhanca` da
resposta — ligado pelo dono em 03/09 (`VIZINHANCA_DIRIGIDA=5`), fora do ranking por construção.
Órfão (conceito sem obra) não tem dono: qualquer cadeira que o reconheça liga ao seu domínio,
2º pai permitido sem negociar — e órfão com dois pais é sinal de ambiguidade, fila de fusão.
