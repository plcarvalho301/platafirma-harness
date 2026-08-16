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
Serviço COM auth própria -> direto, gate próprio contra o realm (vikunja, mcp, Synapse).
Classificar na família errada é o erro que custou duas cartas retificadas em 14/08.

Entrando sem gate de rede, quatro contrapartidas deixam de ser recomendação: registro
desabilitado, login local por senha desabilitado, rate limit de login, painel admin só
na rede interna.

## Ato sobre identidade se confere contra o caminho por onde eu opero

Antes de renomear, desabilitar ou apagar sujeito, listar o que depende dele para EU
continuar operando — não só o que depende dele em geral.

Caso, 14/08/2026: renomeei o username do dono no realm depois de conferir vikunja, wiki,
allowlist do proxy e token do mcp, todos intactos. O que não conferi foi o gate por onde
eu opero: o PEP resolve sujeito por `preferred_username` contra `politica-acesso/sujeitos.yaml`,
e o nome velho estava lá. O rename trancou TODAS as cadeiras fora do ops-mcp — `run_command`,
`read_file`, `write_file` — de uma vez.

Por que a recuperação é cara: o admin console do Keycloak é loopback-only (`127.0.0.1:8180`;
`/admin` dá 404 na borda), então não há rota de conserto pelo conector. Quem destrava é o
dono, no terminal do host. Toda mudança de identidade que possa alcançar `sujeitos.yaml`
precisa da correção preparada ANTES do ato, não depois.

## Revogar credencial a partir de lista de terceiro

A lista que a outra cadeira manda descreve o que ela lembra, não o que o arquivo tem.
Antes de apagar, três passadas — nesta ordem, porque a segunda já salvou uma linha viva:

1. **Separar credencial de configuração.** Nem tudo com o prefixo do serviço morto é
   segredo. Caso 16/08: `VIKUNJA_BASE` era rota do verbo `tarefas`, não credencial —
   removível só porque `bin/tarefas` já tinha migrado para `TAREFAS_BASE`. Conferir contra
   quem LÊ a chave hoje, não contra o nome dela.
2. **Grep por nome de chave, nunca por menção.** Duplicata em `.env` é silenciosa: no mesmo
   arquivo, `VIKUNJA_DB_PASSWORD` e `VIKUNJA_SERVICE_SECRET` apareciam duas vezes cada,
   com valores distintos. Contar por chave devolve 5; contar por linha devolve 7.
3. **Reescrever com verificação, não com `sed` no lugar.** Filtrar por chave, e afirmar
   antes de gravar que as chaves restantes seguem byte a byte iguais e que o conjunto
   removido é exatamente o esperado. Permissão 600 se reaplica após o `os.replace`.

Ordem do ato: primeiro o realm (apagar o client mata service account e secret juntos),
depois o `.env`. Fechamento: `acesso orfaos` tem de perder o achado correspondente — é a
única confirmação que não depende da minha narrativa.

O que quase nunca alcanço e por isso vira ato de outrem: arquivo de credencial em conta
que não é `claudinho`, e entrada de custódia no KDBX do dono.

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
- Slug da cadeira MUDA por verbo, e errar não dá erro — devolve outro armazém. `mesa`,
  `encerrar` e `caderno` querem `seguranca` (o nome do arquivo de persona); `fila` e
  `tarefas --cadeira` querem `claudinho-seguranca`. Chamar `mesa` com o slug longo abre um
  segundo store, plausível e vazio do que importa.
- `encerrar fita` marca o slot `iam` como "ÓRFÃO — slug não declarado na persona" e sugere
  `mesa limpa`. É FALSO POSITIVO: a persona declara `iam` como slug da head, mas fora do
  bloco GERÊNCIAS, que é o que o verbo lê. Não limpar.
