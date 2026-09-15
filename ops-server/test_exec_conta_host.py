"""Medicao de aceite da story #3007 NO HOST - aqui a troca de uid acontece de verdade.

`test_exec_conta.py` e puro e roda em qualquer maquina; este nao. O que se mede aqui e
o aceite que o README enuncia: o comando do sujeito sai sob o uid da conta, e o arquivo
que ele escreve NASCE com o owner dela. Exige os dois atos de root do dono - a regra de
sudoers e uma raiz gravavel pela conta. Faltando qualquer um, os casos PULAM com o
motivo em vez de passar vazios: teste verde por vacuidade e a aparencia do aceite sem o
aceite, e some do radar por parecer ativo.

    PF_CONTA_TESTE=jaiminho PF_RAIZ_CONTA_TESTE=/srv/pf/ops-provider \
        python3 -m pytest ops-server/test_exec_conta_host.py -q
"""
import os
import pwd
import subprocess

import pytest

from exec_conta import argv_escrita, argv_sob_conta, env_sob_conta, erro_de_conta

CONTA = os.environ.get("PF_CONTA_TESTE", "jaiminho")
RAIZ_CONTA = os.environ.get("PF_RAIZ_CONTA_TESTE", "/srv/pf/ops-provider")
RAIZ_PORTA = os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa")

# Env de uma chamada da porta: um caminho que so o uid dela alcanca (XDG_RUNTIME_DIR,
# modo 0700) e a identidade da fita, que precisa atravessar (#2902).
ENV_PORTA = {"PATH": "/usr/bin:/bin", "PF_SESSAO": "teste-3007",
             "XDG_RUNTIME_DIR": "/run/user/%d" % os.getuid()}


def _roda(argv, entrada=None):
    return subprocess.run(argv, input=entrada, capture_output=True, timeout=30,
                          check=False)


@pytest.fixture(scope="module")
def travessia():
    """Uid da conta e env que atravessa - ou skip do modulo com o motivo do host."""
    try:
        uid = pwd.getpwnam(CONTA).pw_uid
    except KeyError:
        pytest.skip("conta %r nao existe neste host" % CONTA)
    env = env_sob_conta(ENV_PORTA, CONTA)
    cp = _roda(argv_sob_conta(["bash", "-c", "id -u"], CONTA, env))
    if cp.returncode != 0:
        motivo = (erro_de_conta(cp.returncode, cp.stderr)
                  or cp.stderr.decode("utf-8", "replace"))
        pytest.skip("travessia indisponivel: %s" % motivo.strip()[:200])
    return {"uid": uid, "env": env}


def test_comando_do_sujeito_sai_sob_o_uid_da_conta(travessia):
    """Aceite 1: do outro lado da travessia, `id -u` e o uid da conta, nao o da porta."""
    cp = _roda(argv_sob_conta(["bash", "-c", "id -u"], CONTA, travessia["env"]))
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.decode().strip() == str(travessia["uid"])
    assert travessia["uid"] != os.getuid(), "conta de teste e a propria porta"


def test_write_nasce_com_o_owner_da_conta(travessia):
    """Aceite 2, e o que de fato isola: o owner NO DISCO, nao o uid de quem executou.

    Quem le o owner e a propria conta (`stat` do outro lado), porque a raiz do provider
    e 0750 dela - a porta nem lista o diretorio, e essa e a propriedade desejada.
    Usa `argv_escrita`, o mesmo argv do `_write_sob_conta` do server: mudando a forma
    de escrever em producao, este teste passa a medir outra coisa e cai junto.
    """
    dir_alvo = "%s/aceite-3007" % RAIZ_CONTA
    alvo = "%s/%d.txt" % (dir_alvo, os.getpid())
    cp = _roda(argv_sob_conta(argv_escrita(alvo), CONTA, travessia["env"]),
               entrada=b"medicao de aceite #3007\n")
    if cp.returncode != 0:
        motivo = (erro_de_conta(cp.returncode, cp.stderr)
                  or cp.stderr.decode("utf-8", "replace"))
        pytest.skip("raiz %r nao gravavel pela conta: %s" % (RAIZ_CONTA,
                                                            motivo.strip()[:200]))
    try:
        dono = _roda(argv_sob_conta(["stat", "-c", "%u", alvo], CONTA, travessia["env"]))
        assert dono.returncode == 0, dono.stderr
        assert dono.stdout.decode().strip() == str(travessia["uid"])
    finally:
        _roda(argv_sob_conta(["rm", "-rf", dir_alvo], CONTA, travessia["env"]))


def test_a_casa_da_plataforma_nao_e_gravavel_pela_conta(travessia):
    """O isolamento e de MAO UNICA, e e por isso que ele vale.

    A plataforma alcanca a conta (os casos acima); a conta nao alcanca a casa da
    plataforma. Se este caso ficar verde ao contrario - o write passando -, o
    isolamento no disco sumiu, e some calado: tudo continua funcionando.
    """
    alvo = "%s/.probe-3007-%d" % (RAIZ_PORTA, os.getpid())
    cp = _roda(argv_sob_conta(["touch", alvo], CONTA, travessia["env"]))
    assert cp.returncode != 0, "a conta %s escreveu em %s" % (CONTA, RAIZ_PORTA)
    assert not os.path.exists(alvo)


def test_env_da_porta_nao_atravessa_e_o_da_fita_atravessa(travessia):
    """A escolha 3 do modulo, medida no host: `sudo` roda com `env_reset`, entao o que
    chega do outro lado e o que esta no argv - nem mais (XDG_RUNTIME_DIR do uid da
    porta, que daria EACCES) nem menos (PF_SESSAO, sem o qual a auditoria do outro lado
    perde o join da fita)."""
    cp = _roda(argv_sob_conta(
        ["bash", "-c", 'echo "${XDG_RUNTIME_DIR:-vazio} ${PF_SESSAO:-vazio}"'],
        CONTA, travessia["env"]))
    assert cp.returncode == 0, cp.stderr
    xdg, sessao = cp.stdout.decode().split()
    assert xdg == "vazio", "runtime dir do uid da porta atravessou"
    assert sessao == "teste-3007"
