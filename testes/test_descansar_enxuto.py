"""`descansar fita` enxuto (dono, 14/11/2026).

O que se trava: o relatorio do fim de fita mostra so o que o Sair usa (mesa, caderno e aresta; a
caixa saiu em 17/11/2026). Saiu o dossie de release, servico e acervo; saiu a contagem de giro, que so imprimia e nao
era custo; saiu a descoberta de cadeira pelo ledger com o prefixo claudinho-; o carimbo de
descanso e do encerramento; `--parada` sem `--encerra-sessao` recusa.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERBO = REPO_ROOT / "bin" / "descansar"
loader = SourceFileLoader("descansar_enxuto_bin", str(VERBO))
spec = importlib.util.spec_from_loader("descansar_enxuto_bin", loader)
assert spec and spec.loader
descansar = importlib.util.module_from_spec(spec)
loader.exec_module(descansar)

TEXTO = VERBO.read_text(encoding="utf-8")


def test_o_dossie_e_a_contagem_de_giro_sairam():
    for cmd in ("release estado", "conferir servico", "acervo escada", "infra estado"):
        assert cmd not in TEXTO, f"o dossie saiu: {cmd}"
    for fn in ("economia_de_giro", "fabrica_pela_porta", "giros_por_turno_code_local", "def roda("):
        assert fn not in TEXTO, f"saiu: {fn}"


def test_a_cadeira_e_o_slug_que_chega_sem_ledger_nem_prefixo(monkeypatch):
    assert "_ledger_map" not in TEXTO and "eventos-org.jsonl" not in TEXTO
    monkeypatch.setenv("PF_CADEIRA", "IA")
    assert descansar.slug() == "ia"


def test_a_varredura_le_as_cadeiras_da_abertura(monkeypatch, tmp_path):
    (tmp_path / "ia" / "busca").mkdir(parents=True)
    (tmp_path / "ti").mkdir()
    (tmp_path / "solto.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(descansar, "ABERTURA", str(tmp_path))
    assert descansar.cadeiras_da_abertura() == ["ia", "ti"]
    monkeypatch.setattr(descansar, "ABERTURA", str(tmp_path / "nao-existe"))
    assert descansar.cadeiras_da_abertura() == []


def test_o_carimbo_e_do_encerramento_nao_do_relatorio():
    fecho = TEXTO[TEXTO.index("def _fechar_sessao"):TEXTO.index("def ato_fita")]
    ato = TEXTO[TEXTO.index("def ato_fita"):TEXTO.index("def ato_varredura")]
    assert 'rc.set(f"mem:{curto}"' in fecho
    assert "rc.set(" not in ato


def test_parada_com_sem_encerrar_recusa(monkeypatch):
    monkeypatch.setenv("PF_CADEIRA", "ia")
    monkeypatch.setattr(descansar.sys, "argv", ["descansar", "fita", "--sem-encerrar", "--parada", "teto_giros"])
    monkeypatch.setattr(descansar, "conn", lambda: pytest.fail("a recusa nao toca o msg-mem"))
    with pytest.raises(SystemExit) as saiu:
        descansar.main()
    assert "--parada nao vale com --sem-encerrar" in str(saiu.value)
