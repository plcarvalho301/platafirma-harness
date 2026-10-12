"""`infra ingress`: a copia da instancia do cloudflared.yml passa a ter um ato que a escreve (#3473).

O cloudflared do tunel `wiki` le a COPIA da instancia (deploy/core/cloudflared.yml, montada pelo
override; card #3010), nao o arquivo versionado do core, e nenhum ato a escrevia: a rota
decomissionada (mcp.platafirma.org) seguiu viva ate o dono copiar a mao (#3271). O ato copia o
versionado da release no ar para a copia, mostra a diferenca antes (`--ver` so mostra) e reinicia o
contêiner. Estes casos rodam o bin/infra de verdade, com docker de mentira no PATH e fonte, copia e
nome do contêiner trocados por variavel: nada toca a producao.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("diff") is None,
                                reason="sem bash ou diff no PATH")

CONTEINER = "platafirma-core-cloudflared-1"

INGRESS_NOVO = """\
tunnel: 01452d04-7dd9-40ea-be5a-f8bcaa7bed8f
credentials-file: /etc/cloudflared/creds/01452d04-7dd9-40ea-be5a-f8bcaa7bed8f.json
ingress:
  - hostname: wiki.platafirma.org
    service: http://gate-wiki:4180
  # mcp.platafirma.org: decomissionada
  - hostname: mcp.platafirma.org
    service: http_status:404
  - service: http_status:404
"""

INGRESS_VELHO = INGRESS_NOVO.replace(
    "  - hostname: mcp.platafirma.org\n    service: http_status:404\n",
    "  - hostname: mcp.platafirma.org\n    service: http://mcp:8000\n")

# docker de mentira: o estado vem de variavel de ambiente, o rastro vai para um arquivo.
DOCKER = r"""#!/usr/bin/env bash
case "$*" in
  *--filter*) echo "${STUB_STATUS:-Up 2 seconds}" ;;
  *'{{.Names}}\t{{.Status}}'*) printf '%s\tUp 1 second\n' "${STUB_CONTEINER:-}" ;;
  *'{{.Names}}'*) [ -z "${STUB_CONTEINER:-}" ] || echo "$STUB_CONTEINER" ;;
  restart*)
    printf 'restart %s rota_velha=%s\n' "$2" "$(grep -c 'mcp:8000' "$STUB_COPIA" || true)" >> "$STUB_LOG"
    ;;
  *) echo "docker-stub: comando nao coberto: $*" >&2; exit 1 ;;
esac
"""


class Cena:
    def __init__(self, tmp_path):
        self.raiz = tmp_path
        self.fonte = tmp_path / "release" / "core" / "deploy" / "cloudflared-config.yml"
        self.copia = tmp_path / "instancia" / "deploy" / "core" / "cloudflared.yml"
        self.log = tmp_path / "docker.log"
        self.bin = tmp_path / "bin"
        for p in (self.fonte.parent, self.copia.parent, self.bin):
            p.mkdir(parents=True)
        self.log.write_text("")
        docker = self.bin / "docker"
        docker.write_text(DOCKER)
        docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
        self.fonte.write_text(INGRESS_NOVO)
        self.copia.write_text(INGRESS_VELHO)

    def roda(self, *args, **env):
        e = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
             "INFRA_INGRESS_FONTE": str(self.fonte), "INFRA_INGRESS_COPIA": str(self.copia),
             "INFRA_INGRESS_CONTEINER": CONTEINER, "INFRA_INGRESS_ESPERA": "0",
             "STUB_CONTEINER": CONTEINER, "STUB_COPIA": str(self.copia), "STUB_LOG": str(self.log)}
        e.update(env)
        return subprocess.run([BASH, str(INFRA), "ingress", *args], capture_output=True, text=True,
                              env=e, timeout=30, check=False)

    def restarts(self):
        return [linha for linha in self.log.read_text().splitlines() if linha.startswith("restart")]


@pytest.fixture
def cena(tmp_path):
    return Cena(tmp_path)


# --- --ver: so mostra ----------------------------------------------------------------------

def test_ver_mostra_a_diferenca_sai_1_e_nao_toca_na_copia(cena):
    r = cena.roda("--ver")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "-    service: http://mcp:8000" in r.stdout
    assert "+    service: http_status:404" in r.stdout
    assert "divergente" in r.stdout
    assert cena.copia.read_text() == INGRESS_VELHO
    assert not Path(str(cena.copia) + ".anterior").exists()
    assert cena.restarts() == []


def test_ver_com_copia_igual_sai_0(cena):
    cena.copia.write_text(INGRESS_NOVO)
    r = cena.roda("--ver")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "igual" in r.stdout
    assert cena.restarts() == []


# --- sem --ver: grava e reinicia -----------------------------------------------------------

def test_grava_a_copia_guarda_a_anterior_e_reinicia_depois_de_gravar(cena):
    r = cena.roda()
    assert r.returncode == 0, r.stdout + r.stderr
    # a diferenca sai ANTES da gravacao
    assert r.stdout.index("== diferença") < r.stdout.index("gravada:")
    assert cena.copia.read_text() == INGRESS_NOVO
    assert Path(str(cena.copia) + ".anterior").read_text() == INGRESS_VELHO
    # o restart viu a copia nova (sem a rota velha), nao a anterior
    assert cena.restarts() == [f"restart {CONTEINER} rota_velha=0"]
    assert "de pé" in r.stdout


def test_copia_ja_igual_nao_grava_nem_reinicia(cena):
    cena.copia.write_text(INGRESS_NOVO)
    r = cena.roda()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nada gravado, nada reiniciado" in r.stdout
    assert cena.restarts() == []
    assert not Path(str(cena.copia) + ".anterior").exists()


def test_a_copia_nova_guarda_o_modo_da_antiga(cena):
    cena.copia.chmod(0o640)
    r = cena.roda()
    assert r.returncode == 0, r.stdout + r.stderr
    assert stat.S_IMODE(cena.copia.stat().st_mode) == 0o640


def test_sem_copia_anterior_cria_com_644_e_reinicia(cena):
    cena.copia.unlink()
    r = cena.roda()
    assert r.returncode == 0, r.stdout + r.stderr
    assert cena.copia.read_text() == INGRESS_NOVO
    assert stat.S_IMODE(cena.copia.stat().st_mode) == 0o644
    assert len(cena.restarts()) == 1
    assert not [p for p in cena.copia.parent.iterdir() if p.name.startswith(".cloudflared.")]


# --- o que recusa, sem gravar nem reiniciar ------------------------------------------------

def test_fonte_ausente_sai_3_sem_tocar_na_copia(cena):
    cena.fonte.unlink()
    r = cena.roda()
    assert r.returncode == 3, r.stdout + r.stderr
    assert "dependência" in r.stderr and "release promover platafirma-core" in r.stderr
    assert cena.copia.read_text() == INGRESS_VELHO and cena.restarts() == []


@pytest.mark.parametrize("corpo,porque", [
    (INGRESS_NOVO.replace("  - service: http_status:404\n", ""), "sem a regra final"),
    (INGRESS_NOVO.replace("ingress:\n", "ingres:\n"), "sem ingress:"),
    (INGRESS_NOVO.replace("tunnel: 01452d04-7dd9-40ea-be5a-f8bcaa7bed8f\n", ""), "sem tunnel:"),
    ("", "vazio"),
])
def test_fonte_que_o_cloudflared_recusaria_nao_se_grava(cena, corpo, porque):
    cena.fonte.write_text(corpo)
    r = cena.roda()
    assert r.returncode == 1, porque + r.stdout + r.stderr
    assert "reprovado" in r.stderr
    assert cena.copia.read_text() == INGRESS_VELHO and cena.restarts() == []


def test_conteiner_ausente_sai_3_sem_gravar(cena):
    r = cena.roda(STUB_CONTEINER="")
    assert r.returncode == 3, r.stdout + r.stderr
    assert f"contêiner {CONTEINER}: ausente" in r.stderr
    assert cena.copia.read_text() == INGRESS_VELHO and cena.restarts() == []


def test_opcao_desconhecida_sai_2_sem_efeito(cena):
    r = cena.roda("--forcar")
    assert r.returncode == 2
    assert "opção desconhecida em ingress: --forcar" in r.stderr
    assert cena.copia.read_text() == INGRESS_VELHO and cena.restarts() == []


# --- contêiner que nao sobe: a anterior volta ----------------------------------------------

def test_conteiner_que_nao_fica_de_pe_volta_a_copia_anterior(cena):
    r = cena.roda(STUB_STATUS="Restarting (1) 2 seconds ago")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "não ficou de pé" in r.stderr and "voltou a cópia anterior" in r.stderr
    assert cena.copia.read_text() == INGRESS_VELHO
    # primeiro com a copia nova; o segundo, o da volta, ja com a anterior de pe
    assert cena.restarts() == [f"restart {CONTEINER} rota_velha=0", f"restart {CONTEINER} rota_velha=1"]
    assert not Path(str(cena.copia) + ".volta").exists()


# --- cabecalho e usage ---------------------------------------------------------------------

def test_o_ato_esta_no_cabecalho_com_o_par_de_restart_e_na_usage():
    cab = INFRA.read_text(encoding="utf-8").splitlines()[:30]
    atos = next(linha for linha in cab if linha.startswith("# atos:"))
    # o par (acao, tipo) que o PEP le e o mesmo de restart: nenhuma regra nova de PEP
    assert "ingress (escrita, operacao)" in atos and "restart (escrita, operacao)" in atos
    assert any(linha.startswith("# escreve:") and "ingress=" in linha for linha in cab)
    r = subprocess.run([BASH, str(INFRA), "--ajuda"], capture_output=True, text=True, timeout=30,
                       check=False)
    assert r.returncode == 2 and "infra ingress  [--ver]" in r.stderr
