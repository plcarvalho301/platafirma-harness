"""Contrato do verbo bin/teste conforme a spec (card #3152, passo 9).

Cobre:
1. usage (sem argumento) -> exit 2
2. ato desconhecido -> exit 2
3. nome desconhecido -> exit 2
4. nome duplicado stack=repo -> exit 2
5. sem bancada da cadeira -> exit 1 com varrido: e vizinho: repo abrir
6. sem lock declarado/existente -> exit 5
7. --arvore fora da raiz materializada -> exit 4
8. --portao roda apenas a lista de VERDES
9. --ajuda sem efeito colateral -> exit 2
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTE_BIN = Path(__file__).resolve().parents[2] / "bin" / "teste"
IDENT = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(*args, cwd=None):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={**os.environ, **IDENT},
    )


def _python():
    for p in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if p and os.access(p, os.X_OK):
            return p
    pytest.skip("sem python de sistema")


def _run_teste(env_extra: dict, *args: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),
        **env_extra,
    }
    return subprocess.run(
        [str(TESTE_BIN), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_usage_sem_argumento_sai_2(tmp_path):
    r = _run_teste({})
    assert r.returncode == 2, r.stdout + r.stderr
    assert "uso:" in (r.stdout + r.stderr)
    assert "teste rodar" in (r.stdout + r.stderr)


def test_ato_desconhecido_sai_2(tmp_path):
    r = _run_teste({}, "ato_invalido")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "ato desconhecido" in (r.stdout + r.stderr)
    assert "rodar, detectar, inventario" in (r.stdout + r.stderr)


def test_nome_desconhecido_sai_2(tmp_path):
    vjson = tmp_path / "venvs.json"
    vjson.write_text('{"repositorios": {"repo-a": {"esteira": "codigo"}}, "stack-a": {"familia": "repo-a", "lock": "lock.txt"}}\n')
    env = {"PLATAFIRMA_VENVS": str(vjson)}
    r = _run_teste(env, "rodar", "nao-existe")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "desconhecido" in (r.stdout + r.stderr)
    assert "stack-a" in (r.stdout + r.stderr)


def test_nome_duplicado_stack_e_repositorio_sai_2(tmp_path):
    vjson = tmp_path / "venvs.json"
    vjson.write_text('{"repositorios": {"colisao": {"esteira": "codigo"}}, "colisao": {"familia": "colisao", "lock": "lock.txt"}}\n')
    env = {"PLATAFIRMA_VENVS": str(vjson)}
    r = _run_teste(env, "rodar", "colisao")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "stack com nome igual a repositório" in (r.stdout + r.stderr)
    assert "'colisao'" in (r.stdout + r.stderr)


def test_sem_bancada_da_cadeira_sai_1_com_varrido_e_vizinho(tmp_path):
    vjson = tmp_path / "venvs.json"
    vjson.write_text('{"repositorios": {"demo-repo": {"esteira": "codigo"}}, "demo-stack": {"familia": "demo-repo", "lock": "lock.txt"}}\n')
    b = tmp_path / "bancada"
    b.mkdir()
    env = {
        "PLATAFIRMA_BANCADA": str(b),
        "PLATAFIRMA_VENVS": str(vjson),
        "PF_CADEIRA": "ti",
    }
    r = _run_teste(env, "rodar", "demo-repo")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "varrido:" in r.stderr
    assert "vizinho: repo abrir demo-repo" in r.stderr


def test_sem_lock_declarado_ou_existente_sai_5(tmp_path):
    vjson = tmp_path / "venvs.json"
    vjson.write_text('{"repositorios": {"demo": {"esteira": "codigo", "stack": "demo-stack"}}, "demo-stack": {"familia": "demo"}}\n')
    b = tmp_path / "bancada"
    base = b / "demo"
    base.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=base)
    (base / "arquivo.txt").write_text("ok\n")
    _git("add", "-A", cwd=base)
    _git("commit", "-q", "-m", "semente", cwd=base)
    wt = b / "wt" / "demo" / "ti" / "card-1"
    _git("worktree", "add", "-q", "-b", "fabrica/card-1", str(wt), cwd=base)

    env = {
        "PLATAFIRMA_BANCADA": str(b),
        "PLATAFIRMA_VENVS": str(vjson),
        "PF_CADEIRA": "ti",
        "PLATAFIRMA_PYTHON": _python(),
    }
    r = _run_teste(env, "rodar", "demo-stack")
    assert r.returncode == 5, r.stdout + r.stderr
    assert "lock" in r.stderr


def test_arvore_fora_da_raiz_materializada_sai_4(tmp_path):
    fora = tmp_path / "caminho_fora_teste"
    fora.mkdir(exist_ok=True)
    try:
        release_raiz = tmp_path / "release"
        release_raiz.mkdir()
        vjson = tmp_path / "venvs.json"
        vjson.write_text('{"repositorios": {"demo": {"esteira": "codigo"}}, "demo-stack": {"familia": "demo", "lock": "lock.txt"}}\n')
        env = {
            "PF_RELEASE_RAIZ": str(release_raiz),
            "TMPDIR": str(tmp_path / "custom_tmp"),
            "PLATAFIRMA_VENVS": str(vjson),
        }
        r = _run_teste(env, "rodar", "demo-stack", "--arvore", str(fora))
        assert r.returncode == 4, r.stdout + r.stderr
        assert "o caminho de --arvore só é aceito sob a raiz de árvores materializadas" in r.stderr
    finally:
        shutil.rmtree(fora, ignore_errors=True)


def test_portao_roda_apenas_a_lista_de_verdes(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv ausente")
    release_raiz = tmp_path / "release"
    arvore = release_raiz / "demo" / "rev1"
    arvore.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=arvore)

    (arvore / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0"\nrequires-python = ">=3.10"\ndependencies = []\n'
    )
    (arvore / "lock.txt").write_text("# fixture: venv vazio\n")
    (arvore / "controle" / "tests").mkdir(parents=True)
    (arvore / "controle" / "tests" / "test_verde.py").write_text("def test_v(): assert True\n")
    (arvore / "controle" / "tests" / "test_vermelho.py").write_text("def test_f(): assert False\n")
    (arvore / "controle" / "tests" / "VERDES").write_text("tests/test_verde.py\n")

    _git("add", "-A", cwd=arvore)
    _git("commit", "-q", "-m", "semente", cwd=arvore)

    vjson = tmp_path / "venvs.json"
    vjson.write_text(
        json.dumps({
            "repositorios": {"demo": {"esteira": "codigo", "stack": "demo-stack"}},
            "demo-stack": {"familia": "demo", "lock": "lock.txt", "teste": "controle"},
        })
    )

    env = {
        "PF_RELEASE_RAIZ": str(release_raiz),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PLATAFIRMA_VENVS": str(vjson),
        "PLATAFIRMA_PYTHON": _python(),
        "PF_TESTE_PYTHON": _python(),
    }
    r = _run_teste(env, "rodar", "demo-stack", "--portao", "--arvore", str(arvore))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "suite VERDE" in r.stdout
    assert "1 passed" in r.stdout
    assert "test_vermelho" not in r.stdout


def test_rodada_parcial_nao_grava_o_memo_do_portao(tmp_path):
    """Um arquivo verde nao e a arvore verde: o memo que pre-push e gate leem so recebe a
    rodada do portao inteiro. Antes, `teste rodar <stack> <um arquivo>` gravava verde ali,
    e o push seguinte da mesma arvore passava sem medir o resto (medido em 27/09: tres
    arquivos diferentes, um so rodou, os outros dois sairam "reaproveitado"). """
    if not shutil.which("uv"):
        pytest.skip("uv ausente")
    release_raiz = tmp_path / "release"
    arvore = release_raiz / "demo" / "rev1"
    arvore.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=arvore)
    (arvore / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0"\nrequires-python = ">=3.10"\ndependencies = []\n'
    )
    (arvore / "lock.txt").write_text("# fixture: venv vazio\n")
    (arvore / "controle" / "tests").mkdir(parents=True)
    (arvore / "controle" / "tests" / "test_verde.py").write_text("def test_v(): assert True\n")
    (arvore / "controle" / "tests" / "test_vermelho.py").write_text("def test_f(): assert False\n")
    (arvore / "controle" / "tests" / "VERDES").write_text("tests/test_verde.py\ntests/test_vermelho.py\n")
    _git("add", "-A", cwd=arvore)
    _git("commit", "-q", "-m", "semente", cwd=arvore)
    vjson = tmp_path / "venvs.json"
    vjson.write_text(json.dumps({
        "repositorios": {"demo": {"esteira": "codigo", "stack": "demo-stack"}},
        "demo-stack": {"familia": "demo", "lock": "lock.txt", "teste": "controle"},
    }))
    inst = tmp_path / "instancia"
    env = {
        "PF_RELEASE_RAIZ": str(release_raiz),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_VENVS": str(vjson),
        "PLATAFIRMA_PYTHON": _python(),
        "PF_TESTE_PYTHON": _python(),
    }
    r = _run_teste(env, "rodar", "demo-stack", "controle/tests/test_verde.py", "--arvore", str(arvore))
    assert r.returncode == 0, r.stdout + r.stderr
    memo_portao = inst / "var" / "pre-push" / "vereditos"
    assert not memo_portao.exists() or not any(memo_portao.rglob("*")), list(memo_portao.rglob("*"))

    r2 = _run_teste(env, "rodar", "demo-stack", "--portao", "--arvore", str(arvore))
    assert r2.returncode == 1, r2.stdout + r2.stderr
    assert "reaproveitado" not in r2.stdout


def test_ajuda_sai_2_sem_efeito_colateral(tmp_path):
    inst = tmp_path / "instancia"
    env = {
        "PLATAFIRMA_INSTANCIA": str(inst),
    }
    r1 = _run_teste(env, "--ajuda")
    assert r1.returncode == 2, r1.stdout + r1.stderr
    assert "uso:" in (r1.stdout + r1.stderr)
    assert "teste rodar" in (r1.stdout + r1.stderr)

    r2 = _run_teste(env, "rodar", "--ajuda")
    assert r2.returncode == 2, r2.stdout + r2.stderr
    assert "uso:" in (r2.stdout + r2.stderr)
    assert "teste rodar" in (r2.stdout + r2.stderr)

    assert not inst.exists()


# --- esteira documento (passo 6): teste chama a admissao da ingestao, nao a copia ------

def _documento(tmp_path, rc_stub: int):
    """Registro com repo de esteira documento, arvore sob a raiz de release e um
    `acervo` de stub que grava os argumentos e sai com rc_stub."""
    release_raiz = tmp_path / "release"
    arvore = release_raiz / "casa" / "rev1"
    (arvore / "guia").mkdir(parents=True)
    (arvore / "guia" / "x.md").write_text("# x\n")
    vjson = tmp_path / "venvs.json"
    vjson.write_text('{"repositorios": {"casa-demo": {"esteira": "documento"}}}\n')
    log = tmp_path / "acervo-args.txt"
    stub = tmp_path / "acervo"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" > "{log}"\n'
        'echo "portao chave: recusado em guia/x.md"\n'
        f"exit {rc_stub}\n"
    )
    stub.chmod(0o755)
    env = {
        "PF_RELEASE_RAIZ": str(release_raiz),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PLATAFIRMA_VENVS": str(vjson),
        "PF_ACERVO_BIN": str(stub),
    }
    return env, arvore, log


def test_documento_limpo_sai_0_chamando_a_admissao(tmp_path):
    env, arvore, log = _documento(tmp_path, 0)
    r = _run_teste(env, "rodar", "casa-demo", "--arvore", str(arvore))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "suite VERDE" in r.stdout
    assert log.read_text().split() == ["ingerir", "casa", "casa-demo", "--arvore", str(arvore)]


def test_documento_recusado_pela_admissao_sai_1_nomeando(tmp_path):
    env, arvore, _ = _documento(tmp_path, 3)
    r = _run_teste(env, "rodar", "casa-demo", "--arvore", str(arvore))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "suite VERMELHA" in r.stdout
    assert "reprovado: portao chave" in r.stdout


def test_documento_motor_fora_sai_5_nao_medido(tmp_path):
    env, arvore, _ = _documento(tmp_path, 1)
    r = _run_teste(env, "rodar", "casa-demo", "--arvore", str(arvore))
    assert r.returncode == 5, r.stdout + r.stderr
    assert "INDISPONIVEL" in r.stdout
