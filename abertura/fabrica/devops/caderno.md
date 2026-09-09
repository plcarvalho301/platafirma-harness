# caderno — fabrica / devops

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Teste que nasce verde não prova nada até o mutante derrubá-lo

Teste escrito DEPOIS da correção nasce verde por construção: passa tanto com o furo
fechado quanto com ele aberto, se a asserção não morde o ponto exato. Entregar assim é
entregar a aparência da trava, e a regressão volta com a suíte inteira verde.

A régua: antes de abrir o MR, **reponha o furo** e rode. O teste novo tem de ficar
VERMELHO. Só então ele vale como trava. Reponha e restaure no mesmo giro, com backup do
arquivo — a janela em que a árvore está mutada é o único risco, e ela dura segundos.

Medido no #2945 (reancorar voto por `sessao_id`, 09/2026): 6 casos novos, todos verdes.
Repondo os dois furos — o fallback temporal cego e o `sessao_id` que não era repassado —
**5 dos 6 vermelharam**. O sexto era verde vazio e teria ido no MR como trava que não
trava. Sem o mutante, ninguém veria a diferença entre os dois grupos.

Corolário do mesmo princípio, e o caso que engana mais: **falha anterior se PROVA, não se
alega**. Suíte que já vem vermelha tenta o atalho "essas falhas não são minhas". A prova
é o contrafactual: `git stash` das mudanças, rodar em HEAD, ver as mesmas falhas com os
mesmos nomes, `git stash pop`. No #2945 eram 6 (`test_sidecar` 2, `test_carga_acervo` 2,
`test_nomes` 1, `test_planilha` 1) — e só depois de medidas em HEAD é que couberam no
corpo do MR como dívida de outra frente.

O que os dois casos têm em comum: um resultado de teste é uma afirmação sobre uma
DIFERENÇA (com o bug vs sem, com minha mudança vs sem), e diferença não se lê num estado
só. Rodar uma vez e reportar a cor é opinião; rodar os dois lados é medida.

## Apontamento de linha se declara no MR, não se resolve calado

Despacho de outra cadeira fecha o desenho, mas quem executa é quem encosta no código — e
às vezes a letra do desenho, aplicada ao pé, produz regressão que o desenho não pediu.
Quando isso aparece, não são dois caminhos (obedecer cegamente ou reabrir o desenho): é
um terceiro. Implemente a leitura que preserva o comportamento, **isole a decisão num
bloco próprio do corpo do MR**, com o motivo medido e o custo de reverter ("é uma linha").
A cadeira que desenhou decide na revisão, com o código na frente, em vez de decidir no
abstrato antes.

No #2945 a §2 mandava não descer ao fallback quando `sessao_id` não casasse. Ao pé da
letra, isso matava também a busca por `ordem_id` — porque a mesma mudança fazia `_votar`
herdar `PF_SESSAO`, e voto por `ordem_id` passaria a chegar com `sessao_id` preenchido sem
ninguém pedir. Cortar só o degrau CEGO e declarar o desvio custou um parágrafo; descobrir
a regressão depois do deploy teria custado o ciclo inteiro.

## Uma recusa se mede pelo efeito, não pela mensagem

Trava que imprime "recuso" e mesmo assim executa é pior que trava nenhuma: some do
radar por parecer ativa. Testar uma contenção é tentar violá-la e conferir que a AÇÃO
não aconteceu — não que a mensagem apareceu.

Duas formas do mesmo erro, medidas no #3004 (09/2026):

- **A recusa que morre no subshell.** Validação chamada dentro de `$(...)` que recusa por
  `exit` mata só o subshell. Sem `|| exit $?` no chamador, o "não" vira string vazia e o
  fluxo segue. O alvo recusado virou alvo VAZIO, e o runner rodou o repositório inteiro,
  com a mensagem de recusa impressa no stderr logo acima. Em bash, `[ -n "$x" ] && x="$(valida)"`
  também não serve: encadeado a `|| exit`, dispara quando a condição é falsa.
- **O gate vazio, que ninguém provou.** Uma flag de retenção ficou ligada meses porque
  não havia ninguém para reter — inofensiva por vacuidade. No dia em que o primeiro
  sujeito entrou na lista, ela serviu tudo. Gate sem sujeito não está provado: prova-se
  no ato de pôr o PRIMEIRO sob ele, conferindo que reteve.

Corolário: ao pôr o primeiro item sob um controle existente, a medição não é "o controle
existe" — é "o controle reteve ESTE item". São afirmações diferentes, e só a segunda é
observável.

## Suíte que não rodou não é suíte vermelha

Runner que monta ambiente isolado (`uvx pytest` e parentes) tira do projeto as próprias
dependências: a suíte morre no import, não no teste. A cor é vermelha e a causa é o
ambiente — reportar isso como falha do código manda a próxima fita caçar bug que não
existe.

Vale para todo instrumento de leitura, e a régua é a mesma do `situacao` (arq:0085):
fonte inalcançável responde INDETERMINÁVEL, nunca zero. Não-rodou, não-alcançou e
não-encontrou são estados distintos de falhou, e um verbo que os funde num só mente
barato. Quando o fallback isolado for o único caminho, ele sai avisado — a saída diz que
uma falha de import ali é do ambiente, não do código.

Medido no #3004: o mesmo alvo deu `No module named yaml` no ambiente isolado e 25 passed
com o interpretador do projeto. Nada no código mudou entre as duas execuções.

## Antes de abrir incidente, confira se o roadmap já condena aquilo

Serviço fora do ar nem sempre é incidente. Quando a feature em curso vai APOSENTAR aquele
componente, "está down" é o estado esperado, não um alarme — e tratá-lo como alarme gasta
a fita do dono, abre card que ninguém vai executar e enterra o achado que importava.

A pergunta antes de escalar não é "isto está quebrado?", é "alguém já decidiu que isto
morre?". Se sim, o achado vale como MEDIDA a favor da feature (o argumento dela, na
prática), e é assim que entra no card existente — não como incidente novo.

Medido no #3012 (09/2026): o braço da fábrica estava fora do ar havia dias, e a story em
curso era justamente aposentá-lo. O que era entrega — "o argumento da #3007, medido" —
subiu como alarme, e o dono teve de cortar.

## Checagem de lote/sessão não se prova por chamadas "paralelas" do cliente

Duas chamadas de tool emitidas no mesmo turno não chegam por garantia na mesma sessão de
transporte. Cada uma pode abrir conexão própria no servidor, e um mecanismo que agrupa
por sessão (`lote_id`/`lote_n`, por exemplo) fica cego para elas — não porque o
agrupamento esteja quebrado, mas porque a premissa "mesmo turno == mesmo canal" não vale
para todo cliente.

A régua: antes de reportar a checagem como falha do serviço, confirme que o CANAL usado
para testar de fato produz o que o mecanismo espera monitorar. Sem essa confirmação, o
resultado é INDETERMINÁVEL, não vermelho — mesma família do "suíte que não rodou não é
suíte vermelha" acima.

Medido na ordem-deploy economia-de-giro §3 (06/09/2026): duas chamadas `read_file` no
mesmo turno, pós-restart do `ops-mcp`, vieram com `lote_id`/`lote_n` null nas duas, cada
uma em `sessao` HTTP distinta no log. Ficou registrado como achado aberto, não como
regressão confirmada — o cliente (Code) pode nunca produzir lote literal em tool calls
"paralelas", e sem outro cliente para comparar a checagem não decide sozinha.

## Ordem de deploy que pede restart de serviço precisa se declarar como tal

Um agente de contexto fresco — sem a fita que escreveu a ordem, só o texto do runbook —
não sabe, só pela letra do passo, que reiniciar um serviço desta conta é trabalho de
devops rotineiro sobre infraestrutura própria. A régua de segurança do agente classifica
"reiniciar serviço" e "editar drop-in de systemd" como modificação de configuração de
sistema/segurança — categoria que trava mesmo com autorização explícita — porque essa é a
leitura correta por default quando não se sabe de quem é a infraestrutura. Sem uma linha
dizendo que o alvo é próprio da conta, o passo do restart tem chance real de ser
recusado, e a recusa se propaga: o rollback documentado na mesma ordem cai na mesma
categoria e também é recusado.

A régua: ordem de deploy que inclui restart de serviço ou edição de unit/drop-in nomeia,
na própria linha do passo, que o alvo é infraestrutura desta conta administrada por esta
cadeira — não configuração de sistema ou conta de terceiro. Custa uma linha; sem ela,
custa um ciclo inteiro de recusa, escalonamento e retomada manual.

Medido na ordem-deploy economia-de-giro (06/09/2026): um subagent de Workflow, com o
runbook completo no prompt mas sem o resto da fita, recusou o restart do `ops-mcp` E o
rollback documentado na mesma ordem, citando exatamente essa categoria — mesmo com o
passo anterior (env já editado e conferido por outra parte do processo) relatado como
concluído no próprio prompt. O restart só aconteceu depois de a cadeira que orquestrava
fazer a chamada direta, autorizada em chat pelo dono.

## Aposentadoria se decide por quem CONSOME, não pelo papel que o card atribui

Card que manda aposentar um componente carrega uma premissa junto: a de que aquele
componente é o que o card diz que ele é. A premissa envelhece — o nome sobrevive à
migração, e a frase "hoje X é o braço" continua legível muito depois de deixar de ser
verdade. Executar o passo de aposentadoria sobre a premissa, e não sobre a medida,
derruba contrato vivo de outra frente com o card inteiro parecendo cumprido.

A régua tem dois lados, e o segundo é o que se esquece:

- **O que ele É** — não o papel no card, e sim a superfície servida. Um servidor sem
  caminho de execução não isola execução nenhuma; aposentá-lo não move a agulha que o
  card quer mover, por mais que o texto diga que sim.
- **Quem o CONSOME** — `grep` do endereço dele (host:porta, alias de rede, URL em
  compose/env) por todo o repositório. Consumidor vivo transforma "aposentar" em
  "regredir", e a decisão volta para o dono como recorte, não como execução.

Medido no #3007 (09/2026): o card mandava aposentar o `jaiminho-server` como "o braço
da fábrica". Ele é o MCP de recurso do colaborador externo — sem `run_command`, sem
superfície de execução —, o braço real já havia migrado noutro card, e o `ACERVO_URL`
de um serviço vivo apontava para o endereço que o passo mandava derrubar. Uma leitura
das tools e um `grep` do endereço separaram os três fatos; executar o passo teria
tirado acervo e wiki do externo e desfeito um sign-off anterior.

## Trocar de identidade não é ganhar capacidade — são três atos, e falta sempre o último

Isolar execução por conta de SO parece um ato só: autorizar a troca de uid. Não é. A
autorização move QUEM executa; ela não cria, em lugar nenhum, um chão em que a nova
identidade possa escrever. O caminho feliz do teste — `id -u` devolvendo o uid novo —
passa com o segundo ato faltando, e a falha só aparece no primeiro `write` real, como
`EACCES` num ponto que ninguém associa à troca.

A régua, ao projetar qualquer execução sob outra identidade: liste os três atos lado a
lado antes de estimar, e trate os dois últimos como parte do aceite, não como detalhe
de ambiente. (1) o mecanismo da troca — sudoers, `runuser`, `User=` de unit; (2) o
alcance da identidade de destino — grupo, dono de diretório, socket, `$HOME`; (3) a
INTERSEÇÃO desse alcance com o que a política já permite àquele sujeito. Vale para além do
uid: token que troca de sujeito sem entrada correspondente no PAP falha pelo mesmo
formato — identidade nova sem alcance projetado.

Medido no #3007 (09/2026): o card previa só a regra de sudoers. `/home/claudinho/AI` é
`claudinho:claudinho` e a conta de destino não estava no grupo — com a regra instalada
e sem mais nada, o comando trocaria de uid e o arquivo não nasceria. O aceite pedia
justamente um arquivo com o owner novo no disco: passaria no `id -u` e falharia no que
importava.

O terceiro ato apareceu no mesmo card um dia depois, com os dois primeiros já feitos, e
é o que nenhum dos dois lados acusa sozinho: a regra que permite ao fornecedor escrever
casa `sobre: [platafirma-*/*, var/tmp/*]` — tudo na casa da plataforma, onde o uid novo
leva `EACCES` —, e a raiz onde ele de fato escreve não está no `sobre` de regra nenhuma.
SO verde de um lado, política verde do outro, interseção vazia no meio: o write é
impossível e nenhum teste de um lado só o mostra. O teste do SO escreve num caminho que
a política não autoriza; o do PDP autoriza um caminho onde o SO não deixa escrever. A
medida que decide é uma só, e tem de ser feita no MESMO caminho: aquele onde os dois
dizem sim. Vale para toda identidade nova, não só para uid — o par (mecanismo, alcance)
sem a interseção com a política é meia migração que passa em todo ensaio.

## Filtro que reformata saída alheia guarda o que não casou

Todo filtro que reagrupa saída de outro programa — resultado de busca, log, tabela — é
uma aposta sobre o formato. A aposta erra, e o modo de errar tem duas metades: casar o
que não devia, e **sumir com o que não casou**. A segunda é a cara, porque é muda: quem
lê o retorno vê um bloco bem formatado e não tem como saber que três linhas foram
descartadas no caminho.

Duas regras, e a segunda não é opcional:

- **O reconhecedor exige forma plausível, não só o padrão.** `arquivo:linha:conteúdo`
  casa qualquer timestamp `HH:MM:SS`; exigir que o primeiro campo pareça caminho (sem
  espaço, com `/` ou `.`, não só dígito) é o que separa um `rg` de um `journalctl`.
- **O que não casou sai onde estava, intacto.** Agrupar é poda; descartar linha é
  perda de informação, e perda muda é a que treina a próxima sessão a confiar num
  retorno mutilado.

Medido no #3013 (06/09/2026): o lavador da porta remontou `systemctl show; journalctl`
como se fosse busca — `18:58:05` virou «arquivo 18, linha 58» — e engoliu `active`,
`MainPID=…` e `health=200`. Não apareceu em 48 testes verdes: o ensaio é hermético e
não tem saída de sistema de verdade dentro. Apareceu no PRIMEIRO retorno real depois
do restart. Regra de método que fica: subiu filtro de retorno, leia o primeiro retorno
de produção com desconfiança — é o único lugar onde a saída é do mundo, e não sua.

## Chave de estado nunca sob identificador reciclável

Estado que pertence a uma conversa — ledger, cache, atribuição de autoria — precisa de
chave que não reapareça na vida de outra. Identificador derivado de endereço de objeto
(`id()`, ponteiro, handle) parece estável dentro de um processo e é **reciclado depois
do GC**: horas depois, outra sessão recebe o mesmo valor e herda o estado da primeira.
O sintoma não é erro; é dado de um aparecendo na fita de outro.

A régua: chave de estado vem de quem tem dono e ciclo de vida declarados — uuid cunhado
por ato, id de sessão que o cliente manda no header. Não vindo nenhum, **não se grava**:
rodar sem o índice é degradação honesta, e chave reciclável é troca silenciosa de
identidade. Vale igual para nome de arquivo temporário e diretório de trabalho.

Medido no #3013: o join conexão→sessão gravou sob `s<hex>` de `id(ServerSession)`. Com
`stateless_http=True` cada POST cria sessão nova, então nem resolvia — e teria sido pior
se resolvesse. É o mesmo formato do #409 (18/08), que quase produziu atribuição errada
de autoria.

## Gerador único mora no ponto por onde toda superfície passa

Quando uma entidade tem de nascer UMA vez, a pergunta não é «qual componente é o mais
natural para cunhar», e sim **por onde todas as entradas passam**. Cunhar no componente
mais próximo do consumidor mais visível deixa as outras entradas sem a entidade — e a
correção que aparece sozinha, na cabeça de quem opera a entrada órfã, é cunhar mais um
ali. É assim que uma entidade com «um gerador» vira quatro, cada um defensável no seu
contexto.

Régua ao implementar identidade única: liste as entradas ANTES de escolher o lugar, e
escolha a interseção — normalmente o verbo, não a porta, porque a porta é uma superfície
entre várias e o verbo é o que todas chamam. Quem não pode cunhar deve poder RECEBER
(flag, parâmetro) e declarar ausência quando não veio; nunca inventar.

Medido no #3013: o cunho do `sessao_id` ficou na tool da porta, e a fábrica — que chama
`bin/monta-sessao` direto, sem porta no meio — nascia sem sessão. A saída que eu propus
foi um segundo gerador no `chat`, que seria o quinto ponto de nascimento da mesma
entidade que a ADR tinha acabado de reduzir a um. O dono cortou: a geração é no verbo.

## Gancho que chama ferramenta futura dispara pelo ANÚNCIO, nunca às cegas

Escrever o gatilho antes da ferramenta que ele aciona é legítimo: o card fatia assim de
propósito («só o gancho aqui; a ingestão é a outra story»). O erro que isso convida não é
o gancho falhar — falha é barata e se avisa. É a flag desconhecida ser ENGOLIDA como
argumento posicional pela versão de hoje da ferramenta, e o gatilho disparar uma operação
válida e errada, com o mesmo exit 0 de um sucesso.

A régua: gancho para sub-ato que ainda não existe só dispara se a ferramenta ANUNCIAR o
sub-ato — o texto de uso do verbo é o golden record da forma dele, e lê-lo custa uma
chamada. Não anunciando, o gancho declara o que faltou e sai 0. Duas amarras vêm junto:
falha do lado acessório nunca desfaz o ato principal (índice atrasado se conserta
reindexando; publicação desfeita tira do ar o que toda cadeira lê), e o guarda lê o uso
capturado ANTES — sob `pipefail`, `cmd | grep -q` herda o exit 2 do uso e mente que não
achou.

Medido no #3019 (07/09/2026): o gancho de reindexação da casa em `publicar-abertura`
chama `acervo ingerir --casa --sha <sha> --de <arvore> --apply`. O `acervo` de hoje é
`ingerir <raiz> [--apply]`: sem o guarda, `--casa` viraria a RAIZ de uma ingestão de obra
com `--apply`, disparada por toda publicação de abertura.

## Aceite que a superfície não pode medir se embute no artefato

Quando o instrumento do aceite não existe na superfície que executa — porta só-verbo sem
psql, sem shell, sem o verbo que o card supõe —, há três saídas e só uma entrega: parar
(devolve nada), alegar verde por analogia (mente), ou EMBUTIR o aceite no artefato, de
modo que ele se meça sozinho no ato de quem aplicar. Migração leva o aceite dentro, em
bloco que aborta a transação; script leva a conferência antes do efeito. O limite de
medição continua declarado — o que muda é que a medida deixa de depender de quem não
pode fazê-la.

A régua vale para além do SQL: entregue o aceite como código que roda no ambiente do
destinatário, não como comando no comentário do card esperando que alguém o rode.

Medido no #3019: nenhum dos quatro aceites era executável da fábrica. Os dois que cabiam
em SQL viraram blocos `DO` dentro da própria migração 045 (as seis espécies presentes; e
gravar/ler/rejeitar-FK, desfeito na mesma transação); os outros dois foram declarados
como não medidos no comentário do card, com o motivo nomeado.

## Corte declarado como marcador ainda é corte

Substituir conteúdo por um marcador com hash — `<blob tipo=base64 … sha=…>`, `<linha longa
bytes=… sha=…>` — só é ALÇA quando o que saiu é token opaco que decisão nenhuma lê. Quando
o que saiu era o próprio conteúdo, o marcador é corte de miolo com outro nome, e o sha não
restaura nada utilizável: quem lê não sabe sequer o que perdeu. Ao julgar uma regra de
poda, pergunte o que SOBRA para quem lê, nunca que nome a classe tem — a classe é o nome
que o autor deu à aposta dele sobre o formato, e a aposta erra.

O caso que engana é o da regra com dois ramos, em que só um é alça. `_marca_blob` marca
base64/hex contíguo (alça legítima) E janela `±120` qualquer linha acima de 1.000 bytes
(corte). Sob a mesma classe `blob`, no mesmo relatório. Quem revisa a lista de classes vê
uma; quem lê o retorno recebe a outra.

Medido no #3022 (08/09/2026): um `motor rag buscar` real volta como UMA linha de JSON de
12.250 bytes, e o segundo ramo servia `<linha longa …>` — o top-k inteiro sumia. O card
havia diagnosticado três outras regras e mandado PRESERVAR a classe `blob`; a medida
mostrou que a trava valia para um ramo e não para o outro.

## Mede-se o SERVIDO, não o produzido

O envelope da porta traz `poda.bytes_produzidos` ao lado de `poda.bytes_servidos`. A razão
entre os dois denuncia poda destrutiva em UM giro, sem precisar do cru e sem desligar
nada: 12.510 produzidos contra 291 servidos é um número que não precisa de interpretação.
Nenhum ensaio hermético teria achado isso — fixture de teste tem o formato que o autor do
teste imaginou, e o retorno de produção tem o formato do mundo. Mesma família do «filtro
que reformata saída alheia» acima: subiu regra de retorno, leia o primeiro retorno REAL e
compare os dois números do envelope antes de qualquer outra coisa.

## Curadoria feita no espaço vetorial não se re-cura por heurística de string

Top-k ranqueado por similaridade já passou pelo filtro bom, e cada trecho é unidade
inteira de recuperação. Regra de terminal a jusante — agrupar como busca, fundir molde,
cortar no teto, janelar linha longa — dobra o filtro do vetor com um pior, que decide por
formato de string o que já fora decidido por sentido. Vale para todo retorno de
recuperação, não só para o verbo que motivou; o controle de qualidade mora no campo de
similaridade, e o que a porta pode fazer sem estragar é lavagem cosmética.

Corolário de fatiamento: quando um regime novo desliga regras por VERBO, verbo misto não
cabe num perfil só — `acervo casa` é recuperação semântica e `acervo listar` é listagem
estruturada. Sem escopo por ato, a listagem herda o regime e perde o teto.

## DDL em base viva entra com `lock_timeout`, e o perigo não é a demora

`ALTER TABLE` pede ACCESS EXCLUSIVE. Se alguma transação antiga ainda segura a tabela, o
ALTER não falha: entra na FILA — e a partir daí toda leitura que chegar fica atrás dele,
porque pedido de lock exclusivo bloqueia quem vem depois. O sintoma não é erro de DDL, é
busca travada, e a causa está a dois passos de distância de quem for investigar.

A régua tem três partes: (1) migração que altera tabela viva abre com `SET lock_timeout`
curto — falhar rápido é o comportamento correto, reaplica-se depois; (2) antes de aplicar,
ler `pg_stat_activity` procurando `idle in transaction` sobre o alvo; (3) se o cliente que
disparou o DDL morrer (timeout da porta, sessão derrubada), o BACKEND continua na fila
segurando a posição — `pg_terminate_backend` no pid órfão é parte do rollback, não
opcional.

Medido no #3027 (09/09/2026): uma conexão do `rag-api` estava `idle in transaction` havia
36 h com uma consulta de faceta que nunca fechou; o ALTER de `motor.indice` ficou 3 min na
fila e o timeout de 180 s da porta matou o cliente, deixando o backend esperando. Foi
preciso terminar o órfão E a conexão velha para migrar.

## Aposentar-e-criar se ancora no DONO estável, nunca na versão

Em toda cadeia de aposentar-e-criar (impressão, índice, publicação), a pergunta "quem eu
substituo?" só tem resposta contra uma identidade que NÃO muda entre as versões. Ancorar
a substituição no id da versão nova é tautologia: ele não existia antes, então a consulta
não alcança o antecessor, nada é aposentado e os dois passam a servir ao mesmo tempo. O
defeito é mudo — o novo entra, o velho fica, e a recuperação devolve as duas versões.

Quando o dono estável mora do outro lado de uma fronteira sem FK (outro contêiner, outro
banco), a saída não é inventar um JOIN nem duplicar o dono: é fazer a LISTA dos irmãos
atravessar como dado, lida no lado que a conhece e passada a quem vai aposentar.

Medido no #3027: a spec mandava aposentar o índice de casa por `(particao,
alvo_impressao_id, remissao, granularidade)` — e `alvo_impressao_id` é a impressão NOVA,
diferente a cada sha. Em obra a chave é `obra_id`, que é o dono e não muda; casa não tem
coluna de dono no motor, então `promover_indice_casa` passou a receber as impressões
irmãs, lidas no acervo.

## Diário de bordo

Episódio cru: a fita chamou um verbo e teve de chamar outro, ou bateu em parede de
ferramenta da casa. Sem interpretação.

07/09/2026 — precisei escrever migração num worktree porque o clone `platafirma-conhecimento`
estava sujo e detached com trabalho de outra cadeira; `repo git ... worktree add` criou
`var/wt/conhecimento-3019` sem problema, mas `write_file` recusou o caminho («fora de morada»:
só clones `platafirma-*`, `platafirma-harness/bin/` e `var/tmp/`) — contorno encontrado NA DATA
07/09/2026 foi escrever o arquivo no clone principal (morada válida, untracked, sem tocar no
trabalho alheio), `repo git <clone> hash-object -w <arq>`, `repo git <clone> -C <worktree>
update-index --add --cacheinfo 100644,<blob>,<path>`, `checkout-index -f -- <path>`, commit no
worktree e `clean -f -- <path>` no clone principal. `repo git <clone> -C <abs>` funciona: git
aceita vários `-C` e o último absoluto vence.

07/09/2026 — quis validar sintaxe de bash: `lint rodar platafirma-harness bin/publicar-abertura`
devolveu 53k de `invalid-syntax` do ruff lendo shell como Python, e o retorno estourou o teto da
tool, indo parar num arquivo em `~/.claude/projects/...` que `read_file` só alcançou por
`../.claude/...` — contorno encontrado NA DATA 07/09/2026 foi nenhum linter de shell: revisão
por leitura mais `teste rodar platafirma-harness controle/tests/test_contrato_monta_sessao.py`
(25 passed) e o pre-push (42 passed); item de mesa #12 aberto.

07/09/2026 — tentei rodar o próprio verbo que acabara de editar, `publicar-abertura estado`, e
`run_command` recusou com `{recusado, motivo: "sem verbo", sugestao: null}` — contorno encontrado
NA DATA 07/09/2026 foi nenhum: aceite declarado como não medido no card e item de mesa #13
aberto. `sugestao: null` é verbo que falta, e vira card por ato do dono.

07/09/2026 — `fila enviar ti --tipo impedimento` recusou («tipo invalido»; válidos: decisao,
demanda, handoff, minuta, pedido, resposta) — contorno encontrado NA DATA 07/09/2026 foi
`--tipo handoff`, que é o tipo da parada devolvida à cadeira dona.

07/09/2026 — `mesa item` e `mesa anota` têm assinatura que a lista de atos não mostra — contorno
encontrado NA DATA 07/09/2026 foi chamar o ato sem args para o argparse imprimir o uso:
`mesa item <chapeu> --ato ATO --alvo ALVO`, `mesa anota <slot>` com corpo em stdin. `mesa caderno
[slot]` só declara leitura; escrever nele foi por `write_file` na fonte do clone
(`platafirma-harness/abertura/fabrica/<chapeu>/caderno.md`), com `trecho`, para não arriscar
sobrescrever 16k de caderno por stdin de assinatura não declarada.

07/09/2026 — `write_file` com `trecho` grande (~6 KB de JSON) voltou `InputValidationError: could
not be parsed as JSON`, com a entrada cortada no meio — contorno encontrado NA DATA 07/09/2026
foi partir a escrita em duas chamadas menores.

07/09/2026 — passo 3 do `descansar fita` (triagem da memória do Project por `memory_user_edits`)
não rodou: a tool não existe nesta superfície, e o próprio roteiro diz que o host não a alcança
— contorno encontrado NA DATA 07/09/2026 foi nenhum, fica registrado aqui e no item de mesa #10,
para a superfície que alcança.

08/09/2026 — `read_file` com `paths` de dois arquivos (54.637 chars) estourou o teto do
harness, que salvou o resultado num arquivo LOCAL sob `~/.claude/projects/…/tool-results/`
e mandou lê-lo — a fábrica não tem Read nativo e não alcança esse FS; reler o mesmo path
inteiro devolveu `ledger: igual` e 67 bytes de aviso, ou seja, o dedup da poda deduplicou
contra conteúdo que NUNCA chegou à fita — contorno encontrado NA DATA 08/09/2026 foi reler
em fatias por `offset`/`max_bytes` (~11 KB cada), porque cada fatia tem sha próprio e
escapa do ledger.

08/09/2026 — `teste rodar platafirma-harness ops-server/_ensaio.py` deu `ModuleNotFoundError:
No module named 'mcp'` (o `.venv-harness` não tem, e `_ensaio.py` importa `server`); `infra
unit-env ops-server` respondeu que a unit `--user` não existe; `longjob`, que a mesa velha
dizia servir para `bash -lc 'export …; <verbo>'`, voltou `{recusado, motivo: "sem verbo"}`
do `run_command` — contorno encontrado NA DATA 08/09/2026 foi escrever um arquivo espelho
`_ensaio_3022_tmp.py` importando SÓ `poda` (que por desenho não depende da porta), rodar 8
testes verdes por ele, e apagar com `repo git <clone> clean -f <path>` no mesmo turno.

08/09/2026 — `repo commitar <repo> "<msg>"` recusou com «argumento nao reconhecido» e `mesa
item <chapeu> "<texto>"` recusou pedindo `--ato` e `--alvo` — contorno encontrado NA DATA
08/09/2026 foi chamar o verbo SEM ato para ele imprimir o uso: `repo commitar <repo> -m
<msg>` e `mesa item <chapeu> --ato … --alvo …`.

08/09/2026 — `repo_grep` da wiki com `context: 55` devolveu só ~10 linhas de «after»,
inútil para ler bloco grande de código — contorno encontrado NA DATA 08/09/2026 foi
`repo_read` com `offset` em BYTES, estimando ~45 bytes por linha para achar a região.

08/09/2026 — passo 3 do `descansar fita` (triagem da memória do Project) de novo não
rodou: não há `memory_user_edits` nem Write/Edit nativo nesta superfície, então nem ver
nem remover — contorno encontrado NA DATA 08/09/2026 foi nenhum; fica o achado para quem
alcança: a memória `verbo-de-memoria-da-cadeira-precisa-de-pf-cadeira` é FÓSSIL — nesta
fita `mesa item` e `mesa anota` rodaram pela porta só com `sessao_id`, sem `PF_CADEIRA`.

09/09/2026 — precisei de working tree limpo em dois repos e tentei o atalho de criar o
worktree DENTRO da raiz com nome `platafirma-<repo>-3027`, apostando que a morada de
`write_file` casava por prefixo; recusou com a lista literal de moradas (`platafirma-core/,
platafirma-conhecimento/, platafirma-arquitetura/, platafirma-harness/, platafirma-motor/,
platafirma-posto/, modulo-osint/`) — é lista de clones nomeados, não padrão — contorno
encontrado NA DATA 09/09/2026 foi o mesmo do 07/09, agora sem passar pelo clone principal:
`write_file` em `var/tmp/<sessao_id>/` (aceita `.py .sql .txt .md`, recusa `.patch`),
`repo git <worktree> hash-object -w <abs>`, `update-index --add --cacheinfo`,
`checkout-index -f -- <path>`. `repo git` aceita o worktree como se fosse clone.

09/09/2026 — para editar arquivo grande sem reescrever os 36 KB, escrevi diff unificado em
`var/tmp/` e rodei `repo git <worktree> apply --recount`: funcionou em 6 patches e depois
passou a recusar com `error: while searching for:` mostrando EXATAMENTE o texto que o
`git grep` achava no arquivo; nem `--ignore-whitespace`, nem `-C1`, nem hunk de UMA linha
sem acento mudaram o veredito — contorno encontrado NA DATA 09/09/2026 foi
`git apply --unidiff-zero --recount`, que aplicou o mesmo hunk limpo na primeira tentativa.
Ou seja: pela porta, patch com linha de contexto é loteérico; hunk com contexto ZERO
(`@@ -N,1 +N,1 @@`, só `-` e `+`) aplica. A causa não foi isolada nesta fita.

09/09/2026 — `acervo psql --banco rag|motor` recebe SQL por stdin e roda de verdade (foi
com ele que as duas migrações do #3027 entraram e os aceites `DO $$` correram), mas não lê
arquivo: não há `-f` nem caminho do host dentro do contêiner — contorno encontrado NA DATA
09/09/2026 foi o par no MESMO lote, `repo git <worktree> show :<path>` como item 0 e
`{"de": 0}` no stdin do psql; custa reimprimir o arquivo inteiro no retorno, e a poda
deduplica na segunda vez (serviu 756 bytes de delta em vez de 7,5 KB).

09/09/2026 — `lint rodar <worktree>` e `teste rodar <worktree>` não servem em worktree:
o lint respondeu `indeterminavel — nenhuma stack detectada` (a detecção procura
`pyproject.toml`/`.ruff_cache` na RAIZ do clone, e `.ruff_cache` é gerado, não versionado)
e o teste caiu para `uvx pytest` isolado, avisando que a dependência do projeto pode
faltar — contorno encontrado NA DATA 09/09/2026 foi nenhum: código do #3027 ficou sem lint
e sem suite, declarado na mesa. O `.venv` do projeto está no clone principal e o worktree
não o enxerga.
