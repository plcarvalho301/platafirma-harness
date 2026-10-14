"""A porta entrega o fundamento da face ao verbo (card #3513, unidade U1; arq:0124 R16).

A tela do dono manda `turno_fonte="face"` e, em `turno_texto`, a razao do ato. A porta:

  - aceita `face` no vocabulario de `turno_fonte` (o que a chamada entrega vale);
  - entrega o texto ao verbo em `PF_FUNDAMENTO`, e so a face o produz: o que o env da porta trouxer
    nao chega ao verbo;
  - recusa, ANTES de executar, o ato declarado so de escrita (`# atos: x (escrita, ...)`) sem texto, e
    qualquer `--fundamento` junto do texto da face (seriam dois textos para o mesmo ato);
  - deixa passar o ato misto (`leitura|escrita`, como `motor ajuste`): quem sabe se a chamada escreve e o
    verbo, que sai 2 sem fundamento;
  - nao muda nada fora da face.

O verbo dos testes e um script de brinquedo com cabecalho `# atos:`, que escreve `PF_FUNDAMENTO` no
stdout e deixa uma marca em disco: a marca prova que o verbo rodou, ou que a recusa veio antes.
Vive em ops-server/ porque server.py precisa do venv com `mcp`.
"""
from __future__ import annotations

import asyncio
import json
import os
import stat
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

_TMP = Path(tempfile.mkdtemp(prefix="ops-fundamento-face-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import oplog  # noqa: E402
import server as s  # noqa: E402

SID = "44444444-4444-4444-8444-444444444444"
IDENT_TOKEN = {"sujeito": "b6986be0", "sub": "b6986be0", "username": "megafone",
               "azp": "agy-cli", "sid": "sid-login", "jti": "jti-1"}
IDENT = {"sessao_id": SID, "ordem_id": "o1", "cadeira": "ia", "sujeito": "", "origem_sessao": ""}

SCRIPT = """#!/bin/sh
# fake — verbo de teste do card #3513
# atos: gravar (escrita, x), ler (leitura, x), misto (leitura|escrita, x)
echo "FUND=$PF_FUNDAMENTO"
: > "$PF_MARCA"
"""


@pytest.fixture(autouse=True)
def porta_isolada():
    s._ORIGENS.clear()
    s._CARIMBOS.clear()
    s._DECLARA_EXIT.clear()
    s._ATOS_DO_CABECALHO.clear()
    with patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))), \
            patch.object(s, "_quem", return_value=IDENT_TOKEN):
        yield
    s._ORIGENS.clear()
    s._CARIMBOS.clear()
    s._ATOS_DO_CABECALHO.clear()


class Verbo:
    """O verbo de brinquedo: `str(verbo)` e o caminho dele, `verbo.marca` o arquivo que ele cria ao rodar."""

    def __init__(self, caminho: Path, marca: Path):
        self.caminho, self.marca = caminho, marca

    def __str__(self) -> str:
        return str(self.caminho)


@pytest.fixture
def verbo(tmp_path, monkeypatch):
    caminho = tmp_path / "fake"
    caminho.write_text(SCRIPT, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR)
    marca = tmp_path / "rodou"
    monkeypatch.setenv("PF_MARCA", str(marca))
    monkeypatch.delenv("PF_FUNDAMENTO", raising=False)
    return Verbo(caminho, marca)


def _saiu(r) -> str:
    return r["stdout"]["texto"]


def _linhas(pasta) -> list[dict]:
    return [json.loads(linha) for f in sorted(pasta.glob("ops-*.jsonl"))
            for linha in f.read_text(encoding="utf-8").splitlines()]


def _tool(verbo_, tmp_path):
    """A tool de verbo de `_faz_tool_verbo`, sem PEP e sem poda, com a porta no log do teste."""
    return s._faz_tool_verbo("fake", str(verbo_), "x")


def _roda(tool, tmp_path, **kw):
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r), \
            patch.object(s, "_sessao_resolve", return_value=IDENT):
        return asyncio.run(tool(**kw))


# --- vocabulario ----------------------------------------------------------------------------

def test_face_e_fonte_de_turno_e_o_chamador_pode_entrega_la(tmp_path):
    assert "face" in oplog.FONTES_TURNO and "face" in oplog.FONTES_ENTREGUES
    with patch.object(s, "LOG_DIR", tmp_path):
        s._carimba_turno(IDENT, "T0", "ajusta o piso porque a cobertura caiu", "face")
    (turno,) = [t for t in _linhas(tmp_path) if t.get("evento") == "turno"]
    assert turno["turno_fonte"] == "face" and turno["texto"].startswith("ajusta o piso")
    assert oplog.validar(turno) == []


# --- o subprocesso: PF_FUNDAMENTO vem da chamada e de mais nada -----------------------------

def test_o_verbo_ve_o_fundamento_que_a_chamada_entrega(verbo):
    r = s._run_verbo_blocking([str(verbo), "ler"], None, 10, IDENT, None, "porque a cobertura caiu")
    assert "FUND=porque a cobertura caiu" in _saiu(r)


def test_sem_fundamento_o_verbo_nao_ve_nada_mesmo_com_o_env_da_porta_sujo(verbo, monkeypatch):
    monkeypatch.setenv("PF_FUNDAMENTO", "do ambiente da porta")
    r = s._run_verbo_blocking([str(verbo), "ler"], None, 10, IDENT)
    assert _saiu(r).strip() == "FUND="


# --- a decisao: fundamento e recusa ---------------------------------------------------------

def _decide(verbo_, *tokens, texto="", fonte="face"):
    return s._fundamento_do_ato("fake", str(verbo_), [str(verbo_), *tokens], IDENT, texto, fonte)


def test_fora_da_face_nada_muda_nem_para_o_ato_de_escrita(verbo):
    for fonte in ("", "hook", "transcript", "declarado", "runner"):
        assert _decide(verbo, "gravar", texto="qualquer", fonte=fonte) == (None, None)
        assert _decide(verbo, "gravar", "--fundamento", "x", fonte=fonte) == (None, None)


def test_face_com_texto_entrega_o_fundamento_nos_tres_tipos_de_ato(verbo):
    for ato in ("gravar", "ler", "misto"):
        fundamento, recusa = _decide(verbo, ato, texto="  porque sim \n")
        assert (fundamento, recusa) == ("porque sim", None), ato


def test_face_sem_texto_recusa_so_o_ato_declarado_so_de_escrita(verbo):
    fundamento, recusa = _decide(verbo, "gravar", texto="   ")
    assert fundamento is None and recusa["recusado"] is True and "sem fundamento" in recusa["motivo"]
    assert recusa["verbo"] == "fake" and "gravar" in recusa["motivo"]
    # leitura e ato misto passam: o misto o verbo recusa, na escrita, com exit 2
    assert _decide(verbo, "ler", texto="") == (None, None)
    assert _decide(verbo, "misto", texto="") == (None, None)
    # ato que o cabecalho nao declara nao e escrita para a porta
    assert _decide(verbo, "inventado", texto="") == (None, None)


def test_a_instancia_antes_do_ato_nao_esconde_a_escrita(verbo):
    """`motor rag trocar ...`: o ato esta em argv[2], nao em argv[1]."""
    assert _decide(verbo, "rag", "gravar", "biblioteca", texto="")[1]["recusado"] is True
    assert _decide(verbo, "rag", "ler", "biblioteca", texto="") == (None, None)
    assert _decide(verbo, "rag", "gravar", "biblioteca", texto="porque")[0] == "porque"


@pytest.mark.parametrize("flag", [["--fundamento", "outra razao"], ["--fundamento=outra razao"]])
def test_a_flag_fundamento_junto_da_face_e_recusada_mesmo_no_ato_misto(verbo, flag):
    fundamento, recusa = _decide(verbo, "misto", *flag, texto="a razao da face")
    assert fundamento is None and recusa["recusado"] is True and "dois textos" in recusa["motivo"]


def test_a_fonte_vem_normalizada(verbo):
    assert _decide(verbo, "gravar", texto="porque", fonte=" FACE ")[0] == "porque"


def test_o_fundamento_longo_e_cortado_no_teto_sem_partir_caractere(verbo):
    fundamento, recusa = _decide(verbo, "gravar", texto="ç" * 5000)        # 10.000 bytes
    assert recusa is None and 0 < len(fundamento.encode("utf-8")) <= s.FUNDAMENTO_MAX
    assert set(fundamento) == {"ç"}


def test_verbo_sem_a_linha_de_atos_nao_recusa_nada(tmp_path):
    cru = tmp_path / "cru"
    cru.write_text("#!/bin/sh\n# cru — sem atos declarados\necho oi\n", encoding="utf-8")
    cru.chmod(cru.stat().st_mode | stat.S_IXUSR)
    assert s._fundamento_do_ato("cru", str(cru), [str(cru), "gravar"], IDENT, "", "face") == (None, None)


def test_a_recusa_fica_no_bruto_como_escrita_recusada_valida(verbo, tmp_path):
    with patch.object(s, "LOG_DIR", tmp_path):
        _decide(verbo, "gravar", texto="")
    (linha,) = [t for t in _linhas(tmp_path) if t.get("evento") == "escrita_recusada"]
    assert linha["tool"] == "fake" and linha["ato"] == "gravar" and linha["classe"] == "gramatica"
    assert "sem fundamento" in linha["motivo"] and oplog.validar(linha) == []


# --- a tool de verbo: a recusa vem antes de executar ----------------------------------------

def test_tool_face_com_texto_roda_e_o_verbo_ve_o_fundamento(verbo, tmp_path):
    r = _roda(_tool(verbo, tmp_path), tmp_path, ato="gravar", turno="T1",
              turno_texto="o piso estava alto demais", turno_fonte="face")
    assert r["exit_code"] == 0 and "FUND=o piso estava alto demais" in _saiu(r)
    assert verbo.marca.exists()


def test_tool_face_sem_texto_recusa_a_escrita_e_o_verbo_nao_roda(verbo, tmp_path):
    r = _roda(_tool(verbo, tmp_path), tmp_path, ato="gravar", turno="T1", turno_fonte="face")
    assert r["recusado"] is True and "exit_code" not in r
    assert not verbo.marca.exists()


def test_tool_face_sem_texto_deixa_o_ato_de_leitura_rodar_sem_fundamento(verbo, tmp_path):
    r = _roda(_tool(verbo, tmp_path), tmp_path, ato="ler", turno="T1", turno_fonte="face")
    assert r["exit_code"] == 0 and _saiu(r).strip() == "FUND=" and verbo.marca.exists()


def test_tool_fora_da_face_segue_como_era(verbo, tmp_path):
    r = _roda(_tool(verbo, tmp_path), tmp_path, ato="gravar", turno="T1",
              turno_texto="msg do dono no Code", turno_fonte="hook")
    assert r["exit_code"] == 0 and _saiu(r).strip() == "FUND=" and verbo.marca.exists()


def test_tool_em_lote_recusa_o_item_de_escrita_sem_texto_e_roda_o_resto(verbo, tmp_path, monkeypatch):
    monkeypatch.setattr(s, "PF_TOOLS_LOTE", True)
    out = _roda(_tool(verbo, tmp_path), tmp_path, lote=[{"ato": "gravar"}, {"ato": "ler"}],
                turno="T1", turno_fonte="face")
    gravar, ler = out["lote"]
    assert gravar["recusado"] is True
    assert ler["exit_code"] == 0 and _saiu(ler).strip() == "FUND="


def test_tool_em_lote_entrega_o_fundamento_a_cada_item(verbo, tmp_path, monkeypatch):
    monkeypatch.setattr(s, "PF_TOOLS_LOTE", True)
    out = _roda(_tool(verbo, tmp_path), tmp_path, lote=[{"ato": "gravar"}, {"ato": "misto"}],
                turno="T1", turno_texto="uma razao so", turno_fonte="face")
    assert all("FUND=uma razao so" in _saiu(item) for item in out["lote"])


# --- o malote -------------------------------------------------------------------------------

def _malote(verbo_, tmp_path, monkeypatch, item, **kw):
    monkeypatch.setattr(s, "SLUGS_SERVIDOS", {"fake"})
    monkeypatch.setitem(s.BINARIOS, "fake", str(verbo_))
    with patch.object(s, "LOG_DIR", tmp_path), patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r), \
            patch.object(s, "_sessao_resolve", return_value=IDENT):
        return asyncio.run(s.malote(commands=[item], **kw))


def test_malote_face_com_texto_entrega_o_fundamento(verbo, tmp_path, monkeypatch):
    r = _malote(verbo, tmp_path, monkeypatch, "fake gravar", turno="T1",
                turno_texto="razao pelo malote", turno_fonte="face")
    assert r["exit_code"] == 0 and "FUND=razao pelo malote" in _saiu(r)


def test_malote_face_sem_texto_recusa_a_escrita_antes_de_rodar(verbo, tmp_path, monkeypatch):
    r = _malote(verbo, tmp_path, monkeypatch, "fake gravar", turno="T1", turno_fonte="face")
    assert r["recusado"] is True and not verbo.marca.exists()


def test_malote_fora_da_face_nao_ganha_fundamento(verbo, tmp_path, monkeypatch):
    r = _malote(verbo, tmp_path, monkeypatch, "fake gravar", turno="T1",
                turno_texto="texto de transcript", turno_fonte="transcript")
    assert r["exit_code"] == 0 and _saiu(r).strip() == "FUND="
