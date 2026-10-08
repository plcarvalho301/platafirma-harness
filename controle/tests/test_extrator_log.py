"""lib/oplog_extracao e bin/_infra/linhagem-ops: o extrator do bruto da porta para a partição log (card #3353).

arq:0123 §8, §11-§13; spec apis-escrita-acervo §D5. Tudo contra uma pasta em tmp_path e uma API falsa (ou um
servidor HTTP de loopback): sem a porta, sem o banco e sem o log real. O que não se prova aqui é o SQL do
serviço, que o Postgres executa na passada do dia 2026-09-23, medida no relato do card.
"""
import hashlib
import http.server
import json
import os
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
LINHAGEM = RAIZ / "bin" / "_infra" / "linhagem-ops"
DIA = "2026-09-23"
SESSAO = "8f576862-23dd-4880-856f-4c9353096ee1"
SEGREDOS = ("SEGREDO-ARGS", "SEGREDO-ERRO", "SEGREDO-SUJEITO", "SEGREDO-USUARIO", "SEGREDO-SID", "SEGREDO-JTI",
            "SEGREDO-AZP", "SEGREDO-SUB", "SEGREDO-PERGUNTA", "SEGREDO-TEXTO")


def _id(n):
    return str(uuid.UUID(int=n))


def _escreve(pasta, dia, linhas, fim="\n"):
    """Grava o dia: str vai como veio, dict vai como JSON; `fim` fecha a última linha."""
    corpo = "\n".join(l if isinstance(l, str) else json.dumps(l, ensure_ascii=False) for l in linhas)
    (pasta / oplog.nome_do_dia(dia)).write_text(corpo + fim, encoding="utf-8")


def _antiga(**mud):
    """Uma linha de giro de antes da chave (sem evento_id, schema_v, classe, origem), com identidade e args."""
    reg = {"ts": f"{DIA}T10:00:00.000-03:00", "instancia": "casa", "usuario": "claudinho", "cadeira": "ti",
           "ordem_id": "o20260923T100000-aaaaaa", "sessao_id": SESSAO, "tool": "acervo", "ato": "ler",
           "args": "casa spec SEGREDO-ARGS", "exit_code": 0, "dur_ms": 40,
           "sujeito": "SEGREDO-SUJEITO", "sub": "SEGREDO-SUB", "username": "SEGREDO-USUARIO",
           "azp": "SEGREDO-AZP", "sid": "SEGREDO-SID", "jti": "SEGREDO-JTI"}
    reg.update(mud)
    return {k: v for k, v in reg.items() if v is not None}


def _inv():
    return ex.Invalidos()


# --- lib/oplog: os bytes do dia, as linhas numeradas, a chave v5 --------------------------------

def test_linhas_do_dia_numera_fisicamente_e_nao_conta_linha_em_branco():
    dados = b'{"a":1}\n\n   \n{"b":2}\nnao e json\n[1,2]\n'
    achadas = list(oplog.linhas_do_dia(dados))
    assert [(n, r) for n, _, r in achadas] == [(1, {"a": 1}), (4, {"b": 2}), (5, None), (6, None)]
    assert achadas[0][1] == b'{"a":1}', "a linha bruta vai sem o \\n"


def test_as_contagens_do_extrator_batem_com_as_de_oplog_ler_nos_casos_de_borda(tmp_path):
    """O corte (#3354) confere as contagens de `oplog.ler` com as da partição: as duas leituras têm de concordar
    em linha em branco, JSON que não é objeto, UTF-8 inválido, CRLF e a última linha sem \\n."""
    dados = (b'{"tool":"a","ts":"2026-09-23T10:00:00-03:00"}\n\n   \nnao e json\n[1,2]\n'
             b'{"tool":"b","x":"\xff\xfe"}\n{"tool":"c"}\r\n{"tool":"d"')
    (tmp_path / oplog.nome_do_dia(DIA)).write_bytes(dados)
    leitura = oplog.ler(DIA, diretorio_=tmp_path)
    assert len(list(leitura)) == 3
    pelo_modulo = (leitura.dias[DIA].legiveis, leitura.dias[DIA].ilegiveis)
    achadas = list(oplog.linhas_do_dia(dados))
    assert pelo_modulo == (sum(r is not None for _, _, r in achadas), sum(r is None for _, _, r in achadas)) == (3, 3)


def test_evento_id_da_linha_sem_chave_e_v5_e_estavel():
    a = oplog.evento_id_da_linha(DIA, 12)
    assert a == oplog.evento_id_da_linha(DIA, 12) != oplog.evento_id_da_linha(DIA, 13) != oplog.evento_id_da_linha("2026-09-24", 12)
    assert uuid.UUID(a).version == 5
    assert oplog.evento_id_da_linha(date(2026, 9, 23), 12) == a


def test_o_namespace_da_linha_antiga_nao_muda():
    """Mudar o namespace muda o evento_id de toda linha antiga: a regravação deixaria de ser idempotente."""
    assert str(oplog.NAMESPACE_LINHA) == "157dc68d-11da-5eb4-b10f-5bb34f239b50"
    assert oplog.evento_id_da_linha(DIA, 1) == "4de723f8-8303-5120-9010-f9f4177ee759"
    assert oplog.evento_id_da_linha(DIA, 12) == "19fff130-3ad6-5f7e-8500-2baf0c2adc39"


def test_nome_do_dia_e_so_o_nome():
    assert oplog.nome_do_dia(DIA) == "ops-2026-09-23.jsonl"


# --- o tipo da linha ----------------------------------------------------------------------------

@pytest.mark.parametrize("reg, tipo", [
    ({"tool": "acervo", "ato": "ler", "exit_code": 0}, "giro"),
    ({"tool": "write_file", "evento": "escrita"}, "giro"),
    ({"tool": "run_command", "evento": "sem_verbo", "motivo": "x"}, "giro"),
    ({"tool": "acervo", "evento": "pep_negou", "regra": "projecao"}, "giro"),
    ({"tool": "monta_sessao", "erro": "boom"}, "giro"),
    ({"tool": "monta_sessao", "exit_code": 3}, "giro"),
    ({"tool": "monta_sessao"}, "abertura"),
    ({"tool": "monta-sessao"}, "abertura"),
    ({"tool": "-", "evento": "http_req", "path": "/mcp"}, "http_req"),
    ({"tool": "-", "evento": "auth_negada", "path": "/mcp"}, "auth_negada"),
    ({"tool": "-", "evento": "jwt_recusado", "motivo": "ExpiredSignatureError"}, "auth_negada"),
    ({"tool": "-", "evento": "pep_negou", "regra": "identidade"}, "pep_negou"),
    ({"tool": "-", "evento": "negado", "motivo": "sem identidade"}, "pep_negou"),
    ({"tool": "sessao", "evento": "escopo", "escopo": "#3345"}, "escopo"),
    ({"tool": "sessao", "evento": "turno", "turno_id": "T1"}, "turno"),
    ({"tool": "descansar", "evento": "fecho", "motivo_parada": "concluiu"}, "fecho"),
    ({"tool": "motor", "evento": "consulta", "query": "x"}, "consulta_motor"),
    ({"tool": "run_command", "evento": "fallback"}, "fallback"),
    ({"tool": "repo", "evento": "verbo_contornado"}, "contorno"),
])
def test_tipo_particao(reg, tipo):
    assert ex.tipo_particao(reg) == tipo


@pytest.mark.parametrize("reg, evento", [
    ({"tool": "-", "evento": "pep_permitiu"}, "pep_permitiu"),
    ({"evento": "algo_que_ninguem_conhece"}, "algo_que_ninguem_conhece"),
    ({}, "(sem evento, sem tool)"),
])
def test_linha_que_nao_cabe_nos_doze_tipos_levanta_com_o_nome_dela(reg, evento):
    with pytest.raises(ex.SemTraducao) as e:
        ex.tipo_particao(reg)
    assert e.value.evento == evento


def test_os_doze_tipos_do_extrator_sao_os_da_ddl():
    assert ex.TIPOS == ("giro", "abertura", "fecho", "auth_negada", "http_req", "pep_negou", "contorno", "fallback",
                        "leitura", "escopo", "turno", "consulta_motor")


# --- a tradução: sem conteúdo -----------------------------------------------------------------

def _tudo(item):
    return json.dumps(item, ensure_ascii=False, default=str)


def test_giro_antigo_atravessa_sem_args_nem_identidade_e_ganha_chave_classe_e_origem():
    item = ex.para_item(_antiga(), DIA, 7, _inv())
    assert not any(s in _tudo(item) for s in SEGREDOS)
    for proibido in ("args", "erro", "sujeito", "sub", "username", "azp", "sid", "jti", "texto", "pergunta"):
        assert proibido not in item["evento"] and proibido not in item["giro"]
    ev = item["evento"]
    assert ev["evento_id"] == oplog.evento_id_da_linha(DIA, 7) and ev["linha_n"] == 7 and ev["schema_v"] == 0
    assert (ev["tipo"], ev["fonte"], ev["origem"], ev["sessao_id"], ev["cadeira"]) == ("giro", "bruto", "cadeira", SESSAO, "ti")
    assert item["giro"]["classe"] == "ok" and item["giro"]["classe_fonte"] == "tabela" and item["giro"]["tool"] == "acervo"
    assert item["giro"]["ato"] == "ler" and item["giro"]["exit_code"] == 0 and item["giro"]["dur_ms"] == 40


def test_linha_com_chave_mantem_o_evento_id_e_a_classe_que_a_porta_gravou():
    linha = _antiga(evento_id=_id(99), schema_v=1, classe="execucao", causa="exit_3", classe_fonte="verbo", exit_code=3,
                    origem="cadeira", escopo="#3353", turno_id="T1", turno_fonte="declarado", lavado=["branco"],
                    bytes_produzidos=500, bytes_servidos=200, aparado=["args"])
    item = ex.para_item(linha, DIA, 7, _inv())
    assert item["evento"]["evento_id"] == _id(99) and item["evento"]["schema_v"] == 1
    assert item["giro"] == {
        "tool": "acervo", "ato": "ler", "exit_code": 3, "classe": "execucao", "causa": "exit_3", "classe_fonte": "verbo",
        "dur_ms": 40, "bytes_produzidos": 500, "bytes_servidos": 200, "lavado": ["branco"], "ledger": None,
        "lote_id": None, "lote_n": None, "capacidade": None, "ferramenta": None, "escopo": "#3353",
        "turno_id": "T1", "turno_fonte": "declarado", "aparado": True}


def test_a_sonda_se_deduz_da_identidade_antes_de_ela_ser_descartada():
    sonda = {"ts": f"{DIA}T00:01:00.000-03:00", "tool": "sessao", "sessao_id": "-", "azp": "SEGREDO-AZP"}
    inv = _inv()
    item = ex.para_item(sonda, DIA, 3, inv)
    assert item["evento"]["origem"] == "sonda" and item["evento"]["sessao_id"] is None and item["evento"]["cadeira"] is None
    assert inv.total == 0, "o `-` é o nulo da porta, não um valor que não coube"
    assert ex.para_item(_antiga(origem_sessao=_id(5)), DIA, 3, _inv())["evento"]["origem"] == "agente"


def test_valor_que_nao_cabe_vira_nulo_e_conta():
    inv = _inv()
    item = ex.para_item(_antiga(sessao_id="nao-e-uuid", ato="ler arquivo com espaco", escopo="card 3353",
                                turno_fonte="palpite", exit_code="3", lote_id="a b", ledger="X Y"), DIA, 1, inv)
    assert item["evento"]["sessao_id"] is None and item["giro"]["ato"] is None and item["giro"]["escopo"] is None
    assert item["giro"]["turno_fonte"] is None and item["giro"]["exit_code"] is None
    assert item["giro"]["lote_id"] is None and item["giro"]["ledger"] is None
    assert dict(inv.por_campo) == {"sessao_id": 1, "ato": 1, "escopo": 1, "turno_fonte": 1, "exit_code": 1,
                                   "lote_id": 1, "ledger": 1}


@pytest.mark.parametrize("fonte", ["abertura", "runner", "gap", "hook", "transcript", "declarado"])
def test_as_seis_fontes_de_turno_atravessam_e_as_de_09_10_estao_entre_elas(fonte):
    """`abertura`, `runner` e `gap` são as de 09/10/2026 (spec log-de-negocio §3); as três antigas só existem no bruto
    anterior e se leem como estão. O CHECK de acervo.log_giro (088 e 089) tem as seis."""
    inv = _inv()
    assert ex._giro(_antiga(turno_fonte=fonte), inv)["turno_fonte"] == fonte and inv.total == 0
    assert set(ex.TURNO_FONTES) == {"abertura", "runner", "gap", "hook", "transcript", "declarado"}


def test_ato_que_e_texto_digitado_nao_atravessa():
    """`ato` de uma linha recusada pode ser o que o chamador digitou: só entra o que tem forma de nome de ato."""
    item = ex.para_item({"tool": "run_command", "evento": "sem_verbo", "ato": "git commit -m SEGREDO-ARGS", "ts": f"{DIA}T10:00:00-03:00"},
                        DIA, 1, _inv())
    assert item["giro"]["ato"] is None and "SEGREDO" not in _tudo(item)


def test_giro_com_tool_fora_da_forma_nao_e_traduzido():
    with pytest.raises(ex.SemTraducao, match="tool fora da forma"):
        ex.para_item({"tool": "um verbo com espaco", "ts": f"{DIA}T10:00:00-03:00"}, DIA, 1, _inv())


def test_ts_ausente_cai_no_comeco_do_dia_e_conta():
    inv = _inv()
    item = ex.para_item({"tool": "acervo"}, DIA, 1, inv)
    assert item["evento"]["ts"].startswith(f"{DIA}T00:00:00") and item["evento"]["ts"].endswith("-03:00")
    assert inv.por_campo["ts"] == 1


def test_abertura_traduz_a_via_do_roteador_sem_a_pergunta():
    base = {"tool": "monta_sessao", "ts": f"{DIA}T10:00:00-03:00", "chapeu": "observabilidade", "superficie": "claude.ai",
            "tokens_pecas": {"persona": 0, "chapeu": 1203}, "metodo_tokens": "tokenizador qwen2.5",
            "prefixo_sha": "7c18f2b", "montador_sha": "7c18f2b", "pergunta": "SEGREDO-PERGUNTA", "pergunta_bytes": 16}
    vias = {"fallback": "fallback", "determinístico": "casou", "deterministico": "casou", "casou": "casou",
            "comando": None, None: None}
    for via, esperada in vias.items():
        inv = _inv()
        item = ex.para_item({**base, "roteador_via": via}, DIA, 1, inv)
        assert item["abertura"]["roteador_via"] == esperada and inv.total == 0, via
    inv = _inv()
    item = ex.para_item({**base, "roteador_via": "inventado"}, DIA, 1, inv)
    assert item["abertura"]["roteador_via"] is None and inv.por_campo["roteador_via"] == 1
    assert item["abertura"]["tokens_pacote"] == {"persona": 0, "chapeu": 1203, "metodo": "tokenizador-qwen2.5"}
    assert item["abertura"]["superficie"] == "claude.ai" and item["abertura"]["chapeu"] == "observabilidade"
    assert "SEGREDO" not in _tudo(item) and "pergunta" not in _tudo(item)


def test_tokens_por_peca_aceita_a_lista_de_pares_da_linha():
    reg = {"tool": "monta_sessao", "ts": f"{DIA}T10:00:00-03:00", "tokens_pecas": [{"peca": "persona", "tokens": 3}, ["conduta", 7]]}
    assert ex.para_item(reg, DIA, 1, _inv())["abertura"]["tokens_pacote"] == {"persona": 3, "conduta": 7}


@pytest.mark.parametrize("bruto, motivo", [
    ("ExpiredSignatureError", "expirado"), ("InvalidAudienceError", "audience"), ("InvalidIssuerError", "emissor"),
    ("InvalidSignatureError", "assinatura"), ("DecodeError", "nao_jwt"), ("ErroDesconhecido", "outro")])
def test_jwt_recusado_vira_auth_negada_com_motivo_do_vocabulario(bruto, motivo):
    item = ex.para_item({"tool": "-", "evento": "jwt_recusado", "motivo": bruto, "ts": f"{DIA}T10:00:00-03:00"}, DIA, 1, _inv())
    assert item["evento"]["tipo"] == "auth_negada" and item["acesso"]["motivo"] == motivo


def test_acesso_atravessa_o_caminho_sem_a_query_string():
    reg = {"tool": "-", "evento": "auth_negada", "ts": f"{DIA}T10:00:00-03:00", "path": "/mcp?token=SEGREDO-TEXTO",
           "motivo": "sem_token", "origem_requisicao": "198.51.100.7"}
    item = ex.para_item(reg, DIA, 1, _inv())
    assert item["acesso"] == {"caminho": "/mcp", "origem_requisicao": "198.51.100.7", "status_http": None, "motivo": "sem_token"}
    assert "SEGREDO" not in _tudo(item)


def test_o_texto_do_turno_nao_atravessa():
    reg = {"tool": "sessao", "evento": "turno", "ts": f"{DIA}T10:00:00-03:00", "turno_id": "T0", "turno_fonte": "hook",
           "texto": "SEGREDO-TEXTO", "texto_bytes": 13}
    item = ex.para_item(reg, DIA, 1, _inv())
    assert item["evento"]["tipo"] == "turno" and set(item) == {"evento"} and "SEGREDO" not in _tudo(item)


# --- a amostra: a regra e o vetor-ouro, o mesmo do serviço -----------------------------------------

def test_amostra_vetor_ouro_bate_com_o_do_servico():
    """Os dez `ok` de menor md5(evento_id::text) entre os uuid de inteiro 1 a 30 (calculados fora do código).
    O mesmo literal está em platafirma-conhecimento/rag/tests/test_log_evento.py: as duas pontas concordam
    sem uma reimplementar a outra."""
    giros = [(_id(n), "acervo", "ok") for n in range(1, 31)]
    assert ex.amostra_esperada(giros) == {_id(n) for n in (29, 5, 21, 23, 14, 22, 20, 6, 12, 8)}


def test_amostra_leva_execucao_e_interrompida_e_ate_dez_ok_por_tool():
    giros = [(_id(n), "acervo", "ok") for n in range(1, 31)]
    giros += [(_id(100), "acervo", "execucao"), (_id(101), "repo", "interrompida"), (_id(102), "repo", "negativa"),
              (_id(103), "repo", "gramatica"), (_id(104), "repo", "negada")] + [(_id(200 + n), "repo", "ok") for n in range(4)]
    esperada = ex.amostra_esperada(giros)
    assert len(esperada) == 10 + 2 + 4
    assert _id(100) in esperada and _id(101) in esperada
    assert not {_id(102), _id(103), _id(104)} & esperada
    assert ex.amostra_esperada(reversed(giros)) == esperada, "a ordem da entrada não conta"


# --- o dia lido ---------------------------------------------------------------------------------

def _dia_misto(pasta):
    linhas = [_antiga(),                                                    # 1 giro antigo
              _antiga(tool="repo", ato="listar", exit_code=3, erro="SEGREDO-ERRO"),  # 2 execução
              "isto nao e json",                                           # 3 ilegível
              {"ts": f"{DIA}T10:00:01-03:00", "tool": "-", "evento": "http_req", "path": "/mcp"},     # 4
              "",                                                          # 5 em branco
              {"ts": f"{DIA}T10:00:02-03:00", "tool": "sessao", "sessao_id": "-"}]                    # 6 sonda
    _escreve(pasta, DIA, linhas)


def test_extracao_conta_lidas_legiveis_e_ilegiveis_como_o_modulo(tmp_path):
    _dia_misto(tmp_path)
    ext = ex.extrair(DIA, tmp_path)
    assert (ext.lidas, ext.legiveis, ext.ilegiveis) == (5, 4, 1)
    assert ext.lidas == ext.legiveis + ext.ilegiveis
    assert ext.por_tipo == {"giro": 3, "http_req": 1}
    assert ext.schema_v == {0} and ext.bytes == (tmp_path / oplog.nome_do_dia(DIA)).stat().st_size
    assert ext.sha256 == hashlib.sha256((tmp_path / oplog.nome_do_dia(DIA)).read_bytes()).hexdigest()
    assert [i["evento"]["linha_n"] for i in ext.itens] == [1, 2, 4, 6], "o número da linha é o físico, com a em branco contada"
    leitura = oplog.ler(DIA, diretorio_=tmp_path)
    list(leitura)
    assert (leitura.dias[DIA].legiveis, leitura.dias[DIA].ilegiveis) == (ext.legiveis, ext.ilegiveis)
    assert ext.fecho("ti") == {"autor": "ti", "linhas_lidas": 5, "linhas_legiveis": 4, "linhas_ilegiveis": 1,
                               "campos_invalidos": 0, "schema_v_achadas": [0], "por_tipo": {"giro": 3, "http_req": 1}}


def test_o_conteudo_vai_so_nos_itens_da_amostra_e_com_o_sha256_dos_bytes_da_linha(tmp_path):
    _dia_misto(tmp_path)
    ext = ex.extrair(DIA, tmp_path)
    (lote,) = list(ext.lotes())
    com = [i for i in lote if "conteudo" in i]
    assert {i["evento"]["tipo"] for i in com} == {"giro"} and len(com) == 3 == len(ext.amostra)
    assert all(i["evento"]["tipo"] == "giro" for i in com)
    dados = (tmp_path / oplog.nome_do_dia(DIA)).read_bytes()
    segunda = dados.split(b"\n")[1]
    c2 = next(i for i in com if i["evento"]["linha_n"] == 2)["conteudo"]
    assert c2["linha_sha256"] == hashlib.sha256(segunda).hexdigest()
    assert c2["linha"]["erro"] == "SEGREDO-ERRO", "a linha inteira, com o erro, só no conteúdo da amostra"
    assert all("conteudo" not in i for i in lote if i["evento"]["tipo"] == "http_req")


def test_a_linha_da_amostra_troca_nul_por_substituto(tmp_path):
    _escreve(tmp_path, DIA, [json.dumps(_antiga(args="a\u0000b"), ensure_ascii=True)])
    (lote,) = list(ex.extrair(DIA, tmp_path).lotes())
    assert lote[0]["conteudo"]["linha"]["args"] == "a�b"


def test_lotes_de_mil_na_ordem_do_arquivo(tmp_path):
    _escreve(tmp_path, DIA, [_antiga(ato=f"a{n}") for n in range(2503)])
    ext = ex.extrair(DIA, tmp_path)
    lotes = list(ext.lotes())
    assert [len(l) for l in lotes] == [1000, 1000, 503]
    assert [i["evento"]["linha_n"] for l in lotes for i in l] == list(range(1, 2504))


def test_dia_sem_arquivo_e_ausente_nunca_zero(tmp_path):
    ext = ex.extrair("2026-09-10", tmp_path)
    assert ext.ausente and ext.sha256 is None and ext.bytes is None and list(ext.lotes()) == []
    assert ext.fecho("ti")["linhas_lidas"] == 0


def test_o_dia_inteiro_nao_traz_segredo_fora_do_conteudo(tmp_path):
    _dia_misto(tmp_path)
    ext = ex.extrair(DIA, tmp_path)
    assert not any(s in _tudo(ext.itens) for s in SEGREDOS)


# --- o modo seco: só contagem ---------------------------------------------------------------------

def test_seco_devolve_so_contagem_e_a_conta_que_fecha_com_o_legado(tmp_path):
    _escreve(tmp_path, DIA, [_antiga(), _antiga(tool="monta_sessao", ato=None),
                             {"ts": f"{DIA}T10:00:00-03:00", "tool": "motor", "evento": "consulta", "query": "SEGREDO-TEXTO"},
                             {"ts": f"{DIA}T10:00:00-03:00", "tool": "-", "evento": "pep_permitiu", "sujeito": "SEGREDO-SUJEITO"}])
    rel = ex.relatorio_seco(ex.extrair(DIA, tmp_path))
    texto = json.dumps(rel, ensure_ascii=False)
    assert not any(s in texto for s in SEGREDOS), "o seco não devolve valor, só contagem"
    assert rel["por_evento_do_bruto"] == {"(sem evento)": 2, "consulta": 1, "pep_permitiu": 1}
    assert rel["sem_traducao"] == {"pep_permitiu": 1}
    assert rel["por_tipo_da_particao"] == {"abertura": 1, "consulta_motor": 1, "giro": 1}
    assert rel["giros_legado_por_tool"] == {"acervo": 1, "monta_sessao": 1, "motor": 1}
    assert rel["por_tool_e_tipo"] == {"acervo": {"giro": 1}, "monta_sessao": {"abertura": 1}, "motor": {"consulta_motor": 1}}
    assert rel["giros_por_tool"] == {"acervo": 1}


# --- a API e a passada ------------------------------------------------------------------------------

class ApiFalsa:
    """O servidor de D5.1 a D5.4 em memória o bastante para a passada: guarda o que recebeu."""

    def __init__(self, abertura=None, fecho=None, lote_falha=None):
        self.chamadas, self.itens = [], []
        self.abertura, self.fecho, self.lote_falha = abertura, fecho, list(lote_falha or [])

    def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
        self.chamadas.append((metodo, caminho, corpo))
        if caminho.startswith("/acervo/log/dias/") and caminho.endswith("/extracoes"):
            if self.abertura:
                raise self.abertura
            return 201, {"id": "p-nova", "estado": "aberta"}
        if caminho.startswith("/acervo/log/dias/"):
            return 200, {"dia": caminho.rsplit("/", 1)[1]}
        if caminho.endswith("/eventos"):
            if self.lote_falha:
                raise self.lote_falha.pop(0)
            self.itens.extend(corpo["itens"])
            return 200, {"novos": len(corpo["itens"]), "existentes": 0, "amostra": 0}
        if caminho.endswith("/fechar"):
            if self.fecho:
                raise self.fecho
            return 200, {"id": caminho.split("/")[-2], "estado": "concluida", "cobertura": "completo", "linhas_lidas": corpo["linhas_lidas"],
                         "linhas_legiveis": corpo["linhas_legiveis"], "linhas_ilegiveis": corpo["linhas_ilegiveis"],
                         "eventos_novos": len(self.itens), "eventos_existentes": 0, "amostra_n": 1, "campos_invalidos": 0}
        if metodo == "GET" and caminho == "/acervo/log/dias":
            return 200, {"itens": [{"dia": "2026-09-22", "passada": {"id": "x"}}, {"dia": "2026-09-23", "passada": None},
                                   {"dia": "2026-09-24", "passada": None}]}
        if metodo == "GET" and caminho.startswith("/acervo/log/extracoes/"):
            return 200, {"estado": "concluida", "id": caminho.rsplit("/", 1)[1]}
        raise AssertionError(f"chamada que a API falsa não conhece: {metodo} {caminho}")


def _sem_espera(_s):
    pass


def test_passada_percorre_d51_a_d54_na_ordem_e_manda_o_sha256_dos_bytes_lidos(tmp_path):
    _dia_misto(tmp_path)
    ext, api = ex.extrair(DIA, tmp_path), ApiFalsa()
    fechada = ex.passada(api, ext, "ti", "abc1234", espera=_sem_espera)
    assert [(m, c) for m, c, _ in api.chamadas] == [
        ("PUT", f"/acervo/log/dias/{DIA}"), ("POST", f"/acervo/log/dias/{DIA}/extracoes"),
        ("POST", "/acervo/log/extracoes/p-nova/eventos"), ("POST", "/acervo/log/extracoes/p-nova/fechar")]
    assert api.chamadas[0][2] == {"autor": "ti", "arquivo": oplog.nome_do_dia(DIA), "bytes": ext.bytes, "sha256": ext.sha256}
    assert api.chamadas[1][2] == {"autor": "ti", "versao_extrator": "abc1234", "sha256_lido": ext.sha256}
    assert len(api.itens) == 4 and fechada["estado"] == "concluida"
    assert not any(s in _tudo([i["evento"] for i in api.itens]) for s in SEGREDOS)


def test_dia_ausente_declara_ausente_e_nao_manda_lote(tmp_path):
    ext, api = ex.extrair("2026-09-10", tmp_path), ApiFalsa()
    ex.passada(api, ext, "ti", "abc1234", espera=_sem_espera)
    assert api.chamadas[0][2] == {"autor": "ti", "ausente": True}
    assert api.chamadas[1][2]["sha256_lido"] is None
    assert not any(c.endswith("/eventos") for _, c, _ in api.chamadas)


def test_passada_aberta_de_antes_e_retomada_com_o_id_que_o_problema_traz(tmp_path):
    _dia_misto(tmp_path)
    aberta = ex.Falha(1, "já tem passada", "ExtracaoAberta", {"extracao_id": "p-velha"})
    api = ApiFalsa(abertura=aberta)
    ex.passada(api, ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=_sem_espera)
    assert ("POST", "/acervo/log/extracoes/p-velha/eventos") in [(m, c) for m, c, _ in api.chamadas]
    assert ("POST", "/acervo/log/extracoes/p-velha/fechar") in [(m, c) for m, c, _ in api.chamadas]


def test_lote_que_cai_por_conexao_tenta_de_novo_e_o_banco_que_nao_volta_vira_exit_3(tmp_path):
    _dia_misto(tmp_path)
    api = ApiFalsa(lote_falha=[ex.Falha(3, "conexão recusada"), ex.Falha(5, "caiu")])
    esperas = []
    ex.passada(api, ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=esperas.append)
    assert esperas == [2, 4], "backoff de 2 s, 4 s"
    api = ApiFalsa(lote_falha=[ex.Falha(3, "fora")] * 9)
    with pytest.raises(ex.Falha) as e:
        ex.passada(api, ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=_sem_espera)
    assert e.value.codigo == 3


def test_linha_sem_traducao_aborta_antes_de_tocar_a_api(tmp_path):
    _escreve(tmp_path, DIA, [_antiga(), {"ts": f"{DIA}T10:00:00-03:00", "tool": "-", "evento": "evento_novo"}])
    api = ApiFalsa()
    with pytest.raises(ex.Falha, match=r"evento_novo \(1\)") as e:
        ex.passada(api, ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=_sem_espera)
    assert e.value.codigo == 1 and api.chamadas == []


def test_fecho_que_reprova_sai_exit_1_e_a_resposta_perdida_confere_a_passada(tmp_path):
    _dia_misto(tmp_path)
    reprovada = ex.Falha(1, "não fecha", "ExtracaoNaoFecha", {"numeros": {}})
    with pytest.raises(ex.Falha) as e:
        ex.passada(ApiFalsa(fecho=reprovada), ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=_sem_espera)
    assert e.value.codigo == 1 and e.value.titulo == "ExtracaoNaoFecha"
    perdida = ApiFalsa(fecho=ex.Falha(5, "a resposta se perdeu"))
    assert ex.passada(perdida, ex.extrair(DIA, tmp_path), "ti", "abc1234", espera=_sem_espera)["estado"] == "concluida"


def test_dias_pendentes_sao_os_fechados_sem_passada_concluida():
    assert ex.dias_pendentes(ApiFalsa(), date(2026, 9, 25)) == ["2026-09-23", "2026-09-24"]
    assert ex.dias_pendentes(ApiFalsa(), date(2026, 9, 15)) == [], "hoje não é dia fechado, e antes de 15/09 não há bruto"


# --- main: exits e saída -----------------------------------------------------------------------------

def _roda(argv, api, tmp_path, hoje=date(2026, 9, 25)):
    saida = []
    codigo = ex.main(argv, api=api, hoje=hoje, saida=saida.append, diretorio_=tmp_path, espera=_sem_espera)
    return codigo, saida


def test_main_sem_argumento_roda_os_pendentes_em_ordem_e_imprime_uma_linha_por_dia(tmp_path):
    _dia_misto(tmp_path)
    codigo, saida = _roda([], ApiFalsa(), tmp_path)
    assert codigo == 0 and len(saida) == 2 and saida[0].startswith("linhagem-ops 2026-09-23: concluida cobertura=completo lidas=5")
    assert "sha256=" in saida[0] and not any(s in " ".join(saida) for s in SEGREDOS)


def test_main_dia_aberto_nao_se_extrai(tmp_path, capsys):
    codigo, _ = _roda(["--dia", "2026-09-25"], ApiFalsa(), tmp_path)
    assert codigo == 2 and "ainda aberto" in capsys.readouterr().err


@pytest.mark.parametrize("falha, exit_", [
    (ex.Falha(3, "banco fora"), 3), (ex.Falha(1, "não fecha", "ExtracaoNaoFecha"), 1), (ex.Falha(4, "token", None), 4),
    (ex.Falha(4, "sha256 divergente", "Sha256Divergente"), 4), (ex.Falha(5, "indeterminável"), 5)])
def test_main_traduz_a_falha_da_passada_no_exit(tmp_path, falha, exit_, capsys):
    _dia_misto(tmp_path)

    class Quebra(ApiFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if metodo == "PUT":
                raise falha
            return super().chamar(metodo, caminho, corpo, params, aceita)
    codigo, _ = _roda(["--dia", DIA], Quebra(), tmp_path)
    assert codigo == exit_
    if falha.titulo == "Sha256Divergente":
        assert "ALARME DE INTEGRIDADE" in capsys.readouterr().err


def test_main_um_dia_que_falha_nao_impede_o_seguinte_e_o_exit_e_o_pior(tmp_path):
    _escreve(tmp_path, "2026-09-23", [_antiga()])
    _escreve(tmp_path, "2026-09-24", [_antiga()])

    class UmQuebra(ApiFalsa):
        def chamar(self, metodo, caminho, corpo=None, params=None, aceita=(200,)):
            if metodo == "PUT" and caminho.endswith("2026-09-23"):
                raise ex.Falha(3, "fora")
            return super().chamar(metodo, caminho, corpo, params, aceita)
    codigo, saida = _roda([], UmQuebra(), tmp_path)
    assert codigo == 3 and len(saida) == 1 and "2026-09-24" in saida[0]


def test_main_uso_errado_sai_2():
    assert ex.main(["--dia"]) == 2 and ex.main(["--dia", "ontem"]) == 2 and ex.main(["--que"]) == 2


def test_main_seco_nao_toca_a_api(tmp_path):
    _dia_misto(tmp_path)

    class Morta:
        def chamar(self, *a, **k):
            raise AssertionError("o seco foi à API")
    codigo, saida = _roda(["--seco", DIA], Morta(), tmp_path)
    corpo = json.loads(saida[0])
    assert codigo == 0 and corpo["linhas_lidas"] == 5 and corpo["por_tipo_da_particao"] == {"giro": 3, "http_req": 1}
    assert not any(s in saida[0] for s in SEGREDOS)


# --- o cliente HTTP, contra um servidor de loopback -------------------------------------------------

class _Servidor:
    def __init__(self, respostas):
        recebidas = self.recebidas = []

        class H(http.server.BaseHTTPRequestHandler):
            def _atende(self):
                n = int(self.headers.get("content-length") or 0)
                recebidas.append((self.command, self.path, self.headers.get("authorization"), self.rfile.read(n)))
                status, corpo = respostas.get((self.command, self.path.split("?")[0]), (404, {}))
                dados = json.dumps(corpo).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)
            do_GET = do_PUT = do_POST = _atende

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fecha(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def servidor():
    criados = []

    def novo(respostas):
        s = _Servidor(respostas)
        criados.append(s)
        return s
    yield novo
    for s in criados:
        s.fecha()


def test_api_manda_o_bearer_so_com_token_e_devolve_o_corpo(servidor):
    s = servidor({("PUT", "/acervo/log/dias/2026-09-23"): (201, {"dia": DIA})})
    status, corpo = ex.Api(s.base, token="t0k3n").chamar("PUT", "/acervo/log/dias/2026-09-23", {"autor": "ti"}, aceita=(200, 201))
    assert (status, corpo) == (201, {"dia": DIA})
    assert s.recebidas[0][2] == "Bearer t0k3n" and json.loads(s.recebidas[0][3]) == {"autor": "ti"}
    ex.Api(s.base, token="").chamar("PUT", "/acervo/log/dias/2026-09-23", {}, aceita=(200, 201))
    assert s.recebidas[1][2] is None


@pytest.mark.parametrize("status, titulo, codigo", [
    (503, "FonteIndisponivel", 3), (404, None, 3), (405, None, 3), (401, None, 4), (403, None, 4),
    (409, "Sha256Divergente", 1), (422, "EventoInvalido", 1), (404, "ExtracaoNaoEncontrada", 1),
    (500, None, 5), (502, None, 5), (400, None, 2)])
def test_api_traduz_o_status_no_exit_da_tabela(servidor, status, titulo, codigo):
    s = servidor({("POST", "/x"): (status, {"title": titulo, "detail": "d"} if titulo else {})})
    with pytest.raises(ex.Falha) as e:
        ex.Api(s.base, token="").chamar("POST", "/x", {})
    assert e.value.codigo == codigo and e.value.titulo == titulo


def test_api_conexao_recusada_e_exit_3_sem_vazar_o_token():
    with pytest.raises(ex.Falha) as e:
        ex.Api("http://127.0.0.1:9", token="SEGREDO-TOKEN", timeout=2).chamar("GET", "/x")
    assert e.value.codigo == 3 and "SEGREDO-TOKEN" not in str(e.value)


def test_api_usa_a_ordem_de_variaveis_do_bot_para_a_url(monkeypatch):
    for v in ("MOTOR_ACERVO_URL", "RAG_API_URL", "RAG_API_BASE"):
        monkeypatch.delenv(v, raising=False)
    assert ex.Api().base == "http://127.0.0.1:8100"
    monkeypatch.setenv("RAG_API_BASE", "http://c:3")
    monkeypatch.setenv("RAG_API_URL", "http://b:2/")
    assert ex.Api().base == "http://b:2"
    monkeypatch.setenv("MOTOR_ACERVO_URL", "http://a:1")
    assert ex.Api().base == "http://a:1"


def test_a_versao_do_extrator_sai_do_sha_da_release_ou_do_ambiente(monkeypatch):
    monkeypatch.setenv("PF_VERSAO_EXTRATOR", "abc1234")
    assert ex.versao_do_extrator() == "abc1234"
    monkeypatch.delenv("PF_VERSAO_EXTRATOR")
    assert ex.versao_do_extrator() in ("dev",) or len(ex.versao_do_extrator()) == 12


# --- o ponto de entrada -------------------------------------------------------------------------------

def _roda_script(tmp_path, env_extra, *args):
    env = {**os.environ, "OPS_LOG_DIR": str(tmp_path), **env_extra}
    return subprocess.run([sys.executable, str(LINHAGEM), *args], capture_output=True, text=True, env=env, timeout=60)


def test_linhagem_ops_seco_pela_linha_de_comando(tmp_path):
    _dia_misto(tmp_path)
    r = _roda_script(tmp_path, {}, "--seco", DIA)
    assert r.returncode == 0 and json.loads(r.stdout)["linhas_legiveis"] == 4
    assert not any(s in r.stdout + r.stderr for s in SEGREDOS)


def test_linhagem_args_do_drop_in_entra_separado_por_virgula(tmp_path):
    _dia_misto(tmp_path)
    r = _roda_script(tmp_path, {"LINHAGEM_ARGS": f"--seco,{DIA}"})
    assert r.returncode == 0 and json.loads(r.stdout)["dia"] == DIA


def test_linhagem_ops_uso_errado_sai_2_e_a_ajuda_sai_0(tmp_path):
    assert _roda_script(tmp_path, {}, "--que").returncode == 2
    ajuda = _roda_script(tmp_path, {}, "--ajuda")
    assert ajuda.returncode == 0 and "exit: 0 ok" in ajuda.stdout


def test_linhagem_ops_nao_abre_o_bruto_por_conta_propria():
    """O detector do leitor único (test_oplog_unico_leitor) varre bin/ e lib/: nenhum dos dois novos arquivos cita o
    diretório nem o nome do arquivo do dia em código."""
    from test_oplog_unico_leitor import achados
    for caminho in (LINHAGEM, RAIZ / "lib" / "oplog_extracao.py"):
        assert achados(caminho, caminho.read_text(encoding="utf-8")) == [], caminho.name
