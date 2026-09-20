"""Medidor de distancia do Ledger — roda sem o pacote `mcp` (importa so `poda`).

O `_ensaio.py` importa `server`, que importa FastMCP; em bancada sem `mcp` ele nem
coleta. A regua de distancia e logica pura de `poda.Ledger`, e este arquivo a trava
onde quer que o pytest rode.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import poda as _p                                              # noqa: E402

_SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _Fake:
    def __init__(self):
        self.kv, self.h = {}, {}

    def incr(self, k):
        return self.incrby(k, 1)

    def incrby(self, k, n):
        self.kv[k] = int(self.kv.get(k, 0)) + n
        return self.kv[k]

    def get(self, k):
        return self.kv.get(k)

    def expire(self, k, ttl):
        return True

    def hget(self, k, f):
        return self.h.get(k, {}).get(f)

    def hset(self, k, f, v):
        self.h.setdefault(k, {})[f] = v


def _ledger(monkeypatch):
    monkeypatch.setattr(_p, "DERRAME", Path(tempfile.mkdtemp()))
    return _p.Ledger(_Fake(), _SID)


def test_aviso_nao_entregue_nao_empurra_distancia(monkeypatch):
    """Medido no ar em 20/09 (#3092): treze releituras servidas como aviso de 68 bytes
    somavam 30 kB cada, e o ponteiro expirou com ~26 kB entregues de fato."""
    led = _ledger(monkeypatch)
    texto = "linha de arquivo grande\n" * 2_000
    n = len(texto.encode())
    assert led.olha("release:ler poda.py", texto, 1, "release")["ledger"] == "novo"
    assert led.bytes_totais() == n
    vezes = _p.DISTANCIA_MAX_PONTEIRO // n + 2
    for giro in range(2, 2 + vezes):
        assert led.olha("release:ler poda.py", texto, giro, "release")["ledger"] == "igual"
    assert led.bytes_totais() < n + vezes * 200


def test_entrega_real_alem_do_limite_ainda_expira(monkeypatch):
    led = _ledger(monkeypatch)
    texto = "conteudo estavel " * 20
    led.olha("a:a", texto, 1, "a")
    led.olha("b:b", "x" * (_p.DISTANCIA_MAX_PONTEIRO + 1), 2, "b")
    r = led.olha("a:a", texto, 3, "a")
    assert r["ledger"] == "expirado" and r["distancia"] > _p.DISTANCIA_MAX_PONTEIRO


def test_marco_do_envio_nao_conta_a_propria_peca(monkeypatch):
    led = _ledger(monkeypatch)
    texto = "y" * 10_000
    led.olha("a:a", texto, 1, "a")
    r = led.olha("a:a", texto, 2, "a")
    assert r["ledger"] == "igual"
    led.olha("b:b", "z" * (_p.DISTANCIA_MAX_PONTEIRO - 5_000), 3, "b")
    assert led.olha("a:a", texto, 4, "a")["ledger"] == "igual", "abaixo do limite, segue aviso"
