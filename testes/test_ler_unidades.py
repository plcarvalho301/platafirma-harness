"""Testes das unidades do leitor único, setup-leitor.sh, conferir unit e infra (story #4442, t8)."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DEPLOY_HARNESS = RAIZ / "deploy-harness"
SETUP_SCRIPT = DEPLOY_HARNESS / "setup-leitor.sh"
BIN_INFRA = RAIZ / "bin" / "infra"
CONFERIR_DIR = RAIZ / "bin" / "_release" / "conferir"

UNIDADES = (
    "leitor.socket",
    "leitor.service",
    "leitor-extrator.socket",
    "leitor-extrator@.service",
)


def _instalar_copia_local(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nome in UNIDADES:
        alvo = destino / nome
        shutil.copyfile(DEPLOY_HARNESS / nome, alvo)
        alvo.chmod(0o644)


def _rodar_check(
    systemd_dir: Path,
    *,
    origem: Path = DEPLOY_HARNESS,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PF_SYSTEMD_DIR": str(systemd_dir),
        "PF_UNITS_ORIGEM": str(origem),
        "PF_CHECK_SEM_CONTAS": "1",
        "PF_CHECK_SEM_DONO": "1",
        **(extra_env or {}),
    }
    return subprocess.run(
        ["bash", str(SETUP_SCRIPT), "--check"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def test_setup_leitor_sintaxe_bash() -> None:
    proc = subprocess.run(["bash", "-n", str(SETUP_SCRIPT)], capture_output=True, text=True, timeout=30, check=False)
    assert proc.returncode == 0, proc.stderr


def test_setup_leitor_check_conforme(tmp_path: Path) -> None:
    systemd_dir = tmp_path / "systemd"
    _instalar_copia_local(systemd_dir)
    proc = _rodar_check(systemd_dir)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "conforme: leitor" in proc.stdout


def test_setup_leitor_check_reprova_symlink_e_modo(tmp_path: Path) -> None:
    systemd_dir = tmp_path / "systemd"
    _instalar_copia_local(systemd_dir)
    alvo = systemd_dir / "leitor.service"
    alvo.unlink()
    alvo.symlink_to(DEPLOY_HARNESS / "leitor.service")
    proc = _rodar_check(systemd_dir)
    assert proc.returncode == 1
    assert "leitor.service" in proc.stdout

    alvo.unlink()
    shutil.copyfile(DEPLOY_HARNESS / "leitor.service", alvo)
    alvo.chmod(0o666)
    proc_modo = _rodar_check(systemd_dir)
    assert proc_modo.returncode == 1
    assert "644" in proc_modo.stdout


@pytest.mark.parametrize(
    ("unidade", "diretiva_original", "mutacao"),
    [
        ("leitor.socket", "SocketMode=0660", "SocketMode=0666"),
        ("leitor.socket", "SocketGroup=pf-verbos", "SocketGroup=root"),
        ("leitor.service", "ProtectHome=yes", "ProtectHome=no"),
        ("leitor.service", "PrivateTmp=yes", "PrivateTmp=no"),
        ("leitor.service", "PrivateDevices=yes", "PrivateDevices=no"),
        ("leitor.service", "CapabilityBoundingSet=", "CapabilityBoundingSet=CAP_SYS_ADMIN"),
        ("leitor.service", "IPAddressDeny=any", "IPAddressDeny="),
        ("leitor.service", "IPAddressAllow=localhost", "IPAddressAllow=any"),
        ("leitor.service", "SystemCallFilter=@system-service", "SystemCallFilter="),
        ("leitor.service", "RestrictNamespaces=yes", "RestrictNamespaces=no"),
        ("leitor.service", "LockPersonality=yes", "LockPersonality=no"),
        ("leitor.service", "ProtectKernelTunables=yes", "ProtectKernelTunables=no"),
        ("leitor.service", "ProtectKernelModules=yes", "ProtectKernelModules=no"),
        ("leitor.service", "ProtectControlGroups=yes", "ProtectControlGroups=no"),
        ("leitor.service", "UMask=0077", "UMask=0022"),
        ("leitor-extrator.socket", "Accept=yes", "Accept=no"),
        ("leitor-extrator.socket", "SocketMode=0600", "SocketMode=0666"),
        ("leitor-extrator.socket", "SocketGroup=pf-verbos", "SocketGroup=pf-leitor"),
        ("leitor-extrator@.service", "PrivateNetwork=yes", "PrivateNetwork=no"),
        ("leitor-extrator@.service", "ProtectSystem=strict", "ProtectSystem=full"),
        ("leitor-extrator@.service", "NoNewPrivileges=yes", "NoNewPrivileges=no"),
        ("leitor-extrator@.service", "LimitCORE=0", "LimitCORE=infinity"),
        ("leitor-extrator@.service", "RestrictAddressFamilies=AF_UNIX", "RestrictAddressFamilies=AF_INET"),
        ("leitor-extrator@.service", "UMask=0077", "UMask=0022"),
    ],
)
def test_mutacao_diretivas_isolamento_reprovada(
    tmp_path: Path, unidade: str, diretiva_original: str, mutacao: str
) -> None:
    """Cada mutante que afrouxa uma diretiva de endurecimento tem de sair 1 mesmo com origem=destino."""
    origem = tmp_path / "origem"
    systemd_dir = tmp_path / "systemd"
    _instalar_copia_local(origem)
    _instalar_copia_local(systemd_dir)

    for pasta in (origem, systemd_dir):
        arq = pasta / unidade
        texto = arq.read_text(encoding="utf-8")
        assert diretiva_original in texto
        arq.write_text(texto.replace(diretiva_original, mutacao, 1), encoding="utf-8")
        arq.chmod(0o644)

    proc = _rodar_check(systemd_dir, origem=origem)
    assert proc.returncode == 1, f"mutante sobreviveu em {unidade}: {diretiva_original} -> {mutacao}"
    assert unidade in proc.stdout


def test_soquetes_so_usam_grupos_que_o_roteiro_cria() -> None:
    """SocketGroup sem grupo no host derruba o soquete na largada (Job failed no setup do dono, 25/11/2026)."""
    roteiro = SETUP_SCRIPT.read_text(encoding="utf-8")
    criados = {"pf-verbos", "pf-leitor-extrator"}  # groupadd pf-verbos e useradd --user-group pf-leitor-extrator
    assert 'groupadd --system "$GRUPO_VERBOS"' in roteiro
    assert "--user-group \"$CONTA_EXTRATOR\"" in roteiro
    for nome in ("leitor.socket", "leitor-extrator.socket"):
        for linha in (DEPLOY_HARNESS / nome).read_text(encoding="utf-8").splitlines():
            if linha.startswith("SocketGroup="):
                assert linha.split("=", 1)[1] in criados, f"{nome}: {linha} aponta grupo que setup-leitor.sh não cria"


def test_soquetes_nao_declaram_runtime_directory() -> None:
    """RuntimeDirectory num soquete nasce root com o modo dado e some no stop, levando os vizinhos sob /run/platafirma;
    o systemd já cria os pais do ListenStream em 0755 (DirectoryMode)."""
    for arq in sorted(DEPLOY_HARNESS.glob("*.socket")):
        texto = arq.read_text(encoding="utf-8")
        assert "RuntimeDirectory" not in texto, f"{arq.name} declara RuntimeDirectory"


def test_sudoers_ajudante_de_logs_sem_noexec() -> None:
    """NOEXEC barra o ajudante, que é roteiro e executa bash e journalctl ('/usr/bin/env: bash: Permission denied')."""
    linhas = [l for l in SETUP_SCRIPT.read_text(encoding="utf-8").splitlines() if l.startswith("${CONTA_CHAMADORA} ALL=")]
    ajudante = [l for l in linhas if l.endswith("${AJUDANTE_LOGS}")]
    restart = [l for l in linhas if l.endswith("/usr/bin/systemctl restart leitor.service")]
    assert len(ajudante) == 1 and "NOEXEC:" not in ajudante[0]
    assert len(restart) == 1 and "NOEXEC:" in restart[0]


def test_mutacao_readwritepaths_no_extrator_reprovada(tmp_path: Path) -> None:
    origem = tmp_path / "origem"
    systemd_dir = tmp_path / "systemd"
    _instalar_copia_local(origem)
    _instalar_copia_local(systemd_dir)
    for pasta in (origem, systemd_dir):
        arq = pasta / "leitor-extrator@.service"
        arq.write_text(arq.read_text(encoding="utf-8") + "ReadWritePaths=/tmp\n", encoding="utf-8")
        arq.chmod(0o644)
    proc = _rodar_check(systemd_dir, origem=origem)
    assert proc.returncode == 1
    assert "ReadWritePaths" in proc.stdout


def test_conferir_unit_leitor_registra_e_executa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(CONFERIR_DIR))
    import conferir

    assert "leitor" in conferir._SETUPS_UNIT_CHECK
    assert conferir._SETUPS_UNIT_CHECK["leitor"] == ("harness", "deploy-harness/setup-leitor.sh")

    release_dir = tmp_path / "release"
    (release_dir / "harness" / "deploy-harness").mkdir(parents=True)
    shutil.copytree(DEPLOY_HARNESS, release_dir / "harness" / "deploy-harness", dirs_exist_ok=True)
    systemd_dir = tmp_path / "systemd"
    _instalar_copia_local(systemd_dir)

    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(release_dir))
    monkeypatch.setenv("PF_SYSTEMD_DIR", str(systemd_dir))
    monkeypatch.setenv("PF_CHECK_SEM_CONTAS", "1")
    monkeypatch.setenv("PF_CHECK_SEM_DONO", "1")
    assert conferir.conferir_unit("leitor", como_json=True) == 0

    (systemd_dir / "leitor.service").unlink()
    assert conferir.conferir_unit("leitor", como_json=True) == 1


def test_infra_logs_e_restart_leitor_service(tmp_path: Path) -> None:
    stub_logs = tmp_path / "stub-logs"
    stub_logs.write_text("#!/usr/bin/env bash\nprintf 'linha-telemetria n=%s\\n' \"$1\"\n", encoding="utf-8")
    stub_logs.chmod(0o755)

    stub_restart = tmp_path / "stub-restart"
    stub_restart.write_text("#!/usr/bin/env bash\nprintf 'ok %s\\n' \"$1\"\n", encoding="utf-8")
    stub_restart.chmod(0o755)

    env = {
        **os.environ,
        "PF_SUJEITO": "engenharia",
        "INFRA_LEITOR_LOGS_CMD": str(stub_logs),
        "INFRA_LEITOR_RESTART_CMD": str(stub_restart),
        "PF_LEITOR_SOCKET": str(tmp_path / "inexistente.sock"),
    }
    p_logs = subprocess.run(
        ["bash", str(BIN_INFRA), "logs", "leitor.service", "3"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert p_logs.returncode == 0, p_logs.stderr
    assert "linha-telemetria n=3" in p_logs.stdout

    p_rst = subprocess.run(
        ["bash", str(BIN_INFRA), "restart", "leitor.service"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert p_rst.returncode == 0, p_rst.stderr
    assert "leitor.service reiniciada" in p_rst.stdout


def test_recuperacao_nao_depende_do_leitor_unico(tmp_path: Path) -> None:
    """infra e release rodam sem chamar o soquete do leitor único."""
    texto_infra = BIN_INFRA.read_text(encoding="utf-8")
    assert "leitor.sock" not in texto_infra
    assert "leitura.cliente" not in texto_infra
    texto_release = (RAIZ / "bin" / "release").read_text(encoding="utf-8")
    assert "leitor.sock" not in texto_release
    assert "leitura.cliente" not in texto_release
    # Mesmo com PF_LEITOR_SOCKET apontando para caminho inexistente, infra medir rede --help sai 0.
    env = {**os.environ, "PF_LEITOR_SOCKET": str(tmp_path / "nao-existe.sock")}
    p = subprocess.run(
        ["bash", str(BIN_INFRA), "medir", "rede", "--help"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert p.returncode == 0
    assert stat.S_ISREG((DEPLOY_HARNESS / "setup-leitor.sh").stat().st_mode)
