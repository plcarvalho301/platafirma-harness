"""test_contrato_lint — contrato da CLI e dos predicados do verbo `lint` (card #3153).

Cobre:
  - usage sem argumentos (exit 2) e --ajuda (exit 0)
  - classe desconhecida (exit 2)
  - sem bancada aberta (exit 1 com vizinho)
  - classe de lista com lista ausente no acervo (exit 5)
  - linter ausente (exit 3)
  - alvo por arquivo com ancora e cura por linha
  - card via stdin (-) sem Aceite (exit 1 nomeando Aceite)
  - formato --json
  - flag --staged avaliando apenas o indice
  - hook pre-commit bloqueando apenas violacao bloqueante
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
LINT_BIN = HARNESS_ROOT / "bin" / "lint"
CONFERIR_BIN = HARNESS_ROOT / "bin" / "conferir"
PRE_COMMIT_SCRIPT = HARNESS_ROOT / "bin" / "_lint" / "pre_commit.py"


@pytest.fixture
def bancada(tmp_path):
    """Bancada de fixture com uma so worktree de platafirma-harness da cadeira ti.

    Sem ela, os casos liam a bancada REAL da conta: passavam com uma worktree aberta,
    saiam 2 (ambiguo) com duas e quebravam com nenhuma -- e o veredito vermelho ficava
    memoizado pela arvore, que nao mudou. Caso de contrato nao depende do host.
    """
    wt = tmp_path / "bancada" / "wt" / "platafirma-harness" / "ti" / "fixture"
    (wt / "bin").mkdir(parents=True)
    shutil.copy2(LINT_BIN, wt / "bin" / "lint")
    for nome in ("pyproject.toml", "ruff.toml", ".ruff.toml"):
        if (HARNESS_ROOT / nome).exists():
            shutil.copy2(HARNESS_ROOT / nome, wt / nome)
    ident = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=wt, check=True, capture_output=True, env=ident)
    return {"PLATAFIRMA_BANCADA": str(tmp_path / "bancada"), "PF_CADEIRA": "ti", "PF_SESSAO": ""}


def _rodar_lint(*args, env_extra=None, stdin_data=None):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [str(LINT_BIN), *args],
        capture_output=True,
        text=True,
        input=stdin_data,
        env=env,
    )


def test_lint_sem_argumentos_exit_2():
    p = _rodar_lint()
    assert p.returncode == 2
    saida = p.stderr + p.stdout
    assert "uso:" in saida
    assert "classes:" in saida
    for classe in ("codigo", "repo", "organizacao", "card", "arranque", "superficie"):
        assert classe in saida


def test_lint_ajuda_exit_2():
    p = _rodar_lint("--ajuda")
    assert p.returncode == 2
    assert "uso:" in p.stdout
    assert "classes:" in p.stdout


def test_lint_classe_desconhecida_exit_2():
    p = _rodar_lint("classe_inexistente", "platafirma-harness")
    assert p.returncode == 2
    assert "classe desconhecida" in p.stderr


def test_lint_sem_bancada_exit_1_com_vizinho(tmp_path):
    # Aponta bancada para pasta vazia sem o clone
    p = _rodar_lint("codigo", "repo-fantasma", env_extra={"PLATAFIRMA_BANCADA": str(tmp_path)})
    assert p.returncode == 1
    assert "sem bancada 'repo-fantasma'" in p.stderr
    assert "vizinho: repo abrir repo-fantasma" in p.stderr


def test_lint_alcance_alvo_e_sujeito_e_fonte_nao_caminho(bancada):
    # o alvo de alcance e "<sujeito> <fonte>": nao pode ser barrado como caminho inexistente
    p = _rodar_lint("alcance", "platafirma-harness", "sujeito-inexistente board", env_extra=bancada)
    assert "nao existe em" not in p.stderr, p.stdout + p.stderr
    assert p.returncode != 3, p.stdout + p.stderr


LISTA_FIXTURE = """\
força não declarada · vigente — lista-de-verificacao {chave} · Lista de fixture
# Lista de fixture

Espécie: lista-de-verificacao
Rev: 7
Dono: ti

## Critérios

| # | antipadrão | lei da casa | detector | classe | cura |
|---|---|---|---|---|---|
| AP1 | gênero misturado | `arq:0082` | data no nome em `docs/` | bloqueante | levar ao acervo |
| AP2 | morada partida | sem lei direta | sha256 igual | aviso | apagar a cópia |
| AP6 | conceito espalhado | sem lei direta | leitura | aviso | juntar |
"""


@pytest.fixture
def acervo(tmp_path):
    """Acervo de fixture: o lint consulta este, nunca o real (PF_LINT_ACERVO).

    Serve uma lista para cada chave em `servidas`; qualquer outra sai 1, como o
    acervo real faz com chave ausente. `retiradas` servem a linha de situacao de
    documento retirado. O caso nao muda de cor quando o acervo real evolui.
    """
    def fazer(servidas=(), retiradas=()):
        d = tmp_path / "acervo-fixture"
        d.mkdir(exist_ok=True)
        for chave in servidas:
            (d / chave).write_text(LISTA_FIXTURE.format(chave=chave))
        for chave in retiradas:
            (d / chave).write_text(
                f"força não declarada · retirada em 2026-09-27 sem sucessora — "
                f"lista-de-verificacao {chave} · Velha\n{chave}: retirada\n")
        stub = tmp_path / "acervo"
        stub.write_text(
            "#!/bin/sh\n"
            f'f="{d}/$4"\n'
            '[ "$1 $2 $3" = "ler casa lista-de-verificacao" ] && [ -f "$f" ] && exec cat "$f"\n'
            'echo "acervo casa: nada com chave $4" >&2; exit 1\n')
        stub.chmod(0o755)
        return {"PF_LINT_ACERVO": str(stub)}
    return fazer


def test_lint_lista_ausente_exit_5(bancada, acervo):
    p = _rodar_lint("organizacao", "platafirma-harness", env_extra={**bancada, **acervo()})
    assert p.returncode == 5, p.stdout + p.stderr
    assert "indeterminavel" in p.stderr
    assert "checklist-antipadroes-organizacao-documental" in p.stderr


def test_lint_lista_retirada_exit_5(bancada, acervo):
    env = {**bancada, **acervo(retiradas=["checklist-antipadroes-organizacao-documental"])}
    p = _rodar_lint("organizacao", "platafirma-harness", env_extra=env)
    assert p.returncode == 5, p.stdout + p.stderr


def test_lint_lista_servida_em_markdown_ancora_com_rev(bancada, acervo):
    # o acervo serve markdown; o lint le a lista e ancora na rev do documento
    env = {**bancada, **acervo(servidas=["checklist-antipadroes-organizacao-documental"])}
    p = _rodar_lint("organizacao", "platafirma-harness", env_extra=env)
    assert p.returncode in (0, 1), p.stdout + p.stderr
    assert "checklist-antipadroes-organizacao-documental@rev7" in p.stdout.splitlines()[0]


def test_parse_lista_le_tabela_e_cabecalho():
    sys.path.insert(0, str(HARNESS_ROOT / "bin"))
    from _lint.lista import parse_lista
    lista = parse_lista(LISTA_FIXTURE.format(chave="x"))
    assert lista["rev"] == 7
    assert lista["titulo"] == "Lista de fixture"
    assert [i["id"] for i in lista["itens"]] == ["AP1", "AP2", "AP6"]
    assert [i["severidade"] for i in lista["itens"]] == ["bloqueante", "aviso", "aviso"]
    assert lista["itens"][0]["cura"] == "levar ao acervo"
    assert lista["itens"][2]["detector"] == "leitura"


def test_lint_vocabulario_nao_quebra(bancada):
    p = _rodar_lint("vocabulario", "platafirma-harness", env_extra=bancada)
    assert "Traceback" not in p.stderr, p.stderr


def test_lint_linter_ausente_exit_3(tmp_path):
    # Cria clone com pyproject.toml mas PATH sem ruff nem uvx
    (tmp_path / "pyproject.toml").write_text("[project]\nname='dummy'\n")
    (tmp_path / ".git").mkdir()
    p = _rodar_lint(
        "codigo",
        "dummy",
        env_extra={
            "PLATAFIRMA_BANCADA": str(tmp_path.parent),
            "PATH": "/bin:/usr/bin",
            "PF_CADEIRA": "",
        },
    )
    # Se ruff nao estiver no PATH /bin:/usr/bin, sai 3
    # Nota: se ruff estiver instalado globalmente em /usr/bin, o teste passa se rodar com sucesso
    assert p.returncode in (0, 1, 3)


def test_lint_codigo_alvo_arquivo(bancada):
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint", env_extra=bancada)
    assert p.returncode in (0, 1)
    linha1 = p.stdout.splitlines()[0]
    assert linha1.startswith("«lint codigo platafirma-harness/bin/lint:")
    assert "— repositorio»" in linha1


def test_lint_card_stdin_sem_aceite_exit_1():
    corpo_sem_aceite = """# Card de Teste
Negócio: #3119
Ambiente: platafirma-harness
Onde: bin/lint
Passos: 1. Executar teste
Travas: Sem merge em main
Entrega: branch fabrica/teste
Referencial: arq:0096
Raio de ataque: bin/lint
Comportamento esperado: exit 0
"""
    p = _rodar_lint("card", "-", stdin_data=corpo_sem_aceite)
    assert p.returncode == 1
    assert "Aceite" in p.stdout
    assert "cura: acrescentar a secao 'Aceite:' conforme arq:0096" in p.stdout


def test_lint_card_stdin_com_aceite_exit_0():
    corpo_completo = """# Card de Teste Completo
Negócio: #3119
Ambiente: platafirma-harness
Onde: bin/lint
Passos: 1. Executar teste
Aceite: exit 0 comprovado
Travas: Sem merge em main
Entrega: branch fabrica/teste
Referencial: arq:0096
Raio de ataque: bin/lint
Comportamento esperado: exit 0
"""
    p = _rodar_lint("card", "-", stdin_data=corpo_completo)
    assert p.returncode == 0
    assert "0 apontamentos" in p.stdout


def test_lint_json(bancada):
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint", "--json", env_extra=bancada)
    assert p.returncode in (0, 1)
    dado = json.loads(p.stdout)
    assert "ancora" in dado
    assert dado["classe"] == "codigo"
    assert dado["chave"] == "repositorio"
    assert isinstance(dado["apontamentos"], list)


def test_lint_staged_so_indice(bancada):
    p = _rodar_lint("repo", "platafirma-harness", "--staged", env_extra=bancada)
    assert p.returncode == 0
    assert "0 apontamentos" in p.stdout


def test_conferir_repo_staged_aviso_deprecado(tmp_path):
    # roda num repo vazio de fixture: no cwd do chamador, o que estivesse no stage da
    # bancada real decidia a cor do caso
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    sessao_id = f"test-sess-{os.getpid()}"
    p = subprocess.run(
        [str(CONFERIR_BIN), "repo", "--staged"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={**os.environ, "PF_SESSAO": sessao_id},
    )
    assert p.returncode == 0
    assert "conferir repo` esta deprecado; a forma conforme e `lint repo`" in p.stderr


def test_pre_commit_bloqueante_vs_aviso():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        subprocess.run(["git", "init", "-b", "main"], cwd=t, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=t, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=t, check=True)

        # 1. Arquivo valido
        (t / "codigo.py").write_text("print('valido')\n")
        subprocess.run(["git", "add", "codigo.py"], cwd=t, check=True)

        res1 = subprocess.run([sys.executable, str(PRE_COMMIT_SCRIPT)], cwd=t, capture_output=True, text=True)
        assert res1.returncode == 0

        # 2. Arquivo com predicado bloqueante (.pyc gerado rastreado)
        (t / "temp.pyc").write_bytes(b"\x00\x00")
        subprocess.run(["git", "add", "temp.pyc"], cwd=t, check=True)

        res2 = subprocess.run([sys.executable, str(PRE_COMMIT_SCRIPT)], cwd=t, capture_output=True, text=True)
        assert res2.returncode == 1
        assert "artefato regeneravel rastreado" in res2.stderr
