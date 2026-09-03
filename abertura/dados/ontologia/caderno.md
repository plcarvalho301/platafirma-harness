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

## O que a teia mede é a ficha do livro, não o assunto (parecer da rodada geral, 03/09/2026)

Cruzamento de estante, isolamento de domínio e "livros em comum" leem `obra_trata_de` — a ficha que
alguém escreveu à mão (1,6 conceitos por livro). Estante que sai "fechada" na medida (IA, 03/09) é
ficha rala, não assunto fechado: o conceito implícito (o harness em Python, a memória em Postgres,
o javascript do livro de interface) não está na ficha. Antes de afirmar isolamento, conferir a
ficha; o remédio mecânico é refletir estante e subestante em conceito e espalhar por
`curar --reclassificar --de-dominio X --trata-de X` (dono, avenida 6) — e, feito isso, descontar os
conceitos de estante ao medir coocorrência, senão toda ligação parece sustentada. "Consistente" no
HermiT com `filhos_exclusivos` = 0 e 4 `disjunta` não prova nada: ninguém afirmou o que pudesse
falhar. Ligar por garantia instituída é o natural antes de haver uso medido; garantia de uso só
nasce quando o registro de busca guardar os conceitos declarados por pergunta (hoje guarda só o
texto).

## Apelido é de um conceito só (Z39.19 §6.2.2 e §8.2; dono, 03/09/2026)

Termo mais amplo não lista o mais estreito como sinônimo — se o filho existe como conceito, o nome
é dele (governo eletrônico era apelido de governo digital e vice-versa; "API" em
contratos-de-interface; "dense retrieval" em recuperacao-semantica). Homonímia não some: cada
apelido ganha qualificador ("kernel (estratégia)" × "kernel (sistema operacional)"). Conferência:
`SELECT lower(rotulo) FROM acervo.conceito_rotulo GROUP BY 1 HAVING count(DISTINCT conceito_id) > 1`
vazia. Primeiro pai hierárquico vai na coluna; enquanto `curar` só escrever a tabela (#2983), o
primeiro pai sobe por SQL registrado em `ontologia/colheita/` e o motivo fica no export em git.

## Lavrar do TSV de coocorrência: título truncado e lastro por UUID (03/09/2026)

Ao lavrar arestas em lote a partir de `var/tmp/teia-parecer/pares-coocorrentes-sem-aresta.tsv`
(avenida 1), dois mordem:
- **O TSV traz o título da obra TRUNCADO** (ex.: "...Using L"). `curar --relacionar --lastro`
  recusa match aproximado — devolve "casou só aproximado com <uuid> (...)" e NÃO grava. Título
  curto que casa EXATO passa (ex.: "Accelerate: State of DevOps 2018"); título longo truncado
  falha. Remédio: puxar o UUID da obra no banco (`SELECT id,titulo FROM acervo.obra WHERE titulo
  ILIKE '<prefixo>%'`) e passar o UUID no `--lastro`, não o título do TSV.
- **`grep` filtrando a saída do `--apply` engole o erro**: um loop que só faz `grep -E "^Aresta"`
  vê zero linhas e parece "nada aplicado" sem dizer por quê. Rodar UM sem filtro primeiro para
  ver a recusa real, depois lotear.

## curar --relacionar regenera o export no WORKTREE main, não no clone corrente (03/09/2026)

`curar --relacionar --apply` grava no banco E regenera `ontologia/acervo/conceito_relacao.jsonl`
— mas no worktree `/home/claudinho/AI/var/wt/conhecimento-main` (branch main), NÃO no clone de
trabalho `platafirma-conhecimento` se este estiver noutra branch (ex.: `fabrica/NNNN-...`).
Sinal do descompasso: banco tem N arestas, export do clone de fábrica tem N-92. O commit+push é
do worktree main: `cd var/wt/conhecimento-main; git add ...jsonl; git commit; git push origin main`.
O banco é fonte de verdade; o jsonl é derivado e legível (FK resolvida para slug, sem uuid, uma
linha por registro) — `git diff --numstat` confirma que o apply só adicionou (N insertions, 0
removals) antes de commitar.
