# componente: componente:avisos
"""Testes da rodada de avisos OSV (`seg avisos`, card #4417)."""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "lib"))

import avisos as av  # noqa: E402


def _rodar_servidor(rotas):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            corpo = json.loads(self.rfile.read(tam).decode("utf-8") or "{}")
            status, resp = rotas("POST", self.path, corpo)
            raw = json.dumps(resp).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            status, resp = rotas("GET", self.path, {})
            raw = json.dumps(resp).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_aviso_em_pacote_pinado_levanta_alerta_com_dono_e_prazo_e_deduplica(tmp_path):
    trilha = tmp_path / "avisos.jsonl"
    deps = [
        av.DependenciaPinada(
            dependente="receita:venv-porta",
            dono="ti",
            dependencia="dependencia-externa:pypi.org:mcp",
            ecossistema="PyPI",
            pacote="mcp",
            versao="1.28.1",
            pino="1.28.1",
        )
    ]
    agora = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)

    rc, alertas = av.avaliar_avisos(
        deps,
        consultar_lote=lambda qs: [{"vulns": [{"id": "PYSEC-2026-0001"}]}],
        consultar_aviso=lambda vid: {
            "id": vid,
            "summary": "Falha de teste em mcp 1.28.1",
            "aliases": ["CVE-2026-99999"],
            "database_specific": {"severity": "HIGH"},
        },
        trilha=trilha,
        agora_fn=lambda: agora,
    )
    assert rc == 0
    assert len(alertas) == 1
    assert alertas[0]["esfera"] == "plataforma"
    assert alertas[0]["sobre"] == "receita:venv-porta"
    assert alertas[0]["dono"] == "ti"
    assert alertas[0]["prazo"] == "2026-12-20T12:00:00Z"
    payload = json.loads(alertas[0]["payload"])
    assert payload["aviso"] == "PYSEC-2026-0001"
    assert payload["aliases"] == ["CVE-2026-99999"]
    assert payload["severidade"] == "HIGH"

    # Segunda rodada com o mesmo aviso sobre o mesmo dependente não duplica
    rc2, alertas2 = av.avaliar_avisos(
        deps,
        consultar_lote=lambda qs: [{"vulns": [{"id": "PYSEC-2026-0001"}]}],
        consultar_aviso=lambda vid: {"id": vid, "summary": "Falha de teste em mcp 1.28.1"},
        trilha=trilha,
        agora_fn=lambda: agora,
    )
    assert rc2 == 0
    assert alertas2 == []


def test_aviso_em_versao_nao_usada_nao_levanta_alerta(tmp_path):
    trilha = tmp_path / "avisos.jsonl"
    deps = [
        av.DependenciaPinada(
            dependente="receita:venv-porta",
            dono="ti",
            dependencia="dependencia-externa:pypi.org:pyyaml",
            ecossistema="PyPI",
            pacote="pyyaml",
            versao="6.0.3",
            pino="6.0.3",
        )
    ]
    rc, alertas = av.avaliar_avisos(
        deps,
        consultar_lote=lambda qs: [{}],
        consultar_aviso=lambda vid: (_ for _ in ()).throw(AssertionError("não deve hidratar sem match")),
        trilha=trilha,
    )
    assert rc == 0
    assert alertas == []
    linhas = [json.loads(l) for l in trilha.read_text(encoding="utf-8").splitlines()]
    assert [e["tipo-de-evento"] for e in linhas] == [
        "seg.avisos.rodada-iniciada",
        "seg.avisos.rodada-concluida",
    ]


def test_base_de_avisos_fora_do_ar_sai_5_e_nao_grava_alerta(tmp_path):
    trilha = tmp_path / "avisos.jsonl"
    deps = [
        av.DependenciaPinada(
            dependente="receita:venv-porta",
            dono="ti",
            dependencia="dependencia-externa:pypi.org:uvicorn",
            ecossistema="PyPI",
            pacote="uvicorn",
            versao="0.51.0",
            pino="0.51.0",
        )
    ]

    def falha(_qs):
        raise av.ErroBaseAvisos("OSV fora do ar")

    rc, alertas = av.avaliar_avisos(
        deps,
        consultar_lote=falha,
        consultar_aviso=lambda vid: {},
        trilha=trilha,
    )
    assert rc == 5
    assert alertas == []
    linhas = [json.loads(l) for l in trilha.read_text(encoding="utf-8").splitlines()]
    assert [e["tipo-de-evento"] for e in linhas] == [
        "seg.avisos.rodada-iniciada",
        "seg.avisos.rodada-falhou",
    ]


def test_cli_seg_avisos_aviso_em_pacote_pinado_via_loopback(tmp_path):
    def olaria(method, path, body):
        assert method == "POST" and path == "/ler"
        classe = body.get("classe")
        if classe == "dependencia-externa":
            return 200, {"yaml": (
                "classe: dependencia-externa\nfichas:\n"
                "- chave: dependencia-externa:pypi.org:mcp\n"
                "  dados:\n    nome: mcp\n    origem: pypi.org\n"
            )}
        if classe == "receita":
            return 200, {"yaml": (
                "classe: receita\nfichas:\n"
                "- chave: receita:venv-porta\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:pypi.org:mcp\n"
                "      pino: 1.28.1\n"
            )}
        return 200, {"yaml": f"classe: {classe}\nfichas: []\n"}

    def osv(method, path, body):
        if method == "POST" and path == "/v1/querybatch":
            assert body["queries"] == [{"package": {"ecosystem": "PyPI", "name": "mcp"}, "version": "1.28.1"}]
            return 200, {"results": [{"vulns": [{"id": "GHSA-test-4417"}]}]}
        if method == "GET" and path == "/v1/vulns/GHSA-test-4417":
            return 200, {"id": "GHSA-test-4417", "summary": "Aviso de teste 4417"}
        return 404, {"erro": "nao encontrado"}

    srv_olaria, url_olaria = _rodar_servidor(olaria)
    srv_osv, url_osv = _rodar_servidor(osv)
    try:
        env = dict(os.environ)
        env.update({
            "OLARIA_URL": url_olaria,
            "OLARIA_CHAVE": "chave-teste",
            "OSV_API_URL": url_osv,
            "SEG_LOG_DIR": str(tmp_path),
        })
        proc = subprocess.run(
            [str(RAIZ / "bin" / "seg"), "avisos", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        saida = json.loads(proc.stdout)
        assert saida["total"] == 1
        assert saida["alertas"][0]["esfera"] == "plataforma"
        assert saida["alertas"][0]["sobre"] == "receita:venv-porta"
        assert saida["alertas"][0]["dono"] == "ti"
        assert saida["alertas"][0]["prazo"]
        assert (tmp_path / "avisos.jsonl").is_file()
    finally:
        srv_olaria.shutdown()
        srv_osv.shutdown()


def test_paginacao_osv_next_page_token_e_linha_corrompida_na_trilha(tmp_path):
    trilha = tmp_path / "avisos.jsonl"
    trilha.write_text("{linha-quebrada\n", encoding="utf-8")
    deps = [
        av.DependenciaPinada(
            dependente="receita:venv-porta",
            dono="ti",
            dependencia="dependencia-externa:pypi.org:mcp",
            ecossistema="PyPI",
            pacote="mcp",
            versao="1.28.1",
            pino="1.28.1",
        )
    ]

    chamadas: list[list[dict]] = []

    def consultar_lote(qs: list[dict]) -> list[dict]:
        chamadas.append(qs)
        if len(chamadas) == 1:
            return [{"vulns": [{"id": "OSV-PAG-1"}], "next_page_token": "tok-2"}]
        assert qs[0].get("page_token") == "tok-2"
        return [{"vulns": [{"id": "OSV-PAG-2"}]}]

    rc, alertas = av.avaliar_avisos(
        deps,
        consultar_lote=consultar_lote,
        consultar_aviso=lambda vid: {"id": vid, "summary": f"Resumo {vid}"},
        trilha=trilha,
    )
    assert rc == 0
    assert len(chamadas) == 2
    assert {json.loads(a["payload"])["aviso"] for a in alertas} == {"OSV-PAG-1", "OSV-PAG-2"}


def test_cli_olaria_fora_do_ar_sai_5_e_registra_falha_na_trilha(tmp_path):
    env = dict(os.environ)
    env.update({
        "OLARIA_URL": "http://127.0.0.1:1",
        "OLARIA_CHAVE": "chave-teste",
        "SEG_LOG_DIR": str(tmp_path),
    })
    proc = subprocess.run(
        [str(RAIZ / "bin" / "seg"), "avisos"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 5
    linhas = [json.loads(l) for l in (tmp_path / "avisos.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [e["tipo-de-evento"] for e in linhas] == [
        "seg.avisos.rodada-iniciada",
        "seg.avisos.rodada-falhou",
    ]
    assert all(e["esfera"] == "plataforma" for e in linhas)
