"""bancada — resolucao de bancada de trabalho para o verbo lint."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# Importa raizes
try:
    from lib import raizes
except ImportError:
    aqui = Path(__file__).resolve().parent
    harness_raiz = aqui.parent.parent
    if str(harness_raiz) not in sys.path:
        sys.path.insert(0, str(harness_raiz))
    from lib import raizes


class ErroBancada(Exception):
    def __init__(self, msg: str, exit_code: int = 1):
        super().__init__(msg)
        self.msg = msg
        self.exit_code = exit_code


def resolver_bancada(nome_repo: str) -> Tuple[Path, Optional[str]]:
    """Resolve a pasta de bancada para o repositorio.
    
    Retorna (caminho_absoluto, chave_se_houver).
    Lanca ErroBancada caso nao encontre ou seja invalido.
    """
    if not nome_repo:
        raise ErroBancada("falta o nome do repo", 2)

    chave = None
    if "@" in nome_repo:
        nome_repo, chave = nome_repo.split("@", 1)

    for c in ("/", "..", "\\"):
        if c in nome_repo:
            raise ErroBancada(f"nome de repo invalido: '{nome_repo}'", 4)
        if chave and c in chave:
            raise ErroBancada(f"chave de bancada invalida: '{chave}'", 2)

    try:
        raiz_bancada = raizes.bancada()
    except Exception as e:
        raise ErroBancada(str(e), 3)

    cadeira = os.environ.get("PF_CADEIRA", "").strip()
    cadeira = cadeira.removeprefix("claudinho-").removeprefix("claudinha-")

    # 1. Se chave explicita foi passada: wt/<nome>/<cadeira>/<chave>
    if chave:
        if cadeira:
            cand = raiz_bancada / "wt" / nome_repo / cadeira / chave
            if (cand / ".git").exists():
                return cand.resolve(), chave
        raise ErroBancada(
            f"sem bancada '{nome_repo}@{chave}' nesta cadeira — vizinho: repo abrir {nome_repo} <card> --slug <s>",
            1,
        )

    # 2. Se cadeira tem worktree aninhada
    if cadeira:
        dir_cadeira = raiz_bancada / "wt" / nome_repo / cadeira
        if dir_cadeira.is_dir() and not (dir_cadeira / ".git").exists():
            cands = [d for d in dir_cadeira.iterdir() if d.is_dir() and (d / ".git").exists()]
            if len(cands) == 1:
                return cands[0].resolve(), cands[0].name
            if len(cands) > 1:
                nomes_cands = "\n".join(f"  {nome_repo}@{d.name}" for d in sorted(cands, key=lambda x: x.name))
                raise ErroBancada(
                    f"mais de uma bancada aberta de {nome_repo} nesta cadeira — nomeie qual:\n{nomes_cands}",
                    2,
                )

    # 3. Legado: sessao
    sid = os.environ.get("PF_SESSAO", "").strip()
    if sid:
        cand_sid = raiz_bancada / "wt" / nome_repo / sid
        if (cand_sid / ".git").exists():
            return cand_sid.resolve(), sid

    # 4. Plana da cadeira: wt/<nome>/<cadeira>
    if cadeira:
        cand_cad = raiz_bancada / "wt" / nome_repo / cadeira
        if (cand_cad / ".git").exists():
            return cand_cad.resolve(), None

    # 5. Worktrees no formato wt-<card>-<repo>
    if raiz_bancada.is_dir():
        cands_wt = []
        for d in raiz_bancada.iterdir():
            if d.is_dir() and d.name.startswith("wt-") and (d / ".git").exists():
                curto = nome_repo.removeprefix("platafirma-")
                if d.name.endswith(f"-{curto}") or d.name.endswith(f"-{nome_repo}"):
                    cands_wt.append(d)
        if len(cands_wt) == 1:
            return cands_wt[0].resolve(), cands_wt[0].name

    # 6. Fallback direto no repo: <bancada>/<nome_repo>
    cand_direto = raiz_bancada / nome_repo
    if cand_direto.is_dir() and (cand_direto / ".git").exists():
        return cand_direto.resolve(), None

    # 7. Fallback com prefixo platafirma-
    if not nome_repo.startswith("platafirma-"):
        cand_pf = raiz_bancada / f"platafirma-{nome_repo}"
        if cand_pf.is_dir() and (cand_pf / ".git").exists():
            return cand_pf.resolve(), None

    nome_exib = f"{nome_repo}@{chave}" if chave else nome_repo
    raise ErroBancada(
        f"sem bancada '{nome_exib}' nesta cadeira — vizinho: repo abrir {nome_repo} <card> --slug <s>",
        1,
    )


def resolver_alvo(raiz_repo: Path, alvo: str) -> Path:
    """Resolve e valida o caminho do alvo dentro do repositorio."""
    if alvo.startswith("-"):
        raise ErroBancada(f"alvo nao pode comecar com '-': '{alvo}'", 2)

    caminho = (raiz_repo / alvo).resolve()
    raiz_real = raiz_repo.resolve()

    try:
        caminho.relative_to(raiz_real)
    except ValueError:
        raise ErroBancada(f"alvo '{alvo}' resolve fora da raiz do repo", 4)

    if not caminho.exists():
        raise ErroBancada(f"alvo '{alvo}' nao existe em {raiz_repo}", 3)

    return caminho
