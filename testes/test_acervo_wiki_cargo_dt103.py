"""DT #103: acervo wiki cargo diagnostica campo/tabela inválidos em vez de exibir MWException crua."""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
import urllib.parse
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WIKI_BIN = RAIZ / "bin" / "_acervo" / "wiki"


@contextmanager
def wiki_falsa(handler_fn):
    chamadas: list[dict[str, str]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            qs = urllib.parse.urlparse(self.path).query
            params = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}
            chamadas.append(params)
            body = json.dumps(handler_fn(params)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/api.php"
        yield url, chamadas
    finally:
        srv.shutdown()
        srv.server_close()


def _rodar_cargo(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "MW_API_URL": url}
    return subprocess.run(
        [sys.executable, str(WIKI_BIN), "cargo", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


def test_cargo_caminho_feliz_uma_chamada():
    def api(p):
        assert p["action"] == "cargoquery"
        return {"cargoquery": [{"title": {"pagina": "IA/x", "especie": "spec"}}]}

    with wiki_falsa(api) as (url, chamadas):
        r = _rodar_cargo(url, "Paginas", "_pageName=pagina, especie", "--json")

    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{"pagina": "IA/x", "especie": "spec"}]
    assert len(chamadas) == 1


def test_cargo_campo_invalido_caso_dt103():
    def api(p):
        if p["action"] == "cargoquery":
            return {
                "error": {
                    "code": "internal_api_error_MWException",
                    "info": "[c217332eef25611815d15bad] Exception caught: Unknown column 'tipo'",
                }
            }
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {
                "cargofields": {
                    "titulo": {"type": "String"},
                    "dominio": {"type": "String"},
                    "especie": {"type": "String"},
                }
            }
        raise AssertionError(f"chamada inesperada: {p}")

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(url, "Paginas", "tipo, COUNT(*)=n", "--group-by", "tipo")

    assert r.returncode == 1
    assert "internal_api_error_MWException" not in r.stderr
    assert "tipo" in r.stderr
    for campo in ("titulo", "dominio", "especie"):
        assert campo in r.stderr


def test_cargo_campo_invalido_apenas_em_group_by():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "boom"}}
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {"cargofields": {"titulo": {"type": "String"}, "especie": {"type": "String"}}}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(url, "Paginas", "_pageName=pagina, COUNT(*)=n", "--group-by", "tipo")

    assert r.returncode == 1
    assert "tipo" in r.stderr
    assert "titulo" in r.stderr
    assert "especie" in r.stderr


def test_cargo_where_ignora_literais_string_e_aponta_campo_errado():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "boom"}}
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {"cargofields": {"dominio": {"type": "String"}, "especie": {"type": "String"}}}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(url, "Paginas", "dominio", "--where", "dominio = 'tipo' AND errado = 1")

    assert r.returncode == 1
    assert "errado" in r.stderr
    assert "tipo" not in r.stderr
    assert "dominio, especie" in r.stderr


def test_cargo_order_by_aceita_alias_de_fields_e_acusa_campo_invalido():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "boom"}}
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {"cargofields": {"especie": {"type": "String"}}}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(
            url, "Paginas", "especie, COUNT(*)=n", "--group-by", "especie", "--order-by", "n DESC, bogus ASC"
        )

    assert r.returncode == 1
    assert "bogus" in r.stderr
    assert "n," not in r.stderr and ": n." not in r.stderr


def test_cargo_tabela_desconhecida_lista_tabelas():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "no such table"}}
        if p["action"] == "cargofields":
            return {"error": {"code": "invalidtable", "info": "table not found"}}
        if p["action"] == "cargotables":
            return {"cargotables": ["Paginas", "Referencias", "Frentes"]}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(url, "TabelaFake", "campo")

    assert r.returncode == 1
    assert "TabelaFake" in r.stderr
    assert "Paginas, Referencias, Frentes" in r.stderr


def test_cargo_multiplas_tabelas_com_alias():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "bad col"}}
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {"cargofields": {"titulo": {"type": "String"}}}
        if p["action"] == "cargofields" and p.get("table") == "Referencias":
            return {"cargofields": {"obra": {"type": "String"}}}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(
            url, "Paginas=p, Referencias=r", "p.titulo, r.inexistente", "--join-on", "p._pageName=r._pageName"
        )

    assert r.returncode == 1
    assert "r.inexistente" in r.stderr
    assert "Paginas: titulo" in r.stderr
    assert "Referencias: obra" in r.stderr


def test_cargo_erro_com_campos_validos_mostra_erro_e_campos():
    def api(p):
        if p["action"] == "cargoquery":
            return {"error": {"code": "internal_api_error_MWException", "info": "syntax error"}}
        if p["action"] == "cargofields" and p.get("table") == "Paginas":
            return {"cargofields": {"dominio": {"type": "String"}, "especie": {"type": "String"}}}
        raise AssertionError(p)

    with wiki_falsa(api) as (url, _):
        r = _rodar_cargo(url, "Paginas", "dominio", "--where", "dominio === 'ia'")

    assert r.returncode == 1
    assert "internal_api_error_MWException: syntax error" in r.stderr
    assert "dominio, especie" in r.stderr
