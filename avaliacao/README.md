# avaliacao

Instrumentos e dados de avaliação do harness. Antes deste diretório, viviam
soltos em `~/AI/` fora de controle de versão — o conjunto rotulado que dá
comparabilidade entre ondas de medição era o único artefato do stack sem
rastreabilidade própria.

- `gold-set/` — conjunto rotulado: perguntas, gabaritos e o manifesto do acervo
  contra o qual foram escritos. `fase-b/` e `coleta/` são material por cadeira.
- `rag-medicao/` — protocolo da escada de ablação e as sondas de linha de base
  (T0).

Método e protocolo canônicos: `platafirma-conhecimento/rag/docs/protocolo-medicao.md`
e `rag/docs/gold-set-firmabot.md`. Este diretório guarda os dados; aquele, a regra.

`~/AI/gold-set` e `~/AI/rag-medicao` são symlinks para cá — os caminhos antigos
seguem válidos.
