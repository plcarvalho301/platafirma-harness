"""arranque — verificacao de texto de arranque (CLAUDE.md) apontando para abertura/arranque.md."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .resultado import Apontamento

PONTEIRO_ARRANQUE = "abertura/arranque.md"  # conduta/ virou abertura/ no tombamento de 22/08 (arq:0073)

SINAIS_ARRANQUE = (
    re.compile(r"monta[_-]sessao", re.I),
    re.compile(r"vasculh", re.I),
    re.compile(r"de onde sai a cadeira", re.I),
    re.compile(r"primeira a[cç][aã]o", re.I),
    re.compile(r"improvis\w* cadeira", re.I),
    re.compile(r"PF_CADEIRA.{0,30}export", re.I | re.S),
)

FORA_DA_REGUA = ("archi_base", "mdm_rh", "i-have-adhd")
INSTANCIA_EFEMERA = ("fitas",)


def _sh(args: list[str], cwd: Optional[str | Path] = None) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def julgar_arranque(texto: str) -> tuple[str, int]:
    """Retorna ('aponta' | 'copia' | 'sem-arranque', n_sinais)."""
    if PONTEIRO_ARRANQUE in texto:
        return "aponta", 0
    n = sum(1 for r in SINAIS_ARRANQUE if r.search(texto))
    return ("copia" if n >= 2 else "sem-arranque"), n


def achar_claude_mds(raiz: Path) -> list[Path]:
    achados = []
    if (raiz / "CLAUDE.md").is_file():
        achados.append(raiz / "CLAUDE.md")
    for sub in sorted(raiz.iterdir()):
        if sub.name.startswith(".") or sub.name in FORA_DA_REGUA or sub.name in INSTANCIA_EFEMERA:
            continue
        if sub.is_dir() and not sub.is_symlink():
            cand = sub / "CLAUDE.md"
            if cand.is_file():
                achados.append(cand)
            for subsub in sorted(sub.iterdir()):
                if subsub.is_dir() and not subsub.is_symlink() and not subsub.name.startswith("."):
                    cand2 = subsub / "CLAUDE.md"
                    if cand2.is_file():
                        achados.append(cand2)
    return achados


def verificar_arranque(
    raiz: Path | str,
    staged: bool = False,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica se CLAUDE.md aponta para abertura/arranque.md sem copiar redacao."""
    raiz = Path(raiz)
    alvos: list[Path] = []

    if staged:
        rc, saida, _ = _sh(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=raiz)
        if rc == 0 and saida:
            for n in saida.splitlines():
                if n.strip().endswith("CLAUDE.md"):
                    caminho = raiz / n.strip()
                    if caminho.is_file():
                        alvos.append(caminho)
    elif alvo:
        caminho = (raiz / alvo).resolve()
        if caminho.is_file():
            alvos.append(caminho)
        else:
            return [
                Apontamento(
                    alvo,
                    1,
                    f"arquivo {alvo!r} nao encontrado",
                    "indicar caminho valido para CLAUDE.md",
                    severidade="bloqueante",
                )
            ]
    else:
        alvos = achar_claude_mds(raiz)

    apontamentos: list[Apontamento] = []
    for c in alvos:
        try:
            rel = str(c.relative_to(raiz))
        except ValueError:
            rel = c.name

        try:
            texto = c.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            apontamentos.append(
                Apontamento(
                    rel,
                    1,
                    f"nao consegui ler arquivo: {e}",
                    "verificar permissoes de leitura",
                    severidade="bloqueante",
                )
            )
            continue

        veredito, n = julgar_arranque(texto)
        if veredito == "copia":
            apontamentos.append(
                Apontamento(
                    rel,
                    1,
                    f"CLAUDE.md com bloco proprio de arranque sem apontador ({n} sinais)",
                    f"substituir o bloco pelo ponteiro para {PONTEIRO_ARRANQUE}",
                    severidade="bloqueante",
                    id="COPIA",
                )
            )

    return apontamentos
