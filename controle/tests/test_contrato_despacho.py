# componente: componente:suite
"""test_contrato_despacho — contrato do esquema, extrator, cliente, delegador e leitura (card #4455).

Cobre na suíte do harness (t2 + t6, Aceite 3):
- extrator da trilha (`oplog_extracao`): `malote` e `execucao` atravessam como tipos próprios
  sem virar `giro` mesmo quando a linha traz `tool`, e evento desconhecido sem `tool` levanta `SemTraducao`
- esquema literal `registro/esquemas/pipeline.schema.json`: aceita artefato compilado válido
  e reprova falta de `tempo_maximo`, `em_saida` incompleto, guarda sem `servico`/`reguas` e desvio
- chamada de `verificar` com dois testes entregue via `DelegadorSuiteDespacho` e `despachar_pelo_core`
  ao motor `suíte de testes` (`python -m suite laudo`), devolvendo o laudo como veio (`exit 0`)
- saída `3` (`dependencia-sem-resposta`) quando a porta/despachar não responde ou está ausente
- saída `5` (`tempo-esgotado`) quando a suíte passa do prazo do `verificar` (unidade encerrada ou parcial)
- leitura da execução pelo evento `execucao` via `oplog.ler` (`0` dono, `1` inexistente, `4` outro sujeito)
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

TESTS_DIR = Path(__file__).resolve().parent
HARNESS_ROOT = TESTS_DIR.parents[1]
ESQUEMA_PATH = HARNESS_ROOT / "registro" / "esquemas" / "pipeline.schema.json"
LEIA_PIPELINES_PATH = HARNESS_ROOT / "registro" / "pipelines" / "LEIA.md"
TOTAL_TIPOS_PARTICAO = 14
TOTAL_ITENS_DUAS_FICHAS = 2
SAIDA_OK = 0
SAIDA_INEXISTENTE = 1
SAIDA_DEPENDENCIA = 3
SAIDA_NEGADA = 4
SAIDA_INDETERMINAVEL = 5
SUJEITO_DONO = "11111111-1111-1111-1111-111111111111"
SUJEITO_OUTRO = "22222222-2222-2222-2222-222222222222"


def _preparar_sys_path() -> None:
    for pasta in (HARNESS_ROOT / "lib", HARNESS_ROOT / "bin", TESTS_DIR):
        texto = str(pasta)
        if texto not in sys.path:
            sys.path.insert(0, texto)


def _extrator() -> Any:
    _preparar_sys_path()
    import oplog_extracao

    return oplog_extracao


def _modulos_despacho() -> tuple[Any, Any, Any, Any]:
    _preparar_sys_path()
    import despacho
    import leitura.recusa as mod_recusa
    import oplog
    import verificador

    return despacho, mod_recusa, oplog, verificador


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
        "versao_esquema": 2,
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
                "substrato": "{obra}",
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
                        "substrato": "politica:acervo",
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
                "substrato": "obra:{obra}",
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


def _mut_versao_esquema_1(art: dict[str, Any]) -> None:
    art["versao_esquema"] = 1


def _mut_instrucao_sem_substrato(art: dict[str, Any]) -> None:
    art["instrucoes"][0].pop("substrato")


def _mut_instrucao_substrato_invalido(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["substrato"] = "alvo-sem-classe"


def _mut_guarda_sem_substrato(art: dict[str, Any]) -> None:
    art["instrucoes"][0]["guardas"][0].pop("substrato")


def _mut_executor_tipo_bot(art: dict[str, Any]) -> None:
    art["instrucoes"][1]["executor"]["tipo"] = "bot"


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


def _preparar_arvore_duas_fichas(raiz: Path) -> Path:
    arvore = raiz / "arvore_alfa"
    (arvore / "tests").mkdir(parents=True, exist_ok=True)
    (arvore / "tests" / "test_a1.py").write_text(
        "# componente: componente:alfa\n\ndef test_um():\n    assert True\n",
        encoding="utf-8",
    )
    (arvore / "tests" / "test_a2.py").write_text(
        "# componente: componente:alfa\n# verifica: politica:0011\n\ndef test_dois():\n    assert True\n",
        encoding="utf-8",
    )
    return arvore


def _runner_ponte_suite_real(
    arq_duble: Path,
    pedidos_vistos: list[dict[str, Any]],
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Simula a borda do core invocando `python -m suite laudo` em subprocesso real."""

    def _executar(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        pedido = json.loads(str(kwargs.get("input") or "{}"))
        pedidos_vistos.append(pedido)
        params = pedido["parametros"]
        cmd_suite = [
            sys.executable,
            "-m",
            "suite",
            "laudo",
            *params["chaves_fichas"],
            "--arvore",
            params["arvore"],
            "--alvo",
            params.get("alvo", ""),
            "--prazo",
            str(pedido.get("prazo_espera_s", 30.0)),
            "--json",
        ]
        env_filho = {
            **os.environ,
            "PYTHONPATH": str(HARNESS_ROOT / "lib"),
            "PF_SUITE_DUBLE_JSON": str(arq_duble),
        }
        return subprocess.run(
            cmd_suite,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env=env_filho,
        )

    return _executar


def _rodar_verificador_duas_fichas(
    arvore: Path,
    delegador: Any,
    *,
    prazo_s: float = 30.0,
) -> tuple[int, str, str]:
    _despacho, _mod_recusa, _oplog, verificador = _modulos_despacho()
    from test_contrato_verificar import DubleFichario, _reguas_padrao, _vista_padrao

    fichario = DubleFichario(
        reguas=_reguas_padrao(),
        alvos={
            "componente:alfa": verificador.AlvoVerificado(
                chave="componente:alfa",
                classe="componente",
                slug="alfa",
                raiz=arvore,
            )
        },
    )
    out = io.StringIO()
    err = io.StringIO()
    amb = verificador.AmbienteVerificacao(
        vista=_vista_padrao(),
        fichario=fichario,
        delegador_suite=delegador,
        prazo_s=prazo_s,
    )
    rc = verificador.executar(
        "ops",
        ["componente:alfa", "--regua", "teste:alfa", "--regua", "teste:alfa--politica-0011", "--json"],
        ambiente=amb,
        stdout=out,
        stderr=err,
    )
    return rc, out.getvalue(), err.getvalue()


def _ler_recusa_json(stderr_txt: str) -> dict[str, str]:
    _despacho, mod_recusa, _oplog, _verificador = _modulos_despacho()
    linhas = [ln for ln in stderr_txt.splitlines() if ln.strip()]
    assert linhas != []
    rec = json.loads(linhas[-1])
    for campo in mod_recusa.CAMPOS:
        assert campo in rec
    return rec


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
        (_mut_versao_esquema_1, "const 2"),
        (_mut_instrucao_sem_substrato, "substrato"),
        (_mut_instrucao_substrato_invalido, "padrao"),
        (_mut_guarda_sem_substrato, "substrato"),
        (_mut_executor_tipo_bot, "enum"),
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


def test_extrator_traduz_linha_do_bot_como_giro_unico_sem_contar_duas_vezes() -> None:
    extrator = _extrator()
    linha_bot = {
        "ts": "2026-11-28T11:00:00.000-03:00",
        "evento_id": "019a0000-0000-7000-8000-000000000020",
        "schema_v": 1,
        "tool": "acervo",
        "evento": "verbo",
        "ato": "ingerir",
        "substrato": "obra:42",
        "args": "obra:42",
        "origem": "bot",
        "execucao_id": "exec-0001",
        "passo_id": "incorporar-item",
        "sujeito": SUJEITO_DONO,
        "cadeira": "engenharia",
        "sessao_id": "489968fd-8076-406e-88b9-3a1646d49f80",
        "ordem_id": "o20261128T110000-abc123",
        "exit_code": 0,
        "dur_ms": 45,
        "bytes_produzidos": 18,
        "bytes_servidos": 18,
    }
    linha_malote = {
        "ts": "2026-11-28T11:00:01.000-03:00",
        "evento_id": "019a0000-0000-7000-8000-000000000021",
        "schema_v": 1,
        "evento": "malote",
        "execucao_id": "exec-0001",
        "pipeline": "ingestao",
        "verbo_entrada": "acervo",
        "cadeira": "engenharia",
        "sessao_id": "489968fd-8076-406e-88b9-3a1646d49f80",
        "ordem_id": "o20261128T110000-abc123",
        "exit_code": 0,
    }
    linha_execucao = {
        "ts": "2026-11-28T11:00:01.050-03:00",
        "evento_id": "019a0000-0000-7000-8000-000000000022",
        "schema_v": 1,
        "evento": "execucao",
        "execucao_id": "exec-0001",
        "alvo_classe": "pipeline",
        "alvo_chave": "ingestao",
        "verbo_entrada": "acervo",
        "estado": "concluida",
        "cadeira": "engenharia",
        "sessao_id": "489968fd-8076-406e-88b9-3a1646d49f80",
        "ordem_id": "o20261128T110000-abc123",
        "exit_code": 0,
    }

    inv = extrator.Invalidos()
    item_bot = extrator.para_item(linha_bot, "2026-11-28", 1, inv)
    assert inv.total == 0
    assert item_bot["evento"]["tipo"] == "giro"
    assert item_bot["giro"]["tool"] == "acervo"
    assert item_bot["giro"]["ato"] == "ingerir"
    assert item_bot["giro"]["classe"] == "ok"

    dados_dia = (
        "\n".join(json.dumps(ln) for ln in (linha_bot, linha_malote, linha_execucao)) + "\n"
    ).encode("utf-8")
    resumo = extrator.relatorio_seco(extrator.Extracao("2026-11-28", dados_dia))
    assert resumo["sem_traducao"] == {}
    assert resumo["campos_invalidos"] == 0
    assert resumo["por_tipo_da_particao"] == {"execucao": 1, "giro": 1, "malote": 1}
    assert resumo["giros_por_tool"] == {"acervo": 1}


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


def test_verificar_com_dois_testes_despacha_motor_suite_e_devolve_laudo_como_veio(
    tmp_path: Path,
) -> None:
    despacho, _mod_recusa, _oplog, verificador = _modulos_despacho()
    from verificador.tipos import MOTOR_SUITE_TESTES

    arvore = _preparar_arvore_duas_fichas(tmp_path)
    arq_duble = tmp_path / "duble_suite.json"
    arq_duble.write_text(
        json.dumps(
            {
                "casos": {
                    "tests/test_a1.py::test_um": True,
                    "tests/test_a2.py::test_dois": False,
                }
            }
        ),
        encoding="utf-8",
    )
    pedidos_vistos: list[dict[str, Any]] = []
    cfg = despacho.ConfigClienteDespacho(runner=_runner_ponte_suite_real(arq_duble, pedidos_vistos))
    delegador = despacho.DelegadorSuiteDespacho(config_cliente=cfg, ident={"sujeito": SUJEITO_DONO})

    rc, stdout_txt, stderr_txt = _rodar_verificador_duas_fichas(arvore, delegador)
    assert rc == SAIDA_OK
    assert stderr_txt == ""
    assert len(pedidos_vistos) == 1
    assert pedidos_vistos[0]["alvo_classe"] == "motor"
    assert pedidos_vistos[0]["alvo_chave"] == MOTOR_SUITE_TESTES

    dados = json.loads(stdout_txt)
    assert dados["versao_contrato"] == verificador.VERSAO_CONTRATO
    assert dados["veredito"]["motor"] == MOTOR_SUITE_TESTES
    assert dados["veredito"]["resultado"] == "nao"
    assert dados["veredito"]["constatacao"] == "divergente"
    assert len(dados["itens"]) == TOTAL_ITENS_DUAS_FICHAS
    assert [it["resultado"] for it in dados["itens"]] == ["sim", "nao"]
    assert len(dados["apontamentos"]) == 1
    assert dados["apontamentos"][0]["item"] == "test_dois"


def test_verificar_sai_3_quando_porta_despachar_nao_responde_ou_esta_ausente(
    tmp_path: Path,
) -> None:
    despacho, _mod_recusa, _oplog, _verificador = _modulos_despacho()
    arvore = _preparar_arvore_duas_fichas(tmp_path)
    cfg_ausente = despacho.ConfigClienteDespacho(
        python_porta=tmp_path / "python-inexistente",
        core_dir=tmp_path / "core-inexistente",
    )
    delegador_ausente = despacho.DelegadorSuiteDespacho(config_cliente=cfg_ausente)
    rc_ausente, out_ausente, err_ausente = _rodar_verificador_duas_fichas(arvore, delegador_ausente)
    assert rc_ausente == SAIDA_DEPENDENCIA
    assert out_ausente == ""
    assert _ler_recusa_json(err_ausente)["codigo"] == "dependencia-sem-resposta"

    def _runner_timeout(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="porta.despachar.entrada", timeout=1.0)

    delegador_timeout = despacho.DelegadorSuiteDespacho(
        config_cliente=despacho.ConfigClienteDespacho(runner=_runner_timeout)
    )
    rc_to, out_to, err_to = _rodar_verificador_duas_fichas(arvore, delegador_timeout)
    assert rc_to == SAIDA_DEPENDENCIA
    assert out_to == ""
    assert _ler_recusa_json(err_to)["codigo"] == "dependencia-sem-resposta"


def test_verificar_sai_5_quando_suite_passa_do_prazo_do_verificar(tmp_path: Path) -> None:
    despacho, _mod_recusa, _oplog, _verificador = _modulos_despacho()
    arvore = _preparar_arvore_duas_fichas(tmp_path)

    def _runner_unidade_parada_pelo_despachar(
        *_args: Any,
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        envelope_timeout = {
            "erro": {
                "codigo": "tempo-esgotado",
                "onde": "motor:harness:suite-de-testes",
                "recebido": "prazo_s=0.1",
                "regra": "prazo-do-verificar",
                "cura": "a suíte de testes excedeu o prazo do verificar e a unidade foi encerrada",
                "proximo": "",
            },
            "erros": [],
        }
        linha = json.dumps(envelope_timeout) + "\n"
        return subprocess.CompletedProcess(
            args=["python", "-m", "porta.despachar.entrada"],
            returncode=SAIDA_INDETERMINAVEL,
            stdout=linha,
            stderr=linha,
        )

    delegador = despacho.DelegadorSuiteDespacho(
        config_cliente=despacho.ConfigClienteDespacho(runner=_runner_unidade_parada_pelo_despachar)
    )
    rc, stdout_txt, stderr_txt = _rodar_verificador_duas_fichas(arvore, delegador, prazo_s=0.1)
    assert rc == SAIDA_INDETERMINAVEL
    assert stdout_txt == ""
    assert _ler_recusa_json(stderr_txt)["codigo"] == "tempo-esgotado"


def test_cliente_despacho_devolve_em_andamento_com_proximo_pronto() -> None:
    despacho, _mod_recusa, _oplog, _verificador = _modulos_despacho()

    def _runner_andamento(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        corpo = {
            "em_andamento": True,
            "execucao_id": "exec-001",
            "estado": "em_andamento",
            "proximo": "acervo ler execucao exec-001",
        }
        return subprocess.CompletedProcess(
            args=["python"],
            returncode=SAIDA_OK,
            stdout=json.dumps(corpo) + "\n",
            stderr="",
        )

    resp = despacho.despachar_pelo_core(
        despacho.PedidoClienteDespacho(
            verbo_entrada="acervo",
            alvo_classe="pipeline",
            alvo_chave="ingestao",
            parametros={"obra": "obra:1"},
            ident={"sujeito": SUJEITO_DONO},
        ),
        config=despacho.ConfigClienteDespacho(runner=_runner_andamento),
    )
    assert resp.exit_code == SAIDA_OK
    assert resp.em_andamento is True
    assert resp.execucao_id == "exec-001"
    assert resp.proximo == "acervo ler execucao exec-001"


def test_ler_execucao_pelo_evento_oplog_respeita_sujeito_e_chave_inexistente(
    tmp_path: Path,
) -> None:
    despacho, mod_recusa, oplog_mod, _verificador = _modulos_despacho()
    pasta_ops = tmp_path / "bruto"
    assert oplog_mod.emitir(
        {
            "evento": "execucao",
            "execucao_id": "exec-abc-123",
            "alvo_classe": "pipeline",
            "alvo_chave": "ingestao",
            "verbo_entrada": "acervo",
            "estado": "em_andamento",
            "exit_code": None,
            "sujeito": SUJEITO_DONO,
            "fases": [],
        },
        diretorio_=pasta_ops,
    )
    assert oplog_mod.emitir(
        {
            "evento": "execucao",
            "execucao_id": "exec-abc-123",
            "alvo_classe": "pipeline",
            "alvo_chave": "ingestao",
            "verbo_entrada": "acervo",
            "estado": "concluida",
            "exit_code": SAIDA_OK,
            "artefato_digest": "sha256:" + ("b" * 64),
            "dur_ms": 210,
            "sujeito": SUJEITO_DONO,
            "fases": [
                {
                    "id": "incorporar-item",
                    "indice": 0,
                    "verbo": "acervo",
                    "ato": "ingerir",
                    "estado": "concluido",
                    "exit_code": SAIDA_OK,
                    "linha": "item 42 incorporado",
                    "harness_sha": "56d22669",
                    "dur_ms": 110,
                }
            ],
        },
        diretorio_=pasta_ops,
    )

    lido = despacho.ler_execucao(
        "acervo",
        "exec-abc-123",
        sujeito=SUJEITO_DONO,
        diretorio_oplog=pasta_ops,
    )
    assert lido["estado"] == "concluida"
    assert lido["exit_code"] == SAIDA_OK
    assert len(lido["fases"]) == 1
    assert lido["fases"][0]["linha"] == "item 42 incorporado"
    assert lido["fases"][0]["harness_sha"] == "56d22669"

    with pytest.raises(mod_recusa.Recusa) as exc_inexistente:
        despacho.ler_execucao("acervo", "exec-nao-existe", sujeito=SUJEITO_DONO, diretorio_oplog=pasta_ops)
    assert exc_inexistente.value.saida == SAIDA_INEXISTENTE
    assert exc_inexistente.value.codigo == "chave-inexistente"

    with pytest.raises(mod_recusa.Recusa) as exc_negado:
        despacho.ler_execucao("acervo", "exec-abc-123", sujeito=SUJEITO_OUTRO, diretorio_oplog=pasta_ops)
    assert exc_negado.value.saida == SAIDA_NEGADA
    assert exc_negado.value.codigo == "acesso-negado"


def test_ambiente_padrao_do_verificador_carrega_delegador_da_suite() -> None:
    despacho, _mod_recusa, _oplog, verificador = _modulos_despacho()
    amb = verificador._ambiente_padrao()
    assert isinstance(amb.delegador_suite, despacho.DelegadorSuiteDespacho)
