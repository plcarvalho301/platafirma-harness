"""O registro da porta (registro/porta.yaml, card #4117 e decisão #5322 da F4073).

Hermetico: le registro/porta.yaml sem depender da porta legada nem do registro de ferramental do banco.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRO = REPO_ROOT / "registro" / "porta.yaml"
FORA_DA_LISTA = {"chat", "minuta", "persona", "preferencia", "sinal", "situacao", "sessao"}
TRANSPORTE_ESPERADO = {"malote", "ler_arquivo", "write_file", "monta_sessao"}


@pytest.fixture(scope="module")
def registro():
    return yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))


def test_transporte_declara_exatamente_as_quatro_tools_sem_legados(registro):
    transporte = set(registro["transporte"])
    assert transporte == TRANSPORTE_ESPERADO
    assert not ({"run_command", "read_file"} & transporte)


def test_ocultas_e_removidas_da_lista(registro):
    verbos = registro["verbos"]
    assert not ({"chat", "minuta", "sinal", "situacao"} & set(verbos))
    for oculto in ("preferencia", "sessao", "persona"):
        assert oculto in verbos and verbos[oculto].get("modelo") is False
    visiveis = {k for k, v in verbos.items() if (v or {}).get("modelo", True) is not False}
    assert not (visiveis & FORA_DA_LISTA)
    assert "metrica" in visiveis


def test_todo_verbo_visivel_tem_descricao_no_manifesto(registro):
    """Decisão #5322: a toolstring mora em registro/porta.yaml."""
    for slug, meta in registro["verbos"].items():
        if (meta or {}).get("modelo", True) is False:
            continue
        desc = (meta or {}).get("descricao") or ""
        assert desc.strip(), f"{slug}: sem descricao em registro/porta.yaml"
        assert len(desc.strip()) > 20, f"{slug}: descricao curta demais"


def test_faces_da_borda_saem_do_registro(registro):
    faces: dict[str, list[str]] = {}
    for slug, v in registro["verbos"].items():
        for face in (v or {}).get("faces") or {}:
            faces.setdefault(face, []).append(slug)
    assert sorted(faces) == ["casca", "motor"]
    assert sorted(faces["casca"]) == ["preferencia", "release", "tarefas"]
    assert sorted(faces["motor"]) == ["fila", "motor"]


def test_registro_expoe_exatamente_as_24_tools_visiveis_do_ar(registro):
    esperadas = {
        "acervo", "acesso", "agente", "analise", "bot", "busca", "conferir",
        "descansar", "expediente", "fila", "infra", "ler_arquivo", "lint",
        "malote", "mesa", "metrica", "monta_sessao", "pesquisar", "release",
        "repo", "seg", "tarefas", "teste", "write_file",
    }
    visiveis = set(registro["transporte"])
    for slug, meta in registro["verbos"].items():
        meta = meta or {}
        if meta.get("modelo", True) is False:
            continue
        visiveis.add(meta.get("nome") or slug)
    assert visiveis == esperadas
    assert registro["verbos"]["motor"].get("nome") == "busca"


def test_toolstring_do_malote_no_registro(registro):
    desc = registro["transporte"]["malote"]["descricao"]
    assert "cadeia que para no primeiro erro" in desc
    assert "duto" in desc
    assert "verbo sem tool própria" in desc
    assert "em paralelo" in desc
    assert "lote_next" in desc
    assert "SEMPRE que for chamar dois ou mais verbos" not in desc
