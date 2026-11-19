"""Testes da projecao de conta de SO no despacho (story #3007), migrados de ops-server/ (#4348).

Rodam SEM root e sem as dependencias da porta: a logica mora em lib/isolacao/exec_conta.py.
O que exige root (a troca de uid de verdade) nao se testa aqui: e medicao de aceite no host
(`seg isolacao medir`, guardada em test_contrato_seg_isolacao.py).

A conta de destino dos testes e um nome de fixture (`provedor`), nao uma conta da casa.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib" / "isolacao"))

from exec_conta import (  # noqa: E402
    ContaNaoDespachavel,
    argv_escrita,
    argv_sob_conta,
    conta_do_sujeito,
    env_sob_conta,
    erro_de_conta,
)

PORTA = "claudinho"
OUTRA = "provedor"


# --- quem troca de conta e quem nao troca ------------------------------------
def test_sujeito_sem_conta_so_nao_troca():
    """O caso de TODA cadeira. Se este teste cair, a mudanca virou regressao geral."""
    assert conta_do_sujeito({"natureza": "pessoa", "papeis": ["cadeira"]}, PORTA) is None


def test_sujeito_sem_atributos_nao_troca():
    assert conta_do_sujeito(None, PORTA) is None
    assert conta_do_sujeito({}, PORTA) is None


def test_conta_so_vazia_ou_so_espaco_nao_troca():
    assert conta_do_sujeito({"conta_so": ""}, PORTA) is None
    assert conta_do_sujeito({"conta_so": "   "}, PORTA) is None


def test_conta_so_igual_a_da_porta_nao_troca():
    assert conta_do_sujeito({"conta_so": PORTA}, PORTA) is None


def test_conta_so_diferente_troca():
    assert conta_do_sujeito({"conta_so": OUTRA}, PORTA) == OUTRA


# --- o env que atravessa -----------------------------------------------------
def test_env_do_uid_da_porta_nao_atravessa():
    novo = env_sob_conta({"XDG_RUNTIME_DIR": "/run/user/1001",
                          "DOCKER_HOST": "unix:///run/user/1001/docker.sock",
                          "SSH_AUTH_SOCK": "/tmp/ssh-1001/agent",
                          "PATH": "/x"}, OUTRA)
    assert "XDG_RUNTIME_DIR" not in novo
    assert "DOCKER_HOST" not in novo
    assert "SSH_AUTH_SOCK" not in novo


def test_env_reescreve_identidade_e_casa():
    novo = env_sob_conta({"HOME": "/home/claudinho", "USER": PORTA,
                          "LOGNAME": PORTA, "PATH": "/x"}, OUTRA)
    assert novo["HOME"] == f"/home/{OUTRA}"
    assert novo["USER"] == OUTRA and novo["LOGNAME"] == OUTRA


def test_env_troca_o_local_bin_e_preserva_o_ferramental_da_casa():
    novo = env_sob_conta(
        {"PATH": "/opt/platafirma/current/harness/bin:/home/claudinho/.local/bin:/usr/bin"}, OUTRA)
    caminhos = novo["PATH"].split(":")
    assert caminhos[0] == f"/home/{OUTRA}/.local/bin"
    assert "/home/claudinho/.local/bin" not in caminhos, "binario da casa alheia"
    assert "/opt/platafirma/current/harness/bin" in caminhos, "ferramental da plataforma e legivel"


def test_env_home_explicito_vence_o_default():
    novo = env_sob_conta({"PATH": "/x"}, OUTRA, home=f"/srv/pf/{OUTRA}")
    assert novo["HOME"] == f"/srv/pf/{OUTRA}"


def test_pf_sessao_e_pf_ordem_id_atravessam():
    novo = env_sob_conta({"PF_SESSAO": "abc", "PF_ORDEM_ID": "o1", "PATH": "/x"}, OUTRA)
    assert novo["PF_SESSAO"] == "abc" and novo["PF_ORDEM_ID"] == "o1"


# --- o argv que troca de conta ------------------------------------------------
def test_argv_leva_o_wrapper_a_conta_e_o_env_explicito():
    argv = argv_sob_conta(["bash", "-c", "id -u"], OUTRA, {"PF_SESSAO": "abc"})
    assert argv[:5] == ["sudo", "-n", "-u", OUTRA, "--"]
    assert argv[5:7] == ["env", "-"]
    assert "PF_SESSAO=abc" in argv
    assert argv[-3:] == ["bash", "-c", "id -u"]


def test_argv_e_estavel_entre_chamadas():
    env = {"B": "2", "A": "1", "C": "3"}
    assert argv_sob_conta(["id"], OUTRA, env) == argv_sob_conta(["id"], OUTRA, env)


def test_argv_descarta_chave_de_env_invalida():
    argv = argv_sob_conta(["id"], OUTRA, {"A=B": "x", "OK": "1"})
    assert "OK=1" in argv
    assert not any(a.startswith("A=B=") for a in argv)


def test_wrapper_sem_placeholder_e_recusado():
    with pytest.raises(ContaNaoDespachavel):
        argv_sob_conta(["id"], OUTRA, {}, wrapper="sudo -n -u claudinho --")


def test_wrapper_alternativo_e_respeitado():
    argv = argv_sob_conta(["id"], OUTRA, {}, wrapper="runuser -u {conta} --")
    assert argv[:4] == ["runuser", "-u", OUTRA, "--"]


def test_conta_com_metacaractere_ocupa_uma_palavra_so():
    argv = argv_sob_conta(["id"], "pr; rm -rf /", {})
    assert argv[:5] == ["sudo", "-n", "-u", "pr; rm -rf /", "--"]


def test_argv_de_escrita_leva_o_caminho_por_argv_e_nao_no_script():
    argv = argv_escrita("/srv/pf/ops-provider/$(id -u).txt")
    assert argv[:2] == ["bash", "-c"]
    assert argv[-1] == "/srv/pf/ops-provider/$(id -u).txt"
    assert "$(id -u)" not in argv[2], "caminho vazou para dentro do script"


# --- distinguir falha da travessia de falha do comando ------------------------
def test_falha_de_sudoers_e_nomeada_como_tal():
    msg = erro_de_conta(1, b"sudo: a password is required\n")
    assert msg and "sudoers" in msg


def test_nao_autorizado_e_nomeado_como_tal():
    msg = erro_de_conta(1, f"claudinho is not allowed to execute '/bin/bash' as {OUTRA}")
    assert msg and "sudoers" in msg


def test_falha_do_comando_do_sujeito_nao_vira_falha_de_conta():
    assert erro_de_conta(128, b"fatal: not a git repository") is None


def test_sucesso_nunca_e_falha_de_conta():
    assert erro_de_conta(0, b"sudo: a password is required") is None
