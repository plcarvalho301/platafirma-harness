"""vocabulario — verificacao de verbos e atos citados no texto contra bin/.

Modulo unico (card #3153): `lint vocabulario` e `conferir vocabulario` leem os atos com
`carregar_verbos_e_atos` e julgam cada citacao com `julgar_citacao`, daqui.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from .resultado import Apontamento

PADRAO_CRASE = re.compile(r"`([^`\n]+)`")


def carregar_verbos_e_atos(bin_dir: Path | str) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Varre bin/ e extrai os atos declarados no cabecalho de cada verbo.

    Devolve ({verbo: atos}, {verbo: placeholder}) — o segundo para verbo de ato aberto
    (`ato=<assunto>`), que aceita qualquer ato.
    """
    bin_dir = str(bin_dir)
    verbos: dict[str, set[str]] = {}
    atos_abertos: dict[str, str] = {}
    if not os.path.isdir(bin_dir):
        return verbos, atos_abertos
    for nome in os.listdir(bin_dir):
        caminho = os.path.join(bin_dir, nome)
        if os.path.isdir(caminho) or nome.startswith("_") or nome.startswith("."):
            continue
        real = os.path.realpath(caminho)
        atos: set[str] = set()
        aberto = None
        try:
            with open(real, "r", encoding="utf-8", errors="replace") as fp:
                for i, linha in enumerate(fp):
                    if i > 35:
                        break
                    if linha.startswith("# atos:"):
                        raw = linha.split(":", 1)[1].strip()
                        if "nenhum" in raw.lower() and "sem ato" in raw.lower():
                            continue
                        if raw.startswith("a capacidade"):
                            continue
                        m_ph = re.search(r"ato=<([^>]+)>", raw)
                        if m_ph:
                            aberto = m_ph.group(1)
                            atos.add(f"<{aberto}>")
                        cleaned = re.sub(r"\(.*?\)", "", raw)
                        for part in re.split(r"[,·;]", cleaned):
                            part = part.strip()
                            if (not part or part.startswith("sem ato")
                                    or part.startswith("a capacidade") or part.startswith("nenhum")):
                                continue
                            m = re.match(r"^([a-zA-Z0-9_-]+)", part)
                            if m and m.group(1) not in ("ato", "args", "sem", "flags"):
                                atos.add(m.group(1))
        except OSError:
            pass
        verbos[nome] = atos
        if aberto:
            atos_abertos[nome] = aberto

    # Redirecionamentos e expansoes canonicas conhecidas
    if "acervo" in verbos:
        verbos["acervo"].add("adr")
    if "motor" in verbos:
        verbos["motor"].add("casa")
    if "conferir" in verbos:
        verbos["conferir"].add("vocabulario")

    return verbos, atos_abertos


def julgar_citacao(
    expr: str, verbos: dict[str, set[str]], abertos: dict[str, str]
) -> Optional[tuple[str, str, bool]]:
    """(verbo, ato, serve?) para uma citacao `<verbo> <ato>`; None se nao e citacao de
    verbo da casa (um token so, verbo desconhecido, flag no lugar do ato)."""
    tokens = expr.strip().split()
    if len(tokens) < 2:
        return None
    v = tokens[0]
    if v.startswith("bin/"):
        v = v[4:]
    if v not in verbos:
        return None
    if tokens[1].startswith("-"):
        return None
    if v == "motor" and len(tokens) >= 3 and tokens[1] in ("rag", "reasoner", "embeddings"):
        ato = tokens[2]
    else:
        ato = tokens[1]
    if v in abertos:
        return v, ato, True
    return v, ato, ato in verbos[v]


def verificar_vocabulario(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Varre <verbo> <ato> entre crases e confere com bin/<verbo>."""
    raiz = Path(raiz)
    verbos, abertos = carregar_verbos_e_atos(raiz / "bin")

    candidatos: list[Path] = []
    if alvo:
        p = Path(alvo) if Path(alvo).is_absolute() else (raiz / alvo)
        if p.is_file():
            candidatos.append(p)
        elif p.is_dir():
            candidatos.extend(p.glob("**/*.md"))
    else:
        for fixa in ("abertura/dono.md", "abertura/oficio.md", "abertura/oficio-ferramental.md"):
            if (raiz / fixa).is_file():
                candidatos.append(raiz / fixa)
        for padrao in ("docs/spec_*.md", "skills/*/SKILL.md"):
            for cand in sorted(raiz.glob(padrao)):
                if cand.is_file() and cand not in candidatos:
                    candidatos.append(cand)

    apontamentos: list[Apontamento] = []
    for arq in sorted(candidatos):
        try:
            rel = str(arq.relative_to(raiz))
        except ValueError:
            rel = arq.name
        try:
            linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            apontamentos.append(Apontamento(
                rel, 1, f"nao consegui ler arquivo: {e}", "verificar permissoes de leitura",
                severidade="bloqueante",
            ))
            continue
        for num_linha, linha in enumerate(linhas, 1):
            for m in PADRAO_CRASE.finditer(linha):
                expr = m.group(1).strip()
                j = julgar_citacao(expr, verbos, abertos)
                if j is None or j[2]:
                    continue
                v, ato, _ = j
                apontamentos.append(Apontamento(
                    rel, num_linha,
                    f"`{expr}`: verbo '{v}' nao serve ato '{ato}'",
                    f"corrigir a citacao do ato ou declarar ato '{ato}' em bin/{v}",
                    severidade="aviso", id="VOCABULARIO",
                ))
    return apontamentos
