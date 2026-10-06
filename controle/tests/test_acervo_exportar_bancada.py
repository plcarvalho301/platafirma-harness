"""#3163: `acervo exportar --bancada <chave>` escolhe entre várias bancadas abertas da cadeira."""
from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

EXPORTAR = Path(__file__).resolve().parents[2] / "bin" / "_acervo" / "exportar"


@pytest.fixture
def mod(tmp_path, monkeypatch):
    loader = importlib.machinery.SourceFileLoader("exportar_teste", str(EXPORTAR))
    spec = importlib.util.spec_from_loader("exportar_teste", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    for chave in ("3194-a", "3163-export"):
        (tmp_path / "wt" / m.REPO / "dados" / chave / ".git").mkdir(parents=True)
    monkeypatch.setattr(m.raizes, "bancada", lambda: tmp_path)
    monkeypatch.setenv("PF_CADEIRA", "dados")
    monkeypatch.delenv("PF_SESSAO", raising=False)
    return m


def test_duas_bancadas_sem_chave_recusa_e_diz_a_opcao(mod, capsys):
    with pytest.raises(SystemExit) as e:
        mod.bancada_do_repo()
    assert e.value.code == 2 and "--bancada" in capsys.readouterr().err


def test_chave_escolhe_a_bancada(mod, tmp_path):
    assert mod.bancada_do_repo("3163-export") == tmp_path / "wt" / mod.REPO / "dados" / "3163-export"


def test_chave_que_nao_existe_recusa(mod):
    with pytest.raises(SystemExit) as e:
        mod.bancada_do_repo("9999-nada")
    assert e.value.code == 2


def _marca(mod, tmp_path, chave, sessao):
    (tmp_path / "wt" / mod.REPO / "dados" / chave / ".git" / "pf-sessao-viva").write_text(
        f"{sessao}\t2026-10-06T13:00:00Z\n", encoding="utf-8")

def test_marca_da_sessao_desempata_sem_escolher_calado(mod, tmp_path, monkeypatch):
    # #3317: o --apply de retirar chama o export sem --bancada; a bancada marcada pela sessão vale
    _marca(mod, tmp_path, "3163-export", "sessao-a")
    _marca(mod, tmp_path, "3194-a", "sessao-b")
    monkeypatch.setenv("PF_SESSAO", "sessao-a")
    assert mod.bancada_do_repo() == tmp_path / "wt" / mod.REPO / "dados" / "3163-export"

def test_sem_marca_da_sessao_segue_recusando(mod, tmp_path, monkeypatch, capsys):
    _marca(mod, tmp_path, "3194-a", "sessao-b")
    monkeypatch.setenv("PF_SESSAO", "sessao-a")
    with pytest.raises(SystemExit) as e:
        mod.bancada_do_repo()
    assert e.value.code == 2 and "--bancada" in capsys.readouterr().err

def test_argumento_desconhecido_e_uso(mod):
    assert mod.main(["--outra"]) == 2
