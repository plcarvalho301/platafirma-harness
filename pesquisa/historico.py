"""Snapshot de terceiro — prova para além de nós (spec §4.4).

Prática canônica de OSINT (Bazzell cap. 24; Berkeley Protocol): o `sha256` prova o que
*nós* recebemos; `historico` prova que a página existia e como era independente de nós.
Fonte que some ou muda depois da coleta deixa de ficar só com prova nossa.

  sem --em/--salvar : lista capturas do Wayback (CDX)
  --em AAAA-MM-DD    : (quem chama) lê a captura por `ler`, origem = arquivo
  --salvar          : Save Page Now e grava a URL do arquivo de terceiro no manifesto

`fetch` injetável. Guarda de rede aplica-se à URL alvo antes de qualquer chamada.
"""

from __future__ import annotations

from typing import Any, Callable

from .envelope import FalhaFonte
from .guarda import UrlRecusada, verifica_url

Fetch = Callable[[str, dict], tuple[int, bytes]]
CDX = "http://web.archive.org/cdx/search/cdx"
SPN = "https://web.archive.org/save/"


def _fetch_httpx(url: str, headers: dict) -> tuple[int, bytes]:
    import httpx

    try:
        r = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        return r.status_code, r.content
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"wayback-fora:{type(exc).__name__}") from exc


def capturas(url: str, *, fetch: Fetch | None = None) -> dict[str, Any]:
    """Lista capturas conhecidas (CDX). Vazio não é erro — é não-achado."""
    try:
        verifica_url(url)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec
    import json

    q = f"{CDX}?url={url}&output=json&fl=timestamp,original,statuscode,digest&limit=50"
    status, corpo = (fetch or _fetch_httpx)(q, {})
    if not (200 <= status < 300):
        raise FalhaFonte(f"cdx-status-{status}")
    linhas = json.loads(corpo.decode("utf-8", "replace") or "[]")
    caps = [dict(zip(linhas[0], row)) for row in linhas[1:]] if linhas else []
    return {"capturas": caps, "total": len(caps)}


def url_captura(url: str, data: str) -> str:
    """URL de leitura da captura naquela data (o fluxo de `ler` lê daqui)."""
    ts = data.replace("-", "") + "000000"
    return f"http://web.archive.org/web/{ts}/{url}"


def salvar(url: str, *, fetch: Fetch | None = None) -> dict[str, Any]:
    """Pede Save Page Now. Devolve a URL do arquivo de terceiro para o manifesto."""
    try:
        verifica_url(url)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec
    status, _ = (fetch or _fetch_httpx)(SPN + url, {})
    if not (200 <= status < 400):
        raise FalhaFonte(f"spn-status-{status}")
    return {"arquivo_terceiro": SPN + url, "status": status}
