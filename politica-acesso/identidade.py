"""Validação de token OIDC e extração de identidade de sujeito.

Rechaveado por `sub` (#137) — `sub` é o identificador único e imutável do sujeito no realm;
`preferred_username` é descritivo (não-normativo).
Auditoria (#139) — `sid` e `jti` do token são extraídos para compor a trilha de auditoria.
O token em si nunca vai para o log.
"""
from __future__ import annotations

import os
from typing import Any, Callable

_jwks_cache: dict[str, Any] = {}


def _jwks(jwks_url: str | None = None):
    """Cliente JWKS com cache — a chave do realm só se busca quando o `kid` muda."""
    from jwt import PyJWKClient

    url = jwks_url or os.environ.get(
        "OIDC_JWKS_URL",
        "http://127.0.0.1:8180/realms/platafirma/protocol/openid-connect/certs",
    )
    if url not in _jwks_cache:
        _jwks_cache[url] = PyJWKClient(url, cache_keys=True, lifespan=3600)
    return _jwks_cache[url]


def _sujeito_do_jwt(
    header: str,
    auditor: Callable[..., None] | None = None,
    jwks_url: str | None = None,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict:
    """Valida o Bearer como JWT do realm e devolve a identidade. {} = não é JWT válido.

    Rechaveado por sub (#137): 'sub' e 'sujeito' recebem claims['sub'], e 'username'
    recebe claims.get('preferred_username') como campo descritivo não-normativo.
    Inclui 'sid' e 'jti' para auditoria (#139).

    Devolver {} em vez de levantar é deliberado: quem chama decide se cai na rota de
    emergência ou nega. A negativa loga o motivo, nunca o token.
    """
    if not header or not header.startswith("Bearer "):
        return {}
    tok = header[len("Bearer "):].strip()
    if tok.count(".") != 2:                 # token estático não é JWT — nem tenta
        return {}
    try:
        import jwt

        iss = issuer or os.environ.get(
            "OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma"
        )
        aud = audience or os.environ.get("OIDC_AUDIENCE", "ops-mcp")
        client = _jwks(jwks_url)
        signing_key = client.get_signing_key_from_jwt(tok).key
        claims = jwt.decode(
            tok,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=aud,
            issuer=iss,
            options={"require": ["exp", "iat", "sub"]},
        )
        sub = claims["sub"]
        return {
            "sub": sub,
            "sujeito": sub,
            "username": claims.get("preferred_username"),
            "azp": claims.get("azp", "-"),
            "sid": claims.get("sid", "-"),
            "jti": claims.get("jti", "-"),
        }
    except Exception as e:                                  # noqa: BLE001
        if auditor is not None:
            try:
                auditor(tool="-", evento="jwt_recusado", motivo=type(e).__name__)
            except TypeError:
                try:
                    auditor(evento="jwt_recusado", motivo=type(e).__name__)
                except Exception:                           # noqa: BLE001
                    pass
        return {}
