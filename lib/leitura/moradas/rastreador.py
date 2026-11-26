"""Adaptador da morada `rastreador` (cards ativos e comentários)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada, montar_pagina_bruta, normalizar_termo

# A API do rastreador mora em /api, na mesma porta que o verbo tarefas usa (bin/tarefas, TAREFAS_BASE).
_RASTREADOR_URL_PADRAO = "http://127.0.0.1:8120/api"
_CLASSES_SEM_NIVEL = frozenset({"card", "comentario"})
_HTTP_NOT_FOUND = 404
ESTADOS_TERMINAIS = frozenset(
    {"concluido", "concluído", "fechado", "cancelado", "arquivado", "descartado", "done", "closed"}
)

ClienteHttpRastreador = Callable[[str, Mapping[str, str], float], Any]


def _requisitar_rastreador_padrao(
    url: str, params: Mapping[str, str], timeout_s: float
) -> Any:
    destino = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    req = urllib.request.Request(destino, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _estado_eh_terminal(estado: str) -> bool:
    return normalizar_termo(estado) in ESTADOS_TERMINAIS


def _filtros_para_estado_e_mae(
    filtros: Sequence[FiltroCatalogo],
) -> tuple[str | None, str | None]:
    estado_ped: str | None = None
    mae_ped: str | None = None
    for f in filtros:
        if f.tipo == "estado" and f.valor:
            estado_ped = normalizar_termo(f.valor)
        elif f.tipo == "filhas" and f.valor:
            mae_ped = f.valor
    return estado_ped, mae_ped


def _item_aceito_na_lista(
    reg: Mapping[str, Any],
    *,
    classe: str,
    estado_ped: str | None,
    mae_ped: str | None,
    termo_n: str | None,
) -> dict[str, str] | None:
    estado = str(reg.get("estado") or "")
    nivel = str(reg.get("nivel_nome") or "")
    if classe not in _CLASSES_SEM_NIVEL and nivel and nivel != classe:
        return None
    if classe != "comentario" and estado_ped is None and _estado_eh_terminal(estado):
        return None
    if estado_ped is not None and normalizar_termo(estado) != estado_ped:
        return None
    if mae_ped is not None and str(reg.get("pai") or reg.get("mae") or "") != mae_ped:
        return None
    cid = str(reg.get("id") or "")
    if not cid:
        return None
    chave = f"{classe}:{cid}"
    rotulo = str(reg.get("titulo") or cid)
    if termo_n and termo_n not in normalizar_termo(chave) and termo_n not in normalizar_termo(rotulo):
        return None
    return {"chave": chave, "rotulo": rotulo, "resumo_curto": estado}


class AdaptadorRastreador:
    """Lê e lista cards ativos e comentários pela interface do serviço rastreador."""

    def __init__(
        self,
        *,
        url_base: str | None = None,
        cliente_http: ClienteHttpRastreador | None = None,
    ) -> None:
        self._url = (url_base or os.environ.get("RASTREADOR_URL", _RASTREADOR_URL_PADRAO)).rstrip("/")
        self._http = cliente_http or _requisitar_rastreador_padrao

    def _chamar(
        self, caminho: str, params: Mapping[str, str], prazo_ms: int, recebido: str
    ) -> Any:
        timeout_s = max(0.05, prazo_ms / 1000.0)
        try:
            return self._http(f"{self._url}{caminho}", params, timeout_s)
        except urllib.error.HTTPError as exc:
            if exc.code == _HTTP_NOT_FOUND:
                return None
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="morada:rastreador",
                    recebido=recebido,
                    regra="disponibilidade-morada-rastreador",
                    cura=f"serviço rastreador respondeu HTTP {exc.code}",
                    proximo=f"tarefas ler {recebido}",
                )
            ) from None
        except TimeoutError as exc:
            raise ErroMorada(
                Recusa(
                    saida=5,
                    codigo="tempo-esgotado",
                    onde="morada:rastreador",
                    recebido=recebido,
                    regra="prazo-da-chamada",
                    cura=f"rastreador excedeu o prazo de {prazo_ms} ms ({exc})",
                    proximo=f"tarefas ler {recebido}",
                )
            ) from None
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="morada:rastreador",
                    recebido=recebido,
                    regra="disponibilidade-morada-rastreador",
                    cura=f"serviço rastreador indisponível: {exc}",
                    proximo=f"tarefas ler {recebido}",
                )
            ) from None

    @staticmethod
    def _recusa_comentario_sem_card(recebido: str) -> ErroMorada:
        return ErroMorada(
            Recusa(
                saida=2,
                codigo="chave-mal-formada",
                onde="chave",
                recebido=recebido,
                regra="comentario-pela-chave-do-card",
                cura="o rastreador só publica comentário pela lista do card: use comentario:<card>/<id>",
                proximo="tarefas comentarios <card>",
            )
        )

    def _ler_comentario(self, slug: str, prazo_ms: int, recebido: str) -> Any:
        card, _, cid = slug.partition("/")
        if not card or not cid:
            raise self._recusa_comentario_sem_card(recebido)
        bruto = self._chamar(f"/itens/{card}/comentarios", {}, prazo_ms, recebido)
        lista = bruto.get("comentarios", []) if isinstance(bruto, Mapping) else []
        return next((c for c in lista if isinstance(c, Mapping) and str(c.get("id")) == cid), None)

    @staticmethod
    def _validar_versao_vigente(pedida: str | None, vigente: str, chave: str) -> None:
        if pedida and pedida != vigente:
            rec = Recusa(
                saida=2,
                codigo="versao-divergente",
                onde="--versao",
                recebido=pedida,
                regra="versao-vigente-no-rastreador",
                cura=f"revisão atual no rastreador é {vigente}",
                proximo=f"tarefas ler {chave}",
            )
            raise ErroMorada(rec)

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto:
        slug = alvo.endereco.split(":", 1)[1] if ":" in alvo.endereco else alvo.endereco
        eh_comentario = alvo.classe == "comentario"
        params: dict[str, str] = {}
        if alvo.classe == "story" and seletor.com_decisoes_ancestrais:
            params["com_decisoes_ancestrais"] = "true"

        if eh_comentario:
            item = self._ler_comentario(slug, prazo_ms, alvo.chave_pedida)
        else:
            item = self._chamar(f"/itens/{slug}", params, prazo_ms, alvo.chave_pedida)
        if not isinstance(item, Mapping):
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:rastreador",
                    recebido=alvo.chave_pedida,
                    regra="card-ativo-no-rastreador",
                    cura=f"{alvo.chave_pedida} não encontrado no rastreador",
                    proximo="tarefas listar",
                )
            )

        estado = str(item.get("estado") or "")
        if not eh_comentario and estado and _estado_eh_terminal(estado):
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:rastreador",
                    recebido=alvo.chave_pedida,
                    regra="card-terminal-fora-de-ler",
                    cura=f"card em estado terminal ({estado!r}) sai como inexistente no ato ler",
                    proximo="tarefas listar",
                )
            )

        versao = str(
            item.get("descricao_versao") or item.get("versao") or item.get("revisao") or "1"
        )
        self._validar_versao_vigente(seletor.versao_pedida, versao, alvo.chave_pedida)

        payload = dict(item)
        if not seletor.com_decisoes_ancestrais:
            payload.pop("decisoes_ancestrais", None)

        dados = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
        return ObjetoBruto(alvo, versao, dados=dados, nome_arquivo=f"{alvo.classe}.json", total_bytes=len(dados))

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        estado_ped, mae_ped = _filtros_para_estado_e_mae(filtros)
        if classe == "comentario":
            if mae_ped is None:
                raise self._recusa_comentario_sem_card(f"listar:{classe}")
            bruto = self._chamar(f"/itens/{mae_ped}/comentarios", {}, prazo_ms, f"listar:{classe}")
            crus = bruto.get("comentarios", []) if isinstance(bruto, Mapping) else []
            lista = [{**c, "id": f"{mae_ped}/{c.get('id')}"} for c in crus if isinstance(c, Mapping)]
            mae_ped = None
        else:
            bruto = self._chamar("/itens", {}, prazo_ms, f"listar:{classe}")
            lista = bruto.get("itens", []) if isinstance(bruto, Mapping) else (bruto or [])

        termo_n = normalizar_termo(termo) if termo else None
        itens: list[dict[str, str]] = []
        for reg in lista:
            if not isinstance(reg, Mapping):
                continue
            aceito = _item_aceito_na_lista(
                reg,
                classe=classe,
                estado_ped=estado_ped,
                mae_ped=mae_ped,
                termo_n=termo_n,
            )
            if aceito is not None:
                itens.append(aceito)

        return montar_pagina_bruta(
            classe, itens, limite=limite, cursor=cursor, universo_fechado=True
        )
