# componente: componente:verbo-infra
"""Provas de segurança do verbo `infra` (achados #1354 e #1356).

- #1354: `infra unit-env` exige PF_SUJEITO, valida chave com ^[A-Za-z_][A-Za-z0-9_]*$,
  recusa quebra de linha e caractere de controle (evitando injeção de diretiva systemd),
  recusa segredos em Environment= (variável solta), grava drop-in em 0600 e suporta
  `--credencial NOME=stack/segredo` (LoadCredential= apontando para o cofre 0600).
- #1356: todos os atos de mutação do `infra` exigem PF_SUJEITO (enquanto leituras e `--ver`
  seguem sem exigir), e `cache disco` / `limpeza cache` não executam `docker volume prune -f`.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or shutil.which("python3") is None,
    reason="sem bash ou python3 no PATH",
)


def _stub(bin_dir: Path, nome: str, corpo: str) -> Path:
    p = bin_dir / nome
    p.write_text("#!/usr/bin/env bash\n" + corpo + "\n", encoding="utf-8")
    p.chmod(0o755)
    return p


def _env_base(tmp_path: Path, *, sujeito: str | None = "teste") -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    inst = tmp_path / "instancia"
    inst.mkdir(exist_ok=True)
    _stub(
        bin_dir,
        "systemctl",
        'if [ "${1:-}" = "--user" ] && [ "${2:-}" = "cat" ]; then exit 0; fi\n'
        'if [ "${1:-}" = "--user" ] && [ "${2:-}" = "show" ]; then echo ""; exit 0; fi\n'
        "exit 0",
    )
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "PLATAFIRMA_INSTANCIA": str(inst),
        "INFRA_UNITS_CONFIG_DIR": str(home / ".config" / "systemd" / "user"),
    }
    (home / ".config" / "systemd" / "user").mkdir(parents=True, exist_ok=True)
    if sujeito is None:
        env.pop("PF_SUJEITO", None)
    else:
        env["PF_SUJEITO"] = sujeito
    return env, inst


# --- #1354: unit-env --------------------------------------------------------

def test_unit_env_mutacao_exige_pf_sujeito_mas_ver_nao(tmp_path: Path):
    env, _ = _env_base(tmp_path, sujeito=None)
    r_ver = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "--ver"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_ver.returncode == 0, r_ver.stderr

    r_write = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "FOO=bar"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_write.returncode == 3
    assert "PF_SUJEITO" in r_write.stderr


@pytest.mark.parametrize("arg", [
    "FOO=bar\nExecStartPre=/bin/evil",
    "FOO=bar\rExecStartPre=/bin/evil",
    "FOO=bar\x07bell",
    "123INVALID=ok",
    "FOO-BAR=ok",
    "FOO.BAR=ok",
])
def test_unit_env_recusa_injecao_controle_e_chave_invalida(tmp_path: Path, arg: str):
    env, _ = _env_base(tmp_path)
    r = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", arg],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    dropin = Path(env["INFRA_UNITS_CONFIG_DIR"]) / "demo.service.d" / "zz-infra-env.conf"
    assert not dropin.exists()


@pytest.mark.parametrize("arg", [
    "POSTGRES_PASSWORD=segredo",
    "RAG_API_TOKEN=tok123",
    "CLIENT_SECRET=abc",
    "API_KEY=xyz",
    "CERT_MATERIAL=-----BEGIN PRIVATE KEY-----",
])
def test_unit_env_recusa_segredo_como_variavel_solta(tmp_path: Path, arg: str):
    env, _ = _env_base(tmp_path)
    r = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", arg],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 4, (r.returncode, r.stdout, r.stderr)
    assert "seg segredo gravar" in r.stderr
    assert "--credencial" in r.stderr
    dropin = Path(env["INFRA_UNITS_CONFIG_DIR"]) / "demo.service.d" / "zz-infra-env.conf"
    assert not dropin.exists()


def test_unit_env_grava_0600_e_suporta_load_credential_do_cofre(tmp_path: Path):
    env, inst = _env_base(tmp_path)
    cofre_stack = inst / "segredos" / "rag"
    cofre_stack.mkdir(parents=True)
    seg = cofre_stack / "RAG_API_TOKEN"
    seg.write_text("valor-secreto-nao-exposto", encoding="utf-8")
    seg.chmod(0o600)

    r = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "MODO=ativo", "--credencial", "rag_token=rag/RAG_API_TOKEN"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    dropin = Path(env["INFRA_UNITS_CONFIG_DIR"]) / "demo.service.d" / "zz-infra-env.conf"
    assert dropin.is_file()
    assert stat.S_IMODE(dropin.stat().st_mode) == 0o600
    conteudo = dropin.read_text(encoding="utf-8")
    assert "Environment=MODO=ativo" in conteudo
    assert f"LoadCredential=rag_token:{seg.resolve()}" in conteudo
    assert "valor-secreto-nao-exposto" not in conteudo

    # Remoção da credencial preserva Environment=
    r_rm = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "--credencial", "rag_token="],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_rm.returncode == 0, r_rm.stderr
    conteudo2 = dropin.read_text(encoding="utf-8")
    assert "Environment=MODO=ativo" in conteudo2
    assert "LoadCredential=" not in conteudo2


def test_unit_env_credencial_recusa_permissao_aberta_e_ausente(tmp_path: Path):
    env, inst = _env_base(tmp_path)
    # Ausente -> exit 3
    r_aus = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "--credencial", "tok=rag/NAO_EXISTE"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_aus.returncode == 3

    # Permissão aberta (0644) -> exit 4
    cofre_stack = inst / "segredos" / "rag"
    cofre_stack.mkdir(parents=True)
    seg = cofre_stack / "ABERTO"
    seg.write_text("x", encoding="utf-8")
    seg.chmod(0o644)
    r_ab = subprocess.run(
        [BASH, str(INFRA), "unit-env", "demo", "--credencial", "tok=rag/ABERTO"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r_ab.returncode == 4


# --- #1356: PF_SUJEITO em mutações e sem docker volume prune ----------------

@pytest.mark.parametrize("args", [
    ["restart", "demo"],
    ["cache", "vram"],
    ["cache", "disco"],
    ["limpeza", "cache"],
    ["limpeza", "logs"],
    ["limpeza", "quarentena"],
    ["limpeza", "fossil"],
    ["limpeza", "jobs"],
    ["limpeza", "imagens"],
    ["ingress"],
    ["agenda", "aplicar"],
    ["units", "aplicar"],
    ["ambiente", "aplicar"],
])
def test_atos_de_mutacao_do_infra_exigem_pf_sujeito(tmp_path: Path, args: list[str]):
    env, _ = _env_base(tmp_path, sujeito=None)
    r = subprocess.run(
        [BASH, str(INFRA), *args],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 3, (args, r.returncode, r.stdout, r.stderr)
    assert "PF_SUJEITO" in r.stderr


def test_cache_disco_nao_roda_docker_volume_prune(tmp_path: Path):
    env, _ = _env_base(tmp_path, sujeito="teste")
    bin_dir = tmp_path / "bin"
    rastro = tmp_path / "docker.log"
    _stub(
        bin_dir,
        "docker",
        f'echo "$*" >> "{rastro}"\n'
        'if [ "${1:-}" = "ps" ]; then exit 0; fi\n'
        'if [ "${1:-}" = "images" ]; then exit 0; fi\n'
        "exit 0",
    )
    _stub(bin_dir, "uv", "exit 0")
    r = subprocess.run(
        [BASH, str(INFRA), "cache", "disco"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    comandos = rastro.read_text(encoding="utf-8")
    assert "volume prune" not in comandos
    assert "volumes Docker nao sao podados aqui" in r.stdout
