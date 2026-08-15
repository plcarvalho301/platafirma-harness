# caderno — iam

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Régua: gate de rede na frente de serviço que já autentica

Três perguntas, nesta ordem. A terceira anula as duas primeiras quando é sim.

1. A superfície pré-auth é grande ou imatura? (muito endpoint anônimo, extensão, CVE pré-auth)
2. O cliente é exclusivamente navegador? (havendo app/CLI/webhook, o custo é quebrar cliente)
3. O serviço é alcançável por outro caminho? (sendo, a borda é enfeite)

Duas camadas que validam contra o MESMO IdP não são defesa em profundidade — falham
juntas. O que a camada entrega é redução de superfície alcançável, não segunda
autenticação. A pergunta certa nunca é "autenticar duas vezes?", é "quero que
requisição não autorizada toque o código deste serviço?".

Custo sempre subestimado: a borda autoriza por allowlist de e-mail, o serviço autoriza
por papel no realm — dois mapas de quem-alcança-o-quê, que divergem em silêncio.

## Token opaco não se valida na borda

Validador de borda para token opaco exige o estado do emissor, e ter o estado do
emissor é ser o emissor. Consequência: token exchange, gateway mediador e casca do
serviço na borda colapsam todos, pelo mesmo motivo.

O requisito comum das três saídas é o mesmo: token auto-contido e do emissor que a
borda conhece. Havendo JWT assinado, validação de borda é JWKS em memória e nenhuma
das três é necessária. Quando o requisito de cliente nativo for real, a resposta é
MUDAR O EMISSOR, não construir tradutor no caminho.

Distinção que confunde porque as duas terminam em 401:
- audiência incompatível  -> token exchange resolve
- portador incompatível   -> nada resolve sem mudar cliente ou emissor

Cliente nativo SEGUE redirect de browser para SSO (aba do sistema + deep link). O que
ele não faz é carregar cookie de sessão nas chamadas de API.

Ensaio completo: wiki, PlataFirma:Sec/autenticacao-de-borda

## Duas famílias de superfície no core

Serviço SEM auth própria -> atrás do oauth2-proxy (wiki, harness).
Serviço COM auth própria -> direto, gate próprio contra o realm (vikunja, mcp, Synapse).
Classificar na família errada é o erro que custou duas cartas retificadas em 14/08.

Entrando sem gate de rede, quatro contrapartidas deixam de ser recomendação: registro
desabilitado, login local por senha desabilitado, rate limit de login, painel admin só
na rede interna.

## Padrões da casa, medidos

- clientId de serviço no realm `platafirma`: opaco, 6 chars A-Z0-9 (L0R8OJ, SQ53VU).
- Secret de stack: ~/AI/var/secrets/<stack>/, dir 700, arquivo 600. Nunca no compose,
  nunca no git, nunca na fila.
- Conta isolada nova: uid sequencial, home 700, faixa subuid/subgid disjunta de 65536
  (megafone 100000, claudinho 165536, modulo-osint 231072, jaiminho 296608), linger on,
  grupo único, sem sudo.
- `seg keycloak` exige `kcadm.sh config credentials` a cada sessão; a credencial sai de
  platafirma-core/.env, e o realm de trabalho é `platafirma` (não `master`).
- Caixa alheia não se lê: `fila ler <outra-persona>` é recusado pelo próprio verbo,
  inclusive com --tudo. Não há como reler carta que eu mesmo enviei.
