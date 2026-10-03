"""Contrato de `repo pr-merge` e do saneamento de ramos ja mesclados (card #3108).

Git real contra bare local; o forge do PR e um `gh` de fixture (PF_GH_BIN) que guarda o
estado do PR em arquivos, no mesmo estilo de test_contrato_repo_pr_fechar.py. Prova:
pr-merge (fresco e "ja feito") apaga o ramo do PR no origin e DECLARA o resultado na
mesma chamada -- o defeito medido era o apagar silencioso, sem linha nenhuma; `repo
sanear` alcanca o ramo ja mesclado que o pr-merge de antes desta emenda deixou no origin
sem bancada nenhuma, em --relatar e em --apply; ramo que recebeu commit por cima do que
foi mesclado (arvore diferente) fica, nunca se apaga; wip/* nunca entra na varredura.
Nao prova: o GitHub de verdade (squash real, refs/pull/<n>/head).
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

# Fixture minima: nao roda merge de verdade, so guarda/serve o estado que o teste grava
# nos arquivos ao lado (estado, ramo, oid, mergeoid, merged-list). "pr merge" marca MERGED
# e, sem mergeoid pre-gravado pelo teste, usa a propria ponta (caso limpo: arvore = arvore).
GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
case "$1 $2" in
  "pr view")
    case "$*" in
      *"--json state,headRefName,headRefOid,mergeCommit"*)
        echo "$(cat "$d/estado") $(cat "$d/ramo") $(cat "$d/mergeoid" 2>/dev/null || echo -) $(cat "$d/oid")" ;;
      *"--json state,mergeCommit"*)
        echo "$(cat "$d/estado") $(cat "$d/mergeoid" 2>/dev/null || echo -)" ;;
      *"--json statusCheckRollup"*)
        if [ -f "$d/checks" ]; then cat "$d/checks"; else echo '{"statusCheckRollup":[]}'; fi ;;
      *) cat "$d/estado" ;;
    esac ;;
  "pr merge")
    echo MERGED > "$d/estado"
    [ -s "$d/mergeoid" ] || cat "$d/oid" > "$d/mergeoid"
    exit 0 ;;
  "pr list")
    case "$*" in
      *"--state merged"*) [ -f "$d/merged-list" ] && cat "$d/merged-list" ;;
      *"--state open"*)   [ -f "$d/open-list" ] && cat "$d/open-list" ;;
      *) : ;;
    esac ;;
  *) exit 9 ;;
esac
"""


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _montar(tmp_path):
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
    gh.write_text(GH_FIXTURE)
    gh.chmod(0o755)
    return bancada, forge


def _repo(tmp_path, bancada, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _pr_empurrado(tmp_path, bancada, forge, estado="OPEN"):
    """Bancada do card 42 com um commit empurrado; o PR #7 do forge aponta para a ponta."""
    r = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt / "CARD.md").write_text("trabalho\n")
    _git("add", "CARD.md", cwd=wt)
    _git("commit", "-m", "card: CARD.md", cwd=wt)
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stderr
    (forge / "estado").write_text(estado + "\n")
    (forge / "ramo").write_text("fabrica/42-x\n")
    (forge / "oid").write_text(_git("rev-parse", "HEAD", cwd=wt) + "\n")
    return wt


def _no_origin(tmp_path, ramo):
    r = subprocess.run(["git", "--git-dir", str(tmp_path / "origem.git"), "rev-parse", "--verify", "-q",
                        f"refs/heads/{ramo}"], capture_output=True, text=True)
    return r.returncode == 0


# --- pr-merge apaga o remoto E declara (card #3108) -------------------------------------

def test_pr_merge_fresco_apaga_o_remoto_e_declara(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    assert _no_origin(tmp_path, "fabrica/42-x")
    r = _repo(tmp_path, bancada, "pr-merge", "demo", "7", "--forcar")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGED" in r.stdout
    assert "origin/fabrica/42-x: apagado" in r.stdout
    assert not _no_origin(tmp_path, "fabrica/42-x")


def test_pr_merge_ja_feito_tambem_apaga_e_declara(tmp_path):
    """O ramo sobreviveu de uma corrida anterior (merge feito, delete nao rodou ou nao foi
    lido) -- o retorno idempotente tambem tenta e declara, nao so no caminho fresco."""
    bancada, forge = _montar(tmp_path)
    wt = _pr_empurrado(tmp_path, bancada, forge, estado="MERGED")
    (forge / "mergeoid").write_text((forge / "oid").read_text())
    _git("push", "-u", "origin", "fabrica/42-x", cwd=wt)
    assert _no_origin(tmp_path, "fabrica/42-x")
    r = _repo(tmp_path, bancada, "pr-merge", "demo", "7", "--forcar")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "já feito: PR #7 MERGED" in r.stdout
    assert "origin/fabrica/42-x: apagado" in r.stdout
    assert not _no_origin(tmp_path, "fabrica/42-x")


# --- sanear alcanca o que o pr-merge de antes desta emenda deixou (card #3108) -----------

def test_sanear_apaga_ramo_ja_mesclado_sem_bancada_nenhuma(tmp_path):
    bancada, forge = _montar(tmp_path)
    outra = tmp_path / "outra"
    _git("clone", str(tmp_path / "origem.git"), str(outra))
    _git("checkout", "-b", "fabrica/9-velho", cwd=outra)
    (outra / "velho.md").write_text("v\n")
    _git("add", "velho.md", cwd=outra)
    _git("commit", "-m", "card: velho", cwd=outra)
    ponta = _git("rev-parse", "HEAD", cwd=outra)
    _git("push", "-u", "origin", "fabrica/9-velho", cwd=outra)
    (forge / "merged-list").write_text(f"fabrica/9-velho {ponta}\n")

    r = _repo(tmp_path, bancada, "sanear", "--relatar")
    assert r.returncode == 1, r.stdout
    assert "relataria apagar (mesclado" in r.stdout
    assert _no_origin(tmp_path, "fabrica/9-velho")

    r = _repo(tmp_path, bancada, "sanear")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "apagado (mesclado" in r.stdout
    assert not _no_origin(tmp_path, "fabrica/9-velho")


def test_sanear_nao_apaga_ramo_com_commit_por_cima_do_mesclado(tmp_path):
    """Trava do card: arvore da ponta atual != arvore do que o PR mesclou -- fica."""
    bancada, forge = _montar(tmp_path)
    outra = tmp_path / "outra"
    _git("clone", str(tmp_path / "origem.git"), str(outra))
    _git("checkout", "-b", "fabrica/9-velho", cwd=outra)
    (outra / "velho.md").write_text("v\n")
    _git("add", "velho.md", cwd=outra)
    _git("commit", "-m", "card: velho", cwd=outra)
    merge_oid = _git("rev-parse", "HEAD", cwd=outra)
    _git("push", "-u", "origin", "fabrica/9-velho", cwd=outra)
    # depois do "merge", alguem empurrou mais um commit no mesmo ramo
    (outra / "mais.md").write_text("depois\n")
    _git("add", "mais.md", cwd=outra)
    _git("commit", "-m", "card: mais", cwd=outra)
    _git("push", "origin", "fabrica/9-velho", cwd=outra)
    (forge / "merged-list").write_text(f"fabrica/9-velho {merge_oid}\n")

    r = _repo(tmp_path, bancada, "sanear")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fabrica/9-velho" not in r.stdout
    assert _no_origin(tmp_path, "fabrica/9-velho")


def test_sanear_nunca_apaga_wip_mesmo_se_a_gh_listasse_como_mesclado(tmp_path):
    bancada, forge = _montar(tmp_path)
    outra = tmp_path / "outra"
    _git("clone", str(tmp_path / "origem.git"), str(outra))
    _git("checkout", "-b", "wip/ti/algo", cwd=outra)
    (outra / "sujo.md").write_text("s\n")
    _git("add", "sujo.md", cwd=outra)
    _git("commit", "-m", "wip", cwd=outra)
    ponta = _git("rev-parse", "HEAD", cwd=outra)
    _git("push", "-u", "origin", "wip/ti/algo", cwd=outra)
    (forge / "merged-list").write_text(f"wip/ti/algo {ponta}\n")

    r = _repo(tmp_path, bancada, "sanear")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "wip/ti/algo" not in r.stdout
    assert _no_origin(tmp_path, "wip/ti/algo")

# --- check vermelho: a recusa nomeia o check (#2856, PR 424 do harness) ------------------

def test_pr_merge_check_vermelho_recusa_e_nomeia_o_check(tmp_path):
    """Antes a recusa dizia so «check vermelho» e quem merge nao tinha como saber qual."""
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    (forge / "checks").write_text(
        '{"statusCheckRollup":[{"conclusion":"SUCCESS","name":"verde"},'
        '{"conclusion":"FAILURE","detailsUrl":"https://ci.exemplo/run/1","name":"controle — testes"}]}\n')
    r = _repo(tmp_path, bancada, "pr-merge", "demo", "7")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "check vermelho no PR #7" in r.stderr
    assert "controle — testes https://ci.exemplo/run/1" in r.stderr
    assert "verde" not in r.stderr
    assert _no_origin(tmp_path, "fabrica/42-x")

def test_pr_merge_check_vermelho_com_forcar_mescla(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    (forge / "checks").write_text(
        '{"statusCheckRollup":[{"conclusion":"FAILURE","name":"controle — testes"}]}\n')
    r = _repo(tmp_path, bancada, "pr-merge", "demo", "7", "--forcar")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGED" in r.stdout
