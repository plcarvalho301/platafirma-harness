"""`motor raciocinador raciocinar` (card #4077): o HermiT sobre um modelo formal com o MIREOT servido e os
casos somados, pelo Python do rag. Chamada temporária, por ordem do dono de 01/11/2026.

O despacho e a régua de saída rodam sempre. O HermiT de verdade roda só onde o ambiente o tem (rdflib,
owlready2 e Java); sem ele, os dois casos reais se pulam com o motivo, e a saída 5 é provada à parte."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "motor"
AJUDANTE = RAIZ / "bin" / "_motor" / "raciocinador.py"

PREFIXOS = ("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            "@prefix ex: <https://exemplo.org/> .\n")
MODELO = PREFIXOS + ("<https://exemplo.org/m> a owl:Ontology .\n"
                     "ex:A a owl:Class . ex:B a owl:Class . ex:A owl:disjointWith ex:B .\n")
CASO = PREFIXOS + "ex:C a owl:Class ; rdfs:subClassOf ex:A, ex:B .\n"


def _modulo():
    spec = importlib.util.spec_from_file_location("motor_raciocinador_teste", AJUDANTE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    bancada, instancia = tmp_path / "bancada", tmp_path / "instancia"
    (bancada / "rascunho").mkdir(parents=True)
    (instancia / "var" / "tmp").mkdir(parents=True)
    modelo = bancada / "rascunho" / "plataforma.ttl"
    modelo.write_text(MODELO, encoding="utf-8")
    caso = bancada / "rascunho" / "caso.ttl"
    caso.write_text(CASO, encoding="utf-8")
    mireot = tmp_path / "mireot.ttl"
    mireot.write_text(PREFIXOS, encoding="utf-8")
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(bancada))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(instancia))
    monkeypatch.setenv("PF_MIREOT_TTL", str(mireot))
    return {"modelo": modelo, "caso": caso, "mireot": mireot, "tmp": tmp_path}


@pytest.mark.parametrize("argv", [[], ["outro"], ["raciocinar"], ["raciocinar", "--modelo"],
                                  ["raciocinar", "--modelo", "a", "--modelo", "b"], ["raciocinar", "--outra", "a"]])
def test_uso_errado_sai_2(mundo, capsys, argv):
    assert _modulo().main(argv) == 2
    assert capsys.readouterr().err.startswith("uso: motor raciocinador")


def test_arquivo_fora_da_bancada_e_da_instancia_recusa(mundo, capsys):
    fora = mundo["tmp"] / "fora.ttl"
    fora.write_text(MODELO, encoding="utf-8")
    assert _modulo().main(["raciocinar", "--modelo", str(fora)]) == 2
    assert "fora da bancada" in capsys.readouterr().err


def test_modelo_que_nao_existe_sai_2(mundo, capsys):
    assert _modulo().main(["raciocinar", "--modelo", str(mundo["modelo"].with_name("nao.ttl"))]) == 2
    assert "não existe" in capsys.readouterr().err


def test_sem_mireot_sai_5(mundo, monkeypatch, capsys):
    monkeypatch.setenv("PF_MIREOT_TTL", str(mundo["tmp"] / "sem.ttl"))
    assert _modulo().main(["raciocinar", "--modelo", str(mundo["modelo"])]) == 5
    assert "MIREOT servido fora da máquina" in capsys.readouterr().err


@pytest.mark.parametrize("estado,saida", [(True, 0), (False, 1), (None, 5)])
def test_a_saida_segue_o_veredito(mundo, monkeypatch, estado, saida):
    mod = _modulo()
    vistos = []

    def falso(modelo, somados, mireot):
        vistos.append((modelo, somados, mireot))
        return estado, "dublê", ()

    monkeypatch.setattr(mod, "raciocinar", falso)
    assert mod.main(["raciocinar", "--modelo", str(mundo["modelo"]), "--somar", str(mundo["caso"])]) == saida
    assert vistos == [(mundo["modelo"].resolve(), [mundo["caso"].resolve()], mundo["mireot"])]


def test_sem_java_nao_roda(mundo, monkeypatch):
    monkeypatch.setenv("JAVA_EXE", "java-que-nao-existe-4077")
    estado, motivo, _ = _modulo().raciocinar(mundo["modelo"], [], mundo["mireot"])
    assert estado is None and "Java" in motivo


def _hermit_disponivel() -> str:
    if shutil.which("java") is None:
        return "Java fora do PATH"
    for nome in ("rdflib", "owlready2"):
        if importlib.util.find_spec(nome) is None:
            return f"{nome} fora do Python do teste"
    return ""


@pytest.mark.skipif(bool(_hermit_disponivel()), reason=_hermit_disponivel() or "-")
def test_hermit_de_verdade_fecha_e_reprova_o_caso(mundo):
    mod = _modulo()
    fecha = mod.raciocinar(mundo["modelo"], [], mundo["mireot"])
    assert fecha[0] is True, fecha[1]
    reprova = mod.raciocinar(mundo["modelo"], [mundo["caso"]], mundo["mireot"])
    assert reprova[0] is False and "C" in reprova[2], reprova[1]


def test_pela_porta_a_instancia_existe_e_o_cabecalho_declara_o_ato(mundo):
    env = {**os.environ, "RAG_PYTHON": sys.executable}
    r = subprocess.run([sys.executable, str(BIN), "raciocinador", "outro"], capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "uso: motor raciocinador" in r.stderr
    r = subprocess.run([sys.executable, str(BIN), "raciocinador", "raciocinar", "--modelo", str(mundo["modelo"])],
                       capture_output=True, text=True, env={**env, "PF_MIREOT_TTL": str(mundo["tmp"] / "sem.ttl")})
    assert r.returncode == 5 and "MIREOT" in r.stderr
    cabecalho = BIN.read_text(encoding="utf-8")
    assert "raciocinar (leitura, medida)" in cabecalho
    assert "# le: raciocinar=" in cabecalho and "# escreve: raciocinar=" in cabecalho


def test_o_ajudante_nao_fala_com_banco():
    texto = AJUDANTE.read_text(encoding="utf-8")
    assert "psql" not in texto and "docker" not in texto
