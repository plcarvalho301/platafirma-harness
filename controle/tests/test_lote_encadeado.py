"""Contrato do lote encadeado da porta (card:3149 passo 7; spec_ambiente-de-desenvolvimento
§6; comentario #939 secao A).

Prova a regra de parada em `ops-server/lote.py`, o iterador unico que `run_command
commands[]` e o `lote` da tool de verbo chamam: lista branca (so exit 0 e 1 seguem), os tres
estados por item (rodou, nao rodou, omitido por teto) e o bloco `cadeia`. Nao prova: a
fiacao em server.py (execve, PDP, auditoria) -- a suite da porta precisa do venv com `mcp`,
que o runner de controle/ nao tem; ela roda no ensaio da porta e ao vivo depois da promocao.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops-server"))
import lote  # noqa: E402


def _roda_com(saidas):
    rodados = []

    async def roda(i, item, _resultados):
        rodados.append(i)
        return saidas[i]
    return roda, rodados


def _ex(e):
    return {"exit_code": e, "stdout": {"texto": f"item saiu {e}\n", "bytes_total": 12}}


def _rodar(saidas, **kw):
    roda, rodados = _roda_com(saidas)
    out = asyncio.run(lote.itera(list(range(len(saidas))), roda, **kw))
    return out, rodados


def test_cadeia_do_aceite_ok_1_4_ok_para_no_terceiro():
    out, rodados = _rodar([_ex(0), _ex(1), _ex(4), _ex(0)], encadeado=True)
    assert rodados == [0, 1, 2]
    assert out["lote"][3] == {"nao_rodou": True, "motivo": "a cadeia parou no item 2"}
    c = out["cadeia"]
    assert c["parou_em"] == 2 and c["exit"] == 4 and c["nao_rodou"] == [3]
    assert c["motivo"] == "parou em 2: item saiu 4"
    assert [x["exit"] for x in c["itens"]] == [0, 1, 4, None]


def test_recusa_da_porta_para_como_2():
    recusa = {"recusado": True, "verbo": "cat", "motivo": "sem verbo"}
    out, rodados = _rodar([recusa, _ex(0)], encadeado=True)
    assert rodados == [0]
    assert out["cadeia"]["parou_em"] == 0 and out["cadeia"]["exit"] == 2


def test_timeout_para_como_5():
    timeout = {"erro": "timeout (120s) — grupo de processo morto"}
    out, rodados = _rodar([_ex(0), timeout, _ex(0)], encadeado=True)
    assert rodados == [0, 1]
    assert out["cadeia"]["parou_em"] == 1 and out["cadeia"]["exit"] == 5


def test_negado_pelo_pdp_para_como_4():
    negado = {"erro": "negado pela politica de acesso: x", "regra": "projecao"}
    out, _ = _rodar([negado, _ex(0)], encadeado=True)
    assert out["cadeia"]["exit"] == 4


def test_exit_fora_da_tabela_para_como_5_nao_segue():
    """Lista negra (2..5) deixaria o 128 do git passar como 'seguir'."""
    out, rodados = _rodar([_ex(0), _ex(128), _ex(0)], encadeado=True)
    assert rodados == [0, 1]
    assert out["cadeia"]["exit"] == 5


def test_tudo_zero_ou_um_nao_para_e_exit_do_topo_resume():
    out, rodados = _rodar([_ex(0), _ex(0)], encadeado=True)
    assert rodados == [0, 1] and out["cadeia"]["exit"] == 0 and out["cadeia"]["parou_em"] is None
    out, _ = _rodar([_ex(0), _ex(1)], encadeado=True)
    assert out["cadeia"]["exit"] == 1


def test_teto_no_meio_da_cadeia_devolve_lote_next_sem_declarar_parada():
    out, rodados = _rodar([_ex(0), _ex(0), _ex(0)], encadeado=True, cap=20,
                          bytes_de=lote.bytes_stdout)
    assert rodados == [0, 1]
    assert out["lote_next"] == 2
    assert out["lote"][2] == {"omitido_por_teto": True}
    assert out["cadeia"]["parou_em"] is None


def test_sem_encadeado_o_comportamento_de_sempre():
    """Regressao: sem a chave, erro num item nao derruba os outros e nao ha bloco cadeia."""
    out, rodados = _rodar([_ex(4), _ex(0)])
    assert rodados == [0, 1]
    assert "cadeia" not in out
    assert out["lote_next"] is None
