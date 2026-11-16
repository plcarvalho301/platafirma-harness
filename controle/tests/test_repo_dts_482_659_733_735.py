"""Cobertura dos DTs 482, 659, 733 e 735 em bin/repo."""

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


def _prepara_bancada(tmp_path: Path, nome: str = "demo", direto_main: bool = False):
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
        ramo = "engenharia/main"
    else:
        wt = bancada / "wt" / nome / "engenharia" / "dt-teste"
        ramo = "engenharia/dt-teste"
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(clone_base, "worktree", "add", "-q", "--track", "-b", ramo, str(wt), "origin/main")

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
        check=False,
    )


def test_dt_482_733_copiar_binario_e_svg_do_rascunho_para_bancada(tmp_path: Path):
    env, _, _, _, wt = _prepara_bancada(tmp_path)
    inst = Path(env["PLATAFIRMA_INSTANCIA"])
    ordem = "o20261116T120000-abc123"
    rascunho = inst / "var" / "tmp" / ordem
    rascunho.mkdir(parents=True)

    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\x00"
    (rascunho / "figura.png").write_bytes(png_bytes)
    (rascunho / "rota-t.svg").write_text("<svg><rect/></svg>\n", encoding="utf-8")

    # Caminho absoluto do rascunho para a bancada (binario)
    r1 = _roda(env, "copiar", "demo", str(rascunho / "figura.png"), "docs/fig/figura.png")
    assert r1.returncode == 0, r1.stderr
    assert (wt / "docs" / "fig" / "figura.png").read_bytes() == png_bytes
    assert "copiado:" in r1.stdout
    assert "repo commitar demo" in r1.stdout

    # Caminho relativo usando PF_ORDEM_ID
    env_ordem = {**env, "PF_ORDEM_ID": ordem}
    r2 = _roda(env_ordem, "copiar", "demo", "rota-t.svg", "instancias/figura/rota-t.svg")
    assert r2.returncode == 0, r2.stderr
    assert (wt / "instancias" / "figura" / "rota-t.svg").read_text(encoding="utf-8") == "<svg><rect/></svg>\n"


def test_dt_482_733_copiar_recusa_fora_do_rascunho_e_escapes(tmp_path: Path):
    env, _, _, _, wt = _prepara_bancada(tmp_path)
    fora = tmp_path / "segredo.png"
    fora.write_bytes(b"secret")

    r_fora = _roda(env, "copiar", "demo", str(fora), "docs/segredo.png")
    assert r_fora.returncode == 4, r_fora.stderr

    inst = Path(env["PLATAFIRMA_INSTANCIA"])
    rascunho = inst / "var" / "tmp" / "o1"
    rascunho.mkdir(parents=True)
    (rascunho / "ok.svg").write_text("<svg/>", encoding="utf-8")

    r_falta = _roda(env, "copiar", "demo", str(rascunho / "nao-existe.svg"), "docs/x.svg")
    assert r_falta.returncode == 1

    r_esc = _roda(env, "copiar", "demo", str(rascunho / "ok.svg"), "../fora.svg")
    assert r_esc.returncode == 4
    assert not (wt.parent / "fora.svg").exists()


def test_dt_735_mover_pasta_e_arquivo_entre_repositorios(tmp_path: Path):
    env, bancada, _, semente_orig, wt_dest = _prepara_bancada(tmp_path, nome="platafirma-ui")

    # Cria repositorio de origem com pasta de icones
    orig_bare = tmp_path / "platafirma-casa-espelho.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(orig_bare)], check=True)
    orig_sem = tmp_path / "semente-espelho"
    subprocess.run(["git", "clone", "-q", str(orig_bare), str(orig_sem)], check=True)
    (orig_sem / "outros_repos" / "ui" / "icones").mkdir(parents=True)
    (orig_sem / "outros_repos" / "ui" / "icones" / "a.svg").write_text("<svg>A</svg>\n", encoding="utf-8")
    (orig_sem / "outros_repos" / "ui" / "icones" / "sub" / "b.svg").parent.mkdir()
    (orig_sem / "outros_repos" / "ui" / "icones" / "sub" / "b.svg").write_text("<svg>B</svg>\n", encoding="utf-8")
    _git(orig_sem, "add", ".")
    _git(orig_sem, "commit", "-q", "-m", "icones")
    _git(orig_sem, "push", "-q", "-u", "origin", "main")
    sha = _git(orig_sem, "rev-parse", "HEAD").stdout.strip()

    # Clona origem na bancada para que url/local resolva sem rede
    subprocess.run(["git", "clone", "-q", str(orig_bare), str(bancada / "platafirma-casa-espelho")], check=True)

    r = _roda(env, "mover", f"platafirma-casa-espelho@{sha}:outros_repos/ui/icones", "platafirma-ui:icones")
    assert r.returncode == 0, r.stderr
    assert "movido:" in r.stdout
    assert "2 arquivo(s)" in r.stdout
    assert (wt_dest / "icones" / "a.svg").read_text(encoding="utf-8") == "<svg>A</svg>\n"
    assert (wt_dest / "icones" / "sub" / "b.svg").read_text(encoding="utf-8") == "<svg>B</svg>\n"
    st = _git(wt_dest, "status", "--porcelain").stdout
    assert "A  icones/a.svg" in st
    assert "A  icones/sub/b.svg" in st

    # Mover arquivo unico e erro em caminho inexistente
    r_blob = _roda(env, "mover", f"platafirma-casa-espelho@{sha}:outros_repos/ui/icones/a.svg", "platafirma-ui:unico.svg")
    assert r_blob.returncode == 0, r_blob.stderr
    assert (wt_dest / "unico.svg").read_text(encoding="utf-8") == "<svg>A</svg>\n"

    r_miss = _roda(env, "mover", f"platafirma-casa-espelho@{sha}:nao/existe", "platafirma-ui:x")
    assert r_miss.returncode == 1


def test_dt_659_portao_casa_materializa_em_pre_push_e_imprime_ato_ingestao(tmp_path: Path):
    env, _, _, _, wt = _prepara_bancada(tmp_path, nome="platafirma-casa", direto_main=True)
    doc = wt / "guia" / "expediente.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Expediente\n\nEspécie: guia\n", encoding="utf-8")
    _git(wt, "add", "guia/expediente.md")
    _git(wt, "commit", "-q", "-m", "doc")

    inst = Path(env["PLATAFIRMA_INSTANCIA"])
    pre_push_raiz = inst / "var" / "pre-push"
    captura = tmp_path / "arvore_vista.txt"

    falso_ingerir = tmp_path / "falso-casa-ingerir"
    falso_ingerir.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "idx = sys.argv.index('--arvore')\n"
        "arv = os.path.realpath(sys.argv[idx + 1])\n"
        f"raiz = os.path.realpath({json.dumps(str(pre_push_raiz))})\n"
        f"open({json.dumps(str(captura))}, 'w').write(arv)\n"
        "if not arv.startswith(raiz + os.sep):\n"
        "    sys.exit(4)\n"
        "assert os.path.isfile(os.path.join(arv, 'guia', 'expediente.md'))\n"
        "print(json.dumps({'lote': {'itens': []}}))\n",
        encoding="utf-8",
    )
    falso_ingerir.chmod(0o755)
    env["PF_CASA_INGERIR"] = str(falso_ingerir)

    r = _roda(env, "sincronizar", "platafirma-casa")
    assert r.returncode == 0, r.stderr
    assert "portão de ingestão indisponível" not in r.stderr
    assert captura.read_text().startswith(str(pre_push_raiz.resolve()) + os.sep)
    assert "próximo: acervo ingerir casa platafirma-casa@" in r.stdout
    assert "--apply" in r.stdout
