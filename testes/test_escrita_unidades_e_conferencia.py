"""Suíte hermética da t6 (#4441): unidades, instalador --check, conferência e sonda."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

_HARNESS = Path(__file__).resolve().parents[1]
_LIB = _HARNESS / "lib"
_CONFERIR_DIR = _HARNESS / "bin" / "_release" / "conferir"
for _p in (str(_LIB), str(_CONFERIR_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from escrita.politica import carregar_politica  # noqa: E402
from escrita.servidor import ConfigServidor, ServidorEscritor  # noqa: E402


def test_release_conferir_repassa_a_classe_escritor() -> None:
    """`release conferir escritor` saiu 2 classe-desconhecida no ar (25/11/2026): a lista do verbo não tinha a classe."""
    texto = (_HARNESS / "bin" / "release").read_text(encoding="utf-8")
    bloco = texto.split("CLASSES_SERVIDO=(", 1)[1].split(")", 1)[0]
    assert '"escritor"' in bloco


def test_conferir_escritor_le_o_cliente_da_release_e_nao_do_clone() -> None:
    """No ar, HARNESS aponta o clone em ~/AI, sem lib/escrita/cliente.py: ModuleNotFoundError (25/11/2026).
    Esta suíte pré-importa escrita da árvore e mascarava o defeito; a prova é pela fonte."""
    import inspect

    conferir = _carregar_modulo("conferir_t6_regressao", _CONFERIR_DIR / "conferir.py")
    fonte = inspect.getsource(conferir.conferir_escritor)
    assert "_Path(HARNESS)" not in fonte
    assert '"current" / "harness"' in fonte


def _carregar_modulo(nome: str, caminho: Path):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _parse_unit(caminho: Path) -> dict[str, str]:
    campos: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#") or limpa.startswith("[") or "=" not in limpa:
            continue
        k, v = limpa.split("=", 1)
        campos[k.strip()] = v.strip()
    return campos


def _core_dir() -> Path:
    cand = Path("/home/claudinho/AI/wt/platafirma-core/engenharia/4441-ato-escrever")
    if cand.is_dir():
        return cand
    cand_opt = Path("/opt/platafirma/current/core")
    return cand_opt


def test_diretivas_das_unidades_socket_e_service() -> None:
    sock_u = _parse_unit(_HARNESS / "deploy-harness" / "escritor.socket")
    assert sock_u["SocketUser"] == "pf-escritor"
    assert sock_u["SocketGroup"] == "platafirma-escrita"
    assert sock_u["SocketMode"] == "0660"
    assert sock_u["MaxConnections"] == "32"
    assert sock_u["ListenStream"] == "/run/platafirma/escritor.sock"

    svc_u = _parse_unit(_HARNESS / "deploy-harness" / "escritor.service")
    esperados = {
        "User": "pf-escritor",
        "UMask": "0077",
        "LimitCORE": "0",
        "NoNewPrivileges": "yes",
        "ProtectSystem": "strict",
        "ProtectHome": "tmpfs",
        "BindReadOnlyPaths": "/home/claudinho/AI",
        "BindPaths": "/home/claudinho/AI/wt",
        "PrivateTmp": "yes",
        "PrivateDevices": "yes",
        "CapabilityBoundingSet": "",
        "RestrictAddressFamilies": "AF_UNIX AF_INET AF_INET6",
        "IPAddressDeny": "any",
        "IPAddressAllow": "localhost",
        "SystemCallFilter": "@system-service",
        "SystemCallArchitectures": "native",
        "MemoryDenyWriteExecute": "yes",
        "RestrictNamespaces": "yes",
        "LockPersonality": "yes",
        "ProtectKernelTunables": "yes",
        "ProtectKernelModules": "yes",
        "ProtectControlGroups": "yes",
        "MemoryHigh": "192M",
        "MemoryMax": "256M",
        "TasksMax": "64",
        "KillMode": "mixed",
        "TimeoutStopSec": "45s",
    }
    for chave, valor in esperados.items():
        assert svc_u.get(chave) == valor, f"diretiva {chave} divergente: {svc_u.get(chave)!r}"
    assert "/home/claudinho/AI/wt" in svc_u["ReadWritePaths"]


def test_setup_escritor_check_e_units_da_instancia(tmp_path: Path) -> None:
    core = _core_dir()
    setup = core / "deploy" / "setup-escritor.sh"
    if not setup.is_file():
        pytest.skip("platafirma-core/deploy/setup-escritor.sh ausente neste ambiente")

    units_json = json.loads((core / "deploy" / "units-da-instancia.json").read_text(encoding="utf-8"))
    fora = units_json["_fora_deste_instalador"]
    assert "escritor.socket, escritor.service" in fora
    assert "setup-escritor.sh" in fora["escritor.socket, escritor.service"]

    sys_dir = tmp_path / "systemd"
    sys_dir.mkdir()
    env = {
        **os.environ,
        "PF_HARNESS_DIR": str(_HARNESS),
        "PF_SYSTEM_UNITS": str(sys_dir),
        "PF_ESCRITOR_SKIP_IDENTIDADE": "1",
    }

    # 1. Ausentes -> sai 1
    p_aus = subprocess.run(["bash", str(setup), "--check"], env=env, capture_output=True, text=True, check=False)
    assert p_aus.returncode == 1

    # 2. Cópias idênticas -> sai 0
    for nome in ("escritor.socket", "escritor.service"):
        (sys_dir / nome).write_bytes((_HARNESS / "deploy-harness" / nome).read_bytes())
    p_ok = subprocess.run(["bash", str(setup), "--check"], env=env, capture_output=True, text=True, check=False)
    assert p_ok.returncode == 0, p_ok.stderr

    # 3. Divergência de conteúdo -> sai 1
    (sys_dir / "escritor.service").write_text("[Service]\nMemoryMax=512M\n", encoding="utf-8")
    p_div = subprocess.run(["bash", str(setup), "--check"], env=env, capture_output=True, text=True, check=False)
    assert p_div.returncode == 1

    # 4. Symlink para a release -> sai 1
    (sys_dir / "escritor.service").unlink()
    (sys_dir / "escritor.service").symlink_to(_HARNESS / "deploy-harness" / "escritor.service")
    p_sym = subprocess.run(["bash", str(setup), "--check"], env=env, capture_output=True, text=True, check=False)
    assert p_sym.returncode == 1


def test_conferir_escritor_conforme_e_divergencias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    conferir = _carregar_modulo("conferir_t6", _CONFERIR_DIR / "conferir.py")
    assert "escritor" in conferir.CLASSES_IMPLEMENTADAS

    sys_dir = tmp_path / "systemd"
    sys_dir.mkdir()
    for nome in ("escritor.socket", "escritor.service"):
        (sys_dir / nome).write_bytes((_HARNESS / "deploy-harness" / nome).read_bytes())

    setup = _core_dir() / "deploy" / "setup-escritor.sh"
    if not setup.is_file():
        setup = tmp_path / "setup-fake.sh"
        setup.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    monkeypatch.setenv("PF_HARNESS_DIR", str(_HARNESS))
    monkeypatch.setenv("PF_SYSTEM_UNITS", str(sys_dir))
    monkeypatch.setenv("PF_ESCRITOR_SKIP_IDENTIDADE", "1")

    sock_path = tmp_path / "escritor.sock"
    pol = carregar_politica(_HARNESS / "registro" / "escrita.yaml")
    srv = ServidorEscritor(
        ConfigServidor(
            socket_path=sock_path,
            raiz_bancadas=tmp_path / "wt",
            estado_dir=tmp_path / "estado",
            politica=pol,
            uid_escritor=os.geteuid(),
            varrer_orfaos_na_largada=False,
            poll_intervalo_s=0.05,
        )
    )
    srv.iniciar()
    th = threading.Thread(target=srv.servir, daemon=True)
    th.start()
    try:
        rc_ok = conferir.conferir_escritor(
            como_json=True,
            setup_script=setup,
            service_unit=sys_dir / "escritor.service",
            socket_unit=sys_dir / "escritor.socket",
            socket_path=sock_path,
            analyze_runner=lambda: (0, "→ Overall exposure level for escritor.service: 1.7 SAFE\n", ""),
        )
        assert rc_ok == 0

        rc_exp = conferir.conferir_escritor(
            como_json=True,
            setup_script=setup,
            service_unit=sys_dir / "escritor.service",
            socket_unit=sys_dir / "escritor.socket",
            socket_path=sock_path,
            analyze_runner=lambda: (0, "→ Overall exposure level for escritor.service: 2.6 OK\n", ""),
        )
        assert rc_exp == 1

        rc_sock_fora = conferir.conferir_escritor(
            como_json=True,
            setup_script=setup,
            service_unit=sys_dir / "escritor.service",
            socket_unit=sys_dir / "escritor.socket",
            socket_path=tmp_path / "ausente.sock",
            analyze_runner=lambda: (0, "→ Overall exposure level for escritor.service: 1.7 SAFE\n", ""),
        )
        assert rc_sock_fora == 1
    finally:
        srv.parar("fim-teste")
        th.join(timeout=3.0)


def test_sonda_escritor_no_verbo_sinal(tmp_path: Path) -> None:
    sinal = _carregar_modulo("sinal_t6", _HARNESS / "bin" / "sinal")

    fora = sinal.do_escritor(tmp_path / "ausente.sock")
    assert fora["estado"] == "fora"
    assert fora["motivo"]

    sock_path = tmp_path / "escritor-sinal.sock"
    pol = carregar_politica(_HARNESS / "registro" / "escrita.yaml")
    srv = ServidorEscritor(
        ConfigServidor(
            socket_path=sock_path,
            raiz_bancadas=tmp_path / "wt",
            estado_dir=tmp_path / "estado",
            politica=pol,
            uid_escritor=os.geteuid(),
            varrer_orfaos_na_largada=False,
            poll_intervalo_s=0.05,
        )
    )
    srv.iniciar()
    th = threading.Thread(target=srv.servir, daemon=True)
    th.start()
    try:
        no_ar = sinal.do_escritor(sock_path)
        assert no_ar["estado"] == "no-ar"
        assert "saude" in no_ar["exercitado"]
    finally:
        srv.parar("fim-teste")
        th.join(timeout=3.0)
