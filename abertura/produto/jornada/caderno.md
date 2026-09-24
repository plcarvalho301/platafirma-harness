2a CONHECIMENTO CURADO (jornada)
(sem entradas)

2b DIARIO DE BORDO (jornada)
- 2026-09-24 — tentei `acervo ler spec rotinas-e-ciclos`, deu "particao 'spec' desconhecida" — contorno encontrado NA DATA 2026-09-24 foi `acervo ler casa spec rotinas-e-ciclos` (a particao vem antes da especie).
- 2026-09-24 — tentei `mesa anota "<texto>"`, deu "slot invalido"; tentei `mesa item "<texto>"`, deu "--ato e --alvo sao obrigatorios" — contorno encontrado NA DATA 2026-09-24 foi `mesa item <chapeu> --ato <...> --alvo <...>` (e `mesa anota <chapeu>` com o texto por stdin).
- 2026-09-24 — tentei `repo ramo platafirma-casa 3120`, deu "fabrica/3120 already used by worktree" (worktree de outra cadeira); tentei nome livre `3120-rotinas-rev2`, o ramo subiu mas `repo commitar` recusou "ramo pertence a outra cadeira" — contorno encontrado NA DATA 2026-09-24 foi `repo git branch -m produto/<slug>` e apagar o ramo remoto orfao; depois, `repo ramo <repo> <card> --slug <slug>` (fabrica/<card>-<slug>).
- 2026-09-24 — `repo ramo` criou o ramo de um origin/main velho (sem fetch depois de um merge da mesma fita); o arquivo lido era a rev anterior — contorno encontrado NA DATA 2026-09-24 foi `repo git fetch origin` + `repo git reset --hard origin/main` antes de editar.
- 2026-09-24 — merge em main do platafirma-casa (PRs #10 e #11) nao disparou a ingestao prevista em arq:0115 8.1; `acervo ler casa` seguia servindo a revisao anterior — contorno encontrado NA DATA 2026-09-24 foi `acervo ingerir casa platafirma-casa --apply` na mao, depois de cada merge.
- 2026-09-24 — `descobrir "recuperação por identidade"` voltou "sem concessao para acervo:*" — contorno encontrado NA DATA 2026-09-24 foi `motor rag buscar casa "<termo>"` e depois `acervo ler casa <especie> <chave>`. (dono: descobrir foi absorvido; nao usar.)
- 2026-09-24 — `mesa caderno <chapeu>` so le; nao ha ato que escreva caderno — contorno encontrado NA DATA 2026-09-24 foi editar abertura/produto/<chapeu>/caderno.md no platafirma-harness por ramo caderno/produto/* e PR.
