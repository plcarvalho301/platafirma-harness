"""Correlação da ordem no monta_sessao (#2894).

O gold mede recuperação condicionada a ter havido consulta. O que falta medir é o
DISPARO: ordem com corpus aplicável e nenhuma busca. Estes testes fixam o contrato do
identificador que casa a ordem com as buscas da mesma sessão MCP.
"""
import hashlib


def _ordem_id(sessao: str, pergunta: str):
    """Espelho puro da regra do server (mesma expressão), para testar sem subir o MCP."""
    ordem = (pergunta or "").strip()
    if not ordem:
        return None
    return hashlib.sha1(f"{sessao}\x00{ordem}".encode()).hexdigest()[:12]


def test_pergunta_vazia_nao_gera_ordem():
    # Sem ordem não há o que correlacionar: id nulo é ausência declarada, não id falso.
    assert _ordem_id("s1", "") is None
    assert _ordem_id("s1", "   ") is None


def test_mesma_ordem_mesma_sessao_e_estavel():
    assert _ordem_id("s1", "conserta a FK") == _ordem_id("s1", "conserta a FK")


def test_espaco_de_borda_nao_muda_o_id():
    assert _ordem_id("s1", " conserta a FK\n") == _ordem_id("s1", "conserta a FK")


def test_sessoes_diferentes_nao_colidem():
    # Duas cadeiras podem receber a MESMA ordem; se o id colidir, as buscas de uma
    # entram na conta de disparo da outra.
    assert _ordem_id("s1", "conserta a FK") != _ordem_id("s2", "conserta a FK")


def test_ordens_diferentes_na_mesma_sessao_nao_colidem():
    assert _ordem_id("s1", "conserta a FK") != _ordem_id("s1", "conserta o embed")


def test_id_e_hex_de_12():
    i = _ordem_id("s1", "x")
    assert len(i) == 12 and all(c in "0123456789abcdef" for c in i)
