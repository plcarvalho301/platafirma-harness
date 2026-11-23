"""retrato.py — a conexão de leitura do banco casa, num retrato só por chamada (stories 4426 e 4427).

Contrato: platafirma-casa@referencias/instancias/verbo/busca.md, seções «A conexão e o retrato»,
«Os códigos de saída» e «As alavancas». O leitor entra no banco casa pelo papel analise_leitura, o
mesmo do verbo analise, sem senha, pelo socket local do contêiner (`docker exec … psql`). Cada
chamada abre uma sessão só, numa transação REPEATABLE READ READ ONLY, e antes de cada comando fixa
na transação o tempo que resta do prazo da chamada (`SET LOCAL statement_timeout`).

O texto de cada consulta é fixo: o que varia chega como parâmetro ligado pelo `\\bind` do psql, e
o verbo nunca monta SQL juntando valor. Parâmetro nulo viaja como texto vazio (`''`), lido por
`NULLIF` na consulta. Cada consulta volta como uma linha JSON só, a lista das linhas do resultado.
"""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Self

from .recusa import Recusa

ROLE_LEITURA = "analise_leitura"
BANCO = "casa"
PRAZO_CHAMADA = 5.0            # segundos para a chamada inteira (alavanca do verbo busca)
FOLGA_LEITURA = 1.0            # o cliente espera um pouco além do prazo do servidor
BLOCO_LEITURA = 65536
SQL = Path(__file__).resolve().parent / "sql"
_REGISTRO = Path(__file__).resolve().parents[2] / "registro" / "bancos.json"
_REGRA = "verbo:busca §A conexão e o retrato"


def registro_do_banco(banco: str = BANCO) -> dict:
    """A entrada do banco em registro/bancos.json (PF_BUSCA_BANCOS só aponta outro registro no ensaio)."""
    arq = Path(os.getenv("PF_BUSCA_BANCOS") or _REGISTRO)
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Recusa(3, "banco-indisponivel", onde="registro de bancos", recebido=str(arq),
                     regra=_REGRA, cura="o registro de bancos do harness não se lê") from None
    info = dados.get(banco)
    if not isinstance(info, dict) or not info.get("conteiner") or not info.get("base"):
        raise Recusa(3, "banco-indisponivel", onde="registro de bancos", recebido=banco,
                     regra=_REGRA, cura=f"o banco {banco} não está no registro com contêiner e base")
    return info


def comando_padrao(banco: str = BANCO) -> list[str]:
    info = registro_do_banco(banco)
    return [
        os.getenv("PF_BUSCA_DOCKER", "docker"), "exec", "-i", info["conteiner"],
        "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-U", ROLE_LEITURA, "-d", info["base"],
    ]


def literal(valor: Any) -> str:
    """O valor como argumento do `\\bind`, entre aspas simples do psql; nulo vira texto vazio."""
    if valor is None:
        return "''"
    if isinstance(valor, (list, tuple)):
        itens = (str(v).replace("\\", "\\\\").replace('"', '\\"') for v in valor)
        valor = "{" + ",".join(f'"{i}"' for i in itens) + "}"
    s = str(valor)
    for de, para in (("\\", "\\\\"), ("'", "\\'"), ("\n", "\\n"), ("\r", "\\r"), ("\t", "\\t")):
        s = s.replace(de, para)
    return f"'{s}'"


def _causa(err: str) -> Recusa:
    """A falha do psql como recusa; nunca devolve o diagnóstico do servidor, que pode ter dado."""
    e = err.lower()
    if "statement timeout" in e or "canceling statement" in e:
        return Recusa(5, "prazo-estourado", onde="banco casa", regra=_REGRA,
                      cura="a chamada passou do prazo; tente de novo ou leia pela chave exata")
    if "permission denied" in e or "read-only transaction" in e:
        return Recusa(4, "acesso-negado", onde="banco casa", regra=_REGRA,
                      cura="o papel de leitura não alcança a tabela; abra incidente")
    if ("too many connections for role" in e or "too many clients already" in e
            or "remaining connection slots" in e):
        return Recusa(3, "conexoes-esgotadas", onde="banco casa", regra=_REGRA,
                      cura="as quatro conexões do papel de leitura estão ocupadas; tente de novo em instantes")
    if ("no such container" in e or "is not running" in e or "cannot connect to the docker" in e
            or f'role "{ROLE_LEITURA}" does not exist' in e or "not permitted to log in" in e
            or "could not connect" in e or "connection to server" in e
            or "the database system is starting up" in e or "the database system is shutting down" in e):
        return Recusa(3, "banco-indisponivel", onde="banco casa", regra=_REGRA,
                      cura="não consegui olhar o banco casa; confira com infra estado")
    return Recusa(5, "falha-interna", onde="banco casa", regra=_REGRA,
                  cura="a sessão de leitura do banco casa falhou; veja o log da porta")


class Retrato:
    """Uma sessão psql em transação REPEATABLE READ READ ONLY, com o prazo contado para a chamada."""

    def __init__(self, *, prazo: float = PRAZO_CHAMADA, comando: Sequence[str] | None = None) -> None:
        self._prazo = prazo
        self._comando = list(comando) if comando is not None else None
        self._inicio = 0.0
        self._proc: subprocess.Popen[bytes] | None = None
        self._buf = b""
        self._err = b""
        self._marca = f"__pf_fim_{uuid.uuid4().hex}__"

    def __enter__(self) -> Self:
        self._inicio = time.monotonic()
        cmd = self._comando if self._comando is not None else comando_padrao()
        try:
            self._proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
        except OSError:
            raise Recusa(3, "banco-indisponivel", onde="banco casa", regra=_REGRA,
                         cura="não consegui abrir o cliente do banco casa") from None
        self._enviar(
            "\\pset tuples_only on\n"
            "\\pset format unaligned\n"
            "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
        )
        self._ate_marca()
        return self

    def __exit__(self, *_exc: object) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin:
                proc.stdin.write(b"ROLLBACK;\n\\q\n")
                proc.stdin.close()
            proc.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()
            proc.wait()
        finally:
            for fh in (proc.stdout, proc.stderr):
                if fh:
                    fh.close()

    # ---------------------------------------------------------------- consultas
    def resta(self) -> float:
        return self._prazo - (time.monotonic() - self._inicio)

    def consultar(self, sql: str, *parametros: Any) -> list[dict]:
        """As linhas do resultado de `sql`, com `$1…$n` ligados a `parametros`."""
        if self._proc is None:
            raise RuntimeError("retrato fechado")
        ms = int(self.resta() * 1000)
        if ms <= 0:
            raise Recusa(5, "prazo-estourado", onde="banco casa", regra=_REGRA,
                         cura="o prazo da chamada acabou antes da consulta")
        corpo = sql.strip().rstrip(";").strip()
        ligados = " ".join(literal(p) for p in parametros)
        self._enviar(
            f"SET LOCAL statement_timeout = {ms};\n"
            "SELECT coalesce(jsonb_agg(to_jsonb(t)), '[]'::jsonb)::text FROM (\n"
            f"{corpo}\n) t\n"
            f"\\bind {ligados} \\g\n"
        )
        linhas = [ln for ln in self._ate_marca() if ln.strip()]
        if len(linhas) != 1:
            raise Recusa(5, "falha-interna", onde="banco casa", regra=_REGRA,
                         cura="a consulta não voltou numa linha só; abra incidente")
        return json.loads(linhas[0])

    def resolver_nomes(self, termos: Sequence[str]) -> list[dict]:
        """Que fichas cada termo nomeia, pela consulta resolver_nomes do leitor."""
        sql = (SQL / "resolver_nomes.sql").read_text(encoding="utf-8")
        return self.consultar(sql, list(termos))

    # ---------------------------------------------------------------- protocolo
    def _enviar(self, texto: str) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("retrato fechado")
        try:
            self._proc.stdin.write(texto.encode("utf-8"))
            self._proc.stdin.flush()
        except OSError:
            raise self._falha() from None

    def _ate_marca(self) -> list[str]:
        """Linhas do stdout até a marca; a sessão que cai ou estoura vira recusa."""
        if self._proc is None or self._proc.stdout is None or self._proc.stderr is None:
            raise RuntimeError("retrato fechado")
        self._enviar(f"\\echo {self._marca}\n")
        limite = time.monotonic() + max(self.resta(), 0) + FOLGA_LEITURA
        marca = self._marca.encode()
        sel = selectors.DefaultSelector()
        sel.register(self._proc.stdout, selectors.EVENT_READ, "out")
        sel.register(self._proc.stderr, selectors.EVENT_READ, "err")
        try:
            return self._ler_ate_marca(sel, marca, limite)
        finally:
            sel.close()

    def _ler_ate_marca(self, sel: selectors.BaseSelector, marca: bytes, limite: float) -> list[str]:
        while True:
            linhas = self._buf.split(b"\n")
            if marca in linhas[:-1]:
                i = linhas.index(marca)
                self._buf = b"\n".join(linhas[i + 1:])
                return [ln.decode("utf-8", "replace") for ln in linhas[:i]]
            falta = limite - time.monotonic()
            if falta <= 0:
                if self._proc is not None:
                    self._proc.kill()
                raise Recusa(5, "prazo-estourado", onde="banco casa", regra=_REGRA,
                             cura="o banco casa não respondeu no prazo da chamada")
            for chave, _ in sel.select(timeout=falta):
                dado = os.read(chave.fileobj.fileno(), BLOCO_LEITURA)
                if not dado:
                    sel.unregister(chave.fileobj)
                    if chave.data == "out":
                        raise self._falha()
                    continue
                if chave.data == "out":
                    self._buf += dado
                else:
                    self._err += dado

    def _falha(self) -> Recusa:
        proc = self._proc
        if proc is not None:
            try:
                proc.wait(timeout=1)
                if proc.stderr:
                    self._err += proc.stderr.read() or b""
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        return _causa(self._err.decode("utf-8", "replace"))
