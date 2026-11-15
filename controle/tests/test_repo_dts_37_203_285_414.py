from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_REPO = REPO_ROOT / "bin" / "repo"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )


def _setup_repo(tmp_path: Path, nome: str = "demo", cadeira: str = "ti", chave: str = "42-x") -> tuple[Path, Path, Path]:
    bancada = tmp_path / "bancada"
    bancada.mkdir(parents=True, exist_ok=True)
    origin = tmp_path / f"{nome}-origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))

    seed = tmp_path / f"{nome}-seed"
    _git(tmp_path, "clone", str(origin), str(seed))
    (seed / "README.md").write_text("base\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "init")
    _git(seed, "push", "-u", "origin", "main")

    base = bancada / nome
    _git(tmp_path, "clone", str(origin), str(base))
    _git(base, "checkout", "--detach", "origin/main")

    wt = bancada / "wt" / nome / cadeira / chave
    wt.parent.mkdir(parents=True, exist_ok=True)
    ramo = f"{cadeira}/main" if chave == "main" else f"fabrica/{chave}"
    _git(base, "worktree", "add", "-b", ramo, str(wt), "origin/main")
    return bancada, origin, wt


def _run_repo(bancada: Path, *args: str, cadeira: str = "ti", extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": cadeira,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(BIN_REPO), *args],
        text=True,
        capture_output=True,
        env=env,
    )


def test_dt37_commitar_restaura_stage_quando_gate_diagrama_recusa(tmp_path: Path) -> None:
    """DT 37: quando a trava de diagrama recusa em `repo commitar`, o arquivo novo não fica staged (A)."""
    bancada, _, wt = _setup_repo(tmp_path)

    # Stub de `conferir` que recusa diagramas quebrados (exit 1) ou indisponíveis (exit 5)
    stub_conferir = tmp_path / "conferir-stub"
    stub_conferir.write_text(
        "#!/usr/bin/env bash\n"
        "exit \"${STUB_CONFERIR_RC:-1}\"\n",
        encoding="utf-8",
    )
    stub_conferir.chmod(0o755)

    # Também prepara um arquivo já staged previamente para garantir que o stage anterior é preservado
    (wt / "previo.txt").write_text("ja estava no stage\n", encoding="utf-8")
    _git(wt, "add", "previo.txt")

    # Cria diagrama novo não rastreado
    (wt / "fluxo.mmd").write_text("flowchart TD\n  A -->\n", encoding="utf-8")

    # Caso 1: caminhos nomeados e Kroki recusando (exit 1)
    r1 = _run_repo(
        bancada,
        "commitar",
        "demo@42-x",
        "-m",
        "tenta commitar diagrama quebrado",
        "fluxo.mmd",
        extra_env={"PF_CONFERIR_BIN": str(stub_conferir), "STUB_CONFERIR_RC": "1"},
    )
    assert r1.returncode == 1, r1.stderr
    assert "diagrama fluxo.mmd quebrado" in r1.stderr

    porcelain1 = _git(wt, "status", "--porcelain").stdout.splitlines()
    assert "?? fluxo.mmd" in porcelain1, f"fluxo.mmd deveria voltar para untracked (??): {porcelain1}"
    assert "A  previo.txt" in porcelain1, f"stage prévio deveria ser preservado: {porcelain1}"

    # Caso 2: --tudo e Kroki indisponível (exit 5)
    r2 = _run_repo(
        bancada,
        "commitar",
        "demo@42-x",
        "-m",
        "tenta commitar tudo com kroki fora",
        "--tudo",
        extra_env={"PF_CONFERIR_BIN": str(stub_conferir), "STUB_CONFERIR_RC": "5"},
    )
    assert r2.returncode == 5, r2.stderr
    assert "nao medido" in r2.stderr

    porcelain2 = _git(wt, "status", "--porcelain").stdout.splitlines()
    assert "?? fluxo.mmd" in porcelain2, f"fluxo.mmd deveria continuar untracked (??) após --tudo falhar: {porcelain2}"
    assert "A  previo.txt" in porcelain2, f"stage prévio deveria ser preservado após --tudo falhar: {porcelain2}"


def test_dt203_estado_inclui_caminho_absoluto_da_bancada(tmp_path: Path) -> None:
    """DT 203: `repo estado` devolve o caminho absoluto da bancada no texto e no --json."""
    bancada, _, wt = _setup_repo(tmp_path)
    wt_abs = str(wt.resolve())

    # Com <repo> em texto
    r_txt = _run_repo(bancada, "estado", "demo")
    assert r_txt.returncode == 0, r_txt.stderr
    assert f"bancada {wt_abs}" in r_txt.stdout

    # Com <repo> em --json
    r_json = _run_repo(bancada, "estado", "demo", "--json")
    assert r_json.returncode == 0, r_json.stderr
    dados = json.loads(r_json.stdout)
    assert dados["bancada"] == wt_abs

    # Sem <repo> em texto
    r_all_txt = _run_repo(bancada, "estado")
    assert r_all_txt.returncode == 0, r_all_txt.stderr
    assert wt_abs in r_all_txt.stdout

    # Sem <repo> em --json
    r_all_json = _run_repo(bancada, "estado", "--json")
    assert r_all_json.returncode == 0, r_all_json.stderr
    dados_all = json.loads(r_all_json.stdout)
    assert dados_all["bancadas"]["demo"]["bancada"] == wt_abs


def test_dt285_descartar_remove_bancada_limpa_e_recusa_suja_ou_com_commit(tmp_path: Path) -> None:
    """DT 285: `repo descartar <repo>@<chave>` remove worktree e ramo local quando limpa; recusa suja/ahead sem --forcar."""
    bancada, _, wt = _setup_repo(tmp_path, nome="demo", cadeira="ti", chave="101-limpa")
    base = bancada / "demo"

    # 1. Bancada limpa e sem commits exclusivos -> remove worktree e ramo local
    r_ok = _run_repo(bancada, "descartar", "demo@101-limpa")
    assert r_ok.returncode == 0, r_ok.stderr
    assert "descartada:" in r_ok.stdout
    assert not wt.exists()
    ramos = _git(base, "branch", "--list", "fabrica/101-limpa").stdout.strip()
    assert ramos == ""

    # 2. Cria nova bancada e suja a árvore -> recusa sem --forcar (exit 4)
    wt2 = bancada / "wt" / "demo" / "ti" / "102-suja"
    _git(base, "worktree", "add", "-b", "fabrica/102-suja", str(wt2), "origin/main")
    (wt2 / "rascunho.txt").write_text("sujo\n", encoding="utf-8")

    r_suja = _run_repo(bancada, "descartar", "demo@102-suja")
    assert r_suja.returncode == 4
    assert "árvore suja" in r_suja.stderr
    assert "--forcar" in r_suja.stderr
    assert wt2.exists()

    # 3. Cria commit exclusivo na bancada (árvore limpa, mas commit não mesclado) -> recusa sem --forcar (exit 4)
    _git(wt2, "add", "rascunho.txt")
    _git(wt2, "commit", "-m", "commit local nao mesclado")
    r_ahead = _run_repo(bancada, "descartar", "demo@102-suja")
    assert r_ahead.returncode == 4
    assert "commits exclusivos" in r_ahead.stderr
    assert wt2.exists()

    # 4. Com --forcar -> descarta mesmo com commit exclusivo e apaga o ramo local
    r_forcar = _run_repo(bancada, "descartar", "demo@102-suja", "--forcar")
    assert r_forcar.returncode == 0, r_forcar.stderr
    assert not wt2.exists()
    assert _git(base, "branch", "--list", "fabrica/102-suja").stdout.strip() == ""


def test_dt414_dt530_abrir_direto_em_main_recoloca_ramo_antigo_ancestral(tmp_path: Path) -> None:
    """DT 414 e DT 530: em platafirma-casa e platafirma-casa-espelho, `repo abrir` recoloca worktree de main presa em ramo antigo ancestral de origin/main."""
    for repo_nome in ("platafirma-casa", "platafirma-casa-espelho"):
        bancada, origin, wt = _setup_repo(tmp_path / repo_nome, nome=repo_nome, cadeira="ti", chave="main")

        # Cria um ramo antigo cujo HEAD já está contido em origin/main e deixa a worktree presa nele
        _git(wt, "checkout", "-b", "fabrica/4183-antigo")

        # Avança origin/main para que fabrica/4183-antigo seja ancestral estrito de origin/main
        seed = tmp_path / repo_nome / f"{repo_nome}-seed"
        (seed / "novo.md").write_text("avanco em main\n", encoding="utf-8")
        _git(seed, "add", "novo.md")
        _git(seed, "commit", "-m", "avanca main")
        _git(seed, "push", "origin", "main")

        # 1. Árvore limpa e HEAD ancestral de origin/main -> repo abrir recoloca em ti/main automaticamente
        r_abrir = _run_repo(bancada, "abrir", repo_nome, cadeira="ti")
        assert r_abrir.returncode == 0, r_abrir.stderr
        assert "recolocada:" in r_abrir.stdout
        assert _git(wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "ti/main"
        assert _git(wt, "rev-parse", "HEAD").stdout.strip() == _git(wt, "rev-parse", "origin/main").stdout.strip()

        # 2. Se estiver em ramo antigo com commit exclusivo fora de origin/main -> recusa (exit 4) indicando comando de checkout
        _git(wt, "checkout", "-b", "ia/ramo-com-commit-exclusivo")
        (wt / "exclusivo.md").write_text("nao mesclado\n", encoding="utf-8")
        _git(wt, "add", "exclusivo.md")
        _git(wt, "commit", "-m", "exclusivo")

        r_recusa = _run_repo(bancada, "abrir", repo_nome, cadeira="ti")
        assert r_recusa.returncode == 4
        assert f"repo git {repo_nome} checkout -B ti/main origin/main" in r_recusa.stderr


def test_invariantes_estaticos_bin_repo() -> None:
    """Garante que bin/repo declara descartar no cabeçalho e não contém chamadas git/gh nuas."""
    import re

    linhas = BIN_REPO.read_text(encoding="utf-8").splitlines()
    cabecalho = "\n".join(linhas[:65])
    assert "descartar (escrita, operacao)" in cabecalho
    assert "# le: descartar=repo" in cabecalho
    assert "# escreve: descartar=repo" in cabecalho
    assert "# poda: cosmetica@git" in cabecalho

    padrao_git_nu = re.compile(r"([$(]|^\s*)git\s")
    padrao_gh_nu = re.compile(r"([$(]|^\s*)gh\s")
    for idx, linha in enumerate(linhas, start=1):
        if "#" in linha or "GIT=" in linha or "GH=" in linha:
            continue
        assert not padrao_git_nu.search(linha), f"git nu na linha {idx}: {linha}"
        assert not padrao_gh_nu.search(linha), f"gh nu na linha {idx}: {linha}"
