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


def test_duas_chamadas_seguidas_nao_deixam_bytecode_na_bancada(monkeypatch, tmp_path, bancada):
    """DT 456: o Python da peça gravava __pycache__ na bancada e a chamada seguinte saía 4
    (arquivo fora do git). A peça roda sem gravar bytecode, e a segunda chamada sai como a primeira."""
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    mod = _modulo()
    _prepara(mod, monkeypatch, tmp_path, bancada)
    assert mod.main(["rodar", "p"]) == 7
    assert mod.main(["rodar", "p"]) == 7
    assert not list(bancada.rglob("__pycache__"))


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


def test_peca_casa_nao_depende_do_caminho_do_conversor():
    """#4137: cada caminho da peça entra no gate de origin/main. O conversor, que a peça casa não
    importa, no pythonpath fazia a chamada sair 4 sempre que outra cadeira commitava nele."""
    reg = json.loads((RAIZ / "registro" / "pecas.json").read_text(encoding="utf-8"))
    casa = reg["casa"]
    assert casa["pythonpath"] == ["outros_repos/conhecimento/rag"]
    assert not any("conversor" in c for c in [casa["cwd"], *casa["pythonpath"]])


def _peca_olaria(mod, monkeypatch, tmp_path, wt, *, com_chave: bool):
    """A peça `p` com ambiente olaria: um pacote que imprime o que recebe, e o cofre da instância num diretório temporário."""
    pkg = wt / "rag" / "pkg2"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text("import os\nprint('url=' + os.environ.get('OLARIA_URL', ''))\n"
                                     "print('chave=' + os.environ.get('OLARIA_CHAVE', ''))\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "peca olaria")
    _git(wt, "push", "origin", "HEAD:main")
    reg = tmp_path / "pecas.json"
    reg.write_text(json.dumps({"p": {"dono": "ti", "origem": "espelho", "repo": "r", "cwd": "rag", "modulo": "pkg2",
                                     "pythonpath": ["rag"], "python": "rag", "ambiente": "olaria", "teto_s": 30}}))
    monkeypatch.setattr(mod, "REG", reg)
    ex = mod._exportar()
    monkeypatch.setattr(ex, "bancada_do_repo", lambda chave="": wt)
    monkeypatch.setattr(ex, "python_do_rag", lambda: sys.executable)
    instancia = tmp_path / "instancia"
    if com_chave:
        (instancia / "segredos" / "olaria").mkdir(parents=True)
        (instancia / "segredos" / "olaria" / "OLARIA_CHAVE").write_text("chave-do-cofre\n")
    monkeypatch.setattr(ex.raizes, "instancia", lambda: instancia)
    monkeypatch.setattr(mod, "_exportar", lambda: ex)


def test_ambiente_olaria_poe_a_url_e_a_chave_do_cofre_na_peca_e_nao_imprime_a_chave(monkeypatch, tmp_path, bancada, capfd):
    mod = _modulo()
    _peca_olaria(mod, monkeypatch, tmp_path, bancada, com_chave=True)
    assert mod.main(["rodar", "p"]) == 0
    out, err = capfd.readouterr()
    assert "url=http://127.0.0.1:8103" in out and "chave=chave-do-cofre" in out      # a peça recebe os dois
    assert "chave-do-cofre" not in err                                              # e o verbo não imprime a chave
    assert "(OLARIA_CHAVE, OLARIA_URL)" in err                                      # só os nomes saem no stderr


def test_ambiente_olaria_sem_a_chave_no_cofre_sai_3_dizendo_onde_ela_devia_estar(monkeypatch, tmp_path, bancada, capfd):
    mod = _modulo()
    _peca_olaria(mod, monkeypatch, tmp_path, bancada, com_chave=False)
    with pytest.raises(SystemExit) as e:
        mod.main(["rodar", "p"])
    assert e.value.code == 3
    assert "segredos/olaria/OLARIA_CHAVE" in capfd.readouterr().err


def test_registro_do_harness_declara_a_peca_olaria():
    reg = json.loads((RAIZ / "registro" / "pecas.json").read_text(encoding="utf-8"))
    olaria = reg["olaria"]
    assert olaria["origem"] == "espelho" and olaria["repo"] == "platafirma-casa-espelho"
    assert olaria["cwd"] == "outros_repos/harness/bin" and olaria["pythonpath"] == ["outros_repos/harness/bin"]
    assert olaria["modulo"] == "_olaria" and olaria["python"] == "rag" and olaria["ambiente"] == "olaria"
    assert olaria["teto_s"] == 120
