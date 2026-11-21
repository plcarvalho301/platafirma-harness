# componente: componente:verbo-infra
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
INFRA = RAIZ / "bin" / "infra"


def _stub(bin_dir: Path, nome: str, corpo: str) -> None:
    p = bin_dir / nome
    p.write_text("#!/usr/bin/env bash\n" + corpo + "\n", encoding="utf-8")
    p.chmod(0o755)


def _env_com_stubs(tmp_path: Path) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "rastro.log"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["RASTRO"] = str(log)
    env["HOME"] = str(tmp_path / "home")
    Path(env["HOME"]).mkdir(exist_ok=True)
    return env, log


def test_dt15_cache_ver_lista_imagens_e_disco_preserva_keep_storage(tmp_path: Path):
    env, log = _env_com_stubs(tmp_path)
    bin_dir = tmp_path / "bin"
    _stub(bin_dir, "curl", 'echo "{}"')
    _stub(bin_dir, "nvidia-smi", 'echo "100 MiB, 8000 MiB"')
    _stub(bin_dir, "du", 'echo "10M\t$2"')
    _stub(
        bin_dir,
        "docker",
        'echo "docker $*" >> "$RASTRO"\n'
        'if [ "${1:-}" = "system" ]; then echo "TYPE TOTAL ACTIVE SIZE RECLAIMABLE"; fi',
    )
    r_ver = subprocess.run(
        ["bash", str(INFRA), "cache", "ver"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_ver.returncode == 0, r_ver.stderr
    assert "== imagens docker" in r_ver.stdout
    assert "== em produção" in r_ver.stdout

    log.write_text("", encoding="utf-8")
    env["INFRA_BUILD_CACHE_KEEP_STORAGE"] = "12GB"
    r_disco = subprocess.run(
        ["bash", str(INFRA), "cache", "disco"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_disco.returncode == 0, r_disco.stderr
    linhas = log.read_text(encoding="utf-8").splitlines()
    assert "docker builder prune -a -f --keep-storage 12GB" in linhas
    assert "docker images --no-trunc --format {{json .}}" in linhas


def test_dt16_restart_roda_daemon_reload_quando_need_daemon_reload_yes(tmp_path: Path):
    env, log = _env_com_stubs(tmp_path)
    bin_dir = tmp_path / "bin"
    _stub(
        bin_dir,
        "systemctl",
        'echo "systemctl $*" >> "$RASTRO"\n'
        'if [ "${1:-}" = "--user" ] && [ "${2:-}" = "cat" ]; then exit 0; fi\n'
        'if [ "${1:-}" = "--user" ] && [ "${2:-}" = "show" ]; then echo "yes"; exit 0; fi\n'
        'exit 0',
    )
    _stub(bin_dir, "systemd-run", 'echo "systemd-run $*" >> "$RASTRO"')

    r = subprocess.run(
        ["bash", str(INFRA), "restart", "demo.service"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    linhas = log.read_text(encoding="utf-8").splitlines()
    assert "systemctl --user daemon-reload" in linhas
    assert "systemctl --user restart demo.service" in linhas
    idx_reload = linhas.index("systemctl --user daemon-reload")
    idx_restart = linhas.index("systemctl --user restart demo.service")
    assert idx_reload < idx_restart


def test_dt56_unit_env_recusa_com_exit_4_quando_dir_nao_gravavel(tmp_path: Path):
    env, _ = _env_com_stubs(tmp_path)
    bin_dir = tmp_path / "bin"
    _stub(
        bin_dir,
        "systemctl",
        'if [ "${1:-}" = "--user" ] && [ "${2:-}" = "cat" ]; then exit 0; fi\nexit 0',
    )
    cfg_dir = tmp_path / "systemd-user"
    cfg_dir.mkdir(parents=True)
    cfg_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
    env["INFRA_UNITS_CONFIG_DIR"] = str(cfg_dir)

    try:
        r = subprocess.run(
            ["bash", str(INFRA), "unit-env", "prior-secao.service", "FOO=bar"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        cfg_dir.chmod(0o755)

    assert r.returncode == 4, (r.returncode, r.stdout, r.stderr)
    assert "sudo bash" in r.stderr
    assert "deploy/units-da-instancia.json" in r.stderr
    assert "Permission denied" not in r.stderr
