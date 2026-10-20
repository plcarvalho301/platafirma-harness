"""release conferir verbo: a chave `mecanismo:` e a `casca` em `face:` (card #3899; arq:0124 §3, emenda de
18/10/2026). A casca e componente, nao face: `mecanismo:` aceita so os pares da ADR, e `casca` em `face:` e
divergencia. Os verbos reais (preferencia, tarefas, release) saem conformes."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CONFERIR_PATH = RAIZ / "bin" / "_release" / "conferir" / "conferir.py"
RESULTADO_PATH = RAIZ / "bin" / "_release" / "conferir" / "resultado.py"


def _carregar(caminho, nome):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


resultado = _carregar(RESULTADO_PATH, "resultado_mecanismo_teste")
conferir = _carregar(CONFERIR_PATH, "conferir_mecanismo_teste")


def _isolar(monkeypatch, bin_dir):
    monkeypatch.setattr(conferir, "BIN", str(bin_dir))
    monkeypatch.setattr(conferir, "_capacidade_veredito", lambda cap: resultado.conforme())
    monkeypatch.setattr(conferir, "_desde_familia", lambda familia: None)
    monkeypatch.setattr(conferir, "origem", lambda nome, caminho: ("symlink-release", str(caminho)))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")


def _verbo(tmp_path, monkeypatch, nome, linhas, atos="ler, escrever, telas, espera-dono"):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / nome).write_text(
        "#!/usr/bin/env bash\n"
        f"# {nome} - verbo de teste do mecanismo\n"
        "# capacidade: verificacao-de-teste\n"
        "# dono: claudinho-TI\n"
        f"# atos: {atos}\n"
        + "".join(f"# {linha}\n" for linha in linhas)
        + "echo ok\n", encoding="utf-8")
    _isolar(monkeypatch, bin_dir)


def _conferir(nome, capsys):
    exit_code = conferir.conferir_verbo(nome, como_json=True)
    dado = json.loads(capsys.readouterr().out)
    item = next(i for i in dado["itens"] if i["nome"] == nome)
    return exit_code, item


@pytest.mark.parametrize("nome,linhas", [
    ("preferencia", ["mecanismo: ler=casca", "mecanismo: escrever=casca"]),
    ("release", ["mecanismo: telas=casca"]),
    ("tarefas", ["mecanismo: espera-dono=casca"]),
])
def test_os_pares_da_arq_0124_sao_aceitos_em_mecanismo(tmp_path, monkeypatch, capsys, nome, linhas):
    _verbo(tmp_path, monkeypatch, nome, linhas)
    exit_code, item = _conferir(nome, capsys)
    assert exit_code == 0 and item["estado"] == "conforme", item


def test_casca_em_face_e_divergente(tmp_path, monkeypatch, capsys):
    _verbo(tmp_path, monkeypatch, "preferencia", ["face: ler=casca", "rotulo: ler=Ler o tema", "volta: ler=nao"])
    exit_code, item = _conferir("preferencia", capsys)
    assert exit_code == 1 and item["estado"] == "divergente"
    assert "casca" in item["motivo"] and "face: ler=casca" in item["motivo"]


def test_casca_em_face_e_divergente_em_qualquer_caixa(tmp_path, monkeypatch, capsys):
    _verbo(tmp_path, monkeypatch, "preferencia", ["face: ler=Casca"])
    assert _conferir("preferencia", capsys)[0] == 1


def test_mecanismo_de_par_fora_da_lista_e_divergente(tmp_path, monkeypatch, capsys):
    # o ato certo, no verbo errado
    _verbo(tmp_path, monkeypatch, "meuverbo", ["mecanismo: telas=casca"])
    exit_code, item = _conferir("meuverbo", capsys)
    assert exit_code == 1 and item["estado"] == "divergente" and "fora dos pares" in item["motivo"]


def test_mecanismo_de_ato_fora_da_lista_do_verbo_e_divergente(tmp_path, monkeypatch, capsys):
    _verbo(tmp_path, monkeypatch, "preferencia", ["mecanismo: apagar=casca"])
    assert _conferir("preferencia", capsys)[0] == 1


def test_mecanismo_com_outro_componente_e_divergente(tmp_path, monkeypatch, capsys):
    _verbo(tmp_path, monkeypatch, "preferencia", ["mecanismo: ler=outra"])
    assert _conferir("preferencia", capsys)[0] == 1


def test_os_tres_verbos_reais_saem_sem_divergencia_de_mecanismo(monkeypatch, capsys):
    _isolar(monkeypatch, RAIZ / "bin")
    for nome in ("preferencia", "release", "tarefas"):
        assert conferir._mecanismo_fora_da_regra(nome, str(RAIZ / "bin" / nome)) == [], nome
        exit_code, item = _conferir(nome, capsys)
        assert exit_code == 0 and item["estado"] == "conforme", (nome, item)
