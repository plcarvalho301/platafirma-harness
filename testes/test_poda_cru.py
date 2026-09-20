"""arq:0101, invariante (ii): poda que tira conteudo deixa alca de restauracao.

`poda.py` nao conhece FastMCP nem rede, e por isso roda aqui, no venv do harness, sem
subir a porta. O par deste teste em `ops-server/_ensaio.py` cobre o lado do `server.py`
(o escopo `cosmetica@ato` decidido pelo argv), que so importa no venv do ops-server.

Medido em 18/09 (carta do arquiteto a dados): `motor rag buscar` caiu fora do regime
cosmetico, a janela de linha longa serviu 289 de 13 kB, e o `sha=` do marcador era alca
morta — abaixo do teto o cru nao derramava, e nada na porta desreferencia sha.

Medido em 20/09 (carta da gestao, fita eedd4c14): a forma curta `motor buscar "..."`
caiu fora do escopo de novo, e `read_file` no cru janelava igual — a alca existia e nao
abria. Duas guardas novas, as duas pelo CONTEUDO e nao pela forma da chamada: JSON
valido em linha unica nao e blob, e `read_file` nunca janela.
"""
import json
import sys
from pathlib import Path

_OPS = Path(__file__).resolve().parent.parent / "ops-server"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

import poda as _p  # noqa: E402

_SESSAO = "00000000-0000-4000-8000-000000000001"
_LINHA = '{"fontes":[' + ",".join(f'{{"n":{i},"trecho":"conteudo do trecho {i}"}}'
                                  for i in range(1, 40)) + \
         '],"ontologia":{"conceitos":["concorrencia"]}}'
# linha longa que NAO e documento estruturado: prosa corrida, o caso que a janela atende
_PROSA = " ".join(f"palavra{i % 7} de um log sem quebra" for i in range(80))


def _args(**extra):
    base = {"cap": 50_000, "cauda": False, "alca": "tarefas:listar --json",
            "sessao_id": _SESSAO, "giro": 1, "tool": "tarefas", "ledger": None,
            "nome_derrame": "g00001-stdout.txt"}
    base.update(extra)
    return base


def test_linha_longa_abaixo_do_teto_deixa_o_cru_e_diz_onde(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    assert len(_PROSA) > _p.LINHA_LONGA
    fora, meta = _p.poda_texto(_PROSA, **_args())
    assert "<linha longa" in fora and "blob" in meta["lavado"]
    assert Path(meta["cru"]).read_text(encoding="utf-8") == _PROSA
    humana = _p.linha_humana(meta)
    assert meta["cru"] in humana and "saiu do retorno" in humana


def test_json_de_linha_unica_nao_e_blob_em_perfil_nenhum(tmp_path, monkeypatch):
    """O incidente de 20/09: verbo FORA do regime cosmetico devolve JSON denso numa linha.
    O campo de resultado (`conceitos`) tem de chegar inteiro, sem depender do cabecalho."""
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    assert len(_LINHA) > _p.LINHA_LONGA and json.loads(_LINHA)
    fora, meta = _p.poda_texto(_LINHA, **_args(tool="motor", alca="motor:buscar pergunta"))
    assert fora == _LINHA and "blob" not in meta["lavado"] and "cru" not in meta
    assert '"conceitos":["concorrencia"]' in fora
    assert not list(tmp_path.rglob("*.txt"))


def test_jsonl_passa_linha_a_linha(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    texto = _LINHA + "\n" + _LINHA.replace("concorrencia", "topologia")
    fora, meta = _p.poda_texto(texto, **_args())
    assert fora == texto and "blob" not in meta["lavado"]


def test_json_quebrado_segue_sendo_linha_longa(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fora, meta = _p.poda_texto(_LINHA[:-1], **_args())
    assert "<linha longa" in fora and "blob" in meta["lavado"]


def test_read_file_nunca_janela_nem_fragmento_do_cru(tmp_path, monkeypatch):
    """`read_file offset=` no cru devolve FRAGMENTO de JSON (nao parseia) e ainda assim
    sai inteiro: e a alca de restauracao, janelar ali fecha a porta de volta."""
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fragmento = _LINHA[5:1405]
    assert len(fragmento) > _p.LINHA_LONGA
    for texto in (fragmento, _PROSA):
        fora, meta = _p.poda_texto(texto, **_args(tool="read_file", alca="read_file:/x"))
        assert fora == texto and "blob" not in meta["lavado"] and "cru" not in meta


def test_read_file_ainda_marca_base64(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    texto = "chave: " + "QUJD" * 100
    fora, meta = _p.poda_texto(texto, **_args(tool="read_file", alca="read_file:/x"))
    assert "<blob tipo=base64" in fora and "blob" in meta["lavado"]


def test_regime_cosmetico_serve_a_linha_inteira_e_nao_derrama(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fora, meta = _p.poda_texto(_PROSA, cosmetica=True, **_args(tool="motor"))
    assert fora == _PROSA and meta["lavado"] == [] and "cru" not in meta
    assert not list(tmp_path.rglob("*.txt"))


def test_lavagem_que_so_tira_ruido_nao_anuncia_perda(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    fora, meta = _p.poda_texto("a\n\n\n\nb", **_args())
    assert meta["lavado"] == ["branco"] and "cru" not in meta
    assert _p.linha_humana(meta) == "poda: lavado (branco)"


def test_acima_do_teto_o_corte_reusa_o_mesmo_cru(tmp_path, monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", tmp_path)
    # sem digito e sem repeticao consecutiva: nem molde nem `linha x N` encolhem o texto
    texto = _PROSA + "\n" + "\n".join("abcdefghij"[i % 10] * (i % 7 + 3) + " conteudo " + "y" * 40
                                     for i in range(200))
    fora, meta = _p.poda_texto(texto, **_args(cap=2_000))
    assert meta["modo"] == "corte" and meta["alca"] == meta["cru"]
    assert len(list(tmp_path.rglob("g00001-stdout.txt"))) == 1
