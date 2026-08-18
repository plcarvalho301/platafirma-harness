# caderno — conhecimento (claudinho-dados)

## Carga de acervo

- Carga de acervo é **rotina, não vira card** (dono, 18/08/2026). A régua "artefato
  durável vira card" não basta: o corte é rotina × mudança. O que o acervo faz toda
  semana é operação, e o board não a rastreia.
- **Ler o board antes de disparar job de ingestão.** Em 18/08 disparei `ingest corpus`
  com o #280 aberto dizendo exatamente para não fazer isso; custou reembed de 92.189
  trechos onde 2.207 bastavam.

## Sequência que funciona para lote novo (contorno, enquanto #283 não fecha)

O verbo `acervo ingerir <raiz> --apply` **recusa** lote novo por desenho: ele faz
`mv` do inventário sobre o manifest, e a raiz canônica (`Firma/...`) não existe mais
em disco — os objetos vivem no MinIO. Inventário menor que manifest → recusa.

```
1. rclone copy → ~/AI/entrada/Firma/<leva>/     (o bucket sai do path: Firma/ → acervo)
2. sha256sum + mc ls pf/{acervo,pessoal}/<sha>  (duplicata por conteúdo)
3. pdftotext -l 20 | wc -c                      (scan sem camada de texto → OCR antes)
4. cp acervo/manifest.jsonl acervo/manifest.jsonl.bak-<data>
5. inventario-acervo.py <raiz> | jq select(path_origem) >> manifest   (APPEND, nunca mv)
6. ingerir-acervo.py <raiz> manifest ; fila-acervo.py
7. cli carregar-acervo --apply
8. UPDATE objeto/arquivo — carregar-acervo NÃO os preenche (ver abaixo)
9. cli materializar-acervo <dir> --apply
10. cp só os PDFs do lote para dir isolado ; cli ingest <dir isolado>   ← o passo que importa
11. cli embed ; cli sincronizar-acervo --apply ; cli embed-meta
```

O passo 10 é o que separa carga barata de estrago: `ingest` sobre o corpus inteiro
re-extrai tudo, porque `abrir_impressao` não é idempotente. Cada re-extração aposenta
a impressão que servia e abre outra, sem vetor — e o `embed`, que não é escopável,
varre todo trecho servindo sem vetor.

## Armadilhas medidas em 18/08/2026

- **`carregar-acervo` cria obra só com titulo/endereco/colecao.** `objeto` e `arquivo`
  ficam NULL, e sem `objeto` o `materializar-acervo` não baixa nada. Reparo:
  `UPDATE acervo.obra SET objeto = replace(endereco,'minio://','')`.
- **`materializar-acervo <dir>` não é escopável.** O destino é só onde escreve; baixa o
  acervo inteiro (760 arquivos para 6 obras).
- **`mesa anota <chapeu>` REESCREVE o slot inteiro.** Item com ato pendente é
  `mesa item <chapeu> --ato ... --alvo ...`. `anota` é prosa do substrato velho.
- **Escada: degrau `d` é `n_emb = n_texto`, uma igualdade.** Queda de `d` significa o
  lado do texto subindo (impressão nova sem vetor), NÃO vetor apagado. Ler queda de `d`
  como perda de dado é erro de leitura — foi o meu.

## Triagem antes de ingerir

`pdftotext -l 20 <f> - | wc -c` — abaixo de ~1.000 caracteres em 20 páginas é scan puro.
Ingerir produz obra com zero trecho elegível, que é o buraco do item #40 da mesa.
