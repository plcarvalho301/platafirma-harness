"""#4084: `acervo consultar casa <pergunta>` — perguntas com nome sobre o schema casa, pela role busca.

O banco não entra no portão: um docker de mentira no PATH grava o argv e o stdin que o ato lhe passa,
e o que se prova é a rota, a lista fechada de perguntas, a role `busca` e o argumento indo por
variável do psql, fora do corpo do SQL. A recusa de escrita pela role busca se prova no banco, na
fita do card.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"
PERGUNTAS = ("onde-mora", "linhagem", "descendentes", "documento", "golden")

DOCKER_FALSO = r"""#!/usr/bin/env bash
if [ "$1" = inspect ]; then echo true; exit 0; fi
printf '%s\n' "$@" > "$DOCKER_LOG.argv"
cat > "$DOCKER_LOG.stdin"
echo " entidade "
echo "----------"
echo " guia"
echo "(1 row)"
"""


def _acervo(*argv, tmp_path: Path):
    bin_falso = tmp_path / "bin"
    bin_falso.mkdir(exist_ok=True)
    docker = bin_falso / "docker"
    docker.write_text(DOCKER_FALSO, encoding="utf-8")
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_falso}{os.pathsep}{os.environ.get('PATH', '')}",
           "DOCKER_LOG": str(tmp_path / "docker"), "PF_SESSAO_ID": f"t-consultar-{uuid.uuid4().hex}"}
    return subprocess.run(["bash", str(ACERVO), "consultar", *argv], capture_output=True, text=True,
                          env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)


def test_pergunta_fora_da_lista_sai_2_com_a_lista(tmp_path):
    r = _acervo("casa", "xyz", tmp_path=tmp_path)
    assert r.returncode == 2
    assert "pergunta xyz fora da lista" in r.stderr
    for p in PERGUNTAS:
        assert p in r.stderr, p
    assert not (tmp_path / "docker.argv").exists()


def test_sem_argumento_e_particao_errada_saem_2(tmp_path):
    assert _acervo(tmp_path=tmp_path).returncode == 2
    assert _acervo("biblioteca", "onde-mora", "guia", tmp_path=tmp_path).returncode == 2
    assert _acervo("casa", "onde-mora", tmp_path=tmp_path).returncode == 2
    assert _acervo("casa", "golden", "card", tmp_path=tmp_path).returncode == 2


def test_argumento_vai_por_variavel_e_nunca_no_sql(tmp_path):
    malicioso = "guia' OR 1=1; DROP TABLE casa.ficha; --"
    r = _acervo("casa", "onde-mora", malicioso, tmp_path=tmp_path)
    assert r.returncode == 0, r.stderr
    argv = (tmp_path / "docker.argv").read_text(encoding="utf-8").splitlines()
    sql = (tmp_path / "docker.stdin").read_text(encoding="utf-8")
    assert argv[argv.index("-U") + 1] == "busca"
    assert f"a1={malicioso}" in argv
    assert "default_transaction_read_only=on" in " ".join(argv)
    assert malicioso not in sql and "DROP" not in sql
    assert ":'a1'" in sql


def test_cada_pergunta_roda_uma_consulta_fixa(tmp_path):
    vistos = set()
    for p in PERGUNTAS:
        args = ("card", "3926") if p == "golden" else ("procedimento",)
        r = _acervo("casa", p, *args, tmp_path=tmp_path)
        assert r.returncode == 0, (p, r.stderr)
        sql = (tmp_path / "docker.stdin").read_text(encoding="utf-8")
        assert "casa." in sql
        assert not any(w in sql.upper() for w in ("INSERT", "UPDATE", "DELETE", "DROP")), p
        vistos.add(sql)
    assert len(vistos) == len(PERGUNTAS)


def test_cabecalho_declara_o_ato_como_leitura():
    cab = ACERVO.read_text(encoding="utf-8")
    assert "consultar (leitura, casa)" in cab
    assert "# escreve: consultar=nada" in cab
    assert "# capacidade-ato: consultar=leitura" in cab
