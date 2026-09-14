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


def test_foto_servida_bate_com_alias_cadeiras_monta_sessao():
    """Aceite: persona foto bate com alias-cadeiras servido pelo monta-sessao."""
    proc = _run_persona(["foto"])
    assert proc.returncode == 0
    linhas = proc.stdout.strip().splitlines()
    assert len(linhas) == 11
    # Verifica ordem exata pelo alias
    esperado = [
        "Carla Cangurina -> gestao-estrategica",
        "Elias Elefante -> ia",
        "Fábrica -> fabrica",
        "João-de-Barro -> arquiteto",
        "Leonardo Tartaruga -> seguranca",
        "Luiz Guará -> politicas-publicas",
        "Lygia Bem-te-vi -> produto",
        "Nicole Capivara -> inteligencia",
        "Nuno Bacalhau -> direito",
        "Olga Corujeira -> dados",
        "Oswaldo Aranha -> ti",
    ]
    assert linhas == esperado


def test_foto_json_servido():
    """Aceite: persona foto --json devolve dicionário completo das 11 cadeiras."""
    proc = _run_persona(["foto", "--json"])
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert isinstance(dados, dict)
    assert len(dados) == 11

    # Verifica campos de cadeiras conhecidas
    assert dados["gestao-estrategica"]["alias"] == "Carla Cangurina"
    assert "estrategia" in dados["gestao-estrategica"]["chapeus"]

    assert dados["ia"]["alias"] == "Elias Elefante"
    assert "agente" in dados["ia"]["chapeus"]

    assert dados["fabrica"]["alias"] == "Fábrica"
    assert sorted(dados["fabrica"]["chapeus"]) == ["blueteam", "devops", "front-end"]


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


def test_foto_opcao_invalida():
    """Flag desconhecida sai 2 com mensagem de uso."""
    proc = _run_persona(["foto", "--desconhecida"])
    assert proc.returncode == 2
    assert "argumento desconhecido" in proc.stderr
