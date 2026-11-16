"""Contratos da poda na porta (arq:0101 e incidente #3503): lavador, corte, ledger e escrita."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso", HARNESS_DIR / "comum"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-poda-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import poda as _p
import server as s
from hash_servido import sha_servido

s._MORADAS_LEITURA += (str(HARNESS_DIR),)

_UUID_A = "11111111-2222-4333-8444-555555555555"
_REQ = str(OPS_SERVER_DIR / "requirements.txt")
_SERVER = str(OPS_SERVER_DIR / "server.py")

_TRECHOS_VETORIAIS = "\n".join(
    f"acervo/obras/arq-0101.md:{10 + i * 7}: trecho {i} do top-k, "
    f"ranqueado por similaridade e servido inteiro"
    for i in range(1, 9)
)

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


class FakeRedisMemoria:
    def __init__(self, kv=None, sets=None):
        self.kv = dict(kv or {})
        self.sets = {k: set(v) for k, v in (sets or {}).items()}
        self.hash: dict[str, dict] = {}
        self.get = self.kv.get

    def __call__(self, *a, **k):
        return self

    def set(self, k, v, **opcoes):
        self.kv[k] = v
        return True

    def sadd(self, k, v):
        self.sets.setdefault(k, set()).add(v)
        return 1

    def expire(self, k, ttl):
        return True

    def smembers(self, k):
        return set(self.sets.get(k, set()))

    def exists(self, k):
        return int(k in self.kv)

    def hget(self, k, campo):
        mapa = self.hash.get(k) or {}
        return mapa.get(campo, None)

    def hset(self, k, campo=None, valor=None, mapping=None):
        d = self.hash.setdefault(k, {})
        if mapping:
            d.update(mapping)
        else:
            d[campo] = valor
        return 1

    def hgetall(self, k):
        return dict(self.hash.get(k) or {})

    def incr(self, k):
        return self.incrby(k, 1)

    def incrby(self, k, n):
        self.kv[k] = int(self.kv.get(k, 0)) + n
        return self.kv[k]

    def delete(self, *ks):
        return sum(
            1
            for k in ks
            if (self.kv.pop(k, None) is not None or self.hash.pop(k, None) is not None)
        )

    def hdel(self, k, *campos):
        d = self.hash.get(k) or {}
        return sum(1 for c in campos if d.pop(c, None) is not None)


def _na_morada(monkeypatch, pasta: Path) -> None:
    monkeypatch.setattr(s, "_MORADAS_LEITURA", (*s._MORADAS_LEITURA, str(pasta.resolve())))


def _derrame_tmp():
    return patch.object(_p, "DERRAME", Path(tempfile.mkdtemp(prefix="poda-ensaio-")))


def test_quem_escreve_sai_do_cabecalho_do_verbo(tmp_path):
    bin_ = HARNESS_DIR / "bin"
    s._ESCREVEM.clear()
    for ato in ("editar", "comentar", "mover", "criar", "dt"):
        assert s._escreve("tarefas", str(bin_ / "tarefas"), ato), ato
    for ato in ("ler", "listar", "comentarios", "modelo", None):
        assert not s._escreve("tarefas", str(bin_ / "tarefas"), ato), ato
    assert s._escreve("motor", str(bin_ / "motor"), "indexar")
    assert not s._escreve("motor", str(bin_ / "motor"), "eleger")
    assert not s._escreve("motor", str(bin_ / "motor"), "rag")
    sem = tmp_path / "semdecl"
    sem.write_text(
        "#!/usr/bin/env bash\n# forma: listagem\nset -e\n# volta: x=nao\n",
        encoding="utf-8",
    )
    assert not s._escreve("semdecl", str(sem), "x")
    s._ESCREVEM.clear()


def test_escrita_repetida_serve_a_confirmacao_inteira_toda_vez(tmp_path):
    bin_tarefas = str(HARNESS_DIR / "bin" / "tarefas")
    s._ESCREVEM.clear()
    conf = "item 3497 editado — descricao trocada, estado inalterado; " * 3
    r = {"exit_code": 0, "stdout": {"texto": conf, "bytes_total": len(conf)}}
    kw = {
        "tool": "tarefas",
        "alca": "tarefas editar 3497 --desc-stdin",
        "ident": {"sessao_id": _UUID_A},
    }
    esc_editar = s._escreve("tarefas", bin_tarefas, "editar")
    esc_ler = s._escreve("tarefas", bin_tarefas, "ler")
    with _derrame_tmp(), patch.object(s, "_rc", return_value=FakeRedisMemoria()):
        um = s._serve(dict(r), escrita=esc_editar, **kw)
        dois = s._serve(dict(r), escrita=esc_editar, **kw)
        lido = s._serve(dict(r), escrita=esc_ler, **{**kw, "alca": "tarefas ler 3497"})
        relido = s._serve(dict(r), escrita=esc_ler, **{**kw, "alca": "tarefas ler 3497"})
    assert um["stdout"]["texto"] == conf and dois["stdout"]["texto"] == conf
    assert "igual ao giro" not in dois["stdout"]["texto"]
    assert lido["stdout"]["texto"] == conf and "igual ao giro" in relido["stdout"]["texto"]

    verbo = tmp_path / "verbo_esc"
    verbo.write_text(
        "#!/bin/sh\n# atos: editar (escrita, card), ler (leitura, card)\n"
        "# volta: ler=sim — só lê\n# volta: editar=sim — desfaz\n",
        encoding="utf-8",
    )
    verbo.chmod(0o755)
    s._ESCREVEM.clear()
    tool = s._faz_tool_verbo("verbo_esc", str(verbo), "teste escrita")
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "_audit"
    ), patch.object(
        s, "_sessao_resolve", return_value={"sessao_id": _UUID_A, "ordem_id": "o1", "cadeira": "ia"}
    ), patch.object(
        s, "_run_verbo_blocking", side_effect=lambda *a, **k: dict(r)
    ), patch.object(
        s, "_rc", return_value=FakeRedisMemoria()
    ):
        t1 = asyncio.run(tool(ato="editar", args=["3497"]))
        t2 = asyncio.run(tool(ato="editar", args=["3497"]))
    assert t1["stdout"]["texto"] == conf and t2["stdout"]["texto"] == conf
    assert "igual ao giro" not in t2["stdout"]["texto"]
    s._ESCREVEM.clear()


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
        _rmod.Redis = FakeRedisMemoria()
        assert s._serve(dict(ruidoso), tool="t", alca="a", ident={"sessao_id": _UUID_A}) == ruidoso


def test_identificador_exato_nao_se_toca():
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        r = s.ler_arquivo(caminho=_REQ, sessao_id=_UUID_A)
    assert r["caminho"].endswith("requirements.txt")


def test_releitura_identica_serve_aviso_estavel_sem_timestamp():
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        r1 = s.ler_arquivo(caminho=_SERVER, linhas="1-80", sessao_id=_UUID_A)
        r2 = s.ler_arquivo(caminho=_SERVER, linhas="1-80", sessao_id=_UUID_A)
        r3 = s.ler_arquivo(caminho=_SERVER, linhas="1-80", sessao_id=_UUID_A)
    assert r1["poda"]["ledger"] == "novo"
    assert r2["poda"]["modo"] == "igual" and "não reenviados" in r2["conteudo"]
    assert r2["conteudo"] == r3["conteudo"]
    assert len(r2["conteudo"]) < len(r1["conteudo"])


def test_retorno_curto_nao_deduplica_porque_o_aviso_custaria_mais(tmp_path, monkeypatch):
    _na_morada(monkeypatch, tmp_path)
    curto = tmp_path / "curto.txt"
    curto.write_text("mcp==1.0\nredis==5.0\n", encoding="utf-8")
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        s.ler_arquivo(caminho=str(curto), sessao_id=_UUID_A)
        r2 = s.ler_arquivo(caminho=str(curto), sessao_id=_UUID_A)
    assert r2["poda"]["ledger"] == "curto" and "mcp==1.0" in r2["conteudo"]


def test_c15_leitura_serve_blob_e_crlf_como_estao(tmp_path, monkeypatch):
    _na_morada(monkeypatch, tmp_path)
    texto = "chave: " + "0123456789abcdef" * 25 + "\r\nlinha dois\r\n" + "QUJD" * 100 + "\n"
    alvo = tmp_path / "blob.txt"
    alvo.write_bytes(texto.encode())
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        r = s.ler_arquivo(caminho=str(alvo), sessao_id=_UUID_A)
    assert r["conteudo"] == texto and r["poda"]["lavado"] == []


def test_c16_releitura_igual_avisa_e_inteiro_reenvia(tmp_path, monkeypatch):
    _na_morada(monkeypatch, tmp_path)
    alvo = tmp_path / "relido.txt"
    alvo.write_text("".join(f"linha {i} de um arquivo relido\n" for i in range(200)))
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        r1 = s.ler_arquivo(caminho=str(alvo), sessao_id=_UUID_A)
        r2 = s.ler_arquivo(caminho=str(alvo), sessao_id=_UUID_A)
        r3 = s.ler_arquivo(caminho=str(alvo), sessao_id=_UUID_A, inteiro=True)
    assert r1["poda"]["ledger"] == "novo" and r1["conteudo"] == alvo.read_text()
    assert r2["poda"]["modo"] == "igual" and "cabecalho" not in r2 and r2["versao"]
    assert r2["conteudo"].endswith("bytes não reenviados; inteiro=true reenvia]")
    assert r3["conteudo"] == alvo.read_text() and r3["poda"]["ledger"] == "novo"


def test_ler_arquivo_audita_classe_do_erro(tmp_path, monkeypatch):
    _na_morada(monkeypatch, tmp_path)
    with _derrame_tmp(), patch.object(s, "_autoriza", return_value=None), patch.object(
        s, "redis"
    ) as _rmod, patch.object(s, "_audit") as aud:
        _rmod.Redis = FakeRedisMemoria()
        r = s.ler_arquivo(caminho=str(tmp_path / "nao" / "existe.py"), sessao_id=_UUID_A)
    assert r["erro"] == "não existe" and r["existe_ate"] == str(tmp_path)
    assert "classe_erro" not in r
    campos = aud.call_args.kwargs
    assert campos["tool"] == "ler_arquivo" and campos["classe_erro"] == "caminho"


def test_releitura_de_arquivo_mudado_serve_diff():
    fake = FakeRedisMemoria()
    with _derrame_tmp(), patch.object(s, "redis") as _rmod:
        _rmod.Redis = fake
        led = _p.Ledger(fake, _UUID_A)
        base = "linha 1\nlinha 2\nlinha 3\n" * 20
        led.olha("arq", base, 1, "ler_arquivo")
        d = led.olha("arq", base.replace("linha 2", "linha DOIS", 1), 2, "ler_arquivo")
    assert d["modo"] == "diff" and "linha DOIS" in d["texto"] and "giro 1" in d["texto"]


def test_ledger_sem_sessao_roda_e_conta_nunca_recusa():
    led = _p.Ledger(None, "")
    d = led.olha("a", "texto", 0, "t")
    assert d["modo"] == "inteiro" and d["ledger"] == "sem_sessao"


def test_constitutiva_nunca_vira_ponteiro_no_caminho_do_verbo():
    led = _p.Ledger(FakeRedisMemoria(), _UUID_A)
    persona = "TEXTO DA PERSONA " * 50
    r1 = led.olha("persona:persona conduta", persona, 1, "persona", constitutiva=True)
    r2 = led.olha("persona:persona conduta", persona, 2, "persona", constitutiva=True)
    assert r1["ledger"] == "novo" and r2["ledger"] == "constitutiva"
    assert r1["modo"] == "inteiro" and r2["modo"] == "inteiro" and r2["texto"] == persona


def test_eh_constitutiva_cobre_a_tabela_do_dono():
    assert s._eh_constitutiva("persona", "persona conduta")
    assert s._eh_constitutiva("persona", "persona ler")
    assert s._eh_constitutiva("mesa", "mesa caderno engenharia-de-harness")
    assert s._eh_constitutiva("expediente", "expediente montar")
    assert s._eh_constitutiva("tarefas", "tarefas modelo story")
    assert not s._eh_constitutiva("mesa", "mesa ver")
    assert not s._eh_constitutiva("motor", "motor rag buscar casa x")


def test_pf_poda_zero_reverte_a_porta_inteira():
    r = {"exit_code": 0, "stdout": {"texto": "\x1b[31mcor\x1b[0m\n" * 50, "bytes_total": 10}}
    with patch.dict(os.environ, {"PF_PODA": "0"}):
        assert s._serve(dict(r), tool="t", alca="a", ident={"sessao_id": _UUID_A}) == r
    with patch.dict(os.environ, {"PF_PODA": "1"}), _derrame_tmp(), patch.object(
        s, "redis"
    ) as _rmod:
        _rmod.Redis = FakeRedisMemoria()
        assert s._serve(dict(r), tool="t", alca="a", ident={"sessao_id": _UUID_A}) != r


def test_lavador_regras_deterministicas():
    fora_t, rel_t = _p.lava("\x1b[31mvermelho\x1b[0m\nbaixando 10%\rbaixando 100%\n")
    assert "\x1b[" not in fora_t and "baixando 100%" in fora_t and "10%" not in fora_t
    assert "terminal" in rel_t["classes"]

    fora_r, rel_r = _p.lava("igual\n" * 10)
    assert "× 10" in fora_r and "repeticao" in rel_r["classes"]

    fora_m, rel_m = _p.lava("\n".join(f"processando item {i}" for i in range(20)))
    assert "+18 linhas no mesmo molde" in fora_m and "repeticao" in rel_m["classes"]

    fora_b, rel_b = _p.lava("prefixo " + ("Zm9vYmFyego" * 40) + " sufixo")
    assert "<blob tipo=base64 bytes=440" in fora_b and fora_b.startswith("prefixo")
    assert fora_b.endswith("sufixo") and "blob" in rel_b["classes"]

    linhas = [f"src/a.py:{i}:achou aqui" for i in range(1, 12)]
    linhas += [f"src/b.py:{i}:achou tambem" for i in range(1, 4)]
    fora_g, rel_g = _p.lava("\n".join(linhas))
    assert "src/a.py  (11 matches)" in fora_g and "+6 matches neste arquivo" in fora_g
    assert "busca" in rel_g["classes"] and "src/b.py" in fora_g

    fora_p, _ = _p.lava("Collecting redis\nDownloading redis.whl\n....... [ 87%]\nok final")
    assert fora_p.strip() == "ok final"

    fora_cap, rel_cap = _p.lava("z" * 10_000, cap=1_000)
    assert "guardrail" in rel_cap["classes"] and len(fora_cap) < 5_000

    fora_env = _p.enxuga_envelope(
        {
            "exit_code": 0,
            "stderr": {"texto": "", "bytes_total": 0},
            "cwd": str(_p.CWD_PADRAO),
            "erro": None,
            "stdout": {"texto": "x"},
        }
    )
    assert "stderr" not in fora_env and "cwd" not in fora_env and "erro" not in fora_env
    assert "stdout" in fora_env


def test_perfil_e_regime_cosmetico(tmp_path):
    s._PERFIS.clear()
    assert s._perfil_verbo("descansar", str(HARNESS_DIR / "bin/descansar")) == {
        "forma": "relatorio",
        "cauda": True,
        "poda": "inteira",
        "poda_atos": (),
    }
    s._PERFIS.clear()
    assert s._perfil_verbo("inexistente", "/nao/existe") == {
        "forma": "listagem",
        "cauda": False,
        "poda": "inteira",
        "poda_atos": (),
    }

    fora, rel = _p.lava(_TRECHOS_VETORIAIS)
    assert "busca" in rel["classes"] and "+3 matches neste arquivo" in fora
    assert "trecho 8" not in fora

    fora_c, rel_c = _p.lava(_TRECHOS_VETORIAIS, cosmetica=True)
    assert set(rel_c["classes"]) <= {"terminal", "branco", "blob"}
    for i in range(1, 9):
        assert f"trecho {i} do top-k" in fora_c
    assert fora_c.index("trecho 1") < fora_c.index("trecho 8")

    molde = "\n".join(f"trecho {i} de 8 - score 0.9{i} - fonte arq 101 secao 3" for i in range(1, 9))
    assert "repeticao" in _p.lava(molde)[1]["classes"]
    fora_m, rel_m = _p.lava(molde, cosmetica=True)
    assert "repeticao" not in rel_m["classes"] and fora_m.count("score") == 8

    sujo = "\x1b[31m[1] fonte\x1b[0m\n\n\n[2] " + ("Zm9vYmFyego" * 40)
    fora_s, rel_s = _p.lava(sujo, cosmetica=True)
    assert "\x1b[" not in fora_s and "\n\n\n" not in fora_s and "<blob tipo=base64" in fora_s
    assert set(rel_s["classes"]) == {"terminal", "branco", "blob"}

    texto = "\n".join(f"[{i}] trecho vetorial numero {i} " + "conteudo " * 30 for i in range(1, 21))
    args = {
        "cap": 2_000,
        "cauda": False,
        "alca": "motor:casa",
        "sessao_id": _UUID_A,
        "giro": 1,
        "tool": "motor",
        "ledger": None,
        "nome_derrame": "g00001-stdout.txt",
    }
    with _derrame_tmp():
        fora_d, meta_d = _p.poda_texto(texto, cosmetica=True, **args)
        hoje, m_hoje = _p.poda_texto(texto, **args)
    assert meta_d["modo"] == "derrame" and meta_d["perfil"] == "cosmetica" and meta_d["alca"]
    assert "[20] trecho vetorial numero 20" in fora_d
    assert "repeticao" in m_hoje["lavado"] and "[20] trecho vetorial numero 20" not in hoje


def test_eixo_poda_cabecalho_e_argv(tmp_path):
    bin_ = HARNESS_DIR / "bin"
    s._PERFIS.clear()
    motor = s._perfil_verbo("motor", str(bin_ / "motor"))
    assert motor["poda"] == "cosmetica" and motor["poda_atos"] == ("rag", "casa", "buscar")
    assert s._cosmetica(motor, "casa") and not s._cosmetica(motor, "listar")
    no_ato = s._argv_verbo("bin/motor", "rag", ["buscar", "obra", "pergunta"])
    no_args = s._argv_verbo("bin/motor", "", ["rag", "buscar", "obra", "pergunta"])
    assert no_ato == no_args
    assert s._ato_efetivo(no_args) == "rag" and s._cosmetica(motor, s._ato_efetivo(no_args))
    assert not s._cosmetica(motor, s._ato_efetivo(s._argv_verbo("bin/motor", "", ["listar"])))
    assert s._ato_efetivo(s._argv_verbo("bin/motor", "", [])) is None

    sint = tmp_path / "sintetico"
    sint.write_text("#!/usr/bin/env python3\n# forma: listagem\n# poda: cosmetica@casa,buscar\n", encoding="utf-8")
    s._PERFIS.clear()
    perfil = s._perfil_verbo("sintetico", str(sint))
    assert perfil["poda"] == "cosmetica" and s._cosmetica(perfil, "casa") and not s._cosmetica(perfil, "listar")

    assert not s._cosmetica(s._perfil_verbo("teste", str(bin_ / "teste")), "rodar")
    assert not s._cosmetica(s._perfil_verbo("repo", str(bin_ / "repo")), "estado")
    assert s._cosmetica(s._perfil_verbo("repo", str(bin_ / "repo")), "git")
    s._PERFIS.clear()


def test_hash_unico_pecas_e_busca():
    assert sha_servido("  abc\n") == sha_servido("abc") == _p.sha_servido("abc")
    assert len(sha_servido("abc")) == 12

    corpo = "TRECHOS DO ACERVO " * 50
    acervo = {"peca": "acervo-consultado", "ref": "verbo:acervo", "conteudo": corpo, "sha": _p.sha_servido(corpo)}
    texto = "TEXTO DA PERSONA " * 50
    persona = {"peca": "persona", "sha": _p.sha_servido(texto), "conteudo": texto}
    with patch.object(s, "redis") as _rmod, patch.object(s, "_superficie", return_value="cli"):
        _rmod.Redis = FakeRedisMemoria()
        r1 = {"pecas": [dict(acervo), dict(persona)]}
        s._delta_pecas(r1, _UUID_A)
        r2 = {"pecas": [dict(acervo), dict(persona)]}
        conta = s._delta_pecas(r2, _UUID_A)
    a2, p2 = r2["pecas"]
    assert a2["conteudo"] is None and a2["regime"] == "ponteiro"
    assert p2["conteudo"] == texto and conta["pecas_dedup"] == 1

    fora_j, rel_j = _p.lava(_JOURNAL)
    assert "busca" not in rel_j["classes"] and "MainPID=737373" in fora_j

    bruto = "procurando…\n" + "\n".join(f"src/a.py:{i}:achou" for i in range(1, 9)) + "\n8 arquivos varridos"
    fora_b, rel_b = _p.lava(bruto)
    assert "busca" in rel_b["classes"]
    assert fora_b.splitlines()[0] == "procurando…" and fora_b.splitlines()[-1] == "8 arquivos varridos"
