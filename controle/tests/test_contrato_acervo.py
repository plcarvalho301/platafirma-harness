# Contrato de `acervo` (bin/acervo) — arq:0110 / spec_acervo
#
# Só o que o cliente decide sozinho: gramática, recusas, cabeçalho, aviso de deprecado,
# e a resposta honesta quando o registro não responde. Nada aqui lê o banco nem o cânone
# reais (conftest: teste não lê estado real). O que o acervo SERVE — schema migrado,
# quantas ADRs há, que obra existe, qual chave está retirada — é estado de produção e
# se confere, não se testa.
import os
import shutil
import subprocess

import pytest

# `teste <verbo>` mede a REV (arq:0110 §9): o bin do repo, nao a copia servida no PATH.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "bin", "acervo")


def _acervo(*args, env=None):
    return subprocess.run([BIN, *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def _docker_de_fixture(tmp_path, corpo):
    d = tmp_path / "bin-docker"
    d.mkdir()
    p = d / "docker"
    p.write_text("#!/bin/sh\n" + corpo)
    p.chmod(0o755)
    return {"PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}


# --- gramática e recusas -------------------------------------------------------

def test_acervo_usage_sem_argumento():
    r = _acervo()
    assert r.returncode == 2
    assert "uso" in r.stderr.lower()


def test_acervo_ajuda():
    r = _acervo("--ajuda")
    assert r.returncode == 2
    assert "uso" in r.stderr.lower()


def test_acervo_ato_desconhecido():
    r = _acervo("ato_inventado_xyz")
    assert r.returncode == 2
    assert "desconhecido" in r.stderr.lower()


def test_identidade_adr_forma_invalida():
    # arq:11O tem 'O' maiúsculo no lugar de zero: o cliente recusa pela forma, antes do banco
    r = _acervo("ler", "casa", "adr", "arq:11O")
    assert r.returncode == 2
    assert "invalido" in r.stderr
    assert "Forma esperada" in r.stderr
    r_res = _acervo("resolver", "adr", "arq:11O")
    assert r_res.returncode == 2
    assert "invalido" in r_res.stderr


def test_escrever_recusa_de_fronteira():
    r = _acervo("escrever", "casa", "adr", "x")
    assert r.returncode == 2
    assert "adr nasce em git, não se escreve no acervo." in r.stderr
    assert ("Caminho: write_file na bancada de platafirma-casa → PR → merge em main → "
            "acervo ingerir casa platafirma-casa.") in r.stderr
    assert "escrever grava só: pagina, arquivo, ferramental, stack." in r.stderr


# --- registro fora do ar: nunca «0 linhas», nunca conforme ---------------------

@pytest.mark.parametrize("args", [
    ("ler", "casa", "adr", "arq:0110"),
    ("listar", "casa", "adr"),
    ("listar", "obra", "obra", "--sobre", "qualquer"),
])
def test_registro_fora_do_ar_nao_responde_vazio(tmp_path, args):
    env = _docker_de_fixture(tmp_path, 'echo "Error: No such container" >&2; exit 1\n')
    r = _acervo(*args, env=env)
    assert r.returncode in (3, 5), r.stdout + r.stderr
    assert "0 linha" not in r.stdout


# --- despachante, cabeçalho Q1 e conferência -----------------------------------

def test_camada_d_cabecalho_q1():
    with open(BIN, "r", encoding="utf-8") as f:
        lines = [f.readline() for _ in range(15)]
    text = "".join(lines)
    assert "# capacidade: conhecimento" in text
    assert "# dono: dados" in text
    assert "# classe: B" in text
    with open(BIN, "r", encoding="utf-8") as f:
        text = "".join(f.readline() for _ in range(45))
    # acesso e POR ATO: uma linha `# le:`/`# escreve:` para cada um dos oito atos
    for ato in ("ler", "listar", "resolver", "escrever", "ingerir", "curar", "extrato", "psql"):
        assert f"# le: {ato}=" in text
        assert f"# escreve: {ato}=" in text
    # ato que escreve declara escrita (Q12): psql escreve, logo nao e 'leitura'
    assert "psql (escrita, acervo)" in text
    assert "# escreve: ler=nada" in text
    assert "# consome: motor_acervo_rest, rag_extractor_pg" in text


def test_camada_d_recusa_adr_deprecado():
    r = _acervo("adr", "0110")
    assert r.returncode == 2
    assert "acervo adr: ato deprecado e removido" in r.stderr
    assert "acervo ler casa adr" in r.stderr


def test_camada_d_recusa_ato_desconhecido():
    r = _acervo("ato_inexistente")
    assert r.returncode == 2
    assert "acervo: ato 'ato_inexistente' desconhecido" in r.stderr
    assert "Atos canonicos: ler, listar, resolver, escrever, ingerir, curar, extrato, exportar, psql" in r.stderr


def test_camada_d_aviso_uma_vez_por_sessao():
    sess_id = f"test-sess-{os.getpid()}"
    env = {"PF_SESSAO_ID": sess_id}
    r1 = _acervo("bancada", "obra", "lote", env=env)
    assert "acervo: `acervo bancada` e a forma vigente" in r1.stderr
    r2 = _acervo("bancada", "obra", "lote", env=env)
    assert "acervo: `acervo bancada` e a forma vigente" not in r2.stderr
    shutil.rmtree(f"/tmp/platafirma-avisos-{sess_id}", ignore_errors=True)
