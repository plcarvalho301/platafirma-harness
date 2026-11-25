# componente: componente:leitura
"""Testes do extrator isolado e dos formatos endurecidos (story #4442, t4)."""
from __future__ import annotations

import gzip
import io
import os
import socket
import threading
import zipfile
from pathlib import Path

import pytest

from leitura import extrator, formatos as F

try:
    import pymupdf
except ImportError:
    pymupdf = None


def _criar_zip(entradas: dict[str, bytes], compressao: int = zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compressao) as zf:
        for nome, dados in entradas.items():
            zf.writestr(nome, dados)
    return buf.getvalue()


def _criar_docx(document_xml: bytes) -> bytes:
    return _criar_zip({"word/document.xml": document_xml})


def _criar_pdf_bytes(paginas: list[str]) -> bytes:
    if pymupdf is None:
        return b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF\n"
    doc = pymupdf.open()
    for texto in paginas:
        page = doc.new_page()
        if texto:
            page.insert_text((72, 72), texto)
    dados = doc.tobytes()
    doc.close()
    return dados


def _abrir_fd_temporario(tmp_path: Path, nome: str, dados: bytes) -> int:
    arq = tmp_path / nome
    arq.write_bytes(dados)
    return os.open(arq, os.O_RDONLY | os.O_CLOEXEC)


# ------------------------------------------------------------------ XML sem DTD nem entidade
def test_xml_com_doctype_e_entidade_sai_2_descompressao_recusada(tmp_path: Path) -> None:
    xml_xxe = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b"<w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body></w:document>"
    )
    with pytest.raises(F.ErroDescompressao):
        F.parse_xml_seguro(xml_xxe)

    # Também bloqueado quando empacotado dentro de DOCX passando pelo extrator isolado.
    fd = _abrir_fd_temporario(tmp_path, "hostil.docx", _criar_docx(xml_xxe))
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_em_subprocesso(fd, {"chave": "obra:1"})
        assert exc.value.saida == 2
        assert exc.value.recusa.codigo == "descompressao-recusada"
    finally:
        os.close(fd)


def test_xml_billion_laughs_bloqueado_no_parser() -> None:
    bomba_xml = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE lolz ['
        b'<!ENTITY lol "lol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
        b"]><root>&lol2;</root>"
    )
    with pytest.raises(F.ErroDescompressao):
        F.parse_xml_seguro(bomba_xml)


# ------------------------------------------------------------------ bombas ZIP / GZIP / aninhamento
def test_bomba_zip_razao_acima_de_100_sai_2_descompressao_recusada(tmp_path: Path) -> None:
    # 512 KiB de zeros comprimem para ~500 bytes -> razão > 1000x
    bomba = _criar_zip({"bomba.txt": b"\x00" * (512 * 1024)})
    fd = _abrir_fd_temporario(tmp_path, "bomba.zip", bomba)
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_em_subprocesso(fd, {"chave": "obra:2", "membro": "bomba.txt"})
        assert exc.value.saida == 2
        assert exc.value.recusa.codigo == "descompressao-recusada"
    finally:
        os.close(fd)


def test_zip_com_excesso_de_membros_e_soma_descomprimida_recusado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(F, "MEMBROS_PACOTE_MAX", 3)
    pacote = _criar_zip({f"a{i}.txt": b"ok" for i in range(4)})
    with zipfile.ZipFile(io.BytesIO(pacote)) as zf:
        with pytest.raises(F.ErroDescompressao):
            F.validar_pacote_zip(zf, max_membros=3)

    orc = F.OrcamentoDescompressao(limite_total=10)
    orc.consumir(6)
    with pytest.raises(F.ErroDescompressao):
        orc.consumir(5)


def test_zip_aninhado_alem_de_um_nivel_sai_2_descompressao_recusada(tmp_path: Path) -> None:
    interno = _criar_zip({"dentro.txt": b"segredo"})
    externo = _criar_zip({"camada.zip": interno})
    fd = _abrir_fd_temporario(tmp_path, "aninhado.zip", externo)
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_em_subprocesso(fd, {"chave": "obra:3", "membro": "camada.zip"})
        assert exc.value.saida == 2
        assert exc.value.recusa.codigo == "descompressao-recusada"
    finally:
        os.close(fd)


def test_gzip_normal_e_gzip_aninhado(tmp_path: Path) -> None:
    gz_ok = gzip.compress(b"conteudo valido em utf-8\n")
    fd_ok = _abrir_fd_temporario(tmp_path, "ok.gz", gz_ok)
    try:
        res = extrator.extrair_em_subprocesso(fd_ok, {"chave": "obra:4"})
        assert res["conteudo"] == "conteudo valido em utf-8\n"
    finally:
        os.close(fd_ok)

    gz_zip = gzip.compress(_criar_zip({"a.txt": b"x"}))
    fd_an = _abrir_fd_temporario(tmp_path, "an.gz", gz_zip)
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_em_subprocesso(fd_an, {"chave": "obra:5"})
        assert exc.value.saida == 2
        assert exc.value.recusa.codigo == "descompressao-recusada"
    finally:
        os.close(fd_an)


# ------------------------------------------------------------------ PDF, avisos fora do conteúdo, PNG
class _PdfFalso(F.Documento):
    def __init__(self, _fonte: object) -> None:
        super().__init__(tipo=F.PDF, unidade="pagina", n=2, render=True)

    def _extrai(self, i: int) -> str:
        if i == 1:
            return "Primeira pagina do relatorio"
        self.sem_texto.append(2)
        self.avisos.append("pagina_2_sem_texto")
        return ""

    def imagem(self, i: int, dpi: int = F.DPI_PADRAO) -> tuple[bytes | None, str, dict]:
        # PNG 1x1 válido mínimo
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00"
            b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return png, F.PNG, {"dimensoes": (1, 1), "dpi": dpi}


def test_pdf_texto_sem_texto_e_modo_pagina_via_socket_scm_rights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if pymupdf is None:
        monkeypatch.setattr(F, "_Pdf", _PdfFalso)
    pdf_bytes = _criar_pdf_bytes(["Primeira pagina do relatorio", ""])
    fd = _abrir_fd_temporario(tmp_path, "relatorio.pdf", pdf_bytes)

    sock_path = tmp_path / "extrator.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(2)

    def _atender() -> None:
        for _ in range(2):
            conn, _ = srv.accept()
            with conn:
                extrator.servir_conexao(conn)

    th = threading.Thread(target=_atender, daemon=True)
    th.start()
    try:
        res_txt = extrator.extrair_via_socket(
            sock_path, fd, {"chave": "obra:10", "modo": "texto", "paginas": [1, 2]}
        )
        assert "Primeira pagina do relatorio" in res_txt["conteudo"]
        assert "<!--" not in res_txt["conteudo"]
        assert res_txt["sem_texto"] == [2]
        assert any("pagina_2_sem_texto" in a for a in res_txt["avisos"])

        res_img = extrator.extrair_via_socket(
            sock_path, fd, {"chave": "obra:10", "modo": "pagina", "paginas": [1, 1], "dpi": 72}
        )
        assert res_img["conteudo"] is None
        assert len(res_img["imagens"]) == 1
        img = res_img["imagens"][0]
        assert img["pagina"] == 1
        assert img["mime"] == "image/png"
        assert img["largura"] > 0 and img["altura"] > 0
        assert len(img["sha256"]) == 64
    finally:
        os.close(fd)
        th.join(timeout=3.0)
        srv.close()


# ------------------------------------------------------------------ XLSX teto de células
def test_xlsx_truncado_marca_parcial_e_aviso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(F, "CELULAS_XLSX_MAX", 2)
    wb = (
        b'<?xml version="1.0"?>'
        b'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        b'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        b'<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        b'<?xml version="1.0"?>'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        b'<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
    )
    sheet = (
        b'<?xml version="1.0"?>'
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b"<sheetData>"
        b'<row r="1"><c r="A1" t="inlineStr"><is><t>c1</t></is></c>'
        b'<c r="B1" t="inlineStr"><is><t>c2</t></is></c>'
        b'<c r="C1" t="inlineStr"><is><t>c3</t></is></c></row>'
        b"</sheetData></worksheet>"
    )
    xlsx_bytes = _criar_zip(
        {
            "xl/workbook.xml": wb,
            "xl/_rels/workbook.xml.rels": rels,
            "xl/worksheets/sheet1.xml": sheet,
        }
    )
    doc = F.abre(F.XLSX, dados=xlsx_bytes)
    try:
        txt = doc.texto(1)
        assert "c1" in txt and "c2" in txt
        assert doc.truncado is True
        assert "planilha_truncada" in doc.avisos
    finally:
        doc.fecha()


# ------------------------------------------------------------------ confinamento, prazo e memória
def test_extrator_nao_herda_credenciais_e_sai_5_no_prazo_ou_memoria(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Credencial no ambiente do pai NÃO vaza para o subprocesso extrator.
    monkeypatch.setenv("PF_CREDENCIAL_SECRETA", "segredo-super-sensivel")
    pacote = _criar_zip({"nota.txt": b"texto limpo"})
    fd = _abrir_fd_temporario(tmp_path, "limpo.zip", pacote)
    try:
        res = extrator.extrair_em_subprocesso(fd, {"chave": "obra:20", "membro": "nota.txt"})
        assert res["conteudo"] == "texto limpo"
        assert "segredo-super-sensivel" not in str(res)
    finally:
        os.close(fd)

    # Estouro de prazo -> saída 5 tempo-esgotado, deixando o processo chamador intacto.
    sock_lento = tmp_path / "lento.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_lento))
    srv.listen(1)
    evento = threading.Event()

    def _travar() -> None:
        conn, _ = srv.accept()
        with conn:
            evento.wait(timeout=2.0)

    th = threading.Thread(target=_travar, daemon=True)
    th.start()
    fd2 = _abrir_fd_temporario(tmp_path, "vazio.zip", pacote)
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_via_socket(sock_lento, fd2, {"chave": "obra:21"}, prazo_ms=100)
        assert exc.value.saida == 5
        assert exc.value.recusa.codigo == "tempo-esgotado"
    finally:
        evento.set()
        os.close(fd2)
        th.join(timeout=2.0)
        srv.close()

    # Teto de memória muito baixo no subprocesso -> saída 5 (falta-de-memoria ou morto-por-sinal).
    fd3 = _abrir_fd_temporario(tmp_path, "mem.zip", pacote)
    try:
        with pytest.raises(extrator.ErroExtrator) as exc:
            extrator.extrair_em_subprocesso(
                fd3,
                {"chave": "obra:22"},
                prazo_ms=3_000,
                limite_memoria_bytes=1 * 1024 * 1024,  # 1 MiB: Python falha ao iniciar/alocar
            )
        assert exc.value.saida == 5
        assert exc.value.recusa.codigo in ("falta-de-memoria", "morto-por-sinal")
    finally:
        os.close(fd3)
