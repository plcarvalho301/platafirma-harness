"""vocabulario — verificacao de verbos e atos citados no texto contra bin/."""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .resultado import Apontamento


def carregar_verbos_e_atos(bin_dir: Path) -> tuple[dict[str, set[str]], set[str]]:
    verbos: dict[str, set[str]] = {}
    abertos: set[str] = set()

    if not bin_dir.is_dir():
        return verbos, abertos

    for entry in bin_dir.iterdir():
        if entry.is_file() and not entry.name.startswith((".", "_")):
            nome = entry.name
            atos: set[str] = set()
            try:
                with open(entry, "r", encoding="utf-8", errors="replace") as fp:
                    linhas = [fp.readline() for _ in range(50)]
                for l in linhas:
                    if l.startswith("# atos:"):
                        conteudo = l.split(":", 1)[1].strip()
                        for p in conteudo.split(","):
                            p = p.strip()
                            if "(" in p:
                                p = p.split("(", 1)[0].strip()
                            if "<" in p or "=" in p:
                                abertos.add(nome)
                            elif p:
                                atos.add(p)
                        break
            except OSError:
                pass
            verbos[nome] = atos
    return verbos, abertos


def verificar_vocabulario(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Varre <verbo> <ato> entre crases e confere com bin/<verbo>."""
    raiz = Path(raiz)
    bin_dir = raiz / "bin"
    verbos, abertos = carregar_verbos_e_atos(bin_dir)

    candidatos: list[Path] = []
    if alvo:
        p = Path(alvo) if Path(alvo).is_absolute() else (raiz / alvo)
        if p.is_file():
            candidatos.append(p)
        elif p.is_dir():
            for m in p.glob("**/*.md"):
                candidatos.append(m)
    else:
        for fixa in ("abertura/dono.md", "abertura/oficio.md", "abertura/oficio-ferramental.md"):
            cand = raiz / fixa
            if cand.is_file():
                candidatos.append(cand)
        docs_dir = raiz / "docs"
        if docs_dir.is_dir():
            for cand in sorted(docs_dir.glob("spec_*.md")):
                if cand.is_file() and cand not in candidatos:
                    candidatos.append(cand)
        skills_dir = raiz / "skills"
        if skills_dir.is_dir():
            for cand in sorted(skills_dir.glob("*/SKILL.md")):
                if cand.is_file() and cand not in candidatos:
                    candidatos.append(cand)

    padrao_crase = re.compile(r"`([^`\n]+)`")
    apontamentos: list[Apontamento] = []

    for arq in sorted(candidatos):
        try:
            rel = str(arq.relative_to(raiz))
        except ValueError:
            rel = arq.name

        try:
            linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
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

        for num_linha, linha in enumerate(linhas, 1):
            for m in padrao_crase.finditer(linha):
                expr = m.group(1).strip()
                tokens = expr.split()
                if len(tokens) < 2:
                    continue
                v = tokens[0]
                if v.startswith("bin/"):
                    v = v[4:]
                if v not in verbos:
                    continue
                if tokens[1].startswith("-"):
                    continue

                if v == "motor" and len(tokens) >= 3 and tokens[1] in ("rag", "reasoner", "embeddings"):
                    ato = tokens[2]
                else:
                    ato = tokens[1]

                if v in abertos:
                    continue

                if ato not in verbos[v]:
                    apontamentos.append(
                        Apontamento(
                            rel,
                            num_linha,
                            f"`{expr}`: verbo '{v}' nao serve ato '{ato}'",
                            f"corrigir a citacao do ato ou declarar ato '{ato}' em bin/{v}",
                            severidade="aviso",
                            id="VOCABULARIO",
                        )
                    )

    return apontamentos
