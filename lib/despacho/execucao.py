"""execucao — leitura de `<verbo> ler execucao <chave>` pelo evento `execucao` (card #4455, t6).

Lê o bruto exclusivamente por `oplog` (`dias_no_disco` e `ler`), devolve o estado mais recente
da execução com cada fase, o código de saída e a primeira linha do retorno, e recusa chave
inexistente com saída `1` e chave pertencente a outro sujeito com saída `4`.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import oplog
from leitura.recusa import Recusa

SAIDA_INEXISTENTE = 1
SAIDA_NEGADA = 4
REGRA_LEITURA_EXECUCAO = "ato:despachar §Acompanhamento assíncrono por ler execucao"


def _normalizar_fase(bruta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(bruta.get("id") or ""),
        "indice": int(bruta.get("indice") or 0),
        "verbo": str(bruta.get("verbo") or ""),
        "ato": str(bruta.get("ato") or ""),
        "estado": str(bruta.get("estado") or ""),
        "exit_code": bruta.get("exit_code"),
        "linha": str(bruta.get("linha") or ""),
        "harness_sha": str(bruta.get("harness_sha") or ""),
        "dur_ms": int(bruta.get("dur_ms") or 0),
    }


def _buscar_ultimo_evento_execucao(
    chave_execucao: str,
    diretorio_oplog: Path | None,
) -> dict[str, Any] | None:
    dias = list(oplog.dias_no_disco(diretorio_oplog))
    for dia in reversed(dias):
        ultimo_do_dia: dict[str, Any] | None = None
        for reg in oplog.ler(dia, diretorio_=diretorio_oplog):
            if reg.get("evento") == "execucao" and reg.get("execucao_id") == chave_execucao:
                ultimo_do_dia = reg
        if ultimo_do_dia is not None:
            return ultimo_do_dia
    return None


def ler_execucao(
    verbo_entrada: str,
    chave_execucao: str,
    *,
    sujeito: str,
    diretorio_oplog: Path | None = None,
) -> dict[str, Any]:
    """Lê o estado consolidado de `chave_execucao` para `verbo_entrada` e valida `sujeito`."""
    chave = chave_execucao.strip()
    verbo = verbo_entrada.strip()
    onde = f"{verbo} ler execucao" if verbo else "ler execucao"

    if not chave:
        raise Recusa(
            SAIDA_INEXISTENTE,
            "chave-inexistente",
            onde=onde,
            recebido=chave_execucao,
            regra=REGRA_LEITURA_EXECUCAO,
            cura="informe a chave da execução devolvida pelo ato despachar",
        )

    reg = _buscar_ultimo_evento_execucao(chave, diretorio_oplog)
    verbo_evento = str(reg.get("verbo_entrada") or "") if reg is not None else ""
    if reg is None or (verbo and verbo_evento and verbo_evento != verbo):
        raise Recusa(
            SAIDA_INEXISTENTE,
            "chave-inexistente",
            onde=onde,
            recebido=chave,
            regra=REGRA_LEITURA_EXECUCAO,
            cura=f"nenhuma execução '{chave}' encontrada para o verbo '{verbo}'",
        )

    dono = str(reg.get("sujeito") or "").strip()
    chamador = sujeito.strip()
    if not chamador or not dono or chamador != dono:
        raise Recusa(
            SAIDA_NEGADA,
            "acesso-negado",
            onde=onde,
            recebido=chave,
            regra=REGRA_LEITURA_EXECUCAO,
            cura="apenas o sujeito que disparou a execução pode consultar seu estado",
        )

    fases_brutas = reg.get("fases")
    fases = (
        [_normalizar_fase(f) for f in fases_brutas if isinstance(f, Mapping)]
        if isinstance(fases_brutas, list)
        else []
    )
    return {
        "execucao_id": chave,
        "alvo_classe": str(reg.get("alvo_classe") or ""),
        "alvo_chave": str(reg.get("alvo_chave") or ""),
        "verbo_entrada": verbo_evento,
        "estado": str(reg.get("estado") or ""),
        "exit_code": reg.get("exit_code"),
        "artefato_digest": reg.get("artefato_digest"),
        "dur_ms": reg.get("dur_ms"),
        "ts": str(reg.get("ts") or ""),
        "fases": fases,
    }
