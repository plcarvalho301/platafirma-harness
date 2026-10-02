"""O agente delegado abre pela mesma tool que a cadeira (incidente #3223, ordem do dono 01/10/2026).

`monta_sessao` repassa `origem`/`agente` a `sessao abrir` e `perfil`/`modo`/`regua` a `expediente montar`,
com PF_ORIGEM_SESSAO no ambiente do expediente. Sem esses campos, a abertura da cadeira fica byte a byte
como antes. `sessao` e `expediente` são dublês que gravam argv e ambiente.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-monta-agente-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)
_BANCADA_ANTES = os.environ.pop("PLATAFIRMA_BANCADA", None)
os.environ.setdefault("PLATAFIRMA_ARQUIVO_BANCADA", str(_TMP / "sem-declaracao"))

import server as s  # noqa: E402

if _BANCADA_ANTES is not None:
    os.environ["PLATAFIRMA_BANCADA"] = _BANCADA_ANTES

FILHA = "33333333-3333-4333-8333-333333333333"
ORQ = "11111111-1111-4111-8111-111111111111"

STUB = """#!{py}
import json, os, sys
open({log!r}, "a").write(json.dumps({{"verbo": {nome!r}, "argv": sys.argv[1:],
    "origem": os.environ.get("PF_ORIGEM_SESSAO"), "stdin": "" if {nome!r} == "sessao" else sys.stdin.read()}}) + "\\n")
if {nome!r} == "sessao":
    print(json.dumps({{"sessao_id": "{filha}", "cadeira": "engenharia", "ordem_id": "o-filha"}}))
else:
    print(json.dumps({{"pecas": [{{"peca": "modo", "conteudo": "LENTE"}}]}}))
"""


def _mundo(tmp_path):
    log = tmp_path / "log.jsonl"
    bins = {}
    for nome in ("sessao", "expediente"):
        arq = tmp_path / nome
        arq.write_text(STUB.format(py=sys.executable, log=str(log), nome=nome, filha=FILHA))
        arq.chmod(0o755)
        bins[nome] = str(arq)

    def chamadas():
        return [json.loads(l) for l in log.read_text().splitlines()]

    return bins, chamadas


def _monta(tmp_path, **kw):
    bins, chamadas = _mundo(tmp_path)

    def rc_fora():
        raise RuntimeError("sem msg-mem no teste")

    with patch.object(s, "_acha_bin", side_effect=lambda nome: bins[nome]), patch.object(s, "_rc", rc_fora):
        r = s._montar("engenharia", True, kw.pop("chapeu", "devops"), kw.pop("pergunta", "a tarefa"), None, "suj-1", **kw)
    return r, chamadas()


def test_agente_abre_pela_mesma_tool_com_origem_perfil_modo_e_regua(tmp_path):
    r, (abrir, montar) = _monta(tmp_path, perfil="cadeirinha", modo="revisar", regua="padrao readme",
                                origem=ORQ, agente="revisor", pergunta="revise isto")
    assert "erro" not in r and r["sessao"]["sessao_id"] == FILHA
    assert abrir["argv"] == ["abrir", "engenharia", "--origem", ORQ, "--agente", "revisor",
                             "--em-nome-de", "engenharia", "--conta", s.OPS_USER, "--json"]
    assert montar["argv"] == ["montar", "--json", "--chapeu", "devops", "--perfil", "cadeirinha",
                              "--modo", "revisar", "--regua", "padrao", "readme"]
    assert montar["origem"] == ORQ and montar["stdin"] == "revise isto"


def test_sem_campos_de_agente_a_abertura_da_cadeira_fica_como_antes(tmp_path):
    r, (abrir, montar) = _monta(tmp_path)
    assert "erro" not in r
    assert abrir["argv"] == ["abrir", "engenharia", "--json"]
    assert montar["argv"] == ["montar", "--json", "--chapeu", "devops"]
    assert montar["origem"] is None
