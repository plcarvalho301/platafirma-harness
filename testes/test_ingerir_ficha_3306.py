"""#3306: o plano de `acervo ingerir biblioteca` mostra a ficha de cada arquivo (spec acervo-obra §7).

O leitor da ficha mora no serviço do conversor e a gravação na rag-api (platafirma-conhecimento); o
cliente fino só mostra o que o portão `ficha` do plano traz. Aqui a rag-api é um dublê que devolve o plano
que ela devolveria, e o que se prova é o cliente: a coluna Formato, o `?` do arquivo que o conversor não
leu, o `-` do que não ganha ficha no plano, e que o `.pdf` que é JSON não aparece como PDF.

O ambiente de teste do harness não tem `requests`, que o verbo importa: o módulo `requests` é trocado por
um dublê com o que o verbo usa (`put`, `post`, `exceptions`, `Response`), e o `main()` roda de verdade.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INGERIR = RAIZ / "bin" / "ingerir"

FICHAS = {
    "minto-pyramid.pdf": {"formato": "JSON", "versao": None, "tipo": "application/json",
                          "identificacao": "identificado", "paginas": None, "paginas_ocr": None},
    "red-team.pdf": {"formato": "GZIP", "versao": None, "tipo": None,
                     "identificacao": "identificado", "paginas": None, "paginas_ocr": None},
    "livro.pdf": {"formato": "PDF", "versao": "1.7", "tipo": "application/pdf",
                  "identificacao": "identificado", "paginas": 23, "paginas_ocr": 2},
}


class _Resposta:
    def __init__(self, status: int, corpo: dict | None = None):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo) if corpo is not None else ""

    def json(self):
        return self._corpo


def _requests_falso(visto: dict):
    """O `requests` que o verbo usa, contra uma rag-api de mentira que devolve o plano do lote."""
    modulo = types.ModuleType("requests")
    modulo.Response = _Resposta
    modulo.exceptions = types.SimpleNamespace(RequestException=OSError)

    def put(url, data=None, headers=None, **_):
        data.read()
        return _Resposta(201)

    def post(url, json=None, headers=None, **_):
        visto["lote"] = json
        itens = []
        for posicao, item in enumerate(json["itens"]):
            portoes = [{"portao": "origem", "resultado": "aprovado"},
                       {"portao": "ficha", "resultado": "aprovado", "ficha": FICHAS[item["arquivo"]]}]
            itens.append({"posicao": posicao, "arquivo": item["arquivo"], "titulo": item["titulo"],
                          "veredito": "criar", "portoes": portoes})
        return _Resposta(201, {"id": "lote-1", "autor": json["autor"], "ate": json["ate"], "ocr": False,
                               "colecao": json["colecao"], "resumo": {"criar": len(itens)}, "itens": itens})

    modulo.put, modulo.post = put, post
    return modulo


def _mod(monkeypatch, visto: dict | None = None):
    monkeypatch.setitem(sys.modules, "requests", _requests_falso(visto if visto is not None else {}))
    loader = importlib.machinery.SourceFileLoader("ingerir_3306", str(INGERIR))
    spec = importlib.util.spec_from_loader("ingerir_3306", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _item(ficha=None, resultado="aprovado"):
    portao = {"portao": "ficha", "resultado": resultado}
    if ficha is not None:
        portao["ficha"] = ficha
    return {"portoes": [{"portao": "origem", "resultado": "aprovado"}, portao]}


# --- a célula ----------------------------------------------------------------------------------------


def test_a_celula_diz_formato_versao_paginas_e_ocr(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item(FICHAS["livro.pdf"])) == "PDF 1.7 · 23p · 2 OCR"
    assert mod.descrever_ficha(_item(FICHAS["minto-pyramid.pdf"])) == "JSON"
    assert mod.descrever_ficha(_item(FICHAS["red-team.pdf"])) == "GZIP"


def test_pdf_sem_pagina_de_ocr_nao_poe_ocr_na_celula(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item({**FICHAS["livro.pdf"], "paginas_ocr": 0})) == "PDF 1.7 · 23p"


def test_ficha_que_o_conversor_nao_leu_no_plano_sai_com_interrogacao(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item(None, "indisponivel")) == "?"


def test_item_sem_portao_ficha_sai_com_traco_e_formato_desconhecido_se_diz(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha({"portoes": [{"portao": "ja_ingerido", "resultado": "ja_ingerido"}]}) == "-"
    assert mod.descrever_ficha({}) == "-"
    assert mod.descrever_ficha(_item({"formato": None, "identificacao": "desconhecido"})) == "desconhecido"


# --- o plano de uma pasta de teste ---------------------------------------------------------------------


def test_o_plano_de_uma_pasta_de_teste_mostra_a_ficha_de_cada_arquivo(monkeypatch, tmp_path, capsys):
    """O aceite do card, do lado do cliente: `minto-pyramid.pdf` (JSON) sai JSON, `red-team.pdf` (GZIP)
    sai GZIP, e o PDF de verdade traz a versão, as páginas e as que pedem OCR."""
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "minto-pyramid.pdf").write_bytes(b'{"piramide": [1, 2]}')
    (pasta / "red-team.pdf").write_bytes(b"\x1f\x8b\x08\x00" + b"x" * 40)
    (pasta / "livro.pdf").write_bytes(b"%PDF-1.7\n" + b"0" * 100)
    monkeypatch.setenv("HOME", str(tmp_path))  # o manifesto do lote não vai para a bancada de verdade
    visto: dict = {}
    mod = _mod(monkeypatch, visto)
    monkeypatch.setattr(sys, "argv", ["ingerir", "--lote", str(pasta)])
    with pytest.raises(SystemExit) as saida:
        mod.main()
    assert saida.value.code == 0
    out = capsys.readouterr().out
    assert "Formato (ficha)" in out
    linhas = {arq: linha for linha in out.splitlines() for arq in FICHAS if linha[4:].startswith(arq)}
    assert set(linhas) == set(FICHAS), out
    assert "JSON" in linhas["minto-pyramid.pdf"] and "GZIP" in linhas["red-team.pdf"]
    assert "PDF" not in linhas["minto-pyramid.pdf"].replace("minto-pyramid.pdf", "")
    assert "PDF 1.7 · 23p · 2 OCR" in linhas["livro.pdf"]
    # o cliente não manda formato: a ficha é lida pela rag-api nos bytes, não no que o cliente diz do nome
    assert all("formato" not in item and "tipo" not in item for item in visto["lote"]["itens"])
