"""Testes do verbo persona: `conferir` (card #3105).

Cobre:
- (a) `persona conferir` passa no molde novo e reprova no molde velho.
- (d) teto recalibrado para 1400 palavras contra o template.

Os atos `abrir`, `sanear` e `salvar` deixaram de fazer git no #3273; o contrato novo
(bancada de card, sem commit, sem push, clone-cache intocado) esta em
controle/tests/test_contrato_persona_bancada.py.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_PERSONA = REPO_ROOT / "bin" / "persona"


def _run_persona(args: list[str], cwd: Path | None = None, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(BIN_PERSONA)] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
        env=env,
    )


def test_conferir_molde_novo_cadeiras_vivas():
    """As personas migradas para o molde novo passam sem erro."""
    for cad in ["engenharia", "gestao-estrategica", "ia", "ti"]:
        proc = _run_persona(["conferir", cad])
        assert proc.returncode == 0, f"Falha em conferir {cad}: {proc.stderr}\n{proc.stdout}"
        assert "0 erro(s)" in proc.stdout


def test_conferir_reprova_molde_velho():
    """Personas no molde velho (como arquiteto) reprovam com exit 1 e listam as seções que faltam."""
    proc = _run_persona(["conferir", "arquiteto"])
    assert proc.returncode == 1
    assert "falta a secao Perguntas de competência" in proc.stdout
    assert "falta a secao Vocabulário canônico" in proc.stdout
    assert "secao obsoleta do molde velho 'POSTURA'" in proc.stdout


def test_conferir_arquivo_customizado(tmp_path):
    """Linter valida arquivo avulso no molde novo e detecta quebras estruturais."""
    p_dir = tmp_path / "minha-cadeira"
    p_dir.mkdir()
    p_file = p_dir / "persona.md"

    # Molde novo perfeito com um chapéu
    (p_dir / "operacao").mkdir()
    (p_dir / "operacao" / "chapeu.md").write_text("# chapeu operacao\n")

    p_file.write_text(
        "Você é uma cadeira no molde novo da PlataFirma.\n"
        "Linha 2 de introdução.\n\n"
        "## Perguntas de competência\n\n1. Pergunta 1?\n\n"
        "## Vocabulário canônico\n\n- termo: definicao\n\n"
        "## Escopo\n\n- o que nao faz\n\n"
        "## Sinais de reconhecimento\n\n- sinal 1\n\n"
        "## Gerências\n\n- **operacao** — linha de operacao\n"
    )

    proc = _run_persona(["conferir", str(p_file)])
    assert proc.returncode == 0, proc.stdout
    assert "0 erro(s)" in proc.stdout

    # Quebra de ordem das seções
    p_file.write_text(
        "Você é uma cadeira no molde novo da PlataFirma.\n\n"
        "## Vocabulário canônico\n\n- termo: definicao\n\n"
        "## Perguntas de competência\n\n1. Pergunta 1?\n\n"
        "## Escopo\n\n- o que nao faz\n\n"
        "## Sinais de reconhecimento\n\n- sinal 1\n\n"
        "## Gerências\n\n- **operacao** — linha de operacao\n"
    )
    proc_ordem = _run_persona(["conferir", str(p_file)])
    assert proc_ordem.returncode == 1
    assert "fora de ordem" in proc_ordem.stdout


def test_conferir_teto_recalibrado(tmp_path):
    """Teto recalibrado para 1400: avisa apenas acima do limite."""
    p_dir = tmp_path / "cadeira-extensa"
    p_dir.mkdir()
    p_file = p_dir / "persona.md"
    (p_dir / "sub").mkdir()
    (p_dir / "sub" / "chapeu.md").write_text("# chapeu sub\n")

    # 1300 palavras (dentro do teto)
    corpo_1300 = "palavra " * 1300
    p_file.write_text(
        "Introdução da cadeira.\n\n"
        "## Perguntas de competência\n\n1. Pergunta?\n\n"
        "## Vocabulário canônico\n\n" + corpo_1300 + "\n\n"
        "## Escopo\n\n- escopo\n\n"
        "## Sinais de reconhecimento\n\n- sinal\n\n"
        "## Gerências\n\n- **sub** — linha sub\n"
    )
    proc = _run_persona(["conferir", str(p_file)])
    assert proc.returncode == 0
    assert "teto 1400" not in proc.stdout

    # 1450 palavras (estoura teto -> aviso, mas não erro)
    corpo_1450 = "palavra " * 1450
    p_file.write_text(
        "Introdução da cadeira.\n\n"
        "## Perguntas de competência\n\n1. Pergunta?\n\n"
        "## Vocabulário canônico\n\n" + corpo_1450 + "\n\n"
        "## Escopo\n\n- escopo\n\n"
        "## Sinais de reconhecimento\n\n- sinal\n\n"
        "## Gerências\n\n- **sub** — linha sub\n"
    )
    proc_teto = _run_persona(["conferir", str(p_file)])
    assert proc_teto.returncode == 0
    assert "palavras (teto 1400)" in proc_teto.stdout
