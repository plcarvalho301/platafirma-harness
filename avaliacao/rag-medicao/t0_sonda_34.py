#!/usr/bin/env python3
"""T0 -- sonda fixa do acervo, 34 sondas do gold-set-firmabot.md (substitui as
10 antigas, que foram deletadas por serem fossil). Protocolo:
instancia sem persona, rag_search por sonda, parametros congelados
texto="secao", k=8, sem filtro de dominio/subdominio/frente/colecao.
Fonte das 34 perguntas: platafirma-conhecimento/rag/docs/gold-set-firmabot.md
"""
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
                 "clientInfo": {"name": "t0-sonda-34", "version": "1"}}})
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

# Bloco A -- 10 sondas fixas (pergunta completa)
BLOCO_A = [
 ("01", "o que é um conceito e qual seu critério de identidade?"),
 ("02", "o que distingue um tipo de um papel?"),
 ("03", "o que é arquitetura de software?"),
 ("04", "o que é arquitetura de dados?"),
 ("05", "o que é governança de dados?"),
 ("06", "o que é um domínio em gestão do conhecimento?"),
 ("07", "o que é inteligência?"),
 ("08", "o que é criptografia pós-quântica?"),
 ("09", "o que é uma decisão arquitetural e quando se registra?"),
 ("10", "o que é curadoria de acervo?"),
]

# Bloco B -- 24 termos, teste de dicionario estrito (termo -> obra)
BLOCO_B = [
 ("11", "DDD"),
 ("12", "convergência sociotécnica"),
 ("13", "arquitetura de negócios"),
 ("14", "vocabulário controlado"),
 ("15", "continuant e occurrent"),
 ("16", "proveniência arquivística"),
 ("17", "fusão recíproca de rankings"),
 ("18", "estratégia de chunking"),
 ("19", "quantização de modelo"),
 ("20", "opportunity solution tree"),
 ("21", "posicionamento de produto"),
 ("22", "avaliação heurística"),
 ("23", "gestão de incidente"),
 ("24", "gestão de mudança"),
 ("25", "observabilidade"),
 ("26", "trunk-based development"),
 ("27", "feature flag"),
 ("28", "teste de contrato"),
 ("29", "cryptoperiod"),
 ("30", "nível de garantia de autenticação"),
 ("31", "gestão de acesso privilegiado"),
 ("32", "cost of delay"),
 ("33", "limite de WIP"),
 ("34", "role charter"),
]

TODAS = BLOCO_A + BLOCO_B
OUT_DIR = pathlib.Path("/home/claudinho/AI/platafirma-harness/avaliacao/rag-medicao/T0")
OUT_DIR.mkdir(parents=True, exist_ok=True)

for nn, p in TODAS:
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
    acervo_sha = retorno.get("indice", {}).get("acervo_sha") if isinstance(retorno, dict) else None
    rec = {
        "sonda": "T0",
        "n": nn,
        "bloco": "A" if int(nn) <= 10 else "B",
        "persona": "persona-nao-declarada",
        "pergunta": p,
        "parametros_congelados": {"texto": "secao", "k": 8, "dominio": None,
                                   "subdominio": None, "frente": None, "colecao": None},
        "chamada_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "acervo_sha": acervo_sha,
        "retorno": retorno,
    }
    fname = OUT_DIR / f"T0-{nn}-persona-nao-declarada.json"
    json.dump(rec, open(fname, "w"), ensure_ascii=False, indent=1)
    print(nn, "ok", len(txt or ""), "->", fname.name, file=sys.stderr)

print(f"gravadas {len(TODAS)} sondas em {OUT_DIR}")
