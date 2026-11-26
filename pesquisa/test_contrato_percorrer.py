# componente: componente:verbo-pesquisar
"""Contrato do ato `percorrer` e da leitura de bruto na sessão (story #4458)."""
from __future__ import annotations

import gzip
import importlib.machinery
import importlib.util
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from pesquisa import atos, extrator
from pesquisa import manifesto as M
from pesquisa import percorrer as P
from pesquisa import robots as R
from pesquisa.envelope import UsoInvalido

_IP_PUBLICO_TESTE = "93.184.216.34"
_EXIT_OK = 0
_EXIT_USO = 2
_PROF_FICHA_TESTE = 3
_HTTP_OK = 200
_HTTP_NAO_ENCONTRADO = 404
_HTTP_INDISPONIVEL = 503
_TAMANHO_DOCX_FAKE = 48_120
_ESPERA_MIN_CRAWL_DELAY = 0.5
_HORA_FIXA = "2026-11-26T10:00:00Z"


def _derivador_simples(html: str, _base: str) -> dict[str, str]:
    texto = " ".join(html.split())
    return {"md_fit": texto, "md_raw": texto}


def _resposta_teste(
    url: str,
    corpo: bytes = b"",
    *,
    status: int = _HTTP_OK,
    tipo: str = "text/html; charset=utf-8",
    cabecalhos_extra: list[tuple[str, str]] | None = None,
) -> extrator.Resposta:
    cabecalhos = [("content-type", tipo), *(cabecalhos_extra or [])]
    return extrator.Resposta(
        corpo=corpo,
        status=status,
        cabecalhos=cabecalhos,
        url_pedida=url,
        url_final=url,
        hora=_HORA_FIXA,
    )


def _opcoes_rede_teste(requisitor: Any) -> P.OpcoesRede:
    return P.OpcoesRede(
        requisitor=requisitor,
        guarda_resolvedor=lambda _h: [_IP_PUBLICO_TESTE],
        dormir=lambda _s: None,
        derivador=_derivador_simples,
    )


def _carregar_cli_pesquisar() -> Any:
    caminho = Path(__file__).resolve().parents[1] / "bin" / "pesquisar"
    loader = importlib.machinery.SourceFileLoader("_cli_pesquisar_teste", str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ler_jsonl(caminho: Path) -> list[dict[str, Any]]:
    return [
        json.loads(ln)
        for ln in caminho.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def test_robots_rfc9309_curingas_ancora_precedencia_e_sitemaps() -> None:
    robots_gov = (
        "Sitemap: https://www.gov.br/sitemap.xml.gz\n"
        "User-agent: Yandex\n"
        "Disallow: /\n\n"
        "User-Agent: *\n"
        "Disallow: /economia/pt-br/internet/*\n"
        "Disallow: /*sendto_form$\n"
        "Disallow: /ebserh/*++theme++*\n"
        "Allow: /economia/pt-br/internet/aberta\n"
        "Crawl-delay: 0.5\n"
    )
    pol = R.analisa_robots(robots_gov, status=_HTTP_OK, host="www.gov.br")
    assert pol.sitemaps == ("https://www.gov.br/sitemap.xml.gz",)
    assert pol.crawl_delay == _ESPERA_MIN_CRAWL_DELAY

    ok_ficha, mot_ficha = pol.pode_buscar(
        "https://www.gov.br/governodigital/pt-br/publicacoes/ficha-de-sistema-de-ia"
    )
    assert ok_ficha is True and mot_ficha is None

    ok_form, mot_form = pol.pode_buscar("https://www.gov.br/governodigital/pt-br/sendto_form")
    assert ok_form is False and mot_form == "robots:/*sendto_form$"

    ok_form_meio, _ = pol.pode_buscar("https://www.gov.br/governodigital/sendto_form/ajuda")
    assert ok_form_meio is True

    ok_tema, mot_tema = pol.pode_buscar("https://www.gov.br/ebserh/x/++theme++padrao/app.css")
    assert ok_tema is False and mot_tema == "robots:/ebserh/*++theme++*"

    ok_mais_longa, _ = pol.pode_buscar("https://www.gov.br/economia/pt-br/internet/aberta")
    assert ok_mais_longa is True

    pol_404 = R.analisa_robots("Disallow: /\n", status=_HTTP_NAO_ENCONTRADO, host="exemplo.org")
    assert pol_404.pode_buscar("https://exemplo.org/qualquer")[0] is True

    pol_503 = R.analisa_robots("", status=_HTTP_INDISPONIVEL, host="exemplo.org")
    ok_503, mot_503 = pol_503.pode_buscar("https://exemplo.org/qualquer")
    assert ok_503 is False and mot_503 == "robots-status-503"


def test_percorrer_bfs_limites_profundidade_e_teto(tmp_path: Path) -> None:
    paginas = {
        "https://portal.exemplo/robots.txt": (_HTTP_NAO_ENCONTRADO, "text/plain", b""),
        "https://portal.exemplo/sitemap.xml": (_HTTP_NAO_ENCONTRADO, "text/plain", b""),
        "https://portal.exemplo/sitemap.xml.gz": (_HTTP_NAO_ENCONTRADO, "text/plain", b""),
        "https://portal.exemplo/": (
            _HTTP_OK,
            "text/html",
            b'<html><title>Raiz</title><a href="/n1a">A</a><a href="/n1b">B</a></html>',
        ),
        "https://portal.exemplo/n1a": (
            _HTTP_OK,
            "text/html",
            b'<html><title>N1A</title><a href="/n2">N2</a></html>',
        ),
        "https://portal.exemplo/n1b": (_HTTP_OK, "text/html", b"<html><title>N1B</title></html>"),
        "https://portal.exemplo/n2": (
            _HTTP_OK,
            "text/html",
            b'<html><title>N2</title><a href="/n3">N3</a></html>',
        ),
        "https://portal.exemplo/n3": (_HTTP_OK, "text/html", b"<html><title>N3</title></html>"),
    }
    ordem_get: list[str] = []

    def falso_req(metodo: str, url: str) -> extrator.Resposta:
        if metodo == "GET" and not url.endswith((".txt", ".xml", ".gz")):
            ordem_get.append(url)
        st, ct, corpo = paginas[url]
        return _resposta_teste(url, corpo, status=st, tipo=ct)

    rede = _opcoes_rede_teste(falso_req)
    trab_prof = M.Trabalho("p-prof", raiz=tmp_path)
    env_prof = atos.percorrer(
        "https://portal.exemplo/",
        trab=trab_prof,
        opcoes={"profundidade": 1, "teto": 20},
        opcoes_rede=rede,
    )
    assert env_prof["parou_por"] == "profundidade"
    assert ordem_get == [
        "https://portal.exemplo/",
        "https://portal.exemplo/n1a",
        "https://portal.exemplo/n1b",
    ]
    profs = {n["id"]: n["profundidade"] for n in env_prof["nos"] if n["tipo_no"] == "pagina"}
    assert profs == {
        "https://portal.exemplo/": 0,
        "https://portal.exemplo/n1a": 1,
        "https://portal.exemplo/n1b": 1,
    }

    ordem_get.clear()
    trab_teto = M.Trabalho("p-teto", raiz=tmp_path)
    env_teto = atos.percorrer(
        "https://portal.exemplo/",
        trab=trab_teto,
        opcoes={"profundidade": 4, "teto": 2},
        opcoes_rede=rede,
    )
    assert env_teto["parou_por"] == "teto"
    assert env_teto["resumo"]["paginas_visitadas"] == _EXIT_USO


def test_percorrer_cortesia_robots_intervalo_e_uma_conexao_por_host(tmp_path: Path) -> None:
    rotas = {
        "/robots.txt": (
            _HTTP_OK,
            "text/plain",
            b"User-agent: *\nDisallow: /*sendto_form$\nCrawl-delay: 0.5\n",
        ),
        "/sitemap.xml": (_HTTP_NAO_ENCONTRADO, "text/plain", b""),
        "/sitemap.xml.gz": (_HTTP_NAO_ENCONTRADO, "text/plain", b""),
        "/inicio": (
            _HTTP_OK,
            "text/html",
            b'<html><a href="/permitida">Ok</a><a href="/inicio/sendto_form">Form</a></html>',
        ),
        "/permitida": (_HTTP_OK, "text/html", b"<html><title>Permitida</title></html>"),
        "/inicio/sendto_form": (_HTTP_OK, "text/html", b"<html>NAO DEVE PEDIR</html>"),
    }
    pedidas: list[tuple[str, str]] = []
    transports_criados: list[str] = []

    def criar_transport(host: str) -> Any:
        transports_criados.append(host)

        def handler(request: httpx.Request) -> httpx.Response:
            pedidas.append((request.method, request.url.path))
            st, ct, corpo = rotas.get(request.url.path, (_HTTP_NAO_ENCONTRADO, "text/plain", b""))
            return httpx.Response(st, headers={"content-type": ct}, content=corpo)

        return httpx.MockTransport(handler)

    relogio = [100.0]
    dormidas: list[float] = []

    def dormir_falso(seg: float) -> None:
        dormidas.append(seg)
        relogio[0] += seg

    rede = P.OpcoesRede(
        transport_por_host=criar_transport,
        guarda_resolvedor=lambda _h: [_IP_PUBLICO_TESTE],
        dormir=dormir_falso,
        relogio_mono=lambda: relogio[0],
        derivador=_derivador_simples,
    )
    trab = M.Trabalho("p-cortesia", raiz=tmp_path)
    env = atos.percorrer(
        "https://cortes.exemplo/inicio",
        trab=trab,
        opcoes={"dominio": ["cortes.exemplo"], "profundidade": 2, "teto": 10, "intervalo": 0.2},
        opcoes_rede=rede,
    )

    assert pedidas[0] == ("GET", "/robots.txt")
    caminhos_pedidos = {cam for _, cam in pedidas}
    assert "/inicio/sendto_form" not in caminhos_pedidos
    assert transports_criados == ["cortes.exemplo"]
    assert env["resumo"]["conexoes_por_host"] == {"cortes.exemplo": 1}
    assert len(dormidas) >= _EXIT_USO
    assert all(d >= _ESPERA_MIN_CRAWL_DELAY - 1e-6 for d in dormidas)

    linhas_grafo = _ler_jsonl(Path(env["grafo"]["arquivo"]))
    puladas = [x for x in linhas_grafo if x["tipo"] == "no" and x.get("pulada")]
    assert len(puladas) == 1
    assert puladas[0]["id"] == "https://cortes.exemplo/inicio/sendto_form"
    assert puladas[0]["motivo"] == "robots:/*sendto_form$"
    assert puladas[0]["pedida"] is False


def test_percorrer_head_em_arquivos_e_sitemap_xml_gz(tmp_path: Path) -> None:
    sm_filho = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://gov.exemplo/portal/orfa</loc></url>"
        b"</urlset>"
    )
    sm_indice = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<sitemap><loc>https://gov.exemplo/sitemap-1.xml.gz</loc></sitemap>"
        b"</sitemapindex>"
    )
    metodos_por_url: list[tuple[str, str]] = []

    def falso_req(metodo: str, url: str) -> extrator.Resposta:
        metodos_por_url.append((metodo, url))
        if url.endswith("/robots.txt"):
            return _resposta_teste(
                url,
                b"User-agent: *\nSitemap: https://gov.exemplo/sitemap-index.xml.gz\n",
                tipo="text/plain",
            )
        if url.endswith("/sitemap-index.xml.gz"):
            return _resposta_teste(url, gzip.compress(sm_indice), tipo="application/gzip")
        if url.endswith("/sitemap-1.xml.gz"):
            return _resposta_teste(url, gzip.compress(sm_filho), tipo="application/octet-stream")
        if url.endswith("/ficha.docx/@@download/file"):
            assert metodo == "HEAD", "arquivo deve ser consultado apenas com HEAD"
            return _resposta_teste(
                url,
                tipo=extrator.TIPO_DOCX,
                cabecalhos_extra=[("content-length", str(_TAMANHO_DOCX_FAKE))],
            )
        if url.endswith("/portal"):
            return _resposta_teste(
                url,
                b'<html><title>Portal</title><a href="/portal/ficha.docx/@@download/file">Baixar Ficha</a></html>',
            )
        if url.endswith("/portal/orfa"):
            return _resposta_teste(url, b"<html><title>Pagina Orfa</title></html>")
        return _resposta_teste(url, status=_HTTP_NAO_ENCONTRADO, tipo="text/plain")

    trab = M.Trabalho("p-head-sm", raiz=tmp_path)
    env = atos.percorrer(
        "https://gov.exemplo/portal",
        trab=trab,
        opcoes={"dominios": ["gov.exemplo"], "profundidade": 2, "teto": 10},
        opcoes_rede=_opcoes_rede_teste(falso_req),
    )

    nos_por_id = {n["id"]: n for n in env["nos"]}
    arq_no = nos_por_id["https://gov.exemplo/portal/ficha.docx/@@download/file"]
    assert arq_no["tipo_no"] == "arquivo"
    assert arq_no["metodo"] == "HEAD"
    assert arq_no["tipo_conteudo"] == extrator.TIPO_DOCX
    assert arq_no["tamanho_bytes"] == _TAMANHO_DOCX_FAKE
    assert arq_no["profundidade"] == 1
    assert ("GET", "https://gov.exemplo/portal/ficha.docx/@@download/file") not in metodos_por_url

    orfa_no = nos_por_id["https://gov.exemplo/portal/orfa"]
    assert orfa_no["em_sitemap"] is True
    assert orfa_no["profundidade"] is None


def test_percorrer_canonical_fundido_metadados_e_ttps_quebrado(tmp_path: Path) -> None:
    html_semente = (
        "<html><head><title>Governo Digital</title></head><body>"
        '<nav id="portal-breadcrumbs"><li>Página Inicial<li>Página Inicial<li>Governo Digital</nav>'
        '<span class="documentPublished">Publicado em 02/07/2026 14h30</span>'
        '<a href="/ia">Núcleo IA</a>'
        '<a href="/ia-1"><img alt="Núcleo IA legado"></a>'
        '<a href="ttps://gov.exemplo/efgd-quebrado">EFGD 2024-2027</a>'
        '<a href="https://externo.org/guia">Guia Externo</a>'
        "</body></html>"
    ).encode()
    html_ia = (
        "<html><head>"
        '<base href="https://gov.exemplo/ia/ia-1/" />'
        '<link rel="canonical" href="https://gov.exemplo/ia" />'
        "<title>Ficha de Sistema de IA</title>"
        "</head><body>"
        '<span class="documentModified">Atualizado em 15/07/2026 10h00</span>'
        '<a href="sub">Subpágina relativa à base</a>'
        "</body></html>"
    ).encode()

    def falso_req(_metodo: str, url: str) -> extrator.Resposta:
        if url.endswith(("/robots.txt", "/sitemap.xml", "/sitemap.xml.gz", "/ia/ia-1/sub")):
            return _resposta_teste(url, status=_HTTP_NAO_ENCONTRADO, tipo="text/plain")
        if url == "https://gov.exemplo/":
            return _resposta_teste(url, html_semente)
        if url in ("https://gov.exemplo/ia", "https://gov.exemplo/ia-1"):
            return _resposta_teste(url, html_ia)
        raise AssertionError(f"URL inesperada pedida: {url}")

    trab = M.Trabalho("p-canon", raiz=tmp_path)
    env = atos.percorrer(
        "https://gov.exemplo/",
        trab=trab,
        opcoes={"dominios": ["gov.exemplo"], "profundidade": 2, "teto": 10},
        opcoes_rede=_opcoes_rede_teste(falso_req),
    )

    paginas = {n["id"]: n for n in env["nos"] if n["tipo_no"] == "pagina"}
    assert set(paginas) == {"https://gov.exemplo/", "https://gov.exemplo/ia"}

    raiz = paginas["https://gov.exemplo/"]
    assert raiz["breadcrumb"] == ["Página Inicial", "Página Inicial", "Governo Digital"]
    assert raiz["data_visivel"] == "Publicado em 02/07/2026 14h30"

    no_ia = paginas["https://gov.exemplo/ia"]
    assert no_ia["canonical"] == "https://gov.exemplo/ia"
    assert no_ia["profundidade"] == 1
    assert "https://gov.exemplo/ia" in no_ia["urls"]
    assert "https://gov.exemplo/ia-1" in no_ia["urls"]
    assert "https://gov.exemplo/ia/ia-1/" in no_ia["urls"]

    assert len(env["arestas_quebradas"]) == 1
    queb = env["arestas_quebradas"][0]
    assert queb["href"] == "ttps://gov.exemplo/efgd-quebrado"
    assert queb["quebrada"] is True
    assert queb["motivo"] == "esquema-malformado:ttps"

    linhas_grafo = _ler_jsonl(Path(env["grafo"]["arquivo"]))
    arestas = [x for x in linhas_grafo if x["tipo"] == "aresta"]
    legado = next(a for a in arestas if a["href"] == "/ia-1")
    assert legado["texto"] == "Núcleo IA legado"
    ext = next(a for a in arestas if a["href"] == "https://externo.org/guia")
    assert ext["mesmo_dominio"] is False
    assert ext["dominio_permitido"] is False
    rel_base = next(a for a in arestas if a["href"] == "sub")
    assert rel_base["destino"] == "https://gov.exemplo/ia/ia-1/sub"


def test_custodia_bruto_abre_na_sessao_e_cli_recusa_uso_invalido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(M, "RAIZ_VAR", tmp_path)
    html = b"<html><head><title>Semente</title></head>\n<body>Linha dois do bruto</body></html>\n"

    def falso_req(_metodo: str, url: str) -> extrator.Resposta:
        if url == "https://site.exemplo/":
            return _resposta_teste(url, html)
        return _resposta_teste(url, status=_HTTP_NAO_ENCONTRADO, tipo="text/plain")

    rede = _opcoes_rede_teste(falso_req)
    trab = M.Trabalho("t-sessao", raiz=tmp_path)
    env = atos.percorrer(
        "https://site.exemplo/",
        trab=trab,
        opcoes={"profundidade": 0, "teto": 5},
        opcoes_rede=rede,
    )
    no = env["nos"][0]
    caminho_bruto = Path(no["bruto"])
    assert caminho_bruto.is_file()
    assert M.sha256_bytes(caminho_bruto.read_bytes()) == no["sha256"]

    cli = _carregar_cli_pesquisar()
    rc_cam = cli.main(["pesquisar", "ler", str(caminho_bruto), "--linhas", "2-2"])
    saida_cam = capsys.readouterr().out
    assert rc_cam == _EXIT_OK
    assert "Linha dois do bruto" in saida_cam

    rc_chave = cli.main(["pesquisar", "ler", f"pesquisa:t-sessao/bruto/{caminho_bruto.name}"])
    saida_chave = capsys.readouterr().out
    assert rc_chave == _EXIT_OK
    assert "<title>Semente</title>" in saida_chave

    with pytest.raises(UsoInvalido, match="semente-fora-dos-dominios"):
        atos.percorrer(
            "https://fora.exemplo/",
            trab=trab,
            opcoes={"dominios": ["site.exemplo"], "profundidade": 1, "teto": 5},
            opcoes_rede=rede,
        )

    rc_neg = cli.main(
        ["pesquisar", "percorrer", "https://site.exemplo/", "--profundidade", "-1", "--trabalho", "t-sessao"]
    )
    err_neg = capsys.readouterr().err
    assert rc_neg == _EXIT_USO
    assert "profundidade-negativa" in err_neg


def test_percorrer_prioriza_conteudo_sobre_cromo_e_deduplica_base_plone(tmp_path: Path) -> None:
    paginas = {
        "https://gov.exemplo/portal": (
            b'<html><head><base href="https://gov.exemplo/portal/home/" />'
            b'<link rel="canonical" href="https://gov.exemplo/portal" /></head><body>'
            b'<nav id="main-navigation">'
            b'<a href="#topo">Topo</a>'
            b'<a href="/portal/menu-1">M1</a><a href="/portal/menu-2">M2</a><a href="/portal/menu-3">M3</a>'
            b"</nav>"
            b'<main><a href="/portal/ind">IND</a></main></body></html>'
        ),
        "https://gov.exemplo/portal/ind": b'<html><body><main><a href="/portal/ind/ia">IA</a></main></body></html>',
        "https://gov.exemplo/portal/ind/ia": (
            b'<html><body><main><a href="/portal/ind/ia/ficha">Ficha IA</a></main></body></html>'
        ),
        "https://gov.exemplo/portal/ind/ia/ficha": b"<html><title>Ficha de Sistema de IA</title></html>",
        "https://gov.exemplo/portal/menu-1": b"<html><title>Menu 1</title></html>",
        "https://gov.exemplo/portal/menu-2": b"<html><title>Menu 2</title></html>",
        "https://gov.exemplo/portal/menu-3": b"<html><title>Menu 3</title></html>",
    }
    gets: list[str] = []

    def falso_req(metodo: str, url: str) -> extrator.Resposta:
        if metodo == "GET" and url in paginas:
            gets.append(url)
            return _resposta_teste(url, paginas[url])
        return _resposta_teste(url, status=_HTTP_NAO_ENCONTRADO, tipo="text/plain")

    trab = M.Trabalho("p-cromo", raiz=tmp_path)
    env = atos.percorrer(
        "https://gov.exemplo/portal",
        trab=trab,
        opcoes={"dominios": ["gov.exemplo"], "profundidade": 4, "teto": 4},
        opcoes_rede=_opcoes_rede_teste(falso_req),
    )
    assert gets == [
        "https://gov.exemplo/portal",
        "https://gov.exemplo/portal/ind",
        "https://gov.exemplo/portal/ind/ia",
        "https://gov.exemplo/portal/ind/ia/ficha",
    ]
    nos_por_id = {n["id"]: n for n in env["nos"] if n["tipo_no"] == "pagina"}
    assert nos_por_id["https://gov.exemplo/portal/ind/ia/ficha"]["profundidade"] == _PROF_FICHA_TESTE
