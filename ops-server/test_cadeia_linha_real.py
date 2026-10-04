"""A linha da cadeia leva o que o item disse, mesmo quando a poda serviu o corpo como igual
(balde #2856, linha 183).

Medido em 04/10/2026: `malote(encadeado=true)` repetido devolvia em `cadeia.itens[].linha`
o marcador «[igual ao giro N ...]» e, na parada, `motivo` com o mesmo marcador. O corpo
podado e certo (arq:0101); a linha que a cadeira le para decidir sem abrir o item, nao.

Cobre:
- lote.resumo_cadeia: com `brutos` e poda `igual`, linha e motivo saem do texto cru;
  sem `brutos`, ou com poda de outro modo, nada muda.
- a fiacao da porta: `malote` repassa o stdout cru de cada item a `lote.itera`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
PDP_CODE_DIR = HARNESS_DIR / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import lote as _lote
import server as s

MARCADOR = "[igual ao giro 1 \u2014 sha 3eab777aa710, 185 bytes n\u00e3o reenviados]"


def _item(exit_code, texto, modo=None):
    r = {"exit_code": exit_code,
         "stdout": {"texto": texto, "bytes_total": len(texto), "truncado": False}}
    if modo:
        r["poda"] = {"ato": "repo", "modo": modo, "ledger": modo}
    return r


def test_resumo_usa_a_linha_real_quando_a_poda_serviu_igual():
    res = [_item(0, MARCADOR, "igual"), _item(4, MARCADOR, "igual")]
    brutos = ["\n  primeira linha real\nsegunda", "negado pela politica\nresto"]
    c = _lote.resumo_cadeia(res, 1, brutos)
    assert c["itens"][0]["linha"] == "primeira linha real"
    assert c["itens"][1]["linha"] == "negado pela politica"
    assert c["motivo"] == "parou em 1: negado pela politica"


def test_resumo_sem_brutos_ou_sem_poda_igual_fica_como_era():
    res = [_item(0, MARCADOR, "igual"), _item(0, "texto servido", "diff_maior")]
    assert _lote.resumo_cadeia(res, None)["itens"][0]["linha"] == MARCADOR
    c = _lote.resumo_cadeia(res, None, ["cru a", "cru b"])
    assert c["itens"][1]["linha"] == "texto servido"
    # texto cru vazio: cai no que o resultado diz
    assert _lote.resumo_cadeia(res, None, ["", ""])["itens"][0]["linha"] == MARCADOR


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_malote_encadeado_leva_a_linha_real_com_corpo_podado():
    saidas = {"a": (0, "a saiu 0\nsegunda linha"), "b": (4, "b saiu 4\nresto")}

    def fake_run(argv, stdin, timeout, ident, prazo=None):
        e, t = saidas[argv[1]]
        return {"exit_code": e, "stdout": {"texto": t, "bytes_total": len(t), "truncado": False}}

    def fake_serve(r, **kw):
        # o que a poda faz na segunda chamada igual: o corpo vira marcador
        out = dict(r)
        out["stdout"] = {"texto": MARCADOR, "bytes_total": r["stdout"]["bytes_total"],
                         "truncado": False}
        out["poda"] = {"ato": "repo", "modo": "igual", "ledger": "igual"}
        return out

    with patch("server.SLUGS_SERVIDOS", {"repo"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo"}), \
         patch("server._autoriza", return_value=None), \
         patch("server._audit"), \
         patch("server._serve", side_effect=fake_serve), \
         patch("server._run_verbo_blocking", side_effect=fake_run):
        res = await s.malote(commands=["repo a", "repo b"], encadeado=True)

    assert res["lote"][0]["stdout"]["texto"] == MARCADOR      # o corpo segue podado
    assert res["cadeia"]["itens"][0]["linha"] == "a saiu 0"
    assert res["cadeia"]["itens"][1]["linha"] == "b saiu 4"
    assert res["cadeia"]["motivo"] == "parou em 1: b saiu 4"
