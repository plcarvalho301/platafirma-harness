"""Contrato da guarda de rede — SSRF fail-closed (spec §2.6, §7, §8.3).

`python3 -m pytest pesquisa/ -q` da raiz do repo. O par URL privada/pública é o teste
que o §8.3 exige em código; sem ele a guarda não está conferida.
"""

from __future__ import annotations

import pytest

from pesquisa.guarda import UrlRecusada, verifica_url


def _resolve_fixo(mapa):
    return lambda host: mapa.get(host, [])


def test_url_publica_passa():
    r = _resolve_fixo({"exemplo.org": ["93.184.216.34"]})
    assert verifica_url("https://exemplo.org/pagina", resolvedor=r) == "https://exemplo.org/pagina"


def test_host_que_resolve_para_privado_recusa():
    r = _resolve_fixo({"interno.exemplo.org": ["10.0.0.5"]})
    with pytest.raises(UrlRecusada) as e:
        verifica_url("https://interno.exemplo.org/x", resolvedor=r)
    assert "privado" in e.value.causa


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8888/",
    "http://169.254.169.254/latest/meta-data/",  # link-local (metadata cloud)
    "http://[::1]/",
    "http://192.168.0.10/",
    "http://10.1.2.3/",
])
def test_ip_literal_perigoso_recusa(url):
    with pytest.raises(UrlRecusada):
        verifica_url(url, resolvedor=_resolve_fixo({}))


@pytest.mark.parametrize("url", [
    "http://localhost/x",
    "https://algo.internal/y",
    "http://maquina.local/z",
])
def test_nome_interno_recusa(url):
    with pytest.raises(UrlRecusada):
        verifica_url(url, resolvedor=_resolve_fixo({}))


def test_esquema_nao_http_recusa():
    with pytest.raises(UrlRecusada) as e:
        verifica_url("file:///etc/passwd", resolvedor=_resolve_fixo({}))
    assert "esquema" in e.value.causa


def test_fail_closed_quando_nao_resolve():
    # dúvida de resolução RECUSA (não deixa passar) — o ganho é assimétrico
    def estoura(_host):
        raise OSError("dns fora")
    with pytest.raises(UrlRecusada) as e:
        verifica_url("https://sumiu.exemplo.org/", resolvedor=estoura)
    assert "nao-resolve" in e.value.causa
