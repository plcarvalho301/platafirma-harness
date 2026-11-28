# componente: componente:suite
"""Suíte da borda comum do ato `despachar` e `ler execucao` (card #4455, t11).

Cobre o Aceite 6:
- verbo de prova que declara `despachar` no registro de prova chega ao core pela camada comum
  com classe explícita (`pipeline`), sem classe (alvo padrão `pipeline`), `<chave>`, `--fan-out`,
  `--pedido`, parâmetros JSON na entrada padrão e prazo de espera `PF_PRAZO_S`, devolvendo a
  saída e o código do core (inclusive `em andamento <chave>` e envelope de erro);
- verbo que não declara `despachar` recusa com saída `2` (`ato-nao-declarado`) sem chamar o core;
- classe diferente de `pipeline` (`motor`, `delegacao`) ou `stdin` que não seja objeto JSON
  recusam com saída `2` sem chamar o core;
- core sem resposta sai `3` (`dependencia-sem-resposta`);
- `ler execucao <chave>` da mesma borda lê o evento `execucao` (saída `0` para o dono, `1` para
  chave inexistente e `4` para outro sujeito);
- invocação real por subprocesso do executável de prova `fixtures/despacho/verbo-prova`.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_RAIZ = Path(__file__).resolve().parents[2]
_LIB = _RAIZ / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from despacho import (  # noqa: E402
    AmbienteBordaDespachar,
    ConfigClienteDespacho,
    PedidoClienteDespacho,
    RespostaClienteDespacho,
    executar_ato,
    executar_despachar,
    executar_ler_execucao,
)

FIXTURES_DESPACHO = Path(__file__).resolve().parent / "fixtures" / "despacho"
PORTA_YAML_PROVA = FIXTURES_DESPACHO / "porta.yaml"
VERBO_PROVA_BIN = FIXTURES_DESPACHO / "verbo-prova"

SAIDA_OK = 0
SAIDA_INEXISTENTE = 1
SAIDA_USO = 2
SAIDA_DEPENDENCIA = 3
SAIDA_NEGADA = 4
FAN_OUT_TRES = 3
PRAZO_CUSTOM_S = 12.5


def _ambiente_duble(
    *,
    invocar_core: Any = None,
    config_cliente: ConfigClienteDespacho | None = None,
    stdin_texto: str = "",
    prazo_espera_s: float | None = None,
    diretorio_oplog: Path | None = None,
    sujeito: str = "sujeito-dono",
) -> tuple[AmbienteBordaDespachar, io.StringIO, io.StringIO]:
    out = io.StringIO()
    err = io.StringIO()
    kwargs: dict[str, Any] = {
        "porta_yaml": PORTA_YAML_PROVA,
        "config_cliente": config_cliente,
        "diretorio_oplog": diretorio_oplog,
        "sujeito": sujeito,
        "ident": {
            "sujeito": sujeito,
            "cadeira": "engenharia",
            "sessao_id": "sessao-borda-4455",
            "ordem_id": "o20261128T114000-abcdef",
        },
        "prazo_espera_s": prazo_espera_s,
        "stdin": io.StringIO(stdin_texto),
        "stdout": out,
        "stderr": err,
    }
    if invocar_core is not None:
        kwargs["invocar_core"] = invocar_core
    return AmbienteBordaDespachar(**kwargs), out, err


def _gravar_oplog_execucao(pasta: Path, dia: str, linhas: list[dict[str, Any]]) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / f"ops-{dia}.jsonl"
    arq.write_text(
        "".join(json.dumps(ln, ensure_ascii=False) + "\n" for ln in linhas),
        encoding="utf-8",
    )
    return arq


def _criar_core_falso_em_disco(pasta: Path) -> tuple[Path, Path]:
    """Cria árvore `core/porta/despachar/entrada.py` sintética para o subprocesso de `verbo-prova`."""
    core_dir = pasta / "core"
    pacote = core_dir / "porta" / "despachar"
    pacote.mkdir(parents=True, exist_ok=True)
    (core_dir / "porta" / "__init__.py").write_text("", encoding="utf-8")
    (pacote / "__init__.py").write_text("", encoding="utf-8")
    registro_chamadas = pasta / "chamadas-core.jsonl"
    script_entrada = f"""from __future__ import annotations
import json, pathlib, sys

pedido = json.loads(sys.stdin.read() or "{{}}")
arq = pathlib.Path({str(registro_chamadas)!r})
with arq.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(pedido, ensure_ascii=False) + "\\n")

corpo = {{
    "execucao_id": "exec-subproc-01",
    "pipeline": pedido["alvo_chave"],
    "estado": "concluida",
    "exit_code": 0,
    "passos": [{{"id": "passo-unico", "indice": 0, "exit": 0, "linha": "ok-subproc"}}],
    "conteudo": "entrega-final\\n",
}}
sys.stdout.write(json.dumps(corpo, ensure_ascii=False) + "\\n")
raise SystemExit(0)
"""
    (pacote / "entrada.py").write_text(script_entrada, encoding="utf-8")
    return core_dir, registro_chamadas


def test_verbo_declarado_chega_ao_core_com_classe_chave_fan_out_pedido_e_parametros(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pedidos_recebidos: list[PedidoClienteDespacho] = []
    monkeypatch.setenv("PF_PRAZO_S", str(PRAZO_CUSTOM_S))

    def _core_ok(
        pedido: PedidoClienteDespacho,
        *,
        config: ConfigClienteDespacho | None = None,
    ) -> RespostaClienteDespacho:
        del config
        pedidos_recebidos.append(pedido)
        corpo = {
            "execucao_id": "exec-0001",
            "pipeline": pedido.alvo_chave,
            "estado": "concluida",
            "exit_code": 0,
            "passos": [{"id": "passo-a", "indice": 0, "exit": 0, "linha": "feito"}],
            "conteudo": "resultado-final\n",
        }
        return RespostaClienteDespacho(
            exit_code=0,
            execucao_id="exec-0001",
            em_andamento=False,
            stdout=json.dumps(corpo) + "\n",
            stderr="",
            dados=corpo,
        )

    amb, out, err = _ambiente_duble(
        invocar_core=_core_ok,
        stdin_texto='{"obra": "obra:42", "forcar": false}',
    )
    rc = executar_despachar(
        "verbo-prova",
        ["pipeline", "ingestao", "--fan-out", "3", "--pedido", "ped-42"],
        ambiente=amb,
    )
    assert rc == SAIDA_OK
    assert err.getvalue() == ""
    assert len(pedidos_recebidos) == 1
    ped = pedidos_recebidos[0]
    assert ped.verbo_entrada == "verbo-prova"
    assert ped.alvo_classe == "pipeline"
    assert ped.alvo_chave == "ingestao"
    assert ped.fan_out == FAN_OUT_TRES
    assert ped.pedido_id == "ped-42"
    assert ped.prazo_espera_s == PRAZO_CUSTOM_S
    assert ped.parametros == {"obra": "obra:42", "forcar": False}
    linhas_out = out.getvalue().splitlines()
    assert linhas_out[0] == "exec-0001"
    assert "passo-a\texit=0\tfeito" in linhas_out[1]
    assert linhas_out[2] == "resultado-final"


def test_sem_classe_assume_pipeline_e_propaga_em_andamento_com_chave() -> None:
    pedidos_recebidos: list[PedidoClienteDespacho] = []

    def _core_em_andamento(
        pedido: PedidoClienteDespacho,
        *,
        config: ConfigClienteDespacho | None = None,
    ) -> RespostaClienteDespacho:
        del config
        pedidos_recebidos.append(pedido)
        corpo = {
            "em_andamento": True,
            "execucao_id": "exec-lento-99",
            "estado": "em_andamento",
            "mensagem": "em andamento exec-lento-99",
            "proximo": "verbo-prova ler execucao exec-lento-99",
        }
        return RespostaClienteDespacho(
            exit_code=0,
            execucao_id="exec-lento-99",
            em_andamento=True,
            stdout=json.dumps(corpo) + "\n",
            stderr="",
            dados=corpo,
            proximo="verbo-prova ler execucao exec-lento-99",
        )

    amb, out, err = _ambiente_duble(invocar_core=_core_em_andamento, prazo_espera_s=5.0)
    rc = executar_ato("verbo-prova", "despachar", ["ingestao"], ambiente=amb)
    assert rc == SAIDA_OK
    assert err.getvalue() == ""
    assert len(pedidos_recebidos) == 1
    assert pedidos_recebidos[0].alvo_classe == "pipeline"
    assert pedidos_recebidos[0].alvo_chave == "ingestao"
    assert pedidos_recebidos[0].parametros == {}
    assert out.getvalue() == (
        "em andamento exec-lento-99\nproximo: verbo-prova ler execucao exec-lento-99\n"
    )


def test_verbo_sem_despachar_declarado_recusa_com_2_ato_nao_declarado_sem_chamar_core() -> None:
    chamadas_core: list[PedidoClienteDespacho] = []

    def _nunca_chamar(
        pedido: PedidoClienteDespacho,
        *,
        config: ConfigClienteDespacho | None = None,
    ) -> RespostaClienteDespacho:
        del config
        chamadas_core.append(pedido)
        raise AssertionError("core não pode ser chamado para verbo sem despachar declarado")

    amb, out, err = _ambiente_duble(invocar_core=_nunca_chamar)
    rc = executar_despachar("verbo-sem-despachar", ["pipeline", "ingestao"], ambiente=amb)
    assert rc == SAIDA_USO
    assert chamadas_core == []
    assert out.getvalue() == ""
    envelope = json.loads(err.getvalue())
    assert envelope["erro"]["codigo"] == "ato-nao-declarado"
    assert envelope["erro"]["onde"] == "verbo-sem-despachar despachar"


@pytest.mark.parametrize(
    ("argv", "stdin_txt", "codigo_esperado"),
    [
        (["motor", "suite-de-testes"], "{}", "classe-invalida"),
        (["delegacao", "auditor-de-plano"], "{}", "classe-invalida"),
        (["pipeline", "ingestao"], '["lista", "nao", "eh", "objeto"]', "parametro-invalido"),
        (["pipeline", "ingestao"], '"escalar"', "parametro-invalido"),
        (["pipeline", "ingestao"], "{json-quebrado", "parametro-invalido"),
        (["pipeline", "../escape"], "{}", "chave-invalida"),
        (["pipeline", "ingestao", "--fan-out", "0"], "{}", "parametro-invalido"),
        (["pipeline", "ingestao", "--flag-inexistente"], "{}", "flag-invalida"),
    ],
)
def test_classe_invalida_ou_stdin_fora_de_objeto_json_recusam_com_2_sem_chamar_core(
    argv: list[str],
    stdin_txt: str,
    codigo_esperado: str,
) -> None:
    chamadas_core: list[PedidoClienteDespacho] = []

    def _nunca_chamar(
        pedido: PedidoClienteDespacho,
        *,
        config: ConfigClienteDespacho | None = None,
    ) -> RespostaClienteDespacho:
        del config
        chamadas_core.append(pedido)
        raise AssertionError("core não pode ser chamado em erro de borda")

    amb, _out, err = _ambiente_duble(invocar_core=_nunca_chamar, stdin_texto=stdin_txt)
    rc = executar_despachar("verbo-prova", argv, ambiente=amb)
    assert rc == SAIDA_USO
    assert chamadas_core == []
    envelope = json.loads(err.getvalue())
    assert envelope["erro"]["codigo"] == codigo_esperado


def test_core_sem_resposta_sai_3_dependencia_sem_resposta(tmp_path: Path) -> None:
    cfg_ausente = ConfigClienteDespacho(
        python_porta=tmp_path / "nao-existe" / "python",
        core_dir=tmp_path / "nao-existe" / "core",
    )
    amb, _out, err = _ambiente_duble(config_cliente=cfg_ausente, prazo_espera_s=2.0)
    rc = executar_despachar("verbo-prova", ["pipeline", "ingestao", "--json"], ambiente=amb)
    assert rc == SAIDA_DEPENDENCIA
    envelope = json.loads(err.getvalue())
    assert envelope["erro"]["codigo"] == "dependencia-sem-resposta"


def test_ler_execucao_pela_borda_le_evento_execucao_e_respeita_sujeito(tmp_path: Path) -> None:
    oplog_dir = tmp_path / "ops"
    _gravar_oplog_execucao(
        oplog_dir,
        "2026-11-28",
        [
            {
                "ts": "2026-11-28T11:30:00-03:00",
                "evento": "execucao",
                "execucao_id": "exec-borda-77",
                "alvo_classe": "pipeline",
                "alvo_chave": "ingestao",
                "verbo_entrada": "verbo-prova",
                "sujeito": "sujeito-dono",
                "estado": "concluida",
                "exit_code": 0,
                "artefato_digest": "sha256:" + ("b" * 64),
                "dur_ms": 95,
                "fases": [
                    {
                        "id": "incorporar-item",
                        "indice": 0,
                        "verbo": "acervo",
                        "ato": "ingerir",
                        "estado": "concluido",
                        "exit_code": 0,
                        "linha": "obra:42 incorporada",
                        "harness_sha": "56f075a4747a",
                        "dur_ms": 50,
                    }
                ],
            }
        ],
    )

    amb_ok, out_ok, err_ok = _ambiente_duble(diretorio_oplog=oplog_dir, sujeito="sujeito-dono")
    rc_ok = executar_ato(
        "verbo-prova",
        "ler",
        ["execucao", "exec-borda-77", "--json"],
        ambiente=amb_ok,
    )
    assert rc_ok == SAIDA_OK
    assert err_ok.getvalue() == ""
    lido = json.loads(out_ok.getvalue())
    assert lido["execucao_id"] == "exec-borda-77"
    assert lido["estado"] == "concluida"
    assert lido["fases"][0]["id"] == "incorporar-item"

    amb_outro, _out_outro, err_outro = _ambiente_duble(
        diretorio_oplog=oplog_dir,
        sujeito="outro-sujeito",
    )
    rc_outro = executar_ler_execucao(
        "verbo-prova",
        ["exec-borda-77"],
        ambiente=amb_outro,
    )
    assert rc_outro == SAIDA_NEGADA
    assert json.loads(err_outro.getvalue())["erro"]["codigo"] == "acesso-negado"

    amb_inex, _out_inex, err_inex = _ambiente_duble(
        diretorio_oplog=oplog_dir,
        sujeito="sujeito-dono",
    )
    rc_inex = executar_ler_execucao(
        "verbo-prova",
        ["exec-inexistente"],
        ambiente=amb_inex,
    )
    assert rc_inex == SAIDA_INEXISTENTE
    assert json.loads(err_inex.getvalue())["erro"]["codigo"] == "chave-inexistente"


def test_executavel_verbo_prova_em_subprocesso_despacha_e_recusa_sem_regra_no_verbo(
    tmp_path: Path,
) -> None:
    core_dir, arq_chamadas = _criar_core_falso_em_disco(tmp_path)
    env_base = {
        **os.environ,
        "PF_PORTA_YAML": str(PORTA_YAML_PROVA),
        "PF_PORTA_PYTHON": sys.executable,
        "PF_CORE_DIR": str(core_dir),
        "PF_SUJEITO": "sujeito-subproc",
        "PF_CADEIRA": "engenharia",
        "PF_SESSAO": "sessao-subproc",
        "PF_PRAZO_S": "9.5",
    }

    proc_ok = subprocess.run(
        [
            sys.executable,
            str(VERBO_PROVA_BIN),
            "despachar",
            "pipeline",
            "ingestao",
            "--fan-out=2",
            "--pedido=ped-sub",
        ],
        input='{"obra": "obra:99"}',
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env_base,
    )
    assert proc_ok.returncode == SAIDA_OK, proc_ok.stderr
    assert "exec-subproc-01" in proc_ok.stdout
    assert "entrega-final" in proc_ok.stdout
    chamadas = [json.loads(ln) for ln in arq_chamadas.read_text(encoding="utf-8").splitlines()]
    assert len(chamadas) == 1
    assert chamadas[0]["verbo_entrada"] == "verbo-prova"
    assert chamadas[0]["alvo_classe"] == "pipeline"
    assert chamadas[0]["alvo_chave"] == "ingestao"
    assert chamadas[0]["fan_out"] == 2
    assert chamadas[0]["pedido_id"] == "ped-sub"
    assert chamadas[0]["prazo_espera_s"] == 9.5
    assert chamadas[0]["parametros"] == {"obra": "obra:99"}

    env_sem_ato = {**env_base, "PF_VERBO_PROVA": "verbo-sem-despachar"}
    proc_neg = subprocess.run(
        [sys.executable, str(VERBO_PROVA_BIN), "despachar", "pipeline", "ingestao"],
        input="{}",
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=env_sem_ato,
    )
    assert proc_neg.returncode == SAIDA_USO
    assert json.loads(proc_neg.stderr)["erro"]["codigo"] == "ato-nao-declarado"
    assert len(arq_chamadas.read_text(encoding="utf-8").splitlines()) == 1
