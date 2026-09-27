"""Contrato de `release conferir jobs` (card #3147).

Release e systemd --user de fixture: um `systemctl` que responde `list-units` e `show`
de um JSON, e uma release minima com os dois declarantes que a casa tem
(harness/deploy-harness/instalar e core/deploy/units-da-instancia.json). Prova: um item
por timer agendado; conforme so com declarante, link pelo atalho estavel, nada da
bancada, EnvironmentFile do ops-mcp quando chama verbo, habilitado e ultima execucao
sem falha; unit de pacote do sistema e conforme; timer que um instalador promete e nao
esta agendado e divergente; systemd ilegivel sai 5. Nao prova: o systemd real da conta.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

CONFERIR = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"
ENV_OPS = "/home/claudinho/.config/ops/env"

STUB = """#!/usr/bin/env python3
import json, os, sys
d = json.load(open(os.environ["STUB_JOBS"]))
a = sys.argv[1:]
if d.get("quebrado"):
    print("Failed to connect to bus", file=sys.stderr); sys.exit(1)
if "list-units" in a:
    print("\\n".join(t + " loaded active waiting x" for t in d["timers"])); sys.exit(0)
if "show" in a:
    u = a[a.index("show") + 1]
    for k, v in d["units"].get(u, {}).items():
        print(f"{k}={v}")
    sys.exit(0)
sys.exit(9)
"""

INSTALAR = """#!/usr/bin/env bash
UNITS=(
  "deploy-harness/a.service|alvo-de-timer"
  "deploy-harness/a.timer|habilita"
  "deploy-harness/esperado.service|alvo-de-timer"
  "deploy-harness/esperado.timer|habilita"
  "deploy-harness/velho.service|alvo-de-timer"
  "deploy-harness/velho.timer|habilita"
)
"""

REGISTRO = {
    "units": {"b.service": {"fonte": "motor/deploy/b.service"},
              "b.timer": {"fonte": "motor/deploy/b.timer", "liga": "timers.target"}},
    "_fora_deste_instalador": {"c.service, c.timer": "deploy/setup-c.sh — dono root"},
}


def _montar(tmp_path, quebrado=False):
    rel = tmp_path / "rel"
    (rel / "harness" / "deploy-harness").mkdir(parents=True)
    (rel / "harness" / "deploy-harness" / "instalar").write_text(INSTALAR)
    (rel / "core" / "deploy").mkdir(parents=True)
    (rel / "core" / "deploy" / "units-da-instancia.json").write_text(json.dumps(REGISTRO))
    units = tmp_path / "units"
    units.mkdir()

    def link(nome, alvo):
        (units / nome).symlink_to(alvo)
        return str(units / nome)

    def copia(nome):
        (units / nome).write_text("[Unit]\n")
        return str(units / nome)

    verbo_ok = {"ExecStart": "{ path=x ; argv[]=/opt/platafirma/current/harness/bin/sinal ; }",
                "EnvironmentFiles": f"{ENV_OPS} (ignore_errors=no)", "WorkingDirectory": "/opt", "Result": "success"}
    script = {"ExecStart": "{ argv[]=/usr/bin/python3 /opt/platafirma/current/motor/x.py }",
              "EnvironmentFiles": "", "WorkingDirectory": "/srv", "Result": "success"}
    r = str(rel)
    u = {
        "a.timer": {"Unit": "a.service", "FragmentPath": link("a.timer", f"{r}/harness/deploy-harness/a.timer"),
                    "UnitFileState": "enabled", "ActiveState": "active"},
        "a.service": {"FragmentPath": link("a.service", f"{r}/harness/deploy-harness/a.service"), **verbo_ok},
        "b.timer": {"Unit": "b.service", "FragmentPath": link("b.timer", f"{r}/motor/deploy/b.timer"),
                    "UnitFileState": "disabled", "ActiveState": "active"},
        "b.service": {"FragmentPath": link("b.service", f"{r}/motor/deploy/b.service"), **script},
        "c.timer": {"Unit": "c.service", "FragmentPath": copia("c.timer"), "UnitFileState": "enabled"},
        "c.service": {"FragmentPath": copia("c.service"), **verbo_ok, "EnvironmentFiles": ""},
        "d.timer": {"Unit": "d.service", "FragmentPath": copia("d.timer"), "UnitFileState": "enabled"},
        "d.service": {"FragmentPath": copia("d.service"), **script},
        "s.timer": {"Unit": "s.service", "FragmentPath": "/usr/lib/systemd/user/s.timer", "UnitFileState": "enabled"},
        "s.service": {"FragmentPath": "/usr/lib/systemd/user/s.service", **script},
        "velho.timer": {"Unit": "velho.service", "UnitFileState": "enabled",
                        "FragmentPath": link("velho.timer", "/opt/platafirma/platafirma-harness/abc123/deploy-harness/velho.timer")},
        "velho.service": {"FragmentPath": link("velho.service", f"{r}/harness/deploy-harness/velho.service"), **verbo_ok},
    }
    dados = {"timers": ["a.timer", "b.timer", "c.timer", "d.timer", "s.timer", "velho.timer"], "units": u,
             "quebrado": quebrado}
    (tmp_path / "jobs.json").write_text(json.dumps(dados))
    stubdir = tmp_path / "stub"
    stubdir.mkdir()
    (stubdir / "systemctl").write_text(STUB)
    (stubdir / "systemctl").chmod(0o755)
    env = {**os.environ, "PATH": f"{stubdir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
           "STUB_JOBS": str(tmp_path / "jobs.json"), "PLATAFIRMA_RELEASE": r,
           "PF_AI_DIR": str(tmp_path / "AI"), "PF_HARNESS_DIR": str(tmp_path / "nada")}
    return env


def _jobs(env, *extra):
    return subprocess.run([sys.executable, str(CONFERIR), "jobs", *extra, "--json"],
                          capture_output=True, text=True, env=env)


def _por_nome(p):
    d = json.loads(p.stdout)
    return {i["nome"].split()[0]: i for i in d["itens"]}, d


def test_um_item_por_timer_e_os_vereditos(tmp_path):
    p = _jobs(_montar(tmp_path))
    assert p.returncode == 1, p.stdout + p.stderr
    itens, d = _por_nome(p)
    assert d["ancora"].startswith("release conferir jobs")
    assert itens["a.timer"]["estado"] == "conforme"
    assert itens["s.timer"]["estado"] == "conforme"
    assert "disabled" in itens["b.timer"]["motivo"]
    assert "EnvironmentFile" in itens["c.timer"]["motivo"]
    assert "sem declarante" in itens["d.timer"]["motivo"]
    assert "fora do atalho estavel" in itens["velho.timer"]["motivo"]
    assert "nao agendado" in itens["esperado.timer"]["motivo"]
    # seis agendados + o prometido e ausente
    assert len(itens) == 7


def test_alvo_mede_so_um_timer(tmp_path):
    p = _jobs(_montar(tmp_path), "a")
    assert p.returncode == 0, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert list(itens) == ["a.timer"]


def test_systemd_ilegivel_sai_5(tmp_path):
    p = _jobs(_montar(tmp_path, quebrado=True))
    assert p.returncode == 5, p.stdout + p.stderr
