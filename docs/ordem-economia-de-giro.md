# ORDEM DE EXECUÇÃO — economia de giro (mastigada para a fábrica / ultracode)

> Efêmera. Canônico é `platafirma-arquitetura/docs/specs/spec_economia-de-giro.md`.
> Apagar este arquivo no commit que entregar a Leva 2. Redigida por ia (engenharia-de-harness), 06/09/2026, por ordem do dono.

## Como rodar
Um turno. Faz TODAS as edições abaixo, roda o gate verde, e faz **dois commits** no
`platafirma-harness` (COMMIT-A = Leva 1, COMMIT-B = Leva 2). **Não reinicia o ops-mcp** —
o restart é ato de janela do TI (razão: T1 abaixo). Empurra os dois commits e para.

Trabalha em `~/AI/platafirma-harness`. Todos os caminhos são relativos a ele.

## T1 — a trava que manda no faseamento (ler antes de tudo)
Trocar o conjunto de tools apresentado ao cliente **no meio de uma sessão** invalida o
prefixo cacheado e força releitura de tudo a preço cheio (doc de prompt caching da
Anthropic; §8 da spec). Por isso:
- Mudança de **schema de tool** (campos novos: `lote`, `commands[]`, `paths[]`, `sessao_id`
  nas genéricas) **só entra por restart**, nunca mid-fita.
- A fábrica **entrega código+testes+commits**; quem reinicia é o TI, em janela dita antes
  (mesa TI #6 já espera). Reiniciar mid-sessão queima mais teto do que a ordem economiza.
- Tudo atrás de flag de env, para o restart ligar/desligar sem tocar banco nem ADR.

## Flags (todas em `ops-server/server.py`, junto de `TOOLS_VERBOS`)
```
PF_SOMBRA   = os.environ.get("PF_SOMBRA", "1") != "0"      # sessão-sombra inequívoca (§3)
PF_GATE     = os.environ.get("PF_GATE", "1") != "0"        # gate transparente (§4)
PF_TOOLS_LOTE = os.environ.get("PF_TOOLS_LOTE", "0") == "1" # chamada em lote (§5) — Leva 2
```
Rollback de qualquer perna: env a 0 + restart. Sem migração, sem ADR.

---

# COMMIT-A — Leva 1 (identidade, gate, medição, renome)

## A1. Sessão-sombra inequívoca — `_sessao_resolve` (§3)
**Problema medido (ti):** o join por conexão (`_sessao_por_sid[sid_conexao]`) está morto no
claude.ai — `stateless_http=True` recicla `id(ServerSession)` a cada request e 0/205
requests trazem `Mcp-Session-Id`. Sem parâmetro, a cadeira some do log.

**Passo 1 — gravar a identidade do abridor na abertura.** Em `monta_sessao`, onde hoje
grava `sessao:{_sessao_id}` no Valkey (bloco `_rc.set(f"sessao:{_sessao_id}", ...)`):
- Capturar `_q = _quem()` no trecho async (antes do `to_thread`, junto de `_sid = _sessao_atual()`).
- Incluir no JSON do valor: `"sub": _q.get("sub","-"), "sid": _q.get("sid","-"), "jti": _q.get("jti","-")`.
- Escrever um índice reverso, mesmo TTL (172800): chave
  `sombra:{sub}:{sid}:{jti}` → adicionar `_sessao_id` a um set. Use `_rc.sadd(chave, _sessao_id); _rc.expire(chave, 172800)`.
  Não gravar sombra quando `sub`, `sid` e `jti` forem todos `"-"` (token estático: colidiria
  todas as sessões da fábrica sob uma chave — §3 diz que ali o runner passa o id).

**Passo 2 — resolver por sombra.** Reescrever `_sessao_resolve`:
```py
def _sessao_resolve(sessao_id: str | None) -> dict:
    """cadeira/ordem da sessão: parâmetro → join por conexão → sombra inequívoca → nada (§3, spec_economia-de-giro)."""
    sid_conexao = _sessao_atual()
    if not sessao_id:
        sessao_id = _sessao_por_sid.get(sid_conexao) or None
    if not sessao_id and PF_SOMBRA:
        sessao_id = _sombra_inequivoca()   # None quando 0 ou ≥2 vivas
    out = {"sessao_id": sessao_id or "-", "ordem_id": _ordem_por_sid.get(sid_conexao, "-"), "cadeira": ""}
    if not sessao_id:
        return out
    # ... resto igual (lê sessao:{id} do Valkey) ...
```
Nova função `_sombra_inequivoca()`:
```py
def _sombra_inequivoca() -> str | None:
    q = _quem()
    sub, sid, jti = q.get("sub","-"), q.get("sid","-"), q.get("jti","-")
    if sub == "-" and sid == "-" and jti == "-":
        return None                      # token estático: não infere
    try:
        rc = redis.Redis(host=MEM_REDIS_HOST, port=MEM_REDIS_PORT, decode_responses=True)
        vivas = [s for s in rc.smembers(f"sombra:{sub}:{sid}:{jti}") if rc.exists(f"sessao:{s}")]
    except Exception as e:               # noqa: BLE001
        print(f"[sombra] indisponível: {e!r}", file=sys.stderr, flush=True); return None
    if len(vivas) == 1:
        return vivas[0]
    _audit(tool="-", evento="sessao_ambigua", sob=f"{sub}:{sid}:{jti}", vivas=len(vivas))
    return None                          # 0 ou ≥2 → "-" + aviso (#409: não inferir com ambiguidade)
```
Chamar `_quem()`/`_sombra_inequivoca()` sempre no trecho **async** da tool (nunca dentro do
`to_thread`; o contexto do FastMCP não sobrevive à thread — comentário em `run_command:401`).

## A2. `sessao_id` nas três genéricas + auditoria de identidade (M1)
**`run_command`** — assinatura `async def run_command(command, cwd="", timeout=120, sessao_id=None)`.
Trocar o bloco `sid=... ; oid=_ordem_por_sid... ; sessao_id=_sessao_por_sid...` por:
```py
    ident = _sessao_resolve(sessao_id)      # trecho async, ok
    ...
    r = await anyio.to_thread.run_sync(_run_blocking, command, d, timeout, ident["sessao_id"], ident["ordem_id"], ident["cadeira"])
```
`_run_blocking` ganha `cadeira: str = ""` e, quando não vazia, injeta `PF_CADEIRA` no env do
subprocesso (hoje só põe PF_SESSAO/PF_ORDEM_ID). Assim run_command legítimo carrega cadeira.
`_audit(tool="run_command", ...)` ganha `cadeira=ident["cadeira"] or None,
sessao_id=ident["sessao_id"], ordem_id=ident["ordem_id"]`.

**`read_file`** e **`write_file`** — assinatura ganha `sessao_id: str | None = None`. No corpo,
`ident = _sessao_resolve(sessao_id)` e o `_audit` grava `cadeira/sessao_id/ordem_id` como acima.
(São tools síncronas; `_sessao_resolve` roda inline no task do request — o `_audit` já chama
`_sessao_atual()` ali hoje, logo o contexto existe.)

## A3. Gate transparente em `run_command` (§4, M2)
Entre `_autoriza` (que fica) e a execução. Só dispara com `PF_GATE`. Regra dura de
reconhecimento — **na dúvida, é fallback** (não executar shell complexo pela via de verbo):

1. `segs = [s.strip() for s in command.split(";") if s.strip()]`.
2. O comando é elegível ao gate **só se** não contém nenhum de `| & > < $ ` \` * ?` `(` `)` e
   **todo** `seg` tem, como primeira palavra (`shlex.split(seg)[0]`), um slug em
   `SLUGS_SERVIDOS`. Senão → fallback (segue o caminho atual de `_run_blocking`, auditado
   `evento="fallback"`).
3. Elegível: para cada `seg`, `argv = shlex.split(seg)`; roda `_run_verbo_blocking(argv,
   None, timeout, ident)` (via de verbo, com identidade do A1). Auditar cada um
   `_audit(tool=<slug>, evento="verbo_contornado", ...)`.
4. Retorno: um seg só → resultado do verbo + `"aviso": "tem tool <slug> — chamada roteada pela porta"`.
   Vários segs → `{"lote": [<result por seg>], "aviso": "N verbos roteados"}` (este é o «lote
   entre verbos» do §5b, já com identidade, sem tool nova).

`SLUGS_SERVIDOS`: montar um `set(TOOLS_DERIVADAS)` logo após `TOOLS_DERIVADAS = _gera_tools_verbos()`.
`import shlex` no topo.

## A4. Renome Leva (D2) — libera a palavra «lote» para o batch
O batch (§5) chama-se **chamada em lote** e usa o campo `lote`. A onda de rollout, que hoje
se chama «lote 2», passa a **«leva»**. Grep e renomear o sentido-de-onda, não o de-batch:
- `ops-server/server.py`: `TOOLS_LOTE2` → `TOOLS_LEVA2`; env `PF_TOOLS_LOTE2` → `PF_TOOLS_LEVA2`;
  `int(i.get("lote") or 1)` → `int(i.get("leva") or 1)`; comentários «Lote 1/Lote 2» (rollout) → «Leva 1/Leva 2».
- `abertura/oficio-ferramental.md`: marcador `repo lote:2` → `repo leva:2`; a nota da linha 9
  reescreve «`lote:2` foi retirado…» → «`leva:2`…».
- `bin/acervo`: onde `listar ferramental --tools` projeta o marcador para o campo JSON `lote`,
  renomear o campo para `leva` (grep `lote` em bin/acervo; é o parse do marcador `:2`, não o
  `bancada [lote]` da linha 20, que fica).
- Confirir que nada mais lê o JSON antigo: `grep -rn '"lote"' ops-server bin` deve ficar vazio
  após o renome (o `lote` que sobra é o campo NOVO de batch do §5, que só entra na Leva 2).

## A5. Roteador curto no `oficio.md` (§6) — texto
Substituir o bloco cercado «O que NÃO é tool…» por:
```
Necessidade → verbo (a porta redireciona e avisa se você chamar por `run_command`):
ver/editar mesa, fila, tarefas, acervo, motor, deploy… → a tool de mesmo nome.
Fica fallback (NÃO é verbo — passa e conta): git · rg · fd · jq · yq · lnav · sar · df/du/ncdu
· uv · python3 · longjob (>2 min) · conta-abertura · deploy-harness/instalar · politica-sync
· shim de instância (rastreador|keycloak…).
```
E corrigir o bullet de `sessao_id`: «Sem ele, a porta resolve por sessão-sombra só quando é
inequívoca (uma sessão viva sua); ambíguo → roda sem cadeira.» Remover a frase «tenta o join
pela conexão». (Vigência: próxima `publicar-abertura`, ato do TI — o repo só guarda o texto.)

## A6. Testes (gate verde antes do push) — em `ops-server/_ensaio.py`
Baseline são 42; adicionar e manter todos verdes:
- `_sombra_inequivoca`: 1 viva → devolve o id; 2 vivas → None + audita `sessao_ambigua`; 0 → None; token estático (-,-,-) → None sem tocar Valkey.
- `_sessao_resolve`: parâmetro vence sombra; sem parâmetro e 1 viva → resolve cadeira.
- gate: `run_command("mesa ver")` com PF_GATE → vai à via de verbo, traz `aviso`; `"git status"` → fallback (sem aviso, sem rota); `"mesa ver; fila status"` → `lote` com 2 itens; `"rg x | wc -l"` → fallback (tem `|`).
- M1: linha de `_audit` de `run_command`/`read_file`/`write_file` carrega `sessao_id`, `ordem_id`, `cadeira`.
- renome: `int(i.get("leva") or 1)` retém slug de `leva:2` quando `PF_TOOLS_LEVA2` off.

Rodar: `cd ~/AI/platafirma-harness && python3 -m pytest ops-server/_ensaio.py -q`. Verde → COMMIT-A.
Mensagem: `economia-de-giro leva 1: sombra inequivoca, sessao_id nas genericas (M1), gate transparente (M2), renome leva`.

---

# COMMIT-B — Leva 2 (chamada em lote)

Atrás de `PF_TOOLS_LOTE`. Teto do lote = teto de uma chamada única (D4): `CAP` global; item
trunca por `_cap`; o lote para de somar itens quando o acumulado de `bytes_total` atinge `CAP`,
e os itens restantes voltam `{"omitido_por_teto": True}` com `lote_next=<índice>`.

## B1. Verbos da casa — `_faz_tool_verbo` (§5a)
`_tool` ganha `lote: list[dict] | None = None`. Quando presente (e `PF_TOOLS_LOTE`), ignora
`ato`/`args`/`stdin` escalares e itera `lote` (cada item `{ato, args, stdin}`), mesmo `binario`,
mesmo `ident`. Um `_audit` por item com `lote_id=<uuid4 hex[:8]>` e `lote_n=<i>`. Retorno
`{"lote": [<result>], "lote_n": N, "lote_next": <idx|null>}`. Mesmo verbo, N atos (D2/dono):
`mesa ver` + `mesa anota` num lote é um verbo, uma capacidade — `arq:0037` intacto.

## B2. Genéricas — listas (§5c)
- `run_command(commands: list[str] | None = None, ...)`: se `commands` e `PF_TOOLS_LOTE`, itera
  (cada item = `bash -c` próprio, `timeout` próprio, sequencial, mesmo `ident`); erro num item
  não derruba o lote. Mesmo teto/`lote_next`. Escalar `command` segue válido.
- `read_file(paths: list[str] | None = None, ...)`: idem, item = uma leitura.
- **NÃO** em `write_file` (falha parcial sem transação). **NÃO** `edit` (nativa do runner do Code, fora da porta).

## B3. Testes (em `_ensaio.py`)
- verbo em lote: `lote=[{ato:"ver"},{ato:"ver"}]` → 2 resultados, `lote_n=2`.
- `run_command(commands=["echo a","echo b"])` → 2; um item com exit≠0 não derruba os outros.
- `read_file(paths=[p1,p2])` → 2.
- teto: lote que estoura `CAP` corta e devolve `lote_next`.
- `PF_TOOLS_LOTE` off → campo `lote`/`commands`/`paths` ignorado (schema presente, comportamento escalar).

Verde → COMMIT-B (que também **apaga este arquivo**: `git rm docs/ordem-economia-de-giro.md`).
Mensagem: `economia-de-giro leva 2: chamada em lote nos verbos e genericas (teto D4); remove ordem`.

---

# Depois da fábrica (ato do TI, não é despacho de trabalho — é a janela de restart, T1)
1. Restart 1 (COMMIT-A no ar): `systemctl --user restart ops-mcp`. Flags default já ligam sombra+gate.
2. Restart 2 (COMMIT-B): `PF_TOOLS_LOTE=1` + restart.
3. `descansar` M3 (perna da ia, entra sozinha depois do restart 1; sem restart — bin roda fresco):
   `ato_fita` lê `~/AI/var/log/ops/ops-<hoje>.jsonl`, filtra `ordem_id == os.environ["PF_ORDEM_ID"]`,
   conta por tool, `verbo_contornado`×`fallback`, lotes e bytes; imprime bloco «giros medidos
   (porta)». Série da fábrica (transcript `requestId`×`last-prompt`) é consulta, não instrumenta.
4. Uma semana: medir `sessao_id != "-"` em `run_command` e bytes/giro (C1/C2 da spec).

# O que NÃO fazer
- Não reiniciar o ops-mcp de dentro da própria fita (T1).
- Não tocar `dono.md` nem o molde de resposta.
- Não criar verbo para `git`/`rg`/`jq` (matéria do arquiteto; o gate só conta).
- Não pôr batch em `write_file` nem `edit`.
