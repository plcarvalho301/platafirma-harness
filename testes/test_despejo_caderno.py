# componente: componente:descanso
"""Suíte do despejo único dos cadernos e da rota fechada (story #4355, feature #4269)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS_DIR / "lib"))

from descanso import despejo_caderno as dc  # noqa: E402


CHAVES_FICHARIO = {
    "dados",
    "ia",
    "engenharia",
    "persona:politicas-publicas",
    "chapeu:engenharia-de-dados",
    "card:4355",
    "capacidade:tarefas",
}


class OrigemMemoria:
    def __init__(
        self,
        entradas: list[dict[str, Any]],
        eventos: list[dict[str, Any]],
        usos_aresta: list[dict[str, Any]],
        legados: list[dict[str, Any]],
    ):
        self._dados = (entradas, eventos, usos_aresta, legados)

    def ler(self):
        return self._dados


class GravadorMemoria:
    def __init__(self, mudo: bool = False):
        self.mudo = mudo
        self.lotes: list[list[dict[str, Any]]] = []
        self.gravadas: dict[str, dict[str, Any]] = {}

    def gravar_lote(self, lote: list[dict[str, Any]]) -> dict[str, Any]:
        if self.mudo:
            raise dc.BancoMudo("banco de eventos mudo no ensaio")
        self.lotes.append(lote)
        inseridos, existentes = [], []
        for ev in lote:
            eid = ev["evento_id"]
            if eid in self.gravadas:
                existentes.append(eid)
            else:
                self.gravadas[eid] = ev
                inseridos.append(eid)
        return {"familia": "mensagem", "inseridos": inseridos, "existentes": existentes}


def _origem_amostra() -> OrigemMemoria:
    entradas = [
        {
            "id": 101,
            "cadeira": "dados",
            "chapeu": "engenharia-de-dados",
            "categoria": "licao",
            "estado": "vigente",
            "texto": "Vistas em casa_leitura precisam de GRANT SELECT para olaria.",
            "caso": "#4355",
            "dito_em": "2026-11-17",
            "dito_onde": "chat de dados",
            "criada_em": "2026-10-15T12:00:00+00:00",
            "criada_por": "dados",
            "de_ponta": "capacidade:tarefas",
            "para_ponta": "termo-livre-sem-ficha",
        },
        {
            "id": 102,
            "cadeira": "politicas-publicas",
            "chapeu": "governanca",  # chapéu da casa velha, sem ficha
            "categoria": "premissa",
            "estado": "retirada",
            "texto": "Premissa antiga retirada depois.",
            "caso": "texto livre sem numero de card",
            "dito_em": None,
            "dito_onde": None,
            "criada_em": "2026-11-01T09:30:00+00:00",
            "criada_por": "o dono",
        },
    ]
    eventos = [
        {"id": 1, "entrada_id": 102, "ato": "retirar", "de_estado": "vigente", "para_estado": "retirada", "por": "dados", "em": "2026-11-05T10:00:00+00:00"},
        {"id": 2, "entrada_id": 102, "ato": "podar", "de_estado": "retirada", "para_estado": "retirada", "por": "bot", "em": "2026-11-06T10:00:00+00:00"},
    ]
    usos = [
        {"entrada_id": 101, "fita": "fita-77", "quem": "dados", "declarada": True, "em": "2026-11-10T14:00:00+00:00"},
    ]
    legados = [
        {
            "chave_origem": "dados:engenharia-de-dados:sec-1",
            "cadeira": "dados",
            "chapeu": "engenharia-de-dados",
            "texto": "Texto da seção de legado.",
            "bytes": 26,
            "capturado_em": "2026-10-01T08:00:00+00:00",
            "triado_em": None,
        }
    ]
    return OrigemMemoria(entradas, eventos, usos, legados)


def test_despejo_converte_entradas_usos_e_legado_e_mantem_eventos_no_payload():
    origem = _origem_amostra()
    gravador = GravadorMemoria()

    resumo = dc.despejar(origem, gravador, CHAVES_FICHARIO)
    assert resumo == {"esperado": 4, "entradas": 2, "usos_aresta": 1, "legados": 1, "inseridos": 4, "existentes": 0}
    assert len(gravador.gravadas) == 4

    por_origem = {ev["origem"]: ev for ev in gravador.gravadas.values()}
    m101 = por_origem["caderno_entrada|101"]
    assert m101["tipo_de_mensagem"] == "afirmacao"
    assert m101["destinatarios"] == ["dados"]
    assert m101["sobre"] == "chapeu:engenharia-de-dados"
    assert m101["apoios"] == ["card:4355"]
    assert m101["cita"] == "chat de dados · 2026-11-17"
    assert set(m101["etiquetas"]) == {"dados", "chapeu:engenharia-de-dados", "card:4355", "capacidade:tarefas"}
    assert "termo-livre-sem-ficha" not in m101["etiquetas"]
    assert "licao" not in m101["etiquetas"]
    assert m101["payload"]["linha"]["categoria"] == "licao"
    assert m101["payload"]["linha"]["para_ponta"] == "termo-livre-sem-ficha"

    m102 = por_origem["caderno_entrada|102"]
    assert m102["destinatarios"] == ["persona:politicas-publicas"]
    assert m102["sobre"] == "persona:politicas-publicas"
    assert m102["quem"] == "o dono"
    assert m102["apoios"] == []
    assert m102["etiquetas"] == ["persona:politicas-publicas"]
    assert [e["ato"] for e in m102["payload"]["eventos"]] == ["retirar", "podar"]
    assert m102["payload"]["linha"]["estado"] == "retirada"


def test_despejo_rodado_duas_vezes_grava_zero_na_segunda():
    origem = _origem_amostra()
    gravador = GravadorMemoria()

    r1 = dc.despejar(origem, gravador, CHAVES_FICHARIO)
    r2 = dc.despejar(origem, gravador, CHAVES_FICHARIO)
    assert r1["inseridos"] == 4 and r1["existentes"] == 0
    assert r2["inseridos"] == 0 and r2["existentes"] == 4
    assert len(gravador.gravadas) == 4


def test_despejo_reparte_em_lotes_de_ate_mil():
    entradas = [
        {"id": i, "cadeira": "dados", "chapeu": "engenharia-de-dados", "categoria": "licao", "estado": "vigente",
         "texto": f"entrada {i}", "criada_em": "2026-11-10T10:00:00+00:00"}
        for i in range(1, 1006)
    ]
    gravador = GravadorMemoria()
    resumo = dc.despejar(OrigemMemoria(entradas, [], [], []), gravador, CHAVES_FICHARIO)
    assert resumo["inseridos"] == 1005
    assert [len(l) for l in gravador.lotes] == [1000, 5]


def test_despejo_com_banco_mudo_para_sem_fechar_rota():
    origem = _origem_amostra()
    gravador = GravadorMemoria(mudo=True)
    rota_fechada = False
    with pytest.raises(dc.BancoMudo):
        dc.despejar(origem, gravador, CHAVES_FICHARIO)
        rota_fechada = True
    assert rota_fechada is False
