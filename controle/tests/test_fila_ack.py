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
    """Malha fake multi-caixa com consumer group, PEL, chaves KV, ZSET e SET."""

    def __init__(self, entradas, caixa_padrao="caixa:ti"):
        self.streams = {caixa_padrao: list(entradas)}
        self.caixa_padrao = caixa_padrao
        self.ponteiros = {}
        self.pels = {}
        self.acks = []
        self.kv = {}
        self.sets = {}
        self.zsets = {}
        self._seq = 1000

    @property
    def entradas(self):
        return self.streams.setdefault(self.caixa_padrao, [])

    @property
    def ponteiro(self):
        return self.ponteiros.get(self.caixa_padrao, "0-0")

    @ponteiro.setter
    def ponteiro(self, val):
        self.ponteiros[self.caixa_padrao] = val

    @property
    def pel(self):
        return self.pels.setdefault(self.caixa_padrao, [])

    def ping(self):
        return True

    def xgroup_create(self, *a, **k):
        return True

    def xlen(self, chave):
        return len(self.streams.get(chave, []))

    def xinfo_groups(self, chave):
        ent = self.streams.get(chave, [])
        pont = self.ponteiros.get(chave, "0-0")
        pel = self.pels.get(chave, [])
        lag = sum(1 for t, _ in ent if _id(t) > _id(pont))
        return [{"name": "cadeira", "pending": len(pel), "lag": lag,
                 "last-delivered-id": pont}]

    def xrange(self, chave, min="-", max="+", count=None):
        def dentro(t):
            if min not in ("-",):
                if min.startswith("("):
                    if _id(t) <= _id(min[1:]):
                        return False
                elif _id(t) < _id(min):
                    return False
            return not (max != "+" and _id(t) > _id(max))
        out = [(t, c) for t, c in self.streams.get(chave, []) if dentro(t)]
        return out[:count] if count else out

    def xadd(self, chave, campos):
        self._seq += 1
        tec = f"{self._seq}-0"
        self.streams.setdefault(chave, []).append((tec, dict(campos)))
        return tec

    def xreadgroup(self, grupo, consumidor, streams, count=None):
        out = []
        for stream in streams:
            pont = self.ponteiros.get(stream, "0-0")
            ent = self.streams.get(stream, [])
            novas = [(t, c) for t, c in ent if _id(t) > _id(pont)]
            if count:
                novas = novas[:count]
            pel = self.pels.setdefault(stream, [])
            for t, _ in novas:
                pel.append(t)
                self.ponteiros[stream] = t
            if novas:
                out.append((stream, novas))
        return out

    def xpending_range(self, chave, grupo, min="-", max="+", count=None, consumername=None):
        return [{"message_id": t} for t in self.pels.get(chave, [])]

    def xack(self, chave, grupo, *ids):
        pel = self.pels.setdefault(chave, [])
        n = 0
        for i in ids:
            if i in pel:
                pel.remove(i)
                self.acks.append(i)
                n += 1
        return n

    def xinfo_consumers(self, chave, grupo):
        return []

    def get(self, chave):
        return self.kv.get(chave)

    def set(self, chave, valor, nx=False, ex=None):
        if nx and chave in self.kv:
            return None
        self.kv[chave] = valor
        return True

    def sadd(self, chave, *vals):
        s = self.sets.setdefault(chave, set())
        antes = len(s)
        s.update(vals)
        return len(s) - antes

    def smembers(self, chave):
        return set(self.sets.get(chave, set()))

    def srem(self, chave, *vals):
        s = self.sets.setdefault(chave, set())
        n = 0
        for v in vals:
            if v in s:
                s.remove(v)
                n += 1
        return n

    def zadd(self, chave, mapping):
        z = self.zsets.setdefault(chave, {})
        z.update(mapping)
        return len(mapping)

    def zrange(self, chave, start, end):
        itens = sorted(self.zsets.get(chave, {}).items(), key=lambda kv: kv[1])
        ids = [k for k, _ in itens]
        return ids[start:] if end == -1 else ids[start:end + 1]

    def zremrangebyscore(self, chave, min_s, max_s):
        return 0

    def expire(self, chave, seg):
        return True


def _carta(tecnico, msgid, assunto):
    return (tecnico, {"id": msgid, "de": "ia", "tipo": "pedido", "assunto": assunto,
                      "ref": "", "responde": "", "corpo": "corpo " + assunto})


def _rodar(monkeypatch, capsys, argv, rc, eu="ti", personas=None):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: (personas or {"ti", "ia", "dados"}))
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
    # segunda leitura quente nao reentrega, mas diz a pendencia (#4112): igual ao status
    _, cap = _rodar(monkeypatch, capsys, ["ler"], rc)
    assert cap.out.startswith("nada novo · 2 pendurada(s)")
    assert "===MSG" not in cap.out
    assert rc.pel == ["100-1", "100-2"]


def test_ler_diz_em_dia_so_sem_nova_e_sem_pendurada(monkeypatch, capsys):
    rc = _rc()
    _rodar(monkeypatch, capsys, ["ler"], rc)
    _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia", "20261003T110000-ia"], rc)
    _, cap = _rodar(monkeypatch, capsys, ["ler"], rc)
    assert cap.out.strip() == "caixa em dia"


def test_ler_e_status_dizem_o_mesmo_numero(monkeypatch, capsys):
    rc = _rc()
    _rodar(monkeypatch, capsys, ["ler"], rc)
    rc.xack("caixa:ti", "cadeira", "100-1")
    _, ler = _rodar(monkeypatch, capsys, ["ler"], rc)
    _, status = _rodar(monkeypatch, capsys, ["status"], rc)
    assert "1 pendurada(s)" in ler.out
    assert "1 pendurada(s)" in status.out


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


def test_tratar_aceita_lida_fria_e_recusa_inexistente(monkeypatch, capsys):
    rc = _rc()
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261003T100000-ia", "nada-ia"], rc)
    assert code == 1
    assert "20261003T100000-ia: tratada" in cap.out
    assert "nada-ia: nao existe" in cap.out


def test_tratar_inexistente_sem_cura_de_leitura(monkeypatch, capsys):
    code, cap = _rodar(monkeypatch, capsys, ["tratar", "nada-ia"], _rc())
    assert code == 1
    assert "cura:" not in cap.err


def test_dt_413_ler_tudo_e_tratar_nao_queima_outras_cartas(monkeypatch, capsys):
    rc = StreamRC([
        ("100-1", {"id": "20261003T100000-ia", "de": "ia", "tipo": "pedido",
                   "assunto": "de ia", "ref": "", "responde": "", "corpo": "c1"}),
        ("100-2", {"id": "20261003T110000-dados", "de": "dados", "tipo": "pedido",
                   "assunto": "de dados", "ref": "", "responde": "", "corpo": "c2"}),
    ])
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ti", "ia", "dados"})
    code, cap = _rodar(monkeypatch, capsys, ["ler", "ti", "--tudo", "dados"], rc)
    assert code == 0
    assert "20261003T110000-dados" in cap.out

    code, cap = _rodar(monkeypatch, capsys, ["tratar", "20261003T110000-dados"], rc)
    assert code == 0
    assert "20261003T110000-dados: tratada" in cap.out

    # status e leitura quente nao mostram a ja tratada, e entregam a de ia
    _, st = _rodar(monkeypatch, capsys, ["status"], rc)
    assert "1 nova(s)" in st.out
    _, ler = _rodar(monkeypatch, capsys, ["ler"], rc)
    assert "20261003T100000-ia" in ler.out
    assert "20261003T110000-dados" not in ler.out


def test_dt_188_remetente_rele_enviadas_e_por_id(monkeypatch, capsys):
    import io
    rc = StreamRC([])
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ti", "ia", "dados"})
    monkeypatch.setattr(sys, "stdin", io.StringIO("decisao tomada"))
    code, cap = _rodar(monkeypatch, capsys, ["enviar", "dados", "--tipo", "decisao", "--assunto", "a1"], rc, eu="ti")
    assert code == 0
    mid = cap.out.strip()

    # remetente le via --enviadas e via --id
    code, cap = _rodar(monkeypatch, capsys, ["ler", "--enviadas"], rc, eu="ti")
    assert code == 0 and mid in cap.out and "para: dados" in cap.out
    code, cap = _rodar(monkeypatch, capsys, ["ler", "--id", mid], rc, eu="ti")
    assert code == 0 and mid in cap.out and "decisao tomada" in cap.out

    # terceira cadeira nao le
    code, cap = _rodar(monkeypatch, capsys, ["ler", "--id", mid], rc, eu="ia")
    assert code == 1


def test_dt_336_enviar_responde_trata_original(monkeypatch, capsys):
    import io
    rc = StreamRC([_carta("100-1", "20261003T100000-dados", "pergunta")])
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ti", "dados"})
    _rodar(monkeypatch, capsys, ["ler"], rc, eu="ti")
    assert rc.pel == ["100-1"]

    monkeypatch.setattr(sys, "stdin", io.StringIO("resposta ok"))
    code, cap = _rodar(monkeypatch, capsys,
                       ["enviar", "dados", "--tipo", "resposta", "--assunto", "re", "--responde", "20261003T100000-dados"],
                       rc, eu="ti")
    assert code == 0
    assert rc.pel == []
    assert "responde: 20261003T100000-dados tratada" in cap.err


def test_dt_439_enviar_responde_inexistente_recusa(monkeypatch, capsys):
    import io
    rc = StreamRC([])
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ti", "dados"})
    monkeypatch.setattr(sys, "stdin", io.StringIO("resposta"))
    code, cap = _rodar(monkeypatch, capsys,
                       ["enviar", "dados", "--tipo", "resposta", "--assunto", "re", "--responde", "20261095336-arquiteto"],
                       rc, eu="ti")
    assert code == 1
    assert "20261095336-arquiteto" in cap.err
    assert rc.streams.get("caixa:dados", []) == []


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
