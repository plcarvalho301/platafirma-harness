"""Runtime do Jaiminho — colaborador externo (Gemini) em modelo DMZ.

O container e o corpo do Jaiminho: fala com a API do Google e com o ops-server
pela porta publica, com o client proprio dele no realm. NAO monta ~/AI, NAO
alcanca o Valkey e NAO tem credencial de cadeira nenhuma — a superficie dele
continua sendo o PEP (card 344, seg:0009).

Quem chama: o dono (por claudinho-TI ou, adiante, por uma ponte Matrix). O
container nao decide sozinho quando falar; nao ha timer aqui por desenho.
"""
import json
import os
import time

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

REALM = os.environ.get("OIDC_ISSUER", "https://auth.platafirma.org/realms/platafirma")
OPS = os.environ.get("OPS_URL", "https://ops.platafirma.org")
CLIENT_ID = os.environ.get("JAIMINHO_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("JAIMINHO_CLIENT_SECRET", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELO = os.environ.get("JAIMINHO_MODELO", "gemini-3.1-pro-preview")
GOOGLE = "https://generativelanguage.googleapis.com/v1beta"

_tok = {"valor": None, "expira": 0}


def _erro(msg, http=503, **extra):
    return JSONResponse({"erro": msg, **extra}, status_code=http)


async def _token(c):
    """Token do realm por client_credentials, reusado ate 30 s do fim."""
    if _tok["valor"] and time.time() < _tok["expira"] - 30:
        return _tok["valor"]
    if not (CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("JAIMINHO_CLIENT_ID/SECRET ausentes no .env do container")
    r = await c.post(f"{REALM}/protocol/openid-connect/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET})
    r.raise_for_status()
    d = r.json()
    _tok.update(valor=d["access_token"], expira=time.time() + d.get("expires_in", 300))
    return _tok["valor"]


async def _ops(c, metodo, rota, corpo=None):
    h = {"Authorization": f"Bearer {await _token(c)}"}
    r = await c.request(metodo, f"{OPS}{rota}", headers=h, json=corpo)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"texto": r.text[:400]}


def _sistema(sessao):
    """Instrucao de sistema montada do que o proprio ops-server declara — nao ha
    copia de persona aqui: persona e artefato de RH, servido por GET /sessao."""
    persona = sessao.get("persona") or {}
    corpo = persona.get("conteudo") or persona.get("content")
    if not corpo:
        corpo = ("Voce e o Jaiminho, colaborador externo da PlataFirma, especializado em "
                 "investigacao de fonte aberta. Persona canonica ainda nao escrita pelo RH: "
                 "opere pelo manifesto de acoes abaixo e diga quando algo estiver fora dele.")
    acoes = json.dumps(sessao.get("acoes", []), ensure_ascii=False)
    return (f"{corpo}\n\nAcoes que voce alcanca hoje (manifesto do ops-server): {acoes}\n"
            "Voce fala com claudinho-IA (Elias Elefante) e com o dono. Nao tem shell, "
            "nao alcanca repositorio nem o broker de mensagens.")


async def _gemini(c, sistema, partes):
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY ausente — o container sobe, mas nao fala")
    r = await c.post(
        f"{GOOGLE}/models/{MODELO}:generateContent",
        headers={"x-goog-api-key": GEMINI_KEY, "content-type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": sistema}]},
              "contents": [{"role": "user", "parts": [{"text": p} for p in partes]}]})
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")
    d = r.json()
    cand = (d.get("candidates") or [{}])[0]
    return "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))


async def estado(req):
    fora = {"chave_google": bool(GEMINI_KEY), "client": bool(CLIENT_ID and CLIENT_SECRET),
            "modelo": MODELO, "ops": OPS}
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            cod, sessao = await _ops(c, "GET", "/sessao")
            fora["sessao"] = {"http": cod, "sujeito": sessao.get("sujeito"),
                              "persona_ausente": bool((sessao.get("persona") or {}).get("ausente")),
                              "caixa": sessao.get("fila")}
        except Exception as e:                                        # noqa: BLE001
            fora["sessao"] = {"erro": str(e)[:200]}
    return JSONResponse(fora)


async def perguntar(req):
    """Pergunta direta ao Jaiminho. `para_elias: true` manda a resposta na caixa."""
    corpo = await req.json()
    texto = (corpo.get("texto") or "").strip()
    if not texto:
        return _erro("campo `texto` vazio", 400)
    async with httpx.AsyncClient(timeout=180) as c:
        try:
            _, sessao = await _ops(c, "GET", "/sessao")
            resposta = await _gemini(c, _sistema(sessao), [texto])
        except Exception as e:                                        # noqa: BLE001
            return _erro(str(e)[:400])
        fora = {"resposta": resposta, "modelo": MODELO}
        if corpo.get("para_elias"):
            cod, d = await _ops(c, "POST", "/msg", {
                "para": "claudinho-IA", "tipo": corpo.get("tipo", "resposta"),
                "assunto": corpo.get("assunto", "resposta do Jaiminho"), "corpo": resposta})
            fora["enviado"] = {"http": cod, **d}
    return JSONResponse(fora)


async def caixa(req):
    """Le a caixa dele. Com ?responder=1, responde cada mensagem ao Elias."""
    responder = req.query_params.get("responder") in ("1", "true")
    async with httpx.AsyncClient(timeout=300) as c:
        cod, d = await _ops(c, "GET", "/msg")
        if cod != 200:
            return JSONResponse(d, status_code=cod)
        msgs = d.get("mensagens", [])
        if not responder or not msgs:
            return JSONResponse(d)
        _, sessao = await _ops(c, "GET", "/sessao")
        sistema = _sistema(sessao)
        feitas = []
        for m in msgs:
            try:
                texto = await _gemini(c, sistema, [json.dumps(m, ensure_ascii=False)])
                cod2, r2 = await _ops(c, "POST", "/msg", {
                    "para": "claudinho-IA", "tipo": "resposta",
                    "assunto": f"re: {m.get('assunto', '-')}",
                    "responde": m.get("msgid"), "corpo": texto})
                feitas.append({"msgid": m.get("msgid"), "http": cod2, **r2})
            except Exception as e:                                    # noqa: BLE001
                feitas.append({"msgid": m.get("msgid"), "erro": str(e)[:200]})
    return JSONResponse({"lidas": len(msgs), "respostas": feitas})


app = Starlette(routes=[
    Route("/estado", estado),
    Route("/perguntar", perguntar, methods=["POST"]),
    Route("/caixa", caixa),
])
