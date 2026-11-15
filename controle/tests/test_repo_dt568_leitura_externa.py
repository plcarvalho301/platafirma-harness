"""Cobertura do DT-568: leitura só-leitura de repositório fora da bancada (ex.: mdm_rh)."""

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"
IDENT = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(cwd: Path | None, *args: str) -> str:
    env = {**os.environ, **IDENT}
    cmd = ["git"]
    if cwd is not None:
        cmd.extend(["-C", str(cwd)])
    cmd.extend(args)
    return subprocess.run(cmd, env=env, capture_output=True, text=True, check=True).stdout.strip()


def _prepara_externo(tmp_path: Path, nome: str = "mdm_rh", ramo: str = "main"):
    origem = tmp_path / f"{nome}.git"
    _git(None, "init", "--bare", "-q", "-b", ramo, str(origem))

    semente = tmp_path / f"semente_{nome}"
    _git(None, "clone", "-q", str(origem), str(semente))
    _git(semente, "checkout", "-q", "-B", ramo)
    (semente / "docs").mkdir()
    (semente / "docs" / "ADR-005.md").write_text("# ADR-005\nDecisao externa.\n", encoding="utf-8")
    _git(semente, "add", ".")
    _git(semente, "commit", "-q", "-m", "doc: ADR-005")
    _git(semente, "push", "-q", "-u", "origin", ramo)

    bancada = tmp_path / "bancada"
    bancada.mkdir(exist_ok=True)
    release = tmp_path / "release"
    reg = release / "harness" / "registro" / "familias.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({nome: str(origem), "nao_existe": str(tmp_path / "inexistente.git")}), encoding="utf-8")

    env = {
        **os.environ,
        **IDENT,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_RELEASE": str(release),
        "PF_CADEIRA": "engenharia",
        "HOME": str(tmp_path),
    }
    return env, bancada, origem, semente


def _roda(env, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_dt568_leitura_externa_listar_ler_procurar_historico(tmp_path):
    env, bancada, _, semente = _prepara_externo(tmp_path, "mdm_rh", "main")

    # 1. listar
    r_ls = _roda(env, "listar", "mdm_rh")
    assert r_ls.returncode == 0, r_ls.stderr
    assert "docs/ADR-005.md" in r_ls.stdout
    assert "sem bancada (só leitura):" in r_ls.stderr

    # 2. procurar
    r_grep = _roda(env, "procurar", "mdm_rh", "ADR-005")
    assert r_grep.returncode == 0, r_grep.stderr
    assert "docs/ADR-005.md:1:# ADR-005" in r_grep.stdout

    # 3. ler
    r_ler = _roda(env, "ler", "mdm_rh", "docs/ADR-005.md")
    assert r_ler.returncode == 0, r_ler.stderr
    assert "Decisao externa." in r_ler.stdout

    # 4. historico
    r_hist = _roda(env, "historico", "mdm_rh", "--n", "5")
    assert r_hist.returncode == 0, r_hist.stderr
    assert "doc: ADR-005" in r_hist.stdout

    # 5. atualizacao no origin aparece na leitura seguinte (fetch)
    (semente / "docs" / "ADR-006.md").write_text("# ADR-006\nNovo.\n", encoding="utf-8")
    _git(semente, "add", "docs/ADR-006.md")
    _git(semente, "commit", "-q", "-m", "doc: ADR-006")
    _git(semente, "push", "-q", "origin", "main")

    r_ler2 = _roda(env, "ler", "mdm_rh", "docs/ADR-006.md")
    assert r_ler2.returncode == 0, r_ler2.stderr
    assert "Novo." in r_ler2.stdout

    # 6. repo estado nao lista cache .leitura como clone de bancada
    r_est = _roda(env, "estado")
    assert r_est.returncode == 0, r_est.stderr
    assert "mdm_rh" not in r_est.stdout
    assert not (bancada / "mdm_rh").exists()


def test_dt568_escrita_segue_recusando_repo_fora_da_bancada(tmp_path):
    env, *_ = _prepara_externo(tmp_path, "mdm_rh", "main")

    for cmd in (
        ("commitar", "mdm_rh", "-m", "x", "docs/ADR-005.md"),
        ("ramo", "mdm_rh", "568"),
        ("atualizar", "mdm_rh"),
        ("sincronizar", "mdm_rh"),
    ):
        r = _roda(env, *cmd)
        assert r.returncode == 2, (cmd, r.stdout, r.stderr)
        assert "repositório desconhecido" in r.stderr


def test_dt568_repo_inexistente_no_forge_sai_2(tmp_path):
    env, *_ = _prepara_externo(tmp_path, "mdm_rh", "main")

    r = _roda(env, "ler", "nao_existe", "README.md")
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "repositório desconhecido" in r.stderr


def test_dt568_repo_externo_com_ramo_padrao_master(tmp_path):
    env, *_ = _prepara_externo(tmp_path, "legado_rh", "master")

    r = _roda(env, "procurar", "legado_rh", "Decisao externa")
    assert r.returncode == 0, r.stderr
    assert "docs/ADR-005.md:2:Decisao externa." in r.stdout
    assert "origin/master@" in r.stderr
