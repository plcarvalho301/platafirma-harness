"""A borda das faces diante da porta de verdade (card #3516, U3; R22 e R30 a R32 da spec
plano-de-controle-face-motor; seg:0015 §5).

O que sobe aqui é a porta de verdade: o `server.py` com o FastMCP sem estado, o `BearerAuth` que valida o
JWT (assinatura, emissor e audiência) e a tool de verbo, num uvicorn de verdade em loopback. Na frente dela, a
borda de verdade com o cliente HTTP dela, que fala MCP por HTTP. O que é de brinquedo: o realm (um par de chaves
do teste assina os tokens), o verbo (um script `motor` que grava o que viu) e o PDP, que é o da R25 e tem a suíte
própria em politica-acesso/. A pergunta que o teste responde é a do Aceite: o que a tela faz pela borda deixa na
porta o mesmo rastro de um ato de cadeira, com o sujeito do dono, e o que não deve chegar não chega.

Vive em ops-server/ porque precisa do venv `ops` (mcp, uvicorn, cryptography).
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso", HARNESS_DIR / "lib", HARNESS_DIR / "borda"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-contrato-borda-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import jwt  # noqa: E402
import uvicorn  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

import borda  # noqa: E402
import identidade  # noqa: E402
import oplog  # noqa: E402
import server as s  # noqa: E402

SUB = "b6986be0-c5b6-4693-839f-73c90b79b25a"      # o dono em politica-acesso/sujeitos.yaml
CLIENT_CUBO = "cubo-controle"
ORIGEM = "https://controle.exemplo.org"
FUNDAMENTO = "o piso estava alto demais"
CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)

VERBO = """#!/bin/sh
# motor — verbo de brinquedo do teste de contrato da borda (#3516)
# atos: listar (leitura, x), ler (leitura, x), gravar (escrita, x), ajuste (leitura|escrita, x), sortear (escrita, x)
# face: listar=motor
# face: ler=motor
# face: gravar=motor
# face: ajuste=motor
if [ "$1" = "listar" ]; then echo '{"instancias": ["rag"]}'; exit 0; fi
if [ "$2" = "ajuste" ] && [ -n "$4" ] && [ -z "$PF_FUNDAMENTO" ]; then
  echo "ajuste: escrita sem fundamento" >&2; exit 2
fi
echo "SUJ=$PF_SUJEITO CAD=$PF_CADEIRA SESSAO=$PF_SESSAO FUND=$PF_FUNDAMENTO ARGS=$*" >> "$PF_MARCA"
echo "FUND=$PF_FUNDAMENTO"
"""


class _ChaveDoRealm:
    key = CHAVE.public_key()


class _JwksDeTeste:
    def get_signing_key_from_jwt(self, _tok):
        return _ChaveDoRealm()


def _token(azp=CLIENT_CUBO, aud=None, sub=SUB) -> str:
    agora = int(time.time())
    return jwt.encode({"iss": s.OIDC_ISSUER, "aud": aud or s.OIDC_AUDIENCE, "sub": sub, "azp": azp,
                       "iat": agora, "exp": agora + 300, "preferred_username": "megafone"},
                      CHAVE, algorithm="RS256")


@pytest.fixture(scope="module")
def porta(tmp_path_factory):
    """A porta de verdade num uvicorn em loopback, com o verbo de brinquedo como a tool `motor`."""
    verbo = tmp_path_factory.mktemp("verbo") / "motor"
    verbo.write_text(VERBO, encoding="utf-8")
    verbo.chmod(verbo.stat().st_mode | stat.S_IXUSR)
    ferramentas = s.mcp._tool_manager._tools
    antiga = ferramentas.pop("motor", None)
    s.mcp.tool(name="motor", description="motor de brinquedo")(s._faz_tool_verbo("motor", str(verbo), "x"))
    gerente = s.mcp._session_manager
    s.mcp._session_manager = None          # o lifespan do gerente roda uma vez só: este app tem o dele
    app = s.mcp.streamable_http_app()
    app.add_middleware(s.BearerAuth)
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        numero = sk.getsockname()[1]
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=numero, log_level="warning"))
    fio = threading.Thread(target=servidor.run, daemon=True)
    fio.start()
    for _ in range(300):
        if servidor.started:
            break
        time.sleep(0.02)
    assert servidor.started, "a porta de teste não subiu"
    yield SimpleNamespace(url=f"http://127.0.0.1:{numero}/mcp", verbo=verbo)
    servidor.should_exit = True
    fio.join(10)
    ferramentas.pop("motor", None)
    if antiga is not None:
        ferramentas["motor"] = antiga
    s.mcp._session_manager = gerente


@pytest.fixture(autouse=True)
def ambiente(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "LOG_DIR", tmp_path)
    monkeypatch.setattr(s, "FACE_CLIENTS", frozenset({CLIENT_CUBO}))
    monkeypatch.setattr(identidade, "_jwks", lambda *_a, **_k: _JwksDeTeste())
    monkeypatch.setenv("PF_MARCA", str(tmp_path / "marca"))
    for cache in (s._ORIGENS, s._CARIMBOS, s._DECLARA_EXIT, s._ATOS_DO_CABECALHO):
        cache.clear()
    with patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))), \
            patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_serve", side_effect=lambda r, **_k: r):
        yield
    for cache in (s._ORIGENS, s._CARIMBOS, s._ATOS_DO_CABECALHO):
        cache.clear()


def _linhas(pasta) -> list[dict]:
    return [json.loads(linha) for f in sorted(pasta.glob("ops-*.jsonl"))
            for linha in f.read_text(encoding="utf-8").splitlines()]


def _borda(porta_):
    face = borda.Face("motor", verbo=str(porta_.verbo), instancia="rag", sem_instancia=("listar",))
    return borda.Borda([face], origens=(ORIGEM,), porta_url=porta_.url, saida=io.StringIO())


def _pede(porta_, metodo, caminho, token=None, corpo=None, consulta=b"", origem=ORIGEM):
    cab = {"authorization": f"Bearer {token}"} if token else {}
    if metodo != "GET":
        cab.update({"origin": origem, "x-pf-tela": "1", "content-type": "application/json"})
    status, _, dado = asyncio.run(borda._chamar(
        _borda(porta_), metodo, caminho, cab, json.dumps(corpo).encode() if corpo is not None else b"",
        consulta=consulta))
    return status, json.loads(dado)


def _marca(tmp_path) -> str | None:
    """O que o verbo de brinquedo viu, ou None se ele nao rodou."""
    caminho = tmp_path / "marca"
    return caminho.read_text(encoding="utf-8").strip() if caminho.exists() else None


# --- R22 e R30: a escrita da tela deixa na porta o rastro do dono --------------------------------

def test_a_escrita_pela_borda_deixa_no_bruto_o_sub_do_dono_a_data_e_o_fundamento(porta, tmp_path):
    status, resposta = _pede(porta, "POST", "/api/motor/ajuste", _token(),
                             {"args": ["piso", "0.6"], "fundamento": FUNDAMENTO})
    assert status == 200 and resposta["exit_code"] == 0 and "cwd" not in resposta
    assert f"FUND={FUNDAMENTO}" in resposta["stdout"]["texto"]
    linhas = _linhas(tmp_path)
    (turno,) = [t for t in linhas if t.get("evento") == "turno"]
    (giro,) = [g for g in linhas if g.get("tool") == "motor" and not g.get("evento")]
    assert turno["turno_fonte"] == "face" and turno["texto"] == FUNDAMENTO and turno["ts"]
    assert giro["turno_fonte"] == "face" and giro["sessao_id"] == turno["sessao_id"] and giro["ts"]
    assert giro["sub"] == SUB and giro["sujeito"] == SUB and giro["azp"] == CLIENT_CUBO
    assert giro["cadeira"] is None and giro["exit_code"] == 0
    assert oplog.validar(turno) == [] and oplog.validar(giro) == []
    # e o verbo viu o mesmo: o sub como sujeito, nenhuma cadeira, o texto do dono como fundamento
    assert _marca(tmp_path) == (f"SUJ={SUB} CAD= SESSAO={giro['sessao_id']} FUND={FUNDAMENTO} "
                                "ARGS=rag ajuste piso 0.6")


def test_sem_fundamento_a_porta_recusa_a_escrita_da_face_antes_de_executar(porta, tmp_path):
    status, resposta = _pede(porta, "POST", "/api/motor/gravar", _token(), {"args": ["x"]})
    assert status == 200 and resposta["recusado"] is True and "sem fundamento" in resposta["motivo"]
    assert _marca(tmp_path) is None, "o verbo rodou"
    (recusa,) = [t for t in _linhas(tmp_path) if t.get("evento") == "escrita_recusada"]
    assert recusa["tool"] == "motor" and recusa["sub"] == SUB and oplog.validar(recusa) == []


def test_o_ajuste_com_valor_por_get_chega_sem_fundamento_e_o_verbo_nao_grava(porta, tmp_path):
    """O risco declarado no Plano: a R32 cita «um ajuste por GET» em 403, mas `ajuste` é leitura|escrita no
    cabeçalho. A borda não lê argumento; a garantia é que GET nunca leva fundamento, e o verbo recusa (exit 2)."""
    status, resposta = _pede(porta, "GET", "/api/motor/ajuste", _token(), consulta=b"a=piso&a=0.6")
    assert status == 200 and resposta["exit_code"] == 2
    assert _marca(tmp_path) is None


def test_a_leitura_pela_borda_passa_com_a_fonte_face(porta, tmp_path):
    status, resposta = _pede(porta, "GET", "/api/motor/ler", _token(), consulta=b"a=piso")
    assert status == 200 and resposta["exit_code"] == 0
    assert "ARGS=rag ler piso" in (tmp_path / "marca").read_text(encoding="utf-8")
    status, resposta = _pede(porta, "GET", "/api/motor/listar", _token())
    assert status == 200 and json.loads(resposta["stdout"]["texto"]) == {"instancias": ["rag"]}
    giros = [g for g in _linhas(tmp_path) if g.get("tool") == "motor" and not g.get("evento")]
    assert len(giros) == 2 and {g["turno_fonte"] for g in giros} == {"face"}
    assert len({g["sessao_id"] for g in giros}) == 2, "cada chamada abre a sessão dela"


# --- R30: o token ----------------------------------------------------------------------------------

def test_token_de_outro_client_com_a_fonte_face_sai_recusado_e_o_verbo_nao_roda(porta, tmp_path):
    status, resposta = _pede(porta, "GET", "/api/motor/ler", _token(azp="agy-cli"))
    assert status == 200 and resposta["recusado"] is True and "azp" in resposta["motivo"]
    assert _marca(tmp_path) is None


def test_token_sem_a_porta_na_audiencia_e_recusado_pela_porta_e_a_borda_devolve_401(porta, tmp_path):
    status, resposta = _pede(porta, "GET", "/api/motor/ler", _token(aud="outro-servico"))
    assert status == 401 and "erro" in resposta
    linhas = _linhas(tmp_path)
    assert [x["motivo"] for x in linhas if x.get("evento") == "auth_negada"] == ["audience"]
    assert not [g for g in linhas if g.get("tool") == "motor"], "a chamada chegou ao verbo"
    assert _marca(tmp_path) is None


def test_chamada_a_borda_sem_token_sai_401_e_nao_deixa_linha_no_bruto_da_porta(porta, tmp_path):
    assert _pede(porta, "GET", "/api/motor/ler")[0] == 401
    assert _pede(porta, "POST", "/api/motor/gravar", None, {"args": [], "fundamento": "x"})[0] == 401
    assert _linhas(tmp_path) == [] and _marca(tmp_path) is None


# --- R31 e R32: o que a borda barra não chega à porta ---------------------------------------------

def test_as_recusas_da_borda_nao_deixam_linha_no_bruto_da_porta(porta, tmp_path):
    tentativas = [
        _pede(porta, "POST", "/api/motor/gravar", _token(), {"args": [], "fundamento": "x"}, origem="https://x.exemplo"),
        _pede(porta, "GET", "/api/motor/gravar", _token()),                        # escrita por GET
        _pede(porta, "POST", "/api/motor/sortear", _token(), {"args": []}),         # ato sem face
        _pede(porta, "GET", "/api/motor/inexistente", _token()),                   # fora da carga
        _pede(porta, "POST", "/api/motor/ler", _token(), {"args": []}),             # leitura por POST
    ]
    assert [t[0] for t in tentativas] == [403] * 5
    assert _linhas(tmp_path) == [] and _marca(tmp_path) is None
