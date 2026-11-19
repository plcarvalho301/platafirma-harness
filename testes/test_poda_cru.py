"""arq:0101, invariante (ii): poda que tira conteudo deixa alca de restauracao.

Testa `lib/poda/poda.py` (substituto da poda antiga de ops-server) no venv do harness,
sem subir a porta.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PODA = Path(__file__).resolve().parent.parent / "lib" / "poda"
if str(_PODA) not in sys.path:
    sys.path.insert(0, str(_PODA))

import poda as _p  # noqa: E402

_SESSAO = "00000000-0000-4000-8000-000000000001"
_PROSA = " ".join(f"palavra{i % 7} de um log sem quebra" for i in range(120))


def test_linha_longa_abaixo_do_teto_deixa_o_cru_e_diz_onde(tmp_path):
    servir, meta = _p.podar_texto(
        _PROSA,
        tool="tarefas",
        alca="tarefas:listar",
        sessao_id=_SESSAO,
        derrame_dir=tmp_path,
        cap=50_000,
    )
    assert "blob" in meta["lavado"]
    assert "cru" in meta
    cru = Path(meta["cru"])
    assert cru.is_file()
    assert cru.read_text(encoding="utf-8") == _PROSA
    assert len(servir) < len(_PROSA)


def test_corte_acima_do_teto_grava_alca_com_conteudo_inteiro(tmp_path):
    grande = "\n".join(f"linha {i:04d} de conteudo util" for i in range(400))
    servir, meta = _p.podar_texto(
        grande,
        tool="repo",
        alca="repo:diff",
        sessao_id=_SESSAO,
        derrame_dir=tmp_path,
        cap=1024,
    )
    assert meta["modo"] == "corte"
    assert meta["bytes_omitidos"] > 0
    alca = Path(meta["alca"])
    assert alca.is_file()
    assert alca.read_text(encoding="utf-8") == grande
    assert len(servir.encode("utf-8")) <= 2048


def test_regime_cosmetico_serve_inteiro_e_grava_derrame_acima_do_cap(tmp_path):
    grande = "\n".join(f"resultado {i:04d}" for i in range(200))
    servir, meta = _p.podar_texto(
        grande,
        tool="busca",
        alca="busca:buscar",
        sessao_id=_SESSAO,
        derrame_dir=tmp_path,
        cap=512,
        cosmetica=True,
    )
    assert meta["perfil"] == "cosmetica"
    assert meta["modo"] == "derrame"
    assert "resultado 0199" in servir
    assert Path(meta["alca"]).read_text(encoding="utf-8") == grande
