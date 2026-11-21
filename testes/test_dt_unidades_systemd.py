# componente: componente:verbo-infra
"""Provas dos DTs 352, 380, 390 e 479: conferir unit, longjob --collect/ExecStopPost e infra unit-env."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFERIR_PATH = RAIZ / "bin" / "_release" / "conferir" / "conferir.py"
LONGJOB_PATH = RAIZ / "bin" / "_sessao" / "longjob"
INFRA_PATH = RAIZ / "bin" / "infra"


def _carregar(caminho, nome):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


conferir = _carregar(CONFERIR_PATH, "conferir_unit_teste")


def _prepara_setup(tmp_path, monkeypatch, body):
    release = tmp_path / "release"
    script = release / "conhecimento" / "rag" / "deploy" / "setup-prior-secao.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/usr/bin/env bash\n" + body + "\n")
    script.chmod(0o755)
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(release))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")
    return script


def test_conferir_unit_conforme(tmp_path, monkeypatch, capsys):
    _prepara_setup(tmp_path, monkeypatch, 'echo "convergido"; exit 0')
    rc = conferir.conferir_unit("prior-secao.timer", como_json=True)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["itens"] == [{"nome": "prior-secao", "estado": "conforme", "desde": "indeterminavel", "motivo": None}]


def test_conferir_unit_divergente(tmp_path, monkeypatch, capsys):
    _prepara_setup(tmp_path, monkeypatch, 'echo "DIFERE: prior-secao.service"; exit 1')
    rc = conferir.conferir_unit("prior-secao", como_json=True)
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["itens"][0]["estado"] == "divergente"
    assert "DIFERE: prior-secao.service" in out["itens"][0]["motivo"]


def test_conferir_unit_sem_permissao_sai_indeterminavel(tmp_path, monkeypatch, capsys):
    _prepara_setup(tmp_path, monkeypatch, 'echo "nao consegui ler a instancia" >&2; exit 1')
    rc = conferir.conferir_unit(None, como_json=True)
    assert rc == 5
    out = json.loads(capsys.readouterr().out)
    assert out["itens"][0]["estado"] == "indeterminavel"


def test_conferir_unit_desconhecida(capsys):
    rc = conferir.conferir_unit("inexistente", como_json=True)
    assert rc == 2


def test_longjob_run_passa_collect_e_execstoppost(tmp_path):
    falso_bin = tmp_path / "falso_bin"
    falso_bin.mkdir()
    args_arq = tmp_path / "systemd_run_args.txt"
    (falso_bin / "systemd-run").write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$@\" > {str(args_arq)!r}\n"
    )
    (falso_bin / "systemd-run").chmod(0o755)
    (falso_bin / "systemctl").write_text(
        "#!/usr/bin/env bash\n"
        "echo 'not-found'\n"
    )
    (falso_bin / "systemctl").chmod(0o755)

    inst = tmp_path / "inst"
    inst.mkdir()
    env = {
        **os.environ,
        "PATH": f"{falso_bin}:{os.environ['PATH']}",
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PLATAFIRMA_RELEASE": str(tmp_path / "rel"),
    }
    p = subprocess.run(
        [str(LONGJOB_PATH), "run", "teste", "echo", "oi"],
        env=env, capture_output=True, text=True, check=True,
    )
    unit = [l.split(":", 1)[1].strip() for l in p.stdout.splitlines() if l.startswith("unit:")][0]
    log = [l.split(":", 1)[1].strip() for l in p.stdout.splitlines() if l.startswith("log:")][0]

    args = args_arq.read_text().splitlines()
    assert "--collect" in args
    exec_stop = [a for a in args if a.startswith("--property=ExecStopPost=")]
    assert len(exec_stop) == 1
    assert "%" not in exec_stop[0]

    # Simula o systemd executando o comando de ExecStopPost ao sair com falha
    cmd = exec_stop[0].split("=", 2)[2]
    subprocess.run(
        ["/bin/bash", "-c", f"SERVICE_RESULT=exit-code EXIT_STATUS=7 {cmd}"],
        check=True,
    )
    st = subprocess.run(
        [str(LONGJOB_PATH), "status", unit],
        env=env, capture_output=True, text=True, check=True,
    )
    assert "Result=exit-code" in st.stdout
    assert "ExecMainStatus=7" in st.stdout
    assert Path(log).exists()


def _prepara_falso_systemctl(bin_dir, home_dir, frag_por_unit):
    bin_dir.mkdir(exist_ok=True)
    log_arq = bin_dir / "systemctl.log"
    mapa = json.dumps(frag_por_unit)
    (bin_dir / "systemctl").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"mapa = json.loads({mapa!r})\n"
        f"open({str(log_arq)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        "args = sys.argv[1:]\n"
        "if 'cat' in args:\n"
        "    sys.exit(0)\n"
        "if 'show' in args:\n"
        "    unit = args[-1]\n"
        "    if 'FragmentPath' in args:\n"
        "        print(mapa.get(unit, ''))\n"
        "    sys.exit(0)\n"
        "sys.exit(0)\n"
    )
    (bin_dir / "systemctl").chmod(0o755)
    return log_arq


def test_infra_unit_env_usa_local_share_quando_config_bloqueado(tmp_path):
    home = tmp_path / "home"
    cfg = home / ".config" / "systemd" / "user"
    loc = home / ".local" / "share" / "systemd" / "user"
    cfg.mkdir(parents=True)
    loc.mkdir(parents=True)
    (loc / "corte-bruto.service").write_text("[Service]\n")
    cfg.chmod(0o555)
    try:
        falso_bin = tmp_path / "bin"
        log_arq = _prepara_falso_systemctl(
            falso_bin, home,
            {"corte-bruto.service": str(loc / "corte-bruto.service")},
        )
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{falso_bin}:{os.environ['PATH']}",
        }
        env.pop("INFRA_UNITS_CONFIG_DIR", None)
        env.pop("XDG_DATA_HOME", None)
        p = subprocess.run(
            [str(INFRA_PATH), "unit-env", "corte-bruto", "CORTE_ARGS=--seco"],
            env=env, capture_output=True, text=True,
        )
        assert p.returncode == 0, p.stderr
        dropin = loc / "corte-bruto.service.d" / "zz-infra-env.conf"
        assert dropin.exists()
        assert "Environment=CORTE_ARGS=--seco" in dropin.read_text()
        assert "daemon-reload" in log_arq.read_text()
    finally:
        cfg.chmod(0o755)


def test_infra_unit_env_recusa_unit_de_root_em_config(tmp_path):
    home = tmp_path / "home"
    cfg = home / ".config" / "systemd" / "user"
    cfg.mkdir(parents=True)
    (cfg / "ops-mcp.service").write_text("[Service]\n")
    cfg.chmod(0o555)
    try:
        falso_bin = tmp_path / "bin"
        _prepara_falso_systemctl(
            falso_bin, home,
            {"ops-mcp.service": str(cfg / "ops-mcp.service")},
        )
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{falso_bin}:{os.environ['PATH']}",
        }
        env.pop("INFRA_UNITS_CONFIG_DIR", None)
        p = subprocess.run(
            [str(INFRA_PATH), "unit-env", "ops-mcp", "X=1"],
            env=env, capture_output=True, text=True,
        )
        assert p.returncode == 4
    finally:
        cfg.chmod(0o755)
