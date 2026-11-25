"""Protocolo interno das moradas do escritor único e utilitários compartilhados."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from ..politica import PoliticaEscrita
from ..portao import DecisaoPortao
from ..registro import LinhaOperacao, RegistroOperacoes, hash_canonico_pedido
from ..resolucao import AlvoResolvido
from ..tipos import PedidoEscrita, ResultadoEscrita


@dataclass(frozen=True)
class ExecucaoMorada:
    """Contexto completo e imutável entregue a uma morada após portão e resolução."""

    pedido: PedidoEscrita
    decisao: DecisaoPortao
    alvo: AlvoResolvido
    politica: PoliticaEscrita
    release: str
    prazo_ns: int = 0
    registro: RegistroOperacoes | None = None


class MoradaEscrita(Protocol):
    """Protocolo interno único de moradas invisível aos verbos."""

    nome: str
    ponto_de_nao_volta: str

    def executar(self, execucao: ExecucaoMorada) -> ResultadoEscrita:
        """Executa a operação de escrita ou ensaio na morada."""


def proximo_repeticao_pedido(pedido: PedidoEscrita, classe: str) -> str:
    """Monta a chamada canônica pronta para repetir com `--pedido` em saídas 5."""
    partes = [pedido.verbo, pedido.forma]
    if pedido.forma == "ensaiar" and pedido.forma_ensaiada:
        partes.append(pedido.forma_ensaiada)
    partes.extend([classe, pedido.chave])
    if pedido.versao:
        partes.append(pedido.versao)
    partes.extend(["--pedido", pedido.pedido])
    return " ".join(partes)


def registrar_operacao_sucesso(
    execucao: ExecucaoMorada,
    resultado: ResultadoEscrita,
    *,
    repo: str | None = None,
    caminho_relativo: str | None = None,
) -> None:
    """Grava a linha de operação bem-sucedida no registro só de acréscimo."""
    if execucao.registro is None or resultado.ensaiado:
        return
    dec = execucao.decisao
    linha = LinhaOperacao(
        pedido=execucao.pedido.pedido,
        sha256_pedido=hash_canonico_pedido(execucao.pedido, classe=dec.classe),
        conta_par=dec.conta_par,
        uid_par=dec.uid_par,
        gid_par=dec.gid_par,
        pid_par=dec.pid_par,
        sujeito=dec.sujeito,
        verbo=dec.verbo,
        cadeira=dec.cadeira,
        forma=dec.forma,
        classe=dec.classe,
        chave=resultado.chave,
        morada=resultado.morada,
        endereco=execucao.alvo.alvo.endereco,
        repo=repo,
        caminho_relativo=caminho_relativo,
        versao_lida=execucao.pedido.versao,
        versao_gravada=resultado.versao,
        bytes=resultado.bytes,
        exit_code=0,
        release=execucao.release,
        timestamp=time.time(),
        fornada=resultado.fornada,
        resultado=resultado.como_dict(),
    )
    execucao.registro.registrar(linha)


__all__ = [
    "ExecucaoMorada",
    "MoradaEscrita",
    "proximo_repeticao_pedido",
    "registrar_operacao_sucesso",
]
