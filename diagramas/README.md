# diagramas/ — morada única do desenho neste repositório

Todo diagrama da PlataFirma mora em `diagramas/` na raiz do repositório que o
publica. Não há figura em `docs/` nem em subpasta de assunto.

## Regra

- **Um diretório, sem subpasta.** Recorte vai no nome do arquivo, não em pasta.
- **Nome:** `<assunto>[-<recorte>].<ext>`, kebab-case, sem prefixo de repositório
  e sem data.
- **Render e fonte no mesmo nome-base** (`arq:0042`): `posse-de-mensagem.svg` +
  `posse-de-mensagem.d2`.
- **Sufixo de ferramenta** (`-d2`, `-mmd`) só existe enquanto dois renders do
  mesmo assunto disputam. Escolhido um, o sufixo sai.
- **Índice obrigatório:** diagrama novo entra na tabela abaixo no mesmo commit.
- **Instrumento não mora aqui**: `tooling/diagramas/`.

Régua de forma: `platafirma-arquitetura/design/diagramas.md`.

## Índice

| Diagrama | Mostra | Fonte |
|---|---|---|
| `posse-de-mensagem.svg` | Posse e leitura de mensagem na fila | `.d2`, `.mmd` |
| `topologia-camadas-d2.svg` | Camadas da plataforma | `topologia-camadas.d2` |
| `topologia-estratos-d2.svg` | Estratos da plataforma | `topologia-estratos.d2` |
| `topologia-estratos-mmd.svg` | Estratos da plataforma (render Mermaid) | `topologia-estratos.mmd` |
| — | Atos do motor sobre trilho (sem render) | `motor-atos-sobre-trilho.mmd` |
