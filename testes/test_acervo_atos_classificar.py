"""#3296: os atos de Classificar pelo estágio (arq:0119 §2, §4, §7), com a forma velha em aviso.

`acervo catalogar|definir|relacionar|desrelacionar|derivar|desderivar` chamam o ramo de bin/curar
que já fazia o trabalho; `acervo curar biblioteca --<opção>` segue rodando e avisa o ato novo.
Os casos que provam a rota usam validações de bin/curar que recusam antes de chamar o motor: só o
ramo certo dá aquela mensagem. O aviso sai em bin/acervo antes do exec, então o motor fica num
endereço fechado e o retorno do ramo não importa a esses casos.
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
    # bin/curar importa `requests`, que o venv de teste pode nao ter (o mesmo de test_curar_bancada)
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
precisa_curar = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def _acervo(*argv, sessao: str):
    # o aviso sai uma vez por sessao (trava em /tmp): cada chamada leva sessao nova
    # _acervo/curar roda por `env python3`: o python com requests vem primeiro no PATH
    caminho = os.environ.get("PATH", "")
    if PY:
        caminho = f"{Path(PY).parent}{os.pathsep}{caminho}"
    env = {**os.environ, "PATH": caminho, "PF_SESSAO_ID": f"{sessao}-{uuid.uuid4().hex}",
           "MOTOR_ACERVO_URL": MOTOR_FECHADO, "RAG_API_URL": MOTOR_FECHADO, "RAG_API_BASE": MOTOR_FECHADO}
    return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True,
                          env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)


def test_ajuda_lista_os_atos_de_classificar(tmp_path):
    r = _acervo("--ajuda", sessao=f"t-ajuda-{tmp_path.name}")
    assert r.returncode == 2
    for ato in ("catalogar     biblioteca obra", "definir       biblioteca conceito",
                "relacionar    biblioteca conceito", "desrelacionar biblioteca relacao",
                "derivar       biblioteca obra", "desderivar    biblioteca obra",
                "listar        biblioteca relacao <conceito>"):
        assert f"acervo {ato}" in r.stderr, ato
    # a crase solta na ajuda virava substituicao de comando (`continue com --offset N`)
    assert "only meaningful" not in r.stderr
    assert "`continue com --offset N`" in r.stderr


@precisa_curar
def test_relacionar_ajuda_traz_a_cartilha(tmp_path):
    r = _acervo("relacionar", "biblioteca", "conceito", "--ajuda", sessao=f"t-cart-{tmp_path.name}")
    assert r.returncode == 0, r.stderr
    assert "cartilha de --relacionar" in r.stdout


def test_particao_ou_entidade_errada_recusa_com_a_forma(tmp_path):
    for argv, forma in (
        (("catalogar", "casa", "obra", "x"), "acervo catalogar biblioteca obra"),
        (("definir", "biblioteca", "obra", "x"), "acervo definir biblioteca conceito"),
        (("desrelacionar", "biblioteca", "conceito", "7"), "acervo desrelacionar biblioteca relacao"),
    ):
        r = _acervo(*argv, sessao=f"t-forma-{tmp_path.name}")
        assert r.returncode == 2, (argv, r.stderr)
        assert f"a forma e `{forma}" in r.stderr, (argv, r.stderr)


@pytest.mark.parametrize("argv, ramo", [
    (("catalogar", "biblioteca", "obra", "x", "--trata-de", "a", "--remover-trata-de", "b"),
     "use apenas uma das opções de conceitos"),
    (("definir", "biblioteca", "conceito", "x", "--renomear", "y", "--pai", "z"),
     "--renomear não combina com"),
    (("derivar", "biblioteca", "obra", "x"), "--derivar exige --de"),
    (("desderivar", "biblioteca", "obra", "x"), "--desderivar exige --de"),
])
@precisa_curar
def test_ato_novo_cai_no_ramo_de_curar_sem_aviso(tmp_path, argv, ramo):
    r = _acervo(*argv, sessao=f"t-rota-{tmp_path.name}")
    assert r.returncode == 2, r.stderr
    assert ramo in r.stderr
    assert "forma vigente" not in r.stderr


@pytest.mark.parametrize("opcoes, nova", [
    (("--reclassificar", "--obra", "x", "--dominio", "d"), "acervo catalogar biblioteca obra [<obra>]"),
    (("--conceito", "x", "--renomear", "y", "--pai", "z"), "acervo definir biblioteca conceito <slug>"),
    (("--relacionar", "a", "b", "--tipo", "generica"), "acervo relacionar biblioteca conceito <de> <para>"),
    (("--relacoes", "a"), "acervo listar biblioteca relacao <conceito>"),
    (("--desrelacionar", "7"), "acervo desrelacionar biblioteca relacao <id>"),
    (("--derivar", "x"), "acervo derivar biblioteca obra <obra> --de <origem>"),
    (("--derivacoes", "x"), "acervo listar biblioteca derivacao <obra>"),
    (("--desderivar", "x"), "acervo desderivar biblioteca obra <obra> --de <origem>"),
])
def test_forma_velha_avisa_o_ato_novo(tmp_path, opcoes, nova):
    r = _acervo("curar", "biblioteca", *opcoes, sessao=f"t-velha-{tmp_path.name}")
    assert f"`acervo curar biblioteca {next(o for o in opcoes if o in _VELHAS)}` e a forma vigente" in r.stderr, r.stderr
    assert f"a conforme (arq:0119 §2) e `{nova}`" in r.stderr, r.stderr
    assert "nenhuma ação especificada" not in r.stderr


_VELHAS = {"--reclassificar", "--conceito", "--relacionar", "--relacoes", "--desrelacionar",
           "--derivar", "--derivacoes", "--desderivar"}


def test_forma_velha_implicita_avisa_reclassificar(tmp_path):
    r = _acervo("curar", "biblioteca", "--obra", "x", "--dominio", "d", sessao=f"t-impl-{tmp_path.name}")
    assert "`acervo curar biblioteca --reclassificar` e a forma vigente" in r.stderr, r.stderr


@pytest.mark.parametrize("opcoes", [
    ("--situacao", "x"),
    ("--expurgar", "x"),
    ("--promover", "x"),
    ("--reextrair", "x", "--obra", "x"),
    ("--registrar-obra", "Titulo"),
])
def test_opcao_de_outro_estagio_nao_avisa_classificar(tmp_path, opcoes):
    r = _acervo("curar", "biblioteca", *opcoes, sessao=f"t-outro-{tmp_path.name}")
    assert "arq:0119 §2" not in r.stderr, r.stderr
