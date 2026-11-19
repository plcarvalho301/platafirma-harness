"""Contratos da ler_arquivo (spec ler-arquivo §14, card #3263) que a casa nova mantém,
migrados de ops-server/test_leitura.py (#4348).

Os contratos que lib/leitura não implementa (offset, linha longa por bytes, sumário,
encoding suposto e não julgado, onde o caminho parou, índice e cache, UTF-16, gramática
estrita de linhas) estão listados em remocao-no-pr e no débito técnico da story #4342.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ / "lib"))

from leitura import leitura as L  # noqa: E402

ORCAMENTOS = (1_024, 4_096, 40_000)


def _segue(p, **kw):
    paginas = [L.ler(p, **kw)]
    limite = Path(p).stat().st_size * 2 + 10
    while paginas[-1].get("proximo_args"):
        assert len(paginas) < limite, "a continuação não anda"
        args = dict(paginas[-1]["proximo_args"])
        paginas.append(L.ler(args.pop("caminho"), **{**kw, **args}))
    return paginas


def _soma(paginas) -> str:
    return "".join(pg["conteudo"] for pg in paginas)


def _fixtures(tmp_path) -> dict:
    textos = {
        "ascii.txt": "".join(f"linha {i}\n" for i in range(1, 3000)),
        "acentos.md": "# Título\n\nação, café, coração — “aspas” e 😀 emoji\n" * 400,
        "crlf.txt": "primeira\r\nsegunda\r\n\r\nquarta sem fim\r\n" * 300,
        "sem_fim.py": "def f():\n    return 1\n\n\nx = f()",
        "vazias.txt": "\n\n\na\n\n\n",
    }
    for nome, t in textos.items():
        (tmp_path / nome).write_bytes(t.encode("utf-8"))
    return {nome: tmp_path / nome for nome in textos}


# --- C1 soma das páginas · C2 corte em fim de linha -----------------------------------------------
@pytest.mark.parametrize("orcamento", ORCAMENTOS)
def test_c1_paginas_somadas_dao_o_arquivo(tmp_path, orcamento):
    for nome, p in _fixtures(tmp_path).items():
        paginas = _segue(p, max_bytes=orcamento)
        assert _soma(paginas).encode("utf-8") == p.read_bytes(), (nome, orcamento)
        assert paginas[-1]["proximo"] == L.FIM and "proximo_args" not in paginas[-1]


@pytest.mark.parametrize("orcamento", ORCAMENTOS)
def test_c2_pagina_por_linhas_so_termina_em_fim_de_linha(tmp_path, orcamento):
    for nome, p in _fixtures(tmp_path).items():
        for pg in _segue(p, max_bytes=orcamento)[:-1]:
            if pg["conteudo"]:
                assert pg["conteudo"].endswith("\n"), (nome, orcamento, pg["cabecalho"])


def test_c2_crlf_volta_como_esta(tmp_path):
    pg = L.ler(_fixtures(tmp_path)["crlf.txt"])
    assert "primeira\r\nsegunda\r\n" in pg["conteudo"]


# --- cauda e faixa ----------------------------------------------------------------------------------
def test_cauda_le_as_ultimas_linhas(tmp_path):
    p = tmp_path / "dez.txt"
    p.write_text("".join(f"{i}\n" for i in range(1, 11)))
    pg = L.ler(p, linhas="-3")
    assert pg["conteudo"] == "8\n9\n10\n" and pg["linhas"] == [8, 10]
    assert pg["proximo"] == L.FIM


def test_faixa_do_meio(tmp_path):
    p = tmp_path / "muitas.txt"
    p.write_text("".join(f"linha {i}\n" for i in range(1, 5_001)))
    pg = L.ler(p, linhas="3000-3002")
    assert pg["conteudo"] == "linha 3000\nlinha 3001\nlinha 3002\n"
    assert pg["linhas"] == [3000, 3002] and pg["linhas_total"] == 5_000


# --- C6 versão ----------------------------------------------------------------------------------------
def test_c6_arquivo_que_muda_entre_paginas_avisa(tmp_path):
    p = tmp_path / "muda.txt"
    p.write_text("".join(f"linha {i}\n" for i in range(1000)))
    pg1 = L.ler(p, max_bytes=1_024)
    with p.open("a") as f:
        f.write("nova\n")
    args = dict(pg1["proximo_args"])
    pg2 = L.ler(args.pop("caminho"), **args)
    assert pg2["mudou"] == {"de": pg1["versao"], "para": pg2["versao"]}
    assert pg2["cabecalho"].startswith("ARQUIVO MUDOU desde a versão")


# --- encoding -----------------------------------------------------------------------------------------
def test_encoding_pedido_julga(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes("ação\n".encode("cp1252"))
    pg = L.ler(p, encoding="latin-1")
    assert pg["encoding"]["por"] == "pedido" and pg["conteudo"] == "ação\n"


def test_cp1252_le_e_diz_que_caiu_no_fallback(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes("ação, café e coração\n".encode("cp1252"))
    pg = L.ler(p)
    assert "ação, café" in pg["conteudo"]
    assert pg["encoding"]["decidido"] == "cp1252" and pg["encoding"]["por"] == "fallback"


# --- C9 binário · C12 ausente · diretório -----------------------------------------------------------
@pytest.mark.parametrize("nome,dados,tipo", [
    ("a.bin", b"\x7fELF\x02\x01\x01" + bytes(range(256)), "application/x-elf"),
    ("a.txt", b"texto\x00com nulo\n", "application/octet-stream"),
])
def test_c9_binario_fora_da_tabela_recusa_com_nome(tmp_path, nome, dados, tipo):
    p = tmp_path / nome
    p.write_bytes(dados)
    r = L.ler(p)
    assert r["exit_code"] == 1 and r["erro"] == "sem_leitor" and r["tipo"] == tipo
    assert "conteudo" not in r


def test_c12_caminho_ausente_sai_exit1_sem_parecidos(tmp_path):
    r = L.ler(tmp_path / "nao" / "existe.py")
    assert r["exit_code"] == 1 and r["erro"] == "nao_existe"
    assert "parecidos" not in r


def test_diretorio_lista_em_ordem_e_marca_subpasta(tmp_path):
    d = tmp_path / "pasta"
    d.mkdir()
    (d / "b.txt").write_text("bb")
    (d / "a.txt").write_text("a")
    (d / "sub").mkdir()
    pg = L.ler(d)
    assert pg["entradas"] == ["a.txt", "b.txt", "sub/"]
    assert pg["total"] == 3


def test_dt242_diretorio_filtro_termo(tmp_path):
    d = tmp_path / "mistura"
    d.mkdir()
    (d / "alvo1.log").write_text("1")
    (d / "alvo2.log").write_text("2")
    (d / "outro.txt").write_text("3")
    (d / "alvo_dir").mkdir()
    pg = L.ler(d, termo="alvo")
    assert pg["total"] == 3
    assert "alvo1.log" in pg["conteudo"] and "alvo_dir/" in pg["conteudo"]
    assert "outro.txt" not in pg["conteudo"]


def test_gramatica_de_linhas_recusa_o_que_nao_e_numero(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a\n")
    r = L.ler(p, linhas="abc")
    assert r["exit_code"] == 2 and str(p) in r["proximo"]
