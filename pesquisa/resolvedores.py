"""Resolução determinística de identificador (spec §4.1b).

`resolver <tipo> <id>` responde "para onde X aponta" contra registro oficial — não é
metabusca. Resposta de registro tem credibilidade distinta de página indexada; o verbo
não julga, só registra a origem. Trata pessoa/entidade como procedência de fonte aberta
como qualquer outra (decisão do dono, 03/09: sem LGPD no verbo).

Tipos plugáveis; a lista fechada definitiva é política do dono no `settings.yml`. O
default aqui cobre os cinco do §4.1b. `fetch` é injetável (testes sem rede).
Não-resolução vira linha de não-achado, escrita por quem chama.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .envelope import FalhaFonte
from .guarda import UrlRecusada, verifica_url

# fetch(url, headers) -> (status:int, corpo:bytes)
Fetch = Callable[[str, dict], tuple[int, bytes]]

TIPOS = ("dominio", "doi", "isbn", "cnpj", "orcid")


def _url_de(tipo: str, ident: str) -> tuple[str, dict]:
    ident = ident.strip()
    if tipo == "dominio":
        return f"https://rdap.org/domain/{ident}", {"Accept": "application/rdap+json"}
    if tipo == "doi":
        return f"https://api.crossref.org/works/{ident}", {"Accept": "application/json"}
    if tipo == "orcid":
        return f"https://pub.orcid.org/v3.0/{ident}/record", {"Accept": "application/json"}
    if tipo == "isbn":
        limpo = re.sub(r"[^0-9Xx]", "", ident)
        return f"https://openlibrary.org/isbn/{limpo}.json", {"Accept": "application/json"}
    if tipo == "cnpj":
        limpo = re.sub(r"\D", "", ident)
        return f"https://brasilapi.com.br/api/cnpj/v1/{limpo}", {"Accept": "application/json"}
    raise FalhaFonte(f"tipo-desconhecido:{tipo}")


def _fetch_httpx(url: str, headers: dict) -> tuple[int, bytes]:
    import httpx

    try:
        r = httpx.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        return r.status_code, r.content
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"registro-fora:{type(exc).__name__}") from exc


def resolver(tipo: str, ident: str, *, fetch: Fetch | None = None) -> dict[str, Any]:
    """Devolve {status, url, sha256, bruto_bytes, registro, resolvido}.

    `resolvido=False` (status 404/inexistente) NÃO é erro de fonte — é não-achado, que
    quem chama grava no manifesto. Erro de rede/registro fora, sim, levanta FalhaFonte.
    """
    if tipo not in TIPOS:
        raise FalhaFonte(f"tipo-desconhecido:{tipo}")
    url, headers = _url_de(tipo, ident)
    try:
        verifica_url(url)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec

    status, corpo = (fetch or _fetch_httpx)(url, headers)
    resolvido = 200 <= status < 300
    registro: Any = None
    if resolvido and corpo:
        try:
            registro = json.loads(corpo.decode("utf-8", "replace"))
        except (ValueError, UnicodeError):
            registro = None  # registro veio, mas não é JSON — bruto guarda o que veio
    return {
        "status": status,
        "url": url,
        "resolvedor": {"dominio": "rdap", "doi": "crossref", "orcid": "orcid",
                       "isbn": "openlibrary", "cnpj": "brasilapi"}[tipo],
        "resolvido": resolvido,
        "bruto_bytes": corpo,
        "registro": registro,
    }
