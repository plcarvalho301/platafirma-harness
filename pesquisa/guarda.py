"""Guarda de rede — fail-closed para dentro (spec §2.6, §7 SSRF).

O verbo roda como `claudinho`, com Valkey, Keycloak e o ops-server no loopback. Uma
URL de terceiro que resolva para faixa privada, loopback, link-local ou `.internal` é
recusada ANTES do request. É código, testado (par de URL privada/pública, §8.3), não
configuração.

Fail-closed de verdade: se o host não resolve, a guarda RECUSA (não deixa passar a
dúvida). O ganho é assimétrico — uma recusa injusta custa uma mensagem; um SSRF que
alcança o Keycloak custa a casa.

A metabusca (SearXNG em 127.0.0.1:8888) NÃO passa por aqui: é consumo interno do verbo,
não URL de terceiro trazida pela sessão. Esta guarda vale para `ler`, `coletar` e
`historico`.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ESQUEMAS_OK = frozenset({"http", "https"})
SUFIXOS_NEGADOS = (".internal", ".local", ".localdomain")
NOMES_NEGADOS = frozenset({"localhost"})


class UrlRecusada(Exception):
    """URL barrada pela guarda. `causa` é legível; nunca vira request."""

    def __init__(self, causa: str) -> None:
        super().__init__(causa)
        self.causa = causa


def _ip_e_perigoso(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def verifica_url(url: str, *, resolvedor=None) -> str:
    """Devolve a URL se for segura; levanta `UrlRecusada` com causa se não.

    `resolvedor(host) -> list[str]` de IPs é injetável para teste (o default usa DNS
    real). Um host que aponta para QUALQUER endereço perigoso é recusado inteiro.
    """
    partes = urlsplit(url)
    esquema = (partes.scheme or "").lower()
    if esquema not in ESQUEMAS_OK:
        raise UrlRecusada(f"esquema-nao-permitido:{esquema or 'vazio'}")
    host = (partes.hostname or "").lower().rstrip(".")
    if not host:
        raise UrlRecusada("host-vazio")
    if host in NOMES_NEGADOS or host.endswith(SUFIXOS_NEGADOS):
        raise UrlRecusada(f"host-interno:{host}")

    # Host que já é IP literal: decide sem DNS.
    try:
        ip = ipaddress.ip_address(host)
        if _ip_e_perigoso(ip):
            raise UrlRecusada(f"ip-privado:{host}")
        return url
    except ValueError:
        pass  # não é IP literal — resolve por DNS abaixo

    resolve = resolvedor or _resolve_dns
    try:
        ips = resolve(host)
    except Exception as exc:  # noqa: BLE001 — fail-closed: dúvida de resolução recusa
        raise UrlRecusada(f"nao-resolve:{host}") from exc
    if not ips:
        raise UrlRecusada(f"nao-resolve:{host}")
    for bruto in ips:
        try:
            ip = ipaddress.ip_address(bruto)
        except ValueError:
            raise UrlRecusada(f"ip-invalido:{bruto}")
        if _ip_e_perigoso(ip):
            raise UrlRecusada(f"aponta-para-privado:{host}->{bruto}")
    return url


def _resolve_dns(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    return sorted({info[4][0] for info in infos})
