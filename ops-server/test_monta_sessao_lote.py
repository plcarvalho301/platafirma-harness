"""Testes de contrato da tool monta_sessao como projeção do lote (spec_sessao §6, #3053).

Aceite coberto:
- abrir ok → expediente recebe os três PF_* em slug puro (assert no env do execve);
- abrir exit 3 → expediente não roda;
- sessao_id portado → ordem_id novo, id igual;
- pergunta chega por stdin.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
PDP_CODE_DIR = HARNESS_DIR / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_abrir_ok_expediente_recebe_tres_pf_em_slug_puro():
    sid = "11111111-2222-3333-4444-555555555555"
    oid = "o20260914T120000-abcdef"
    sub = "user-sub-123"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub,
        "cadeira": "ia",
        "canonizada": True,
        "autorizada_por": "regra@plano",
        "ordem_id": oid,
        "registrada": True,
        "duravel": True,
        "porte": "devolva este sessao_id",
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": None,
        "roteador": {"via": "fallback", "slug": None},
        "pacote": {"pecas": 7, "tokens": 1200},
        "pecas": [{"peca": "conduta", "tokens": 100}],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="comando desconhecido")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub, "sujeito": "claudinho"}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="claudinho-IA", pergunta="iniciar fita")

    # Assert: sessao abrir foi chamado com PF_SUJEITO = sub
    assert len(chamadas_run) == 2
    abrir_call = chamadas_run[0]
    assert "abrir" in abrir_call["argv"]
    # a porta passa a cadeira COMO RECEBEU; canonizar e etapa 3 de `sessao abrir` (spec_sessao §2)
    assert "claudinho-IA" in abrir_call["argv"]
    assert "ia" not in abrir_call["argv"]
    assert abrir_call["kwargs"]["env"]["PF_SUJEITO"] == sub

    # Assert: expediente montar recebeu os três PF_* em slug puro
    exp_call = chamadas_run[1]
    env_exp = exp_call["kwargs"]["env"]
    assert env_exp["PF_CADEIRA"] == "ia", f"esperava slug puro 'ia', recebido: {env_exp['PF_CADEIRA']}"
    assert env_exp["PF_SESSAO"] == sid
    assert env_exp["PF_ORDEM_ID"] == oid

    # Assert: resposta traz bloco sessao no topo
    chaves = list(res.keys())
    assert chaves[0] == "sessao"
    assert res["sessao"]["sessao_id"] == sid
    assert res["pacote"]["pecas"] == 7


@pytest.mark.anyio
async def test_abrir_exit_3_expediente_nao_roda():
    mock_rc = MagicMock()
    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        return subprocess.CompletedProcess(
            argv, returncode=3,
            stdout=json.dumps({"erro": "sem sujeito: a porta não autenticou"}),
            stderr=""
        )

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": None}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", pergunta="qualquer")

    # Apenas o abrir roda; expediente NÃO roda
    assert len(chamadas_run) == 1
    assert "abrir" in chamadas_run[0]["argv"]
    assert res.get("erro") == "sem sujeito: a porta não autenticou"


@pytest.mark.anyio
async def test_sessao_id_portado_ordem_id_novo_id_igual():
    sid_portado = "22222222-3333-4444-5555-666666666666"
    oid_novo = "o20260914T130000-newoid"
    sub = "user-sub-123"

    abrir_out = {
        "sessao_id": sid_portado,
        "cunhada_agora": False,
        "sujeito": sub,
        "cadeira": "ia",
        "canonizada": True,
        "autorizada_por": "regra@plano",
        "ordem_id": oid_novo,
        "registrada": True,
        "duravel": True,
        "porte": "devolva este sessao_id",
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid_portado,
        "ordem_id": oid_novo,
        "chapeu": None,
        "roteador": {"via": "fallback", "slug": None},
        "pacote": {"pecas": 7, "tokens": 1200},
        "pecas": [],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid_novo, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", sessao_id=sid_portado)

    abrir_call = chamadas_run[0]
    assert "--sessao-id" in abrir_call["argv"]
    idx = abrir_call["argv"].index("--sessao-id")
    assert abrir_call["argv"][idx + 1] == sid_portado

    exp_call = chamadas_run[1]
    assert exp_call["kwargs"]["env"]["PF_SESSAO"] == sid_portado
    assert exp_call["kwargs"]["env"]["PF_ORDEM_ID"] == oid_novo

    assert res["sessao_id"] == sid_portado
    assert res["ordem_id"] == oid_novo


@pytest.mark.anyio
async def test_pergunta_chega_por_stdin():
    sid = "33333333-4444-5555-6666-777777777777"
    oid = "o20260914T140000-zzzzzz"
    sub = "user-sub-123"
    pergunta_literal = "Qual é o status da migração de dados?"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub,
        "cadeira": "ia",
        "ordem_id": oid,
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": "contexto",
        "pacote": {"pecas": 7, "tokens": 1000},
        "pecas": [],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", pergunta=pergunta_literal, chapeu="contexto")

    exp_call = chamadas_run[1]
    assert exp_call["kwargs"]["input"] == pergunta_literal
    assert "--pergunta" not in exp_call["argv"]
    assert "--chapeu" in exp_call["argv"]
    assert res["chapeu"] == "contexto"


@pytest.mark.anyio
async def test_prefixo_estavel_marcado_cache_control():
    """Passo 3 (#3067): porta marca prefixo estável (persona+conduta) com cache_control."""
    sid = "44444444-5555-6666-7777-888888888888"
    oid = "o20260914T150000-aaaaaa"
    sub = "user-sub-123"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub,
        "cadeira": "ia",
        "ordem_id": oid,
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": None,
        "pacote": {"pecas": 4, "tokens": 2000},
        "pecas": [
            {"peca": "persona", "sha": "sha_persona", "conteudo": "Conteudo da Persona"},
            {"peca": "conduta", "sha": "sha_conduta", "conteudo": "Conteudo da Conduta"},
            {"peca": "mesa", "sha": "sha_mesa", "conteudo": "Conteudo da Mesa"},
            {"peca": "cadernos", "sha": "sha_cadernos", "conteudo": "Conteudo dos Cadernos"},
        ],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid, "sub": sub})
    mock_rc.hgetall.return_value = {}

    def fake_subprocess_run(argv, *args, **kwargs):
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(abrir_out), stderr="")
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(exp_out), stderr="")
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", pergunta="primeiro turno")

    pecas = res["pecas"]
    p_persona = next(p for p in pecas if p["peca"] == "persona")
    p_conduta = next(p for p in pecas if p["peca"] == "conduta")
    p_mesa = next(p for p in pecas if p["peca"] == "mesa")
    p_cadernos = next(p for p in pecas if p["peca"] == "cadernos")

    # Prefixo estável [persona, conduta] sai marcado cacheável
    assert p_persona["cache_control"] == {"type": "ephemeral"}
    assert p_persona["cacheavel"] is True
    assert p_conduta["cache_control"] == {"type": "ephemeral"}
    assert p_conduta["cacheavel"] is True

    # Demais peças não são marcadas
    assert "cache_control" not in p_mesa
    assert "cache_control" not in p_cadernos


@pytest.mark.anyio
async def test_duas_aberturas_prefixo_byte_identico_e_nao_sofre_dedup():
    """Aceite (#3067): duas aberturas seguidas da mesma cadeira produzem prefixo
    persona+conduta byte-idêntico e marcado cacheável; não sofrem desreferência R2."""
    sid = "55555555-6666-7777-8888-999999999999"
    oid1 = "o20260914T160000-111111"
    oid2 = "o20260914T160000-222222"
    sub = "user-sub-123"

    abrir_out_1 = {"sessao_id": sid, "cunhada_agora": True, "sujeito": sub, "cadeira": "ia", "ordem_id": oid1}
    abrir_out_2 = {"sessao_id": sid, "cunhada_agora": False, "sujeito": sub, "cadeira": "ia", "ordem_id": oid2}

    def make_exp_out(oid):
        return {
            "cadeira": "ia",
            "sessao_id": sid,
            "ordem_id": oid,
            "chapeu": None,
            "pacote": {"pecas": 3, "tokens": 1500},
            "pecas": [
                {"peca": "persona", "sha": "sha_persona_fixo", "conteudo": "Texto imutavel da persona"},
                {"peca": "conduta", "sha": "sha_conduta_fixo", "conteudo": "Texto imutavel da conduta"},
                {"peca": "mesa", "sha": "sha_mesa_1", "conteudo": "Texto mutavel da mesa"},
            ],
            "avisos": [],
        }

    ledger_mem = {}

    class FakeRedis:
        def get(self, key):
            return json.dumps({"cadeira": "ia", "ordem_id": oid1, "sub": sub})
        def set(self, key, val, ex=None):
            pass
        def hgetall(self, key):
            return dict(ledger_mem.get(key, {}))
        def hset(self, key, mapping=None):
            ledger_mem.setdefault(key, {}).update(mapping or {})
        def expire(self, key, ttl):
            pass

    abertura_cont = [0]

    def fake_subprocess_run(argv, *args, **kwargs):
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            abrir_out = abrir_out_1 if abertura_cont[0] == 0 else abrir_out_2
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(abrir_out), stderr="")
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            oid = oid1 if abertura_cont[0] == 0 else oid2
            abertura_cont[0] += 1
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(make_exp_out(oid)), stderr="")
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=FakeRedis()), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res1 = await s.monta_sessao(cadeira="ia", pergunta="primeira abertura")
        res2 = await s.monta_sessao(cadeira="ia", sessao_id=sid)

    pref1 = res1["pecas"][:2]
    pref2 = res2["pecas"][:2]

    # Ambas saem marcadas cache_control
    for p in pref1 + pref2:
        assert p["cache_control"] == {"type": "ephemeral"}
        assert p["cacheavel"] is True

    # Prefixo [persona, conduta] é byte-idêntico
    assert json.dumps(pref1, sort_keys=True) == json.dumps(pref2, sort_keys=True)

    # Balde 1: Conteúdo integral preservado (NÃO substituído por ponteiro de dedup R2)
    assert pref2[0]["conteudo"] == "Texto imutavel da persona"
    assert pref2[1]["conteudo"] == "Texto imutavel da conduta"

    # Balde 3: mesa sai INTEIRA (não sofre dedup R2, nunca ponteiro)
    assert res2["pecas"][2]["conteudo"] == "Texto mutavel da mesa"


@pytest.mark.anyio
async def test_reabrir_sessao_balde_2_ponteiro_e_baldes_1_e_3_inteiros():
    """Aceite (PR #53 / #3065):
    Reabrir a mesma sessão: acervo-consultado e corpo de caderno saem como ponteiro (ref, sha)
    do 2º giro em diante; mesa do chapéu ativo, alias-cadeiras e índice de cadernos saem INTEIROS;
    persona e conduta saem inteiros e byte-idênticos.
    """
    from hash_servido import sha_servido
    sid = "66666666-7777-8888-9999-000000000000"
    oid1 = "o20260914T170000-111111"
    oid2 = "o20260914T170000-222222"
    sub = "user-sub-456"

    txt_persona = "Texto imutavel da persona da fabrica"
    txt_conduta = "Texto imutavel da conduta do dono"
    txt_alias = "Carla Cangurina -> gestao-estrategica"
    txt_mesa = "mesa com 1 item do chapeu devops"
    txt_indice_cadernos = "devops 100 B ha 1 h\n  (corpo sob demanda: `mesa caderno <chapeu>`)"
    txt_acervo = "CONSULTA AO ACERVO: trecho 1, trecho 2"
    txt_corpo_caderno = "===== abertura/fabrica/devops/caderno.md =====\nlicao 1 aprendida"

    sha_persona = sha_servido(txt_persona)
    sha_conduta = sha_servido(txt_conduta)
    sha_alias = sha_servido(txt_alias)
    sha_mesa = sha_servido(txt_mesa)
    sha_indice = sha_servido(txt_indice_cadernos)
    sha_acervo = sha_servido(txt_acervo)
    sha_corpo = sha_servido(txt_corpo_caderno)

    abrir_out_1 = {"sessao_id": sid, "cunhada_agora": True, "sujeito": sub, "cadeira": "fabrica", "ordem_id": oid1}
    abrir_out_2 = {"sessao_id": sid, "cunhada_agora": False, "sujeito": sub, "cadeira": "fabrica", "ordem_id": oid2}

    def make_exp_out(oid):
        return {
            "cadeira": "fabrica",
            "sessao_id": sid,
            "ordem_id": oid,
            "chapeu": "devops",
            "pacote": {"pecas": 7, "tokens": 4000},
            "pecas": [
                {"peca": "persona", "ref": "verbo:persona ler fabrica", "sha": sha_persona, "regime": "valor", "conteudo": txt_persona},
                {"peca": "conduta", "ref": "verbo:persona conduta", "sha": sha_conduta, "regime": "valor", "conteudo": txt_conduta},
                {"peca": "alias-cadeiras", "ref": "verbo:persona foto", "sha": sha_alias, "regime": "valor", "conteudo": txt_alias},
                {"peca": "mesa", "ref": "verbo:mesa ver devops", "sha": sha_mesa, "regime": "valor", "conteudo": txt_mesa},
                {"peca": "cadernos", "ref": "verbo:mesa caderno", "sha": sha_indice, "regime": "valor", "conteudo": txt_indice_cadernos},
                {"peca": "acervo-consultado", "ref": 'verbo:motor rag buscar casa "pergunta"', "sha": sha_acervo, "regime": "valor", "conteudo": txt_acervo},
                {"peca": "caderno", "ref": "verbo:mesa caderno devops", "sha": sha_corpo, "regime": "valor", "conteudo": txt_corpo_caderno},
            ],
            "avisos": [],
        }

    ledger_mem = {}

    class FakeRedis:
        def get(self, key):
            return json.dumps({"cadeira": "fabrica", "ordem_id": oid1, "sub": sub})
        def set(self, key, val, ex=None):
            pass
        def hgetall(self, key):
            return dict(ledger_mem.get(key, {}))
        def hset(self, key, mapping=None):
            ledger_mem.setdefault(key, {}).update(mapping or {})
        def expire(self, key, ttl):
            pass

    abertura_cont = [0]

    def fake_subprocess_run(argv, *args, **kwargs):
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            abrir_out = abrir_out_1 if abertura_cont[0] == 0 else abrir_out_2
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(abrir_out), stderr="")
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            oid = oid1 if abertura_cont[0] == 0 else oid2
            abertura_cont[0] += 1
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(make_exp_out(oid)), stderr="")
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=FakeRedis()), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res1 = await s.monta_sessao(cadeira="fabrica", pergunta="primeira abertura")
        res2 = await s.monta_sessao(cadeira="fabrica", sessao_id=sid)

    pecas1 = {p["peca"]: p for p in res1["pecas"]}
    pecas2 = {p["peca"]: p for p in res2["pecas"]}

    # Balde 1: persona e conduta inteiros e byte-idênticos
    pref1 = res1["pecas"][:2]
    pref2 = res2["pecas"][:2]
    assert json.dumps(pref1, sort_keys=True) == json.dumps(pref2, sort_keys=True)
    assert pecas2["persona"]["conteudo"] == txt_persona
    assert pecas2["conduta"]["conteudo"] == txt_conduta

    # Balde 3: mesa do chapéu ativo, alias-cadeiras e índice de cadernos saem INTEIROS
    assert pecas2["mesa"]["conteudo"] == txt_mesa
    assert pecas2["alias-cadeiras"]["conteudo"] == txt_alias
    assert pecas2["cadernos"]["conteudo"] == txt_indice_cadernos

    # Balde 2: acervo-consultado e corpo de caderno saem como PONTEIRO (ref, sha)
    p_acervo = pecas2["acervo-consultado"]
    assert p_acervo["regime"] == "ponteiro"
    assert p_acervo["sha"] == sha_acervo
    assert p_acervo["ref"] == 'verbo:motor rag buscar casa "pergunta"'
    assert p_acervo["conteudo"] is None

    p_caderno = pecas2["caderno"]
    assert p_caderno["regime"] == "ponteiro"
    assert p_caderno["sha"] == sha_corpo
    assert p_caderno["ref"] == "verbo:mesa caderno devops"
    assert p_caderno["conteudo"] is None


@pytest.mark.anyio
async def test_sha_que_nao_bate_recusa_fail_closed():
    """Aceite (PR #53 / #3065): sha que não bate -> recusa (fail-closed), não serve cego."""
    from hash_servido import sha_servido
    sid = "77777777-8888-9999-0000-111111111111"
    oid = "o20260914T180000-333333"
    sub = "user-sub-789"

    txt_acervo = "Resultado legitimo do acervo"
    sha_falso = "deadbeef1234"  # Não bate com sha_servido(txt_acervo)

    abrir_out = {"sessao_id": sid, "cunhada_agora": True, "sujeito": sub, "cadeira": "fabrica", "ordem_id": oid}
    exp_out = {
        "cadeira": "fabrica",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": None,
        "pacote": {"pecas": 1, "tokens": 500},
        "pecas": [
            {"peca": "acervo-consultado", "ref": "verbo:motor rag buscar", "sha": sha_falso, "conteudo": txt_acervo},
        ],
        "avisos": [],
    }

    class FakeRedis:
        def get(self, key):
            return None
        def set(self, key, val, ex=None):
            pass
        def hgetall(self, key):
            return {}
        def hset(self, key, mapping=None):
            pass
        def expire(self, key, ttl):
            pass

    def fake_subprocess_run(argv, *args, **kwargs):
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(abrir_out), stderr="")
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(exp_out), stderr="")
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=FakeRedis()), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="fabrica", pergunta="teste sha")

    # Recusa declarada (fail-closed), não serve cego
    assert "erro" in res
    assert "fail-closed" in res["erro"]
    p_acervo = res["pecas"][0]
    assert p_acervo["conteudo"] is None
    assert p_acervo["frescor"] == "indisponivel"
    assert p_acervo.get("recusa") == "fail-closed"


@pytest.mark.anyio
async def test_audit_sessao_aberta_sujeito_do_token_e_slug_da_cadeira():
    # Card #3068 Aceite 1: evento=sessao_aberta via=tool tem sujeito = sub do token e cadeira = slug
    sid = "3738e88d-0e55-44dc-b603-63f0c2360c6f"
    oid = "o20260917T015509-2ea343"
    sub_jwt = "e57eadb1-ec5d-41b5-a1be-e6d62196cff5"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub_jwt,
        "cadeira": "fabrica",
        "canonizada": True,
        "autorizada_por": "fornecedor@test",
        "ordem_id": oid,
        "registrada": True,
        "duravel": True,
        "porte": "devolva este sessao_id",
    }
    exp_out = {
        "cadeira": "fabrica",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": "devops",
        "roteador": {"via": "determinístico", "slug": "devops"},
        "pacote": {"pecas": 1, "tokens": 100},
        "pecas": [{"peca": "persona", "tokens": 50}],
        "avisos": [],
    }

    class FakeRedis:
        def get(self, key):
            return None
        def set(self, key, val, ex=None):
            pass

    auditorias = []
    def fake_audit(**kwargs):
        auditorias.append(kwargs)

    def fake_subprocess_run(argv, *args, **kwargs):
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(abrir_out), stderr="")
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=json.dumps(exp_out), stderr="")
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub_jwt, "sujeito": sub_jwt}), \
         patch("server._rc", return_value=FakeRedis()), \
         patch("server._audit", side_effect=fake_audit), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="fabrica", pergunta="Fabrica devops, card 3068")

    assert not res.get("erro")
    chamadas_sessao = [a for a in auditorias if a.get("tool") == "sessao" and a.get("evento") == "sessao_aberta"]
    assert len(chamadas_sessao) == 1
    call = chamadas_sessao[0]
    assert call["sujeito"] == sub_jwt
    assert call["cadeira"] == "fabrica"
    assert call["ordem_id"] == oid
    assert call["sessao_id"] == sid
    assert call["via"] == "tool"



