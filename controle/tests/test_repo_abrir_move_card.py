# componente: componente:verbo-repo
"""Cobertura dos DTs 80, 95, 407 e 451 em bin/repo (abrir / move_card)."""

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"


def _cria_fake_tarefas(tmp_path: Path, itens: dict[str, dict]) -> tuple[Path, Path]:
    log_path = tmp_path / "tarefas_calls.log"
    itens_path = tmp_path / "itens.json"
    itens_path.write_text(json.dumps(itens), encoding="utf-8")
    script = tmp_path / "fake_tarefas.sh"
    script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "api" ] && [ "$2" = "GET" ]; then
  id="${{3#/itens/}}"
  python3 -c 'import sys, json; d = json.load(open(sys.argv[1])); print(json.dumps(d.get(sys.argv[2], {{}})))' "{itens_path}" "$id"
  exit 0
fi
printf '%s\\n' "$*" >> "{log_path}"
exit 0
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script, log_path


def _prepara_ambiente(tmp_path: Path, itens: dict[str, dict], repo_nome: str = "demo"):
    bancada = tmp_path / "bancada"
    origin = tmp_path / "origins" / f"{repo_nome}.git"
    seed = tmp_path / "seed"
    origin.parent.mkdir(parents=True)
    seed.mkdir(parents=True)

    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "-C", str(seed), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(seed), "config", "user.name", "Teste"], check=True)
    subprocess.run(["git", "-C", str(seed), "config", "user.email", "t@example.com"], check=True)
    (seed / "README.md").write_text("ok\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(seed), "add", "."], check=True)
    subprocess.run(["git", "-C", str(seed), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(seed), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q", "origin", "main"], check=True)

    bancada.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(bancada / repo_nome)], check=True)

    fake_tarefas, log_path = _cria_fake_tarefas(tmp_path, itens)
    env = os.environ.copy()
    env["PLATAFIRMA_BANCADA"] = str(bancada)
    env["PF_CADEIRA"] = "engenharia"
    env["PF_TAREFAS_BIN"] = str(fake_tarefas)
    return env, log_path


def _roda(env, *args):
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_dt80_nao_move_outra_cadeira_homologacao_ou_entregue(tmp_path):
    itens = {
        "101": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "priorizada",
            "estado_fase": "funil",
            "cadeira": "dados",
            "executor": "",
        },
        "102": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "em-homologacao",
            "estado_fase": "delivery",
            "cadeira": "engenharia",
            "executor": "engenharia",
        },
        "103": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "entregue",
            "estado_fase": "terminal",
            "cadeira": "engenharia",
            "executor": "engenharia",
        },
    }
    env, log_path = _prepara_ambiente(tmp_path, itens)

    r1 = _roda(env, "abrir", "demo", "101")
    assert r1.returncode == 0, r1.stderr
    assert "card #101: nao movido (cadeira do card e dados, sessao e engenharia)" in r1.stdout

    r2 = _roda(env, "abrir", "demo", "102")
    assert r2.returncode == 0, r2.stderr
    assert "card #102: mantido em em-homologacao" in r2.stdout

    r3 = _roda(env, "abrir", "demo", "103")
    assert r3.returncode == 0, r3.stderr
    assert "card #103: nao movido (estado terminal entregue)" in r3.stdout

    assert not log_path.exists()


def test_dt95_sem_mover_nao_toca_card_inclusive_direto_em_main(tmp_path):
    itens = {
        "3194": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "em-refinamento-tecnico",
            "estado_fase": "delivery",
            "cadeira": "engenharia",
            "executor": "engenharia",
        }
    }
    env, log_path = _prepara_ambiente(tmp_path, itens, repo_nome="platafirma-casa")

    r = _roda(env, "abrir", "platafirma-casa", "3194", "--sem-mover")
    assert r.returncode == 0, r.stderr
    assert "card #3194: nao movido (--sem-mover)" in r.stdout
    assert not log_path.exists()


def test_dt407_e_dt451_nao_move_incidente_nem_recua_em_execucao(tmp_path):
    itens = {
        "4008": {
            "classe": "incidente",
            "nivel_nome": None,
            "estado": "detectado",
            "estado_fase": "incidente",
            "cadeira": "engenharia",
            "executor": "engenharia",
        },
        "4084": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "em-execucao",
            "estado_fase": "delivery",
            "cadeira": "engenharia",
            "executor": "engenharia",
        },
    }
    env, log_path = _prepara_ambiente(tmp_path, itens)

    r_inc = _roda(env, "abrir", "demo", "4008")
    assert r_inc.returncode == 0, r_inc.stderr
    assert "card #4008: nao movido (incidente nao move em abrir)" in r_inc.stdout

    r_exec = _roda(env, "abrir", "demo", "4084")
    assert r_exec.returncode == 0, r_exec.stderr
    assert "card #4084: mantido em em-execucao" in r_exec.stdout

    assert not log_path.exists()


def test_abrir_avanca_story_priorizada_da_propria_cadeira(tmp_path):
    itens = {
        "500": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "priorizada",
            "estado_fase": "funil",
            "cadeira": "engenharia",
            "executor": "",
        }
    }
    env, log_path = _prepara_ambiente(tmp_path, itens)

    r = _roda(env, "abrir", "demo", "500")
    assert r.returncode == 0, r.stderr
    assert "card #500: executor engenharia" in r.stdout
    assert "card #500: em-refinamento-tecnico" in r.stdout

    calls = log_path.read_text(encoding="utf-8").splitlines()
    assert calls == [
        "editar 500 --executor engenharia",
        "mover 500 em-refinamento-tecnico",
    ]


def test_dt741_abrir_direto_em_main_move_para_em_refinamento_tecnico(tmp_path):
    """DT 741: repo abrir em repo direto_em_main (platafirma-casa e platafirma-casa-espelho)
    move story priorizada para em-refinamento-tecnico, nao para em-execucao."""
    itens = {
        "4295": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "priorizada",
            "estado_fase": "funil",
            "cadeira": "engenharia",
            "executor": "",
        },
        "4304": {
            "classe": "planejado",
            "nivel_nome": "story",
            "estado": "priorizada",
            "estado_fase": "funil",
            "cadeira": "engenharia",
            "executor": "",
        },
    }
    env_espelho, log_espelho = _prepara_ambiente(
        tmp_path / "espelho", itens, repo_nome="platafirma-casa-espelho"
    )
    r_esp = _roda(env_espelho, "abrir", "platafirma-casa-espelho", "4295")
    assert r_esp.returncode == 0, r_esp.stderr
    assert "card #4295: em-refinamento-tecnico" in r_esp.stdout
    assert log_espelho.read_text(encoding="utf-8").splitlines() == [
        "editar 4295 --executor engenharia",
        "mover 4295 em-refinamento-tecnico",
    ]

    env_casa, log_casa = _prepara_ambiente(
        tmp_path / "casa", itens, repo_nome="platafirma-casa"
    )
    r_casa = _roda(env_casa, "abrir", "platafirma-casa", "4304")
    assert r_casa.returncode == 0, r_casa.stderr
    assert "card #4304: em-refinamento-tecnico" in r_casa.stdout
    assert log_casa.read_text(encoding="utf-8").splitlines() == [
        "editar 4304 --executor engenharia",
        "mover 4304 em-refinamento-tecnico",
    ]
