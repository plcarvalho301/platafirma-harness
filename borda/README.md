# borda

A API que a tela de cada face do cubo de controle chama (card #3516). Mora aqui, em serviço próprio, e não
na `platafirma-ui` nem no `harness-controle` (arq:0057: front não serve rota de API). É comum às faces:
a face vem do caminho, e a lista de atos dela vem do cabeçalho do verbo.

## O que faz

Recebe `/api/<face>/<ato>` do navegador, atrás do gate do cubo, e leva o ato à porta de verbos com o token do
dono como Bearer, `turno_fonte=face` e o fundamento em `turno_texto`. Antes disso recusa, com 403 e uma linha
JSON no stdout, o que não deve chegar à porta:

| recusa | regra |
|---|---|
| escrita (todo método fora de GET, HEAD e OPTIONS) sem `Origin` exata da lista da instância, sem `x-pf-tela: 1` ou sem corpo `application/json` | R31 |
| ato que o cabeçalho do verbo não declara para a face (`# face: <ato>=<face>`), ou que está na linha de exclusão | R32 |
| escrita por GET, leitura por POST (a capacidade vem de `# atos:`; o ato `leitura\|escrita` aceita os dois) | R32 |

O token do dono vem de `X-Forwarded-Access-Token`, cru, onde o gate do cubo o entrega (#2548); sem ele a resposta
é 401 e nada chega à porta, e um `Authorization` posto pelo navegador não vale. A escrita ainda confere a idade
do login (#2572): o `auth_time` do token com mais de cinco minutos sai 401 com `{"login": "antigo"}`, sem chegar à
porta, e a tela leva o dono a `/oauth2/sign_out` e depois a `/oauth2/start` antes de repetir o ato. A leitura não tem
este corte (o `auth_time` não muda quando o gate renova o token). Token sem o claim passa e deixa a linha
`sem-auth-time` no stdout (`infra logs`): a conferência é o primeiro login real no cubo, e se o claim faltar o
buraco volta ao card #3575, sem outro sinal no lugar. A assinatura do token não é conferida na borda: é da porta. A borda não responde CORS, não lê cabeçalho de sujeito do navegador e não tem credencial própria.

## O pedido que a tela faz

```
GET  /api/motor/consultas?a=<arg>&a=<arg>                       ato de leitura
POST /api/motor/ajuste   {"args": ["piso", "0.6"], "fundamento": "porque…"}   ato de escrita
```

Cabeçalhos da escrita: `Origin` da tela, `x-pf-tela: 1`, `Content-Type: application/json`. A resposta é o
envelope da porta (`exit_code`, `stdout`, `stderr`, ou `recusado` e `motivo`), sem o que é do host. A borda
não confere o fundamento: a porta recusa a escrita da face que chega sem ele.

Status da borda: 400 pedido fora da forma · 401 sem token, ou token recusado pela porta · 403 recusa · 404
rota ou face desconhecida · 405 método fora de GET e POST · 413 corpo acima de 16 KB · 502 porta fora do ar ·
503 cabeçalho do verbo ilegível · 504 prazo.

## A rota do tema da casca (#3738)

A casca da Taipa (`pf-casca`, R40 da spec taipa) lê e grava o tema da pessoa em `/api/preferencia/tema`,
e não em `/api/<face>/<ato>`. A borda serve essa rota fixa pelo verbo `preferencia` (mecanismo da `casca`, ver adiante):

```
GET /api/preferencia/tema                         → 200 {"valor": "claro"|"escuro"|"sistema"|null}
PUT /api/preferencia/tema   {"valor": "escuro"}   → 200 {"valor": "escuro"}
```

Mesmas recusas das outras rotas (escrita de outro site em 403, ato fora da face em 403, sem token em 401,
POST e outros métodos em 405). Diferenças, ditas: o corpo leva só `valor` (letras minúsculas, até 16); o
**fundamento** que a porta exige da escrita da face é uma frase fixa da instância
(`BORDA_TEMA_FUNDAMENTO`, padrão «escolha do tema na casca da tela»), posta pela borda e nunca aceita do
navegador; e o **corte de login recente** (#2572) não vale, porque o tema volta com um clique. O sujeito é
o `sub` do token, que a porta tira dele: nem o navegador nem a borda o mandam (spec preferencia R1). Saída do
verbo vira status: 2 (valor fora do vocabulário) 400, 3 (sem sujeito) 401, 5 (banco mudo) e o resto 502, e
«recusado» pela porta 403. `valor: null` é «sem preferência gravada», e só isso: banco que não respondeu nunca vira
`null`.

A `borda-casca-rastreador` do `compose.yaml` é esta rota para o gate de `tarefas.platafirma.org`, numa instância
própria (a lista de origens é da borda inteira). O client do gate dele entra em `PF_FACE_CLIENTS` da porta. A
`borda-casca-site` é a mesma coisa para o site da casa, na rede `pf-borda-casca-site`; o client do gate do site
entra em `PF_FACE_CLIENTS` na story do portão do core (#3902).

## As três leituras da casca (#3899)

A casca da Taipa lê três coisas da própria origem, cada uma do verbo dono do objeto (arq:0124 §3, mecanismo
comum). Elas não caem em face: o cabeçalho do verbo as declara por `# mecanismo: <ato>=casca`, e a borda lê a
carga daí (a chave `face:` com `casca` não carrega nada, e `release conferir verbo` a acusa).

| rota | verbo e ato | corpo |
|---|---|---|
| `GET\|PUT /api/preferencia/tema` | `preferencia ler` e `escrever` | `{"valor"}` (acima) |
| `GET /api/faces` | `release telas --json` | `{"telas": [{"id", "rotulo", "href", "posicao", "face"}]}` |
| `GET /api/espera-dono` | `tarefas espera-dono --json` | o corpo da API do rastreador, como veio |

As duas leituras novas têm as mesmas recusas do tema: escrita de outro site em 403, ato fora da carga em 403,
sem token em 401, método fora de GET em 405, e o status da porta passa (401, 502, 504). A saída do verbo vira
status: `recusado` da porta 403; saída diferente de 0, ou corpo que não é o JSON da forma (a lista leva `telas`
em lista), 502. A borda não lê sujeito: o `sub` do token é tirado pela porta.

O formato da lista de telas é PROVISÓRIO: o épico do plano de controle (#3379) o confirma. Mora em dois lugares, um
de cada lado: `bin/_release/telas/telas.py` (quem o escreve) e `_resposta_da_leitura` aqui (que confere que é
objeto com `telas` em lista). A rota `/api/faces` é o nome que a seg:0016, item 6, fixa; muda só o corpo.

## A declaração das telas e as origens

`registro/telas.json` é a declaração única das telas da instância (dona ti; o rótulo é caneta de produto). Duas
leituras saem dela: `release telas`, que devolve só a tela cuja stack está promovida (registrada no acervo com
compose e a família servindo um `current`), e a lista de origens que podem escrever (R31), que antes era uma lista
à mão em cada instância. Tela nova entra no menu e na escrita por uma linha só; a que sai do ar sai do menu sem
mexer na lista.

Cada instância da borda atende uma tela (`BORDA_TELAS_ATENDE`, o `id` da declaração) e lê a declaração de
`BORDA_TELAS`, de novo quando o arquivo muda. Declaração ausente ou ilegível recusa toda escrita de navegador
(falha fechada); `BORDA_ORIGENS` soma origens por cima, e fica vazia por padrão. A lista de origens é da borda
inteira, por isso há uma instância por tela: a do cubo (`motor`, as faces e a casca), a da casca do rastreador
(`rastreador`) e a da casca do site (`casa`).

## Configuração da instância

| variável | o que é |
|---|---|
| `BORDA_ORIGENS` | origens que podem escrever somadas às da declaração, vírgula entre valores; vazias as duas, a borda só lê |
| `BORDA_TELAS` | caminho de `registro/telas.json`, de onde saem as origens das telas que a instância atende |
| `BORDA_TELAS_ATENDE` | os `id` da declaração que esta instância atende, vírgula entre valores; vazio, todas |
| `BORDA_PORTA_URL` | a porta de verbos (`…/mcp`) |
| `BORDA_CABECALHO_TOKEN` | cabeçalho em que o gate põe o token do dono (padrão `x-forwarded-access-token`, onde o gate do cubo o entrega; `authorization` só para gate que o use, com Bearer) |
| `BORDA_LOGIN_MAX_S` | idade máxima do login para escrever, em segundos (padrão 300; 0 desliga) |
| `BORDA_FACES` | JSON `{"<face>": {"verbo": "<arquivo>", "instancia": "rag", "sem_instancia": ["listar"]}}`, ou uma lista desses quando a face chama mais de um verbo |

Uma face pode chamar mais de um verbo (#3518): a face motor chama o `motor` e, do `fila`, só o `contestar`, que
é o único ato que o cabeçalho do `fila` declara para ela. A carga da face é a união do que cada verbo declara;
o mesmo ato declarado por dois verbos da mesma face sai 503, sem escolher um. A porta precisa de `PF_FACE_CLIENTS` com o client do gate do cubo: sem a lista ela
nega toda fonte face.

## Teste

```
python3 borda/borda.py                    # o self-check, sem rede e sem uvicorn
teste rodar borda@<bancada>               # o portão da chave borda
teste rodar ops@<bancada> ops-server/test_contrato_borda.py   # a borda diante da porta de verdade
```
