"""Guardas das DTs 832, 897, 898 e 899 migradas de ops-server/test_dts_832_897_898_899.py (#4348).

O ler_arquivo da casa nova mora em lib/leitura. O que a porta antiga fazia e a casa nova
mantém fica guardado aqui; o que saiu está dito em remocao-no-pr.
"""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ / "lib"))

import oplog  # noqa: E402
from leitura import formatos as F  # noqa: E402
from leitura import leitura as L  # noqa: E402

BIN_LER = _RAIZ / "bin" / "ler_arquivo"
_PY_HARNESS = Path("/opt/platafirma/current/venv/harness/bin/python")


@pytest.fixture(autouse=True)
def _morada_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))


def _chamar(payload: dict) -> tuple[int, dict]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    cp = subprocess.run(
        [py, str(BIN_LER)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    return cp.returncode, json.loads(cp.stdout)


# --- DT 832: descompressão segura -----------------------------------------------------------------
def test_dt832_gzip_bomba_recusa_com_motivo_descompressao(tmp_path):
    """Bomba de compressão gzip recusa com motivo=descompressao (DT 832, DT 919)."""
    gz = tmp_path / "bomba.txt.gz"
    with gzip.open(gz, "wb") as fh:
        fh.write(b"\x00" * (512 * 1024))
    r = L.ler(gz)
    assert r.get("recusado") is True
    assert r.get("motivo") == "descompressao"
    assert r["exit_code"] == 2
    assert "conteudo" not in r


def test_dt832_membro_zip_acima_do_teto_recusa(tmp_path):
    zp = tmp_path / "pacote.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("grande.txt", "x" * 8192)
    with zipfile.ZipFile(zp) as zf, pytest.raises(F.ErroDescompressao):
        F.ler_zip_seguro(zf, "grande.txt", limite=2048)


def test_dt832_membro_zip_razao_alta_recusa(tmp_path):
    zp = tmp_path / "zeros.zip"
    with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.bin", b"\x00" * (512 * 1024))
    with zipfile.ZipFile(zp) as zf, pytest.raises(F.ErroDescompressao):
        F.ler_zip_seguro(zf, "zeros.bin")


def test_dt832_docx_bomba_recusa_com_motivo_descompressao(tmp_path):
    docx = tmp_path / "bomba.docx"
    corpo = (
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>' + (" " * (1024 * 1024)) + "</w:body></w:document>"
    )
    with zipfile.ZipFile(docx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", corpo)
    r = L.ler(docx)
    assert r.get("recusado") is True
    assert r.get("motivo") == "descompressao"
    assert r["exit_code"] == 2


# --- DT 899: XLSX esparso -------------------------------------------------------------------------
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
    with zipfile.ZipFile(xlsx, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    r = L.ler(xlsx)
    assert "erro" not in r and "falta" not in r, r
    assert "col1" in r["conteudo"] and "col_ultima" in r["conteudo"]
    assert len(r["conteudo"]) < 64 * 1024


# --- DT 898: códigos de saída e classificação no oplog --------------------------------------------
def test_dt898_ausencia_sai_exit1_sem_parecidos(tmp_path):
    r = L.ler(tmp_path / "inexistente.txt")
    assert r["exit_code"] == 1
    assert "parecidos" not in r
    assert oplog.classificar({"tool": "ler_arquivo", **r})["classe"] == "negativa"


def test_dt898_sem_render_sai_exit2_e_nao_exit4(tmp_path):
    zp = tmp_path / "a.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.txt", "ola")
    r = L.ler(zp, modo="pagina")
    assert r.get("exit_code") == 2, r


def test_dt898_oplog_classifica_recusado_e_ausencia_antes_de_exit2():
    c_rec = oplog.classificar({"tool": "ler_arquivo", "recusado": True, "exit_code": 2, "classe_erro": "recusado"})
    assert c_rec["classe"] == "negada"
    c_cam = oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "caminho"})
    assert c_cam["classe"] == "negativa"
    c_bin = oplog.classificar({"tool": "ler_arquivo", "exit_code": 2, "classe_erro": "binario"})
    assert c_bin["classe"] == "negativa"


# --- DT 897: caminhos, termo sem caixa e seletores por item ---------------------------------------
def test_dt897_termo_diretorio_sem_caixa(tmp_path):
    (tmp_path / "README.md").write_text("x")
    (tmp_path / "Outro.txt").write_text("y")
    r = L.ler(tmp_path, termo="readme")
    assert "README.md" in r["conteudo"]
    assert "Outro.txt" not in r["conteudo"]


def test_dt897_rejeita_caminhos_texto_escalar(tmp_path):
    rc, r = _chamar({"caminhos": str(tmp_path / "a.txt")})
    assert rc == 2 and r["exit_code"] == 2


def test_dt897_lote_aplica_seletores_por_item(tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    (d / "Alpha.txt").write_text("1\n2\n3\n")
    (d / "Beta.txt").write_text("x\n")
    rc, r = _chamar({
        "caminhos": [
            {"caminho": str(d), "termo": "alpha"},
            {"caminho": str(d / "Alpha.txt"), "linhas": "2-2"},
        ]
    })
    assert rc == 0, r
    assert "Alpha.txt" in r["lote"][0]["conteudo"]
    assert "Beta.txt" not in r["lote"][0]["conteudo"]
    assert r["lote"][1]["linhas"] == [2, 2]
