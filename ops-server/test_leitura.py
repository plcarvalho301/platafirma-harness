"""Contrato da `ler_arquivo` sobre `leitura.py` (spec ler-arquivo §14, card #3263).

Sem subir a porta e sem estado do host: cada caso escreve a própria fixture em `tmp_path`.
C15 e C16 são da poda e moram no `_ensaio.py`, que precisa do servidor.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leitura as L                                            # noqa: E402

ORCAMENTOS = (1, 7, 64, 4_096, 40_000)


def _segue(p, **kw):
    """Lê de `linhas="1-"` (ou do que `kw` pedir) seguindo `proximo_args` até o fim."""
    paginas = [L.le(p, **kw)]
    limite = Path(p).stat().st_size * 2 + 10
    while paginas[-1].get("proximo_args"):
        assert len(paginas) < limite, "a continuação não anda"
        paginas.append(L.le(**{"p": paginas[-1]["proximo_args"]["caminho"],
                               **{k: v for k, v in paginas[-1]["proximo_args"].items()
                                  if k != "caminho"}}))
    return paginas


def _soma(paginas) -> str:
    return "".join(pg["conteudo"] for pg in paginas)


def _fixtures(tmp_path) -> dict:
    textos = {
        "ascii.txt": "".join(f"linha {i}\n" for i in range(1, 300)),
        "acentos.md": "# Título\n\nação, café, coração — “aspas” e 😀 emoji\n" * 40,
        "crlf.txt": "primeira\r\nsegunda\r\n\r\nquarta sem fim\r\n" * 30,
        "sem_fim.py": "def f():\n    return 1\n\n\nx = f()",
        "vazias.txt": "\n\n\na\n\n\n",
        "longa_no_meio.txt": "curta\n" + "x" * 300 + "\ncurta de novo\n",
    }
    for nome, t in textos.items():
        (tmp_path / nome).write_bytes(t.encode("utf-8"))
    return {nome: tmp_path / nome for nome in textos}


# --- C1 soma das páginas · C2 corte em fim de linha --------------------------------------
@pytest.mark.parametrize("orcamento", ORCAMENTOS)
def test_c1_paginas_somadas_dao_o_arquivo(tmp_path, orcamento):
    for nome, p in _fixtures(tmp_path).items():
        L.esvazia_cache()                    # a primeira página a frio, as seguintes a quente
        paginas = _segue(p, max_bytes=orcamento)
        enc = paginas[0]["encoding"]["decidido"]
        assert _soma(paginas).encode(enc) == p.read_bytes(), (nome, orcamento)
        assert paginas[-1]["proximo"] == L.FIM and "proximo_args" not in paginas[-1]


@pytest.mark.parametrize("orcamento", ORCAMENTOS)
def test_c2_pagina_por_linhas_so_termina_em_fim_de_linha(tmp_path, orcamento):
    for nome, p in _fixtures(tmp_path).items():
        paginas = _segue(p, max_bytes=orcamento)
        for pg in paginas[:-1]:
            if pg.get("linhas") and pg["conteudo"]:
                assert pg["conteudo"].endswith("\n"), (nome, orcamento, pg["cabecalho"])


def test_c2_crlf_volta_como_esta(tmp_path):
    p = _fixtures(tmp_path)["crlf.txt"]
    pg = L.le(p)
    assert "primeira\r\nsegunda\r\n" in pg["conteudo"]


# --- C3 multibyte por bytes ----------------------------------------------------------------
def test_c3_corte_por_bytes_nunca_fabrica_substituicao(tmp_path):
    p = tmp_path / "multi.txt"
    p.write_bytes(("é€😀ñ漢" * 50).encode("utf-8"))
    for orcamento in range(1, 10):
        paginas = _segue(p, offset=0, max_bytes=orcamento)
        assert all("\ufffd" not in pg["conteudo"] for pg in paginas), orcamento
        assert _soma(paginas).encode("utf-8") == p.read_bytes(), orcamento


def test_c3_offset_no_meio_do_caractere_avanca_e_diz(tmp_path):
    p = tmp_path / "multi.txt"
    p.write_bytes("a€b".encode("utf-8"))
    pg = L.le(p, offset=2)
    assert pg["conteudo"] == "b" and "2 bytes pulados" in pg["cabecalho"]


# --- C4 linha longa --------------------------------------------------------------------------
def test_c4_linha_longa_vira_continuacao_por_bytes(tmp_path):
    p = tmp_path / "uma.json"
    p.write_text(json.dumps({"k": "v" * 60_000}), encoding="utf-8")
    pg = L.le(p)
    assert pg["conteudo"].encode() == p.read_bytes()[:L.ORCAMENTO_PADRAO], "já traz o 1º pedaço"
    assert pg["linha_longa"] == {"linha": 1, "bytes": p.stat().st_size, "byte_ini": 0}
    assert pg["cabecalho"].startswith("LINHA LONGA")
    assert pg["proximo_args"]["offset"] == L.ORCAMENTO_PADRAO
    assert len(_segue(p)) == 2, "60 kB em duas páginas, sem página vazia"
    assert _soma(_segue(p)).encode() == p.read_bytes()


def test_c4_linha_longa_no_meio_comeca_no_byte_certo(tmp_path):
    p = tmp_path / "meio.txt"
    p.write_text("um\ndois\n" + "x" * 500 + "\nfim\n", encoding="utf-8")
    pg = L.le(p, linhas="3-", max_bytes=100)
    assert pg["linha_longa"]["byte_ini"] == len("um\ndois\n") and pg["conteudo"] == "x" * 100
    assert "começa na linha 3" in pg["cabecalho"]
    assert _soma(_segue(p, max_bytes=100)).encode() == p.read_bytes()


# --- C5 vazio e além do fim --------------------------------------------------------------------
def test_c5_vazio_e_alem_do_fim_nunca_se_confundem(tmp_path):
    vazio = tmp_path / "vazio.txt"
    vazio.write_bytes(b"")
    pg = L.le(vazio)
    assert pg["conteudo"] == "" and pg["proximo"] == L.FIM
    assert "arquivo vazio (0 bytes)" in pg["cabecalho"]
    dez = tmp_path / "dez.txt"
    dez.write_text("".join(f"{i}\n" for i in range(10)))
    r = L.le(dez, linhas="999-")
    assert r["erro"] == "faixa além do fim" and r["linhas_total"] == 10
    assert r["classe_erro"] == "faixa" and 'linhas="-100"' in r["cura"]


def test_cauda_le_as_ultimas_linhas(tmp_path):
    p = tmp_path / "dez.txt"
    p.write_text("".join(f"{i}\n" for i in range(1, 11)))
    pg = L.le(p, linhas="-3")
    assert pg["conteudo"] == "8\n9\n10\n" and pg["linhas"] == [8, 10]
    assert pg["proximo"] == L.FIM


# --- C6 versão ---------------------------------------------------------------------------------
def test_c6_arquivo_que_muda_entre_paginas_avisa(tmp_path):
    p = tmp_path / "muda.txt"
    p.write_text("".join(f"linha {i}\n" for i in range(100)))
    pg1 = L.le(p, max_bytes=50)
    with p.open("a") as f:
        f.write("nova\n")
    args = dict(pg1["proximo_args"])
    pg2 = L.le(args.pop("caminho"), **args)
    assert pg2["mudou"] == {"de": pg1["versao"], "para": pg2["versao"]}
    assert pg2["cabecalho"].startswith("ARQUIVO MUDOU desde a versão")


# --- C7 Latin-1 · C8 UTF-8 com byte inválido ------------------------------------------------------
def test_c7_cp1252_e_suposto_e_nao_julgado(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes("ação, café e coração\n".encode("cp1252"))
    pg = L.le(p)
    assert pg["encoding"]["por"] == "suposto" and pg["encoding"]["julgado"] is False
    assert "ação, café" in pg["conteudo"]
    assert pg["cabecalho"].startswith("NÃO JULGADO")


def test_c8_um_byte_invalido_conta_e_marca_so_a_sua_pagina(tmp_path):
    p = tmp_path / "quase.txt"
    linhas = ["ação número %d\n" % i for i in range(40)]
    dados = "".join(linhas).encode("utf-8")
    meio = dados.index(b"20\n") + 3
    p.write_bytes(dados[:meio] + b"\xff" + dados[meio:])
    paginas = _segue(p, max_bytes=120)
    assert paginas[0]["encoding"] == {"decidido": "utf-8", "por": "maioria", "invalidos": 1,
                                      "julgado": False}
    subst = [pg["conteudo"].count("\ufffd") for pg in paginas]
    assert sum(subst) == 1 and subst.count(1) == 1


def test_encoding_pedido_julga(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes("ação\n".encode("cp1252"))
    pg = L.le(p, encoding="latin-1")
    assert pg["encoding"]["por"] == "pedido" and pg["conteudo"] == "ação\n"
    assert not pg["cabecalho"].startswith("NÃO JULGADO")


# --- C9 binário ----------------------------------------------------------------------------------
# Emenda de 04/10/2026 (§7.2.2, §7.4): binário de tipo que o acervo guarda se lê pelo leitor do
# formato (C18, test_formatos.py); só o de tipo fora da tabela recusa, com nome e `sem_leitor`.
@pytest.mark.parametrize("nome,dados,tipo", [
    ("a.bin", b"\x7fELF\x02\x01\x01" + bytes(range(256)), "application/x-elf"),
    ("a.txt", b"texto\x00com nulo\n", "application/octet-stream"),
    ("a.db", b"SQLite format 3\x00" + bytes(range(256)), "application/vnd.sqlite3"),
    ("a.gz", b"\x1f\x8b\x08\x00" + bytes(range(256)), "application/gzip"),
])
def test_c9_binario_fora_da_tabela_recusa_com_nome(tmp_path, nome, dados, tipo):
    p = tmp_path / nome
    p.write_bytes(dados)
    r = L.le(p)
    assert r["recusado"] is True and r["motivo"] == "sem_leitor" and r["tipo"] == tipo
    assert "conteudo" not in r and r["versao"] and r["classe_erro"] == "binario"
    assert "§7.4" in r["cura"]


# --- C10 sumário Markdown · C11 sumário Python -----------------------------------------------------
def test_c10_sumario_markdown_so_o_que_o_formato_declara(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("---\ntitulo: x\n# não é título\n---\n"
                 "# Um\ntexto\n```\n# comentário de código\n```\n"
                 "## Um.um\n~~~~\n# ainda código\n~~~~\n"
                 "# Dois\nfim\n#sem espaço não é título\n", encoding="utf-8")
    pg = L.le(p, modo="sumario")
    assert pg["sumario_por"] == "markdown"
    assert [i[:2] for i in pg["sumario"]] == [[1, "Um"], [2, "Um.um"], [1, "Dois"]]
    topo = [i for i in pg["sumario"] if i[0] == 1]
    assert topo[0][2] == 5 and topo[-1][3] == pg["linhas_total"]
    assert all(a[3] + 1 == b[2] for a, b in zip(topo, topo[1:])), "furo no primeiro nível"


def test_c11_sumario_python_e_o_do_ast(tmp_path):
    import ast
    fonte = ("import os\n\n\nclass A:\n    def m(self):\n        return 1\n\n"
             "    async def n(self):\n        pass\n\n\n"
             "@decorador\n@outro\ndef f(x):\n    return x\n")
    p = tmp_path / "m.py"
    p.write_text(fonte)
    itens = L.le(p, modo="sumario")["sumario"]
    arvore = ast.parse(fonte)
    classe, func = arvore.body[1], arvore.body[2]
    assert itens[0] == [1, "class A", classe.lineno, classe.end_lineno]
    assert itens[1] == [2, "def m", classe.body[0].lineno, classe.body[0].end_lineno]
    assert itens[2] == [2, "async def n", classe.body[1].lineno, classe.body[1].end_lineno]
    assert itens[3] == [1, "def f", func.decorator_list[0].lineno, func.end_lineno]
    ruim = tmp_path / "ruim.py"
    ruim.write_text("def f(:\n")
    r = L.le(ruim, modo="sumario")
    assert r["sumario"] is None and r["motivo"].startswith("python não analisa")


def test_sumario_sem_analisador_e_null_com_motivo(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text("a: 1\n")
    r = L.le(p, modo="sumario")
    assert r["sumario"] is None and "sem analisador" in r["motivo"]


def test_pagina_parcial_aponta_o_sumario(tmp_path):
    p = tmp_path / "grande.py"
    p.write_text("".join(f"def f{i}():\n    return {i}\n\n" for i in range(200)))
    pg = L.le(p, max_bytes=500)
    assert pg["sumario"] == f'ler_arquivo(caminho="{p}", modo="sumario")'


def test_sumario_com_linhas_e_gramatica(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# a\n")
    r = L.le(p, modo="sumario", linhas="1-")
    assert r["classe_erro"] == "gramatica" and "cura" in r


# --- C12 caminho ausente · C13 diretório -----------------------------------------------------------
def test_c12_caminho_ausente_diz_onde_parou(tmp_path):
    d = tmp_path / "bin" / "_acervo"
    d.mkdir(parents=True)
    for nome in ("curar", "ingerir", "leitura"):
        (d / nome).write_text("x")
    (d / "sub").mkdir()
    r = L.le(d / "leiturq")
    assert r["erro"] == "não existe" and r["classe_erro"] == "caminho"
    assert r["existe_ate"] == str(d)
    assert r["la_tem"] == ["curar", "ingerir", "leitura", "sub/"] and r["la_tem_total"] == 4
    assert r["parecidos"][0] == "leitura"
    assert r["cura"] == f'ler_arquivo(caminho="{d}")'
    longe = L.le(d / "x" / "y" / "z.py")
    assert longe["existe_ate"] == str(d)
    negado = L.le(d / "leiturq", nega=lambda q: q == d)
    assert negado["existe_ate"] == str(d) and "la_tem" not in negado


def test_c13_diretorio_lista_em_ordem_e_esconde_o_negado(tmp_path):
    d = tmp_path / "pasta"
    d.mkdir()
    (d / "b.txt").write_text("bb")
    (d / "a.txt").write_text("a")
    (d / "sub").mkdir()
    (d / ".env").write_text("SEGREDO=1")
    nega = lambda q: q.name.startswith(".env")                          # noqa: E731
    pg = L.le(d, nega=nega)
    assert pg["conteudo"] == "a.txt  1\nb.txt  2\nsub/\n"
    assert ".env" not in pg["conteudo"] and pg["ocultas"] == 1
    assert "diretório · 3 entradas" in pg["cabecalho"] and "1 fora por negativa" in pg["cabecalho"]
    primeira = L.le(d, nega=nega, linhas="1-2")
    assert primeira["conteudo"] == "a.txt  1\nb.txt  2\n"
    assert primeira["proximo_args"] == {"caminho": str(d), "linhas": "3-"}


# --- C14 lote --------------------------------------------------------------------------------------
def test_c14_teto_do_lote_conta_o_servido_e_nao_o_arquivo(tmp_path):
    ps = []
    for i in range(3):
        p = tmp_path / f"g{i}.txt"
        p.write_text("".join(f"{i} linha {j}\n" for j in range(10_000))[:100_000])
        ps.append(p)
    r = L.lote(ps, lambda _i, p: L.le(p, max_bytes=2_000), teto=50_000)
    assert r["lote_next"] is None
    assert all(item.get("conteudo") for item in r["lote"]), "o lote derrubou item"


def test_lote_erro_num_item_nao_derruba_os_outros(tmp_path):
    p = tmp_path / "ok.txt"
    p.write_text("ok\n")
    r = L.lote([tmp_path / "nao", p], lambda _i, q: L.le(q), teto=50_000)
    assert r["lote"][0]["erro"] == "não existe" and r["lote"][1]["conteudo"] == "ok\n"


# --- C17 apelido -----------------------------------------------------------------------------------
def test_c17_apelido_read_file_coerente_com_os_campos_novos(tmp_path):
    p = _fixtures(tmp_path)["acentos.md"]
    novo = L.le(p, max_bytes=300)
    r = L.como_read_file(L.le(p, max_bytes=300))
    assert r["content"] == novo["conteudo"] and "conteudo" not in r
    assert r["truncated"] is True and r["next_offset"] == novo["bytes"][1]
    assert r["offset"] == 0 and r["bytes_lidos"] == novo["bytes"][1] and r["path"] == str(p)
    # quem segue o apelido por next_offset recompõe o arquivo
    texto, off = r["content"], r["next_offset"]
    while off is not None:
        r = L.como_read_file(L.le(p, offset=off, max_bytes=300))
        texto, off = texto + r["content"], r["next_offset"]
    assert texto.encode() == p.read_bytes()
    erro = L.como_read_file(L.le(tmp_path / "nao"))
    assert erro["path"] == str(tmp_path / "nao")


def test_releitura_igual_sai_so_com_aviso_e_alca(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x\n" * 100)
    r = L.le(p)
    r.update(conteudo="[igual ao giro 3 — sha abc, 200 bytes não reenviados; inteiro=true reenvia]",
             poda={"modo": "igual"})
    magro = L.enxuga_releitura(dict(r))
    assert set(magro) == {"conteudo", "caminho", "versao", "poda"}
    inteiro = L.le(p)
    assert L.enxuga_releitura(dict(inteiro)) == inteiro, "página servida não perde campo"


# --- índice: marcos e cache ------------------------------------------------------------------------
def test_marco_acha_a_linha_a_frio_e_a_quente(tmp_path):
    p = tmp_path / "muitas.txt"
    p.write_text("".join(f"linha {i}\n" for i in range(1, 5_001)))
    for _ in range(2):
        L.esvazia_cache()
        pg = L.le(p, linhas="3000-3002")
        assert pg["conteudo"] == "linha 3000\nlinha 3001\nlinha 3002\n"
        assert pg["linhas"] == [3000, 3002] and pg["linhas_total"] == 5_000
    idx = L.indice_de(p)
    assert idx.marcos[1] == len("".join(f"linha {i}\n" for i in range(1, 1_025)))


def test_cache_tem_teto(tmp_path):
    L.esvazia_cache()
    for i in range(L.INDICES_MAX + 5):
        p = tmp_path / f"{i}.txt"
        p.write_text("x\n")
        L.le(p)
    assert len(L._INDICES) == L.INDICES_MAX


def test_utf16_com_bom_transcodifica_e_soma_fecha(tmp_path):
    p = tmp_path / "w.txt"
    p.write_bytes(codecs_bom("utf-16-le") + "ação\r\nlinha dois\r\n".encode("utf-16-le"))
    paginas = _segue(p, max_bytes=8)
    assert paginas[0]["encoding"]["decidido"] == "utf-16-le"
    assert "transcodificado de utf-16" in paginas[0]["cabecalho"]
    assert _soma(paginas).encode("utf-16-le") == p.read_bytes()


def codecs_bom(enc):
    import codecs
    return {"utf-16-le": codecs.BOM_UTF16_LE}[enc]


def test_gramatica_de_linhas(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a\n")
    for ruim in ("0-", "5-2", "abc", "-0"):
        r = L.le(p, linhas=ruim)
        assert r["classe_erro"] == "gramatica", ruim
