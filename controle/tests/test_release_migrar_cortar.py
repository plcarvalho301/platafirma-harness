"""release migrar cortar (DT 792): o corte de um schema entre bancos do registro.

O docker e falso: um script no PATH que responde ao `inspect`, conta as tabelas do schema
(a origem, o destino antes e o destino depois do restore), devolve um dump fixo ao pg_dump
e guarda o que o pg_restore recebeu. O teste confere que o dump vai a um arquivo da
instancia, entra no destino inteiro e nunca sai no stdout do verbo.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

MIGRAR = Path(__file__).resolve().parents[2] / "bin" / "_release" / "migrar"

DOCKER_FALSO = """#!/usr/bin/env bash
echo "$*" >> "$DIR/chamadas"
case "$1" in
  inspect) echo true; exit 0 ;;
esac
case " $* " in
  *" pg_dump "*) printf 'DUMP-DO-SCHEMA'; exit "${FALHA_DUMP:-0}" ;;
  *" createdb "*) exit 0 ;;
  *" pg_restore "*) cat > "$DIR/restaurado"; exit "${FALHA_RESTORE:-0}" ;;
  *"information_schema.tables"*)
    n=$(cat "$DIR/contagens" 2>/dev/null | wc -l)
    echo x >> "$DIR/contagens"
    if [ "$n" -eq 0 ]; then echo "$N_ORIGEM"
    elif [ -e "$DIR/restaurado" ]; then echo "${N_DEPOIS:-$N_ORIGEM}"
    else echo "${N_ANTES:-0}"; fi
    exit 0 ;;
esac
exit 0
"""


def _rodar(tmp_path: Path, *args: str, sujeito: bool = True, **extra: str):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    docker = bindir / "docker"
    docker.write_text(DOCKER_FALSO)
    docker.chmod(0o755)
    env = {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        "DIR": str(tmp_path),
        "N_ORIGEM": "7",
        **extra,
    }
    if sujeito:
        env["PF_SUJEITO"] = "teste"
    return subprocess.run(["bash", str(MIGRAR), "cortar", *args], capture_output=True, text=True, env=env)


def test_corta_para_outro_banco_e_conta_os_dois_lados(tmp_path):
    p = _rodar(tmp_path, "rag", "analise", "casa")
    assert p.returncode == 0, p.stderr
    assert "7 tabela(s) na origem, 7 no destino" in p.stdout
    dumps = list((tmp_path / "inst" / "var" / "cortes").glob("*-rag-analise.dump"))
    assert len(dumps) == 1
    assert stat.S_IMODE(dumps[0].stat().st_mode) == 0o600
    assert (tmp_path / "restaurado").read_text() == dumps[0].read_text() == "DUMP-DO-SCHEMA"
    assert "DUMP-DO-SCHEMA" not in p.stdout and "DUMP-DO-SCHEMA" not in p.stderr
    chamadas = (tmp_path / "chamadas").read_text()
    assert "--schema=analise -Fc" in chamadas
    assert "--exit-on-error -1" in chamadas


def test_rascunho_cria_base_nova_no_conteiner_da_origem(tmp_path):
    p = _rodar(tmp_path, "rag", "analise", "--rascunho")
    assert p.returncode == 0, p.stderr
    chamadas = (tmp_path / "chamadas").read_text()
    assert "createdb" in chamadas and "rascunho_analise_" in chamadas
    assert "rascunho_analise_" in p.stdout


def test_destino_com_tabela_no_schema_recusa_sem_dump(tmp_path):
    p = _rodar(tmp_path, "rag", "analise", "casa", N_ANTES="3")
    assert p.returncode == 4
    assert "nao sobrescreve" in p.stderr
    assert not (tmp_path / "restaurado").exists()


def test_contagem_divergente_sai_1(tmp_path):
    p = _rodar(tmp_path, "rag", "analise", "casa", N_DEPOIS="6")
    assert p.returncode == 1
    assert "contagem diverge" in p.stderr


def test_restore_abortado_sai_1_e_guarda_o_dump(tmp_path):
    p = _rodar(tmp_path, "rag", "analise", "casa", FALHA_RESTORE="1")
    assert p.returncode == 1
    assert "transacao nao commitou" in p.stderr


def test_entradas_invalidas(tmp_path):
    assert _rodar(tmp_path, "fora", "analise", "casa").returncode == 4
    assert _rodar(tmp_path, "rag", "analise", "fora").returncode == 4
    assert _rodar(tmp_path, "rag", "Analise;drop", "casa").returncode == 2
    assert _rodar(tmp_path, "rag", "analise", "rag").returncode == 2
    assert _rodar(tmp_path, "rag", "analise").returncode == 2
    assert _rodar(tmp_path, "rag", "analise", "casa", sujeito=False).returncode == 3
