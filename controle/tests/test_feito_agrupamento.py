# Card #394: unidade sobre o agrupamento de /feito por dia, incluindo card
# sem data de fechamento (aberto) e card/commit órfão (sem o outro lado).
# Camada de unidade do modelo de teste do card — sem subprocess/git/rede de
# verdade, tudo mockado no nível de _commits_por_dia/_cards_fechados_por_dia.
from __future__ import annotations

from harness_controle import web
from harness_controle.verbos import ResultadoVerbo


def _sem_commits(monkeypatch):
    monkeypatch.setattr(web, "_commits_por_dia", lambda *a, **k: {})


def _sem_cards(monkeypatch):
    monkeypatch.setattr(web, "_cards_fechados_por_dia", lambda *a, **k: {})


def test_card_e_commit_que_se_referenciam_aparecem_juntos(monkeypatch):
    monkeypatch.setattr(web, "_commits_por_dia", lambda *a, **k: {
        "2026-08-10": [
            {"sha": "86cfdea", "mensagem": "LOTE 3 (#390): tela", "card_ref": 390},
        ],
    })
    monkeypatch.setattr(web, "_cards_fechados_por_dia", lambda *a, **k: {
        "2026-08-10": [{"id": 390, "titulo": "plano de controle do harness"}],
    })

    dias = web._monta_feito()
    assert len(dias) == 1
    dia = dias[0]
    assert dia["data"] == "2026-08-10"
    assert len(dia["cards"]) == 1
    assert dia["cards"][0]["id"] == 390
    assert dia["cards"][0]["commits"] == [{"sha": "86cfdea", "mensagem": "LOTE 3 (#390): tela"}]
    assert dia["commits"] == []  # o commit ligado NAO duplica na lista de orfaos


def test_card_fechado_sem_commit_associado_e_orfao(monkeypatch):
    """Card fechado que nenhum commit referencia — aparece, com lista de
    commits vazia (o render decide o texto "sem commit associado")."""
    _sem_commits(monkeypatch)
    monkeypatch.setattr(web, "_cards_fechados_por_dia", lambda *a, **k: {
        "2026-08-05": [{"id": 999, "titulo": "fechado na unha, sem commit citado"}],
    })

    dias = web._monta_feito()
    assert dias == [{"data": "2026-08-05", "cards": [
        {"id": 999, "titulo": "fechado na unha, sem commit citado", "commits": []},
    ], "commits": []}]


def test_commit_sem_referencia_e_orfao(monkeypatch):
    """Commit cuja mensagem nao cita nenhum "#<id>" — vai pra lista de
    orfaos do dia, nunca sumido nem inventado card pra ele."""
    monkeypatch.setattr(web, "_commits_por_dia", lambda *a, **k: {
        "2026-08-06": [{"sha": "abc1234", "mensagem": "ajuste solto sem card", "card_ref": None}],
    })
    _sem_cards(monkeypatch)

    dias = web._monta_feito()
    assert dias == [{"data": "2026-08-06", "cards": [],
                      "commits": [{"sha": "abc1234", "mensagem": "ajuste solto sem card"}]}]


def test_commit_referencia_card_fora_da_janela_e_orfao(monkeypatch):
    """Commit cita "#123", mas nenhum card 123 foi encontrado fechado dentro
    da janela (fechado fora da janela, ainda aberto, ou id que nao existe) —
    o commit continua aparecendo, como orfao, nunca some."""
    monkeypatch.setattr(web, "_commits_por_dia", lambda *a, **k: {
        "2026-08-06": [{"sha": "abc1234", "mensagem": "refs #123 mas card nao veio", "card_ref": 123}],
    })
    _sem_cards(monkeypatch)

    dias = web._monta_feito()
    assert dias[0]["commits"] == [{"sha": "abc1234", "mensagem": "refs #123 mas card nao veio"}]
    assert dias[0]["cards"] == []


def test_card_aberto_fechado_em_null_nunca_entra_no_agrupamento(monkeypatch):
    """`_cards_fechados_por_dia` já filtra isso (funcao dublada aqui pra
    isolar SO a logica de agrupamento) — mas o teste de unidade do card #394
    pede explicitamente o caso "card sem data de fechamento": zero cards
    fechados -> /feito nao inventa dia nenhum pra ele."""
    _sem_commits(monkeypatch)

    def _cards_reais(limite_dias=14):
        # replica o filtro real: card aberto (fechado_em null) nunca aparece
        crus = [
            {"id": 1, "fechado": False, "fechado_em": None, "titulo": "aberto"},
            {"id": 2, "fechado": True, "fechado_em": "2026-08-06T10:00:00-03:00", "titulo": "fechado"},
        ]
        por_dia = {}
        for c in crus:
            if not c["fechado"] or not c["fechado_em"]:
                continue
            por_dia.setdefault("2026-08-06", []).append({"id": c["id"], "titulo": c["titulo"]})
        return por_dia

    monkeypatch.setattr(web, "_cards_fechados_por_dia", _cards_reais)

    dias = web._monta_feito()
    todos_ids = [c["id"] for dia in dias for c in dia["cards"]]
    assert todos_ids == [2]  # so o fechado — o aberto (id 1) nunca aparece


def test_sem_cards_e_sem_commits_devolve_lista_vazia(monkeypatch):
    _sem_commits(monkeypatch)
    _sem_cards(monkeypatch)
    assert web._monta_feito() == []


def test_dias_ordenados_do_mais_recente_pro_mais_antigo(monkeypatch):
    monkeypatch.setattr(web, "_commits_por_dia", lambda *a, **k: {
        "2026-08-05": [{"sha": "aaa1111", "mensagem": "dia antigo", "card_ref": None}],
        "2026-08-10": [{"sha": "bbb2222", "mensagem": "dia recente", "card_ref": None}],
    })
    _sem_cards(monkeypatch)

    dias = web._monta_feito()
    assert [d["data"] for d in dias] == ["2026-08-10", "2026-08-05"]


# --- _cards_fechados_por_dia: normalizacao real de fechado_em -------------


def test_cards_fechados_por_dia_usa_o_verbo_e_agrupa_pela_data(monkeypatch):
    def _chamar_falso(argv, timeout=None, env=None):
        assert argv[:2] == ["tarefas", "listar-tudo"]
        assert "--json" in argv
        return ResultadoVerbo(True, [
            {"id": 1, "titulo": "aberto", "fechado": False, "fechado_em": None},
            {"id": 2, "titulo": "fechado hoje", "fechado": True,
             "fechado_em": "2026-08-10T09:00:00-03:00"},
        ], None, 0, 0.01)

    monkeypatch.setattr(web, "chamar", _chamar_falso)
    por_dia = web._cards_fechados_por_dia(limite_dias=365)
    assert list(por_dia) == ["2026-08-10"]
    assert por_dia["2026-08-10"] == [{"id": 2, "titulo": "fechado hoje"}]


def test_cards_fechados_por_dia_verbo_indisponivel_nao_quebra(monkeypatch):
    monkeypatch.setattr(
        web, "chamar", lambda *a, **k: ResultadoVerbo(False, None, "timeout", None, 20.0)
    )
    assert web._cards_fechados_por_dia() == {}
