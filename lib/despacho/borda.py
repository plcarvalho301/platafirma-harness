"""borda — entrada comum de `<verbo> despachar` e `<verbo> ler execucao` (card #4455, t11).

Todo verbo que declara o ato `despachar` em `registro/porta.yaml` delega a esta peça:
- `<verbo> despachar [<classe>] <chave> [--fan-out <n>] [--pedido <id>] [--json]`, lendo os
  parâmetros da entrada padrão como objeto JSON e o prazo de espera de `PF_PRAZO_S`;
- `<verbo> ler execucao <chave> [--json]`, lendo o estado pelo evento `execucao` na trilha.

Aplica Parse, don't validate na fronteira: verbo sem `despachar` declarado sai `2`
(`ato-nao-declarado`), classe diferente de `pipeline` ou `stdin` que não seja objeto JSON
saem `2` sem chamar o core, e ausência de resposta do core sai `3` (`dependencia-sem-resposta`).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

import yaml
from leitura.recusa import Recusa, formato_lista

from .cliente import (
    PRAZO_ESPERA_PADRAO_S,
    ConfigClienteDespacho,
    PedidoClienteDespacho,
    RespostaClienteDespacho,
    despachar_pelo_core,
)
from .execucao import ler_execucao

SAIDA_OK = 0
SAIDA_USO = 2
SAIDA_DEPENDENCIA = 3

REGRA_DECLARACAO_ATO = "ato:despachar §O que o verbo declara para aceitar o despachar?"
REGRA_FORMA_DESPACHAR = "ato:despachar §Qual é a forma?"
REGRA_LEITURA_EXECUCAO = "ato:despachar §Acompanhamento assíncrono por ler execucao"

_RE_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_RE_PEDIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RE_PARENTESES = re.compile(r"\([^)]*\)")
_RE_ATOS_DESCRICAO = re.compile(r"(?:^|·|\s)atos:\s*(.+)$", re.IGNORECASE | re.DOTALL)
_MAX_POSICIONAIS_DESPACHAR = 2
_POSICIONAIS_LER_COM_SUBATO = 2


@dataclass(frozen=True, slots=True)
class PedidoBordaDespachar:
    """Chamada validada de `<verbo> despachar [<classe>] <chave>`."""

    verbo: str
    alvo_classe: str
    alvo_chave: str
    parametros: Mapping[str, Any]
    fan_out: int = 1
    pedido_id: str = ""
    prazo_espera_s: float = PRAZO_ESPERA_PADRAO_S
    como_json: bool = False


@dataclass(frozen=True, slots=True)
class PedidoBordaLerExecucao:
    """Chamada validada de `<verbo> ler execucao <chave>`."""

    verbo: str
    chave_execucao: str
    como_json: bool = False


@dataclass(frozen=True, slots=True)
class AmbienteBordaDespachar:
    """Dependências e fluxos injetáveis da borda comum do `despachar`."""

    porta_yaml: Path | None = None
    config_cliente: ConfigClienteDespacho | None = None
    diretorio_oplog: Path | None = None
    sujeito: str | None = None
    ident: Mapping[str, Any] = field(default_factory=dict)
    prazo_espera_s: float | None = None
    stdin: TextIO | None = None
    stdout: TextIO | None = None
    stderr: TextIO | None = None
    invocar_core: Callable[..., RespostaClienteDespacho] = despachar_pelo_core


def _caminho_porta_yaml_padrao(amb: AmbienteBordaDespachar) -> Path:
    if amb.porta_yaml is not None:
        return Path(amb.porta_yaml)
    env_yaml = (os.environ.get("PF_PORTA_YAML") or "").strip()
    if env_yaml:
        return Path(env_yaml)
    env_harness = (os.environ.get("PF_HARNESS_DIR") or "").strip()
    if env_harness:
        return Path(env_harness) / "registro" / "porta.yaml"
    raiz_harness = Path(__file__).resolve().parents[2]
    return raiz_harness / "registro" / "porta.yaml"


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


def verbo_declara_despachar(verbo: str, porta_yaml: Path) -> bool:
    """Retorna `True` se `verbo` existe em `porta.yaml` e declara o ato `despachar`."""
    try:
        bruto = yaml.safe_load(porta_yaml.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise Recusa(
            SAIDA_DEPENDENCIA,
            "dependencia-sem-resposta",
            onde=f"{verbo} despachar",
            recebido=str(exc),
            regra=REGRA_DECLARACAO_ATO,
            cura="garanta registro/porta.yaml legível na release do harness",
        ) from exc

    verbos = bruto.get("verbos") if isinstance(bruto, dict) else None
    if not isinstance(verbos, dict):
        raise Recusa(
            SAIDA_DEPENDENCIA,
            "dependencia-sem-resposta",
            onde=f"{verbo} despachar",
            recebido=type(bruto).__name__,
            regra=REGRA_DECLARACAO_ATO,
            cura="garanta o mapa 'verbos' em registro/porta.yaml",
        )

    entrada = verbos.get(verbo)
    if not isinstance(entrada, dict):
        return False

    lista_explicita = entrada.get("atos")
    if isinstance(lista_explicita, list):
        atos = frozenset(str(a).strip() for a in lista_explicita if str(a).strip())
    else:
        atos = _extrair_atos_descricao(str(entrada.get("descricao") or ""))
    return "despachar" in atos


def _exigir_verbo_com_despachar(verbo: str, porta_yaml: Path, *, ato_chamado: str) -> str:
    verbo_limpo = verbo.strip().lower()
    onde = f"{verbo_limpo or '<verbo>'} {ato_chamado}"
    if not verbo_limpo or not _RE_KEBAB.fullmatch(verbo_limpo):
        raise Recusa(
            SAIDA_USO,
            "chave-invalida",
            onde="verbo",
            recebido=verbo,
            regra=REGRA_DECLARACAO_ATO,
            cura="informe um nome de verbo válido em kebab-case",
        )
    if not verbo_declara_despachar(verbo_limpo, porta_yaml):
        raise Recusa(
            SAIDA_USO,
            "ato-nao-declarado",
            onde=onde,
            recebido=onde,
            regra=REGRA_DECLARACAO_ATO,
            cura=f"declare 'despachar' na lista de atos do verbo '{verbo_limpo}' em registro/porta.yaml",
        )
    return verbo_limpo


def _resolver_prazo_espera(verbo: str, amb: AmbienteBordaDespachar) -> float:
    if amb.prazo_espera_s is not None:
        prazo = float(amb.prazo_espera_s)
        if not math.isfinite(prazo) or prazo <= 0:
            raise Recusa(
                SAIDA_USO,
                "parametro-invalido",
                onde=f"{verbo} despachar/prazo",
                recebido=str(amb.prazo_espera_s),
                regra=REGRA_FORMA_DESPACHAR,
                cura="informe prazo de espera positivo em segundos",
            )
        return prazo

    bruto_env = (os.environ.get("PF_PRAZO_S") or "").strip()
    if not bruto_env:
        return PRAZO_ESPERA_PADRAO_S
    try:
        prazo_env = float(bruto_env)
    except ValueError as exc:
        raise Recusa(
            SAIDA_USO,
            "parametro-invalido",
            onde=f"{verbo} despachar/PF_PRAZO_S",
            recebido=bruto_env,
            regra=REGRA_FORMA_DESPACHAR,
            cura="defina PF_PRAZO_S com número positivo em segundos",
        ) from exc
    if not math.isfinite(prazo_env) or prazo_env <= 0:
        raise Recusa(
            SAIDA_USO,
            "parametro-invalido",
            onde=f"{verbo} despachar/PF_PRAZO_S",
            recebido=bruto_env,
            regra=REGRA_FORMA_DESPACHAR,
            cura="defina PF_PRAZO_S com número maior que zero",
        )
    return prazo_env


def _converter_fan_out(verbo: str, valor: str) -> int:
    limpo = valor.strip()
    if not limpo or not limpo.lstrip("+-").isdigit():
        raise Recusa(
            SAIDA_USO,
            "flag-invalida",
            onde=f"{verbo} despachar/--fan-out",
            recebido=valor,
            regra=REGRA_FORMA_DESPACHAR,
            cura="informe inteiro maior ou igual a 1 em --fan-out <n>",
            proximo=f"{verbo} despachar pipeline <chave> --fan-out 1",
        )
    numero = int(limpo)
    if numero < 1:
        raise Recusa(
            SAIDA_USO,
            "parametro-invalido",
            onde=f"{verbo} despachar/--fan-out",
            recebido=valor,
            regra=REGRA_FORMA_DESPACHAR,
            cura="informe inteiro maior ou igual a 1 em --fan-out <n>",
            proximo=f"{verbo} despachar pipeline <chave> --fan-out 1",
        )
    return numero


def _converter_pedido_id(verbo: str, valor: str) -> str:
    limpo = valor.strip()
    if not limpo or ".." in limpo or "/" in limpo or "\\" in limpo or not _RE_PEDIDO.fullmatch(limpo):
        raise Recusa(
            SAIDA_USO,
            "flag-invalida",
            onde=f"{verbo} despachar/--pedido",
            recebido=valor,
            regra=REGRA_FORMA_DESPACHAR,
            cura="informe identificador seguro em --pedido <id> (sem barras nem '..')",
            proximo=f"{verbo} despachar pipeline <chave> --pedido <id>",
        )
    return limpo


def _decodificar_parametros_stdin(verbo: str, stdin_texto: str | None) -> dict[str, Any]:
    texto = (stdin_texto or "").strip()
    if not texto:
        return {}
    try:
        lido = json.loads(texto)
    except ValueError as exc:
        raise Recusa(
            SAIDA_USO,
            "parametro-invalido",
            onde=f"{verbo} despachar/stdin",
            recebido=texto,
            regra=REGRA_FORMA_DESPACHAR,
            cura="envie os parâmetros na entrada padrão como objeto JSON válido ({...})",
        ) from exc
    if not isinstance(lido, dict):
        raise Recusa(
            SAIDA_USO,
            "parametro-invalido",
            onde=f"{verbo} despachar/stdin",
            recebido=type(lido).__name__,
            regra=REGRA_FORMA_DESPACHAR,
            cura="envie os parâmetros na entrada padrão como objeto JSON ({...}), não lista ou escalar",
        )
    return dict(lido)


def _consumir_flag_despachar(
    verbo: str,
    arg: str,
    prox: str | None,
    estado_flags: dict[str, Any],
) -> bool:
    if arg == "--json":
        estado_flags["como_json"] = True
        return False
    if arg == "--fan-out":
        if prox is None or prox.startswith("--"):
            raise Recusa(
                SAIDA_USO,
                "flag-invalida",
                onde=f"{verbo} despachar/--fan-out",
                recebido=arg,
                regra=REGRA_FORMA_DESPACHAR,
                cura="informe o número de execuções após --fan-out",
            )
        estado_flags["fan_out"] = _converter_fan_out(verbo, prox)
        return True
    if arg.startswith("--fan-out="):
        estado_flags["fan_out"] = _converter_fan_out(verbo, arg.split("=", 1)[1])
        return False
    if arg == "--pedido":
        if prox is None or prox.startswith("-"):
            raise Recusa(
                SAIDA_USO,
                "flag-invalida",
                onde=f"{verbo} despachar/--pedido",
                recebido=arg,
                regra=REGRA_FORMA_DESPACHAR,
                cura="informe o identificador do pedido após --pedido",
            )
        estado_flags["pedido_id"] = _converter_pedido_id(verbo, prox)
        return True
    if arg.startswith("--pedido="):
        estado_flags["pedido_id"] = _converter_pedido_id(verbo, arg.split("=", 1)[1])
        return False
    raise Recusa(
        SAIDA_USO,
        "flag-invalida",
        onde=f"{verbo} despachar",
        recebido=arg,
        regra=REGRA_FORMA_DESPACHAR,
        cura="flags aceitas em despachar: --fan-out <n>, --pedido <id> e --json",
        proximo=f"{verbo} despachar [<classe>] <chave> [--fan-out <n>] [--pedido <id>] [--json]",
    )


def converter_chamada_despachar(
    verbo: str,
    argv: Sequence[str],
    *,
    stdin_texto: str | None = None,
    prazo_espera_s: float = PRAZO_ESPERA_PADRAO_S,
) -> PedidoBordaDespachar:
    """Converte `argv` (após `despachar`) e `stdin` num `PedidoBordaDespachar` imutável."""
    verbo_limpo = verbo.strip().lower()
    posicionais: list[str] = []
    estado_flags: dict[str, Any] = {"fan_out": 1, "pedido_id": "", "como_json": False}
    args = list(argv)
    idx = 0
    somente_posicionais = False

    while idx < len(args):
        tok = args[idx]
        if not somente_posicionais and tok == "--":
            somente_posicionais = True
            idx += 1
            continue
        if not somente_posicionais and tok.startswith("-"):
            prox = args[idx + 1] if idx + 1 < len(args) else None
            consumiu = _consumir_flag_despachar(verbo_limpo, tok, prox, estado_flags)
            idx += 2 if consumiu else 1
            continue
        posicionais.append(tok)
        idx += 1

    if not posicionais or len(posicionais) > _MAX_POSICIONAIS_DESPACHAR:
        raise Recusa(
            SAIDA_USO,
            "argumento-invalido",
            onde=f"{verbo_limpo} despachar",
            recebido=" ".join(posicionais) if posicionais else "<vazio>",
            regra=REGRA_FORMA_DESPACHAR,
            cura="informe [<classe>] <chave> (ex.: 'pipeline <slug>' ou '<slug>')",
            proximo=f"{verbo_limpo} despachar pipeline <chave>",
        )

    if len(posicionais) == 1:
        alvo_classe = "pipeline"
        chave_bruta = posicionais[0].strip()
    else:
        alvo_classe = posicionais[0].strip()
        chave_bruta = posicionais[1].strip()

    if alvo_classe != "pipeline":
        raise Recusa(
            SAIDA_USO,
            "classe-invalida",
            onde=f"{verbo_limpo} despachar",
            recebido=alvo_classe,
            regra=REGRA_FORMA_DESPACHAR,
            cura="a única classe aceita pela borda de verbo nesta story é 'pipeline'",
            proximo=f"{verbo_limpo} despachar pipeline <chave>",
        )

    chave_norm = chave_bruta.removeprefix("pipeline:")
    if not chave_norm or not _RE_KEBAB.fullmatch(chave_norm):
        raise Recusa(
            SAIDA_USO,
            "chave-invalida",
            onde=f"{verbo_limpo} despachar/chave",
            recebido=chave_bruta,
            regra=REGRA_FORMA_DESPACHAR,
            cura="informe o slug do pipeline em kebab-case ASCII (ex.: 'ingestao' ou 'pipeline:ingestao')",
            proximo=f"{verbo_limpo} despachar pipeline <slug>",
        )

    parametros = _decodificar_parametros_stdin(verbo_limpo, stdin_texto)
    return PedidoBordaDespachar(
        verbo=verbo_limpo,
        alvo_classe=alvo_classe,
        alvo_chave=chave_norm,
        parametros=parametros,
        fan_out=int(estado_flags["fan_out"]),
        pedido_id=str(estado_flags["pedido_id"]),
        prazo_espera_s=prazo_espera_s,
        como_json=bool(estado_flags["como_json"]),
    )


def _converter_chamada_ler_execucao(verbo: str, argv: Sequence[str]) -> PedidoBordaLerExecucao:
    posicionais: list[str] = []
    como_json = False
    somente_pos = False
    for tok in argv:
        if not somente_pos and tok == "--":
            somente_pos = True
            continue
        if not somente_pos and tok == "--json":
            como_json = True
            continue
        if not somente_pos and tok.startswith("-"):
            raise Recusa(
                SAIDA_USO,
                "flag-invalida",
                onde=f"{verbo} ler execucao",
                recebido=tok,
                regra=REGRA_LEITURA_EXECUCAO,
                cura="a única flag aceita em ler execucao é --json",
                proximo=f"{verbo} ler execucao <chave> [--json]",
            )
        posicionais.append(tok)

    if len(posicionais) == _POSICIONAIS_LER_COM_SUBATO and posicionais[0] == "execucao":
        chave = posicionais[1].strip()
    elif len(posicionais) == 1:
        chave = posicionais[0].strip()
    else:
        raise Recusa(
            SAIDA_USO,
            "argumento-invalido",
            onde=f"{verbo} ler execucao",
            recebido=" ".join(posicionais) if posicionais else "<vazio>",
            regra=REGRA_LEITURA_EXECUCAO,
            cura="informe exatamente a chave da execução devolvida pelo despachar",
            proximo=f"{verbo} ler execucao <chave>",
        )

    if not chave:
        raise Recusa(
            SAIDA_USO,
            "chave-invalida",
            onde=f"{verbo} ler execucao",
            recebido=chave,
            regra=REGRA_LEITURA_EXECUCAO,
            cura="informe a chave não vazia da execução",
            proximo=f"{verbo} ler execucao <chave>",
        )
    return PedidoBordaLerExecucao(verbo=verbo, chave_execucao=chave, como_json=como_json)


def _ler_stdin_seguro(amb: AmbienteBordaDespachar) -> str:
    if amb.stdin is not None:
        return amb.stdin.read()
    if sys.stdin is None or sys.stdin.closed or sys.stdin.isatty():
        return ""
    return sys.stdin.read()


def _formatar_texto_resposta_core(pedido: PedidoBordaDespachar, resp: RespostaClienteDespacho) -> str:
    if resp.em_andamento:
        proximo = resp.proximo or f"{pedido.verbo} ler execucao {resp.execucao_id}"
        return f"em andamento {resp.execucao_id}\nproximo: {proximo}\n"

    dados = resp.dados
    if isinstance(dados.get("execucoes"), list):
        pipeline_nome = str(dados.get("pipeline") or pedido.alvo_chave)
        linhas_fan = [
            f"{item['execucao_id']}\texit={item.get('exit_code', 0)}\t{pipeline_nome}"
            for item in dados["execucoes"]
            if isinstance(item, Mapping) and "execucao_id" in item
        ]
        return ("\n".join(linhas_fan) + "\n") if linhas_fan else ""

    if resp.exit_code != SAIDA_OK and not dados.get("passos"):
        return ""

    linhas: list[str] = []
    if resp.execucao_id:
        linhas.append(resp.execucao_id)
    for p in dados.get("passos") or ():
        if isinstance(p, Mapping):
            linhas.append(f"{p.get('id', '')}\texit={p.get('exit', 0)}\t{p.get('linha', '')}")
    conteudo = str(dados.get("conteudo") or "")
    if conteudo:
        linhas.append(conteudo.rstrip("\n"))
    return ("\n".join(linhas) + "\n") if linhas else ""


def _escrever_recusa_borda(
    recusa: Recusa,
    *,
    como_json: bool,
    out: TextIO,
    err: TextIO,
) -> int:
    linha = json.dumps(formato_lista([recusa]), ensure_ascii=False) + "\n"
    err.write(linha)
    err.flush()
    if como_json:
        out.write(linha)
        out.flush()
    return recusa.saida


def executar_despachar(
    verbo: str,
    argv: Sequence[str],
    *,
    ambiente: AmbienteBordaDespachar | None = None,
) -> int:
    """Entrada comum de `<verbo> despachar [<classe>] <chave> [--fan-out <n>] [--pedido <id>] [--json]`."""
    amb = ambiente or AmbienteBordaDespachar()
    out = amb.stdout if amb.stdout is not None else sys.stdout
    err = amb.stderr if amb.stderr is not None else sys.stderr
    pediu_json_bruto = "--json" in argv

    try:
        porta_yaml = _caminho_porta_yaml_padrao(amb)
        verbo_limpo = _exigir_verbo_com_despachar(verbo, porta_yaml, ato_chamado="despachar")
        prazo_s = _resolver_prazo_espera(verbo_limpo, amb)
        stdin_txt = _ler_stdin_seguro(amb)
        pedido = converter_chamada_despachar(
            verbo_limpo,
            argv,
            stdin_texto=stdin_txt,
            prazo_espera_s=prazo_s,
        )
        resp = amb.invocar_core(
            PedidoClienteDespacho(
                verbo_entrada=pedido.verbo,
                alvo_classe=pedido.alvo_classe,
                alvo_chave=pedido.alvo_chave,
                parametros=pedido.parametros,
                ident=amb.ident,
                pedido_id=pedido.pedido_id,
                fan_out=pedido.fan_out,
                prazo_espera_s=pedido.prazo_espera_s,
            ),
            config=amb.config_cliente,
        )
    except Recusa as recusa:
        return _escrever_recusa_borda(recusa, como_json=pediu_json_bruto, out=out, err=err)

    if pedido.como_json:
        texto_json = resp.stdout if resp.stdout.strip() else (json.dumps(resp.dados, ensure_ascii=False) + "\n")
        out.write(texto_json if texto_json.endswith("\n") else texto_json + "\n")
        out.flush()
    else:
        texto_out = _formatar_texto_resposta_core(pedido, resp)
        if texto_out:
            out.write(texto_out)
            out.flush()

    if resp.stderr:
        err.write(resp.stderr if resp.stderr.endswith("\n") else resp.stderr + "\n")
        err.flush()
    elif resp.exit_code != SAIDA_OK and "erro" in resp.dados:
        env_err = {"erro": resp.dados["erro"], "erros": resp.dados.get("erros", [resp.dados["erro"]])}
        err.write(json.dumps(env_err, ensure_ascii=False) + "\n")
        err.flush()

    return resp.exit_code


def _formatar_texto_execucao(dados: Mapping[str, Any]) -> str:
    linhas = [
        f"{dados['execucao_id']}\testado={dados['estado']}\texit={dados.get('exit_code')}"
    ]
    for f in dados.get("fases") or ():
        if isinstance(f, Mapping):
            linhas.append(
                f"{f.get('id', '')}\t{f.get('estado', '')}\texit={f.get('exit_code')}\t{f.get('linha', '')}"
            )
    return "\n".join(linhas) + "\n"


def executar_ler_execucao(
    verbo: str,
    argv: Sequence[str],
    *,
    ambiente: AmbienteBordaDespachar | None = None,
) -> int:
    """Entrada comum de `<verbo> ler execucao <chave> [--json]`."""
    amb = ambiente or AmbienteBordaDespachar()
    out = amb.stdout if amb.stdout is not None else sys.stdout
    err = amb.stderr if amb.stderr is not None else sys.stderr
    pediu_json_bruto = "--json" in argv

    try:
        porta_yaml = _caminho_porta_yaml_padrao(amb)
        verbo_limpo = _exigir_verbo_com_despachar(verbo, porta_yaml, ato_chamado="ler execucao")
        pedido = _converter_chamada_ler_execucao(verbo_limpo, argv)
        sujeito = (
            amb.sujeito
            if amb.sujeito is not None
            else str(amb.ident.get("sujeito") or os.environ.get("PF_SUJEITO") or "")
        )
        dir_oplog = amb.diretorio_oplog
        if dir_oplog is None:
            env_oplog = (os.environ.get("PF_OPLOG_DIR") or "").strip()
            if env_oplog:
                dir_oplog = Path(env_oplog)
        dados = ler_execucao(
            verbo_limpo,
            pedido.chave_execucao,
            sujeito=sujeito,
            diretorio_oplog=dir_oplog,
        )
    except Recusa as recusa:
        return _escrever_recusa_borda(recusa, como_json=pediu_json_bruto, out=out, err=err)

    if pedido.como_json:
        out.write(json.dumps(dados, ensure_ascii=False) + "\n")
    else:
        out.write(_formatar_texto_execucao(dados))
    out.flush()
    return SAIDA_OK


def executar_ato(
    verbo: str,
    ato: str,
    argv: Sequence[str],
    *,
    ambiente: AmbienteBordaDespachar | None = None,
) -> int:
    """Despacha `despachar` ou `ler execucao` de qualquer verbo pela camada comum."""
    ato_limpo = ato.strip().lower()
    if ato_limpo == "despachar":
        return executar_despachar(verbo, argv, ambiente=ambiente)
    if ato_limpo == "ler" and argv and argv[0] == "execucao":
        return executar_ler_execucao(verbo, argv[1:], ambiente=ambiente)
    if ato_limpo == "ler-execucao":
        return executar_ler_execucao(verbo, argv, ambiente=ambiente)

    amb = ambiente or AmbienteBordaDespachar()
    out = amb.stdout if amb.stdout is not None else sys.stdout
    err = amb.stderr if amb.stderr is not None else sys.stderr
    recusa = Recusa(
        SAIDA_USO,
        "ato-nao-declarado",
        onde=f"{verbo.strip() or '<verbo>'} {ato_limpo or '<vazio>'}",
        recebido=f"{verbo} {ato}".strip(),
        regra=REGRA_DECLARACAO_ATO,
        cura="encaminhe à borda de despacho apenas 'despachar' ou 'ler execucao'",
    )
    return _escrever_recusa_borda(recusa, como_json=("--json" in argv), out=out, err=err)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI auxiliar `python -m despacho.borda <verbo> <ato> [args...]`."""
    args = list(sys.argv[1:] if argv is None else argv)
    min_tokens = 2
    if len(args) < min_tokens:
        recusa = Recusa(
            SAIDA_USO,
            "argumento-invalido",
            onde="despacho.borda",
            recebido=" ".join(args) or "<vazio>",
            regra=REGRA_FORMA_DESPACHAR,
            cura="uso: python -m despacho.borda <verbo> <despachar|ler> ...",
        )
        return _escrever_recusa_borda(recusa, como_json=False, out=sys.stdout, err=sys.stderr)
    return executar_ato(args[0], args[1], args[2:])


if __name__ == "__main__":
    raise SystemExit(main())
