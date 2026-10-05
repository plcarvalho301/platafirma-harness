"""#3163: `curar --conceito <slug> --natureza <n>` (conceito existente: reclassifica, cura K19).

Mesmo servidor HTTP falso e mesmo subprocesso do teste de renomear (#3239), de onde vêm as fixtures.
"""
from __future__ import annotations

import json

import pytest

from test_curar_renomear import PATCH_EXPORT, PY, _curar, ambiente, falso  # noqa: F401 (fixtures)

pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")

SLUG, ID = "parecer-juridico", "11111111-2222-3333-4444-555555555555"
ARGS = ("--conceito", SLUG, "--natureza", "modelo", "--motivo", "a definição diz manifestação", "--autor", "dados")
CONFERENCIAS = ("ciclo", "categoria", "exclusividade", "ciclo_coluna")


def plano(corpo, **over):
    """O que o servidor devolve, como `rc.trocar_natureza` o monta."""
    p = {
        "modo": "aplicado" if corpo.get("aplicar") else "plano",
        "aprovado": True,
        "conceito": {"id": ID, "slug": SLUG, "rotulo": "Parecer jurídico"},
        "natureza": {"de": "processo", "para": corpo["natureza"]},
        "vizinhos_genericos": [{"slug": "ato-administrativo", "natureza": "modelo", "papel": "pai"}],
        "motivo": corpo["motivo"],
        "emitido_por": corpo["autor"],
        "conferencias": {n: {"antes": 0, "depois": 0, "novas": []} for n in CONFERENCIAS},
    }
    if corpo.get("aplicar"):
        p["id"] = ID
    p.update(over)
    return p


@pytest.fixture(autouse=True)
def _cenario(falso):
    falso.cenario = lambda corpo, caminho: (200, plano(corpo))


def test_plano_seco_mostra_de_para_vizinhos_e_vai_ao_documento(ambiente, falso):
    p = _curar(ambiente, *ARGS, "--sem-hermit")
    assert p.returncode == 0, p.stdout + p.stderr
    s = p.stdout
    assert "natureza: processo -> modelo" in s
    assert "pai   genérico: ato-administrativo (modelo)" in s
    assert all(f"conferência {n}" in s for n in CONFERENCIAS)
    assert "veredito: APROVADO" in s
    assert falso.patches() == [("PATCH", f"/acervo/conceitos/{SLUG}",
                                {"natureza": "modelo", "motivo": "a definição diz manifestação",
                                 "autor": "dados", "aplicar": False})]


def test_apply_grava_e_regera_o_export(ambiente, falso):
    p = _curar(ambiente, *ARGS, "--sem-hermit", "--apply", patches=PATCH_EXPORT)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "Natureza reclassificada" in p.stdout and "export : regenerado" in p.stdout
    assert [c[2]["aplicar"] for c in falso.patches()] == [False, True]


def test_conferencia_que_reprova_nao_grava(ambiente, falso):
    falso.cenario = lambda corpo, caminho: (200, plano(corpo, aprovado=False))
    p = _curar(ambiente, *ARGS, "--sem-hermit", "--apply", "--json")
    assert p.returncode == 1
    assert json.loads(p.stdout)["aprovado"] is False
    assert [c[2]["aplicar"] for c in falso.patches()] == [False]


def test_sem_motivo_sai_2_sem_chamar(ambiente, falso):
    p = _curar(ambiente, "--conceito", SLUG, "--natureza", "modelo", "--autor", "dados")
    assert p.returncode == 2 and "exige --motivo" in p.stderr
    assert falso.patches() == []
