#!/usr/bin/env python3
# porta-sessao — a fita do Claude Code PORTA o sessao_id em toda chamada (arq:0101 §1, spec do dono).
# capacidade: porte-de-sessao-no-cliente
# dono: claudinho-TI
#
# FONTE: platafirma-harness/agente/hooks/porta-sessao.py. Ha UMA copia distribuida, byte a
# byte, em platafirma-posto/.claude/hooks/porta-sessao.py — o posto e a porta de entrada
# humana (qualquer maquina, so `git pull`) e nao enxerga /opt/platafirma. Mudou aqui, copia
# la no mesmo ato; `cmp` entre os dois e o aceite. Por isso este arquivo nao depende de
# nada do host: so stdlib, e todo caminho do host e opcional.
#
# O problema medido (card 3007, 06/09): a cadeira em Code recebe o `sessao_id` no
# retorno do `monta_sessao` e NAO o repassa nas chamadas seguintes (0/190). A porta
# nao infere mais (85ece31), entao sem porte a fita roda sem sessao. Este hook faz o
# porte ser MECANICO, no cliente, independe do agente lembrar — que e a spec:
# `monta_sessao` cunha -> Valkey -> a fita porta o id.
#
# Tres eventos, um script:
#  - PostToolUse em monta_sessao: extrai sessao_id e cadeira do RETORNO e grava por fita do Code.
#  - PreToolUse nas tools da porta: se a chamada nao traz sessao_id, injeta o
#    gravado via `updatedInput` (nunca sobrescreve um id que o agente ja pos).
#  - SessionStart com source compact|resume (ia, 20/09/2026): a compactacao do Code apaga
#    retorno antigo de tool, e persona e conduta chegam como retorno de `monta_sessao`.
#    O hook devolve, em `additionalContext`, a cadeira e o sessao_id gravados e manda
#    reabrir por `monta_sessao` com o MESMO id, que devolve o pacote inteiro — vale em
#    qualquer maquina. No host, onde a morada publicada existe, a persona ja vai junto
#    (lida de la, nunca copia: arranque.md). A conduta nao cabe aqui: tem mais que os
#    10.000 caracteres que o Code aceita por string de hook.
import json, sys, re, os, time
from pathlib import Path

DIR = Path(os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or "/tmp") / "pf-sessao-code"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
# `\\?"` porque o retorno pode chegar como string JSON dentro de JSON (aspas escapadas).
CADEIRA = re.compile(r'\\?"cadeira\\?"\s*:\s*\\?"([a-z0-9][a-z0-9-]{0,40})\\?"')
MORADA = Path(os.environ.get("PF_ABERTURA_DIR", "/srv/platafirma/casa/var/abertura-publicada"))
TETO_CONTEXTO = 9_500          # o Code corta cada string de hook em 10.000 caracteres
JANELA_DEDUP_S = 30            # conta + projeto podem declarar o mesmo hook: fala um so

def arquivo(sid_code: str, sufixo: str = "sid") -> Path:
    seguro = re.sub(r"[^0-9a-zA-Z_-]", "_", sid_code or "sem")
    return DIR / f"{seguro}.{sufixo}"

def le(sid_code, sufixo="sid"):
    try:
        return arquivo(sid_code, sufixo).read_text().strip() or None
    except Exception:
        return None

def grava(sid_code, valor, sufixo="sid"):
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        arquivo(sid_code, sufixo).write_text(valor)
    except Exception as e:
        print(f"[porta-sessao] grava falhou: {e!r}", file=sys.stderr)

def _publicado(*partes: str) -> str | None:
    try:
        return (MORADA / "current" / "abertura").joinpath(*partes).read_text(
            encoding="utf-8", errors="replace").strip() or None
    except Exception:
        return None

def persona_publicada(cadeira: str) -> str | None:
    return _publicado(cadeira, "persona.md") if SLUG.match(cadeira or "") else None

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
    """O que volta a janela depois de compactar ou retomar. None = nada gravado, nada a dizer."""
    cadeira, sid = le(sid_code, "cadeira"), le(sid_code)
    if not cadeira:
        return None
    oque = "compactou" if origem == "compact" else "foi retomada"
    chamada = f"monta_sessao(cadeira=\"{cadeira}\"" + (f", sessao_id=\"{sid}\"" if sid else "") + ")"
    cab = (f"[porta-sessao] A fita {oque}. Retorno antigo de tool pode ter saido da janela, "
           f"inclusive o pacote de monta_sessao — persona, conduta do dono, mesa. Voce segue "
           f"sendo a cadeira `{cadeira}`" + (f", sessao `{sid}`" if sid else "") + ".\n")
    persona = persona_publicada(cadeira)
    conduta_no_host = _publicado("dono.md") is not None
    if persona and conduta_no_host:
        corpo = (cab
                 + "1. A conduta do dono esta no CLAUDE.md da conta (import) e nao saiu.\n"
                 + f"2. Mesa, fila e chapeu: {chamada} devolve o pacote inteiro.\n"
                 + "3. O que estava em curso e nao esta na mesa: `mesa item`, com ato e alvo, antes de seguir.\n"
                 + "\nPersona, da morada publicada:\n\n" + persona)
    else:
        corpo = (cab
                 + f"1. ANTES de qualquer outra coisa: {chamada}. O mesmo sessao_id devolve o "
                   "pacote inteiro; sem ele voce responde sem persona e sem a conduta do dono.\n"
                 + "2. O que estava em curso e nao esta na mesa: `mesa item`, com ato e alvo, antes de seguir.\n")
    if len(corpo) > TETO_CONTEXTO:
        corpo = corpo[:TETO_CONTEXTO] + "\n[persona cortada pelo teto do hook — inteira por `persona ler`]"
    return corpo

def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                        # entrada ma: nao atrapalha a fita
    evento = ev.get("hook_event_name") or ev.get("hookEventName") or ""
    tool = ev.get("tool_name") or ev.get("toolName") or ""
    sid_code = ev.get("session_id") or ev.get("sessionId") or "sem"

    if evento == "SessionStart":
        origem = ev.get("source") or ""
        if origem not in ("compact", "resume"):
            sys.exit(0)                    # startup/clear: quem abre e o monta_sessao
        ctx = contexto_de_retomada(sid_code, origem)
        if ctx and primeiro_a_falar(sid_code, origem):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": ctx}}, ensure_ascii=False))
        sys.exit(0)

    if not (tool.endswith("run_command") or tool.endswith("read_file") or
            tool.endswith("write_file") or tool.endswith("mesa") or tool.endswith("fila") or
            tool.endswith("tarefas") or tool.endswith("motor") or tool.endswith("descansar") or
            tool.endswith("monta_sessao") or ("claudinho-mcp" in tool) or ("platafirma-ops" in tool)):
        sys.exit(0)

    if evento == "PostToolUse" and tool.endswith("monta_sessao"):
        resp = ev.get("tool_response") or ev.get("toolResponse") or ""
        texto = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        m = re.search(r'"sessao_id"\s*:\s*"(' + UUID.pattern + r')"', texto) or UUID.search(texto)
        if m:
            grava(sid_code, m.group(1) if m.lastindex else m.group(0))
        c = CADEIRA.search(texto)
        if c:
            grava(sid_code, c.group(1), "cadeira")
        sys.exit(0)

    if evento == "PreToolUse":
        ti = ev.get("tool_input") or ev.get("toolInput") or {}
        if not isinstance(ti, dict):
            sys.exit(0)
        if ti.get("sessao_id"):
            sys.exit(0)                    # o agente ja portou — respeita
        if tool.endswith("monta_sessao"):
            sys.exit(0)                    # abertura: quem cunha e o verbo
        sid = le(sid_code)
        if not sid:
            sys.exit(0)                    # nada gravado ainda — roda sem sessao (contado)
        novo = dict(ti); novo["sessao_id"] = sid
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "updatedInput": novo}}))
        sys.exit(0)
    sys.exit(0)

if __name__ == "__main__":
    main()
