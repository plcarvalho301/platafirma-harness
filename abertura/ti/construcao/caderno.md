# caderno — construcao (chapéu de TI)

## Lições (conhecimento curado)

- Validar PR — da fábrica OU da própria cadeira em outra fita — é medir, não confiar no relato: ler o diff inteiro contra as TRAVAS do card, e onde o card cita commit-por-passo, conferir com `repo git show <sha> --stat` que o commit muda o que diz mudar. Em 26/09 o PR 206 (desta cadeira) passava nos próprios testes e violava a trava «não apagar sem salvar»: tratava ramo ausente no origin como entregue, e ramo nunca empurrado também está ausente. O teste que faltava era o caso que a trava protege.
- Aceite que só se mede pós-deploy (métrica sobre 24h de ops log) não bloqueia o merge — declarar como pendência de medição, não como verde. Distinguir do aceite que roda agora (suíte de contrato).
- Gate de outra cadeira que vem com correção de fato: conferir a correção contra a fonte antes de aceitar, e devolver âncora onde ela erra.
- `release promover <familia>` promove a família inteira, não o commit: toda stack registrada para aquela família sobe junto. O raio de ação real só se sabe lendo o registro de stacks da família antes.
- Gatilho automático de infra (timer que decide sozinho) pede régua estreita e literal, não heurística. Vale para desempate também: sem chave, «o mais recente» por mtime escolhia pela hora do `worktree add`, não do uso — ambíguo sai 2 e pede a chave. Decide por forma comparável, nunca por inferência.
- Escrita de arquivo sem extensão pela porta (`write_file`) só é aceita dentro de `bin/` do harness (em qualquer bancada: plana, por sessão ou por cadeira e card). Fora de `bin/`, patch em var/tmp/<ordem>/*.txt + `repo git <repo> apply --recount`, ou `<nome>.txt` + `git mv`. `VERDES` se escreve direto.
- Verbo que commita em nome de uma cadeira parte de `origin/main` recém-buscado, num worktree efêmero com ramo novo por escrita — nunca do checkout de um clone, que pode estar em qualquer ramo.
- Verbo promovido no meio da fita muda o que a sessão viva vê. Promoveu verbo de bancada, roda `repo estado` e escreve no caminho que ele mostra, não no que a fita lembra.
- Mudar a resolução de bancada no `repo` muda para TODOS os leitores dela: `bin/teste`, `bin/lint` e a morada de escrita da porta (`_em_bin_do_harness`) tinham cópias próprias e ficaram para trás em 26/09 — a porta passou a recusar bin/ na bancada nova e teste/lint mediram o clone base, com aviso só em stderr. Antes de promover mudança de resolução, `repo procurar <repo> --termo bancada_de` em bin/ e a porta.
- Ao revisar peça de outra cadeira, buscar no acervo a seção que decide a questão, não a que confirma a hipótese. Vale para a própria parada: em 26/09 parei por «revisão de par», e a mesma seção da spec diz que a revisão não aprova subida. Antes de `PARADA:`, ler a frase inteira da regra que ancora.

## Diário de bordo

- 2026-09-25 — rotina de commit de alto nível não pegou arquivo novo criado por escrita direta. Contorno encontrado na data foi: `add` explícito antes.
- 2026-09-25 — `deploy-harness/instalar` sem extensão recusado por `write_file`. Contorno encontrado na data foi: `.txt` + `add` + `mv`.
- 2026-09-25 — bit de execução perdido no `mv`, e o commit de alto nível re-adicionava do disco em 644. Contorno encontrado na data foi: `update-index --chmod=+x` + commit de baixo nível + `checkout -- <caminho>`.
- 2026-09-25 — promover platafirma-conhecimento para um fix pequeno reconstruiu wiki e rag inteiros. Contorno: nenhum — desenho do `release promover` (família inteira).
- 2026-09-26 — `teste rodar` com caminho de clone ou alvo fora de controle/tests: «alvo não existe» / «nome de repo inválido». Contorno encontrado na data foi: rodar na própria bancada.
- 2026-09-26 — `/tmp/pre-push-contrato.txt` sobrescrito por push de outra cadeira. Contorno encontrado na data foi: diagnosticar pela árvore da rev. (O pre-push novo grava na instância.)
- 2026-09-26 — `repo procurar` com dois caminhos recusou «argumento excedente». Contorno encontrado na data foi: `repo git <repo> grep -n -e ... -- <caminhos>`.
- 2026-09-26 — `release promover harness` / sem rev recusados. Contorno encontrado na data foi: `release promover platafirma-harness <sha>`.
- 2026-09-26 — `mesa anota` REESCREVE o slot inteiro. Contorno encontrado na data foi: anotação nova + anterior na mesma chamada.
- 2026-09-26 — `teste rodar platafirma-harness ops-server` não coletou (`No module named 'mcp'`). Contorno encontrado na data 26/09 foi: teste temporário em controle/tests com mcp e starlette em stub (`sys.modules`), rodado e apagado com `repo git <repo> clean -f <arquivo>`; a suíte da porta segue sem runner.
- 2026-09-26 — `repo abrir` nascia atrás de origin/main e `repo estado` dizia «atrás 0». Contorno: `fetch` antes. (Corrigido no #3149: abrir e estado buscam o forge.)
- 2026-09-26 — `repo atualizar` em ramo sem upstream saiu 3. Contorno: `sincronizar` (#3149).
- 2026-09-26 — `run_command` recusou `sed … ; cat …`. Contorno: `release ler`; vários, `commands[]`.
- 2026-09-26 — `acervo ler casa org org:0008` saiu 2. Contorno: espécie `adr`.
- 2026-09-26 — `motor` sem partição assume `obra`. Contorno: `motor rag buscar casa "…"`.
- 2026-09-26 — `mesa caderno <chapeu>` com stdin só LÊ. Contorno: `mesa escrever <chapeu>` com o corpo inteiro.
- 2026-09-26 — com a bancada plana de outro card (#3150) ocupando wt/platafirma-harness/ti, o `repo` servido de antes do #3149 resolvia tudo para ela; `repo pr-abrir` não tinha como abrir PR de outro ramo. Contorno encontrado na data foi: `repo git platafirma-harness worktree add <wt/.../<sessao_id>> <ramo>` e todo git por `repo git <repo> -C <caminho absoluto> ...` (o `-C` recusado é o seguido de NOME de repo, não de caminho); PR único já aberto recebeu os commits.
- 2026-09-26 — `write_file` recusou bin/release em wt/platafirma-harness/ti/<card>/bin («tipo sem extensão») — regressão do #3149 na porta. Contorno encontrado na data foi: `repo git <repo> -C <clone base> worktree move <bancada> wt/<repo>/<sessao_id>` (profundidade antiga aceita) até a porta nova subir (0e23f23).
- 2026-09-26 — `teste rodar` e `lint rodar` mediram o clone base com a bancada por card aberta (aviso «usando fallback» só em stderr). Contorno encontrado na data foi: o mesmo `worktree move` para o caminho por sessão; corrigido em f44786d (teste) e e9b3310 (lint).
- 2026-09-26 — `repo commitar` sem caminhos falharia com arquivo temporário já apagado no log da sessão. Contorno encontrado na data foi: commitar sempre com os caminhos nomeados.
