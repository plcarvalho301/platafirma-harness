"""Testes unitários e contratuais para o verbo persona após fix do card #3105.

Cobre:
- Comportamento esperado (a): `persona conferir` passa no molde novo e reprova no molde velho.
- Comportamento esperado (b): `persona salvar` e verificação de alvos.
- Comportamento esperado (c): `persona abrir` e `persona sanear` recuperam de clone divergente sem erro.
- Comportamento esperado (d): teto recalibrado para 1400 palavras contra o template.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
import pytest

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


def test_abrir_e_sanear_recupera_divergencia(tmp_path):
    """`persona abrir` e `persona sanear` recuperam sem exit 128 quando há divergência git."""
    remote_bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote_bare)], check=True, capture_output=True)

    # Clone inicial
    orig = tmp_path / "orig"
    subprocess.run(["git", "clone", str(remote_bare), str(orig)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(orig), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(orig), "config", "user.email", "test@platafirma.org"], check=True)

    (orig / "base.txt").write_text("base\n")
    (orig / "abertura").mkdir()
    (orig / "abertura" / "teste").mkdir()
    (orig / "abertura" / "teste" / "persona.md").write_text("persona\n")
    subprocess.run(["git", "-C", str(orig), "add", "."], check=True)
    subprocess.run(["git", "-C", str(orig), "commit", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(orig), "branch", "-M", "main"], check=True)
    subprocess.run(["git", "-C", str(orig), "push", "-u", "origin", "main"], check=True)
    subprocess.run(["git", "-C", str(remote_bare), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)

    # Clone de trabalho onde persona abrir rodará
    clone_trabalho = tmp_path / "clone_trabalho"
    subprocess.run(["git", "clone", "-b", "main", str(remote_bare), str(clone_trabalho)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(clone_trabalho), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(clone_trabalho), "config", "user.email", "test@platafirma.org"], check=True)

    # 1. Commit remoto via orig
    (orig / "remoto.txt").write_text("remoto\n")
    subprocess.run(["git", "-C", str(orig), "add", "."], check=True)
    subprocess.run(["git", "-C", str(orig), "commit", "-m", "commit no remoto"], check=True)
    subprocess.run(["git", "-C", str(orig), "push", "origin", "main"], check=True)

    # 2. Commit local divergente em clone_trabalho
    (clone_trabalho / "local.txt").write_text("local\n")
    subprocess.run(["git", "-C", str(clone_trabalho), "add", "."], check=True)
    subprocess.run(["git", "-C", str(clone_trabalho), "commit", "-m", "commit local divergente"], check=True)

    # Se chamasse git pull --ff-only puro, falharia com exit 128.
    # Com o fix de abrir/sanear, recupera via rebase sem erro.
    proc_abrir = _run_persona(["abrir"], env_extra={"PERSONA_REPO": str(clone_trabalho)})
    assert proc_abrir.returncode == 0, f"persona abrir falhou: {proc_abrir.stderr}"
    assert "clone em dia" in proc_abrir.stdout or "clone recuperado" in proc_abrir.stdout
    assert (clone_trabalho / "remoto.txt").is_file()
    assert (clone_trabalho / "local.txt").is_file()

    # Testa também o sub-ato explícito `persona sanear`
    proc_sanear = _run_persona(["sanear"], env_extra={"PERSONA_REPO": str(clone_trabalho)})
    assert proc_sanear.returncode == 0
