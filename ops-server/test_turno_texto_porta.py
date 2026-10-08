"""A porta recebe o texto do turno (card #3357, spec log-de-negocio §0 e §3).

Toda tool da porta aceita `turno_texto` e `turno_fonte`, opcionais e com padrao vazio como o
`turno`. Quando `turno` muda, a linha `turno` leva `texto` (a mensagem do dono, aparada como os
outros campos longos) e `texto_bytes` (o tamanho original); `turno_fonte` vale `hook` ou
`transcript`, e o que vier fora do vocabulario sai `declarado`. O texto fica so no bruto: o giro
nao o repete. Cada linha cumpre `oplog.validar`. Vive em ops-server/ porque server.py precisa do
venv com `mcp`.
"""
from __future__ import annotations

import asyncio
import inspect
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

_TMP = Path(tempfile.mkdtemp(prefix="ops-turno-texto-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import oplog  # noqa: E402
import server as s  # noqa: E402

SID = "33333333-3333-4333-8333-333333333333"
IDENT_TOKEN = {"sujeito": "b6986be0", "sub": "b6986be0", "username": "megafone",
               "azp": "agy-cli", "sid": "sid-login", "jti": "jti-1"}
IDENT = {"sessao_id": SID, "ordem_id": "o1", "cadeira": "ti", "sujeito": "", "origem_sessao": ""}


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
    return [json.loads(linha) for f in sorted(pasta.glob("ops-*.jsonl"))
            for linha in f.read_text(encoding="utf-8").splitlines()]


def _giro(pasta) -> dict:
    campos = dict(tool="tarefas", evento="verbo", ato="ler", args="3357", cadeira="ti",
                  sessao_id=SID, ordem_id="o1", exit_code=0, erro=None,
                  **s._campos_poda({"exit_code": 0}))
    with patch.object(s, "LOG_DIR", pasta):
        s._audit(**campos)
    return _linhas(pasta)[-1]


def _turno(pasta, valor="T0", texto="", fonte="") -> dict:
    with patch.object(s, "LOG_DIR", pasta):
        s._carimba_turno(IDENT, valor, texto, fonte)
    return [t for t in _linhas(pasta) if t.get("evento") == "turno"][-1]


def test_turno_texto_vira_texto_e_texto_bytes_na_linha_de_turno(tmp_path):
    linha = _turno(tmp_path, "T0", "Cards 3356 e 3357, por favor.", "hook")
    assert linha["texto"] == "Cards 3356 e 3357, por favor."
    assert linha["texto_bytes"] == len("Cards 3356 e 3357, por favor.".encode())
    assert (linha["turno_id"], linha["turno_fonte"]) == ("T0", "hook")
    assert oplog.validar(linha) == []


@pytest.mark.parametrize("fonte", ["hook", "transcript"])
def test_turno_fonte_do_vocabulario_vale_o_que_veio(tmp_path, fonte):
    linha = _turno(tmp_path, "T0", "oi", fonte)
    assert linha["turno_fonte"] == fonte and oplog.validar(linha) == []


def test_texto_sem_fonte_e_do_hook_do_code(tmp_path):
    assert _turno(tmp_path, "T0", "oi")["turno_fonte"] == "hook"


@pytest.mark.parametrize("fonte", ["runner", "gap", "declarado", "inventada"])
def test_fonte_que_o_chamador_nao_pode_entregar_vira_declarado(tmp_path, fonte):
    linha = _turno(tmp_path, "T0", "oi", fonte)
    assert linha["turno_fonte"] == "declarado" and oplog.validar(linha) == []
    assert linha["texto"] == "oi"                                   # a mensagem do dono nao se perde


@pytest.mark.parametrize("fonte", ["HOOK ", "  "])
def test_fonte_com_caixa_ou_espaco_e_normalizada(tmp_path, fonte):
    assert _turno(tmp_path, "T0", "oi", fonte)["turno_fonte"] == "hook"


def test_sem_turno_texto_o_texto_sai_nulo_e_o_turno_segue_declarado(tmp_path):
    linha = _turno(tmp_path, "T0")
    assert linha.get("texto") is None and linha["texto_bytes"] is None
    assert linha["turno_fonte"] == "declarado" and oplog.validar(linha) == []
    assert _turno(tmp_path, "T1", "   ").get("texto") is None      # so espaco nao e mensagem


def test_texto_longo_e_aparado_mas_o_tamanho_original_fica_em_texto_bytes(tmp_path):
    original = "ação " * 4000                                         # 20.000 caracteres
    linha = _turno(tmp_path, "T0", original, "hook")
    assert linha["texto_bytes"] == len(original.encode("utf-8"))
    assert len(linha["texto"].encode("utf-8")) <= oplog.LIMITE_CAMPO
    assert "texto" in linha["aparado"] and oplog.validar(linha) == []
    (arquivo,) = tmp_path.glob("ops-*.jsonl")
    assert len(arquivo.read_bytes().splitlines()[0]) + 1 <= oplog.LINHA_MAX


def test_o_turno_abre_uma_vez_e_so_a_primeira_chamada_leva_o_texto(tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        s._carimba_turno(IDENT, "T0", "primeira", "hook")
        s._carimba_turno(IDENT, "T0", "outra coisa", "hook")      # mesmo turno: nada novo
        s._carimba_turno(IDENT, "T1", "", "")
    turnos = _linhas(tmp_path)
    assert [t["turno_id"] for t in turnos] == ["T0", "T1"]
    assert turnos[0]["texto"] == "primeira" and turnos[1].get("texto") is None


def test_os_giros_seguintes_carregam_a_fonte_do_turno_sem_o_texto(tmp_path):
    _turno(tmp_path, "T0", "mensagem do dono", "transcript")
    giro = _giro(tmp_path)
    assert (giro["turno_id"], giro["turno_fonte"]) == ("T0", "transcript")
    assert "texto" not in giro and "mensagem do dono" not in json.dumps(giro, ensure_ascii=False)
    assert oplog.validar(giro) == []


def test_a_fonte_sobrevive_ao_restart_pela_chave_viva(tmp_path):
    rc = MagicMock(get=MagicMock(return_value=json.dumps(
        {"cadeira": "ti", "turno_valor": "T4", "turno_id": "T4", "turno_fonte": "hook"})))
    with patch.object(s, "_rc", return_value=rc):
        giro = _giro(tmp_path)
    assert (giro["turno_id"], giro["turno_fonte"]) == ("T4", "hook")


def test_fonte_nova_grava_na_chave_viva_sem_mexer_no_ttl(tmp_path):
    rc = MagicMock(get=MagicMock(return_value=json.dumps({"cadeira": "ti"})))
    with patch.object(s, "_rc", return_value=rc), patch.object(s, "LOG_DIR", tmp_path):
        s._carimba_turno(IDENT, "T0", "oi", "hook")
    chave, valor = rc.set.call_args.args
    assert chave == f"sessao:{SID}" and json.loads(valor)["turno_fonte"] == "hook"
    assert rc.set.call_args.kwargs == {"keepttl": True}


def test_o_contrato_do_turno_recusa_resposta_pacote_e_token():
    linha = {"ts": "t", "evento_id": "e", "schema_v": 1, "origem": "cadeira", "mapa_v": None,
             "tool": "sessao", "evento": "turno", "sessao_id": SID, "turno_id": "T0",
             "turno_fonte": "hook", "sujeito": "x", "sub": "x", "username": "x", "azp": "x",
             "sid": "x", "jti": "x", "texto": "oi", "texto_bytes": 2}
    assert oplog.validar(linha) == []
    for campo in ("resposta", "pacote", "token"):
        assert f"nao se grava {campo}" in oplog.validar({**linha, campo: "x"})


def test_toda_tool_da_porta_aceita_turno_texto_e_turno_fonte_opcionais():
    tools = [s.malote, s.run_command, s.ler_arquivo, s.read_file, s.write_file, s.monta_sessao,
             s._faz_tool_verbo("tarefas", "/bin/true", "x")]
    for tool in tools:
        params = inspect.signature(tool).parameters
        for campo in ("turno_texto", "turno_fonte"):
            p = params.get(campo)
            assert p is not None and p.default == "", f"{tool.__name__}.{campo}"


def test_o_texto_chega_pelo_parametro_da_tool_de_verbo_e_fica_so_na_linha_de_turno(tmp_path):
    tool = s._faz_tool_verbo("tarefas", "/bin/true", "x")
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r), \
            patch.object(s, "_sessao_resolve", return_value=IDENT), \
            patch.object(s, "_run_verbo_blocking", return_value={"exit_code": 0, "stdout": {"texto": "ok"}}):
        asyncio.run(tool(ato="ler", args=["3357"], turno="T7", turno_texto="cards 3356 e 3357",
                         turno_fonte="transcript"))
    turno, giro = _linhas(tmp_path)
    assert turno["evento"] == "turno" and turno["texto"] == "cards 3356 e 3357"
    assert (turno["turno_id"], turno["turno_fonte"]) == ("T7", "transcript")
    assert giro["tool"] == "tarefas" and (giro["turno_id"], giro["turno_fonte"]) == ("T7", "transcript")
    assert "cards 3356 e 3357" not in json.dumps(giro, ensure_ascii=False)
    assert oplog.validar(turno) == [] and oplog.validar(giro) == []
