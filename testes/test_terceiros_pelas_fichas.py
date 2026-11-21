# componente: componente:terceiros
"""Testes de materialização e expurgo de terceiros pelas fichas da Olaria (card #4417)."""
from __future__ import annotations

import hashlib
import http.server
import importlib.machinery
import importlib.util
import json
import os
import ssl
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "lib"))

import terceiros_olaria as to  # noqa: E402


def _gerar_cert_loopback(tmp_path: Path) -> tuple[Path, Path]:
    cert = tmp_path / "loopback.crt"
    chave = tmp_path / "loopback.key"
    proc = subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(chave), "-out", str(cert),
            "-days", "1", "-subj", "/CN=127.0.0.1",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "subjectAltName=IP:127.0.0.1",
        ],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return cert, chave


def _servidor_http(handler_fn, *, ssl_cert: tuple[Path, Path] | None = None):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(tam)
            status, ctype, payload = handler_fn("POST", self.path, raw)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            status, ctype, payload = handler_fn("GET", self.path, b"")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    esquema = "http"
    if ssl_cert is not None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(ssl_cert[0]), keyfile=str(ssl_cert[1]))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        esquema = "https"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"{esquema}://127.0.0.1:{srv.server_address[1]}"


def _rodar_materializar(familia: str, arvore: Path, cache: Path, env_extra: dict[str, str]):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    env.update(env_extra)
    if "CURL_CA_BUNDLE" in env_extra and "SSL_CERT_FILE" not in env_extra:
        env["SSL_CERT_FILE"] = env_extra["CURL_CA_BUNDLE"]
    cmd = f'. "{RAIZ}/lib/terceiros.sh" && materializar_terceiros_em "{familia}" "{arvore}" "{cache}"'
    return subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True, check=False, timeout=30)


def _carregar_expurgo():
    caminho = RAIZ / "bin" / "_release" / "expurgo"
    loader = importlib.machinery.SourceFileLoader("pf_expurgo_teste_4417", str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod


def test_terceiro_materializado_pelas_fichas_com_download_e_cache(tmp_path):
    conteudo = b"conteudo-pinado-4417\n"
    sha = hashlib.sha256(conteudo).hexdigest()
    cert, chave = _gerar_cert_loopback(tmp_path)

    def artefato_fn(method, path, _raw):
        if method == "GET" and path == "/artefato.bin":
            return 200, "application/octet-stream", conteudo
        return 404, "text/plain", b"nao encontrado"

    srv_https, url_https = _servidor_http(artefato_fn, ssl_cert=(cert, chave))

    def olaria_fn(method, path, _raw):
        if method == "POST" and path == "/ler":
            yaml_txt = (
                "classe: stack\nfichas:\n"
                "- chave: stack:harness\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:teste:artefato\n"
                "      nome: artefato-teste\n"
                "      familia: platafirma-harness\n"
                "      destino: terceiros/artefato.bin\n"
                f"      pino: sha256:{sha}\n"
                f"      url: {url_https}/artefato.bin\n"
            )
            return 200, "application/json", json.dumps({"yaml": yaml_txt}).encode("utf-8")
        return 404, "text/plain", b"nao encontrado"

    srv_olaria, url_olaria = _servidor_http(olaria_fn)
    try:
        arvore = tmp_path / "arvore"
        arvore.mkdir()
        cache = tmp_path / "cache"
        proc = _rodar_materializar(
            "platafirma-harness",
            arvore,
            cache,
            {
                "OLARIA_URL": url_olaria,
                "OLARIA_CHAVE": "chave-teste",
                "CURL_CA_BUNDLE": str(cert),
            },
        )
        assert proc.returncode == 0, proc.stderr
        assert (arvore / "terceiros/artefato.bin").read_bytes() == conteudo
        assert (cache / sha).read_bytes() == conteudo
        assert to.shas_declarados({"OLARIA_URL": url_olaria, "OLARIA_CHAVE": "chave-teste"}) == {sha}
    finally:
        srv_olaria.shutdown()
        srv_https.shutdown()


def test_terceiro_com_url_http_sem_tls_recusa_com_saida_3(tmp_path):
    sha = "b" * 64

    def olaria_fn(method, path, _raw):
        if method == "POST" and path == "/ler":
            yaml_txt = (
                "classe: stack\nfichas:\n"
                "- chave: stack:harness\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:teste:inseguro\n"
                "      nome: artefato-http\n"
                "      familia: platafirma-harness\n"
                "      destino: terceiros/inseguro.bin\n"
                f"      pino: sha256:{sha}\n"
                "      url: http://127.0.0.1:9999/inseguro.bin\n"
            )
            return 200, "application/json", json.dumps({"yaml": yaml_txt}).encode("utf-8")
        return 404, "text/plain", b"nao encontrado"

    srv_olaria, url_olaria = _servidor_http(olaria_fn)
    try:
        arvore = tmp_path / "arvore"
        arvore.mkdir()
        cache = tmp_path / "cache"
        proc = _rodar_materializar(
            "platafirma-harness",
            arvore,
            cache,
            {"OLARIA_URL": url_olaria, "OLARIA_CHAVE": "chave-teste"},
        )
        assert proc.returncode == 3
        assert "mal declarado" in proc.stderr
        assert not (arvore / "terceiros/inseguro.bin").exists()
    finally:
        srv_olaria.shutdown()


def test_terceiro_com_sha256_diferente_do_pino_recusa_com_saida_4(tmp_path):
    sha_esperado = "a" * 64
    cert, chave = _gerar_cert_loopback(tmp_path)

    def artefato_fn(method, path, _raw):
        if method == "GET" and path == "/adulterado.bin":
            return 200, "application/octet-stream", b"conteudo-adulterado\n"
        return 404, "text/plain", b"nao encontrado"

    srv_https, url_https = _servidor_http(artefato_fn, ssl_cert=(cert, chave))

    def olaria_fn(method, path, _raw):
        if method == "POST" and path == "/ler":
            yaml_txt = (
                "classe: stack\nfichas:\n"
                "- chave: stack:harness\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:teste:adulterado\n"
                "      nome: artefato-adulterado\n"
                "      familia: platafirma-harness\n"
                "      destino: terceiros/adulterado.bin\n"
                f"      pino: sha256:{sha_esperado}\n"
                f"      url: {url_https}/adulterado.bin\n"
            )
            return 200, "application/json", json.dumps({"yaml": yaml_txt}).encode("utf-8")
        return 404, "text/plain", b"nao encontrado"

    srv_olaria, url_olaria = _servidor_http(olaria_fn)
    try:
        arvore = tmp_path / "arvore"
        arvore.mkdir()
        cache = tmp_path / "cache"
        proc = _rodar_materializar(
            "platafirma-harness",
            arvore,
            cache,
            {
                "OLARIA_URL": url_olaria,
                "OLARIA_CHAVE": "chave-teste",
                "CURL_CA_BUNDLE": str(cert),
            },
        )
        assert proc.returncode == 4
        assert "current intacto" in proc.stderr
        assert not (arvore / "terceiros/adulterado.bin").exists()
    finally:
        srv_olaria.shutdown()
        srv_https.shutdown()


def test_olaria_fora_do_ar_sai_3_sem_tocar_arvore(tmp_path):
    arvore = tmp_path / "arvore"
    arvore.mkdir()
    cache = tmp_path / "cache"
    proc = _rodar_materializar(
        "platafirma-harness",
        arvore,
        cache,
        {"OLARIA_URL": "http://127.0.0.1:1", "OLARIA_CHAVE": "chave-teste"},
    )
    assert proc.returncode == 3
    assert "Olaria" in proc.stderr
    assert list(arvore.iterdir()) == []


def test_expurgo_falha_fechado_sem_apagar_cache_quando_olaria_cai(tmp_path, monkeypatch):
    raiz = tmp_path / "opt"
    inst = tmp_path / "srv"
    (inst / "var" / "release").mkdir(parents=True)
    reg = tmp_path / "reg"
    reg.mkdir()
    (reg / "familias.json").write_text(json.dumps({"platafirma-harness": "https://example.invalid/h.git"}), encoding="utf-8")
    (reg / "venvs.json").write_text(json.dumps({}), encoding="utf-8")
    cache_arq = raiz / "terceiros" / "sha256" / ("c" * 64)
    cache_arq.parent.mkdir(parents=True)
    cache_arq.write_text("pinado", encoding="utf-8")

    monkeypatch.setenv("OLARIA_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("OLARIA_CHAVE", "chave-teste")
    monkeypatch.setenv("PLATAFIRMA_FAMILIAS", str(reg / "familias.json"))
    monkeypatch.setenv("PLATAFIRMA_VENVS", str(reg / "venvs.json"))
    monkeypatch.setenv("PF_EXPURGO_SEM_DOCKER", "1")
    monkeypatch.setenv("PF_EXPURGO_SEM_PROC", "1")

    exp = _carregar_expurgo()
    fosseis, indet = exp.diagnosticar_fosseis(raiz, inst, incluir_imagens=False, sem_docker=True)
    assert any("terceiros:" in m for m in indet)
    assert not any(f.categoria == "terceiro" for f in fosseis)

    rc = exp.executar_expurgo(raiz, inst, sem_docker=True)
    assert rc == 0
    assert cache_arq.is_file(), "expurgo não pode apagar cache de terceiros quando a Olaria está fora do ar"
