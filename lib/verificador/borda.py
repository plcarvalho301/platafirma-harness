"""borda — conversão em passada única de `<verbo> verificar …` num `PedidoVerificacao` (card #4454).

Aplica o padrão Parse, don't validate: recusa flag desconhecida, caminho solto de sistema
de arquivos ou chave fora da gramática na saída 2, antes de abrir rede, banco ou disco.
Reaproveita `Recusa` de `lib/leitura/recusa.py` sem cópia.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from leitura.recusa import Recusa

from .tipos import PedidoVerificacao

_REGRA_BORDA = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"
_RE_CLASSE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RE_CHAVE = re.compile(r"^[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9._:/-]*$")
_RE_SUBSTRATO = re.compile(r"^[a-z0-9][a-z0-9._@-]*$")
_RE_DRIVE_WIN = re.compile(r"^[A-Za-z]:[\\/]")


def _eh_caminho_solto(token: str) -> bool:
    return (
        token.startswith(("/", "./", "../", "~"))
        or token in (".", "..")
        or bool(_RE_DRIVE_WIN.match(token))
        or "\\" in token
    )


def _normalizar_chave(token: str, *, onde: str, verbo: str) -> str:
    limpo = token.strip()
    if not limpo or _eh_caminho_solto(limpo) or ".." in limpo:
        raise Recusa(
            2,
            "chave-invalida",
            onde=onde,
            recebido=token,
            regra=_REGRA_BORDA,
            cura="informe uma chave canônica <classe>:<slug>, nunca caminho de sistema de arquivos",
            proximo=f"{verbo} verificar <classe>:<slug> --regua <regua>",
        )
    if limpo.endswith(":") and ":" not in limpo[:-1]:
        classe = limpo[:-1]
        if _RE_CLASSE.fullmatch(classe):
            return f"shape:{classe}"
    if _RE_CHAVE.fullmatch(limpo):
        return limpo
    raise Recusa(
        2,
        "chave-invalida",
        onde=onde,
        recebido=token,
        regra=_REGRA_BORDA,
        cura="use a gramática <classe>:<slug> ou <classe>:",
        proximo=f"{verbo} verificar <classe>:<slug> --regua <regua>",
    )


def _consumir_flag(
    verbo: str,
    arg: str,
    proximo: str | None,
    *,
    reguas: list[str],
) -> tuple[bool, bool]:
    """Consome uma flag conhecida. Devolve (consumiu_proximo, como_json)."""
    if arg == "--json":
        return False, True
    if arg == "--regua":
        if not proximo or proximo.startswith("-"):
            raise Recusa(
                2,
                "flag-invalida",
                onde="flag --regua",
                recebido=arg,
                regra=_REGRA_BORDA,
                cura="informe a chave da régua após --regua",
                proximo=f"{verbo} verificar <alvo> --regua gabarito:<slug>",
            )
        reguas.append(_normalizar_chave(proximo, onde="--regua", verbo=verbo))
        return True, False
    if arg.startswith("--regua="):
        valor = arg.split("=", 1)[1]
        if not valor:
            raise Recusa(
                2,
                "flag-invalida",
                onde="flag --regua",
                recebido=arg,
                regra=_REGRA_BORDA,
                cura="informe a chave da régua em --regua=<chave>",
                proximo=f"{verbo} verificar <alvo> --regua gabarito:<slug>",
            )
        reguas.append(_normalizar_chave(valor, onde="--regua", verbo=verbo))
        return False, False
    raise Recusa(
        2,
        "flag-invalida",
        onde="argumentos",
        recebido=arg,
        regra=_REGRA_BORDA,
        cura="flags aceitas em verificar: --regua <chave> e --json",
        proximo=f"{verbo} verificar <alvo> [--regua <chave>] [--json]",
    )


def converter_chamada(
    verbo: str,
    argv: Sequence[str],
    *,
    prazo_s: float = 60.0,
) -> PedidoVerificacao:
    """Valida e converte `argv` (após `verificar`) num `PedidoVerificacao` imutável."""
    verbo_limpo = verbo.strip().lower()
    if not verbo_limpo or not _RE_CLASSE.fullmatch(verbo_limpo):
        raise Recusa(
            2,
            "chave-invalida",
            onde="verbo",
            recebido=verbo,
            regra=_REGRA_BORDA,
            cura="informe um nome de verbo válido",
        )

    posicionais: list[str] = []
    reguas: list[str] = []
    como_json = False
    idx = 0
    args = list(argv)

    while idx < len(args):
        arg = args[idx]
        if arg.startswith("-"):
            prox = args[idx + 1] if idx + 1 < len(args) else None
            consumiu, eh_json = _consumir_flag(verbo_limpo, arg, prox, reguas=reguas)
            if eh_json:
                como_json = True
            idx += 2 if consumiu else 1
            continue
        posicionais.append(arg)
        idx += 1

    if not posicionais:
        raise Recusa(
            2,
            "chave-invalida",
            onde="alvo",
            recebido="",
            regra=_REGRA_BORDA,
            cura="informe ao menos um alvo (<classe>:<slug>) ou substrato",
            proximo=f"{verbo_limpo} verificar <classe>:<slug> [--regua <chave>]",
        )

    substrato: str | None = None
    alvos_brutos = posicionais
    primeiro = posicionais[0]
    min_com_substrato = 2
    if (
        len(posicionais) >= min_com_substrato
        and ":" not in primeiro
        and not _eh_caminho_solto(primeiro)
        and _RE_SUBSTRATO.fullmatch(primeiro)
    ):
        substrato = primeiro
        alvos_brutos = posicionais[1:]

    alvos = tuple(_normalizar_chave(tok, onde="alvo", verbo=verbo_limpo) for tok in alvos_brutos)

    return PedidoVerificacao(
        verbo=verbo_limpo,
        substrato=substrato,
        alvos=alvos,
        reguas=tuple(reguas),
        como_json=como_json,
        prazo_s=prazo_s,
    )
