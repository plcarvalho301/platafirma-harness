# componente: componente:verbo-infra
"""Testes de `infra backup rodar` (DT 932) e `infra backup restaurar` (DT 931)."""
from __future__ import annotations

import gzip
import json
import os
import stat
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BACKUP_PY = RAIZ / "bin" / "_infra" / "backup.py"
REG_REAL = RAIZ / "registro" / "backups.json"


def _rodar(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(BACKUP_PY), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _escrever_gz(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(caminho, "wt", encoding="utf-8") as gz:
        gz.write(texto)


def test_registro_real_declara_script_e_restauracao_nos_alvos_com_cobertura():
    reg = json.loads(REG_REAL.read_text(encoding="utf-8"))
    com_cobertura = [
        nome
        for nome, a in reg["alvos"].items()
        if a.get("cobertura") != "nenhuma" and a.get("alcance") != "fora"
    ]
    assert len(com_cobertura) == 7
    for nome in com_cobertura:
        a = reg["alvos"][nome]
        assert a.get("script"), f"{nome} sem script declarado"
        assert isinstance(a.get("restauracao"), dict) and a["restauracao"].get("tipo"), f"{nome} sem restauracao"


def test_dt_932_backup_rodar_dispara_script_e_confere_geracao(tmp_path: Path):
    backups_dir = tmp_path / "backups" / "casa"
    backups_dir.mkdir(parents=True)
    release_dir = tmp_path / "release"
    script = release_dir / "conhecimento" / "casa-db" / "backup-db.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
python3 -c '
import gzip, pathlib
p = pathlib.Path("{backups_dir}/casa-20261120-120000.sql.gz")
with gzip.open(p, "wt") as gz:
    gz.write("-- dump\\n" + ("SELECT 1;\\n" * 400) + "-- PostgreSQL database dump complete\\n")
'
echo "OK gerado"
""",
        encoding="utf-8",
    )
    # propositalmente sem +x para garantir que roda mesmo assim (caso do card #4402)
    reg_path = tmp_path / "backups.json"
    reg_path.write_text(
        json.dumps(
            {
                "alvos": {
                    "casa-db": {
                        "o_que": "casa",
                        "cobertura": "cron",
                        "diretorio": str(backups_dir),
                        "padrao": "casa-*.sql.gz",
                        "piso_bytes": 50,
                        "alcance": "aqui",
                        "script": "conhecimento/casa-db/backup-db.sh",
                    },
                    "sem-cob": {"o_que": "x", "cobertura": "nenhuma", "alcance": "aqui"},
                }
            }
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "INFRA_BACKUPS_REG": str(reg_path), "PLATAFIRMA_RELEASE": str(release_dir)}

    r_ok = _rodar(["rodar", "casa-db", "--json"], env)
    assert r_ok.returncode == 0, r_ok.stderr
    dados = json.loads(r_ok.stdout)
    assert dados["estado"] == "ok" and dados["geracao_nova"] is True
    assert dados["ultimo"] == "casa-20261120-120000.sql.gz"

    assert _rodar(["rodar"], env).returncode == 2
    assert _rodar(["rodar", "inexistente"], env).returncode == 1
    assert _rodar(["rodar", "sem-cob"], env).returncode == 4


def test_dt_931_restaurar_postgres_mariadb_minio_e_arquivo_gz(tmp_path: Path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir()
    log_chamadas = tmp_path / "chamadas.log"

    docker_falso = bin_falso / "docker"
    docker_falso.write_text(
        f"""#!/usr/bin/env bash
echo "docker $*" >> "{log_chamadas}"
if [ "$1" = "ps" ]; then
  echo "ctr-123"
  exit 0
fi
if echo "$*" | grep -q "information_schema.tables"; then
  echo "12"
  exit 0
fi
cat >/dev/null
exit 0
""",
        encoding="utf-8",
    )
    docker_falso.chmod(docker_falso.stat().st_mode | stat.S_IXUSR)

    mc_falso = bin_falso / "mc"
    mc_falso.write_text(
        f"""#!/usr/bin/env bash
echo "mc $*" >> "{log_chamadas}"
if [ "$1" = "ls" ]; then
  echo "[2026-11-20] 10B obj1"
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    mc_falso.chmod(mc_falso.stat().st_mode | stat.S_IXUSR)

    pg_dir = tmp_path / "b_pg"
    _escrever_gz(pg_dir / "casa-20261120.sql.gz", ("SELECT 1;\n" * 100) + "-- PostgreSQL database dump complete\n")
    _escrever_gz(pg_dir / "casa-quebrado.sql.gz", "SELECT 1;\n")

    maria_dir = tmp_path / "b_maria"
    _escrever_gz(maria_dir / "wiki-20261120.sql.gz", ("SELECT 1;\n" * 100) + "-- Dump completed on 2026-11-20\n")

    minio_dir = tmp_path / "b_minio"
    (minio_dir / "acervo").mkdir(parents=True)
    (minio_dir / "acervo" / "abc").write_text("conteudo", encoding="utf-8")

    esc_dir = tmp_path / "b_esc"
    _escrever_gz(esc_dir / "escapes-do-dono-20261120.jsonl.gz", '{"id": 1}\n')
    _escrever_gz(esc_dir / "escapes-do-dono-ruim.jsonl.gz", "nao-e-json\n")

    instancia = tmp_path / "instancia"
    reg_path = tmp_path / "backups.json"
    reg_path.write_text(
        json.dumps(
            {
                "alvos": {
                    "casa-db": {
                        "cobertura": "cron",
                        "alcance": "aqui",
                        "diretorio": str(pg_dir),
                        "padrao": "casa-*.sql.gz",
                        "piso_bytes": 40,
                        "restauracao": {"tipo": "postgres", "conteiner": "casa-db", "schema": "casa"},
                    },
                    "conhecimento-db": {
                        "cobertura": "cron",
                        "alcance": "aqui",
                        "diretorio": str(maria_dir),
                        "padrao": "*.sql.gz",
                        "piso_bytes": 40,
                        "restauracao": {"tipo": "mariadb", "projeto": "plataforma-wiki", "servico": "db"},
                    },
                    "rag-minio": {
                        "cobertura": "cron",
                        "alcance": "aqui",
                        "diretorio": str(minio_dir),
                        "padrao": "*",
                        "restauracao": {"tipo": "minio-mirror", "buckets": ["acervo", "pessoal"]},
                    },
                    "escapes-do-dono": {
                        "cobertura": "cron",
                        "alcance": "aqui",
                        "diretorio": str(esc_dir),
                        "padrao": "escapes-do-dono-*.jsonl.gz",
                        "restauracao": {"tipo": "arquivo-gz", "destino": "var/esteira/escapes-do-dono.jsonl"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    env_base = {
        **os.environ,
        "PATH": f"{bin_falso}:{os.environ.get('PATH', '')}",
        "INFRA_BACKUPS_REG": str(reg_path),
        "PLATAFIRMA_INSTANCIA": str(instancia),
        "MC_BIN": str(mc_falso),
    }
    env_sem_suj = {k: v for k, v in env_base.items() if k != "PF_SUJEITO"}
    env_com_suj = {**env_sem_suj, "PF_SUJEITO": "sujeito-teste"}

    # Sem PF_SUJEITO: --ensaio passa (0), mutação recusa (3)
    assert _rodar(["restaurar", "casa-db", "casa-20261120.sql.gz", "--ensaio", "--json"], env_sem_suj).returncode == 0
    assert _rodar(["restaurar", "casa-db", "casa-20261120.sql.gz"], env_sem_suj).returncode == 3

    # Dump sem rodapé ou path traversal recusa antes de tocar no destino
    assert _rodar(["restaurar", "casa-db", "casa-quebrado.sql.gz"], env_com_suj).returncode == 1
    assert _rodar(["restaurar", "casa-db", "../etc/passwd"], env_com_suj).returncode == 4

    # Postgres, MariaDB, MinIO e arquivo-gz restauram e conferem conteúdo
    r_pg = _rodar(["restaurar", "casa-db", "casa-20261120.sql.gz", "--json"], env_com_suj)
    assert r_pg.returncode == 0, r_pg.stderr
    assert json.loads(r_pg.stdout)["tabelas"] == 12

    r_maria = _rodar(["restaurar", "conhecimento-db", "--json"], env_com_suj)
    assert r_maria.returncode == 0, r_maria.stderr
    assert json.loads(r_maria.stdout)["estado"] == "restaurado"

    r_minio = _rodar(["restaurar", "rag-minio", "--json"], env_com_suj)
    assert r_minio.returncode == 0, r_minio.stderr
    assert json.loads(r_minio.stdout)["buckets"]["acervo"] == 1

    r_esc = _rodar(["restaurar", "escapes-do-dono", "escapes-do-dono-20261120.jsonl.gz", "--json"], env_com_suj)
    assert r_esc.returncode == 0, r_esc.stderr
    assert (instancia / "var/esteira/escapes-do-dono.jsonl").read_text(encoding="utf-8") == '{"id": 1}\n'

    # JSONL inválido recusa sem sobrescrever destino
    assert _rodar(["restaurar", "escapes-do-dono", "escapes-do-dono-ruim.jsonl.gz"], env_com_suj).returncode == 1
    assert (instancia / "var/esteira/escapes-do-dono.jsonl").read_text(encoding="utf-8") == '{"id": 1}\n'
