"""chapeu — verificacao de chapeu de camada C contra o template de personas."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .resultado import Apontamento


def verificar_chapeu(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica arquivo de chapeu conforme TEMPLATE-chapeu.md."""
    raiz = Path(raiz)
    abertura_dir = raiz / "abertura"
    if not abertura_dir.is_dir():
        return []

    apontamentos: list[Apontamento] = []
    candidatos: list[Path] = []

    if alvo:
        p = Path(alvo) if Path(alvo).is_absolute() else (raiz / alvo)
        if p.is_file():
            candidatos.append(p)
        elif (abertura_dir / alvo / "chapeu.md").is_file():
            candidatos.append(abertura_dir / alvo / "chapeu.md")
    else:
        for p in abertura_dir.glob("**/chapeu.md"):
            if p.is_file():
                candidatos.append(p)

    for cand in candidatos:
        rel = str(cand.relative_to(raiz)) if cand.is_relative_to(raiz) else str(cand)
        try:
            texto = cand.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            apontamentos.append(
                Apontamento(
                    rel,
                    1,
                    f"nao consegui ler chapeu: {e}",
                    "verificar permissoes de leitura",
                    severidade="bloqueante",
                )
            )
            continue

        if not texto.strip():
            apontamentos.append(
                Apontamento(
                    rel,
                    1,
                    "arquivo de chapeu vazio",
                    "preencher o arquivo de chapeu conforme TEMPLATE-chapeu.md",
                    severidade="bloqueante",
                )
            )

    return apontamentos
