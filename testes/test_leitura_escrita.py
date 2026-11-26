# componente: componente:escrita
"""Testes de leitura e escrita de arquivos no harness por processo (story #4342, t4)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

HARNESS_BIN = Path(__file__).resolve().parents[1] / "bin"
BIN_WRITE = HARNESS_BIN / "write_file"
sys.path.insert(0, str(HARNESS_BIN.parent / "lib"))
from leitura.leitura import ler as _ler_nucleo  # noqa: E402


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


def test_write_file_patch_sem_numeros_de_linha_ou_sem_efeito_falha_dt1333(tmp_path: Path):
    """DT 1333: patch que não aplica (sem números de linha, sem hunks ou sem efeito) falha e não diz substituiu."""
    inst = tmp_path / "inst"
    alvo = inst / "var" / "tmp" / "ordem-teste" / "evento.md"
    ctx = {"instancia": str(inst), "ordem_id": "ordem-teste"}
    original = "linha 1\nlinha 2\nlinha 3\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "content": original})
    assert rc == 0 and res["ok"] is True

    # 1. Diff unificado sem números de linha (@@ @@)
    patch_sem_num = "--- a/evento.md\n+++ b/evento.md\n@@ @@\n linha 1\n-linha 2\n+linha DOIS\n linha 3\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch_sem_num})
    assert rc == 2 and not res.get("ok") and "substituiu" not in res
    assert "cabeçalho de hunk inválido" in res["falta"]
    assert "@@ -l,c +l,c @@" in res["proximo"]
    assert alvo.read_text(encoding="utf-8") == original

    # 2. Cabeçalhos ---/+++ sem nenhum hunk @@
    patch_sem_hunk = "--- a/evento.md\n+++ b/evento.md\n-linha 2\n+linha DOIS\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch_sem_hunk})
    assert rc == 2 and not res.get("ok") and "substituiu" not in res
    assert alvo.read_text(encoding="utf-8") == original

    # 3. Um hunk válido misturado com um hunk sem números de linha: falha tudo sem aplicar parcial
    patch_misto = (
        "--- a/evento.md\n+++ b/evento.md\n"
        "@@ -1,3 +1,3 @@\n linha 1\n-linha 2\n+linha DOIS\n linha 3\n"
        "@@ @@\n-linha 3\n+linha TRES\n"
    )
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch_misto})
    assert rc == 2 and not res.get("ok") and "substituiu" not in res
    assert alvo.read_text(encoding="utf-8") == original

    # 4. Hunk com cabeçalho válido mas corpo malformado (sem prefixos de diff)
    patch_corpo_invalido = "--- a/evento.md\n+++ b/evento.md\n@@ -1,3 +1,3 @@\nlinha sem prefixo\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch_corpo_invalido})
    assert rc == 1 and not res.get("ok") and "substituiu" not in res
    assert alvo.read_text(encoding="utf-8") == original

    # 5. Patch válido que não altera nada no arquivo existente
    patch_noop = "--- a/evento.md\n+++ b/evento.md\n@@ -1,3 +1,3 @@\n linha 1\n linha 2\n linha 3\n"
    rc, res = _chamar(BIN_WRITE, {**ctx, "path": str(alvo), "patch": patch_noop})
    assert rc == 1 and not res.get("ok") and "substituiu" not in res
    assert alvo.read_text(encoding="utf-8") == original


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


def test_recusa_segredo_e_fila_em_leitura_e_escrita(tmp_path: Path):
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

    rc, r3 = _chamar(BIN_WRITE, {"path": str(env_arq), "content": "x", "instancia": str(inst)})
    assert rc == 4 and r3["recusado"] is True

    rc, r4 = _chamar(BIN_WRITE, {"path": str(fila_arq), "content": "x", "instancia": str(inst)})
    assert rc == 4 and r4["recusado"] is True
