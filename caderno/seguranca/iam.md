# caderno — iam

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Régua: gate de rede na frente de serviço que já autentica

Três perguntas, nesta ordem. A terceira anula as duas primeiras quando é sim.

1. A superfície pré-auth é grande ou imatura? (muito endpoint anônimo, extensão, CVE pré-auth)
2. O cliente é exclusivamente navegador? (havendo app/CLI/webhook, o custo é quebrar cliente)
3. O serviço é alcançável por outro caminho? (sendo, a borda é enfeite)

Duas camadas contra o MESMO IdP não são defesa em profundidade — falham juntas. O que a
camada entrega é redução de superfície alcançável, não segunda autenticação. A pergunta
certa é "quero que requisição não autorizada toque o código deste serviço?".

## Token opaco não se valida na borda

Validar token opaco na borda exige o estado do emissor, e ter esse estado é ser o
emissor. Token exchange, gateway mediador e casca do serviço colapsam todos por aí. A
saída é MUDAR O EMISSOR para JWT assinado — com JWKS em memória nenhuma das três é
necessária —, nunca construir tradutor no caminho.

Distinção que confunde porque as duas terminam em 401: audiência incompatível, que o
token exchange resolve; portador incompatível, que nada resolve sem mudar cliente ou
emissor. Cliente nativo SEGUE redirect de browser para SSO; o que ele não faz é carregar
cookie de sessão nas chamadas de API.

Ensaio completo: wiki, PlataFirma:Sec/autenticacao-de-borda

## Duas famílias de superfície no core

Serviço SEM auth própria -> atrás do oauth2-proxy (wiki, harness).
Serviço COM auth própria -> direto, gate próprio contra o realm (mcp, Synapse, rastreador).
Classificar na família errada é o erro que custou duas cartas retificadas em 14/08.

Na primeira família NÃO HÁ SUJEITO dentro do serviço: o proxy autentica e encaminha, e o
serviço vê anônimo (medido 16/08 na wiki: grupo `*` com `read`, `edit`, `createpage`). A
régua da borda é binária — entra tudo ou não entra —, e por allowlist de e-mail, que não
conhece papel nem domínio: segundo mapa de quem-alcança-o-quê, divergindo em silêncio do
realm. Diferenciar acesso DENTRO do serviço (ler sim, escrever não) exige antes dar-lhe
identidade — PluggableAuth+OIDC no MediaWiki, equivalente no resto. E no MediaWiki, mesmo
com sujeito, a ACL só reconhece NAMESPACE: domínio, categoria e subpágina não se fecham.

Entrando sem gate de rede, quatro contrapartidas deixam de ser recomendação: registro e
login local por senha desabilitados, rate limit de login, painel admin só na rede interna.

## Ato sobre identidade se confere contra o caminho por onde eu opero

Antes de renomear, desabilitar ou apagar sujeito, listar o que depende dele para EU
continuar operando — não só o que depende dele em geral.

Caso, 14/08/2026: renomeei o username do dono no realm depois de conferir vikunja, wiki,
allowlist do proxy e token do mcp — todos intactos. Não conferi o gate por onde eu opero:
o PEP resolve sujeito por `preferred_username` contra `politica-acesso/sujeitos.yaml`, e o
nome velho estava lá. O rename trancou TODAS as cadeiras fora do ops-mcp de uma vez.

Recuperação é cara: o admin console do Keycloak é loopback-only (`127.0.0.1:8180`; `/admin`
dá 404 na borda), e quem destrava é o dono no terminal do host. Toda mudança de identidade
que possa alcançar `sujeitos.yaml` precisa da correção preparada ANTES do ato.

## Revogar credencial a partir de lista de terceiro

A lista que a outra cadeira manda descreve o que ela lembra, não o que o arquivo tem.
Três passadas antes de apagar: **separar credencial de configuração** (conferir contra quem
LÊ a chave hoje, não contra o nome — `VIKUNJA_BASE` era rota, não segredo); **grep por nome
de chave, nunca por menção** (duplicata em `.env` é silenciosa: por chave deu 5, por linha
7); **reescrever com verificação, não `sed`** (afirmar antes de gravar que as demais seguem
byte a byte, e reaplicar 600 depois do `os.replace`).

Ordem do ato: primeiro o realm (apagar o client mata service account e secret juntos),
depois o `.env`. Fecha quando `acesso orfaos` perde o achado — a única confirmação que não
depende da minha narrativa.

## Gate de borda com mais de um upstream (oauth2-proxy v7)

Medido em 16/08 subindo uma instância DESCARTÁVEL da mesma imagem na mesma rede, com
`--skip-auth-route='GET=^/'` e credencial falsa: mede roteamento sem encostar em produção,
e é o método, não o caso.

- O proxy DECLARA o mapa no boot (`mapping path "/api/" => ...`) — ler o log é a conferência.
- **O path não é removido no repasse.** Upstream `http://api:8000/api/` casa o prefixo e
  encaminha o caminho inteiro: quem serve tem de responder em `/api` de verdade. Mais
  específico primeiro; `/api` SEM barra não casa e cai no upstream `/`.
- **Travessia não vira bypass**: `../`, `..%2f` e `%2e%2e` levam 301 de canonicalização no
  próprio mux ANTES do repasse, e o pedido seguinte passa pela regra de auth. Por isso
  `--skip-auth-route` com regex não ancorada no fim (`^/estatico/`) não abre buraco — mas
  isso é propriedade do mux, não do regex, e se confere a cada troca de versão.
- Rota anônima aponta para o contêiner que a serve: tirá-la de dentro da imagem que monta
  o `.env` encolhe a superfície de injeção de cabeçalho de sujeito, sem tocar na política.

## Forma da cadeira: três matérias e uma régua

`risco` não é gerência ao lado das outras — é o MODO da cadeira. Descoberto escrevendo o
chapéu dele (16/08): a régua que saiu era palavra por palavra a POSTURA da base. São três
matérias (privacidade, blueteam, cripto) sob uma régua que vale nas três, e por isso ela
não pode morar em chapéu: chapéu carrega condicionalmente, e a régua tem de estar ligada
justamente quando estou de outro chapéu.

O escopo desta cadeira não anda sozinho: são quatro perguntas que só aparecem DENTRO do
trabalho alheio. Agrega quando chega junto da mudança — descrevendo-a melhor do que quem a
propôs —, não quando autoriza; chega tarde por desenho, porque o gatilho de hoje é o
deploy e não o nascimento do card.

## Padrões da casa, medidos

- Secret de stack: ~/AI/var/secrets/<stack>/, dir 700, arquivo 600. Nunca no compose,
  nunca no git, nunca na fila.
- Conta isolada nova: uid sequencial, home 700, faixa subuid/subgid disjunta de 65536
  (megafone 100000, claudinho 165536, modulo-osint 231072, jaiminho 296608), linger on,
  grupo único, sem sudo.
- `conferir superficie` é HOMÔNIMO: julga superfície de SESSÃO (claude.ai, code-seco,
  fabrica, fita), não superfície externa em produção. O classificador que falta ao gate
  precisa de outro nome.
- Caixa alheia não se lê: `fila ler <outra-persona>` é recusado pelo próprio verbo,
  inclusive com --tudo. Não há como reler carta que eu mesmo enviei.
- Slug da cadeira MUDA por verbo, e errar não dá erro — devolve outro armazém. `mesa`,
  `encerrar` e `caderno` querem `seguranca` (o nome do arquivo de persona); `fila` e
  `tarefas --cadeira` querem `claudinho-seguranca`. Chamar `mesa` com o slug longo abre um
  segundo store, plausível e vazio do que importa.
- `encerrar fita` marca o slot `iam` como "ÓRFÃO — slug não declarado na persona" e sugere
  `mesa limpa`. É FALSO POSITIVO: a persona declara `iam` como slug da head, mas fora do
  bloco GERÊNCIAS, que é o que o verbo lê. Não limpar.
