"""metrica investigar (card #3355; arq:0123 regras 8, 10 e 15): a linha inteira do bruto, só com incidente aberto.

Tudo contra uma pasta em tmp_path, um rastreador de mentira (o `tarefas ler`), uma API falsa (ou um servidor HTTP de
loopback) e o bruto montado à mão: sem a porta, sem o banco e sem o log real. O que não se prova aqui é o SQL de D5.10 e
D5.11, que o Postgres executa (provado em `rag/tests/test_log_evento.py` com o dublê e, no ar, pela conferência do card).

Os três desfechos do aceite: sem `--incidente` sai 2; incidente que não está aberto sai 4; incidente aberto devolve a
linha inteira (com o argumento e o texto do turno), grava um `leitura_bruto` com o número e cita as linhas na partição.
"""
import hashlib
import http.server
import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import date
from pathlib import Path

import pytest

import oplog
import oplog_extracao as ex

RAIZ = Path(__file__).resolve().parents[2]
METRICA = RAIZ / "bin" / "metrica"
_spec = importlib.util.spec_from_loader("metrica_investigar", importlib.machinery.SourceFileLoader(
    "metrica_investigar", str(METRICA)))
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)
inv = m._investigar

DIA = "2026-09-23"
DIA_FORA_DO_BRUTO = "2026-09-10"
HOJE = date(2026, 10, 8)
INCIDENTE = 3400
SESSAO = "8f576862-23dd-4880-856f-4c9353096ee1"
SESSAO2 = "0a1b2c3d-1111-4222-8333-444455556666"
ENV = {"PF_SESSAO": SESSAO, "PF_CADEIRA": "ti", "PF_ORDEM_ID": "o20261008T100000-aaaaaa"}


# --- andaime --------------------------------------------------------------------------------------

def _id(n):
    return str(uuid.UUID(int=n))


def _ts(n):
    return f"{DIA}T10:{n:02d}:00.000-03:00"


def giro(n, *, sessao=SESSAO, tool="acervo", ato="ler", exit_code=0, chave=True, **mais):
    reg = {"ts": _ts(n), "schema_v": 1, "instancia": "casa", "cadeira": "ti", "ordem_id": "o1", "sessao_id": sessao,
           "tool": tool, "ato": ato, "exit_code": exit_code, "dur_ms": 12, "args": f"SEGREDO-ARGS-{n}",
           "sub": "SEGREDO-SUB", "origem": "cadeira", "mapa_v": None}
    if chave:
        reg["evento_id"] = _id(n)
    reg.update(mais)
    return reg


def turno(n, sessao=SESSAO):
    return {"ts": _ts(n), "evento_id": _id(n), "schema_v": 1, "tool": "sessao", "evento": "turno", "sessao_id": sessao,
            "turno_id": "T1", "turno_fonte": "hook", "texto": "SEGREDO-TEXTO", "texto_bytes": 13, "origem": "cadeira"}


def dia_de_investigacao():
    """Sete linhas físicas: a 1 e a 7 são giros ok da sessão; a 2 é execução (exit 3); a 3 é o turno com o texto do dono;
    a 4 é giro de outra sessão; a 5 é linha antiga, sem chave; a 6 não é JSON."""
    return [giro(0), giro(1, tool="repo", ato="commitar", exit_code=3, erro="SEGREDO-ERRO"), turno(2),
            giro(3, sessao=SESSAO2),
            {"ts": _ts(4), "cadeira": "ti", "ordem_id": "o2", "sessao_id": SESSAO2, "tool": "mesa", "ato": "ver",
             "exit_code": 0, "args": "SEGREDO-ARGS-ANTIGA"},
            "isto nao e json", giro(6)]


def escreve_dia(pasta, linhas=None, dia=DIA):
    linhas = dia_de_investigacao() if linhas is None else linhas
    corpo = "\n".join(l if isinstance(l, str) else json.dumps(l, ensure_ascii=False) for l in linhas) + "\n"
    (Path(pasta) / oplog.nome_do_dia(dia)).write_bytes(corpo.encode("utf-8"))
    return corpo.encode("utf-8")


def aberto(estado="Mitigado", fase="incidente"):
    def tarefas(numero):
        return 0, f"# titulo do card\n#{numero} · null · {estado} ({fase}) · cadeira: ia\n\ncorpo do card\n", ""
    return tarefas


def sem_tarefas(numero):
    raise AssertionError("o rastreador não devia ser consultado")


class ApiFalsa:
    """O que a API devolve de D5.10 e D5.11. `tem` = os evento_id que a partição já tem (None = todos)."""

    def __init__(self, tem=None, itens=(), erro_post=None, erro_get=None, ausentes_no_post=None):
        self.tem, self.itens, self.erro_post, self.erro_get = tem, list(itens), erro_post, erro_get
        self.ausentes_no_post = ausentes_no_post
        self.chamadas = []

    def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,), contrato="1.5.0"):
        self.chamadas.append((metodo, caminho, corpo, dict(params or {}), contrato))
        if metodo == "POST" and caminho == "/acervo/log/citacoes":
            if self.erro_post:
                raise self.erro_post
            ids = [i["evento_id"] for i in corpo["itens"]]
            ausentes = (self.ausentes_no_post if self.ausentes_no_post is not None
                        else [i for i in ids if self.tem is not None and i not in self.tem])
            return 200, {"incidente": corpo["incidente"], "citadas": len(ids) - len(ausentes), "ja_citadas": 0,
                         "conteudo_novo": len(ids) - len(ausentes), "ausentes": ausentes}
        if metodo == "GET" and caminho.endswith("/conteudo"):
            if self.erro_get:
                raise self.erro_get
            return 200, {"dia": caminho.split("/")[-2], "cobertura": "completo", "motivo": None,
                         "versao_extrator": "abc", "itens": self.itens[:params["limite"]], "proximo": None}
        raise AssertionError((metodo, caminho))

    def posts(self):
        return [c for c in self.chamadas if c[0] == "POST"]

    def gets(self):
        return [c for c in self.chamadas if c[0] == "GET"]


def roda(pasta, *args, api=None, tarefas=aberto(), ambiente=None, hoje=HOJE):
    out, err = [], []
    codigo = inv.investigar(list(args), api=api if api is not None else ApiFalsa(), tarefas=tarefas,
                            ambiente=ENV if ambiente is None else ambiente, saida=out.append, saida_erro=err.append,
                            diretorio_=pasta, hoje=hoje)
    return codigo, "\n".join(out), "\n".join(err)


def leituras(pasta):
    """Os `leitura_bruto` gravados na pasta (o evento cai no arquivo de hoje, seja qual for o dia investigado)."""
    achados = []
    for dia in oplog.dias_no_disco(pasta):
        achados += [r for r in oplog.ler(dia, diretorio_=pasta) if r.get("evento") == "leitura_bruto"]
    return achados


def linhas_do_arquivo(dados):
    return dados.split(b"\n")


# --- os três desfechos do aceite ------------------------------------------------------------------

def test_sem_incidente_sai_2_e_diz_o_caminho_sem_consultar_nem_ler(tmp_path):
    escreve_dia(tmp_path)
    codigo, out, err = roda(tmp_path, DIA, tarefas=sem_tarefas)
    assert codigo == 2 and out == ""
    assert "sem --incidente" in err and "corrija:" in err and "não abre incidente" in err
    assert leituras(tmp_path) == [], "nada foi lido, nada se registra"


@pytest.mark.parametrize("estado, fase", [("Resolvido", "terminal"), ("Entregue", "terminal"),
                                          ("Em execução", "delivery"), ("Captada", "funil")])
def test_incidente_que_nao_esta_aberto_sai_4_e_nao_devolve_linha(tmp_path, estado, fase):
    escreve_dia(tmp_path)
    api = ApiFalsa()
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), tarefas=aberto(estado, fase), api=api)
    assert codigo == 4 and out == "" and f"#{INCIDENTE} está «{estado}» ({fase}): não é incidente aberto" in err
    assert "corrija:" in err and "tarefas listar --estado" in err
    assert "SEGREDO" not in err and leituras(tmp_path) == [] and api.chamadas == []


def test_incidente_que_nao_existe_sai_4(tmp_path):
    escreve_dia(tmp_path)
    codigo, out, err = roda(tmp_path, DIA, "--incidente", "99999999",
                            tarefas=lambda n: (1, "", f"item {n} não existe\n"))
    assert codigo == 4 and out == "" and "o incidente #99999999 não existe" in err and "tarefas listar" in err


@pytest.mark.parametrize("estado", ["Detectado", "Em mitigação", "Mitigado"])
def test_incidente_aberto_devolve_a_linha_inteira_com_argumento_e_texto_do_turno(tmp_path, estado):
    escreve_dia(tmp_path)
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO[:8],
                            tarefas=aberto(estado))
    assert codigo == 0, err
    r = json.loads(out)
    assert r["fonte"] == "bruto" and r["incidente"] == INCIDENTE and r["estado_do_incidente"] == estado
    por_n = {l["linha_n"]: l for l in r["linhas"]}
    assert sorted(por_n) == [1, 2, 3, 7], "a sessão inteira: os giros, a execução e a linha de turno"
    assert por_n[1]["linha"]["args"] == "SEGREDO-ARGS-0" and por_n[1]["linha"]["sub"] == "SEGREDO-SUB"
    assert por_n[2]["linha"]["erro"] == "SEGREDO-ERRO"
    assert por_n[3]["linha"]["texto"] == "SEGREDO-TEXTO", "o turno vem com a mensagem do dono"
    assert por_n[1]["evento_id"] == _id(0)
    assert r["devolvidas"] == 4 and r["omitidas"] == 0 and r["ha_mais"] is False
    assert r["leitura_bruto"] == "gravada" and r["linhas_ilegiveis"] == 1


def test_a_leitura_grava_o_evento_com_o_incidente_os_filtros_e_quantas_linhas_saiu_sem_o_conteudo(tmp_path):
    escreve_dia(tmp_path)
    roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO[:8], "--limite", "3")
    (evento,) = leituras(tmp_path)
    assert evento["tool"] == "metrica" and evento["ato"] == "investigar"
    assert (evento["incidente"], evento["dia"], evento["origem_leitura"]) == (INCIDENTE, DIA, "bruto")
    assert (evento["filtro_sessao"], evento["filtro_tool"], evento["filtro_classe"]) == (SESSAO[:8], None, None)
    assert (evento["linhas_devolvidas"], evento["linhas_omitidas"]) == (3, 1)
    assert (evento["sessao_id"], evento["cadeira"], evento["ordem_id"]) == (SESSAO, "ti", ENV["PF_ORDEM_ID"])
    assert oplog.tipo_da_linha(evento) == "leitura" and oplog.validar(evento) == []
    assert "SEGREDO" not in json.dumps(evento, ensure_ascii=False), "o evento é rastro: não leva a linha"


# --- o que casa -------------------------------------------------------------------------------------

def _numeros(out):
    return sorted(l["linha_n"] for l in json.loads(out)["linhas"])


def test_a_sessao_pega_o_turno_e_a_tool_nao(tmp_path):
    escreve_dia(tmp_path)
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--sessao", SESSAO[:8])[1]) == [1, 2, 3, 7]
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo")[1]) == [1, 4, 7], \
        "a linha de turno não é chamada de verbo: --tool não a pega"
    codigo, out, _ = roda(tmp_path, DIA, "--incidente", "1", "--tool", "sessao")
    assert codigo == 1 and out == "", "mesmo com `tool: sessao` na linha, o turno não é giro e --tool não o cita"


def test_tool_e_sessao_se_combinam_e_a_classe_separa_a_execucao(tmp_path):
    escreve_dia(tmp_path)
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo", "--sessao", SESSAO[:8])[1]) == [1, 7]
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--classe", "execucao")[1]) == [2]
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--classe", "ok")[1]) == [1, 4, 5, 7]


def test_a_sessao_casa_por_prefixo_e_pelo_id_inteiro_sem_diferenciar_maiuscula(tmp_path):
    escreve_dia(tmp_path)
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--sessao", SESSAO)[1]) == [1, 2, 3, 7]
    assert _numeros(roda(tmp_path, DIA, "--incidente", "1", "--sessao", SESSAO[:6].upper())[1]) == [1, 2, 3, 7]


def test_nada_que_case_sai_1_com_o_caminho_e_o_rastro_fica_com_zero_linhas(tmp_path):
    escreve_dia(tmp_path)
    api = ApiFalsa()
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--tool", "nao-existe", api=api)
    assert codigo == 1 and out == "" and f"nenhuma linha de {DIA} casa com o filtro" in err and "corrija:" in err
    (evento,) = leituras(tmp_path)
    assert evento["linhas_devolvidas"] == 0 and evento["filtro_tool"] == "nao-existe"
    assert api.posts() == [], "nada a citar"


def test_o_limite_corta_o_que_sai_diz_quanto_ficou_e_so_o_devolvido_e_citado(tmp_path):
    escreve_dia(tmp_path)
    api = ApiFalsa()
    codigo, out, _ = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO[:8], "--limite", "2",
                          api=api)
    r = json.loads(out)
    assert codigo == 0 and r["devolvidas"] == 2 and r["omitidas"] == 2 and r["ha_mais"] is True
    assert [i["evento_id"] for i in api.posts()[0][2]["itens"]] == [_id(0), _id(1)]


def test_o_teto_de_bytes_corta_antes_da_porta_e_diz(tmp_path, monkeypatch):
    dados = escreve_dia(tmp_path)
    primeira = linhas_do_arquivo(dados)[0]
    monkeypatch.setattr(inv, "MAX_BYTES", len(primeira) + oplog.SOBRA_POR_LINHA + 1)
    _, out, _ = roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo", "--sessao", SESSAO[:8])
    r = json.loads(out)
    assert r["devolvidas"] == 1 and r["omitidas"] == 1 and r["ha_mais"] is True
    assert len(out) < 50_000, "cabe nos 50 KB da porta"


def test_a_linha_inteira_que_passa_de_tudo_ainda_sai_uma(tmp_path, monkeypatch):
    """O teto de bytes nunca devolve zero linhas quando algo casou: a primeira sai sempre."""
    escreve_dia(tmp_path)
    monkeypatch.setattr(inv, "MAX_BYTES", 10)
    r = json.loads(roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo")[1])
    assert r["devolvidas"] == 1 and r["omitidas"] == 2


# --- a citação (D5.10) -----------------------------------------------------------------------------------

def test_as_linhas_devolvidas_atravessam_inteiras_com_o_mesmo_evento_id_e_o_sha256_dos_bytes(tmp_path):
    dados = escreve_dia(tmp_path)
    api = ApiFalsa()
    codigo, out, _ = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO2[:8], api=api)
    assert codigo == 0
    ((metodo, caminho, corpo, _params, contrato),) = api.posts()
    assert (metodo, caminho, contrato) == ("POST", "/acervo/log/citacoes", "1.6.0")
    assert corpo["autor"] == "ti" and corpo["incidente"] == INCIDENTE
    por_id = {i["evento_id"]: i for i in corpo["itens"]}
    brutas = linhas_do_arquivo(dados)
    assert set(por_id) == {_id(3), oplog.evento_id_da_linha(DIA, 5)}, "a linha sem chave ganha o uuid v5 do extrator"
    assert por_id[_id(3)]["linha_sha256"] == hashlib.sha256(brutas[3]).hexdigest()
    assert por_id[oplog.evento_id_da_linha(DIA, 5)]["linha_sha256"] == hashlib.sha256(brutas[4]).hexdigest()
    assert por_id[_id(3)]["linha"]["args"] == "SEGREDO-ARGS-3" and por_id[_id(3)]["linha"]["sub"] == "SEGREDO-SUB"
    assert json.loads(out)["citacao"] == {"estado": "gravada", "citadas": 2, "ja_citadas": 0, "ausentes": 0}


def test_a_chave_da_linha_citada_e_a_mesma_que_o_extrator_da_a_ela(tmp_path):
    """Se a citação usasse outra chave, ela cairia fora do evento que a passada do dia gravou."""
    dados = escreve_dia(tmp_path)
    for n, bruta, reg in oplog.linhas_do_dia(dados):
        if reg is None:
            continue
        cit = ex.item_de_citacao(reg, bruta, DIA, n)
        assert cit["evento_id"] == ex.para_item(reg, DIA, n, ex.Invalidos())["evento"]["evento_id"], n


def test_a_linha_com_nul_vai_com_o_nul_trocado_e_o_sha256_continua_o_dos_bytes(tmp_path):
    linhas = [giro(0, args="a\u0000b")]
    dados = escreve_dia(tmp_path, linhas)
    cit = ex.item_de_citacao(json.loads(linhas_do_arquivo(dados)[0]), linhas_do_arquivo(dados)[0], DIA, 1)
    assert cit["linha"]["args"] == "a�b"
    assert cit["linha_sha256"] == hashlib.sha256(linhas_do_arquivo(dados)[0]).hexdigest()


def test_o_dia_que_a_particao_ainda_nao_tem_fica_pendente_e_diz_quando_repetir(tmp_path):
    escreve_dia(tmp_path)
    api = ApiFalsa(tem=set())
    codigo, out, _ = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--tool", "acervo", api=api)
    c = json.loads(out)["citacao"]
    assert codigo == 0 and c["estado"] == "pendente" and c["ausentes"] == 3
    assert "2026-09-24 00:20" in c["proximo_passo"] and f"--incidente {INCIDENTE}" in c["proximo_passo"]
    assert "35 dias" in c["proximo_passo"], "a linha segue no bruto: repetir não é urgência"


def test_parte_das_linhas_na_particao_e_citacao_parcial(tmp_path):
    escreve_dia(tmp_path)
    api = ApiFalsa(tem={_id(0)})
    c = json.loads(roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo", api=api)[1])["citacao"]
    assert c["estado"] == "parcial" and (c["citadas"], c["ausentes"]) == (1, 2)


@pytest.mark.parametrize("erro, codigo_esperado", [
    (ex.Falha(3, "POST /acervo/log/citacoes: http://127.0.0.1:8100 não respondeu (Connection refused)"), 3),
    (ex.Falha(4, "POST /acervo/log/citacoes: HTTP 403"), 4),
    (ex.Falha(5, "POST /acervo/log/citacoes: a conexão caiu"), 5),
    (ex.Falha(1, "POST /acervo/log/citacoes: HTTP 422 CorpoInvalido", "CorpoInvalido"), 5),
    (ex.Falha(1, "POST /acervo/log/citacoes: HTTP 409 ConteudoDivergente", "ConteudoDivergente"), 4),
])
def test_citacao_que_nao_gravou_ainda_entrega_a_linha_e_sai_com_o_codigo_da_falha(tmp_path, erro, codigo_esperado):
    escreve_dia(tmp_path)
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--tool", "acervo",
                            api=ApiFalsa(erro_post=erro))
    r = json.loads(out)
    assert codigo == codigo_esperado and r["devolvidas"] == 3 and r["linhas"][0]["linha"]["args"] == "SEGREDO-ARGS-0"
    assert r["citacao"]["estado"] == "nao_gravada" and r["citacao"]["codigo"] == codigo_esperado
    assert "corrija:" in err and "SEGREDO" not in err


def test_a_divergencia_de_conteudo_manda_para_a_mesa_de_seguranca_e_nao_para_repetir(tmp_path):
    escreve_dia(tmp_path)
    erro = ex.Falha(1, "POST /acervo/log/citacoes: HTTP 409 ConteudoDivergente", "ConteudoDivergente")
    _, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--tool", "acervo", api=ApiFalsa(erro_post=erro))
    proximo = json.loads(out)["citacao"]["proximo_passo"]
    assert "integridade" in proximo and "mesa de seguranca" in proximo and "não repita" in proximo
    assert "mesa de seguranca" in err


# --- sem rastro não sai linha -------------------------------------------------------------------------------

def test_rastro_que_nao_gravou_e_exit_5_e_nao_devolve_nada(tmp_path, monkeypatch):
    escreve_dia(tmp_path)
    monkeypatch.setattr(oplog, "emitir", lambda *a, **k: False)
    api = ApiFalsa()
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), api=api)
    assert codigo == 5 and out == "" and "leitura_bruto" in err and "nada foi devolvido" in err
    assert "SEGREDO" not in err and api.chamadas == [], "sem rastro, nem a citação sai"


def test_ler_inteiras_exige_o_numero_do_incidente(tmp_path):
    escreve_dia(tmp_path)
    for ruim in (None, 0, -1, "3400", True, 3.5):
        with pytest.raises(ValueError, match="incidente"):
            oplog.ler_inteiras(DIA, incidente=ruim, diretorio_=tmp_path)
    assert leituras(tmp_path) == []
    with pytest.raises(TypeError):
        oplog.ler_inteiras(DIA, diretorio_=tmp_path)             # sem `incidente` nem chama


def test_ler_inteiras_de_dia_sem_arquivo_volta_ausente_e_sem_rastro(tmp_path):
    achado = oplog.ler_inteiras(DIA, incidente=INCIDENTE, diretorio_=tmp_path)
    assert achado.ausente and achado.linhas == [] and achado.registrada is False and leituras(tmp_path) == []


def test_ler_inteiras_grava_o_rastro_antes_de_entregar(tmp_path):
    escreve_dia(tmp_path)
    achado = oplog.ler_inteiras(DIA, incidente=INCIDENTE, casa=lambda r: r.get("tool") == "acervo",
                                filtros={"tool": "acervo"}, ambiente=ENV, diretorio_=tmp_path)
    assert achado.registrada and [n for n, _, _ in achado.linhas] == [1, 4, 7]
    assert [e["linhas_devolvidas"] for e in leituras(tmp_path)] == [3]
    assert all(isinstance(b, bytes) and isinstance(r, dict) for _, b, r in achado.linhas)


def test_a_leitura_da_linha_inteira_cruza_a_particao_so_como_topo_sem_o_incidente():
    reg = {"ts": _ts(0), "evento_id": _id(9), "schema_v": 1, "tool": "metrica", "ato": "investigar",
           "evento": "leitura_bruto", "sessao_id": SESSAO, "cadeira": "ti", "incidente": INCIDENTE, "dia": DIA,
           "origem_leitura": "bruto", "filtro_sessao": "ffffffff", "linhas_devolvidas": 3, "linhas_omitidas": 0}
    item = ex.para_item(reg, DIA, 5, ex.Invalidos())
    assert set(item) == {"evento"} and item["evento"]["tipo"] == "leitura"
    assert "ffffffff" not in json.dumps(item) and str(INCIDENTE) not in json.dumps(item)


# --- o dia que já saiu do bruto (D5.11) ---------------------------------------------------------------------

def _guardada(n, **mais):
    linha = {"evento_id": _id(n), "tool": "acervo", "args": f"SEGREDO-GUARDADO-{n}", "sessao_id": SESSAO}
    return {"evento_id": _id(n), "tipo": "giro", "ts": f"{DIA_FORA_DO_BRUTO}T10:00:00-03:00", "linha_n": n,
            "sessao_id": SESSAO, "cadeira": "ti", "tool": "acervo", "classe": "execucao", "amostra": True,
            "incidentes": [3300], "linha": linha, "linha_sha256": "a" * 64, **mais}


def test_dia_que_saiu_do_bruto_devolve_a_amostra_e_a_citada_da_particao_e_cita_de_novo(tmp_path):
    api = ApiFalsa(itens=[_guardada(1), _guardada(2, amostra=False, incidentes=[])])
    codigo, out, _ = roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", str(INCIDENTE), "--tool", "acervo",
                          "--classe", "execucao", "--sessao", SESSAO[:8], api=api)
    assert codigo == 0
    r = json.loads(out)
    assert r["fonte"] == "particao" and r["devolvidas"] == 2 and r["omitidas"] is None and r["ha_mais"] is False
    assert r["linhas"][0]["linha"]["args"] == "SEGREDO-GUARDADO-1" and r["linhas"][0]["incidentes_antes"] == [3300]
    assert r["linhas"][0]["amostra"] is True and r["linhas"][1]["amostra"] is False
    assert r["cobertura"] == {"cobertura": "completo", "motivo": None, "versao_extrator": "abc"}
    ((_, caminho, _, params, contrato),) = api.gets()
    assert caminho == f"/acervo/log/dias/{DIA_FORA_DO_BRUTO}/conteudo" and contrato == "1.6.0"
    assert params == {"limite": 51, "sessao": SESSAO[:8], "tool": "acervo", "classe": "execucao"}
    ((_, _, corpo, _, _),) = api.posts()
    assert corpo["incidente"] == INCIDENTE and [i["evento_id"] for i in corpo["itens"]] == [_id(1), _id(2)]
    assert set(corpo["itens"][0]) == {"evento_id", "linha", "linha_sha256"} and corpo["itens"][0]["linha_sha256"] == "a" * 64
    (evento,) = leituras(tmp_path)
    assert evento["origem_leitura"] == "particao" and evento["linhas_devolvidas"] == 2
    assert evento["linhas_omitidas"] is None and evento["dia"] == DIA_FORA_DO_BRUTO


def test_dia_que_saiu_do_bruto_sem_nada_guardado_sai_1_com_a_frase_do_card(tmp_path):
    api = ApiFalsa(itens=[])
    codigo, out, err = roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", str(INCIDENTE), api=api)
    assert codigo == 1 and out == ""
    assert f"sem linha inteira guardada para {DIA_FORA_DO_BRUTO}" in err and "corrija:" in err
    assert api.posts() == []
    (evento,) = leituras(tmp_path)
    assert evento["linhas_devolvidas"] == 0 and evento["origem_leitura"] == "particao"


def test_o_limite_na_particao_pede_um_a_mais_para_saber_se_tem_mais(tmp_path):
    api = ApiFalsa(itens=[_guardada(1), _guardada(2), _guardada(3)])
    r = json.loads(roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", "1", "--limite", "2", api=api)[1])
    assert r["devolvidas"] == 2 and r["ha_mais"] is True
    assert api.gets()[0][3]["limite"] == 3 and len(api.posts()[0][2]["itens"]) == 2


@pytest.mark.parametrize("erro, esperado", [
    (ex.Falha(3, "GET .../conteudo: http://127.0.0.1:8100 não respondeu (Connection refused)"), 3),
    (ex.Falha(4, "GET .../conteudo: HTTP 401"), 4),
    (ex.Falha(5, "GET .../conteudo: a conexão caiu"), 5),
])
def test_particao_fora_do_ar_sai_com_o_codigo_da_falha_sem_rastro_porque_nada_foi_lido(tmp_path, erro, esperado):
    codigo, out, err = roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", "1", api=ApiFalsa(erro_get=erro))
    assert codigo == esperado and out == "" and "a partição não respondeu" in err and "infra saude" in err
    assert leituras(tmp_path) == []


def test_resposta_fora_do_contrato_da_particao_e_exit_5(tmp_path):
    class Torta(ApiFalsa):
        def chamar(self, *a, **k):
            return 200, {"itens": "isto não é lista"}
    codigo, _, err = roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", "1", api=Torta())
    assert codigo == 5 and "fora do contrato (D5.11)" in err


def test_rastro_que_nao_gravou_na_leitura_da_particao_tambem_e_exit_5(tmp_path, monkeypatch):
    monkeypatch.setattr(oplog, "emitir", lambda *a, **k: False)
    api = ApiFalsa(itens=[_guardada(1)])
    codigo, out, err = roda(tmp_path, DIA_FORA_DO_BRUTO, "--incidente", "1", api=api)
    assert codigo == 5 and out == "" and "nada foi devolvido" in err and api.posts() == []


# --- o incidente: o cabeçalho, nunca o corpo ------------------------------------------------------------------

def test_o_corpo_do_card_nao_forja_o_estado(tmp_path):
    """Um incidente resolvido cujo corpo traz uma linha igual ao cabeçalho de um aberto não abre a leitura."""
    escreve_dia(tmp_path)

    def forjado(numero):
        return 0, (f"# titulo\n#{numero} · null · Resolvido (terminal) · cadeira: ia\n\n"
                   f"#{numero} · null · Mitigado (incidente) · cadeira: ia\n"), ""
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), tarefas=forjado)
    assert codigo == 4 and out == "" and "Resolvido" in err


def test_cabecalho_do_card_que_nao_tem_a_forma_de_sempre_e_exit_5(tmp_path):
    escreve_dia(tmp_path)
    codigo, _, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), tarefas=lambda n: (0, "só uma linha\n", ""))
    assert codigo == 5 and "cabeçalho do card" in err
    codigo, _, _ = roda(tmp_path, DIA, "--incidente", str(INCIDENTE),
                        tarefas=lambda n: (0, "# t\n#1 · null · Mitigado (incidente)\n", ""))
    assert codigo == 5, "o número do cabeçalho tem de ser o pedido"


def test_rastreador_fora_do_ar_e_exit_3(tmp_path, monkeypatch):
    escreve_dia(tmp_path)
    codigo, out, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), tarefas=lambda n: (7, "", "conexão recusada\n"))
    assert codigo == 3 and out == "" and "tarefas ler" in err and "conexão recusada" in err
    monkeypatch.setenv("PF_TAREFAS_BIN", str(tmp_path / "nao-existe"))
    codigo, _, err = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), tarefas=None)
    assert codigo == 3 and "não executou" in err


# --- os argumentos ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("args, trecho", [
    ([], "falta o dia"),
    (["ontem", "--incidente", "1"], "dia inválido"),
    (["2026-10-09", "--incidente", "1"], "ainda não existe"),
    ([DIA, "--incidente", "0"], "não é número de card"),
    ([DIA, "--incidente", "abc"], "não é número de card"),
    ([DIA, "--incidente"], "--incidente pede um valor"),
    ([DIA, "--incidente", "1", "--classe", "palpite"], "fora do vocabulário"),
    ([DIA, "--incidente", "1", "--limite", "0"], "fora de 1.."),
    ([DIA, "--incidente", "1", "--limite", "501"], "fora de 1.."),
    ([DIA, "--incidente", "1", "--limite", "x"], "fora de 1.."),
    ([DIA, "--incidente", "1", "--sessao", "XYZ"], "não é prefixo de sessao_id"),
    ([DIA, "--incidente", "1", "--tool", "a b"], "não é nome de verbo"),
    ([DIA, "--incidente", "1", "--fonte", "bruto"], "argumento desconhecido"),
    ([DIA, "2026-09-24", "--incidente", "1"], "argumento desconhecido"),
])
def test_uso_errado_sai_2_antes_de_consultar_o_rastreador(tmp_path, args, trecho):
    codigo, out, err = roda(tmp_path, *args, tarefas=sem_tarefas)
    assert codigo == 2 and out == "" and trecho in err and "erro: metrica investigar" in err
    assert leituras(tmp_path) == []


def test_ajuda_sai_0_e_diz_o_que_o_ato_faz(tmp_path):
    codigo, out, _ = roda(tmp_path, "--ajuda", tarefas=sem_tarefas)
    assert codigo == 0 and "--incidente" in out and "o verbo nao abre" in out and "exit:" in out


def test_a_cadeira_sem_slug_assina_a_citacao_como_desconhecida(tmp_path):
    escreve_dia(tmp_path)
    api = ApiFalsa()
    roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo", api=api, ambiente={"PF_CADEIRA": "Claudinho_TI!"})
    assert api.posts()[0][2]["autor"] == "claudinho-ti"
    api = ApiFalsa()
    roda(tmp_path, DIA, "--incidente", "1", "--tool", "acervo", api=api, ambiente={})
    assert api.posts()[0][2]["autor"] == "desconhecida"


# --- a saída para gente ----------------------------------------------------------------------------------------------

def test_resumo_imprime_o_cabecalho_a_citacao_e_cada_linha_inteira(tmp_path):
    escreve_dia(tmp_path)
    _, out, _ = roda(tmp_path, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO[:8], "--resumo")
    assert out.startswith(f"== metrica investigar — {DIA} · fonte: bruto · incidente #{INCIDENTE} ==")
    assert "4 linha(s) inteira(s)" in out and "citação: gravada" in out and "leitura registrada" in out
    assert "-- linha 3 · " in out and "SEGREDO-TEXTO" in out


# --- casos e eventos: o giro e o turno, sem conteúdo ----------------------------------------------------------------

def _bruto_em(monkeypatch, pasta):
    original = m.FonteJsonl
    monkeypatch.setattr(m, "FonteJsonl", lambda: original(str(pasta)))
    monkeypatch.setattr(m, "LOG_OPS", str(pasta))


def test_casos_sai_sem_args_nem_texto_de_erro_e_aponta_para_o_investigar(tmp_path, monkeypatch, capsys):
    escreve_dia(tmp_path)
    _bruto_em(monkeypatch, tmp_path)
    assert m.main(["metrica", "casos", DIA]) == 0
    saida = capsys.readouterr().out
    r = json.loads(saida)
    assert "SEGREDO" not in saida
    assert r["argumentos"] == f"metrica investigar {DIA} --incidente <n>"
    (caso,) = r["casos"]
    assert caso["tool"] == "repo" and caso["exit_code"] == 3 and "args" not in caso and "erro" not in caso
    assert r["chaves_omitidas"] == {"args": 1, "erro": 1}
    m.main(["metrica", "casos", DIA, "--resumo"])
    texto = capsys.readouterr().out
    assert f"argumentos: metrica investigar {DIA} --incidente <n>" in texto and "SEGREDO" not in texto


def test_eventos_tipo_turno_sai_sem_o_campo_texto_e_o_stream_comum_tambem(tmp_path, monkeypatch, capsys):
    escreve_dia(tmp_path)
    _bruto_em(monkeypatch, tmp_path)
    assert m.main(["metrica", "eventos", DIA, "--tipo", "turno"]) == 0
    saida = capsys.readouterr().out
    r = json.loads(saida)
    assert "SEGREDO" not in saida and r["argumentos"] == f"metrica investigar {DIA} --incidente <n>"
    (t,) = r["eventos"]
    assert t["tipo"] == "turno" and t["turno_id"] == "T1" and t["texto_bytes"] == 13 and "texto" not in t
    assert m.main(["metrica", "eventos", DIA]) == 0
    assert "SEGREDO" not in capsys.readouterr().out


def test_o_ato_investigar_esta_declarado_e_despachado(monkeypatch, capsys):
    assert "investigar" in m.ATOS
    cabecalho = "".join(METRICA.read_text(encoding="utf-8").splitlines(keepends=True)[:40])
    assert re.search(r"^# atos:.*investigar \(escrita, investigacao\)", cabecalho, re.MULTILINE)
    assert re.search(r"^#\s*exit\s*:", cabecalho, re.MULTILINE), "a porta lê a linha # exit: nas 40 primeiras linhas"
    chamado = []
    monkeypatch.setattr(m._investigar, "investigar", lambda argv: chamado.append(argv) or 0)
    assert m.main(["metrica", "investigar", DIA, "--incidente", "1"]) == 0
    assert chamado == [[DIA, "--incidente", "1"]], "args proprios: nao passa pelo parser comum do metrica"
    assert m.main(["metrica", "--help"]) == 0
    assert "metrica investigar <dia> --incidente <n>" in capsys.readouterr().out


def test_o_investigar_nao_abre_o_bruto_por_conta_propria():
    from test_oplog_unico_leitor import achados
    caminho = RAIZ / "bin" / "_metrica" / "investigar.py"
    assert achados(caminho, caminho.read_text(encoding="utf-8")) == []


def test_so_o_oplog_devolve_a_linha_inteira():
    """A leitura de conteúdo mora num lugar só: o verbo não tem como abrir o dia por fora do módulo."""
    texto = (RAIZ / "bin" / "_metrica" / "investigar.py").read_text(encoding="utf-8")
    assert "oplog.ler_inteiras(" in texto and "open(" not in texto and "read_bytes" not in texto
    assert "tarefas criar" not in texto and '"criar"' not in texto, "o verbo não abre incidente para destravar a leitura"


# --- a CLI de ponta a ponta, contra um servidor de loopback -------------------------------------------------------------

class _Servidor:
    def __init__(self, resposta):
        recebidas = self.recebidas = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                corpo = self.rfile.read(int(self.headers.get("content-length", 0)))
                recebidas.append((self.path, self.headers.get("authorization"), json.loads(corpo)))
                dados = json.dumps(resposta(json.loads(corpo))).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fecha(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def _tarefas_de_mentira(pasta, estado="Mitigado (incidente)"):
    stub = Path(pasta) / "tarefas-de-mentira"
    stub.write_text(f"#!{sys.executable}\nimport sys\n"
                    f"print('# titulo')\nprint('#' + sys.argv[2] + ' · null · {estado} · cadeira: ia')\n",
                    encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _cli(pasta, base, *args, estado="Mitigado (incidente)"):
    env = {**os.environ, "OPS_LOG_DIR": str(pasta), "MOTOR_ACERVO_URL": base, "RAG_API_TOKEN": "SEGREDO-TOKEN",
           "PF_TAREFAS_BIN": str(_tarefas_de_mentira(pasta, estado)), "PYTHONIOENCODING": "utf-8", **ENV}
    return subprocess.run([sys.executable, str(METRICA), "investigar", *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=60)


def test_cli_de_ponta_a_ponta_devolve_a_linha_cita_na_particao_e_nao_vaza_o_token(tmp_path):
    escreve_dia(tmp_path)
    s = _Servidor(lambda corpo: {"incidente": corpo["incidente"], "citadas": len(corpo["itens"]), "ja_citadas": 0,
                                 "conteudo_novo": len(corpo["itens"]), "ausentes": []})
    try:
        r = _cli(tmp_path, s.base, DIA, "--incidente", str(INCIDENTE), "--sessao", SESSAO[:8])
    finally:
        s.fecha()
    assert r.returncode == 0, r.stderr
    saida = json.loads(r.stdout)
    assert saida["citacao"]["estado"] == "gravada" and saida["devolvidas"] == 4
    assert {l["linha_n"]: l["linha"].get("texto") for l in saida["linhas"]}[3] == "SEGREDO-TEXTO"
    assert "SEGREDO-TOKEN" not in r.stdout + r.stderr
    ((caminho, auth, corpo),) = s.recebidas
    assert caminho == "/acervo/log/citacoes" and auth == "Bearer SEGREDO-TOKEN"
    assert corpo["autor"] == "ti" and corpo["incidente"] == INCIDENTE and len(corpo["itens"]) == 4
    assert [e["incidente"] for e in leituras(tmp_path)] == [INCIDENTE]


def test_cli_com_incidente_resolvido_sai_4_e_nao_toca_a_partição(tmp_path):
    escreve_dia(tmp_path)
    r = _cli(tmp_path, "http://127.0.0.1:9", DIA, "--incidente", str(INCIDENTE), estado="Resolvido (terminal)")
    assert r.returncode == 4 and r.stdout == "" and "não é incidente aberto" in r.stderr and "SEGREDO" not in r.stderr
    assert leituras(tmp_path) == []


def test_cli_sem_incidente_sai_2(tmp_path):
    r = _cli(tmp_path, "http://127.0.0.1:9", DIA)
    assert r.returncode == 2 and r.stdout == "" and "sem --incidente" in r.stderr
