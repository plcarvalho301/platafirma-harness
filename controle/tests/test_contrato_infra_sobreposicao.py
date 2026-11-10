"""`infra sobreposicao remover`: o verbo que apaga a sobreposicao da instancia de uma stack (#2856 linha 351).

A sobreposicao (`$PLATAFIRMA_INSTANCIA/deploy/<stack>/compose.override.yaml`) que sobrepoe servico que a rev
removeu trava o `release promover` (#2856 linha 350), e nenhum verbo da conta a apagava: write_file recusa a
morada e o malote nao tem rm, o contorno era `sudo rm` do dono. O ato guarda a copia antes (conferida byte a
byte), apaga so o arquivo regular com esse nome, e e idempotente. Estes casos rodam o bin/infra de verdade com a
instancia e a pasta de removidos trocadas por variavel: nada toca a producao.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH")

OVERRIDE = "services:\n  rag-api:\n    environment:\n      X: \"1\"\n"


class Cena:
    def __init__(self, tmp_path):
        self.inst = tmp_path / "instancia"
        self.removidos = tmp_path / "removidos"
        self.dir = self.inst / "deploy" / "rag"
        self.dir.mkdir(parents=True)
        self.arq = self.dir / "compose.override.yaml"
        self.arq.write_text(OVERRIDE)
        (self.dir / "compose.yaml").write_text("name: rag\n")        # vizinho que nao pode sumir

    def roda(self, *args, sujeito="sujeito-de-teste", **env):
        e = {**os.environ, "PLATAFIRMA_INSTANCIA": str(self.inst), "INFRA_REMOVIDOS": str(self.removidos)}
        e.pop("PF_SUJEITO", None)
        if sujeito:
            e["PF_SUJEITO"] = sujeito
        e.update(env)
        return subprocess.run([BASH, str(INFRA), "sobreposicao", *args], capture_output=True, text=True,
                              env=e, timeout=30, check=False)

    def copias(self):
        return sorted(self.removidos.glob("sobreposicao-rag-*.yaml")) if self.removidos.exists() else []


@pytest.fixture
def cena(tmp_path):
    return Cena(tmp_path)


def test_remove_guarda_a_copia_igual_e_nao_toca_o_vizinho(cena):
    r = cena.roda("remover", "rag")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "removida:" in r.stdout and "sujeito-de-teste" in r.stdout
    assert not cena.arq.exists()
    copias = cena.copias()
    assert len(copias) == 1 and copias[0].read_text() == OVERRIDE      # a volta existe e e a do arquivo
    assert (cena.dir / "compose.yaml").read_text() == "name: rag\n"
    assert "infra up rag -d" in r.stdout                               # diz o que aplica o efeito


def test_ver_so_mostra_e_nao_pede_identidade(cena):
    r = cena.roda("remover", "rag", "--ver", sujeito=None)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ver: removeria" in r.stdout
    assert cena.arq.read_text() == OVERRIDE and cena.copias() == []


def test_sem_identidade_sai_3_e_nao_apaga(cena):
    r = cena.roda("remover", "rag", sujeito=None)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "PF_SUJEITO" in r.stderr
    assert cena.arq.read_text() == OVERRIDE and cena.copias() == []


def test_repetir_e_idempotente(cena):
    assert cena.roda("remover", "rag").returncode == 0
    r = cena.roda("remover", "rag")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nada a remover" in r.stdout
    assert len(cena.copias()) == 1                                    # a segunda nao guardou outra copia


@pytest.mark.parametrize("slug", ["../rag", "rag/../x", "a/b", ".rag", "rag;ls", "rag x"])
def test_slug_que_nao_e_slug_sai_4_com_ou_sem_ver(cena, slug):
    fora = cena.inst / "x"
    fora.mkdir()
    (fora / "compose.override.yaml").write_text(OVERRIDE)
    for extra in ((), ("--ver",)):
        r = cena.roda("remover", slug, *extra)
        assert r.returncode == 4, (slug, r.stdout + r.stderr)
    assert cena.arq.read_text() == OVERRIDE and (fora / "compose.override.yaml").exists()


def test_link_simbolico_sai_4_e_preserva_o_alvo(cena, tmp_path):
    alvo = tmp_path / "alvo.yaml"
    alvo.write_text(OVERRIDE)
    cena.arq.unlink()
    cena.arq.symlink_to(alvo)
    r = cena.roda("remover", "rag")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "link simb" in r.stderr
    assert alvo.read_text() == OVERRIDE and cena.arq.is_symlink()


def test_diretorio_no_lugar_do_arquivo_sai_4(cena):
    cena.arq.unlink()
    cena.arq.mkdir()
    r = cena.roda("remover", "rag")
    assert r.returncode == 4, r.stdout + r.stderr
    assert cena.arq.is_dir()


def test_se_nao_da_para_guardar_a_copia_nada_e_apagado(cena, tmp_path):
    bloqueio = tmp_path / "removidos-e-arquivo"
    bloqueio.write_text("nao e pasta")
    r = cena.roda("remover", "rag", INFRA_REMOVIDOS=str(bloqueio))
    assert r.returncode == 3, r.stdout + r.stderr
    assert cena.arq.read_text() == OVERRIDE


def test_uso_errado_sai_2(cena):
    assert cena.roda().returncode == 2
    assert cena.roda("apagar", "rag").returncode == 2
    assert cena.roda("remover").returncode == 2
    assert cena.roda("remover", "rag", "--forcar").returncode == 2
    assert cena.roda("remover", "rag", "outra").returncode == 2
    assert cena.arq.read_text() == OVERRIDE
