"""Federação de identidade de workload (WIF) para a API da Anthropic (card #4122).

Obtém o token OIDC do Keycloak por client_credentials, grava o arquivo em modo 600
e renova periodicamente em segundo plano enquanto o processo do modelo roda.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib import raizes

INTERVALO_RENOVACAO_S = 240.0  # 4 minutos (o token do Keycloak dura 5 minutos)
TIMEOUT_KEYCLOAK_S = 10.0      # 10 s de teto para a rede do Keycloak
HTTP_OK = 200


class FalhaFederacao(Exception):
    """Falha no fluxo de federação. Motivos canônicos: emissor, troca, credito."""

    def __init__(self, motivo: str, detalhe: str = ""):
        super().__init__(f"falha de federação ({motivo}): {detalhe}" if detalhe else motivo)
        self.motivo = motivo
        self.detalhe = detalhe


class Credencial:
    """Credencial da federação exposta para o processo do agente."""

    def __init__(self, env: dict[str, str], conta_servico: str, token_path: Path):
        self.env = env
        self.conta_servico = conta_servico
        self.token_path = token_path
        self.processo: subprocess.Popen | None = None
        self.falha: FalhaFederacao | None = None

    def registra_processo(self, proc: subprocess.Popen) -> None:
        self.processo = proc


def _le_segredo(conta: str) -> str:
    """Lê o segredo do cliente Keycloak do stack harness ou do ambiente."""
    nome_var = f"KEYCLOAK_CLIENT_SECRET_{conta.replace('-', '_').upper()}"
    direto = os.environ.get(nome_var)
    if direto:
        return direto.strip()
    caminho = raizes.instancia() / "segredos" / "harness" / nome_var
    try:
        with open(caminho, encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    except OSError:
        pass
    raise FalhaFederacao("emissor", f"segredo {nome_var} não encontrado")


def _pede_token(cliente: str, segredo: str, url: str | None = None) -> str:
    """Requisita um novo JWT ao Keycloak por client_credentials."""
    endpoint = url or os.environ.get("KEYCLOAK_TOKEN_URL") or "https://auth.platafirma.org/realms/platafirma/protocol/openid-connect/token"
    dados = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cliente,
        "client_secret": segredo,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=dados,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_KEYCLOAK_S) as resp:
            corpo = resp.read()
            status = resp.status
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise FalhaFederacao("emissor", f"Keycloak não respondeu em {endpoint} ({type(e).__name__}: {e})") from e

    if status != HTTP_OK:
        raise FalhaFederacao("emissor", f"Keycloak HTTP {status}: {corpo[:200].decode('utf-8', 'replace')}")
    try:
        obj = json.loads(corpo.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise FalhaFederacao("emissor", f"Keycloak devolveu JSON inválido: {e}") from e

    token = obj.get("access_token")
    if not token or not isinstance(token, str):
        raise FalhaFederacao("emissor", "Keycloak devolveu resposta sem access_token")
    return token.strip()


def _grava_token(pasta: Path, token: str, destino: Path) -> None:
    """Grava o token em modo 600 por arquivo temporário + rename atômico."""
    pasta.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=pasta, prefix=".token-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(token)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        os.replace(tmp, destino)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@contextmanager
def abre(conta: str, pasta: Path, config: dict,
         intervalo_renovacao_s: float = INTERVALO_RENOVACAO_S,
         url_token: str | None = None) -> Iterator[Credencial]:
    """Abre o contexto de credencial federada para a conta informada.

    Grava o token OIDC inicial na pasta isolada e renova em thread a cada intervalo.
    Em falha inicial, levanta FalhaFederacao('emissor').
    Em falha na renovação, mata o processo registrado e sinaliza falha.
    """
    contas = config.get("contas", {})
    dados_conta = contas.get(conta) or config.get(conta)
    if not dados_conta:
        raise FalhaFederacao("emissor", f"conta {conta!r} não declarada na configuração de federação")

    cliente = dados_conta.get("cliente") or conta
    regra = dados_conta.get("regra", "")
    conta_servico = dados_conta.get("conta_servico", "")
    org_id = config.get("organizacao", "")
    workspace_id = config.get("workspace", "")

    segredo = _le_segredo(conta)
    token_inicial = _pede_token(cliente, segredo, url=url_token)

    token_file = pasta / "anthropic-identity-token.jwt"
    _grava_token(pasta, token_inicial, token_file)

    env_vars = {
        "ANTHROPIC_ORGANIZATION_ID": org_id,
        "ANTHROPIC_WORKSPACE_ID": workspace_id,
        "ANTHROPIC_FEDERATION_RULE_ID": regra,
        "ANTHROPIC_SERVICE_ACCOUNT_ID": conta_servico,
        "ANTHROPIC_IDENTITY_TOKEN_FILE": str(token_file),
    }
    cred = Credencial(env_vars, conta_servico, token_file)

    parar = threading.Event()

    def _loop_renovacao() -> None:
        while not parar.wait(intervalo_renovacao_s):
            try:
                novo_token = _pede_token(cliente, segredo, url=url_token)
                _grava_token(pasta, novo_token, token_file)
            except Exception as e:  # noqa: BLE001 — a thread de renovação precisa capturar qualquer falha para matar o filho
                motivo = e.motivo if isinstance(e, FalhaFederacao) else "emissor"
                cred.falha = FalhaFederacao(motivo, str(e))
                if cred.processo:
                    try:
                        cred.processo.kill()
                    except OSError:
                        pass
                break

    t = threading.Thread(target=_loop_renovacao, daemon=True, name=f"wif-renova-{conta}")
    t.start()
    try:
        yield cred
    finally:
        parar.set()
        t.join(timeout=2.0)
