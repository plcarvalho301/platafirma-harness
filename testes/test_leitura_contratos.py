# componente: componente:porta
# verifica: controle-de-seguranca:borda-da-porta
"""Contratos da `ler_arquivo` sobre `lib/leitura` (spec ler-arquivo §14 e §7.4, DT 919).

Conjunto único de comportamento do `componente:leitor-universal`: cobre C1 a C14 (offset por
bytes, linha longa, vazio e além do fim, versão, encoding suposto/maioria e NÃO JULGADO,
sumário Markdown/Python/JSON, caminho ausente com existe_ate/la_tem, diretório paginado sem
negados e com contagem, lote pelo servido, índice com marcos, cache com teto, UTF-16 com BOM,
gramática estrita), C18 (PDF texto/página/sem camada, EPUB, DOCX, PPTX, XLSX, HTML/MHTML
visível, PNG, ZIP + caminho!membro, GZIP seguro, ELF sem_leitor), guardas das DTs 832/897/898/899
e alcance/morada de leitura e escrita (achado 921).
"""
from __future__ import annotations

import base64
import codecs
import gzip
import json
import os
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path
from typing import Any

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ / "lib"))

import oplog  # noqa: E402
from leitura import formatos as F  # noqa: E402
from leitura import leitura as L  # noqa: E402

BIN_WRITE = _RAIZ / "bin" / "write_file"
_PY_HARNESS = Path("/opt/platafirma/current/venv/harness/bin/python")
ORCAMENTOS = (1, 7, 64, 4_096, 40_000)


@pytest.fixture(autouse=True)
def _morada_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))


_DRIVER_NUCLEO = """
import base64, json, sys
from leitura import formatos as F
from leitura import leitura as L

def _ser(r):
    if isinstance(r.get("lote"), list):
        return {**r, "lote": [_ser(it) if isinstance(it, dict) else it for it in r["lote"]]}
    if not isinstance(r.get("imagens"), list):
        return r
    novas = []
    for it in r["imagens"]:
        if isinstance(it, dict) and isinstance(it.get("png"), (bytes, bytearray)):
            c = dict(it); c["base64"] = base64.b64encode(bytes(c.pop("png"))).decode("ascii"); novas.append(c)
        else:
            novas.append(it)
    return {**r, "imagens": novas}

req = json.loads(sys.stdin.read() or "{}")
sels = ("linhas","paginas","termo","modo","encoding","dpi","max_bytes","versao","offset","membro","inteiro")
caminhos = req.get("caminhos")
if isinstance(caminhos, str):
    print(json.dumps(L.envelope_erro(2, "parâmetro `caminhos` exige lista, não texto escalar"), ensure_ascii=False))
    raise SystemExit(2)
if isinstance(caminhos, list) and caminhos:
    teto = int(req.get("teto") or req.get("cap") or L.ORCAMENTO_MAX)
    def _it(_i, it):
        if isinstance(it, dict):
            cam = it.get("caminho"); sel = {k: it.get(k, req.get(k)) for k in sels}
        else:
            cam = it; sel = {k: req.get(k) for k in sels}
        if not cam or not isinstance(cam, str):
            return L.envelope_erro(2, "item do lote sem 'caminho'")
        dpi = F.DPI_PADRAO if sel["dpi"] is None else sel["dpi"]
        return L.ler(cam, linhas=sel["linhas"], paginas=sel["paginas"], termo=sel["termo"],
                     modo=str(sel["modo"] or "texto"), encoding=sel["encoding"], dpi=dpi,
                     max_bytes=sel["max_bytes"], versao=sel["versao"], offset=sel["offset"],
                     membro=sel["membro"], inteiro=bool(sel["inteiro"]))
    print(json.dumps(_ser(L.lote(caminhos, _it, teto=teto)), ensure_ascii=False))
    raise SystemExit(0)
cam = req.get("caminho")
if not cam:
    print(json.dumps(L.envelope_erro(2, "informe 'caminho' ou 'caminhos'"), ensure_ascii=False))
    raise SystemExit(2)
dpi = F.DPI_PADRAO if req.get("dpi") is None else req.get("dpi")
res = _ser(L.ler(cam, linhas=req.get("linhas"), paginas=req.get("paginas"), termo=req.get("termo"),
                 modo=str(req.get("modo") or "texto"), encoding=req.get("encoding"), dpi=dpi,
                 max_bytes=req.get("max_bytes"), versao=req.get("versao"), offset=req.get("offset"),
                 membro=req.get("membro"), inteiro=bool(req.get("inteiro", False))))
print(json.dumps(res, ensure_ascii=False))
raise SystemExit(int(res.get("exit_code") or 0))
"""


def _chamar(payload: dict) -> tuple[int, dict]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_RAIZ / "lib")
    cp = subprocess.run(
        [py, "-c", _DRIVER_NUCLEO],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    return cp.returncode, json.loads(cp.stdout)


def _chamar_bin(
    binario: Path,
    payload: dict[str, Any],
    *,
    instancia: Path,
    ordem_id: str = "o-921",
) -> tuple[dict[str, Any], bool]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    corpo = {"instancia": str(instancia), **payload}
    if ordem_id:
        corpo.setdefault("ordem_id", ordem_id)
    env = dict(os.environ)
    env["PF_ORDEM_ID"] = ordem_id
    cp = subprocess.run(
        [py, str(binario)],
        input=json.dumps(corpo, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    return json.loads(cp.stdout), cp.returncode != 0


def _segue(p: Path, **kw):
    paginas = [L.le(p, **kw)]
    limite = Path(p).stat().st_size * 2 + 10
    while paginas[-1].get("proximo_args"):
        assert len(paginas) < limite, "a continuação não anda"
        args = dict(paginas[-1]["proximo_args"])
        paginas.append(L.le(args.pop("caminho"), **args))
    return paginas


def _segue_cli(p: Path, **kw):
    rc, pg = _chamar({"caminho": str(p), **kw})
    assert rc == 0, pg
    pags = [pg]
    while pags[-1].get("proximo_args"):
        assert len(pags) < 5_000, "a continuação não anda"
        rc, nxt = _chamar(dict(pags[-1]["proximo_args"]))
        assert rc == 0, nxt
        pags.append(nxt)
    return pags


def _soma(paginas) -> str:
    return "".join(pg["conteudo"] for pg in paginas)


def _fixtures(tmp_path: Path) -> dict[str, Path]:
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


# --- C1 soma das páginas · C2 corte em fim de linha -----------------------------------------------
@pytest.mark.parametrize("orcamento", ORCAMENTOS)
def test_c1_paginas_somadas_dao_o_arquivo(tmp_path, orcamento):
    for nome, p in _fixtures(tmp_path).items():
        L.esvazia_cache()
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


# --- C3 multibyte por bytes -----------------------------------------------------------------------
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


def test_c3_offset_pelo_binario(tmp_path):
    p = tmp_path / "multi.txt"
    p.write_bytes("a€b".encode("utf-8"))
    rc, pg = _chamar({"caminho": str(p), "offset": 2})
    assert rc == 0 and pg["conteudo"] == "b" and "2 bytes pulados" in pg["cabecalho"]


# --- C4 linha longa -------------------------------------------------------------------------------
def test_c4_linha_longa_vira_continuacao_por_bytes(tmp_path):
    p = tmp_path / "uma.json"
    p.write_text(json.dumps({"k": "v" * 60_000}), encoding="utf-8")
    pg = L.le(p)
    assert pg["conteudo"].encode() == p.read_bytes()[: L.ORCAMENTO_PADRAO]
    assert pg["linha_longa"] == {"linha": 1, "bytes": p.stat().st_size, "byte_ini": 0}
    assert pg["cabecalho"].startswith("LINHA LONGA")
    assert pg["proximo_args"]["offset"] == L.ORCAMENTO_PADRAO
    assert len(_segue(p)) == 2
    assert _soma(_segue(p)).encode() == p.read_bytes()


def test_c4_linha_longa_no_meio_comeca_no_byte_certo(tmp_path):
    p = tmp_path / "meio.txt"
    p.write_text("um\ndois\n" + "x" * 500 + "\nfim\n", encoding="utf-8")
    pg = L.le(p, linhas="3-", max_bytes=100)
    assert pg["linha_longa"]["byte_ini"] == len("um\ndois\n") and pg["conteudo"] == "x" * 100
    assert "começa na linha 3" in pg["cabecalho"]
    assert _soma(_segue(p, max_bytes=100)).encode() == p.read_bytes()


# --- C5 vazio e além do fim -----------------------------------------------------------------------
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


# --- C6 versão ------------------------------------------------------------------------------------
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
    linhas = [f"ação número {i}\n" for i in range(40)]
    dados = "".join(linhas).encode("utf-8")
    meio = dados.index(b"20\n") + 3
    p.write_bytes(dados[:meio] + b"\xff" + dados[meio:])
    paginas = _segue(p, max_bytes=120)
    assert paginas[0]["encoding"] == {
        "decidido": "utf-8",
        "por": "maioria",
        "invalidos": 1,
        "julgado": False,
    }
    subst = [pg["conteudo"].count("\ufffd") for pg in paginas]
    assert sum(subst) == 1 and subst.count(1) == 1


def test_encoding_pedido_julga(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes("ação\n".encode("cp1252"))
    pg = L.le(p, encoding="latin-1")
    assert pg["encoding"]["por"] == "pedido" and pg["conteudo"] == "ação\n"
    assert not pg["cabecalho"].startswith("NÃO JULGADO")


# --- C9 binário -----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "nome,dados,tipo",
    [
        ("a.bin", b"\x7fELF\x02\x01\x01" + bytes(range(256)), "application/x-elf"),
        ("a.txt", b"texto\x00com nulo\n", "application/octet-stream"),
        ("a.db", b"SQLite format 3\x00" + bytes(range(256)), "application/vnd.sqlite3"),
    ],
)
def test_c9_binario_fora_da_tabela_recusa_com_nome(tmp_path, nome, dados, tipo):
    p = tmp_path / nome
    p.write_bytes(dados)
    r = L.le(p)
    assert r["recusado"] is True and r["motivo"] == "sem_leitor" and r["tipo"] == tipo
    assert "conteudo" not in r and r["versao"] and r["classe_erro"] == "binario"
    assert "§7.4" in r["cura"]


# --- C10 sumário Markdown · C11 sumário Python ----------------------------------------------------
def test_c10_sumario_markdown_so_o_que_o_formato_declara(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        "---\ntitulo: x\n# não é título\n---\n"
        "# Um\ntexto\n```\n# comentário de código\n```\n"
        "## Um.um\n~~~~\n# ainda código\n~~~~\n"
        "# Dois\nfim\n#sem espaço não é título\n",
        encoding="utf-8",
    )
    pg = L.le(p, modo="sumario")
    assert pg["sumario_por"] == "markdown"
    assert [i[:2] for i in pg["sumario"]] == [[1, "Um"], [2, "Um.um"], [1, "Dois"]]
    topo = [i for i in pg["sumario"] if i[0] == 1]
    assert topo[0][2] == 5 and topo[-1][3] == pg["linhas_total"]
    assert all(a[3] + 1 == b[2] for a, b in zip(topo, topo[1:])), "furo no primeiro nível"


def test_c11_sumario_python_e_o_do_ast(tmp_path):
    import ast

    fonte = (
        "import os\n\n\nclass A:\n    def m(self):\n        return 1\n\n"
        "    async def n(self):\n        pass\n\n\n"
        "@decorador\n@outro\ndef f(x):\n    return x\n"
    )
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


# --- C12 caminho ausente · C13 diretório ----------------------------------------------------------
def test_c12_caminho_ausente_diz_onde_parou(tmp_path):
    d = tmp_path / "bin" / "_acervo"
    d.mkdir(parents=True)
    for nome in ("curar", "ingerir", "leitura"):
        (d / nome).write_text("x")
    (d / "sub").mkdir()
    r = L.le(d / "leiturq")
    assert r["erro"] == "não existe" and r["classe_erro"] == "caminho"
    assert r["exit_code"] == 1
    assert r["existe_ate"] == str(d)
    assert r["la_tem"] == ["curar", "ingerir", "leitura", "sub/"] and r["la_tem_total"] == 4
    assert "parecidos" not in r
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
    nega = lambda q: q.name.startswith(".env")  # noqa: E731
    pg = L.le(d, nega=nega)
    assert pg["conteudo"] == "a.txt  1\nb.txt  2\nsub/\n"
    assert ".env" not in pg["conteudo"] and pg["ocultas"] == 1
    assert "diretório · 3 entradas" in pg["cabecalho"] and "1 fora por negativa" in pg["cabecalho"]
    assert pg["entradas"] == ["a.txt", "b.txt", "sub/"] and pg["total"] == 3
    primeira = L.le(d, nega=nega, linhas="1-2")
    assert primeira["conteudo"] == "a.txt  1\nb.txt  2\n"
    assert primeira["proximo_args"] == {"caminho": str(d), "linhas": "3-"}


def test_diretorio_dica_ultimas_e_filtro_termo(tmp_path):
    d = tmp_path / "muitos"
    d.mkdir()
    for i in range(10):
        (d / f"f{i:02d}.txt").write_text("x")
    pg = L.le(d, linhas="1-3")
    assert "diretório · 10 entradas" in pg["cabecalho"]
    assert "linhas=-3 para as últimas" in pg["cabecalho"]

    m = tmp_path / "mistura"
    m.mkdir()
    (m / "alvo1.log").write_text("1")
    (m / "alvo2.log").write_text("2")
    (m / "outro.txt").write_text("3")
    (m / "alvo_dir").mkdir()
    pgf = L.le(m, termo="alvo")
    assert pgf["linhas_total"] == 3
    assert "alvo1.log" in pgf["conteudo"] and "alvo_dir/" in pgf["conteudo"]
    assert "outro.txt" not in pgf["conteudo"]
    assert "filtro termo='alvo'" in pgf["cabecalho"]


# --- C14 lote · índice · cache · UTF-16 · gramática estrita ---------------------------------------
def test_c14_teto_do_lote_conta_o_servido_e_nao_o_arquivo(tmp_path):
    ps = []
    for i in range(3):
        p = tmp_path / f"g{i}.txt"
        p.write_text("".join(f"{i} linha {j}\n" for j in range(10_000))[:100_000])
        ps.append(p)
    r = L.lote(ps, lambda _i, p: L.le(p, max_bytes=2_000), teto=50_000)
    assert r["lote_next"] is None
    assert all(item.get("conteudo") for item in r["lote"]), "o lote derrubou item"
    rc, rcli = _chamar({"caminhos": [str(p) for p in ps], "max_bytes": 2_000, "teto": 50_000})
    assert rc == 0 and rcli["lote_next"] is None
    assert all(item.get("conteudo") for item in rcli["lote"])


def test_lote_erro_num_item_nao_derruba_os_outros(tmp_path):
    p = tmp_path / "ok.txt"
    p.write_text("ok\n")
    r = L.lote([tmp_path / "nao", p], lambda _i, q: L.le(q), teto=50_000)
    assert r["lote"][0]["erro"] == "não existe" and r["lote"][1]["conteudo"] == "ok\n"


def test_releitura_igual_sai_so_com_aviso_e_alca(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x\n" * 100)
    r = L.le(p)
    r.update(
        conteudo="[igual ao giro 3 — sha abc, 200 bytes não reenviados; inteiro=true reenvia]",
        poda={"modo": "igual"},
    )
    magro = L.enxuga_releitura(dict(r))
    assert set(magro) == {"conteudo", "caminho", "versao", "poda"}
    inteiro = L.le(p)
    assert L.enxuga_releitura(dict(inteiro)) == inteiro


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
    p.write_bytes(codecs.BOM_UTF16_LE + "ação\r\nlinha dois\r\n".encode("utf-16-le"))
    paginas = _segue(p, max_bytes=8)
    assert paginas[0]["encoding"]["decidido"] == "utf-16-le"
    assert "transcodificado de utf-16" in paginas[0]["cabecalho"]
    assert _soma(paginas).encode("utf-16-le") == p.read_bytes()


def test_gramatica_de_linhas(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("a\n")
    for ruim in ("0-", "5-2", "abc", "-0", "0"):
        r = L.le(p, linhas=ruim)
        assert r["classe_erro"] == "gramatica", ruim
        assert r["exit_code"] == 2 and str(p) in r["proximo"]


# --- C18: fixtures e contratos dos formatos do acervo (§7.4) --------------------------------------
def _pdf_fixture(destino: Path) -> Path:
    streams = [
        f"BT /F1 12 Tf 72 720 Td (Pagina {i} do PDF de prova.) Tj 0 -28 Td (Segunda linha, com ponto final.) Tj ET".encode(
            "latin-1"
        )
        for i in range(1, 4)
    ] + [b"0.8 0.1 0.1 rg 50 50 400 200 re f"]
    objs: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [4 0 R 5 0 R 6 0 R 7 0 R] /Count 4 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    for idx in range(4):
        objs.append(
            f"{4 + idx} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {8 + idx} 0 R >>\nendobj\n".encode()
        )
    for idx, st in enumerate(streams):
        objs.append(
            f"{8 + idx} 0 obj\n<< /Length {len(st)} >>\nstream\n".encode()
            + st
            + b"\nendstream\nendobj\n"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    p = destino / "prova.pdf"
    p.write_bytes(bytes(out))
    return p


def _png_fixture(destino: Path) -> Path:
    def chunk(tipo, dados):
        c = tipo + dados
        return struct.pack(">I", len(dados)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    w, h = 4, 3
    raw = b"".join(b"\x00" + bytes([255, 0, 0] * w) for _ in range(h))
    dados = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    p = destino / "figura.png"
    p.write_bytes(dados)
    return p


def _zip_fixture(
    destino: Path, nome: str, membros: list[tuple[str, bytes]], mimetype: bytes | None = None
) -> Path:
    p = destino / nome
    with zipfile.ZipFile(p, "w") as zf:
        if mimetype is not None:
            zf.writestr(zipfile.ZipInfo("mimetype"), mimetype, compress_type=zipfile.ZIP_STORED)
        for n, d in membros:
            zf.writestr(n, d, compress_type=zipfile.ZIP_DEFLATED)
    return p


def _epub_fixture(destino: Path) -> Path:
    cont = (
        b'<?xml version="1.0"?><container version="1.0" '
        b'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
        b'<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        b"</rootfiles></container>"
    )
    opf = (
        b'<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        b'unique-identifier="id"><metadata/><manifest>\n'
        b'<item id="c2" href="cap%202.xhtml" media-type="application/xhtml+xml"/>\n'
        b'<item id="c1" href="cap1.xhtml" media-type="application/xhtml+xml"/>\n'
        b'<item id="img" href="img/fig.png" media-type="image/png"/>\n'
        b'</manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>'
    )
    c1 = (
        b'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml">'
        b"<head><title>Um</title><style>p{color:red}</style></head>"
        b'<body><h1>Capitulo Um</h1><p>Primeiro par&aacute;grafo do livro.</p>'
        b'<p><img src="img/fig.png" alt="figura um"/></p><script>alert(1)</script></body></html>'
    )
    c2 = (
        b'<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Capitulo Dois</h1>'
        b"<p>Segundo capitulo.</p><table><tr><th>a</th><th>b</th></tr>"
        b"<tr><td>1</td><td>2</td></tr></table></body></html>"
    )
    return _zip_fixture(
        destino,
        "livro.epub",
        [
            ("META-INF/container.xml", cont),
            ("OEBPS/content.opf", opf),
            ("OEBPS/cap1.xhtml", c1),
            ("OEBPS/cap 2.xhtml", c2),
            ("OEBPS/img/fig.png", _png_fixture(destino).read_bytes()),
        ],
        mimetype=b"application/epub+zip",
    )


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _docx_fixture(destino: Path) -> Path:
    doc = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{_W}"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Titulo do documento</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Primeiro paragrafo</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r><w:r><w:t>, com nota.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>item de lista</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>col a</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>col b</w:t></w:r></w:p></w:tc></w:tr>
<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>mesclada</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:r><w:t>Ultimo paragrafo</w:t></w:r><w:r><w:commentReference w:id="0"/></w:r></w:p>
<w:sectPr/></w:body></w:document>"""
    styles = f'<?xml version="1.0"?><w:styles xmlns:w="{_W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>'
    notas = f'<?xml version="1.0"?><w:footnotes xmlns:w="{_W}"><w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote><w:footnote w:id="1"><w:p><w:r><w:t>Texto da nota de rodape.</w:t></w:r></w:p></w:footnote></w:footnotes>'
    coment = f'<?xml version="1.0"?><w:comments xmlns:w="{_W}"><w:comment w:id="0" w:author="Olga"><w:p><w:r><w:t>Revisar isto.</w:t></w:r></w:p></w:comment></w:comments>'
    ct = b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    return _zip_fixture(
        destino,
        "doc.docx",
        [
            ("[Content_Types].xml", ct),
            ("word/document.xml", doc.encode()),
            ("word/styles.xml", styles.encode()),
            ("word/footnotes.xml", notas.encode()),
            ("word/comments.xml", coment.encode()),
        ],
    )


def _pptx_fixture(destino: Path) -> Path:
    pres = f'<?xml version="1.0"?><p:presentation xmlns:p="{_P}" xmlns:r="{_R}"><p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId1"/></p:sldIdLst></p:presentation>'
    prels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/></Relationships>'

    def slide(titulo, corpo):
        return f"""<?xml version="1.0"?><p:sld xmlns:p="{_P}" xmlns:a="{_A}" xmlns:r="{_R}"><p:cSld><p:spTree>
<p:sp><p:nvSpPr><p:cNvPr id="2" name="T"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{titulo}</a:t></a:r></a:p></p:txBody></p:sp>
<p:sp><p:nvSpPr><p:cNvPr id="3" name="C"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:txBody><a:p><a:r><a:t>{corpo}</a:t></a:r></a:p><a:p><a:pPr lvl="1"/><a:r><a:t>subitem</a:t></a:r></a:p></p:txBody></p:sp>
<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>h1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>h2</a:t></a:r></a:p></a:txBody></a:tc></a:tr><a:tr><a:tc><a:txBody><a:p><a:r><a:t>v1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>v2</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>
</p:spTree></p:cSld></p:sld>"""

    s1rels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>'
    notas = f'<?xml version="1.0"?><p:notes xmlns:p="{_P}" xmlns:a="{_A}"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="N"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>Nota do apresentador do slide um.</a:t></a:r></a:p></p:txBody></p:sp><p:sp><p:nvSpPr><p:cNvPr id="3" name="num"/><p:cNvSpPr/><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>1</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>'
    return _zip_fixture(
        destino,
        "apres.pptx",
        [
            ("ppt/presentation.xml", pres.encode()),
            ("ppt/_rels/presentation.xml.rels", prels.encode()),
            ("ppt/slides/slide1.xml", slide("Slide arquivo um", "Corpo um").encode()),
            ("ppt/slides/slide2.xml", slide("Slide arquivo dois", "Corpo dois").encode()),
            ("ppt/slides/_rels/slide1.xml.rels", s1rels.encode()),
            ("ppt/notesSlides/notesSlide1.xml", notas.encode()),
        ],
    )


def _xlsx_fixture(destino: Path) -> Path:
    wb = f'<?xml version="1.0"?><workbook xmlns="{_S}" xmlns:r="{_R}"><sheets><sheet name="Vendas" sheetId="1" r:id="rId1"/><sheet name="Resumo" sheetId="2" r:id="rId2"/></sheets></workbook>'
    wrels = f'<?xml version="1.0"?><Relationships xmlns="{_REL}"><Relationship Id="rId1" Type="x/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="x/worksheet" Target="worksheets/sheet2.xml"/></Relationships>'
    ss = f'<?xml version="1.0"?><sst xmlns="{_S}" count="3" uniqueCount="3"><si><t>produto</t></si><si><t>total</t></si><si><r><t>ca</t></r><r><t>fe</t></r></si></sst>'
    s1 = f"""<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData>
<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><f>SUM(1,2)</f><v>3</v></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>cha</t></is></c><c r="B3" t="b"><v>1</v></c></row>
</sheetData><mergeCells count="1"><mergeCell ref="A4:B4"/></mergeCells></worksheet>"""
    s2 = f'<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData><row r="1"><c r="A1" t="str"><v>so uma</v></c></row></sheetData></worksheet>'
    return _zip_fixture(
        destino,
        "plan.xlsx",
        [
            ("xl/workbook.xml", wb.encode()),
            ("xl/_rels/workbook.xml.rels", wrels.encode()),
            ("xl/sharedStrings.xml", ss.encode()),
            ("xl/worksheets/sheet1.xml", s1.encode()),
            ("xl/worksheets/sheet2.xml", s2.encode()),
        ],
    )


def _html_fixture(destino: Path) -> Path:
    p = destino / "pagina.html"
    p.write_text(
        """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Página de prova</title>
<style>body{}</style><script>var x = 1;</script></head><body>
<h1>Cabeçalho</h1><p>Parágrafo <b>com</b> negrito e <a href="x">link</a>.</p>
<p hidden>escondido</p><p style="display:none">também escondido</p>
<ul><li>um</li><li>dois</li></ul>
<table><tr><th>a</th><th>b</th></tr><tr><td>1 | um</td><td>2</td></tr></table>
<pre>linha 1
  linha 2</pre><img src="img/x.png" alt="x"></body></html>""",
        encoding="utf-8",
    )
    return p


def _mhtml_fixture(destino: Path) -> Path:
    p = destino / "snapshot.mhtml"
    p.write_bytes(
        b"""From: <Saved by Blink>
Snapshot-Content-Location: https://exemplo.org/a
Subject: Prova
MIME-Version: 1.0
Content-Type: multipart/related;\r\n\ttype="text/html";\r\n\tboundary="----MultipartBoundary--abc----"

------MultipartBoundary--abc----
Content-Type: text/html
Content-ID: <frame-1@mhtml.blink>
Content-Transfer-Encoding: quoted-printable
Content-Location: https://exemplo.org/a

<html><head><meta charset=3D"utf-8"></head><body><h1>T=C3=ADtulo do snapsh=
ot</h1><p>Corpo do snapshot.</p></body></html>
------MultipartBoundary--abc----
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-Location: https://exemplo.org/x.png

iVBORw0KGgo=
------MultipartBoundary--abc------
"""
    )
    return p


@pytest.fixture(scope="module")
def fx(tmp_path_factory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("formatos")
    elf = d / "programa"
    elf.write_bytes(b"\x7fELF\x02\x01\x01" + bytes(range(256)) * 4)
    return {
        "pdf": _pdf_fixture(d),
        "epub": _epub_fixture(d),
        "docx": _docx_fixture(d),
        "pptx": _pptx_fixture(d),
        "xlsx": _xlsx_fixture(d),
        "html": _html_fixture(d),
        "mhtml": _mhtml_fixture(d),
        "png": _png_fixture(d),
        "zip": _zip_fixture(d, "pacote.zip", [("a/leia.txt", b"ola\nmundo\n"), ("b.md", b"# t\n")]),
        "elf": elf,
    }


@pytest.mark.parametrize(
    "nome,tipo",
    [("epub", F.EPUB), ("docx", F.DOCX), ("pptx", F.PPTX), ("xlsx", F.XLSX), ("zip", F.ZIP)],
)
def test_c18_formato_le_inteiro_sem_recusa(fx, nome, tipo):
    r = L.le(fx[nome])
    assert "recusado" not in r and "erro" not in r, r
    assert r["tipo"] == tipo and r["conteudo"] and r["encoding"]["por"] == "binario"
    assert tipo in r["cabecalho"]


@pytest.mark.parametrize("orcamento", (1, 7, 64, 300, 4_096, 40_000))
@pytest.mark.parametrize("nome", ["epub", "docx", "pptx", "xlsx"])
def test_c18_paginas_somadas_cobrem_toda_unidade_uma_vez(fx, nome, orcamento):
    L.esvazia_cache()
    ref = _soma(_segue(fx[nome], max_bytes=L.ORCAMENTO_MAX))
    L.esvazia_cache()
    pags = _segue(fx[nome], max_bytes=orcamento)
    assert _soma(pags) == ref
    assert pags[-1]["proximo"] == L.FIM and "proximo_args" not in pags[-1]
    if pags[0].get("paginas_total"):
        marcas = [ln for ln in ref.splitlines() if ln.startswith("<!-- p. ")]
        assert marcas == [f"<!-- p. {i} -->" for i in range(1, pags[0]["paginas_total"] + 1)]


def test_c18_tipo_pelos_bytes_e_nao_pelo_nome(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    p = tmp_path / "disfarce.txt"
    p.write_bytes(fx["pdf"].read_bytes())
    rc, rpdf = _chamar({"caminho": str(p)})
    assert rc == 0 and rpdf["tipo"] == F.PDF
    z = tmp_path / "disfarce.zip"
    z.write_bytes(fx["epub"].read_bytes())
    assert L.le(z)["tipo"] == F.EPUB and L.le(z)["unidade"] == "item"
    d = tmp_path / "sem_extensao"
    d.write_bytes(fx["html"].read_bytes())
    assert L.le(d)["tipo"] == F.HTML
    m = tmp_path / "snapshot"
    m.write_bytes(fx["mhtml"].read_bytes())
    assert L.le(m)["tipo"] == F.MHTML


def test_c18_pdf_texto_por_pagina_e_paginacao(fx, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    rc, r = _chamar({"caminho": str(fx["pdf"])})
    assert rc == 0 and r["tipo"] == F.PDF and r["encoding"]["por"] == "binario"
    assert r["unidade"] == "pagina" and r["paginas_total"] == 4 and r["paginas"] == [1, 4]
    assert "<!-- p. 1 -->\nPagina 1 do PDF de prova." in r["conteudo"]
    assert "página 1–4 de 4" in r["cabecalho"]
    rc2, r2 = _chamar({"caminho": str(fx["pdf"]), "paginas": "2-3"})
    assert rc2 == 0 and r2["paginas"] == [2, 3]
    assert "Pagina 2" in r2["conteudo"] and "Pagina 4" not in r2["conteudo"]
    assert "Pagina 1" not in r2["conteudo"]
    rc3, r3 = _chamar({"caminho": str(fx["pdf"]), "paginas": "2-3", "linhas": "2-2"})
    assert rc3 == 0 and r3["conteudo"] == "Pagina 2 do PDF de prova.\n" and r3["linhas"] == [2, 2]
    ref = _soma(_segue_cli(fx["pdf"], max_bytes=L.ORCAMENTO_MAX))
    assert _soma(_segue_cli(fx["pdf"], max_bytes=64)) == ref


def test_c18_pdf_modo_pagina_e_sem_camada(fx, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    rc, r = _chamar({"caminho": str(fx["pdf"]), "modo": "pagina"})
    assert rc == 0 and [i["pagina"] for i in r["imagens"]] == [1, 2, 3, 4]
    for i in r["imagens"]:
        raw = base64.b64decode(i["base64"])
        assert raw[:8] == b"\x89PNG\r\n\x1a\n" and i["mime"] == F.PNG and i["dpi"] == 150
        assert i["largura"] > 1000 and i["altura"] > i["largura"]
    assert r["proximo"] == L.FIM and "conteudo" not in r
    rc72, r72 = _chamar({"caminho": str(fx["pdf"]), "modo": "pagina", "paginas": "4-4", "dpi": 72})
    assert rc72 == 0 and len(r72["imagens"]) == 1 and r72["imagens"][0]["largura"] == 595
    rc_sc, r_sc = _chamar({"caminho": str(fx["pdf"]), "paginas": "4-4"})
    assert rc_sc == 0 and r_sc["cabecalho"].startswith("SEM CAMADA DE TEXTO p. 4")
    assert r_sc["sem_texto"] == [4] and 'modo="pagina"' in r_sc["cura"]
    assert "<!-- p. 4 -->" in r_sc["conteudo"] and "sem camada de texto" in r_sc["conteudo"]
    rc_lote, r_lote = _chamar(
        {"caminhos": [str(fx["pdf"]), str(fx["pdf"])], "modo": "pagina", "teto": 1}
    )
    assert rc_lote == 0 and "imagens" in r_lote["lote"][0]
    assert r_lote["lote"][1] == {"omitido_por_teto": True}


def test_c18_epub_docx_pptx_xlsx_html_mhtml_imagem_zip_gzip_elf(fx, tmp_path, monkeypatch):
    # EPUB
    re_ = L.le(fx["epub"])
    ce = re_["conteudo"]
    assert re_["unidade"] == "item" and re_["paginas_total"] == 2
    assert ce.index("Capitulo Um") < ce.index("Capitulo Dois")
    assert "Primeiro parágrafo" in ce and "alert(1)" not in ce and "color:red" not in ce
    assert "[imagem: OEBPS/img/fig.png" in ce and "| a | b |" in ce
    img_ep = L.le(fx["epub"], membro="OEBPS/img/fig.png", modo="pagina")
    assert img_ep["imagens"][0]["png"] == fx["png"].read_bytes()
    assert img_ep["caminho"].endswith("livro.epub!OEBPS/img/fig.png")

    # DOCX
    rd = L.le(fx["docx"])
    cd = rd["conteudo"]
    assert rd["unidade"] == "nenhuma" and "paginas_total" not in rd
    assert cd.startswith("# Titulo do documento\n")
    assert "Primeiro paragrafo[^1], com nota." in cd and "- item de lista" in cd
    assert "| col a | col b |" in cd and "| mesclada | mesclada |" in cd
    assert cd.index("<!-- notas -->") > cd.index("Ultimo paragrafo")
    assert "[^1]: Texto da nota de rodape." in cd and "[c0] Olga: Revisar isto." in cd
    assert L.le(fx["docx"], paginas="1-1")["classe_erro"] == "gramatica"

    # PPTX
    rp = L.le(fx["pptx"])
    cp = rp["conteudo"]
    assert rp["unidade"] == "slide" and rp["paginas_total"] == 2
    assert cp.index("# Slide arquivo dois") < cp.index("# Slide arquivo um")
    assert "| h1 | h2 |" in cp and "Nota do apresentador do slide um." in cp and "- subitem" in cp
    rec = L.le(fx["pptx"], modo="pagina")
    assert rec["recusado"] is True and rec["motivo"] == "sem_render"

    # XLSX
    rx = L.le(fx["xlsx"])
    cx = rx["conteudo"]
    assert rx["unidade"] == "planilha" and rx["nomes"] == ["Vendas", "Resumo"]
    assert "| cafe | 3 |" in cx and "SUM(" not in cx and "| cha | VERDADEIRO |" in cx
    assert L.le(fx["xlsx"], paginas="2-2")["paginas"] == [2, 2]

    # HTML / MHTML
    assert L.le(fx["html"])["conteudo"] == fx["html"].read_text(encoding="utf-8")
    rh = L.le(fx["html"], modo="visivel")
    ch = rh["conteudo"]
    assert rh["tipo"] == F.HTML and "var x" not in ch and "escondido" not in ch
    assert "| 1 \\| um | 2 |" in ch and "linha 1\n  linha 2" in ch and "[imagem: img/x.png — x]" in ch
    assert L.le(fx["html"], modo="visivel", max_bytes=20)["proximo_args"]["modo"] == "visivel"
    assert L.le(fx["mhtml"], modo="visivel")["conteudo"] == "# Título do snapshot\n\nCorpo do snapshot.\n"
    assert L.le(fx["mhtml"])["conteudo"].startswith("From: <Saved by Blink>")

    # Imagem
    ri = L.le(fx["png"])
    assert ri["cabecalho"].startswith("IMAGEM") and "4×3 px" in ri["cabecalho"]
    assert L.le(fx["png"], modo="pagina")["imagens"][0]["png"] == fx["png"].read_bytes()

    # ZIP + caminho!membro
    assert L.le(fx["zip"])["conteudo"] == "a/leia.txt  10\nb.md  4\n"
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["zip"].parent))
    assert L.ler(f"{fx['zip']}!a/leia.txt")["conteudo"] == "ola\nmundo\n"
    rc_m, m_cli = _chamar({"caminho": f"{fx['zip']}!a/leia.txt"})
    assert rc_m == 0 and m_cli["conteudo"] == "ola\nmundo\n"
    falta = L.le(fx["zip"], membro="nao")
    assert falta["erro"] == "membro não existe" and falta["la_tem"] == ["a/leia.txt", "b.md"]

    # GZIP
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    g = tmp_path / "prova.pdf.gz"
    g.write_bytes(gzip.compress(fx["pdf"].read_bytes()))
    rc_g, rg = _chamar({"caminho": str(g)})
    assert rc_g == 0 and rg["tipo"] == F.PDF and "descomprimido de gzip" in rg["cabecalho"]
    t = tmp_path / "texto.txt.gz"
    t.write_bytes(gzip.compress("linha um\nlinha dois\n".encode()))
    assert L.le(t)["conteudo"] == "linha um\nlinha dois\n"
    assert L.le(t, modo="pagina")["classe_erro"] == "gramatica"
    ruim = tmp_path / "ruim.gz"
    ruim.write_bytes(b"\x1f\x8b\x08\x00" + b"\x00" * 20)
    assert L.le(ruim)["classe_erro"] == "binario" and "gzip não abre" in L.le(ruim)["erro"]

    # ELF fora da tabela
    relf = L.le(fx["elf"])
    assert relf["recusado"] is True and relf["motivo"] == "sem_leitor" and relf["tipo"] == "application/x-elf"


def test_c18_gramatica_parametros_e_versao_muda(fx, tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(fx["pdf"].parent))
    assert _chamar({"caminho": str(fx["pdf"]), "paginas": "x"})[1]["classe_erro"] == "gramatica"
    assert _chamar({"caminho": str(fx["pdf"]), "paginas": "9-"})[1]["erro"] == "página além do fim"
    assert _chamar({"caminho": str(fx["pdf"]), "modo": "pagina", "dpi": 0})[1]["classe_erro"] == "gramatica"
    assert L.le(fx["html"], modo="pagina")["classe_erro"] == "gramatica"
    assert L.le(fx["html"], paginas="1-1")["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], offset=0)["classe_erro"] == "gramatica"
    assert L.le(fx["pdf"], modo="sumario")["sumario"] is None

    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))
    p = tmp_path / "muda.pdf"
    p.write_bytes(fx["pdf"].read_bytes())
    v = _chamar({"caminho": str(p)})[1]["versao"]
    p.write_bytes(fx["pdf"].read_bytes() + b"\n%x")
    r = _chamar({"caminho": str(p), "versao": v})[1]
    assert r["mudou"]["de"] == v and r["cabecalho"].startswith("ARQUIVO MUDOU")


# --- Guardas de descompressão segura, XLSX esparso, exit codes, oplog e seletores no lote ---------
def test_descompressao_segura_gzip_zip_docx_e_xlsx_esparso(tmp_path):
    gz = tmp_path / "bomba.txt.gz"
    with gzip.open(gz, "wb") as fh:
        fh.write(b"\x00" * (512 * 1024))
    rgz = L.ler(gz)
    assert rgz.get("recusado") is True and rgz.get("motivo") == "descompressao" and rgz["exit_code"] == 2

    zp = tmp_path / "pacote.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("grande.txt", "x" * 8192)
    with zipfile.ZipFile(zp) as zf, pytest.raises(F.ErroDescompressao):
        F.ler_zip_seguro(zf, "grande.txt", limite=2048)

    zp2 = tmp_path / "zeros.zip"
    with zipfile.ZipFile(zp2, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.bin", b"\x00" * (512 * 1024))
    with zipfile.ZipFile(zp2) as zf, pytest.raises(F.ErroDescompressao):
        F.ler_zip_seguro(zf, "zeros.bin")

    docx_b = tmp_path / "bomba.docx"
    corpo = (
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>' + (" " * (1024 * 1024)) + "</w:body></w:document>"
    )
    with zipfile.ZipFile(docx_b, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", corpo)
    rdx = L.ler(docx_b)
    assert rdx.get("recusado") is True and rdx.get("motivo") == "descompressao" and rdx["exit_code"] == 2

    xlsx_e = tmp_path / "esparsa.xlsx"
    wb = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1">'
        '<c r="A1" t="inlineStr"><is><t>col1</t></is></c>'
        '<c r="XFD1" t="inlineStr"><is><t>col_ultima</t></is></c>'
        "</row></sheetData>"
        '<mergeCells count="1"><mergeCell ref="A1:XFD5000"/></mergeCells>'
        "</worksheet>"
    )
    with zipfile.ZipFile(xlsx_e, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    rx = L.ler(xlsx_e)
    assert "erro" not in rx and "col1" in rx["conteudo"] and "col_ultima" in rx["conteudo"]
    assert len(rx["conteudo"]) < 64 * 1024


def test_oplog_classificacao_termo_sem_caixa_e_lote_com_seletores(tmp_path):
    r_aus = L.ler(tmp_path / "inexistente.txt")
    assert r_aus["exit_code"] == 1 and "parecidos" not in r_aus
    assert oplog.classificar({"tool": "ler_arquivo", **r_aus})["classe"] == "negativa"

    zp = tmp_path / "a.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.txt", "ola")
    assert L.ler(zp, modo="pagina").get("exit_code") == 2

    assert oplog.classificar({"tool": "ler_arquivo", "recusado": True, "exit_code": 2, "classe_erro": "recusado"})["classe"] == "negada"
    assert oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "caminho"})["classe"] == "negativa"
    assert oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "binario"})["classe"] == "negativa"

    (tmp_path / "README.md").write_text("x")
    (tmp_path / "Outro.txt").write_text("y")
    rt = L.ler(tmp_path, termo="readme")
    assert "README.md" in rt["conteudo"] and "Outro.txt" not in rt["conteudo"]

    rc_esc, r_esc = _chamar({"caminhos": str(tmp_path / "a.txt")})
    assert rc_esc == 2 and r_esc["exit_code"] == 2

    d = tmp_path / "dir"
    d.mkdir()
    (d / "Alpha.txt").write_text("1\n2\n3\n")
    (d / "Beta.txt").write_text("x\n")
    rc_l, r_l = _chamar(
        {"caminhos": [{"caminho": str(d), "termo": "alpha"}, {"caminho": str(d / "Alpha.txt"), "linhas": "2-2"}]}
    )
    assert rc_l == 0 and "Alpha.txt" in r_l["lote"][0]["conteudo"] and "Beta.txt" not in r_l["lote"][0]["conteudo"]
    assert r_l["lote"][1]["linhas"] == [2, 2]


# --- Alcance de leitura e escrita por morada, negativas e lista de extensões ----------------------
@pytest.fixture
def ambiente_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    rel = tmp_path / "release"
    inst = tmp_path / "instancia"
    banc = tmp_path / "bancada"
    pdp = tmp_path / "pdp"
    (rel / "current" / "harness").mkdir(parents=True)
    (inst / "var" / "tmp").mkdir(parents=True)
    (inst / "var" / "fila").mkdir(parents=True)
    (inst / "var" / "log").mkdir(parents=True)
    (inst / "segredos").mkdir(parents=True)
    pdp.mkdir(parents=True)
    (banc / "wt" / "platafirma-core" / "outra-cadeira").mkdir(parents=True)
    (banc / "wt" / "platafirma-casa-espelho" / "seguranca" / "main" / ".git").mkdir(parents=True)
    (banc / "wt" / "platafirma-harness" / "seguranca" / "main" / "bin").mkdir(parents=True)
    (banc / "wt" / "platafirma-rastreador" / "engenharia").mkdir(parents=True)
    (banc / "platafirma-rastreador").mkdir(parents=True)
    (banc / "entrada").mkdir(parents=True)
    monkeypatch.setenv("PLATAFIRMA_RELEASE_RAIZ", str(rel))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(banc))
    monkeypatch.setenv("PDP_DIR", str(pdp))
    return {"release": rel, "instancia": inst, "bancada": banc, "pdp": pdp}


def _motivo(r: dict[str, Any]) -> str:
    assert r.get("recusado") or r.get("erro") or r.get("exit_code", 0) != 0, r
    return str(r.get("motivo") or r.get("falta") or r.get("erro") or "")


def _ler_em_ambiente(caminho: str, *, instancia: Path) -> tuple[dict[str, Any], bool]:
    r = L.ler(caminho, instancia=instancia)
    err = bool(r.get("recusado") or r.get("erro") or int(r.get("exit_code") or 0) != 0)
    return r, err


@pytest.mark.parametrize("caminho", ["/etc/passwd", "/etc", "/", "/nao-existe-921/x.md"])
def test_ler_arquivo_recusa_fora_da_morada(ambiente_harness: dict[str, Any], caminho: str) -> None:
    r, err = _ler_em_ambiente(caminho, instancia=ambiente_harness["instancia"])
    assert err is True and _motivo(r).startswith("fora de morada")


def test_ler_arquivo_morada_symlink_segredo_pdp_fila_e_legitimo(
    ambiente_harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inst = ambiente_harness["instancia"]
    r, _ = _ler_em_ambiente("/etc/passwd", instancia=inst)
    assert str(ambiente_harness["bancada"].resolve()) in _motivo(r)

    elo = inst / "var" / "tmp" / "elo.md"
    elo.symlink_to("/etc/passwd")
    r1, err1 = _ler_em_ambiente(str(elo), instancia=inst)
    assert err1 is True and _motivo(r1).startswith("fora de morada")

    for nome in (".env", "id_rsa", "cert.pem", "priv.key", "cofre.kdbx"):
        inex = ambiente_harness["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / nome
        rs, errs = _ler_em_ambiente(str(inex), instancia=inst)
        assert errs is True and "segredo" in _motivo(rs).lower()

    seg = inst / "segredos" / "token.txt"
    seg.write_text("segredo\n", encoding="utf-8")
    assert "segredo" in _motivo(_ler_em_ambiente(str(seg), instancia=inst)[0]).lower()

    pol = ambiente_harness["pdp"] / "politica.yaml"
    pol.write_text("versao: 1\n", encoding="utf-8")
    assert "segredo" in _motivo(_ler_em_ambiente(str(pol), instancia=inst)[0]).lower()

    fila = inst / "var" / "fila" / "msg.txt"
    fila.write_text("carta\n", encoding="utf-8")
    assert "fila" in _motivo(_ler_em_ambiente(str(fila), instancia=inst)[0]).lower()

    outra = ambiente_harness["bancada"] / "wt" / "platafirma-core" / "outra-cadeira"
    (outra / "x.py").write_text("x = 1\n", encoding="utf-8")
    (outra / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (outra / "fuga").symlink_to("/etc/passwd")
    r_dir, err_dir = _ler_em_ambiente(str(outra), instancia=inst)
    assert err_dir is False and "x.py" in r_dir["entradas"]
    assert ".env" not in r_dir["entradas"] and "fuga" not in r_dir["entradas"]

    monkeypatch.delenv("PLATAFIRMA_BANCADA", raising=False)
    monkeypatch.setenv("PLATAFIRMA_ARQUIVO_BANCADA", str(tmp_path / "sem-bancada"))
    r2, _ = _ler_em_ambiente("/etc/passwd", instancia=inst)
    assert "bancada nao declarada" in _motivo(r2)


def test_write_file_recusa_negadas_extensoes_e_respeita_morada(ambiente_harness: dict[str, Any]) -> None:
    inst = ambiente_harness["instancia"]
    wt = ambiente_harness["bancada"] / "wt" / "platafirma-casa-espelho" / "seguranca" / "main"
    for destino, esperado in (
        (ambiente_harness["release"] / "current" / "harness" / "x.py", "release"),
        (inst / "var" / "log" / "a.log", "log"),
        (inst / "var" / "fila" / "m.txt", "fila"),
        (inst / "segredos" / "s.txt", "segredo"),
        (wt / ".env", "segredo"),
        (wt / ".git" / "config", ".git"),
    ):
        r, err = _chamar_bin(BIN_WRITE, {"path": str(destino), "content": "x\n"}, instancia=inst)
        assert err is True and esperado in _motivo(r).lower() and not destino.exists()

    for nome in ("binario.exe", "foto.png", "semext"):
        r, err = _chamar_bin(BIN_WRITE, {"path": str(wt / nome), "content": "x\n"}, instancia=inst)
        assert err is True and _motivo(r).startswith("tipo:")

    r_csv, err_csv = _chamar_bin(
        BIN_WRITE,
        {"path": str(ambiente_harness["bancada"] / "entrada" / "dados.csv"), "content": "a,b\n1,2\n"},
        instancia=inst,
    )
    assert err_csv is False and r_csv["ok"] is True

    bin_alvo = ambiente_harness["bancada"] / "wt" / "platafirma-harness" / "seguranca" / "main" / "bin" / "meu-verbo"
    r_sem, err_sem = _chamar_bin(BIN_WRITE, {"path": str(bin_alvo), "content": "print(1)\n"}, instancia=inst)
    assert err_sem is True and "#!" in _motivo(r_sem)
    r_com, err_com = _chamar_bin(
        BIN_WRITE, {"path": str(bin_alvo), "content": "#!/usr/bin/env python3\nprint(1)\n"}, instancia=inst
    )
    assert err_com is False and r_com["ok"] is True


def test_inteiro_true_le_arquivo_acima_do_orcamento_padrao_numa_chamada(tmp_path: Path) -> None:
    grande = tmp_path / "busca.md"
    texto = "".join(f"linha {i:04d} — referência completa do verbo na casa\n" for i in range(2200))
    assert len(texto.encode("utf-8")) > 110_000
    grande.write_text(texto, encoding="utf-8")

    # Sem `inteiro`, `ler_arquivo` mantém o orçamento padrão (40 KB) e pagina
    parcial = L.le(grande)
    assert parcial["proximo"] != L.FIM
    assert len(parcial["conteudo"].encode("utf-8")) <= L.ORCAMENTO_PADRAO

    # Com `inteiro=True`, tanto `le`/`ler` quanto o binário `ler_arquivo` devolvem tudo numa chamada
    total_le = L.le(grande, inteiro=True)
    assert total_le["proximo"] == L.FIM
    assert total_le["conteudo"] == texto

    rc_bin, res_bin = _chamar({"caminho": str(grande), "inteiro": True})
    assert rc_bin == 0
    assert res_bin["proximo"] == L.FIM
    assert res_bin["conteudo"] == texto

    rc_lote, res_lote = _chamar({"caminhos": [{"caminho": str(grande), "inteiro": True}]})
    assert rc_lote == 0
    assert res_lote["lote"][0]["proximo"] == L.FIM
    assert res_lote["lote"][0]["conteudo"] == texto

    # Arquivo vazio com offset > 0 recusa como `offset além do fim` (exit 2)
    vazio = tmp_path / "vazio.md"
    vazio.write_bytes(b"")
    r_vazio = L.le(vazio, offset=1)
    assert r_vazio["exit_code"] == 2 and r_vazio["erro"] == "offset além do fim"
