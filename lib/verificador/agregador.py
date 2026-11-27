"""agregador — fecho do veredito agregado, chave de veredito e serialização (card #4454).

Aplica a regra de fecho entre alvos (`divergente` vence `inconclusivo`, que vence `conforme`),
mantém itens de `aviso` fora da alteração de resultado e formata a saída em texto ou JSON
versionado (`versao_contrato = 1`).
"""
from __future__ import annotations

import json
from collections.abc import Sequence

from .tipos import (
    VERSAO_CONTRATO,
    AlvoVerificado,
    AmbienteVerificacao,
    Apontamento,
    ReguaCasada,
    VereditoEmitido,
    VereditoItem,
)


def montar_chave_veredito(
    alvo_ref: str,
    servico_ref: str,
    regua_ref: str,
    ambiente: AmbienteVerificacao,
) -> str:
    """Identidade canônica do veredito: alvo@v | serviço@sha | régua@v | host:stack."""
    return f"{alvo_ref}|{servico_ref}|{regua_ref}|{ambiente.host}:{ambiente.stack}"


def _combinar_constatacoes(itens: Sequence[VereditoItem]) -> tuple[str, str]:
    if not itens:
        return "nao-sei", "inconclusivo"
    if any(i.constatacao == "divergente" or i.resultado == "nao" for i in itens):
        return "nao", "divergente"
    if any(i.constatacao == "inconclusivo" or i.resultado == "nao-sei" for i in itens):
        return "nao-sei", "inconclusivo"
    return "sim", "conforme"


def agregar_vereditos(
    regua_casada: ReguaCasada,
    alvos: Sequence[AlvoVerificado],
    itens: Sequence[VereditoItem],
    ambiente: AmbienteVerificacao,
) -> VereditoEmitido:
    """Agrega vereditos individuais de uma verificação única num `VereditoEmitido`."""
    resultado, constatacao = _combinar_constatacoes(itens)
    motor = itens[0].motor if itens and itens[0].motor else regua_casada.servico
    versao_serv = itens[0].versao_servico if itens and itens[0].versao_servico else "desenvolvimento"
    versao_regua = "+".join(f"{r.chave}@{r.versao}" for r in regua_casada.reguas)
    alvo_ref = ",".join(f"{a.chave}@{a.versao}" for a in alvos)

    chave_agregada = montar_chave_veredito(
        alvo_ref,
        f"{motor}@{versao_serv}",
        versao_regua,
        ambiente,
    )

    apontamentos: list[Apontamento] = []
    nao_julgados: list[str] = []
    for item in itens:
        apontamentos.extend(item.apontamentos)
        for nj in item.nao_julgados:
            if nj not in nao_julgados:
                nao_julgados.append(nj)

    quesito: str | tuple[str, ...] = (
        regua_casada.chaves[0] if len(regua_casada.chaves) == 1 else regua_casada.chaves
    )
    return VereditoEmitido(
        versao_contrato=VERSAO_CONTRATO,
        resultado=resultado,
        constatacao=constatacao,
        modo=itens[0].modo if itens else "enquadrou",
        quesito=quesito,
        chave=chave_agregada,
        motor=motor,
        itens=tuple(itens),
        apontamentos=tuple(apontamentos),
        nao_julgados=tuple(nao_julgados),
    )


def formatar_json(veredito: VereditoEmitido) -> str:
    """Serializa o `VereditoEmitido` no objeto contratual JSON de uma linha."""
    return json.dumps(veredito.como_dict(), ensure_ascii=False)


def formatar_texto(veredito: VereditoEmitido) -> str:
    """Renderiza o `VereditoEmitido` em texto legível para o terminal."""
    quesito_txt = (
        ", ".join(veredito.quesito)
        if isinstance(veredito.quesito, tuple)
        else veredito.quesito
    )
    linhas = [
        f"veredito: {veredito.resultado} ({veredito.constatacao}) · motor: {veredito.motor} · quesito: {quesito_txt}",
        f"chave: {veredito.chave}",
    ]
    for item in veredito.itens:
        linhas.append(f"  - {item.alvo}: {item.resultado} ({item.constatacao})")
        for ap in item.apontamentos:
            linhas.append(
                f"      [{ap.severidade}] {ap.item} ({ap.lugar}): {ap.exigencia} — cura: {ap.cura}"
            )
    if veredito.nao_julgados:
        linhas.append(f"nao-julgados: {', '.join(veredito.nao_julgados)}")
    return "\n".join(linhas)


def formatar_parciais_json(itens: Sequence[VereditoItem]) -> str:
    """Serializa apenas os vereditos individuais já olhados na saída 5 (sem veredito agregado)."""
    return json.dumps(
        {
            "versao_contrato": VERSAO_CONTRATO,
            "itens": [i.como_dict() for i in itens],
        },
        ensure_ascii=False,
    )


def formatar_parciais_texto(itens: Sequence[VereditoItem]) -> str:
    """Renderiza apenas os vereditos individuais já olhados na saída 5 (sem veredito agregado)."""
    linhas: list[str] = []
    for item in itens:
        linhas.append(f"  - {item.alvo}: {item.resultado} ({item.constatacao})")
        for ap in item.apontamentos:
            linhas.append(
                f"      [{ap.severidade}] {ap.item} ({ap.lugar}): {ap.exigencia} — cura: {ap.cura}"
            )
    return "\n".join(linhas)
