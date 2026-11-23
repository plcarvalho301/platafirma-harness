# componente: componente:leitura
"""Testes da unificação de leitura sob `lib/leitura` (`ler_arquivo`) nos verbos (incidente #4433)."""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import threading
from pathlib import Path

RAIZ_HARNESS = Path(__file__).resolve().parents[1]
BIN_REPO = RAIZ_HARNESS / "bin" / "repo"
BIN_TAREFAS = RAIZ_HARNESS / "bin" / "tarefas"


def test_repo_ler_devolve_arquivo_grande_inteiro_e_suporta_recortes(tmp_path: Path) -> None:
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "meu-repo" / "ti" / "4433-teste"
    wt.mkdir(parents=True)
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", "-q", "-b", "fabrica/4433-teste"], cwd=wt, check=True, env=git_env)
    dados = "".join(f"linha {i:04d} — conteúdo utf-8 çãõ " + ("x" * 60) + "\n" for i in range(1200)).encode("utf-8")
    assert len(dados) > 100_000
    (wt / "grande.md").write_bytes(dados)

    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": "ti",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
    }
    # Por padrão devolve o arquivo de >100 KB inteiro, sem paginação de 45 KB
    r_int = subprocess.run(
        [str(BIN_REPO), "ler", "meu-repo@4433-teste", "grande.md"],
        env=env,
        capture_output=True,
        check=False,
    )
    assert r_int.returncode == 0, r_int.stderr
    assert r_int.stdout == dados
    assert b"truncado em" not in r_int.stdout

    # Fatiamento por --linhas e --offset/--max-bytes via lib/leitura
    r_lin = subprocess.run(
        [str(BIN_REPO), "ler", "meu-repo@4433-teste", "grande.md", "--linhas", "1-3", "--numerar"],
        env=env,
        capture_output=True,
        check=False,
    )
    assert r_lin.returncode == 0, r_lin.stderr
    linhas = r_lin.stdout.decode("utf-8").splitlines()
    assert [ln.split(":", 1)[0] for ln in linhas] == ["1", "2", "3"]

    r_off = subprocess.run(
        [str(BIN_REPO), "ler", "meu-repo@4433-teste", "grande.md", "--offset", str(len(dados) + 10)],
        env=env,
        capture_output=True,
        check=False,
    )
    assert r_off.returncode == 2


def test_tarefas_ler_e_comentarios_usam_lib_leitura_sem_aviso_fossil_de_45kb(tmp_path: Path) -> None:
    corpo_grande = "\n".join(f"<p>Parágrafo {i:04d} com detalhe técnico completo {'z' * 80}</p>" for i in range(600))

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/registro"):
                payload: dict[str, object] = {
                    "estados": [
                        {"estado": "em-mitigacao", "fase": "execucao", "natureza": "ativa"},
                        {"estado": "entregue", "fase": "terminal", "natureza": "terminal"},
                    ]
                }
            elif self.path.startswith("/api/itens/4433/comentarios"):
                payload = {
                    "comentarios": [
                        {
                            "id": 5582,
                            "autor": "ti",
                            "carimbo": "2026-11-23T00:00:00Z",
                            "corpo": corpo_grande,
                        }
                    ]
                }
            elif self.path.startswith("/api/itens/4433"):
                payload = {
                    "id": 4433,
                    "titulo": "Incidente leitura unificada",
                    "nivel": 2,
                    "nivel_nome": "story",
                    "estado": "em-mitigacao",
                    "estado_nome": "Em mitigação",
                    "estado_fase": "execucao",
                    "cadeira": "ti",
                    "tipo_demanda": "incidente",
                    "descricao": corpo_grande,
                    "ancestrais": [],
                    "filhas": [],
                }
            else:
                self.send_response(404)
                self.end_headers()
                return
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    porta_http = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        env = {
            **os.environ,
            "TAREFAS_BASE": f"http://127.0.0.1:{porta_http}/api",
            "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
            "PF_CADEIRA": "ti",
        }
        # `tarefas comentarios` > 60 KB sai inteiro e SEM o aviso fóssil de 45000/50000 bytes
        rc_com = subprocess.run(
            [str(BIN_TAREFAS), "comentarios", "4433"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert rc_com.returncode == 0, rc_com.stderr
        assert len(rc_com.stdout.encode("utf-8")) > 55_000
        assert "porta corta a saída em 50000" not in rc_com.stdout
        assert "Parágrafo 0000" in rc_com.stdout and "Parágrafo 0599" in rc_com.stdout

        # `tarefas ler` e `tarefas comentarios` aceitam --linhas e --offset via lib/leitura
        rc_lin = subprocess.run(
            [str(BIN_TAREFAS), "ler", "4433", "--linhas", "1-2"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert rc_lin.returncode == 0, rc_lin.stderr
        assert len(rc_lin.stdout.splitlines()) == 2
        assert "# Incidente leitura unificada" in rc_lin.stdout

        rc_bad = subprocess.run(
            [str(BIN_TAREFAS), "ler", "4433", "--offset", "-5"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert rc_bad.returncode == 2
    finally:
        srv.shutdown()
        srv.server_close()
