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
## O export do acervo e de todos e nao declara autoria na hora de commitar (03-04/09/2026)

`curar --apply` grava no banco E regenera `ontologia/acervo/*.jsonl` — mas no worktree
`/home/claudinho/AI/var/wt/conhecimento-main` (branch main), NAO no clone de trabalho
`platafirma-conhecimento` se este estiver noutra branch (ex.: `fabrica/NNNN-...`). Sinal do
descompasso: banco tem N arestas, export do clone de fabrica tem N-92. Rodar `exportar-acervo`
a mao no clone principal escreve na branch da fabrica (aconteceu com produto, desfeito por
force-with-lease). O commit+push e do worktree main. O banco e fonte de verdade; o jsonl e
derivado e legivel (FK resolvida para slug, uma linha por registro).

**O buraco que isso abre, e que custou trabalho manual a tres cadeiras em dois dias:** o export
regenera do Postgres INTEIRO, entao quem commita o arquivo assina o lote de quem lavrou antes e
nao commitou. `emitido_por` esta em cada registro, mas o ato de commitar nao o le. Arquiteto
montou o indice a mao, seguranca commitou so as duas linhas dele, produto levou 6 obras alheias
de carona e declarou na mensagem — tres defesas manuais do mesmo defeito e falta de ato, nao
falta de disciplina. Enquanto nao houver ato, a defesa e ler o diff antes de assinar.

**Como distinguir reescrita de remocao antes de commitar** — e o susto que faz parar: linha `-`
em `obra.jsonl` quase nunca e obra apagada, e a MESMA obra reescrita com classificacao
corrigida. Confere-se por id, nao por olho:

```sh
git diff -U0 -- ontologia/acervo/obra.jsonl | grep '^-[^-]' | sed 's/^-//' | jq -r .id | sort > /tmp/rem
git diff -U0 -- ontologia/acervo/obra.jsonl | grep '^+[^+]' | sed 's/^+//' | jq -r .id | sort > /tmp/add
comm -23 /tmp/rem /tmp/add    # vazio = zero perda; o que sair aqui e remocao de verdade
```

Vazio prova que nenhuma obra sumiu. `git diff --numstat` sozinho nao distingue os dois casos.

## Vocabulario controlado nao ganha termo para caber no mapa de quem consome (04/09/2026)

Faceta do acervo e `subdominio`, e o vocabulario dele nao e obrigado a espelhar o recorte de
nenhum consumidor. A cadeira de inteligencia pediu classificacao por quatro facetas de chapeu
(teoria/coleta/analise/marco); os subdominios instituidos sao cinco e cortam diferente — teoria
e analise colapsam em `doutrina-e-analise`, e `marco` se parte em `politica-e-estrategia` (o que
a casa quer fazer) e `marco-legal-e-controle` (o que a lei obriga).

A regua: distincao real se lavra; sinonimo do que ja existe, nao. Antes de criar termo por
pedido de consumidor, perguntar que distincao ele precisa fazer que o vocabulario atual nao faz
— a resposta costuma ser nenhuma, e o consumidor passa a ler o vocabulario existente. Duplicar
faceta por conveniencia de quem le quebra a coocorrencia e faz toda medida futura mentir.

## O dado se corta em tres camadas, nao em duas (05/09/2026)

Sempre que a pergunta for "o que e produto e o que e do dono" — publico x interno, o que
entra num pacote, o que sai num export —, a divisao binaria programa/conteudo nao fecha, e
a peca que sobra e sempre a mesma: o vocabulario controlado. As tres camadas:

- **forma** — tabelas, colunas, chaves, invariantes e as conferencias `conf_*`. Ensina
  sozinha, sem uma linha de dado dentro; e a camada de maior valor para quem instala.
- **etiquetas** — os valores fechados que os campos aceitam. Nem programa nem conteudo:
  sem elas a forma instala inteira e a busca por faceta devolve zero LEGITIMAMENTE, sem
  erro — a mesma armadilha da faceta despovoada anotada acima, agora no pior lugar
  possivel, o primeiro uso de quem acabou de instalar.
- **linhas** — as instancias (obra, conceito, aresta, trecho, evento).

Dentro das etiquetas o corte e por NATUREZA DO VALOR, e essa parte e medivel, nao de gosto:
tipologia geral do artefato (familia/especie de documento, forca, colecao — as que ja estao
ancoradas em registro formal externo) vale em qualquer casa e viaja; recorte de assunto
(dominio, subdominio, frente) e o que a casa estuda e nao viaja. Perguntar "este valor
descreve o documento ou a agenda de quem o guardou?" separa os dois sem discussao.

Dois corolarios que custaram medicao:

- **Cortar por schema e errado.** O schema `acervo` nao guarda so acervo: no mesmo lugar
  moram catalogo, vocabulario, inventario de maquina, curador, evento de recuperacao, lote
  e as tabelas de sobra de migracao. Corte por schema leva tudo isso junto sem ninguem ter
  decidido que fosse.
- **Vocabulario cuja unica fonte e o banco nao chega a instalacao nenhuma.** A cadeia
  banco -> export -> wiki so existe para quem ja tem o banco do dono. Sem semente
  versionada junto das migracoes, a camada do meio simplesmente nao existe do lado de fora
  — e e ela que faz a de cima funcionar.

## Onde mora a verdade do vocabulário, e o que fazer com o eixo que sobra (05/09/2026)

`acervo.especie_tipo` tipa **o documento** — que espécie é (paper, norma-tecnica, parecer) —, e
desde 05/09 tipa também o que a casa escreve: obra, artefato de git e página de wiki usam o mesmo
vocabulário, sem tipologia paralela (`ont:0088`). **A estrutura é outro eixo**: quais estratos a
página tem, em que ordem, e quais saem do banco em vez de serem escritos. Os dois eixos se cruzam
nos tipos que a casa produz e divergem no resto, e por isso moram em tabelas diferentes —
`especie_estrato` pendura na espécie, não a substitui. Pedido para «espelhar o estrato em
`especie_tipo`» está pedindo o eixo errado, e essa confusão já chegou duas vezes por escrito.

**A ausência tem de ser representável, senão vira lacuna.** Espécie sem estrato pode significar
duas coisas opostas — «não tem molde porque a forma é fixada fora» (adr, spec, minuta, ato
normativo) e «ainda não foi lavrada» — e sem um campo que as separe as duas são o mesmo silêncio,
que quem consome lê como falta. É o que o `forma_canonica` resolve, e a lição vale para qualquer
vocabulário que a casa sirva: onde o zero é decisão, o zero precisa de marca.

O mesmo vocabulário tem duas superfícies e uma fonte só: o **banco** é fonte,
`ontologia/acervo/*.jsonl` é **export derivado** (o cabeçalho do próprio arquivo diz isso e
proíbe edição à mão). Divergência entre os dois se fecha exportando, nunca editando o jsonl, e
reverter um commit do export não desfaz nada no banco. Corolário medido em 05/09: contagem de
espécie tirada do repo pode estar velha; a do banco não.

## Origem de conceito é derivada, e o conjunto vazio é 10% dele (05/09/2026)

Conceito não estanteia (`ont:0062`): não há coluna de domínio: a origem sai de `obra_trata_de ×
obra.dominio_id`. Duas consequências que só aparecem ao medir, e que toda regra apoiada em origem
tem de tratar antes de ser proposta:

- **A origem nasce de INGESTÃO, não de curadoria.** Fichar uma obra de outro domínio que trate do
  conceito cria o vínculo sem que ninguém tenha decidido criá-lo — não existe ato de lavratura
  onde pendurar aprovação, e regra que peça aceite por vínculo põe um humano no meio de toda
  ingestão em lote.
- **O caso vazio é grande.** Em 05/09: 510 conceitos, 96 com mais de uma origem e **52 com
  nenhuma** (10%, os nascidos por `curar` sem obra). Regra escrita como «o que vale é o conjunto
  das origens» não decide nada para eles — e conjunto vazio não é caso de borda quando é um
  décimo da base.
