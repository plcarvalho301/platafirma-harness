"""Contrato de `seg isolacao medir` (ops-server/medir_isolacao.py).

Prova o veredito, nao o host: o host entra por um executor falso que le o argv que a
producao monta (`exec_conta.argv_sob_conta`). O que se garante aqui:
  - tudo conforme -> 0, e cada conta passa por uid, owner, casa, lateral e env;
  - conta que escreve na casa da plataforma -> 1 (a mao unica quebrou);
  - conta que escreve na home de outra -> 1 (lateral);
  - travessia negada pelo sudoers -> 5, e nenhuma linha `ok` para aquela conta;
  - conta inexistente -> 5, nunca 0 (verde por vacuidade);
  - quebra junto com nao medido -> 1 (a quebra manda).
A medicao contra o host real e o proprio ato, no host; nao e deste arquivo.
"""
import sys
from pathlib import Path

REPO_RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_RAIZ / "ops-server"))

import medir_isolacao as mi  # noqa: E402

CONTAS = {"jaiminho": (1003, "/home/jaiminho"), "quinzinho": (1004, "/home/quinzinho")}
UID_PORTA, HOME_PORTA = 1001, "/home/claudinho"
MARCA = "isolacao-teste"


def _separa(argv):
    """argv da producao: <wrapper...> env - K=V ... <cmd...> -> (conta, env, cmd)."""
    conta = argv[argv.index("-u") + 1]
    i = argv.index("env") + 2
    env = {}
    while i < len(argv) and "=" in argv[i] and not argv[i].startswith("/"):
        k, v = argv[i].split("=", 1)
        env[k] = v
        i += 1
    return conta, env, argv[i:]


def executor(casa_gravavel=(), lateral_gravavel=(), travessia_negada=()):
    def rodar(argv, entrada=None):
        conta, env, cmd = _separa(argv)
        if conta in travessia_negada:
            return 1, b"", b"sudo: a password is required"
        prog = cmd[0]
        if prog == "id":
            return 0, str(CONTAS[conta][0]).encode(), b""
        if prog == "bash" and "mkdir" in cmd[2]:
            return 0, b"", b""
        if prog == "stat":
            return 0, str(CONTAS[conta][0]).encode(), b""
        if prog == "rm":
            return 0, b"", b""
        if prog == "touch":
            alvo = cmd[1]
            if alvo.startswith("/casa/") and conta in casa_gravavel:
                return 0, b"", b""
            if alvo.startswith("/home/") and conta in lateral_gravavel:
                return 0, b"", b""
            return 1, b"", b"touch: Permission denied"
        if prog == "bash":
            return 0, ("vazio %s" % env.get("PF_SESSAO", "vazio")).encode(), b""
        return 127, b"", b"comando inesperado"
    return rodar


def _medir(contas, **kw):
    return mi.medir(contas, rodar=executor(**kw), conta_info=CONTAS.get,
                    raiz_casa="/casa", uid_porta=UID_PORTA, home_porta=HOME_PORTA,
                    marca=MARCA)


def test_tudo_conforme_sai_0_e_mede_as_cinco():
    res = _medir(["jaiminho", "quinzinho"])
    assert mi.veredito(res) == 0
    for conta in ("jaiminho", "quinzinho"):
        vistas = {r[2] for r in res if r[1] == conta and r[0] == mi.OK}
        assert vistas == {"uid", "owner", "casa", "lateral", "env"}


def test_conta_que_escreve_na_casa_quebra():
    res = _medir(["jaiminho"], casa_gravavel=("jaiminho",))
    assert mi.veredito(res) == 1
    assert (mi.FALHA, "jaiminho", "casa") in {r[:3] for r in res}


def test_conta_que_escreve_na_home_alheia_quebra():
    res = _medir(["jaiminho", "quinzinho"], lateral_gravavel=("quinzinho",))
    assert mi.veredito(res) == 1
    assert any(r[0] == mi.FALHA and r[1] == "quinzinho" and r[2] == "lateral" for r in res)


def test_travessia_negada_e_incompleta_sem_ok():
    res = _medir(["jaiminho"], travessia_negada=("jaiminho",))
    assert mi.veredito(res) == 5
    assert not [r for r in res if r[1] == "jaiminho" and r[0] == mi.OK]
    assert "sudoers" in res[0][3]


def test_conta_inexistente_nunca_e_verde():
    res = _medir(["fantasma"])
    assert mi.veredito(res) == 5
    assert res == [(mi.NAO_MEDIDO, "fantasma", "conta", "nao existe neste host")]


def test_quebra_manda_sobre_nao_medido():
    res = _medir(["jaiminho", "fantasma"], casa_gravavel=("jaiminho",))
    assert mi.veredito(res) == 1


def test_lista_vazia_nao_e_conforme():
    assert mi.veredito([]) == 5
