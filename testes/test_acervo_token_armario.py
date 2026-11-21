# componente: componente:verbo-acervo
"""Prova de resolução de RAG_API_TOKEN via armário de chaves da release (4406.r2; DTs 1008, 1202, 1339).

Sem `RAG_API_TOKEN` no ambiente (como a porta executa os verbos sob 4406.r2), `acervo ler biblioteca secao`,
`acervo ler biblioteca conceito` e `acervo ingerir casa` leem o token do armário de chaves da release
(`$PLATAFIRMA_RELEASE/core/deploy/armario-de-chaves.yaml`) resolvido na instância (`$PLATAFIRMA_INSTANCIA`).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from lib import acervo_token


def _python_com_requests() -> str:
    candidatos = [
        sys.executable,
        "/usr/bin/python3",
        shutil.which("python3") or "",
    ]
    for cand in candidatos:
        if cand and Path(cand).is_file():
            r = subprocess.run([cand, "-c", "import requests"], capture_output=True, timeout=5, check=False)
            if r.returncode == 0:
                return cand
    return sys.executable


def _preparar_armario(tmp_path: Path, segredos: dict[str, str]) -> tuple[Path, Path]:
    release = tmp_path / "release"
    inst = tmp_path / "instancia"
    (release / "core" / "deploy").mkdir(parents=True)
    linhas = ["versao: 1", "segredos:"]
    for nome, valor in segredos.items():
        rel = Path("segredos") / nome
        alvo = inst / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(valor + "\n", encoding="utf-8")
        linhas.append(f"  - nome: {nome}")
        linhas.append(f"    caminho: {rel.as_posix()}")
    (release / "core" / "deploy" / "armario-de-chaves.yaml").write_text(
        "\n".join(linhas) + "\n", encoding="utf-8"
    )
    return release, inst


class _ServidorToken:
    def __init__(self, rotas: dict[tuple[str, str], tuple[int, dict]]):
        self.rotas = rotas
        self.chamadas: list[tuple[str, str, str | None]] = []
        srv_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _atender(self, metodo: str) -> None:
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    self.rfile.read(n)
                srv_ref.chamadas.append((metodo, self.path, self.headers.get("Authorization")))
                status, corpo = srv_ref.rotas.get((metodo, self.path), (404, {"detail": "nao-achado"}))
                dados = json.dumps(corpo).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self) -> None:
                self._atender("GET")

            def do_POST(self) -> None:
                self._atender("POST")

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self._httpd.server_port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def fechar(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


def _env_porta(release: Path, inst: Path, base: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "RAG_API_TOKEN"}
    env["PLATAFIRMA_RELEASE"] = str(release)
    env["PLATAFIRMA_INSTANCIA"] = str(inst)
    env["MOTOR_ACERVO_URL"] = base
    env["RAG_API_URL"] = base
    env["RAG_API_BASE"] = base
    return env


def test_ler_token_acervo_precedencia_e_fallback(tmp_path: Path, monkeypatch) -> None:
    release, inst = _preparar_armario(tmp_path, {"rag/RAG_API_TOKEN": "tok-rag"})
    monkeypatch.delenv("RAG_API_TOKEN", raising=False)
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(release))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))

    assert acervo_token.ler_token_acervo() == "tok-rag"

    monkeypatch.setenv("RAG_API_TOKEN", "tok-env")
    assert acervo_token.ler_token_acervo() == "tok-env"

    monkeypatch.delenv("RAG_API_TOKEN")
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(tmp_path / "ausente"))
    assert acervo_token.ler_token_acervo() == ""


def test_secao_usa_token_do_armario_sem_env_dt_1202(tmp_path: Path) -> None:
    release, inst = _preparar_armario(tmp_path, {"acervo-guarda/RAG_API_TOKEN": "tok-secao-1202"})
    sid = "8cc00b2e-5280-52bc-b230-232d157ac62c"
    srv = _ServidorToken({
        ("POST", "/acervo/secoes/consulta"): (200, {
            "secoes": [{"secao_id": sid, "arquivo": "doc", "ancora": "a", "breadcrumb": [],
                        "texto": "conteudo", "particao": "biblioteca"}],
            "nao_achadas": [],
        }),
    })
    try:
        r = subprocess.run(
            [_python_com_requests(), str(RAIZ / "bin" / "_acervo" / "secao"), "biblioteca", sid],
            env=_env_porta(release, inst, srv.base),
            capture_output=True, text=True, timeout=15, check=False,
        )
        assert r.returncode == 0, r.stderr
        chamadas_secao = [auth for m, p, auth in srv.chamadas if (m, p) == ("POST", "/acervo/secoes/consulta")]
        assert chamadas_secao == ["Bearer tok-secao-1202"], srv.chamadas
    finally:
        srv.fechar()


def test_tesauro_usa_token_do_armario_sem_env_dt_1339(tmp_path: Path) -> None:
    release, inst = _preparar_armario(tmp_path, {"rag/RAG_API_TOKEN": "tok-tesauro-1339"})
    srv = _ServidorToken({
        ("GET", "/acervo/conceitos/esteira-de-implantacao"): (200, {
            "id": "15a606f0-611f-4f44-b0e6-3ab7b445f44b",
            "slug": "esteira-de-implantacao",
            "rotulo": "Esteira de implantação",
            "lingua": "pt",
            "definicao": "Caminho do código até a produção.",
            "natureza": "processo",
            "estatuto": "instituido",
            "endereco": None,
            "mais_amplo": None,
            "rotulos_alt": [],
            "versao": "a1b2c3d4e5f6",
        }),
        ("GET", "/acervo/conceitos/esteira-de-implantacao/relacoes"): (200, {"itens": [], "proximo": None}),
    })
    try:
        r = subprocess.run(
            [sys.executable, str(RAIZ / "bin" / "_acervo" / "tesauro.py"),
             "ler", "conceito", "esteira-de-implantacao", "--json"],
            env=_env_porta(release, inst, srv.base),
            capture_output=True, text=True, timeout=15, check=False,
        )
        assert r.returncode == 0, r.stderr
        auths = [auth for _, _, auth in srv.chamadas]
        assert auths and all(a == "Bearer tok-tesauro-1339" for a in auths), srv.chamadas
    finally:
        srv.fechar()


def test_casa_ingerir_usa_token_do_armario_sem_env_dt_1008(tmp_path: Path) -> None:
    release, inst = _preparar_armario(tmp_path, {"busca/RAG_API_TOKEN": "tok-casa-1008"})
    arvore = inst / "var" / "pre-push" / "casa-teste"
    arvore.mkdir(parents=True)
    (arvore / "doc.md").write_text("# Titulo\n\nCorpo.\n", encoding="utf-8")
    srv = _ServidorToken({
        ("POST", "/acervo/casa/lotes"): (201, {
            "lote_id": "00000000-0000-0000-0000-000000000001",
            "estado": "plano",
            "itens": [{"path": "doc.md", "veredito": "ja_ingerido"}],
            "resumo": {"criar": 0, "edicao": 0, "ja_ingerido": 1, "reprovado": 0, "retirar": 0},
        }),
    })
    try:
        r = subprocess.run(
            [_python_com_requests(), str(RAIZ / "bin" / "_acervo" / "casa-ingerir"),
             "platafirma-casa", "--arvore", str(arvore), "--json"],
            env=_env_porta(release, inst, srv.base),
            capture_output=True, text=True, timeout=15, check=False,
        )
        assert r.returncode == 0, r.stderr
        chamadas_lote = [auth for m, p, auth in srv.chamadas if (m, p) == ("POST", "/acervo/casa/lotes")]
        assert chamadas_lote == ["Bearer tok-casa-1008"], srv.chamadas
    finally:
        srv.fechar()
