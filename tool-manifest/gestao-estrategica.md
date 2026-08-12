# tool-manifest — claudinha-gestao-estrategica

Vazio. Preenchido pela própria cadeira, na sessão dela — forma em
`tool-manifest/TEMPLATE.md`.

Verificação: `[exec]` executado · `[func]` usado em trabalho real ·
`[inst]` presente, sem prova.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/TODA-CADEIRA.md`.

## Conectores

## Armadilhas medidas

- **`tarefas api` resolve `/tasks/<n>` por `id`, não por `#index`.** `PUT
  /tasks/<index>/labels` devolve 404; o id é a chave. Vale para a API crua — o
  verbo `tarefas ler` aceita os dois (`<id>` e `#<index>`).
- **Corpo errado em `PUT .../labels` devolve 200 sem aplicar nada.** Sem
  `{"label_id":<n>}` no corpo, a resposta é `{"label_id":0}` e sai com sucesso.
  Conferir com `tarefas ler` depois de rotular, sempre.

## Pendências declaradas
