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
import sys
from unittest.mock import patch


def _fake_redis_cls(kv=None, sets=None):
    _kv = dict(kv or {})
    _sets = {k: set(v) for k, v in (sets or {}).items()}
    _hash = {}

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

        # --- hash, contador e DEL: o que o ledger de dedup (arq:0101 R2) usa ---
        def hget(self, k, campo):
            return _hash.get(k, {}).get(campo)

        def hset(self, k, campo=None, valor=None, mapping=None):
            d = _hash.setdefault(k, {})
            if mapping:
                d.update(mapping)
            else:
                d[campo] = valor

        def hgetall(self, k):
            return dict(_hash.get(k, {}))

        def incr(self, k):
            _kv[k] = int(_kv.get(k, 0)) + 1
            return _kv[k]

        def delete(self, *ks):
            n = 0
            for k in ks:
                n += 1 if _kv.pop(k, None) is not None or _hash.pop(k, None) is not None else 0
            return n

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
        s.read_file(path="platafirma-harness/ops-server/requirements.txt", sessao_id="ensaio-sid-abc")
    achou = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "read_file"]
    assert achou and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou)


def test_audit_write_file_carrega_identidade():
    alvo = "var/tmp/_ensaio_write_probe.txt"
    with patch.object(s, "_audit") as _aud, patch.object(s, "_autoriza", return_value=None):
        s.write_file(path=alvo, content="ensaio\n", sessao_id="ensaio-sid-abc")
    achou = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "write_file"]
    assert achou and all(("sessao_id" in kw and "ordem_id" in kw and "cadeira" in kw) for kw in achou)
    (s.RAIZ / alvo).unlink(missing_ok=True)


# ======================================================================
# Leva 2 — economia de giro: chamada em lote nos verbos e genericas (B1/B2),
# teto D4. Atras de PF_TOOLS_LOTE; hermetico (autoriza liberado, sem tocar
# infra alem do subprocesso real de bash -c / bin/mesa, que ja e o
# comportamento normal de run_command/verbo fora de lote).
# ======================================================================


def test_lote_verbo_dois_atos():
    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(s, "_autoriza", return_value=None):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r = asyncio.run(_tool(lote=[{"ato": "ver"}, {"ato": "ver"}]))
    assert r["lote_n"] == 2
    assert len(r["lote"]) == 2


def test_lote_verbo_autoriza_bloqueia_item_negado():
    sentinela = {"erro": "negado de teste"}

    def _run_verbo_nao_deveria_rodar(*a, **k):
        raise AssertionError("_run_verbo_blocking nao deveria rodar quando _autoriza nega")

    with patch.object(s, "PF_TOOLS_LOTE", True), \
         patch.object(s, "_autoriza", return_value=sentinela), \
         patch.object(s, "_run_verbo_blocking", side_effect=_run_verbo_nao_deveria_rodar):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r = asyncio.run(_tool(lote=[{"ato": "ver"}, {"ato": "ver"}]))
    assert r["lote"] == [sentinela, sentinela]


def test_lote_verbo_off_ignora_campo():
    with patch.object(s, "PF_TOOLS_LOTE", False), patch.object(s, "_autoriza", return_value=None):
        _tool = s._faz_tool_verbo("mesa", "mesa", "mesa (teste)")
        r = asyncio.run(_tool(ato="ver", lote=[{"ato": "ver"}]))
    assert "lote" not in r


def test_lote_run_command_dois_itens_erro_nao_derruba():
    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(commands=["echo a", "false"], cwd="."))
    assert r["lote_n"] == 2
    assert r["lote"][0]["exit_code"] == 0
    assert r["lote"][1]["exit_code"] != 0


def test_lote_run_command_teto_corta_e_devolve_lote_next():
    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "CAP", 1):
        r = asyncio.run(s.run_command(commands=["echo a", "echo b", "echo c"], cwd="."))
    assert r["lote_next"] is not None
    assert any(item.get("omitido_por_teto") for item in r["lote"])


def test_pf_tools_lote_off_ignora_commands():
    with patch.object(s, "PF_TOOLS_LOTE", False), patch.object(s, "_autoriza", return_value=None):
        r = asyncio.run(s.run_command(command="echo ok", commands=["echo a", "echo b"], cwd="."))
    assert "lote" not in r
    assert r.get("exit_code") == 0


def test_lote_read_file_dois_paths():
    with patch.object(s, "PF_TOOLS_LOTE", True), patch.object(s, "_autoriza", return_value=None):
        r = s.read_file(paths=["platafirma-harness/ops-server/requirements.txt", "platafirma-harness/ops-server/_ensaio.py"])
    assert r["lote_n"] == 2
    assert len(r["lote"]) == 2


def test_pf_tools_lote_off_ignora_paths():
    with patch.object(s, "PF_TOOLS_LOTE", False), patch.object(s, "_autoriza", return_value=None):
        r = s.read_file(path="platafirma-harness/ops-server/requirements.txt", paths=["platafirma-harness/ops-server/_ensaio.py"])
    assert "lote" not in r
    assert "content" in r


# ======================================================================
# arq:0101 — poda de contexto na porta + entidade-sessao unica (card #3013).
# Hermetico: Valkey dublado, derrame em tmp, nada toca infra real. Cada bloco
# abaixo casa com uma linha do ACEITE do card, nesta ordem.
# ======================================================================
import tempfile                                              # noqa: E402
import uuid as _uuid                                         # noqa: E402
from pathlib import Path as _Path                            # noqa: E402

import poda as _p                                            # noqa: E402

_UUID_A = "11111111-2222-4333-8444-555555555555"


def _derrame_tmp():
    """Derrame e ledger em tmp: teste que escreve em var/tmp/retornos real polui o
    contrato de morte da fita viva ao lado."""
    return patch.object(_p, "DERRAME", _Path(tempfile.mkdtemp(prefix="poda-ensaio-")))


def _pacote_falso(sessao_id=None, **extra):
    """Duble do MONTADOR — e ele quem cunha `sessao_id` (arq:0101 §1). A porta so
    repassa o que a fita portou e persiste o que voltou."""
    sid = sessao_id or str(_uuid.uuid4())
    return {"cadeira": "fabrica", "nome_canonico": "fabrica", "pecas": [],
            "sessao_id": sid,
            "sessao": {"id": sid, "cunhada_agora": not sessao_id},
            "roteador": {"via": "teste", "slug": None}, **extra}


# --- aceite 1: uma conversa = um sessao_id RFC-4122, cunhado uma vez -----------
def test_abertura_cunha_rfc4122_uma_vez_e_segunda_nao_recunha():
    Fake = _fake_redis_cls()
    with patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "_montar", side_effect=lambda *a: _pacote_falso(a[4] or None)), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        r1 = asyncio.run(s.monta_sessao(cadeira="fabrica"))
        sid = r1["sessao_id"]
        r2 = asyncio.run(s.monta_sessao(cadeira="fabrica", sessao_id=sid))
    assert str(_uuid.UUID(sid)) == sid and sid.count("-") == 4, "formato voltou ao RFC-4122 (0091 §4)"
    assert r1["sessao"]["cunhada_agora"] is True
    assert r2["sessao_id"] == sid and r2["sessao"]["cunhada_agora"] is False
    assert r1["ordem_id"] != r2["ordem_id"], "ordem_id e por ordem; sessao_id e por conversa"


def test_porta_repassa_o_portado_ao_verbo_e_nao_cunha():
    """QUEM CUNHA E O MONTADOR. A porta nao tem gerador — repassa e persiste."""
    Fake, visto = _fake_redis_cls(), {}

    def _duble(cadeira, atualizar, chapeu, pergunta, sessao_id):
        visto["sessao_id"] = sessao_id
        return _pacote_falso(sessao_id or None)

    with patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "_montar", side_effect=_duble), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        asyncio.run(s.monta_sessao(cadeira="fabrica", sessao_id=_UUID_A))
    assert visto["sessao_id"] == _UUID_A, "o portado desce para o verbo"

    # Montador mudo: a porta NAO inventa uuid — sai sem sessao, declarado. (O uuid4 que
    # sobra em `monta_sessao` e o do `ordem_id`, que e da porta por norma: ordem_id e por
    # ordem do dono, sessao_id e por conversa.)
    with patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "_montar", side_effect=lambda *a: {"cadeira": "fabrica",
                                                            "nome_canonico": "fabrica",
                                                            "pecas": []}), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = _fake_redis_cls()
        r = asyncio.run(s.monta_sessao(cadeira="fabrica"))
    assert not r.get("sessao_id"), "porta sem gerador proprio"
    assert any("sessao_id" in a for a in r.get("avisos", [])), "ausencia se declara"
    assert r.get("ordem_id"), "ordem_id continua sendo da porta"


def test_montador_e_o_unico_gerador_de_sessao_id():
    """Cunho e reuso medidos no VERBO, por subprocesso — e ele o ponto por onde toda
    superficie abre (a fabrica chama `bin/monta-sessao` direto, sem porta)."""
    verbo = str(_Path(__file__).parent.parent / "bin/monta-sessao")
    import subprocess as _sp

    def _abre(*flags):
        cp = _sp.run([verbo, "fabrica", "--json", "--so-chapeu", *flags],
                     capture_output=True, text=True, timeout=120)
        return _json.loads(cp.stdout)

    p1 = _abre()
    assert _uuid.UUID(p1["sessao_id"]) and p1["sessao"]["cunhada_agora"] is True
    p2 = _abre("--sessao-id", p1["sessao_id"])
    assert p2["sessao_id"] == p1["sessao_id"] and p2["sessao"]["cunhada_agora"] is False
    p3 = _abre("--sessao-id", _UUID_A.replace("-", ""))          # 32-hex legado
    assert p3["sessao_id"] == _UUID_A
    p4 = _abre("--sessao-id", "nao-e-uuid")
    assert p4["sessao_id"] != "nao-e-uuid"
    assert any("RFC-4122" in a for a in p4.get("avisos", []))




def test_join_nao_se_grava_sob_sid_reciclavel():
    """`s<hex>` de id(session) reaparece em outra fita depois do GC (#409): chave
    reciclavel no ledger daria a fita de uma sessao para a proxima que calhar."""
    Fake = _fake_redis_cls()
    with patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "_montar", side_effect=lambda *a: _pacote_falso(a[4] or None)), \
         patch.object(s, "_sessao_atual", return_value="s7aab160cb740"), \
         patch.object(s, "_sid_header", return_value=None), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        asyncio.run(s.monta_sessao(cadeira="fabrica"))
        rc = Fake()
        assert rc.get("conexao:s7aab160cb740") is None, "sid reciclavel nao vira chave"
        with patch.object(s, "_sombra_inequivoca", return_value=None):
            assert s._sessao_resolve(None)["sessao_id"] == "-"


def test_join_grava_e_resolve_com_header_do_cliente():
    Fake = _fake_redis_cls()
    with patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "_montar", side_effect=lambda *a: _pacote_falso(a[4] or None)), \
         patch.object(s, "_sessao_atual", return_value="hdr-abc"), \
         patch.object(s, "_sid_header", return_value="hdr-abc"), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        r = asyncio.run(s.monta_sessao(cadeira="fabrica"))
        out = s._sessao_resolve(None)
    assert out["sessao_id"] == r["sessao_id"] and out["cadeira"] == "fabrica"


def test_join_conexao_sessao_vive_no_msg_mem_nao_em_ram():
    """O que sobrevive ao restart da porta e o join no msg-mem — nao ha mais dict."""
    assert not hasattr(s, "_sessao_por_sid") and not hasattr(s, "_ordem_por_sid")
    Fake = _fake_redis_cls(kv={f"sessao:{_UUID_A}": _json.dumps({"cadeira": "fabrica",
                                                                 "ordem_id": "o-x"}),
                               "conexao:sid-teste": _UUID_A})
    with patch.object(s, "redis") as _rmod, \
         patch.object(s, "_sessao_atual", return_value="sid-teste"), \
         patch.object(s, "_sid_header", return_value="sid-teste"):
        _rmod.Redis = Fake
        out = s._sessao_resolve(None)
    assert out["sessao_id"] == _UUID_A and out["cadeira"] == "fabrica"


# --- aceite 2: ops log grava bytes_servidos + sha, e sessao_id em toda linha ---
def test_ops_log_grava_sessao_id_em_toda_linha():
    with tempfile.TemporaryDirectory() as d, patch.object(s, "LOG_DIR", _Path(d)):
        s._audit(tool="-", evento="teste_sem_sessao")
        linha = _json.loads(next(iter(_Path(d).glob("ops-*.jsonl"))).read_text().splitlines()[0])
    assert linha["sessao_id"] == "-", "ausencia se declara, nao se omite"


def test_ops_log_grava_bytes_servidos_e_sha_por_retorno():
    Fake = _fake_redis_cls()
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "redis") as _rmod, patch.object(s, "_audit") as _aud:
        _rmod.Redis = Fake
        s.read_file(path="platafirma-harness/ops-server/requirements.txt", sessao_id=_UUID_A)
    kw = [c.kwargs for c in _aud.call_args_list if c.kwargs.get("tool") == "read_file"][0]
    assert kw["bytes_servidos"] and kw["sha"], "o servido e o hash sao o que faltava medir"


# --- aceite 3: corte cabeca+cauda+alca; erro nunca podado; id exato intocado ---
def test_corte_cauda_sim_preserva_o_fim():
    texto = "CABECA\n" + ("x" * 5_000) + "\nVEREDITO: passou"
    fora, meta = _p.corta(texto, 1_000, cauda=True, alca="var/tmp/retornos/x.txt")
    assert fora.startswith("CABECA") and fora.endswith("VEREDITO: passou")
    assert meta["cortado"] and "var/tmp/retornos/x.txt" in fora


def test_corte_cauda_nao_e_o_comportamento_de_hoje():
    texto = "CABECA\n" + ("x" * 5_000) + "\nFIM"
    fora, _ = _p.corta(texto, 1_000, cauda=False, alca=None)
    assert fora.startswith("CABECA") and not fora.endswith("FIM")


def test_erro_e_exit_diferente_de_zero_nunca_podam():
    assert _p.intocavel({"erro": "timeout"})
    assert _p.intocavel({"exit_code": 1})
    assert not _p.intocavel({"exit_code": 0})
    ruidoso = {"exit_code": 2, "stdout": {"texto": "a\n" * 500, "bytes_total": 1000}}
    with patch.object(s, "redis") as _rmod:
        _rmod.Redis = _fake_redis_cls()
        assert s._serve(dict(ruidoso), tool="t", alca="a", ident={"sessao_id": _UUID_A}) == ruidoso


def test_identificador_exato_nao_se_toca():
    """`path` e alca sao identificador: a poda mexe no conteudo, nunca no endereco."""
    Fake = _fake_redis_cls()
    alvo = "platafirma-harness/ops-server/requirements.txt"
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        r = s.read_file(path=alvo, sessao_id=_UUID_A)
    assert r["path"].endswith("requirements.txt")


# --- aceite 4: releitura identica serve delta; mudada serve diff ---------------
def test_releitura_identica_serve_aviso_estavel_sem_timestamp():
    Fake = _fake_redis_cls()
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        alvo = "platafirma-harness/ops-server/server.py"
        r1 = s.read_file(path=alvo, sessao_id=_UUID_A)
        r2 = s.read_file(path=alvo, sessao_id=_UUID_A)
        r3 = s.read_file(path=alvo, sessao_id=_UUID_A)
    assert r1["poda"]["ledger"] == "novo"
    assert r2["poda"]["modo"] == "igual" and "não reenviados" in r2["content"]
    assert r2["content"] == r3["content"], "aviso e ESTAVEL: sem timestamp, senao vira conteudo novo"
    assert len(r2["content"]) < len(r1["content"])


def test_retorno_curto_nao_deduplica_porque_o_aviso_custaria_mais():
    """Poda que engorda o retorno nao e poda: duas linhas cabem por menos que o aviso."""
    Fake = _fake_redis_cls()
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), \
         patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        alvo = "platafirma-harness/ops-server/requirements.txt"
        s.read_file(path=alvo, sessao_id=_UUID_A)
        r2 = s.read_file(path=alvo, sessao_id=_UUID_A)
    assert r2["poda"]["ledger"] == "curto" and "mcp==" in r2["content"]


def test_releitura_de_arquivo_mudado_serve_diff():
    Fake = _fake_redis_cls()
    with _derrame_tmp(), patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        led = _p.Ledger(Fake(), _UUID_A)
        base = "linha 1\nlinha 2\nlinha 3\n" * 20
        led.olha("arq", base, 1, "read_file")
        d = led.olha("arq", base.replace("linha 2", "linha DOIS", 1), 2, "read_file")
    assert d["modo"] == "diff" and "linha DOIS" in d["texto"] and "giro 1" in d["texto"]


def test_ledger_sem_sessao_roda_e_conta_nunca_recusa():
    led = _p.Ledger(None, "")
    d = led.olha("a", "texto", 0, "t")
    assert d["modo"] == "inteiro" and d["ledger"] == "sem_sessao"


# --- aceite 6: PF_PODA=0 + restart reverte -------------------------------------
def test_pf_poda_zero_reverte_a_porta_inteira():
    r = {"exit_code": 0, "stdout": {"texto": "\x1b[31mcor\x1b[0m\n" * 50, "bytes_total": 10}}
    with patch.dict(os.environ, {"PF_PODA": "0"}):
        assert s._serve(dict(r), tool="t", alca="a", ident={"sessao_id": _UUID_A}) == r
    with patch.dict(os.environ, {"PF_PODA": "1"}), _derrame_tmp(), patch.object(s, "redis") as _rmod:
        _rmod.Redis = _fake_redis_cls()
        assert s._serve(dict(r), tool="t", alca="a", ident={"sessao_id": _UUID_A}) != r


# --- R1: lavador determinístico ------------------------------------------------
def test_lavador_tira_ansi_e_progress_bar():
    fora, rel = _p.lava("\x1b[31mvermelho\x1b[0m\nbaixando 10%\rbaixando 100%\n")
    assert "\x1b[" not in fora and "baixando 100%" in fora and "10%" not in fora
    assert "terminal" in rel["classes"]


def test_lavador_colapsa_repeticao_identica():
    fora, rel = _p.lava("igual\n" * 10)
    assert "× 10" in fora and "repeticao" in rel["classes"]


def test_lavador_resume_molde_com_numero_variando():
    fora, rel = _p.lava("\n".join(f"processando item {i}" for i in range(20)))
    assert "+18 linhas no mesmo molde" in fora and "repeticao" in rel["classes"]


def test_lavador_marca_blob_e_preserva_bordas():
    fora, rel = _p.lava("prefixo " + ("Zm9vYmFyego" * 40) + " sufixo")
    assert "<blob tipo=base64 bytes=440" in fora and fora.startswith("prefixo")
    assert fora.endswith("sufixo") and "blob" in rel["classes"]


def test_lavador_agrupa_saida_de_busca():
    linhas = [f"src/a.py:{i}:achou aqui" for i in range(1, 12)]
    linhas += [f"src/b.py:{i}:achou tambem" for i in range(1, 4)]
    fora, rel = _p.lava("\n".join(linhas))
    assert "src/a.py  (11 matches)" in fora and "+6 matches neste arquivo" in fora
    assert "busca" in rel["classes"] and "src/b.py" in fora


def test_lavador_tira_rastro_de_pacote_e_pontos_de_pytest():
    fora, _ = _p.lava("Collecting redis\nDownloading redis.whl\n....... [ 87%]\nok final")
    assert fora.strip() == "ok final"


def test_guardrail_de_entrada_quatro_vezes_o_cap():
    fora, rel = _p.lava("z" * 10_000, cap=1_000)
    assert "guardrail" in rel["classes"] and len(fora) < 5_000


def test_envelope_enxuto_tira_stderr_vazio_e_cwd_repetido():
    fora = _p.enxuga_envelope({"exit_code": 0, "stderr": {"texto": "", "bytes_total": 0},
                               "cwd": str(_p.RAIZ), "erro": None, "stdout": {"texto": "x"}})
    assert "stderr" not in fora and "cwd" not in fora and "erro" not in fora
    assert "stdout" in fora


# --- R4: perfil por verbo lido do cabecalho ------------------------------------
def test_perfil_por_verbo_sai_do_cabecalho_e_ausente_e_o_de_hoje():
    s._PERFIS.clear()
    assert s._perfil_verbo("descansar", str(_Path(__file__).parent.parent / "bin/descansar")) == {
        "forma": "relatorio", "cauda": True}
    s._PERFIS.clear()
    assert s._perfil_verbo("inexistente", "/nao/existe") == {"forma": "listagem", "cauda": False}


# --- R7: hash unico, uma lib para a porta e para o montador --------------------
def test_hash_unico_porta_e_montador():
    sys.path.insert(0, str(_Path(__file__).parent.parent / "comum"))
    from hash_servido import sha_servido
    assert sha_servido("  abc\n") == sha_servido("abc") == _p.sha_servido("abc")
    assert len(sha_servido("abc")) == 12


# --- R2 na abertura: peca ja servida nesta sessao volta como aviso -------------
def test_peca_de_abertura_repetida_vira_aviso_na_segunda_abertura():
    Fake = _fake_redis_cls()
    peca = {"peca": "persona", "sha": "abc123abc123", "conteudo": "TEXTO DA PERSONA " * 50}
    with patch.object(s, "redis") as _rmod:
        _rmod.Redis = Fake
        r1 = {"pecas": [dict(peca)]}
        s._delta_pecas(r1, _UUID_A)
        r2 = {"pecas": [dict(peca)]}
        conta = s._delta_pecas(r2, _UUID_A)
    assert r1["pecas"][0]["conteudo"].startswith("TEXTO DA PERSONA")
    assert "já servido nesta sessão" in r2["pecas"][0]["conteudo"]
    assert conta["pecas_dedup"] == 1


# --- regressao medida no ar (06/09, primeiro retorno depois de subir) ----------
_JOURNAL = """active
ActiveEnterTimestamp=Sun 2026-09-06 18:58:05 -03
MainPID=737373
health=200
Sep 06 18:58:00 host systemd[1]: Stopping ops-mcp...
Sep 06 18:58:01 host systemd[1]: Started ops-mcp.
Sep 06 18:58:05 host uvicorn[737373]: INFO:     Started server process
Sep 06 18:58:05 host uvicorn[737373]: INFO:     Application startup complete.
Sep 06 18:58:05 host uvicorn[737373]: INFO:     Uvicorn running on http://127.0.0.1:8010
Sep 06 18:58:06 host uvicorn[737373]: INFO:     GET /mcp 200 OK"""


def test_timestamp_nao_e_resultado_de_busca():
    """`18:58:05` casava `arquivo:linha:conteudo` e journalctl saia remontado."""
    fora, rel = _p.lava(_JOURNAL)
    assert "busca" not in rel["classes"]
    assert "MainPID=737373" in fora and "health=200" in fora and "active" in fora
    assert "(7 matches)" not in fora


def test_busca_preserva_linha_que_nao_e_match():
    """Numa saida mista, o que nao e match sai onde estava — poda nao come linha."""
    bruto = ("procurando…\n" + "\n".join(f"src/a.py:{i}:achou" for i in range(1, 9))
             + "\n8 arquivos varridos")
    fora, rel = _p.lava(bruto)
    assert "busca" in rel["classes"]
    assert fora.splitlines()[0] == "procurando…"
    assert fora.splitlines()[-1] == "8 arquivos varridos"
    assert "src/a.py  (8 matches)" in fora


def test_contrato_de_morte_e_o_ultimo_ato_nao_o_do_meio():
    """`descansar fita` sem flag NAO mata: matar `sessao:{id}` no meio do rito tira a
    cadeira dos passos que o proprio verbo manda executar em seguida (medido 06/09)."""
    import subprocess as _sp
    verbo = str(_Path(__file__).parent.parent / "bin/descansar")
    env = {**os.environ, "PF_CADEIRA": "fabrica",
           "PF_SESSAO": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"}
    sem = _sp.run([verbo, "fita", "--so-memoria"], capture_output=True, text=True,
                  timeout=120, env=env).stdout
    assert "descansar fita --encerra-sessao" in sem, "o rito nomeia o passo 4"
    assert "contrato de morte" not in sem, "sem a flag, nao mata"
    com = _sp.run([verbo, "fita", "--encerra-sessao"], capture_output=True, text=True,
                  timeout=120, env=env).stdout
    assert "contrato de morte" in com and "chave(s) apagada(s)" in com
