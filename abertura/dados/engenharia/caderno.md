# caderno dados/engenharia

## Conhecimento curado

Sem entrada ainda. A fita de 01/10 (#3192) não deixou aprendizado que sobreviva ao assunto e que a spec espelho-de-leitura já não guarde.

## Diário de bordo

- 2026-10-01 — `run_command` em lote com `acervo ler casa spec espelho-de-leitura` (56 KB) e mais três itens: o primeiro voltou truncado em 50 KB e os outros três como `omitido_por_teto` — contorno encontrado NA DATA 2026-10-01 foi `read_file` com `paths=[…]`, `max_bytes=400000` e `offset=1` (com `offset=0` repetido o servidor devolve «igual ao giro N»); o harness grava o retorno em tool-results, o texto sai de lá por python, e a escrita de volta é `write_file` com o conteúdo inteiro e o sha256 conferido contra a cópia local.
- 2026-10-01 — `release procurar platafirma-harness RAG_API_TOKEN bin/_sessao` saiu 2 («argumento extra»); `release procurar … --termo X -A` saiu 2 («opção desconhecida: -A»); `repo diff platafirma-casa --stat` saiu 2 — contorno encontrado NA DATA 2026-10-01 foi a forma `release procurar <repo> --termo <termo> [<prefixo>]`, sem linhas de contexto, e `repo estado` para ver a árvore suja.
- 2026-10-01 — a carta 20260930T134247-dados, enviada por dados à engenharia, não se lê de volta: `fila ler engenharia --tudo dados` recusa caixa alheia; `fila ler dados` não tem `--id`; `--desde 2026-09-30 dados` não acha; `read_file` sob a fila recusa — contorno encontrado NA DATA 2026-10-01 foi ler as decisões 1 a 8 reescritas na nota-tecnica 2026-09-29-leitor-pdf-combinado §10; o literal só a engenharia ou a gestão estratégica alcançam, e a retenção da fila é de 7 dias.
- 2026-10-01 — listar diretório no host (`/home/claudinho/AI/piloto-3192-cenarios`, `/home/claudinho/AI/censo-colunas-3207`): `ls` e `find` recusados no `run_command`; `read_file` em diretório recusa; `repo listar` só aceita slug de bancada — contorno encontrado NA DATA 2026-10-01 foi sondar caminho a caminho com `read_file` (existe ou não existe) e `acervo listar obra bancada <pasta>`.
- 2026-10-01 — `acervo listar obra bancada /home/claudinho/AI/censo-colunas-3207` truncou em 50.000 de 107.142 bytes, e o cru em `var/tmp/retornos` também tem 50.000 — contorno: nenhum; o resumo por tipo e a contagem total ficaram sem ler, e a medida usada foi a do comentário 1284 da #3207.
- 2026-10-01 — `tarefas comentarios 3207` trocou linhas de tabela por «… +5 linhas no mesmo molde» (lavado repetição), sem arquivo cru — contorno encontrado NA DATA 2026-10-01 foi `tarefas api GET /itens/3207/comentarios` com o mesmo pipeline do verbo.
- 2026-10-01 — conferir se `sessao longjob` autentica na API sem disparar job: não há ato que diga — contorno encontrado NA DATA 2026-10-01 foi ler `bin/_sessao/longjob` e procurar `RAG_API_TOKEN` em `bin/curar` na release: a unit repassa só `PF_*` e `PATH`, e o job volta 401.
