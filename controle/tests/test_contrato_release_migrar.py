"""Contrato de `release migrar` (card #3260, arq:0076, arq:0110 Q9):
Sub-ato migrar do verbo release. Mesma contenção estrutural do antigo bin/migrar:
Q9 do cabeçalho (usage, --ajuda universal, ato desconhecido) e o mapeamento de exit por §4
(dependência ausente, banco fora da allowlist, falha de mérito do psql ao aplicar, identidade,
e ensaio de migração com linha de aborto saindo 1 sem gravar).

Roda bin/release migrar como subprocesso com PATH apontando para stubs controlados.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
RELEASE = REPO_RAIZ / "bin" / "release"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH — nao da pra rodar bin/release")


def _stub(diretorio, nome, corpo):
    caminho = diretorio / nome
    caminho.write_text(f"#!{BASH}\nset -euo pipefail\n" + corpo, encoding="utf-8", newline="\n")
    modo = caminho.stat().st_mode
    caminho.chmod(modo | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def _real(nome):
    p = shutil.which(nome)
    assert p, f"preciso de {nome} real no PATH do host para montar o stub"
    return p


def _stub_real(diretorio, nome):
    return _stub(diretorio, nome, f'exec "{_real(nome)}" "$@"\n')


def _roda(*args, path_dir=None, env_extra=None, stdin_data=None, checa_exit=None):
    env = dict(os.environ)
    env.pop("PF_SUJEITO", None)
    if path_dir is not None:
        env["PATH"] = str(path_dir)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        [BASH, str(RELEASE), "migrar", *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
        input=stdin_data, check=False,
    )
    if checa_exit is not None:
        assert r.returncode == checa_exit, (
            f"exit {r.returncode} != {checa_exit}\nstdout={r.stdout!r}\nstderr={r.stderr!r}"
        )
    return r


@pytest.fixture
def path_sem_docker(tmp_path):
    d = tmp_path / "sem-docker"
    d.mkdir()
    _stub_real(d, "readlink")
    _stub_real(d, "dirname")
    _stub_real(d, "basename")
    _stub_real(d, "head")
    _stub_real(d, "cat")
    _stub_real(d, "grep")
    return d


DOCKER_OK = """
case "$1" in
  inspect) echo "true"; exit 0 ;;
  exec)
    cat >/dev/null   # consome o SQL do stdin (a migracao)
    echo "NOTICE:  aceite ok" >&2
    exit 0 ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""

DOCKER_CTR_PARADO = """
case "$1" in
  inspect) echo "false"; exit 0 ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""

DOCKER_PSQL_FALHA = """
case "$1" in
  inspect) echo "true"; exit 0 ;;
  exec)
    cat >/dev/null
    echo "ERROR:  relation \\"x\\" does not exist" >&2
    exit 3 ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""

DOCKER_PSQL_ENSAIO_ABORTO = """
case "$1" in
  inspect) echo "true"; exit 0 ;;
  exec)
    conteudo=$(cat)
    if grep -q "ensaio: nada gravado" <<<"$conteudo"; then
      echo "NOTICE:  063 aceite: acervo.impressao.espelho existe" >&2
      echo "ERROR:  ensaio: nada gravado" >&2
      exit 3
    fi
    echo "NOTICE:  aceite ok" >&2
    exit 0 ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""


def _monta_path(tmp_path, nome, docker_corpo):
    d = tmp_path / nome
    d.mkdir()
    _stub_real(d, "readlink")
    _stub_real(d, "dirname")
    _stub_real(d, "basename")
    _stub_real(d, "head")
    _stub_real(d, "grep")
    _stub_real(d, "cat")
    _stub(d, "docker", docker_corpo)
    return d


@pytest.fixture
def path_ok(tmp_path):
    return _monta_path(tmp_path, "bin-ok", DOCKER_OK)


@pytest.fixture
def path_ctr_parado(tmp_path):
    return _monta_path(tmp_path, "bin-ctr-parado", DOCKER_CTR_PARADO)


@pytest.fixture
def path_psql_falha(tmp_path):
    return _monta_path(tmp_path, "bin-psql-falha", DOCKER_PSQL_FALHA)


@pytest.fixture
def path_ensaio_aborto(tmp_path):
    return _monta_path(tmp_path, "bin-ensaio-aborto", DOCKER_PSQL_ENSAIO_ABORTO)


@pytest.fixture
def path_delator(tmp_path):
    d = tmp_path / "delator"
    d.mkdir()
    _stub_real(d, "readlink")
    _stub_real(d, "dirname")
    _stub_real(d, "basename")
    _stub_real(d, "head")
    _stub_real(d, "cat")
    _stub(d, "docker", 'echo "DELATOR:docker chamado: $*" >&2\nexit 99\n')
    return d


def _sem_delator(r):
    assert "DELATOR:" not in r.stdout and "DELATOR:" not in r.stderr, (
        f"efeito colateral: {r.stdout!r} {r.stderr!r}"
    )


# --- Q2/Q9: usage, --ajuda, ato desconhecido ------------------------------

def test_release_migrar_sem_argumento_exit_2(path_delator):
    r = _roda(path_dir=path_delator, checa_exit=2)
    assert "uso:" in r.stderr
    assert "release migrar" in r.stderr
    _sem_delator(r)


@pytest.mark.parametrize("args", [
    ("--ajuda",), ("-h",), ("--help",), ("ajuda",),
    ("aplicar", "--ajuda"), ("bancos", "--ajuda"),
])
def test_release_migrar_ajuda_exit_2_em_qualquer_posicao_sem_efeito(path_delator, args):
    r = _roda(*args, path_dir=path_delator, checa_exit=2)
    assert "uso:" in r.stderr
    _sem_delator(r)


def test_release_migrar_ato_desconhecido_exit_2_com_lista(path_delator):
    r = _roda("bogus-ato", path_dir=path_delator, checa_exit=2)
    assert "release migrar: erro: ato desconhecido: bogus-ato" in r.stderr
    assert "atos: aplicar, bancos" in r.stderr
    _sem_delator(r)


# --- bancos: leitura, não exige PF_SUJEITO --------------------------------

def test_release_migrar_bancos_lista_sem_exigir_sujeito(path_delator):
    r = _roda("bancos", path_dir=path_delator, checa_exit=0)
    assert "rag" in r.stdout and "motor" in r.stdout and "sessao" in r.stdout
    _sem_delator(r)


# --- aplicar: identidade, allowlist, dependência, mérito ------------------

def test_release_aplicar_sem_banco_uso_exit_2(path_delator):
    r = _roda("aplicar", path_dir=path_delator, checa_exit=2)
    assert "falta o banco" in r.stderr


def test_release_aplicar_banco_fora_da_allowlist_exit_4(path_delator):
    r = _roda("aplicar", "banco-que-nao-existe", path_dir=path_delator, checa_exit=4)
    assert "fora da allowlist" in r.stderr
    _sem_delator(r)


def test_release_aplicar_sem_pf_sujeito_exit_3(path_ok):
    r = _roda("aplicar", "rag", path_dir=path_ok, stdin_data="select 1;\n", checa_exit=3)
    assert "PF_SUJEITO" in r.stderr


def test_release_aplicar_dependencia_docker_ausente_exit_3(path_sem_docker):
    r = _roda("aplicar", "rag", path_dir=path_sem_docker,
              env_extra={"PF_SUJEITO": "G48UFN"}, stdin_data="select 1;\n", checa_exit=3)
    assert "dependência" in r.stderr
    assert "docker" in r.stderr


def test_release_aplicar_conteiner_fora_do_ar_exit_3(path_ctr_parado):
    r = _roda("aplicar", "rag", path_dir=path_ctr_parado,
              env_extra={"PF_SUJEITO": "G48UFN"}, stdin_data="select 1;\n", checa_exit=3)
    assert "dependência" in r.stderr
    assert "rag-extractor-pg" in r.stderr


def test_release_aplicar_sucesso_chama_docker_exec_com_sujeito(path_ok):
    r = _roda("aplicar", "rag", path_dir=path_ok,
              env_extra={"PF_SUJEITO": "G48UFN"}, stdin_data="select 1;\n", checa_exit=0)
    assert "migracao aplicada em rag" in r.stderr
    assert "sujeito=G48UFN" in r.stderr


def test_release_aplicar_psql_abortou_exit_1(path_psql_falha):
    r = _roda("aplicar", "rag", path_dir=path_psql_falha,
              env_extra={"PF_SUJEITO": "G48UFN"}, stdin_data="select 1;\n", checa_exit=1)
    assert "psql abortou" in r.stderr


def test_release_aplicar_ensaio_linha_de_aborto_exit_1(path_ensaio_aborto):
    # Ensaio do guia ddl-e-migracao (passo 3): com linha de aborto no fim,
    # sai 1 sem gravar nada, acusando falha de mérito da transação.
    sql_ensaio = (
        "ALTER TABLE acervo.impressao ADD COLUMN IF NOT EXISTS espelho jsonb;\n"
        "DO $$ BEGIN RAISE NOTICE '063 aceite: acervo.impressao.espelho existe'; END $$;\n"
        "DO $$ BEGIN RAISE EXCEPTION 'ensaio: nada gravado'; END $$;\n"
    )
    r = _roda("aplicar", "rag", path_dir=path_ensaio_aborto,
              env_extra={"PF_SUJEITO": "G48UFN"}, stdin_data=sql_ensaio, checa_exit=1)
    assert "psql abortou" in r.stderr
