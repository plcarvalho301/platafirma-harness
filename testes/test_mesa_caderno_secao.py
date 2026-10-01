"""`mesa caderno <chapeu> --secao <slug>`: so a secao do caderno que o agente delegado le (card #3158).

O pacote cadeirinha pede a secao `conhecimento-curado`; o diario de bordo e da cadeira. Os cadernos
da casa tem dois formatos de titulo, e o do devops mistura os dois no mesmo arquivo: `## titulo` e
TITULO EM MAIUSCULAS (formato antigo). As duas secoes de mesmo slug saem juntas.

Desde a #3218 o caderno mora no banco, uma linha por entrada; o arquivo de antes chega como legado
a triar (sessao.caderno_legado) e e nele que a secao se recorta, no corpo do chapeu.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("mesa_bin", str(REPO_ROOT / "bin" / "mesa"))
spec = importlib.util.spec_from_loader("mesa_bin", loader)
assert spec and spec.loader
mesa = importlib.util.module_from_spec(spec)
loader.exec_module(mesa)

# o caderno do devops, em miniatura: formato antigo primeiro, o novo depois
MISTO = """CONHECIMENTO CURADO
- Esperar evento assincrono consultando o estado, nunca com pausa fixa.
- Card antigo pode trazer trava fossil.

DIARIO DE BORDO
2026-09-27 — release promover saiu 2 (contorno: nome platafirma-harness).

## conhecimento curado

- Exit 1 tem sentido oposto em lote encadeado e em esteira.
### detalhe dentro da secao
- Nao generalizar a regra.

## diário de bordo

- 2026-09-26 — fui commitar o guia.
"""

NOVO = """# Caderno

## Conhecimento curado
- uma regra

## Diário de bordo
- um dia
"""


@pytest.mark.parametrize("titulo, slug", [
    ("Conhecimento curado", "conhecimento-curado"),
    ("CONHECIMENTO CURADO", "conhecimento-curado"),
    ("Diário de bordo", "diario-de-bordo"),
    ("  Varias   palavras,  com pontuação! ", "varias-palavras-com-pontuacao"),
])
def test_slug_do_titulo(titulo, slug):
    assert mesa._slug_de_titulo(titulo) == slug


@pytest.mark.parametrize("linha, esperado", [
    ("## conhecimento curado", (2, "conhecimento curado")),
    ("# Titulo", (1, "Titulo")),
    ("### sub", (3, "sub")),
    ("CONHECIMENTO CURADO", (0, "CONHECIMENTO CURADO")),
    ("DIARIO DE BORDO", (0, "DIARIO DE BORDO")),
    ("- ITEM EM MAIUSCULAS NAO E TITULO", None),
    ("OK", None),                       # curto demais
    ("texto comum", None),
    ("", None),
    ("####### sete", None),
])
def test_o_que_abre_secao(linha, esperado):
    assert mesa._abre_secao(linha) == esperado


def test_as_duas_secoes_de_mesmo_slug_saem_juntas_e_o_diario_fica_fora():
    s = mesa._secao_do_caderno(MISTO, "conhecimento-curado")
    assert "Esperar evento assincrono" in s and "Card antigo" in s            # formato antigo
    assert "Exit 1 tem sentido oposto" in s and "Nao generalizar" in s        # formato novo
    assert "detalhe dentro da secao" in s, "subtitulo mais fundo pertence a secao"
    assert s.startswith("CONHECIMENTO CURADO")
    for fora in ("DIARIO DE BORDO", "release promover saiu 2", "fui commitar o guia", "diário de bordo"):
        assert fora not in s


def test_secao_acaba_no_proximo_titulo_de_nivel_igual_ou_menor():
    s = mesa._secao_do_caderno(NOVO, "conhecimento-curado")
    assert s == "## Conhecimento curado\n- uma regra"
    assert mesa._secao_do_caderno(NOVO, "diario-de-bordo") == "## Diário de bordo\n- um dia"


def test_secao_inexistente_e_none():
    assert mesa._secao_do_caderno(NOVO, "nao-tem") is None
    assert mesa._secao_do_caderno("", "conhecimento-curado") is None


LEGADO = {"chave_origem": "abertura/engenharia/devops/caderno.md", "chapeu": "devops",
          "bytes": len(MISTO.encode("utf-8")), "capturado_em": None, "texto": MISTO}


def _corpo(secao=None):
    """O corpo do chapeu sem entrada no banco e com o legado ainda nao triado."""
    return mesa._corpo_texto("engenharia", "devops", [], [LEGADO], {}, date(2026, 10, 1),
                             secao=secao)


def test_corpo_com_secao_traz_so_ela_do_legado_e_diz_qual():
    out = _corpo("conhecimento-curado")
    assert "===== legado a triar: abertura/engenharia/devops/caderno.md#conhecimento-curado (" in out
    assert "DIARIO DE BORDO" not in out and "Exit 1 tem sentido oposto" in out


def test_corpo_sem_secao_traz_o_legado_inteiro():
    out = _corpo()
    assert "===== legado a triar: abertura/engenharia/devops/caderno.md (" in out
    assert MISTO.rstrip("\n") in out


def test_secao_ausente_no_legado_e_aviso_nao_erro():
    assert "legado devops: sem a secao nao-tem" in _corpo("nao-tem")


def test_a_secao_corta_o_tamanho():
    assert len(_corpo("conhecimento-curado")) < len(_corpo())


def test_cli_secao_sem_chapeu_e_erro_de_uso():
    import subprocess
    import sys
    env = {**os.environ, "PF_CADEIRA": "engenharia"}
    p = subprocess.run([sys.executable, str(REPO_ROOT / "bin" / "mesa"), "caderno", "--secao", "conhecimento-curado"],
                       capture_output=True, text=True, env=env, timeout=30)
    assert p.returncode != 0
    assert "--secao" in p.stderr and "chapeu" in p.stderr
