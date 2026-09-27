"""Contrato de `lint organizacao` e do bloqueio no pre-commit (card #3118).

A régua é a lista do acervo; aqui o acervo é de fixture (PF_LINT_ACERVO), com a tabela
da lista como ela é servida. Prova: cada detector mecânico aponta o que a lista diz; o
lint relata só os avisos (os bloqueantes só com --todas, para contagem); o pre-commit
barra os bloqueantes no stage só em repositório declarado, e não barra quando a lista
não está servida (avisa). Não prova: a lista real do acervo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]
LINT = HARNESS / "bin" / "lint"
PRE_COMMIT = HARNESS / "bin" / "_lint" / "pre_commit.py"
CHAVE = "checklist-antipadroes-organizacao-documental"

LISTA = """\
força não declarada · vigente — lista-de-verificacao {chave} · Checklist
# Checklist de antipadrões de organização documental

Espécie: lista-de-verificacao
Rev: 2

## As doze classes

| # | antipadrão | lei da casa | detector | classe | cura |
|---|---|---|---|---|---|
| AP1 | gênero misturado em `docs/` | `arq:0082` | data no nome em docs/ | bloqueante | levar ao acervo |
| AP2 | morada partida | sem lei direta | sha256 igual | aviso | apagar a cópia |
| AP3 | fóssil vivo | `arq:0074` | marca de fita no nome | aviso | apagar |
| AP4 | documento de casa em repositório de software | `arq:0115` | `.md` com `Espécie:` | bloqueante | levar ao platafirma-casa |
| AP5 | nome opaco | sem lei direta | caractere fora de [A-Za-z0-9._-] | aviso | renomear |
| AP6 | conceito espalhado | sem lei direta | leitura | aviso | juntar |
| AP7 | chave própria de repositório | `arq:0115` | título com série | bloqueante | tirar a série |
| AP8 | sem porta | `arq:0035` | README ausente | bloqueante | escrever o README |
| AP9 | render ao lado da fonte | `arq:0051` | imagem com nome da fonte | aviso | apagar o render |
| AP10 | profundidade excessiva | sem lei direta | leitura | aviso | achatar |
| AP11 | instrumento no meio da matéria | `arq:0075` | AGENTS.md ou CLAUDE.md fora da raiz | aviso | subir para a raiz |
| AP12 | escrita que humano não entende | `arq:0098` | ponteiro nu em prosa | aviso | rodapé |
"""

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **IDENT})


def _acervo(tmp_path, servida=True):
    d = tmp_path / "acervo-fixture"
    d.mkdir(exist_ok=True)
    if servida:
        (d / CHAVE).write_text(LISTA.format(chave=CHAVE), encoding="utf-8")
    stub = tmp_path / "acervo"
    stub.write_text(
        "#!/bin/sh\n"
        f'f="{d}/$4"\n'
        '[ "$1 $2 $3" = "ler casa lista-de-verificacao" ] && [ -f "$f" ] && exec cat "$f"\n'
        "exit 1\n")
    stub.chmod(0o755)
    return str(stub)


# Um arquivo por classe mecânica. Bloqueantes: AP1, AP4, AP7, AP8. Avisos: o resto.
ARVORE = {
    "README.md": "# Demo\n\nO regime vem de arq:0082 e ninguem explica.\n",
    "docs/2026-01-01-nota.md": "# Nota\n",
    "docs/guia.md": "# Guia\n\nEspécie: guia\n\nTexto.\n",
    "a.txt": "igual\n",
    "b.txt": "igual\n",
    "handoff-sessao.md": "# Passagem\n",
    "nome com espaco.txt": "x\n",
    "adr.md": "# arq:0001 — decisao\n",
    "sub/pyproject.toml": "[project]\nname='x'\n",
    "diag.d2": "a -> b\n",
    "diag.svg": "<svg/>\n",
    "sub2/CLAUDE.md": "instrucao\n",
}
AVISOS = {"AP2", "AP3", "AP5", "AP9", "AP11", "AP12"}
BLOQUEANTES = {"AP1", "AP4", "AP7", "AP8"}


@pytest.fixture
def bancada(tmp_path):
    wt = tmp_path / "bancada" / "wt" / "demo-org" / "ti" / "fixture"
    for rel, corpo in ARVORE.items():
        p = wt / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(corpo, encoding="utf-8")
    _git(wt, "init", "-q", "-b", "main")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "fixture")
    return {"PLATAFIRMA_BANCADA": str(tmp_path / "bancada"), "PF_CADEIRA": "ti"}


def _lint(env, *args):
    r = subprocess.run([str(LINT), "organizacao", "demo-org", *args, "--json"],
                       capture_output=True, text=True, env={**os.environ, **env})
    return r, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else None)


def test_lint_relata_so_os_avisos(tmp_path, bancada):
    r, d = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path)})
    assert r.returncode == 1, r.stdout + r.stderr
    ids = {a["id"] for a in d["apontamentos"]}
    assert ids == AVISOS, ids
    assert d["ancora"].endswith(f"{CHAVE}@rev2»")
    assert all(a["severidade"] == "aviso" for a in d["apontamentos"])


def test_lint_todas_inclui_bloqueantes_para_contagem(tmp_path, bancada):
    r, d = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path)}, "--todas")
    assert r.returncode == 1
    assert {a["id"] for a in d["apontamentos"]} == AVISOS | BLOQUEANTES


def test_classe_de_leitura_nao_roda(tmp_path, bancada):
    _, d = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path)}, "--todas")
    assert not {"AP6", "AP10"} & {a["id"] for a in d["apontamentos"]}


def test_apontamento_traz_a_cura_da_lista(tmp_path, bancada):
    _, d = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path)})
    ap2 = next(a for a in d["apontamentos"] if a["id"] == "AP2")
    assert ap2["cura"] == "apagar a cópia"
    assert ap2["arquivo"] == "b.txt" and "a.txt" in ap2["o_que_fere"]


def test_lint_resumo_conta_por_regra(tmp_path, bancada):
    r, d = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path)}, "--todas", "--resumo")
    assert r.returncode == 1
    assert set(d["contagem"]) == AVISOS | BLOQUEANTES
    assert d["contagem"]["AP4"] == {"n": 1, "severidade": "bloqueante"}
    assert "apontamentos" not in d


def test_lint_sem_lista_sai_5(tmp_path, bancada):
    r, _ = _lint({**bancada, "PF_LINT_ACERVO": _acervo(tmp_path, servida=False)})
    assert r.returncode == 5


# --- pre-commit ----------------------------------------------------------------

def _repo_commit(tmp_path, habilitados, servida=True):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", "https://forge.test/dono/demo-org.git")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "guia.md").write_text("# Guia\n\nEspécie: guia\n", encoding="utf-8")
    _git(repo, "add", "-A")
    reg = tmp_path / "bloqueia.json"
    reg.write_text(json.dumps({"repositorios": habilitados}), encoding="utf-8")
    env = {**os.environ, "PF_ORGANIZACAO_BLOQUEIA": str(reg),
           "PF_LINT_ACERVO": _acervo(tmp_path, servida)}
    return subprocess.run([sys.executable, str(PRE_COMMIT)], cwd=repo,
                          capture_output=True, text=True, env=env)


def test_pre_commit_barra_bloqueante_em_repo_declarado(tmp_path):
    r = _repo_commit(tmp_path, ["demo-org"])
    assert r.returncode == 1, r.stderr
    assert "[organizacao] docs/guia.md" in r.stderr
    assert "cura: levar ao platafirma-casa" in r.stderr


def test_pre_commit_nao_barra_repo_nao_declarado(tmp_path):
    r = _repo_commit(tmp_path, [])
    assert r.returncode == 0, r.stderr


def test_pre_commit_sem_lista_avisa_e_nao_barra(tmp_path):
    r = _repo_commit(tmp_path, ["demo-org"], servida=False)
    assert r.returncode == 0, r.stderr
    assert "organizacao nao verificada" in r.stderr
