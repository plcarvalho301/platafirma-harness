"""`infra pecas | rodar` (bin/_infra/rodar-peca.py): só roda peça declarada, e da origem espelho só
com os caminhos dela iguais a origin/main. Sem banco: o python do rag é o do teste e o ambiente
do cofre é trocado por dublê; o repositório é um git de verdade num diretório temporário.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
AJUDANTE = RAIZ / "bin" / "_infra" / "rodar-peca.py"


def _modulo():
    loader = importlib.machinery.SourceFileLoader("infra_rodar_peca_teste", str(AJUDANTE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


@pytest.fixture()
def bancada(tmp_path):
    """Origin bare com a peça `pkg` em rag/, e um clone igual a origin/main."""
    origem = tmp_path / "origem.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origem)], check=True, capture_output=True)
    wt = tmp_path / "wt"
    subprocess.run(["git", "clone", str(origem), str(wt)], check=True, capture_output=True)
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    pkg = wt / "rag" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(
        "import os, sys\nprint('args=' + ' '.join(sys.argv[1:]))\n"
        "print('banco=' + os.environ.get('POSTGRES_PASSWORD', ''))\nsys.exit(7)\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "peca")
    _git(wt, "push", "origin", "HEAD:main")
    return wt


def _prepara(mod, monkeypatch, tmp_path, wt):
    reg = tmp_path / "pecas.json"
    reg.write_text(json.dumps({"_sobre": "x", "p": {
        "dono": "dados", "origem": "espelho", "repo": "r", "cwd": "rag", "modulo": "pkg",
        "pythonpath": ["rag"], "python": "rag", "ambiente": "banco-rag", "teto_s": 30}}))
    monkeypatch.setattr(mod, "REG", reg)
    ex = mod._exportar()
    monkeypatch.setattr(ex, "bancada_do_repo", lambda chave="": wt)
    monkeypatch.setattr(ex, "python_do_rag", lambda: sys.executable)
    monkeypatch.setattr(ex, "ambiente_da_ingestao", lambda: {"POSTGRES_PASSWORD": "segredo"})
    monkeypatch.setattr(mod, "_exportar", lambda: ex)


def test_peca_nao_declarada_sai_4(monkeypatch, tmp_path, bancada):
    mod = _modulo()
    _prepara(mod, monkeypatch, tmp_path, bancada)
    with pytest.raises(SystemExit) as e:
        mod.main(["rodar", "outra"])
    assert e.value.code == 4


def test_igual_a_origin_main_roda_e_devolve_o_exit_da_peca(monkeypatch, tmp_path, bancada, capfd):
    mod = _modulo()
    _prepara(mod, monkeypatch, tmp_path, bancada)
    assert mod.main(["rodar", "p", "--", "carregar", "--seco"]) == 7
    out, err = capfd.readouterr()
    assert "args=carregar --seco" in out
    assert "banco=segredo" in out           # a peça recebe a credencial do cofre
    assert "segredo" not in err             # e o verbo não a imprime
    assert "(origin/main)" in err and "peça saiu 7" in err


def test_caminho_alterado_ou_solto_sai_4(monkeypatch, tmp_path, bancada):
    mod = _modulo()
    _prepara(mod, monkeypatch, tmp_path, bancada)
    (bancada / "rag" / "pkg" / "__main__.py").write_text("print('nao commitado')\n")
    with pytest.raises(SystemExit) as e:
        mod.main(["rodar", "p"])
    assert e.value.code == 4
    _git(bancada, "checkout", "--", ".")
    (bancada / "rag" / "pkg" / "novo.py").write_text("")
    with pytest.raises(SystemExit) as e:
        mod.main(["rodar", "p"])
    assert e.value.code == 4


def test_mudanca_fora_dos_caminhos_da_peca_nao_trava(monkeypatch, tmp_path, bancada):
    mod = _modulo()
    _prepara(mod, monkeypatch, tmp_path, bancada)
    (bancada / "rascunho.md").write_text("em curso")
    assert mod.main(["rodar", "p"]) == 7


def test_uso_errado_sai_2():
    mod = _modulo()
    assert mod.main([]) == 2
    assert mod.main(["rodar"]) == 2
    assert mod.main(["rodar", "p", "carregar"]) == 2   # args da peça só depois de --
    assert mod.main(["pecas", "--x"]) == 2


def test_registro_do_harness_declara_a_peca_casa():
    reg = json.loads((RAIZ / "registro" / "pecas.json").read_text(encoding="utf-8"))
    casa = reg["casa"]
    assert casa["origem"] == "espelho" and casa["repo"] == "platafirma-casa-espelho"
    assert casa["modulo"] == "motor_acervo.casa" and casa["ambiente"] == "banco-rag"
