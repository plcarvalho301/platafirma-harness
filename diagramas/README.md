# diagramas/ — morada única do desenho neste repositório

Todo diagrama da PlataFirma mora em `diagramas/` na raiz do repositório que o
publica. Não há figura em `docs/` nem em subpasta de assunto.

## Regra

- **Um diretório, sem subpasta.** Recorte vai no nome do arquivo, não em pasta.
- **Nome:** `<assunto>[-<recorte>].<ext>`, kebab-case, sem prefixo de repositório
  e sem data.
- **Render leva o nome completo da fonte mais `.svg`** (`arq:0042`, norma do
  arquiteto de 09/08/2026): `topologia-estratos.d2` rende
  `topologia-estratos.d2.svg`. O nome-base do render deriva do arquivo-fonte
  inteiro, não do radical — colisão impossível com qualquer número de geradores.
- **Regeneração**, chamada de dentro de `diagramas/`:
  - `d2 <fonte>.d2 <fonte>.d2.svg`
  - `npx -y @mermaid-js/mermaid-cli -i <fonte>.mmd -o <fonte>.mmd.svg`
- **Índice obrigatório:** diagrama novo entra na tabela abaixo no mesmo commit.
- **Instrumento não mora aqui**: `tooling/diagramas/`.

Régua de forma: `platafirma-arquitetura/design/diagramas.md`.

## Índice

| Diagrama | Mostra | Fonte |
|---|---|---|
| `posse-de-mensagem.svg` | Posse e leitura de mensagem na fila | `.d2`, `.mmd` |
| `topologia-camadas.d2.svg` | Camadas da plataforma | `topologia-camadas.d2` |
| `topologia-estratos.d2.svg` | Estratos da plataforma | `topologia-estratos.d2` |
| `topologia-estratos.mmd.svg` | Estratos da plataforma (render Mermaid) | `topologia-estratos.mmd` |
| — | Atos do motor sobre trilho (sem render) | `motor-atos-sobre-trilho.mmd` |
