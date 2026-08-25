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

## Padrões da casa, medidos

- Secret de stack: ~/AI/var/secrets/<stack>/, dir 700, arquivo 600 — nunca compose/git/fila.
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
