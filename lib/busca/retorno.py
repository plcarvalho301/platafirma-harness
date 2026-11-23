"""retorno.py — montagem do registro único v1, fecho por bytes e renderização texto/JSON (story 4427, t10).

Contratos:
- platafirma-casa@referencias/instancias/verbo/busca.md, «O que volta», «A página fecha por bytes»,
  «A continuação» e «O vazio não é erro, e não é certeza».
"""
from __future__ import annotations

import json
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .pedido import Pedido, codificar_cursor

VERSAO_RETORNO = 1
TAMANHO_PAGINA_PADRAO = 50
TETO_PAGINA_BYTES = 51200  # 50 KiB: teto de saída da porta


@dataclass(frozen=True)
class _MolduraPagina:
    ped: Pedido
    modo: str
    classe: str
    termo: str | None = None
    condicao: dict[str, Any] | None = None


def _chamada_proxima_pagina(ped: Pedido, token: str) -> str:
    partes = ["busca", "consultar", "--classe", shlex.quote(ped.classe or "")]
    for p in ped.propriedades:
        partes.extend(["--prop", shlex.quote(f"{p.propriedade}={p.valor}")])
    for sp in ped.faltas_propriedade:
        val_s = f"{sp.propriedade}={sp.valor}" if sp.valor is not None else sp.propriedade
        partes.extend(["--sem-prop", shlex.quote(val_s)])
    for g in ped.ligacoes:
        pref = f"{g.sentido}:" if g.sentido == "chegada" else ""
        suf = f"/{g.passos}" if g.passos > 1 else ""
        partes.extend(["--ligacao", shlex.quote(f"{pref}{g.propriedade}{suf}={g.alvo}")])
    for sg in ped.faltas_ligacao:
        pref = f"{sg.sentido}:" if sg.sentido == "chegada" else ""
        alvo_s = f"={sg.alvo}" if sg.alvo is not None else ""
        partes.extend(["--sem-ligacao", shlex.quote(f"{pref}{sg.propriedade}{alvo_s}")])
    if ped.estado is not None:
        partes.extend(["--estado", shlex.quote(ped.estado)])
    if ped.filhas:
        partes.append("--filhas")
    partes.extend(["--cursor", shlex.quote(token)])
    if ped.como_json:
        partes.append("--json")
    return " ".join(partes)


def _ficha_limpa_condicao(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "chave": str(item["chave"]),
        "classe": str(item["classe"]),
        "rotulo": item.get("rotulo"),
        "estado": item.get("estado"),
        "caminho": item.get("caminho"),
    }


def _registro_base(
    *,
    modo: str,
    desfecho: str | None = None,
    termo: str | None = None,
    classe: str | None = None,
    condicao: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "versao": VERSAO_RETORNO,
        "modo": modo,
        "desfecho": desfecho,
        "termo": termo,
        "classe": classe,
        "condicao": condicao,
        "fornada": None,
        "digest": None,
        "de": 0,
        "ate": 0,
        "total": 0,
        "fichas": [],
        "ficha": None,
        "continuacao": None,
        "mudou": None,
        "valores_existentes": None,
        "candidatos": None,
        "disponiveis": None,
        "proximo": None,
    }


def _renderizar_nao_casou(reg: Mapping[str, Any]) -> str:
    linhas = [f"nome «{reg['termo']}» não casou · 0 fichas"]
    for c in reg.get("candidatos") or ():
        rot = f" · {c['rotulo']}" if c.get("rotulo") else ""
        linhas.append(f"candidato: {c['chave']} ({c['classe']}){rot}")
    disp = reg.get("disponiveis")
    if isinstance(disp, Mapping):
        linhas.append("classes: " + ", ".join(disp.get("classes") or ()))
        linhas.append("filtros: " + ", ".join(disp.get("filtros") or ()))
    for pr in reg.get("proximo") or ():
        if pr.get("tipo") == "nome-candidato" and pr.get("termo"):
            linhas.append(f"proximo: nome-candidato: {pr['termo']}")
    return "\n".join(linhas) + "\n"


def _renderizar_modo_nome(reg: Mapping[str, Any]) -> str:
    fichas = reg["fichas"]
    linhas = [f"nome «{reg['termo']}» · {reg['total']} fichas"]
    if reg["total"] == 1 and len(fichas) == 1:
        f0 = fichas[0]
        rot = f" · {f0['rotulo']}" if f0.get("rotulo") else ""
        linhas.append(f"{f0['chave']}{rot}")
        if reg.get("ficha") is not None:
            linhas.append(json.dumps(reg["ficha"], ensure_ascii=False, indent=2, sort_keys=True))
        return "\n".join(linhas) + "\n"
    for f in fichas:
        defin = " ".join(str(f.get("definicao") or "").split())
        linhas.append(f"{f['chave']} · {f['classe']} · {defin} · passo {f['passo']}")
    return "\n".join(linhas) + "\n"


def renderizar_texto(reg: Mapping[str, Any]) -> str:
    """Renderiza o registro único v1 no formato texto canônico da especificação."""
    if reg.get("desfecho") == "termo-nao-casou":
        return _renderizar_nao_casou(reg)
    if reg["modo"] == "nome":
        return _renderizar_modo_nome(reg)

    if reg["modo"] == "condicao":
        cond = reg["condicao"] or {}
        chaves_q = ", ".join(cond.get("chaves") or ())
        primeira = (
            f"nome «{reg['termo']}» virou condição · {reg['classe']} ligada a {chaves_q} "
            f"· fichas {reg['de']} a {reg['ate']} de {reg['total']} · digest {reg['digest']}"
        )
    else:
        primeira = (
            f"classe · fornada {reg['fornada']} "
            f"· fichas {reg['de']} a {reg['ate']} de {reg['total']} · digest {reg['digest']}"
        )

    linhas = [primeira]
    for f in reg["fichas"]:
        rot = f" · {f['rotulo']}" if f.get("rotulo") else ""
        linhas.append(f"{f['chave']}{rot}")
    for vz in reg.get("valores_existentes") or ():
        linhas.append(f"valor existente: {vz['valor']} ({vz['contagem']})")
    for pr in reg.get("proximo") or ():
        if pr.get("tipo") == "pagina" and pr.get("chamada"):
            linhas.append(f"proximo: {pr['chamada']}")
    return "\n".join(linhas) + "\n"


def renderizar(reg: Mapping[str, Any], *, como_json: bool) -> str:
    """Serializa `reg` em JSON de uma linha (`--json`) ou no texto da cadeira."""
    if como_json:
        return json.dumps(dict(reg), ensure_ascii=False) + "\n"
    return renderizar_texto(reg)


def _cabe_no_teto(reg: Mapping[str, Any], *, como_json: bool, teto_bytes: int) -> bool:
    texto_json = json.dumps(dict(reg), ensure_ascii=False).encode("utf-8")
    if len(texto_json) + 1 > teto_bytes:
        return False
    if not como_json:
        texto_hum = renderizar_texto(reg).encode("utf-8")
        if len(texto_hum) > teto_bytes:
            return False
    return True


def montar_retorno_nome(ped: Pedido, res_nome: Mapping[str, Any], *, teto_bytes: int = TETO_PAGINA_BYTES) -> dict[str, Any]:
    """Monta o registro único v1 para a consulta por nome (casada, condição ou `termo-nao-casou`)."""
    tipo = res_nome["tipo_resultado"]
    termo = str(res_nome["termo"])
    if tipo == "termo-nao-casou":
        reg = _registro_base(modo="nome", desfecho="termo-nao-casou", termo=termo)
        reg["candidatos"] = res_nome.get("candidatos")
        reg["disponiveis"] = res_nome.get("disponiveis")
        reg["proximo"] = res_nome.get("proximo")
        return reg

    if tipo == "condicao-por-nome":
        moldura = _MolduraPagina(
            ped=ped, modo="condicao", classe=str(res_nome["classe"]),
            termo=termo, condicao=dict(res_nome["condicao"]),
        )
        return _montar_paginado(moldura, res_nome["consulta"], None, teto_bytes=teto_bytes)

    fichas = list(res_nome["fichas"])
    total = len(fichas)
    melhor: dict[str, Any] | None = None
    for qtd in range(1, total + 1):
        cand = _registro_base(modo="nome", termo=termo)
        cand["total"] = total
        cand["de"] = 1
        cand["ate"] = qtd
        cand["fichas"] = fichas[:qtd]
        cand["ficha"] = res_nome.get("ficha") if total == 1 else None
        if _cabe_no_teto(cand, como_json=ped.como_json, teto_bytes=teto_bytes):
            melhor = cand
        elif melhor is not None:
            break
        else:
            melhor = cand
            break
    if melhor is not None:
        return melhor
    reg_vazio = _registro_base(modo="nome", termo=termo)
    reg_vazio["ficha"] = res_nome.get("ficha")
    return reg_vazio


def _montar_candidato_pagina(
    moldura: _MolduraPagina,
    resultado_db: Mapping[str, Any],
    fatia_crua: Sequence[Mapping[str, Any]],
    valores_existentes: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    ped = moldura.ped
    total = int(resultado_db["total"])
    antes = int(resultado_db["antes"])
    fornada_atual = resultado_db.get("fornada")
    fornada_origem = ped.continuacao.fornada if ped.continuacao is not None else fornada_atual
    mudou: bool | None = (fornada_atual != ped.continuacao.fornada) if ped.continuacao is not None else None

    entregues = [_ficha_limpa_condicao(f) for f in fatia_crua]
    ate = antes + len(entregues) if entregues else 0
    de = antes + 1 if entregues else 0

    continuacao: str | None = None
    proximo: list[dict[str, str]] | None = None
    if moldura.modo == "classe" and entregues and ate < total:
        ultima = fatia_crua[-1]
        continuacao = codificar_cursor(
            ordem=int(ultima["ordem"]),
            chave=str(ultima["chave"]),
            fornada=fornada_origem,
            resumo=ped.resumo,
        )
        proximo = [{"tipo": "pagina", "chamada": _chamada_proxima_pagina(ped, continuacao)}]

    reg = _registro_base(modo=moldura.modo, termo=moldura.termo, classe=moldura.classe, condicao=moldura.condicao)
    reg["fornada"] = fornada_atual
    reg["digest"] = resultado_db.get("digest")
    reg["de"] = de
    reg["ate"] = ate
    reg["total"] = total
    reg["fichas"] = entregues
    reg["continuacao"] = continuacao
    reg["mudou"] = mudou
    reg["valores_existentes"] = valores_existentes if total == 0 else None
    reg["proximo"] = proximo
    return reg


def _montar_paginado(
    moldura: _MolduraPagina,
    resultado_db: Mapping[str, Any],
    valores_existentes: list[dict[str, Any]] | None,
    *,
    teto_bytes: int,
) -> dict[str, Any]:
    brutas: list[Mapping[str, Any]] = list(resultado_db.get("fichas") or [])
    if not brutas:
        return _montar_candidato_pagina(moldura, resultado_db, [], valores_existentes)

    melhor: dict[str, Any] | None = None
    for qtd in range(1, len(brutas) + 1):
        cand = _montar_candidato_pagina(moldura, resultado_db, brutas[:qtd], valores_existentes)
        if _cabe_no_teto(cand, como_json=moldura.ped.como_json, teto_bytes=teto_bytes):
            melhor = cand
        elif melhor is not None:
            break
        else:
            melhor = cand
            break
    if melhor is None:
        raise RuntimeError("página sem candidato montado")
    return melhor


def montar_retorno_condicao(
    ped: Pedido,
    classe_slug: str,
    resultado_db: Mapping[str, Any],
    valores_existentes: list[dict[str, Any]] | None = None,
    *,
    teto_bytes: int = TETO_PAGINA_BYTES,
) -> dict[str, Any]:
    """Monta o registro único v1 para a consulta por condição, fechando por bytes antes do teto."""
    moldura = _MolduraPagina(ped=ped, modo="classe", classe=classe_slug)
    return _montar_paginado(moldura, resultado_db, valores_existentes, teto_bytes=teto_bytes)
