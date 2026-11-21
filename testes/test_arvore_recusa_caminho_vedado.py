# componente: componente:verbo-lint
"""Regressivo #4400 / #4403: bin/_lint/arvore.py e bin/_lint/pre_commit.py recusam
qualquer arquivo sob o caminho vedado no espelho com ARVORE_RAIZ e liberam as três
raízes válidas (instancias/, referencias/, verbetes/).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ_HARNESS = Path(__file__).resolve().parents[1]
if str(RAIZ_HARNESS / "bin") not in sys.path:
    sys.path.insert(0, str(RAIZ_HARNESS / "bin"))

from _lint.arvore import RAIZES, verificar_arvore  # noqa: E402
from _lint.pre_commit import bloqueantes_caminho_vedado_no_stage  # noqa: E402

_VEDADO = "outros" + "_repos"
_PRE_COMMIT = RAIZ_HARNESS / "bin" / "_lint" / "pre_commit.py"


def _init_repo(tmp_path: Path, remote_url: str | None = None) -> Path:
    repo = tmp_path / "casa"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, capture_output=True)
    if remote_url:
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=repo, check=True, capture_output=True)
    return repo


def test_raizes_nao_incluem_caminho_vedado():
    assert RAIZES == ("instancias", "referencias", "verbetes")
    assert _VEDADO not in RAIZES


def test_arvore_recusa_caminho_vedado_com_arvore_raiz(tmp_path: Path):
    repo = _init_repo(tmp_path)
    alvo = repo / _VEDADO / "x" / "a.py"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("x = 1\n", encoding="utf-8")

    apontamentos = verificar_arvore(repo, formas={})
    ids = [(a.id, a.arquivo) for a in apontamentos]
    assert ("ARVORE_RAIZ", _VEDADO) in ids


def test_arvore_aceita_tres_raizes_validas(tmp_path: Path):
    repo = _init_repo(tmp_path)
    (repo / "instancias" / "persona").mkdir(parents=True)
    (repo / "instancias" / "persona" / "ti.md").write_text("# TI\n", encoding="utf-8")
    (repo / "referencias" / "classes").mkdir(parents=True)
    (repo / "referencias" / "classes" / "persona.md").write_text("# Persona\n", encoding="utf-8")
    (repo / "verbetes" / "papel").mkdir(parents=True)
    (repo / "verbetes" / "papel" / "executor.md").write_text("# Executor\n", encoding="utf-8")

    formas = {
        "persona": {
            "golden": "instancias/persona/<slug>.md",
            "referencia": "referencias/classes/persona.md",
        }
    }
    apontamentos = verificar_arvore(
        repo,
        formas=formas,
        fichas=[("persona", "ti")],
        dicionarios={"papel": ["executor"]},
    )
    assert apontamentos == []


def test_pre_commit_bloqueia_caminho_vedado_no_espelho(tmp_path: Path):
    repo = _init_repo(tmp_path, remote_url="https://github.com/plcarvalho301/platafirma-casa.git")
    alvo = repo / _VEDADO / "harness" / "a.py"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", str(alvo.relative_to(repo))], cwd=repo, check=True, capture_output=True)

    achados = bloqueantes_caminho_vedado_no_stage(repo)
    assert len(achados) == 1
    assert achados[0].id == "ARVORE_RAIZ"
    assert achados[0].arquivo == f"{_VEDADO}/harness/a.py"

    proc = subprocess.run([sys.executable, str(_PRE_COMMIT)], cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 1
    assert f"{_VEDADO}/harness/a.py" in proc.stderr
    assert "repositório de destino" in proc.stderr


def test_pre_commit_libera_instancias_no_espelho(tmp_path: Path):
    repo = _init_repo(tmp_path, remote_url="https://github.com/plcarvalho301/platafirma-casa.git")
    alvo = repo / "instancias" / "persona" / "ti.md"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("# TI\n", encoding="utf-8")
    subprocess.run(["git", "add", str(alvo.relative_to(repo))], cwd=repo, check=True, capture_output=True)

    assert bloqueantes_caminho_vedado_no_stage(repo) == []

    proc = subprocess.run([sys.executable, str(_PRE_COMMIT)], cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
