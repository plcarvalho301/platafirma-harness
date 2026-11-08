"""Testes de regressão para DT 376: teste bench e injeção de ambiente de banco."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from lib import ambiente_banco

TESTE_BIN = RAIZ / "bin" / "teste"

def test_ambiente_banco_leitura(tmp_path, monkeypatch):
    seg_dir = tmp_path / "segredos" / "rag"
    seg_dir.mkdir(parents=True)
    (seg_dir / "POSTGRES_DB").write_text("rag_extractor\n", encoding="utf-8")
    (seg_dir / "POSTGRES_USER").write_text("rag_user\n", encoding="utf-8")
    (seg_dir / "EMBED_MODEL").write_text("qwen-test\n", encoding="utf-8")

    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    monkeypatch.setenv("PF_MOTOR_REG", str(tmp_path / "inexistente.json"))

    env = ambiente_banco.ambiente_da_stack("rag")
    assert env["POSTGRES_DB"] == "rag_extractor"
    assert env["POSTGRES_USER"] == "rag_user"
    assert env["EMBED_MODEL"] == "qwen-test"

def test_teste_bench_uso_sem_script():
    r = subprocess.run([str(TESTE_BIN), "bench"], capture_output=True, text=True, check=False, timeout=10)
    assert r.returncode == 2
    assert "uso: teste bench" in r.stderr or "uso:" in r.stderr

def test_teste_bench_executa_script_com_ambiente(tmp_path):
    bancada = tmp_path / "bancada"
    repo = bancada / "platafirma-conhecimento"
    rag_dir = repo / "rag"
    bench_dir = rag_dir / "bench"
    bench_dir.mkdir(parents=True)

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, timeout=10)
    lock_conteudo = b"lock-conteudo-teste\n"
    (rag_dir / "uv.lock").write_bytes(lock_conteudo)
    (rag_dir / "pyproject.toml").write_text("[project]\nname='rag'\nversion='0'\n", encoding="utf-8")

    script = bench_dir / "medida_teste.py"
    script.write_text(
        "import os\n"
        "print('BENCH_OK: ' + os.environ.get('EMBED_MODEL', 'SEM_EMBED'))\n",
        encoding="utf-8"
    )

    subprocess.run(["git", "add", "."], cwd=repo, check=True, timeout=10)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"],
        cwd=repo,
        check=True,
        timeout=10,
    )

    wt_dir = bancada / "wt" / "platafirma-conhecimento" / "ti" / "dt376"
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(wt_dir), "main"], cwd=repo, check=True, timeout=10)

    instancia = tmp_path / "instancia"
    seg = instancia / "segredos" / "rag"
    seg.mkdir(parents=True)
    (seg / "EMBED_MODEL").write_text("modelo-medido-123\n", encoding="utf-8")

    # Mock de release com o venv já construído para evitar dependência de uv na rede
    release_raiz = tmp_path / "release"
    py_cands = ["/usr/bin/python3.12", "/usr/bin/python3"]
    py_exec = next((p for p in py_cands if os.path.exists(p) and os.access(p, os.X_OK)), sys.executable)
    py_real = os.path.realpath(py_exec)
    py_ver = subprocess.check_output(
        [py_exec, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
        text=True,
        timeout=10,
    ).strip()

    hash_env = hashlib.sha256(lock_conteudo + f"\npython={py_real} {py_ver}\n".encode()).hexdigest()[:12]

    venv_dir = release_raiz / "venv" / f"rag-{hash_env}"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").symlink_to(py_exec)
    (venv_dir / "pyvenv.cfg").write_text(f"home = {os.path.dirname(py_real)}\n", encoding="utf-8")
    (venv_dir / ".pronto").touch()

    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_INSTANCIA": str(instancia),
        "PLATAFIRMA_PYTHON": py_exec,
        "PF_RELEASE_RAIZ": str(release_raiz),
        "PF_CADEIRA": "ti",
        "PF_MOTOR_REG": str(tmp_path / "inexistente.json"),
    }

    r = subprocess.run(
        [str(TESTE_BIN), "bench", "platafirma-conhecimento@dt376", "rag/bench/medida_teste.py"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "BENCH_OK: modelo-medido-123" in r.stdout
