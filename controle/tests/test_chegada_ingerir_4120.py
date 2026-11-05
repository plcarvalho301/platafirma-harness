"""O `ingerir` registra a chegada e lista o que ficou de fora (card #4120, itens 3 a 5; U2 e U10).

Antes, `bin/_ingerir/carga.py` (a triagem) só era chamado pelos testes e `acervo.chegada` nunca era gravada. Aqui o
`ingerir` real é carregado como módulo e o servidor é trocado por uma função: o que se prova é o que ele manda a
`POST /acervo/chegada` (cada arquivo com o estado da triagem, a pasta de origem como procedência e a classificação
da planilha presa ao sha256) e a lista das exceções, que não some em silêncio nem suja o `--json`.
"""
from __future__ import annotations

import hashlib
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

from bin._ingerir import carga  # noqa: E402

_loader = SourceFileLoader("ingerir_chegada_mod", str(HARNESS_DIR / "bin" / "ingerir"))
_spec = importlib.util.spec_from_loader("ingerir_chegada_mod", _loader)
ingerir = importlib.util.module_from_spec(_spec)
_loader.exec_module(ingerir)


class _Erro(Exception):
    pass


class RequestsFalso:
    """O `requests` do ingerir: guarda o que recebeu e devolve a resposta combinada."""

    def __init__(self, status=201, corpo=None, falha=None):
        self.chamadas, self._status, self._corpo, self._falha = [], status, corpo or {}, falha
        self.exceptions = SimpleNamespace(RequestException=_Erro)

    def post(self, url, json=None, headers=None, timeout=None):
        self.chamadas.append((url, json, headers))
        if self._falha:
            raise self._falha
        return SimpleNamespace(status_code=self._status, text="corpo", json=lambda: self._corpo)


@pytest.fixture
def pasta(tmp_path):
    raiz = tmp_path / "entrada"
    (raiz / "sub").mkdir(parents=True)
    (raiz / "a.pdf").write_bytes(b"%PDF conteudo a")
    (raiz / "sub" / "b.epub").write_bytes(b"conteudo b")
    (raiz / "vazio.pdf").write_bytes(b"")
    (raiz / "dados.json").write_text("{}")
    (raiz / "planilha.csv").write_text("arquivo,titulo\na.pdf,A\n")
    (raiz / "fila.jsonl").write_text("{}\n")
    (raiz / ".oculto").write_text("x")
    return raiz


def _sha(texto: bytes) -> str:
    return hashlib.sha256(texto).hexdigest()


def test_a_triagem_separa_obra_de_excecao_e_nunca_deixa_item_sumir(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    assert sorted(o["rel"] for o in obras) == ["a.pdf", "sub/b.epub"]
    estados = {e["rel"]: e["estado"] for e in excecoes}
    assert estados == {"vazio.pdf": "vazio", "dados.json": "json_comum", "planilha.csv": "auxiliar",
                       "fila.jsonl": "auxiliar"}  # .csv e .jsonl saem na lista, não são descartados


def test_os_itens_da_chegada_levam_a_procedencia_e_a_classificacao_presa_ao_arquivo(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    itens = carga.itens_da_chegada(obras, excecoes, {"a.pdf": {"dominio": "dados"}})
    por_nome = {i["nome"]: i for i in itens}
    assert por_nome["b.epub"]["pasta_origem"] == "sub" and por_nome["a.pdf"]["pasta_origem"] == ""
    assert por_nome["a.pdf"]["classificacao"] == {"dominio": "dados"}
    assert por_nome["a.pdf"]["sha256"] == _sha(b"%PDF conteudo a")
    assert "classificacao" not in por_nome["b.epub"]  # sem planilha para ele
    assert por_nome["vazio.pdf"]["estado"] == "vazio" and por_nome["vazio.pdf"]["tamanho"] == 0
    assert len(itens) == 6


def test_a_classificacao_so_vai_com_o_item_que_chegou_como_obra(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    itens = carga.itens_da_chegada(obras, excecoes, {"planilha.csv": {"dominio": "x"}, "vazio.pdf": {"dominio": "y"}})
    assert not any("classificacao" in i for i in itens if i["estado"] != "chegado")


def test_as_excecoes_saem_com_estado_e_causa():
    linhas = carga.linhas_das_excecoes([
        {"rel": "z.csv", "nome": "z.csv", "estado": "auxiliar", "motivo": "arquivo auxiliar ou planilha"},
        {"rel": "a/vazio.pdf", "nome": "vazio.pdf", "estado": "vazio", "motivo": "arquivo vazio (0 bytes); não é obra servível"},
    ])
    assert linhas[0] == "Fora da carga (não viraram obra):"
    assert "  [vazio] a/vazio.pdf: arquivo vazio (0 bytes); não é obra servível" in linhas
    assert "  [auxiliar] z.csv: arquivo auxiliar ou planilha" in linhas
    assert carga.linhas_das_excecoes([]) == []


def test_com_apply_a_chegada_vai_ao_servidor_com_o_lote_e_cada_estado(pasta, monkeypatch):
    falso = RequestsFalso(corpo={"registrados": 6, "por_estado": {}, "recusados": []})
    monkeypatch.setattr(ingerir, "requests", falso)
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {"a.pdf": {"dominio": "dados"}},
                                                {"authorization": "Bearer t"}, registrar=True)
    (url, corpo, headers), = falso.chamadas
    assert url.endswith("/acervo/chegada") and headers == {"authorization": "Bearer t"}
    assert corpo["lote_id"] == "L1" and len(corpo["itens"]) == 6
    assert {i["estado"] for i in corpo["itens"]} == {"chegado", "vazio", "json_comum", "auxiliar"}
    assert linhas[0] == "Fora da carga (não viraram obra):" and len(linhas) == 5


def test_sem_apply_o_plano_lista_as_excecoes_e_nao_grava_nada(pasta, monkeypatch):
    falso = RequestsFalso()
    monkeypatch.setattr(ingerir, "requests", falso)
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=False)
    assert falso.chamadas == [] and len(linhas) == 5


def test_chegada_que_falha_vira_aviso_e_o_lote_segue(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(falha=_Erro("caiu")))
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert len(linhas) == 5
    assert "a chegada não registrou (_Erro); o lote segue" in capsys.readouterr().err


def test_chegada_recusada_pelo_servidor_vira_aviso(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(status=500))
    ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert "a chegada não registrou (500)" in capsys.readouterr().err


def test_item_que_o_servidor_recusa_aparece_no_aviso(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(corpo={"recusados": [{"sha256": "abc", "motivo": "tamanho"}]}))
    ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert "chegada recusou abc: tamanho" in capsys.readouterr().err


def test_no_json_a_lista_vai_para_o_stderr_e_a_saida_de_dados_fica_pura(capsys):
    linhas = ["Fora da carga (não viraram obra):", "  [vazio] x.pdf: vazio"]
    ingerir.mostrar_excecoes_da_carga(linhas, como_json=True)
    saida = capsys.readouterr()
    assert saida.out == "" and "[vazio] x.pdf" in saida.err
    ingerir.mostrar_excecoes_da_carga(linhas, como_json=False)
    assert "[vazio] x.pdf" in capsys.readouterr().out
    ingerir.mostrar_excecoes_da_carga([], como_json=False)
    assert capsys.readouterr().out == ""


def test_pasta_que_nao_se_le_nao_derruba_o_lote(monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso())
    monkeypatch.setattr(ingerir, "escanear_pasta_triagem", lambda p: (_ for _ in ()).throw(OSError("sem permissão")))
    assert ingerir.registrar_chegada_da_carga("/x", "L1", {}, {}, registrar=True) == []
    assert "a triagem da chegada falhou" in capsys.readouterr().err
