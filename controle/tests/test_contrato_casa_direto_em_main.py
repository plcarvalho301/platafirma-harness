"""Contrato do regime direto em main em `repo` e `minuta` (arq:0083 §1; ordem do dono de
28/09/2026: platafirma-casa, repositorio de deliberacao, commita direto em main).

Git real contra bare local, sem rede e sem gh. Prova: `repo abrir platafirma-casa` (com e
sem card, com e sem --slug) da UMA worktree por cadeira, wt/platafirma-casa/<cadeira>/main,
que segue origin/main e anda do forge ao reabrir; commitar (so os caminhos nomeados) e
sincronizar chegam ao main do origin, rebaseando sobre main novo sem merge; conflito sai 4
com a lista e a bancada intacta; empurrar e o sincronizar; pr-abrir e pr-merge recusam 2; a
bancada por card antiga segue por <repo>@<chave> e se entrega em main; repositorio de codigo
segue exigindo ramo. `minuta escrever` abre a worktree por `repo abrir` quando falta, puxa
antes de numerar, commita e empurra para main, e sem forge sai 3 com a chamada exata;
`circular` le a minuta que outra mao ja pos em main e empurra a convocacao nova antes do
ping; `formalizar` fecha em main. Nao prova: o forge de verdade (GitHub, credencial, o
pre-push e o pre-commit da casa), nem a `fila` real (stub que grava a chamada).
"""
import json
import os
import subprocess
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / "bin"
CASA = "platafirma-casa"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
RECUSA = "repositório de deliberação: commit direto em main (arq:0083)"


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _bare(tmp_path, nome):
    return tmp_path / f"{nome}.git"


def _semente(tmp_path, nome):
    return tmp_path / f"semente-{nome}"


def _criar_origem(tmp_path, nome, arquivos):
    origem, semente = _bare(tmp_path, nome), _semente(tmp_path, nome)
    _git("init", "-q", "--bare", "-b", "main", str(origem))
    _git("init", "-q", "-b", "main", str(semente))
    for rel, texto in arquivos.items():
        (semente / rel).parent.mkdir(parents=True, exist_ok=True)
        (semente / rel).write_text(texto)
    _git("add", ".", cwd=semente)
    _git("commit", "-q", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "-q", "origin", "main", cwd=semente)


def _main_novo(tmp_path, arquivo="NOVO.md", texto="novo\n", nome=CASA, apagar=False):
    """Outra mao empurra direto em main."""
    semente = _semente(tmp_path, nome)
    _git("pull", "-q", "origin", "main", cwd=semente)
    alvo = semente / arquivo
    if apagar:
        _git("rm", "-q", arquivo, cwd=semente)
    else:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto)
        _git("add", arquivo, cwd=semente)
    _git("commit", "-q", "-m", f"main: {arquivo}", cwd=semente)
    _git("push", "-q", "origin", "main", cwd=semente)


def _montar(tmp_path):
    """platafirma-casa simulado (0003 no disco; 0005 nasceu e foi formalizada) e um repo de
    codigo `demo`, os dois com clone base na bancada temporaria."""
    bancada = tmp_path / "bancada"
    bancada.mkdir()
    _criar_origem(tmp_path, CASA, {"LEIA.md": "x\n", "minuta/0003-velha.md": "# 0003 — Velha\n"})
    _main_novo(tmp_path, "minuta/0005-fechada.md", "# 0005 — Fechada\n")
    _main_novo(tmp_path, "minuta/0005-fechada.md", apagar=True)
    _git("clone", "-q", str(_bare(tmp_path, CASA)), str(bancada / CASA))
    _criar_origem(tmp_path, "demo", {"LEIA.md": "x\n"})
    _git("clone", "-q", str(_bare(tmp_path, "demo")), str(bancada / "demo"))
    return bancada


def _env(tmp_path, bancada, **extra):
    stubs = tmp_path / "stubs"
    stubs.mkdir(exist_ok=True)
    fila = stubs / "fila"
    if not fila.exists():
        fila.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$FILA_LOG"\ncat >> "$FILA_LOG"\n')
        fila.chmod(0o755)
    return {
        "PATH": f"{stubs}:{os.environ.get('PATH', '/usr/bin:/bin')}",
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-dados",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "FILA_LOG": str(tmp_path / "fila.log"),
        **IDENT,
        **extra,
    }


def _repo(tmp_path, bancada, *args, **extra):
    return subprocess.run([str(BIN / "repo"), *args], env=_env(tmp_path, bancada, **extra),
                          capture_output=True, text=True, check=False)


def _minuta(tmp_path, bancada, *args):
    return subprocess.run([str(BIN / "minuta"), *args], env=_env(tmp_path, bancada),
                          capture_output=True, text=True, check=False)


def _wt_main(bancada):
    return bancada / "wt" / CASA / "dados" / "main"


def _abrir(tmp_path, bancada):
    r = _repo(tmp_path, bancada, "abrir", CASA)
    assert r.returncode == 0, r.stderr
    return _wt_main(bancada)


def _main_do_origin(tmp_path, nome=CASA):
    return _git("--git-dir", str(_bare(tmp_path, nome)), "rev-parse", "main")


def _no_origin(tmp_path, caminho, nome=CASA):
    r = subprocess.run(["git", "--git-dir", str(_bare(tmp_path, nome)), "show", f"main:{caminho}"],
                       capture_output=True, text=True, check=False)
    return r.stdout if r.returncode == 0 else None


def _commit_em(wt, arquivo, texto):
    (wt / arquivo).write_text(texto)
    _git("add", arquivo, cwd=wt)
    _git("commit", "-q", "-m", f"local: {arquivo}", cwd=wt)


# --- repo abrir ---------------------------------------------------------------------------

def test_abrir_da_a_worktree_de_main_da_cadeira_com_ou_sem_card(tmp_path):
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "abrir", CASA)
    assert r.returncode == 0, r.stderr
    wt = _wt_main(bancada)
    assert (wt / ".git").exists()
    assert "direto em main" in r.stdout
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "dados/main"
    assert _git("rev-parse", "--abbrev-ref", "@{upstream}", cwd=wt) == "origin/main"

    r = _repo(tmp_path, bancada, "abrir", CASA, "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert "bancada já aberta" in r.stdout and str(wt) in r.stdout
    assert "card #42: em-execucao" in r.stdout
    assert not (bancada / "wt" / CASA / "dados" / "42-x").exists()
    assert _git("branch", "--list", "fabrica/*", cwd=bancada / CASA) == ""


def test_abrir_de_novo_traz_main_novo_do_forge(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "abrir", CASA, "--slug", "qualquer")
    assert r.returncode == 0, r.stderr
    assert "trouxe 1 commit(s) do forge" in r.stdout
    assert _git("rev-parse", "HEAD", cwd=wt) == _main_do_origin(tmp_path)
    assert (wt / "NOVO.md").exists()


# --- commitar, sincronizar, empurrar -------------------------------------------------------

def test_commitar_so_o_nomeado_e_sincronizar_chegam_ao_main_do_origin(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    (wt / "nota.md").write_text("nota\n")
    (wt / "alheio.md").write_text("de outra mao\n")
    r = _repo(tmp_path, bancada, "commitar", CASA, "-m", "nota", "nota.md")
    assert r.returncode == 0, r.stderr
    assert "commit em platafirma-casa (dados/main)" in r.stdout
    assert "forge: origin/main" in r.stdout
    assert _git("show", "--name-only", "--format=", "HEAD", cwd=wt) == "nota.md"
    (wt / "alheio.md").unlink()

    r = _repo(tmp_path, bancada, "sincronizar", CASA)
    assert r.returncode == 0, r.stderr
    assert "sincronizado: main" in r.stdout
    assert _main_do_origin(tmp_path) == _git("rev-parse", "HEAD", cwd=wt)
    assert _no_origin(tmp_path, "nota.md") == "nota\n"

    r = _repo(tmp_path, bancada, "sincronizar", CASA)
    assert r.returncode == 0, r.stderr
    assert "já em dia" in r.stdout


def test_sincronizar_rebaseia_sobre_main_novo_sem_merge(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _commit_em(wt, "nota.md", "nota\n")
    _main_novo(tmp_path)
    r = _repo(tmp_path, bancada, "sincronizar", CASA)
    assert r.returncode == 0, r.stderr
    assert "rebaseado sobre origin/main" in r.stdout
    assert _main_do_origin(tmp_path) == _git("rev-parse", "HEAD", cwd=wt)
    assert _git("rev-list", "--merges", "--count", "HEAD", cwd=wt) == "0"
    assert _no_origin(tmp_path, "NOVO.md") == "novo\n" and _no_origin(tmp_path, "nota.md") == "nota\n"


def test_sincronizar_conflito_sai_4_lista_e_deixa_a_bancada_intacta(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _commit_em(wt, "LEIA.md", "da cadeira\n")
    antes = _git("rev-parse", "HEAD", cwd=wt)
    _main_novo(tmp_path, "LEIA.md", "de main\n")
    main_antes = _main_do_origin(tmp_path)
    r = _repo(tmp_path, bancada, "sincronizar", CASA)
    assert r.returncode == 4, r.stdout
    assert "conflito: LEIA.md" in r.stderr
    assert _git("rev-parse", "HEAD", cwd=wt) == antes
    assert _git("status", "--porcelain", cwd=wt) == ""
    assert _main_do_origin(tmp_path) == main_antes


def test_empurrar_no_regime_e_o_sincronizar_e_nao_cria_ramo_no_origin(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _commit_em(wt, "nota.md", "nota\n")
    r = _repo(tmp_path, bancada, "empurrar", CASA)
    assert r.returncode == 0, r.stderr
    assert _main_do_origin(tmp_path) == _git("rev-parse", "HEAD", cwd=wt)
    assert _git("--git-dir", str(_bare(tmp_path, CASA)), "branch", "--list", "dados/*") == ""


# --- PR recusa -------------------------------------------------------------------------------

def test_pr_abrir_e_pr_merge_recusam_com_2(tmp_path):
    bancada = _montar(tmp_path)
    _abrir(tmp_path, bancada)
    sem_gh = str(tmp_path / "sem-gh")  # nunca o gh real: a recusa vem antes do forge
    r = _repo(tmp_path, bancada, "pr-abrir", CASA, "--titulo", "t", "--corpo", "c", PF_GH_BIN=sem_gh)
    assert r.returncode == 2, r.stdout + r.stderr
    assert RECUSA in r.stderr
    r = _repo(tmp_path, bancada, "pr-merge", CASA, "89", PF_GH_BIN=sem_gh)
    assert r.returncode == 2, r.stdout + r.stderr
    assert RECUSA in r.stderr


# --- bancada por card antiga e repositorio de codigo ----------------------------------------

def test_bancada_por_card_antiga_segue_e_se_entrega_em_main(tmp_path):
    bancada = _montar(tmp_path)
    legado = bancada / "wt" / CASA / "dados" / "7-legado"
    _git("worktree", "add", "-q", "-b", "fabrica/7-legado", str(legado), "origin/main",
         cwd=bancada / CASA)
    _commit_em(legado, "legado.md", "l\n")
    _abrir(tmp_path, bancada)

    r = _repo(tmp_path, bancada, "estado", CASA)
    assert r.returncode == 0, r.stderr
    assert "ramo dados/main" in r.stdout
    r = _repo(tmp_path, bancada, "estado", f"{CASA}@7-legado")
    assert r.returncode == 0, r.stderr
    assert "fabrica/7-legado" in r.stdout

    r = _repo(tmp_path, bancada, "sincronizar", f"{CASA}@7-legado")
    assert r.returncode == 0, r.stderr
    assert _no_origin(tmp_path, "legado.md") == "l\n"
    assert (legado / "legado.md").exists()


def test_repositorio_de_codigo_segue_exigindo_ramo(tmp_path):
    bancada = _montar(tmp_path)
    main_antes = _main_do_origin(tmp_path, "demo")
    r = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "dados" / "42-x"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "fabrica/42-x"
    assert not (bancada / "wt" / "demo" / "dados" / "main").exists()
    _commit_em(wt, "card.md", "c\n")
    r = _repo(tmp_path, bancada, "sincronizar", "demo")
    assert r.returncode == 0, r.stderr
    assert "sincronizado: fabrica/42-x" in r.stdout
    assert _main_do_origin(tmp_path, "demo") == main_antes
    r = _repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "t", PF_GH_BIN=str(tmp_path / "sem-gh"))
    assert r.returncode == 3, r.stdout + r.stderr
    assert "deliberação" not in r.stderr


# --- minuta ----------------------------------------------------------------------------------

def test_minuta_escrever_puxa_antes_de_numerar_commita_e_empurra_para_main(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _main_novo(tmp_path, "minuta/0006-outra.md", "# 0006 — Outra\n")
    r = _minuta(tmp_path, bancada, "escrever", "processamento-de-texto",
                "--convoca", "engenharia,arquiteto", "--card", "#3060")
    assert r.returncode == 0, r.stderr
    arq = wt / "minuta" / "0007-processamento-de-texto.md"
    assert r.stdout.strip() == str(arq)
    assert "Card: #3060" in _no_origin(tmp_path, "minuta/0007-processamento-de-texto.md")
    assert _main_do_origin(tmp_path) == _git("rev-parse", "HEAD", cwd=wt)


def test_minuta_escrever_sem_worktree_abre_por_repo_abrir_e_numera_pelo_historico(tmp_path):
    bancada = _montar(tmp_path)
    r = _minuta(tmp_path, bancada, "escrever", "pauta", "--convoca", "engenharia")
    assert r.returncode == 0, r.stderr
    assert (_wt_main(bancada) / ".git").exists()
    assert r.stdout.strip() == str(_wt_main(bancada) / "minuta" / "0006-pauta.md")
    assert _no_origin(tmp_path, "minuta/0006-pauta.md") is not None


def test_minuta_escrever_sem_forge_sai_3_com_a_chamada_exata(tmp_path):
    bancada = tmp_path / "bancada"
    bancada.mkdir()
    registro = tmp_path / "release" / "current" / "harness" / "registro"
    registro.mkdir(parents=True)
    (registro / "familias.json").write_text(json.dumps({CASA: {"url": str(tmp_path / "nao-ha.git")}}))
    r = _minuta(tmp_path, bancada, "escrever", "pauta", "--convoca", "engenharia")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "rode `repo abrir platafirma-casa`" in r.stderr
    assert r.stdout == ""


def _pauta(convocadas, secoes):
    corpo = [
        "# 0006 — Pauta", "", "Aberta por: arquiteto · 2026-09-28",
        f"Convocadas: {', '.join(convocadas)}", "Fecha: Pedro", "",
        "## Pergunta", "Decide?", "",
    ]
    for cad, texto in secoes.items():
        corpo += [f"## Posição — {cad}", "", texto, ""]
    corpo += ["## Divergência", "<só o que sobrou>", "", "## Decisão", "<quem fecha>", ""]
    return "\n".join(corpo)


def test_minuta_circular_le_a_minuta_que_outra_mao_pos_em_main(tmp_path):
    bancada = _montar(tmp_path)
    wt = _abrir(tmp_path, bancada)
    _main_novo(tmp_path, "minuta/0006-pauta.md",
               _pauta(["engenharia"], {"arquiteto": "posição escrita",
                                       "engenharia": "<a preencher pela própria cadeira>"}))
    r = _minuta(tmp_path, bancada, "circular", "6", "produto")
    assert r.returncode == 0, r.stderr
    assert "circulado: minuta 0006 para produto" in r.stdout
    assert "Convocadas: engenharia, produto" in _no_origin(tmp_path, "minuta/0006-pauta.md")
    assert _main_do_origin(tmp_path) == _git("rev-parse", "HEAD", cwd=wt)
    fila = (tmp_path / "fila.log").read_text()
    assert "--ref minuta/0006-pauta.md produto" in fila


def test_minuta_formalizar_fecha_em_main(tmp_path):
    bancada = _montar(tmp_path)
    _abrir(tmp_path, bancada)
    _main_novo(tmp_path, "minuta/0006-pauta.md",
               _pauta(["engenharia"], {"arquiteto": "posição", "engenharia": "posição"}))
    r = _minuta(tmp_path, bancada, "formalizar", "6", "--como", "adr")
    assert r.returncode == 0, r.stderr
    assert _no_origin(tmp_path, "minuta/0006-pauta.md") is None
    assert _no_origin(tmp_path, "macro-global/decisions/0001-pauta.md") is not None
