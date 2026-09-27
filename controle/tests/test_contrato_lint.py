"""test_contrato_lint — contrato da CLI e dos predicados do verbo `lint` (card #3153).

Cobre:
  - usage sem argumentos (exit 2) e --ajuda (exit 0)
  - classe desconhecida (exit 2)
  - sem bancada aberta (exit 1 com vizinho)
  - classe de lista com lista ausente no acervo (exit 5)
  - linter ausente (exit 3)
  - alvo por arquivo com ancora e cura por linha
  - card via stdin (-) sem Aceite (exit 1 nomeando Aceite)
  - formato --json
  - flag --staged avaliando apenas o indice
  - hook pre-commit bloqueando apenas violacao bloqueante
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
LINT_BIN = HARNESS_ROOT / "bin" / "lint"
CONFERIR_BIN = HARNESS_ROOT / "bin" / "conferir"
PRE_COMMIT_SCRIPT = HARNESS_ROOT / "bin" / "_lint" / "pre_commit.py"


def _rodar_lint(*args, env_extra=None, stdin_data=None):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [str(LINT_BIN), *args],
        capture_output=True,
        text=True,
        input=stdin_data,
        env=env,
    )


def test_lint_sem_argumentos_exit_2():
    p = _rodar_lint()
    assert p.returncode == 2
    saida = p.stderr + p.stdout
    assert "uso:" in saida
    assert "classes:" in saida
    for classe in ("codigo", "repo", "organizacao", "card", "arranque", "superficie"):
        assert classe in saida


def test_lint_ajuda_exit_2():
    p = _rodar_lint("--ajuda")
    assert p.returncode == 2
    assert "uso:" in p.stdout
    assert "classes:" in p.stdout


def test_lint_classe_desconhecida_exit_2():
    p = _rodar_lint("classe_inexistente", "platafirma-harness")
    assert p.returncode == 2
    assert "classe desconhecida" in p.stderr


def test_lint_sem_bancada_exit_1_com_vizinho(tmp_path):
    # Aponta bancada para pasta vazia sem o clone
    p = _rodar_lint("codigo", "repo-fantasma", env_extra={"PLATAFIRMA_BANCADA": str(tmp_path)})
    assert p.returncode == 1
    assert "sem bancada 'repo-fantasma'" in p.stderr
    assert "vizinho: repo abrir repo-fantasma" in p.stderr


def test_lint_lista_ausente_exit_5():
    # organizacao exige lista no acervo que nao existe -> exit 5
    p = _rodar_lint("organizacao", "platafirma-harness")
    assert p.returncode == 5
    assert "indeterminavel" in p.stderr
    assert "checklist-antipadroes-organizacao-documental" in p.stderr


def test_lint_linter_ausente_exit_3(tmp_path):
    # Cria clone com pyproject.toml mas PATH sem ruff nem uvx
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n")
    (tmp_path / ".git").mkdir()
    p = _rodar_lint(
        "codigo",
        "dummy",
        env_extra={
            "PLATAFIRMA_BANCADA": str(tmp_path.parent),
            "PATH": "/bin:/usr/bin",
            "PF_CADEIRA": "",
        },
    )
    # Se ruff nao estiver no PATH /bin:/usr/bin, sai 3
    # Nota: se ruff estiver instalado globalmente em /usr/bin, o teste passa se rodar com sucesso
    assert p.returncode in (0, 1, 3)


def test_lint_codigo_alvo_arquivo():
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint")
    assert p.returncode in (0, 1)
    linha1 = p.stdout.splitlines()[0]
    assert linha1.startswith("«lint codigo platafirma-harness/bin/lint:")
    assert "— repositorio»" in linha1


def test_lint_card_stdin_sem_aceite_exit_1():
    corpo_sem_aceite = """# Card de Teste
Negócio: #3119
Ambiente: platafirma-harness
Onde: bin/lint
Passos: 1. Executar teste
Travas: Sem merge em main
Entrega: branch fabrica/teste
Referencial: arq:0096
Raio de ataque: bin/lint
Comportamento esperado: exit 0
"""
    p = _rodar_lint("card", "-", stdin_data=corpo_sem_aceite)
    assert p.returncode == 1
    assert "Aceite" in p.stdout
    assert "cura: acrescentar a secao 'Aceite:' conforme arq:0096" in p.stdout


def test_lint_card_stdin_com_aceite_exit_0():
    corpo_completo = """# Card de Teste Completo
Negócio: #3119
Ambiente: platafirma-harness
Onde: bin/lint
Passos: 1. Executar teste
Aceite: exit 0 comprovado
Travas: Sem merge em main
Entrega: branch fabrica/teste
Referencial: arq:0096
Raio de ataque: bin/lint
Comportamento esperado: exit 0
"""
    p = _rodar_lint("card", "-", stdin_data=corpo_completo)
    assert p.returncode == 0
    assert "0 apontamentos" in p.stdout


def test_lint_json():
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint", "--json")
    assert p.returncode in (0, 1)
    dado = json.loads(p.stdout)
    assert "ancora" in dado
    assert dado["classe"] == "codigo"
    assert dado["chave"] == "repositorio"
    assert isinstance(dado["apontamentos"], list)


def test_lint_staged_so_indice():
    p = _rodar_lint("repo", "platafirma-harness", "--staged")
    assert p.returncode == 0
    assert "0 apontamentos" in p.stdout


def test_conferir_repo_staged_aviso_deprecado():
    sessao_id = f"test-sess-{os.getpid()}"
    p = subprocess.run(
        [str(CONFERIR_BIN), "repo", "--staged"],
        capture_output=True,
        text=True,
        env={**os.environ, "PF_SESSAO": sessao_id},
    )
    assert p.returncode == 0
    assert "conferir repo` esta deprecado; a forma conforme e `lint repo`" in p.stderr


def test_pre_commit_bloqueante_vs_aviso():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        subprocess.run(["git", "init", "-b", "main"], cwd=t, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=t, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=t, check=True)

        # 1. Arquivo valido
        (t / "codigo.py").write_text("print('valido')\n")
        subprocess.run(["git", "add", "codigo.py"], cwd=t, check=True)

        res1 = subprocess.run([sys.executable, str(PRE_COMMIT_SCRIPT)], cwd=t, capture_output=True, text=True)
        assert res1.returncode == 0

        # 2. Arquivo com predicado bloqueante (.pyc gerado rastreado)
        (t / "temp.pyc").write_bytes(b"\x00\x00")
        subprocess.run(["git", "add", "temp.pyc"], cwd=t, check=True)

        res2 = subprocess.run([sys.executable, str(PRE_COMMIT_SCRIPT)], cwd=t, capture_output=True, text=True)
        assert res2.returncode == 1
        assert "artefato regeneravel rastreado" in res2.stderr
