"""Testes da projecao de conta de SO no despacho (story #3007).

Rodam SEM root e sem as dependencias do servidor — e por isso que a logica mora em
`exec_conta.py` e nao inline no `server.py`. O que exige root (a troca de uid de
verdade) nao se testa aqui e nao se finge testar: e medicao de aceite no host, com a
regra de sudoers no lugar.

    python3 -m pytest ops-server/test_exec_conta.py -q
"""
import pytest
from exec_conta import (
    ContaNaoDespachavel,
    argv_sob_conta,
    conta_do_sujeito,
    env_sob_conta,
    erro_de_conta,
)

PORTA = "claudinho"


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
    """Mandar 1001 rodar como 1001 pelo sudo custa um fork e uma dependencia de
    sudoers para nao mudar nada."""
    assert conta_do_sujeito({"conta_so": PORTA}, PORTA) is None


def test_conta_so_diferente_troca():
    assert conta_do_sujeito({"conta_so": "jaiminho"}, PORTA) == "jaiminho"


# --- o env que atravessa -----------------------------------------------------
def test_env_do_uid_da_porta_nao_atravessa():
    """XDG_RUNTIME_DIR e /run/user/1001 modo 0700: herdado, o uid de destino leva
    EACCES em algo que nao pediu."""
    novo = env_sob_conta({"XDG_RUNTIME_DIR": "/run/user/1001",
                          "DOCKER_HOST": "unix:///run/user/1001/docker.sock",
                          "SSH_AUTH_SOCK": "/tmp/ssh-1001/agent",
                          "PATH": "/x"}, "jaiminho")
    assert "XDG_RUNTIME_DIR" not in novo
    assert "DOCKER_HOST" not in novo
    assert "SSH_AUTH_SOCK" not in novo


def test_env_reescreve_identidade_e_casa():
    novo = env_sob_conta({"HOME": "/home/claudinho", "USER": PORTA,
                          "LOGNAME": PORTA, "PATH": "/x"}, "jaiminho")
    assert novo["HOME"] == "/home/jaiminho"
    assert novo["USER"] == "jaiminho" and novo["LOGNAME"] == "jaiminho"


def test_env_troca_o_local_bin_e_preserva_o_ferramental_da_casa():
    novo = env_sob_conta(
        {"PATH": "/home/claudinho/AI/bin:/home/claudinho/.local/bin:/usr/bin"}, "jaiminho")
    caminhos = novo["PATH"].split(":")
    assert caminhos[0] == "/home/jaiminho/.local/bin"
    assert "/home/claudinho/.local/bin" not in caminhos, "binario da casa alheia"
    assert "/home/claudinho/AI/bin" in caminhos, "ferramental da plataforma e legivel"


def test_env_home_explicito_vence_o_default():
    novo = env_sob_conta({"PATH": "/x"}, "jaiminho", home="/srv/pf/jaiminho")
    assert novo["HOME"] == "/srv/pf/jaiminho"


def test_pf_sessao_e_pf_ordem_id_atravessam():
    """A identidade da fita nao e do uid: se ela nao atravessar, a auditoria do outro
    lado perde o join de D (#2902)."""
    novo = env_sob_conta({"PF_SESSAO": "abc", "PF_ORDEM_ID": "o1", "PATH": "/x"}, "jaiminho")
    assert novo["PF_SESSAO"] == "abc" and novo["PF_ORDEM_ID"] == "o1"


# --- o argv que troca de conta ------------------------------------------------
def test_argv_leva_o_wrapper_a_conta_e_o_env_explicito():
    argv = argv_sob_conta(["bash", "-c", "id -u"], "jaiminho", {"PF_SESSAO": "abc"})
    assert argv[:5] == ["sudo", "-n", "-u", "jaiminho", "--"]
    # `env -` zera o herdado: sem ele o env_reset do sudo entregaria o env do sudoers.
    assert argv[5:7] == ["env", "-"]
    assert "PF_SESSAO=abc" in argv
    assert argv[-3:] == ["bash", "-c", "id -u"]


def test_argv_e_estavel_entre_chamadas():
    """Auditoria comparavel: mesmo env, mesmo argv, sempre."""
    env = {"B": "2", "A": "1", "C": "3"}
    assert argv_sob_conta(["id"], "jaiminho", env) == argv_sob_conta(["id"], "jaiminho", env)


def test_argv_descarta_chave_de_env_invalida():
    """Chave com '=' nao existe em env de processo; deixar passar quebraria o `env -`
    com um par que o kernel nunca aceitaria."""
    argv = argv_sob_conta(["id"], "jaiminho", {"A=B": "x", "OK": "1"})
    assert "OK=1" in argv
    assert not any(a.startswith("A=B=") for a in argv)


def test_wrapper_sem_placeholder_e_recusado():
    """O modo de falha que este modulo existe para nao ter: wrapper mal configurado
    executando sob a conta da porta com cara de sucesso."""
    with pytest.raises(ContaNaoDespachavel):
        argv_sob_conta(["id"], "jaiminho", {}, wrapper="sudo -n -u claudinho --")


def test_wrapper_alternativo_e_respeitado():
    """`runuser` e o caminho de quem roda como root; o default nao e, e a troca e env."""
    argv = argv_sob_conta(["id"], "jaiminho", {}, wrapper="runuser -u {conta} --")
    assert argv[:4] == ["runuser", "-u", "jaiminho", "--"]


def test_conta_com_metacaractere_ocupa_uma_palavra_so():
    """Nao ha shell no meio (execve direto), mas ha um `shlex.split` no wrapper e o
    nome vem do PAP, que e editado a mao. O invariante e de ARIDADE: o nome ocupa
    exatamente uma posicao do argv, aconteca o que acontecer com o conteudo dele.
    Partido em duas palavras, `--` deixaria de ser o fim das opcoes do sudo e o resto
    da linha viraria opcao."""
    argv = argv_sob_conta(["id"], "ja; rm -rf /", {})
    assert argv[:5] == ["sudo", "-n", "-u", "ja; rm -rf /", "--"]


# --- distinguir falha da travessia de falha do comando ------------------------
def test_falha_de_sudoers_e_nomeada_como_tal():
    msg = erro_de_conta(1, b"sudo: a password is required\n")
    assert msg and "sudoers" in msg


def test_nao_autorizado_e_nomeado_como_tal():
    msg = erro_de_conta(1, "claudinho is not allowed to execute '/bin/bash' as jaiminho")
    assert msg and "sudoers" in msg


def test_falha_do_comando_do_sujeito_nao_vira_falha_de_conta():
    """`git status` num diretorio que nao e repo sai 128 — e defeito do comando, e
    chamar isso de problema de conta manda o dono procurar no lugar errado."""
    assert erro_de_conta(128, b"fatal: not a git repository") is None


def test_sucesso_nunca_e_falha_de_conta():
    assert erro_de_conta(0, b"sudo: a password is required") is None
