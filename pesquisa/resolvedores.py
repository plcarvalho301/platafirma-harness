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
from urllib.parse import quote

from .envelope import FalhaFonte
from .guarda import UrlRecusada, verifica_url
from .prazo import CONEXAO_S, Relogio, com_prazo

# fetch(url, headers) -> (status:int, corpo:bytes)
Fetch = Callable[[str, dict], tuple[int, bytes]]

TIPOS = ("dominio", "doi", "isbn", "cnpj", "orcid")

_CROSSREF_SELECT = (
    "DOI,title,author,published,issued,container-title,publisher,ISSN,ISBN,type,URL"
)


def _limpa_doi(ident: str) -> str:
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", ident.strip(), flags=re.IGNORECASE)


def _url_de(tipo: str, ident: str, *, completo: bool = False) -> tuple[str, dict]:
    ident = ident.strip()
    if tipo == "dominio":
        return f"https://rdap.org/domain/{ident}", {"Accept": "application/rdap+json"}
    if tipo == "doi":
        doi = _limpa_doi(ident)
        if completo:
            return f"https://api.crossref.org/works/{doi}", {"Accept": "application/json"}
        doi_q = quote(doi, safe="/")
        return (
            f"https://api.crossref.org/works?filter=doi:{doi_q}&select={_CROSSREF_SELECT}",
            {"Accept": "application/json"},
        )
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
        r = httpx.get(url, headers=headers, timeout=httpx.Timeout(20.0, connect=CONEXAO_S),
                      follow_redirects=True)
        return r.status_code, r.content
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"registro-fora:{type(exc).__name__}") from exc


def _resumo_doi(work: dict[str, Any]) -> dict[str, Any]:
    """Extrai resumo compacto de um item Crossref sem referências."""
    titulos = work.get("title")
    titulo = titulos[0] if isinstance(titulos, list) and titulos else (titulos if isinstance(titulos, str) else None)

    autores: list[str] = []
    for a in work.get("author") or []:
        if not isinstance(a, dict):
            continue
        nome = f"{a.get('given', '')} {a.get('family', '')}".strip() or a.get("name", "")
        if nome:
            autores.append(nome)

    ano = None
    for chave_data in ("published", "issued"):
        partes = ((work.get(chave_data) or {}).get("date-parts") or [[]])[0]
        if partes and isinstance(partes[0], int):
            ano = partes[0]
            break

    veiculos = work.get("container-title")
    veiculo = veiculos[0] if isinstance(veiculos, list) and veiculos else (veiculos if isinstance(veiculos, str) else None)

    ids = {k: v for k, v in {
        "doi": work.get("DOI"),
        "issn": work.get("ISSN"),
        "isbn": work.get("ISBN"),
        "url": work.get("URL"),
    }.items() if v}

    return {k: v for k, v in {
        "titulo": titulo,
        "autores": autores or None,
        "ano": ano,
        "veiculo": veiculo,
        "editora": work.get("publisher"),
        "tipo": work.get("type"),
        "identificadores": ids or None,
    }.items() if v is not None}


def resolver(tipo: str, ident: str, *, completo: bool = False, fetch: Fetch | None = None) -> dict[str, Any]:
    """Devolve {status, url, resolvedor, resolvido, bruto_bytes, registro, resumo}.

    `resolvido=False` (status 404/inexistente) NÃO é erro de fonte — é não-achado, que
    quem chama grava no manifesto. Erro de rede/registro fora, sim, levanta FalhaFonte.
    """
    if tipo not in TIPOS:
        raise FalhaFonte(f"tipo-desconhecido:{tipo}")
    url, headers = _url_de(tipo, ident, completo=completo)
    try:
        verifica_url(url)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec

    # Prazo total do ato (#4457 t3): o registro que não responde vira falha em JSON antes de a
    # porta cortar a conexão.
    relogio = Relogio()
    buscar = fetch or _fetch_httpx
    status, corpo = com_prazo(lambda: buscar(url, headers), relogio.resta(), onde=tipo)
    resolvido = 200 <= status < 300
    registro: Any = None
    resumo: dict[str, Any] | None = None
    if resolvido and corpo:
        try:
            registro = json.loads(corpo.decode("utf-8", "replace"))
        except (ValueError, UnicodeError):
            registro = None  # registro veio, mas não é JSON — bruto guarda o que veio
    if resolvido and tipo == "doi" and not completo and isinstance(registro, dict):
        items = (registro.get("message") or {}).get("items") or []
        if not items:
            resolvido = False
        else:
            resumo = _resumo_doi(items[0])
    return {
        "status": status,
        "url": url,
        "resolvedor": {"dominio": "rdap", "doi": "crossref", "orcid": "orcid",
                       "isbn": "openlibrary", "cnpj": "brasilapi"}[tipo],
        "resolvido": resolvido,
        "bruto_bytes": corpo,
        "registro": registro,
        "resumo": resumo,
    }
