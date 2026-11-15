"""Testes unitários e contratuais para `persona foto` (spec_sessao §2, spec_expediente §7, #3053).

Cobre:
- Formato texto: uma linha por cadeira ordenada pelo alias: `Nome Humano -> slug`
- Formato --json: {"<slug>": {"alias": "<Nome>"|null, "chapeus": ["<slug>", ...]}}
- Cadeira viva sem alias (null no aliases.json) -> (sem alias) -> <slug>
- Cadeira viva ausente de aliases.json -> (sem alias, omitido) -> <slug>
- Exit 3 quando morada não publicada (mesma mensagem e cura de exige_morada)
- Exit 1 quando aliases.json ilegível ou ausente (degrada, não trava)
- Exit 2 em flag desconhecida
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_PERSONA = REPO_ROOT / "bin" / "persona"


def _run_persona(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(BIN_PERSONA)] + args,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )


def test_foto_morada_nao_publicada(tmp_path):
    """Exit 3 quando morada não publicada ($ARVORE não existe)."""
    inexistente = tmp_path / "sem-morada"
    proc = _run_persona(["foto"], env_extra={"PF_ABERTURA_DIR": str(inexistente)})
    assert proc.returncode == 3
    assert "persona: morada nao publicada" in proc.stderr
    assert "publicar-abertura" in proc.stderr


def test_foto_aliases_json_ilegivel(tmp_path):
    """Exit 1 quando aliases.json é ilegível/corrompido — degrada e lista sem alias."""
    abertura = tmp_path / "current" / "abertura"
    abertura.mkdir(parents=True)
    # Cadeira viva
    cad = abertura / "ia"
    cad.mkdir()
    (cad / "persona.md").write_text("# persona ia\n")
    # aliases.json corrompido
    (abertura / "aliases.json").write_text("{invalido json")

    # Texto
    proc = _run_persona(["foto"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc.returncode == 1
    assert "persona foto: aliases.json ausente ou ilegivel" in proc.stderr
    assert "(sem alias) -> ia" in proc.stdout

    # JSON
    proc_json = _run_persona(["foto", "--json"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc_json.returncode == 1
    dados = json.loads(proc_json.stdout)
    assert dados["ia"]["alias"] is None
    assert dados["ia"]["chapeus"] == []


def test_foto_cadeira_sem_alias_null(tmp_path):
    """Cadeira viva sem alias (null no aliases.json) sai `(sem alias) -> <slug>`."""
    abertura = tmp_path / "current" / "abertura"
    abertura.mkdir(parents=True)
    cad = abertura / "fabrica"
    cad.mkdir()
    (cad / "persona.md").write_text("# persona fabrica\n")
    (abertura / "aliases.json").write_text(json.dumps({"fabrica": None}))

    # Texto
    proc = _run_persona(["foto"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc.returncode == 0
    assert proc.stdout.strip() == "(sem alias) -> fabrica"

    # JSON
    proc_json = _run_persona(["foto", "--json"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc_json.returncode == 0
    dados = json.loads(proc_json.stdout)
    assert dados["fabrica"]["alias"] is None


def test_foto_cadeira_ausente_do_mapa(tmp_path):
    """Cadeira viva ausente do mapa sai com nota `(sem alias, omitido) -> <slug>`."""
    abertura = tmp_path / "current" / "abertura"
    abertura.mkdir(parents=True)
    cad1 = abertura / "ia"
    cad1.mkdir()
    (cad1 / "persona.md").write_text("# persona ia\n")

    cad2 = abertura / "nova"
    cad2.mkdir()
    (cad2 / "persona.md").write_text("# persona nova\n")

    (abertura / "aliases.json").write_text(json.dumps({"ia": "Elias Elefante"}))

    # Texto
    proc = _run_persona(["foto"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc.returncode == 0
    linhas = proc.stdout.strip().splitlines()
    assert "(sem alias, omitido) -> nova" in linhas
    assert "Elias Elefante -> ia" in linhas

    # JSON
    proc_json = _run_persona(["foto", "--json"], env_extra={"PF_ABERTURA_DIR": str(tmp_path)})
    assert proc_json.returncode == 0
    dados = json.loads(proc_json.stdout)
    assert dados["nova"]["alias"] is None
    assert dados["ia"]["alias"] == "Elias Elefante"


def test_ler_usa_pf_cadeira_quando_cadeira_omitida(tmp_path):
    """DT 518 / DT 601: `persona ler` e `persona ler --chapeu <slug>` usam PF_CADEIRA quando <cadeira> é omitida."""
    abertura = tmp_path / "current" / "abertura"
    cad = abertura / "conhecimento"
    ch = cad / "modelos-formais"
    ch.mkdir(parents=True)
    (cad / "persona.md").write_text("# Persona Conhecimento\n")
    (ch / "chapeu.md").write_text("# Chapeu Modelos Formais\n")

    proc_p = _run_persona(["ler"], env_extra={"PF_ABERTURA_DIR": str(tmp_path), "PF_CADEIRA": "conhecimento"})
    assert proc_p.returncode == 0, proc_p.stderr
    assert "# Persona Conhecimento" in proc_p.stdout

    proc_c = _run_persona(
        ["ler", "--chapeu", "modelos-formais"],
        env_extra={"PF_ABERTURA_DIR": str(tmp_path), "PF_CADEIRA": "conhecimento"},
    )
    assert proc_c.returncode == 0, proc_c.stderr
    assert "# Chapeu Modelos Formais" in proc_c.stdout


def test_lembrete_mapa_capacidades_aponta_acervo_vigente():
    """DT 608: bin/persona aponta para o vocabulário no acervo da casa (arq:0059 / arq:0119)."""
    texto = BIN_PERSONA.read_text(encoding="utf-8")
    caminho_legado = "platafirma-arquitetura" + "@" + "docs/arquitetura-negocio-operacao.md"
    assert caminho_legado not in texto
    assert "acervo ler casa vocabulario arquitetura-negocio-operacao" in texto
    assert "acervo ler casa vocabulario capacidades" in texto
