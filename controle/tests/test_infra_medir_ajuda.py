"""`infra medir`: o cabeçalho (face, rótulo e volta), a ajuda e o despacho para o ato de eixo (spec eixos-do-host
R1; arq:0124 §3; card #3919).

bin/infra é copiado para uma árvore isolada com um `medir-rede` de mentira ao lado, como o contrato do
`infra limpeza` faz (test_contrato_infra.py): prova o despacho e a passagem do código de saída sem depender do
cloudflared, do systemd nem do docker. O ato de verdade tem a suíte própria (test_infra_medir_rede.py).
"""
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
INFRA = REPO_RAIZ / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH — nao da pra rodar bin/infra")

# A gramática de linha de ato do conferidor de verbo (bin/_release/conferir/conferir.py:_RE_LINHA_DE_ATO).
_LINHA_DE_ATO = re.compile(r"^#\s*(face|rotulo|volta|atalho)\s*:\s*([A-Za-z0-9_-]+(?:\s+--[A-Za-z0-9_-]+)?)\s*=\s*(.*?)\s*$")

FAKE_MEDIR = """
printf 'MEDIR_REDE:'
for a in "$@"; do printf ' [%s]' "$a"; done
printf '\\n'
exit "${FAKE_SAIDA:-0}"
"""


def _stub(diretorio: Path, nome: str, corpo: str) -> Path:
    caminho = diretorio / nome
    caminho.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + corpo, encoding="utf-8", newline="\n")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


@pytest.fixture
def arvore(tmp_path):
    raiz = tmp_path / "arvore"
    (raiz / "bin" / "_infra").mkdir(parents=True)
    (raiz / "lib").mkdir(parents=True)
    shutil.copy2(INFRA, raiz / "bin" / "infra")
    (raiz / "bin" / "infra").chmod(0o755)
    shutil.copy2(REPO_RAIZ / "lib" / "raizes.sh", raiz / "lib" / "raizes.sh")
    return raiz


@pytest.fixture
def delatores(tmp_path):
    """docker, systemctl, curl e python3 que denunciam a chamada: ajuda e erro de uso não tocam o substrato."""
    d = tmp_path / "delatores"
    d.mkdir()
    for nome in ("docker", "systemctl", "curl", "python3"):
        _stub(d, nome, f'echo "DELATOR:{nome} chamado: $*" >&2\nexit 99\n')
    return d


def roda(raiz, *args, path_extra=None, env_extra=None):
    env = dict(os.environ)
    env.pop("PF_SUJEITO", None)
    if path_extra:
        env["PATH"] = str(path_extra) + os.pathsep + env.get("PATH", "")
    env.update(env_extra or {})
    return subprocess.run([BASH, str(raiz / "bin" / "infra"), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=30, check=False)


# --- o cabeçalho ---------------------------------------------------------------------------------

def test_o_cabecalho_declara_face_rotulo_e_volta_do_medir_na_gramatica_do_conferidor():
    declarado = {}
    for linha in INFRA.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("#"):
            break
        m = _LINHA_DE_ATO.match(linha.strip())
        if m:
            declarado[(m.group(1), m.group(2))] = m.group(3)
    assert declarado[("face", "medir")] == "Operação"
    assert declarado[("rotulo", "medir")] == "Medir rede"
    assert declarado[("volta", "medir")] == "sim — só lê"


def test_o_medir_esta_na_lista_de_atos_do_cabecalho_como_leitura():
    cabecalho = INFRA.read_text(encoding="utf-8").split("set -euo pipefail", 1)[0]
    assert "medir (leitura, operacao)" in cabecalho and "medir=nada" in cabecalho


# --- a ajuda -------------------------------------------------------------------------------------

@pytest.mark.parametrize("args", [("medir", "rede", "--help"), ("medir", "--help"), ("medir", "rede", "-h"),
                                  ("medir", "--ajuda")])
def test_medir_help_mostra_face_rotulo_e_volta_e_sai_0_sem_tocar_o_substrato(arvore, delatores, args):
    r = roda(arvore, *args, path_extra=delatores)
    assert r.returncode == 0, r.stderr
    for campo in ("face: Operação", "rotulo: Medir rede", "volta: sim — só lê"):
        assert campo in r.stdout
    assert "DELATOR:" not in r.stdout + r.stderr


@pytest.mark.parametrize("eixo,rotulo", [("rede", "Medir rede"), ("vram", "Medir VRAM"), ("cpu", "Medir processamento")])
def test_a_ajuda_de_cada_eixo_diz_o_rotulo_dele_e_so_o_dele(arvore, delatores, eixo, rotulo):
    r = roda(arvore, "medir", eixo, "--help", path_extra=delatores)
    assert r.returncode == 0, r.stderr
    assert f"uso: infra medir {eixo}" in r.stdout and f"rotulo: {rotulo}" in r.stdout
    assert "face: Operação" in r.stdout and "volta: sim — só lê" in r.stdout
    assert r.stdout.count("rotulo:") == 1 and "DELATOR:" not in r.stdout + r.stderr


def test_a_ajuda_de_vram_declara_que_a_soma_dos_processos_nao_e_o_total_e_que_so_ha_computacao(arvore, delatores):
    r = roda(arvore, "medir", "vram", "--help", path_extra=delatores)
    assert "não é o total da placa" in r.stdout and "Processo gráfico não aparece" in r.stdout


def test_a_ajuda_do_medir_sem_eixo_mostra_os_tres(arvore, delatores):
    r = roda(arvore, "medir", "--help", path_extra=delatores)
    assert r.returncode == 0 and r.stdout.count("rotulo:") == 3


def test_a_ajuda_universal_dos_outros_atos_segue_saindo_2(arvore, delatores):
    r = roda(arvore, "estado", "--ajuda", path_extra=delatores)
    assert r.returncode == 2 and "uso:" in r.stderr and "infra medir" in r.stderr, "o uso geral lista o medir"


# --- o despacho ----------------------------------------------------------------------------------

def test_medir_rede_despacha_com_os_argumentos(arvore):
    _stub(arvore / "bin" / "_infra", "medir-rede", FAKE_MEDIR)
    r = roda(arvore, "medir", "rede", "--json")
    assert r.returncode == 0 and "MEDIR_REDE: [--json]" in r.stdout


@pytest.mark.parametrize("eixo", ["vram", "cpu"])
def test_medir_vram_e_cpu_despacham_cada_um_para_o_seu_ato_com_os_argumentos(arvore, eixo):
    for ato in ("rede", "vram", "cpu"):
        _stub(arvore / "bin" / "_infra", f"medir-{ato}", FAKE_MEDIR.replace("MEDIR_REDE", f"MEDIR_{ato.upper()}"))
    r = roda(arvore, "medir", eixo, "--json")
    assert r.returncode == 0 and f"MEDIR_{eixo.upper()}: [--json]" in r.stdout


@pytest.mark.parametrize("eixo", ["vram", "cpu"])
@pytest.mark.parametrize("saida", [0, 5])
def test_o_codigo_de_saida_de_vram_e_cpu_passa_inteiro(arvore, eixo, saida):
    _stub(arvore / "bin" / "_infra", f"medir-{eixo}", FAKE_MEDIR)
    assert roda(arvore, "medir", eixo, env_extra={"FAKE_SAIDA": str(saida)}).returncode == saida


@pytest.mark.parametrize("saida", [0, 5])
def test_o_codigo_de_saida_do_eixo_passa_inteiro(arvore, saida):
    _stub(arvore / "bin" / "_infra", "medir-rede", FAKE_MEDIR)
    assert roda(arvore, "medir", "rede", env_extra={"FAKE_SAIDA": str(saida)}).returncode == saida


def test_medir_nao_exige_identidade(arvore):
    _stub(arvore / "bin" / "_infra", "medir-rede", FAKE_MEDIR)
    r = roda(arvore, "medir", "rede")
    assert r.returncode == 0 and "PF_SUJEITO" not in r.stderr


def test_medir_sem_eixo_sai_2(arvore, delatores):
    r = roda(arvore, "medir", path_extra=delatores)
    assert r.returncode == 2 and "medir exige o eixo" in r.stderr and "DELATOR:" not in r.stderr


def test_eixo_desconhecido_sai_2_e_diz_os_validos(arvore, delatores):
    r = roda(arvore, "medir", "inexistente", path_extra=delatores)
    assert r.returncode == 2
    assert "eixo desconhecido: inexistente" in r.stderr and "valores válidos: rede, vram, cpu" in r.stderr


@pytest.mark.parametrize("eixo", ["rede", "vram", "cpu"])
def test_ajudante_ausente_e_dependencia_exit_3(arvore, eixo):
    r = roda(arvore, "medir", eixo)
    assert r.returncode == 3 and f"bin/_infra/medir-{eixo}" in r.stderr


def test_o_ato_desconhecido_lista_o_medir(arvore):
    r = roda(arvore, "bogus-ato")
    assert r.returncode == 2 and "medir" in r.stderr.split("atos:", 1)[1].splitlines()[0]
