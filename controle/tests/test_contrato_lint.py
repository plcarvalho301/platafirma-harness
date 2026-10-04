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
    def fazer(servidas=(), retiradas=(), textos=None):
        d = tmp_path / "acervo-fixture"
        d.mkdir(exist_ok=True)
        for chave in servidas:
            (d / chave).write_text(LISTA_FIXTURE.format(chave=chave))
        for chave, texto in (textos or {}).items():
            (d / chave).write_text(texto)
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


LISTA_CODIGO = """\
força não declarada · vigente — lista-de-verificacao antipadroes-de-codigo · Antipadrões de código
# Antipadrões de código

Espécie: lista-de-verificacao
Rev: 3
Dono: engenharia

## Critérios

| # | antipadrão | fonte | detector | severidade | cura |
|---|---|---|---|---|---|
| P1 | argumento padrão mutável | Ramalho | `ruff B006` | aviso | Use `None` e crie dentro. |
| P12 | `assert` em produção | ruff | `ruff S101` | aviso | Levante exceção. |
| P99 | regra que o ruff instalado não conhece | fixture | `ruff ZZZ999` | aviso | nada |
| D14 | código morto | Martin | `ruff F401` | aviso | Apague. |
| S1 | expansão sem aspas | BashPitfalls | `shellcheck SC2086` | aviso | Ponha aspas duplas. |
| S6 | `set -e` como único tratamento | BashFAQ 105 | `lint codigo`, predicado BASH_SET_E | aviso | Confira a saída. |
| S14 | script de shell com mais de 5 linhas | Google Shell | contagem de linhas em arquivo com shebang de shell | aviso | Reescreva em Python. |
| F1 | lote sem fila | ordem | leitura | aviso | Fila. |
"""


def _wt(tmp_path, nome="mono"):
    wt = tmp_path / "bancada" / "wt" / nome / "ti" / "fixture"
    wt.mkdir(parents=True)
    (wt / ".git").mkdir()
    env = {"PLATAFIRMA_BANCADA": str(tmp_path / "bancada"), "PF_CADEIRA": "ti", "PF_SESSAO": ""}
    return wt, env


def _precisa_ruff():
    if not (shutil.which("ruff") or shutil.which("uvx")):
        pytest.skip("ruff/uvx ausente no ambiente")


def test_lint_codigo_sem_a_lista_exit_5(tmp_path, acervo):
    wt, env = _wt(tmp_path)
    (wt / "m.py").write_text("import os\n")
    p = _rodar_lint("codigo", "mono", env_extra={**env, **acervo()})
    assert p.returncode == 5, p.stdout + p.stderr
    assert "antipadroes-de-codigo" in p.stderr


def test_lint_linter_ausente_exit_3(tmp_path, acervo):
    # PATH sem ruff e sem uvx, com arquivo python no alvo: o analisador necessario falta
    wt, env = _wt(tmp_path)
    (wt / "m.py").write_text("import os\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO}), "PATH": "/bin:/usr/bin"}
    if shutil.which("ruff", path="/bin:/usr/bin") or shutil.which("uvx", path="/bin:/usr/bin"):
        pytest.skip("ruff ou uvx instalado no sistema")
    p = _rodar_lint("codigo", "mono", env_extra=env)
    assert p.returncode == 3, p.stdout + p.stderr
    assert "ruff" in p.stderr


def test_lint_codigo_ancora_na_lista(tmp_path, acervo):
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "m.py").write_text("x = 1\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", "m.py", env_extra=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.splitlines()[0] == "«lint codigo mono/m.py: 0 apontamentos — antipadroes-de-codigo@rev3»"


def test_lint_codigo_python_sem_extensao_em_raiz_sem_manifesto(tmp_path, acervo):
    # #2856 linha 190: raiz com bin/ e sem pyproject caia no ramo de shell; o ruff nao rodava
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "bin").mkdir()
    (wt / "bin" / "verbo").write_text("#!/usr/bin/env python3\ndef f(a=[]):\n    return a\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", "bin/verbo", "--json", env_extra=env)
    assert p.returncode == 1, p.stdout + p.stderr
    dado = json.loads(p.stdout)
    assert dado["chave"] == "antipadroes-de-codigo" and dado["rev"] == 3
    (ap,) = dado["apontamentos"]
    assert (ap["arquivo"], ap["linha"], ap["id"]) == ("bin/verbo", 2, "P1")
    assert "B006" in ap["o_que_fere"] and ap["cura"] == "Use `None` e crie dentro."


def test_lint_codigo_regra_desconhecida_vira_aviso_e_o_resto_mede(tmp_path, acervo):
    # selecionar codigo que o ruff nao conhece faz ele sair 2 e nao medir nada
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "m.py").write_text("import os\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", env_extra=env)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "ZZZ999" in p.stderr
    assert "m.py:1: D14" in p.stdout


def test_lint_codigo_assert_em_teste_nao_aponta(tmp_path, acervo):
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "tests").mkdir()
    (wt / "tests" / "test_x.py").write_text("def test_a():\n    assert 1\n")
    (wt / "prod.py").write_text("def f(x):\n    assert x\n    return x\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", env_extra=env)
    assert "prod.py:2: P12" in p.stdout, p.stdout + p.stderr
    assert "test_x.py" not in p.stdout


def test_lint_codigo_shell_pelos_predicados_e_pelo_shellcheck(tmp_path, acervo):
    wt, env = _wt(tmp_path)
    (wt / "s.sh").write_text("#!/bin/bash\nset -e\nf() {\n  [ -n \"$1\" ] && echo ok\n}\necho $HOME\nf\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", "s.sh", env_extra=env)
    assert p.returncode == 1, p.stdout + p.stderr
    assert "s.sh:4: S6" in p.stdout, p.stdout
    assert "s.sh:1: S14" in p.stdout, p.stdout
    if shutil.which("shellcheck") or shutil.which("uvx"):
        assert "s.sh:6: S1" in p.stdout and "SC2086" in p.stdout, p.stdout + p.stderr
    else:
        assert "shellcheck ausente" in p.stderr


def test_lint_codigo_alvo_arquivo(bancada, acervo):
    _precisa_ruff()
    env = {**bancada, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint", env_extra=env)
    assert p.returncode in (0, 1), p.stdout + p.stderr
    linha1 = p.stdout.splitlines()[0]
    assert linha1.startswith("«lint codigo platafirma-harness/bin/lint:")
    assert "— antipadroes-de-codigo@rev3»" in linha1


def test_lint_codigo_alvo_em_subprojeto_roda_ruff_do_subprojeto(tmp_path, acervo):
    # card #3074: raiz com bin/ e pyproject so em rag/ -- o alvo rag/ tem de rodar o ruff
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "bin").mkdir()
    (wt / "bin" / "ferramenta").write_text("#!/bin/sh\necho oi\n")
    (wt / "rag" / "pacote").mkdir(parents=True)
    (wt / "rag" / "pyproject.toml").write_text("[project]\nname='rag'\nversion='0'\n")
    (wt / "rag" / "pacote" / "modulo.py").write_text("import os\n")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    for alvo in ("rag", "rag/pacote/modulo.py"):
        p = _rodar_lint("codigo", "mono", alvo, env_extra=env)
        assert p.returncode == 1, p.stdout + p.stderr
        assert "rag/pacote/modulo.py:1" in p.stdout, p.stdout
        assert "F401" in p.stdout, p.stdout
        assert "-->" not in p.stdout, p.stdout


def test_raiz_da_stack_sobe_ate_o_manifesto(tmp_path):
    sys.path.insert(0, str(HARNESS_ROOT / "bin"))
    from _lint.codigo import raiz_da_stack
    (tmp_path / "bin").mkdir()
    (tmp_path / "rag" / "a" / "b").mkdir(parents=True)
    (tmp_path / "rag" / "ruff.toml").write_text("")
    (tmp_path / "rag" / "a" / "b" / "c.py").write_text("")
    raiz = tmp_path.resolve()
    assert raiz_da_stack(raiz, "rag/a/b/c.py") == raiz / "rag"
    assert raiz_da_stack(raiz, "rag") == raiz / "rag"
    assert raiz_da_stack(raiz, "bin") == raiz
    assert raiz_da_stack(raiz, None) == raiz


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


def test_lint_json(bancada, acervo):
    _precisa_ruff()
    env = {**bancada, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "platafirma-harness", "bin/lint", "--json", env_extra=env)
    assert p.returncode in (0, 1), p.stdout + p.stderr
    dado = json.loads(p.stdout)
    assert "ancora" in dado
    assert dado["classe"] == "codigo"
    assert dado["chave"] == "antipadroes-de-codigo"
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


def test_lint_prosa_le_a_regua_que_mora_como_padrao(bancada, tmp_path):
    # #2856 linha 84: styleguide-da-wiki mora no acervo como `padrao`, e `lint prosa` saia 5 sempre
    doc = tmp_path / "styleguide-da-wiki"
    doc.write_text("força não declarada · vigente — padrao styleguide-da-wiki · Styleguide\n"
                   "# Styleguide da wiki\n\nEspécie: padrao\n")
    stub = tmp_path / "acervo-padrao"
    stub.write_text("#!/bin/sh\n"
                    f'[ "$1 $2 $3 $4" = "ler casa padrao styleguide-da-wiki" ] && exec cat "{doc}"\n'
                    'echo "acervo casa: nada com chave $4" >&2; exit 1\n')
    stub.chmod(0o755)
    p = _rodar_lint("prosa", "platafirma-harness", env_extra={**bancada, "PF_LINT_ACERVO": str(stub)})
    assert p.returncode == 0, p.stdout + p.stderr
    assert "styleguide-da-wiki@rev1" in p.stdout.splitlines()[0]


def test_lint_prosa_sem_a_regua_em_nenhuma_especie_exit_5(bancada, acervo):
    p = _rodar_lint("prosa", "platafirma-harness", env_extra={**bancada, **acervo()})
    assert p.returncode == 5, p.stdout + p.stderr
    assert "indeterminavel" in p.stderr
    assert "styleguide-da-wiki" in p.stderr


# ------------------------------------------------------------------ predicados da casa
# Um caso por predicado: o codigo que tem a forma aponta, e o vizinho que nao tem, nao.


def _achados(tmp_path, nome_predicado, arquivos, item=None):
    sys.path.insert(0, str(HARNESS_ROOT / "bin"))
    from _lint.codigo import TODOS_PREDICADOS
    ctx = _ctx(tmp_path, arquivos)
    funcao, _ = TODOS_PREDICADOS[nome_predicado]
    return sorted((a.arquivo, a.linha) for a in funcao(ctx, item or {}))


def _ctx(tmp_path, arquivos):
    sys.path.insert(0, str(HARNESS_ROOT / "bin"))
    from _lint.codigo import _por_lingua
    from _lint.predicados import Contexto
    raiz = (tmp_path / "repo").resolve()
    for rel, texto in arquivos.items():
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(texto)
    todos = sorted(p for p in raiz.rglob("*") if p.is_file())
    por = _por_lingua(todos)
    return Contexto(raiz, por["python"], por["shell"], por["unit"], por["python"])


def test_predicado_prazo_externo(tmp_path):
    assert _achados(tmp_path, "PRAZO_EXTERNO", {"a.py": (
        "import subprocess\n"
        "subprocess.run(['ls'])\n"
        "subprocess.run(['ls'], timeout=5)\n"
        "p = subprocess.Popen(['ls'])\n"
        "p.communicate()\n")}) == [("a.py", 2), ("a.py", 5)]


def test_predicado_lote_sem_fila(tmp_path):
    # o formato do #3194: laco sobre obras, chamada externa e repeticao dentro
    assert _achados(tmp_path, "LOTE_SEM_FILA", {"a.py": (
        "import time, httpx\n"
        "def lote(obras, cliente):\n"
        "    for obra in obras:\n"
        "        for tentativa in range(3):\n"
        "            try:\n"
        "                cliente.post('/converter', json=obra)\n"
        "                break\n"
        "            except httpx.HTTPError:\n"
        "                time.sleep(30)\n"
        "def soma(xs):\n"
        "    for x in xs:\n"
        "        try:\n"
        "            print(int(x))\n"
        "        except ValueError:\n"
        "            pass\n")}) == [("a.py", 3)]


def test_predicado_lote_sem_fila_pela_funcao_chamada_e_ocupado_repetido(tmp_path):
    # a forma do bin/curar no lote 91feb40b: a funcao da obra repete o 409, o laco a chama
    fonte = {"a.py": (
        "import time, requests\n"
        "def converter(obra):\n"
        "    for _ in range(20):\n"
        "        resp = requests.post('http://c/conversoes', data=obra, timeout=5)\n"
        "        if resp.status_code != 409:\n"
        "            break\n"
        "        time.sleep(30)\n"
        "    return resp\n"
        "def lote(obras):\n"
        "    return [converter(o) for o in obras]\n"
        "def lote_em_laco(obras):\n"
        "    for o in obras:\n"
        "        converter(o)\n")}
    assert _achados(tmp_path, "LOTE_SEM_FILA", fonte) == [("a.py", 10), ("a.py", 12)]
    assert _achados(tmp_path, "OCUPADO_REPETIDO", fonte) == [("a.py", 5)]


def test_predicado_recuo_fixo_e_repete_sem_teto(tmp_path):
    fonte = {"a.py": (
        "import time, random\n"
        "def a(f):\n"
        "    while True:\n"
        "        try:\n"
        "            return f()\n"
        "        except OSError:\n"
        "            time.sleep(2)\n"
        "def b(f):\n"
        "    for i in range(5):\n"
        "        try:\n"
        "            return f()\n"
        "        except OSError:\n"
        "            time.sleep(random.uniform(0, 2 ** i))\n")}
    assert _achados(tmp_path, "RECUO_FIXO", fonte) == [("a.py", 7)]
    assert _achados(tmp_path, "REPETE_SEM_TETO", fonte) == [("a.py", 3)]


def test_predicado_erro_sem_causa(tmp_path):
    assert _achados(tmp_path, "ERRO_SEM_CAUSA", {"a.py": (
        "import sys\n"
        "def a(x):\n"
        "    if not x:\n"
        "        sys.exit(2)\n"
        "    if x < 0:\n"
        "        print('negativo', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "    sys.exit(0)\n")}) == [("a.py", 4)]


def test_predicado_popen_wait(tmp_path):
    assert _achados(tmp_path, "POPEN_WAIT", {"a.py": (
        "import subprocess\n"
        "def a():\n"
        "    p = subprocess.Popen(['ls'], stdout=subprocess.PIPE)\n"
        "    p.wait()\n"
        "    q = subprocess.Popen(['ls'])\n"
        "    q.wait()\n")}) == [("a.py", 4)]


def test_predicado_ambiente_na_importacao(tmp_path):
    assert _achados(tmp_path, "AMBIENTE_NA_IMPORTACAO", {"a.py": (
        "import os\n"
        "RAIZ = os.environ.get('RAIZ', '/tmp')\n"
        "def raiz():\n"
        "    return os.environ.get('RAIZ', '/tmp')\n")}) == [("a.py", 2)]


def test_predicado_trava_com_io(tmp_path):
    assert _achados(tmp_path, "TRAVA_COM_IO", {"a.py": (
        "import subprocess\n"
        "def a(self):\n"
        "    with self._lock:\n"
        "        subprocess.run(['ls'], timeout=1)\n"
        "    with self._lock:\n"
        "        self.n += 1\n")}) == [("a.py", 4)]


def test_predicado_escada_isinstance(tmp_path):
    assert _achados(tmp_path, "ESCADA_ISINSTANCE", {"a.py": (
        "def a(x):\n"
        "    if isinstance(x, int):\n"
        "        return 1\n"
        "    elif isinstance(x, str):\n"
        "        return 2\n"
        "    elif isinstance(x, list):\n"
        "        return 3\n"
        "def b(x):\n"
        "    if isinstance(x, int):\n"
        "        return 1\n"
        "    elif isinstance(x, str):\n"
        "        return 2\n")}) == [("a.py", 2)]


def test_predicado_confere_e_usa(tmp_path):
    assert _achados(tmp_path, "CONFERE_E_USA", {"a.py": (
        "import os\n"
        "def a(f, p):\n"
        "    if os.path.exists(f):\n"
        "        os.remove(f)\n"
        "    if p.exists():\n"
        "        return p.read_text()\n"
        "    if os.path.exists(f):\n"
        "        print(f)\n")}) == [("a.py", 4), ("a.py", 6)]


def test_predicado_unit_segundo_plano(tmp_path):
    assert _achados(tmp_path, "UNIT_SEGUNDO_PLANO", {
        "a.service": "[Service]\nType=forking\nPIDFile=/run/a.pid\n",
        "b.service": "[Service]\nType=simple\n"}) == [("a.service", 2), ("a.service", 3)]


def test_predicado_import_ciclico(tmp_path):
    assert _achados(tmp_path, "IMPORT_CICLICO", {
        "pkg/__init__.py": "",
        "pkg/a.py": "from . import b\n",
        "pkg/b.py": "import os\nfrom pkg import a\n",
        "pkg/c.py": "from . import a\n"}) == [("pkg/a.py", 1), ("pkg/b.py", 2)]


def test_predicado_duplicacao(tmp_path):
    bloco = "".join(f"    v{i} = carregar('{i}')\n" for i in range(9))
    achados = _achados(tmp_path, "DUPLICACAO", {
        "a.py": "def f():\n" + bloco,
        "b.py": "def g():\n" + bloco,
        "c.py": "def h():\n    return 1\n"})
    assert achados == [("a.py", 2), ("b.py", 2)]


def test_predicados_de_teste(tmp_path):
    fonte = {"tests/test_a.py": (
        "import time, pytest, shutil\n"
        "def test_a():\n"
        "    if not shutil.which('x'):\n"
        "        pytest.skip('sem x')\n"
        "    if time.time() > 0:\n"
        "        assert open('/srv/platafirma/casa/x')\n"),
        "prod.py": "import time\nT = time.time()\nC = '/srv/platafirma/casa'\n"}
    assert _achados(tmp_path, "TESTE_CONDICIONAL", fonte) == [("tests/test_a.py", 5)]
    assert _achados(tmp_path, "TESTE_ERRATICO", fonte) == [("tests/test_a.py", 5)]
    assert _achados(tmp_path, "TESTE_ESTADO_REAL", fonte) == [("tests/test_a.py", 6)]


def test_predicado_eval_shell(tmp_path):
    assert _achados(tmp_path, "EVAL_SHELL", {"a.sh": (
        "#!/bin/bash\n"
        "# eval aqui e comentario\n"
        "eval \"$cmd\"\n"
        "echo avaliar\n")}) == [("a.sh", 3)]


def test_todo_predicado_tem_caso(tmp_path):
    # predicado novo sem caso de teste quebra aqui
    sys.path.insert(0, str(HARNESS_ROOT / "bin"))
    from _lint.codigo import TODOS_PREDICADOS
    from _lint.leitura import LEITURAS
    fonte = Path(__file__).read_text()
    # BASH_SET_E e LINHAS_SHELL tem caso no teste de shell pela CLI (S6 e S14); as cinco de fila
    # dividem o caso de _modulos_de_fila
    sem_caso = [n for n in [*TODOS_PREDICADOS, *LEITURAS]
                if f'"{n}"' not in fonte and n not in ("BASH_SET_E", "LINHAS_SHELL")
                and not n.startswith("FILA_")]
    assert sem_caso == [], sem_caso


LISTA_RUFF_PADRAO = LISTA_CODIGO.replace(
    "| F1 | lote sem fila |",
    "| P19 | regra padrão do ruff | ruff | `ruff padrão` | aviso | Siga a regra. |\n| F1 | lote sem fila |")


def test_lint_codigo_ruff_padrao_soma_as_regras_do_ruff(tmp_path, acervo):
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    # F541 (f-string sem campo) esta no padrao do ruff e nao e nomeado pela lista
    (wt / "m.py").write_text("x = f'abc'\ndef f(a=[]):\n    return a\n")
    env_sem = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_CODIGO})}
    p = _rodar_lint("codigo", "mono", "m.py", env_extra=env_sem)
    assert "F541" not in p.stdout and "m.py:2: P1" in p.stdout, p.stdout + p.stderr
    env_com = {**env, **acervo(textos={"antipadroes-de-codigo": LISTA_RUFF_PADRAO})}
    p = _rodar_lint("codigo", "mono", "m.py", env_extra=env_com)
    assert "m.py:1: P19" in p.stdout and "F541" in p.stdout, p.stdout + p.stderr
    assert "m.py:2: P1" in p.stdout, p.stdout


def test_lint_codigo_predicado_candidato_diz_que_e_candidato(tmp_path, acervo):
    _precisa_ruff()
    wt, env = _wt(tmp_path)
    (wt / "t.py").write_text("import time\nwhile True:\n    try:\n        x = 1\n    except OSError:\n        time.sleep(1)\n")
    lista = LISTA_CODIGO.replace(
        "| F1 | lote sem fila |",
        "| R4 | repetição sem teto | SRE | `predicado REPETE_SEM_TETO` (candidata) | aviso | Fixe o teto. |\n"
        "| P98 | predicado que o lint não tem | fixture | `predicado NAO_EXISTE` | aviso | nada |\n"
        "| F1 | lote sem fila |")
    env = {**env, **acervo(textos={"antipadroes-de-codigo": lista})}
    p = _rodar_lint("codigo", "mono", "t.py", env_extra=env)
    assert "t.py:2: R4" in p.stdout and "candidata, confirme lendo" in p.stdout, p.stdout + p.stderr
    assert "NAO_EXISTE" in p.stderr, p.stderr


# ------------------------------------------------------------------ predicados de stack
# Um caso por detector que cruza arquivos: a forma em dois modulos aponta; num so, nao.


SERVIDOR = (
    "import subprocess\n"
    "@app.post('/conversoes')\n"
    "def converter(pedido):\n"
    "    return processar(pedido)\n"
    "def processar(pedido):\n"
    "    for _ in range(3):\n"
    "        try:\n"
    "            return subprocess.run(['docling'], timeout=900, check=True)\n"
    "        except subprocess.CalledProcessError:\n"
    "            pass\n")
CLIENTE = (
    "import requests\n"
    "def pedir(base, dados):\n"
    "    for _ in range(5):\n"
    "        try:\n"
    "            return requests.post(f'{base}/conversoes', data=dados, timeout=(5, 600))\n"
    "        except requests.RequestException:\n"
    "            pass\n")


def test_predicado_prazo_invertido_entre_servicos(tmp_path):
    assert _achados(tmp_path, "PRAZO_INVERTIDO", {"srv/api.py": SERVIDOR, "cli/cliente.py": CLIENTE}) == [
        ("cli/cliente.py", 5)]


def test_predicado_prazo_invertido_com_route_do_starlette_e_constante(tmp_path):
    # a forma do conversor: Route("/conversoes", tratador), prazo em constante de modulo
    servidor = ("import subprocess\nTETO_S = 900\n"
                "async def conversoes(pedido):\n    return subprocess.run(['docling'], timeout=TETO_S, check=True)\n"
                "rotas = [Route('/conversoes', conversoes, methods=['POST']), Route('/saude', conversoes)]\n")
    cliente = ("import requests\nPRAZO_S = 600\n"
               "def pedir(base, oid):\n    return requests.post(base + '/conversoes', timeout=PRAZO_S)\n"
               "def saude(base):\n    return requests.get(f'{base}/obras/{1}', timeout=PRAZO_S)\n")
    assert _achados(tmp_path, "PRAZO_INVERTIDO", {"srv/app.py": servidor, "cli/c.py": cliente}) == [
        ("cli/c.py", 4)]


def test_predicado_repeticao_em_camadas_pela_rota(tmp_path):
    assert _achados(tmp_path, "REPETICAO_EM_CAMADAS", {"srv/api.py": SERVIDOR, "cli/cliente.py": CLIENTE}) == [
        ("cli/cliente.py", 5)]


def test_predicado_listas_gemeas(tmp_path):
    assert _achados(tmp_path, "LISTAS_GEMEAS", {
        "a.py": "EXT = ['pdf', 'epub', 'docx', 'html', 'md']\n",
        "b.py": "FORMATOS = {'pdf', 'epub', 'docx', 'html', 'txt'}\n",
        "c.py": "CORES = ['azul', 'verde', 'roxo', 'preto']\n"}) == [("a.py", 1), ("b.py", 1)]


def test_predicado_idioma_da_stack(tmp_path):
    fonte = {f"m{i}.py": "import httpx\n" for i in range(5)}
    fonte["velho.py"] = "import requests\n"
    assert _achados(tmp_path, "IDIOMA_DA_STACK", fonte) == [("velho.py", 1)]


def test_predicado_forma_repetida(tmp_path):
    forma = "    return {'obra': o, 'estado': e, 'inicio': i, 'fim': f}\n"
    assert _achados(tmp_path, "FORMA_REPETIDA", {
        "a.py": "def a(o, e, i, f):\n" + forma + "def b(o, e, i, f):\n" + forma,
        "b.py": "def c(o, e, i, f):\n" + forma}) == [("a.py", 2), ("a.py", 4), ("b.py", 2)]


def test_predicado_reivindica_sem_trava(tmp_path):
    assert _achados(tmp_path, "REIVINDICA_SEM_TRAVA", {"a.py": (
        "def pega(cur):\n"
        "    cur.execute(\"UPDATE fila SET estado = 'em_execucao' WHERE id = %s\")\n"
        "def pega_bem(cur):\n"
        "    cur.execute(\"UPDATE fila SET estado = 'x' WHERE id = (SELECT id FROM fila FOR UPDATE SKIP LOCKED LIMIT 1)\")\n")}
    ) == [("a.py", 2)]


def test_predicado_concorrencia_sem_teto(tmp_path):
    assert _achados(tmp_path, "CONCORRENCIA_SEM_TETO", {"a.py": (
        "import threading, asyncio\n"
        "from concurrent.futures import ThreadPoolExecutor\n"
        "def a(itens):\n"
        "    with ThreadPoolExecutor() as ex:\n"
        "        pass\n"
        "    for i in itens:\n"
        "        threading.Thread(target=print).start()\n"
        "async def b(itens):\n"
        "    await asyncio.gather(*[f(i) for i in itens])\n")}) == [("a.py", 4), ("a.py", 6), ("a.py", 9)]


def test_predicado_corrotina_sem_await_e_cancela_thread(tmp_path):
    fonte = {"a.py": (
        "import asyncio\n"
        "async def grava():\n"
        "    pass\n"
        "async def a():\n"
        "    grava()\n"
        "    await grava()\n"
        "    await asyncio.wait_for(asyncio.to_thread(sum, [1]), 5)\n")}
    assert _achados(tmp_path, "CORROTINA_SEM_AWAIT", fonte) == [("a.py", 5)]
    assert _achados(tmp_path, "CANCELA_THREAD", fonte) == [("a.py", 7)]


def test_predicados_de_erro_e_saida(tmp_path):
    fonte = {"a.py": (
        "import sys\n"
        "def a(x):\n"
        "    try:\n"
        "        return int(x)\n"
        "    except ValueError:\n"
        "        return None\n"
        "def b(x):\n"
        "    try:\n"
        "        x()\n"
        "    except OSError:\n"
        "        return True\n"
        "def c(x):\n"
        "    try:\n"
        "        return int(x)\n"
        "    except ValueError as e:\n"
        "        raise SystemExit(f'x: {e}') from e\n")}
    assert _achados(tmp_path, "ERRO_VIRA_VAZIO", fonte) == [("a.py", 5)]
    assert _achados(tmp_path, "VERDE_NA_FALHA", fonte) == [("a.py", 11)]


def test_predicados_de_processo(tmp_path):
    fonte = {"a.py": (
        "import subprocess, time, json\n"
        "def a():\n"
        "    p = subprocess.Popen(['x'], close_fds=False)\n"
        "    q = subprocess.Popen(['y'])\n"
        "    q.wait()\n"
        "def servir():\n"
        "    while True:\n"
        "        time.sleep(1)\n"
        "def grava(estado_json, dado):\n"
        "    with open(estado_json, 'w') as f:\n"
        "        json.dump(dado, f)\n")}
    assert _achados(tmp_path, "FILHO_SEM_ESPERA", fonte) == [("a.py", 3)]
    assert _achados(tmp_path, "FD_HERDADO", fonte) == [("a.py", 3)]
    assert _achados(tmp_path, "SERVICO_SEM_SIGTERM", fonte) == [("a.py", 7)]
    assert _achados(tmp_path, "ESCRITA_NO_LUGAR", fonte) == [("a.py", 10)]


def test_predicados_de_fronteira(tmp_path):
    fonte = {"a.py": (
        "import subprocess, requests\n"
        "def a():\n"
        "    r = requests.get('http://x/y', timeout=5)\n"
        "    return r.json()\n"
        "def b():\n"
        "    r = requests.get('http://x/y', timeout=5)\n"
        "    r.raise_for_status()\n"
        "    return r.json()\n"
        "def c():\n"
        "    out = subprocess.run(['git', 'status'], capture_output=True, text=True, check=True).stdout\n"
        "    return out.splitlines()\n"
        "def d():\n"
        "    out = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=True)\n"
        "    return out.stdout.splitlines()\n"
        "@app.get('/obras')\n"
        "def listar(cur):\n"
        "    cur.execute('SELECT 1')\n"
        "    return cur.fetchall()\n")}
    assert _achados(tmp_path, "RESPOSTA_SEM_STATUS", fonte) == [("a.py", 3)]
    assert _achados(tmp_path, "SAIDA_RECORTADA", fonte) == [("a.py", 10)]
    assert _achados(tmp_path, "TRATADOR_NO_BANCO", fonte) == [("a.py", 17)]


def test_predicados_de_desenho_e_teste(tmp_path):
    preparo = "".join(f"    v{i} = {i}\n" for i in range(16))
    fonte = {
        "a.py": ("def ler(caminho, modo):\n    return abrir(caminho, modo)\n"
                 "def ler2(caminho):\n    return abrir(caminho, 'r')\n"
                 "import os\nMODO = os.environ.get('PYTEST_CURRENT_TEST')\n"
                 "def todos(cur, ids):\n    for i in ids:\n        cur.execute('SELECT 1 WHERE id=%s', (i,))\n"),
        "tests/test_a.py": "def test_a():\n" + preparo + "    assert v0 == 0\n"}
    assert _achados(tmp_path, "REPASSE", fonte) == [("a.py", 1)]
    assert _achados(tmp_path, "PREPARACAO_LONGA", fonte) == [("tests/test_a.py", 1)]
    assert _achados(tmp_path, "TESTE_EM_PRODUCAO", fonte) == [("a.py", 6)]
    assert _achados(tmp_path, "IDA_POR_ITEM", fonte) == [("a.py", 8)]


# ------------------------------------------------------------------ leitura (modelo local)
# O gerador junta a evidencia certa; o julgamento vem de um duble no lugar do modelo.


def _perguntas(tmp_path, nome_leitura, arquivos):
    from _lint.leitura import LEITURAS
    ctx = _ctx(tmp_path, arquivos)
    return list(LEITURAS[nome_leitura](ctx))


def test_leitura_instancias_divergentes_cruza_a_stack(tmp_path):
    perguntas = _perguntas(tmp_path, "INSTANCIAS_DIVERGENTES", {
        "a.py": "def a():\n    return Cliente(timeout=30, base='http://c')\n",
        "b.py": "def b():\n    return Cliente(timeout=600, base='http://c')\n",
        "c.py": "def c():\n    return Outro(n=1)\n"})
    (p,) = perguntas
    assert (p.arquivo, p.linha) == ("a.py", 2)
    assert "timeout" in p.questao and "base" not in p.questao.split("diferentes em")[1]
    assert "a.py:2" in p.evidencia and "b.py:2" in p.evidencia and "600" in p.evidencia


def test_leitura_inveja_deposito_comentario_e_temporal(tmp_path):
    inveja = "def pagar(self, e):\n    return e.a + e.b + e.c + e.d + e.f\n"
    muitos = "".join(f"def f{i}():\n    pass\n" for i in range(15))
    fonte = {"a.py": inveja, "dep.py": muitos,
             "c.py": "# soma um\nx = x + 1\n",
             **{f"pac/passo{i}.py": f'"""Passo {i}."""\n' for i in range(4)}}
    assert [(p.arquivo, p.linha) for p in _perguntas(tmp_path, "INVEJA_DE_DADOS", fonte)] == [("a.py", 1)]
    assert [p.arquivo for p in _perguntas(tmp_path, "ARQUIVO_DEPOSITO", fonte)] == ["dep.py"]
    (com,) = _perguntas(tmp_path, "COMENTARIO_REDUNDANTE", fonte)
    assert com.linhas_itens == (1,) and "soma um" in com.evidencia
    assert len(_perguntas(tmp_path, "DECOMPOSICAO_TEMPORAL", fonte)) == 1


def test_leitura_concorrencia_falha_fila_teste_e_rota(tmp_path):
    fonte = {"a.py": (
        "import requests\n"
        "from concurrent.futures import ThreadPoolExecutor\n"
        "def soma(xs):\n    return sum(x * x for x in xs)\n"
        "def disparar(lotes):\n"
        "    with ThreadPoolExecutor(4) as ex:\n"
        "        return list(ex.map(soma, lotes))\n"
        "def pedir(u):\n"
        "    for _ in range(3):\n"
        "        try:\n"
        "            return requests.get(u, timeout=5)\n"
        "        except requests.RequestException:\n"
        "            pass\n"
        "def listar(cur):\n"
        "    cur.execute('SELECT * FROM obra')\n"
        "    return cur.fetchall()\n"
        "FILA = 'INSERT INTO fila (alvo, estado) VALUES (%s, %s)'\n"
        "@app.get('/obras')\n"
        "def rota():\n    return {'n': 1}\n"),
        "tests/test_a.py": ("def test_a():\n    assert 1\n"
                            "def test_b(p):\n    assert p.stdout.splitlines()[0] == 'x'\n")}
    assert [p.arquivo for p in _perguntas(tmp_path, "THREAD_PARA_CPU", fonte)] == ["a.py"]
    assert [p.linha for p in _perguntas(tmp_path, "ESTADO_SEM_TRAVA", fonte)] == [3]
    assert [p.linha for p in _perguntas(tmp_path, "REPETE_PERMANENTE", fonte)] == [9]
    assert [p.linha for p in _perguntas(tmp_path, "CONSULTA_SEM_LIMITE", fonte)] == [15]
    assert all(len(_perguntas(tmp_path, f, fonte)) == 1 for f in (
        "FILA_RETOMA", "FILA_ESTADO_DAS_LINHAS", "FILA_IDEMPOTENTE", "FILA_TETO", "FILA_IDADE"))
    assert [p.linha for p in _perguntas(tmp_path, "TESTE_FRAGIL", fonte)] == [3]
    assert [p.linha for p in _perguntas(tmp_path, "ROTA_SEM_CONTRATO", fonte)] == [19]


def test_leituras_julgam_com_o_modelo_e_apontam_itens(tmp_path, monkeypatch):
    from _lint import codigo
    from _lint.leitura import Julgamento
    ctx = _ctx(tmp_path, {"c.py": "# soma um\nx = x + 1\n# porque o indice e base 1\ny = x\n"})
    monkeypatch.setattr(codigo, "perguntar", lambda p: Julgamento(True, "repete a linha", [1]))
    regua = codigo.Regua(rev=1, leituras={"COMENTARIO_REDUNDANTE": {"id": "D13", "o_que_fere": "x", "cura": "y"}})
    avisos = []
    (ap,) = codigo._leituras(ctx, regua, avisos, ligada=True)
    assert (ap.arquivo, ap.linha, ap.id) == ("c.py", 1, "D13") and "leitura do modelo" in ap.o_que_fere
    assert codigo._leituras(ctx, regua, avisos, ligada=False) == []
    assert "--leitura" in avisos[-1]


def test_leitura_para_com_aviso_quando_o_modelo_nao_responde(tmp_path, monkeypatch):
    from _lint import codigo
    from _lint.leitura import ModeloIndisponivel
    ctx = _ctx(tmp_path, {"c.py": "# soma um\nx = x + 1\n"})

    def fora(p):
        raise ModeloIndisponivel("recusado")
    monkeypatch.setattr(codigo, "perguntar", fora)
    regua = codigo.Regua(rev=1, leituras={"COMENTARIO_REDUNDANTE": {"id": "D13"}})
    avisos = []
    assert codigo._leituras(ctx, regua, avisos, ligada=True) == []
    assert "leitura parou" in avisos[-1]


def test_leitura_cache_pela_evidencia(tmp_path, monkeypatch):
    from _lint import leitura
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    p = leitura.Pergunta("a.py", 1, "q", "e")
    leitura._ao_cache(leitura._chave(p), leitura.Julgamento(True, "ok", [2]))
    monkeypatch.setattr(leitura.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert leitura.perguntar(p) == leitura.Julgamento(True, "ok", [2])
