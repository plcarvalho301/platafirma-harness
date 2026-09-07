"""Ensaio do verbo `metrica` — card #3017.

Duas familias de teste, e a diferenca entre elas e o ponto:

SINTETICO  eventos montados a mao, um por regra do card. Nao dependem de log
           nenhum, entao continuam verdes depois que o log de hoje rotacionar.
           E aqui que cada uma das seis definicoes do card fica pregada.

GABARITO   os erros REAIS de 2026-09-07, que o card fixou como SLO de acuracia do
           verbo. Sao a prova de que a classificacao acerta o mundo, e nao so o
           mundo que o teste inventou. `ops-log-prune` tem retencao: quando o
           arquivo do dia sumir, o teste PULA — nao fica vermelho por falta de
           insumo, e nao vira verde por baixo do pano (o skip aparece na suite).
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

import pytest

VERBO = Path(__file__).resolve().parents[1] / "bin" / "metrica"
_spec = importlib.util.spec_from_loader(
    "metrica", importlib.machinery.SourceFileLoader("metrica", str(VERBO)))
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

DIA_GABARITO = "2026-09-07"


# --- andaime ---------------------------------------------------------------------

class FonteFake:
    """Implementa o mesmo contrato de FonteJsonl: `linhas(dia)` -> dicionarios.

    Que o ensaio consiga substituir a fonte com sete linhas de classe e a prova de
    que a trava do card foi respeitada — a leitura esta isolada das tres camadas.
    """

    def __init__(self, regs):
        self.regs, self.ilegiveis = regs, 0

    def linhas(self, dia):
        return iter(self.regs)


def reg(ts, tool, ato=None, exit_code=0, ordem="o1", **extra):
    d = {"ts": f"2026-09-07T{ts}-03:00", "tool": tool, "ato": ato,
         "ordem_id": ordem, "sessao_id": "s1", "cadeira": "ia",
         "exit_code": exit_code, "dur_ms": 10}
    d.update(extra)
    return d


def classifica(regs, cadeira=None):
    return m.classifica(FonteFake(regs), DIA_GABARITO, cadeira)


# --- SINTETICO: o que e giro ------------------------------------------------------

def test_http_req_e_tool_hifen_ficam_de_fora():
    giros, _, _ = classifica([
        {"ts": "2026-09-07T10:00:00.000-03:00", "tool": "-", "evento": "http_req"},
        {"ts": "2026-09-07T10:00:01.000-03:00", "tool": "-", "evento": "recusa"},
        reg("10:00:02.000", "mesa", "ver"),
    ])
    assert [g["tool"] for g in giros] == ["mesa"]


def test_ordem_e_por_ts_e_desempata_pela_posicao_no_arquivo():
    giros, _, _ = classifica([
        reg("10:00:00.000", "a", "x"),
        reg("10:00:00.000", "b", "x"),   # mesmo milissegundo: vence quem foi escrito antes
        reg("09:00:00.000", "c", "x"),
    ])
    assert [g["tool"] for g in giros] == ["c", "a", "b"]


# --- SINTETICO: erro --------------------------------------------------------------

def test_erro_por_exit_code():
    giros, _, _ = classifica([reg("10:00:00.000", "repo", "commitar", exit_code=3)])
    assert giros[0]["falhou"] is True


def test_erro_por_campo_erro_sem_exit_code():
    """read_file grava `erro` e nao grava `exit_code`. Cair fora daqui contaria
    erro a menos — e o dia 07/09 tem esse caso (caderno/secretaria inexistente)."""
    linha = reg("10:00:00.000", "read_file")
    del linha["exit_code"]
    linha["erro"] = "nao existe ou nao e arquivo"
    giros, _, _ = classifica([linha])
    assert giros[0]["falhou"] is True


def test_erro_por_recusa_da_porta_so_verbo():
    linha = reg("10:00:00.000", "run_command", evento="sem_verbo", motivo="sem verbo")
    del linha["exit_code"]
    giros, _, _ = classifica([linha])
    assert giros[0]["falhou"] is True


def test_exit_zero_nao_e_erro():
    giros, _, _ = classifica([reg("10:00:00.000", "mesa", "ver")])
    assert giros[0]["falhou"] is False


# --- SINTETICO: help-pedido -------------------------------------------------------

def test_help_pedido_exige_o_giro_seguinte_com_ato_real():
    giros, _, _ = classifica([
        reg("10:00:00.000", "fila"),                    # sem ato: candidato
        reg("10:00:01.000", "fila", "ler"),             # o ato real, mesmo ordem_id
    ])
    assert [g["help"] for g in giros] == [True, False]


def test_chamada_sem_ato_sozinha_nao_e_help_pedido():
    giros, _, _ = classifica([reg("10:00:00.000", "fila")])
    assert giros[0]["help"] is False


def test_help_pedido_por_exit_2_mesmo_com_ato():
    """`conferir chapeu` saiu 2 (verbo nao implementado) e a fita chamou outro ato
    depois: o giro perdido foi de descoberta de forma, e conta como help."""
    giros, _, _ = classifica([
        reg("10:00:00.000", "conferir", "chapeu", exit_code=2),
        reg("10:00:01.000", "conferir", "chapeu", exit_code=2),
        reg("10:00:02.000", "conferir", "existe"),
    ])
    assert [g["help"] for g in giros] == [True, True, False]


def test_help_pedido_nao_atravessa_ordem_id():
    giros, _, _ = classifica([
        reg("10:00:00.000", "fila", ordem="o1"),
        reg("10:00:01.000", "fila", "ler", ordem="o2"),
    ])
    assert [g["help"] for g in giros] == [False, False]


# --- SINTETICO: acerto e cadeia ---------------------------------------------------

def test_tres_erros_e_acerto_no_quarto_giro():
    """A forma do gabarito de 07/09: repo commitar, profundidade 3, acerto no 4o."""
    giros, _, cadeias = classifica([
        reg("15:03:00.000", "repo", "commitar", exit_code=3),
        reg("15:03:10.000", "repo", "commitar", exit_code=3),
        reg("15:03:20.000", "repo", "commitar", exit_code=3),
        reg("15:03:30.000", "repo", "commitar"),
    ])
    assert len(cadeias) == 1
    assert cadeias[0]["profundidade"] == 3
    assert cadeias[0]["acerto_no_giro"] == 4
    assert giros[3]["acerto"] is True and giros[3]["ate_acerto"] == 4


def test_um_erro_so_tem_acerto_mas_nao_e_cadeia():
    giros, _, cadeias = classifica([
        reg("10:00:00.000", "repo", "commitar", exit_code=3),
        reg("10:00:01.000", "repo", "commitar"),
    ])
    assert cadeias == []
    assert giros[1]["acerto"] is True


def test_acerto_de_primeira_nao_existe():
    giros, _, cadeias = classifica([reg("10:00:00.000", "repo", "commitar")])
    assert giros[0]["acerto"] is False and cadeias == []


def test_cadeia_que_o_dia_terminou_sem_fechar_conta():
    """Descartar a cadeia que nunca acertou esconderia justamente a pior."""
    _, _, cadeias = classifica([
        reg("23:00:00.000", "repo", "empurrar", exit_code=3),
        reg("23:00:01.000", "repo", "empurrar", exit_code=3),
    ])
    assert len(cadeias) == 1
    assert cadeias[0]["profundidade"] == 2
    assert cadeias[0]["acerto_no_giro"] is None


def test_cadeia_nao_atravessa_par_ordem_tool():
    _, _, cadeias = classifica([
        reg("10:00:00.000", "repo", "commitar", exit_code=3, ordem="o1"),
        reg("10:00:01.000", "repo", "commitar", exit_code=3, ordem="o2"),
        reg("10:00:02.000", "repo", "commitar", ordem="o1"),
    ])
    assert cadeias == []


# --- SINTETICO: lote --------------------------------------------------------------

def test_lote_e_pertinencia_a_lote_id_nao_lote_n_maior_que_um():
    """DIVERGENCIA DO CARD, pregada aqui: no log `lote_n` e o INDICE do item, nao o
    tamanho do lote. Pela formula literal ('lote_n > 1') este lote de dois sairia
    com zero eventos de lote; pela pertinencia a `lote_id`, sai com dois."""
    giros, _, _ = classifica([
        reg("10:00:00.000", "read_file", lote_id="ab12", lote_n=0),
        reg("10:00:01.000", "read_file", lote_id="ab12", lote_n=1),
        reg("10:00:02.000", "mesa", "ver"),
    ])
    assert [g["lote"] for g in giros] == [True, True, False]


# --- SINTETICO: as tres camadas ---------------------------------------------------

def test_camada_eventos_emite_um_objeto_por_evento():
    giros, _, cadeias = classifica([
        reg("10:00:00.000", "repo", "commitar", exit_code=3, lote_id="ab12", lote_n=0),
        reg("10:00:01.000", "repo", "commitar", exit_code=3),
        reg("10:00:02.000", "repo", "commitar"),
    ])
    evs = m.stream_eventos(giros, cadeias)
    conta = {t: sum(1 for e in evs if e["tipo"] == t) for t in m.TIPOS}
    assert conta == {"giro": 3, "erro": 2, "help": 0, "acerto": 1, "cadeia": 1, "lote": 1}


def test_camada_eventos_filtra_por_tipo():
    giros, _, cadeias = classifica([
        reg("10:00:00.000", "repo", "commitar", exit_code=3),
        reg("10:00:01.000", "repo", "commitar"),
    ])
    evs = m.stream_eventos(giros, cadeias, "erro")
    assert [e["tipo"] for e in evs] == ["erro"]


def test_camada_dia_responde_as_quatro_perguntas():
    giros, _, cadeias = classifica([
        reg("10:00:00.000", "fila", ordem="o1"),
        reg("10:00:01.000", "fila", "ler", ordem="o1"),
        reg("10:00:02.000", "repo", "commitar", exit_code=3, ordem="o2"),
        reg("10:00:03.000", "repo", "commitar", exit_code=3, ordem="o2"),
        reg("10:00:04.000", "repo", "commitar", ordem="o2"),
    ])
    r = m.resumo_do_dia(giros, cadeias)
    assert r["giros_por_fita"] == {"o2": 3, "o1": 2}
    assert r["erros_por_verbo"]["repo"] == {"total": 2, "por_ato": {"commitar": 2}}
    assert r["profundidade_de_cadeia"]["maior"] == 2
    assert r["giros_de_help"] == {"fila": 1}
    assert r["total"]["giros"] == 5


def test_camada_ate_acerto_conta_do_primeiro_giro_do_par():
    giros, par, _ = classifica([
        reg("10:00:00.000", "repo", "estado"),                     # 1o giro do par
        reg("10:00:01.000", "repo", "commitar", exit_code=3),
        reg("10:00:02.000", "repo", "commitar"),                   # acerto no 3o
    ])
    r = m.ate_acerto(giros, par)
    assert r["resumo"]["pares_com_acerto"] == 1
    assert r["ate_acerto"][0]["giros_ate_acerto"] == 3
    assert r["ate_acerto"][0]["erros_antes"] == 1
    assert r["ate_acerto"][0]["atos"] == ["estado", "commitar", "commitar"]


def test_cadeira_filtra_antes_de_classificar():
    linhas = [reg("10:00:00.000", "mesa", "ver"),
              reg("10:00:01.000", "mesa", "ver", cadeira="fabrica")]
    giros, _, _ = classifica(linhas, cadeira="fabrica")
    assert len(giros) == 1 and giros[0]["cadeira"] == "fabrica"


# --- borda: uso, erro gracioso, saida ---------------------------------------------

def test_saida_e_json_por_default(capsys):
    assert m.main(["metrica", "dia", "1999-01-02"]) == 4    # sem log: so a borda
    linhas = capsys.readouterr()
    assert linhas.out == ""


def test_dia_sem_log_e_erro_gracioso_exit_4_sem_stack(capsys):
    codigo = m.main(["metrica", "eventos", "1999-01-02"])
    err = capsys.readouterr().err
    assert codigo == 4
    assert err.startswith("erro: metrica: nao ha ops log de 1999-01-02")
    assert "corrija:" in err
    assert "Traceback" not in err


def test_dia_invalido_e_uso_exit_2(capsys):
    assert m.main(["metrica", "dia", "07/09/2026"]) == 2
    assert "AAAA-MM-DD" in capsys.readouterr().err


def test_ato_desconhecido_exit_2(capsys):
    assert m.main(["metrica", "resumir"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("erro: metrica: ato desconhecido 'resumir'")
    assert "eventos, dia, ate-acerto" in err


def test_tipo_desconhecido_exit_2(capsys):
    assert m.main(["metrica", "eventos", "--tipo", "bagunca"]) == 2
    assert "tipo desconhecido" in capsys.readouterr().err


def test_sem_ato_imprime_uso_exit_2(capsys):
    assert m.main(["metrica"]) == 2
    assert "uso:" in capsys.readouterr().err


def test_ajuda_sai_zero_no_stdout(capsys):
    assert m.main(["metrica", "--ajuda"]) == 0
    assert "uso:" in capsys.readouterr().out


# --- GABARITO: os erros reais de 2026-09-07 ---------------------------------------

@pytest.fixture(scope="module")
def dia_real():
    fonte = m.FonteJsonl()
    alvo = fonte.caminho(DIA_GABARITO)
    if not os.path.isfile(alvo):
        pytest.skip(f"ops log de {DIA_GABARITO} ja rotacionado ({alvo}) — "
                    "gabarito historico, ver #3017")
    return m.classifica(fonte, DIA_GABARITO)


def test_gabarito_cadeia_de_repo_commitar_da_ia(dia_real):
    """O card mede na mao: profundidade 3, acerto no 4o giro, por volta das 15:03."""
    _, _, cadeias = dia_real
    alvo = [c for c in cadeias
            if c["tool"] == "repo" and c["cadeira"] == "ia" and "commitar" in c["atos"]]
    assert alvo, "a cadeia de repo commitar da ia sumiu da classificacao"
    c = max(alvo, key=lambda x: x["profundidade"])
    assert c["profundidade"] == 3
    assert c["acerto_no_giro"] == 4
    assert c["ts_acerto"][11:16] == "15:03"


def test_gabarito_conferir_chapeu_da_ia_e_erro_e_help(dia_real):
    """Chamadas exit 2 de `conferir chapeu` (classe declarada e sem implementacao).

    O card conta DUAS, e eram duas quando ele foi escrito; a medicao aqui achou
    tres — a terceira e das 15:38, depois do card. O dia de hoje ainda esta sendo
    escrito, entao o gabarito e um PISO, nao uma igualdade: o que fica pregado e a
    propriedade (exit 2 conta como erro E como help-pedido), nao a foto do contador.
    """
    giros, _, _ = dia_real
    alvo = [g for g in giros
            if g["tool"] == "conferir" and g["ato"] == "chapeu" and g["cadeira"] == "ia"]
    assert len(alvo) >= 2
    assert all(g["exit_code"] == 2 and g["falhou"] for g in alvo)
    assert sum(1 for g in alvo if g["help"]) >= 2


def test_gabarito_giros_de_help_de_repo_fila_minuta(dia_real):
    """Os tres verbos que a fita chamou sem ato so para descobrir a forma."""
    giros, _, cadeias = dia_real
    help_por_verbo = m.resumo_do_dia(giros, cadeias)["giros_de_help"]
    for verbo in ("repo", "fila", "minuta"):
        assert help_por_verbo.get(verbo, 0) >= 1, f"{verbo} sem giro de help em {DIA_GABARITO}"


def test_gabarito_as_tres_camadas_rodam_sobre_o_dia(dia_real):
    """Aceite do card: as tres camadas sobre o log de 07/09, sem estourar."""
    giros, par, cadeias = dia_real
    evs = m.stream_eventos(giros, cadeias)
    resumo = m.resumo_do_dia(giros, cadeias)
    mae = m.ate_acerto(giros, par)
    assert resumo["total"]["giros"] == len(giros) > 0
    assert sum(1 for e in evs if e["tipo"] == "giro") == len(giros)
    assert resumo["profundidade_de_cadeia"]["maior"] >= 3
    assert mae["resumo"]["pares_com_acerto"] >= 1
    json.dumps({"e": evs, "d": resumo, "m": mae}, ensure_ascii=False)   # serializavel
