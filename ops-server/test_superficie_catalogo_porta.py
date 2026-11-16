"""Contratos de catalogo de verbos, lote, sessao e superficie na porta."""
from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-sup-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import poda as _p
import server as s
from test_poda_porta import FakeRedisMemoria

s._MORADAS_LEITURA += (str(HARNESS_DIR),)

_UUID_A = "11111111-2222-4333-8444-555555555555"
_REQ = str(OPS_SERVER_DIR / "requirements.txt")

REGISTRO_DE_ENSAIO = """
verbos:
  visivel: {}
  retido: {retido: true}
  oculto: {modelo: false}
  semdesc: {}
  sembin: {}
transporte:
  malote: {}
"""


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _porta_com_registro(tmp_path, texto, bins, projecao, **opcoes):
    acervo_cai = bool(opcoes.get("acervo_cai"))
    leva2 = bool(opcoes.get("leva2"))
    reg = tmp_path / "porta.yaml"
    reg.write_text(texto, encoding="utf-8")
    pasta = tmp_path / "bin"
    pasta.mkdir(exist_ok=True)
    for nome in bins:
        (pasta / nome).write_text("#!/bin/sh\n", encoding="utf-8")
        (pasta / nome).chmod(0o755)
    cp = subprocess.CompletedProcess([], 0, stdout=json.dumps(projecao), stderr="")
    efeito = OSError("acervo fora") if acervo_cai else None
    retidos, ocultas = set(), set()
    with patch.object(s, "TOOLS_VERBOS", True), patch.object(s, "TOOLS_LEVA2", leva2), patch.object(
        s, "PERSONAS"
    ) as _pers, patch.object(s, "SLUGS_RETIDOS", retidos), patch.object(
        s, "OCULTAS", ocultas
    ), patch.object(
        s, "REGISTRO_PORTA", reg
    ), patch.object(
        s, "BIN_VERBOS", pasta
    ), patch.object(
        s, "mcp"
    ) as _mcp, patch.object(
        s, "_faz_tool_verbo", return_value=lambda: None
    ), patch.dict(
        s.BINARIOS, {}
    ), patch(
        "server.subprocess.run", return_value=cp, side_effect=efeito
    ):
        _pers.is_dir.return_value = True
        servidas = s._gera_tools_verbos()
    registradas = {c.kwargs["name"]: c.kwargs["description"] for c in _mcp.tool.call_args_list}
    return servidas, retidos, ocultas, registradas


def test_o_registro_decide_retencao_ocultas_e_descricao(tmp_path):
    projecao = [{"tool": "visivel", "descricao": "d visivel"}, {"tool": "retido", "descricao": "d"}]
    servidas, retidos, ocultas, registradas = _porta_com_registro(
        tmp_path, REGISTRO_DE_ENSAIO, ["visivel", "retido", "oculto", "semdesc"], projecao
    )
    assert servidas == ["visivel", "oculto", "semdesc"]
    assert retidos == {"retido"} and ocultas == {"oculto"}
    assert registradas["visivel"] == "d visivel"
    assert registradas["semdesc"] == s.DESCRICAO_INDISPONIVEL and "oculto" in registradas


def test_retido_serve_com_a_leva_2_ligada(tmp_path):
    servidas, retidos, _ocultas, _reg = _porta_com_registro(
        tmp_path, REGISTRO_DE_ENSAIO, ["visivel", "retido", "oculto", "semdesc"], [], leva2=True
    )
    assert "retido" in servidas and not retidos


def test_acervo_fora_na_subida_nao_tira_verbo_do_ar(tmp_path):
    servidas, _retidos, _ocultas, registradas = _porta_com_registro(
        tmp_path, REGISTRO_DE_ENSAIO, ["visivel", "retido", "oculto", "semdesc"], [], acervo_cai=True
    )
    assert servidas == ["visivel", "oculto", "semdesc"]
    assert set(registradas.values()) == {s.DESCRICAO_INDISPONIVEL}


def test_registro_ilegivel_deixa_a_porta_sem_verbo_e_sem_abrir_o_bin(tmp_path):
    servidas, retidos, ocultas, registradas = _porta_com_registro(
        tmp_path, "verbos: [isto, nao, e, mapa]\ntransporte: {}\n", ["visivel"], []
    )
    assert servidas == [] and not retidos and not ocultas and not registradas


def test_audit_tools_carregam_identidade_e_metricas(tmp_path):
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        asyncio.run(s.malote(command="git status", sessao_id="ensaio-sid-abc"))
    achou_m = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "malote"]
    assert achou_m and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou_m)

    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod, patch.object(_p, "DERRAME", tmp_path):
        _rmod.Redis = FakeRedisMemoria()
        s.ler_arquivo(caminho=_REQ, sessao_id=_UUID_A)
    achou_l = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "ler_arquivo"]
    assert achou_l and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou_l)
    assert achou_l[0]["bytes_servidos"] and achou_l[0]["sha"]

    alvo = s.TMP_FITA / "_ensaio_write_probe.txt"
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        s.write_file(path=str(alvo), content="ensaio\n", sessao_id="ensaio-sid-abc")
    achou_w = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "write_file"]
    assert achou_w and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou_w)
    alvo.unlink(missing_ok=True)

    with patch.object(s, "LOG_DIR", tmp_path):
        s._audit(tool="-", evento="teste_sem_sessao")
        linha = json.loads(next(iter(tmp_path.glob("ops-*.jsonl"))).read_text().splitlines()[0])
    assert linha["sessao_id"] == "-"


def test_lote_verbo_contratos():
    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(s, "_autoriza", return_value=None):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r = asyncio.run(_tool(lote=[{"ato": "ver"}, {"ato": "ver"}]))
    assert r["lote_n"] == 2 and len(r["lote"]) == 2

    sentinela = {"erro": "negado de teste"}

    def _run_verbo_nao_deveria_rodar(*a, **k):
        raise AssertionError("_run_verbo_blocking nao deveria rodar quando _autoriza nega")

    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(
        s, "_autoriza", return_value=sentinela
    ), patch.object(s, "_run_verbo_blocking", side_effect=_run_verbo_nao_deveria_rodar):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r_neg = asyncio.run(_tool(lote=[{"ato": "ver"}, {"ato": "ver"}]))
    assert r_neg["lote"] == [sentinela, sentinela]

    with patch.object(s, "PF_TOOLS_LOTE", False), patch.object(s, "_autoriza", return_value=None):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r_off = asyncio.run(_tool(ato="ver", lote=[{"ato": "ver"}]))
    assert "lote" not in r_off


def _pacote_falso(sessao_id=None, **extra):
    sid = sessao_id or str(uuid.uuid4())
    return {
        "cadeira": "fabrica",
        "nome_canonico": "fabrica",
        "pecas": [],
        "sessao_id": sid,
        "sessao": {"id": sid, "cunhada_agora": not sessao_id},
        "roteador": {"via": "teste", "slug": None},
        **extra,
    }


def test_sessao_cunhagem_repasse_e_resolucao():
    with patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "_montar", side_effect=lambda *a: _pacote_falso(a[4] or None)
    ), patch.object(s, "redis") as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        r1 = asyncio.run(s.monta_sessao(cadeira="fabrica", pergunta="oi"))
        sid = r1["sessao_id"]
        r2 = asyncio.run(s.monta_sessao(cadeira="fabrica", sessao_id=sid))
    assert str(uuid.UUID(sid)) == sid and sid.count("-") == 4
    assert r1["sessao"]["cunhada_agora"] is True
    assert r2["sessao_id"] == sid and r2["sessao"]["cunhada_agora"] is False

    visto = {}

    def _duble(cadeira, atualizar, chapeu, pergunta, sessao_id, *resto):
        visto["sessao_id"] = sessao_id
        return _pacote_falso(sessao_id or None)

    with patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "_montar", side_effect=_duble
    ), patch.object(s, "redis") as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        asyncio.run(s.monta_sessao(cadeira="fabrica", sessao_id=_UUID_A))
    assert visto["sessao_id"] == _UUID_A

    fonte = (HARNESS_DIR / "bin/monta-sessao").read_text(encoding="utf-8")
    no = next(
        n
        for n in ast.walk(ast.parse(fonte))
        if isinstance(n, ast.FunctionDef) and n.name == "cunha_sessao"
    )
    ns: dict = {}
    exec(compile(ast.Module([no], []), "bin/monta-sessao", "exec"), ns)  # noqa: S102 — função isolada de bin/monta-sessao
    cunha = ns["cunha_sessao"]
    sid1, cunhada1, aviso1 = cunha(None)
    assert uuid.UUID(sid1) and cunhada1 is True and aviso1 is None
    sid2, cunhada2, _ = cunha(sid1)
    assert sid2 == sid1 and cunhada2 is False

    fake_res = FakeRedisMemoria(
        kv={
            f"sessao:{_UUID_A}": json.dumps({"cadeira": "fabrica", "ordem_id": "o-x"}),
            "conexao:hdr-abc": _UUID_A,
        }
    )
    with patch.object(s, "redis") as _rmod:
        _rmod.Redis = fake_res
        assert s._sessao_resolve(None)["sessao_id"] == "-"
        out = s._sessao_resolve(_UUID_A)
    assert out["sessao_id"] == _UUID_A and out["cadeira"] == "fabrica"


def _le_opcional(caminho: Path, padrao: str) -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except OSError:
        return padrao


def _fake_montar_superficie(cadeira, *args, **kwargs):
    cad = cadeira if cadeira and cadeira != "-" else ""
    p_dir = os.environ.get("PF_ABERTURA_DIR")
    txt_p = "PERSONA FAKE"
    txt_c = "CONDUTA FAKE"
    if p_dir:
        base = Path(p_dir) / "current" / "abertura"
        txt_p = _le_opcional(base / (cad or "ia") / "persona.md", txt_p)
        txt_c = _le_opcional(base / "dono.md", txt_c)
    sha_p = s._poda.sha_servido(txt_p)
    sha_c = s._poda.sha_servido(txt_c)
    return {
        "cadeira": cad,
        "nome_canonico": cad,
        "sessao_id": "test-sessao-123",
        "ordem_id": "test-ordem-123",
        "chapeu": None,
        "roteador": {"via": "fallback", "slug": None},
        "pacote": {"pecas": 2, "tokens": 200},
        "pecas": [
            {
                "peca": "persona",
                "ref": f"abertura/{cad}/persona.md" if cad else "persona",
                "sha": sha_p,
                "conteudo": txt_p,
                "tokens": 100,
            },
            {
                "peca": "conduta",
                "ref": "abertura/dono.md",
                "sha": sha_c,
                "conteudo": txt_c,
                "tokens": 100,
            },
        ],
        "avisos": [],
    }


def _roda_monta_com_headers(tmp_path, headers, quem, mapa=None):
    ctx = MagicMock()
    ctx.request_context.request.headers = headers
    mapa_dict = mapa or {"fabrica-teste": "fabrica"}
    with patch.object(s.mcp, "get_context", return_value=ctx), patch.object(
        s, "_autoriza", return_value=None
    ), patch.object(s, "_quem", return_value=quem), patch.object(
        s, "_mapa_azp_superficie", return_value=mapa_dict
    ), patch.object(
        s, "redis"
    ) as _rmod, patch.object(
        s, "_montar", side_effect=_fake_montar_superficie
    ), patch.dict(
        "os.environ", {"PF_ABERTURA_DIR": str(tmp_path), "PF_SUPERFICIE": "desconhecida"}
    ):
        _rmod.Redis = FakeRedisMemoria()
        sup = s._superficie()
        r = asyncio.run(s.monta_sessao(cadeira="ia", pergunta="oi"))
    return sup, next(x for x in r["pecas"] if x["peca"] == "persona")


def test_superficie_resolucao_e_ponteiros(tmp_path):
    ab_ia = tmp_path / "current" / "abertura" / "ia"
    ab_ia.mkdir(parents=True)
    for rel, txt in (
        ("dono.md", "CONDUTA FAKE"),
        ("ia/persona.md", "PERSONA FAKE"),
    ):
        (tmp_path / "current" / "abertura" / rel).write_text(txt, encoding="utf-8")
    sha_persona = s._poda.sha_servido("PERSONA FAKE")

    sup1, p1 = _roda_monta_com_headers(
        tmp_path,
        {"x-pf-superficie": "claude.ai", "mcp-session-id": "t1"},
        {"sub": "claudinho", "azp": "claudinho-mcp"},
    )
    assert sup1 == "claude.ai" and p1["regime"] == "ponteiro" and p1["poda"]["sha"] == sha_persona

    sup2, p2 = _roda_monta_com_headers(
        tmp_path,
        {"x-pf-superficie": "code", "mcp-session-id": "t2"},
        {"sub": "claudinho", "azp": "claudinho-mcp"},
    )
    assert sup2 == "code" and p2.get("regime") != "ponteiro" and p2["conteudo"] == "PERSONA FAKE"

    sup3, p3 = _roda_monta_com_headers(
        tmp_path,
        {"mcp-session-id": "t3"},
        {"sub": "fab", "azp": "fabrica-teste"},
    )
    assert sup3 == "fabrica" and p3.get("regime") != "ponteiro"

    sup4, p4 = _roda_monta_com_headers(
        tmp_path,
        {"mcp-session-id": "t4"},
        {"sub": "alheio", "azp": "azp-desconhecido-xyz"},
    )
    assert sup4 == "desconhecida" and p4.get("regime") != "ponteiro"
