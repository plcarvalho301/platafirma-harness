# componente: componente:release
"""test_gerar_pipelines — compilação imutável de artefatos de pipeline na promoção (card #4472)."""
from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

TESTS_DIR = Path(__file__).resolve().parent
HARNESS_ROOT = TESTS_DIR.parent
ESQUEMA_SRC = HARNESS_ROOT / "registro" / "esquemas" / "pipeline.schema.json"


def _carregar_gerar() -> Any:
    lib_dir = str(HARNESS_ROOT / "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    from pipelines import gerar

    return gerar


def _montar_arvore(tmp_path: Path, slug: str, config_yaml: dict[str, Any]) -> Path:
    arvore = tmp_path / "harness"
    (arvore / "registro" / "esquemas").mkdir(parents=True)
    (arvore / "registro" / "pipelines" / "fontes").mkdir(parents=True)
    shutil.copy2(ESQUEMA_SRC, arvore / "registro" / "esquemas" / "pipeline.schema.json")
    (arvore / "registro" / "porta.yaml").write_text(
        yaml.safe_dump(
            {
                "verbos": {
                    "release": {"descricao": "opera release · atos: estado, conferir, despachar"},
                    "casa": {"descricao": "casa · atos: ler, verificar"},
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (arvore / "registro" / "pipelines" / "fontes" / f"{slug}.yaml").write_text(
        yaml.safe_dump(config_yaml, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return arvore


def _config_valida(slug: str = "conferir-ar") -> dict[str, Any]:
    return {
        "pipeline": slug,
        "entra_por": "release",
        "parametros": [{"nome": "familia", "tipo": "texto", "obrigatorio": True}],
        "tempo_maximo": 60,
        "cache_vereditos": "nenhum",
        "instrucoes": [
            {
                "id": "ler-estado",
                "verbo": "release",
                "ato": "estado",
                "substrato": "repositorio:{familia}",
                "args": ["{familia}"],
                "em_saida": {"0": "segue", "1": "para", "2": "para", "3": "para", "4": "para", "5": "para"},
                "volta": "nenhuma",
                "guardas": [
                    {
                        "id": "conferir-regua",
                        "verbo": "casa",
                        "substrato": "repositorio:{familia}",
                        "servico": "servico:harness:lint",
                        "reguas": ["gabarito:antipadroes-de-codigo"],
                        "args": ["repositorio:{familia}"],
                        "em_veredito": {"sim": "segue", "nao": "para", "nao_sei": "para", "nao_sei_na_catraca": "para"},
                    }
                ],
            }
        ],
    }


def _fichario_valido(slug: str = "conferir-ar") -> Any:
    return lambda: (
        "01a222a0-0000-7000-8000-000000004472",
        {slug: {"chave": f"pipeline:{slug}"}},
        {slug: {"chave": f"configuracao:{slug}", "dados": {"caminho": f"registro/pipelines/fontes/{slug}.yaml"}}},
    )


def test_compila_artefato_completo_com_procedencia_e_digest(tmp_path: Path) -> None:
    gerar = _carregar_gerar()
    arvore = _montar_arvore(tmp_path, "conferir-ar", _config_valida())

    itens = gerar.compilar_pipelines(
        arvore=arvore,
        sha="506d5e579327",
        consultar_fichario=_fichario_valido(),
    )
    assert len(itens) == 1
    assert itens[0].slug == "conferir-ar"
    assert itens[0].digest.startswith("sha256:")
    compilado = yaml.safe_load((arvore / "registro" / "pipelines" / "conferir-ar.yaml").read_text(encoding="utf-8"))
    assert compilado["versao_esquema"] == 2
    assert compilado["procedencia"]["ficha"] == "pipeline:conferir-ar"
    assert compilado["procedencia"]["configuracao"] == "configuracao:conferir-ar"
    assert compilado["procedencia"]["sha"] == "506d5e579327"
    assert compilado["procedencia"]["digest"] == itens[0].digest


@pytest.mark.parametrize(
    ("mutador", "trecho_esperado"),
    [
        (lambda c: c.pop("tempo_maximo"), "tempo_maximo"),
        (lambda c: c["instrucoes"][0]["em_saida"].pop("5"), "em_saida"),
        (lambda c: c["instrucoes"][0]["guardas"][0]["em_veredito"].pop("nao_sei"), "nao_sei"),
        (lambda c: c["instrucoes"][0].update({"verbo": "verbo-inexistente"}), "verbo-registrado"),
        (lambda c: c["instrucoes"][0].update({"ato": "ato-inexistente"}), "ato-declarado-no-verbo"),
    ],
)
def test_recusa_configuracao_invalida_sem_gravar_artefato(
    tmp_path: Path, mutador: Any, trecho_esperado: str
) -> None:
    gerar = _carregar_gerar()
    cfg = copy.deepcopy(_config_valida())
    mutador(cfg)
    arvore = _montar_arvore(tmp_path, "conferir-ar", cfg)

    with pytest.raises(gerar.ErroCompilacaoPipeline) as exc:
        gerar.compilar_pipelines(
            arvore=arvore,
            sha="506d5e579327",
            consultar_fichario=_fichario_valido(),
        )
    assert any(trecho_esperado in e.formatar() for e in exc.value.erros)
    assert not (arvore / "registro" / "pipelines" / "conferir-ar.yaml").exists()


def test_olaria_indisponivel_levanta_erro_saida_3(tmp_path: Path) -> None:
    gerar = _carregar_gerar()
    arvore = _montar_arvore(tmp_path, "conferir-ar", _config_valida())

    def _fora_do_ar() -> Any:
        raise gerar.OlariaIndisponivel("conexao recusada")

    with pytest.raises(gerar.OlariaIndisponivel):
        gerar.compilar_pipelines(arvore=arvore, sha="506d5e579327", consultar_fichario=_fora_do_ar)
