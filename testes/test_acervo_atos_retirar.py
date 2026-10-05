"""#3298: os atos de Retirar pelo estágio (arq:0119 §2, §9), com a forma velha em aviso.

`acervo retirar|restaurar|apagar biblioteca obra` chamam `--expurgar|--restaurar|--apagar` de bin/curar;
`acervo retirar|restaurar casa revisao` chamam `ocultar-revisao|mostrar-revisao` de _acervo/wiki;
`acervo recolher|repor biblioteca espelho` chamam `--espelhos --expurgar|--restaurar`. A forma velha
segue rodando e avisa o ato novo. Mesmo desenho do teste de Transcrever: o motor fica num endereço
fechado, e o que se prova é a rota e o aviso.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"
CURAR = RAIZ / "bin" / "curar"
MOTOR_FECHADO = "http://127.0.0.1:9"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()


def _acervo(*argv, sessao: str):
    caminho = os.environ.get("PATH", "")
    if PY:
        caminho = f"{Path(PY).parent}{os.pathsep}{caminho}"
    env = {**os.environ, "PATH": caminho, "PF_SESSAO_ID": f"{sessao}-{uuid.uuid4().hex}",
           "MOTOR_ACERVO_URL": MOTOR_FECHADO, "RAG_API_URL": MOTOR_FECHADO, "RAG_API_BASE": MOTOR_FECHADO}
    return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True,
                          env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)


def test_ajuda_lista_os_atos_de_retirar(tmp_path):
    r = _acervo("--ajuda", sessao=f"t-ajuda-{tmp_path.name}")
    assert r.returncode == 2
    for ato in ("retirar       biblioteca obra <obra>", "restaurar     biblioteca obra <obra>",
                "apagar        biblioteca obra <obra>", "retirar       casa revisao <revid>",
                "restaurar     casa revisao <revid>", "recolher      biblioteca espelho",
                "repor         biblioteca espelho"):
        assert f"acervo {ato}" in r.stderr, ato


def test_cabecalho_declara_a_capacidade():
    cab = ACERVO.read_text(encoding="utf-8").splitlines()[6]
    for ato in ("retirar", "restaurar", "apagar"):
        assert f"{ato} (escrita, retirada)" in cab, ato
    for ato in ("recolher", "repor"):
        assert f"{ato} (escrita, transcricao)" in cab, ato


@pytest.mark.parametrize("argv, forma", [
    (("retirar", "biblioteca", "conceito", "x"), "acervo retirar biblioteca obra <obra>"),
    (("restaurar", "casa", "obra", "x"), "acervo restaurar biblioteca obra <obra>"),
    (("apagar", "casa", "revisao", "1"), "acervo apagar biblioteca obra <obra>"),
    (("recolher", "biblioteca", "obra", "x"), "acervo recolher biblioteca espelho [<obra>]"),
    (("repor", "casa", "espelho"), "acervo repor biblioteca espelho [<obra>]"),
])
def test_particao_ou_entidade_errada_recusa_com_a_forma(tmp_path, argv, forma):
    r = _acervo(*argv, sessao=f"t-forma-{tmp_path.name}")
    assert r.returncode == 2, (argv, r.stderr)
    assert f"a forma e `{forma}" in r.stderr, (argv, r.stderr)


@pytest.mark.parametrize("argv", [
    ("retirar", "biblioteca", "obra", "x"),
    ("restaurar", "biblioteca", "obra", "x"),
    ("apagar", "biblioteca", "obra", "x"),
    ("recolher", "biblioteca", "espelho"),
    ("repor", "biblioteca", "espelho", "x"),
])
def test_ato_novo_passa_do_despachante_sem_aviso(tmp_path, argv):
    r = _acervo(*argv, sessao=f"t-rota-{tmp_path.name}")
    assert "a forma e `" not in r.stderr, r.stderr
    assert "combinacao nao servida" not in r.stderr, r.stderr
    assert "desconhecido" not in r.stderr, r.stderr
    assert "forma vigente" not in r.stderr, r.stderr
    # chegou a bin/curar, que tentou o motor fechado (e não recusou a chamada por argumento)
    assert "argumento que o verbo não lê" not in r.stderr, r.stderr


@pytest.mark.parametrize("opcoes, velha, nova", [
    (("--expurgar", "x"), "--expurgar", "acervo retirar biblioteca obra <obra>"),
    (("--restaurar", "x"), "--restaurar", "acervo restaurar biblioteca obra <obra>"),
    (("--apagar", "x"), "--apagar", "acervo apagar biblioteca obra <obra>"),
    (("--expurgar", "--espelhos"), "--expurgar --espelhos", "acervo recolher biblioteca espelho [<obra>]"),
    (("--restaurar", "--espelhos", "x"), "--restaurar --espelhos", "acervo repor biblioteca espelho [<obra>]"),
])
def test_forma_velha_avisa_o_ato_novo(tmp_path, opcoes, velha, nova):
    r = _acervo("curar", "biblioteca", *opcoes, sessao=f"t-velha-{tmp_path.name}")
    assert f"`acervo curar biblioteca {velha}` e a forma vigente" in r.stderr, r.stderr
    assert f"a conforme (arq:0119 §9) e `{nova}`" in r.stderr, r.stderr


def test_curar_casa_revisao_avisa_retirar(tmp_path):
    r = _acervo("curar", "casa", "revisao", "--ajuda", sessao=f"t-rev-{tmp_path.name}")
    # --ajuda universal sai antes do despacho; a prova do aviso fica no texto do despachante
    assert r.returncode == 2
    texto = ACERVO.read_text(encoding="utf-8")
    assert 'avisa "acervo curar casa revisao" "acervo retirar casa revisao <revid>"' in texto


def test_wiki_tem_a_volta_da_revisao():
    wiki = (RAIZ / "bin" / "_acervo" / "wiki").read_text(encoding="utf-8")
    assert 'sub.add_parser("mostrar-revisao"' in wiki
    assert '"show": "content|comment"' in wiki


def test_plano_de_retirar_e_restaurar_nomeia_o_que_muda():
    # o aceite da #3298: o plano seco nomeia catálogo, impressão e índice
    texto = CURAR.read_text(encoding="utf-8")
    ini = texto.index("def acao_expurgar(")
    fim = texto.index("def acao_apagar(")
    corpo = texto[ini:fim]
    for termo in ("catálogo :", "impressão:", "índice   :"):
        assert corpo.count(termo) >= 2, termo
    assert "/retirada\"" in corpo and "/restauracao\"" in corpo
