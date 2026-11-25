"""Validação léxica e confinamento de caminho na bancada de dois níveis."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .tipos import ErroEscrita, RecusaEscrita

_RE_SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
_MIN_ASCII_IMPRIMIVEL = 32


@dataclass(frozen=True)
class BancadaConfinada:
    """Alvo confinado a uma bancada worktree válida de dois níveis."""

    repo: str
    cadeira: str
    chave_bancada: str
    raiz_wt: Path
    componentes_bancada: tuple[str, ...]
    componentes_alvo: tuple[str, ...]
    caminho_relativo: str


def _erro_fora_morada(onde: str, recebido: str, cura: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=4,
            codigo="fora-de-morada",
            onde=onde,
            recebido=recebido,
            regra="o caminho deve permanecer estritamente dentro da bancada aberta",
            cura=cura,
            proximo="",
        )
    )


def validar_caminho_relativo(caminho: str) -> tuple[str, ...]:
    """Valida o léxico do caminho relativo, bloqueando segmentos vazios, ., .. e controle."""
    if not caminho or "\\" in caminho or any(ord(c) < _MIN_ASCII_IMPRIMIVEL for c in caminho):
        raise _erro_fora_morada(
            "caminho", caminho, "informe caminho POSIX relativo sem caracteres de controle"
        )
    if caminho.startswith("/"):
        raise _erro_fora_morada(
            "caminho", caminho, "use caminho relativo à raiz do repositório, não absoluto"
        )
    partes = caminho.split("/")
    if any(p in ("", ".", "..") for p in partes):
        raise _erro_fora_morada(
            "caminho", caminho, "remova segmentos vazios, '.' e '..' do caminho"
        )
    if ".git" in partes:
        raise RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="superficie-vedada",
                onde="caminho",
                recebido=caminho,
                regra="pasta interna .git não se altera pelo ato escrever",
                cura="use as operações próprias do verbo repo",
                proximo="",
            )
        )
    return tuple(partes)


def separar_chave_componente(chave: str) -> tuple[str, str | None, str]:
    """Separa `<repo>[@<bancada>]:<caminho_relativo>` validando o nome do repositório."""
    if ":" not in chave:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="chave",
                recebido=chave,
                regra="chave de componente deve seguir <repo>:<caminho_relativo>",
                cura="informe <repo>:<caminho_relativo>",
                proximo="",
            )
        )
    cab, rel = chave.split(":", 1)
    repo, chave_bancada = (cab.split("@", 1) if "@" in cab else (cab, None))
    if not repo or not _RE_SLUG.match(repo) or repo in (".", ".."):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="repo",
                recebido=repo,
                regra="nome de repositório inválido",
                cura="informe o nome do repositório da casa",
                proximo="",
            )
        )
    if chave_bancada is not None and (
        not chave_bancada or not _RE_SLUG.match(chave_bancada) or chave_bancada in (".", "..")
    ):
        raise _erro_fora_morada(
            "bancada", chave_bancada, "informe chave de bancada simples sem separadores"
        )
    return repo, chave_bancada, rel


def _ler_ponteiro_git(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="sem-bancada",
                onde=str(caminho),
                recebido=str(exc),
                regra="ponteiro .git da bancada deve ser legível em UTF-8",
                cura="saneie ou reabra a bancada com repo abrir",
                proximo="",
            )
        ) from exc


def _worktree_registrada_no_clone(clone_base: Path, wt_dir: Path) -> bool:
    """Confere se `wt_dir` é worktree registrada no clone-base sem depender do UID."""
    arq_git = wt_dir / ".git"
    if arq_git.is_symlink() or not arq_git.is_file():
        return False
    linhas = _ler_ponteiro_git(arq_git).splitlines()
    if not linhas:
        return False
    primeira = linhas[0].strip()
    if not primeira.startswith("gitdir:"):
        return False
    bruto = primeira.removeprefix("gitdir:").strip()
    admin_dir = (wt_dir / bruto).resolve()
    worktrees_dir = (clone_base / ".git" / "worktrees").resolve()
    if not admin_dir.is_relative_to(worktrees_dir):
        return False
    ponteiro_volta = admin_dir / "gitdir"
    if not ponteiro_volta.is_file():
        return False
    volta = Path(_ler_ponteiro_git(ponteiro_volta).strip()).resolve()
    return volta == arq_git.resolve()


def _validar_cadeira(cadeira: str) -> str:
    limpa = (cadeira or "").strip()
    if not limpa or not _RE_SLUG.match(limpa) or limpa in (".", ".."):
        raise _erro_fora_morada("cadeira", cadeira, "informe o slug válido da cadeira")
    return limpa


def _selecionar_worktree(
    repo: str,
    cadeira: str,
    chave_bancada: str | None,
    raiz_bancadas: Path,
) -> str:
    clone_base = raiz_bancadas / repo
    wt_cad = raiz_bancadas / "wt" / repo / cadeira
    if chave_bancada is not None:
        if chave_bancada == "clone-base":
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="clone-base-recusado",
                    onde="bancada",
                    recebido=f"{repo}@{chave_bancada}",
                    regra="escrita no clone-base é proibida",
                    cura=f"abra uma bancada com repo abrir {repo} <card>",
                    proximo=f"repo abrir {repo}",
                )
            )
        cand = wt_cad / chave_bancada
        if not cand.is_dir() or not _worktree_registrada_no_clone(clone_base, cand):
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="sem-bancada",
                    onde="bancada",
                    recebido=f"wt/{repo}/{cadeira}/{chave_bancada}",
                    regra="bancada deve existir e estar registrada no clone-base",
                    cura=f"abra a bancada com repo abrir {repo} <card>",
                    proximo=f"repo abrir {repo}",
                )
            )
        return chave_bancada

    abertas = (
        sorted(
            d.name
            for d in wt_cad.iterdir()
            if d.is_dir() and not d.is_symlink() and _worktree_registrada_no_clone(clone_base, d)
        )
        if wt_cad.is_dir()
        else []
    )
    if not abertas:
        if (clone_base / ".git").exists():
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="clone-base-recusado",
                    onde="bancada",
                    recebido=repo,
                    regra="sem bancada aberta para a cadeira; o clone-base não aceita escrita",
                    cura=f"abra uma bancada com repo abrir {repo} <card>",
                    proximo=f"repo abrir {repo}",
                )
            )
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="sem-bancada",
                onde="bancada",
                recebido=repo,
                regra="nenhuma bancada aberta encontrada para a cadeira",
                cura=f"abra uma bancada com repo abrir {repo} <card>",
                proximo=f"repo abrir {repo}",
            )
        )
    if len(abertas) > 1:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="bancada-ambigua",
                onde="bancada",
                recebido=", ".join(abertas),
                regra="mais de uma bancada aberta exige chave explícita <repo>@<chave>",
                cura=f"especifique {repo}@<chave>:<caminho>",
                proximo="",
            )
        )
    return abertas[0]


def resolver_bancada(
    chave: str, cadeira: str, raiz_bancadas: Path
) -> BancadaConfinada:
    """Resolve e confina `<repo>[@<chave>]:<caminho_relativo>` na bancada da cadeira."""
    cad = _validar_cadeira(cadeira)
    repo, chave_bancada, rel = separar_chave_componente(chave)
    componentes_alvo = validar_caminho_relativo(rel)
    selecionada = _selecionar_worktree(repo, cad, chave_bancada, Path(raiz_bancadas))
    return BancadaConfinada(
        repo=repo,
        cadeira=cad,
        chave_bancada=selecionada,
        raiz_wt=Path(raiz_bancadas) / "wt",
        componentes_bancada=(repo, cad, selecionada),
        componentes_alvo=componentes_alvo,
        caminho_relativo="/".join(componentes_alvo),
    )
