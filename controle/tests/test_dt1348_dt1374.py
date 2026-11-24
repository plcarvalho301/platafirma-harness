"""Regressões dos DTs 1348 (extrator/contrato) e 1374 (roteiro da abertura na casa nova)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HARNESS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(HARNESS_LIB) not in sys.path:
    sys.path.insert(0, str(HARNESS_LIB))

import oplog
import oplog_extracao
from abertura.__main__ import _ato_abrir
from abertura.roteiro import ParteLida, PedidoDeRoteiro, PecaDoRoteiro, montar_roteiro


class _LeitorRoteiroStub:
    def __init__(self, pecas):
        self._pecas = pecas

    def construido_de(self, roteiro: str = "porta"):
        return list(self._pecas)


class _LeitorParteStub:
    def __init__(self, mapa):
        self._mapa = mapa

    def ler(self, classe: str, cadeira: str, chapeu: str | None, *, chave: str | None = None) -> ParteLida:
        return self._mapa.get(classe, ParteLida(ok=False, conteudo="", ref=f"{classe}:", erro="sem leitura direta"))


def test_dt1374_coringa_no_roteiro_aceita_instancias_sem_aviso() -> None:
    leitor_ficha = _LeitorRoteiroStub([
        PecaDoRoteiro("persona", "persona:*", posicao=1),
        PecaDoRoteiro("chapeu", "chapeu:*", posicao=2),
        PecaDoRoteiro("cultura", "cultura:*", posicao=3),
    ])
    leitor_parte = _LeitorParteStub({
        "persona": ParteLida(ok=True, conteudo="# TI", ref="persona:ti", instancias=("ti",)),
        "chapeu": ParteLida(ok=True, conteudo="# Plataforma", ref="chapeu:plataforma", instancias=("plataforma",)),
        "cultura": ParteLida(ok=True, conteudo="# Cultura", ref="cultura:da-casa", instancias=("da-casa",)),
    })
    montado = montar_roteiro(PedidoDeRoteiro(cadeira="ti", chapeu="plataforma"), leitor_ficha, leitor_parte)
    assert [p.parte for p in montado.partes] == ["persona", "chapeu", "cultura"]
    assert montado.avisos == ()


def test_dt1374_ato_abrir_sem_falsos_avisos_e_sem_duplicar_pecas_principais(tmp_path: Path) -> None:
    casa = tmp_path / "casa"
    (casa / "instancias" / "persona").mkdir(parents=True)
    (casa / "instancias" / "chapeu").mkdir(parents=True)
    (casa / "instancias" / "cultura").mkdir(parents=True)
    (casa / "instancias" / "postura").mkdir(parents=True)
    (casa / "instancias" / "persona" / "ti.md").write_text(
        "# Oswaldo Aranha\n\nEntidade: persona\n\nPostura preferencial: vigilante\n\n## Gerências\n- **plataforma** — a stack.\n\n## Nomes\n- cadeira **ti**: nenhum\n",
        encoding="utf-8",
    )
    (casa / "instancias" / "chapeu" / "plataforma.md").write_text(
        "# Plataforma\n\nEntidade: chapeu\n\nEspaço de problema.\n",
        encoding="utf-8",
    )
    (casa / "instancias" / "cultura" / "da-casa.md").write_text(
        "# Cultura da casa\n\nEntidade: cultura\n\n## Premissas\n\n- Regra.\n",
        encoding="utf-8",
    )
    (casa / "instancias" / "postura" / "vigilante.md").write_text(
        "# Vigilante\n\nEntidade: postura\n\nPostura vigilante.\n",
        encoding="utf-8",
    )

    saida, rc = _ato_abrir(
        {
            "casa_raiz": str(casa),
            "cadeira": "ti",
            "chapeu": "plataforma",
            "pergunta": "(TI, plataforma) teste",
            "sem_valkey": True,
            "guardados": [],
            "cartas": [],
        }
    )
    assert rc == 0
    assert saida["ok"] is True
    assert saida["avisos"] == []
    assert set(saida["pecas"].keys()) == {"persona", "chapeu", "cultura"}
    # Roteiro não repete persona, chapeu nem cultura que já estão em pecas
    partes_roteiro = [p["parte"] for p in saida["roteiro"]["partes"]]
    assert "persona" not in partes_roteiro
    assert "chapeu" not in partes_roteiro
    assert "cultura" not in partes_roteiro
    assert "postura" in partes_roteiro
    assert "Oswaldo Aranha" not in saida["roteiro"]["conteudo"]


def test_dt1348_extrator_traduz_abertura_e_ignora_pep_politica_carregada() -> None:
    linha_abertura = {
        "ts": "2026-11-23T21:00:00.000-03:00",
        "evento_id": "019ab123-0000-7000-8000-000000000001",
        "schema_v": 1,
        "tool": "monta_sessao",
        "sessao_id": "1ec8d68a-fd0b-454e-b06e-a15c045cf77b",
        "ordem_id": "o20261123T210000-abcdef",
        "cadeira": "ti",
        "chapeu": "plataforma",
        "roteador_via": None,
        "fallback": False,
        "superficie": "agy",
        "tokens_pecas": {"persona": 1200, "cultura": 3300, "chapeu": 800},
        "metodo_tokens": "estimado",
        "prefixo_sha": "8baa90235c9d",
        "montador_sha": "123456789abc",
        "pergunta": "DTs 1348 e 1374",
        "pergunta_bytes": 15,
        "exit_code": 0,
        "sujeito": "sub-1",
        "sub": "sub-1",
        "username": "op",
        "azp": "agy-cli",
        "sid": "sid-1",
        "jti": "jti-1",
        "origem": "cadeira",
        "mapa_v": None,
    }
    assert oplog.validar(linha_abertura) == []

    linha_pep = {
        "ts": "2026-11-23T21:00:01.000-03:00",
        "evento_id": "019ab123-0000-7000-8000-000000000002",
        "schema_v": 1,
        "evento": "pep_politica_carregada",
        "regras": 12,
    }
    linha_auth = {
        "ts": "2026-11-23T21:00:02.000-03:00",
        "evento_id": "019ab123-0000-7000-8000-000000000003",
        "schema_v": 1,
        "evento": "auth_negada",
        "path": "/mcp",
        "origem_requisicao": "127.0.0.1",
        "motivo": "cliente_nao_cadastrado",
        "origem": "cadeira",
        "mapa_v": None,
    }

    bruto = "\n".join(json.dumps(x) for x in (linha_abertura, linha_pep, linha_auth)).encode("utf-8") + b"\n"
    ext = oplog_extracao.Extracao("2026-11-23", bruto)
    assert not ext.sem_traducao
    assert ext.invalidos.total == 0
    assert ext.por_tipo["abertura"] == 1
    assert ext.por_tipo["auth_negada"] == 1
    assert ext.ignorados["pep_politica_carregada"] == 1
