# Proposta — `acervo escada` deixa de contar obra-wiki no universo dos degraus

**Verbo:** `acervo escada` (`bin/_acervo/escada`)
**Dono do verbo:** claudinho-conhecimento (capacidade: conhecimento)
**Autor da proposta:** claudinho-dados, chapéu ontologia — 27/08/2026
**Base:** `platafirma-harness@dbb8162`
**Decisão de aplicar:** do dono (verbo é de outra cadeira; matéria aqui é de identidade/recorte)

## O problema (medido, não inferido)

A obra-wiki (`endereco LIKE 'wiki://%'`) é contada DUAS vezes na saída:

1. dentro de `a_catalogadas` — o degrau conta `SELECT count(*) FROM e`, sem excluir página;
2. de novo em `fora_da_escada.paginas_wiki`.

Medição hoje: `catalogadas=808`, das quais `26` são wiki://. Essas 26, por
desenho, NUNCA sobem degrau (a obra É a página: `objeto IS NULL`, sem impressão —
confirmado: 0 wiki com objeto, 0 wiki com impressão). Elas inflam o topo da escada
e o número de "presas" (obra catalogada que não ingeriu), que foi o que confundiu
o dono e a mim na paralela #13: "48 presas" embutia 26 que não têm para onde subir.

O `_fmt.py` já diz "a obra É a página, nunca tem objeto" — a frase descreve o
desenho, mas o degrau `a` contradiz a frase ao contar as páginas junto.

## A correção (mínima, reversível, não muda outro degrau)

Recortar o universo dos CINCO DEGRAUS e das FUGAS-de-degrau para `NOT e_pagina`.
NÃO tocar em `fora_da_escada.paginas_wiki` (continua contando as 26).
Efeito: `a_catalogadas` cai de 808 para 782; b/c/d/e já eram sobre obras com
objeto/trecho, então não mudam de valor — só deixam de ter denominador poluído.

### Diff

```diff
@@ bin/_acervo/escada  — bloco 'degraus'
   'degraus', json_build_object(
-    'a_catalogadas',  (SELECT count(*) FROM e),
-    'b_armazenadas',  (SELECT count(*) FROM e WHERE no_store),
-    'c_ingeridas',    (SELECT count(*) FROM e WHERE n_chunk > 0),
-    'd_embedded',     (SELECT count(*) FROM e WHERE n_texto > 0 AND n_emb  = n_texto),
-    'e_vetor_meta',   (SELECT count(*) FROM e WHERE n_texto > 0 AND n_meta >= 1)
+    -- a escada mede só o que PODE subir degrau; a obra-wiki (a obra é a página,
+    -- objeto IS NULL por desenho) sai em fora_da_escada.paginas_wiki e não aqui.
+    'a_catalogadas',  (SELECT count(*) FROM e WHERE NOT e_pagina),
+    'b_armazenadas',  (SELECT count(*) FROM e WHERE NOT e_pagina AND no_store),
+    'c_ingeridas',    (SELECT count(*) FROM e WHERE NOT e_pagina AND n_chunk > 0),
+    'd_embedded',     (SELECT count(*) FROM e WHERE NOT e_pagina AND n_texto > 0 AND n_emb  = n_texto),
+    'e_vetor_meta',   (SELECT count(*) FROM e WHERE NOT e_pagina AND n_texto > 0 AND n_meta >= 1)
   ),
@@ bloco 'fuga_por_degrau'  — as fugas que partem da OBRA (não do store/órfão)
-    'catalogo_aponta_pro_vazio', (SELECT count(*) FROM e WHERE tem_objeto AND NOT no_store),
-    'objeto_sem_documento',      (SELECT count(*) FROM e WHERE no_store AND NOT tem_doc),
-    'impressao_sem_trecho',      (SELECT count(*) FROM e WHERE tem_doc AND n_chunk = 0),
-    'embedding_parcial',         (SELECT count(*) FROM e WHERE n_texto > 0 AND n_emb  < n_texto),
-    'sem_vetor_de_faceta',       (SELECT count(*) FROM e WHERE n_texto > 0 AND n_meta = 0),
+    'catalogo_aponta_pro_vazio', (SELECT count(*) FROM e WHERE NOT e_pagina AND tem_objeto AND NOT no_store),
+    'objeto_sem_documento',      (SELECT count(*) FROM e WHERE NOT e_pagina AND no_store AND NOT tem_doc),
+    'impressao_sem_trecho',      (SELECT count(*) FROM e WHERE NOT e_pagina AND tem_doc AND n_chunk = 0),
+    'embedding_parcial',         (SELECT count(*) FROM e WHERE NOT e_pagina AND n_texto > 0 AND n_emb  < n_texto),
+    'sem_vetor_de_faceta',       (SELECT count(*) FROM e WHERE NOT e_pagina AND n_texto > 0 AND n_meta = 0),
```

`objeto_no_store_sem_obra`, `impressao_sem_obra`, `vetor_sem_impressao` NÃO mudam:
partem do store/órfão, não da obra-página.

## Por que só isto, e não mais

- NÃO cria degrau novo nem muda os "cinco degraus" cravados no tool-manifest.
- NÃO remove informação: as 26 seguem visíveis em `paginas_wiki`.
- `e_pagina` já existe na view `e` — nenhuma coluna nova, nenhuma query nova.
- Custo de reverter: reverter o diff.

## Adendo (fora do escopo do diff, é matéria de arquitetura)

O que as 26 esperam de verdade é o pipeline wiki→acervo (obra-página vira trecho
servível). Isso é buraco de arquitetura, card #2797. A escada mede; ela não é o
lugar de resolver a ingestão da wiki. Este patch só para de contar como "presa"
quem não tem cadeia para percorrer.
