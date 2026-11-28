"""suite — delegador da `suíte de testes` pelo ato `despachar` (card #4455, t6).

Implementa `DelegadorSuite` do verificador despachando `motor:harness:suite-de-testes` via
`despacho.cliente` (sem passar pelo motor de lote). Devolve o laudo da suíte convertido em
`VereditoEmitido`, propaga saída `3` (`dependencia-sem-resposta`) quando o `despachar` não
responde e propaga saída `5` (`tempo-esgotado`) quando a suíte excede o prazo do `verificar`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from leitura.recusa import Recusa
from suite.executor import ApontamentoTeste, VereditoTeste
from suite.motor import ErroLaudoSuite
from verificador.executores import traduzir_apontamentos
from verificador.tipos import (
    MOTOR_SUITE_TESTES,
    VERSAO_CONTRATO,
    VereditoEmitido,
    VereditoItem,
)

from .cliente import ConfigClienteDespacho, PedidoClienteDespacho, despachar_pelo_core

SAIDA_OK = 0
SAIDA_DEPENDENCIA = 3
REGRA_DELEGACAO_SUITE = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"


def _reconstruir_veredito_teste(bruto: Mapping[str, Any]) -> VereditoTeste:
    apontamentos = tuple(
        ApontamentoTeste(
            item=str(a.get("item") or ""),
            alvo=str(a.get("alvo") or ""),
            lugar=str(a.get("lugar") or ""),
            exigencia=str(a.get("exigencia") or ""),
            severidade=str(a.get("severidade") or "bloqueante"),
            cura=str(a.get("cura") or ""),
        )
        for a in (bruto.get("apontamentos") or ())
        if isinstance(a, Mapping)
    )
    return VereditoTeste(
        alvo=str(bruto.get("alvo") or ""),
        quesito=str(bruto.get("quesito") or ""),
        resultado=str(bruto.get("resultado") or "nao-sei"),
        constatacao=str(bruto.get("constatacao") or "inconclusivo"),
        modo=str(bruto.get("modo") or "enquadrou"),
        apontamentos=apontamentos,
        motor=str(bruto.get("motor") or ""),
        versao_servico=str(bruto.get("versao_servico") or ""),
        casos_total=int(bruto.get("casos_total") or 0),
        casos_quarentena=int(bruto.get("casos_quarentena") or 0),
    )


def _extrair_erro_retorno(dados: Mapping[str, Any], rc: int) -> tuple[str, str]:
    bloco_erro = dados.get("erro")
    if isinstance(bloco_erro, Mapping):
        codigo = str(bloco_erro.get("codigo") or "falha-suite")
        cura = str(bloco_erro.get("cura") or f"suíte encerrou com saída {rc}")
        return codigo, cura
    codigo_topo = str(dados.get("codigo") or "falha-suite")
    cura_topo = str(dados.get("cura") or f"suíte encerrou com saída {rc}")
    return codigo_topo, cura_topo


def _converter_laudo_em_veredito(
    dados: Mapping[str, Any],
    chaves_fichas: Sequence[str],
    alvo: str,
) -> VereditoEmitido:
    vereditos_brutos = dados.get("vereditos")
    resultado = str(dados.get("resultado") or "")
    constatacao = str(dados.get("constatacao") or "")
    motor = str(dados.get("motor") or MOTOR_SUITE_TESTES)
    versao_motor = str(dados.get("versao_motor") or "desenvolvimento")

    if not isinstance(vereditos_brutos, list) or not resultado or not constatacao:
        raise Recusa(
            SAIDA_DEPENDENCIA,
            "dependencia-sem-resposta",
            onde="suite-de-testes",
            recebido=str(dados),
            regra=REGRA_DELEGACAO_SUITE,
            cura="o motor suíte de testes devolveu payload sem os campos do laudo",
        )

    itens: list[VereditoItem] = []
    for bruto in vereditos_brutos:
        if not isinstance(bruto, Mapping):
            continue
        vt = _reconstruir_veredito_teste(bruto)
        itens.append(
            VereditoItem(
                alvo=f"{vt.alvo}::{vt.quesito}",
                resultado=vt.resultado,
                constatacao=vt.constatacao,
                apontamentos=traduzir_apontamentos(vt.apontamentos),
                modo=vt.modo,
                quesito=vt.quesito,
                motor=vt.motor,
                versao_servico=vt.versao_servico,
            )
        )

    todos_apontamentos = tuple(ap for item in itens for ap in item.apontamentos)
    chave_veredito = (
        f"{alvo}|{motor}@{versao_motor}|{'+'.join(chaves_fichas)}|casa:harness"
    )
    return VereditoEmitido(
        versao_contrato=VERSAO_CONTRATO,
        resultado=resultado,
        constatacao=constatacao,
        modo="enquadrou",
        quesito=tuple(chaves_fichas),
        chave=chave_veredito,
        motor=motor,
        itens=tuple(itens),
        apontamentos=todos_apontamentos,
    )


class DelegadorSuiteDespacho:
    """Implementação de produção de `DelegadorSuite` sobre o ato `despachar`."""

    def __init__(
        self,
        *,
        config_cliente: ConfigClienteDespacho | None = None,
        ident: Mapping[str, Any] | None = None,
    ) -> None:
        self._config = config_cliente
        self._ident = dict(ident or {})

    def despachar_suite(
        self, chaves_fichas: Sequence[str], arvore: Path, *, alvo: str, prazo_s: float
    ) -> VereditoEmitido:
        pedido = PedidoClienteDespacho(
            verbo_entrada="teste",
            alvo_classe="motor",
            alvo_chave=MOTOR_SUITE_TESTES,
            parametros={
                "chaves_fichas": list(chaves_fichas),
                "arvore": str(arvore),
                "alvo": alvo,
            },
            ident=self._ident,
            prazo_espera_s=prazo_s,
        )
        resp = despachar_pelo_core(pedido, config=self._config)

        if resp.exit_code != SAIDA_OK:
            codigo, cura = _extrair_erro_retorno(resp.dados, resp.exit_code)
            if resp.exit_code == SAIDA_DEPENDENCIA or codigo == "passo-dependencia-indisponivel":
                raise Recusa(
                    SAIDA_DEPENDENCIA,
                    "dependencia-sem-resposta",
                    onde="despachar",
                    recebido=", ".join(chaves_fichas),
                    regra=REGRA_DELEGACAO_SUITE,
                    cura=cura,
                )
            parciais_raw = resp.dados.get("vereditos_parciais")
            parciais = (
                tuple(
                    _reconstruir_veredito_teste(p)
                    for p in parciais_raw
                    if isinstance(p, Mapping)
                )
                if isinstance(parciais_raw, list)
                else ()
            )
            raise ErroLaudoSuite(resp.exit_code, codigo, cura, vereditos_parciais=parciais)

        return _converter_laudo_em_veredito(resp.dados, chaves_fichas, alvo)
