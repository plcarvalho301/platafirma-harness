"""Regressivo #4400: bin/_lint/arvore.py recusa qualquer arquivo sob outros_repos/ com ARVORE_RAIZ
e libera as três raízes válidas (instancias/, referencias/, verbetes/).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
import sys

RAIZ_HARNESS = Path(__file__).resolve().parents[1]
if str(RAIZ_HARNESS / "bin") not in sys.path:
    sys.path.insert(0, str(RAIZ_HARNESS / "bin"))

from _lint.arvore import RAIZES, verificar_arvore  # noqa: E402


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "casa"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, capture_output=True)
    return repo


def test_raizes_nao_incluem_outros_repos():
    assert RAIZES == ("instancias", "referencias", "verbetes")
    assert "outros_repos" not in RAIZES


def test_arvore_recusa_outros_repos_com_arvore_raiz(tmp_path: Path):
    repo = _init_repo(tmp_path)
    alvo = repo / "outros_repos" / "x" / "a.py"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("x = 1\n", encoding="utf-8")

    apontamentos = verificar_arvore(repo, formas={})
    ids = [(a.id, a.arquivo) for a in apontamentos]
    assert ("ARVORE_RAIZ", "outros_repos") in ids


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
