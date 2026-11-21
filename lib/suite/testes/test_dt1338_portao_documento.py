# componente: componente:suite
"""DT 1338: portão da main aprova repositório de esteira documento sem suíte de código."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIB_RAIZ = Path(__file__).resolve().parents[2]
if str(LIB_RAIZ) not in sys.path:
    sys.path.insert(0, str(LIB_RAIZ))

from suite.portao import avaliar_portao


def test_dt1338_portao_aprova_repositorio_esteira_documento_sem_suite_de_codigo(tmp_path: Path) -> None:
    venvs = tmp_path / "venvs.json"
    venvs.write_text(
        json.dumps(
            {
                "repositorios": {
                    "platafirma-casa": {"esteira": "documento"},
                    "platafirma-casa-espelho": {"esteira": "documento"},
                    "platafirma-core": {"esteira": "codigo"},
                }
            }
        ),
        encoding="utf-8",
    )
    pasta_vereditos = tmp_path / "vereditos"
    pasta_vereditos.mkdir()

    for repo in ("platafirma-casa", "platafirma-casa-espelho"):
        dec = avaliar_portao(
            repo,
            mudanca="arvore-doc-1",
            base="arvore-main-1",
            pasta_vereditos=pasta_vereditos,
            caminho_venvs=venvs,
        )
        assert dec.aprovado is True
        assert dec.categoria == "verde"
        assert dec.codigo_saida == 0
        assert "esteira documento" in dec.mensagem

    dec_cod = avaliar_portao(
        "platafirma-core",
        mudanca="arvore-cod-1",
        base="arvore-main-1",
        pasta_vereditos=pasta_vereditos,
        caminho_venvs=venvs,
    )
    assert dec_cod.aprovado is False
    assert dec_cod.categoria == "falta-de-rodada"
    assert dec_cod.codigo_saida == 1
