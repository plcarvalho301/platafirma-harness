"""`acervo medir` (débito 330 do balde #2856): um verbo da porta roda `python -m medida` na bancada de
`platafirma-conhecimento` e devolve a primeira linha do relatório.

Roda de verdade, sem dublê de subprocesso: o python do rag é o do próprio teste (RAG_PYTHON) e a bancada é
uma árvore de arquivos com um `medida` de brinquedo, que escreve o que o instrumento escreve (as linhas
`medida: …`, o relatório e a saída 0, 1 ou 5). O que o brinquedo não prova é o instrumento em si, que tem a
suíte dele em `platafirma-conhecimento` (rag/tests/test_medida_*.py)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "acervo"
MEDIR = RAIZ / "bin" / "_acervo" / "medir"
REPO = "platafirma-conhecimento"

BRINQUEDO = '''\
import sys
from pathlib import Path

relatorio = Path(__file__).resolve().parent / "relatorio-de-brinquedo.md"
relatorio.write_text("# Relatório da medida — 2026-10-19T00:00:00Z\\n\\n- fichas cobertas: 3 de 3\\n", encoding="utf-8")
print("medida: modelo abc · 2 entidades")
print(f"medida: relatório gravado em {relatorio}")
print("medida: o banco não respondeu", file=sys.stderr)
sys.exit(%d)
'''


def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_medir_teste", str(MEDIR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _bancada(raiz: Path, chave: str, saida: int | None = 0) -> Path:
    wt = raiz / "wt" / REPO / "dados" / chave
    (wt / ".git").mkdir(parents=True)
    if saida is not None:
        medida = wt / "ontologia" / "medida"
        medida.mkdir(parents=True)
        (medida / "__init__.py").write_text("", encoding="utf-8")
        (medida / "__main__.py").write_text(BRINQUEDO % saida, encoding="utf-8")
    return wt


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    monkeypatch.setenv("PF_CADEIRA", "dados")
    monkeypatch.setenv("RAG_PYTHON", sys.executable)
    monkeypatch.delenv("PF_SESSAO", raising=False)
    return tmp_path


def test_roda_o_instrumento_da_bancada_e_diz_a_primeira_linha_do_relatorio(mundo, capsys):
    wt = _bancada(mundo, "3759-medida")
    assert _modulo().main([]) == 0
    saida = capsys.readouterr().out.splitlines()
    assert saida[0] == "medida: modelo abc · 2 entidades"
    assert saida[-2] == f"bancada: {wt}"
    assert saida[-1] == "relatório: # Relatório da medida — 2026-10-19T00:00:00Z"


@pytest.mark.parametrize("codigo", [1, 5])
def test_a_saida_e_a_do_instrumento_e_o_que_ele_disse_vai_a_tela(mundo, capsys, codigo):
    _bancada(mundo, "3759-medida", saida=codigo)
    assert _modulo().main([]) == codigo
    visto = capsys.readouterr()
    assert "medida: o banco não respondeu" in visto.err and visto.out.startswith("medida: modelo abc")


def test_sem_o_instrumento_na_bancada_recusa_com_o_nome_do_ato(mundo, capsys):
    _bancada(mundo, "3194-a", saida=None)
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 3
    erro = capsys.readouterr().err
    assert erro.startswith("acervo medir:") and "medida" in erro


def test_duas_bancadas_sem_chave_recusa_e_chave_escolhe(mundo, capsys):
    _bancada(mundo, "3194-a")
    escolhida = _bancada(mundo, "3759-medida")
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 2 and "--bancada" in capsys.readouterr().err
    assert _modulo().main(["--bancada", "3759-medida"]) == 0
    assert f"bancada: {escolhida}" in capsys.readouterr().out


def test_argumento_desconhecido_e_uso(mundo, capsys):
    assert _modulo().main(["--outra"]) == 2
    assert capsys.readouterr().err.startswith("uso: acervo medir")


@pytest.mark.parametrize("argv", [["--planilha"], ["--planilha", ""], ["--planilha", "a", "--planilha", "b"]])
def test_planilha_sem_valor_ou_repetida_e_uso(mundo, capsys, argv):
    assert _modulo().main(argv) == 2
    assert "--planilha" in capsys.readouterr().err


def test_planilha_chega_ao_instrumento_com_o_caminho_absoluto(mundo, capsys, tmp_path):
    """#3991: `--planilha <tsv>` vai a `python -m medida --planilha`, que só confere as shapes contra a
    planilha v3 (R16); antes o ato o recusava como uso, e o relatório saía à mão."""
    wt = _bancada(mundo, "3991")
    (wt / "ontologia" / "medida" / "__main__.py").write_text(
        "import sys\nprint('medida: argv ' + ' '.join(sys.argv[1:]))\n", encoding="utf-8")
    tsv = tmp_path / "entidades.tsv"
    tsv.write_text("rotulo\tslug\n", encoding="utf-8")
    assert _modulo().main(["--planilha", str(tsv), "--bancada", "3991"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == f"medida: argv --planilha {tsv.resolve()}"


def test_o_instrumento_nao_roda_sem_python_do_rag(mundo, monkeypatch, capsys):
    _bancada(mundo, "3759-medida")
    monkeypatch.setenv("RAG_PYTHON", str(mundo / "nao-existe"))
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(mundo / "sem-release"))
    with pytest.raises(SystemExit) as e:
        _modulo().main([])
    assert e.value.code == 3 and capsys.readouterr().err.startswith("acervo medir:")


def test_pela_porta_o_ato_existe_e_o_cabecalho_o_declara():
    r = subprocess.run([str(BIN), "medir", "--outra"], capture_output=True, text=True)
    assert r.returncode == 2 and "uso: acervo medir" in r.stderr
    cabecalho = BIN.read_text(encoding="utf-8")
    assert "medir (escrita, acervo)" in cabecalho
    assert "# le: medir=" in cabecalho and "# escreve: medir=" in cabecalho


def test_o_exportar_segue_dizendo_o_proprio_nome(tmp_path):
    """`medir` reusa o módulo do exportar e troca o nome nas mensagens; o exportar não pode ter mudado."""
    env = {**os.environ, "PLATAFIRMA_BANCADA": str(tmp_path), "PF_SESSAO": "x", "PF_CADEIRA": "y"}
    r = subprocess.run([str(BIN), "exportar"], capture_output=True, text=True, env=env)
    assert r.returncode == 3 and r.stderr.startswith("acervo exportar:")
