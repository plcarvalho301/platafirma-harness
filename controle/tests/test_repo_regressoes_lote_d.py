# componente: componente:verbo-repo
"""Cobertura dos DTs 744 e 747 em bin/repo."""

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"
IDENT = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **IDENT},
    )


def _prepara_repo(tmp_path: Path, nome: str = "demo", direto_main: bool = False):
    origem = tmp_path / f"{nome}.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origem)], check=True)

    semente = tmp_path / f"semente-{nome}"
    subprocess.run(["git", "clone", "-q", str(origem), str(semente)], check=True)
    (semente / "LEIA.md").write_text("x\n", encoding="utf-8")
    _git(semente, "add", ".")
    _git(semente, "commit", "-q", "-m", "init")
    _git(semente, "push", "-q", "-u", "origin", "main")

    bancada = tmp_path / "bancada"
    bancada.mkdir(exist_ok=True)
    clone_base = bancada / nome
    subprocess.run(["git", "clone", "-q", str(origem), str(clone_base)], check=True)

    if direto_main:
        wt = bancada / "wt" / nome / "engenharia" / "main"
        wt.parent.mkdir(parents=True, exist_ok=True)
        _git(clone_base, "worktree", "add", "-q", "--track", "-b", "engenharia/main", str(wt), "origin/main")
    else:
        wt = bancada / "wt" / nome / "engenharia" / "3535-dt-277"
        wt.parent.mkdir(parents=True, exist_ok=True)
        _git(clone_base, "worktree", "add", "-q", "--no-track", "-b", "fabrica/3535-dt-277", str(wt), "origin/main")

    env = os.environ.copy()
    env.update(IDENT)
    env["PLATAFIRMA_BANCADA"] = str(bancada)
    env["PF_CADEIRA"] = "engenharia"
    env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "instancia")
    env["PF_RELEASE_RAIZ"] = str(tmp_path / "release")
    return env, bancada, origem, semente, wt


def _roda(env, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_dt744_aviso_atras_origin_ramo_sem_upstream_sugere_sincronizar(tmp_path: Path):
    env, _, _, semente, wt = _prepara_repo(tmp_path, nome="demo", direto_main=False)

    (semente / "novo.txt").write_text("1\n", encoding="utf-8")
    _git(semente, "add", "novo.txt")
    _git(semente, "commit", "-q", "-m", "main avanca")
    _git(semente, "push", "-q", "origin", "main")
    _git(wt, "fetch", "-q", "origin")

    r_listar = _roda(env, "listar", "demo")
    assert r_listar.returncode == 0, r_listar.stderr
    assert "aviso: bancada atrás de origin/main por 1 commit(s) — rode 'repo sincronizar demo'" in r_listar.stderr
    assert "repo atualizar demo" not in r_listar.stderr

    r_at = _roda(env, "atualizar", "demo")
    assert r_at.returncode == 3
    assert "repo sincronizar demo" in r_at.stderr

    r_sinc = _roda(env, "sincronizar", "demo")
    assert r_sinc.returncode == 0, r_sinc.stderr
    assert (wt / "novo.txt").read_text(encoding="utf-8") == "1\n"


def test_dt744_aviso_atras_origin_direto_em_main_mantem_atualizar_ou_sincronizar(tmp_path: Path):
    env, _, _, semente, wt = _prepara_repo(tmp_path, nome="platafirma-casa", direto_main=True)

    (semente / "doc.md").write_text("# Doc\n", encoding="utf-8")
    _git(semente, "add", "doc.md")
    _git(semente, "commit", "-q", "-m", "doc novo")
    _git(semente, "push", "-q", "origin", "main")
    _git(wt, "fetch", "-q", "origin")

    r_listar = _roda(env, "listar", "platafirma-casa")
    assert r_listar.returncode == 0, r_listar.stderr
    assert "rode 'repo atualizar platafirma-casa' ou 'repo sincronizar platafirma-casa'" in r_listar.stderr


def test_dt747_portao_admissao_casa_suporta_centenas_de_arquivos_e_plano_grande(tmp_path: Path):
    env, _, origem, semente, wt = _prepara_repo(tmp_path, nome="platafirma-casa", direto_main=True)

    # Cria 190 arquivos em adr/ e sincroniza na origem
    adr_dir = semente / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    for i in range(190):
        (adr_dir / f"{i:04d}-decisao-longa-para-teste-de-argumentos.md").write_text(f"# {i}\n", encoding="utf-8")
    _git(semente, "add", ".")
    _git(semente, "commit", "-q", "-m", "190 adrs")
    _git(semente, "push", "-q", "origin", "main")
    _git(wt, "pull", "-q", "--ff-only", "origin", "main")

    # Apaga 187 arquivos e altera 1 arquivo na bancada (como no commit 760449c do DT 747)
    for i in range(187):
        _git(wt, "rm", "-q", f"adr/{i:04d}-decisao-longa-para-teste-de-argumentos.md")
    (wt / "adr" / "0189-decisao-longa-para-teste-de-argumentos.md").write_text("# 189 editado\n", encoding="utf-8")
    _git(wt, "add", "adr/0189-decisao-longa-para-teste-de-argumentos.md")
    _git(wt, "commit", "-q", "-m", "apaga 187 adrs")

    # Falso casa-ingerir que devolve > 200 KB de JSON (acima de MAX_ARG_STRLEN = 128 KB do Linux execve)
    falso_ingerir = tmp_path / "falso-casa-ingerir"
    falso_ingerir.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os\n"
        "reprovar = os.environ.get('TESTE_REPROVAR') == '1'\n"
        "itens = [\n"
        "    {\n"
        "        'arquivo': f'platafirma-casa@doc/item-{i:04d}.md',\n"
        "        'veredito': 'aprovado',\n"
        "        'detalhe': 'x' * 500,\n"
        "    }\n"
        "    for i in range(400)\n"
        "]\n"
        "if reprovar:\n"
        "    itens.append({\n"
        "        'arquivo': 'platafirma-casa@adr/0189-decisao-longa-para-teste-de-argumentos.md',\n"
        "        'veredito': 'reprovado',\n"
        "        'portoes': [{'portao': 'forma', 'resultado': 'reprovado', 'detail': 'cabecalho invalido'}],\n"
        "    })\n"
        "print(json.dumps({'lote': {'itens': itens}}))\n",
        encoding="utf-8",
    )
    falso_ingerir.chmod(0o755)
    env["PF_CASA_INGERIR"] = str(falso_ingerir)

    # 1. Quando o portao reprova com JSON > 200 KB, recusa com exit 4 (antes estourava Argument list too long e empurrava!)
    env_reprova = {**env, "TESTE_REPROVAR": "1"}
    r_rep = _roda(env_reprova, "sincronizar", "platafirma-casa")
    assert r_rep.returncode == 4, r_rep.stdout + r_rep.stderr
    assert "Argument list too long" not in r_rep.stderr
    assert "0189-decisao-longa-para-teste-de-argumentos.md: forma: cabecalho invalido" in r_rep.stderr

    # 2. Quando o portao aprova com JSON > 200 KB, sincroniza sem Argument list too long
    r_ok = _roda(env, "sincronizar", "platafirma-casa")
    assert r_ok.returncode == 0, r_ok.stderr
    assert "Argument list too long" not in r_ok.stderr
    assert "sincronizado: main" in r_ok.stdout
    head_wt = _git(wt, "rev-parse", "HEAD").stdout.strip()
    head_orig = subprocess.run(
        ["git", "--git-dir", str(origem), "rev-parse", "main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head_wt == head_orig
