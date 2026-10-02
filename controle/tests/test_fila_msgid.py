"""Id da carta unico por carta (#2856 linha 79).

Varios `fila enviar` da mesma remetente no mesmo segundo, para caixas diferentes, devolviam o mesmo
id: `gerar_msgid` so olhava a caixa do destino. Agora, com a conexao, reserva o id por `SET NX`.
"""
import sys
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parents[2] / "bin" / "_fila"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

import streams as fila_streams


class _Reserva:
    """So o SET NX que reserva o id, como o redis o responde: True ao reservar, None se ja existe."""

    def __init__(self):
        self.chaves = {}

    def set(self, chave, valor, nx=False, ex=None):
        if nx and chave in self.chaves:
            return None
        self.chaves[chave] = valor
        return True


def test_msgid_nao_repete_entre_caixas_diferentes_no_mesmo_segundo():
    rc = _Reserva()
    ids = [fila_streams.gerar_msgid("engenharia", set(), rc) for _ in range(3)]
    assert len(set(ids)) == 3
    assert all(i.endswith("-engenharia") for i in ids)
    assert len(rc.chaves) == 3


def test_msgid_sem_reserva_segue_so_pela_caixa_do_destino():
    primeiro = fila_streams.gerar_msgid("ti", set())
    segundo = fila_streams.gerar_msgid("ti", {primeiro})
    assert segundo != primeiro
