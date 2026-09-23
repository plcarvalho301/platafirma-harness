# Contrato de `acervo exportar` e da limpeza do `acervo extrato` (pedido 20260922T220127-dados)
import importlib.machinery
import importlib.util
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "bin", "acervo")


def _carrega(nome):
    caminho = os.path.join(REPO, "bin", "_acervo", nome)
    loader = importlib.machinery.SourceFileLoader(f"_acervo_{nome}", caminho)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_exportar_recusa_argumento():
    r = subprocess.run([BIN, "exportar", "obra"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "acervo exportar" in r.stderr


def test_exportar_sem_bancada_aponta_o_caminho(tmp_path):
    env = {**os.environ, "PLATAFIRMA_BANCADA": str(tmp_path), "PF_SESSAO": "x", "PF_CADEIRA": "y"}
    r = subprocess.run([BIN, "exportar"], capture_output=True, text=True, env=env)
    assert r.returncode == 3
    assert "repo abrir platafirma-conhecimento" in r.stderr


def test_exportar_prefere_a_bancada_da_sessao(tmp_path, monkeypatch):
    for chave in ("sessao-1", "engenharia"):
        (tmp_path / "wt" / "platafirma-conhecimento" / chave / ".git").mkdir(parents=True)
    (tmp_path / "platafirma-conhecimento" / ".git").mkdir(parents=True)
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    monkeypatch.setenv("PF_CADEIRA", "claudinho-engenharia")
    mod = _carrega("exportar")
    monkeypatch.setenv("PF_SESSAO", "sessao-1")
    assert mod.bancada_do_repo().name == "sessao-1"
    monkeypatch.setenv("PF_SESSAO", "outra")
    assert mod.bancada_do_repo().name == "engenharia"


def test_extrato_limpa_caractere_de_controle():
    mod = _carrega("extrato")
    assert mod.limpa("a\x01b\x1fc\td\ne") == "abc\td\ne"
    assert mod.limpa(None) is None
