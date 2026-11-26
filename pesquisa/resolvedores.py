"""Resolução determinística de identificador (spec §4.1b).

`resolver <tipo> <id>` responde "para onde X aponta" contra registro oficial — não é
metabusca. Resposta de registro tem credibilidade distinta de página indexada; o verbo
não julga, só registra a origem.

O resumo devolvido sem `--completo` traz só o que identifica o registro (#4457 t7). O do CNPJ
sai sem o quadro de sócios, que são pessoas naturais, pela política de dado de pessoa natural
com operação registrada; o bruto ainda guarda o registro inteiro, e o que fazer com ele está
no parecer pedido à segurança.

Tipos plugáveis; a lista fechada definitiva é política do dono no `settings.yml`. O
default aqui cobre os cinco do §4.1b. `fetch` é injetável (testes sem rede).
Não-resolução vira linha de não-achado, escrita por quem chama. O DOI que a Crossref não
conhece se procura na DataCite, que registra os DOIs do arXiv e do Zenodo.
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
DATACITE = "https://api.datacite.org/dois/"
RESOLVEDOR = {"dominio": "rdap", "doi": "crossref", "orcid": "orcid",
              "isbn": "openlibrary", "cnpj": "brasilapi"}


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

    from .manifesto import UA

    try:
        # Os registros públicos pedem que quem consulta se identifique (#4457 t7).
        r = httpx.get(url, headers={"User-Agent": UA, **headers},
                      timeout=httpx.Timeout(20.0, connect=CONEXAO_S), follow_redirects=True)
        return r.status_code, r.content
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"registro-fora:{type(exc).__name__}") from exc


def _primeiro(valor: Any) -> Any:
    if isinstance(valor, list):
        return valor[0] if valor else None
    return valor


def _sem_vazios(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


def _resumo_doi(work: dict[str, Any]) -> dict[str, Any]:
    """Extrai resumo compacto de um item Crossref sem referências."""
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

    ids = _sem_vazios({"doi": work.get("DOI"), "issn": work.get("ISSN"),
                       "isbn": work.get("ISBN"), "url": work.get("URL")})
    return _sem_vazios({
        "titulo": _primeiro(work.get("title")),
        "autores": autores,
        "ano": ano,
        "veiculo": _primeiro(work.get("container-title")),
        "editora": work.get("publisher"),
        "tipo": work.get("type"),
        "identificadores": ids,
    })


def _resumo_datacite(registro: dict[str, Any]) -> dict[str, Any]:
    """Resumo de um DOI da DataCite, nos mesmos campos do resumo da Crossref."""
    a = ((registro.get("data") or {}).get("attributes")) or {}
    autores = []
    for c in a.get("creators") or []:
        if isinstance(c, dict):
            nome = c.get("name") or f"{c.get('givenName', '')} {c.get('familyName', '')}".strip()
            if nome:
                autores.append(nome)
    editora = a.get("publisher")
    if isinstance(editora, dict):
        editora = editora.get("name")
    titulo = _primeiro([t.get("title") for t in a.get("titles") or [] if isinstance(t, dict)])
    return _sem_vazios({
        "titulo": titulo,
        "autores": autores,
        "ano": a.get("publicationYear"),
        "veiculo": (a.get("container") or {}).get("title"),
        "editora": editora,
        "tipo": (a.get("types") or {}).get("resourceTypeGeneral"),
        "identificadores": _sem_vazios({"doi": a.get("doi"), "url": a.get("url")}),
    })


def _valor(no: Any, *caminho: str) -> Any:
    for chave in caminho:
        if not isinstance(no, dict):
            return None
        no = no.get(chave)
    return no


def _resumo_orcid(rec: dict[str, Any]) -> dict[str, Any]:
    """Nome, vínculos e número de obras de um registro ORCID."""
    nome = " ".join(x for x in (
        _valor(rec, "person", "name", "given-names", "value"),
        _valor(rec, "person", "name", "family-name", "value"),
    ) if x)
    vinculos = []
    for grupo in _valor(rec, "activities-summary", "employments", "affiliation-group") or []:
        for s in (grupo or {}).get("summaries") or []:
            emp = (s or {}).get("employment-summary") or {}
            org = _valor(emp, "organization", "name")
            if org:
                vinculos.append(_sem_vazios({"organizacao": org, "cargo": emp.get("role-title")}))
    obras = _valor(rec, "activities-summary", "works", "group")
    return _sem_vazios({
        "orcid": _valor(rec, "orcid-identifier", "path"),
        "nome": nome,
        "vinculos": vinculos,
        "obras": len(obras) if isinstance(obras, list) else None,
    })


_CNPJ_CAMPOS = ("cnpj", "razao_social", "nome_fantasia", "descricao_situacao_cadastral",
                "data_inicio_atividade", "cnae_fiscal_descricao", "natureza_juridica",
                "porte", "municipio", "uf")


def _resumo_cnpj(reg: dict[str, Any]) -> dict[str, Any]:
    """O que identifica a pessoa jurídica, sem o quadro de sócios (pessoas naturais)."""
    return _sem_vazios({k: reg.get(k) for k in _CNPJ_CAMPOS})


def _pede(buscar: Fetch, url: str, headers: dict, relogio: Relogio, onde: str) -> tuple[int, bytes]:
    try:
        verifica_url(url)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec
    # Prazo total do ato (#4457 t3): o registro que não responde vira falha em JSON antes de a
    # porta cortar a conexão.
    return com_prazo(lambda: buscar(url, headers), relogio.resta(), onde=onde)


def _json(corpo: bytes | None) -> Any:
    if not corpo:
        return None
    try:
        return json.loads(corpo.decode("utf-8", "replace"))
    except (ValueError, UnicodeError):
        return None  # registro veio, mas não é JSON — bruto guarda o que veio


def resolver(tipo: str, ident: str, *, completo: bool = False, fetch: Fetch | None = None) -> dict[str, Any]:
    """Devolve {status, url, resolvedor, resolvido, bruto_bytes, registro, resumo}.

    `resolvido=False` (status 404/inexistente) NÃO é erro de fonte — é não-achado, que
    quem chama grava no manifesto. Erro de rede/registro fora, sim, levanta FalhaFonte.
    """
    if tipo not in TIPOS:
        raise FalhaFonte(f"tipo-desconhecido:{tipo}")
    buscar = fetch or _fetch_httpx
    relogio = Relogio()
    url, headers = _url_de(tipo, ident, completo=completo)
    resolvedor = RESOLVEDOR[tipo]
    status, corpo = _pede(buscar, url, headers, relogio, tipo)
    resolvido = 200 <= status < 300
    registro = _json(corpo) if resolvido else None
    resumo: dict[str, Any] | None = None

    if resolvido and tipo == "doi" and not completo and isinstance(registro, dict):
        items = (registro.get("message") or {}).get("items") or []
        if items:
            resumo = _resumo_doi(items[0])
        else:
            resolvido = False

    if tipo == "doi" and not resolvido:
        # A Crossref não conhece o DOI: a DataCite registra os do arXiv, do Zenodo e de dados.
        url = DATACITE + quote(_limpa_doi(ident), safe="/")
        resolvedor = "datacite"
        status, corpo = _pede(buscar, url, {"Accept": "application/vnd.api+json"}, relogio, "datacite")
        registro = _json(corpo) if 200 <= status < 300 else None
        # Só vale como achado o registro que traz o DOI: 2xx sem `data` não é DOI da DataCite.
        resolvido = isinstance(registro, dict) and isinstance(registro.get("data"), dict)
        if not resolvido:
            registro = None
        elif not completo:
            resumo = _resumo_datacite(registro)

    if resolvido and not completo and isinstance(registro, dict):
        if tipo == "orcid":
            resumo = _resumo_orcid(registro)
        elif tipo == "cnpj":
            resumo = _resumo_cnpj(registro)

    return {
        "status": status,
        "url": url,
        "resolvedor": resolvedor,
        "resolvido": resolvido,
        "bruto_bytes": corpo,
        "registro": registro,
        "resumo": resumo,
    }
