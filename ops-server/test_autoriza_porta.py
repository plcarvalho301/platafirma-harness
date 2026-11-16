"""Contrato do PEP da porta (_autoriza): decisao real sobre politica.yaml e sujeitos.yaml."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-autoriza-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import server as s

POLITICA_FIXTURE = """\
versao: 1
eixos:
  dominio:
    plataforma:
      rotulo: "Raiz da plataforma"
    plataforma-runtime:
      rotulo: "Runtime"
      pai: plataforma
    plataforma-identidade:
      rotulo: "Identidade e segredo"
      pai: plataforma
    mensageria:
      rotulo: "Mensageria"
      pai: plataforma
  papel:
    operador:
      rotulo: "Operador humano"
    fornecedor:
      rotulo: "Fornecedor escopado"
  unidade-organizacional:
    pf:
      rotulo: "PlataFirma"
  tema: {}
regras:
  - id: operador-plataforma
    efeito: permite
    motivo: "operador alcanca a plataforma"
    quando: {papel: operador, dominio: plataforma}
    acoes: ["*"]
    sobre: ["*"]
  - id: fornecedor-opera-tarefas
    efeito: permite
    motivo: "fornecedor le e comenta card"
    quando: {papel: fornecedor, dominio: plataforma, tipo: comando}
    acoes: [run_command]
    sobre: ["tarefas ler*", "tarefas comentar*"]
  - id: fornecedor-sem-segredo
    efeito: nega
    motivo: "segredo fora do alcance do fornecedor"
    quando: {papel: fornecedor}
    acoes: ["*"]
    sobre: ["seg *", "acesso *"]
"""

SUJEITOS_FIXTURE = """\
versao: 1
sujeitos:
  sub-operador:
    natureza: pessoa
    papeis: [operador]
    dominios: [plataforma]
    habilitacao: publico
  sub-fornecedor:
    natureza: servico
    papeis: [fornecedor]
    dominios: [plataforma-runtime]
    habilitacao: publico
  sub-sem-papel:
    natureza: servico
    papeis: []
    dominios: [plataforma-runtime]
"""


@pytest.fixture
def pdp_fixture(tmp_path, monkeypatch):
    (tmp_path / "politica.yaml").write_text(POLITICA_FIXTURE, encoding="utf-8")
    (tmp_path / "sujeitos.yaml").write_text(SUJEITOS_FIXTURE, encoding="utf-8")
    monkeypatch.setattr(s, "PDP_DIR", tmp_path)
    monkeypatch.setattr(
        s, "_pdp", {"carimbo": None, "politica": None, "sujeitos": None, "erro": "nao carregada"}
    )
    return tmp_path


@pytest.mark.parametrize(
    ("sujeito", "tool", "alvo", "dominio"),
    [
        ("sub-operador", "tarefas", "tarefas ler 1", "plataforma-runtime"),
        ("sub-operador", "seg", "seg listar", "plataforma-identidade"),
        ("sub-fornecedor", "tarefas", "tarefas ler 722", "plataforma-runtime"),
    ],
)
def test_autoriza_permite_quando_regra_concede(pdp_fixture, sujeito, tool, alvo, dominio):
    with patch.object(s, "_quem", return_value={"sujeito": sujeito}), patch.object(
        s, "_audit"
    ) as aud:
        decisao = s._autoriza(tool, "run_command", "comando", alvo, dominio)
    assert decisao is None
    assert not [c for c in aud.call_args_list if c.kwargs.get("evento") == "pep_negou"]


@pytest.mark.parametrize(
    ("sujeito", "alvo", "dominio", "esperado"),
    [
        ("sub-fornecedor", "seg ler x", "plataforma-runtime", ("fornecedor-sem-segredo", False)),
        ("sub-fornecedor", "release promover x", "plataforma-runtime", ("default", False)),
        ("sub-fornecedor", "tarefas ler 1", "plataforma-identidade", ("intersecao", False)),
        ("sub-sem-papel", "tarefas ler 1", "plataforma-runtime", (None, True)),
    ],
)
def test_autoriza_nega_com_exit_4_e_audita_pep_negou(
    pdp_fixture, sujeito, alvo, dominio, esperado
):
    regra_esperada, por_falta = esperado
    with patch.object(s, "_quem", return_value={"sujeito": sujeito}), patch.object(
        s, "_audit"
    ) as aud:
        decisao = s._autoriza("tarefas", "run_command", "comando", alvo, dominio)
    assert decisao is not None
    assert decisao["exit_code"] == 4
    assert "negado pela política de acesso" in decisao["falta"]
    assert decisao["regra"] == regra_esperada
    eventos = [c.kwargs for c in aud.call_args_list if c.kwargs.get("evento") == "pep_negou"]
    assert len(eventos) == 1
    ev = eventos[0]
    assert ev["sujeito"] == sujeito
    assert ev["regra"] == regra_esperada
    assert ev["por_atributo_ausente"] is por_falta


def test_autoriza_nega_sujeito_sem_projecao(pdp_fixture):
    with patch.object(s, "_quem", return_value={"sujeito": "sub-inexistente"}), patch.object(
        s, "_audit"
    ) as aud:
        decisao = s._autoriza("tarefas", "run_command", "comando", "tarefas ler 1", "plataforma-runtime")
    assert decisao is not None
    assert decisao["exit_code"] == 4
    assert decisao["regra"] == "projecao"
    eventos = [c.kwargs for c in aud.call_args_list if c.kwargs.get("evento") == "pep_negou"]
    assert len(eventos) == 1 and eventos[0]["regra"] == "projecao"


def test_autoriza_falha_fechado_com_exit_3_quando_politica_ilegivel(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "PDP_DIR", tmp_path)
    monkeypatch.setattr(
        s, "_pdp", {"carimbo": None, "politica": None, "sujeitos": None, "erro": "nao carregada"}
    )
    with patch.object(s, "_quem", return_value={"sujeito": "sub-operador"}), patch.object(
        s, "_audit"
    ) as aud:
        decisao = s._autoriza("tarefas", "run_command", "comando", "tarefas ler 1", "plataforma-runtime")
    assert decisao is not None
    assert decisao["exit_code"] == 3
    assert "indisponível" in decisao["falta"]
    eventos = [c.kwargs for c in aud.call_args_list if c.kwargs.get("evento") == "pep_indisponivel"]
    assert len(eventos) == 1 and eventos[0]["sujeito"] == "sub-operador"


def test_tool_verbo_obedece_autoriza_sem_duble(pdp_fixture, tmp_path):
    verbo = tmp_path / "tarefas"
    verbo.write_text("#!/bin/sh\necho executou\n", encoding="utf-8")
    verbo.chmod(0o755)
    tool = s._faz_tool_verbo("tarefas", str(verbo), "tarefas de teste")

    with patch.object(s, "_quem", return_value={"sujeito": "sub-fornecedor"}), patch.object(
        s, "_audit"
    ) as aud, patch.object(s, "_run_verbo_blocking") as exec_mock:
        negado = asyncio.run(tool(ato="apagar", args=["1"]))
    assert negado["exit_code"] == 4
    assert "negado pela política de acesso" in negado["falta"]
    exec_mock.assert_not_called()
    assert any(c.kwargs.get("evento") == "pep_negou" for c in aud.call_args_list)

    retorno_ok = {"exit_code": 0, "stdout": {"texto": "ok\n", "truncado": False, "bytes_total": 3}}
    with patch.object(s, "_quem", return_value={"sujeito": "sub-fornecedor"}), patch.object(
        s, "_audit"
    ), patch.object(s, "_run_verbo_blocking", return_value=retorno_ok) as exec_ok:
        permitido = asyncio.run(tool(ato="ler", args=["722"]))
    assert permitido["exit_code"] == 0
    exec_ok.assert_called_once()
