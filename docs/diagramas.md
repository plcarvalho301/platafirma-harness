# Diagramas

Toda figura do harness mora em `diagramas/`, na raiz, sem subpasta: recorte vai no nome do
arquivo. A régua de forma é `acervo ler casa padrao diagramas`; a do nome do render, a ADR de
morada do que o repositório versiona (`acervo ler casa adr arq:0042`). O instrumento que otimiza e cruza diagramas mora em
`tooling/diagramas/`, não aqui.

## Nome e render

- Nome: `<assunto>[-<recorte>].<ext>`, kebab-case, sem prefixo de repositório e sem data.
- Render leva o nome completo da fonte mais `.svg`: `topologia-estratos.d2` rende
  `topologia-estratos.d2.svg`.

Regenerar, de dentro de `diagramas/`:

```
d2 <fonte>.d2 <fonte>.d2.svg
npx -y @mermaid-js/mermaid-cli -i <fonte>.mmd -o <fonte>.mmd.svg
```

## Índice

| diagrama | mostra | fonte |
|---|---|---|
| `posse-de-mensagem.mmd.svg` | posse e leitura de mensagem na fila | `posse-de-mensagem.mmd` |
| `topologia-camadas.d2.svg` | camadas da plataforma | `topologia-camadas.d2` |
| `topologia-estratos.d2.svg` | estratos da plataforma | `topologia-estratos.d2` |
| — | atos do motor sobre trilho (sem render) | `motor-atos-sobre-trilho.mmd` |
