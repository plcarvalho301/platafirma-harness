# ferramental — TI/construcao (L2)

Desenho de construção e pipeline; interlocução com a fábrica.

- `jaiminho perguntar|continuar|estado|logs` — agente externo, alcance pelo PEP.
- `jaiminho-fabrica <mesmos atos>` — 2ª conta da fábrica (org:0020), papel fornecedor.
- `acervo ingerir <raiz> [--planilha x.ods] [--apply]` — ingestão de obra em lote.
- `conferir servico|verbo|skill|repo|peca|sessao|superficie|commit|chapeu` — gates.
- `yamllint` — lint de YAML de pipeline/compose.

## Ambiente
- `export PF_CADEIRA=TI`.
- Aceito a entrega da fábrica no chapéu devsecops: back, infra, pipeline, engine.

## Armadilhas de uso
- A fábrica é bloqueada pelo PEP em `docker*`, `systemctl*`, `psql*`, `deploy*`,
  `abertura/*` (persona, chapéu, ferramental, conduta) — teste de banco e deploy são meus.
