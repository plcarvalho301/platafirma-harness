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
"""

from __future__ import annotations

import hashlib
import os
from typing import Sequence

from .acervo_leitor import (
    CatalogoAcervo,
    ObraInfo,
    carrega_catalogo,
    normaliza_termo,
    radicais_de,
)
from .adaptadores.base import FonteIndisponivel
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

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
EIXOS_VALIDOS = ("titulo", "conceito", "subdominio")
EIXOS_PADRAO = list(EIXOS_VALIDOS)


def descobrir(
    assunto: str,
    eixos: Sequence[str] | None = None,
    k: int = 8,
    sujeito: str | None = None,
    catalogo: CatalogoAcervo | None = None,
    pep: PEP | None = None,
    cache: Cache | None = None,
    painel: Painel | None = None,
    raiz: str = RAIZ,
) -> Envelope:
    """Descobre o que o acervo tem sobre um assunto por varredura multi-eixo.

    Devolve a UNIÃO (OR) dos eixos consultados, marcando por quais eixos cada obra entrou.
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
            hit = cache.obtem(Fonte.ACERVO, chave_cache)
            if hit is not None:
                return Envelope(linhas=[hit.linha], itens=hit.itens)
        except SemCache:
            pass

    # 4. Leitura do acervo
    try:
        cat = catalogo if catalogo is not None else carrega_catalogo(raiz)
    except FonteIndisponivel as e:
        if painel is not None:
            painel[Fonte.ACERVO].registra_falha()
        return Envelope(
            linhas=[
                LinhaFonte(
                    fonte=Fonte.ACERVO,
                    cobertura=Cobertura.FONTE_NAO_INDEXADA,
                    causa=e.causa,
                )
            ]
        )
    except Exception:
        if painel is not None:
            painel[Fonte.ACERVO].registra_falha()
        return Envelope(
            linhas=[
                LinhaFonte(
                    fonte=Fonte.ACERVO,
                    cobertura=Cobertura.FONTE_NAO_INDEXADA,
                    causa=Causa.FORA_DO_AR,
                )
            ]
        )

    if painel is not None:
        painel[Fonte.ACERVO].registra_sucesso()

    # 5. Varredura multi-eixo
    assunto_norm = normaliza_termo(assunto)
    termos = [t for t in assunto_norm.split() if t]
    rads_assunto = radicais_de(assunto)

    # obra_id -> set of axis names
    obras_encontradas: dict[str, set[str]] = {}
    casamento_exato: dict[str, bool] = {}

    # Eixo: titulo
    if "titulo" in eixos_consultados:
        for oid, obra in cat.obras.items():
            tit_norm = normaliza_termo(obra.titulo)
            arq_norm = normaliza_termo(obra.arquivo or "")
            pub_norm = normaliza_termo(obra.publicacao or "")
            rads_tit = radicais_de(obra.titulo)
            if assunto_norm == tit_norm or (obra.arquivo and assunto_norm == arq_norm):
                obras_encontradas.setdefault(oid, set()).add("titulo")
                casamento_exato[oid] = True
            elif assunto_norm in tit_norm or assunto_norm in arq_norm or assunto_norm in pub_norm:
                obras_encontradas.setdefault(oid, set()).add("titulo")
                casamento_exato.setdefault(oid, False)
            elif termos and all(t in tit_norm for t in termos):
                obras_encontradas.setdefault(oid, set()).add("titulo")
                casamento_exato.setdefault(oid, False)
            elif rads_assunto and all(r in rads_tit for r in rads_assunto):
                obras_encontradas.setdefault(oid, set()).add("titulo")
                casamento_exato.setdefault(oid, False)

    # Eixo: conceito
    if "conceito" in eixos_consultados:
        conceitos_casados = set()
        for slug, conc in cat.conceitos.items():
            rot_norm = normaliza_termo(conc.rotulo)
            slug_norm = normaliza_termo(conc.slug)
            outros = [normaliza_termo(o) for o in conc.outros_rotulos]
            rads_rot = radicais_de(conc.rotulo)
            rads_def = radicais_de(conc.definicao)

            if (
                assunto_norm == rot_norm
                or assunto_norm == slug_norm
                or any(assunto_norm == o for o in outros)
            ):
                conceitos_casados.add((slug, True))
            elif (
                assunto_norm in rot_norm
                or assunto_norm in slug_norm
                or any(assunto_norm in o for o in outros)
                or (termos and all(t in rot_norm for t in termos))
                or (rads_assunto and all(r in rads_rot for r in rads_assunto))
                or (termos and all(t in normaliza_termo(conc.definicao) for t in termos))
                or (rads_assunto and all(r in rads_def for r in rads_assunto))
            ):
                conceitos_casados.add((slug, False))

        for c_slug, exato in conceitos_casados:
            for oid in cat.conceito_obras.get(c_slug, ()):
                obras_encontradas.setdefault(oid, set()).add("conceito")
                if exato:
                    casamento_exato[oid] = True
                else:
                    casamento_exato.setdefault(oid, False)

    # Eixo: subdominio
    if "subdominio" in eixos_consultados:
        subdominios_casados = set()
        for slug, sub in cat.subdominios.items():
            rot_norm = normaliza_termo(sub.rotulo)
            slug_norm = normaliza_termo(sub.slug)
            rec_norm = normaliza_termo(sub.recorte)
            rads_rot = radicais_de(sub.rotulo)
            rads_rec = radicais_de(sub.recorte)

            if assunto_norm == rot_norm or assunto_norm == slug_norm:
                subdominios_casados.add((slug, True))
            elif (
                assunto_norm in rot_norm
                or assunto_norm in slug_norm
                or assunto_norm in rec_norm
                or (termos and all(t in rot_norm for t in termos))
                or (rads_assunto and all(r in rads_rot for r in rads_assunto))
                or (termos and all(t in rec_norm for t in termos))
                or (rads_assunto and all(r in rads_rec for r in rads_assunto))
            ):
                subdominios_casados.add((slug, False))

        for s_slug, exato in subdominios_casados:
            for oid in cat.subdominio_obras.get(s_slug, ()):
                obras_encontradas.setdefault(oid, set()).add("subdominio")
                if exato:
                    casamento_exato[oid] = True
                else:
                    casamento_exato.setdefault(oid, False)

    if not obras_encontradas:
        env_vazio = Envelope(
            linhas=[
                LinhaFonte(
                    fonte=Fonte.ACERVO,
                    cobertura=Cobertura.VAZIA,
                    carimbo=cat.carimbo,
                )
            ]
        )
        if cache is not None and chave_cache:
            try:
                from .adaptadores.base import Resultado

                cache.grava(Fonte.ACERVO, cat.carimbo, chave_cache, Resultado(linha=env_vazio.linhas[0]))
            except SemCache:
                pass
        return env_vazio

    # 6. Montagem de itens com deduplicação e marcação de eixos
    itens: list[Item] = []
    ordenados = sorted(
        obras_encontradas.keys(),
        key=lambda oid: (
            -len(obras_encontradas[oid]),
            not casamento_exato.get(oid, False),
            cat.obras[oid].titulo,
        ),
    )

    carimbo_versao = cat.carimbo.removeprefix("acervo:")[:12] if cat.carimbo else "v1"

    for oid in ordenados[:k]:
        obra = cat.obras[oid]
        eixos_marcados = sorted(obras_encontradas[oid])
        aresta = ", ".join(eixos_marcados)
        expansao = Expansao(
            conceito_origem=assunto,
            aresta=aresta,
            familia="descoberta",
        )
        chave = f"acervo:{obra.objeto_id}"
        versao = Versao(tipo=VersaoTipo.DIGEST, valor=carimbo_versao)
        digest = hashlib.sha256(f"{obra.id}:{obra.titulo}".encode()).hexdigest()[:16]
        casamento = Casamento.EXATO if casamento_exato.get(oid, False) else Casamento.APROXIMADO

        trilha = f"{obra.dominio}/{obra.subdominio}" if obra.dominio and obra.subdominio else (obra.dominio or "")
        ref = f"{obra.titulo}" + (f" — {trilha}" if trilha else "")

        itens.append(
            Item(
                procedencia=Procedencia(
                    fonte=Fonte.ACERVO,
                    chave=chave,
                    versao=versao,
                    digest=digest,
                ),
                ref=ref,
                casamento=casamento,
                expansao=expansao,
            )
        )

    env = Envelope(
        linhas=[
            LinhaFonte(
                fonte=Fonte.ACERVO,
                cobertura=Cobertura.NAO_CALIBRADA,
                carimbo=cat.carimbo,
            )
        ],
        itens=itens,
    )

    if cache is not None and chave_cache:
        try:
            from .adaptadores.base import Resultado

            cache.grava(Fonte.ACERVO, cat.carimbo, chave_cache, Resultado(linha=env.linhas[0], itens=env.itens))
        except SemCache:
            pass

    return env


__all__ = ["EIXOS_PADRAO", "EIXOS_VALIDOS", "descobrir"]
