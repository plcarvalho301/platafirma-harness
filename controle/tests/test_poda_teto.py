# componente: componente:poda
"""Testes do teto rígido de saída na poda (DT 1443)."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from poda.poda import corta, podar_texto


def test_corta_respeita_cap_exato_com_alca_longa() -> None:
    alca = "/tmp/derrames/sessao-teste-longa/" + "x" * 180 + "/g00001-stdout.txt"
    texto = "".join(f"linha {i}: teste com acentuação áéíóú\n" for i in range(120))
    cap = 500
    servido, meta = corta(texto, cap, alca=alca, offset_exato=True)
    assert meta["cortado"] is True
    assert len(servido.encode("utf-8")) <= cap

    servido_cauda, meta_cauda = corta(texto, cap, cauda=True, alca=alca)
    assert meta_cauda["cortado"] is True
    assert len(servido_cauda.encode("utf-8")) <= cap


def test_podar_texto_corta_acima_do_teto_mesmo_em_perfil_cosmetico(tmp_path: Path) -> None:
    texto = "".join(f"item-{i:04d}: resultado extenso da consulta {i}\n" for i in range(80))
    cap = 600
    servido, meta = podar_texto(
        texto,
        tool="busca",
        alca="busca buscar teste",
        sessao_id="s-dt1443",
        derrame_dir=tmp_path,
        cap=cap,
        cosmetica=True,
    )
    assert meta["modo"] == "corte"
    assert meta["bytes_servidos"] <= cap
    assert len(servido.encode("utf-8")) <= cap
    assert meta.get("alca")
    assert Path(meta["alca"]).is_file()
