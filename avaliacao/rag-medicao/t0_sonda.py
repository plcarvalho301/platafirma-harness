#!/usr/bin/env python3
"""T0 - sonda fixa do acervo. 10 perguntas, uma chamada rag_search cada,
parametros congelados: texto='secao', k=8, sem filtro."""
import json, os, sys, urllib.request, uuid, datetime, pathlib, re

ENV = "/home/claudinho/AI/platafirma-conhecimento/.env"
tok = None
for cand in (ENV, "/home/claudinho/AI/platafirma-conhecimento/mcp/.env"):
    if os.path.exists(cand):
        for ln in open(cand):
            m = re.match(r'\s*MCP_AUTH_TOKEN\s*=\s*"?([^"\n]+)"?', ln)
            if m:
                tok = m.group(1).strip()
if not tok:
    sys.exit("MCP_AUTH_TOKEN nao encontrado")

URL = "http://127.0.0.1:8090/mcp"
HDR = {"Content-Type": "application/json",
       "Accept": "application/json, text/event-stream",
       "Authorization": "Bearer " + tok}
SESSION = {}

def post(payload):
    h = dict(HDR)
    h.update(SESSION)
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        sid = r.headers.get("mcp-session-id")
        if sid:
            SESSION["mcp-session-id"] = sid
        body = r.read().decode("utf-8")
    if not body.strip():
        return None
    if body.lstrip().startswith("event:") or body.lstrip().startswith("data:"):
        for line in body.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return None
    return json.loads(body)

post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                 "clientInfo": {"name": "t0-sonda", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

PERGUNTAS = [
 ("01", "o que é um conceito e qual seu critério de identidade"),
 ("02", "o que distingue um tipo de um papel"),
 ("03", "o que é arquitetura de software"),
 ("04", "o que é arquitetura de dados"),
 ("05", "o que é governança de dados"),
 ("06", "o que é um domínio em gestão do conhecimento"),
 ("07", "o que é inteligência"),
 ("08", "o que é criptografia pós-quântica"),
 ("09", "o que é uma decisão arquitetural e quando se registra"),
 ("10", "o que é curadoria de acervo"),
]

out = {}
for nn, p in PERGUNTAS:
    r = post({"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
              "params": {"name": "rag_search",
                         "arguments": {"pergunta": p, "texto": "secao", "k": 8}}})
    res = r.get("result", {})
    txt = None
    for c in res.get("content", []):
        if c.get("type") == "text":
            txt = c["text"]
    try:
        retorno = json.loads(txt)
    except Exception:
        retorno = {"_bruto": txt}
    out[nn] = {"pergunta": p,
               "chamada_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "retorno": retorno}
    print(nn, "ok", len(txt or ""), file=sys.stderr)

pathlib.Path("/home/claudinho/AI/rag-medicao/T0").mkdir(parents=True, exist_ok=True)
json.dump(out, open("/home/claudinho/AI/rag-medicao/T0/_sondas_brutas.json", "w"),
          ensure_ascii=False, indent=1)
print("gravado _sondas_brutas.json")
