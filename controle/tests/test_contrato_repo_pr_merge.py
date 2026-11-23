# componente: componente:verbo-repo
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
    if [ -f "$d/merge-fail" ]; then
      n="$(cat "$d/merge-fail")"
      if [ "$n" -gt 0 ] 2>/dev/null; then
        echo $((n - 1)) > "$d/merge-fail"
        echo "EOF" >&2
        exit 1
      fi
    fi
    echo MERGED > "$d/estado"
    [ -s "$d/mergeoid" ] || cat "$d/oid" > "$d/mergeoid"
    exit 0 ;;
  "api -X")
    if [ -f "$d/api-merge-ok" ]; then
      echo MERGED > "$d/estado"
      [ -s "$d/mergeoid" ] || cat "$d/oid" > "$d/mergeoid"
      exit 0
    fi
    echo "EOF" >&2
    exit 1 ;;
  "run view")
    cat "$d/runlog" 2>/dev/null ;;
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
        "PF_GH_RETRY_SLEEP": "0",
        "PF_ESTEIRA_VEREDITOS_DIR": str(tmp_path / "vereditos"),
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _semear_veredito_verde(tmp_path, wt, repo="demo"):
    import json
    vdir = tmp_path / "vereditos"
    vdir.mkdir(parents=True, exist_ok=True)
    arv_mud = _git("rev-parse", "HEAD^{tree}", cwd=wt)
    arv_main = _git("rev-parse", "origin/main^{tree}", cwd=wt)
    reg = {"repositorio": repo, "arvore_mudanca": arv_mud, "arvore_main": arv_main, "estado": "verde", "fichas": []}
    (vdir / f"{repo}.jsonl").write_text(json.dumps(reg) + "\n", encoding="utf-8")


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
    _semear_veredito_verde(tmp_path, wt)
    return wt


def _no_origin(tmp_path, ramo):
    r = subprocess.run(["git", "--git-dir", str(tmp_path / "origem.git"), "rev-parse", "--verify", "-q",
                        f"refs/heads/{ramo}"], capture_output=True, text=True)
    return r.returncode == 0


# --- pr-merge recusa no regime sem PR (22/11/2026, DT 1366) -------------------------------

def test_pr_merge_recusa_no_regime_sem_pr_e_aponta_sincronizar(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    assert _no_origin(tmp_path, "fabrica/42-x")
    r = _repo(tmp_path, bancada, "pr-merge", "demo", "7", "--forcar")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "regime sem pedido de integração" in r.stderr
    assert "repo sincronizar demo" in r.stderr
    assert _no_origin(tmp_path, "fabrica/42-x")


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

# --- pr-ver --checks / --log: ler QUAL check barra, pelo verbo (#2856) -------------------

_ROLLUP = ('{"statusCheckRollup":[{"conclusion":"SUCCESS","name":"lint","workflowName":"estilo",'
           '"detailsUrl":"https://forge.exemplo/runs/11/job/1"},'
           '{"conclusion":"FAILURE","name":"pytest","workflowName":"controle — testes",'
           '"detailsUrl":"https://forge.exemplo/actions/runs/55/job/9"}]}\n')

def test_pr_ver_checks_lista_resultado_workflow_e_link(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    (forge / "checks").write_text(_ROLLUP)
    r = _repo(tmp_path, bancada, "pr-ver", "demo", "7", "--checks")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SUCCESS" in r.stdout and "estilo / lint" in r.stdout
    assert "FAILURE" in r.stdout and "controle — testes / pytest https://forge.exemplo/actions/runs/55/job/9" in r.stdout
    assert "log do run" not in r.stdout

def test_pr_ver_log_traz_o_fim_do_log_so_do_run_que_falhou(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    (forge / "checks").write_text(_ROLLUP)
    (forge / "runlog").write_text("pytest\tModuleNotFoundError: No module named 'requests'\n")
    r = _repo(tmp_path, bancada, "pr-ver", "demo", "7", "--log")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "== log do run 55 (fim) ==" in r.stdout and "== log do run 11" not in r.stdout
    assert "No module named 'requests'" in r.stdout

def test_pr_ver_sem_flag_nao_lista_checks_e_flag_desconhecida_recusa(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    (forge / "checks").write_text(_ROLLUP)
    assert "checks:" not in _repo(tmp_path, bancada, "pr-ver", "demo", "7").stdout
    assert _repo(tmp_path, bancada, "pr-ver", "demo", "7", "--xis").returncode == 2



