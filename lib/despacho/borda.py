"""borda — entrada comum dos atos `despachar` e `ler execucao` para qualquer verbo (card #4455, t11).

Confere no registro de verbos (`registro/porta.yaml`) se o verbo de entrada declara o ato
`despachar`. Verbo que não declara recusa com saída `2` (`ato-nao-declarado`) sem chamar o core.
Verbo que declara encaminha o pedido ao `porta.despachar.entrada` por processo (via `cliente.py`),
com classe padrão `pipeline` quando omitida, e expõe a leitura `ler execucao <chave>` pelo evento
`execucao` na trilha.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from leitura.recusa import Recusa

from .cliente import (
    ConfigClienteDespacho,
    PedidoClienteDespacho,
    RespostaClienteDespacho,
    despachar_pelo_core,
)
from .execucao import ler_execucao

SAIDA_OK = 0
SAIDA_USO = 2
SAIDA_DEPENDENCIA = 3
CLASSES_ALVO_VALIDAS = frozenset({"pipeline", "motor", "delegacao"})
REGRA_BORDA_DESPACHAR = "ato:despachar §Entrada comum pela camada de verbos"

_RE_PARENTESES = re.compile(r"\([^)]*\)")
_RE_ATOS_DESCRICAO = re.compile(r"(?:^|·|\s)atos:\s*(.+)$", re.IGNORECASE | re.DOTALL)


def _extrair_atos_descricao(descricao: str) -> frozenset[str]:
    m = _RE_ATOS_DESCRICAO.search(descricao)
    if m is None:
        return frozenset()
    sem_parenteses = _RE_PARENTESES.sub("", m.group(1))
    atos: set[str] = set()
    for bruto in re.split(r"[,·;]", sem_parenteses):
        limpo = " ".join(bruto.split()).strip().rstrip(".")
        if not limpo:
            continue
        atos.add(limpo)
        atos.add(limpo.split(" ", 1)[0])
    return frozenset(atos)


def _caminho_porta_yaml_padrao() -> Path:
    env_h = (os.environ.get("PF_HARNESS_DIR") or "").strip()
    if env_h:
        return Path(env_h) / "registro" / "porta.yaml"
    return Path(__file__).resolve().parents[2] / "registro" / "porta.yaml"


def verbo_declara_despachar(verbo: str, *, porta_yaml: Path | None = None) -> bool:
    """Retorna True se `verbo` existe em `registro/porta.yaml` e declara o ato `despachar`."""
    arq = porta_yaml or _caminho_porta_yaml_padrao()
    try:
        bruto = yaml.safe_load(arq.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Recusa(
            SAIDA_DEPENDENCIA,
            "dependencia-sem-resposta",
            onde=f"{verbo} despachar",
            recebido=str(exc),
            regra=REGRA_BORDA_DESPACHAR,
            cura="verifique a presença e integridade de registro/porta.yaml na release",
        ) from exc
    verbos = bruto.get("verbos") if isinstance(bruto, dict) else None
    if not isinstance(verbos, dict):
        return False
    entrada = verbos.get(verbo)
    if not isinstance(entrada, dict):
        return False
    desc = str(entrada.get("descricao") or "")
    return "despachar" in _extrair_atos_descricao(desc)


def _exigir_verbo_declara_despachar(verbo: str, *, porta_yaml: Path | None = None) -> None:
    if not verbo_declara_despachar(verbo, porta_yaml=porta_yaml):
        raise Recusa(
            SAIDA_USO,
            "ato-nao-declarado",
            onde=f"{verbo} despachar",
            recebido=verbo,
            regra=REGRA_BORDA_DESPACHAR,
            cura=f"declare o ato 'despachar' na entrada de '{verbo}' em registro/porta.yaml",
        )


def _coercao_parametro(bruto: str) -> Any:
    if bruto == "true":
        return True
    if bruto == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", bruto):
        return int(bruto)
    return bruto


def _parsear_argv_despachar(verbo: str, argv: Sequence[str]) -> tuple[str, str, dict[str, Any], int, str]:
    pos: list[str] = []
    params: dict[str, Any] = {}
    fan_out = 1
    pedido_id = ""
    i = 0
    tokens = list(argv)
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--fan-out":
            i += 1
            if i >= len(tokens) or not tokens[i].isdigit() or int(tokens[i]) < 1:
                raise Recusa(
                    SAIDA_USO,
                    "uso-invalido",
                    onde=f"{verbo} despachar",
                    recebido="--fan-out",
                    regra=REGRA_BORDA_DESPACHAR,
                    cura="informe inteiro positivo após --fan-out",
                )
            fan_out = int(tokens[i])
        elif tok == "--pedido":
            i += 1
            if i >= len(tokens) or not tokens[i].strip():
                raise Recusa(
                    SAIDA_USO,
                    "uso-invalido",
                    onde=f"{verbo} despachar",
                    recebido="--pedido",
                    regra=REGRA_BORDA_DESPACHAR,
                    cura="informe identificador após --pedido",
                )
            pedido_id = tokens[i].strip()
        elif tok == "--param":
            i += 1
            if i >= len(tokens) or "=" not in tokens[i]:
                raise Recusa(
                    SAIDA_USO,
                    "uso-invalido",
                    onde=f"{verbo} despachar",
                    recebido=tokens[i] if i < len(tokens) else "--param",
                    regra=REGRA_BORDA_DESPACHAR,
                    cura="use --param chave=valor",
                )
            k, v = tokens[i].split("=", 1)
            params[k.strip()] = _coercao_parametro(v)
        elif tok == "--json":
            pass
        elif tok.startswith("--") and "=" in tok:
            k, v = tok[2:].split("=", 1)
            params[k.strip()] = _coercao_parametro(v)
        elif tok.startswith("-"):
            raise Recusa(
                SAIDA_USO,
                "uso-invalido",
                onde=f"{verbo} despachar",
                recebido=tok,
                regra=REGRA_BORDA_DESPACHAR,
                cura="use: <verbo> despachar [<classe>] <chave> [--fan-out N] [--pedido ID] [--param k=v]",
            )
        else:
            pos.append(tok)
        i += 1

    if len(pos) == 1:
        classe, chave = "pipeline", pos[0]
    elif len(pos) == 2 and pos[0] in CLASSES_ALVO_VALIDAS:
        classe, chave = pos[0], pos[1]
    else:
        raise Recusa(
            SAIDA_USO,
            "uso-invalido",
            onde=f"{verbo} despachar",
            recebido=" ".join(pos) or "<vazio>",
            regra=REGRA_BORDA_DESPACHAR,
            cura="use: <verbo> despachar [pipeline|motor|delegacao] <chave>",
        )
    return classe, chave, params, fan_out, pedido_id


def despachar_pela_borda(
    verbo: str,
    argv: Sequence[str],
    *,
    parametros_extra: Mapping[str, Any] | None = None,
    porta_yaml: Path | None = None,
    config_cliente: ConfigClienteDespacho | None = None,
    ident: Mapping[str, Any] | None = None,
) -> RespostaClienteDespacho:
    """Valida a declaração do ato `despachar` no registro e despacha o alvo ao core."""
    _exigir_verbo_declara_despachar(verbo, porta_yaml=porta_yaml)
    classe, chave, params_cli, fan_out, pedido_id = _parsear_argv_despachar(verbo, argv)
    parametros = {**params_cli, **dict(parametros_extra or {})}
    pedido = PedidoClienteDespacho(
        verbo_entrada=verbo,
        alvo_classe=classe,
        alvo_chave=chave,
        parametros=parametros,
        ident=dict(ident or {}),
        pedido_id=pedido_id,
        fan_out=fan_out,
    )
    return despachar_pelo_core(pedido, config=config_cliente)


def ler_execucao_pela_borda(
    verbo: str,
    chave_execucao: str,
    *,
    sujeito: str,
    porta_yaml: Path | None = None,
    diretorio_oplog: Path | None = None,
) -> dict[str, Any]:
    """Valida que `verbo` declara `despachar` e lê o evento `execucao` da chave."""
    _exigir_verbo_declara_despachar(verbo, porta_yaml=porta_yaml)
    return ler_execucao(verbo, chave_execucao, sujeito=sujeito, diretorio_oplog=diretorio_oplog)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI de borda para verbos em bash: `python3 -m despacho.borda <verbo> despachar|ler ...`."""
    tokens = list(sys.argv[1:] if argv is None else argv)
    if len(tokens) < 2:
        sys.stderr.write("uso: python3 -m despacho.borda <verbo> <despachar|ler> ...\n")
        return SAIDA_USO
    verbo, ato, resto = tokens[0], tokens[1], tokens[2:]
    try:
        if ato == "despachar":
            stdin_params: dict[str, Any] = {}
            if not sys.stdin.isatty():
                bruto_in = sys.stdin.read().strip()
                if bruto_in:
                    lido = json.loads(bruto_in)
                    if isinstance(lido, dict):
                        stdin_params = lido
            resp = despachar_pela_borda(verbo, resto, parametros_extra=stdin_params)
            if resp.stdout:
                sys.stdout.write(resp.stdout)
                sys.stdout.flush()
            if resp.stderr:
                sys.stderr.write(resp.stderr)
                sys.stderr.flush()
            return resp.exit_code
        if ato == "ler" and len(resto) >= 2 and resto[0] == "execucao":
            sujeito = (os.environ.get("PF_SUJEITO") or "").strip()
            dados = ler_execucao_pela_borda(verbo, resto[1], sujeito=sujeito)
            sys.stdout.write(json.dumps(dados, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            return SAIDA_OK
        raise Recusa(
            SAIDA_USO,
            "uso-invalido",
            onde=f"{verbo} {ato}",
            recebido=" ".join(resto),
            regra=REGRA_BORDA_DESPACHAR,
            cura="use: <verbo> despachar [<classe>] <chave> ou <verbo> ler execucao <chave>",
        )
    except Recusa as exc:
        sys.stderr.write(json.dumps(exc.campos(), ensure_ascii=False) + "\n")
        sys.stderr.flush()
        return exc.saida


if __name__ == "__main__":
    raise SystemExit(main())
