"""`descobrir` — verbo de descoberta no acervo (#2952, arq:0085 §2).

`spec_leitura-do-conhecimento.md` §0, §2, §3, §5.

Contrato:
  descobrir(assunto: str,
            eixos: list[str] = ["titulo", "conceito", "subdominio"],
            k: int = 8) -> Envelope

Regras duras (arq:0085 §5 + §3):
1. Varre os TRÊS eixos e devolve a UNIÃO (OR entre eixos), não a interseção.
2. Cada obra no envelope MARCA por qual(is) eixo(s) entrou em `itens[].expansao`
   ({conceito_origem, aresta, familia}).
3. Dedupe por digest/id (spec §4): obra que entra por 2 eixos aparece 1 vez, com
   os 2 eixos marcados.
4. Saída = payload único com procedência completa; a âncora citável é projeção.
5. Fonte que não alcança o vivo responde indeterminavel/fonte-nao-indexada, nunca zero (§4).

Verbo fino desde #2957 (arq:0089 §2, arq:0090): a varredura multi-eixo (normalização,
radicais, união, dedupe, marcação de casamento) migrou para `motor_acervo/acervo_consulta.py`,
do outro lado de `GET /acervo/descoberta`. Este módulo só chama a rota (via
`adaptadores.motor_acervo_rest`) e empacota cada item no Envelope — o contrato de dado
do verbo não mudou (F9), mudou de onde o dado vem. `acervo_leitor.py` foi removido.
"""

from __future__ import annotations

import hashlib
import os
from typing import Sequence

from .adaptadores.base import FonteIndisponivel
from .adaptadores.motor_acervo_rest import descoberta as _descoberta_http
from .cache import Cache, SemCache, digest_consulta
from .disjuntor import Painel
from .envelope import (
    Casamento,
    Causa,
    Cobertura,
    ContratoViolado,
    Envelope,
    Expansao,
    Item,
    LinhaFonte,
    Procedencia,
    Versao,
    VersaoTipo,
    linha_disjuntor_aberto,
)
from .fontes import Fonte
from .pep import PEP, recusa_por_concessao

EIXOS_VALIDOS = ("titulo", "conceito", "subdominio")
EIXOS_PADRAO = list(EIXOS_VALIDOS)


def _objeto_id(objeto: str | None) -> str:
    return str(objeto or "").removeprefix("acervo/").removeprefix("pessoal/")


def descobrir(
    assunto: str,
    eixos: Sequence[str] | None = None,
    k: int = 8,
    sujeito: str | None = None,
    pep: PEP | None = None,
    cache: Cache | None = None,
    painel: Painel | None = None,
    http=None,
) -> Envelope:
    """Descobre o que o acervo tem sobre um assunto por varredura multi-eixo.

    Devolve a UNIÃO (OR) dos eixos consultados, marcando por quais eixos cada obra entrou.
    `http` é o ponto de injeção do transporte (mesmo desenho de `AdaptadorAcervo`).
    """
    assunto = (assunto or "").strip()
    if not assunto:
        return Envelope(linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.VAZIA)])

    if eixos is None:
        eixos_consultados = list(EIXOS_PADRAO)
    else:
        eixos_consultados = [str(e).strip().lower() for e in eixos if str(e).strip()]
        for e in eixos_consultados:
            if e not in EIXOS_VALIDOS:
                raise ContratoViolado(
                    f"eixo {e!r} fora do catálogo de eixos (aceitos: {', '.join(EIXOS_VALIDOS)})"
                )

    if not eixos_consultados:
        return Envelope(linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.VAZIA)])

    # 1. Disjuntor (primeiro: disjuntor aberto responde em 0 ms)
    if painel is not None and not painel[Fonte.ACERVO].permite():
        return Envelope(linhas=[linha_disjuntor_aberto(Fonte.ACERVO)])

    # 2. PEP por fonte
    sujeito_resolvido = sujeito or os.environ.get("PF_CADEIRA") or os.environ.get("USER") or "claudinho"
    _pep = pep or PEP()
    negativas = _pep.autoriza(sujeito=sujeito_resolvido, pedidos=[Fonte.ACERVO], acao="rag_buscar")
    if negativas:
        return recusa_por_concessao([Fonte.ACERVO], negativas)

    # 3. Cache lookup
    chave_cache = ""
    filtros_canon = {"eixos": sorted(eixos_consultados)}
    if cache is not None:
        try:
            chave_cache = digest_consulta(assunto, filtros_canon, k, "nenhum")
            hit = cache.le(Fonte.ACERVO, chave_cache)
            if hit is not None:
                return Envelope(linhas=[hit.linha], itens=hit.itens)
        except SemCache:
            pass

    # 4. Chamada à rota REST do motor_acervo
    try:
        payload = _descoberta_http(assunto, eixos_consultados, k, http=http)
    except FonteIndisponivel as e:
        if painel is not None:
            painel[Fonte.ACERVO].registra_falha()
        return Envelope(
            linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.FONTE_NAO_INDEXADA,
                               causa=e.causa)]
        )
    except Exception:
        if painel is not None:
            painel[Fonte.ACERVO].registra_falha()
        return Envelope(
            linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.FONTE_NAO_INDEXADA,
                               causa=Causa.FORA_DO_AR)]
        )

    if painel is not None:
        painel[Fonte.ACERVO].registra_sucesso()

    itens_payload = (payload or {}).get("itens") or []

    # 5. Nenhum item -> envelope vazio
    if not itens_payload:
        env_vazio = Envelope(linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.VAZIA)])
        if cache is not None and chave_cache:
            try:
                from .adaptadores.base import Resultado

                cache.grava(Fonte.ACERVO, chave_cache, Resultado(linha=env_vazio.linhas[0]))
            except SemCache:
                pass
        return env_vazio

    # 6. Empacota os itens já resolvidos e ordenados no Envelope
    itens: list[Item] = []
    for it in itens_payload[:k]:
        chave = f"acervo:{_objeto_id(it.get('objeto'))}"
        digest = hashlib.sha256(f"{it['obra_id']}:{it['titulo']}".encode()).hexdigest()[:16]
        versao = Versao(tipo=VersaoTipo.DIGEST, valor=digest[:12])
        exp = it.get("expansao") or {}
        trilha = (f"{it['dominio']}/{it['subdominio']}" if it.get("dominio") and it.get("subdominio")
                 else (it.get("dominio") or ""))
        ref = it["titulo"] + (f" — {trilha}" if trilha else "")
        itens.append(
            Item(
                procedencia=Procedencia(fonte=Fonte.ACERVO, chave=chave, versao=versao, digest=digest),
                ref=ref,
                casamento=Casamento.EXATO if it.get("casamento") == "exato" else Casamento.APROXIMADO,
                expansao=Expansao(conceito_origem=exp.get("conceito_origem", assunto),
                                  aresta=exp.get("aresta", ""), familia=exp.get("familia", "descoberta")),
            )
        )

    env = Envelope(
        linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.NAO_CALIBRADA)],
        itens=itens,
    )

    if cache is not None and chave_cache:
        try:
            from .adaptadores.base import Resultado

            cache.grava(Fonte.ACERVO, chave_cache, Resultado(linha=env.linhas[0], itens=env.itens))
        except SemCache:
            pass

    return env


__all__ = ["EIXOS_PADRAO", "EIXOS_VALIDOS", "descobrir"]
