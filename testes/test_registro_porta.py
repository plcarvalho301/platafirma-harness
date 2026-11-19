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
