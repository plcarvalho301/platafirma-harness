# componente: componente:escrita
"""Testes de leitura e escrita de arquivos no harness por processo (story #4342, t4)."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

HARNESS_BIN = Path(__file__).resolve().parents[1] / "bin"
BIN_LER = HARNESS_BIN / "ler_arquivo"
BIN_WRITE = HARNESS_BIN / "write_file"


_PY_HARNESS = Path("/opt/platafirma/current/venv/harness/bin/python")


@pytest.fixture(autouse=True)
def _morada_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(tmp_path))


def _chamar(binario: Path, payload: dict) -> tuple[int, dict]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    cp = subprocess.run(
        [py, str(binario)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    return cp.returncode, json.loads(cp.stdout)


def test_write_file_inteiro_trecho_e_patch_por_processo(tmp_path: Path):
    inst = tmp_path / "inst"
    alvo = inst / "var" / "tmp" / "ordem-teste" / "sub" / "notas.txt"
    ctx = {"instancia": str(inst), "ordem_id": "ordem-teste"}
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "content": "linha 1\nlinha 2\nlinha 3\n"})
    assert rc == 0 and res["ok"] is True and res["substituiu"] is False

    # Troca por trecho
    rc, res = _chamar(
        BIN_WRITE,
        {**ctx, "path": str(alvo), "trecho": {"antes": "linha 2", "depois": "linha DOIS"}},
    )
    assert rc == 0 and res["ok"] is True and res["ocorrencias"] == 1
    assert "linha DOIS" in alvo.read_text(encoding="utf-8")

    # Patch unified diff
    patch = "--- a/notas.txt\n+++ b/notas.txt\n@@ -1,3 +1,3 @@\n linha 1\n-linha DOIS\n+linha 2-patch\n linha 3\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch})
    assert rc == 0 and res["ok"] is True
    assert "linha 2-patch" in alvo.read_text(encoding="utf-8")


def test_write_file_fita_sem_turno_vale_a_sessao_dt958_dt962(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sem turno na superfície (ordem_id ausente), a fita é a sessão que a porta exporta em PF_SESSAO."""
    inst = tmp_path / "inst"
    monkeypatch.delenv("PF_ORDEM_ID", raising=False)
    monkeypatch.delenv("PF_SESSAO", raising=False)
    sessao = "5df980f4-aca5-4525-95c5-199f4d6820fd"
    alvo = inst / "var" / "tmp" / sessao / "plano.md"
    carga = {"instancia": str(inst), "path": str(alvo), "content": "plano\n"}

    # sem turno e sem sessão: continua recusando, a fita não foi declarada
    rc, res = _chamar(BIN_WRITE, carga)
    assert rc == 4 and "exige fita declarada" in json.dumps(res, ensure_ascii=False)
    assert not alvo.exists()

    # com a sessão exportada pela porta: grava na pasta da sessão
    monkeypatch.setenv("PF_SESSAO", sessao)
    rc, res = _chamar(BIN_WRITE, carga)
    assert rc == 0 and res["ok"] is True
    assert alvo.read_text(encoding="utf-8") == "plano\n"

    # a pasta de outra sessão continua fora da fita desta
    alheia = inst / "var" / "tmp" / "outra-sessao" / "plano.md"
    rc, res = _chamar(BIN_WRITE, {**carga, "path": str(alheia)})
    assert rc == 4 and not alheia.exists()

    # o turno, quando chega, vence a sessão
    monkeypatch.setenv("PF_ORDEM_ID", "ordem-teste")
    turno = inst / "var" / "tmp" / "ordem-teste" / "plano.md"
    rc, res = _chamar(BIN_WRITE, {**carga, "path": str(turno)})
    assert rc == 0 and turno.exists()

def test_ler_arquivo_texto_paginacao_versao_e_diretorio(tmp_path: Path):
    arq = tmp_path / "grande.txt"
    arq.write_text("".join(f"linha-{i:04d} " + ("x" * 60) + "\n" for i in range(1, 200)), encoding="utf-8")

    rc, r1 = _chamar(BIN_LER, {"caminho": str(arq), "max_bytes": 2048})
    assert rc == 0
    assert r1["linhas"][0] == 1
    assert r1["linhas"][1] < 200
    assert "proximo_args" in r1

    # Continuação usando proximo_args e versao
    rc, r2 = _chamar(BIN_LER, {**r1["proximo_args"], "max_bytes": 2048})
    assert rc == 0
    assert r2["linhas"][0] == r1["linhas"][1] + 1

    # Diretório com filtro termo
    (tmp_path / "alpha.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# b\n", encoding="utf-8")
    rc, rd = _chamar(BIN_LER, {"caminho": str(tmp_path), "termo": "alpha"})
    assert rc == 0
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

    rc, rpdf = _chamar(BIN_LER, {"caminho": str(pdf), "paginas": "1"})
    assert rc == 0
    assert rpdf["tipo"] == "application/pdf"
    assert "Ola PDF do harness" in rpdf["conteudo"]

    docx = tmp_path / "doc.docx"
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Texto DOCX</w:t></w:r></w:p></w:body></w:document>",
        )
    rc, rdocx = _chamar(BIN_LER, {"caminho": str(docx)})
    assert rc == 0
    assert "Texto DOCX" in rdocx["conteudo"]


def test_recusa_segredo_e_fila_em_leitura_e_escrita(tmp_path: Path):
    inst = tmp_path / "casa"
    fila_arq = inst / "var" / "fila" / "msg.jsonl"
    fila_arq.parent.mkdir(parents=True)
    fila_arq.write_text("{}\n", encoding="utf-8")
    env_arq = tmp_path / ".env.prod"
    env_arq.write_text("SECRET=1\n", encoding="utf-8")

    rc, r1 = _chamar(BIN_LER, {"caminho": str(env_arq), "instancia": str(inst)})
    assert rc == 4 and r1["recusado"] is True

    rc, r2 = _chamar(BIN_LER, {"caminho": str(fila_arq), "instancia": str(inst)})
    assert rc == 4 and r2["recusado"] is True

    rc, r3 = _chamar(BIN_WRITE, {"path": str(env_arq), "content": "x", "instancia": str(inst)})
    assert rc == 4 and r3["recusado"] is True

    rc, r4 = _chamar(BIN_WRITE, {"path": str(fila_arq), "content": "x", "instancia": str(inst)})
    assert rc == 4 and r4["recusado"] is True
