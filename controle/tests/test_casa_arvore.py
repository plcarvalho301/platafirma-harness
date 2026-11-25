# componente: componente:verbo-acervo
# Contrato da recusa de `acervo ingerir casa` (#4425) e da leitura de `# regua:` por
# `acervo registrar` (#3153, spec_lint §3/§6).
import importlib.machinery
import importlib.util
import os
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")
BIN = os.path.join(REPO, "bin", "acervo")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


registrar = _carrega("acervo_registrar", "registrar")


def test_acervo_ingerir_casa_removido_sai_2():
    assert not os.path.exists(os.path.join(ACERVO, "casa-ingerir"))
    assert not os.path.exists(os.path.join(ACERVO, "casa-pr-conferir"))
    r = subprocess.run([BIN, "ingerir", "casa", "platafirma-casa"],
                       capture_output=True, text=True, check=False, timeout=10)
    assert r.returncode == 2
    assert "busca consultar" in r.stderr and "busca ler" in r.stderr


def test_acervo_curar_casa_alias_removido_sai_2():
    import sys
    r = subprocess.run([BIN, "curar", "casa", "alias", "persona", "produto", "Lygia Bem-te-vi"],
                       capture_output=True, text=True, check=False, timeout=10)
    assert r.returncode == 2
    assert "ontologia nomes abrir" in r.stderr

    r_sub = subprocess.run([sys.executable, os.path.join(ACERVO, "curar"), "alias",
                            "persona", "produto", "Lygia Bem-te-vi"],
                           capture_output=True, text=True, check=False, timeout=10)
    assert r_sub.returncode == 2
    assert "ontologia nomes abrir" in r_sub.stderr

    with open(os.path.join(ACERVO, "curar"), encoding="utf-8") as fh:
        assert "acervo.entidade_alias" not in fh.read()


# ------------------------------------------------------------------ registrar: # regua:

def test_regua_le_as_duas_formas():
    r = registrar._regua_por_ato(
        ["codigo repositorio", "repo lista-de-verificacao checklist-repo",
         "card lista-de-verificacao arq-0096"], "lint")
    assert r == {"codigo": ("repositorio", None),
                 "repo": ("lista-de-verificacao", "checklist-repo"),
                 "card": ("lista-de-verificacao", "arq-0096")}


@pytest.mark.parametrize("linha", ["repo", "repo lista-de-verificacao", "repo Lista chave", "a b c d"])
def test_regua_fora_da_forma_recusa(linha):
    with pytest.raises(SystemExit) as e:
        registrar._regua_por_ato([linha], "lint")
    assert e.value.code == 3


def test_cabecalho_de_lint_acumula_regua_por_ato(tmp_path):
    f = tmp_path / "lint"
    f.write_text("#!/usr/bin/env python3\n# lint - aponta\n# capacidade: x\n"
                 "# atos: codigo, repo\n# regua: codigo repositorio\n"
                 "# regua: repo lista-de-verificacao checklist-repo\n", encoding="utf-8")
    campos, _ = registrar._le_cabecalho(str(f))
    assert campos["regua"] == ["codigo repositorio", "repo lista-de-verificacao checklist-repo"]
