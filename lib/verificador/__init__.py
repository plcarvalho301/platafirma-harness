"""verificador — concretização do ato `verificar` na camada comum de verbos (card #4454).

Encadeia borda → portões → casamento → conteúdos → executor → agregador.
Sem cache, sem gravação de veredito em evento/trilha/banco e sem consulta própria ao PDP.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from typing import TextIO

from leitura.recusa import Recusa
from leitura.retrato import Retrato

from .agregador import agregar_vereditos, formatar_json, formatar_texto
from .borda import converter_chamada
from .casamento import casar_regua
from .conteudos import FicharioBanco, carregar_alvos, traduzir_recusa_retrato
from .executores import executar_gabarito, executar_teste
from .portoes import carregar_vista_verificar, conferir_portoes
from .tipos import (
    VERSAO_CONTRATO,
    AlvoVerificado,
    AmbienteVerificacao,
    Apontamento,
    DelegadorSuite,
    LeitorFichario,
    PedidoVerificacao,
    ReguaCasada,
    ReguaFicha,
    VereditoEmitido,
    VereditoItem,
    VistaVerificar,
)

__all__ = [
    "VERSAO_CONTRATO",
    "AlvoVerificado",
    "AmbienteVerificacao",
    "Apontamento",
    "DelegadorSuite",
    "LeitorFichario",
    "PedidoVerificacao",
    "ReguaCasada",
    "ReguaFicha",
    "VereditoEmitido",
    "VereditoItem",
    "VistaVerificar",
    "executar",
]


def _escrever_recusa_json(recusa: Recusa, fluxo: TextIO) -> int:
    fluxo.write(json.dumps(recusa.campos(), ensure_ascii=False) + "\n")
    fluxo.flush()
    return recusa.saida


def _rodar_fluxo(verbo: str, argv: Sequence[str], amb: AmbienteVerificacao) -> tuple[VereditoEmitido, bool]:
    pedido = converter_chamada(verbo, argv, prazo_s=amb.prazo_s)
    vista = amb.vista if amb.vista is not None else carregar_vista_verificar(amb.caminho_vista)
    classe_alvo = conferir_portoes(pedido, vista)

    with ExitStack() as pilha:
        fichario: LeitorFichario
        if amb.fichario is not None:
            fichario = amb.fichario
        else:
            try:
                retrato = pilha.enter_context(Retrato(prazo=amb.prazo_s))
            except Recusa as exc:
                raise traduzir_recusa_retrato(exc) from exc
            fichario = FicharioBanco(retrato)

        regua_casada = casar_regua(pedido, classe_alvo, fichario)
        alvos = carregar_alvos(
            pedido,
            classe_alvo,
            fichario,
            leitor_arvore=amb.leitor_arvore,
        )

        if regua_casada.forma == "gabarito":
            itens = executar_gabarito(regua_casada, alvos, amb)
            veredito = agregar_vereditos(regua_casada, alvos, itens, amb)
        elif regua_casada.forma == "teste":
            res = executar_teste(regua_casada, alvos, amb)
            veredito = (
                res
                if isinstance(res, VereditoEmitido)
                else agregar_vereditos(regua_casada, alvos, res, amb)
            )
        else:
            raise Recusa(
                3,
                "dependencia-sem-resposta",
                onde="executor",
                recebido=regua_casada.forma,
                regra="ato:verificar §Contra que régua e como ocorre o casamento?",
                cura=f"forma '{regua_casada.forma}' não possui executor nesta story",
            )
    return veredito, pedido.como_json


def executar(
    verbo: str,
    argv: Sequence[str],
    *,
    ambiente: AmbienteVerificacao | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Executa `<verbo> verificar <argv…>` e devolve o código de saída (0 a 5)."""
    out = sys.stdout if stdout is None else stdout
    err = sys.stderr if stderr is None else stderr
    amb = ambiente or AmbienteVerificacao()

    try:
        veredito, como_json = _rodar_fluxo(verbo, argv, amb)
    except Recusa as recusa:
        return _escrever_recusa_json(recusa, err)
    except Exception as exc:  # noqa: BLE001 — borda: falha inesperada vira saída 5, nunca conforme
        recusa_interna = Recusa(
            5,
            "falha-interna",
            onde="verificador",
            recebido=f"{type(exc).__name__}: {exc}",
            regra="ato:verificar §Qual é o contrato de retorno e de recusa?",
            cura="erro interno inesperado no verificador; abra incidente",
        )
        return _escrever_recusa_json(recusa_interna, err)

    saida_texto = formatar_json(veredito) if como_json else formatar_texto(veredito)
    out.write(saida_texto + "\n")
    out.flush()
    return 0
