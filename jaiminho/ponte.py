"""Ponte autenticada entre o Antigravity CLI e os conectores da PlataFirma.

O `agy` fala MCP em http://127.0.0.1:8022, aqui dentro do container:
  /mcp    -> ops-server      (https://ops.platafirma.org/mcp)
  /acervo -> jaiminho-server (http://jaiminho-server:8000/mcp)

O `/acervo` e o MCP do proprio Jaiminho: nosso codigo, contêiner separado, na rede
`saida`. E por ele que entram a busca no acervo E a leitura da wiki — o ops-server e
o MCP das cadeiras e nao serve externo.

NAO ha rota `/wiki` aqui, e a ausencia e o desenho. O `wiki-mcp` autentica por
segredo estatico e nao tem PEP: um Bearer que abre `get_page` abre `edit_page` e
`upload_file` no mesmo ato. Repassar esse segredo por esta ponte poria a caneta da
wiki na mao do externo. A wiki entra pelo jaiminho-server, que valida o JWT, pergunta
ao PDP e recorta o namespace — o segredo do wiki-mcp fica do nosso lado e nunca
atravessa. (16/08/2026, ordem do dono para dar wiki ao Jaiminho; o que ele mandou foi
o alcance, o mecanismo e nosso.)

Este processo repassa cada chamada com um Bearer do realm sempre fresco — o
token do Jaiminho vive 600 s e o CLI nao sabe renovar credencial de
client_credentials.

Nao ha decisao de acesso aqui: quem decide e o PEP de cada servidor, do outro
lado. Esta ponte so carrega credencial e repassa bytes. Rota que o PEP negar
devolve 403 com o id da regra — resposta legitima, nao defeito da ponte.
"""
import os
import time

import httpx
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

# Borda publica (ops.platafirma.org) atras de Cloudflare bane User-Agent de
# biblioteca com erro 1010 (browser_signature_banned) ANTES de qualquer decisao de
# acesso — medido 02/09/2026. httpx manda UA proprio; a borda o recusa. Um UA de
# browser passa o WAF, e o PEP do outro lado segue decidindo por JWT. Mitigacao ate
# a rota interna host-to-host do ops-server existir (espelha o #2380 do jaiminho-server).
_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

REALM = os.environ.get("OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
OPS = os.environ.get("OPS_URL", "https://ops.platafirma.org")
ACERVO = os.environ.get("ACERVO_URL", "http://jaiminho-server:8000")
CLIENT_ID = os.environ.get("JAIMINHO_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("JAIMINHO_CLIENT_SECRET", "")

_tok = {"valor": None, "expira": 0}
_cli = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=15.0),
                        headers={"User-Agent": _UA})


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
        h = {"Authorization": f"Bearer {await _token()}"}
        r = await _cli.get(f"{OPS}/sessao", headers=h)
        return JSONResponse({"token": "ok", "sessao_http": r.status_code,
                             "sujeito": r.json().get("sujeito") if r.status_code == 200 else None,
                             "ops": OPS, "acervo": ACERVO})
    except Exception as e:                                            # noqa: BLE001
        return JSONResponse({"erro": str(e)[:300]}, status_code=503)


async def _repassa(req, base):
    """Repassa preservando streaming — MCP sobre HTTP e resposta longa."""
    corpo = await req.body()
    cabecalhos = {k: v for k, v in req.headers.items()
                  if k.lower() not in ("host", "authorization", "content-length")}
    cabecalhos["Authorization"] = f"Bearer {await _token()}"
    cabecalhos["User-Agent"] = _UA
    pedido = _cli.build_request(req.method, base, headers=cabecalhos,
                                content=corpo, params=req.query_params)
    resposta = await _cli.send(pedido, stream=True)
    saida = {k: v for k, v in resposta.headers.items()
             if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
    return StreamingResponse(resposta.aiter_raw(), status_code=resposta.status_code,
                             headers=saida, media_type=resposta.headers.get("content-type"),
                             background=BackgroundTask(resposta.aclose))


async def ponte_ops(req):
    return await _repassa(req, f"{OPS}/mcp")


async def ponte_acervo(req):
    return await _repassa(req, f"{ACERVO}/mcp")


_METODOS = ["GET", "POST", "DELETE"]

app = Starlette(routes=[
    Route("/estado", estado),
    Route("/mcp", ponte_ops, methods=_METODOS),
    Route("/mcp/{resto:path}", ponte_ops, methods=_METODOS),
    Route("/acervo", ponte_acervo, methods=_METODOS),
    Route("/acervo/{resto:path}", ponte_acervo, methods=_METODOS),
])
