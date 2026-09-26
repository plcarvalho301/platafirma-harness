#!/usr/bin/env python3
# registro — leitor único de registro/venvs.json, para release, teste e pre-push
# (card #3150, comentário B1: "release, teste e pre-push importam o mesmo leitor;
# nenhum relê o JSON por conta própria").
"""Registro stack -> (família, lock, subárvore de teste).

Cada chave do JSON (exceto as que começam com "_", que são comentário) declara uma
stack: {"familia": "<repo>", "lock": "<caminho do lock na árvore>", "teste":
"<subárvore onde a suíte que usa este venv mora, opcional>"}. `lock` é o caminho
lido por release para construir o venv (chave = <nome>-sha256(lock+python)) e por
teste/pre-push para reaproveitar o mesmo venv, pela mesma chave.

Uso:
  registro.py <nome>              família, lock e subárvore de teste (TSV) da stack <nome>
  registro.py --familia <familia> uma linha TSV (nome, lock, teste) por stack da família

exit: 0 achou · 2 stack desconhecida (lista as conhecidas) · 3 registro ausente ou
      ilegível · 5 stack conhecida sem lock declarado
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def caminho_registro() -> Path:
    return Path(os.environ.get("PLATAFIRMA_VENVS", "registro/venvs.json"))


class RegistroIlegivel(RuntimeError):
    """Registro ausente, ou não é o JSON esperado — sai 3."""


class StackDesconhecida(RuntimeError):
    def __init__(self, nome: str, conhecidas: list[str]):
        super().__init__(nome)
        self.nome = nome
        self.conhecidas = conhecidas


class StackSemLock(RuntimeError):
    def __init__(self, nome: str):
        super().__init__(nome)
        self.nome = nome


def carregar(caminho: Path | None = None) -> dict:
    caminho = caminho or caminho_registro()
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistroIlegivel(f"registro de venvs ilegível ({caminho}): {exc}") from exc
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError as exc:
        raise RegistroIlegivel(f"registro de venvs não é JSON válido ({caminho}): {exc}") from exc
    if not isinstance(dados, dict):
        raise RegistroIlegivel(f"registro de venvs não é um objeto ({caminho})")
    return {k: v for k, v in dados.items() if not k.startswith("_")}


def stacks_da_familia(familia: str, caminho: Path | None = None) -> list[tuple[str, str, str]]:
    """[(nome, lock, subárvore de teste)] das stacks declaradas para <familia>."""
    dados = carregar(caminho)
    saida = []
    for nome, decl in dados.items():
        if not isinstance(decl, dict) or decl.get("familia") != familia:
            continue
        saida.append((nome, decl.get("lock", "") or "", decl.get("teste", "") or ""))
    return saida


def stack(nome: str, caminho: Path | None = None) -> tuple[str, str, str]:
    """(família, lock, subárvore de teste) da stack <nome>.

    Levanta StackDesconhecida ou StackSemLock — o chamador decide o exit (2 ou 5);
    RegistroIlegivel (registro ausente/ilegível) já é 3.
    """
    dados = carregar(caminho)
    decl = dados.get(nome)
    if not isinstance(decl, dict):
        raise StackDesconhecida(nome, sorted(dados.keys()))
    lock = decl.get("lock", "") or ""
    if not lock:
        raise StackSemLock(nome)
    return decl.get("familia", "") or "", lock, decl.get("teste", "") or ""


def _main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "--ajuda"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--familia":
        if len(argv) != 2:
            print("erro: --familia exige exatamente <familia>", file=sys.stderr)
            return 2
        try:
            linhas = stacks_da_familia(argv[1])
        except RegistroIlegivel as exc:
            print(f"registro: {exc}", file=sys.stderr)
            return 3
        for nome, lock, teste in linhas:
            print(f"{nome}\t{lock}\t{teste}")
        return 0
    if len(argv) != 1:
        print("erro: um nome de stack por chamada (ou --familia <familia>)", file=sys.stderr)
        return 2
    try:
        familia, lock, teste = stack(argv[0])
    except RegistroIlegivel as exc:
        print(f"registro: {exc}", file=sys.stderr)
        return 3
    except StackDesconhecida as exc:
        print(f"registro: stack desconhecida: {exc.nome}", file=sys.stderr)
        print("stacks conhecidas: " + (", ".join(exc.conhecidas) or "(nenhuma)"), file=sys.stderr)
        return 2
    except StackSemLock as exc:
        print(f"registro: stack '{exc.nome}' sem lock declarado em {caminho_registro()}", file=sys.stderr)
        return 5
    print(f"{familia}\t{lock}\t{teste}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
