"""Ensaio fim a fim do canal mediado, com sujeito de mentira.

Nao toca no realm: identidade e remit de claudinho-seguranca. O sujeito `jaiminho`
entra pela rota de emergencia (token estatico + OPS_USER), que percorre exatamente
o mesmo caminho de PEP, PDP, rotas e malha msg que o JWT percorreria.
"""
import json
import os
import subprocess

TOKEN = "ensaio-jaiminho-13082026"
os.environ["OPS_USER"] = "jaiminho"
os.environ["OPS_AUTH_TOKEN"] = TOKEN
os.environ["OPS_NAME"] = "ops-ensaio"
os.environ["OPS_TOKEN_ESTATICO_ATE"] = "2026-09-30"

import server as s                                          # noqa: E402
from starlette.testclient import TestClient                 # noqa: E402

H = {"Authorization": f"Bearer {TOKEN}"}
c = TestClient(s.app)


def passo(n, titulo, r, extrai=None):
    tipo = r.headers.get("content-type", "")
    corpo = r.json() if tipo.startswith("application/json") else r.text
    if extrai and isinstance(corpo, dict):
        corpo = extrai(corpo)
    print(f"\n[{n}] {titulo}  -> HTTP {r.status_code}")
    print(json.dumps(corpo, ensure_ascii=False, indent=1)[:900])
    return r


passo(1, "abrir sessao", c.get("/sessao", headers=H), lambda d: {
    "sujeito": d.get("sujeito"),
    "acoes": d.get("acoes"),
    "persona": "ausente" if d.get("persona", {}).get("ausente") else "presente",
    "manifesto_bytes": len(d.get("manifesto", {}).get("content", "")),
    "fila": d.get("fila")})

passo(2, "ler a propria caixa", c.get("/msg", headers=H))

r = passo(3, "mandar recado ao Elias (permitido)", c.post("/msg", headers=H, json={
    "para": "claudinho-IA", "tipo": "handoff", "assunto": "ENSAIO — sera apagado",
    "corpo": "ensaio fim a fim do canal mediado, 13/08. Mensagem de teste."}))
msgid = r.json().get("msgid")

passo(4, "mandar para claudinho-TI (deve NEGAR)", c.post("/msg", headers=H, json={
    "para": "claudinho-TI", "tipo": "pedido", "assunto": "nao devia passar", "corpo": "x"}))

passo(5, "ler caixa alheia por query string (nao ha parametro de caixa)",
      c.get("/msg?caixa=claudinho-TI", headers=H), lambda d: {"caixa_lida": d.get("caixa")})

print("\n[6] tool run_command pelo PEP (deve NEGAR)")
print(json.dumps(s._autoriza("run_command", "run_command", "comando", "id",
                             s.DOM_RUNTIME, ident={"sujeito": "jaiminho"}),
                 ensure_ascii=False, indent=1))

passo(7, "encerrar a fita", c.post("/sessao/encerrar", headers=H,
                                  json={"nota": "ensaio: canal e sessao verificados."}))

passo(8, "sem token (deve dar 401)", c.get("/sessao"))

# limpeza: o ensaio nao deixa lixo na caixa do Elias nem na mesa
f = s._fila_mod()
rc = f.r_conn()
apagadas = 0
for mid, campos in rc.xrange("caixa:claudinho-IA"):
    if campos.get("id") == msgid:
        rc.xdel("caixa:claudinho-IA", mid)
        apagadas += 1
print(f"\n[limpeza] mensagem de ensaio removida da caixa do Elias: {apagadas}")
p = subprocess.run([str(s.RAIZ / "bin" / "mesa"), "limpa", "jaiminho"],
                   capture_output=True, text=True,
                   env={**os.environ, "PF_CADEIRA": "jaiminho"})
print("[limpeza] mesa:", (p.stdout or p.stderr).strip())
