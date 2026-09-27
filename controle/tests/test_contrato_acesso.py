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
# O registro de identidade (banco) nunca e o real: o caso que chega ao banco poe um
# `docker` de fixture no PATH (conftest: teste nao le estado real).
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ACESSO_BIN = REPO_ROOT / "bin" / "acesso"
POLITICA_ORIGINAL = REPO_ROOT / "politica-acesso"


def _docker_de_fixture(tmp_path, corpo):
    d = tmp_path / "bin-docker"
    d.mkdir()
    p = d / "docker"
    p.write_text("#!/bin/sh\n" + corpo)
    p.chmod(0o755)
    return {"PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}


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
        "decidir", "sessao_abrir", "sessao:engenharia",
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
        "decidir", "sessao_abrir", "sessao:engenharia",
        "--papel", "fornecedor", "--dominio", "plataforma",
        "--json",
    )
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["permitido"] is True
    assert d["regra"] == "fornecedor-abre-a-propria-sessao"
    assert d["acao"] == "sessao_abrir"
    assert d["recurso"] == "sessao:engenharia"
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

def test_conceder_sem_sujeito_exit_3():
    """Exit 3: conceder sem PF_SUJEITO nao chega ao banco. Ato de ESTADO nunca se testa
    contra o registro vivo (gravaria concessao real); o contrato provavel sem banco e o
    que vem ANTES dele: uso, fundamento e autor."""
    r = run_acesso("conceder", "claudinho", "papel", "operador", "--fundamento", "concessao de teste valida")
    assert r.returncode == 3
    assert "sem sujeito" in r.stderr

def test_conceder_fundamento_trivial_exit_2():
    r = run_acesso("conceder", "claudinho", "papel", "operador", "--fundamento", "curto")
    assert r.returncode == 2


def test_revogar_sem_uuid_exit_2():
    r = run_acesso("revogar", "nao-e-uuid", "--fundamento", "revogacao de teste valida")
    assert r.returncode == 2

def test_revogar_sem_sujeito_exit_3():
    r = run_acesso("revogar", "00000000-0000-4000-8000-000000000000", "--fundamento", "revogacao de teste valida")
    assert r.returncode == 3
    assert "sem sujeito" in r.stderr

# ==============================================================================
# Transicao: id de recurso em duas formas — NEGATIVA VENCE nas duas; projecao = a do PEP
# ==============================================================================

def test_decidir_negativa_vence_na_forma_nua():
    """`comando:docker ps` casa a negativa `fornecedor-sem-estado-do-host` so na forma nua;
    o veredito tem de citar ESSA regra, nao o default."""
    r = run_acesso("decidir", "run_command", "comando:docker ps", "--papel", "fornecedor", "--dominio", "plataforma-runtime")
    assert r.returncode == 1
    assert "regra=fornecedor-sem-estado-do-host" in r.stdout

def test_decidir_permissao_na_forma_nua():
    r = run_acesso("decidir", "run_command", "comando:git status", "--papel", "fornecedor", "--dominio", "plataforma-runtime")
    assert r.returncode == 0
    assert "regra=fornecedor-le-repo" in r.stdout

def test_decidir_projecao_e_a_do_pep():
    """`--sujeito` casa so a chave da tabela, como a porta. A conta da fabrica e chaveada
    so pelo `sub` desde 22/09/2026 (sujeitos.yaml): o username nao projeta, e isso e medido."""
    r = run_acesso("decidir", "sessao_abrir", "sessao:engenharia", "--sujeito", "jaiminho-fabrica")
    assert r.returncode == 5
    r2 = run_acesso("decidir", "sessao_abrir", "sessao:engenharia", "--sujeito", "e57eadb1-ec5d-41b5-a1be-e6d62196cff5")
    assert r2.returncode == 0

def test_decidir_argumento_nao_vira_codigo():
    """Acao com aspas e ponto-e-virgula chega ao PDP como texto: exit 1 (default), sem traceback."""
    r = run_acesso("decidir", "x'; import os; os.system('id') #", "sessao:fabrica", "--papel", "fornecedor", "--dominio", "plataforma")
    assert r.returncode == 1
    assert "Traceback" not in r.stderr


# ==============================================================================
# Regressao 26/09/2026: a conta da fabrica abre na cadeira que EXISTE
# ==============================================================================
# A cadeira `fabrica` saiu na reconformacao e o PAP seguiu nomeando `sessao:fabrica`:
# `monta_sessao(cadeira="engenharia")` voltou 403 regra=default. Estes testes amarram o
# recurso das tres regras de abertura do fornecedor a uma cadeira servida.
# Sujeito pelo `sub`, a unica chave da conta em sujeitos.yaml desde 22/09/2026.
FABRICA_SUB = "e57eadb1-ec5d-41b5-a1be-e6d62196cff5"

# `monta_sessao` a porta submete como tipo documento: `documento:sessao:<cadeira>`.
@pytest.mark.parametrize("acao,recurso", [
    ("monta_sessao", "documento:sessao:engenharia"),
    ("sessao_abrir", "sessao:engenharia"),
    ("expediente_montar", "expediente:engenharia"),
])
def test_fornecedor_abre_na_cadeira_engenharia(acao, recurso):
    r = run_acesso("decidir", acao, recurso, "--sujeito", FABRICA_SUB)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PERMITIDO" in r.stdout


@pytest.mark.parametrize("acao,recurso", [
    ("monta_sessao", "documento:sessao:ia"),
    ("monta_sessao", "documento:sessao:fabrica"),
    ("sessao_abrir", "sessao:seguranca"),
    ("expediente_montar", "expediente:ti"),
])
def test_fornecedor_nao_abre_cadeira_alheia(acao, recurso):
    r = run_acesso("decidir", acao, recurso, "--sujeito", FABRICA_SUB)
    assert r.returncode == 1
    assert "regra=default" in r.stdout


def test_pap_nao_nomeia_cadeira_inexistente():
    """Todo `sessao:<cadeira>` e `expediente:<cadeira>` citado em regra e cadeira de abertura/."""
    import re
    import yaml
    pap = yaml.safe_load((POLITICA_ORIGINAL / "politica.yaml").read_text(encoding="utf-8"))
    cadeiras = {p.name for p in (REPO_ROOT / "abertura").iterdir() if p.is_dir()} if (REPO_ROOT / "abertura").is_dir() else None
    if not cadeiras:
        pytest.skip("abertura/ sem cadeiras nesta arvore")
    citadas = set()
    for regra in pap.get("regras", []):
        for alvo in regra.get("sobre", []):
            m = re.match(r"^(?:sessao|expediente):([a-z0-9-]+)(?:/|$)", alvo)
            if m and m.group(1) != "*":
                citadas.add(m.group(1))
    assert citadas <= cadeiras, f"PAP cita cadeira que nao existe: {sorted(citadas - cadeiras)}"


def test_listar_devolve_o_que_o_registro_responde(tmp_path):
    env = _docker_de_fixture(tmp_path, 'echo "G48UFN|papel|operador|concessao||ato-1"\n')
    r = run_acesso("listar", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "G48UFN" in r.stdout


def test_listar_registro_fora_do_ar_exit_3(tmp_path):
    env = _docker_de_fixture(tmp_path, 'echo "Error: No such container" >&2; exit 1\n')
    r = run_acesso("listar", env=env)
    assert r.returncode == 3
    assert "registro fora do ar" in r.stderr
