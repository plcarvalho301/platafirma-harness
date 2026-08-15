# tool-manifest — toda cadeira

Comum a todas as cadeiras. Redação de claudinho-TI; forma de RH. Manifesto de
cadeira não replica o que está aqui — aponta.

> **Verbo novo em `bin/`, mesmo commit:** linha aqui antes do push. Ferramenta
> existente e não indexada é ferramenta inexistente.

> **Entrega vai a git ou wiki no mesmo turno.** O dono não tem shell no host: arquivo
> parado em `~/AI` é rascunho, não entrega — ele não consegue abrir nem validar. Publica,
> e só então relata, com link inteiro e colável.


```
ver minha caixa                 : fila status <persona>          quantas novas, sem ler
ler o que chegou                : fila ler <persona>               so o novo; confirma na entrega
reler o historico (7 dias)      : fila ler <persona> --tudo [rem] | --desde AAAAMMDDTHHMMSS
mandar recado                   : fila enviar <dest> --tipo <t> --assunto <a>
                                  (corpo em stdin; --ref e --responde opcionais)
minutas em que estou metido     : minuta ler                     abertas por mim ou que me convocam
                                  exit 1 = nenhuma; leitura fria, nao marca visto
ler uma minuta inteira          : minuta ler <n>|<slug>
abrir deliberacao entre cadeiras: minuta escrever <slug> --convoca <c1>[,<c2>...]
                                  [--fecha <cadeira|pedro>] [--card <#N>]
                                  numera sozinho e nao recicla; NAO commita e NAO circula
despachar o ping de abertura    : minuta circular <n> [<cadeira>...]
                                  recusa pauta vazia e minuta nao commitada
fechar minuta (unico jeito)     : minuta formalizar <n> --como adr|spec [--destino <slug>]
                                  [--vencido]  cria o canonico vazio, APAGA a minuta,
                                  um commit so. Minuta nao se arquiva.
abrir sessão de uma cadeira     : monta-sessao <cadeira>   [tool monta_sessao é a via boa]
despachar giro na sala do chat  : chat despachar --cadeira <slug> --fita <id-ou-vazio>
                                  [--modelo <alias>] [--esforco <nivel>] vem do
                                  comando `pf` da sala, nunca do settings.json
                                  corpo em stdin; UMA linha JSON no stdout (estado, texto,
                                  id_fita, detalhe, reiniciada) e um passo por linha no
                                  stderr. Quem chama e a recepcao do chat, nao a cadeira.
                                  Fita vazia abre por monta-sessao; fita com id retoma e
                                  NAO reinjeta o pacote. --silencioso: giro cujo produto e
                                  escrita em mesa/caderno, sem texto para a sala.
versao do motor x a pinada      : chat versao                    exit 1 = CLI derivou

ver minha memoria de trabalho   : mesa ver [chapeu]              ja vem no monta_sessao
anotar antes de a fita morrer   : mesa anota <chapeu>            corpo em stdin; sobrescreve
esquecer um chapeu              : mesa limpa <chapeu>            alvo obrigatorio
fita corrente da cadeira        : mesa fita [abre|fecha --id <id>]  com PF_FITA no ambiente,
                                  `mesa anota` so escreve se a fita ainda for a corrente
indice dos cadernos duraveis    : mesa caderno                   idade e tamanho, sem corpo
abrir o caderno de um chapeu    : mesa caderno <chapeu>          corpo sob demanda
fechar a fita                   : encerrar fita                  memoria + fatos volateis + triagem do Project
                                  (`descansar` e o mesmo verbo, outro nome)
so o estado da memoria          : encerrar fita --so-memoria     sem o dossie, mais rapido
achar slot fora do remit        : encerrar varredura             todas as cadeiras; timer diario ja roda

ler um card                     : tarefas ler <id>|#<index>   #N e o da fila; <id> e a chave
listar projetos                 : tarefas projetos
listar cards abertos            : tarefas listar <projeto>        (listar-tudo inclui fechados)
abrir card                      : tarefas criar <projeto> "<título>" [--desc "<txt>"|--desc-stdin] [--prio N]
comentar                        : tarefas comentar <id> ["<txt>"]  sem txt, lê stdin
fechar                          : tarefas fechar <id>
amarrar subtarefa               : tarefas sub <pai> <filho>
o que o verbo não cobre         : tarefas api <MÉTODO> <caminho> | tarefas api-corpo (JSON em stdin)

estado do acervo (5 degraus)    : acervo escada          [--json | --detalhe]
                                  ÚNICA fonte de número do acervo — ver regra abaixo
demais atos do acervo           : acervo                  sem argumento, lista os sub-atos
consulta ao RAG pela linha      : motor rag buscar "<pergunta>"  mesmo contrato do rag_search
medir a recuperacao servida     : motor rag medir [--k N] [--rerank] [--rotulo <nome>]
                                  gold canonico pela porta servida; as duas familias
                                  separadas e o delta contra a rodada anterior
ajustes do motor, com trade-off : motor rag ajuste [<ajuste> [<valor>]]  ver, entender e mexer
instancias de motor declaradas  : motor listar

o que está no ar                : infra estado [alvo]
está tudo saudável?             : infra saude  [alvo]
sinal de saude, arquivo unico   : sinal                  coleta e escreve; --ver so mostra
log de contêiner ou unit        : infra logs <alvo> [n]     descobre qual dos dois é
reiniciar sem se matar          : infra restart <alvo>      destacado; exige alvo explícito
serializar carga de GPU         : infra exclusivo [--] <cmd...>  espera a vez + cota de CPU/RAM
ver e liberar cache             : infra cache [ver|vram|disco]   liberar e sempre explicito
estado dos backups declarados   : infra backup [--json]      idade, geracoes; alvo sem cobertura fica na lista

promover release de uma stack   : deploy <stack> up -d      stack obrigatória, sem default
ver o declarado de uma stack    : deploy <stack>            não toca em nada; inclui o SHA servido
rotas do túnel de uma stack     : deploy <stack> rotas      hostname -> serviço, do ingress declarado
quem entra em cada superfície   : deploy <stack> acessos    allowlist e gate próprio, por serviço
segredos que a stack exige      : deploy <stack> segredos   nome e presença, nunca valor
quais stacks existem            : deploy                    lista o registro

declarado x servido             : conferir servico [nome]   exit 1 = há divergência
verbo x arq:0037                : conferir verbo [nome]     origem, cabeçalho e a conta
skill servida x fonte           : conferir skill <nome> --servido <blob do carimbo>
repo x arq:0042                 : conferir repo  [nome]     o que esta rastreado x a regua
                                  mede tambem o cabecalho de genero e publico (arq:0049),
                                  nos arquivos que o repo declara em docs/.operacao
gate de commit (arq:0042)       : conferir repo --staged    o que o pre-commit chama
caminho de execucao x harness   : conferir procedencia      exit 1 = ~/AI/bin resolve pra fora
                                  excecao se declara em harness/docs/procedencia-do-harness.md
instalar o gate num clone       : git -C <clone> config core.hooksPath ~/AI/platafirma-harness/hooks
toolkit de segurança            : seg                       despachante (arq:0040)
quem alcança o quê              : acesso listar [sujeito]    concessões vigentes; sem arg, todas
conceder / revogar acesso       : acesso conceder --sujeito <c> --eixo <e> --valor <v>
                                    --fundamento "<por quê>" --por <quem pratica o ato>
                                  acesso revogar <id-do-ato> --fundamento ... --por ...
                                  fundamento e --por são obrigatórios; nada aqui se apaga
isto seria permitido?           : acesso decidir --papel <p> --dominio <d> --acao <a>
                                    --recurso "<alvo>"       avalia sem tocar em banco
o PAP (política em arquivo)     : acesso politica [conferir|importar]   seg:0008
desligar sujeito de vez         : acesso desligar <sujeito> [--executar]  os quatro atos da
                                  revogacao (seg:0011): realm, sujeitos.yaml, PAP, segredo.
                                  Sem --executar so mede o plano; nunca commita
residuo de acesso               : acesso orfaos              exit 1 = ha ato pendente:
                                  concessao vencida, sujeito sem projecao, credencial dormente

estado do repo                  : git -C ~/AI/<repo> status --short
publicar                        : git -C ~/AI/<repo> add -A ; git ... commit -m "..." ; git ... push
job > 2 min                     : longjob run <nome> <cmd...>   | list, logs, status, log, stop

instrumentar ambiente novo      : platafirma-harness/deploy-harness/instalar
                                  sem argumento converge . --check so mede (exit 1 = divergente)
                                  --prefixo <dir> troca o alvo do symlink farm
                                  nao instala terceiro, nao clona repo, nao fala com rede

venv reprodutível               : uv venv / uv pip install / uvx <pkg>
rodar script solto              : python3 (sem shim de pip — usar uv pip)

buscar em ~/AI                  : rg <padrão>          (~16 ms; grep -r aposentado)
achar arquivo                   : fd <nome>
ler JSON / YAML / log           : jq · yq (não usar regex em config) · lnav
histórico de carga              : sar                  (única que responde "há 3 horas")
espaço                          : df -h · du -sh · ncdu
```

## As tres superficies servem os mesmos conectores

A cadeira nao roda num lugar so: claude.ai, fita do chat (sala do Matrix) e Code
em worktree da fabrica. **O comportamento e o mesmo nas tres**, e a equalizacao e
pelo MEIO — as tres servem `platafirma-ops` e `platafirma-wiki`. Texto de cadeira
nao se reescreve para caber em superficie mais pobre.

- **Registro**: `tool-manifest/superficies.json` — superficie, conectores, tools
  que cada conector serve, e o risco aceito quando ha.
- **Onde se declara**: `.mcp.json` no cwd. Na fita, `prepara_cwd` escreve; nas
  worktrees, ja existia — foi de la que o padrao veio.
- **Conferencia**: `conferir superficie` mede conector prometido e nao servido,
  capacidade sem meio, e texto citando tool que conector nenhum serve.
- **Gate**: o `pre-commit` chama `conferir superficie --staged` — incremental.
- **Superficie nao e fronteira de seguranca.** O modelo e conta segregada (uid
  `claudinho`), acesso por `run_command` via CLI, isolamento e pentest contra
  escalonamento de privilegio. O vetor unico e a IA sair da conta que o inicio de
  sessao lhe designou; dentro da conta e sandbox, feita para quebrar sem
  comprometer o servidor. O allow/deny do settings do Code e higiene de sessao,
  **nao** controle — nao o promova a controle e nao derive modelo de risco dele.

## O verbo declara a capacidade que serve

Todo verbo da plataforma carrega, nas primeiras linhas do arquivo: uma linha de
propósito, `capacidade:` (uma das do mapa da mesa), `dono:` e, quando ajuda,
`componente:`. Capacidade não se inventa no cabeçalho — nome fora do mapa reprova.

Forma extensa do BizBOK e contração valem as duas: `gestao-de-motores` e `motor`
são o mesmo termo, e a conferência as trata como equivalentes.

`conferir verbo` mede isso e a conta de `arq:0037` — um verbo por capacidade — e
sai 1 enquanto houver divergência. Catálogo completo, com origem de cada verbo:
`Operar:catalogo-de-verbos` na wiki e `docs/catalogo-de-verbos.md` no harness.

Verbo que é despachante de toolkit (`acervo`, `seg`) é o par binário+subcomando,
por `arq:0040`: o binário agrupa, o subcomando é o ato.

> **Número do acervo sai de `acervo escada`, nunca de SQL na mão.** Contagem crua
> `WHERE embedding IS NULL` inclui os chunks não-textuais (tabela, figura, layout),
> que nunca recebem vetor por contrato do embedder (`NOT is_not_text AND length(text)>0`)
> — subtrair total menos vetorizados fabrica uma pendência que não existe. Pendência
> real é a linha `embedding parcial` do próprio instrumento. Vale pra toda cadeira:
> quem afirma número do acervo sem ter rodado o instrumento está reportando, não medindo.

## Card por sessão — norma de conduta

Card técnico não tem gatilho de aceite visual: sem isto, ninguém lembra que
existe pra fechar.

- **Início de sessão de execução**: puxar/confirmar o card com pergunta
  binária (`card #N — <título> — é esse?`). Carregar como estado até trocar
  ou encerrar.
- **Fim de sessão**: perguntar fechamento por card do flag, um por um,
  critério explícito — nunca inferência sobre o diff da sessão.
- **Encaminhamento pra outra cadeira** (fila) cita `#N` do flag
  automaticamente quando aplicável.
- **Escrita de git/wiki é manual**, sob pedido explícito do dono — não é
  trigger automático de fim de sessão.
- **Fechou marco, encerra a fita.** `encerrar fita` roda por marco fechado —
  entrega commitada, card fechável, assunto encerrado — e não por hora do dia.
  Esperar o fim do expediente tem o defeito que o verbo existe para corrigir: a
  sessão não sabe quando morre. Quem chama é a cadeira, sem o dono pedir.
- **O dono também dispara por fala.** "encerra", "fecha o dia", "descansa", "vai
  dormir" e afins são a chamada do verbo, não conversa — quem interpreta é a
  sessão, e o binário não tem como ouvir isso.

## Execução inteira — quem começa, termina (dono, 11/08/2026)

- **Antes de iniciar, pergunte.** Refinamento é a fase de perguntar: dúvida,
  insumo e decisão alheia se resolvem aí.
- **Iniciada a execução, precisar de qualquer coisa é exceção** — entrega
  complexa, autorizada pelo dono, com a mensagem dele em `ref`.
- **Complexa = não cabe num agente só**: exige mais de um agente na mesma
  entrega. Ao pedir terceirização, escreva em uma linha por que não cabe em você
  — competência que falta, contexto que estoura, frentes que não serializam.
  Cabendo em você, é sua.
- **Fechado o refinamento, duas rotas**: pedir ao dono autorização para
  terceirizar a entrega inteira à fábrica, ou executar inteiro sozinho — todas as
  peças (código, doc, wiki, migração, card).
- **Rota da fábrica**: dono autoriza (análise de risco é dele) → claudinho-TI
  revisa e despacha o card. A porta da fábrica continua sendo o card do TI.
- **A quebra é dentro da fábrica, não entre cadeiras**: TI fatia a entrega nos
  cards que ela exigir e a fábrica distribui entre agentes.
- **TI revisa nas duas pontas**: entrada (corta o card) e saída (recebe da
  fábrica, revisa e conserta antes do merge). Do card ao push, a entrega é dele.
- **A responsabilidade da execução é do executor.** Não se reparte, não se
  repassa, não se consulta no meio.
- **Risco alto ao ambiente → o merge vai a gate de claudinho-TI**, com sign-off
  pedido por mensagem antes do push. Sem risco, vai até o fim.

## Fila — o que merece mensagem (teste de admissão)

Medido em 09/08/2026 sobre as 40 mensagens vivas: 19 são `resposta`, contra 8
`pedido` e 7 `decisao`. Resposta é o tipo dominante — a fila virou esteira de
entrega em vez de canal de decisão, e caixa que não zera para de informar.

**Teste, antes de escrever qualquer mensagem: se eu não mandar isto, o que
para?** Nada para → não manda.

- **Manda** só o que precisa de decisão ou insumo de OUTRA cadeira para quem
  escreve continuar. Bloqueio real, não cortesia.
- **Não manda**: entrega concluída, achado registrado, retificação de número,
  aviso de commit, "de acordo", "recebido", agradecimento. Isso é card, commit
  ou nada.
- **Silêncio é aceite.** Concordância não se responde; discordância sim.
- **Profundidade máxima 2.** Pedido → resposta encerra a cadeia. Responder a uma
  resposta é proibido; se a resposta abriu assunto novo, o assunto novo é card
  com dono, não terceira mensagem.
- **Achado fora do escopo do pedido vira card**, não mensagem — salvo se o dono
  precisa decidir hoje para não perder trabalho.
- **Handoff é exceção** e continua valendo: é contexto de abertura, não tráfego.
- **Ordem explícita do dono dispensa o teste.** Explícita = verbo de mando +
  destinatário ou ato nomeados por ele; preferência ou pedido implícito não
  contam. Dispensa é do teste, não do registro: grava-se o ato como ordem do
  dono, com a mensagem original em `ref`.

Quem escreve carrega a prova de que passou no teste: a mensagem diz, em uma
linha, o que trava sem ela. Sem essa linha, a caixa do destinatário não deve
nada — pode consumir sem responder.

## Fila — a caixa é log, e ler já confirma

**A caixa é a malha `msg` (Valkey/Streams), não arquivo.** Um stream por persona,
`caixa:<persona>`, com um consumer group — a cadeira dona é o único consumidor.

- `fila ler` entrega **só o que chegou desde a última leitura** e confirma na
  entrega. Não há ato de consumir, e não há caixa a zerar: o ponteiro vive no
  servidor, e a sessão não carrega estado entre fitas.
- **Nada é apagado ao ler.** O histórico segue no stream e sai por `--tudo` ou
  `--desde`, que são leitura fria e não movem o ponteiro.
- **Retenção de 7 dias** (`XTRIM MINID`, timer do motor) é a única coisa que
  apaga carta. Mensagem é consumo curto; o que tem permanência vira card, commit
  ou wiki antes de vencer.
- Fita que morre depois de ler perde o aviso, não a carta: ela volta por
  `--desde` dentro da janela.

Projetos do rastreador: `46 Cards` e `1 Inbox`, só. Filtro salvo (id negativo)
não é projeto e devolve 404 em `/tasks` — `tarefas projetos` já os omite.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.

## Armadilhas que mordem toda cadeira

Estas estavam repetidas em quatro manifestos, com quatro redações. Uma fonte:

- **O espelho de repo serve o SHA velho depois do push.** `repo_read`,
  `repo_grep` e `repo_tree` leem o ref remoto por espelho; sem `repo_sync`
  depois de `git push`, servem a versão anterior em silêncio. Frescor crítico:
  ler o clone local por `run_command`.
- **`&&` encadeado no `run_command` some com o erro.** Passo intermediário
  não-zero derruba o resto sem sinal visível. Usar `;` ou chamadas separadas.
- **Faceta válida e despovoada devolve zero sem erro.** `rag_facets` antes de
  filtrar `rag_search`: zero por faceta vazia é indistinguível de zero por
  ausência de cobertura.
- **`longjob` não herda o ambiente da sessão.** Variável exportada no `run_command`
  (`PF_SIM`, `PF_CADEIRA`) não chega ao job, e `env VAR=x <verbo>` falha porque o
  systemd-run também não traz o PATH do harness. Forma que funciona:
  `longjob run <nome> bash -lc 'export VAR=x PATH=$HOME/AI/bin:$PATH; <verbo>'`.
- **`edit_page` substitui a página inteira.** Não há patch nem append: `get_page`
  antes, sempre, e devolver `basetimestamp` para detectar conflito.

## Escovação de bit — o que gira a cada fita

Régua do dono: escova-se o que é executado dez milhões de vezes. Aqui isso tem
escopo estreito e nomeável — o miolo do loop de inferência, ou seja tudo que
sobe no contexto a **cada giro de fita**. Meia dúzia de token economizada nesse
miolo é cobrada em todo giro de toda cadeira; a mesma economia fora dele não é
cobrada de ninguém.

- **Gira, logo escova-se**: nome de chave e de stream, nome de verbo e de
  sub-ato, campo de envelope da fila, tool-manifest, descrição de tool, saída
  default de verbo chamado por sessão.
- **Não gira, logo não se escova**: ADR, wiki, README, comentário de config,
  mensagem de commit, log, ajuda extensa de verbo, carta da fila.

A régua corta nos dois sentidos: fora do miolo, verbosidade é barata e a
clareza vence a contração. A pergunta que decide é uma só — *isto sobe no
contexto a cada giro?*
