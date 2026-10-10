"""A porta grava os campos da spec log-de-negocio §3 (card #3345).

O giro leva origem, poda (`bytes_produzidos`, `lavado`), escopo e turno; a abertura leva o custo
do pacote e nao leva o texto do dono; a negacao de acesso e um evento so, com caminho, origem da
requisicao e motivo no vocabulario fechado. Cada linha que a porta grava cumpre o contrato do
`lib/oplog` (`oplog.validar`). Vive em ops-server/ porque server.py precisa do venv com `mcp`.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso", HARNESS_DIR / "lib"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-campos-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import oplog  # noqa: E402
import server as s  # noqa: E402
from starlette.requests import Request  # noqa: E402

SID = "11111111-1111-4111-8111-111111111111"
FILHA = "22222222-2222-4222-8222-222222222222"
IDENT_TOKEN = {"sujeito": "b6986be0", "sub": "b6986be0", "username": "megafone",
               "azp": "claudinho-mcp", "sid": "sid-login", "jti": "jti-1"}
IDENT = {"sessao_id": SID, "ordem_id": "o1", "cadeira": "ia", "sujeito": "", "origem_sessao": ""}


@pytest.fixture(autouse=True)
def porta_isolada():
    s._ORIGENS.clear()
    s._CARIMBOS.clear()
    s._DECLARA_EXIT.clear()
    with patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))), \
            patch.object(s, "_quem", return_value=IDENT_TOKEN):
        yield
    s._ORIGENS.clear()
    s._CARIMBOS.clear()


def _linhas(pasta) -> list[dict]:
    return [json.loads(l) for f in sorted(pasta.glob("ops-*.jsonl"))
            for l in f.read_text(encoding="utf-8").splitlines()]


def _giro(tmp_path, **extra) -> dict:
    campos = dict(tool="tarefas", evento="verbo", ato="ler", args="3345", cadeira="ia", sessao_id=SID,
                  ordem_id="o1", exit_code=0, erro=None, **s._campos_poda({"exit_code": 0}))
    campos.update(extra)
    with patch.object(s, "LOG_DIR", tmp_path):
        s._audit(**campos)
    return _linhas(tmp_path)[-1]


# --- giro ---------------------------------------------------------------------------------

def test_o_giro_cumpre_o_contrato_com_poda_escopo_e_turno(tmp_path):
    linha = _giro(tmp_path, **s._campos_poda({"exit_code": 0, "poda": {
        "bytes_produzidos": 5630, "bytes_servidos": 5629, "lavado": ["branco"], "sha": "x",
        "modo": None, "ledger": "novo"}}))
    assert oplog.validar(linha) == []
    assert linha["bytes_produzidos"] == 5630 and linha["bytes_servidos"] == 5629
    assert linha["lavado"] == ["branco"]
    assert linha["escopo"] == "atendimento"
    assert (linha["turno_id"], linha["turno_fonte"]) == ("-", "gap")
    assert linha["origem"] == "cadeira" and linha["mapa_v"] is None
    assert linha["capacidade"] is None and linha["ferramenta"] is None
    assert linha["classe"] == "ok" and linha["evento_id"] and linha["schema_v"] == 1


def test_retorno_que_a_poda_nao_tocou_conta_os_bytes_crus_e_nao_lavou_nada():
    campos = s._campos_poda({"exit_code": 1, "stdout": {"texto": "abc"}, "stderr": {"texto": "de"}})
    assert campos["bytes_produzidos"] == campos["bytes_servidos"] == 5 and campos["lavado"] == []


def test_as_tools_de_arquivo_e_a_escrita_tambem_cumprem_o_contrato(tmp_path):
    leitura = _giro(tmp_path, tool="ler_arquivo", evento=None, ato=None, exit_code=None, erro="x",
                    classe_erro="faixa")
    assert oplog.validar(leitura) == [] and leitura["classe"] == "gramatica"
    escrita = _giro(tmp_path, tool="write_file", evento="escrita", ato=None, exit_code=None)
    assert oplog.validar(escrita) == [] and escrita["classe"] == "ok"
    recusa = _giro(tmp_path, tool="write_file", evento="escrita_recusada", ato=None, exit_code=None)
    assert oplog.validar(recusa) == [] and recusa["classe"] == "gramatica"


def test_a_linha_da_sonda_sai_com_origem_sonda_e_a_da_sessao_filha_com_agente(tmp_path):
    sonda = _giro(tmp_path, tool="sessao", evento=None, ato=None, cadeira=None, sessao_id="-",
                  ordem_id="-", exit_code=None)
    assert sonda["origem"] == "sonda"
    rc = MagicMock(get=MagicMock(side_effect=lambda k: json.dumps({"cadeira": "ia", "origem_sessao": SID})))
    with patch.object(s, "_rc", return_value=rc):
        filha = _giro(tmp_path, sessao_id=FILHA)
    assert filha["origem"] == "agente" and filha["origem_sessao"] == SID
    assert (filha["turno_id"], filha["turno_fonte"]) == (FILHA, "runner")


# --- escopo -------------------------------------------------------------------------------

def test_repo_abrir_com_card_abre_o_escopo_e_os_giros_seguintes_o_carimbam(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "3345", "--slug", "x"],
                          {"exit_code": 0}, IDENT)
    (escopo,) = _linhas(tmp_path)
    assert escopo["evento"] == "escopo" and escopo["escopo"] == "#3345" and escopo["card"] == 3345
    assert oplog.validar(escopo) == []
    assert _giro(tmp_path)["escopo"] == "#3345"


def test_tarefas_mover_em_execucao_tambem_abre_e_fita_com_dois_cards_vale_o_ultimo(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "3345"], {"exit_code": 0}, IDENT)
        s._escopo_do_giro("tarefas", "mover", ["#3346", "em-execucao"], {"exit_code": 0}, IDENT)
    assert [l["escopo"] for l in _linhas(tmp_path)] == ["#3345", "#3346"]
    assert _giro(tmp_path)["escopo"] == "#3346"


@pytest.mark.parametrize("slug, ato, args, r", [
    ("repo", "abrir", ["platafirma-harness", "3345"], {"exit_code": 1}),          # nao saiu 0
    ("repo", "abrir", ["platafirma-casa"], {"exit_code": 0}),                      # sem card
    ("repo", "estado", ["platafirma-harness", "3345"], {"exit_code": 0}),          # outro ato
    ("tarefas", "mover", ["3345", "entregue"], {"exit_code": 0}),                  # nao e em-execucao
    ("tarefas", "ler", ["3345"], {"exit_code": 0}),
    ("repo", "abrir", ["platafirma-harness", "nao-e-card"], {"exit_code": 0}),
])
def test_o_que_nao_declara_card_nao_muda_o_escopo(tmp_path, slug, ato, args, r):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._escopo_do_giro(slug, ato, args, r, IDENT)
    assert _linhas(tmp_path) == [] and _giro(tmp_path)["escopo"] == "atendimento"


def test_o_mesmo_card_duas_vezes_abre_o_escopo_uma_vez(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        for _ in range(2):
            s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "3345"], {"exit_code": 0}, IDENT)
    assert len(_linhas(tmp_path)) == 1


def test_sessao_sem_id_nao_guarda_escopo(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "3345"], {"exit_code": 0},
                          {**IDENT, "sessao_id": "-"})
    assert _linhas(tmp_path) == []


def test_o_escopo_sobrevive_ao_restart_pela_chave_viva(tmp_path):
    rc = MagicMock(get=MagicMock(return_value=json.dumps({"cadeira": "ia", "escopo_atual": "#3300",
                                                          "turno_valor": "T4", "turno_id": "T4"})))
    with patch.object(s, "_rc", return_value=rc):
        linha = _giro(tmp_path)
    assert linha["escopo"] == "#3300" and (linha["turno_id"], linha["turno_fonte"]) == ("T4", "declarado")


def test_escopo_novo_grava_na_chave_viva_sem_mexer_no_ttl(tmp_path):
    rc = MagicMock(get=MagicMock(return_value=json.dumps({"cadeira": "ia"})))
    with patch.object(s, "_rc", return_value=rc), patch.object(s, "LOG_DIR", tmp_path):
        s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "3345"], {"exit_code": 0}, IDENT)
    chave, valor = rc.set.call_args.args
    assert chave == f"sessao:{SID}" and json.loads(valor)["escopo_atual"] == "#3345"
    assert rc.set.call_args.kwargs == {"keepttl": True}


# --- turno --------------------------------------------------------------------------------

def test_turno_declarado_abre_o_turno_quando_o_valor_muda(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._carimba_turno(IDENT, "T0")
        s._carimba_turno(IDENT, "T0")                  # mesmo valor: nada novo
        s._carimba_turno(IDENT, "T1")
    turnos = _linhas(tmp_path)
    assert [t["turno_id"] for t in turnos] == ["T0", "T1"]
    assert all(t["evento"] == "turno" and t["turno_fonte"] == "declarado" for t in turnos)
    assert all("texto" not in t and oplog.validar(t) == [] for t in turnos)
    giro = _giro(tmp_path)
    assert (giro["turno_id"], giro["turno_fonte"]) == ("T1", "declarado")


def test_sem_o_campo_o_turno_e_gap_e_o_vazio_nao_abre_turno(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._carimba_turno(IDENT, "")
        s._carimba_turno(IDENT, None)
        s._carimba_turno({**IDENT, "sessao_id": "-"}, "T0")
    assert _linhas(tmp_path) == []
    assert (_giro(tmp_path)["turno_id"], _giro(tmp_path)["turno_fonte"]) == ("-", "gap")


def test_toda_tool_da_porta_aceita_o_campo_turno_opcional_com_padrao_vazio():
    import inspect
    tools = [s.malote, s.run_command, s.ler_arquivo, s.read_file, s.write_file, s.monta_sessao]
    tools += [s._faz_tool_verbo("tarefas", "/bin/true", "x")]
    for tool in tools:
        p = inspect.signature(tool).parameters.get("turno")
        assert p is not None and p.default == "", tool.__name__


def test_o_turno_chega_pelo_parametro_da_tool_de_verbo(tmp_path):
    tool = s._faz_tool_verbo("tarefas", "/bin/true", "x")
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r), \
            patch.object(s, "_sessao_resolve", return_value=IDENT), \
            patch.object(s, "_run_verbo_blocking", return_value={"exit_code": 0, "stdout": {"texto": "ok"}}):
        asyncio.run(tool(ato="ler", args=["3345"], turno="T7"))
    turno, giro = _linhas(tmp_path)
    assert turno["evento"] == "turno" and turno["turno_id"] == "T7"
    assert giro["tool"] == "tarefas" and giro["turno_id"] == "T7" and giro["turno_fonte"] == "declarado"


def test_repo_abrir_pela_tool_de_verbo_carimba_o_escopo_nos_giros_seguintes(tmp_path):
    tool = s._faz_tool_verbo("repo", "/bin/true", "x")
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r), \
            patch.object(s, "_sessao_resolve", return_value=IDENT), \
            patch.object(s, "_run_verbo_blocking", return_value={"exit_code": 0, "stdout": {"texto": "ok"}}):
        asyncio.run(tool(ato="abrir", args=["platafirma-harness", "3345", "--slug", "campos-giro"]))
        asyncio.run(tool(ato="estado", args=["platafirma-harness"]))
    abriu, escopo, depois = _linhas(tmp_path)
    assert abriu["escopo"] == "atendimento"             # o giro que abre o escopo nao o carrega
    assert escopo["evento"] == "escopo" and escopo["escopo"] == "#3345"
    assert depois["escopo"] == "#3345"


# --- abertura -----------------------------------------------------------------------------

PECAS = [{"peca": "persona", "sha": "aaa", "tokens": 0}, {"peca": "chapeu", "sha": "bbb", "tokens": 1291},
         {"peca": "mesa", "sha": "ccc", "tokens": 80}]
PACOTE = {"metodo_tokens": "tokenizador qwen2.5", "montador_sha": "76e618a",
          "prefixo_cacheavel": ["persona", "chapeu"]}


def _abre(tmp_path, r, pergunta="oi, tudo bem?", **extra):
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_montar", return_value=r), patch.object(s, "_delta_pecas", return_value=None), \
            patch.object(s, "_superficie", return_value="claude.ai"):
        asyncio.run(s.monta_sessao(cadeira="ia", pergunta=pergunta, **extra))
    return [l for l in _linhas(tmp_path) if l.get("tool") == "monta_sessao"][0]


def _resposta(**extra):
    return {"cadeira": "ia", "chapeu": "engenharia-de-harness", "sessao_id": SID, "ordem_id": "o1",
            "sessao": {"sessao_id": SID, "cunhada_agora": True, "ordem_id": "o1"},
            "roteador": {"via": "comando", "slug": "engenharia-de-harness"},
            "pecas": PECAS, "pacote": PACOTE, **extra}


def test_a_abertura_grava_o_prompt_do_dono_e_o_custo_do_pacote_mas_nao_o_pacote(tmp_path):
    # Ordem do dono (08/10): grava so o prompt dele, nao o pacote todo.
    pecas = [{**p, "conteudo": f"CONTEUDO-DA-PECA-{p['peca']}"} for p in PECAS]
    linha = _abre(tmp_path, _resposta(pecas=pecas), pergunta="oi, tudo bem?")
    assert linha["pergunta"] == "oi, tudo bem?" and linha["pergunta_bytes"] == len("oi, tudo bem?".encode())
    bruto = json.dumps(_linhas(tmp_path))
    assert "CONTEUDO-DA-PECA" not in bruto, "o conteudo das pecas do pacote nao entra em linha nenhuma"
    assert not {"pecas", "pacote", "conteudo", "resposta"} & set(linha)
    assert linha["tokens_pecas"] == {"persona": 0, "chapeu": 1291, "mesa": 80}
    assert linha["metodo_tokens"] == "tokenizador qwen2.5" and linha["montador_sha"] == "76e618a"
    assert linha["prefixo_sha"] == hashlib.sha256(b"persona:aaa|chapeu:bbb").hexdigest()[:12]
    assert linha["chapeu"] == "engenharia-de-harness" and linha["roteador_via"] == "comando"
    assert linha["fallback"] is False
    assert linha["superficie"] == "claude.ai"
    assert oplog.validar(linha) == []


def test_abertura_em_fallback_grava_fallback_true_e_cumpre_o_contrato(tmp_path):
    r_fb = _resposta(chapeu=None, roteador={"via": "fallback", "slug": None})
    linha = _abre(tmp_path, r_fb, pergunta="oi")
    assert linha["fallback"] is True and linha["chapeu"] is None
    assert linha["roteador_via"] == "fallback"
    assert oplog.validar(linha) == []


def test_o_prefixo_cacheavel_muda_quando_uma_peca_do_prefixo_muda(tmp_path):
    a = s._custo_da_abertura(_resposta())["prefixo_sha"]
    outras = [{**p, "sha": "zzz"} if p["peca"] == "chapeu" else p for p in PECAS]
    b = s._custo_da_abertura(_resposta(pecas=outras))["prefixo_sha"]
    c = s._custo_da_abertura(_resposta(pecas=[{**p, "sha": "zzz"} if p["peca"] == "mesa" else p
                                              for p in PECAS]))["prefixo_sha"]
    assert a != b and a == c, "peca fora do prefixo nao mexe no sha do prefixo"


def test_abertura_recusada_nao_tem_pacote_mas_grava_o_prompt(tmp_path):
    linha = _abre(tmp_path, {"erro": "persona nao achada", "cadeira": "x"}, pergunta="o que o dono pediu")
    assert linha["tokens_pecas"] is None and linha["prefixo_sha"] is None
    assert linha["pergunta"] == "o que o dono pediu" and linha["pergunta_bytes"] == len("o que o dono pediu")


def test_reabertura_sem_mensagem_nova_grava_pergunta_nula_e_cumpre_o_contrato(tmp_path):
    linha = _abre(tmp_path, _resposta(), pergunta="", sessao_id=SID)
    assert linha["pergunta"] is None and linha["pergunta_bytes"] == 0
    assert oplog.validar(linha) == []


def test_a_abertura_com_turno_abre_o_t0(tmp_path):
    _abre(tmp_path, _resposta(), turno="T0")
    turno = [l for l in _linhas(tmp_path) if l.get("evento") == "turno"]
    assert [t["turno_id"] for t in turno] == ["T0"] and turno[0]["sessao_id"] == SID


# --- auth_negada --------------------------------------------------------------------------

def _req(headers=(), client=("203.0.113.9", 5000), path="/mcp") -> Request:
    return Request({"type": "http", "method": "POST", "path": path, "raw_path": path.encode(),
                    "query_string": b"", "scheme": "http", "server": ("127.0.0.1", 8010),
                    "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
                    "client": client})


def _nega(tmp_path, headers=(), recusa=None, client=("203.0.113.9", 5000)):
    """Roda a middleware com um JWT que o PyJWT recusa pela excecao `recusa` (ou sem recusa)."""
    def falso(header, auditor=None, **_):
        if recusa:
            auditor(tool="-", evento="jwt_recusado", motivo=recusa)
        return {}
    chamou = []

    async def segue(_req):
        chamou.append(1)

    mw = s.BearerAuth(app=lambda *a, **k: None)
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_sujeito_do_jwt", falso), \
            patch.object(s, "_estatico_vigente", return_value=False):
        resp = asyncio.run(mw.dispatch(_req(headers, client), segue))
    assert not chamou, "requisicao negada nao segue"
    return resp, _linhas(tmp_path)


@pytest.mark.parametrize("headers, recusa, motivo", [
    ([], None, "sem_token"),
    ([("authorization", "Bearer ")], None, "sem_token"),
    ([("authorization", "Basic abc")], None, "sem_token"),
    ([("authorization", "Bearer abc")], None, "nao_jwt"),
    ([("authorization", "Bearer a.b.c")], "ExpiredSignatureError", "expirado"),
    ([("authorization", "Bearer a.b.c")], "InvalidAudienceError", "audience"),
    ([("authorization", "Bearer a.b.c")], "InvalidIssuerError", "emissor"),
    ([("authorization", "Bearer a.b.c")], "InvalidSignatureError", "assinatura"),
    ([("authorization", "Bearer a.b.c")], "PyJWKClientError", "assinatura"),
    ([("authorization", "Bearer a.b.c")], "DecodeError", "nao_jwt"),
    ([("authorization", "Bearer a.b.c")], "MissingRequiredClaimError", "outro"),
    ([("authorization", "Bearer a.b.c")], None, "outro"),
])
def test_a_negacao_e_um_evento_so_com_o_motivo_no_vocabulario_fechado(tmp_path, headers, recusa, motivo):
    resp, linhas = _nega(tmp_path, headers, recusa)
    assert resp.status_code == 401
    (linha,) = linhas                                   # o jwt_recusado avulso nao e gravado
    assert linha["evento"] == "auth_negada" and linha["motivo"] == motivo
    assert linha["path"] == "/mcp" and linha["motivo"] in oplog.MOTIVOS_NEGACAO
    assert oplog.validar(linha) == []


def test_requisicao_sem_token_grava_auth_negada_com_sem_token_e_o_cliente(tmp_path):
    _, (linha,) = _nega(tmp_path)
    assert linha["motivo"] == "sem_token" and linha["cliente"] == "203.0.113.9"
    assert linha["origem_requisicao"] == "203.0.113.9"


@pytest.mark.parametrize("cliente, cabecalho, esperado", [
    ("127.0.0.1", "198.51.100.7", "198.51.100.7"),           # do conector: vale o cabecalho
    ("::1", "2001:db8::1", "2001:db8::1"),
    ("203.0.113.9", "198.51.100.7", "203.0.113.9"),          # de fora: o cabecalho e forjavel, vale o IP da conexao
    ("127.0.0.1", "'; drop table x;--", "127.0.0.1"),        # texto livre nao entra na linha
    ("127.0.0.1", "", "127.0.0.1"),
])
def test_origem_da_requisicao_so_confia_no_cabecalho_do_conector(tmp_path, cliente, cabecalho, esperado):
    headers = [("cf-connecting-ip", cabecalho)] if cabecalho else []
    _, (linha,) = _nega(tmp_path, headers, client=(cliente, 5000))
    assert linha["origem_requisicao"] == esperado
