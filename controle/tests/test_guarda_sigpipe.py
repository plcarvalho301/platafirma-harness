"""Guarda de SIGPIPE da suíte (incidente #3274): o pytest nunca morre por escrita em pipe fechado.

Os testes 1 a 3 dependem da ordem em que estão escritos: o primeiro deixa SIGPIPE em SIG_DFL,
como o import de `bin/_acervo/registrar` e o `acervo` de test_bot.py faziam; o segundo e o
terceiro provam que o conftest devolveu SIGPIPE ignorado. Sem o fixture `_sigpipe_ignorado` do
conftest.py o segundo falha e o terceiro mata o processo do pytest (exit 141).

Os testes 4 e 5 fecham a causa de fundo: os scripts de bin/_acervo/* punham SIGPIPE em SIG_DFL
no import, e quem os importava (test_casa_arvore) herdava um processo que morre ao escrever
em pipe fechado. Agora a chamada mora só no `if __name__ == "__main__"` de cada script.
"""
import ast
import signal
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ACERVO = Path(__file__).resolve().parents[2] / "bin" / "_acervo"
SCRIPTS = ["casa", "curar", "entidade", "ferramenta", "listar", "registrar", "stack"]
TODOS = ["_identidade.py"] + SCRIPTS


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


@pytest.mark.parametrize("arq", TODOS)
def test_4_importar_o_arquivo_do_acervo_nao_muda_o_sigpipe_do_chamador(arq):
    codigo = (
        "import importlib.machinery, importlib.util, signal, sys\n"
        "antes = signal.getsignal(signal.SIGPIPE)\n"
        "loader = importlib.machinery.SourceFileLoader('modulo_sob_teste', sys.argv[1])\n"
        "spec = importlib.util.spec_from_loader('modulo_sob_teste', loader)\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "loader.exec_module(mod)\n"
        "assert signal.getsignal(signal.SIGPIPE) == antes, 'o import mudou o SIGPIPE'\n"
    )
    p = subprocess.run([sys.executable, "-c", codigo, str(ACERVO / arq)],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr


def _chamadas_sigpipe(no):
    return [n for n in ast.walk(no)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "signal" and n.args
            and isinstance(n.args[0], ast.Attribute) and n.args[0].attr == "SIGPIPE"]


def _guarda_main(stmt):
    return (isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare)
            and isinstance(stmt.test.left, ast.Name) and stmt.test.left.id == "__name__")


@pytest.mark.parametrize("arq", TODOS)
def test_5_a_chamada_de_sigpipe_so_existe_no_guard_de_execucao_direta(arq):
    arvore = ast.parse((ACERVO / arq).read_text(encoding="utf-8"))
    no_import = [s for s in arvore.body
                 if not _guarda_main(s) and not isinstance(s, (ast.FunctionDef, ast.ClassDef))
                 and _chamadas_sigpipe(s)]
    assert not no_import, f"{arq}: signal(SIGPIPE, ...) no nivel do modulo, executa no import"
    no_guard = [c for s in arvore.body if _guarda_main(s) for c in _chamadas_sigpipe(s)]
    if arq in SCRIPTS:
        assert no_guard, f"{arq}: o script perdeu a saida limpa no `| head`"
