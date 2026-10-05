"""#3297: os atos de Transcrever pelo estágio (arq:0119 §2, §5), com a forma velha em aviso.

`acervo espelhar|recortar|promover|julgar|converter` e `acervo ler biblioteca lote` chamam a opção
de bin/curar que já fazia o trabalho; `acervo curar biblioteca --reextrair|--recortar|--promover|
--rejulgar` segue rodando e avisa o ato novo. O aviso sai em bin/acervo antes do exec, então o
motor fica num endereço fechado: o que se prova é a rota e o aviso, não o retorno do motor.
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
MOTOR_FECHADO = "http://127.0.0.1:9"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()


def _acervo(*argv, sessao: str):
    # o aviso sai uma vez por sessao (trava em /tmp): cada chamada leva sessao nova
    caminho = os.environ.get("PATH", "")
    if PY:
        caminho = f"{Path(PY).parent}{os.pathsep}{caminho}"
    env = {**os.environ, "PATH": caminho, "PF_SESSAO_ID": f"{sessao}-{uuid.uuid4().hex}",
           "MOTOR_ACERVO_URL": MOTOR_FECHADO, "RAG_API_URL": MOTOR_FECHADO, "RAG_API_BASE": MOTOR_FECHADO}
    return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True,
                          env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)


def test_ajuda_lista_os_atos_de_transcrever(tmp_path):
    r = _acervo("--ajuda", sessao=f"t-ajuda-{tmp_path.name}")
    assert r.returncode == 2
    for ato in ("espelhar      biblioteca obra <obra>", "espelhar      biblioteca lote",
                "ler           biblioteca lote <lote>", "recortar      biblioteca obra <obra>",
                "promover      biblioteca obra <obra> --impressao <id>", "julgar        biblioteca lote",
                "converter     biblioteca obra"):
        assert f"acervo {ato}" in r.stderr, ato


def test_cabecalho_declara_a_capacidade(tmp_path):
    cab = ACERVO.read_text(encoding="utf-8").splitlines()[6]
    for ato in ("espelhar", "recortar", "promover", "julgar", "converter"):
        assert f"{ato} (escrita, transcricao)" in cab, ato


@pytest.mark.parametrize("argv, forma", [
    (("espelhar", "casa", "obra", "x"), "acervo espelhar biblioteca obra"),
    (("espelhar", "biblioteca", "conceito", "x"), "acervo espelhar biblioteca obra|lote"),
    (("recortar", "biblioteca", "lote"), "acervo recortar biblioteca obra"),
    (("promover", "casa", "obra", "x"), "acervo promover biblioteca obra"),
    (("julgar", "biblioteca", "obra", "x"), "acervo julgar biblioteca lote"),
    (("converter", "biblioteca", "lote"), "acervo converter biblioteca obra"),
])
def test_particao_ou_entidade_errada_recusa_com_a_forma(tmp_path, argv, forma):
    r = _acervo(*argv, sessao=f"t-forma-{tmp_path.name}")
    assert r.returncode == 2, (argv, r.stderr)
    assert f"a forma e `{forma}" in r.stderr, (argv, r.stderr)


def test_converter_sem_bancada_recusa(tmp_path):
    r = _acervo("converter", "biblioteca", "obra", "a,b", sessao=f"t-conv-{tmp_path.name}")
    assert r.returncode == 2
    assert "falta --bancada" in r.stderr


@pytest.mark.parametrize("argv", [
    ("espelhar", "biblioteca", "obra", "x"),
    ("espelhar", "biblioteca", "lote"),
    ("recortar", "biblioteca", "obra", "x"),
    ("promover", "biblioteca", "obra", "x", "--impressao", "y"),
    ("julgar", "biblioteca", "lote"),
    ("ler", "biblioteca", "lote", "abc"),
])
def test_ato_novo_passa_do_despachante_sem_aviso(tmp_path, argv):
    r = _acervo(*argv, sessao=f"t-rota-{tmp_path.name}")
    assert "a forma e `" not in r.stderr, r.stderr
    assert "combinacao nao servida" not in r.stderr, r.stderr
    assert "desconhecido" not in r.stderr, r.stderr
    assert "forma vigente" not in r.stderr, r.stderr


@pytest.mark.parametrize("opcoes, velha, nova", [
    (("--reextrair", "x"), "--reextrair", "acervo espelhar biblioteca obra <obra>"),
    (("--reextrair", "--lote"), "--reextrair --lote", "acervo espelhar biblioteca lote"),
    (("--reextrair", "--lote", "--relatorio", "abc"), "--reextrair --lote --relatorio",
     "acervo ler biblioteca lote <lote>"),
    (("--reextrair", "a,b", "--bancada", "/tmp/nada"), "--reextrair --bancada",
     "acervo converter biblioteca obra <ids> --bancada <pasta>"),
    (("--recortar", "x"), "--recortar", "acervo recortar biblioteca obra <obra>"),
    (("--promover", "x", "--impressao", "y"), "--promover",
     "acervo promover biblioteca obra <obra> --impressao <id>"),
    (("--rejulgar", "--lote"), "--rejulgar --lote", "acervo julgar biblioteca lote"),
])
def test_forma_velha_avisa_o_ato_novo(tmp_path, opcoes, velha, nova):
    r = _acervo("curar", "biblioteca", *opcoes, sessao=f"t-velha-{tmp_path.name}")
    assert f"`acervo curar biblioteca {velha}` e a forma vigente" in r.stderr, r.stderr
    assert f"a conforme (arq:0119 §2) e `{nova}`" in r.stderr, r.stderr


def test_espelhos_de_retirar_nao_avisa_transcrever(tmp_path):
    # `--expurgar|--restaurar --espelhos` avisa `recolher|repor` (#3298), nunca um ato de Transcrever
    r = _acervo("curar", "biblioteca", "--expurgar", "--espelhos", sessao=f"t-esp-{tmp_path.name}")
    assert "arq:0119 §2" not in r.stderr, r.stderr
