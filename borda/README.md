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

Sem token (Authorization: Bearer, ou o cabeçalho de `BORDA_CABECALHO_TOKEN`) a resposta é 401 e nada chega à
porta. A borda não responde CORS, não lê cabeçalho de sujeito do navegador e não tem credencial própria.

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

## Configuração da instância

| variável | o que é |
|---|---|
| `BORDA_ORIGENS` | origens que podem escrever, vírgula entre valores; vazia, a borda só lê |
| `BORDA_PORTA_URL` | a porta de verbos (`…/mcp`) |
| `BORDA_CABECALHO_TOKEN` | cabeçalho em que o gate põe o token do dono (padrão do código `authorization`; o `compose.yaml` fixa `x-forwarded-access-token`, que é onde o gate do cubo o entrega) |
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
