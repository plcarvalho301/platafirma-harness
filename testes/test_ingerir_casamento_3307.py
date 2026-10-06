"""#3307: o plano de `acervo ingerir biblioteca` diz o motivo de cada recusa.

A rag-api decide (duplicata, arquivo vazio, arquivo que não é o que o nome diz) e devolve o motivo no `detail`
do portão; o cliente fino o mostra na linha do item, em vez de só o nome do portão. O ambiente de teste do
harness não tem `requests`, que o verbo importa: o módulo é trocado por um dublê.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INGERIR = RAIZ / "bin" / "ingerir"


def _mod(monkeypatch):
    modulo = types.ModuleType("requests")
    modulo.exceptions = types.SimpleNamespace(RequestException=OSError)
    monkeypatch.setitem(sys.modules, "requests", modulo)
    loader = importlib.machinery.SourceFileLoader("ingerir_3307", str(INGERIR))
    spec = importlib.util.spec_from_loader("ingerir_3307", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _lote():
    return {"id": "lote-1", "autor": "dados", "ate": "catalogar", "ocr": False, "colecao": "firma",
            "resumo": {"ja_ingerido": 1, "bloqueada": 1, "reprovado": 1},
            "itens": [
                {"posicao": 0, "arquivo": "copia.pdf", "titulo": "Copia", "veredito": "ja_ingerido",
                 "portoes": [{"portao": "ja_ingerido", "resultado": "ja_ingerido", "title": "JaIngerido",
                              "detail": "o acervo já tem este arquivo: obra 1111 «Livro»"}]},
                {"posicao": 1, "arquivo": "vazio.pdf", "titulo": "Vazio", "veredito": "bloqueada",
                 "portoes": [{"portao": "origem", "resultado": "bloqueada", "title": "ArquivoVazio",
                              "detail": "arquivo vazio (0 bytes); não é obra servível"}]},
                {"posicao": 2, "arquivo": "minto.pdf", "titulo": "Minto", "veredito": "reprovado",
                 "portoes": [{"portao": "ficha", "resultado": "reprovado", "title": "ArquivoNaoAbre",
                              "detail": "o nome diz .pdf e os bytes dizem JSON"}]},
                {"posicao": 3, "arquivo": "ok.pdf", "titulo": "Ok", "veredito": "criar",
                 "portoes": [{"portao": "origem", "resultado": "aprovado"}]},
            ]}


def test_o_plano_mostra_o_motivo_de_cada_recusa(monkeypatch):
    saida = _mod(monkeypatch).formatar_tabela_plano(_lote()).splitlines()
    linha = {n: next(x for x in saida if x[4:].startswith(a)) for n, a in
             enumerate(["copia.pdf", "vazio.pdf", "minto.pdf", "ok.pdf"])}
    assert "obra 1111 «Livro»" in linha[0]
    assert "arquivo vazio (0 bytes)" in linha[1]
    assert "os bytes dizem JSON" in linha[2]
    assert linha[3].rstrip().endswith("todos aprovados")
