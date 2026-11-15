"""Testes da DT-228: --exposicao em catalogar e exposicao/portao nos planos de ingerir e espelhar."""
import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2]
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))
if "requests" not in sys.modules:
    sys.modules["requests"] = MagicMock()


def _carregar(nome, caminho):
    loader = SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ingerir_mod = _carregar("ingerir_dt228", HARNESS_DIR / "bin" / "ingerir")
curar_mod = _carregar("curar_dt228", HARNESS_DIR / "bin" / "curar")


def test_ingerir_plano_mostra_exposicao_e_portao_parada():
    lote = {
        "id": "1b01e9fe",
        "autor": "dados",
        "motor": None,
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 2, "edicao": 0, "ja_ingerido": 0, "bloqueada": 0, "reprovado": 0},
        "itens": [
            {
                "posicao": 1,
                "arquivo": "records.pdf",
                "titulo": "Records",
                "veredito": "criar",
                "exposicao": "trecho",
                "portao_parada": "transcrição/índice (para em catalogar; falta espelhar, indexar e promover)",
                "portoes": [],
            },
            {
                "posicao": 2,
                "arquivo": "planilha.xlsx",
                "titulo": "Planilha",
                "veredito": "criar",
                "exposicao": "arquivo",
                "portao_parada": "nenhum (servida inteira, exposição arquivo)",
                "portoes": [],
            },
        ],
    }
    tabela = ingerir_mod.formatar_tabela_plano(lote)
    assert "Exposição" in tabela
    assert "trecho" in tabela
    assert "arquivo" in tabela
    assert "para em: transcrição/índice" in tabela

    resumo = ingerir_mod.formatar_resumo_veredito_e_excecoes(lote, fase="plano")
    assert "Exposição e portão de parada:" in resumo
    assert "records.pdf: exposição trecho · para em: transcrição/índice" in resumo


def test_curar_reextrair_e_lote_mostram_exposicao_medida_e_portao(monkeypatch, capsys):
    monkeypatch.setattr(curar_mod, "resolver_obra_id", lambda obra, headers: "11111111-1111-1111-1111-111111111111")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "modo": "plano",
        "obra_id": "11111111-1111-1111-1111-111111111111",
        "titulo": "Kent",
        "objeto": "acervo/abc",
        "exposicao": "trecho",
        "medida_atual": "sem medida (régua 5)",
        "portao_parada": "medida (régua 6) -> índice (motor indexar antes de promover)",
        "metodo_alvo": "combinado",
        "espelho_atual": "deadbeef",
    }
    monkeypatch.setattr(curar_mod.requests, "post", lambda *a, **kw: resp)

    args = SimpleNamespace(reextrair="Kent", apply=False, metodo=None, corte="blocos-1")
    assert curar_mod.acao_reextrair(args, "dados", False, {}) == 0
    out = capsys.readouterr().out
    assert "exposição : trecho" in out
    assert "medida    : sem medida (régua 5)" in out
    assert "portão    : medida (régua 6) -> índice" in out

    monkeypatch.setattr(curar_mod, "_chamar", lambda *a, **kw: {
        "modo": "plano",
        "n": 1,
        "corte": "blocos-1",
        "totais": [],
        "itens": [{
            "posicao": 1,
            "obra_id": "11111111-1111-1111-1111-111111111111",
            "tipo": "pdf",
            "bytes": 1024,
            "metodo_atual": "perfil",
            "metodo_alvo": "combinado",
            "exposicao": "trecho",
            "portao_parada": "medida (régua 6) -> índice",
            "titulo": "Kent",
        }],
    })
    args_lote = SimpleNamespace(ordem=None, metodo=None, corte="blocos-1", apply=False, medida=False, replicas=None)
    assert curar_mod.acao_reextrair_lote(args_lote, "dados", False, {}) == 0
    out_lote = capsys.readouterr().out
    assert "trecho  [medida (régua 6) -> índice]" in out_lote


def test_curar_reclassificar_exposicao_valida_e_invalida(monkeypatch):
    capturado = {}
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"modo": "plano", "n": 1, "itens": []}

    def fake_patch(url, json=None, headers=None):
        capturado["url"] = url
        capturado["json"] = json
        return resp

    monkeypatch.setattr(curar_mod, "resolver_obra_id", lambda obra, headers: "11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(curar_mod.requests, "patch", fake_patch)

    args_base = dict(
        dominio=None, subdominio=None, especie=None, subtipo=None, anotacao=None,
        vinculacao=None, titulo=None, resumo=None, subtitulo=None, id_canonico=None,
        publicacao=None, emitido_por=None, trata_de=None, remover_trata_de=None,
        substituir_trata_de=None, obra="Kent", obras=None, de_dominio=None,
        de_subdominio=None, de_conceito=None, de_colecao=None, sem_dominio=False,
        expurgadas=False, apply=False, teto=200,
    )
    assert curar_mod.acao_reclassificar(SimpleNamespace(**args_base, exposicao="arquivo"), "dados", True, {}) == 0
    assert capturado["json"]["alteracao"] == {"exposicao": "arquivo"}

    with pytest.raises(SystemExit) as exc:
        curar_mod.acao_reclassificar(SimpleNamespace(**args_base, exposicao="invalida"), "dados", True, {})
    assert exc.value.code == 2
