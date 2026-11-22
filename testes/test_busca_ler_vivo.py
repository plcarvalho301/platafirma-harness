# componente: componente:verbo-busca
"""Story 4426: o ato ler do verbo busca contra o banco casa e a release servida (degrau rodada).

Roda o executável como a porta o roda: o retrato abre o banco casa pelo docker, com o papel
analise_leitura, e o arquivo sai da release em /opt/platafirma/current/casa. Os casos puros, com o
retrato falso, estão em test_busca_ler.py.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"
CASA = Path("/opt/platafirma/current/casa")


def _executar(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BIN), "ler", *args], capture_output=True, text=True,
                          timeout=30, check=False)


def _blob(p: Path) -> str:
    dados = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(dados) + dados).hexdigest()


def test_capacidade_busca_le_a_referencia_com_o_sha_do_blob() -> None:
    r = _executar("capacidade:busca")
    arq = CASA / "referencias/instancias/capacidade/busca.md"
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\n", 1)[0].startswith(f"capacidade:busca · versão {_blob(arq)} · ")


def test_framework_da_ontologia_le_o_gabarito() -> None:
    r = _executar("framework da ontologia")
    arq = CASA / "instancias/gabarito/framework-da-ontologia.md"
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith(f"gabarito:framework-da-ontologia · versão {_blob(arq)} · inteiro\n")
    assert r.stdout.split("\n", 1)[1] == arq.read_text(encoding="utf-8")


@pytest.mark.parametrize("chave", ["sessao", "sessao:"])
def test_sessao_le_a_ficha_da_classe(chave: str) -> None:
    r = _executar(chave)
    assert r.returncode == 0, r.stderr
    primeira = r.stdout.split("\n", 1)[0]
    assert primeira.startswith("shape:sessao · versão ")
    assert primeira.endswith("objeto lido: a ficha da classe sessao")


def test_caminho_solto_sai_2_com_a_chave_em_proximo() -> None:
    r = _executar("/srv/platafirma/casa/x.md")
    assert r.returncode == 2 and r.stdout == ""
    assert r.stderr.startswith("codigo: caminho-solto-recusado")
    assert r.stderr.rstrip().endswith("proximo: busca ler x")
