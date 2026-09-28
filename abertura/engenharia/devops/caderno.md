CONHECIMENTO CURADO
- Esperar evento assíncrono (ingestão da casa, suíte "em andamento") se faz consultando o estado a cada ciclo do produtor, nunca com pausa fixa longa; a espera cega é o que o dono lê como lentidão.
- Card antigo pode trazer trava fóssil herdada do esqueleto da época; antes de parar por trava do card, conferir se o guia vigente a revogou (quem escreveu mescla e sobe, arq:0109 §3).
- Documento de casa que não aparece depois do merge: primeiro suspeito é o cabeçalho (Sobre: com referente fora de verbo/capacidade/stack/instancia/repositorio/cadeira/risco é recusado em silêncio).
- Antes de tornar obrigatória uma variável de ambiente num verbo, conferir quem a injeta em cada caminho de chamada (porta, cron, esteira de promoção); exigir o que a porta não injeta deixa o verbo inutilizável para toda cadeira.
- Mudança no próprio caminho de subida do harness (release, ajudante de stack) só vale da promoção seguinte: a promoção corrente roda com o release antigo já carregado e pode sair em estado partido; repetir a chamada confirma "já no ar".
- Orquestrar sub-agentes no mesmo sessao_id: a poda é por sessão, então um agente recebe "igual ao giro N" do que só outro leu; o executor relê pela bancada (repo ler, read_file com offset).
- Promover harness reinicia a porta e o conector cai por segundos: é esperado, não incidente; espera e confere o release estado, sem relatar "não sei se subiu".
- A fita termina o próprio trabalho; tarefa agendada para retomar é recusada pelo dono. Pendência que não fecha na fita sai no relato.
- Barreira de ferramenta (write_file recusando um tipo de arquivo) sobe como barreira no mesmo turno; não se contorna mudando o desenho do card calado.
- Checagem nova vira aviso, não portão que trava merge: o dono recusa teste/portão obrigatório (medo de teste fóssil travando código); não propor nem cobrar ruleset.
- README (padrao readme): em subpasta, o critério é «sobe ou testa sozinha»; o AP8 do lint só enxerga pyproject/package.json/Dockerfile/Makefile, então pasta com compose ou venv próprio leva README mesmo sem o lint acusar (DT 31). Revisão de README é de TODOS, raiz inclusa: trava de card que poupa raiz é erro de quem escreveu o card.
- `lint organizacao <repo>` com nome nu mede a bancada aberta da cadeira, não main; com bancada velha aberta, medir numa bancada sincronizada com main.
- Skill mora no harness (skills/<nome>/SKILL.md); atualizar lá é o ato inteiro. Cadeira não exporta skill nem abre card de skill para o dono.
- Fóssil que o dono manda apagar se apaga inteiro, com as referências vivas nos outros repositórios; histórico (registro/, análise datada) fica. Em 27/09: Vikunja, platafirma-osint, platafirma-ollama-orchestrator. platafirma-cofre-backup NÃO é fóssil: fica.

DIARIO DE BORDO
2026-09-27 — release promover harness 47c8ce6 saiu 2 "família fora do registro"; li registro/familias.json — contorno encontrado NA DATA 2026-09-27 foi usar o nome platafirma-harness.
2026-09-27 — write_file em /home/claudinho/wt/... recusado "fora de morada" — contorno encontrado NA DATA 2026-09-27 foi o caminho /home/claudinho/AI/wt/<repo>/<cadeira>/<slug>.
2026-09-27 — fila enviar com --tipo aviso: tipo invalido; com resposta sem --assunto: erro; com corpo posicional: "corpo vazio"; pipe recusado pela porta — contorno encontrado NA DATA 2026-09-27 foi o parametro stdin da tool fila.
2026-09-27 — repo procurar recusou lista de caminhos; repo ler recusou --linhas — contorno encontrado NA DATA 2026-09-27 foi repo git <repo> grep -n -A/-B.
2026-09-27 — nota-tecnica 2026-09-14-virada-onda-2 em main e ausente do acervo; acervo ler exit 1; git grep "^Sobre:.*card" achou só ela — contorno encontrado NA DATA 2026-09-27 foi tirar "card 3053" do Sobre: e pôr "Card: #3053" em linha própria (PR casa #61).
2026-09-27 — write_file em bin/tarefas e padrao/card-execucao-e-fila.md negado pelo classificador de permissão ("Instruction Poisoning") — nenhum contorno; dono aprovou explicitamente no chat e a reedição passou.
2026-09-27 — infra logs ops-mcp 400 --desde/--ate ignorou a janela e serviu 40 KB — nenhum, encaminhado a ti.
2026-09-27 — repo abrir platafirma-casa 3117 com o card já em homologação moveu o card de volta a em-execucao — contorno encontrado NA DATA 2026-09-27 foi mover de novo à mão; para ajuste sem card, repo abrir <repo> --slug <s> (ramo <cadeira>/<slug>) não mexe em card.
2026-09-27 — mesa caderno devops com stdin só lê (caderno não existia) — contorno encontrado NA DATA 2026-09-27 foi mesa escrever devops.
2026-09-27 — (#3145) despacho de sub-agente para mesclar e promover negado pelo classificador do Claude Code ("Merge Without Review", "Production Deploy", "Interfere With Workloads") — contorno encontrado NA DATA 2026-09-27 foi autorização explícita do dono no chat e troca do modo de permissão; o aceite da stack motor passou depois que o dono explicou que não interfere.
2026-09-27 — (#3145) repo procurar/ler em platafirma-harness saiu 2 "mais de uma bancada aberta" — contorno encontrado NA DATA 2026-09-27 foi a chave platafirma-harness@<card>-<slug>.
2026-09-27 — (#3145) lint rodar não existe (guia desenvolvimento cita) — contorno encontrado NA DATA 2026-09-27 foi lint codigo <repo>@<chave> <arquivo>.
2026-09-27 — (#3145) teste rodar testes/<script>.sh saiu 4 "alvo fora da subárvore"; bash não é verbo — nenhum, suíte hermética conferida só por leitura.
2026-09-27 — (#3145) write_file com trecho recusou antes com parênteses/chaves; write_file recusou arquivo sem extensão fora de bin/ (deploy/crontab-claudinho) — contorno encontrado NA DATA 2026-09-27 foi reescrever o arquivo inteiro e repo git apply.
2026-09-27 — (#3145) write_file em agente/settings.json negado pelo classificador ("Self-Modification") — nenhum, fica com o dono.
2026-09-27 — (#3145) release promover platafirma-harness saiu 4 no gate por capacidade infra/plataforma inexistente no acervo — contorno encontrado NA DATA 2026-09-27 foi capacidade: infra (PR 257).
2026-09-27 — (#3145) 1ª promoção do harness saiu 3 "deploy não encontrado" com current já trocado (release antigo carregado) — contorno encontrado NA DATA 2026-09-27 foi repetir a chamada ("já no ar").
2026-09-27 — (#3145) migrar aplicar saiu 3 "variável PF_SUJEITO: ausente" (porta só a injetava em sessao abrir) — contorno encontrado NA DATA 2026-09-27 foi a porta injetar PF_SUJEITO da sessão em todo verbo (PRs 262, 263; migração 0094).
2026-09-27 — (#3145) release promover platafirma-motor no sha no ar saiu 1 "já no ar" — contorno encontrado NA DATA 2026-09-27 foi infra restart motor-msg-mem para o aceite da sessão viva.
2026-09-27 — (#3145) tarefas sub 3119 saiu 1 "line 880: 2: filho" — contorno encontrado NA DATA 2026-09-27 foi tarefas ler 3119 (lista as filhas).
2026-09-27 — (#3145) fila enviar sem --assunto saiu 2 — contorno encontrado NA DATA 2026-09-27 foi --assunto.
2026-09-27 — (#3136) write_file de deploy-harness/casa-pr-conferir.service recusado (tipo .service fora da lista) — nenhum; encaminhado ao #3147 (ti).
2026-09-27 — (#3136) release promover harness/conhecimento (nome curto) saiu 2 "família fora do registro" — contorno encontrado NA DATA 2026-09-27 foi o nome platafirma-<família> (de novo).
2026-09-27 — (#3136) infra log não existe; unit casa-site-publicar manda stdout a arquivo, infra logs só mostra systemd — contorno encontrado NA DATA 2026-09-27 foi read_file do publicar.log com offset.
2026-09-27 — (#3136) repo pr-ver não mostra status de commit (conferir) — contorno encontrado NA DATA 2026-09-27 foi ler o publicar.log.
2026-09-27 — (#3136) fechar PR sem merge: repo não tem ato — contorno encontrado NA DATA 2026-09-27 foi repo git push origin --delete <ramo> e repo sanear.
2026-09-27 — (#3136) repo abrir com card em entregue saiu com recusa de mover (exige motivo), bancada aberta mesmo assim — contorno encontrado NA DATA 2026-09-27 foi ignorar o move.
2026-09-27 — (#3177) teste rodar <stack> recusa com mais de uma bancada do harness aberta e não aceita nomear a bancada; teste rodar <bancada> ops-server roda no venv harness (No module named mcp) — nenhum, DT 30.
2026-09-27 — (#3177) repo não tem ato de fechar bancada; bancada só some no pr-merge — contorno encontrado NA DATA 2026-09-27 foi repo sincronizar na bancada velha antes de medir.
2026-09-27 — (#3177) repo commitar recusa caminho apagado — contorno encontrado NA DATA 2026-09-27 foi repo git rm antes e commitar só os caminhos vivos (o stage leva a remoção).
2026-09-27 — (#3177) nenhum verbo apaga repositório no forge; run_command gh recusado "sem verbo" — nenhum, o dono apagou pela mão.
2026-09-27 — (#3177) write_file recusou wt/platafirma-osint e wt/platafirma-ollama-orchestrator "fora de morada" — nenhum, os repos eram fósseis e foram apagados.