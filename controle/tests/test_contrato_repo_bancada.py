"""Contrato de `repo abrir` e da resolucao de bancada: worktree por CADEIRA (arq:0109 §2).

Defeito medido em 26/09/2026 (revisao do PR 22 de platafirma-casa): `repo abrir` criava
wt/<repo>/<sessao_id>; a sessao seguinte da mesma cadeira nao achava a bancada e caia no
clone compartilhado, com aviso so em stderr. Git real contra bare local, sem rede.

Prova: o worktree nasce em wt/<repo>/<cadeira>, e outra sessao da mesma cadeira resolve
a mesma bancada sem fallback. Nao prova: o forge (clone base ja existe; nao ha push).
"""
import os
import subprocess
import time
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


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
    return bancada


def _repo(tmp_path, bancada, sessao, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": sessao,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def test_abrir_cria_worktree_por_cadeira_e_card_nao_so_cadeira(tmp_path):
    """card:3149 passo 3: a pasta e wt/<repo>/<cadeira>/<card>-<slug>, nao so
    wt/<repo>/<cadeira> -- e o que deixa dois cards da mesma cadeira coexistirem."""
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sessao-1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert (bancada / "wt" / "demo" / "ti" / "42-x" / ".git").exists()
    assert not (bancada / "wt" / "demo" / "ti" / ".git").exists()
    assert not (bancada / "wt" / "demo" / "sessao-1").exists()


def test_outra_sessao_da_mesma_cadeira_acha_a_bancada_sem_fallback(tmp_path):
    bancada = _montar(tmp_path)
    assert _repo(tmp_path, bancada, "sessao-1", "abrir", "demo", "42", "--slug", "x").returncode == 0
    r = _repo(tmp_path, bancada, "sessao-2", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fallback" not in r.stderr
    assert "fabrica/42-x" in r.stdout


def test_worktree_legado_por_sessao_segue_legivel_ate_a_cadeira_ter_o_seu(tmp_path):
    bancada = _montar(tmp_path)
    _git("worktree", "add", "-b", "fabrica/7-legado",
         str(bancada / "wt" / "demo" / "sessao-velha"), "origin/main", cwd=bancada / "demo")
    r = _repo(tmp_path, bancada, "sessao-velha", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fabrica/7-legado" in r.stdout
    assert "fallback" not in r.stderr


def test_abrir_dois_cards_da_mesma_cadeira_nao_colidem(tmp_path):
    """card:3149 passo 3: o defeito medido ao vivo em 26/09 -- abrir um card enquanto
    outro da mesma cadeira estava aberto caiu na MESMA pasta (wt/<repo>/<cadeira>, sem
    card no caminho) e o segundo abrir so trocou o ramo debaixo do primeiro."""
    bancada = _montar(tmp_path)
    assert _repo(tmp_path, bancada, "s1", "abrir", "demo", "42", "--slug", "x").returncode == 0
    r42 = _repo(tmp_path, bancada, "s1", "estado", "demo")
    assert r42.returncode == 0, r42.stderr
    assert "fabrica/42-x" in r42.stdout

    assert _repo(tmp_path, bancada, "s2", "abrir", "demo", "43", "--slug", "y").returncode == 0
    assert (bancada / "wt" / "demo" / "ti" / "42-x" / ".git").exists()
    assert (bancada / "wt" / "demo" / "ti" / "43-y" / ".git").exists()

    # ambiguo agora (2 worktrees da mesma cadeira, sem chave para 'estado' escolher):
    # forca 42-x mais velho para o desempate por mtime ser deterministico no teste, nao
    # na ordem em que o relogio da maquina serviu as duas chamadas.
    velho = time.time() - 100
    os.utime(bancada / "wt" / "demo" / "ti" / "42-x" / ".git", (velho, velho))
    r43 = _repo(tmp_path, bancada, "s2", "estado", "demo")
    assert r43.returncode == 0, r43.stderr
    assert "fabrica/43-y" in r43.stdout


def test_ler_sem_bancada_aberta_da_vizinho_nao_desconhecido(tmp_path):
    """card:3149 passo 3: repo conhecido (clone base existe) mas sem worktree desta
    cadeira -- exit 1 com 'vizinho: repo abrir', nunca 'repositorio desconhecido' nem
    fallback silencioso para o cache (spec_ambiente-de-desenvolvimento §2)."""
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sessao-1", "ler", "demo", "LEIA.md")
    assert r.returncode == 1, r.stderr
    assert "vizinho: repo abrir" in r.stderr
    assert "desconhecido" not in r.stderr


def test_sanear_enxerga_worktree_sob_wt_e_remove_ramo_entregue(tmp_path):
    """card:3149 comentario #939 secao B4/B3: sanear tem de descer em wt/ (glob do topo
    nao desce) e reconhecer ramo entregue pela ausencia no origin, nunca por
    merge-base --is-ancestor (squash nao deixa ancestral)."""
    bancada = _montar(tmp_path)
    wt = bancada / "wt" / "demo" / "outra"
    _git("worktree", "add", "-b", "fabrica/99-x", str(wt), "origin/main", cwd=bancada / "demo")
    _git("push", "-u", "origin", "fabrica/99-x", cwd=wt)
    _git("push", "origin", "--delete", "fabrica/99-x", cwd=wt)
    r = _repo(tmp_path, bancada, "sessao-x", "sanear")
    assert r.returncode == 0, r.stderr
    assert not wt.exists()
    assert "removido" in r.stdout


def test_sanear_relatar_nao_apaga_e_nomeia_o_worktree_sob_wt(tmp_path):
    bancada = _montar(tmp_path)
    wt = bancada / "wt" / "demo" / "outra"
    _git("worktree", "add", "-b", "fabrica/98-x", str(wt), "origin/main", cwd=bancada / "demo")
    _git("push", "-u", "origin", "fabrica/98-x", cwd=wt)
    _git("push", "origin", "--delete", "fabrica/98-x", cwd=wt)
    r = _repo(tmp_path, bancada, "sessao-x", "sanear", "--relatar")
    assert r.returncode == 0, r.stderr
    assert wt.exists()
    assert "relataria worktree remove" in r.stdout


def test_sanear_wip_de_arvore_suja_nomeia_cadeira_e_nao_colide_por_minuto(tmp_path):
    """card:3149 comentario #939 secao B6: o nome do wip carrega cadeira, segundos e
    sha -- so o minuto (vigente) colide entre duas passadas no mesmo minuto."""
    bancada = _montar(tmp_path)
    (bancada / "demo" / "novo.txt").write_text("x\n")
    r = _repo(tmp_path, bancada, "sessao-x", "sanear")
    assert r.returncode == 0, r.stderr
    assert "salvo em wip -> origin/wip/ti/" in r.stdout
