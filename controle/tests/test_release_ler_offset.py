"""Contrato de `release ler <repo> <caminho> [--offset N]` (#2856 linha 146).

O defeito medido: a porta corta a saida em 50 KB sem `next_offset`, e o arquivo servido maior
que isso (estilo.css do rastreador, 52.643 bytes) nao se obtinha inteiro. O verbo agora pagina
em bytes, no mesmo idioma do `acervo ler casa --offset`: paginas de 45000 bytes, corte na
fronteira de caractere utf-8, ultima linha `truncado em N de M bytes; continue com --offset N
(release ler <repo> <caminho> --offset N)`, sem aviso na ultima pagina, `--offset`
malformado/negativo/alem do fim sai 2, documento curto sai como antes (byte a byte).

Sem rede e sem forge: usa a familia `abertura` (current = diretorio somente-leitura com
MANIFEST.json), a unica que `release ler` resolve sem checkout git. Nao prova: a poda da porta
(ops-server), que fica fora deste verbo.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "release"
SHA = "a" * 40
PAGINA = 45000
RODAPE = re.compile(
    r"^truncado em (\d+) de (\d+) bytes; continue com --offset (\d+) "
    r"\(release ler abertura (\S+) --offset (\d+)\)$")


class Servido:
    """PF_ABERTURA_DIR/current -> <sha>/ somente-leitura, com os arquivos do teste."""

    def __init__(self, tmp_path: Path):
        self.dir = tmp_path / "srv" / "var" / "abertura-publicada"
        self.alvo = self.dir / SHA
        self.alvo.mkdir(parents=True)
        (self.alvo / "MANIFEST.json").write_bytes(
            json.dumps({"sha": SHA, "publicado_em": "2026-10-03 00:00:00Z"}).encode())
        (self.dir / "current").symlink_to(self.alvo)
        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        self.env["PF_ABERTURA_DIR"] = str(self.dir)
        for nome in ("FAMILIAS", "VENVS", "TERCEIROS"):
            arq = tmp_path / f"{nome.lower()}.json"
            arq.write_text("{}", encoding="utf-8")
            self.env[f"PLATAFIRMA_{nome}"] = str(arq)

    def grava(self, rel: str, dados: bytes) -> None:
        (self.alvo / rel).write_bytes(dados)

    def fecha(self) -> None:
        os.chmod(self.alvo, 0o555)   # servido e somente-leitura (resolver_identidade exige)

    def ler(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), "ler", "abertura", *args], env=self.env,
                              capture_output=True, timeout=60, check=False)


@pytest.fixture()
def servido(tmp_path):
    s = Servido(tmp_path)
    yield s
    os.chmod(s.alvo, 0o755)   # tmp_path precisa poder ser apagado


def _grande(servido: Servido) -> bytes:
    """1200 linhas de 100 bytes = 120000 bytes: as paginas caem em fronteira de linha."""
    dados = b"".join(b"%04d " % i + b"x" * 94 + b"\n" for i in range(1200))
    assert len(dados) == 120000
    servido.grava("estilo.css", dados)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root): o servido nao fica somente-leitura")
    return dados


def test_documento_curto_sai_byte_a_byte_como_antes(servido):
    # sem \n final de proposito: o verbo nao pode acrescentar nada ao que cabe numa pagina
    curto = b"linha um\nlinha dois\nsem quebra no fim"
    servido.grava("curto.md", curto)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root)")
    r = servido.ler("curto.md")
    assert r.returncode == 0, r.stderr
    assert r.stdout == curto
    assert b"truncado" not in r.stdout


def test_documento_no_limite_da_pagina_sai_inteiro_sem_aviso(servido):
    dados = b"y" * PAGINA
    servido.grava("justo.txt", dados)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root)")
    r = servido.ler("justo.txt")
    assert r.returncode == 0, r.stderr
    assert r.stdout == dados


def test_arquivo_maior_que_a_pagina_trunca_com_next_offset_abaixo_dos_50kb(servido):
    dados = _grande(servido)
    r = servido.ler("estilo.css")
    assert r.returncode == 0, r.stderr
    assert len(r.stdout) < 50000
    corpo, _, ultima = r.stdout.decode().rstrip("\n").rpartition("\n")
    m = RODAPE.match(ultima)
    assert m, ultima
    assert m.groups() == ("45000", "120000", "45000", "estilo.css", "45000")
    assert (corpo + "\n").encode() == dados[:PAGINA]


def test_paginas_remontam_o_arquivo_inteiro_e_a_ultima_nao_avisa(servido):
    dados = _grande(servido)
    juntado, offset, paginas = b"", 0, 0
    while True:
        args = ["estilo.css"] + (["--offset", str(offset)] if offset else [])
        r = servido.ler(*args)
        assert r.returncode == 0, r.stderr
        paginas += 1
        ultima = r.stdout.rstrip(b"\n").rsplit(b"\n", 1)[-1]
        if ultima.startswith(b"truncado em "):
            m = RODAPE.match(ultima.decode())
            assert m, ultima
            juntado += r.stdout.rsplit(b"truncado em ", 1)[0]
            offset = int(m.group(3))
        else:
            juntado += r.stdout
            break
        assert paginas < 10
    assert paginas == 3
    assert juntado == dados


def test_corte_cai_na_fronteira_de_caractere_utf8(servido):
    dados = "é".encode() * 40000      # 80000 bytes, 2 por caractere
    servido.grava("acentos.txt", dados)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root)")
    # offset 1 cai no meio de um "é": a pagina comeca no proximo caractere inteiro,
    # e o fim (45001) tambem cairia no meio de um: recua para 45000.
    r = servido.ler("acentos.txt", "--offset", "1")
    assert r.returncode == 0, r.stderr
    corpo, _, ultima = r.stdout.rstrip(b"\n").rpartition(b"\n")
    corpo.decode("utf-8")             # nao levanta: nenhum multibyte partido
    m = RODAPE.match(ultima.decode())
    assert m and m.group(1) == "45000" and m.group(2) == "80000", ultima
    assert corpo == dados[2:45000]


@pytest.mark.parametrize("offset", ["abc", "-1", "1.5", ""])
def test_offset_malformado_ou_negativo_sai_2(servido, offset):
    _grande(servido)
    r = servido.ler("estilo.css", "--offset", offset)
    assert r.returncode == 2, (r.stdout[:200], r.stderr)
    assert b"truncado" not in r.stdout


def test_offset_sem_valor_sai_2(servido):
    _grande(servido)
    r = servido.ler("estilo.css", "--offset")
    assert r.returncode == 2, r.stderr


def test_offset_alem_do_fim_sai_2_e_no_fim_exato_sai_vazio(servido):
    _grande(servido)
    r = servido.ler("estilo.css", "--offset", "120001")
    assert r.returncode == 2, r.stderr
    assert b"120000" in r.stderr
    r = servido.ler("estilo.css", "--offset", "120000")
    assert r.returncode == 0, r.stderr
    assert r.stdout == b""


def test_uso_documenta_o_offset(servido):
    r = subprocess.run([str(SCRIPT), "ler"], env=servido.env, capture_output=True,
                       timeout=60, check=False)
    assert r.returncode == 2
    assert "release ler        <repo> <caminho> [--offset <bytes>]" in r.stderr.decode()
