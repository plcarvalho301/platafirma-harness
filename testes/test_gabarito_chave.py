"""Gabarito reendereçado pela chave da seção (#3909, peça 8 da #3506).

Toda linha de avaliacao/gabarito.jsonl que tem alvo de seção (alvo_section_id) aponta pela chave
(esperado[].chave) ou sai marcada para revisão (revisao): nunca sem um dos dois, nunca com os dois.
O alvo que não casa não se adivinha. As linhas sem alvo de seção (T2 e T3) não mudam.
"""
import json
import re
from pathlib import Path

GABARITO = Path(__file__).resolve().parents[1] / "avaliacao" / "gabarito.jsonl"
# acervo:<sha256 do objeto>#<âncora da seção> (spec modelo-acervo-secao §2-bis 7)
CHAVE = re.compile(r"^acervo:[0-9a-f]{64}#\S+$")
CAUSAS = {
    "ambigua",
    "faixa-so-titulo",
    "ordinal-posicional",
    "sem-cabecalho-com-o-codigo",
    "texto-antigo-menor-que-250",
}


def _linhas():
    return [json.loads(l) for l in GABARITO.read_text(encoding="utf-8").splitlines() if l.strip()]


def _com_alvo_de_secao():
    return [l for l in _linhas() if l.get("alvo_section_id")]


def test_gabarito_mantem_as_228_linhas():
    assert len(_linhas()) == 228


def test_alvo_de_secao_aponta_pela_chave_ou_vai_para_revisao():
    for l in _com_alvo_de_secao():
        chaves = [e["chave"] for e in l["esperado"]]
        assert bool(chaves) != bool(l.get("revisao")), l["id"]


def test_chave_tem_a_forma_da_spec():
    for l in _com_alvo_de_secao():
        for e in l["esperado"]:
            assert CHAVE.match(e["chave"]), (l["id"], e["chave"])
            assert ":p" not in e["chave"].split("#", 1)[1], (l["id"], e["chave"])


def test_causa_de_revisao_e_uma_das_cinco():
    for l in _com_alvo_de_secao():
        if l.get("revisao"):
            assert l["revisao"] in CAUSAS, (l["id"], l["revisao"])


def test_linha_sem_alvo_de_secao_nao_ganha_esperado():
    for l in _linhas():
        if not l.get("alvo_section_id"):
            assert "esperado" not in l and "revisao" not in l, l["id"]
