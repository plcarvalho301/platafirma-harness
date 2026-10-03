# Tres estados da caixa (decisao do dono, 03/10/2026): nao lida -> pendurada -> tratada.
# `ler` entrega sem XACK; `tratar` e o XACK; `ler --penduradas` le PEL + nao lidas
# sem mover nada. Fake com estado de grupo de verdade (ponteiro e PEL).
import json
import sys
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parents[2] / "bin" / "_fila"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

import streams as fila_streams


def _id(x):
    ms, _, seq = x.partition("-")
    return (int(ms), int(seq or 0))


class StreamRC:
    """Um stream por caixa com um grupo: entradas, ponteiro e PEL."""

    def __init__(self, entradas):
        self.entradas = list(entradas)  # [(tecnico, campos)]
        self.ponteiro = "0-0"
        self.pel = []
        self.acks = []

    def ping(self):
        return True

    def xgroup_create(self, *a, **k):
        return True

    def xlen(self, chave):
        return len(self.entradas)

    def xinfo_groups(self, chave):
        lag = sum(1 for t, _ in self.entradas if _id(t) > _id(self.ponteiro))
        return [{"name": "cadeira", "pending": len(self.pel), "lag": lag,
                 "last-delivered-id": self.ponteiro}]

    def xrange(self, chave, min="-", max="+", count=None):
        def dentro(t):
            if min not in ("-",):
                if min.startswith("("):
                    if _id(t) <= _id(min[1:]):
                        return False
                elif _id(t) < _id(min):
                    return False
            return not (max != "+" and _id(t) > _id(max))
        out = [(t, c) for t, c in self.entradas if dentro(t)]
        return out[:count] if count else out

    def xreadgroup(self, grupo, consumidor, streams, count=None):
        out = []
        for stream in streams:
            novas = [(t, c) for t, c in self.entradas if _id(t) > _id(self.ponteiro)]
            if count:
                novas = novas[:count]
            for t, _ in novas:
                self.pel.append(t)
                self.ponteiro = t
            if novas:
                out.append((stream, novas))
        return out

    def xpending_range(self, chave, grupo, min="-", max="+", count=None, consumername=None):
        return [{"message_id": t} for t in self.pel]

    def xack(self, chave, grupo, *ids):
        n = 0
        for i in ids:
            if i in self.pel:
                self.pel.remove(i)
                self.acks.append(i)
                n += 1
        return n

    def xinfo_consumers(self, chave, grupo):
        return []


def _carta(tecnico, msgid, assunto):
    return (tecnico, {"id": msgid, "de": "ia", "tipo": "pedido", "assunto": assunto,
                      "ref": "", "responde": "", "corpo": "corpo " + assunto})


def _rodar(monkeypatch, capsys, argv, rc, eu="ti"):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ti"})
    monkeypatch.setattr(sys, "argv", ["fila"] + argv)
    monkeypatch.setenv("PF_CADEIRA", eu)
    monkeypatch.setattr(fila_streams, "r_conn", lambda: rc)
    try:
        fila_streams.main()
        code = 0
    except SystemExit as e:
        code = e.code
    return code, capsys.readouterr()


def _rc():
    return StreamRC([_carta("100-1", "20261003T100000-ia", "a"),
                     _carta("100-2", "20261003T110000-ia", "b")])


def test_ler_entrega_sem_ack(monkeypatch, capsys):
    rc = _rc()
    code, cap = _rodar(monkeypatch, capsys, ["ler"], rc)
    assert code == 0
    assert "===MSG 20261003T100000-ia===" in cap.out
    assert rc.acks == []
    assert rc.pel == ["100-1", "100-2"]
    # segunda leitura quente nao reentrega
    _, cap = _rodar(monkeypatch, capsys, ["ler"], rc)
    assert cap.out.strip() == "caixa em dia"


def test_status_separa_novas_de_penduradas(monkeypatch, capsys):
    rc = _rc()
    _, cap = _rodar(monkeypatch, capsys, ["status"], rc)
    assert cap.out == "ti: 2 nova(s) · 2 no historico (7 dias)\n"
    _rodar(monkeypatch, capsys, ["ler"], rc)
    _, cap = _rodar(monkeypatch, capsys, ["status"], rc)
    assert cap.out == "ti: nada novo · 2 pendurada(s) · 2 no historico (7 dias)\n"
    _, cap = _rodar(monkeypatch, capsys, ["status", "--json"], rc)
    item = json.loads(cap.out)[0]
    assert (item["pendentes"], item["penduradas"], item["estado"]) == (0, 2, "em_dia")


def test_tratar_e_o_ack(monkeypatch, capsys):
    rc = _rc()
    _rodar(monkeypatch, capsys, ["ler"], rc)
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia"], rc)
    assert code == 0
    assert cap.out == "20261003T100000-ia: tratada\n"
    assert rc.pel == ["100-2"]
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia"], rc)
    assert code == 0
    assert cap.out == "20261003T100000-ia: ja tratada\n"


def test_tratar_recusa_nao_lida_e_inexistente(monkeypatch, capsys):
    rc = _rc()
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia", "nada-ia"], rc)
    assert code == 1
    assert "20261003T100000-ia: nao lida" in cap.out
    assert "nada-ia: nao existe" in cap.out
    assert rc.acks == []


def test_penduradas_le_pel_e_nao_lidas_sem_mover(monkeypatch, capsys):
    rc = _rc()
    rc.entradas.append(_carta("100-3", "20261003T120000-ia", "c"))
    rc.xreadgroup("cadeira", "ti", {"caixa:ti": ">"}, count=2)  # a e b lidas
    rc.xack("caixa:ti", "cadeira", "100-1")                      # a tratada
    antes = (rc.ponteiro, list(rc.pel))
    code, cap = _rodar(monkeypatch, capsys, ["ler", "--penduradas", "--json"], rc)
    assert code == 0
    saida = json.loads(cap.out)
    por_id = {m["msgid"]: m["estado"] for m in saida}
    assert por_id == {"20261003T110000-ia": "pendurada", "20261003T120000-ia": "nao lida"}
    assert (rc.ponteiro, rc.pel) == antes


def test_penduradas_vazia(monkeypatch, capsys):
    rc = _rc()
    _rodar(monkeypatch, capsys, ["ler"], rc)
    _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia", "20261003T110000-ia"], rc)
    _, cap = _rodar(monkeypatch, capsys, ["ler", "--penduradas"], rc)
    assert cap.out.strip() == "nada pendurado"


def test_sonda_nao_trata(monkeypatch, capsys):
    rc = _rc()
    code, _ = _rodar(monkeypatch, capsys, ["tratar", "x"], rc, eu="sonda")
    assert code == 1
