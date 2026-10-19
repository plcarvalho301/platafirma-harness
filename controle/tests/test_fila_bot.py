"""Carta assinada por bot (#3884).

O bot `caderno-poda` (Tito Tesourinha) manda carta a cadeira dona do caderno com o que tombar. Bot nao
tem sessao nem caixa: assina `bot:<slug>`, e so de dentro do proprio `bot rodar <slug>`, que poe o
slug em PF_BOT_SLUGS. Fora dele o remetente e forjado e sai 1. Carta a bot nao existe.
"""
import argparse
import io
import sys
from pathlib import Path

import pytest

BIN_DIR = Path(__file__).resolve().parents[2] / "bin" / "_fila"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

import streams as fila_streams


class _Malha:
    """O que `cmd_enviar_bot` usa da malha: a leitura fria da caixa, a reserva do id e o XADD."""

    def __init__(self):
        self.enviadas = []

    def set(self, chave, valor, nx=False, ex=None):
        return True

    def xadd(self, stream, campos):
        self.enviadas.append((stream, campos))


def _args(de="bot:caderno-poda", destinatario="ia"):
    return argparse.Namespace(de=de, destinatario=destinatario, tipo="pedido",
                              assunto="caderno: 1 lição(ões) a tombar no chapéu", ref=None, responde=None)


@pytest.fixture()
def malha(monkeypatch):
    rc = _Malha()
    monkeypatch.setattr(fila_streams, "frias", lambda rc_, persona: [])
    monkeypatch.setattr(fila_streams, "valida_persona", lambda p: None)
    monkeypatch.setattr(fila_streams, "canoniza_persona", lambda p: p)
    monkeypatch.setattr("sys.stdin", io.StringIO("Sou o Tito Tesourinha...\n"))
    return rc


def test_bot_assina_de_dentro_do_proprio_rodar(malha, monkeypatch, capsys):
    monkeypatch.setenv("PF_BOT_SLUGS", "caderno-poda")
    fila_streams.cmd_enviar_bot(malha, _args())
    stream, campos = malha.enviadas[0]
    assert stream == "caixa:ia"
    assert campos["de"] == "bot:caderno-poda" and campos["tipo"] == "pedido"
    assert campos["id"].endswith("-bot-caderno-poda")
    assert capsys.readouterr().out.strip() == campos["id"]


def test_fora_do_bot_rodar_o_remetente_e_forjado(malha, monkeypatch, capsys):
    monkeypatch.delenv("PF_BOT_SLUGS", raising=False)
    with pytest.raises(SystemExit) as saida:
        fila_streams.cmd_enviar_bot(malha, _args())
    assert saida.value.code == 1
    assert "remetente nao se forja" in capsys.readouterr().err
    assert malha.enviadas == []


def test_outro_bot_nao_assina_por_este(malha, monkeypatch):
    monkeypatch.setenv("PF_BOT_SLUGS", "aresta-balde")
    with pytest.raises(SystemExit):
        fila_streams.cmd_enviar_bot(malha, _args())
    assert malha.enviadas == []


def test_carta_a_bot_recusa_com_a_cura(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["fila", "enviar", "bot:caderno-poda", "--tipo", "resposta",
                                      "--assunto", "ok"])
    with pytest.raises(SystemExit) as saida:
        fila_streams.main()
    assert saida.value.code == 1
    assert "bot nao tem caixa" in capsys.readouterr().err
