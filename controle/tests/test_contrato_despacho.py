# componente: componente:suite
"""test_contrato_despacho — contrato do esquema de pipeline, extrator e despacho (card #4455).

Cobre na suíte do harness:
- extrator da trilha (`oplog_extracao`): `malote` e `execucao` atravessam como tipos próprios
  apenas com `evento` de topo, sem virar `giro` mesmo quando a linha traz `tool`, e evento
  desconhecido sem `tool` segue levantando `SemTraducao`
- esquema literal `registro/esquemas/pipeline.schema.json`: aceita artefato compilado válido
  (incluindo guardas ordenadas, `volta` e `executor` manual) e reprova falta de `tempo_maximo`,
  `em_saida` incompleto, guarda sem `servico` ou sem `reguas`, chave desconhecida e desvio
"""
from __future__ import annotations

import copy
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HARNESS_ROOT / "lib"))

ESQUEMA_PATH = HARNESS_ROOT / "registro" / "esquemas" / "pipeline.schema.json"
LEIA_PIPELINES_PATH = HARNESS_ROOT / "registro" / "pipelines" / "LEIA.md"
TOTAL_TIPOS_PARTICAO = 14


def _extrator() -> Any:
    import oplog_extracao

    return oplog_extracao


def _esquema_pipeline() -> dict[str, Any]:
    return json.loads(ESQUEMA_PATH.read_text(encoding="utf-8"))


def _resolver_ref(raiz: dict[str, Any], ref: str) -> dict[str, Any]:
    alvo: Any = raiz
    for parte in ref.removeprefix("#/").split("/"):
        alvo = alvo[parte]
    return alvo


def _validar_vazio(_instancia: Any, _sub: dict[str, Any], _raiz: dict[str, Any], _onde: str) -> list[str]:
    return []


def _validar_texto(instancia: str, sub: dict[str, Any], _raiz: dict[str, Any], onde: str) -> list[str]:
    erros: list[str] = []
    if "minLength" in sub and len(instancia) < sub["minLength"]:
        erros.append(f"{onde}: texto menor que minLength {sub['minLength']}")
    if "pattern" in sub and re.fullmatch(sub["pattern"], instancia) is None:
        erros.append(f"{onde}: texto fora do padrao {sub['pattern']}")
    return erros


def _validar_inteiro(instancia: int, sub: dict[str, Any], _raiz: dict[str, Any], onde: str) -> list[str]:
    if "minimum" in sub and instancia < sub["minimum"]:
        return [f"{onde}: inteiro menor que minimum {sub['minimum']}"]
    return []


def _validar_lista(instancia: list[Any], sub: dict[str, Any], raiz: dict[str, Any], onde: str) -> list[str]:
    erros: list[str] = []
    if "minItems" in sub and len(instancia) < sub["minItems"]:
        erros.append(f"{onde}: lista menor que minItems {sub['minItems']}")
    esquema_item = sub.get("items")
    if isinstance(esquema_item, dict):
        for idx, elem in enumerate(instancia):
            erros.extend(_validar_esquema_no(elem, esquema_item, raiz, f"{onde}[{idx}]"))
    return erros


def _validar_objeto(instancia: dict[str, Any], sub: dict[str, Any], raiz: dict[str, Any], onde: str) -> list[str]:
    erros: list[str] = []
    props = sub.get("properties") or {}
    for obrig in sub.get("required") or ():
        if obrig not in instancia:
            erros.append(f"{onde}: campo obrigatorio ausente '{obrig}'")
    if sub.get("additionalProperties") is False:
        erros.extend(f"{onde}: chave desconhecida '{c}'" for c in sorted(instancia) if c not in props)
    for chave, val in instancia.items():
        if chave in props:
            erros.extend(_validar_esquema_no(val, props[chave], raiz, f"{onde}.{chave}"))
    return erros


_REGRAS_TIPO: dict[
    str,
    tuple[Callable[[Any], bool], Callable[[Any, dict[str, Any], dict[str, Any], str], list[str]]],
] = {
    "object": (lambda x: isinstance(x, dict), _validar_objeto),
    "array": (lambda x: isinstance(x, list), _validar_lista),
    "string": (lambda x: isinstance(x, str), _validar_texto),
    "boolean": (lambda x: isinstance(x, bool), _validar_vazio),
    "integer": (lambda x: isinstance(x, int) and not isinstance(x, bool), _validar_inteiro),
}


def _validar_esquema_no(
    instancia: Any,
    sub: dict[str, Any],
    raiz: dict[str, Any],
    onde: str,
) -> list[str]:
    if "$ref" in sub:
        return _validar_esquema_no(instancia, _resolver_ref(raiz, sub["$ref"]), raiz, onde)
    if "oneOf" in sub:
        ramos = [_validar_esquema_no(instancia, ramo, raiz, onde) for ramo in sub["oneOf"]]
        return [] if sum(1 for r in ramos if not r) == 1 else [f"{onde}: valor fora de oneOf"]

    tipo = sub.get("type")
    regra = _REGRAS_TIPO.get(tipo or "")
    if regra is not None and not regra[0](instancia):
        return [f"{onde}: esperado tipo {tipo}"]

    erros: list[str] = []
    if "const" in sub and instancia != sub["const"]:
        erros.append(f"{onde}: esperado const {sub['const']!r}")
    if "enum" in sub and instancia not in sub["enum"]:
        erros.append(f"{onde}: valor fora de enum {sub['enum']!r}")
    if regra is not None:
        erros.extend(regra[1](instancia, sub, raiz, onde))
    return erros


def _erros_esquema(artefato: dict[str, Any]) -> list[str]:
    esquema = _esquema_pipeline()
    return _validar_esquema_no(artefato, esquema, esquema, "$")


def _artefato_valido() -> dict[str, Any]:
    return {
        "versao_esquema": 1,
        "procedencia": {
            "ficha": "pipeline:ingestao",
            "configuracao": "configuracao:ingestao",
            "fornada": "01a21dcc-e60f-7b7b-b8a7-4774190e5f36",
            "sha": "92d20cbf1d45",
            "compilado_em": "2026-11-27T22:00:00Z",
            "digest": "sha256:" + ("a" * 64),
        },
        "pipeline": "ingestao",
        "entra_por": "acervo",
        "parametros": [
            {"nome": "obra", "tipo": "texto", "obrigatorio": True},
        ],
        "tempo_maximo": 300,
        "teto_de_repeticoes": 4,
        "cache_vereditos": "por_arvore",
        "instrucoes": [
            {
                "id": "incorporar-item",
                "verbo": "acervo",
                "ato": "ingerir",
                "args": ["{obra}"],
                "em_saida": {
                    "0": "segue",
                    "1": "para",
                    "2": "para",
                    "3": "para",
                    "4": "para",
                    "5": "para",
                },
                "volta": "nenhuma",
                "guardas": [
                    {
                        "id": "conferir-acervo",
                        "verbo": "casa",
                        "servico": "servico:harness:lint",
                        "reguas": ["gabarito:antipadroes-do-acervo"],
                        "args": ["politica:acervo"],
                        "em_veredito": {
                            "sim": "segue",
                            "nao": "para",
                            "nao_sei": "para",
                            "nao_sei_na_catraca": "para",
                        },
                    }
                ],
            },
            {
                "id": "classificar-manual",
                "verbo": "acervo",
                "ato": "catalogar",
                "args": ["{obra}"],
                "duto": "incorporar-item",
                "aceita_vazio": False,
                "em_saida": {
                    "0": "segue",
                    "1": "segue",
                    "2": "para",
                    "3": "para",
                    "4": "para",
                    "5": "para",
                },
                "volta": {
                    "verbo": "acervo",
                    "ato": "retirar",
                    "args": ["{obra}"],
                },
                "executor": {
                    "tipo": "pessoa",
                    "alvo": "curadoria",
                    "prazo_espera": 600,
                },
            },
        ],
    }


def _mut_sem_tempo_maximo(art: dict[str, Any]) -> None:
    art.pop("tempo_maximo")


def _mut_em_saida_sem_cinco(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["em_saida"].pop("5")


def _mut_guarda_sem_servico(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["guardas"][0].pop("servico")


def _mut_guarda_sem_reguas(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["guardas"][0].pop("reguas")


def _mut_guarda_reguas_vazia(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["guardas"][0]["reguas"] = []


def _mut_chave_desconhecida_topo(art: dict[str, Any]) -> None:
    art["chave_inventada"] = True


def _mut_campo_desvio_instrucao(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["quando"] = "saida == 0"


def _mut_id_fora_kebab(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["id"] = "Passo_Invalido"


def test_diretorio_pipelines_e_esquema_existem_e_validam_artefato_canonico() -> None:
    assert LEIA_PIPELINES_PATH.is_file()
    assert LEIA_PIPELINES_PATH.read_text(encoding="utf-8").strip() != ""
    esquema = _esquema_pipeline()
    assert esquema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert esquema["additionalProperties"] is False
    assert _erros_esquema(_artefato_valido()) == []


@pytest.mark.parametrize(
    ("mutador", "trecho_esperado"),
    [
        (_mut_sem_tempo_maximo, "tempo_maximo"),
        (_mut_em_saida_sem_cinco, "'5'"),
        (_mut_guarda_sem_servico, "servico"),
        (_mut_guarda_sem_reguas, "reguas"),
        (_mut_guarda_reguas_vazia, "minItems"),
        (_mut_chave_desconhecida_topo, "chave_inventada"),
        (_mut_campo_desvio_instrucao, "quando"),
        (_mut_id_fora_kebab, "padrao"),
    ],
)
def test_esquema_reprova_desvios_obrigatorios_e_campos_fechados(
    mutador: Callable[[dict[str, Any]], None],
    trecho_esperado: str,
) -> None:
    art = copy.deepcopy(_artefato_valido())
    mutador(art)
    erros = _erros_esquema(art)
    assert erros != []
    assert trecho_esperado in " | ".join(erros)


@pytest.mark.parametrize("tipo_novo", ["malote", "execucao"])
def test_extrator_traduz_malote_e_execucao_sem_virar_giro_mesmo_com_tool(tipo_novo: str) -> None:
    extrator = _extrator()
    assert len(extrator.TIPOS) == TOTAL_TIPOS_PARTICAO
    assert tipo_novo in extrator.TIPOS

    linha_sem_tool = {
        "ts": "2026-11-27T21:00:00.000-03:00",
        "evento": tipo_novo,
        "evento_id": "019a0000-0000-7000-8000-000000000010",
        "schema_v": 1,
        "cadeira": "engenharia",
        "sessao_id": "489968fd-8076-406e-88b9-3a1646d49f80",
        "ordem_id": "o20261127T210000-abc123",
    }
    linha_com_tool = {**linha_sem_tool, "tool": "acervo", "ato": "despachar", "exit_code": 0}

    assert extrator.tipo_particao(linha_sem_tool) == tipo_novo
    assert extrator.tipo_particao(linha_com_tool) == tipo_novo

    item_sem = extrator.para_item(linha_sem_tool, "2026-11-27", 1, extrator.Invalidos())
    item_com = extrator.para_item(linha_com_tool, "2026-11-27", 2, extrator.Invalidos())
    assert list(item_sem.keys()) == ["evento"]
    assert list(item_com.keys()) == ["evento"]
    assert item_sem["evento"]["tipo"] == tipo_novo
    assert item_com["evento"]["tipo"] == tipo_novo

    dados_dia = (json.dumps(linha_sem_tool) + "\n" + json.dumps(linha_com_tool) + "\n").encode("utf-8")
    resumo = extrator.relatorio_seco(extrator.Extracao("2026-11-27", dados_dia))
    assert resumo["sem_traducao"] == {}
    assert resumo["por_tipo_da_particao"] == {tipo_novo: 2}
    assert resumo["giros_por_tool"] == {}
    assert resumo["amostra_n"] == 0


def test_extrator_mantem_sem_traducao_para_evento_desconhecido_sem_tool() -> None:
    extrator = _extrator()
    with pytest.raises(extrator.SemTraducao) as exc_info:
        extrator.tipo_particao({"evento": "evento_inexistente_xyz"})
    assert exc_info.value.evento == "evento_inexistente_xyz"
