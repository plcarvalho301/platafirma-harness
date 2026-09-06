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
    "para": "ia", "tipo": "handoff", "assunto": "ENSAIO — sera apagado",
    "corpo": "ensaio fim a fim do canal mediado, 13/08. Mensagem de teste."}))
msgid = r.json().get("msgid")

passo(4, "mandar para ti (deve NEGAR)", c.post("/msg", headers=H, json={
    "para": "ti", "tipo": "pedido", "assunto": "nao devia passar", "corpo": "x"}))

passo(5, "ler caixa alheia por query string (nao ha parametro de caixa)",
      c.get("/msg?caixa=ti", headers=H), lambda d: {"caixa_lida": d.get("caixa")})

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
for mid, campos in rc.xrange("caixa:ia"):
    if campos.get("id") == msgid:
        rc.xdel("caixa:ia", mid)
        apagadas += 1
print(f"\n[limpeza] mensagem de ensaio removida da caixa do Elias: {apagadas}")
p = subprocess.run([str(s.RAIZ / "bin" / "mesa"), "limpa", "jaiminho"],
                   capture_output=True, text=True,
                   env={**os.environ, "PF_CADEIRA": "jaiminho"})
print("[limpeza] mesa:", (p.stdout or p.stderr).strip())


# ======================================================================
# Leva 1 — economia de giro (docs/ordem-economia-de-giro.md, apagado na
# Leva 2): sombra inequivoca (A1), sessao_id nas genericas + auditoria de
# identidade (A2), gate transparente em run_command (A3), renome leva (A4).
# Hermetico DAQUI PRA BAIXO: redis e _quem() sao dublados nestes testes novos,
# nada deles toca o Valkey real. O script de ensaio ACIMA (linhas 1-76, canal
# mediado do jaiminho) e preexistente, roda a importacao do modulo e toca
# infra real (Valkey, fila) — nao foi tocado por esta leva.
# ======================================================================
import asyncio
import json as _json
from unittest.mock import patch


def _fake_redis_cls(kv=None, sets=None):
    _kv = dict(kv or {})
    _sets = {k: set(v) for k, v in (sets or {}).items()}

    class _FakeRedis:
        def __init__(self, *a, **k):
            pass

        def set(self, k, v, ex=None):
            _kv[k] = v

        def get(self, k):
            return _kv.get(k)

        def sadd(self, k, v):
            _sets.setdefault(k, set()).add(v)

        def expire(self, k, ttl):
            pass

        def smembers(self, k):
            return set(_sets.get(k, set()))

        def exists(self, k):
            return k in _kv

    return _FakeRedis


def test_sombra_inequivoca_uma_viva():
    FakeRedis = _fake_redis_cls(kv={"sessao:S1": "{}"}, sets={"sombra:u:sd:j": {"S1"}})
    with patch.object(s, "redis") as _rmod, \
         patch.object(s, "_quem", return_value={"sub": "u", "sid": "sd", "jti": "j"}):
        _rmod.Redis = FakeRedis
        assert s._sombra_inequivoca() == "S1"


def test_sombra_inequivoca_duas_vivas_audita_ambigua():
    FakeRedis = _fake_redis_cls(kv={"sessao:S1": "{}", "sessao:S2": "{}"},
                                sets={"sombra:u:sd:j": {"S1", "S2"}})
    with patch.object(s, "redis") as _rmod, \
         patch.object(s, "_quem", return_value={"sub": "u", "sid": "sd", "jti": "j"}), \
         patch.object(s, "_audit") as _aud:
        _rmod.Redis = FakeRedis
        assert s._sombra_inequivoca() is None
        assert any(c.kwargs.get("evento") == "sessao_ambigua" for c in _aud.call_args_list)


def test_sombra_inequivoca_zero_vivas():
    FakeRedis = _fake_redis_cls()
    with patch.object(s, "redis") as _rmod, \
         patch.object(s, "_quem", return_value={"sub": "u", "sid": "sd", "jti": "j"}):
        _rmod.Redis = FakeRedis
        assert s._sombra_inequivoca() is None


def test_sombra_inequivoca_token_estatico_nao_toca_valkey():
    with patch.object(s, "redis") as _rmod, \
         patch.object(s, "_quem", return_value={"sub": "-", "sid": "-", "jti": "-"}):
        assert s._sombra_inequivoca() is None
        _rmod.Redis.assert_not_called()


def test_sessao_resolve_parametro_vence_sombra():
    with patch.object(s, "_sombra_inequivoca", return_value="NUNCA-CHAMADA"):
        out = s._sessao_resolve("EXPLICITO")
    assert out["sessao_id"] == "EXPLICITO"


def test_sessao_resolve_sem_parametro_usa_sombra_e_resolve_cadeira():
    FakeRedis = _fake_redis_cls(kv={"sessao:VIA-SOMBRA": _json.dumps(
        {"cadeira": "fabrica", "ordem_id": "o-teste"})})
    with patch.object(s, "_sombra_inequivoca", return_value="VIA-SOMBRA"), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = FakeRedis
        out = s._sessao_resolve(None)
    assert out["sessao_id"] == "VIA-SOMBRA"
    assert out["cadeira"] == "fabrica"


def test_gate_verbo_roteado_traz_aviso():
    with patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(command="mesa ver"))
    assert "aviso" in r


def test_gate_fallback_sem_verbo():
    with patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(command="git status", cwd="platafirma-harness"))
    assert "aviso" not in r and "lote" not in r
    assert r.get("exit_code") == 0


def test_gate_lote_dois_segs_roteados():
    with patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(command="mesa ver; fila status"))
    assert "lote" in r and len(r["lote"]) == 2


def test_gate_pipe_cai_no_fallback():
    with patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(command="rg x | wc -l"))
    assert "aviso" not in r and "lote" not in r
    assert r.get("exit_code") == 0


def test_renome_leva_campo_json_e_retencao():
    import subprocess
    cp = subprocess.run(["acervo", "listar", "ferramental", "--tools"],
                        capture_output=True, text=True, timeout=30, cwd=str(s.RAIZ))
    assert cp.returncode == 0, cp.stderr
    itens = _json.loads(cp.stdout)
    by_tool = {i["tool"]: i for i in itens}
    assert "repo" in by_tool, "verbo repo sumiu da projecao apos o renome"
    assert "leva" in by_tool["repo"], "campo JSON deveria ser 'leva', nao 'lote'"
    assert by_tool["repo"]["leva"] == 2
    assert all("lote" not in i for i in itens), "campo antigo 'lote' nao deveria sobreviver"
    retidas_leva2 = {t for t, i in by_tool.items() if int(i.get("leva") or 1) >= 2}
    assert "repo" in retidas_leva2


def test_audit_run_command_carrega_identidade():
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        asyncio.run(s.run_command(command="git status", sessao_id="ensaio-sid-abc"))
    achou = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "run_command"]
    assert achou and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou)


def test_audit_read_file_carrega_identidade():
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        s.read_file(path="README.md", sessao_id="ensaio-sid-abc")
    achou = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "read_file"]
    assert achou and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou)


def test_audit_write_file_carrega_identidade():
    alvo = "var/tmp/_ensaio_write_probe.txt"
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        s.write_file(path=alvo, content="ensaio\n", sessao_id="ensaio-sid-abc")
    achou = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "write_file"]
    assert achou and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou)
    (s.RAIZ / alvo).unlink(missing_ok=True)
