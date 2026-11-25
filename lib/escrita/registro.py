"""Registro de operações só de acréscimo na conta do escritor e repetição por pedido."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .tipos import ErroEscrita, PedidoEscrita, RecusaEscrita

_FLAGS_APPEND = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC
_MODO_REGISTRO = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP


def _conteudo_canonico(pedido: PedidoEscrita) -> Any:
    if pedido.trecho is not None:
        return {
            "antes": pedido.trecho.antes,
            "depois": pedido.trecho.depois,
            "todos": pedido.trecho.todos,
        }
    if pedido.patch is not None:
        return {
            "old_path": pedido.patch.old_path,
            "new_path": pedido.patch.new_path,
            "hunks": [
                {
                    "old_start": h.old_start,
                    "old_count": h.old_count,
                    "new_start": h.new_start,
                    "new_count": h.new_count,
                    "linhas": list(h.linhas),
                }
                for h in pedido.patch.hunks
            ],
        }
    return pedido.conteudo


def hash_canonico_pedido(pedido: PedidoEscrita, *, classe: str) -> str:
    """Calcula SHA-256 sobre a forma canônica dos campos do pedido de escrita."""
    estrutura = {
        "forma": pedido.forma,
        "forma_ensaiada": pedido.forma_ensaiada,
        "classe": classe,
        "chave": pedido.chave,
        "versao": pedido.versao,
        "documento": pedido.documento,
        "formato": pedido.formato,
        "permitir_vazio": pedido.permitir_vazio,
        "conteudo": _conteudo_canonico(pedido),
    }
    bruto = json.dumps(
        estrutura, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()


@dataclass(frozen=True)
class LinhaOperacao:
    """Linha imutável gravada no registro só de acréscimo do escritor."""

    pedido: str
    sha256_pedido: str
    conta_par: str
    uid_par: int
    gid_par: int
    pid_par: int
    sujeito: str
    verbo: str
    cadeira: str
    forma: str
    classe: str
    chave: str
    morada: str
    endereco: str
    versao_lida: str | None
    versao_gravada: str | None
    bytes: int
    exit_code: int
    release: str
    timestamp: float
    registrado_em: str = ""
    repo: str | None = None
    caminho_relativo: str | None = None
    fornada: str | None = None
    resultado: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.registrado_em:
            iso = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
            object.__setattr__(self, "registrado_em", iso)

    def como_dict(self) -> dict[str, Any]:
        """Serializa a linha para gravação em JSONL."""
        return {
            "pedido": self.pedido,
            "sha256_pedido": self.sha256_pedido,
            "conta_par": self.conta_par,
            "uid_par": self.uid_par,
            "gid_par": self.gid_par,
            "pid_par": self.pid_par,
            "sujeito": self.sujeito,
            "verbo": self.verbo,
            "cadeira": self.cadeira,
            "forma": self.forma,
            "classe": self.classe,
            "chave": self.chave,
            "morada": self.morada,
            "endereco": self.endereco,
            "repo": self.repo,
            "caminho_relativo": self.caminho_relativo,
            "versao_lida": self.versao_lida,
            "versao_gravada": self.versao_gravada,
            "bytes": self.bytes,
            "exit_code": self.exit_code,
            "release": self.release,
            "timestamp": self.timestamp,
            "registrado_em": self.registrado_em,
            "fornada": self.fornada,
            "resultado": self.resultado,
        }

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> LinhaOperacao:
        """Reconstrói LinhaOperacao a partir de um objeto JSONL."""
        return cls(
            pedido=str(dados["pedido"]),
            sha256_pedido=str(dados["sha256_pedido"]),
            conta_par=str(dados["conta_par"]),
            uid_par=int(dados["uid_par"]),
            gid_par=int(dados["gid_par"]),
            pid_par=int(dados["pid_par"]),
            sujeito=str(dados["sujeito"]),
            verbo=str(dados["verbo"]),
            cadeira=str(dados["cadeira"]),
            forma=str(dados["forma"]),
            classe=str(dados["classe"]),
            chave=str(dados["chave"]),
            morada=str(dados["morada"]),
            endereco=str(dados["endereco"]),
            repo=dados.get("repo"),
            caminho_relativo=dados.get("caminho_relativo"),
            versao_lida=dados.get("versao_lida"),
            versao_gravada=dados.get("versao_gravada"),
            bytes=int(dados["bytes"]),
            exit_code=int(dados["exit_code"]),
            release=str(dados["release"]),
            timestamp=float(dados["timestamp"]),
            registrado_em=str(dados.get("registrado_em") or ""),
            fornada=dados.get("fornada"),
            resultado=dados.get("resultado"),
        )


def _erro_pedido_diferente(pedido_id: str, motivo: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=2,
            codigo="pedido-com-conteudo-diferente",
            onde="--pedido",
            recebido=f"{pedido_id} ({motivo})",
            regra="um mesmo identificador --pedido não pode ser reutilizado com sujeito, alvo ou conteúdo diferente",
            cura="repita a chamada sem reutilizar o --pedido anterior",
            proximo="",
        )
    )


def _diferenca_repeticao(
    linha: LinhaOperacao,
    pedido: PedidoEscrita,
    classe: str,
    sha256_atual: str,
) -> str | None:
    if linha.sujeito != pedido.contexto.sujeito:
        return "sujeito diferente"
    if linha.verbo != pedido.verbo:
        return "verbo diferente"
    if linha.classe != classe or linha.chave != pedido.chave:
        return "alvo diferente"
    if linha.sha256_pedido != sha256_atual:
        return "conteúdo diferente"
    return None


class RegistroOperacoes:
    """Registro append-only JSONL mantido na conta do escritor."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def registrar(self, linha: LinhaOperacao) -> None:
        """Acrescenta uma linha de operação de forma atômica e durável (fsync)."""
        if linha.forma == "ensaiar":
            raise ValueError("ensaio não grava linha no registro de operações")
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(linha.como_dict(), ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(str(self.caminho), _FLAGS_APPEND, _MODO_REGISTRO)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                view = memoryview(payload)
                escrito = 0
                while escrito < len(payload):
                    escrito += os.write(fd, view[escrito:])
                os.fsync(fd)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def listar(self) -> list[LinhaOperacao]:
        """Lê todas as linhas gravadas em ordem cronológica de acréscimo."""
        if not self.caminho.is_file():
            return []
        linhas: list[LinhaOperacao] = []
        with self.caminho.open("r", encoding="utf-8") as arq:
            for bruto in arq:
                texto = bruto.strip()
                if not texto:
                    continue
                linhas.append(LinhaOperacao.de_dict(json.loads(texto)))
        return linhas

    def buscar_por_pedido(self, pedido_id: str) -> LinhaOperacao | None:
        """Devolve a última linha registrada para `pedido_id`, se existir."""
        achada: LinhaOperacao | None = None
        for linha in self.listar():
            if linha.pedido == pedido_id:
                achada = linha
        return achada

    def consultar_repeticao(
        self,
        pedido: PedidoEscrita,
        *,
        classe: str,
        retencao_s: int,
        agora: float | None = None,
    ) -> LinhaOperacao | None:
        """Verifica se `pedido` já foi gravado dentro da janela de retenção."""
        instante = time.time() if agora is None else agora
        corte = instante - retencao_s
        sha_atual = hash_canonico_pedido(pedido, classe=classe)
        for linha in reversed(self.listar()):
            if linha.timestamp < corte:
                continue
            if linha.pedido != pedido.pedido:
                continue
            motivo = _diferenca_repeticao(linha, pedido, classe, sha_atual)
            if motivo is not None:
                raise _erro_pedido_diferente(pedido.pedido, motivo)
            return linha
        return None

    def arquivos_gravados_na_bancada(
        self,
        repo: str,
        cadeira: str,
        *,
        desde: float | None = None,
    ) -> list[str]:
        """Lista os caminhos relativos gravados com sucesso na bancada para repo commitar."""
        vistos: set[str] = set()
        ordenados: list[str] = []
        for linha in self.listar():
            if linha.morada != "git" or linha.exit_code != 0:
                continue
            if linha.repo != repo or linha.cadeira != cadeira:
                continue
            if desde is not None and linha.timestamp < desde:
                continue
            rel = linha.caminho_relativo
            if rel and rel not in vistos:
                vistos.add(rel)
                ordenados.append(rel)
        return ordenados
