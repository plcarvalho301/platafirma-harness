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

Verbo fino desde #2957 (arq:0089 §2, arq:0090): a escada de degraus e o casamento de
obra por título/arquivo migraram para `motor_acervo/acervo_consulta.py`, do outro lado
de `GET /acervo/obras/{obra_id}/situacao`. Este módulo só chama a rota (via
`adaptadores.motor_acervo_rest`) e empacota a resposta no Envelope — o contrato de dado
do verbo não mudou (F9), mudou de onde o dado vem. `acervo_leitor.py` foi removido: não
sobra leitor de disco no módulo.
"""

from __future__ import annotations

import json
import os

from .adaptadores.base import FonteIndisponivel
from .adaptadores.motor_acervo_rest import situacao_obra as _situacao_obra_http
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


def _objeto_id(objeto: str | None) -> str:
    return str(objeto or "").removeprefix("acervo/").removeprefix("pessoal/")


def situacao(
    obra: str,
    sujeito: str | None = None,
    pep: PEP | None = None,
    cache: Cache | None = None,
    painel: Painel | None = None,
    http=None,
) -> Envelope:
    """Verifica a situação viva de uma obra na escada do acervo.

    `http` é o ponto de injeção do transporte (mesmo desenho de `AdaptadorAcervo`) —
    os testes de contrato passam um cliente falso em vez de sair à rede.
    """
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

    # 4. Chamada à rota REST do motor_acervo
    try:
        payload = _situacao_obra_http(obra_query, http=http)
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

    # 5. Obra não encontrada -> envelope vazio (a API respondeu 404)
    if payload is None:
        env_vazio = Envelope(linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.VAZIA)])
        if cache is not None and chave_cache:
            try:
                from .adaptadores.base import Resultado

                cache.grava(Fonte.ACERVO, chave_cache, Resultado(linha=env_vazio.linhas[0]))
            except SemCache:
                pass
        return env_vazio

    # 6. Empacota o payload já resolvido no Envelope
    conteudo = {
        "servivel": payload["servivel"],
        "desde": payload["desde"],
        "impressao_id": payload["impressao_id"],
        "degrau": payload["degrau"],
    }
    conteudo_json = json.dumps(conteudo, ensure_ascii=False)

    chave = f"acervo:{_objeto_id(payload.get('objeto'))}"
    versao_val = (payload.get("impressao_id") or payload.get("carimbo") or "sem-versao")[:12]
    proc = Procedencia(fonte=Fonte.ACERVO, chave=chave,
                       versao=Versao(tipo=VersaoTipo.DIGEST, valor=versao_val))
    casamento = (Casamento.EXATO if payload.get("casamento") == "exato"
                else Casamento.APROXIMADO)

    item = Item(procedencia=proc, conteudo=conteudo_json, casamento=casamento)

    env = Envelope(
        linhas=[LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.NAO_CALIBRADA,
                           carimbo=payload.get("carimbo"))],
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
