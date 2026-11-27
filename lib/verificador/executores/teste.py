"""teste — adaptador do verificador para o executor de testes e a suíte de testes (card #4454).

Com uma ficha de teste, chama direto o executor de testes (`suite.executor.julgar_ficha`)
no processo do verbo. Com duas ou mais fichas, delega à suíte de testes pela interface
`DelegadorSuite` (que a story #4455 liga ao ato `despachar`).
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from leitura.recusa import Recusa
from suite.executor import ErroExecutorTestes, OpcoesExecucaoTeste, julgar_ficha

from ..tipos import (
    SERVICO_EXECUTOR_TESTES,
    AlvoVerificado,
    AmbienteVerificacao,
    ReguaCasada,
    VereditoEmitido,
    VereditoItem,
)
from . import traduzir_apontamentos

_REGRA_TESTE = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"
_MIN_TESTES_SUITE = 2


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


def executar_teste(
    regua_casada: ReguaCasada,
    alvos: Sequence[AlvoVerificado],
    ambiente: AmbienteVerificacao,
) -> VereditoEmitido | tuple[VereditoItem, ...]:
    """Executa uma ficha direto no executor de testes ou delega várias fichas à suíte."""
    if regua_casada.servico != SERVICO_EXECUTOR_TESTES:
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="servico",
            recebido=regua_casada.servico,
            regra=_REGRA_TESTE,
            cura=f"serviço '{regua_casada.servico}' não suportado pelo executor de testes",
        )

    alvo = alvos[0]
    raiz = _raiz_do_alvo(alvo)

    if len(regua_casada.reguas) >= _MIN_TESTES_SUITE:
        if ambiente.delegador_suite is None:
            raise Recusa(
                3,
                "dependencia-sem-resposta",
                onde="despachar",
                recebido=", ".join(regua_casada.chaves),
                regra=_REGRA_TESTE,
                cura="a delegação de dois ou mais testes à suíte pelo ato despachar entra na story #4455",
            )
        return ambiente.delegador_suite.despachar_suite(
            regua_casada.chaves,
            raiz,
            alvo=alvo.chave,
            prazo_s=ambiente.prazo_s,
        )

    regua = regua_casada.reguas[0]
    opcoes = OpcoesExecucaoTeste(
        alvo=alvo.chave,
        executor_isolado=ambiente.executor_isolado,
        prazo_s=ambiente.prazo_s,
        ficha_confirmada=True,
    )
    try:
        vt = julgar_ficha(regua.chave, raiz, opcoes=opcoes)
    except ErroExecutorTestes as exc:
        raise Recusa(
            exc.saida,
            exc.codigo,
            onde="executor-de-testes",
            recebido=regua.chave,
            regra=_REGRA_TESTE,
            cura=exc.detalhe,
        ) from exc

    return (
        VereditoItem(
            alvo=vt.alvo,
            resultado=vt.resultado,
            constatacao=vt.constatacao,
            apontamentos=traduzir_apontamentos(vt.apontamentos),
            modo=vt.modo,
            quesito=vt.quesito,
            motor=vt.motor,
            versao_servico=vt.versao_servico,
            versao_regua=regua.versao,
        ),
    )
