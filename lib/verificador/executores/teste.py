"""teste — adaptador do verificador para o executor de testes e a suíte de testes (card #4454).

Com uma ficha de teste, chama direto o executor de testes (`suite.executor.julgar_ficha`)
no processo do verbo. Com duas ou mais fichas, delega à suíte de testes pela interface
`DelegadorSuite` (que a story #4455 liga ao ato `despachar`).
"""
from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from leitura.recusa import Recusa
from suite.executor import ErroExecutorTestes, OpcoesExecucaoTeste, VereditoTeste, julgar_ficha
from suite.motor import ErroLaudoSuite

from ..tipos import (
    SERVICO_EXECUTOR_TESTES,
    AlvoVerificado,
    AmbienteVerificacao,
    ErroVerificacaoParcial,
    ReguaCasada,
    VereditoEmitido,
    VereditoItem,
)
from . import traduzir_apontamentos

_REGRA_TESTE = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"
_MIN_TESTES_SUITE = 2
_SAIDA_INDETERMINAVEL = 5


def _raiz_do_alvo(alvo: AlvoVerificado) -> Path:
    if alvo.raiz is not None:
        return alvo.raiz
    raise Recusa(
        3,
        "dependencia-sem-resposta",
        onde="alvo",
        recebido=alvo.chave,
        regra=_REGRA_TESTE,
        cura=f"o alvo '{alvo.chave}' não trouxe árvore de construção resolvida para executar testes",
    )


def _traduzir_veredito_teste(vt: VereditoTeste, versao_regua: str = "") -> VereditoItem:
    return VereditoItem(
        alvo=vt.alvo,
        resultado=vt.resultado,
        constatacao=vt.constatacao,
        apontamentos=traduzir_apontamentos(vt.apontamentos),
        modo=vt.modo,
        quesito=vt.quesito,
        motor=vt.motor,
        versao_servico=vt.versao_servico,
        versao_regua=versao_regua,
    )


def _executar_suite(
    regua_casada: ReguaCasada,
    alvos: Sequence[AlvoVerificado],
    ambiente: AmbienteVerificacao,
) -> VereditoEmitido:
    if len(alvos) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="alvo",
            recebido=", ".join(a.chave for a in alvos),
            regra=_REGRA_TESTE,
            cura="a delegação de dois ou mais testes à suíte aceita um alvo por chamada",
        )
    alvo = alvos[0]
    raiz = _raiz_do_alvo(alvo)
    if ambiente.delegador_suite is None:
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="despachar",
            recebido=", ".join(regua_casada.chaves),
            regra=_REGRA_TESTE,
            cura="a delegação de dois ou mais testes à suíte pelo ato despachar entra na story #4455",
        )
    try:
        return ambiente.delegador_suite.despachar_suite(
            regua_casada.chaves,
            raiz,
            alvo=alvo.chave,
            prazo_s=ambiente.prazo_s,
        )
    except ErroLaudoSuite as exc:
        recusa = Recusa(
            exc.saida,
            exc.codigo,
            onde="suite-de-testes",
            recebido=", ".join(regua_casada.chaves),
            regra=_REGRA_TESTE,
            cura=exc.detalhe,
        )
        if exc.saida == _SAIDA_INDETERMINAVEL and exc.vereditos_parciais:
            parciais = tuple(_traduzir_veredito_teste(v) for v in exc.vereditos_parciais)
            raise ErroVerificacaoParcial(recusa, parciais) from exc
        raise recusa from exc


def _falhar_ou_parcial(recusa: Recusa, itens: Sequence[VereditoItem], exc: BaseException | None = None) -> None:
    if recusa.saida == _SAIDA_INDETERMINAVEL and itens:
        raise ErroVerificacaoParcial(recusa, tuple(itens)) from exc
    raise recusa from exc


def executar_teste(
    regua_casada: ReguaCasada,
    alvos: Sequence[AlvoVerificado],
    ambiente: AmbienteVerificacao,
) -> VereditoEmitido | tuple[VereditoItem, ...]:
    """Executa uma ficha direto no executor de testes para cada alvo ou delega várias fichas à suíte."""
    if regua_casada.servico != SERVICO_EXECUTOR_TESTES:
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="servico",
            recebido=regua_casada.servico,
            regra=_REGRA_TESTE,
            cura=f"serviço '{regua_casada.servico}' não suportado pelo executor de testes",
        )

    if len(regua_casada.reguas) >= _MIN_TESTES_SUITE:
        return _executar_suite(regua_casada, alvos, ambiente)

    regua = regua_casada.reguas[0]
    fim = time.monotonic() + ambiente.prazo_s
    itens: list[VereditoItem] = []

    for alvo in alvos:
        resta = fim - time.monotonic()
        if resta <= 0:
            recusa = Recusa(
                _SAIDA_INDETERMINAVEL,
                "tempo-esgotado",
                onde="executor-de-testes",
                recebido=regua.chave,
                regra=_REGRA_TESTE,
                cura=f"prazo esgotado antes de julgar o alvo '{alvo.chave}'",
            )
            _falhar_ou_parcial(recusa, itens)

        raiz = _raiz_do_alvo(alvo)
        opcoes = OpcoesExecucaoTeste(
            alvo=alvo.chave,
            executor_isolado=ambiente.executor_isolado,
            prazo_s=resta,
            ficha_confirmada=True,
        )
        try:
            vt = julgar_ficha(regua.chave, raiz, opcoes=opcoes)
        except ErroExecutorTestes as exc:
            recusa = Recusa(
                exc.saida,
                exc.codigo,
                onde="executor-de-testes",
                recebido=regua.chave,
                regra=_REGRA_TESTE,
                cura=exc.detalhe,
            )
            _falhar_ou_parcial(recusa, itens, exc)

        itens.append(_traduzir_veredito_teste(vt, versao_regua=regua.versao))

    return tuple(itens)
