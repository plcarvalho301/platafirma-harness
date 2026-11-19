"""A receita da figura (o plano e a fonte) guardada dentro do próprio SVG.

Na pasta da figura ficam dois arquivos: o texto (.md) e o desenho (.svg). O desenho carrega, em
<metadata>, o plano e a fonte de que saiu, para quem abre a pasta ver só a figura e para a peça
poder redesenhá-la. `embutir` grava a receita no SVG; `receita` a devolve como arquivos, no
rascunho, para o ciclo de desenho recomeçar.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PAPEIS = ("plano", "fonte")
_BLOCO = re.compile(r'<metadata id="pf-(plano|fonte)"><!\[CDATA\[(.*?)\]\]></metadata>', re.S)
_ABRE_SVG = re.compile(r"<svg\b[^>]*>", re.S)


def ler(svg: str) -> dict[str, dict]:
    """A receita que o SVG traz, por papel; vazio quando não traz nenhuma."""
    return {m.group(1): json.loads(m.group(2)) for m in _BLOCO.finditer(svg)}


def _bloco(papel: str, dados: dict) -> str:
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    if "]]>" in texto:
        raise ValueError(f"o {papel} traz ']]>', que fecharia o bloco no SVG")
    return f'<metadata id="pf-{papel}"><![CDATA[\n{texto}\n]]></metadata>'


def embutir_texto(svg: str, receita: dict[str, dict]) -> str:
    """O SVG com a receita logo depois da abertura de <svg>; a receita anterior sai."""
    limpo = _BLOCO.sub("", svg)
    abre = _ABRE_SVG.search(limpo)
    if not abre:
        raise ValueError("o arquivo não abre <svg>")
    blocos = "".join(_bloco(p, receita[p]) for p in PAPEIS if p in receita)
    return limpo[: abre.end()] + blocos + limpo[abre.end():]


def _json(caminho: str | Path) -> dict:
    caminho = Path(caminho)
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"JSON inválido em {caminho}: {err}") from err


def embutir(caminho_svg: str | Path, caminho_fonte: str | Path, caminho_plano: str | Path | None = None) -> Path:
    svg = Path(caminho_svg)
    receita = {"fonte": _json(caminho_fonte)}
    if caminho_plano:
        receita["plano"] = _json(caminho_plano)
    svg.write_text(embutir_texto(svg.read_text(encoding="utf-8"), receita), encoding="utf-8")
    return svg


def extrair(caminho_svg: str | Path, saida_dir: str | Path | None = None) -> list[Path]:
    svg = Path(caminho_svg)
    receita = ler(svg.read_text(encoding="utf-8"))
    if not receita:
        raise LookupError(f"{svg} não traz receita: foi desenhado à mão ou antes da peça a guardar")
    destino = Path(saida_dir) if saida_dir else svg.parent
    destino.mkdir(parents=True, exist_ok=True)
    feitos = []
    for papel in PAPEIS:
        if papel in receita:
            arq = destino / f"{svg.stem}.{papel}.json"
            arq.write_text(json.dumps(receita[papel], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            feitos.append(arq)
    return feitos


def main_embutir(argv: list[str]) -> int:
    if len(argv) not in (2, 3) or argv[0] in ("-h", "--help"):
        print("uso: diagrama embutir <figura.svg> <fonte.json> [<plano.json>]", file=sys.stderr)
        return 2
    try:
        print(str(embutir(*argv)))
        return 0
    except (ValueError, FileNotFoundError) as err:
        print(f"diagrama embutir: erro: {err}", file=sys.stderr)
        return 1


def main_receita(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("uso: diagrama receita <figura.svg> [--saida <dir>]", file=sys.stderr)
        return 2
    saida = argv[2] if len(argv) >= 3 and argv[1] in ("--saida", "-o") else None
    try:
        for arq in extrair(argv[0], saida):
            print(str(arq))
        return 0
    except (LookupError, FileNotFoundError, ValueError) as err:
        print(f"diagrama receita: erro: {err}", file=sys.stderr)
        return 1
