"""Consertos do verbo `pesquisar` na revisão de 15/11/2026 (#2856 linhas 93, 546, 661, 662 e 663).

Sem rede, sem SearXNG e sem browser: o coletor, a metabusca, o leitor e o Wayback são falsos.

  93   falha de rede leva o caminho que sobra (outra fonte primária, cópia de terceiro)
  546  `consultar --cat codigo` diz onde sai a documentação de ferramenta
  661  `historico --em` devolve envelope, em vez de cair com TypeError
  662  `coletar` em paralelo devolve o stdout ao processo
  663  `historico` lista as capturas mais recentes, a última primeiro
"""
from __future__ import annotations

import contextlib
import functools
import json
import sys
import threading
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from pesquisa import atos, extrator, historico, manifesto as M, searxng  # noqa: E402
from pesquisa.envelope import FalhaFonte  # noqa: E402

PUB = lambda host: ["93.184.216.34"]  # noqa: E731 — resolvedor de guarda que devolve IP público
URL = "http://93.184.216.34/p"


# ------------------------------------------------------------------ linha 93
def test_falha_de_rede_leva_o_caminho_que_sobra(tmp_path):
    httpx = pytest.importorskip("httpx")
    t = M.Trabalho("r93", raiz=tmp_path)

    def handler(req):
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.", request=req)

    col = functools.partial(extrator._coletor_httpx, transport=httpx.MockTransport(handler))
    with pytest.raises(FalhaFonte) as e:
        extrator.ler(URL, t, coletor=col, guarda_resolvedor=PUB)
    assert e.value.causa == "rede:RemoteProtocolError"
    assert "Server disconnected" in e.value.extra["detalhe"]
    assert "outra fonte primária" in e.value.extra["sugestao"]
    assert "historico <url> --em" in e.value.extra["sugestao"]
    linha = t.linhas()[-1]
    assert linha["nao_achado"] is True and "historico <url>" in linha["sugestao"]


# ------------------------------------------------------------------ linha 546
def _metabusca_vazia(*a, **k):
    return {"resultados": [], "engines_ok": [], "engines_falha": [], "engines_vivos": ["mdn"]}


def test_consultar_em_codigo_diz_onde_sai_a_documentacao(tmp_path, monkeypatch):
    t = M.Trabalho("c546", raiz=tmp_path)
    monkeypatch.setattr(searxng, "consultar", _metabusca_vazia)
    env = atos.consultar("jq manual path expressions", k=4, categoria="codigo", desde=None,
                         idioma="auto", trab=t)
    assert env["ok"] and "--cat geral" in env["dica"] and "documentação" in env["dica"]


def test_consultar_fora_de_codigo_nao_leva_dica(tmp_path, monkeypatch):
    t = M.Trabalho("c546b", raiz=tmp_path)
    monkeypatch.setattr(searxng, "consultar", _metabusca_vazia)
    for cat in ("geral", "ciencia", "social"):
        env = atos.consultar("jq manual", k=4, categoria=cat, desde=None, idioma="auto", trab=t)
        assert "dica" not in env


# ------------------------------------------------------------------ linha 661
def test_historico_em_devolve_envelope_com_a_url_pedida_e_a_do_arquivo(tmp_path, monkeypatch):
    t = M.Trabalho("h661", raiz=tmp_path)
    pedidos = []

    def falso_ler(url, trab, **kw):
        pedidos.append((url, kw))
        return {"n": 1, "url": url, "url_final": url.replace("20261001000000", "20260930101010"),
                "conteudo": "Art. 1º Esta Lei dispõe", "status": 200, "sha256": "abc"}

    monkeypatch.setattr(extrator, "ler", falso_ler)
    env = atos.hist("https://exemplo.org/lei.htm", em="2026-10-01", salvar=False,
                    leitura={"foco": "art. 1", "max_chars": 900, "offset": 0}, trab=t)
    arquivo = "http://web.archive.org/web/20261001000000id_/https://exemplo.org/lei.htm"
    assert env["ok"] and env["ato"] == "historico" and env["tipo"] == "dado"
    assert env["url"] == "https://exemplo.org/lei.htm" and env["em"] == "2026-10-01"
    assert env["url_arquivo"] == arquivo and env["origem"] == "arquivo"
    assert "20260930101010" in env["url_final"] and env["conteudo"].startswith("Art. 1º")
    assert pedidos[0][0] == arquivo
    assert pedidos[0][1]["foco"] == "art. 1" and pedidos[0][1]["max_chars"] == 900


# ------------------------------------------------------------------ linha 662
def test_coletar_em_paralelo_devolve_o_stdout_ao_processo(tmp_path, monkeypatch):
    """Duas leituras trocam o stdout na ordem que o perdia: A entra, B entra, A sai, B sai."""
    t = M.Trabalho("c662", raiz=tmp_path)
    a_entrou, b_entrou, a_saiu = threading.Event(), threading.Event(), threading.Event()

    def falso_ler(url, trab, **kw):
        # o que o derivador de verdade faz enquanto a Crawl4AI fala
        if url.endswith("/a"):
            with contextlib.redirect_stdout(sys.stderr):
                a_entrou.set()
                assert b_entrou.wait(5)
            a_saiu.set()
        else:
            assert a_entrou.wait(5)
            with contextlib.redirect_stdout(sys.stderr):
                b_entrou.set()
                assert a_saiu.wait(5)
        return {"n": 1, "sha256": "abc", "status": 200, "tipo_real": "text/html", "binario": False}

    monkeypatch.setattr(extrator, "ler", falso_ler)
    antes = sys.stdout
    env = atos.coletar(["http://x.org/a", "http://x.org/b"], trab=t)
    assert sys.stdout is antes, "o coletar deixou o stdout do processo trocado"
    assert env["ok"] and env["total"] == 2 and all(c["ok"] for c in env["coletados"])


def test_coletar_repassa_a_saida_da_pagina_que_depende_de_script(tmp_path, monkeypatch):
    t = M.Trabalho("c662b", raiz=tmp_path)

    def falso_ler(url, trab, **kw):
        raise FalhaFonte("pagina-depende-de-javascript", sugestao="--render")

    monkeypatch.setattr(extrator, "ler", falso_ler)
    env = atos.coletar(["http://x.org/spa"], trab=t)
    assert env["coletados"] == [{"url": "http://x.org/spa", "ok": False,
                                 "causa": "pagina-depende-de-javascript",
                                 "sugestao": "ler <url> --render"}]


# ------------------------------------------------------------------ linha 663
def test_capturas_pede_as_mais_recentes_e_devolve_a_ultima_primeiro():
    pedidos = []

    def fetch(url, headers):
        pedidos.append(url)
        corpo = json.dumps([["timestamp", "original", "statuscode", "digest"],
                            ["20260101000000", "http://exemplo.org/", "200", "A"],
                            ["20261104180620", "http://exemplo.org/", "200", "B"]]).encode()
        return 200, corpo

    r = historico.capturas(URL, fetch=fetch)
    assert f"limit=-{historico.MAX_CAPTURAS}" in pedidos[0] and "collapse=digest" in pedidos[0]
    assert [c["timestamp"] for c in r["capturas"]] == ["20261104180620", "20260101000000"]
    assert r["total"] == 2 and r["ordem"] == "mais recente primeiro"
    assert historico.MAX_CAPTURAS <= 20


def test_capturas_vazias_seguem_sendo_nao_achado():
    r = historico.capturas(URL, fetch=lambda url, headers: (200, b"[]"))
    assert r["capturas"] == [] and r["total"] == 0


def test_url_da_captura_pede_o_corpo_como_o_arquivo_capturou():
    assert historico.url_captura("https://exemplo.org/p", "2026-10-01") == \
        "http://web.archive.org/web/20261001000000id_/https://exemplo.org/p"
