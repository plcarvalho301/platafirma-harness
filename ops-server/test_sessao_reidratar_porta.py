"""Reidratação de `sessao:{id}` do lado da PORTA (card #3145, Onda 1 Frente E).

A porta roda no venv ops (sem driver de banco -- mesma razão de
bin/_sessao/giro-carga.py) e por isso nunca fala com o Postgres direto: quando
`sessao:{id}` falta do msg-mem, delega ao módulo comum (bin/_sessao/reidratar.py,
`reidratar_via_verbo`), que por sua vez chama o verbo `sessao ver --json`.

Cobre (item 6 do card): "a porta usa a mesma função" -- `_sessao_resolve` e o passo
(b) de `_montar` chamam `_reidratar_porta`, que delega ao módulo comum; "import
quebrado na porta -> comportamento atual" -- ajudante ausente não derruba a porta,
cadeira fica vazia como hoje.

Vive em ops-server/ (não em controle/tests/) porque server.py precisa do venv com
`mcp` (controle/tests/test_lote_encadeado.py já documenta essa fronteira).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-reidratar-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import server as s  # noqa: E402


def test_sessao_resolve_ausente_usa_reidratar_porta():
    """`_sessao_resolve`: sessao:{id} ausente do msg-mem -> chama `_reidratar_porta`,
    que delega ao módulo comum (`reidratar_via_verbo`) -- "a porta usa a mesma
    função"."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = None  # sessao:{id} ausente

    fake_mod = MagicMock()
    fake_mod.reidratar_via_verbo.return_value = {"cadeira": "ia", "ordem_id": "o-reidratado"}

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", fake_mod):
        out = s._sessao_resolve(sid)

    assert out["cadeira"] == "ia"
    assert out["ordem_id"] == "o-reidratado"
    fake_mod.reidratar_via_verbo.assert_called_once()
    argv_chamado = fake_mod.reidratar_via_verbo.call_args[0]
    assert argv_chamado[0] == sid


def test_sessao_resolve_chave_presente_nao_reidrata():
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = '{"cadeira": "produto", "ordem_id": "o1"}'

    fake_mod = MagicMock()

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", fake_mod):
        out = s._sessao_resolve(sid)

    assert out["cadeira"] == "produto"
    fake_mod.reidratar_via_verbo.assert_not_called()


def test_sessao_resolve_import_quebrado_mantem_comportamento_atual():
    """Ajudante ausente (`_reidratar_mod is None`, como se o import lá no topo tivesse
    falhado): `_sessao_resolve` não trava, cadeira fica vazia -- exatamente o
    comportamento de antes desta fita."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = None

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", None):
        out = s._sessao_resolve(sid)

    assert out["cadeira"] == ""
    assert out["ordem_id"] == "-"
    assert out["sessao_id"] == sid


def test_reidratar_porta_devolve_none_sem_ajudante():
    with patch.object(s, "_reidratar_mod", None):
        assert s._reidratar_porta("qualquer-sid") is None


def test_reidratar_porta_propaga_excecao_como_none_e_loga(capsys):
    fake_mod = MagicMock()
    fake_mod.reidratar_via_verbo.side_effect = RuntimeError("boom")
    with patch.object(s, "_reidratar_mod", fake_mod):
        assert s._reidratar_porta("qualquer-sid") is None
    assert "reidratar" in capsys.readouterr().err


# ---------------------------------------------------------------- PF_SUJEITO no execve (card #3145)
# Contrato item 2 (#3053) estendido pelo card #3145: todo execve de verbo injeta
# PF_SUJEITO quando o registro da sessao o tem -- mesmo ponto onde PF_CADEIRA ja entra
# (_run_verbo_blocking), sem fallback para cadeira/USER/valor fixo (decisao 9).

def test_sessao_resolve_traz_sujeito_da_chave_viva():
    """`sessao:{id}` presente no msg-mem, com `sujeito` gravado na cunhagem
    (bin/sessao::ato_abrir): `_sessao_resolve` devolve o mesmo valor."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = '{"cadeira": "ti", "ordem_id": "o1", "sujeito": "jose-123"}'

    with patch.object(s, "_rc", return_value=mock_rc):
        out = s._sessao_resolve(sid)

    assert out["sujeito"] == "jose-123"


def test_sessao_resolve_sem_sujeito_no_registro_devolve_vazio():
    """Registro sem a chave `sujeito` (sessao antiga, ou sonda sem sujeito): string
    vazia -- nunca fallback para cadeira/USER/valor fixo (decisao 9 do card #3145)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = '{"cadeira": "ti", "ordem_id": "o1"}'

    with patch.object(s, "_rc", return_value=mock_rc):
        out = s._sessao_resolve(sid)

    assert out["sujeito"] == ""


def test_sessao_resolve_reidratada_traz_sujeito():
    """`sessao:{id}` ausente -> reidrata via `_reidratar_porta`; quando o registro
    duravel tem sujeito (migracao 0094), a reidratacao o devolve tambem -- "sessao
    reidratada traz o sujeito" (item 4 do card #3145)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = None  # sessao:{id} ausente

    fake_mod = MagicMock()
    fake_mod.reidratar_via_verbo.return_value = {
        "cadeira": "ia", "ordem_id": "o-reidratado", "sujeito": "jose-123"}

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", fake_mod):
        out = s._sessao_resolve(sid)

    assert out["cadeira"] == "ia"
    assert out["sujeito"] == "jose-123"


def test_sessao_resolve_reidratada_sem_sujeito_devolve_vazio():
    """Reidratacao de uma linha gravada antes da migracao 0094 (sem a coluna
    `sujeito`): `_reidratar_mod.reidratar_via_verbo` nao devolve a chave -- porta nao
    fabrica valor nenhum."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = None

    fake_mod = MagicMock()
    fake_mod.reidratar_via_verbo.return_value = {"cadeira": "ia", "ordem_id": "o-reidratado"}

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", fake_mod):
        out = s._sessao_resolve(sid)

    assert out["sujeito"] == ""


class _ProcessoFake:
    """Dublê de `subprocess.Popen`: comunica vazio e sai 0, sem tocar processo real."""

    returncode = 0

    def communicate(self, input=None, timeout=None):
        return b"", b""


def test_run_verbo_blocking_injeta_pf_sujeito_da_sessao():
    """O env do execve do verbo despachado traz PF_SUJEITO igual ao da sessao -- mesmo
    ponto onde PF_CADEIRA já entra (item 4 do card #3145)."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": "ti", "sujeito": "jose-123"}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert capturado["env"]["PF_SUJEITO"] == "jose-123"
    assert capturado["env"]["PF_CADEIRA"] == "ti"


def test_run_verbo_blocking_sem_sujeito_nao_injeta_variavel():
    """Sessão sem sujeito no registro: PF_SUJEITO simplesmente não entra no ambiente
    do verbo -- nunca fallback para cadeira/USER/valor fixo (decisão 9)."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": "ti", "sujeito": ""}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert "PF_SUJEITO" not in capturado["env"]
    assert capturado["env"]["PF_CADEIRA"] == "ti"


def test_run_verbo_blocking_sem_chave_sujeito_no_ident_nao_quebra():
    """`ident` sem a chave `sujeito` (defensivo -- todo `_sessao_resolve` real a traz,
    mas `_run_verbo_blocking` nao pode cair se algum chamador futuro nao trouxer):
    `.get("sujeito")` nunca estoura KeyError."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": ""}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert "PF_SUJEITO" not in capturado["env"]


# ---------------------------------------------------------------- PF_CHAPEU no execve (card #3367)

def test_sessao_resolve_traz_chapeu_da_chave_viva():
    """`sessao:{id}` presente no msg-mem, com `chapeu` gravado: `_sessao_resolve` devolve o valor (#3367)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = '{"cadeira": "ia", "ordem_id": "o1", "chapeu": "engenharia-de-harness"}'

    with patch.object(s, "_rc", return_value=mock_rc):
        out = s._sessao_resolve(sid)

    assert out["chapeu"] == "engenharia-de-harness"


def test_sessao_resolve_sem_chapeu_no_registro_devolve_vazio():
    """Registro sem a chave `chapeu`: string vazia (#3367)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = '{"cadeira": "ia", "ordem_id": "o1"}'

    with patch.object(s, "_rc", return_value=mock_rc):
        out = s._sessao_resolve(sid)

    assert out["chapeu"] == ""


def test_sessao_resolve_reidratada_traz_chapeu():
    """`sessao:{id}` ausente -> reidrata via `_reidratar_porta`; quando o registro durável
    tem `chapeu`, a reidratação o devolve (#3367)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = None

    fake_mod = MagicMock()
    fake_mod.reidratar_via_verbo.return_value = {
        "cadeira": "ia", "ordem_id": "o-reidratado", "chapeu": "contexto"}

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s, "_reidratar_mod", fake_mod):
        out = s._sessao_resolve(sid)

    assert out["chapeu"] == "contexto"


def test_run_verbo_blocking_injeta_pf_chapeu_da_sessao():
    """O env do execve do verbo despachado traz PF_CHAPEU igual ao da sessao (#3367)."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": "ia", "chapeu": "engenharia-de-harness"}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert capturado["env"]["PF_CHAPEU"] == "engenharia-de-harness"
    assert capturado["env"]["PF_CADEIRA"] == "ia"


def test_run_verbo_blocking_sem_chapeu_nao_injeta_variavel():
    """Sessão sem chapéu no registro: PF_CHAPEU simplesmente não entra no ambiente do verbo (#3367)."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": "ia", "chapeu": ""}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert "PF_CHAPEU" not in capturado["env"]
    assert capturado["env"]["PF_CADEIRA"] == "ia"


def test_run_verbo_blocking_sem_chave_chapeu_no_ident_nao_quebra():
    """`ident` sem a chave `chapeu`: .get("chapeu") nunca estoura KeyError (#3367)."""
    ident = {"sessao_id": "sid-1", "ordem_id": "o-1", "cadeira": "ia"}
    capturado = {}

    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert "PF_CHAPEU" not in capturado["env"]


# ---------------------------------------------------------------- card #3385: chapéu da sessão, fallback e troca

def test_abertura_em_fallback_grava_chave_com_fallback_true_e_sem_chapeu():
    """(a) abertura em fallback → chave com `fallback: true` e sem `chapeu` (#3385)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": "o1", "sujeito": "s1"})

    proc_abrir = MagicMock(returncode=0, stdout=json.dumps({"sessao_id": sid, "ordem_id": "o1", "cadeira": "ia"}), stderr="")
    proc_exp = MagicMock(returncode=0, stdout=json.dumps({
        "roteador": {"via": "fallback", "slug": None},
        "chapeu": None,
        "pecas": [],
    }), stderr="")

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s.subprocess, "run", side_effect=[proc_abrir, proc_exp]):
        res = s._montar("ia", False, "", "oi", sid, "s1")

    assert res.get("chapeu") is None
    mock_rc.set.assert_called_once()
    chave, raw = mock_rc.set.call_args[0]
    assert chave == f"sessao:{sid}"
    dados = json.loads(raw)
    assert dados["fallback"] is True
    assert "chapeu" not in dados
    assert mock_rc.set.call_args[1].get("keepttl") is True


def test_abertura_com_chapeu_grava_chapeu_e_fallback_false():
    """(b) abertura com `chapeu=` → `chapeu` e `fallback: false` (#3385)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": "o1", "sujeito": "s1"})

    proc_abrir = MagicMock(returncode=0, stdout=json.dumps({"sessao_id": sid, "ordem_id": "o1", "cadeira": "ia"}), stderr="")
    proc_exp = MagicMock(returncode=0, stdout=json.dumps({
        "roteador": {"via": "comando", "slug": "engenharia-de-harness"},
        "chapeu": "engenharia-de-harness",
        "pecas": [],
    }), stderr="")

    with patch.object(s, "_rc", return_value=mock_rc), \
         patch.object(s.subprocess, "run", side_effect=[proc_abrir, proc_exp]):
        res = s._montar("ia", False, "harness", "oi", sid, "s1")

    assert res.get("chapeu") == "engenharia-de-harness"
    mock_rc.set.assert_called_once()
    chave, raw = mock_rc.set.call_args[0]
    assert chave == f"sessao:{sid}"
    dados = json.loads(raw)
    assert dados["fallback"] is False
    assert dados["chapeu"] == "engenharia-de-harness"
    assert mock_rc.set.call_args[1].get("keepttl") is True


def test_chapeu_do_giro_troca_grava_chapeu_e_preserva_fallback():
    """(c) giro `persona ler <cadeira da sessão> --chapeu X` exit 0 → `chapeu: X`, `fallback` inalterado (#3385)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": "o1", "fallback": True})

    ident = {"sessao_id": sid, "cadeira": "ia", "ordem_id": "o1"}
    with patch.object(s, "_rc", return_value=mock_rc):
        s._chapeu_do_giro("persona", "ler", ["ia", "--chapeu", "contexto"], {"exit_code": 0}, ident)

    mock_rc.set.assert_called_once()
    chave, raw = mock_rc.set.call_args[0]
    assert chave == f"sessao:{sid}"
    dados = json.loads(raw)
    assert dados["chapeu"] == "contexto"
    assert dados["fallback"] is True
    assert mock_rc.set.call_args[1].get("keepttl") is True
    assert ident["chapeu"] == "contexto"


def test_chapeu_do_giro_outra_cadeira_ou_exit_diferente_de_zero_mantem_chave_intacta():
    """(d) `persona ler` de outra cadeira, ou exit ≠ 0 → chave intacta (#3385)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": "o1", "fallback": True})

    ident = {"sessao_id": sid, "cadeira": "ia", "ordem_id": "o1"}
    with patch.object(s, "_rc", return_value=mock_rc):
        # 1. Outra cadeira ("ti" em vez de "ia")
        s._chapeu_do_giro("persona", "ler", ["ti", "--chapeu", "infra"], {"exit_code": 0}, ident)
        # 2. Exit code diferente de 0
        s._chapeu_do_giro("persona", "ler", ["ia", "--chapeu", "contexto"], {"exit_code": 1}, ident)
        # 3. Tool diferente de "persona"
        s._chapeu_do_giro("repo", "ler", ["ia", "--chapeu", "contexto"], {"exit_code": 0}, ident)
        # 4. Ato diferente de "ler"
        s._chapeu_do_giro("persona", "foto", ["ia", "--chapeu", "contexto"], {"exit_code": 0}, ident)
        # 5. Sem --chapeu
        s._chapeu_do_giro("persona", "ler", ["ia"], {"exit_code": 0}, ident)

    mock_rc.set.assert_not_called()


def test_verbo_seguinte_a_troca_de_chapeu_recebe_pf_chapeu():
    """(e) o verbo seguinte ao (c) recebe PF_CHAPEU=X (#3385)."""
    sid = "11111111-2222-3333-4444-555555555555"
    mock_rc = MagicMock()
    # Simula a chave viva já com "chapeu": "contexto" após o giro de troca (c)
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": "o1", "chapeu": "contexto", "fallback": True})

    with patch.object(s, "_rc", return_value=mock_rc):
        ident = s._sessao_resolve(sid)

    assert ident["chapeu"] == "contexto"

    capturado = {}
    def fake_popen(argv, **kw):
        capturado["env"] = kw.get("env")
        return _ProcessoFake()

    with patch.object(s.subprocess, "Popen", side_effect=fake_popen):
        r = s._run_verbo_blocking(["/bin/infra", "up"], None, 5, ident)

    assert r["exit_code"] == 0
    assert capturado["env"]["PF_CHAPEU"] == "contexto"
    assert capturado["env"]["PF_CADEIRA"] == "ia"
