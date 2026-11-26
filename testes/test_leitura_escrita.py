# componente: componente:leitura
"""Testes de leitura de arquivos no harness por processo (story #4342, t4)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

HARNESS_BIN = Path(__file__).resolve().parents[1] / "bin"
sys.path.insert(0, str(HARNESS_BIN.parent / "lib"))
from leitura.leitura import ler as _ler_nucleo  # noqa: E402


@pytest.fixture(autouse=True)
def _morada_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))


def test_ler_arquivo_texto_paginacao_versao_e_diretorio(tmp_path: Path):
    arq = tmp_path / "grande.txt"
    arq.write_text("".join(f"linha-{i:04d} " + ("x" * 60) + "\n" for i in range(1, 200)), encoding="utf-8")

    r1 = _ler_nucleo(str(arq), max_bytes=2048)
    assert int(r1.get("exit_code") or 0) == 0
    assert r1["linhas"][0] == 1
    assert r1["linhas"][1] < 200
    assert "proximo_args" in r1

    # Continuação usando proximo_args e versao
    r2 = _ler_nucleo(
        str(r1["proximo_args"]["caminho"]),
        linhas=r1["proximo_args"].get("linhas"),
        versao=r1["proximo_args"].get("versao"),
        max_bytes=2048,
    )
    assert int(r2.get("exit_code") or 0) == 0
    assert r2["linhas"][0] == r1["linhas"][1] + 1

    # Diretório com filtro termo
    (tmp_path / "alpha.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# b\n", encoding="utf-8")
    rd = _ler_nucleo(str(tmp_path), termo="alpha")
    assert int(rd.get("exit_code") or 0) == 0
    assert rd["entradas"] == ["alpha.py"]


def _pdf_minimo(texto: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def test_ler_arquivo_formatos_pdf_e_docx(tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(_pdf_minimo("Ola PDF do harness"))

    py_h = Path("/opt/platafirma/current/venv/harness/bin/python")
    py = str(py_h) if py_h.is_file() else sys.executable
    env = {**os.environ, "PYTHONPATH": str(HARNESS_BIN.parent / "lib")}
    cp = subprocess.run(
        [
            py,
            "-c",
            "import json, sys; from leitura.leitura import ler; "
            "print(json.dumps(ler(sys.argv[1], paginas='1'), ensure_ascii=False))",
            str(pdf),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    rpdf = json.loads(cp.stdout)
    assert int(rpdf.get("exit_code") or 0) == 0
    assert rpdf["tipo"] == "application/pdf"
    assert "Ola PDF do harness" in rpdf["conteudo"]

    docx = tmp_path / "doc.docx"
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Texto DOCX</w:t></w:r></w:p></w:body></w:document>",
        )
    rdocx = _ler_nucleo(str(docx))
    assert int(rdocx.get("exit_code") or 0) == 0
    assert "Texto DOCX" in rdocx["conteudo"]


def test_recusa_segredo_e_fila_em_leitura(tmp_path: Path):
    inst = tmp_path / "casa"
    fila_arq = inst / "var" / "fila" / "msg.jsonl"
    fila_arq.parent.mkdir(parents=True)
    fila_arq.write_text("{}\n", encoding="utf-8")
    env_arq = tmp_path / ".env.prod"
    env_arq.write_text("SECRET=1\n", encoding="utf-8")

    r1 = _ler_nucleo(str(env_arq), instancia=inst)
    assert r1["exit_code"] == 4 and r1["recusado"] is True

    r2 = _ler_nucleo(str(fila_arq), instancia=inst)
    assert r2["exit_code"] == 4 and r2["recusado"] is True
