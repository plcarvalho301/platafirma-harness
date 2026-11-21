# componente: componente:verbo-sessao
"""Interoperabilidade de `sessao:<id>` como hash no Valkey (story #4343, T1).

Prova que `porta.sessao_mem.RepositorioSessaoValkey`, `bin/sessao`, `bin/_sessao/reidratar.py`
e `lib/postura/lousa.py` gravam e leem a mesma chave `sessao:<id>` como hash no Valkey,
sem WRONGTYPE, preservando escritas concorrentes de campos distintos (`turno` e `chapeu`)
e reutilizando um único pool de conexões.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import socketserver
import sys
import threading
import types
import uuid

import pytest

_HARNESS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _HARNESS_DIR / "lib"
_CANDIDATOS_CORE = (
    Path("/opt/platafirma/current/core"),
)
_CORE_DIR = next((c for c in _CANDIDATOS_CORE if (c / "porta" / "sessao_mem.py").is_file()), None)

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
if _CORE_DIR is not None and str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

try:
    from porta.sessao_mem import RepositorioSessaoValkey  # noqa: E402
except ModuleNotFoundError:
    import redis as _redis_mod

    class _PoolLocal:
        def __init__(self, cliente: _redis_mod.Redis) -> None:
            self._cli = cliente

        def executar(self, comandos: list[tuple]) -> list:
            return [self._cli.execute_command(*cmd) for cmd in comandos]

    class RepositorioSessaoValkey:  # type: ignore[no-redef]
        """Fallback local sobre redis.Redis (pool único) quando platafirma-core não está ao lado."""

        def __init__(self, host: str = "127.0.0.1", porta: int = 6380, timeout_s: float = 2.0) -> None:
            self._conn_pool = _redis_mod.BlockingConnectionPool(
                host=host, port=porta, max_connections=1, timeout=timeout_s,
                decode_responses=True, socket_timeout=timeout_s,
                protocol=2, lib_name=None, lib_version=None,
            )
            self._cli = _redis_mod.Redis(connection_pool=self._conn_pool)
            self.pool = _PoolLocal(self._cli)

        @property
        def conexoes_abertas(self) -> int:
            conns = getattr(self._conn_pool, "_connections", None)
            if conns is not None:
                return len(conns)
            return len(getattr(self._conn_pool, "_available_connections", [])) + len(
                getattr(self._conn_pool, "_in_use_connections", [])
            )

        def ler_sessao(self, sid: str) -> dict | None:
            bruto = self._cli.hgetall(f"sessao:{sid}")
            if not bruto:
                return None
            out = dict(bruto)
            if "canonizada" in out:
                out["canonizada"] = out["canonizada"] == "true"
            return out

        def ler_campo(self, sid: str, campo: str) -> str | None:
            return self._cli.hget(f"sessao:{sid}", campo)

        def gravar_campo(self, sid: str, campo: str, valor: str) -> None:
            self._cli.hset(f"sessao:{sid}", campo, valor)

        def gravar_campos(self, sid: str, campos: dict[str, str], ttl_s: int = 3600) -> None:
            self._cli.hset(f"sessao:{sid}", mapping=campos)
            self._cli.expire(f"sessao:{sid}", ttl_s)

        def fechar(self) -> None:
            self._conn_pool.disconnect()

from postura.lousa import Lousa  # noqa: E402


def _carregar_modulo(nome: str, caminho: Path):
    loader = SourceFileLoader(nome, str(caminho))
    spec = spec_from_loader(nome, loader)
    assert spec is not None
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _resp_bulk(valor: str | None) -> bytes:
    if valor is None:
        return b"$-1\r\n"
    b = valor.encode("utf-8")
    return f"${len(b)}\r\n".encode("ascii") + b + b"\r\n"


def _resp_array(itens: list[str]) -> bytes:
    partes = [f"*{len(itens)}\r\n".encode("ascii")]
    for it in itens:
        partes.append(_resp_bulk(it))
    return b"".join(partes)


class _EstadoRESP:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.expires_chamados: list[tuple[str, int]] = []
        self.conexoes_aceitas = 0

    def executar(self, args: list[str]) -> bytes:
        cmd = args[0].upper()
        with self.lock:
            if cmd == "PING":
                return b"+PONG\r\n"
            if cmd == "HSET":
                chave = args[1]
                if chave in self.strings:
                    return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
                h = self.hashes.setdefault(chave, {})
                novos = 0
                for i in range(2, len(args), 2):
                    if args[i] not in h:
                        novos += 1
                    h[args[i]] = args[i + 1]
                return f":{novos}\r\n".encode("ascii")
            if cmd == "HGET":
                chave, campo = args[1], args[2]
                if chave in self.strings:
                    return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
                return _resp_bulk(self.hashes.get(chave, {}).get(campo))
            if cmd == "HGETALL":
                chave = args[1]
                if chave in self.strings:
                    return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
                h = self.hashes.get(chave, {})
                plano: list[str] = []
                for k, v in h.items():
                    plano.extend([k, v])
                return _resp_array(plano)
            if cmd == "GET":
                chave = args[1]
                if chave in self.hashes:
                    return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
                return _resp_bulk(self.strings.get(chave))
            if cmd == "SET":
                chave, valor = args[1], args[2]
                if chave in self.hashes:
                    return b"-WRONGTYPE Operation against a key holding the wrong kind of value\r\n"
                self.strings[chave] = valor
                return b"+OK\r\n"
            if cmd == "EXPIRE":
                chave, segs = args[1], int(args[2])
                self.ttls[chave] = segs
                self.expires_chamados.append((chave, segs))
                return b":1\r\n"
            if cmd == "TTL":
                chave = args[1]
                if chave not in self.hashes and chave not in self.strings:
                    return b":-2\r\n"
                return f":{self.ttls.get(chave, -1)}\r\n".encode("ascii")
            if cmd == "EXISTS":
                chave = args[1]
                existe = 1 if (chave in self.hashes or chave in self.strings) else 0
                return f":{existe}\r\n".encode("ascii")
            if cmd == "DEL":
                apag = 0
                for chave in args[1:]:
                    if chave in self.hashes:
                        del self.hashes[chave]
                        apag += 1
                    if chave in self.strings:
                        del self.strings[chave]
                        apag += 1
                return f":{apag}\r\n".encode("ascii")
            return f"-ERR comando nao suportado: {cmd}\r\n".encode("utf-8")


class _ServidorRESP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, estado: _EstadoRESP) -> None:
        self.estado = estado
        super().__init__(("127.0.0.1", 0), _HandlerRESP)


class _HandlerRESP(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        estado: _EstadoRESP = self.server.estado  # type: ignore[attr-defined]
        with estado.lock:
            estado.conexoes_aceitas += 1
        while True:
            linha = self.rfile.readline()
            if not linha:
                break
            if not linha.startswith(b"*"):
                break
            n = int(linha[1:].strip())
            args: list[str] = []
            for _ in range(n):
                tam_l = self.rfile.readline()
                tam = int(tam_l[1:].strip())
                dado = self.rfile.read(tam + 2)
                args.append(dado[:-2].decode("utf-8"))
            self.wfile.write(estado.executar(args))
            self.wfile.flush()


class _ClienteHashMinimo:
    """Adaptador fino no estilo `redis.Redis` falando com `_ServidorRESP` via `RepositorioSessaoValkey`."""

    def __init__(self, repo: RepositorioSessaoValkey) -> None:
        self._repo = repo

    def hset(self, chave: str, mapping: dict[str, str]) -> int:
        pares: list[str] = []
        for k, v in mapping.items():
            pares.extend([str(k), str(v)])
        return int(self._repo.pool.executar([("HSET", chave, *pares)])[0])

    def expire(self, chave: str, ttl: int) -> int:
        return int(self._repo.pool.executar([("EXPIRE", chave, int(ttl))])[0])

    def hgetall(self, chave: str) -> dict[str, str]:
        plano = self._repo.pool.executar([("HGETALL", chave)])[0] or []
        if isinstance(plano, dict):
            return dict(plano)
        return dict(zip(plano[0::2], plano[1::2]))

    def get(self, chave: str) -> str | None:
        return self._repo.pool.executar([("GET", chave)])[0]


@pytest.fixture
def servidor_resp():
    estado = _EstadoRESP()
    srv = _ServidorRESP(estado)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield srv.server_address[1], estado
    finally:
        srv.shutdown()
        srv.server_close()


def test_interoperabilidade_hash_porta_sessao_reidratar_e_lousa(servidor_resp, monkeypatch):
    porta, estado = servidor_resp
    sid = str(uuid.uuid4())

    mod_sessao = _carregar_modulo("bin_sessao_teste", _HARNESS_DIR / "bin" / "sessao")
    mod_reidratar = _carregar_modulo("reidratar_teste", _HARNESS_DIR / "bin" / "_sessao" / "reidratar.py")

    repo = RepositorioSessaoValkey(host="127.0.0.1", porta=porta, timeout_s=2.0)
    rc = _ClienteHashMinimo(repo)
    lousa = Lousa(host="127.0.0.1", porta=porta, espera_s=2.0)

    # 1. bin/sessao grava sessao:<id> como hash
    mod_sessao._grava_chave(
        rc,
        sid,
        {
            "sujeito": "suj-1",
            "cadeira": "engenharia",
            "chapeu": "back-end",
            "canonizada": True,
            "ordem_id": "o20261119-001",
            "superficie": "agy",
        },
        ttl_s=3600,
    )

    # 2. Porta le o mesmo hash e grava campo adicional sem WRONGTYPE
    lida_porta = repo.ler_sessao(sid)
    assert lida_porta is not None
    assert lida_porta["cadeira"] == "engenharia"
    assert lida_porta["canonizada"] is True

    # 3. Duas escritas concorrentes (turno e chapeu) preservam os dois campos
    with ThreadPoolExecutor(max_workers=2) as pool_th:
        f1 = pool_th.submit(repo.gravar_campo, sid, "turno", "T7")
        f2 = pool_th.submit(repo.gravar_campo, sid, "chapeu", "testes")
        f1.result()
        f2.result()

    # 4. bin/sessao e lousa.py leem os campos atualizados sem WRONGTYPE
    lida_sessao = mod_sessao._le_chave(rc, sid)
    assert lida_sessao is not None
    assert lida_sessao["turno"] == "T7"
    assert lida_sessao["chapeu"] == "testes"
    assert lousa.chapeu_da_sessao(sid) == "testes"

    # 5. reidratar.py grava hash compatível quando a chave some
    sid2 = str(uuid.uuid4())
    agora = datetime.now(timezone.utc)

    class _CurFake:
        def execute(self, _sql, _params):
            pass

        def fetchone(self):
            return ("engenharia", "back-end", "agy", agora, None, "suj-2", "o20261119-002")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _ConFake:
        def cursor(self):
            return _CurFake()

        def rollback(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_psycopg = types.SimpleNamespace(connect=lambda *_a, **_kw: _ConFake())
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    reid = mod_reidratar.reidratar(sid2, rc, lambda *_a, **_kw: (0, "segredo-fake", ""))
    assert reid is not None
    assert reid["cadeira"] == "engenharia"
    assert repo.ler_campo(sid2, "cadeira") == "engenharia"
    assert lousa.chapeu_da_sessao(sid2) == "back-end"

    # 6. GET em chave hash acusa WRONGTYPE (prova que realmente é hash no servidor)
    with pytest.raises(Exception, match="WRONGTYPE"):
        rc.get(f"sessao:{sid}")

    repo.fechar()


def test_um_pool_valkey_reutiliza_conexao_em_multiplas_leituras(servidor_resp):
    porta, estado = servidor_resp
    sid = str(uuid.uuid4())
    repo = RepositorioSessaoValkey(host="127.0.0.1", porta=porta, timeout_s=2.0)

    repo.gravar_campos(sid, {"cadeira": "engenharia", "chapeu": "back-end"}, ttl_s=1000)
    for _ in range(10):
        assert repo.ler_campo(sid, "cadeira") == "engenharia"
        assert repo.ler_campo(sid, "chapeu") == "back-end"
        assert repo.ler_sessao(sid)["cadeira"] == "engenharia"

    assert repo.conexoes_abertas == 1
    assert estado.conexoes_aceitas == 1
    repo.fechar()
