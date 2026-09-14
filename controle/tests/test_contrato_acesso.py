# test_contrato_acesso — contrato do verbo `acesso` (bin/acesso e bin/_acesso/desligar.py)
# Conforme spec_acesso.md (rev 1.3) §1 (gramática), §2 (regras comuns), §3 (formato),
# §4 (códigos de saída), §5 (cabeçalho Q1) e §6 (transição).
#
# Cobre os códigos de saída:
#   exit 0: PERMITIDO / conferência do PAP válida / sem órfãos
#   exit 1: NEGADO pela política / PAP inválido (erro de regra)
#   exit 2: uso inválido (forma antiga, falta de argumento, chave sem tipo, subcomando desconhecido)
#   exit 3: infraestrutura / PAP ausente / sintaxe corrompida
#   exit 5: medição incompleta / faltou atributo na projeção / realm não medido
#
# Atos que dependem de banco (conceder, revogar, listar) declaram @pytest.mark.skip
# na ausência do contêiner de banco de dados.
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ACESSO_BIN = REPO_ROOT / "bin" / "acesso"
POLITICA_ORIGINAL = REPO_ROOT / "politica-acesso"
DB_CONTAINER = os.environ.get("ACESSO_DB_CONTAINER", "platafirma-core-identidade-db-1")


def _docker_container_running(name: str) -> bool:
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and "true" in r.stdout.lower()
    except Exception:
        return False


TEM_BANCO = _docker_container_running(DB_CONTAINER)


def run_acesso(*args, env=None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    if "PF_SUJEITO" in e:
        del e["PF_SUJEITO"]
    if env:
        e.update(env)
    if "ACESSO_POLITICA_DIR" not in e:
        e["ACESSO_POLITICA_DIR"] = str(POLITICA_ORIGINAL)
    return subprocess.run(
        [str(ACESSO_BIN), *args],
        capture_output=True,
        text=True,
        env=e,
    )


# ==============================================================================
# §1 e §4: Decidir — Exit 0, 1, 2, 3, 5 e --json
# ==============================================================================

def test_decidir_permitido_exit_0():
    """Exit 0: ação permitida por regra explícita no PAP."""
    r = run_acesso(
        "decidir", "sessao_abrir", "sessao:fabrica",
        "--papel", "fornecedor", "--dominio", "plataforma",
    )
    assert r.returncode == 0
    assert "PERMITIDO" in r.stdout
    assert "fornecedor-abre-a-propria-sessao" in r.stdout


def test_decidir_negado_politica_exit_1():
    """Exit 1: negado pela política (nenhuma regra permite, ou regra nega)."""
    r = run_acesso(
        "decidir", "sessao_encerrar", "sessao:ia/x",
        "--papel", "fornecedor", "--dominio", "plataforma",
    )
    assert r.returncode == 1
    assert "NEGADO" in r.stdout
    assert "regra=default" in r.stdout


def test_decidir_uso_invalido_forma_antiga_exit_2():
    """Exit 2: uso da forma obsoleta --acao/--recurso/--tipo rejeitada com instrução da nova."""
    r = run_acesso("decidir", "--acao", "sessao_abrir", "--recurso", "sessao:fabrica", "--tipo", "sessao")
    assert r.returncode == 2
    assert "forma obsoleta --acao/--recurso/--tipo" in r.stderr


def test_decidir_uso_invalido_sem_prefixo_tipo_exit_2():
    """Exit 2: recurso sem prefixo <tipo>:<chave>."""
    r = run_acesso("decidir", "sessao_abrir", "sem_tipo", "--papel", "operador", "--dominio", "plataforma")
    assert r.returncode == 2
    assert "recurso sem prefixo de tipo" in r.stderr


def test_decidir_uso_invalido_sem_sujeito_exit_2():
    """Exit 2: sem PF_SUJEITO e sem --sujeito ou --papel/--dominio."""
    r = run_acesso("decidir", "sessao_abrir", "sessao:fabrica")
    assert r.returncode == 2
    assert "sem sujeito" in r.stderr


def test_decidir_pap_ausente_exit_3():
    """Exit 3: arquivo de política ausente no diretório apontado."""
    r = run_acesso(
        "decidir", "sessao_abrir", "sessao:fabrica",
        "--sujeito", "claudinho",
        env={"ACESSO_POLITICA_DIR": "/tmp/diretorio_inexistente_de_pap"},
    )
    assert r.returncode == 3
    assert "PAP servido ausente" in (r.stdout + r.stderr)


def test_decidir_pap_invalido_exit_3(tmp_path):
    """Exit 3: arquivo politica.yaml com sintaxe quebrada ou regra corrompida."""
    p_corrompida = tmp_path / "politica.yaml"
    p_corrompida.write_text("regras:\n  - id: regra_sem_efeito\n", encoding="utf-8")
    s_yaml = tmp_path / "sujeitos.yaml"
    s_yaml.write_text("versao: 1\nsujeitos: {}\n", encoding="utf-8")
    shutil.copy(POLITICA_ORIGINAL / "pdp.py", tmp_path / "pdp.py")

    r = run_acesso(
        "decidir", "sessao_abrir", "sessao:fabrica",
        "--sujeito", "claudinho",
        env={"ACESSO_POLITICA_DIR": str(tmp_path)},
    )
    assert r.returncode == 3
    assert "PAP servido inválido" in (r.stdout + r.stderr)


def test_decidir_faltou_atributo_projecao_exit_5():
    """Exit 5: sujeito não encontrado na projeção, faltam atributos essenciais."""
    r = run_acesso("decidir", "sessao_abrir", "sessao:fabrica", "--sujeito", "sujeito_desconhecido_123")
    assert r.returncode == 5
    assert "faltou: sujeito.papeis, sujeito.dominios" in r.stdout


def test_decidir_json_permitido_exit_0():
    """--json: objeto estruturado com permitido=True, regra, motivo, faltou, plano."""
    r = run_acesso(
        "decidir", "sessao_abrir", "sessao:fabrica",
        "--papel", "fornecedor", "--dominio", "plataforma",
        "--json",
    )
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["permitido"] is True
    assert d["regra"] == "fornecedor-abre-a-propria-sessao"
    assert d["acao"] == "sessao_abrir"
    assert d["recurso"] == "sessao:fabrica"
    assert d["faltou"] == []
    assert len(d["plano"]) == 8


def test_decidir_json_negado_exit_1():
    """--json: objeto estruturado com permitido=False quando negado pela política."""
    r = run_acesso(
        "decidir", "sessao_encerrar", "sessao:ia/x",
        "--papel", "fornecedor", "--dominio", "plataforma",
        "--json",
    )
    assert r.returncode == 1
    d = json.loads(r.stdout)
    assert d["permitido"] is False
    assert d["regra"] == "default"
    assert d["faltou"] == []


def test_decidir_json_faltou_exit_5():
    """--json: objeto estruturado com permitido=False e faltou=[...] no exit 5."""
    r = run_acesso("decidir", "sessao_abrir", "sessao:fabrica", "--sujeito", "sujeito_inexistente", "--json")
    assert r.returncode == 5
    d = json.loads(r.stdout)
    assert d["permitido"] is False
    assert "sujeito.papeis" in d["faltou"]
    assert "sujeito.dominios" in d["faltou"]


def test_decidir_json_erro_exit_2():
    """--json: erro de sintaxe devolve objeto com erro no stdout."""
    r = run_acesso("decidir", "sessao_abrir", "sessao:fabrica", "--json")
    assert r.returncode == 2
    d = json.loads(r.stdout)
    assert "erro" in d


def test_decidir_json_erro_exit_3():
    """--json: falha de infraestrutura devolve erro formatado."""
    r = run_acesso(
        "decidir", "sessao_abrir", "sessao:fabrica",
        "--sujeito", "claudinho", "--json",
        env={"ACESSO_POLITICA_DIR": "/tmp/nao-existe"},
    )
    assert r.returncode == 3
    d = json.loads(r.stdout)
    assert "erro" in d


# ==============================================================================
# Subcomando `politica`: conferir e validação
# ==============================================================================

def test_politica_conferir_valido_exit_0():
    """acesso politica conferir no PAP servido válido devolve 0."""
    r = run_acesso("politica", "conferir")
    assert r.returncode == 0
    assert "politica valida" in r.stdout


def test_politica_conferir_ausente_exit_3():
    """acesso politica conferir em diretório sem politica.yaml devolve 3."""
    r = run_acesso("politica", "conferir", env={"ACESSO_POLITICA_DIR": "/tmp/sem_politica"})
    assert r.returncode == 3
    assert "PAP ausente" in r.stderr


def test_politica_conferir_invalido_exit_1(tmp_path):
    """acesso politica conferir com regras inválidas devolve 1 identificando a linha."""
    p_corrompida = tmp_path / "politica.yaml"
    p_corrompida.write_text("regras:\n  - id: regra_sem_nada\n", encoding="utf-8")
    shutil.copy(POLITICA_ORIGINAL / "pdp.py", tmp_path / "pdp.py")

    r = run_acesso("politica", "conferir", env={"ACESSO_POLITICA_DIR": str(tmp_path)})
    assert r.returncode == 1
    assert "política inválida" in r.stderr


# ==============================================================================
# Subcomando `orfaos`: medição e exit 5
# ==============================================================================

def test_orfaos_sem_realm_exit_5():
    """acesso orfaos --sem-realm declara realm não medido e devolve exit 5."""
    r = run_acesso("orfaos", "--sem-realm")
    assert r.returncode == 5
    assert "NAO MEDIDO (--sem-realm)" in r.stdout
    assert "exit 5 (medicao incompleta)" in r.stdout


def test_subcomando_desconhecido_exit_2():
    """Subcomando inválido devolve 2."""
    r = run_acesso("subcomando_inexistente")
    assert r.returncode == 2
    assert "subcomando desconhecido" in r.stderr


# ==============================================================================
# Atos que dependem de banco de dados (conceder, revogar, listar)
# ==============================================================================

@pytest.mark.skipif(not TEM_BANCO, reason="exige contêiner de banco de dados identidade rodando")
def test_conceder_com_banco():
    r = run_acesso("conceder", "claudinho", "papel", "operador", "--fundamento", "concessao de teste valida")
    assert r.returncode in (0, 1)


@pytest.mark.skipif(not TEM_BANCO, reason="exige contêiner de banco de dados identidade rodando")
def test_revogar_com_banco():
    r = run_acesso("revogar", "claudinho", "papel", "operador", "--fundamento", "revogacao de teste valida")
    assert r.returncode in (0, 1)


@pytest.mark.skipif(not TEM_BANCO, reason="exige contêiner de banco de dados identidade rodando")
def test_listar_com_banco():
    r = run_acesso("listar")
    assert r.returncode == 0
