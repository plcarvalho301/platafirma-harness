"""Testes unitários do parser novo do card #3110: `rotulos_da_gerencias` lê a seção
`## Gerências` de um persona.md (molde novo), no lugar de `rotulos_da_secao_b` (antiga
`## b)` de chapeu.md, molde velho).

Cobre, num fixture só (cadeira sintética "testecadeira"):
- separador ': ' antes do 1º rótulo, sem '. ' no primeiro segmento ("destrava: ...")
- rótulo com '. ' interno num segmento que NÃO é o primeiro (não sofre o corte de
  descrição) — "direcionamento vs. implementabilidade"
- bullet quebrado em duas linhas de continuação (reconstituído por join)
- slug acentuado no bullet ("governança") divergente do diretório real ("governanca")
- rótulo inventado que não casa o golden record, virando órfão sob --estrito
- slug de bullet sem diretório correspondente, virando órfão de chapéu
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from recuperacao import gerar_rotas_chapeu as grc  # noqa: E402

GOLDEN_FAKE = [
    {"rotulo": "quando cabe um agente", "slug": "quando-cabe-um-agente"},
    {"rotulo": "direcionamento vs. implementabilidade", "slug": "direcionamento-vs-implementabilidade"},
    {"rotulo": "rotulo quebrado em duas linhas", "slug": "rotulo-quebrado-em-duas-linhas"},
    {"rotulo": "segundo rotulo real", "slug": "segundo-rotulo-real"},
]


def _persona_fixture_texto() -> str:
    return (
        "Introdução da cadeira de teste.\n"
        "Segunda linha de introdução.\n\n"
        "## Perguntas de competência\n\n1. Pergunta?\n\n"
        "## Vocabulário canônico\n\n- termo: definicao\n\n"
        "## Escopo\n\n- nao faz nada\n\n"
        "## Sinais de reconhecimento\n\n- sinal\n\n"
        "## Gerências\n\n"
        "Cada gerência é um chapéu.\n\n"
        "- **alfa** — destrava: quando cabe um agente · direcionamento vs. implementabilidade ·\n"
        "  rotulo quebrado em duas\n"
        "  linhas · rotulo-inventado-que-nao-casa-golden.\n"
        "- **governança** — outra descrição solta. segundo rotulo real.\n"
    )


@pytest.fixture
def abertura_fixture(tmp_path):
    abertura = tmp_path / "abertura"
    cad = abertura / "testecadeira"
    cad.mkdir(parents=True)
    (cad / "persona.md").write_text(_persona_fixture_texto(), encoding="utf-8")
    (cad / "alfa").mkdir()
    (cad / "alfa" / "chapeu.md").write_text("# alfa\n", encoding="utf-8")
    (cad / "governanca").mkdir()
    (cad / "governanca" / "chapeu.md").write_text("# governanca\n", encoding="utf-8")
    return abertura


def test_rotulos_da_gerencias_parser(abertura_fixture):
    texto = (abertura_fixture / "testecadeira" / "persona.md").read_text(encoding="utf-8")
    base = str(abertura_fixture / "testecadeira")

    gerencias, orfaos_chapeu = grc.rotulos_da_gerencias(texto, base)

    assert orfaos_chapeu == []  # os dois slugs batem com diretorio real
    assert set(gerencias.keys()) == {"alfa", "governanca"}

    assert gerencias["alfa"] == [
        "quando cabe um agente",                          # corte por ': ' (sem '. ' antes)
        "direcionamento vs. implementabilidade",           # '.' interno preservado (nao e o 1o segmento)
        "rotulo quebrado em duas linhas",                  # bullet quebrado em duas linhas, reconstituido
        "rotulo-inventado-que-nao-casa-golden",             # ponto final removido
    ]
    assert gerencias["governanca"] == ["segundo rotulo real"]  # corte por '. ', slug sem acento


def test_rotulos_da_gerencias_slug_orfao_de_chapeu(tmp_path):
    """Slug do bullet sem diretório real correspondente vira órfão de chapéu."""
    texto = "## Gerências\n\n- **fantasma** — rotulo qualquer.\n"
    gerencias, orfaos_chapeu = grc.rotulos_da_gerencias(texto, str(tmp_path))
    assert gerencias == {}
    assert len(orfaos_chapeu) == 1
    assert "fantasma" in orfaos_chapeu[0]


def test_rotulos_da_gerencias_sem_secao_volta_vazio():
    gerencias, orfaos_chapeu = grc.rotulos_da_gerencias("sem secao de gerencias aqui\n")
    assert gerencias == {}
    assert orfaos_chapeu == []


def test_gerar_orfao_de_conceito_sob_estrito_sem_falso_positivo(monkeypatch, abertura_fixture):
    monkeypatch.setattr(grc, "_conceitos_http", lambda: {"itens": GOLDEN_FAKE})

    tabela, orfaos = grc.gerar(True, str(abertura_fixture))

    texto_orfaos = "\n".join(orfaos)
    # nenhum dos rotulos que casam o golden vira orfao — prova que a regra ': '/'. '
    # funcionou e que o '.' interno de "vs." nao quebrou o rotulo
    assert "quando cabe um agente" not in texto_orfaos
    assert "direcionamento vs. implementabilidade" not in texto_orfaos
    assert "rotulo quebrado em duas linhas" not in texto_orfaos
    assert "segundo rotulo real" not in texto_orfaos

    # o rotulo inventado (fixture) vira orfao de conceito
    assert any("rotulo-inventado-que-nao-casa-golden" in o for o in orfaos)

    assert tabela["testecadeira"]["alfa"]
    assert tabela["testecadeira"]["governanca"]


def test_main_estrito_sai_diferente_de_zero_com_rotulo_inventado(monkeypatch, abertura_fixture, capsys):
    monkeypatch.setattr(grc, "_conceitos_http", lambda: {"itens": GOLDEN_FAKE})
    monkeypatch.setattr(
        sys, "argv",
        ["gerar_rotas_chapeu.py", "--abertura", str(abertura_fixture), "--dry-run", "--estrito"],
    )
    rc = grc.main()
    assert rc != 0
    captured = capsys.readouterr()
    assert "AVISO órfão" in captured.err


def test_main_cadeira_mescla_sem_tocar_outras(monkeypatch, abertura_fixture):
    monkeypatch.setattr(grc, "_conceitos_http", lambda: {"itens": GOLDEN_FAKE})

    saida = abertura_fixture / "rotas-chapeu.json"
    existente = {"outra-cadeira": {"algum-chapeu": ["gatilho-preexistente"]}}
    saida.write_text(
        json.dumps(existente, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys, "argv",
        ["gerar_rotas_chapeu.py", "--abertura", str(abertura_fixture), "--cadeira", "testecadeira"],
    )
    rc = grc.main()
    assert rc == 0

    final = json.loads(saida.read_text(encoding="utf-8"))
    assert final["outra-cadeira"] == existente["outra-cadeira"]
    assert "alfa" in final["testecadeira"]
    assert "governanca" in final["testecadeira"]
