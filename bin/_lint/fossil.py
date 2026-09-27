"""fossil — busca referencias a caminhos e simbolos quebrados/orfaos."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from .resultado import Apontamento


def verificar_fossil(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica referencias a arquivos locais inexistentes citados no codigo/documentacao."""
    raiz = Path(raiz)
    candidatos: list[Path] = []
    if alvo:
        p = (raiz / alvo).resolve()
        if p.is_file():
            candidatos.append(p)
        elif p.is_dir():
            for f in p.glob("**/*"):
                if f.is_file() and not f.name.startswith("."):
                    candidatos.append(f)
    else:
        for f in raiz.glob("docs/**/*.md"):
            candidatos.append(f)
        for f in raiz.glob("bin/*"):
            if f.is_file() and not f.name.startswith((".", "_")):
                candidatos.append(f)

    padrao_caminho = re.compile(r"`([a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]+)`")
    apontamentos: list[Apontamento] = []

    for arq in candidatos:
        try:
            rel = str(arq.relative_to(raiz))
        except ValueError:
            rel = arq.name

        try:
            linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, linha in enumerate(linhas, 1):
            for m in padrao_caminho.finditer(linha):
                ref = m.group(1).strip()
                # Verifica apenas caminhos relativos explicitos dentro do repo
                if "/" in ref and not ref.startswith(("http://", "https://", "/")):
                    cand_ref = raiz / ref
                    # Se parecer caminho de arquivo mas nao existe
                    if any(ref.endswith(ext) for ext in (".py", ".sh", ".md", ".json", ".yaml", ".yml")):
                        if not cand_ref.exists() and not cand_ref.is_symlink():
                            # Se for caminho sob pasta comum que deveria existir
                            if any(ref.startswith(p) for p in ("bin/", "lib/", "docs/", "controle/", "skills/")):
                                apontamentos.append(
                                    Apontamento(
                                        rel,
                                        i,
                                        f"referencia a caminho inexistente: `{ref}`",
                                        f"remover referencia quebrada ou corrigir caminho para {ref}",
                                        severidade="aviso",
                                        id="FOSSIL_CAMINHO",
                                    )
                                )

    return apontamentos
