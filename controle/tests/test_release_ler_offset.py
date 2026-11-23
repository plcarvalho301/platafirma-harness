# componente: componente:verbo-release
"""Contrato de `release ler <repo> <caminho>` sobre `lib/leitura` (incidente #4433).

Por padrão, `release ler` devolve o arquivo servido inteiro (sem páginas fixas de
45 KB e sem rodapé `truncado em N de M bytes`), deixando o teto de 200 KiB e o
aviso de corte para a poda da porta. Quando o chamador pede recorte explícito
(`--linhas`, `--offset`, `--max-bytes`), o fatiamento delega a `lib/leitura`,
preservando fronteiras UTF-8 e recusando `--offset` inválido ou além do fim com exit 2.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "release"


class Servido:
    """<PF_RELEASE_RAIZ>/fixture/current -> <sha>/ somente-leitura (checkout destacado)."""

    def __init__(self, tmp_path: Path):
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        src = tmp_path / "src"
        src.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=src, check=True, env=git_env)
        (src / "README").write_text("ok\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=src, check=True, env=git_env)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=src, check=True, env=git_env)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=src,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.dir = tmp_path / "opt" / "fixture"
        self.alvo = self.dir / sha
        self.dir.mkdir(parents=True)
        subprocess.run(["git", "clone", "-q", str(src), str(self.alvo)], check=True, env=git_env)
        subprocess.run(["git", "checkout", "-q", "--detach", sha], cwd=self.alvo, check=True, env=git_env)
        (self.dir / "current").symlink_to(sha)
        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        for nome in ("FAMILIAS", "VENVS", "TERCEIROS"):
            arq = tmp_path / f"{nome.lower()}.json"
            arq.write_text("{}", encoding="utf-8")
            self.env[f"PLATAFIRMA_{nome}"] = str(arq)

    def grava(self, rel: str, dados: bytes) -> None:
        (self.alvo / rel).write_bytes(dados)

    def fecha(self) -> None:
        os.chmod(self.alvo, 0o555)

    def ler(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SCRIPT), "ler", "fixture", *args],
            env=self.env,
            capture_output=True,
            timeout=60,
            check=False,
        )


@pytest.fixture()
def servido(tmp_path):
    s = Servido(tmp_path)
    yield s
    os.chmod(s.alvo, 0o755)


def _grande(servido: Servido) -> bytes:
    """1200 linhas de 100 bytes = 120000 bytes (~117 KiB, acima dos antigos 45 KB)."""
    dados = b"".join(b"%04d " % i + b"x" * 94 + b"\n" for i in range(1200))
    assert len(dados) == 120000
    servido.grava("estilo.css", dados)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root): o servido nao fica somente-leitura")
    return dados


def test_documento_curto_sai_byte_a_byte_como_antes(servido):
    curto = b"linha um\nlinha dois\nsem quebra no fim"
    servido.grava("curto.md", curto)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root)")
    r = servido.ler("curto.md")
    assert r.returncode == 0, r.stderr
    assert r.stdout == curto
    assert b"truncado" not in r.stdout


def test_arquivo_grande_120kb_sai_inteiro_por_padrao_sem_paginar(servido):
    dados = _grande(servido)
    r = servido.ler("estilo.css")
    assert r.returncode == 0, r.stderr
    assert r.stdout == dados
    assert b"truncado em" not in r.stdout


def test_max_bytes_e_offset_fatiam_e_remontam_arquivo_inteiro(servido):
    dados = _grande(servido)
    juntado, offset, paginas = b"", 0, 0
    while offset < len(dados):
        r = servido.ler("estilo.css", "--offset", str(offset), "--max-bytes", "45000")
        assert r.returncode == 0, r.stderr
        assert r.stdout
        assert b"truncado em" not in r.stdout
        juntado += r.stdout
        offset += len(r.stdout)
        paginas += 1
        assert paginas <= 5
    assert paginas == 3
    assert juntado == dados


def test_linhas_e_numerar_delegam_a_lib_leitura(servido):
    dados = _grande(servido)
    esperadas = dados.splitlines(keepends=True)[9:12]
    r = servido.ler("estilo.css", "--linhas", "10-12")
    assert r.returncode == 0, r.stderr
    assert r.stdout == b"".join(esperadas)

    rn = servido.ler("estilo.css", "--linhas", "10-12", "--numerar")
    assert rn.returncode == 0, rn.stderr
    linhas_num = rn.stdout.decode("utf-8").splitlines()
    assert [ln.split(":", 1)[0] for ln in linhas_num] == ["10", "11", "12"]


def test_corte_cai_na_fronteira_de_caractere_utf8(servido):
    dados = "é".encode("utf-8") * 40000  # 80000 bytes, 2 por caractere
    servido.grava("acentos.txt", dados)
    servido.fecha()
    if os.access(servido.alvo, os.W_OK):
        pytest.skip("conta com escrita irrestrita (root)")
    # offset 1 cai no meio de "é": avança para o byte 2; max-bytes 44999 recua para fronteira par (44998 bytes = 2..45000)
    r = servido.ler("acentos.txt", "--offset", "1", "--max-bytes", "44999")
    assert r.returncode == 0, r.stderr
    texto = r.stdout.decode("utf-8")
    assert "\ufffd" not in texto
    assert r.stdout == dados[2:45000]


@pytest.mark.parametrize("offset", ["abc", "-1", "1.5", ""])
def test_offset_malformado_ou_negativo_sai_2(servido, offset):
    _grande(servido)
    r = servido.ler("estilo.css", "--offset", offset)
    assert r.returncode == 2, (r.stdout[:200], r.stderr)


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


def test_uso_documenta_opcoes_sem_fossil_de_45kb(servido):
    r = subprocess.run(
        [str(SCRIPT), "ler"],
        env=servido.env,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 2
    err = r.stderr.decode("utf-8")
    assert "--linhas <faixa>" in err
    assert "--offset <bytes>" in err
    assert "--inteiro" in err
    assert "45000" not in err
    assert "truncado em" not in err
