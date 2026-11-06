"""Testes de contrato da biblioteca de federação (lib/federacao.py).

Testa:
- Servidor Keycloak de mentira em HTTP local;
- Segredo ausente levanta FalhaFederacao('emissor');
- Arquivo do token gravado em modo 600;
- Timeout do Keycloak levanta FalhaFederacao('emissor');
- Renovação com intervalo curto grava jti novo (-k renova).
"""

from __future__ import annotations

import base64
import json
import stat
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib import federacao

CONFIG_TESTE = {
    "organizacao": "org-teste-123",
    "workspace": "wrkspc-teste-456",
    "contas": {
        "agente-juiz": {
            "cliente": "agente-juiz",
            "regra": "fdrl_juiz_teste",
            "conta_servico": "svac_juiz_teste",
            "regime": "federacao",
        }
    },
}


def _jwt_mentira(jti: str) -> str:
    cab = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode("ascii")
    corpo = base64.urlsafe_b64encode(json.dumps({"jti": jti, "sub": "sub-teste"}).encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"{cab}.{corpo}.assinatura_fake"


def _jti_do_jwt(jwt_str: str) -> str:
    partes = jwt_str.strip().split(".")
    assert len(partes) >= 2
    padded = partes[1] + "=" * ((4 - len(partes[1]) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    return payload.get("jti", "")


def _espera_jti_novo(token_file: Path, anterior: str, limite_tentativas: int = 50) -> str:
    for _ in range(limite_tentativas):
        time.sleep(0.05)
        atual = _jti_do_jwt(token_file.read_text(encoding="utf-8"))
        if atual != anterior:
            return atual
    return ""


class HandlerKeycloakMentira(BaseHTTPRequestHandler):
    contador = 0
    trava = threading.Lock()
    atraso_s = 0.0
    ultimo_user_agent = ""

    def do_POST(self):
        if self.atraso_s > 0:
            time.sleep(self.atraso_s)
        tamanho = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(tamanho)
        with self.trava:
            HandlerKeycloakMentira.contador += 1
            num = HandlerKeycloakMentira.contador
            HandlerKeycloakMentira.ultimo_user_agent = self.headers.get("User-Agent", "")

        token = _jwt_mentira(f"jti-{num}")
        resp = json.dumps({"access_token": token, "token_type": "Bearer", "expires_in": 300}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def keycloak_mentira():
    HandlerKeycloakMentira.contador = 0
    HandlerKeycloakMentira.atraso_s = 0.0
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), HandlerKeycloakMentira)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    porta = servidor.server_port
    url = f"http://127.0.0.1:{porta}/token"
    yield url
    servidor.shutdown()


def test_segredo_ausente_levanta_emissor(tmp_path, keycloak_mentira, monkeypatch):
    monkeypatch.delenv("KEYCLOAK_CLIENT_SECRET_AGENTE_JUIZ", raising=False)
    monkeypatch.setattr(federacao.raizes, "instancia", lambda: tmp_path / "sem_instancia")
    with pytest.raises(federacao.FalhaFederacao) as exc_info, federacao.abre("agente-juiz", tmp_path, CONFIG_TESTE, url_token=keycloak_mentira):
        pass
    assert exc_info.value.motivo == "emissor"


def test_arquivo_do_token_em_modo_600(tmp_path, keycloak_mentira, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET_AGENTE_JUIZ", "segredo-teste")
    with federacao.abre("agente-juiz", tmp_path, CONFIG_TESTE, url_token=keycloak_mentira) as cred:
        token_file = Path(cred.env["ANTHROPIC_IDENTITY_TOKEN_FILE"])
        assert token_file.exists()
        modo = stat.S_IMODE(token_file.stat().st_mode)
        assert modo == 0o600, f"esperado modo 0o600, obtido {oct(modo)}"
        assert cred.env["ANTHROPIC_ORGANIZATION_ID"] == "org-teste-123"
        assert cred.env["ANTHROPIC_WORKSPACE_ID"] == "wrkspc-teste-456"
        assert cred.env["ANTHROPIC_FEDERATION_RULE_ID"] == "fdrl_juiz_teste"
        assert cred.env["ANTHROPIC_SERVICE_ACCOUNT_ID"] == "svac_juiz_teste"
        assert cred.conta_servico == "svac_juiz_teste"


def test_timeout_de_10s_levanta_emissor(tmp_path, monkeypatch):
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), HandlerKeycloakMentira)
    HandlerKeycloakMentira.atraso_s = 0.5
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    porta = servidor.server_port
    url = f"http://127.0.0.1:{porta}/token"

    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET_AGENTE_JUIZ", "segredo-teste")
    monkeypatch.setattr(federacao, "TIMEOUT_KEYCLOAK_S", 0.1)  # encurtado para o teste

    try:
        with pytest.raises(federacao.FalhaFederacao) as exc_info, federacao.abre("agente-juiz", tmp_path, CONFIG_TESTE, url_token=url):
            pass
        assert exc_info.value.motivo == "emissor"
    finally:
        servidor.shutdown()


def test_renova(tmp_path, keycloak_mentira, monkeypatch):
    """Com intervalo encurtado, o arquivo do token é reescrito duas vezes com jti diferentes antes de o filho sair."""
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET_AGENTE_JUIZ", "segredo-teste")
    jtis_vistos = []

    with federacao.abre("agente-juiz", tmp_path, CONFIG_TESTE, intervalo_renovacao_s=0.1, url_token=keycloak_mentira) as cred:
        token_file = Path(cred.env["ANTHROPIC_IDENTITY_TOKEN_FILE"])
        primeiro = _jti_do_jwt(token_file.read_text(encoding="utf-8"))
        jtis_vistos.append(primeiro)

        segundo = _espera_jti_novo(token_file, primeiro)
        assert segundo and segundo != primeiro
        jtis_vistos.append(segundo)

        terceiro = _espera_jti_novo(token_file, segundo)
        assert terceiro and terceiro != segundo
        jtis_vistos.append(terceiro)

    assert len(jtis_vistos) >= 3, f"esperados pelo menos 3 tokens diferentes, vieram: {jtis_vistos}"
    assert len(set(jtis_vistos)) == len(jtis_vistos)


def test_user_agent_enviado(tmp_path, keycloak_mentira, monkeypatch):
    """Garante que a requisição ao Keycloak envia o User-Agent próprio da PlataFirma."""
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET_AGENTE_JUIZ", "segredo-teste")
    with federacao.abre("agente-juiz", tmp_path, CONFIG_TESTE, url_token=keycloak_mentira):
        pass
    assert HandlerKeycloakMentira.ultimo_user_agent == federacao.USER_AGENT
