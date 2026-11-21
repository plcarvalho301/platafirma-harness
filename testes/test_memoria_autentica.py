"""Testes de autenticação dos clientes do msg-mem pelo armário de chaves (story #4412)."""
from __future__ import annotations

import io
import socket
import sys
import threading
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = HARNESS_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from memoria_de_trabalho import (  # noqa: E402
    SEGREDO_MSG_MEM,
    SenhaIndisponivel,
    kwargs_redis_msg_mem,
    ler_senha_msg_mem,
)
from postura.lousa import Fora, Lousa  # noqa: E402

SENHA_TESTE = "senha-ficticia-harness-4412"


class _ServidorRESPFalso:
    """Servidor RESP2 local que imita Valkey nos modos nopass e com senha."""

    def __init__(self, *, senha_exigida: str | None) -> None:
        self.senha_exigida = senha_exigida
        self.comandos: list[list[str]] = []
        self.hashes: dict[str, dict[str, str]] = {}
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(4)
        self.porta = self._sock.getsockname()[1]
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _ler_cmd(self, leitor: io.BufferedReader) -> list[str] | None:
        cab = leitor.readline()
        if not cab or not cab.startswith(b"*"):
            return None
        n = int(cab[1:-2])
        itens: list[str] = []
        for _ in range(n):
            tam = int(leitor.readline()[1:-2])
            itens.append(leitor.read(tam + 2)[:-2].decode("utf-8"))
        return itens

    def _tratar(self, conn: socket.socket) -> None:
        autenticado = self.senha_exigida is None
        leitor = conn.makefile("rb")
        try:
            while True:
                cmd = self._ler_cmd(leitor)
                if not cmd:
                    break
                self.comandos.append(cmd)
                op = cmd[0].upper()
                if op == "AUTH":
                    if self.senha_exigida is None:
                        if len(cmd) == 3 and cmd[1] == "default":
                            conn.sendall(b"+OK\r\n")
                        else:
                            conn.sendall(
                                b"-ERR AUTH <password> called without any password configured\r\n"
                            )
                    elif len(cmd) == 3 and cmd[1] == "default" and cmd[2] == self.senha_exigida:
                        autenticado = True
                        conn.sendall(b"+OK\r\n")
                    else:
                        conn.sendall(b"-WRONGPASS invalid username-password pair\r\n")
                elif not autenticado:
                    conn.sendall(b"-NOAUTH Authentication required.\r\n")
                elif op == "HSET":
                    self.hashes.setdefault(cmd[1], {})[cmd[2]] = cmd[3]
                    conn.sendall(b":1\r\n")
                elif op == "HGET":
                    val = self.hashes.get(cmd[1], {}).get(cmd[2])
                    if val is None:
                        conn.sendall(b"$-1\r\n")
                    else:
                        bval = val.encode("utf-8")
                        conn.sendall(b"$%d\r\n%s\r\n" % (len(bval), bval))
                elif op == "DEL":
                    apagados = sum(1 for k in cmd[1:] if self.hashes.pop(k, None) is not None)
                    conn.sendall(b":%d\r\n" % apagados)
                else:
                    conn.sendall(b"+OK\r\n")
        finally:
            leitor.close()
            conn.close()

    def _loop(self) -> None:
        self._sock.settimeout(0.2)
        while not self._parar.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._tratar, args=(conn,), daemon=True).start()

    def fechar(self) -> None:
        self._parar.set()
        self._sock.close()


def _montar_instancia(tmp_path: Path, *, senha: str | None = SENHA_TESTE) -> Path:
    inst = tmp_path / "inst"
    (inst / "deploy").mkdir(parents=True)
    (inst / "segredos" / "motor").mkdir(parents=True)
    (inst / "deploy" / "armario-de-chaves.yaml").write_text(
        "versao: 1\n"
        "segredos:\n"
        f"  - nome: {SEGREDO_MSG_MEM}\n"
        "    caminho: segredos/motor/MSG_MEM_SENHA\n"
        "    origem:\n"
        "      tipo: refeito\n"
        "      por: seg-segredo-gerar\n"
        "    leitores:\n"
        "      - porta\n"
        "      - harness\n"
        "      - motor\n",
        encoding="utf-8",
    )
    if senha is not None:
        arq = inst / "segredos" / "motor" / "MSG_MEM_SENHA"
        arq.write_text(senha + "\n", encoding="utf-8")
        arq.chmod(0o600)
    return inst


@pytest.mark.parametrize("senha_servidor", [None, SENHA_TESTE])
def test_lousa_autentica_grava_le_e_apaga(
    tmp_path: Path, senha_servidor: str | None
) -> None:
    inst = _montar_instancia(tmp_path)
    srv = _ServidorRESPFalso(senha_exigida=senha_servidor)
    try:
        lousa = Lousa(host="127.0.0.1", porta=srv.porta, instancia_dir=inst)
        lousa.gravar_campo_sessao("s4412", "chapeu", "back-end")
        assert lousa.ler_campo_sessao("s4412", "chapeu") == "back-end"
        lousa.apagar_tudo("s4412")
        assert srv.comandos[0] == ["AUTH", "default", SENHA_TESTE]
    finally:
        srv.fechar()


def test_lousa_sem_senha_no_armario_cai_em_fora(tmp_path: Path) -> None:
    inst = _montar_instancia(tmp_path, senha=None)
    lousa = Lousa(host="127.0.0.1", porta=6380, instancia_dir=inst)
    with pytest.raises(Fora):
        lousa.ler_campo_sessao("s4412", "chapeu")


def test_kwargs_redis_resolve_usuario_default_e_senha(tmp_path: Path) -> None:
    inst = _montar_instancia(tmp_path)
    assert ler_senha_msg_mem(inst) == SENHA_TESTE
    assert kwargs_redis_msg_mem(inst) == {
        "username": "default",
        "password": SENHA_TESTE,
    }


def test_sem_armario_levanta_senha_indisponivel(tmp_path: Path) -> None:
    with pytest.raises(SenhaIndisponivel):
        ler_senha_msg_mem(tmp_path / "nao-existe")
