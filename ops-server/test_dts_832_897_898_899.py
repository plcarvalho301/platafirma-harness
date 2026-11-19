"""Testes de contrato para os DTs 832, 897, 898 e 899 (ler_arquivo no harness)."""
from __future__ import annotations

import gzip
import os
import sys
import threading
import zipfile
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
os.environ.setdefault("PF_HARNESS", str(_RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(_RAIZ / "lib"))

import formatos as F
import leitura as L
import oplog
import server as S


# --- DT 832 + DT 899: descompressão segura em streaming -------------------------------------------
def test_dt832_gzip_acima_do_teto_recusa_em_streaming(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "MEMBRO_MAX", 4096)
    gz_path = tmp_path / "bomba.txt.gz"
    with gzip.open(gz_path, "wb") as fh:
        fh.write(b"A" * 16384)
    r = L.le(gz_path)
    assert r.get("recusado") is True
    assert r.get("motivo") == "descompressao"
    assert r.get("exit_code") == 2


def test_dt832_gzip_razao_alta_recusa(tmp_path):
    gz_path = tmp_path / "zeros.txt.gz"
    # 512 KiB de zeros comprime em ~600 bytes -> razão > 800x (> 100x)
    with gzip.open(gz_path, "wb") as fh:
        fh.write(b"\x00" * (512 * 1024))
    r = L.le(gz_path)
    assert r.get("recusado") is True
    assert r.get("motivo") == "descompressao"
    assert r.get("exit_code") == 2


def test_dt832_zip_membro_acima_do_teto_recusa(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "MEMBRO_MAX", 2048)
    zp = tmp_path / "pacote.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("grande.txt", "x" * 8192)
    r = L.le(zp, membro="grande.txt")
    assert r.get("recusado") is True
    assert r.get("motivo") == "descompressao"
    assert r.get("exit_code") == 2


# --- DT 899: Indice.extra sob trava + orçamento de memória + XLSX esparso -------------------------
def test_dt899_indice_extra_orcamento_e_concorrencia(monkeypatch):
    L.esvazia_cache()
    monkeypatch.setattr(L, "CACHE_EXTRA_BYTES_MAX", 1024)
    idx = L.Indice(versao="abc123", tamanho=100, linhas_total=10, marcos=[0],
                   multibyte=0, invalidos=0, cp1252_invalidos=0, cabeca=b"")
    erros = []

    def trabalhador(tid: int) -> None:
        try:
            for k in range(25):
                L._extra_unidade_gravar(idx, "application/pdf", tid * 100 + k, ("x" * 200, False))
                L._extra_unidade_obter(idx, "application/pdf", tid * 100 + k)
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    threads = [threading.Thread(target=trabalhador, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not erros
    assert L._EXTRA_ESTADO["bytes"] <= 1024


def test_dt899_xlsx_grade_esparsa_e_merge_gigante_nao_explodem(tmp_path):
    xlsx = tmp_path / "esparsa.xlsx"
    wb = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
        ' Target="worksheets/sheet1.xml"/></Relationships>'
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>'
        '<row r="1">'
        '<c r="A1" t="inlineStr"><is><t>col1</t></is></c>'
        '<c r="XFD1" t="inlineStr"><is><t>col_ultima</t></is></c>'
        '</row>'
        '</sheetData>'
        '<mergeCells count="1"><mergeCell ref="A1:XFD5000"/></mergeCells>'
        '</worksheet>'
    )
    with zipfile.ZipFile(xlsx, "w") as zf:
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    r = L.le(xlsx)
    assert "erro" not in r
    assert "| col1 | col_ultima |" in r["conteudo"]


# --- DT 898: exit codes, oplog.classificar e dur_ms -----------------------------------------------
def test_dt898_ausencia_exit1_e_nao_marca_erro(tmp_path):
    r = L.le(tmp_path / "inexistente.txt")
    assert r["exit_code"] == 1
    assert "parecidos" not in r
    assert S._deve_marcar_erro(r) is False


def test_dt898_sem_render_usa_exit2_nao_exit4(tmp_path):
    zp = tmp_path / "a.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.txt", "ola")
    r = L.le(zp, modo="pagina")
    assert r.get("motivo") == "sem_render"
    assert r.get("exit_code") == 2


def test_dt898_oplog_classifica_recusado_e_ausencia_antes_de_exit2():
    c_rec = oplog.classificar({"tool": "ler_arquivo", "recusado": True, "exit_code": 2, "classe_erro": "recusado"})
    assert c_rec["classe"] == "negada"
    c_cam = oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "caminho"})
    assert c_cam["classe"] == "negativa"
    c_bin = oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "binario"})
    assert c_bin["classe"] == "negativa"


def test_dt898_le_um_arquivo_grava_dur_ms(tmp_path, monkeypatch):
    arq = tmp_path / "oi.txt"
    arq.write_text("ola\n")
    eventos = []
    monkeypatch.setattr(S, "_autoriza", lambda *a, **k: None)
    monkeypatch.setattr(S, "_bancada", lambda: tmp_path)
    monkeypatch.setattr(S, "_nega_fila", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_segredo", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_morada", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_analise", lambda *a, **k: False)
    monkeypatch.setattr(S, "_audit", lambda **kw: eventos.append(kw))
    ident = {"cadeira": "engenharia", "sessao_id": "s1", "ordem_id": "o1"}
    r = S._le_um_arquivo(str(arq), {}, ident, "ler_arquivo")
    assert "conteudo" in r
    assert eventos and isinstance(eventos[-1].get("dur_ms"), int)
    assert eventos[-1]["dur_ms"] >= 0


# --- DT 897: esquema caminhos, seletores por item, str escalar, termo sem caixa, bancada ativa ----
def test_dt897_esquema_plano_expoe_caminhos_tipado():
    bruto = {
        "type": "object",
        "properties": {
            "caminhos": {
                "anyOf": [
                    {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "object"}]}},
                    {"type": "null"},
                ]
            }
        },
    }
    plano = S._esquema_plano(bruto)
    items = plano["properties"]["caminhos"]["items"]
    assert items["type"] == "object"
    for campo in ("caminho", "linhas", "paginas", "modo", "offset", "versao", "encoding",
                  "termo", "dpi", "max_bytes", "inteiro"):
        assert campo in items["properties"]


def test_dt897_rejeita_caminhos_str_escalar(monkeypatch):
    monkeypatch.setattr(S, "_sessao_resolve", lambda sid: {"cadeira": "engenharia", "sessao_id": "s", "ordem_id": "o"})
    monkeypatch.setattr(S, "_carimba_turno", lambda *a, **k: None)
    r = S.ler_arquivo(caminhos="/tmp/a.txt")
    assert r["exit_code"] == 2


def test_dt897_termo_diretorio_sem_caixa(tmp_path):
    (tmp_path / "README.md").write_text("x")
    (tmp_path / "Outro.txt").write_text("y")
    r = L.le(tmp_path, termo="readme")
    assert "README.md" in r["conteudo"]
    assert "Outro.txt" not in r["conteudo"]


def test_dt897_resolve_bancada_ativa_e_separa_membro(tmp_path, monkeypatch):
    wt = tmp_path / "wt" / "platafirma-harness" / "engenharia" / "slug-1"
    wt.mkdir(parents=True)
    zp = wt / "dados.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.txt", "dentro")
    S._BANCADA_ATIVA[("sess-x", "platafirma-harness")] = wt
    try:
        arq, membro = S._separa_membro(
            "platafirma-harness/dados.zip!a.txt",
            bancada=tmp_path, cadeira="engenharia", sessao_id="sess-x",
        )
        assert arq == "platafirma-harness/dados.zip"
        assert membro == "a.txt"
        resolvido, erro, _ = S._resolve_leitura_relativo(
            "platafirma-harness/dados.zip", tmp_path, "engenharia", "sess-x",
        )
        assert erro is None and resolvido == zp
    finally:
        S._BANCADA_ATIVA.pop(("sess-x", "platafirma-harness"), None)


def test_dt897_lote_propaga_todos_seletores_por_item(tmp_path, monkeypatch):
    d = tmp_path / "dir"
    d.mkdir()
    (d / "Alpha.txt").write_text("1\n2\n3\n")
    (d / "Beta.txt").write_text("x\n")
    monkeypatch.setattr(S, "PF_TOOLS_LOTE", True)
    monkeypatch.setattr(S, "_sessao_resolve", lambda sid: {"cadeira": "engenharia", "sessao_id": "s2", "ordem_id": "o2"})
    monkeypatch.setattr(S, "_carimba_turno", lambda *a, **k: None)
    monkeypatch.setattr(S, "_autoriza", lambda *a, **k: None)
    monkeypatch.setattr(S, "_bancada", lambda: tmp_path)
    monkeypatch.setattr(S, "_nega_fila", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_segredo", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_morada", lambda *a, **k: None)
    monkeypatch.setattr(S, "_nega_analise", lambda *a, **k: False)
    monkeypatch.setattr(S, "_audit", lambda **kw: None)
    r = S.ler_arquivo(caminhos=[
        {"caminho": str(d), "termo": "alpha"},
        {"caminho": str(d / "Alpha.txt"), "offset": 2, "max_bytes": 2},
    ])
    assert "Alpha.txt" in r["lote"][0]["conteudo"]
    assert "Beta.txt" not in r["lote"][0]["conteudo"]
    assert r["lote"][1]["bytes"] == [2, 4]
