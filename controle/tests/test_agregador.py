# Camada 2 do modelo de teste do card #390: unidade sobre a transformacao
# saida-de-verbo -> estado. Caso inegociavel: verbo morto -> indisponivel com
# motivo, nunca ausencia do bloco e nunca zero. Sem subprocess de verdade —
# `chamar()` e sempre trocado por um dublê.
from __future__ import annotations

import json
import time

from harness_controle.agregador import (
    Agregador,
    Sonda,
    SondaGrupo,
    _grava_atomico,
    bloco_de,
)
from harness_controle.verbos import ResultadoVerbo

# --- bloco_de(): a camada inegociavel ---------------------------------------


def test_bloco_de_sucesso_com_objeto():
    r = ResultadoVerbo(ok=True, dados={"resultado": "ok", "servicos": []}, motivo=None,
                        exit_code=0, duracao_seg=0.01)
    b = bloco_de(r, agora=1000.0)
    assert b == {"lido_em": 1000.0, "estado": "ok", "motivo": None,
                 "dados": {"resultado": "ok", "servicos": []}}


def test_bloco_de_sucesso_com_array():
    """fila status --json devolve array no caminho feliz — "erro" nao se
    aplica a um array, nao pode confundir isso com falha."""
    r = ResultadoVerbo(ok=True, dados=[{"persona": "x", "pendentes": 0}], motivo=None,
                        exit_code=0, duracao_seg=0.01)
    b = bloco_de(r, agora=1000.0)
    assert b["estado"] == "ok"
    assert b["dados"] == [{"persona": "x", "pendentes": 0}]


def test_bloco_de_zero_legitimo_nao_vira_indisponivel():
    """0 divergencias e um resultado de leitura bem-sucedida, nao ausencia de
    leitura — a regua do card e clara sobre nao colapsar os dois."""
    r = ResultadoVerbo(ok=True, dados={"resultado": "ok", "verbos": []}, motivo=None,
                        exit_code=0, duracao_seg=0.02)
    b = bloco_de(r, agora=1000.0)
    assert b["estado"] == "ok"
    assert b["dados"]["verbos"] == []


def test_bloco_de_verbo_morto_vira_indisponivel_com_motivo():
    """O caso inegociavel do LOTE 2: processo nao respondeu (timeout) ->
    indisponivel com motivo, NUNCA {"estado": "ok"} nem ausencia de bloco."""
    r = ResultadoVerbo(ok=False, dados=None, motivo="timeout apos 15s",
                        exit_code=None, duracao_seg=15.0)
    b = bloco_de(r, agora=1000.0)
    assert b["estado"] == "indisponivel"
    assert b["motivo"] == "timeout apos 15s"
    assert b["dados"] is None
    assert "lido_em" in b  # idade do dado presente mesmo em falha


def test_bloco_de_erro_do_verbo_vira_indisponivel():
    """Verbo rodou, devolveu JSON valido, mas o proprio JSON e {"erro": ...}
    (ex.: fila_streams.py sem credencial na malha msg) — trata igual a falha
    de execucao: indisponivel com o motivo que o verbo relatou."""
    r = ResultadoVerbo(ok=True, dados={"erro": "nao alcancei a malha msg"}, motivo=None,
                        exit_code=1, duracao_seg=0.05)
    b = bloco_de(r, agora=1000.0)
    assert b["estado"] == "indisponivel"
    assert b["motivo"] == "nao alcancei a malha msg"
    assert b["dados"] is None


def test_bloco_de_indeterminado_nao_e_erro():
    """conferir skill sem --servido: veredito "indeterminado", exit 2 — isto e
    uma leitura BEM-SUCEDIDA (ok=True), so o CONTEUDO diz "sem dado pra
    comparar". Nao e o caso "indisponivel" do agregador."""
    r = ResultadoVerbo(ok=True, dados={"skill": "osint", "veredito": "indeterminado"},
                        motivo=None, exit_code=2, duracao_seg=0.03)
    b = bloco_de(r, agora=1000.0)
    assert b["estado"] == "ok"
    assert b["dados"]["veredito"] == "indeterminado"


def test_bloco_de_usa_time_time_por_padrao():
    r = ResultadoVerbo(ok=True, dados={}, motivo=None, exit_code=0, duracao_seg=0.0)
    antes = time.time()
    b = bloco_de(r)
    depois = time.time()
    assert antes <= b["lido_em"] <= depois


# --- escrita atomica ---------------------------------------------------------


def test_grava_atomico_produz_json_completo_e_valido(tmp_path):
    destino = tmp_path / "sub" / "estado.json"
    _grava_atomico(destino, {"a": 1, "b": [1, 2, 3]})
    assert json.loads(destino.read_text(encoding="utf-8")) == {"a": 1, "b": [1, 2, 3]}
    # nao sobra arquivo temporario
    sobras = list(destino.parent.glob(".estado-*.tmp"))
    assert sobras == []


def test_grava_atomico_sobrescreve_sem_deixar_lixo(tmp_path):
    destino = tmp_path / "estado.json"
    _grava_atomico(destino, {"versao": 1})
    _grava_atomico(destino, {"versao": 2})
    assert json.loads(destino.read_text(encoding="utf-8")) == {"versao": 2}
    assert list(destino.parent.glob(".estado-*.tmp")) == []


# --- orquestracao: sondas simples ------------------------------------------


def _sonda_fixa(nome, resultado: ResultadoVerbo, intervalo=0.02, timeout=1.0):
    return Sonda(nome, intervalo, timeout, lambda: [nome], dict)


def test_ciclo_sonda_grava_estado_ok(tmp_path, monkeypatch):
    ag = Agregador(estado_path=tmp_path / "estado.json", sondas=[], sondas_grupo=[])
    chamadas = []

    def _chamar_falso(argv, timeout, env):
        chamadas.append(argv)
        return ResultadoVerbo(True, {"resultado": "ok"}, None, 0, 0.01)

    monkeypatch.setattr("harness_controle.agregador.chamar", _chamar_falso)
    s = _sonda_fixa("teste", None)
    ag._ciclo_sonda(s)

    assert chamadas == [["teste"]]
    assert ag._estado["teste"]["estado"] == "ok"
    assert json.loads(ag.estado_path.read_text(encoding="utf-8"))["teste"]["estado"] == "ok"


def test_ciclo_sonda_verbo_morto_nunca_derruba_o_agregador(tmp_path, monkeypatch):
    """O ciclo de UMA sonda falhando (timeout) nao levanta excecao pra fora —
    grava indisponivel e segue. Testa a integracao bloco_de() + persistencia,
    nao so a funcao pura."""
    ag = Agregador(estado_path=tmp_path / "estado.json", sondas=[], sondas_grupo=[])

    def _chamar_falso(argv, timeout, env):
        raise AssertionError("nao deveria ser chamado neste teste")

    # Simula timeout diretamente via ResultadoVerbo, sem precisar de subprocess real.
    def _chamar_timeout(argv, timeout, env):
        return ResultadoVerbo(False, None, f"timeout apos {timeout}s", None, timeout)

    monkeypatch.setattr("harness_controle.agregador.chamar", _chamar_timeout)
    s = _sonda_fixa("infra_estado", None, timeout=5.0)
    ag._ciclo_sonda(s)  # nao deve levantar

    bloco = ag._estado["infra_estado"]
    assert bloco["estado"] == "indisponivel"
    assert "timeout" in bloco["motivo"]
    assert bloco["dados"] is None


def test_loop_de_uma_sonda_lenta_nao_atrasa_outra(tmp_path, monkeypatch):
    """"Timer independente por verbo. Verbo lento nao segura os outros" — a
    exigencia central do LOTE 2. Uma sonda "lenta" (chamar() dorme) roda numa
    thread separada de uma sonda "rapida"; a rapida acumula varios ciclos
    enquanto a lenta ainda esta no primeiro."""
    ag = Agregador(estado_path=tmp_path / "estado.json", sondas=[], sondas_grupo=[])
    contagem_rapida = {"n": 0}

    def _chamar(argv, timeout, env):
        nome = argv[0]
        if nome == "lenta":
            time.sleep(0.5)
            return ResultadoVerbo(True, {"ok": True}, None, 0, 0.5)
        contagem_rapida["n"] += 1
        return ResultadoVerbo(True, {"n": contagem_rapida["n"]}, None, 0, 0.001)

    monkeypatch.setattr("harness_controle.agregador.chamar", _chamar)

    lenta = Sonda("lenta", 999, 5.0, lambda: ["lenta"], dict)
    rapida = Sonda("rapida", 0.02, 5.0, lambda: ["rapida"], dict)
    ag.sondas = [lenta, rapida]

    ag.iniciar()
    try:
        time.sleep(0.3)
        with ag._lock:
            n_durante = ag._estado.get("rapida", {}).get("dados", {}).get("n", 0)
        # a rapida deve ter progredido varias vezes enquanto a lenta ainda dorme
        assert n_durante >= 5
        with ag._lock:
            assert "lenta" not in ag._estado or ag._estado["lenta"]["dados"] is None
    finally:
        ag.parar(timeout=2.0)


# --- orquestracao: sondas em grupo (cadeiras/skills) -------------------------


def test_ciclo_sonda_grupo_isola_falha_por_item(tmp_path, monkeypatch):
    """Um item do grupo falhando (ex.: uma cadeira sem persona legivel) nao
    derruba os outros itens nem o bloco inteiro — cada item carrega o proprio
    estado/motivo, e "itens" sempre tem todos os itens descobertos."""
    ag = Agregador(estado_path=tmp_path / "estado.json", sondas=[], sondas_grupo=[])

    def _chamar(argv, timeout, env):
        _, cadeira, *_ = argv
        if cadeira == "quebrada":
            return ResultadoVerbo(False, None, "nao existe persona-quebrada.md", None, 0.01)
        return ResultadoVerbo(True, {"cadeira": cadeira, "atualizado": False}, None, 0, 0.01)

    monkeypatch.setattr("harness_controle.agregador.chamar", _chamar)

    g = SondaGrupo(
        "cadeiras", 999, 5.0,
        lambda: ["TI", "quebrada", "IA"],
        lambda c: ["monta-sessao", c, "--json", "--sem-atualizar"],
        chave_item="cadeira",
    )
    ag._ciclo_sonda_grupo(g)

    bloco = ag._estado["cadeiras"]
    assert bloco["estado"] == "ok"  # o GRUPO leu — a falha e de UM item
    por_cadeira = {i["cadeira"]: i for i in bloco["itens"]}
    assert set(por_cadeira) == {"TI", "quebrada", "IA"}
    assert por_cadeira["quebrada"]["estado"] == "indisponivel"
    assert por_cadeira["TI"]["estado"] == "ok"
    assert por_cadeira["IA"]["estado"] == "ok"


def test_ciclo_sonda_grupo_sem_itens_vira_indisponivel_nao_omisso(tmp_path, monkeypatch):
    """Lista de itens vazia (ex.: diretorio de skills nao existe ainda) nao e
    silenciosamente omitida — vira bloco indisponivel com motivo, mesma regua
    de ausencia-nunca-e-saude."""
    ag = Agregador(estado_path=tmp_path / "estado.json", sondas=[], sondas_grupo=[])
    monkeypatch.setattr("harness_controle.agregador.chamar",
                         lambda *a, **k: (_ for _ in ()).throw(AssertionError("nao deveria chamar")))

    g = SondaGrupo("skills", 999, 5.0, list, lambda s: ["conferir", "skill", s], chave_item="skill")
    ag._ciclo_sonda_grupo(g)

    bloco = ag._estado["skills"]
    assert bloco["estado"] == "indisponivel"
    assert bloco["itens"] == []
    assert bloco["motivo"]


def test_agregador_nao_escreve_nada_alem_do_proprio_estado(tmp_path, monkeypatch):
    """"O agregador nao escreve em lugar nenhum alem do proprio arquivo de
    estado" — confere que o unico artefato novo em tmp_path e o estado.json."""
    ag = Agregador(estado_path=tmp_path / "controle" / "estado.json", sondas=[], sondas_grupo=[])
    monkeypatch.setattr(
        "harness_controle.agregador.chamar",
        lambda *a, **k: ResultadoVerbo(True, {"ok": True}, None, 0, 0.01),
    )
    ag._ciclo_sonda(_sonda_fixa("x", None))

    caminhos = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert caminhos == ["controle/estado.json"]
