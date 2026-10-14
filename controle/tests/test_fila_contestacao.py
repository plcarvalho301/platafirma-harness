# O tipo `contestacao` (card #3532; arq:0124 §3, mecanismo comum; R24 da spec plano-de-controle-face-motor):
# a face contesta um indicador pela caixa da cadeira que o configurou. `--ref` leva o indicador, o corpo leva o
# fundamento, e `fila ler` mostra os dois. Sem armazenamento novo: os campos sao os de toda carta.
import io
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


class CaixaRC:
    """Um stream por caixa com um grupo: o bastante para `enviar` gravar e `ler` entregar."""

    def __init__(self):
        self.entradas = {}   # chave do stream -> [(tecnico, campos)]
        self.ponteiro = {}   # chave do stream -> ultimo id entregue
        self.pel = {}        # chave do stream -> ids entregues e sem ack
        self.reservas = set()
        self._seq = 0

    def ping(self):
        return True

    def set(self, chave, valor, nx=False, ex=None):
        if nx and chave in self.reservas:
            return False
        self.reservas.add(chave)
        return True

    def xgroup_create(self, *a, **k):
        return True

    def xadd(self, chave, campos):
        self._seq += 1
        tecnico = f"{1000 + self._seq}-0"
        self.entradas.setdefault(chave, []).append((tecnico, dict(campos)))
        return tecnico

    def xrange(self, chave, min="-", max="+", count=None):
        return list(self.entradas.get(chave, []))

    def xreadgroup(self, grupo, consumidor, streams, count=None):
        out = []
        for chave in streams:
            ponteiro = self.ponteiro.get(chave, "0-0")
            novas = [(t, c) for t, c in self.entradas.get(chave, []) if _id(t) > _id(ponteiro)]
            for t, _ in novas:
                self.pel.setdefault(chave, []).append(t)
                self.ponteiro[chave] = t
            if novas:
                out.append((chave, novas))
        return out


def _rodar(monkeypatch, capsys, argv, rc, eu, stdin=""):
    monkeypatch.setattr(fila_streams, "personas_validas", lambda: {"ia", "ti"})
    monkeypatch.setattr(sys, "argv", ["fila"] + argv)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    monkeypatch.setenv("PF_CADEIRA", eu)
    monkeypatch.setattr(fila_streams, "r_conn", lambda: rc)
    try:
        fila_streams.main()
        code = 0
    except SystemExit as e:
        code = e.code
    return code, capsys.readouterr()


def _contestar(monkeypatch, capsys, rc, *, ref="taxa-de-cobertura-fraca", fundamento="o piso de 0,342 corta demais"):
    argv = ["enviar", "ia", "--tipo", "contestacao", "--assunto", "contestar a taxa de cobertura fraca"]
    if ref is not None:
        argv += ["--ref", ref]
    return _rodar(monkeypatch, capsys, argv, rc, eu="ti", stdin=fundamento)


def test_contestacao_e_tipo_valido_e_aparece_em_tipos(monkeypatch, capsys):
    assert "contestacao" in fila_streams.TIPOS_VALIDOS
    _, cap = _rodar(monkeypatch, capsys, ["tipos"], CaixaRC(), eu="ti")
    assert "contestacao" in cap.out.split()


def test_enviar_contestacao_grava_na_caixa_da_cadeira(monkeypatch, capsys):
    rc = CaixaRC()
    code, cap = _contestar(monkeypatch, capsys, rc)
    assert code == 0, cap.err
    [(_, campos)] = rc.entradas["caixa:ia"]
    assert campos["tipo"] == "contestacao"
    assert campos["de"] == "ti"
    assert campos["ref"] == "taxa-de-cobertura-fraca"
    assert campos["corpo"] == "o piso de 0,342 corta demais"


def test_ler_mostra_o_indicador_e_o_fundamento(monkeypatch, capsys):
    rc = CaixaRC()
    _contestar(monkeypatch, capsys, rc)
    code, cap = _rodar(monkeypatch, capsys, ["ler"], rc, eu="ia")
    assert code == 0
    assert "tipo: contestacao" in cap.out
    assert "indicador: taxa-de-cobertura-fraca" in cap.out
    assert "fundamento:\no piso de 0,342 corta demais" in cap.out
    assert "ref:" not in cap.out


def test_ler_em_json_leva_ref_e_corpo(monkeypatch, capsys):
    rc = CaixaRC()
    _contestar(monkeypatch, capsys, rc)
    _, cap = _rodar(monkeypatch, capsys, ["ler", "--json"], rc, eu="ia")
    [carta] = json.loads(cap.out)
    assert (carta["tipo"], carta["ref"], carta["corpo"]) == (
        "contestacao", "taxa-de-cobertura-fraca", "o piso de 0,342 corta demais")


def test_contestacao_sem_indicador_sai_2_e_nao_grava(monkeypatch, capsys):
    rc = CaixaRC()
    code, cap = _contestar(monkeypatch, capsys, rc, ref=None)
    assert code == 2
    assert "--ref" in cap.err and "indicador" in cap.err
    assert rc.entradas == {}


def test_contestacao_sem_fundamento_sai_1_e_nao_grava(monkeypatch, capsys):
    rc = CaixaRC()
    code, cap = _contestar(monkeypatch, capsys, rc, fundamento="  \n")
    assert code == 1
    assert "fundamento vazio" in cap.err
    assert rc.entradas == {}


def test_outro_tipo_segue_sem_exigir_ref_e_com_o_rotulo_de_sempre(monkeypatch, capsys):
    rc = CaixaRC()
    code, cap = _rodar(monkeypatch, capsys,
                       ["enviar", "ia", "--tipo", "pedido", "--assunto", "a", "--ref", "#1"], rc,
                       eu="ti", stdin="corpo")
    assert code == 0, cap.err
    _, cap = _rodar(monkeypatch, capsys, ["ler"], rc, eu="ia")
    assert "ref: #1" in cap.out
    assert "indicador:" not in cap.out and "fundamento:" not in cap.out
