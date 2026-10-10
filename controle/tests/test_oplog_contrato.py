"""O contrato do log da porta no lib/oplog (card #3345, spec log-de-negocio §3).

«Campo obrigatorio ausente reprova no teste de contrato»: cada tipo de linha tem os campos que
a spec manda, `validar` os cobra, e o que a casa decidiu nao gravar (o texto do dono, o token)
reprova quando aparece. Estes testes exercitam o modulo; a porta gravando por ele esta em
ops-server/test_campos_giro_porta.py.
"""
import copy

import pytest

import oplog

IDENT = {"sujeito": "s", "sub": "s", "username": "u", "azp": "claudinho-mcp", "sid": "x", "jti": "j"}
TODA = {"ts": "2026-10-08T10:00:00.000-03:00", "evento_id": "01a11bd5-18d9-77e1-b818-bf36232140f2",
        "schema_v": 1, "origem": "cadeira", "mapa_v": None}

GIRO = {**TODA, **IDENT, "tool": "tarefas", "ato": "ler", "args": "3345", "sessao_id": "sid",
        "cadeira": "ia", "ordem_id": "o1", "exit_code": 0, "classe": "ok", "classe_fonte": "tabela",
        "bytes_produzidos": 120, "bytes_servidos": 100, "lavado": ["branco"], "capacidade": None,
        "ferramenta": None, "escopo": "#3345", "turno_id": "T1", "turno_fonte": "declarado"}
ABERTURA = {**TODA, **IDENT, "tool": "monta_sessao", "sessao_id": "sid", "chapeu": "engenharia-de-harness",
            "roteador_via": "comando", "fallback": False, "superficie": "claude.ai", "pergunta": "oi", "pergunta_bytes": 2,
            "tokens_pecas": {"persona": 0, "chapeu": 1291}, "metodo_tokens": "tokenizador qwen2.5",
            "prefixo_sha": "abc123", "montador_sha": "76e618a"}
FECHO = {**TODA, "tool": "descansar", "evento": "fecho", "sessao_id": "sid", "cadeira": "ia",
         "motivo_parada": "concluiu", "tokens": 10, "fonte_tokens": "provedor"}
AUTH = {**TODA, "tool": "-", "evento": "auth_negada", "path": "/mcp", "origem_requisicao": "198.51.100.7",
        "motivo": "sem_token"}
HTTP = {**TODA, **IDENT, "tool": "-", "evento": "http_req", "path": "/mcp", "via": "oidc"}
ESCOPO = {**TODA, **IDENT, "tool": "sessao", "evento": "escopo", "sessao_id": "sid", "escopo": "#3345"}
TURNO = {**TODA, **IDENT, "tool": "sessao", "evento": "turno", "sessao_id": "sid", "turno_id": "T1",
         "turno_fonte": "declarado"}
CONSULTA = {**TODA, "tool": "motor", "evento": "consulta", "origem_consulta": "abertura",
            "particao": "casa", "query": "oi", "query_bytes": 2}

LEITURA = {**TODA, "tool": "metrica", "ato": "investigar", "evento": "leitura_bruto", "sessao_id": "sid",
           "cadeira": "ti", "ordem_id": "o1", "incidente": 3400, "dia": "2026-10-08", "origem_leitura": "bruto",
           "filtro_sessao": None, "filtro_tool": "acervo", "filtro_classe": None, "linhas_devolvidas": 3,
           "linhas_omitidas": 0}

LINHAS = {"giro": GIRO, "abertura": ABERTURA, "fecho": FECHO, "auth_negada": AUTH, "http_req": HTTP,
          "escopo": ESCOPO, "turno": TURNO, "consulta": CONSULTA, "leitura": LEITURA}


@pytest.mark.parametrize("tipo", sorted(LINHAS))
def test_a_linha_de_exemplo_de_cada_tipo_cumpre_o_contrato(tipo):
    assert oplog.tipo_da_linha(LINHAS[tipo]) == tipo
    assert oplog.validar(LINHAS[tipo]) == []


def _casos_de_campo_ausente():
    # `tool` e `evento` dizem de que tipo e a linha: sem eles ela vira outro tipo, nao um tipo incompleto.
    for tipo in LINHAS:
        for campo in oplog.CONTRATO["toda"] + oplog.CONTRATO[tipo]:
            if campo not in ("tool", "evento"):
                yield pytest.param(tipo, campo, id=f"{tipo}-{campo}")


@pytest.mark.parametrize("tipo, campo", list(_casos_de_campo_ausente()))
def test_campo_obrigatorio_ausente_reprova(tipo, campo):
    linha = copy.deepcopy(LINHAS[tipo])
    linha.pop(campo)
    assert f"falta {campo}" in oplog.validar(linha)


def test_so_capacidade_ferramenta_e_mapa_v_saem_nulos_por_falta_da_projecao():
    # Enquanto a projecao do golden record nao existe na release (arq:0123 §7), os tres saem nulos.
    for campo in ("capacidade", "ferramenta"):
        assert oplog.validar({**GIRO, campo: None}) == []
    assert oplog.validar({**GIRO, "mapa_v": None}) == []
    # Os demais nao: escopo e turno_id sempre dizem alguma coisa (`atendimento`, `-`).
    for campo in ("escopo", "turno_id", "classe", "turno_fonte", "sub", "jti"):
        assert f"{campo} nulo" in oplog.validar({**GIRO, campo: None}), campo


def test_a_mensagem_do_dono_se_grava_mas_o_pacote_a_resposta_e_o_token_nao():
    # Ordem do dono (08/10): grava o prompt dele, so o prompt, no bruto.
    assert oplog.validar({**ABERTURA, "pergunta": "oi, tudo bem?"}) == []
    assert oplog.validar({**ABERTURA, "pergunta": None, "pergunta_bytes": 0}) == []   # reabertura
    for campo in ("pacote", "pecas", "conteudo", "resposta"):
        assert f"nao se grava {campo}" in oplog.validar({**ABERTURA, campo: "x"}), campo
    assert "nao se grava resposta" in oplog.validar({**GIRO, "resposta": "x"})
    assert "nao se grava token" in oplog.validar({**GIRO, "token": "eyJ..."})
    assert "nao se grava authorization" in oplog.validar({**GIRO, "authorization": "Bearer x"})


def test_a_consulta_do_motor_grava_a_query_da_abertura_e_a_de_cadeira():
    assert oplog.validar(CONSULTA) == []                                      # origem_consulta abertura
    assert oplog.validar({**CONSULTA, "origem_consulta": "busca", "query": "o que e caderno"}) == []
    sem_query = {k: v for k, v in CONSULTA.items() if k != "query"}
    assert "falta query" in oplog.validar(sem_query)


def test_a_leitura_da_linha_inteira_e_rastro_e_nao_leva_o_conteudo():
    """#3355: o evento diz quem leu, por qual incidente e quanto saiu; a linha, o argumento e o texto do turno nao."""
    for campo in ("linha", "linhas", "args", "texto", "erro", "conteudo", "resposta", "pergunta", "query", "token"):
        assert f"nao se grava {campo}" in oplog.validar({**LEITURA, campo: "x"}), campo
    assert any("origem_leitura" in e for e in oplog.validar({**LEITURA, "origem_leitura": "disco"}))
    for ruim in (0, -1, "3400", True, None):
        assert any("incidente" in e for e in oplog.validar({**LEITURA, "incidente": ruim})), ruim
    # a particao nao conta o que ficou de fora, e filtro que ninguem pediu e nulo
    assert oplog.validar({**LEITURA, "origem_leitura": "particao", "linhas_omitidas": None}) == []
    assert oplog.validar({**LEITURA, "filtro_tool": None}) == []
    assert oplog.tipo_da_linha({"tool": "metrica", "evento": "leitura_bruto"}) == "leitura"


@pytest.mark.parametrize("motivo", oplog.MOTIVOS_NEGACAO)
def test_auth_negada_aceita_o_vocabulario_fechado(motivo):
    assert oplog.validar({**AUTH, "motivo": motivo}) == []


def test_auth_negada_fora_do_vocabulario_reprova():
    assert any("motivo" in e for e in oplog.validar({**AUTH, "motivo": "token feio"}))
    assert set(oplog.MOTIVOS_NEGACAO) == {"sem_token", "nao_jwt", "assinatura", "audience", "emissor",
                                          "expirado", "outro"}


def test_origem_e_do_vocabulario_e_turno_fonte_tambem():
    assert any("origem" in e for e in oplog.validar({**GIRO, "origem": "robo"}))
    assert any("turno_fonte" in e for e in oplog.validar({**GIRO, "turno_fonte": "palpite"}))
    for fonte in ("declarado", "gap", "runner"):
        assert oplog.validar({**GIRO, "turno_fonte": fonte}) == []


def test_tokens_do_fecho_pedem_a_fonte():
    sem_fonte = {k: v for k, v in FECHO.items() if k != "fonte_tokens"}
    assert "tokens sem fonte_tokens" in oplog.validar(sem_fonte)
    sem_tokens = {k: v for k, v in FECHO.items() if k not in ("tokens", "fonte_tokens")}
    assert oplog.validar(sem_tokens) == []        # onde a superficie nao informa, o fecho sai sem


# --- origem -----------------------------------------------------------------------------

def test_origem_agente_quando_ha_origem_sessao():
    assert oplog.origem_da_linha({"tool": "repo", "cadeira": "engenharia", "origem_sessao": "uuid"}) == "agente"


def test_origem_sonda_pela_assinatura_do_giro_da_tool_sessao_sem_ato_nem_cadeira():
    sonda = {"tool": "sessao", "ato": None, "cadeira": None, "sessao_id": "-", "exit_code": None}
    assert oplog.origem_da_linha(sonda) == "sonda"
    # A chamada de verdade da tool `sessao` sem sessao (ato e exit) nao e sonda.
    real = {"tool": "sessao", "ato": "monta_sessao", "cadeira": None, "sessao_id": "-", "exit_code": 2}
    assert oplog.origem_da_linha(real) == "cadeira"


def test_origem_cadeira_no_resto():
    assert oplog.origem_da_linha({"tool": "tarefas", "ato": "ler", "cadeira": "ia", "sessao_id": "x"}) == "cadeira"


def test_emitir_carimba_origem_e_mapa_v_e_ler_da_origem_a_linha_antiga(tmp_path):
    import json
    from datetime import datetime, timezone
    agora = datetime.fromisoformat("2026-10-08T12:00:00+00:00").astimezone(timezone.utc)
    oplog.emitir({"tool": "repo", "exit_code": 0, "origem_sessao": "uuid"}, diretorio_=tmp_path, agora=agora)
    (linha,) = [json.loads(l) for l in (tmp_path / "ops-2026-10-08.jsonl").read_text().splitlines()]
    assert linha["origem"] == "agente" and linha["mapa_v"] is None
    antiga = {"tool": "sessao", "ato": None, "cadeira": None, "sessao_id": "-"}
    (tmp_path / "ops-2026-09-23.jsonl").write_text(json.dumps(antiga) + "\n")
    (lida,) = list(oplog.ler("2026-09-23", diretorio_=tmp_path))
    assert lida["origem"] == "sonda" and lida["classe"] == "ok"


# --- classe das tools de leitura ----------------------------------------------------------

@pytest.mark.parametrize("classe_erro, classe", [
    ("gramatica", "gramatica"), ("faixa", "gramatica"), ("recusado", "negada"),
    ("caminho", "negativa"), ("binario", "negativa")])
def test_classe_do_erro_das_tools_de_leitura(classe_erro, classe):
    r = oplog.classificar({"tool": "ler_arquivo", "erro": "x", "classe_erro": classe_erro})
    # `causa` so existe na execucao: CHECK (classe = 'execucao' OR causa IS NULL) de acervo.log_giro.
    assert r["classe"] == classe and "causa" not in r


def test_o_vocabulario_cumpre_os_check_do_schema_fisico_da_particao_log():
    # spec apis-escrita-acervo §D1: acervo.log_giro.classe/causa e acervo.log_fecho.motivo_parada.
    import re
    desfechos = [{"exit_code": c} for c in (0, 1, 2, 3, 4, 5, 9, 137)] + [
        {"erro": "timeout (30s)"}, {"erro": "falha ao abrir"}, {"erro": "x"}, {"cancelado": True},
        {"evento": "sem_verbo"}, {"evento": "pep_negou"}, {"evento": "pep_indisponivel"},
        {"evento": "escrita_recusada"}] + [{"erro": "x", "classe_erro": c} for c in
                                          ("gramatica", "faixa", "recusado", "caminho", "binario")]
    for d in desfechos:
        r = oplog.classificar(d)
        assert r["classe"] in oplog.CLASSES and r["classe_fonte"] in ("verbo", "tabela"), d
        assert r["classe"] == "execucao" or "causa" not in r, f"causa fora da execucao: {d} -> {r}"
        assert re.fullmatch(r"[a-z][a-z0-9_]*", r.get("causa", "x")), d
    assert set(oplog.MOTIVOS_PARADA) == {"concluiu", "teto_giros", "orcamento_erro", "interrompida"}
    assert set(oplog.FONTES_TURNO) == {"hook", "transcript", "runner", "declarado", "gap"}
    assert set(oplog.FONTES_TOKENS) == {"provedor", "estimado"}


def test_escrita_recusada_e_gramatica_e_erro_sem_classe_segue_execucao():
    assert oplog.classificar({"tool": "write_file", "evento": "escrita_recusada"})["classe"] == "gramatica"
    assert oplog.classificar({"tool": "ler_arquivo", "erro": "disco cheio"})["classe"] == "execucao"
