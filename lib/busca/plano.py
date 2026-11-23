"""plano.py — conferência do pedido contra o catálogo e montagem do plano canônico (story 4427, t10).

Contratos:
- platafirma-casa@referencias/instancias/verbo/busca.md, «Como a condição vira plano».
"""
from __future__ import annotations

import json
import shlex
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from leitura import casa_db
from leitura.recusa import Recusa, Recusas

from .nome import resolver_alvo_ligacao
from .pedido import FiltroLigacaoCru, FiltroPropriedadeCru, Pedido

REGRA_PLANO = "verbo:busca §Como a condição vira plano"
_AMOSTRA_CLASSES_CURA = 15


@dataclass(frozen=True)
class PropriedadeParaVazio:
    slug: str
    fonte: str
    restricoes: tuple[str, ...]
    coluna: str | None


@dataclass(frozen=True)
class PlanoConsulta:
    classe_slug: str
    classes_uuids: tuple[str, ...]
    filtro_db: dict[str, Any]
    propriedades_vazio: tuple[PropriedadeParaVazio, ...]


@dataclass
class _CatalogoIndexado:
    classe_slug: str
    classes_uuids: list[str]
    props_dado: dict[str, dict[str, Any]] = field(default_factory=dict)
    props_ligacao: dict[tuple[str, str], str] = field(default_factory=dict)
    colunas: dict[str, casa_db.ColunaFixa] = field(default_factory=dict)
    estados: list[str] = field(default_factory=list)


def _resolver_classe_principal(sessao: casa_db.SessaoLeitura, nome_classe: str) -> tuple[str, str]:
    res = sessao.resolver_nomes([nome_classe])
    if 1 in res.ords_negados:
        raise Recusas([Recusa(
            4,
            "acesso-negado",
            onde="--classe",
            recebido=nome_classe,
            regra=REGRA_PLANO,
            cura=f"acesso negado para ler a classe «{nome_classe}»",
            proximo="busca consultar --classe shape",
        )])

    vistas: set[str] = set()
    classes_achadas: list[dict] = []
    for ln in res.linhas:
        ch = ln.get("chave")
        if ch and ln.get("e_classe") and str(ch) not in vistas:
            vistas.add(str(ch))
            classes_achadas.append(ln)

    if not classes_achadas:
        disp = sessao.classes_disponiveis()
        amostra = ", ".join(disp[:_AMOSTRA_CLASSES_CURA]) + ("…" if len(disp) > _AMOSTRA_CLASSES_CURA else "")
        cands = [c for c in disp if c != nome_classe]
        sugestao_cls = cands[0] if cands else ("gabarito" if nome_classe == "shape" else "shape")
        raise Recusas([Recusa(
            2,
            "classe-desconhecida",
            onde="--classe",
            recebido=nome_classe,
            regra=REGRA_PLANO,
            cura=f"nenhuma classe tem o nome «{nome_classe}»; classes disponíveis: {amostra}",
            proximo=f"busca consultar --classe {shlex.quote(sugestao_cls)}",
        )])

    if len(classes_achadas) > 1:
        nomes_cand = ", ".join(str(ln["chave"]) for ln in classes_achadas)
        primeira = str(classes_achadas[0]["chave"])
        segunda = str(classes_achadas[1]["chave"])
        escolhida = segunda if primeira == nome_classe else primeira
        raise Recusas([Recusa(
            2,
            "classe-ambigua",
            onde="--classe",
            recebido=nome_classe,
            regra=REGRA_PLANO,
            cura=f"«{nome_classe}» nomeia {len(classes_achadas)} classes ({nomes_cand}); use o slug exato",
            proximo=f"busca consultar --classe {shlex.quote(escolhida)}",
        )])

    slug = str(classes_achadas[0]["chave"])
    sessao.exigir_autorizacao(slug)
    uid = sessao.uuid_da_classe(slug)
    if uid is None:
        raise Recusas([Recusa(
            5,
            "falha-interna",
            onde="--classe",
            recebido=slug,
            regra=REGRA_PLANO,
            cura=f"a classe {slug} não foi encontrada em casa.shape",
            proximo="busca consultar --classe shape",
        )])
    return uid, slug


def _indexar_catalogo(
    classe_slug: str,
    classes_pares: Sequence[tuple[str, str]],
    linhas_cat: Sequence[dict],
) -> _CatalogoIndexado:
    cat = _CatalogoIndexado(
        classe_slug=classe_slug,
        classes_uuids=[u for u, _ in classes_pares],
    )
    estados_set: set[str] = set()
    for _, slug_c in classes_pares:
        for nome_col, meta_col in casa_db.colunas_da_classe(slug_c).items():
            cat.colunas.setdefault(nome_col, meta_col)

    for ln in linhas_cat:
        for est in ln.get("estados") or ():
            estados_set.add(str(est))
        prop_slug = str(ln["propriedade"])
        tipo_val = str(ln["tipo_de_valor"])
        sentido = str(ln.get("sentido") or "saida")
        if tipo_val == "ligacao":
            cat.props_ligacao[(prop_slug, sentido)] = str(ln["propriedade_id"])
            continue
        entrada = cat.props_dado.setdefault(
            prop_slug,
            {"restricoes": [], "tipo_de_valor": tipo_val, "valores": []},
        )
        r_id = str(ln["restricao"])
        if r_id not in entrada["restricoes"]:
            entrada["restricoes"].append(r_id)
        for v in ln.get("valores") or ():
            if v not in entrada["valores"]:
                entrada["valores"].append(v)

    cat.estados = sorted(estados_set)
    return cat


def _converter_valor_escalar(texto: str, tipo: str) -> Any:
    baixo = texto.strip().lower()
    if tipo == "booleano":
        if baixo in ("true", "sim"):
            return True
        if baixo in ("false", "nao", "não"):
            return False
        return texto
    if tipo in ("inteiro", "numero", "decimal"):
        try:
            return int(texto) if "." not in texto else float(texto)
        except ValueError:
            return texto
    return texto


def _resolver_valor_dicionario(
    fp: FiltroPropriedadeCru,
    valores_dic: Sequence[dict],
    classe_slug: str,
) -> tuple[str | None, Recusa | None]:
    if fp.valor is None:
        return None, None
    alvo_low = fp.valor.strip().lower()
    for v in valores_dic:
        if str(v["slug"]).lower() == alvo_low or str(v.get("rotulo") or "").strip().lower() == alvo_low:
            return str(v["slug"]), None
    aceitos = ", ".join(f"{v['slug']} ({v.get('rotulo') or v['slug']})" for v in valores_dic)
    sugestao_val = str(valores_dic[0]["slug"]) if valores_dic else "vigente"
    if sugestao_val == fp.valor:
        sugestao_val = "outro"
    onde = "--sem-prop" if fp.sem else "--prop"
    return None, Recusa(
        2,
        "valor-fora-do-dicionario",
        onde=onde,
        recebido=fp.valor,
        regra=REGRA_PLANO,
        cura=f"valor fora do dicionário de {fp.propriedade}; aceitos: {aceitos}",
        proximo=f"busca consultar --classe {shlex.quote(classe_slug)} {onde} {shlex.quote(f'{fp.propriedade}={sugestao_val}')}",
    )


def _traduzir_prop_coluna(
    sessao: casa_db.SessaoLeitura,
    classe_slug: str,
    fp: FiltroPropriedadeCru,
    col: casa_db.ColunaFixa,
    erros: list[Recusa],
) -> tuple[dict[str, Any] | None, PropriedadeParaVazio | None]:
    onde = "--sem-prop" if fp.sem else "--prop"
    if fp.valor is None:
        return {
            "fonte": col.fonte, "restricoes": [], "coluna": col.nome,
            "valor": None, "alvo": None, "sem": True, "_slug": fp.propriedade,
        }, None

    if col.tipo == "dicionario" and col.dicionario_slug is not None:
        valores_dic = sessao.valores_do_dicionario(col.dicionario_slug)
        slug_dic, rec_dic = _resolver_valor_dicionario(fp, valores_dic, classe_slug)
        if rec_dic is not None:
            erros.append(rec_dic)
            return None, None
        return {
            "fonte": col.fonte, "restricoes": [], "coluna": col.nome,
            "valor": slug_dic, "alvo": None, "sem": fp.sem, "_slug": fp.propriedade,
        }, None

    if col.tipo == "ficha" and col.classe_alvo is not None:
        ficha_alvo, rec = resolver_alvo_ligacao(
            sessao, fp.valor, onde=onde, classe_restrita=col.classe_alvo,
        )
        if rec is not None and rec.codigo == "alvo-ambiguo":
            erros.append(rec)
            return None, None
        alvo_uid = ficha_alvo.uuid if ficha_alvo is not None else None
        val_json = None if alvo_uid is not None else fp.valor
    else:
        alvo_uid = None
        val_json = _converter_valor_escalar(fp.valor, col.tipo)

    meta_vazio = (
        None if fp.sem
        else PropriedadeParaVazio(slug=fp.propriedade, fonte=col.fonte, restricoes=(), coluna=col.nome)
    )
    return {
        "fonte": col.fonte, "restricoes": [], "coluna": col.nome,
        "valor": val_json, "alvo": alvo_uid, "sem": fp.sem, "_slug": fp.propriedade,
    }, meta_vazio


def _traduzir_prop(
    sessao: casa_db.SessaoLeitura,
    cat: _CatalogoIndexado,
    fp: FiltroPropriedadeCru,
    erros: list[Recusa],
) -> tuple[dict[str, Any] | None, PropriedadeParaVazio | None]:
    onde = "--sem-prop" if fp.sem else "--prop"
    if fp.propriedade in cat.props_dado:
        info = cat.props_dado[fp.propriedade]
        restricoes = list(info["restricoes"])
        tipo_val = str(info["tipo_de_valor"])
        if fp.valor is None:
            return {
                "fonte": "dado", "restricoes": restricoes, "coluna": None,
                "valor": None, "alvo": None, "sem": True, "_slug": fp.propriedade,
            }, None
        if tipo_val == "dicionario":
            slug_dic, rec = _resolver_valor_dicionario(fp, info["valores"], cat.classe_slug)
            if rec is not None:
                erros.append(rec)
                return None, None
            return {
                "fonte": "dado", "restricoes": restricoes, "coluna": None,
                "valor": slug_dic, "alvo": None, "sem": fp.sem, "_slug": fp.propriedade,
            }, None

        val_conv = _converter_valor_escalar(fp.valor, tipo_val)
        meta_vazio = (
            None if fp.sem
            else PropriedadeParaVazio(slug=fp.propriedade, fonte="dado", restricoes=tuple(restricoes), coluna=None)
        )
        return {
            "fonte": "dado", "restricoes": restricoes, "coluna": None,
            "valor": val_conv, "alvo": None, "sem": fp.sem, "_slug": fp.propriedade,
        }, meta_vazio

    if fp.propriedade in cat.colunas:
        return _traduzir_prop_coluna(sessao, cat.classe_slug, fp, cat.colunas[fp.propriedade], erros)

    declaradas = sorted({*cat.props_dado.keys(), *cat.colunas.keys()})
    lista_txt = ", ".join(declaradas) if declaradas else "(nenhuma)"
    prox = (
        f"busca consultar --classe {shlex.quote(cat.classe_slug)} --sem-prop {shlex.quote(declaradas[0])}"
        if declaradas and declaradas[0] != fp.propriedade
        else f"busca consultar --classe {shlex.quote(cat.classe_slug)}"
    )
    erros.append(Recusa(
        2,
        "propriedade-desconhecida",
        onde=onde,
        recebido=fp.propriedade,
        regra=REGRA_PLANO,
        cura=f"a classe {cat.classe_slug} não declara a propriedade «{fp.propriedade}»; declaradas: {lista_txt}",
        proximo=prox,
    ))
    return None, None


def _traduzir_ligacao(
    sessao: casa_db.SessaoLeitura,
    cat: _CatalogoIndexado,
    lg: FiltroLigacaoCru,
    erros: list[Recusa],
) -> tuple[str, str, str | None, str | None] | None:
    onde = "--sem-ligacao" if lg.sem else "--ligacao"
    prop_id = cat.props_ligacao.get((lg.propriedade, lg.sentido))
    if prop_id is None:
        declaradas = sorted(f"{s}:{p}" if s == "chegada" else p for p, s in cat.props_ligacao)
        lista_txt = ", ".join(declaradas) if declaradas else "(nenhuma)"
        erros.append(Recusa(
            2,
            "ligacao-desconhecida",
            onde=onde,
            recebido=lg.propriedade,
            regra=REGRA_PLANO,
            cura=f"a classe {cat.classe_slug} não declara a ligação «{lg.propriedade}» ({lg.sentido}); declaradas: {lista_txt}",
            proximo=f"busca consultar --classe {shlex.quote(cat.classe_slug)}",
        ))

    alvo_uid: str | None = None
    alvo_chave: str | None = None
    if lg.alvo is not None:
        ficha_alvo, rec = resolver_alvo_ligacao(sessao, lg.alvo, onde=onde)
        if rec is not None:
            if rec.codigo == "alvo-inexistente":
                rec = Recusa(
                    2,
                    "alvo-inexistente",
                    onde=onde,
                    recebido=lg.alvo,
                    regra=REGRA_PLANO,
                    cura=rec.cura,
                    proximo=f"nome-candidato: {lg.alvo}",
                )
            erros.append(rec)
            return None
        if ficha_alvo is not None:
            alvo_uid = ficha_alvo.uuid
            alvo_chave = ficha_alvo.chave

    if prop_id is None:
        return None
    return prop_id, lg.propriedade, alvo_uid, alvo_chave


def _chave_ordem_prop(item: dict[str, Any]) -> tuple[str, str, str]:
    val_s = json.dumps(item["valor"], ensure_ascii=False, sort_keys=True) if item["valor"] is not None else ""
    return str(item["_slug"]), val_s, str(item["alvo"] or "")


@dataclass
class _AcumuladorPlano:
    erros: list[Recusa] = field(default_factory=list)
    props_tem: list[dict[str, Any]] = field(default_factory=list)
    props_sem: list[dict[str, Any]] = field(default_factory=list)
    vazio_candidatas: list[PropriedadeParaVazio] = field(default_factory=list)
    ligs_brutas: list[tuple[int, str, str, str, str]] = field(default_factory=list)
    sem_ligs_brutas: list[tuple[str, str, str, str, str | None]] = field(default_factory=list)


def _coletar_predicados(
    sessao: casa_db.SessaoLeitura,
    cat: _CatalogoIndexado,
    ped: Pedido,
) -> _AcumuladorPlano:
    ac = _AcumuladorPlano()
    for fp in ped.propriedades:
        trad, meta_vz = _traduzir_prop(sessao, cat, fp, ac.erros)
        if trad is not None:
            ac.props_tem.append(trad)
        if meta_vz is not None:
            ac.vazio_candidatas.append(meta_vz)

    for sfp in ped.faltas_propriedade:
        trad, _ = _traduzir_prop(sessao, cat, sfp, ac.erros)
        if trad is not None:
            ac.props_sem.append(trad)

    for lg in ped.ligacoes:
        res_lg = _traduzir_ligacao(sessao, cat, lg, ac.erros)
        if res_lg is not None and res_lg[2] is not None and res_lg[3] is not None:
            prop_id, prop_slug, alvo_uid, alvo_chave = res_lg
            ac.ligs_brutas.append((lg.passos, prop_slug, lg.sentido, alvo_chave, f"{prop_id}|{alvo_uid}"))

    for slg in ped.faltas_ligacao:
        res_slg = _traduzir_ligacao(sessao, cat, slg, ac.erros)
        if res_slg is not None:
            prop_id, prop_slug, alvo_uid, alvo_chave = res_slg
            ac.sem_ligs_brutas.append((prop_slug, slg.sentido, alvo_chave or "", prop_id, alvo_uid))

    _validar_estado(cat, ped.estado, ac.erros)
    return ac


def _validar_estado(cat: _CatalogoIndexado, estado: str | None, erros: list[Recusa]) -> None:
    if estado is None or estado in cat.estados:
        return
    est_txt = ", ".join(cat.estados) if cat.estados else "(nenhum estado declarado)"
    erros.append(Recusa(
        2,
        "estado-desconhecido",
        onde="--estado",
        recebido=estado,
        regra=REGRA_PLANO,
        cura=f"o estado «{estado}» não pertence à classe {cat.classe_slug}; estados: {est_txt}",
        proximo=f"busca consultar --classe {shlex.quote(cat.classe_slug)}",
    ))


def _deduplicar_vazio(candidatas: Sequence[PropriedadeParaVazio]) -> tuple[PropriedadeParaVazio, ...]:
    unicas: list[PropriedadeParaVazio] = []
    vistas: set[tuple[str, str]] = set()
    for vz in sorted(candidatas, key=lambda v: v.slug):
        k = (vz.fonte, vz.slug)
        if k not in vistas:
            vistas.add(k)
            unicas.append(vz)
    return tuple(unicas)


def montar_plano(sessao: casa_db.SessaoLeitura, ped: Pedido) -> PlanoConsulta:
    """Confere `ped` contra o catálogo do retrato e devolve o `PlanoConsulta` em ordem canônica.

    Acumula numa só `Recusas` (saída 2) todos os erros de propriedade, valor de dicionário,
    ligação, alvo e estado.
    """
    if ped.classe is None:
        raise ValueError("montar_plano exige pedido de modo classe")

    classe_uuid, classe_slug = _resolver_classe_principal(sessao, ped.classe)
    classes_pares = sessao.filhas_da_classe(classe_uuid) if ped.filhas else [(classe_uuid, classe_slug)]
    linhas_cat = sessao.catalogo_da_classe([u for u, _ in classes_pares])
    cat = _indexar_catalogo(classe_slug, classes_pares, linhas_cat)

    ac = _coletar_predicados(sessao, cat, ped)
    if ac.erros:
        raise Recusas(ac.erros)

    props_ordenadas = [*sorted(ac.props_tem, key=_chave_ordem_prop), *sorted(ac.props_sem, key=_chave_ordem_prop)]
    props_db = [
        {
            "n": idx,
            "fonte": p["fonte"],
            "restricoes": p["restricoes"],
            "coluna": p["coluna"],
            "valor": p["valor"],
            "alvo": p["alvo"],
            "sem": p["sem"],
        }
        for idx, p in enumerate(props_ordenadas, start=1)
    ]

    ligs_ordenadas = sorted(ac.ligs_brutas, key=lambda t: (t[0], t[1], t[2], t[3]))
    preds_lig = [
        casa_db.PredicadoLigacao(
            n=idx,
            propriedade_id=par.split("|", 1)[0],
            sentido=sentido,
            alvos=(par.split("|", 1)[1],),
            passos=passos,
        )
        for idx, (passos, _slug, sentido, _chave, par) in enumerate(ligs_ordenadas, start=1)
    ]

    sem_ligs_ordenadas = sorted(ac.sem_ligs_brutas, key=lambda t: (t[0], t[1], t[2]))
    faltas_lig_db = [
        {"propriedade": prop_id, "sentido": sentido, "alvo": alvo_uid}
        for _slug, sentido, _chave, prop_id, alvo_uid in sem_ligs_ordenadas
    ]

    return PlanoConsulta(
        classe_slug=classe_slug,
        classes_uuids=tuple(cat.classes_uuids),
        filtro_db={
            "classes_uuids": cat.classes_uuids,
            "propriedades": props_db,
            "ligacoes": preds_lig,
            "faltas_ligacao": faltas_lig_db,
            "estado": ped.estado,
        },
        propriedades_vazio=_deduplicar_vazio(ac.vazio_candidatas),
    )
