"""#2856 linha 156 (caso #3240): `acervo listar obra --qualidade` agrega, por classe (ok / suspeita /
nao-julgada), a qualidade dos espelhos servindo; com `--por-obra`, uma linha por obra.

A qualidade é o veredito da régua, gravado em `acervo.impressao.espelho -> veredito` (conhecimento,
`conversor/regua.py`). Sem banco: o módulo `bin/_acervo/listar` se carrega como fonte e `_psql_json` é
trocado por uma função que responde pela consulta que o ato faz (só leitura).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
LISTAR = RAIZ / "bin" / "_acervo" / "listar"

def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_listar_2856_156", str(LISTAR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

def _linha(n, titulo, qualidade, regua=2, tem_espelho=True):
    return {"id": f"{n:08x}-0000-4000-8000-000000000000", "titulo": titulo,
            "tem_espelho": tem_espelho, "qualidade": qualidade, "regua": regua}

LINHAS = [
    _linha(1, "Lei 14.133", "ok"),
    _linha(2, "Manual de Redes", "suspeita"),
    _linha(3, "Anuário", "suspeita"),
    _linha(4, "Livro EPUB", "nao-julgada"),
    _linha(5, "Sem espelho ainda", None, regua=None, tem_espelho=False),
]

@pytest.fixture
def listar(monkeypatch):
    mod = _modulo()
    consultas = []

    def falso(sql, alvo):
        consultas.append((alvo, sql))
        if alvo == "qualidade_espelho":
            return LINHAS
        raise AssertionError(f"consulta inesperada: {alvo}")

    monkeypatch.setattr(mod, "_psql_json", falso)
    return mod, consultas

def test_primeira_linha_traz_o_total_e_o_criterio_em_palavras(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, False)
    primeira = capsys.readouterr().out.splitlines()[0]
    assert primeira.startswith("4 espelhos servindo")
    for palavra in ("suspeita", "nao-julgada", "ok", "piso"):
        assert palavra in primeira

def test_agrega_por_classe_a_contagem_dos_espelhos_servindo(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, False)
    linhas = capsys.readouterr().out.splitlines()
    contagem = {l.split()[0]: int(l.split()[1]) for l in linhas
                if l.split() and l.split()[0] in ("ok", "suspeita", "nao-julgada")}
    assert contagem == {"ok": 1, "suspeita": 2, "nao-julgada": 1}

def test_sem_por_obra_nao_lista_obra(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, False)
    saida = capsys.readouterr().out
    assert "Lei 14.133" not in saida and "Manual de Redes" not in saida

def test_por_obra_traz_uma_linha_por_obra_com_a_classe(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(True, False)
    saida = capsys.readouterr().out
    por_titulo = {}
    for l in saida.splitlines():
        for t in ("Lei 14.133", "Manual de Redes", "Anuário", "Livro EPUB"):
            if l.rstrip().endswith(t):
                por_titulo[t] = l.split()[0]
    assert por_titulo == {"Lei 14.133": "ok", "Manual de Redes": "suspeita",
                          "Anuário": "suspeita", "Livro EPUB": "nao-julgada"}
    assert "Sem espelho ainda" not in saida

def test_a_margem_do_piso_nao_e_inventada_e_a_pendencia_vai_numa_linha(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, False)
    saida = capsys.readouterr().out
    pendencias = [l for l in saida.splitlines() if "margem do piso: definição de dados" in l]
    assert len(pendencias) == 1
    assert not any(ch.isdigit() for ch in pendencias[0].replace("#2856", ""))

def test_obras_servindo_sem_espelho_saem_contadas_a_parte(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, False)
    assert "sem espelho 1" in capsys.readouterr().out

def test_json_traz_total_classes_criterio_e_pendencia(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(True, True)
    doc = json.loads(capsys.readouterr().out)
    assert doc["total"] == 4
    assert doc["sem_espelho"] == 1
    assert doc["classes"] == {"ok": 1, "suspeita": 2, "nao-julgada": 1}
    assert "piso" in doc["criterio"]
    assert doc["pendencia"] == "margem do piso: definição de dados"
    assert {o["classe"] for o in doc["obras"]} == {"ok", "suspeita", "nao-julgada"}
    assert len(doc["obras"]) == 4

def test_json_sem_por_obra_nao_traz_obras(listar, capsys):
    mod, _ = listar
    mod.listar_obra_qualidade(False, True)
    assert "obras" not in json.loads(capsys.readouterr().out)

def test_a_consulta_e_so_leitura_no_catalogo(listar, capsys):
    mod, consultas = listar
    mod.listar_obra_qualidade(False, False)
    capsys.readouterr()
    sql = next(sql for alvo, sql in consultas if alvo == "qualidade_espelho").lower()
    assert "acervo.impressao" in sql and "servindo" in sql and "veredito" in sql
    for escrita in ("insert", "update", "delete", "drop", "alter"):
        assert escrita not in sql

def test_veredito_ausente_conta_como_nao_julgada(listar, monkeypatch, capsys):
    mod, _ = listar
    monkeypatch.setattr(mod, "_psql_json", lambda sql, alvo: [_linha(9, "Velho", None)])
    mod.listar_obra_qualidade(False, True)
    assert json.loads(capsys.readouterr().out)["classes"]["nao-julgada"] == 1

def test_cli_qualidade_chama_o_ato(listar, capsys):
    mod, _ = listar
    with pytest.raises(SystemExit) as e:
        mod.main(["obra", "--qualidade", "--por-obra"])
    assert e.value.code == 0
    saida = capsys.readouterr().out
    assert saida.startswith("4 espelhos servindo") and "Lei 14.133" in saida

@pytest.mark.parametrize("extra", [["--situacao"], ["--eixo", "titulo"], ["--sobre", "Lei"]])
def test_cli_qualidade_recusa_o_que_nao_filtra(listar, extra, capsys):
    mod, _ = listar
    with pytest.raises(SystemExit) as e:
        mod.main(["obra", "--qualidade", *extra])
    assert e.value.code == 2

def test_cli_por_obra_sem_qualidade_recusa(listar, capsys):
    mod, _ = listar
    with pytest.raises(SystemExit) as e:
        mod.main(["obra", "--por-obra"])
    assert e.value.code == 2
