#!/usr/bin/env python3
# porta-sessao — a fita do Claude Code PORTA o sessao_id em toda chamada.
# capacidade: porte-de-sessao-no-cliente
# dono: ti
#
# FONTE: platafirma-harness/agente/hooks/porta-sessao.py. O posto NAO carrega copia: a mudanca
# que o faria porta de entrada humana, com o hook no proprio repo, foi revertida em e2ddecb
# (platafirma-posto, 20/09/2026), e o settings do posto nao registra este script. Se uma copia
# voltar ao posto, ela e byte a byte desta e `cmp` entre as duas e o aceite. Por isso este
# arquivo nao depende de nada do host: so stdlib, e todo caminho do host e opcional.
#
# Quatro eventos, um script:
#  - UserPromptSubmit: guarda o contador do turno (T0, T1, ...) e a mensagem do dono,
#    e marca o turno pendente. NAO imprime nada: o que este evento imprime entra no contexto do
#    modelo. O PreToolUse seguinte leva `turno` e, na primeira chamada, `turno_texto` a porta.
#  - PostToolUse em monta_sessao: extrai sessao_id e cadeira do RETORNO e grava por fita do Code.
#  - PreToolUse nas tools da porta: se a chamada nao traz sessao_id, injeta o
#    gravado via `updatedInput` (nunca sobrescreve um id que o agente ja pos).
#  - SessionStart com source compact|resume (ia, 20/09/2026): a compactacao do Code apaga
#    retorno antigo de tool, e persona e conduta chegam como retorno de `monta_sessao`.
import json, sys, re, os, time
from pathlib import Path
from urllib import error as _url_error, request as _url_request

DIR = Path(os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or "/tmp") / "pf-sessao-code"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
# `\\?"` porque o retorno pode chegar como string JSON dentro de JSON (aspas escapadas).
CADEIRA = re.compile(r'\\?"cadeira\\?"\s*:\s*\\?"([a-z0-9][a-z0-9-]{0,40})\\?"')
CASA_NOVA = Path(os.environ.get("PF_CASA_RAIZ") or str(Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current")) / "casa"))
TETO_CONTEXTO = 9_500          # o Code corta cada string de hook em 10.000 caracteres
JANELA_DEDUP_S = 30            # conta + projeto podem declarar o mesmo hook: fala um so
TETO_TURNO_TEXTO = 16_000      # caracteres da mensagem do dono que o hook entrega a porta
PRAZO_CABECALHO_S = 0.5        # prazo curto com falha aberta no UserPromptSubmit
PRAZO_REMONTAGEM_S = 3.0       # prazo de remontagem pós-compactação pela porta
_PREFIXOS_MALOTE = ("malote ", "run_command ")


def _post_porta(caminho: str, payload: dict, *, timeout_s: float) -> dict | None:
    """Chama rota leve da porta nova em stdlib com falha aberta em erro ou timeout."""
    base = (os.environ.get("PF_PORTA_URL") or "").strip().rstrip("/")
    if not base:
        return None
    corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = (os.environ.get("PF_PORTA_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = _url_request.Request(f"{base}{caminho}", data=corpo, headers=headers, method="POST")
    try:
        with _url_request.urlopen(req, timeout=timeout_s) as resp:
            bruto = resp.read().decode("utf-8", errors="replace").strip()
            dado = json.loads(bruto) if bruto else {}
            return dado if isinstance(dado, dict) else None
    except (_url_error.URLError, TimeoutError, OSError, ValueError):
        return None


def pedir_cabecalho(sid_code: str, turno: str) -> str | None:
    """Pede o cabeçalho do turno à porta nova com prazo curto (500 ms) e falha aberta."""
    sid = le(sid_code)
    if not sid:
        return None
    try:
        prazo = float(os.environ.get("PF_CABECALHO_PRAZO_S") or PRAZO_CABECALHO_S)
    except ValueError:
        prazo = PRAZO_CABECALHO_S
    resp = _post_porta("/turno/cabecalho", {"sessao_id": sid, "turno": turno}, timeout_s=prazo)
    if not resp or not resp.get("ok"):
        return None
    cab = resp.get("cabecalho")
    return str(cab).strip() if isinstance(cab, str) and cab.strip() else None

def arquivo(sid_code: str, sufixo: str = "sid") -> Path:
    seguro = re.sub(r"[^0-9a-zA-Z_-]", "_", sid_code or "sem")
    return DIR / f"{seguro}.{sufixo}"

def le(sid_code, sufixo="sid"):
    try:
        return arquivo(sid_code, sufixo).read_text(encoding="utf-8", errors="replace").strip() or None
    except Exception:
        return None

def grava(sid_code, valor, sufixo="sid"):
    """Arquivo 0600 numa pasta 0700: a mensagem do dono fica em disco ate a proxima."""
    try:
        DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(DIR, 0o700)
        except OSError:
            pass                           # pasta de outro dono: segue com o que ha
        alvo = arquivo(sid_code, sufixo)
        fd = os.open(str(alvo), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(valor)
        os.chmod(alvo, 0o600)              # arquivo que ja existia com outro modo
    except Exception as e:
        print(f"[porta-sessao] grava falhou: {e!r}", file=sys.stderr)

def apaga(sid_code, sufixo):
    try:
        arquivo(sid_code, sufixo).unlink()
    except Exception:
        pass

def proximo_turno(sid_code: str) -> str:
    """O contador do turno: T0 na primeira mensagem do dono da fita, T1 na segunda, e assim por diante."""
    m = re.fullmatch(r"T(\d+)", le(sid_code, "turno") or "")
    return f"T{int(m.group(1)) + 1}" if m else "T0"

def com_turno(sid_code: str, ti: dict) -> dict:
    """Poe `turno` na chamada da porta e, na primeira depois da mensagem do dono, `turno_texto` e
    limpa o pendente. Chamada que ja traz `turno` segue como veio. Sem mensagem guardada, nada."""
    turno = le(sid_code, "turno")
    if not turno or ti.get("turno"):
        return ti
    novo = dict(ti, turno=turno)
    if le(sid_code, "pendente"):
        texto = le(sid_code, "texto")
        if texto:
            novo["turno_texto"] = texto[:TETO_TURNO_TEXTO]
        apaga(sid_code, "pendente")
    return novo

def _da_casa_nova(*partes: str) -> str | None:
    try:
        return CASA_NOVA.joinpath(*partes).read_text(
            encoding="utf-8", errors="replace").strip() or None
    except Exception:
        return None

def _do_projeto(*partes: str) -> str | None:
    """Copia local do posto (quando fora do host). `CLAUDE_PROJECT_DIR` vem do Code."""
    raiz = os.environ.get("CLAUDE_PROJECT_DIR")
    if not raiz:
        return None
    try:
        return Path(raiz).joinpath(*partes).read_text(
            encoding="utf-8", errors="replace").strip() or None
    except Exception:
        return None

def persona_publicada(cadeira: str) -> str | None:
    if not SLUG.match(cadeira or ""):
        return None
    return _da_casa_nova("instancias", "persona", f"{cadeira}.md") or _do_projeto("abertura", cadeira, "persona.md")

def conduta_importada() -> bool:
    """A conduta chega pelo arranque do posto ou da casa nova."""
    return (_da_casa_nova("instancias", "cultura", "da-casa.md") or _do_projeto("AGENTS.md")) is not None

def primeiro_a_falar(sid_code: str, origem: str) -> bool:
    """O mesmo hook pode estar declarado na conta e no projeto (posto aberto no host): os
    dois disparam juntos. Quem cria o marcador da janela fala; o outro se cala."""
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        balde = int(time.time() // JANELA_DEDUP_S)
        if arquivo(sid_code, f"{origem}-{balde - 1}.dito").exists():
            return False                   # o par disparou na virada do balde
        marca = arquivo(sid_code, f"{origem}-{balde}.dito")
        os.close(os.open(str(marca), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False
    except Exception:
        return True                        # na duvida, fala: repetir custa menos que calar

def contexto_de_retomada(sid_code: str, origem: str) -> str | None:
    """O que volta a janela depois de compactar ou retomar via rota `/sessao/remontar` da porta."""
    cadeira, sid = le(sid_code, "cadeira"), le(sid_code)
    if not cadeira and not sid:
        return None
    resp = _post_porta(
        "/sessao/remontar",
        {"sessao_id": sid or "", "cadeira": cadeira or ""},
        timeout_s=PRAZO_REMONTAGEM_S,
    )
    if resp and resp.get("ok") and isinstance(resp.get("texto"), str) and resp["texto"].strip():
        texto = resp["texto"].strip()
        if len(texto) > TETO_CONTEXTO:
            texto = texto[:TETO_CONTEXTO]
        return texto
    if not cadeira:
        return None
    oque = "compactou" if origem == "compact" else "foi retomada"
    chamada = f"monta_sessao(cadeira=\"{cadeira}\"" + (f", sessao_id=\"{sid}\"" if sid else "") + ")"
    cab = (f"[porta-sessao] A fita {oque}. Retorno antigo de tool pode ter saido da janela. "
           f"Voce segue sendo a cadeira `{cadeira}`" + (f", sessao `{sid}`" if sid else "") + ".\n"
           f"Se a remontagem pela porta nao chegou, reabra com {chamada}.\n")
    persona = persona_publicada(cadeira)
    corpo = cab + ("\n" + persona if persona else "")
    if len(corpo) > TETO_CONTEXTO:
        corpo = corpo[:TETO_CONTEXTO]
    return corpo

def _base(tool: str) -> str:
    return tool.rsplit("__", 1)[-1]

def _com_origem(args, origem: str) -> list:
    args = list(args or [])
    if any(str(a) == "--origem" or str(a).startswith("--origem=") for a in args):
        return args                        # o que o agente ja pos vale
    return args + ["--origem", origem]

def _normaliza_texto_malote(texto: str) -> str:
    s = texto.lstrip()
    for pref in _PREFIXOS_MALOTE:
        if s.startswith(pref):
            return s[len(pref):].lstrip()
    return s

def _eh_abertura_sessao_dict(x: dict) -> bool:
    verbo = str(x.get("verbo") or "").strip()
    ato = str(x.get("ato") or "").strip()
    args = x.get("args")
    if verbo == "sessao":
        if ato == "abrir":
            return True
        if not ato and isinstance(args, list) and args and str(args[0]) == "abrir":
            return True
    if verbo in ("malote", "run_command") and ato == "sessao":
        if isinstance(args, list) and args and str(args[0]) == "abrir":
            return True
    return False

def liga_origem(tool: str, ti: dict, origem: str) -> dict:
    """Sub-agente abrindo a PROPRIA sessao: `sessao abrir ... --origem <sessao do orquestrador>`.
    Posto aqui para a linhagem nao depender de o modelo lembrar.
    So toca abertura de sessao; o resto da chamada segue como veio."""
    novo = dict(ti)
    base = _base(tool)
    if base == "sessao":
        if novo.get("ato") == "abrir":
            novo["args"] = _com_origem(novo.get("args"), origem)
        if isinstance(novo.get("lote"), list):
            novo["lote"] = [dict(i, args=_com_origem(i.get("args"), origem))
                            if isinstance(i, dict) and i.get("ato") == "abrir" else i
                            for i in novo["lote"]]
    elif base in ("malote", "run_command"):            # run_command: apelido de malote (#3270)
        def item(x):
            if isinstance(x, str):
                norm = _normaliza_texto_malote(x)
                if norm.startswith("sessao abrir") and "--origem" not in x:
                    return f"{x} --origem {origem}"
                return x
            if isinstance(x, dict) and _eh_abertura_sessao_dict(x):
                return dict(x, args=_com_origem(x.get("args"), origem))
            return x
        if isinstance(novo.get("itens"), list):
            novo["itens"] = [item(x) for x in novo["itens"]]
        if isinstance(novo.get("commands"), list):
            novo["commands"] = [item(x) for x in novo["commands"]]
        if isinstance(novo.get("command"), str):
            novo["command"] = item(novo["command"])
    return novo

def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                        # entrada ma: nao atrapalha a fita
    evento = ev.get("hook_event_name") or ev.get("hookEventName") or ""
    tool = ev.get("tool_name") or ev.get("toolName") or ""
    sid_code = ev.get("session_id") or ev.get("sessionId") or "sem"
    agente = ev.get("agent_id") or ev.get("agentId")
    chave = f"{sid_code}__{agente}" if agente else sid_code

    if evento == "SessionStart":
        origem = ev.get("source") or ""
        if origem not in ("compact", "resume"):
            sys.exit(0)                    # startup/clear: quem abre e o monta_sessao
        ctx = contexto_de_retomada(sid_code, origem)
        if ctx and primeiro_a_falar(sid_code, origem):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": ctx}}, ensure_ascii=False))
        sys.exit(0)

    if evento == "UserPromptSubmit":
        prompt = ev.get("prompt")
        if not agente and isinstance(prompt, str) and prompt.strip():
            turno = proximo_turno(sid_code)
            grava(sid_code, turno, "turno")
            grava(sid_code, prompt, "texto")
            grava(sid_code, "1", "pendente")
            cab = pedir_cabecalho(sid_code, turno)
            if cab:
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": cab,
                    }
                }, ensure_ascii=False))
        sys.exit(0)

    if not (tool.endswith("malote") or tool.endswith("run_command") or tool.endswith("read_file") or tool.endswith("ler_arquivo") or
            tool.endswith("write_file") or tool.endswith("mesa") or tool.endswith("fila") or
            tool.endswith("tarefas") or tool.endswith("busca") or tool.endswith("descansar") or
            tool.endswith("monta_sessao") or ("claudinho-mcp" in tool) or ("platafirma-ops" in tool)):
        sys.exit(0)

    if evento == "PostToolUse" and tool.endswith("monta_sessao"):
        resp = ev.get("tool_response") or ev.get("toolResponse") or ""
        texto = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        m = re.search(r'"sessao_id"\s*:\s*"(' + UUID.pattern + r')"', texto) or UUID.search(texto)
        if m:
            grava(chave, m.group(1) if m.lastindex else m.group(0))
        c = CADEIRA.search(texto)
        if c:
            grava(chave, c.group(1), "cadeira")
        sys.exit(0)

    if evento == "PreToolUse":
        ti = ev.get("tool_input") or ev.get("toolInput") or {}
        if not isinstance(ti, dict):
            sys.exit(0)
        novo = dict(ti)
        if agente:                         # sub-agente abrindo a propria sessao: liga a do orquestrador
            origem = le(sid_code)
            if origem:
                novo = liga_origem(tool, novo, origem)
        if not novo.get("sessao_id") and not tool.endswith("monta_sessao"):
            sid = (le(chave) if agente else None) or le(sid_code)
            if sid:
                novo["sessao_id"] = sid
        if not agente:                     # sub-agente nao recebe o turno do orquestrador (#3356)
            novo = com_turno(sid_code, novo)
        if novo == ti:
            sys.exit(0)                    # o agente ja portou — respeita
        out = {"hookEventName": "PreToolUse", "updatedInput": novo}
        if ev.get("permission_mode") != "plan":
            out["permissionDecision"] = "allow"
        print(json.dumps({"hookSpecificOutput": out}))
        sys.exit(0)
    sys.exit(0)

if __name__ == "__main__":
    main()
