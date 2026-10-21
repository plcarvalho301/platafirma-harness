"""A cadência da passada da sonda (bin/_metrica/cadencia.py; spec eixos-do-host R15; card #3922).

O registro real vale um minuto para tudo; o que não é múltiplo de um minuto é recusado; e a regra, sobre registros de
mentira em tmp: eixo em cinco minutos grava de cinco em cinco com janela de cinco, e um serviço dele em um minuto liga
o eixo todo minuto com janela de um. Nada toca o host.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin" / "_metrica"))
sys.path.insert(0, str(RAIZ / "bin" / "_infra"))
import cadencia  # noqa: E402
import eixos  # noqa: E402

INICIO = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)


def _registro(tmp_path, **campos):
    arquivo = tmp_path / "cadencia.json"
    arquivo.write_text(json.dumps({"padrao_s": 60, **campos}), encoding="utf-8")
    return cadencia.carregar(arquivo)


def _passadas(reg, minutos, estado=None):
    """Roda `minutos` passadas de um minuto e devolve, por eixo, os minutos (desde o início) em que ele foi lido."""
    estado = {} if estado is None else estado
    lidos = {eixo: [] for eixo in cadencia.EIXOS}
    for n in range(minutos):
        minuto = INICIO + timedelta(minutes=n)
        for eixo, plano in cadencia.planejar(reg, estado, minuto).items():
            if plano.le:
                lidos[eixo].append(n)
                cadencia.registrar(estado, plano, minuto)
    return lidos


def test_os_eixos_da_cadencia_sao_os_do_modulo_comum():
    assert cadencia.EIXOS == eixos.EIXOS


def test_o_registro_real_vale_um_minuto_para_tudo():
    reg = cadencia.carregar()
    assert reg["padrao_s"] == 60
    assert {cadencia.intervalo(reg, eixo) for eixo in cadencia.EIXOS} == {60}
    assert reg["stacks"] == {} and reg["servicos"] == {}


def test_o_registro_real_grava_os_quatro_eixos_todo_minuto_com_janela_de_um_minuto():
    reg = cadencia.carregar()
    lidos = _passadas(reg, 10)
    assert all(lidos[eixo] == list(range(10)) for eixo in cadencia.EIXOS)
    assert {cadencia.janela_s(reg, eixo) for eixo in cadencia.EIXOS} == {60}


@pytest.mark.parametrize("segundos", [0, 30, 59, 61, 90, 150, -60, 60.0, "60", True, None])
def test_intervalo_que_nao_e_multiplo_de_um_minuto_e_recusado(segundos):
    with pytest.raises(cadencia.RegistroInvalido, match="padrao_s"):
        cadencia.validar({"padrao_s": segundos})


@pytest.mark.parametrize("onde", ["eixos", "stacks", "servicos"])
def test_intervalo_ruim_em_qualquer_nivel_do_registro_e_recusado(onde):
    chave = {"eixos": "ram", "stacks": "core", "servicos": "core/keycloak"}[onde]
    with pytest.raises(cadencia.RegistroInvalido, match="múltiplo de um minuto"):
        cadencia.validar({"padrao_s": 60, onde: {chave: 90}})
    with pytest.raises(cadencia.RegistroInvalido, match="múltiplo de um minuto"):
        cadencia.validar({"padrao_s": 60, onde: {chave: 30}})


def test_o_registro_sem_padrao_recusa_porque_a_cadencia_nao_mora_no_codigo():
    with pytest.raises(cadencia.RegistroInvalido, match="padrao_s"):
        cadencia.validar({"eixos": {"ram": 60}})


@pytest.mark.parametrize("bruto, causa", [
    ({"padrao_s": 60, "eixos": {"disco": 60}}, "eixo fora de"),
    ({"padrao_s": 60, "stacks": {"core/keycloak": 60}}, "sem barra"),
    ({"padrao_s": 60, "servicos": {"keycloak": 60}}, "<stack>/<serviço>"),
    ({"padrao_s": 60, "servicos": {"core/keycloak": {"disco": 60}}}, "eixo fora de"),
    ({"padrao_s": 60, "eixos": 300}, "esperava um objeto"),
    ({"padrao_s": 60, "intervalos": {}}, "campo desconhecido"),
    ([60], "objeto JSON"),
])
def test_forma_errada_do_registro_e_recusada_com_a_causa(bruto, causa):
    with pytest.raises(cadencia.RegistroInvalido, match=causa):
        cadencia.validar(bruto)


def test_registro_ilegivel_ou_ausente_recusa_sem_ler_cadencia_de_outro_lugar(tmp_path):
    with pytest.raises(cadencia.RegistroInvalido):
        cadencia.carregar(tmp_path / "nao-existe.json")
    (tmp_path / "ruim.json").write_text("{nao e json", encoding="utf-8")
    with pytest.raises(cadencia.RegistroInvalido):
        cadencia.carregar(tmp_path / "ruim.json")


def test_comentario_de_registro_com_sublinhado_nao_e_campo(tmp_path):
    reg = _registro(tmp_path, _leia="texto livre")
    assert reg["padrao_s"] == 60


def test_o_intervalo_sai_do_mais_especifico_para_o_mais_geral(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 300}, stacks={"core": 120, "rag": {"ram": 180}},
                    servicos={"core/keycloak": {"ram": 60}})
    assert cadencia.intervalo(reg, "ram", "core/keycloak") == 60, "o serviço manda"
    assert cadencia.intervalo(reg, "ram", "core/landing") == 120, "sem o serviço, a stack"
    assert cadencia.intervalo(reg, "ram", "rag/api") == 180, "a stack por eixo"
    assert cadencia.intervalo(reg, "ram", "wiki/mediawiki") == 300, "sem stack, o eixo"
    assert cadencia.intervalo(reg, "ram") == 300
    assert cadencia.intervalo(reg, "cpu", "wiki/mediawiki") == 60, "sem nada, o padrão"
    assert cadencia.intervalo(reg, "cpu", "core/landing") == 120, "stack em número vale nos quatro eixos"
    assert cadencia.intervalo(reg, "cpu", "core/keycloak") == 120, "serviço só no ram: nos outros eixos, a stack"


def test_eixo_em_cinco_minutos_grava_de_cinco_em_cinco_com_janela_de_cinco(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 300})
    lidos = _passadas(reg, 16)
    assert lidos["ram"] == [0, 5, 10, 15]
    assert lidos["cpu"] == list(range(16)), "os outros eixos seguem no padrão"
    assert cadencia.janela_s(reg, "ram") == 300 and cadencia.janela_s(reg, "cpu") == 60


def test_servico_em_um_minuto_liga_o_eixo_todo_minuto_com_janela_de_um(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 300}, servicos={"core/keycloak": {"ram": 60}})
    lidos = _passadas(reg, 16)
    assert lidos["ram"] == list(range(16)), "o total vem junto, de graça, da mesma coleta"
    assert cadencia.janela_s(reg, "ram") == 60


def test_a_lista_cheia_do_eixo_volta_de_cinco_em_cinco_mesmo_com_o_servico_ligando_o_eixo(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 300}, servicos={"core/keycloak": {"ram": 60}})
    estado = {}
    cheia, so_o_servico = [], []
    for n in range(11):
        minuto = INICIO + timedelta(minutes=n)
        plano = cadencia.planejar(reg, estado, minuto)["ram"]
        (cheia if plano.lista_vence else so_o_servico).append(n)
        assert plano.le
        cadencia.registrar(estado, plano, minuto)
    assert cheia == [0, 5, 10] and so_o_servico == [1, 2, 3, 4, 6, 7, 8, 9]


def test_quem_entra_na_amostra_segue_o_proprio_intervalo(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 300}, servicos={"core/keycloak": {"ram": 60}})
    consumidores = [{"servico": "core/keycloak"}, {"servico": "core/landing"}, {"desvio": "unit_sem_stack"}]
    estado = {}
    primeira = cadencia.planejar(reg, estado, INICIO)["ram"]
    assert [bool(cadencia.entra(reg, primeira, c)) for c in consumidores] == [True, True, True]
    cadencia.registrar(estado, primeira, INICIO)
    segunda = cadencia.planejar(reg, estado, INICIO + timedelta(minutes=1))["ram"]
    assert [bool(cadencia.entra(reg, segunda, c)) for c in consumidores] == [True, False, False], \
        "o serviço de um minuto entra; o resto segue o eixo, que ainda não venceu"


def test_stack_em_dois_minutos_leva_todos_os_servicos_dela(tmp_path):
    reg = _registro(tmp_path, eixos={"vram": 600}, stacks={"motor": {"vram": 120}})
    estado = {}
    entraram = []
    for n in range(5):
        minuto = INICIO + timedelta(minutes=n)
        plano = cadencia.planejar(reg, estado, minuto)["vram"]
        if plano.le:
            entraram.append((n, cadencia.entra(reg, plano, {"servico": "motor/busca"}),
                             cadencia.entra(reg, plano, {"servico": "core/keycloak"})))
            cadencia.registrar(estado, plano, minuto)
    assert entraram == [(0, True, True), (2, True, False), (4, True, False)]


def test_servico_ausente_da_leitura_nao_forca_leitura_a_mais(tmp_path):
    """A entrada vencida conta como atendida na leitura, esteja o serviço entre os maiores ou não."""
    reg = _registro(tmp_path, eixos={"ram": 300}, servicos={"core/raro": {"ram": 120}})
    lidos = _passadas(reg, 7)
    assert lidos["ram"] == [0, 2, 4, 5, 6], "a cada dois minutos pelo serviço, e a lista cheia aos cinco"


def test_estado_vazio_vence_tudo(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 3600})
    planos = cadencia.planejar(reg, {}, INICIO)
    assert all(p.le and p.lista_vence for p in planos.values())


def test_estado_com_instante_ilegivel_vale_vencido(tmp_path):
    reg = _registro(tmp_path, eixos={"ram": 3600})
    plano = cadencia.planejar(reg, {"lista": {"ram": "ontem"}}, INICIO)["ram"]
    assert plano.le


def test_o_estado_vai_e_volta_inteiro_e_sem_resto_provisorio(tmp_path):
    pasta = tmp_path / "var" / "eventos"
    estado = {"lista": {"ram": "2026-10-21T15:00:00Z"}, "reconexoes": {"ops": 7}}
    cadencia.gravar_estado(pasta, estado)
    assert cadencia.ler_estado(pasta) == estado
    assert [p.name for p in pasta.iterdir()] == ["cadencia.json"]


@pytest.mark.parametrize("conteudo", [None, "", "{nao e json", "[1, 2]"])
def test_estado_ausente_ou_ilegivel_vale_estado_vazio(tmp_path, conteudo):
    if conteudo is not None:
        (tmp_path / "cadencia.json").write_text(conteudo, encoding="utf-8")
    assert cadencia.ler_estado(tmp_path) == {}
