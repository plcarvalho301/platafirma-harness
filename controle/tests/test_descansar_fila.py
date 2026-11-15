"""Testes de separacao novas vs penduradas em `bin/descansar` (#4289)."""
import importlib.util
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]


def _carrega_descansar():
    loader = SourceFileLoader("descansar_4289", str(REPO_ROOT / "bin" / "descansar"))
    spec = importlib.util.spec_from_loader("descansar_4289", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_roda_fila_cabecalho_so_penduradas_nao_diz_nao_lida(capsys):
    """#4289: quando nao ha carta nova, `novas` mostra (nenhuma) e `penduradas` vai separado."""
    mod = _carrega_descansar()
    saida_ler = (
        "===MSG 20261115T100000-engenharia===\n"
        "de: engenharia\n"
        "tipo: resposta\n"
        "estado: pendurada\n"
        "assunto: Leitura por chave exata\n"
        "\n"
        "===MSG 20261115T110000-dados===\n"
        "de: dados\n"
        "tipo: pauta\n"
        "estado: pendurada\n"
        "assunto: Leitura do acervo antes da busca\n"
    )
    saida_status = "conhecimento: nada novo · 2 pendurada(s) · 42 no historico (7 dias)\n"

    def fake_run(cmd, **_kw):
        texto = " ".join(cmd)
        if "fila status" in texto:
            return subprocess.CompletedProcess(cmd, 0, stdout=saida_status, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=saida_ler, stderr="")

    with patch.object(mod.subprocess, "run", side_effect=fake_run):
        mod.roda_fila_cabecalho(
            "fila — caixa de conhecimento",
            "fila ler conhecimento --penduradas",
            status_cmd="fila status conhecimento",
        )

    out = capsys.readouterr().out
    assert "status: conhecimento: nada novo · 2 pendurada(s)" in out
    assert "[novas — esperando leitura]\n  (nenhuma)" in out
    assert "[penduradas — ja lidas, aguardando `fila tratar` (nao esperam leitura)]" in out
    assert "2 pendurada(s) (ja lida(s), sem `fila tratar`)" in out
    assert "pendurada(s) ou nao lida(s)" not in out


def test_roda_fila_cabecalho_separa_novas_de_penduradas(capsys):
    """#4289: cartas `nao lida` e `pendurada` aparecem em blocos distintos com totais proprios."""
    mod = _carrega_descansar()
    saida_ler = (
        "===MSG 20261115T120000-engenharia===\n"
        "de: engenharia\n"
        "tipo: pedido\n"
        "estado: nao lida\n"
        "assunto: Carta nova\n"
        "\n"
        "===MSG 20261115T100000-dados===\n"
        "de: dados\n"
        "tipo: resposta\n"
        "estado: pendurada\n"
        "assunto: Carta ja lida\n"
    )
    saida_status = "conhecimento: 1 nova(s) · 1 pendurada(s) · 42 no historico (7 dias)\n"

    def fake_run(cmd, **_kw):
        texto = " ".join(cmd)
        if "fila status" in texto:
            return subprocess.CompletedProcess(cmd, 0, stdout=saida_status, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=saida_ler, stderr="")

    with patch.object(mod.subprocess, "run", side_effect=fake_run):
        mod.roda_fila_cabecalho(
            "fila — caixa de conhecimento",
            "fila ler conhecimento --penduradas",
            status_cmd="fila status conhecimento",
        )

    out = capsys.readouterr().out
    idx_novas = out.index("[novas — esperando leitura]")
    idx_pend = out.index("[penduradas — ja lidas, aguardando `fila tratar` (nao esperam leitura)]")
    assert idx_novas < idx_pend
    assert "1 nova(s) (nao lida(s))" in out[idx_novas:idx_pend]
    assert "1 pendurada(s) (ja lida(s), sem `fila tratar`)" in out[idx_pend:]
