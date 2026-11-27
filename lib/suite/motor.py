"""motor — a suíte de testes como motor que reúne o executor de testes como jurado (card #4454).

A suíte não julga caso nenhum: recebe duas ou mais chaves de ficha de teste (por delegação
via ato despachar), aciona o executor de testes uma vez por ficha, preserva cada veredito
como saiu e emite o laudo com o resultado combinado:
- qualquer `nao` → `nao` (`divergente`)
- sem `nao`, qualquer `nao-sei` → `nao-sei` (`inconclusivo`)
- todos `sim` → `sim` (`conforme`)
"""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from suite.executor import (
    ErroExecutorTestes,
    OpcoesExecucaoTeste,
    VereditoTeste,
    julgar_ficha,
    versao_servico,
)

MOTOR_CHAVE = "motor:harness:suite-de-testes"


class ErroLaudoSuite(Exception):
    """Falha ao montar o laudo da suíte, preservando os vereditos das fichas já julgadas."""

    def __init__(
        self,
        saida: int,
        codigo: str,
        detalhe: str,
        *,
        vereditos_parciais: Sequence[VereditoTeste] = (),
    ) -> None:
        super().__init__(detalhe)
        self.saida = int(saida)
        self.codigo = str(codigo)
        self.detalhe = str(detalhe)
        self.vereditos_parciais = tuple(vereditos_parciais)


@dataclass(frozen=True, slots=True)
class LaudoSuite:
    """Laudo consolidado emitido pela suíte de testes a partir dos vereditos do jurado."""

    alvo: str
    resultado: str
    constatacao: str
    vereditos: tuple[VereditoTeste, ...]
    motor: str
    versao_motor: str


def combinar_resultados(vereditos: Sequence[VereditoTeste]) -> tuple[str, str]:
    """Combina os vereditos individuais segundo a regra de fecho do laudo."""
    if not vereditos:
        return "nao-sei", "inconclusivo"
    if any(v.resultado == "nao" for v in vereditos):
        return "nao", "divergente"
    if any(v.resultado == "nao-sei" for v in vereditos):
        return "nao-sei", "inconclusivo"
    return "sim", "conforme"


def julgar_laudo(
    chaves_fichas: Sequence[str],
    arvore: str | Path,
    *,
    opcoes: OpcoesExecucaoTeste | None = None,
    jurado_fn: Callable[..., VereditoTeste] | None = None,
) -> LaudoSuite:
    """Aciona o executor de testes para cada ficha em `chaves_fichas` e devolve o laudo."""
    cfg = opcoes or OpcoesExecucaoTeste()
    if cfg.prazo_s <= 0:
        raise ErroLaudoSuite(5, "tempo-esgotado", "prazo esgotado antes de iniciar a suíte de testes")
    if not chaves_fichas:
        raise ErroLaudoSuite(1, "regua-inexistente", "nenhuma ficha de teste informada à suíte")

    raiz = Path(arvore).resolve()
    alvo_chave = cfg.alvo or raiz.name
    fim = time.monotonic() + cfg.prazo_s
    chamar_jurado = jurado_fn or julgar_ficha
    vereditos: list[VereditoTeste] = []

    for chave in chaves_fichas:
        resta = fim - time.monotonic()
        if resta <= 0:
            raise ErroLaudoSuite(
                5,
                "tempo-esgotado",
                f"prazo esgotado antes de julgar a ficha '{chave}'",
                vereditos_parciais=vereditos,
            )
        opcoes_ficha = replace(cfg, alvo=alvo_chave, prazo_s=resta)
        try:
            veredito = chamar_jurado(chave, raiz, opcoes=opcoes_ficha)
        except ErroExecutorTestes as exc:
            raise ErroLaudoSuite(
                exc.saida,
                exc.codigo,
                exc.detalhe,
                vereditos_parciais=vereditos,
            ) from exc
        vereditos.append(veredito)

    resultado, constatacao = combinar_resultados(vereditos)
    return LaudoSuite(
        alvo=alvo_chave,
        resultado=resultado,
        constatacao=constatacao,
        vereditos=tuple(vereditos),
        motor=MOTOR_CHAVE,
        versao_motor=versao_servico(),
    )
