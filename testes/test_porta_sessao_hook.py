# componente: componente:agente-hooks
"""Testes do hook `porta-sessao.py` (cabeçalho fail-open e remontagem pela porta nova, story #4343 T5)."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

_HOOK = Path(__file__).resolve().parents[1] / "agente" / "hooks" / "porta-sessao.py"


def _subir_servidor(rotas: dict[str, tuple[int, dict, float]]):
    chamadas: list[tuple[str, dict]] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            tam = int(self.headers.get("Content-Length") or "0")
            corpo = json.loads(self.rfile.read(tam).decode("utf-8")) if tam else {}
            chamadas.append((self.path, corpo))
            status, resp, atraso = rotas.get(self.path, (404, {"ok": False}, 0.0))
            if atraso > 0:
                time.sleep(atraso)
            raw = json.dumps(resp, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            try:
                self.wfile.write(raw)
            except OSError:
                pass

        def log_message(self, *_args):
            return

    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, chamadas


def _rodar_hook(evento: dict, *, runtime_dir: Path, porta_url: str, prazo_s: str = "0.5") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    env["PF_PORTA_URL"] = porta_url
    env["PF_CABECALHO_PRAZO_S"] = prazo_s
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(evento, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
        check=False,
    )


def _registrar_sessao_hook(runtime_dir: Path, sid_code: str, sessao_id: str, cadeira: str, porta_url: str) -> None:
    _rodar_hook(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "mcp__claudinho-mcp__monta_sessao",
            "session_id": sid_code,
            "tool_response": json.dumps({"sessao_id": sessao_id, "cadeira": cadeira}),
        },
        runtime_dir=runtime_dir,
        porta_url=porta_url,
    )


def test_user_prompt_submit_devolve_cabecalho_da_porta(tmp_path):
    sid_code = "code-fita-1"
    sessao_id = str(uuid.uuid4())
    srv, chamadas = _subir_servidor(
        {
            "/turno/cabecalho": (
                200,
                {"ok": True, "cabecalho": "(engenharia, back-end)"},
                0.0,
            )
        }
    )
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        _registrar_sessao_hook(tmp_path, sid_code, sessao_id, "engenharia", url)
        proc = _rodar_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": sid_code,
                "prompt": "executa a story 4343",
            },
            runtime_dir=tmp_path,
            porta_url=url,
        )
    finally:
        srv.shutdown()
        srv.server_close()

    assert proc.returncode == 0
    saida = json.loads(proc.stdout)
    assert saida["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert saida["hookSpecificOutput"]["additionalContext"] == "(engenharia, back-end)"
    assert chamadas == [("/turno/cabecalho", {"sessao_id": sessao_id, "turno": "T0"})]


def test_user_prompt_submit_fail_open_quando_estoura_prazo(tmp_path):
    sid_code = "code-fita-timeout"
    sessao_id = str(uuid.uuid4())
    srv, _chamadas = _subir_servidor(
        {
            "/turno/cabecalho": (
                200,
                {"ok": True, "cabecalho": "(engenharia, back-end)"},
                0.6,
            )
        }
    )
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        _registrar_sessao_hook(tmp_path, sid_code, sessao_id, "engenharia", url)
        t0 = time.monotonic()
        proc = _rodar_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": sid_code,
                "prompt": "turno com porta lenta",
            },
            runtime_dir=tmp_path,
            porta_url=url,
            prazo_s="0.15",
        )
        dur = time.monotonic() - t0
    finally:
        srv.shutdown()
        srv.server_close()

    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert dur < 1.5


def test_session_start_compact_chama_remontagem_abaixo_de_10000_chars(tmp_path):
    sid_code = "code-fita-compact"
    sessao_id = str(uuid.uuid4())
    texto_rem = "# Gabriel Chimpanzé\n\nPOSTURAS EM VIGOR\n- [abertura: decisor] ..."
    srv, chamadas = _subir_servidor(
        {
            "/sessao/remontar": (
                200,
                {"ok": True, "texto": texto_rem, "caracteres": len(texto_rem)},
                0.0,
            )
        }
    )
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        _registrar_sessao_hook(tmp_path, sid_code, sessao_id, "engenharia", url)
        proc = _rodar_hook(
            {
                "hook_event_name": "SessionStart",
                "source": "compact",
                "session_id": sid_code,
            },
            runtime_dir=tmp_path,
            porta_url=url,
        )
    finally:
        srv.shutdown()
        srv.server_close()

    assert proc.returncode == 0
    saida = json.loads(proc.stdout)
    ctx = saida["hookSpecificOutput"]["additionalContext"]
    assert "Gabriel Chimpanzé" in ctx
    assert len(ctx) < 10_000
    assert chamadas == [("/sessao/remontar", {"sessao_id": sessao_id, "cadeira": "engenharia"})]
