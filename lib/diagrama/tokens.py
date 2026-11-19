"""Leitura do tokens.css do design system: a cor, o tamanho e o fio da figura vêm dele, nunca de hex escrito à mão.

O arquivo é o da release no ar, ou o que DIAGRAMA_TOKENS indicar. Os valores são `light-dark(claro, escuro)`
e `var(--platafirma-...)` encadeados; este módulo resolve os dois e devolve o valor do tema claro.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

RELEASE = "/opt/platafirma/current/ui/src/tokens.css"

FAMILIA_DA_CATEGORIA = {
    "persistencia": 1, "servico": 2, "superficie": 3, "porta": 4,
    "conhecimento": 5, "host": 6, "mensageria": 7, "identidade": 8,
}

_DECL = re.compile(r"--platafirma-([\w-]+)\s*:\s*([^;]+);")
_VAR = re.compile(r"var\(\s*--platafirma-([\w-]+)\s*(?:,\s*([^()]*))?\)")
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def caminho_tokens() -> Path:
    for c in (os.environ.get("DIAGRAMA_TOKENS"), RELEASE):
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError(f"tokens.css não encontrado (DIAGRAMA_TOKENS ou {RELEASE})")


def carregar(caminho: str | Path | None = None) -> dict[str, str]:
    texto = Path(caminho or caminho_tokens()).read_text(encoding="utf-8")
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    return {nome: valor.strip() for nome, valor in _DECL.findall(texto)}


def _separa(args: str) -> list[str]:
    partes, nivel, atual = [], 0, ""
    for c in args:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
        if c == "," and nivel == 0:
            partes.append(atual.strip())
            atual = ""
        else:
            atual += c
    partes.append(atual.strip())
    return partes


def resolver(nome: str, tokens: dict[str, str], escuro: bool = False, _pilha: tuple = ()) -> str:
    if nome in _pilha:
        raise ValueError(f"token circular: {' > '.join(_pilha + (nome,))}")
    if nome not in tokens:
        raise KeyError(f"token --platafirma-{nome} não existe")
    return _valor(tokens[nome], tokens, escuro, _pilha + (nome,))


def _valor(v: str, tokens: dict[str, str], escuro: bool, pilha: tuple) -> str:
    v = v.strip()
    m = re.fullmatch(r"light-dark\((.*)\)", v, flags=re.S)
    if m:
        args = _separa(m.group(1))
        v = args[1 if escuro and len(args) > 1 else 0]

    def troca(mv: re.Match) -> str:
        ref, reserva = mv.group(1), mv.group(2)
        if ref in tokens:
            return resolver(ref, tokens, escuro, pilha)
        if reserva is not None:
            return reserva.strip()
        raise KeyError(f"token --platafirma-{ref} não existe")

    anterior = None
    while anterior != v:
        anterior, v = v, _VAR.sub(troca, v)
    m = re.fullmatch(r"light-dark\((.*)\)", v, flags=re.S)
    if m:
        return _valor(v, tokens, escuro, pilha)
    return v


def cor(nome: str, tokens: dict[str, str], escuro: bool = False) -> str:
    """A cor do token em #rrggbb minúsculo."""
    c = normaliza_cor(resolver(nome, tokens, escuro))
    if c is None:
        raise ValueError(f"token --platafirma-{nome} não resolve para uma cor")
    return c


def normaliza_cor(s: str) -> str | None:
    s = s.strip().lower()
    m = _HEX.match(s)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h}"


def px(valor: str) -> float:
    valor = valor.strip()
    if valor.endswith("rem"):
        return float(valor[:-3]) * 16
    if valor.endswith("px"):
        return float(valor[:-2])
    return float(valor)


def familia(tokens: dict[str, str], n: int) -> dict[str, str]:
    """As cores da família n. O glifo não se lê: nenhuma figura o desenha."""
    base = f"family-{n}"
    return {
        "bg": cor(f"{base}-bg", tokens),
        "zone": cor(f"{base}-zone", tokens),
        "bd": cor(f"{base}-bd", tokens),
        "fg": cor(f"{base}-fg", tokens),
        "stroke": cor(f"{base}-stroke", tokens),
    }


def paleta(tokens: dict[str, str]) -> set[str]:
    """Toda cor que algum token resolve, nos dois temas: o que a figura pode usar."""
    cores: set[str] = set()
    for nome in tokens:
        for escuro in (False, True):
            try:
                c = normaliza_cor(resolver(nome, tokens, escuro))
            except (KeyError, ValueError):
                continue
            if c:
                cores.add(c)
    return cores
