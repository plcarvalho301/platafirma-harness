"""Contrato do gerador de gold das fontes exatas (#2309).

O que se julga aqui: o SCHEMA do §13, o peso de prova de cada classe de caso, e a recusa
de gerar o que o gerador não pode afirmar. A conformidade — gerar contra as fontes vivas —
é pulada com motivo quando elas não estão no ar.
"""

from __future__ import annotations

import json

import pytest

from recuperacao import gold
from recuperacao.adaptadores.base import Adaptador, FonteIndisponivel
from recuperacao.envelope import (Causa, Fonte, Item, LinhaFonte, Procedencia, Versao,
                                  VersaoTipo)

CAMPOS = {"id", "fonte", "classe", "entrada", "esperado", "resposta_certa", "origem", "pontuavel"}


class FonteFalsa(Adaptador):
    fonte = Fonte("board")

    def __init__(self, itens=3, caida=False) -> None:
        self._n, self._caida = itens, caida

    def _carimbo(self):
        return "203/393"

    def _busca(self, alvo, filtros, k, texto):
        if self._caida:
            raise FonteIndisponivel(Causa.FORA_DO_AR, "caiu")
        return [
            Item(procedencia=Procedencia(fonte=self.fonte, chave=f"item:{2300 + i}",
                                         versao=Versao(VersaoTipo.SEQ, str(180 + i))),
                 ref=f"#{2300 + i} — Adaptador de repositorio {i}")
            for i in range(self._n)
        ]


# ================================================================= 1. schema do §13


def test_todo_caso_traz_os_campos_do_schema():
    for c in gold.gera("board", FonteFalsa()):
        assert CAMPOS <= set(c), f"faltam {CAMPOS - set(c)} em {c['id']}"


def test_vocabulario_fechado_de_resposta_certa():
    for c in gold.gera("board", FonteFalsa()):
        assert c["resposta_certa"] in {"item", "vazia", "ausente"}
        assert c["classe"] == "exata"
        assert c["fonte"] == "board"


def test_esperado_e_lista_de_objetos_com_chave():
    for c in gold.gera("board", FonteFalsa()):
        assert isinstance(c["esperado"], list)
        assert all(set(e) <= {"chave", "coordenada"} and e.get("chave") for e in c["esperado"])


def test_id_e_unico():
    casos = gold.gera("board", FonteFalsa())
    assert len({c["id"] for c in casos}) == len(casos)


def test_saida_e_jsonl_valido(tmp_path):
    destino = gold.escreve(gold.gera("board", FonteFalsa()), str(tmp_path / "g.jsonl"))
    linhas = [json.loads(l) for l in open(destino, encoding="utf-8") if l.strip()]
    assert len(linhas) == len(gold.gera("board", FonteFalsa()))


# ================================================================= 2. peso de prova


def test_chave_exata_e_pontuavel():
    casos = [c for c in gold.gera("board", FonteFalsa()) if c["id"].startswith("board-chave")]
    assert casos
    for c in casos:
        assert c["pontuavel"] is True
        assert c["esperado"] == [{"chave": c["entrada"]}]
        assert c["casamento_esperado"] == "exato"


def test_caso_de_vazia_e_pontuavel_e_tem_esperado_vazio():
    c = [x for x in gold.gera("board", FonteFalsa()) if x["resposta_certa"] == "vazia"][0]
    assert c["esperado"] == [] and c["pontuavel"] is True
    assert c["entrada"] == "item:99999999"


def test_caso_de_termo_sai_despontuavel_e_declarado():
    """Esperado derivado do mesmo mecanismo que será medido é gabarito com a prova aberta."""
    casos = [c for c in gold.gera("board", FonteFalsa()) if c["id"].startswith("board-termo")]
    assert casos
    for c in casos:
        assert c["pontuavel"] is False
        assert "CANDIDATO" in c["origem"]


def test_sem_termo_nao_emite_candidato():
    casos = gold.gera("board", FonteFalsa(), com_termo=False)
    assert not [c for c in casos if not c["pontuavel"]]


def test_termo_nao_e_palavra_de_parada_nem_numero():
    for c in gold.gera("board", FonteFalsa()):
        if c["id"].startswith("board-termo"):
            assert c["entrada"].lower() not in gold.PARADAS
            assert not c["entrada"].isdigit()


# ================================================================= 3. congelamento


def test_origem_carrega_fonte_carimbo_e_data():
    c = gold.gera("board", FonteFalsa())[0]
    assert c["origem"].startswith("gerador:board@203/393")
    assert "sem validacao humana" in c["origem"]


def test_origem_carimba_com_a_busca_que_gerou_os_casos():
    """O carimbo é o da BUSCA, não o de uma segunda chamada.

    Medido em 20/08/2026: `AdaptadorFila._carimbo()` sem alvo devolve `0-0` por desenho, e
    a segunda chamada carimbava 41 casos da caixa viva com uma versão que ninguém leu.
    Aqui o carimbo cai DEPOIS da busca: a versão correta é a que os casos têm, e ela já
    está na linha."""

    class CarimboIntermitente(FonteFalsa):
        def __init__(self):
            super().__init__()
            self.vezes = 0

        def _carimbo(self):
            self.vezes += 1
            if self.vezes > 1:
                raise FonteIndisponivel(Causa.FORA_DO_AR, "sem carimbo")
            return "203/393"

    assert "@203/393" in gold.gera("board", CarimboIntermitente())[0]["origem"]


def test_carimbo_indisponivel_nao_inventa_carimbo():
    """Sem carimbo na linha e sem carimbo na chamada, `sem-carimbo` declarado — o que o
    gerador não pode produzir é gold que PARECE congelado numa versão que não existe."""

    class SemCarimboNenhum(FonteFalsa):
        def __init__(self):
            super().__init__()
            self.vezes = 0

        def _carimbo(self):
            self.vezes += 1
            if self.vezes > 1:
                raise FonteIndisponivel(Causa.FORA_DO_AR, "sem carimbo")
            return ""

        def busca(self, *a, **kw):
            r = super().busca(*a, **kw)
            r.linha = LinhaFonte(fonte=r.linha.fonte, cobertura=r.linha.cobertura)
            return r

    assert "@sem-carimbo" in gold.gera("board", SemCarimboNenhum())[0]["origem"]


# ================================================================= 4. o que ele recusa


def test_fonte_sem_estado_levanta_em_vez_de_emitir_gold_vazio():
    """Gold vazio é pior que gold ausente: parece medido e serve `coberta` a seco."""
    with pytest.raises(gold.SemEstado):
        gold.gera("board", FonteFalsa(caida=True))
    with pytest.raises(gold.SemEstado):
        gold.gera("board", FonteFalsa(itens=0))


def test_acervo_nao_sai_daqui():
    """§13 — Cargo e acervo são de claudinho-dados; e o acervo nem é classe exata."""
    with pytest.raises(gold.SemEstado):
        gold.gera("acervo")
    assert "acervo" not in gold.ADAPTADORES


def test_nao_gera_resposta_certa_ausente():
    """`ausente` é juízo sobre o corpus, não sobre o estado — gabarito de autor (§13)."""
    assert not [c for c in gold.gera("board", FonteFalsa()) if c["resposta_certa"] == "ausente"]


def test_respeita_o_teto_de_casos():
    casos = gold.gera("board", FonteFalsa(itens=50), casos=5, com_termo=False)
    assert len([c for c in casos if c["resposta_certa"] == "item"]) == 5


def test_resumo_separa_pontuavel_de_candidato():
    r = gold.resumo(gold.gera("board", FonteFalsa()))
    assert r["total"] == r["pontuaveis"] + r["candidatos"]
    assert r["por_resposta_certa"]["vazia"] == 1


# ================================================================= 5. linha de comando


def test_cli_escreve_um_arquivo_por_fonte(tmp_path, monkeypatch):
    monkeypatch.setitem(gold.ADAPTADORES, "board", FonteFalsa)
    assert gold.main(["--fonte", "board", "--saida-dir", str(tmp_path)]) == 0
    assert (tmp_path / "gold-board.jsonl").exists()


def test_cli_fonte_sem_estado_falha_declarando_e_nao_apaga_o_resto(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(gold.ADAPTADORES, "board", lambda: FonteFalsa(caida=True))
    assert gold.main(["--fonte", "board", "--saida-dir", str(tmp_path)]) == 1
    assert "SEM GOLD" in capsys.readouterr().err
    assert not (tmp_path / "gold-board.jsonl").exists()


# ================================================================= 6. conformidade


def fonte_no_ar(nome: str) -> bool:
    try:
        gold.gera(nome, casos=2, com_termo=False)
    except Exception:  # noqa: BLE001
        return False
    return True


@pytest.mark.parametrize("nome", ["board", "registro"])
def test_conformidade_gera_contra_a_fonte_viva(nome):
    if not fonte_no_ar(nome):
        pytest.skip(f"{nome} não devolveu estado nesta bancada")
    casos = gold.gera(nome, casos=3)
    assert casos and all(c["fonte"] == nome for c in casos)
    pontuaveis = [c for c in casos if c["pontuavel"]]
    assert pontuaveis, "gold sem caso pontuável não calibra nada"
