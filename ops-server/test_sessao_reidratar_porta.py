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
