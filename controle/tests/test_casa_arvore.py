# Contrato de `acervo ingerir casa platafirma-casa --arvore <dir>` (#3152 passo 6, spec_teste §4)
# e da leitura de `# regua:` por `acervo registrar` (#3153, spec_lint §3/§6). Sem banco e sem
# rede: o POST do plano é trocado por um falso que devolve o lote como o servidor devolveria.
import importlib.machinery
import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ingerir = _carrega("casa_ingerir_arvore", "casa-ingerir")
registrar = _carrega("acervo_registrar", "registrar")

DOCS = {
    "spec/acervo.md": "# Acervo\n\nEspécie: spec\nSobre: verbo acervo\n",
    "spec/acervo.1.mmd": "graph TD; a-->b\n",
    "padrao/sem-doc.2.mmd": "graph TD; x-->y\n",
    "README.md": "# leia-me\n",
    ".git/HEAD": "ref: refs/heads/main\n",
}


@pytest.fixture
def raiz(tmp_path, monkeypatch):
    inst = tmp_path / "instancia"
    arv = inst / "var" / "pre-push" / "arvores" / "abc"
    for p, txt in DOCS.items():
        f = arv / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(txt, encoding="utf-8")
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))
    monkeypatch.setenv("PF_RELEASE_RAIZ", str(tmp_path / "release"))
    return arv


def _roda(argv):
    with pytest.raises(SystemExit) as e:
        ingerir.main(argv)
    return e.value.code


def test_arvore_com_apply_recusa_uso(raiz):
    assert _roda(["platafirma-casa", "--arvore", str(raiz), "--apply"]) == 2


def test_arvore_com_rev_recusa_uso(raiz):
    assert _roda(["platafirma-casa@abc123", "--arvore", str(raiz)]) == 2


def test_arvore_fora_da_raiz_sai_4(tmp_path, raiz):
    fora = tmp_path / "fora"
    fora.mkdir()
    (fora / "x.md").write_text("# x\n", encoding="utf-8")
    assert _roda(["platafirma-casa", "--arvore", str(fora)]) == 4


def test_arvore_manda_so_md_sem_git_nem_readme_e_nunca_retira(raiz, monkeypatch, capsys):
    enviado = {}

    def falso(payload):
        enviado.update(payload)
        return {"id": "l1", "autor": payload["autor"], "motor": "rag", "ate": "vetor",
                "itens": [{"arquivo": "platafirma-casa@spec/acervo.md", "veredito": "criar",
                           "portoes": []}]}

    monkeypatch.setattr(ingerir, "postar_lote", falso)
    # diagrama sem documento é recusa local: exit 3 mesmo com o servidor limpo
    assert _roda(["platafirma-casa", "--arvore", str(raiz)]) == 3
    assert [i["path"] for i in enviado["itens"]] == ["spec/acervo.md"]
    assert enviado["fonte"]["arvore_completa"] is False
    assert len(enviado["fonte"]["sha"]) == 40
    assert "padrao/sem-doc.2.mmd" in capsys.readouterr().out


def test_arvore_limpa_sai_0_e_digest_estavel(raiz, monkeypatch):
    (raiz / "padrao" / "sem-doc.2.mmd").unlink()
    shas = []

    def falso(payload):
        shas.append(payload["fonte"]["sha"])
        return {"id": "l2", "itens": [{"arquivo": "x", "veredito": "criar", "portoes": []}]}

    monkeypatch.setattr(ingerir, "postar_lote", falso)
    assert _roda(["platafirma-casa", "--arvore", str(raiz)]) == 0
    assert _roda(["platafirma-casa", "--arvore", str(raiz)]) == 0
    assert shas[0] == shas[1]


def test_arvore_recusa_do_servidor_sai_3(raiz, monkeypatch):
    (raiz / "padrao" / "sem-doc.2.mmd").unlink()
    monkeypatch.setattr(ingerir, "postar_lote", lambda p: {"id": "l3", "itens": [
        {"arquivo": "x", "veredito": "reprovado",
         "portoes": [{"portao": "especie", "resultado": "reprovado"}]}]})
    assert _roda(["platafirma-casa", "--arvore", str(raiz)]) == 3


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
