"""Contrato da bancada do `repo`: abrir, achar, ficar em dia e fechar (card:3149;
spec_ambiente-de-desenvolvimento §2 §5; arq:0109 §2 §5).

Git real contra bare local, sem rede e sem gh. Prova: a pasta por cadeira E card; a
resolucao sem fallback ao cache e sem heuristica (ambiguo pede <repo>@<chave>); a migracao
da pasta plana legada; `sincronizar` nos cinco casos do card; o fecho idempotente de
`empurrar` e `commitar`; e o `sanear` que so remove o entregue ou o fora do eixo, salvando
antes em wip/ o que so existe na bancada. Nao prova: o forge de verdade (PR mesclado lido do
gh -- aqui so o ramo apagado do origin), nem `pr-*`, nem o pre-push (os clones de teste nao
tem hooksPath).
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


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
        "PF_TAREFAS_BIN": "/bin/true",
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _main_novo(tmp_path, arquivo="NOVO.md", texto="novo\n"):
    """Outra mao mescla em main: commit na semente, empurrado ao origin."""
    semente = tmp_path / "semente"
    _git("pull", "-q", "origin", "main", cwd=semente)
    (semente / arquivo).write_text(texto)
    _git("add", arquivo, cwd=semente)
    _git("commit", "-m", f"main: {arquivo}", cwd=semente)
    _git("push", "-q", "origin", "main", cwd=semente)


def _abrir_42(tmp_path, bancada):
    r = _repo(tmp_path, bancada, "s1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    return bancada / "wt" / "demo" / "ti" / "42-x"


def _commit_em(wt, arquivo, texto):
    (wt / arquivo).write_text(texto)
    _git("add", arquivo, cwd=wt)
    _git("commit", "-m", f"card: {arquivo}", cwd=wt)


# --- abrir e achar ------------------------------------------------------------------------

def test_abrir_cria_worktree_por_cadeira_e_card_e_move_o_card(tmp_path):
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sessao-1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert (bancada / "wt" / "demo" / "ti" / "42-x" / ".git").exists()
    assert not (bancada / "wt" / "demo" / "ti" / ".git").exists()
    assert "atras de origin/main: 0" in r.stdout and "arvore limpa" in r.stdout
    assert "card #42: em-execucao" in r.stdout


def test_abrir_de_novo_nao_move_nada_e_diz_o_atraso(tmp_path):
    bancada = _montar(tmp_path)
    _abrir_42(tmp_path, bancada)
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "s2", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert "bancada já aberta" in r.stdout
    assert "atras de origin/main: 1" in r.stdout
    assert "card #42" not in r.stdout


def test_abrir_sem_card_com_slug_abre_ramo_da_cadeira(tmp_path):
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "s1", "abrir", "demo", "--slug", "faxina")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "ti" / "faxina"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "ti/faxina"


def test_outra_sessao_da_mesma_cadeira_acha_a_bancada_sem_fallback(tmp_path):
    bancada = _montar(tmp_path)
    _abrir_42(tmp_path, bancada)
    r = _repo(tmp_path, bancada, "sessao-2", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fallback" not in r.stderr
    assert "fabrica/42-x" in r.stdout


def test_estado_diz_o_atraso_contra_origin_main_depois_de_buscar(tmp_path):
    bancada = _montar(tmp_path)
    _abrir_42(tmp_path, bancada)
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "s1", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "origin/main  ·  atras 1" in r.stdout


def test_worktree_legado_por_sessao_segue_legivel_ate_a_cadeira_ter_o_seu(tmp_path):
    bancada = _montar(tmp_path)
    _git("worktree", "add", "-b", "fabrica/7-legado",
         str(bancada / "wt" / "demo" / "sessao-velha"), "origin/main", cwd=bancada / "demo")
    r = _repo(tmp_path, bancada, "sessao-velha", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fabrica/7-legado" in r.stdout


def test_dois_cards_da_mesma_cadeira_nao_colidem_e_ambiguo_pede_a_chave(tmp_path):
    """O defeito medido em 26/09: dois cards da mesma cadeira na MESMA pasta. E o de antes
    desta revisao: sem chave, o desempate por mtime do .git escolhia pela hora do add."""
    bancada = _montar(tmp_path)
    _abrir_42(tmp_path, bancada)
    assert _repo(tmp_path, bancada, "s2", "abrir", "demo", "43", "--slug", "y").returncode == 0
    assert (bancada / "wt" / "demo" / "ti" / "42-x" / ".git").exists()
    assert (bancada / "wt" / "demo" / "ti" / "43-y" / ".git").exists()

    r = _repo(tmp_path, bancada, "s2", "estado", "demo")
    assert r.returncode == 2, r.stdout
    assert "demo@42-x" in r.stderr and "demo@43-y" in r.stderr

    r = _repo(tmp_path, bancada, "s2", "estado", "demo@42-x")
    assert r.returncode == 0, r.stderr
    assert "fabrica/42-x" in r.stdout


def test_ler_sem_bancada_aberta_da_vizinho_nao_desconhecido(tmp_path):
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sessao-1", "ler", "demo", "LEIA.md")
    assert r.returncode == 1, r.stderr
    assert "vizinho: repo abrir" in r.stderr
    assert "desconhecido" not in r.stderr


def test_abrir_migra_a_pasta_plana_legada_antes_de_aninhar(tmp_path):
    """wt/<repo>/<cadeira> que e ela propria worktree: a aninhada nasceria dentro dela."""
    bancada = _montar(tmp_path)
    plana = bancada / "wt" / "demo" / "ti"
    _git("worktree", "add", "-b", "fabrica/7-legado", str(plana), "origin/main", cwd=bancada / "demo")
    r = _repo(tmp_path, bancada, "s1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert "migrada" in r.stdout
    assert not (plana / ".git").exists()
    assert (plana / "7-legado" / ".git").exists()
    assert (plana / "42-x" / ".git").exists()


def test_abrir_recusa_aninhar_em_plana_suja(tmp_path):
    bancada = _montar(tmp_path)
    plana = bancada / "wt" / "demo" / "ti"
    _git("worktree", "add", "-b", "fabrica/7-legado", str(plana), "origin/main", cwd=bancada / "demo")
    (plana / "meio.txt").write_text("trabalho\n")
    r = _repo(tmp_path, bancada, "s1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 4, r.stdout
    assert (plana / "meio.txt").exists()
    assert not (plana / "42-x").exists()


# --- sincronizar: os cinco casos do card ------------------------------------------------

def test_sincronizar_em_dia_sai_0_ja_em_dia(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "card.md", "c\n")
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 0, r.stderr
    assert "sincronizado" in r.stdout
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 0, r.stderr
    assert "já em dia" in r.stdout


def test_sincronizar_main_novo_mescla_e_empurra(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "card.md", "c\n")
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 0, r.stderr
    assert "mesclou origin/main" in r.stdout
    assert (wt / "NOVO.md").exists()
    remoto = _git("ls-remote", "origin", "refs/heads/fabrica/42-x", cwd=wt).split()[0]
    assert remoto == _git("rev-parse", "HEAD", cwd=wt)


def test_sincronizar_conflito_sai_4_lista_e_deixa_a_bancada_intacta(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "LEIA.md", "do card\n")
    antes = _git("rev-parse", "HEAD", cwd=wt)
    _main_novo(tmp_path, "LEIA.md", "de main\n")
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 4, r.stdout
    assert "conflito: LEIA.md" in r.stderr
    assert _git("rev-parse", "HEAD", cwd=wt) == antes
    assert _git("status", "--porcelain", cwd=wt) == ""


def test_sincronizar_arvore_suja_sai_4_antes_de_mesclar(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    (wt / "meio.txt").write_text("x\n")
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 4, r.stdout
    assert "vizinho: repo commitar" in r.stderr
    assert not (wt / "NOVO.md").exists()


def test_sincronizar_ramo_divergido_do_proprio_upstream_sai_4(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "card.md", "c\n")
    assert _repo(tmp_path, bancada, "s1", "empurrar", "demo").returncode == 0
    outra = tmp_path / "outra-mao"
    _git("clone", "-q", "-b", "fabrica/42-x", str(tmp_path / "origem.git"), str(outra))
    _commit_em(outra, "da-outra.md", "o\n")
    _git("push", "-q", "origin", "fabrica/42-x", cwd=outra)
    _commit_em(wt, "local.md", "l\n")
    r = _repo(tmp_path, bancada, "s1", "sincronizar", "demo")
    assert r.returncode == 4, r.stdout
    assert "vizinho: repo atualizar" in r.stderr


# --- fecho idempotente ------------------------------------------------------------------

def test_empurrar_repetido_devolve_ja_feito(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "card.md", "c\n")
    r = _repo(tmp_path, bancada, "s1", "empurrar", "demo")
    assert r.returncode == 0, r.stderr
    assert "[lido do forge]" in r.stdout
    r = _repo(tmp_path, bancada, "s1", "empurrar", "demo")
    assert r.returncode == 0, r.stderr
    assert "já feito" in r.stdout


def test_commitar_sem_nada_novo_devolve_ja_feito_e_o_estado_do_forge(tmp_path):
    bancada = _montar(tmp_path)
    _abrir_42(tmp_path, bancada)
    r = _repo(tmp_path, bancada, "s1", "commitar", "demo", "-m", "nada", "LEIA.md")
    assert r.returncode == 0, r.stderr
    assert "já feito" in r.stdout
    assert "forge: origin/fabrica/42-x ausente" in r.stdout


# --- sanear: so o entregue ou o fora do eixo some, e nada sem salvar ---------------------

def test_sanear_remove_bancada_cujo_ramo_foi_apagado_do_origin(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _git("push", "-u", "origin", "fabrica/42-x", cwd=wt)
    _git("push", "origin", "--delete", "fabrica/42-x", cwd=wt)
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert not wt.exists()
    assert "entregue: ramo apagado do origin" in r.stdout


def test_sanear_nunca_remove_bancada_de_ramo_nunca_empurrado(tmp_path):
    """Ausente do origin porque nunca subiu nao e entregue: e bancada viva."""
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _commit_em(wt, "card.md", "so aqui\n")
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert (wt / "card.md").exists()
    assert "42-x" not in r.stdout


def test_sanear_nao_toca_bancada_viva_suja(tmp_path):
    """O que o #950 mediu: sanear alheio levou a escrita nao commitada para um wip/."""
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    (wt / "meio.txt").write_text("escrevendo\n")
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert (wt / "meio.txt").exists()
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "fabrica/42-x"


def test_sanear_relatar_nao_apaga_e_nomeia(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir_42(tmp_path, bancada)
    _git("push", "-u", "origin", "fabrica/42-x", cwd=wt)
    _git("push", "origin", "--delete", "fabrica/42-x", cwd=wt)
    r = _repo(tmp_path, bancada, "s9", "sanear", "--relatar")
    assert r.returncode == 1, r.stdout
    assert wt.exists()
    assert "relataria remover (entregue" in r.stdout


def test_sanear_fora_do_eixo_salva_commit_so_local_e_remove(tmp_path):
    bancada = _montar(tmp_path)
    wt = bancada / "wt" / "demo" / "0a1b2c3d-1111-2222-3333-444455556666"
    _git("worktree", "add", "-b", "fabrica/9-velho", str(wt), "origin/main", cwd=bancada / "demo")
    _commit_em(wt, "velho.md", "v\n")
    ponta = _git("rev-parse", "HEAD", cwd=wt)
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert not wt.exists()
    assert "salvos em origin/wip/ti/fabrica/9-velho-" in r.stdout
    wips = _git("ls-remote", "origin", "refs/heads/wip/*", cwd=bancada / "demo")
    assert ponta in wips


def test_sanear_migra_plana_limpa_ao_eixo(tmp_path):
    bancada = _montar(tmp_path)
    plana = bancada / "wt" / "demo" / "ti"
    _git("worktree", "add", "-b", "fabrica/7-legado", str(plana), "origin/main", cwd=bancada / "demo")
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert (plana / "7-legado" / ".git").exists()


def test_sanear_cache_sujo_salva_em_wip_e_destaca_uma_vez_so(tmp_path):
    """Cache sujo: salva e destaca. Na passada seguinte, cache ja destacado e limpo nao gera
    wip de novo (a revisao do PR 206 achou o destacado virando wip/detached-* todo dia)."""
    bancada = _montar(tmp_path)
    (bancada / "demo" / "novo.txt").write_text("x\n")
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert "salvo em origin/wip/ti/" in r.stdout
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=bancada / "demo") == "HEAD"
    r = _repo(tmp_path, bancada, "s9", "sanear")
    assert r.returncode == 0, r.stderr + r.stdout
    assert "wip" not in r.stdout
    r = _repo(tmp_path, bancada, "s9", "sanear", "--relatar")
    assert r.returncode == 0, r.stdout
    assert "conforme:" in r.stdout
