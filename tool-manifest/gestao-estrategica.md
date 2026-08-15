# tool-manifest — claudinha-gestao-estrategica

Forma em `tool-manifest/TEMPLATE.md`.

Verificação: `[exec]` executado · `[func]` usado em trabalho real ·
`[inst]` presente, sem prova.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/TODA-CADEIRA.md`.

## Verbos próprios

```
escrita das personas            : persona abrir | conferir | salvar -m "<msg>"
abrir cadeira                   : persona prover <cadeira> [--alias "<Nome>"]
dar/tirar gerência              : persona designar | dispensar <cadeira> <gerência>
migrar competência              : persona remover <gerência> <de> <para>
suspender / reabrir             : persona afastar <cadeira> --gatilho "<cond>" | reverter <cadeira>
encerrar cadeira                : persona desligar <cadeira> --motivo "<txt>"
estado atual, por replay        : persona foto
a série datada                  : persona filme [cadeira]
```

Vocabulário emprestado do `dom_tipo_evento` do mdm-rh: a cadeira é o vínculo, a gerência
é a função. Ledger append-only em `personas/eventos-org.jsonl` — **não se edita**: erro
se corrige com evento novo, como no golden source de RH. `--em AAAA-MM-DD` é a data do
FATO, não a da digitação; `--autor` responde quem decidiu.

## Conectores

## Armadilhas medidas

- **`tarefas api` resolve `/tasks/<n>` por `id`, não por `#index`.** `PUT
  /tasks/<index>/labels` devolve 404; o id é a chave. Vale para a API crua — o
  verbo `tarefas ler` aceita os dois (`<id>` e `#<index>`).
- **Corpo errado em `PUT .../labels` devolve 200 sem aplicar nada.** Sem
  `{"label_id":<n>}` no corpo, a resposta é `{"label_id":0}` e sai com sucesso.
  Conferir com `tarefas ler` depois de rotular, sempre.
- **Mover card entre colunas do Kanban não se confirma por leitura.** A coluna é
  do view, não do card: `GET /tasks/<id>` devolve `bucket_id: 0` mesmo depois de
  mover, e `GET /projects/<p>/views/<v>/buckets` devolve os buckets com `tasks`
  vazio e `count: 0`. A única confirmação disponível é a resposta da escrita —
  `POST /projects/<p>/views/<v>/buckets/<b>/tasks` com `{"task_id":<id>}` devolve
  o objeto `bucket` com o `count` já incrementado. Movimento que não mudou nada
  (card já naquela coluna) devolve `bucket: null` com o `task_id` ecoado: é no-op,
  não falha. Medido em 12/08/2026 sobre o projeto 46; conferido no Kanban pelo dono.
- **Os buckets do projeto 46 são do view 203** (Kanban): Backlog 174, Ready 206,
  Doing 175, Completed (fábrica) 207, Done 176. Os outros três views (List 200,
  Gantt 201, Table 202) não têm bucket e não aceitam esse POST.
- **Reparentar card não remove o pai anterior.** `tarefas sub <novo-pai> <filho>`
  acrescenta a relação; o pai velho continua, e o card aparece nos dois lugares.
  Remover é chamada própria: `tarefas api DELETE /tasks/<filho>/relations/parenttask/<pai-velho>`.
  Conferir com `jq '.related_tasks.parenttask'` depois, sempre.

## Pendências declaradas

- Seção `## Conectores` ainda vazia: nenhuma tool de conector foi verificada por
  esta cadeira com prova de uso.

## Minuta — deliberação entre cadeiras

`minuta ler` · `escrever` · `circular` · `formalizar`, no manifesto comum
(`tool-manifest/TODA-CADEIRA.md`). Verbo de toda cadeira; dona da matéria:
claudinha-gestao-estrategica. **Nunca é leitura automática** — só roda chamada,
por ping `tipo: minuta` na caixa ou ordem do dono. Protocolo:
`platafirma-arquitetura/minutas/PROTOCOLO.md`.
