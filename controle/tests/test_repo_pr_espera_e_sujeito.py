# componente: componente:verbo-repo
"""Contrato dos DTs 915 (`repo pr-abrir --espera` + `pr-merge` de rascunho) e 928 (`PF_SUJEITO` sem `PF_CADEIRA`)."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
TAREFAS_BIN = Path(__file__).resolve().parents[2] / "bin" / "tarefas"
IDENT = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}

GH_FIXTURE_915 = """#!/bin/sh
d="$(dirname "$0")"
printf '%s\\n' "$*" >> "$d/calls.log"
if [ "$1" = api ]; then
  echo "$*" >> "$d/api"
  exit 0
fi
case "$1 $2" in
  "pr list")
    if [ -f "$d/pr_criado" ]; then
      echo "#7 https://forge/demo/pull/7 (head $(cat "$d/oid" | cut -c1-7))"
    fi ;;
  "pr create")
    echo "$*" > "$d/create_args"
    case "$*" in
      *--draft*) echo true > "$d/draft" ;;
      *)         echo false > "$d/draft" ;;
    esac
    echo OPEN > "$d/estado"
    touch "$d/pr_criado"
    exit 0 ;;
  "pr ready")
    echo "$*" > "$d/ready_args"
    echo false > "$d/draft"
    exit 0 ;;
  "pr view")
    case "$*" in
      *"--json state,headRefName,headRefOid,mergeCommit,isDraft"*)
        echo "$(cat "$d/estado") $(cat "$d/ramo") $(cat "$d/mergeoid" 2>/dev/null || echo -) $(cat "$d/oid") $(cat "$d/draft" 2>/dev/null || echo false)" ;;
      *"--json number,state,url,headRefOid"*)
        echo "#7 $(cat "$d/estado") https://forge/demo/pull/7 (head $(cat "$d/oid" | cut -c1-7))" ;;
      *"--json state,mergeCommit"*)
        echo "$(cat "$d/estado") $(cat "$d/mergeoid" 2>/dev/null || echo -)" ;;
      *"--json statusCheckRollup"*)
        echo '{"statusCheckRollup":[]}' ;;
      *) cat "$d/estado" ;;
    esac ;;
  "pr merge")
    if [ "$(cat "$d/draft" 2>/dev/null)" = "true" ]; then
      echo "Pull request #7 is a draft" >&2
      exit 1
    fi
    echo MERGED > "$d/estado"
    cat "$d/oid" > "$d/mergeoid"
    exit 0 ;;
  "api repos/"*)
    echo "$*" > "$d/api"
    exit 0 ;;
  *) exit 0 ;;
esac
"""


def _git(*args, cwd=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **IDENT},
    ).stdout.strip()


def _montar_repo(tmp_path: Path):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    (semente / "LEIA.md").write_text("x\n")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    forge = tmp_path / "forge"
    forge.mkdir()
    gh = forge / "gh"
    gh.write_text(GH_FIXTURE_915)
    gh.chmod(0o755)
    return bancada, forge


def _rodar_repo(tmp_path: Path, bancada: Path, *args, extra_env=None):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "engenharia",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        "PF_GH_RETRY_SLEEP": "0",
        "PF_ESTEIRA_VEREDITOS_DIR": str(tmp_path / "vereditos"),
        "PF_HOOK_PREPUSH": "/nao-existe/pre-push",
        **IDENT,
    }
    if extra_env:
        for k, v in extra_env.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def test_dt915_pr_abrir_espera_abre_rascunho_e_pr_merge_promove_e_integra(tmp_path: Path):
    bancada, forge = _montar_repo(tmp_path)
    r = _rodar_repo(tmp_path, bancada, "abrir", "demo", "--slug", "espera")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "espera"
    (wt / "DOC.md").write_text("aguarda homologacao\n")
    _git("add", "DOC.md", cwd=wt)
    _git("commit", "-m", "doc em espera", cwd=wt)
    sha = _git("rev-parse", "HEAD", cwd=wt)
    (forge / "oid").write_text(sha + "\n")
    (forge / "ramo").write_text("engenharia/espera\n")

    # Semeia marca de pre-push e veredito verde
    marca_dir = tmp_path / "instancia" / "var" / "pre-push" / "vereditos"
    marca_dir.mkdir(parents=True, exist_ok=True)
    (marca_dir / f"portao-demo-{sha}").write_text("verde harness-0123456789ab\n")
    vdir = tmp_path / "vereditos"
    vdir.mkdir(parents=True, exist_ok=True)
    arv_mud = _git("rev-parse", "HEAD^{tree}", cwd=wt)
    arv_main = _git("rev-parse", "origin/main^{tree}", cwd=wt)
    (vdir / "demo.jsonl").write_text(
        json.dumps({"repositorio": "demo", "arvore_mudanca": arv_mud, "arvore_main": arv_main, "estado": "verde", "fichas": []}) + "\n"
    )

    assert _rodar_repo(tmp_path, bancada, "empurrar", "demo").returncode == 0
    if (forge / "api").exists():
        (forge / "api").unlink()

    r_ab = _rodar_repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "Aguarda homologacao", "--espera")
    assert r_ab.returncode == 0, r_ab.stdout + r_ab.stderr
    assert "--draft" in (forge / "create_args").read_text()
    assert (forge / "draft").read_text().strip() == "true"
    assert f"statuses/{sha}" in (forge / "api").read_text()
    assert "rascunho" in r_ab.stdout
    assert "repo pr-merge demo 7" in r_ab.stdout

    # Regime sem PR (22/11/2026): pr-merge recusa com 2 e aponta sincronizar
    r_mg = _rodar_repo(tmp_path, bancada, "pr-merge", "demo", "7")
    assert r_mg.returncode == 2, r_mg.stdout + r_mg.stderr
    assert "repo sincronizar demo" in r_mg.stderr


def test_dt928_repo_abrir_sem_pf_cadeira_usa_pf_sujeito(tmp_path: Path):
    bancada, _ = _montar_repo(tmp_path)
    # Sem PF_CADEIRA e sem PF_SUJEITO: recusa 3
    r_sem = _rodar_repo(
        tmp_path, bancada, "abrir", "demo", "--slug", "inc",
        extra_env={"PF_CADEIRA": None, "PF_SUJEITO": None},
    )
    assert r_sem.returncode == 3

    # Sem PF_CADEIRA, mas com PF_SUJEITO da conexão: abre bancada
    r_ok = _rodar_repo(
        tmp_path, bancada, "abrir", "demo", "--slug", "inc",
        extra_env={"PF_CADEIRA": None, "PF_SUJEITO": "sub-dono-928"},
    )
    assert r_ok.returncode == 0, r_ok.stdout + r_ok.stderr
    assert (bancada / "wt" / "demo" / "sub-dono-928" / "inc" / ".git").exists()


def test_dt928_tarefas_sem_pf_cadeira_carimba_pf_sujeito(tmp_path: Path):
    capturado: dict[str, str] = {}

    class _H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            _ = self.rfile.read(n)
            capturado["hdr"] = self.headers.get("x-auth-request-preferred-username", "")
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 9999, "titulo": "Incidente", "estado": "aberto"}).encode())

        def log_message(self, *args):
            pass

    srv = HTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(tmp_path),
            "TAREFAS_BASE": f"http://127.0.0.1:{srv.server_port}/api",
            "PF_SUJEITO": "sub-dono-928",
        }
        r = subprocess.run(
            [str(TAREFAS_BIN), "criar", "Incidente abertura", "--incidente", "--cadeira", "ti"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert capturado.get("hdr") == "sub-dono-928"
    finally:
        srv.shutdown()
