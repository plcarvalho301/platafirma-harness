"""arq:0101, invariante (ii): poda que tira conteudo deixa alca de restauracao.

`poda.py` nao conhece FastMCP nem rede, e por isso roda aqui, no venv do harness, sem
subir a porta. O par deste teste em `ops-server/_ensaio.py` cobre o lado do `server.py`
(o escopo `cosmetica@ato` decidido pelo argv), que so importa no venv do ops-server.

Medido em 18/09 (carta do arquiteto a dados): `motor rag buscar` caiu fora do regime
cosmetico, a janela de linha longa serviu 289 de 13 kB, e o `sha=` do marcador era alca
morta — abaixo do teto o cru nao derramava, e nada na porta desreferencia sha.
"""
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops-server"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import poda as _p  # noqa: E402

_SESSAO = "00000000-0000-4000-8000-000000000001"
_LINHA = '{"fontes":[' + ",".join(f'{{"n":{i},"trecho":"conteudo do trecho {i}"}}'
                                  for i in range(1, 40)) + "]}"


def _args(**extra):
    base = {"cap": 50_000, "cauda": False, "alca": "tarefas:listar --json",
            "sessao_id": _SESSAO, "giro": 1, "tool": "tarefas", "ledger": None,
            "nome_derrame": "g00001-stdout.txt"}
    base.update(extra)
    return base


def test_linha_longa_abaixo_do_teto_deixa_o_cru_e_diz_onde(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    assert len(_LINHA) > _p.LINHA_LONGA
    fora, meta = _p.poda_texto(_LINHA, **_args())
    assert "<linha longa" in fora and "blob" in meta["lavado"]
    assert Path(meta["cru"]).read_text(encoding="utf-8") == _LINHA
    humana = _p.linha_humana(meta)
    assert meta["cru"] in humana and "saiu do retorno" in humana


def test_regime_cosmetico_serve_a_linha_inteira_e_nao_derrama(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fora, meta = _p.poda_texto(_LINHA, cosmetica=True, **_args(tool="motor"))
    assert fora == _LINHA and meta["lavado"] == [] and "cru" not in meta
    assert not list(tmp_path.rglob("*.txt"))


def test_lavagem_que_so_tira_ruido_nao_anuncia_perda(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fora, meta = _p.poda_texto("a\n\n\n\nb", **_args())
    assert meta["lavado"] == ["branco"] and "cru" not in meta
    assert _p.linha_humana(meta) == "poda: lavado (branco)"


def test_acima_do_teto_o_corte_reusa_o_mesmo_cru(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    # sem digito e sem repeticao consecutiva: nem molde nem `linha x N` encolhem o texto
    texto = _LINHA + "\n" + "\n".join("abcdefghij"[i % 10] * (i % 7 + 3) + " conteudo " + "y" * 40
                                     for i in range(200))
    fora, meta = _p.poda_texto(texto, **_args(cap=2_000))
    assert meta["modo"] == "corte" and meta["alca"] == meta["cru"]
    assert len(list(tmp_path.rglob("g00001-stdout.txt"))) == 1
