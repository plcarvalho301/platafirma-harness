"""Ponte autenticada entre o Antigravity CLI e o ops-server.

O `agy` fala MCP em http://127.0.0.1:8022/mcp, aqui dentro do container. Este
processo repassa cada chamada para https://ops.platafirma.org/mcp com um Bearer
do realm sempre fresco — o token do Jaiminho vive 600 s e o CLI nao sabe renovar
credencial de client_credentials.

Nao ha decisao de acesso aqui: quem decide e o PEP do ops-server, do outro lado.
Esta ponte so carrega credencial e repassa bytes.
"""
import os
import time

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

REALM = os.environ.get("OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
OPS = os.environ.get("OPS_URL", "https://ops.platafirma.org")
CLIENT_ID = os.environ.get("JAIMINHO_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("JAIMINHO_CLIENT_SECRET", "")

_tok = {"valor": None, "expira": 0}
_cli = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=15.0))


async def _token():
    if _tok["valor"] and time.time() < _tok["expira"] - 30:
        return _tok["valor"]
    if not (CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("JAIMINHO_CLIENT_ID/SECRET ausentes")
    r = await _cli.post(f"{REALM}/protocol/openid-connect/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET})
    r.raise_for_status()
    d = r.json()
    _tok.update(valor=d["access_token"], expira=time.time() + d.get("expires_in", 300))
    return _tok["valor"]


async def estado(req):
    try:
        await _token()
        h = {"Authorization": f"Bearer {await _token()}"}
        r = await _cli.get(f"{OPS}/sessao", headers=h)
        return JSONResponse({"token": "ok", "sessao_http": r.status_code,
                             "sujeito": r.json().get("sujeito") if r.status_code == 200 else None,
                             "ops": OPS})
    except Exception as e:                                            # noqa: BLE001
        return JSONResponse({"erro": str(e)[:300]}, status_code=503)


async def ponte(req):
    """Repassa /mcp preservando streaming — MCP sobre HTTP e resposta longa."""
    corpo = await req.body()
    cabecalhos = {k: v for k, v in req.headers.items()
                  if k.lower() not in ("host", "authorization", "content-length")}
    cabecalhos["Authorization"] = f"Bearer {await _token()}"
    pedido = _cli.build_request(req.method, f"{OPS}/mcp", headers=cabecalhos,
                                content=corpo, params=req.query_params)
    resposta = await _cli.send(pedido, stream=True)
    saida = {k: v for k, v in resposta.headers.items()
             if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
    return StreamingResponse(resposta.aiter_raw(), status_code=resposta.status_code,
                             headers=saida, media_type=resposta.headers.get("content-type"),
                             background=BackgroundTask(resposta.aclose))


app = Starlette(routes=[
    Route("/estado", estado),
    Route("/mcp", ponte, methods=["GET", "POST", "DELETE"]),
    Route("/mcp/{resto:path}", ponte, methods=["GET", "POST", "DELETE"]),
])
