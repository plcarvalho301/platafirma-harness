"""Contrato do gate de citação — verificar (spec §4.6, §8.4)."""

from __future__ import annotations

from pesquisa import manifesto as M
from pesquisa.verificar import verificar


def _trabalho_com_uma_leitura(tmp_path, n=3, corpo_md="o gato subiu no telhado"):
    t = M.Trabalho("ver", raiz=tmp_path)
    html = b"<html>fonte</html>"
    t.guarda_bruto(n, html, "html")
    t.guarda_derivado(n, corpo_md, "md")
    t.grava_linha({"n": n, "ato": "ler", "url": "https://f.org/a", "status": 200,
                   "sha256": M.sha256_bytes(html), "bruto": str(t.bruto / f"{n}.html")})
    return t


def test_sem_ancora_reprova(tmp_path):
    t = _trabalho_com_uma_leitura(tmp_path)
    rel = tmp_path / "r.md"
    rel.write_text("Afirmo algo forte [m:9].", encoding="utf-8")  # linha 9 não existe
    r = verificar(rel, t)
    assert r["sem_ancora"] == [9] and r["reprovou"]


def test_ancora_integra_com_trecho_presente_passa(tmp_path):
    t = _trabalho_com_uma_leitura(tmp_path, corpo_md="o gato subiu no telhado ao amanhecer")
    rel = tmp_path / "r.md"
    rel.write_text('O felino escalou [m:3 «subiu no telhado»].', encoding="utf-8")
    r = verificar(rel, t)
    assert not r["reprovou"] and r["sem_ancora"] == [] and r["trecho_ausente"] == []


def test_trecho_ausente_reprova(tmp_path):
    t = _trabalho_com_uma_leitura(tmp_path, corpo_md="texto que existe")
    rel = tmp_path / "r.md"
    rel.write_text('Cito [m:3 «texto que NAO esta la»].', encoding="utf-8")
    r = verificar(rel, t)
    assert r["trecho_ausente"] == [3] and r["reprovou"]


def test_ancora_quebrada_quando_sha_nao_bate(tmp_path):
    t = _trabalho_com_uma_leitura(tmp_path)
    # adultera o bruto no disco: hash deixa de bater com a linha do manifesto
    (t.bruto / "3.html").write_bytes(b"<html>ADULTERADO</html>")
    rel = tmp_path / "r.md"
    rel.write_text("Uso a fonte [m:3].", encoding="utf-8")
    r = verificar(rel, t)
    assert r["ancora_quebrada"] == [3] and r["reprovou"]


def test_nao_citado_lista_coleta_orfa(tmp_path):
    t = _trabalho_com_uma_leitura(tmp_path, n=3)
    # uma segunda leitura que ninguém cita
    t.guarda_bruto(4, b"<html>2</html>", "html")
    t.grava_linha({"n": 4, "ato": "ler", "url": "https://f.org/b", "status": 200,
                   "sha256": M.sha256_bytes(b"<html>2</html>"), "bruto": str(t.bruto / "4.html")})
    rel = tmp_path / "r.md"
    rel.write_text("Só cito a primeira [m:3].", encoding="utf-8")
    r = verificar(rel, t)
    assert r["nao_citado"] == [4] and not r["reprovou"]  # não-citado não reprova
