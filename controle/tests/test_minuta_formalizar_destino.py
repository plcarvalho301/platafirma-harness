"""Contrato do destino de `minuta formalizar` (arq:0115 §3.2 e §4; spec verbo-minuta §5; #3328).

Prova: a série de ADR é a das ADRs da casa (arq, ont, org, seg, infra, integracao) e o número
do ADR novo é o maior número da pasta da série mais um, contando só `NNNN-*.md`; pasta que não
existe começa em 1. O percurso inteiro, contra git real, está em
test_contrato_casa_direto_em_main.py. Não prova: o forge de verdade.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

FORMALIZAR = Path(__file__).resolve().parents[2] / "bin" / "_minuta" / "formalizar"


def _mod():
    loader = importlib.machinery.SourceFileLoader("formalizar_destino_mod", str(FORMALIZAR))
    spec = importlib.util.spec_from_loader("formalizar_destino_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _tocar(pasta: Path, *nomes: str) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in nomes:
        (pasta / nome).write_text("# x\n", encoding="utf-8")


def test_series_sao_as_de_adr_da_casa():
    assert _mod().SERIES == ("arq", "ont", "org", "seg", "infra", "integracao")


def test_numero_comeca_em_1_quando_a_serie_nao_existe(tmp_path):
    assert _mod().proximo_numero(str(tmp_path / "adr" / "org")) == 1


def test_numero_e_o_maior_da_serie_mais_um_mesmo_com_buraco(tmp_path):
    pasta = tmp_path / "adr" / "arq"
    _tocar(pasta, "0001-a.md", "0005-b.md", "0003-c.md")
    assert _mod().proximo_numero(str(pasta)) == 6


def test_numero_ignora_o_que_nao_e_adr_numerado(tmp_path):
    pasta = tmp_path / "adr" / "arq"
    _tocar(pasta, "README.md", "12-curto.md", "0007.md", "0009-nao-md.txt")
    assert _mod().proximo_numero(str(pasta)) == 1
