"""nome.py — resolução de nome, cortes com qualificador, candidatos e alvos de ligação (story 4427, t9 e t10).

Contratos:
- platafirma-casa@referencias/instancias/verbo/busca.md, «Como um nome vira ficha»,
  «O que o verbo faz com o que voltou» e «O que o ler faz com a consulta por nome».
"""
from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from leitura import casa_db, resolvedor
from leitura.recusa import Recusa, Recusas

from .pedido import FILTROS_DISPONIVEIS, Pedido

REGRA_NOME = "verbo:busca §Como um nome vira ficha"
REGRA_PLANO = "verbo:busca §Como a condição vira plano"
_PREPOSICOES = frozenset({"de", "da", "do", "das", "dos"})
_RE_PALAVRA_ESPACO = re.compile(r"\S+")


@dataclass(frozen=True)
class CorteQualificador:
    nucleo: str
    qualificador: str


def gerar_cortes_qualificador(termo: str) -> list[CorteQualificador]:
    """Gera cortes nas palavras `de`, `da`, `do`, `das` e `dos`, do núcleo mais longo ao mais curto."""
    partes = list(_RE_PALAVRA_ESPACO.finditer(termo))
    cortes: list[CorteQualificador] = []
    for idx in range(len(partes) - 2, 0, -1):
        m = partes[idx]
        if m.group(0).lower() in _PREPOSICOES:
            nucleo = termo[: m.start()].strip()
            qualificador = termo[m.end() :].strip()
            if nucleo and qualificador:
                cortes.append(CorteQualificador(nucleo=nucleo, qualificador=qualificador))
    return cortes


def gerar_subtermos_aproximados(termo: str) -> list[str]:
    """Extrai cada par de palavras vizinhas e cada palavra do termo, sem repetir o termo inteiro."""
    palavras = re.findall(r"\w+", termo)
    termo_limpo = " ".join(palavras).lower()
    vistos: set[str] = {termo_limpo, termo.strip().lower()}
    subtermos: list[str] = []

    for i in range(len(palavras) - 1):
        par = f"{palavras[i]} {palavras[i + 1]}"
        k = par.lower()
        if k not in vistos and any(ch.isalnum() for ch in par):
            vistos.add(k)
            subtermos.append(par)

    for p in palavras:
        k = p.lower()
        if k not in vistos and any(ch.isalnum() for ch in p):
            vistos.add(k)
            subtermos.append(p)

    return subtermos


def _agrupar_por_ord(linhas: Sequence[dict]) -> dict[int, list[dict]]:
    grupos: dict[int, list[dict]] = {}
    for ln in linhas:
        grupos.setdefault(int(ln["ord"]), []).append(ln)
    return grupos


def _fichas_do_grupo(grupo: Sequence[dict]) -> list[dict]:
    vistas: set[str] = set()
    saida: list[dict] = []
    for ln in grupo:
        ch = ln.get("chave")
        if ch and ch not in vistas:
            vistas.add(str(ch))
            saida.append(ln)
    return saida


def resolver_alvo_ligacao(
    sessao: casa_db.SessaoLeitura,
    alvo_txt: str,
    *,
    onde: str,
    classe_restrita: str | None = None,
) -> tuple[resolvedor.Ficha | None, Recusa | None]:
    """Resolve um alvo como chave humana exata primeiro e depois pelos quatro passos do nome.

    Quando `classe_restrita` vem (como em coluna `capacidade` -> classe `capacidade`),
    filtra as fichas candidatas pelas daquela classe.
    """
    exata = sessao.ficha_da_chave(alvo_txt)
    if exata is not None and (classe_restrita is None or exata.classe == classe_restrita):
        return exata, None

    res = sessao.resolver_nomes([alvo_txt])
    if 1 in res.ords_negados:
        raise Recusa(
            4,
            "acesso-negado",
            onde=onde,
            recebido=alvo_txt,
            regra=REGRA_NOME,
            cura=f"acesso negado para ler as fichas nomeadas por «{alvo_txt}»",
            proximo="busca consultar --classe shape",
        )
    achadas = _fichas_do_grupo(res.linhas)
    if classe_restrita is not None:
        achadas = [ln for ln in achadas if ln.get("classe") == classe_restrita]

    if not achadas:
        sugestao = f"busca consultar --classe {shlex.quote(classe_restrita or 'shape')}"
        return None, Recusa(
            2,
            "alvo-inexistente",
            onde=onde,
            recebido=alvo_txt,
            regra=REGRA_PLANO,
            cura=f"«{alvo_txt}» não é chave nem nome de ficha nenhuma",
            proximo=sugestao,
        )

    if len(achadas) > 1:
        lista_cand = ", ".join(f"{ln['chave']} ({ln['classe']})" for ln in achadas)
        primeira_chave = str(achadas[0]["chave"])
        return None, Recusa(
            2,
            "alvo-ambiguo",
            onde=onde,
            recebido=alvo_txt,
            regra=REGRA_PLANO,
            cura=f"«{alvo_txt}» nomeia {len(achadas)} fichas: {lista_cand}; passe a chave exata",
            proximo=f"busca consultar {shlex.quote(primeira_chave)}",
        )

    ficha_unica = sessao.ficha_da_chave(str(achadas[0]["chave"]))
    if ficha_unica is None:
        raise Recusa(
            5,
            "falha-interna",
            onde=onde,
            recebido=alvo_txt,
            regra=REGRA_PLANO,
            cura="a resolução do alvo devolveu chave ausente de casa.ficha",
            proximo="busca consultar --classe shape",
        )
    return ficha_unica, None


def _buscar_candidatos_aproximados(sessao: casa_db.SessaoLeitura, termo: str) -> list[dict[str, Any]]:
    subtermos = gerar_subtermos_aproximados(termo)
    if not subtermos:
        return []
    res = sessao.resolver_nomes(subtermos)
    vistos: set[str] = set()
    candidatos: list[dict[str, Any]] = []
    for ln in res.linhas:
        ch = ln.get("chave")
        if ch and str(ch) not in vistos:
            vistos.add(str(ch))
            candidatos.append({
                "chave": str(ch),
                "classe": str(ln["classe"]),
                "rotulo": ln.get("rotulo"),
            })
    return candidatos


@dataclass(frozen=True)
class _CorteResolvido:
    termo: str
    corte: CorteQualificador
    classe_slug: str
    fichas_qualificador: Sequence[dict]


def _executar_condicao_de_corte(
    sessao: casa_db.SessaoLeitura,
    resolvido: _CorteResolvido,
    *,
    tamanho_pagina: int = 50,
) -> dict[str, Any]:
    classe_slug = resolvido.classe_slug
    classe_uuid = sessao.uuid_da_classe(classe_slug)
    if classe_uuid is None:
        raise Recusa(5, "falha-interna", onde="classe", recebido=classe_slug, regra=REGRA_NOME,
                     cura=f"a classe {classe_slug} sumiu do catálogo no retrato",
                     proximo="busca consultar --classe shape")
    sessao.exigir_autorizacao(classe_slug)

    alvos_uuids: list[str] = []
    chaves_qual: list[str] = []
    for fq in resolvido.fichas_qualificador:
        ch = str(fq["chave"])
        f_obj = sessao.ficha_da_chave(ch)
        if f_obj is not None:
            alvos_uuids.append(f_obj.uuid)
            chaves_qual.append(ch)

    pred = casa_db.PredicadoLigacao(
        n=1,
        propriedade_id=None,
        sentido="qualquer",
        alvos=tuple(alvos_uuids),
        passos=1,
    )
    resultado_db = sessao.consultar_fichas(
        {"classes_uuids": [classe_uuid], "ligacoes": [pred]},
        tamanho_pagina=tamanho_pagina,
    )
    return {
        "tipo_resultado": "condicao-por-nome",
        "termo": resolvido.termo,
        "classe": classe_slug,
        "condicao": {
            "nucleo": resolvido.corte.nucleo,
            "qualificador": resolvido.corte.qualificador,
            "chaves": chaves_qual,
        },
        "consulta": resultado_db,
    }


def consultar_por_nome(
    sessao: casa_db.SessaoLeitura,
    ped: Pedido,
    *,
    tamanho_pagina: int = 50,
) -> dict[str, Any]:
    """Resolve `ped.termo` pelos quatro passos, tenta cortes de qualificador ou monta `termo-nao-casou`."""
    if ped.termo is None:
        raise ValueError("consultar_por_nome exige pedido com termo")
    termo = ped.termo
    cortes = gerar_cortes_qualificador(termo)
    termos_lote: list[str] = [termo]
    for c in cortes:
        termos_lote.append(c.nucleo)
        termos_lote.append(c.qualificador)

    res = sessao.resolver_nomes(termos_lote)
    grupos = _agrupar_por_ord(res.linhas)

    if 1 in res.ords_negados:
        raise Recusas([Recusa(
            4,
            "acesso-negado",
            onde="termo",
            recebido=termo,
            regra=REGRA_NOME,
            cura=f"acesso negado a todas as classes das fichas nomeadas por «{termo}»",
            proximo="busca consultar --classe shape",
        )])

    grupo_termo = grupos.get(1, [])
    norm_termo = str(grupo_termo[0].get("norm") or "") if grupo_termo else ""
    if not norm_termo:
        raise Recusas([Recusa(
            2,
            "termo-sem-letra",
            onde="termo",
            recebido=termo,
            regra=REGRA_NOME,
            cura="o termo normalizou para vazio no banco; passe letras de a a z ou números",
            proximo="busca consultar gabarito",
        )])

    achadas = _fichas_do_grupo(grupo_termo)
    if achadas:
        ficha_lida: dict[str, Any] | None = None
        if len(achadas) == 1 and ped.origem != "leitura":
            ficha_lida = sessao.ler_ficha(str(achadas[0]["chave"]), com_ligacoes=(ped.com_ligacoes == "com"))
        return {
            "tipo_resultado": "nome-casou",
            "termo": termo,
            "fichas": [
                {
                    "chave": str(ln["chave"]),
                    "classe": str(ln["classe"]),
                    "rotulo": ln.get("rotulo"),
                    "estado": None,
                    "caminho": None,
                    "passo": int(ln["passo"]),
                    "definicao": ln.get("definicao"),
                }
                for ln in achadas
            ],
            "ficha": ficha_lida,
        }

    # Nenhum casamento inteiro: tenta cortes de núcleo mais longo -> qualificador
    for idx, corte in enumerate(cortes):
        ord_nuc = 2 + idx * 2
        ord_qual = 3 + idx * 2
        fichas_nuc = _fichas_do_grupo(grupos.get(ord_nuc, []))
        classes_nuc = [ln for ln in fichas_nuc if ln.get("e_classe")]
        fichas_qual = _fichas_do_grupo(grupos.get(ord_qual, []))
        if len(classes_nuc) == 1 and fichas_qual:
            return _executar_condicao_de_corte(
                sessao,
                _CorteResolvido(termo, corte, str(classes_nuc[0]["chave"]), fichas_qual),
                tamanho_pagina=tamanho_pagina,
            )

    # Nem termo inteiro nem corte serviu -> termo-nao-casou
    candidatos = _buscar_candidatos_aproximados(sessao, termo)
    disponiveis: dict[str, Any] | None = None
    if not candidatos:
        disponiveis = {
            "classes": sessao.classes_disponiveis(),
            "filtros": list(FILTROS_DISPONIVEIS),
        }
    return {
        "tipo_resultado": "termo-nao-casou",
        "termo": termo,
        "candidatos": candidatos if candidatos else None,
        "disponiveis": disponiveis,
        "proximo": [{"tipo": "nome-candidato", "termo": termo}],
    }
