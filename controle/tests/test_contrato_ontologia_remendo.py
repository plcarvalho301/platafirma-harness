# componente: componente:verbo-ontologia
"""Contrato do verbo `ontologia` para remendo parcial em lote (card #4466)."""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

from _olaria.__main__ import executar  # noqa: E402

V1 = "019a0000-0000-7000-8000-000000000001"
V2 = "019a0000-0000-7000-8000-000000000002"
PEDIDO = "019a0000-0000-7000-8000-000000000100"


def _subir_duble(handler_fn):
    recebidas: list[tuple[str, dict]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            tam = int(self.headers.get("Content-Length") or 0)
            corpo = json.loads(self.rfile.read(tam) or b"{}")
            recebidas.append((self.path, corpo))
            status, resp = handler_fn(self.path, corpo, self.headers)
            dados = json.dumps(resp, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    th = Thread(target=srv.serve_forever, daemon=True)
    th.start()
    import tempfile

    import yaml

    cfg_dir = Path(tempfile.mkdtemp(prefix="pf-remendo-cfg-"))
    cfg_arq = cfg_dir / "escrita.yaml"
    pol_dados = yaml.safe_load((RAIZ / "registro" / "escrita.yaml").read_text(encoding="utf-8"))
    pol_dados["verbos_ligados"] = []
    cfg_arq.write_text(yaml.safe_dump(pol_dados, sort_keys=False), encoding="utf-8")
    env = {
        "OLARIA_URL": f"http://127.0.0.1:{srv.server_address[1]}",
        "OLARIA_CHAVE": "chave-teste",
        "PF_CADEIRA": "engenharia",
        "PF_ESCRITA_CONFIG": str(cfg_arq),
    }
    return srv, env, recebidas


def test_envio_de_remendo_e_resumo_com_versoes_e_aviso(tmp_path: Path) -> None:
    arq = tmp_path / "remendo.yaml"
    arq.write_text(
        f"# parte\nclasses:\n- slug: chapeu\n  versao: {V1}\n  _remendo: true\n  definicao: Nova\n",
        encoding="utf-8",
    )

    def _responder(rota: str, corpo: dict, _hdrs):
        assert rota == "/trocar"
        assert "_remendo: true" in corpo["yaml"]
        return 200, {
            "estado": "fez",
            "fornada": PEDIDO,
            "uso": "catalogo",
            "classes": ["chapeu", "persona"],
            "gravadas": [],
            "removidas": [],
            "versoes": {"shape:chapeu": PEDIDO, "shape:persona": PEDIDO},
            "avisos": ["as fichas de chapeu mudaram de versão (releia antes de trocar fichas dessa classe)"],
        }

    srv, env, recebidas = _subir_duble(_responder)
    try:
        saida = executar(["trocar", str(arq), "--pedido", PEDIDO], env=env)
    finally:
        srv.shutdown()
        srv.server_close()

    assert saida.codigo == 0
    assert len(recebidas) == 1
    assert f"versao: shape:chapeu · {PEDIDO}" in saida.stdout
    assert f"versao: shape:persona · {PEDIDO}" in saida.stdout
    assert "classes: chapeu, persona" in saida.stdout
    assert "aviso: as fichas de chapeu mudaram de versão" in saida.stdout


def test_ensaiar_trocar_lista_classes_e_retorna_dois_conflitos(tmp_path: Path) -> None:
    arq = tmp_path / "remendo.yaml"
    arq.write_text(
        f"classes:\n- slug: chapeu\n  versao: {V1}\n  _remendo: true\n- slug: persona\n  versao: {V2}\n  _remendo: true\n",
        encoding="utf-8",
    )

    def _responder_ok(rota: str, corpo: dict, _hdrs):
        assert rota == "/ensaiar"
        assert corpo["ato"] == "trocar"
        return 200, {
            "estado": "ensaio",
            "uso": "catalogo",
            "classes": ["chapeu", "persona"],
            "gravadas": [],
            "removidas": [],
        }

    srv, env, _ = _subir_duble(_responder_ok)
    try:
        saida = executar(["ensaiar", "trocar", str(arq)], env=env)
    finally:
        srv.shutdown()
        srv.server_close()

    assert saida.codigo == 0
    assert "classes: chapeu, persona" in saida.stdout

    def _responder_conflitos(_rota: str, _corpo: dict, _hdrs):
        return 422, {
            "estado": "recusada",
            "total": 2,
            "erros": [
                {
                    "codigo": "versao-diferente",
                    "onde": "/classes/0/versao",
                    "recebido": V1,
                    "regra": "A versão lida coincide com a gravada.",
                    "cura": f"A versão atual de chapeu é {V2}.",
                    "proximo": "ontologia ler shape chapeu",
                },
                {
                    "codigo": "versao-diferente",
                    "onde": "/classes/1/versao",
                    "recebido": V2,
                    "regra": "A versão lida coincide com a gravada.",
                    "cura": f"A versão atual de persona é {V1}.",
                    "proximo": "ontologia ler shape persona",
                },
            ],
            "leituras_atuais": [
                {"onde": "/classes/0/versao", "chave": "chapeu", "versao": V2, "yaml": ""},
                {"onde": "/classes/1/versao", "chave": "persona", "versao": V1, "yaml": ""},
            ],
        }

    srv2, env2, _ = _subir_duble(_responder_conflitos)
    try:
        saida_err = executar(["ensaiar", "trocar", str(arq)], env=env2)
    finally:
        srv2.shutdown()
        srv2.server_close()

    assert saida_err.codigo == 1
    linhas = [ln for ln in saida_err.stdout.splitlines() if ln.strip()]
    assert len(linhas) == 2
    assert all(ln.startswith("versao-diferente · ") for ln in linhas)
    assert "ontologia ler shape chapeu" in linhas[0]
    assert "ontologia ler shape persona" in linhas[1]


def test_recusa_de_uso_sem_versao_e_ajuda_documenta_remendo(tmp_path: Path) -> None:
    arq = tmp_path / "sem_versao.yaml"
    arq.write_text("classes:\n- slug: chapeu\n  _remendo: true\n  definicao: Nova\n", encoding="utf-8")

    def _responder_400(_rota: str, _corpo: dict, _hdrs):
        return 400, {"estado": "ilegivel", "erro": "trocar exige versão lida (em posição ou em /classes/0/versao)"}

    srv, env, _ = _subir_duble(_responder_400)
    try:
        saida = executar(["trocar", str(arq)], env=env)
        saida_uso = executar(["trocar"], env=env)
        saida_help = executar(["--help"], env=env)
    finally:
        srv.shutdown()
        srv.server_close()

    assert saida.codigo == 2
    assert "pedido-ilegivel" in saida.stdout
    assert saida_uso.codigo == 2
    assert "versao-ausente" in saida_uso.stdout
    assert saida_help.codigo == 0
    assert "_remendo: true" in saida_help.stdout
    assert "_remover: true" in saida_help.stdout
    assert "ontologia trocar <arquivo.yaml>" in saida_help.stdout
