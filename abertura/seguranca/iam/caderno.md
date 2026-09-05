# caderno — iam
Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Régua: gate de rede na frente de serviço que já autentica

Três perguntas, nesta ordem; a terceira anula as duas primeiras quando é sim. (1) a
superfície pré-auth é grande ou imatura? (2) o cliente é exclusivamente navegador? — havendo
app/CLI/webhook, o custo é quebrar cliente; (3) o serviço é alcançável por outro caminho? —
sendo, a borda é enfeite. Duas camadas contra o MESMO IdP não são defesa em profundidade:
falham juntas. O que a camada entrega é redução de superfície alcançável, não segunda
autenticação.

## Token opaco não se valida na borda

Validar token opaco na borda exige o estado do emissor, e ter esse estado é ser o emissor —
token exchange, gateway mediador e casca do serviço colapsam todos aí. A saída é MUDAR O
EMISSOR para JWT assinado, nunca construir tradutor no caminho. Distinção que confunde
porque as duas dão 401: audiência incompatível o token exchange resolve; portador
incompatível não se resolve sem mudar cliente ou emissor.
Ensaio completo: wiki, PlataFirma:Sec/autenticacao-de-borda

## Duas famílias de superfície no core

Serviço SEM auth própria -> atrás do oauth2-proxy (wiki, harness). COM auth própria ->
direto, gate próprio contra o realm (mcp, Synapse, rastreador). Classificar na família
errada custou duas cartas retificadas em 14/08.

Na primeira família NÃO HÁ SUJEITO dentro do serviço: o proxy autentica e encaminha, e o
serviço vê anônimo (medido 16/08 na wiki: grupo `*` com `read`, `edit`, `createpage`). A
régua da borda é binária e por allowlist de e-mail, que não conhece papel nem domínio —
segundo mapa de quem-alcança-o-quê, divergindo em silêncio do realm. Diferenciar acesso
DENTRO do serviço exige antes dar-lhe identidade (PluggableAuth+OIDC no MediaWiki), e mesmo
com sujeito a ACL do MediaWiki só reconhece NAMESPACE. Entrando sem gate de rede, três
contrapartidas deixam de ser recomendação: registro e login local por senha desabilitados,
rate limit de login, painel admin só na rede interna.

## Ato sobre identidade se confere contra o caminho por onde eu opero

Antes de renomear, desabilitar ou apagar sujeito, listar o que depende dele para EU
continuar operando — não só o que depende dele em geral. Caso 14/08: renomeei o username do
dono no realm depois de conferir vikunja, wiki, allowlist e token do mcp, todos intactos, e
não conferi o gate por onde eu opero — o PEP resolve por `preferred_username` contra
`sujeitos.yaml`, o nome velho estava lá, e o rename trancou TODAS as cadeiras fora do
ops-mcp de uma vez.

Recuperação é cara: o admin console é loopback-only (`/admin` dá 404 na borda) e quem
destrava é o dono no terminal do host. Mudança de identidade que possa alcançar
`sujeitos.yaml` precisa da correção preparada ANTES do ato.

## Revogar credencial a partir de lista de terceiro

A lista que a outra cadeira manda descreve o que ela lembra, não o que o arquivo tem. Três
passadas antes de apagar: **separar credencial de configuração** (conferir contra quem
LÊ a chave hoje, não contra o nome); **grep por nome de chave, nunca por menção** (duplicata
em `.env` é silenciosa: por chave deu 5, por linha 7); **reescrever com verificação, não
`sed`** (afirmar antes de gravar que as demais seguem byte a byte, e reaplicar 600 depois).
Ordem: primeiro o realm (apagar o client mata service account e secret juntos), depois o
`.env`. Fecha quando `acesso orfaos` perde o achado — a única confirmação que não depende
da minha narrativa.

Corolário aprendido em 04/09, apagando o client L0R8OJ: **perder o achado só conta se a
medição foi COMPLETA**. `acesso orfaos` tem um terceiro veredito além de achou/não-achou —
`REPROVADO: realm NAO medido`, exit 2 — e ele sai quando o kcadm não alcançou o realm de
dentro do próprio verbo. Nesse estado o verbo lista os achados de SO e banco normalmente, o
que engana — parece resultado. Ler o exit code, não a lista. Fecho declarado com `get`
devolvendo vazio é menos que fecho medido, e a diferença é justamente a que o auditor pede.

CORRIGE o que esta entrada dizia até 04/09 (noite): eu havia anotado que refazer o login do
kcadm à mão "NÃO alcança o verbo, porque o caminho que o verbo usa é outro". É falso, e
custou uma fita inteira de exit 2. Não há dois caminhos: o `seg keycloak` e o login pelo
`docker exec` gravam e leem o MESMO `~/.keycloak/kcadm.config` dentro do contêiner. Refeito
o login lá dentro, o verbo passa a alcançar o realm na chamada seguinte, sem mais nada — e
`acesso orfaos` sai de exit 2 para exit 1 no mesmo giro. O que não alcança é login feito no
HOST, que grava noutro arquivo. Diagnóstico velho, quando não é refutado, vira muro
imaginário: o de baixo (\"a sessão do kcadm expira\") já trazia a forma certa, e eu não a
tentei porque esta entrada dizia que não adiantava.

## Gate de borda com mais de um upstream (oauth2-proxy v7)

MÉTODO, que vale mais que o caso: subir instância DESCARTÁVEL da mesma imagem na mesma
rede, com `--skip-auth-route='GET=^/'` e credencial falsa — mede roteamento sem encostar em
produção. Medido 16/08:

- O proxy DECLARA o mapa no boot (`mapping path "/api/" => ...`); ler o log é a conferência.
- **O path não é removido no repasse**: upstream `.../api/` casa o prefixo e encaminha o
  caminho inteiro, então quem serve tem de responder em `/api` de verdade. Mais específico
  primeiro, e `/api` SEM barra não casa: cai no upstream `/`.
- **Travessia não vira bypass**: `../`, `..%2f` e `%2e%2e` levam 301 de canonicalização no
  próprio mux ANTES do repasse. Isso é propriedade do mux, não do regex de skip-auth, e se
  reconfere a cada troca de versão.
- Rota anônima aponta para o contêiner que a serve: tirá-la da imagem que monta o `.env`
  encolhe a superfície de injeção de cabeçalho de sujeito, sem tocar na política.

## Auditoria que resolve identidade dentro de si mesma fecha ciclo em token ruim

Extrair `_sujeito_do_jwt` para módulo comum e fazer `_audit` chamar `_quem()` parece
inofensivo até o token ser inválido: a recusa dentro de `_sujeito_do_jwt` chama de volta
`auditor=_audit`, que chama `_quem()`, que chama `_sujeito_do_jwt` de novo. Sem guarda de
reentrância, todo Bearer malformado derruba a porta — medido em 25/08, RecursionError
depois de 67 voltas. Não é bug raro: é o CAMINHO DE RECUSA, o mais chamado de todos.

Um servidor pode escapar do mesmo ciclo por acidente de formato (ex.: `_audit` só resolvia
identidade quando `tool != "-"`, e a recusa saía com `tool="-"`) — isso não prova que o
desenho está certo, prova que ninguém bateu no caso ainda. Ao revisar código que unifica
resolução de identidade com auditoria, achar o ciclo é o primeiro teste, não o último:
simular a recusa (token malformado) contra a versão nova ANTES de olhar o resto do diff.

## Forma da cadeira: três matérias e uma régua

`risco` não é gerência ao lado das outras — é o MODO da cadeira. Descoberto escrevendo o
chapéu dele (16/08): a régua que saiu era palavra por palavra a POSTURA da base. Por isso
não pode morar em chapéu, que carrega condicionalmente: a régua tem de estar ligada
justamente quando estou de outro chapéu. O escopo também não anda sozinho — são quatro
perguntas que só aparecem DENTRO do trabalho alheio. Agrega quando chega junto da mudança,
descrevendo-a melhor do que quem a propôs, não quando autoriza; e chega tarde por desenho,
porque o gatilho é o deploy e não o nascimento do card.

## O PAP afirma; só o PDP decide — e é o domínio PAI, não herança, que mata a negativa

O `politica.yaml` é prosa comentada com generosidade, e os comentários dizem coisas
verdadeiras sobre o próprio arquivo ("o default do PDP é negar", em duas linhas distintas).
Assinar embaixo de comentário é o erro barato de cometer e caro de descobrir: comentário
declara a INTENÇÃO de quem escreveu a regra, não o comportamento do motor que a avalia.
`acesso decidir --papel … --dominio … --acao … --recurso …` não toca banco e devolve o
veredito com a regra que o produziu — quando volta `NEGADO regra=default`, isso é a
medição, e é o que se cita para outra cadeira. Perguntado se o default fecha, eu respondo
com quatro casos rodados, incluindo um domínio e uma ação inexistentes; não com número de
linha.

**A pergunta que parece a certa quase sempre é a errada.** Quando o TI pediu conferência do
recorte do quinzinho, a dúvida oferecida era "negativa nomeada basta, ou preciso de
catch-all?" — e a resposta é que basta, porque o default fecha. Mas medir o default só
prova o que acontece SEM concessão. O buraco estava no lado oposto: `reino`, detendo o PAI
`plataforma`, sai PERMITIDO quando perguntado sobre `plataforma-drive`.

**Não é herança, e chamar de herança manda a próxima fita caçar uma engrenagem que não
existe** — anotei "a herança do eixo domínio é real e desce sozinha" em 04/09 (tarde) e a
medição da mesma noite refutou. São duas peças somadas, e é a soma que ninguém vê:

- `intersecao` exige que o sujeito detenha o domínio DO RECURSO, e ele SEGURA:
  `reino + [plataforma-acervo] → plataforma-drive` dá `NEGADO regra=intersecao`.
- `reino-plataforma-tudo` tem `acoes: ["*"]` e `sobre: ["*"]` — não trava nada DENTRO dos
  domínios que o sujeito já alcança.

Deter o pai satisfaz a interseção contra cada filho, um por um, e a segunda regra libera
tudo neles. As quatro medidas: `[plataforma]→drive` PERMITIDO; `[plataforma]→identidade`
PERMITIDO; `[acervo,wiki]→acervo` PERMITIDO; `[acervo,wiki]→identidade` NEGADO.

A consequência prática é a mesma de antes e por isso a condição não mudou — toda trava
construída como negativa por domínio nomeado tem a premissa não escrita de que ninguém
conceda o pai, e cai sem que regra nenhuma esteja errada. Mas o mecanismo certo diz ONDE
olhar: para um papel com `acoes`/`sobre` irrestritos, a LISTA DE DOMÍNIOS do sujeito é a
única superfície de controle que existe — quem edita essa lista edita o controle inteiro.
Conferência de recorte que audita só as regras escritas está incompleta por construção:
audita-se o que a CONCESSÃO pode citar. Por isso OK de alcance sai condicionado ao domínio
FILHO nomeado, e a condição é parte do OK, não recomendação.

Régua que sobra das duas versões: **hipótese de mecanismo não vira entrada de caderno sem
o caso de controle rodado.** "Herança" explicava o PERMITIDO e por isso pareceu suficiente;
faltava rodar o caso que a refutava — o sujeito com só o filho. Um PERMITIDO confirma que
alguma coisa permite, nunca QUAL. As medidas moram em `politica.yaml`, no comentário sobre
`reino-plataforma-tudo` (commit 6aa3e33), que é onde quem for editar a regra vai ler.

## Trilha que não existe não é ato sem autor — e não se leva ao dono como suspeita

Perguntado "quem desabilitou este client?", o reflexo é caçar o autor. Antes disso: conferir
se o sistema GRAVA autor. Medido 04/09 — o realm `platafirma` estava com `eventsEnabled:
false` E `adminEventsEnabled: false`, e nunca gravou um ato administrativo sequer. A pergunta
não tinha resposta possível, e a diferença importa porque as duas situações produzem a mesma
tela vazia: ato deliberadamente apagado e ato nunca registrado. Sem instrumento não há
achado — há falta de instrumento, que é ato meu de corrigir, não suspeita para levar ao dono.
Levar como suspeita queima confiança de outra cadeira por uma lacuna que é minha.

Corolário sobre o próprio instrumento: `adminEventsDetailsEnabled` guarda o CORPO da
requisição, e corpo de update de client carrega `secret` em claro. Ligar details troca um
buraco de auditoria por um depósito de segredo no banco. Quem/o-quê/onde já responde à
pergunta de responsabilidade — `operationType`, `resourcePath`, `userId`, `ipAddress` saem
sem details. Antes-e-depois não vale esse preço, e a escolha se declara para quem for
auditar, senão parece descuido.

E a régua que fecha: **controle só conta verificado por execução, não por configuração**.
Ligar a flag e ler a flag de volta prova que a flag está ligada, não que o evento é gravado.
Provar é gerar um ato e achá-lo em `get admin-events`. Contraponto honesto, que fica como
próximo passo e não como conquista: trilha que ninguém LÊ ainda não é detecção — vale como
registro até algum verbo passar a consultá-la.

## Deletar conta de SO não reduz superfície quando o uid é reciclável

O pedido chega como "mata a conta" e o reflexo é `userdel`. Medir o resíduo antes: quem mais
no disco pertence àquele uid. Em 04/09, o `modulo-osint` (uid 1002) possuía o home E sete
cópias dele dentro de `/timeshift/snapshots/`. Deletado o cadastro, o uid volta à fila — e,
sendo o menor livre da faixa, a PRÓXIMA conta criada o recebe e herda a propriedade de tudo
aquilo, sem que ninguém tenha decidido nada. Deletar não limpa: transfere a herança para um
estranho, e o transfere calado.

Ordem que preserva as duas coisas (superfície pequena e dado intacto):
`usermod -L -s /usr/sbin/nologin` primeiro — inerte, reversível com `-U`, não destrói nada e
resolve HOJE; o destino dos dados depois, com calma; `userdel` por último e só com o uid
queimado ou os arquivos chowneados antes.

Duas distinções que a mesma noite cobrou, e que valem para todo desligamento de conta:
- **Runtime caído ≠ conta morta.** Derrubar a sessão apaga processo, socket e
  `/run/user/<uid>`; o cadastro, o shell e o home continuam. `acesso orfaos` segue apontando,
  corretamente. Quem relata "matei a conta" costuma ter matado o runtime — conferir o
  `getent passwd`, não a frase.
- **`disable-linger` é o que faz durar.** Só o `stop` derruba hoje e o lingering remonta a
  sessão inteira no próximo boot. A ordem é `disable-linger` e depois `stop`, e o que se
  verifica é o sumiço de `/var/lib/systemd/linger/<conta>`.

Limite que se declara em vez de encobrir: home 0700 de outra conta não se lê sem root, então
"não há chave SSH autorizada" é afirmação que eu não posso fazer. O que se relata é o que se
mediu — e que `.ssh` ficou fora do alcance.

## Padrões da casa, medidos

- Secret de stack: ~/AI/var/secrets/<stack>/, dir 700, arquivo 600 — nunca compose/git/fila.
- `seg keycloak -- …` (e todo passthrough do `seg`) executa DENTRO do contêiner: endereço
  que vale é o de lá (`http://localhost:8080`), não o publicado no host
  (`127.0.0.1:8180`, que dá `Connection refused` e parece serviço fora do ar).
- Conta isolada nova: uid sequencial, home 700, faixa subuid/subgid disjunta de 65536,
  linger on, grupo único, sem sudo.
- `conferir superficie` é HOMÔNIMO: julga superfície de SESSÃO (claude.ai, code-seco,
  fabrica, fita), não superfície externa em produção. O classificador que falta ao gate
  precisa de outro nome.
- Caixa alheia não se lê, nem com --tudo: não há como reler carta que eu mesmo enviei.
- Slug da cadeira é a forma nua (`seguranca`) em todo verbo; o prefixo
  `claudinho-`/`claudinha-` é aceito e descartado na normalizacao. Errar a
  GRAFIA do slug, porém, não dá erro — abre um segundo armazém, plausível e vazio.
- **Medir uma superfície e concluir sobre o arranjo**: serviço existe em host E em contêiner, e
  `ss -ltnp` só vê o host — dois erros meus em 20/08 vieram daí. Perímetro se mede nas duas:
  `ps -eo uid`, `docker inspect -f '{{.Config.User}}'`, e onde os volumes moram.

## Comando de conta precisa do principal E do env — a sessão não se presume

Runbook que entrega comando escopado a usuário (`systemctl --user`, docker rootless, path com
`~`) para um operador que loga como OUTRA conta falha em três pontos — todos vividos em 25/08
passando a Onda 5 (#2678) do dono (conta `megafone`, uid 1000) para os serviços (conta
`claudinho`, uid 1001):

- **`~` mente.** `~/AI/...` vira `/home/megafone/AI` na mão do dono, não `/home/claudinho/AI`.
  Runbook cross-conta usa caminho ABSOLUTO, sempre.
- **`docker` sem contexto bate no daemon errado.** megafone está no grupo `docker`, então
  `docker compose ... --build` foi para o daemon de SISTEMA, não para o rootless do claudinho
  onde a prod vive. Build que "rodou" e não tocou nada. Rootless é POR conta: o socket é
  `/run/user/<uid>/docker.sock` — o do claudinho é `/run/user/1001/docker.sock`.
- **`sudo -iu claudinho systemctl --user` dá `Failed to connect to bus: No medium found`.**
  O login-shell troca de usuário mas NÃO anexa ao bus do user-manager que já roda (lingering).
  Precisa do env do runtime: `XDG_RUNTIME_DIR=/run/user/1001` e
  `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus`. Formas que funcionam:
  `sudo -u claudinho env XDG_RUNTIME_DIR=... DBUS_SESSION_BUS_ADDRESS=... systemctl --user ...`,
  `sudo machinectl shell claudinho@`, ou `sudo systemctl -M claudinho@ --user ...` (systemd 255).

Regra: comando de conta declara o principal E carrega o env (runtime dir, bus, socket do
docker, caminho absoluto). "Roda como claudinho" em prosa não basta — o mecanismo de VIRAR
claudinho tem que montar o ambiente, senão o comando cai num contexto plausível e vazio, que
é o pior modo de falhar: não erra alto, erra quieto (mesma família do slug com grafia errada
que abre um segundo armazém vazio). Corolário: o ops-server não se reinicia de dentro de si
(mata a própria tool call), então o restart dele é sempre ato de terminal DE FORA — e por isso
cai justamente na conta do operador, que é onde este bug mora.

## Sessão do kcadm expira, e reautenticar não precisa passar o segredo por mim

`seg keycloak -- ...` é passthrough para o `kcadm.sh` DENTRO de
`platafirma-core-keycloak-1`, e o kcadm guarda a sessão em arquivo no contêiner. Ela expira
sozinha: `Session has expired. Login again with 'kcadm.sh config credentials'`. Isso não é
incidente, é o estado normal de qualquer fita que não operou o realm recentemente — e é
muro que já parou cadeira de fora no meio de um expurgo (TI, 02/09, client L0R8OJ), com o
ato passando adiante por handoff em vez de por falta de alcance.

O reflexo errado é procurar a senha do admin para digitá-la no comando. Não procure: o
contêiner JÁ a tem no próprio ambiente, e o login se refaz de lá de dentro, sem o segredo
atravessar o contexto da sessão nem o log de auditoria do `run_command`:

    docker exec platafirma-core-keycloak-1 sh -c \
      '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 \
         --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
         --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" \
       2>&1 | sed "s/$KC_BOOTSTRAP_ADMIN_PASSWORD/<oculto>/g"'

Três coisas que a forma carrega, e que é o que vale guardar: (1) o segredo é lido e gasto no
mesmo processo que já tinha direito a ele — quem opera nunca o vê; (2) o `sed` na saída é
cinto de segurança contra a ferramenta ecoar o que recebeu; (3) `env | sed 's/=.*/=<oculto>/'`
é como se descobre o NOME da variável sem colher o valor — descobrir onde o segredo mora não
exige lê-lo. Régua geral: segredo que já está do lado de lá não se traz para cá; leva-se o
comando até ele.

## Grão de leitura se decide pelo produto, não pelo aviso do fornecedor do motor

O mediawiki.org diz «não foi desenhado para restrição por página» — e eu vetei ABAC na
wiki por isso, respondendo «instância» na 0024 (05/09). O dono derrubou em dois turnos: a
wiki É a camada de leitura do acervo; leitor não lê banco; logo o grão é a PÁGINA, ou o
produto não existe. Vetar era a patologia da persona (casco que ninguém entra) vestida de
prudência. A régua que sobra: **pergunte primeiro «esta superfície é a de leitura do
produto?»** — sendo, o grão é o que o produto precisa, e o trabalho de segurança é pagar o
mecanismo, não negá-lo. Bench de mercado (Confluence/Notion/BookStack, manifesto m:7–m:16)
serve para nomear o custo, não para decidir o grão.

O que «pagar o mecanismo» é, no MediaWiki, e vale para qualquer motor que avise «não
desenhado»: (1) sujeito dentro do motor (sem identidade lá dentro não há grão); (2) um
hook, uma pergunta ao PDP da casa, zero regra no motor; (3) a lista oficial de furos do
fornecedor vira SUÍTE que roda como sujeito sem concessão e é gate de upgrade; (4) porta
lateral que não fecha por hook se remove e se substitui por peça nossa — a busca da wiki
sai e o motor da casa entra, porque aí a decisão é de ponta a ponta; (5) atributo de
página escrita por humano vem do CAMINHO, nunca de campo editável (o `move` da Lockdown por
outra porta); (6) intermediário que serve leitura (motor de busca) tem sujeito próprio para
trilha, mas decide cada resultado contra o sujeito do LEITOR — acesso delegado, mesma régua
da `inferencia-escopada`. Risco aceito escrito: o resíduo é a porta que um upgrade abre;
dono seguranca; reabre sem a suíte verde.

Erro de forma que custou um turno de confiança: usei «segregação» em dois sentidos entre
turnos (tranca na wiki × recorte de conteúdo) sem avisar, e o dono leu contradição. Palavra
que muda de sentido entre turnos se declara no turno em que muda.

## `acesso decidir`: o que o veredito NÃO diz (tipo, existência, casamento de nome)

`acesso decidir` é a medição da política — mas o veredito, sozinho, esconde três coisas
que a varredura de permissionamento da jaiminho (05/09) cobrou uma a uma:

- **O tipo é parte da pergunta, não opcional.** A regra casa por `tipo:` no `quando`, e o
  PEP carimba o tipo em runtime. Rodar `acesso decidir` sem `--tipo` (ou com o errado)
  devolve `NEGADO regra=default` mesmo HAVENDO regra que permite. Medido: `rag_buscar` sem
  `--tipo acervo` → NEGADO/default; com `--tipo acervo` → PERMITIDO/`fabrica-le-acervo-inteiro`.
  Falso-negativo por tipo omitido é indistinguível de política fechando de verdade — sempre
  passar o tipo que o PEP carimbaria naquela chamada.
- **PERMITIDO é sobre POLÍTICA, não sobre existência nem alcançabilidade.** O PDP avalia a
  regra; não checa se o verbo existe. `teste_rodar`/`repo_*` saem PERMITIDO por
  `fornecedor-usa-verbo-operacional` e NÃO EXISTEM (`conferir verbo` não os lista) — regra
  viva para verbo inerte. "Pode chamar o verbo V?" exige TRÊS medidas, não uma: `acesso
  decidir` (a política permite) E `conferir verbo` (o verbo existe) E o nome-da-ação casa o
  verbo.
- **Concessão por nome-de-ação que não bate o verbo é concessão que a superfície não
  alcança.** O acervo é concedido ao fornecedor via ações `rag_buscar`/`rag_facetas`, mas o
  verbo servido chama-se `acervo` — e o verbo `acervo` sai NEGADO enquanto `rag_buscar` sai
  PERMITIDO. Resultado medido: 0 usos do acesso concedido em 11 dias. Conceder a ação certa
  com o nome que o verbo NÃO emite é conceder no papel e negar na porta. Ao escrever regra,
  conferir que o `acoes:` casa o nome que a tool/verbo de fato submete ao PEP, não o nome
  conceitual da operação.
