# componente: componente:verbo-pesquisar
"""Contrato dos resolvedores — DataCite, resumos de ORCID e CNPJ e prazo total (card #4457 t7).

Sem rede: o `fetch` é falso, e a guarda de rede só resolve nomes públicos conhecidos.
"""

from __future__ import annotations

import json
import time

import pytest

from pesquisa import prazo, resolvedores
from pesquisa.envelope import FalhaFonte


@pytest.fixture(autouse=True)
def _guarda_sem_dns(monkeypatch):
    monkeypatch.setattr(resolvedores, "verifica_url", lambda url: None)


def _fetch_por_host(respostas):
    chamadas = []

    def _f(url, headers):
        chamadas.append(url)
        for prefixo, (status, corpo) in respostas.items():
            if url.startswith(prefixo):
                return status, json.dumps(corpo).encode() if corpo is not None else b""
        return 404, b""
    _f.chamadas = chamadas
    return _f


DATACITE_ARXIV = {"data": {"id": "10.48550/arxiv.2305.14314", "attributes": {
    "doi": "10.48550/arxiv.2305.14314",
    "titles": [{"title": "QLoRA: Efficient Finetuning of Quantized LLMs"}],
    "creators": [{"name": "Dettmers, Tim"}, {"givenName": "Artidoro", "familyName": "Pagnoni"}],
    "publicationYear": 2023, "publisher": "arXiv",
    "types": {"resourceTypeGeneral": "Preprint"}, "url": "https://arxiv.org/abs/2305.14314",
}}}


def test_doi_que_a_crossref_nao_conhece_sai_pela_datacite():
    f = _fetch_por_host({
        "https://api.crossref.org/": (200, {"message": {"items": []}}),
        "https://api.datacite.org/dois/": (200, DATACITE_ARXIV),
    })
    r = resolvedores.resolver("doi", "10.48550/arXiv.2305.14314", fetch=f)
    assert r["resolvido"] and r["resolvedor"] == "datacite"
    assert r["url"] == "https://api.datacite.org/dois/10.48550/arXiv.2305.14314"
    assert r["resumo"] == {
        "titulo": "QLoRA: Efficient Finetuning of Quantized LLMs",
        "autores": ["Dettmers, Tim", "Artidoro Pagnoni"],
        "ano": 2023, "editora": "arXiv", "tipo": "Preprint",
        "identificadores": {"doi": "10.48550/arxiv.2305.14314", "url": "https://arxiv.org/abs/2305.14314"},
    }


def test_doi_que_nenhuma_das_duas_conhece_e_nao_achado():
    f = _fetch_por_host({"https://api.crossref.org/": (200, {"message": {"items": []}})})
    r = resolvedores.resolver("doi", "10.0/inexistente", fetch=f)
    assert r["resolvido"] is False and r["resolvedor"] == "datacite" and r["registro"] is None
    assert len(f.chamadas) == 2


def test_doi_da_crossref_nao_pergunta_a_datacite():
    item = {"DOI": "10.1145/3597503", "title": ["Estudo"]}
    f = _fetch_por_host({"https://api.crossref.org/": (200, {"message": {"items": [item]}})})
    r = resolvedores.resolver("doi", "10.1145/3597503", fetch=f)
    assert r["resolvedor"] == "crossref" and len(f.chamadas) == 1


def test_resumo_do_cnpj_sai_sem_o_quadro_de_socios():
    reg = {"cnpj": "00394460000141", "razao_social": "MINISTERIO DA FAZENDA",
           "descricao_situacao_cadastral": "ATIVA", "municipio": "BRASILIA", "uf": "DF",
           "qsa": [{"nome_socio": "FULANO DE TAL", "cnpj_cpf_do_socio": "***123456**"}]}
    f = _fetch_por_host({"https://brasilapi.com.br/": (200, reg)})
    r = resolvedores.resolver("cnpj", "00.394.460/0001-41", fetch=f)
    assert r["resumo"]["razao_social"] == "MINISTERIO DA FAZENDA"
    assert "qsa" not in r["resumo"] and "FULANO" not in json.dumps(r["resumo"])


def test_resumo_do_orcid_traz_nome_vinculos_e_obras():
    rec = {"orcid-identifier": {"path": "0000-0002-1825-0097"},
           "person": {"name": {"given-names": {"value": "Josiah"}, "family-name": {"value": "Carberry"}}},
           "activities-summary": {
               "employments": {"affiliation-group": [{"summaries": [{"employment-summary": {
                   "organization": {"name": "Brown University"}, "role-title": "Professor"}}]}]},
               "works": {"group": [{}, {}, {}]}}}
    f = _fetch_por_host({"https://pub.orcid.org/": (200, rec)})
    r = resolvedores.resolver("orcid", "0000-0002-1825-0097", fetch=f)
    assert r["resumo"] == {"orcid": "0000-0002-1825-0097", "nome": "Josiah Carberry",
                           "vinculos": [{"organizacao": "Brown University", "cargo": "Professor"}],
                           "obras": 3}


def test_completo_devolve_o_registro_sem_resumo():
    reg = {"cnpj": "00394460000141", "qsa": []}
    f = _fetch_por_host({"https://brasilapi.com.br/": (200, reg)})
    r = resolvedores.resolver("cnpj", "00394460000141", completo=True, fetch=f)
    assert r["resumo"] is None and r["registro"] == reg


def test_registro_que_nao_responde_sai_por_prazo(monkeypatch):
    monkeypatch.setattr(prazo, "PRAZO_TOTAL_S", 0.2)

    def parado(url, headers):
        time.sleep(2)
        return 200, b"{}"

    inicio = time.monotonic()
    with pytest.raises(FalhaFonte) as e:
        resolvedores.resolver("doi", "10.1145/3597503", fetch=parado)
    assert time.monotonic() - inicio < 1.5 and e.value.causa == "prazo-total-esgotado"
