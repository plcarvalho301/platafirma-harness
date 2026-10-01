"""Contrato de `release conferir jobs` (card #3147).

Release e systemd --user de fixture: um `systemctl` que responde `list-units` e `show`
de um JSON, e uma release minima com os dois declarantes que a casa tem
(harness/deploy-harness/instalar e core/deploy/units-da-instancia.json). Prova: um item
por timer agendado; conforme so com declarante, link pelo atalho estavel, nada da
bancada, EnvironmentFile do ops-mcp quando chama verbo, habilitado e ultima execucao
sem falha; unit de pacote do sistema e conforme; timer que um instalador promete e nao
esta agendado e divergente; systemd ilegivel sai 5.

Card #3186: a unit do bot (cabecalho de lib/units.py E ficha ativa do slug, por `bot listar
--json`) conta como declarada, nos dois nomes; a unit sai do GERADOR real e passa pela
fixture, entao o primeiro timer do bot nao sai divergente; cabecalho sem ficha e orfa;
ficha de timer sem unit agendada diverge e a de gatilho manual nao promete nada; servico
de fichas fora e "nao consegui olhar". Nao prova: o systemd nem o servico reais da conta.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

import units

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


# --- unit do bot (card #3186) -------------------------------------------------------

BOT_STUB = """#!/usr/bin/env python3
import json, os, sys
d = json.load(open(os.environ["STUB_FICHAS"]))
if sys.argv[1:] != ["listar", "--json"]:
    sys.exit(9)
if d.get("quebrado"):
    print("bot: rota /acervo/automacoes fora do ar", file=sys.stderr); sys.exit(3)
print(json.dumps(d["fichas"]))
"""

SLUG = "bot-x"
CALENDARIO = "*-*-* 06:45"


def _ficha(slug, trigger="timer", ciclo="ativa"):
    return {"slug": slug, "ciclo": ciclo, "trigger_tipo": trigger, "dono": "ti",
            "trigger_arg": CALENDARIO if trigger == "timer" else None}


def _valor(texto, chave):
    return next(l.split("=", 1)[1] for l in texto.splitlines() if l.startswith(chave + "="))


def _montar_bot(tmp_path, fichas, cabecalho=(True, True), timers=(f"{SLUG}.timer",), ficha_fora=False):
    """Variante de _montar: release sem declarante de manifesto, uma unit do bot gerada pelo
    GERADOR REAL (o show do stub devolve o que o texto gerado declara) e `bot` de stub."""
    rel = tmp_path / "rel"
    (rel / "harness" / "deploy-harness").mkdir(parents=True)
    (rel / "harness" / "deploy-harness" / "instalar").write_text("#!/usr/bin/env bash\nUNITS=(\n)\n")
    (rel / "core" / "deploy").mkdir(parents=True)
    (rel / "core" / "deploy" / "units-da-instancia.json").write_text(json.dumps({"units": {}}))
    (rel / "harness" / "bin").mkdir()
    (rel / "harness" / "bin" / "bot").write_text(BOT_STUB)
    (rel / "harness" / "bin" / "bot").chmod(0o755)
    pasta = tmp_path / "units"
    pasta.mkdir()
    service, timer = units.gera_unit(_ficha(SLUG))
    textos = {f"{SLUG}.timer": timer, f"{SLUG}.service": service}  # na ordem de `cabecalho`
    for (nome, texto), com in zip(textos.items(), cabecalho):
        (pasta / nome).write_text(texto if com else texto.split("\n", 1)[1])
    u = {
        f"{SLUG}.timer": {"Unit": f"{SLUG}.service", "FragmentPath": str(pasta / f"{SLUG}.timer"),
                          "UnitFileState": "enabled", "ActiveState": "active"},
        f"{SLUG}.service": {
            "FragmentPath": str(pasta / f"{SLUG}.service"),
            "ExecStart": "{ path=x ; argv[]=" + _valor(service, "ExecStart") + " ; }",
            "EnvironmentFiles": _valor(service, "EnvironmentFile") + " (ignore_errors=no)",
            "WorkingDirectory": _valor(service, "WorkingDirectory"), "Result": "success"},
    }
    (tmp_path / "jobs.json").write_text(json.dumps({"timers": list(timers), "units": u, "quebrado": False}))
    (tmp_path / "fichas.json").write_text(json.dumps({"fichas": fichas, "quebrado": ficha_fora}))
    stubdir = tmp_path / "stub"
    stubdir.mkdir()
    (stubdir / "systemctl").write_text(STUB)
    (stubdir / "systemctl").chmod(0o755)
    return {**os.environ, "PATH": f"{stubdir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "STUB_JOBS": str(tmp_path / "jobs.json"), "STUB_FICHAS": str(tmp_path / "fichas.json"),
            "PLATAFIRMA_RELEASE": str(rel), "PF_AI_DIR": str(tmp_path / "AI"),
            "PF_HARNESS_DIR": str(tmp_path / "nada")}


def test_primeiro_timer_do_bot_nao_sai_divergente(tmp_path):
    p = _jobs(_montar_bot(tmp_path, [_ficha(SLUG)]))
    assert p.returncode == 0, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert itens[f"{SLUG}.timer"]["estado"] == "conforme"
    assert f"[bot@{SLUG}]" in itens[f"{SLUG}.timer"]["nome"]
    assert len(itens) == 1


def test_cabecalho_do_bot_sem_ficha_ativa_e_orfa(tmp_path):
    for i, fichas in enumerate(([], [_ficha(SLUG, ciclo="retirada")], [_ficha("outro")])):
        p = _jobs(_montar_bot(tmp_path / str(i), fichas))
        assert p.returncode == 1, p.stdout + p.stderr
        itens, _ = _por_nome(p)
        assert "sem declarante" in itens[f"{SLUG}.timer"]["motivo"]


def test_ficha_ativa_sem_cabecalho_continua_sem_declarante(tmp_path):
    p = _jobs(_montar_bot(tmp_path, [_ficha(SLUG)], cabecalho=(False, False)))
    assert p.returncode == 1, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert "sem declarante" in itens[f"{SLUG}.timer"]["motivo"]


def test_os_dois_nomes_tem_de_ser_do_bot(tmp_path):
    p = _jobs(_montar_bot(tmp_path, [_ficha(SLUG)], cabecalho=(False, True)))
    itens, _ = _por_nome(p)
    assert "sem declarante" in itens[f"{SLUG}.timer"]["motivo"]
    p = _jobs(_montar_bot(tmp_path / "2", [_ficha(SLUG)], cabecalho=(True, False)))
    itens, _ = _por_nome(p)
    assert f"{SLUG}.service sem declarante" in itens[f"{SLUG}.timer"]["motivo"]
    assert f"bot@{SLUG}" in itens[f"{SLUG}.timer"]["motivo"]


def test_ficha_de_timer_sem_unit_agendada_diverge_e_manual_nao_promete(tmp_path):
    fichas = [_ficha("sem-unit"), _ficha("so-manual", trigger="manual")]
    p = _jobs(_montar_bot(tmp_path, fichas, timers=()))
    assert p.returncode == 1, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert "nao agendado" in itens["sem-unit.timer"]["motivo"]
    assert "bot@sem-unit" in itens["sem-unit.timer"]["motivo"]
    assert list(itens) == ["sem-unit.timer"]


def test_fichas_fora_do_ar_e_nao_consegui_olhar(tmp_path):
    p = _jobs(_montar_bot(tmp_path, [], ficha_fora=True))
    assert p.returncode == 5, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert itens[f"{SLUG}.timer"]["estado"] == "indeterminavel"
    assert "fichas do bot" in itens[f"{SLUG}.timer"]["motivo"]
    # sem unit do bot na rodada o servico fora nao muda o exit: so o aviso, em stderr
    p = _jobs(_montar_bot(tmp_path / "2", [], timers=(), ficha_fora=True))
    assert p.returncode == 0, p.stdout + p.stderr
    itens, _ = _por_nome(p)
    assert itens == {}
    assert "nao li as fichas do bot" in p.stderr

def test_sem_unit_do_bot_e_servico_de_fichas_fora_o_exit_e_os_itens_nao_mudam(tmp_path):
    base = _jobs(_montar(tmp_path / "a"))                    # release sem bin/bot: nunca pergunta as fichas
    env = _montar(tmp_path / "b")                            # a mesma ronda, agora com o bot ouvindo um servico fora
    bin_ = Path(env["PLATAFIRMA_RELEASE"]) / "harness" / "bin"
    bin_.mkdir()
    (bin_ / "bot").write_text(BOT_STUB)
    (bin_ / "bot").chmod(0o755)
    (tmp_path / "b" / "fichas.json").write_text(json.dumps({"fichas": [], "quebrado": True}))
    p = _jobs({**env, "STUB_FICHAS": str(tmp_path / "b" / "fichas.json")})
    assert base.returncode == 1 and p.returncode == base.returncode, p.stdout + p.stderr
    itens, d = _por_nome(p)
    assert {n: i["estado"] for n, i in itens.items()} == {n: i["estado"] for n, i in _por_nome(base)[0].items()}
    assert "(fichas" not in itens
    assert d["ancora"].split(" — release")[0] == _por_nome(base)[1]["ancora"].split(" — release")[0], "a contagem dos 7 itens nao muda"
    assert "nao li as fichas do bot" in p.stderr and "nao li as fichas" not in base.stderr


def test_duracao_para_iso():
    for texto, iso in (("1d", "P1D"), ("6h", "PT6H"), ("30m", "PT30M"), ("90s", "PT90S"),
                       ("1d12h", "P1DT12H"), ("P1D", "P1D"), ("pt6h", "PT6H"), ("P1DT12H", "P1DT12H")):
        assert units.duracao_para_iso(texto) == iso
    for ruim in ("", "0s", "0d0h", "-1d", "1x", "abc", "P", "PT", "P1DT", "P0D", "1d 2h", "h6"):
        try:
            units.duracao_para_iso(ruim)
        except ValueError:
            continue
        raise AssertionError(f"aceitou {ruim!r}")


def test_gerador_e_deterministico_e_recusa_injecao():
    decl = _ficha(SLUG)
    service, timer = units.gera_unit(decl)
    assert (service, timer) == units.gera_unit(dict(decl))
    assert units.eh_unit_do_bot(service) and units.eh_unit_do_bot(timer)
    assert not units.eh_unit_do_bot("[Unit]\n" + service) and not units.eh_unit_do_bot("")
    assert f"ExecStart=/opt/platafirma/current/harness/bin/bot rodar {SLUG}\n" in service
    assert f"EnvironmentFile={ENV_OPS}\n" in service and "Type=oneshot\n" in service
    assert f"OnCalendar={CALENDARIO}\n" in timer and "WantedBy=timers.target\n" in timer
    assert f"Unit={SLUG}.service\n" in timer
    for ruim in ("*-*-* 06:45\nExecStartPre=/bin/x", "\r", "06:45\x00", "  ", "", "2099-01-01 \\", "*-*-* %H:00"):
        try:
            units.gera_unit({**decl, "trigger_arg": ruim})
        except ValueError:
            continue
        raise AssertionError(f"aceitou calendario {ruim!r}")
    for ruim in ("Bot-X", "x y", "-x", "x/../y", "", "foo\n"):
        try:
            units.gera_unit({**decl, "slug": ruim})
        except ValueError:
            continue
        raise AssertionError(f"aceitou slug {ruim!r}")
    try:
        units.gera_unit({**decl, "trigger_tipo": "manual"})
    except ValueError:
        return
    raise AssertionError("gerou unit para gatilho manual")
