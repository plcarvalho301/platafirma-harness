"""`situacao` — verbo de verificação de estado de serviço de obra (#2953, arq:0085 §2).

`spec_leitura-do-conhecimento.md` §0, §2, §4, §10.6.

Contrato:
  situacao(obra: str) -> Envelope   # payload {servivel, desde, impressao_id, degrau}

Regras duras (arq:0085 §4 + §2):
1. Lê a CADEIA VIVA (impressão → estado de serviço), não retrato agregado.
2. Fonte que não alcança o vivo responde indeterminavel/fonte-nao-indexada, NUNCA zero (§4).
3. degrau mapeia na tabela de estados do conceito (spec §10.6: ancorado ·
   declarado-não-servindo · sem-obra-não-julgado · órfão).
4. Mais leve que descobrir; mesma biblioteca, mesmo envelope.
"""

from __future__ import annotations

import json
import os

from .acervo_leitor import CatalogoAcervo, ObraInfo, carrega_catalogo, normaliza_termo
from .adaptadores.base import FonteIndisponivel
from .cache import Cache, SemCache, digest_consulta
from .disjuntor import Painel
from .envelope import (
    Casamento,
    Causa,
    Cobertura,
    Envelope,
    Item,
    LinhaFonte,
    Procedencia,
    Versao,
    VersaoTipo,
    linha_disjuntor_aberto,
)
from .fontes import Fonte
from .pep import PEP, recusa_por_concessao
from .resolvedor import Degrau, EstadoConceito

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))


def situacao(
    obra: str,
    sujeito: str | None = None,
    catalogo: CatalogoAcervo | None = None,
    pep: PEP | None = None,
    cache: Cache | None = None,
    painel: Painel | None = None,
    raiz: str = RAIZ,
) -> Envelope:
    """Verifica a situação viva de uma obra na escada do acervo."""
    obra_query = (obra or "").strip()
    if not obra_query:
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
    if cache is not None:
        try:
            chave_cache = digest_consulta(obra_query, {"tipo": "situacao"}, 1, "nenhum")
            hit = cache.le(Fonte.ACERVO, chave_cache)
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

    # 5. Localização da obra na cadeia viva
    obra_achada: ObraInfo | None = None
    query_norm = normaliza_termo(obra_query)

    # Busca exata por ID
    if obra_query in cat.obras:
        obra_achada = cat.obras[obra_query]
    elif query_norm in cat.obras_por_titulo:
        obra_achada = cat.obras_por_titulo[query_norm][0]
    else:
        # Busca aproximada por título ou arquivo
        for o in cat.obras.values():
            tit_norm = normaliza_termo(o.titulo)
            arq_norm = normaliza_termo(o.arquivo or "")
            if query_norm == tit_norm or (o.arquivo and query_norm == arq_norm):
                obra_achada = o
                break
            if query_norm in tit_norm or (o.arquivo and query_norm in arq_norm):
                obra_achada = o
                break

    if obra_achada is None:
        # Obra não encontrada no vivo -> resposta vazia
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

                cache.grava(Fonte.ACERVO, chave_cache, Resultado(linha=env_vazio.linhas[0]))
            except SemCache:
                pass
        return env_vazio

    # 6. Avaliação de estado da cadeia viva
    # Classificação
    classificado = bool(
        obra_achada.dominio or obra_achada.subdominio or cat.obra_trata_de.get(obra_achada.id)
    )

    impressoes = cat.impressoes_por_obra.get(obra_achada.id, [])
    impressao_servindo = next((imp for imp in impressoes if imp.estado == "servindo"), None)

    if not classificado:
        degrau = str(EstadoConceito.ORFAO)
        servivel = impressao_servindo is not None
        desde = impressao_servindo.criada_em if impressao_servindo else None
        impressao_id = impressao_servindo.id if impressao_servindo else None
    elif impressao_servindo is not None:
        degrau = str(EstadoConceito.ANCORADO)
        servivel = True
        desde = impressao_servindo.criada_em
        impressao_id = impressao_servindo.id
    elif impressoes:
        degrau = str(EstadoConceito.DECLARADO_NAO_SERVINDO)
        servivel = False
        desde = None
        impressao_id = impressoes[0].id
    else:
        degrau = str(EstadoConceito.SEM_OBRA_NAO_JULGADO)
        servivel = False
        desde = None
        impressao_id = None

    payload = {
        "servivel": servivel,
        "desde": desde,
        "impressao_id": impressao_id,
        "degrau": degrau,
    }

    versao_val = (impressao_id or cat.carimbo.removeprefix("acervo:") or "sem-versao")[:12]
    proc = Procedencia(
        fonte=Fonte.ACERVO,
        chave=f"acervo:{obra_achada.objeto_id}",
        versao=Versao(tipo=VersaoTipo.DIGEST, valor=versao_val),
    )

    conteudo_json = json.dumps(payload, ensure_ascii=False)
    ref = f"{obra_achada.titulo} — {degrau} (servivel={servivel})"

    item = Item(
        procedencia=proc,
        conteudo=conteudo_json,
        casamento=Casamento.EXATO if query_norm == normaliza_termo(obra_achada.titulo) else Casamento.APROXIMADO,
    )

    env = Envelope(
        linhas=[
            LinhaFonte(
                fonte=Fonte.ACERVO,
                cobertura=Cobertura.NAO_CALIBRADA,
                carimbo=cat.carimbo,
            )
        ],
        itens=[item],
    )

    if cache is not None and chave_cache:
        try:
            from .adaptadores.base import Resultado

            cache.grava(Fonte.ACERVO, chave_cache, Resultado(linha=env.linhas[0], itens=env.itens))
        except SemCache:
            pass

    return env


__all__ = ["situacao"]
