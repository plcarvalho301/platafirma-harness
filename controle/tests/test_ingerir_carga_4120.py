"""Testes da carga da caixa de entrada e triagem (#4120).

U2 da story 4120:
- Portão 1 compara o manifesto com o que chegou (incluindo subpastas)
- .csv, .ods e .jsonl na lista de exceções em vez de descartados em silêncio
- .json comum e arquivo vazio como estado do item e nunca viram obra
- Expurgo da regra 20: o de 8 dias expurgado e o de 6 dias mantido
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from bin._ingerir import carga, expurgar_chegada


def test_portao_1_compara_manifesto_com_subpastas(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "raiz.pdf").write_text("conteudo raiz")
    sub = staging / "setor" / "2026"
    sub.mkdir(parents=True)
    (sub / "relatorio.pdf").write_text("conteudo relatorio")

    manifesto_ok = ["raiz.pdf", "setor/2026/relatorio.pdf"]
    ok, msg = carga.conferir_manifesto_portao_1(manifesto_ok, staging)
    assert ok is True
    assert "PORTÃO 1 aprovado: 2 arquivo(s)" in msg

    # Divergência: manifesto esperando mais arquivos
    manifesto_incompleto = ["raiz.pdf", "setor/2026/relatorio.pdf", "setor/2026/faltou.pdf"]
    ok, msg = carga.conferir_manifesto_portao_1(manifesto_incompleto, staging)
    assert ok is False
    assert "diverge do staging" in msg or "lote incompleto" in msg


def test_escanear_pasta_triagem_separa_excecoes(tmp_path: Path):
    pasta = tmp_path / "lote"
    pasta.mkdir()

    # Obra válida
    (pasta / "livro.pdf").write_text("conteudo pdf")

    # Obra válida em subpasta
    sub = pasta / "artigos" / "ti"
    sub.mkdir(parents=True)
    (sub / "paper.docx").write_text("conteudo docx")

    # Arquivo vazio
    (pasta / "vazio.pdf").write_bytes(b"")

    # .json comum (não sidecar)
    (pasta / "meta.json").write_text('{"item": 1}')

    # Planilhas e listas auxiliares que não devem sumir em silêncio
    (pasta / "planilha.csv").write_text("a,b,c\n1,2,3")
    (pasta / "dados.ods").write_bytes(b"ods-fake")
    (pasta / "linhas.jsonl").write_text('{"k": "v"}\n')

    # Sidecar
    (pasta / "livro.sidecar.json").write_text('{"autor": "x"}')

    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)

    # Obras válidas
    nomes_obras = {o["nome"] for o in obras}
    assert nomes_obras == {"livro.pdf", "paper.docx"}

    # Verifica pasta_origem preservada na subpasta
    paper_item = next(o for o in obras if o["nome"] == "paper.docx")
    assert paper_item["pasta_origem"] == "artigos/ti"

    # Exceções
    estados_excecoes = {e["nome"]: e["estado"] for e in excecoes}
    assert estados_excecoes["vazio.pdf"] == "vazio"
    assert estados_excecoes["meta.json"] == "json_comum"
    assert estados_excecoes["planilha.csv"] == "auxiliar"
    assert estados_excecoes["dados.ods"] == "auxiliar"
    assert estados_excecoes["linhas.jsonl"] == "auxiliar"
    assert estados_excecoes["livro.sidecar.json"] == "auxiliar"

    # Nenhum dos itens de exceção virou obra
    assert "vazio.pdf" not in nomes_obras
    assert "meta.json" not in nomes_obras
    assert "planilha.csv" not in nomes_obras


def test_expurgar_chegada_regra_20(tmp_path: Path):
    chegada_dir = tmp_path / "chegada"
    chegada_dir.mkdir()

    agora = 1700000000.0  # timestamp fixo para o teste

    # Item de 8 dias atrás: deve ser expurgado (8 > 7)
    item_8_dias = chegada_dir / "sha256_antigo_8_dias"
    item_8_dias.mkdir()
    (item_8_dias / "arquivo.pdf").write_text("antigo")
    ts_8_dias = agora - (8 * 86400)
    os.utime(item_8_dias, (ts_8_dias, ts_8_dias))

    # Item de 6 dias atrás: deve ser mantido (6 < 7)
    item_6_dias = chegada_dir / "sha256_recente_6_dias"
    item_6_dias.mkdir()
    (item_6_dias / "arquivo.pdf").write_text("recente")
    ts_6_dias = agora - (6 * 86400)
    os.utime(item_6_dias, (ts_6_dias, ts_6_dias))

    removidos = expurgar_chegada.expurgar_chegada(chegada_dir, dias=7, agora=agora)

    assert "sha256_antigo_8_dias" in removidos
    assert "sha256_recente_6_dias" not in removidos

    assert not item_8_dias.exists()
    assert item_6_dias.exists()
