"""Incidente #3236 (arq:0101 §1, regra (c)): chamada sem `sessao_id` não herda a sessão de
outra cadeira. A porta não adivinha: cadeira vazia, e quem recusa é o verbo."""
import os
import sys
from pathlib import Path

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server  # noqa: E402


class _RedisQueNaoDeviaSerLido:
    def get(self, chave):
        raise AssertionError(f"a porta leu {chave!r} para uma chamada sem sessao_id")


def test_sem_sessao_id_nao_resolve_cadeira(monkeypatch):
    monkeypatch.setattr(server, "_rc", lambda: _RedisQueNaoDeviaSerLido())
    server._sessao.set("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")   # outra fita montou antes
    for vazio in (None, "", "-"):
        out = server._sessao_resolve(vazio)
        assert out["cadeira"] == ""
        assert out["sessao_id"] == "-"


def test_nao_ha_mais_sessao_viva_global():
    assert not hasattr(server, "_sessao_viva")
    assert not hasattr(server, "_ULTIMA_SESSAO_ID")
