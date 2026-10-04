"""Guarda de SIGPIPE da suíte (incidente #3274): o pytest nunca morre por escrita em pipe fechado.

Os testes abaixo dependem da ordem em que estão escritos: o primeiro deixa SIGPIPE em SIG_DFL,
como o import de `bin/_acervo/registrar` e o `acervo` de test_bot.py faziam; o segundo e o
terceiro provam que o conftest devolveu SIGPIPE ignorado. Sem o fixture `_sigpipe_ignorado` do
conftest.py o segundo falha e o terceiro mata o processo do pytest (exit 141).
"""
import signal
import socket

import pytest


def test_1_um_teste_que_deixa_sigpipe_no_padrao_como_o_import_do_registrar():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    assert signal.getsignal(signal.SIGPIPE) == signal.SIG_DFL


def test_2_o_teste_seguinte_comeca_com_sigpipe_ignorado():
    assert signal.getsignal(signal.SIGPIPE) == signal.SIG_IGN


def test_3_escrita_em_socket_fechado_pelo_outro_lado_da_erro_e_nao_mata_o_pytest():
    a, b = socket.socketpair()
    b.close()
    try:
        with pytest.raises(BrokenPipeError):
            a.send(b"x")
    finally:
        a.close()
