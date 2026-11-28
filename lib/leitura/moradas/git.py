"""Adaptador da morada git: leitura segura na árvore publicada da release.

Caminha segmento a segmento com `openat` + `O_RDONLY | O_NOFOLLOW | O_CLOEXEC`,
recusa elos simbólicos com saída 4 (`acesso-negado`), confere `S_ISREG` e
`(st_dev, st_ino)` / `(st_size, st_mtime_ns)` no descritor aberto, bloqueia
superfícies vedadas (`eh_segredo`) e calcula a versão `sha1` Git do blob.
"""
from __future__ import annotations

import errno
import hashlib
import os
import stat
import subprocess
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path

from ..morada import eh_segredo
from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada

_FLAGS_ABERTURA = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_FLAGS_DIR = _FLAGS_ABERTURA | getattr(os, "O_DIRECTORY", 0)
_BLOCO_LEITURA = 1024 * 1024


def _sha1_git_blob(dados: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(dados)}\0".encode("ascii"))
    h.update(dados)
    return h.hexdigest()


def _normalizar_termo(texto: str) -> str:
    return unicodedata.normalize("NFC", texto).casefold()


def _fechar(fd: int) -> None:
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass


def _recusa_negado_git(rel_path: str, regra: str, cura: str) -> ErroMorada:
    return ErroMorada(
        Recusa(
            saida=4,
            codigo="acesso-negado",
            onde="morada:git",
            recebido=rel_path,
            regra=regra,
            cura=cura,
            proximo="",
        )
    )


def _abrir_segmento(dir_fd: int, segmento: str, flags: int, rel_path: str) -> int:
    try:
        return os.open(segmento, flags, dir_fd=dir_fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise _recusa_negado_git(
                rel_path,
                "sem-elo-simbolico-em-openat",
                "elo simbólico recusado na abertura na release",
            ) from None
        if exc.errno == errno.ENOENT:
            raise FileNotFoundError(rel_path) from None
        raise


def _validar_fd_regular(dir_fd: int, ultimo: str, fd: int, rel_path: str) -> os.stat_result:
    st_lstat = os.lstat(ultimo, dir_fd=dir_fd)
    st_fd = os.fstat(fd)
    if not stat.S_ISREG(st_fd.st_mode):
        raise _recusa_negado_git(
            rel_path,
            "arquivo-regular-exigido",
            "o alvo na morada git não é arquivo regular",
        )
    if (st_fd.st_dev, st_fd.st_ino) != (st_lstat.st_dev, st_lstat.st_ino):
        raise _recusa_negado_git(
            rel_path,
            "invariante-dev-ino-fstat",
            "divergência de identidade de arquivo entre lstat e fstat",
        )
    return st_fd


def _abrir_sem_symlink(raiz: Path, rel_path: str) -> tuple[int, os.stat_result]:
    """Abre `rel_path` sob `raiz` caminhando segmento a segmento com O_NOFOLLOW."""
    partes = [p for p in rel_path.split("/") if p]
    if not partes or any(p in (".", "..") for p in partes):
        raise _recusa_negado_git(
            rel_path,
            "caminho-relativo-confinado",
            "caminho fora da árvore publicada da release",
        )

    dir_fd = os.open(raiz, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0))
    try:
        for segmento in partes[:-1]:
            proximo = _abrir_segmento(dir_fd, segmento, _FLAGS_DIR, rel_path)
            _fechar(dir_fd)
            dir_fd = proximo

        ultimo = partes[-1]
        fd = _abrir_segmento(dir_fd, ultimo, _FLAGS_ABERTURA, rel_path)
        try:
            return fd, _validar_fd_regular(dir_fd, ultimo, fd, rel_path)
        except Exception:
            _fechar(fd)
            raise
    finally:
        _fechar(dir_fd)


class AdaptadorGit:
    """Adaptador da morada `git` sobre a árvore publicada da release."""

    def __init__(
        self,
        raiz_release: Path,
        *,
        fallback_banco: Callable[[AlvoResolvido, SeletorParte, int], ObjetoBruto] | None = None,
        repo_git: Path | None = None,
    ) -> None:
        self._raiz = Path(raiz_release)
        self._fallback_banco = fallback_banco
        self._repo_git = Path(repo_git) if repo_git is not None else None

    def _ler_versao_git(self, alvo: AlvoResolvido, versao_pedida: str, prazo_ms: int) -> ObjetoBruto:
        if self._repo_git is None:
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="versao-divergente",
                    onde="--versao",
                    recebido=versao_pedida,
                    regra="versao-na-morada-git",
                    cura="a versão pedida não coincide com o objeto publicado e não há histórico git local",
                    proximo=f"busca ler {alvo.chave_pedida}",
                )
            )
        spec = f"{versao_pedida}:{alvo.endereco}"
        proc = subprocess.run(
            ["git", "-C", str(self._repo_git), "show", spec],
            capture_output=True,
            check=False,
            timeout=max(0.5, prazo_ms / 1000.0),
        )
        if proc.returncode != 0:
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="versao-divergente",
                    onde="--versao",
                    recebido=versao_pedida,
                    regra="versao-na-morada-git",
                    cura=f"revisão {versao_pedida!r} não encontrada para {alvo.endereco}",
                    proximo=f"busca ler {alvo.chave_pedida}",
                )
            )
        dados = proc.stdout
        return ObjetoBruto(
            alvo=alvo,
            versao=_sha1_git_blob(dados),
            dados=dados,
            nome_arquivo=Path(alvo.endereco).name,
            total_bytes=len(dados),
        )

    def ler_objeto(
        self,
        alvo: AlvoResolvido,
        seletor: SeletorParte,
        prazo_ms: int,
    ) -> ObjetoBruto:
        caminho_logico = self._raiz / alvo.endereco
        if eh_segredo(caminho_logico) or eh_segredo(Path(alvo.endereco)):
            raise ErroMorada(
                Recusa(
                    saida=4,
                    codigo="segredo-fora-do-leitor",
                    onde="morada:git",
                    recebido=alvo.chave_pedida,
                    regra="vedacao-de-superficies",
                    cura="superfície vedada ao leitor geral",
                    proximo="",
                )
            )

        try:
            fd, st_antes = _abrir_sem_symlink(self._raiz, alvo.endereco)
        except FileNotFoundError:
            if self._fallback_banco is not None:
                bruto_vivo = self._fallback_banco(alvo, seletor, prazo_ms)
                avisos = (*bruto_vivo.avisos, "arquivo aguarda promocao na release")
                return ObjetoBruto(
                    alvo=bruto_vivo.alvo,
                    versao=bruto_vivo.versao,
                    dados=bruto_vivo.dados,
                    fluxo=bruto_vivo.fluxo,
                    nome_arquivo=bruto_vivo.nome_arquivo,
                    total_bytes=bruto_vivo.total_bytes,
                    mtime_ns=bruto_vivo.mtime_ns,
                    avisos=avisos,
                    mudou=bruto_vivo.mudou,
                )
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:git",
                    recebido=alvo.chave_pedida,
                    regra="objeto-na-release",
                    cura=f"arquivo {alvo.endereco!r} não encontrado na árvore publicada",
                    proximo=f"busca consultar --classe {alvo.classe}",
                )
            ) from None

        try:
            partes: list[bytes] = []
            while True:
                bloco = os.read(fd, _BLOCO_LEITURA)
                if not bloco:
                    break
                partes.append(bloco)
            st_depois = os.fstat(fd)
        finally:
            _fechar(fd)

        dados = b"".join(partes)
        versao = _sha1_git_blob(dados)
        avisos_lista: list[str] = []
        if (st_antes.st_size, st_antes.st_mtime_ns) != (st_depois.st_size, st_depois.st_mtime_ns):
            avisos_lista.append("instavel")

        if seletor.versao_pedida and seletor.versao_pedida != versao:
            return self._ler_versao_git(alvo, seletor.versao_pedida, prazo_ms)

        return ObjetoBruto(
            alvo=alvo,
            versao=versao,
            dados=dados,
            nome_arquivo=Path(alvo.endereco).name,
            total_bytes=len(dados),
            mtime_ns=st_depois.st_mtime_ns,
            avisos=tuple(avisos_lista),
        )

    def _varrer_arvore(self, base: Path, classe: str, termo_norm: str | None) -> list[dict[str, str]]:
        itens: list[dict[str, str]] = []
        pilha: list[Path] = [base]
        while pilha:
            atual = pilha.pop()
            try:
                entradas = sorted(os.scandir(atual), key=lambda e: e.name)
            except OSError:
                continue
            for entrada in entradas:
                if entrada.is_symlink() or entrada.name.startswith("."):
                    continue
                caminho = Path(entrada.path)
                rel = caminho.relative_to(self._raiz).as_posix()
                if eh_segredo(caminho) or eh_segredo(Path(rel)):
                    continue
                if entrada.is_dir(follow_symlinks=False):
                    pilha.append(caminho)
                elif entrada.is_file(follow_symlinks=False):
                    slug = caminho.relative_to(base).with_suffix("").as_posix()
                    chave = f"{classe}:{slug}"
                    if termo_norm and termo_norm not in _normalizar_termo(chave):
                        continue
                    itens.append({"chave": chave, "rotulo": slug, "resumo_curto": rel})
        itens.sort(key=lambda it: it["chave"])
        return itens

    def _base_da_classe(self, classe: str) -> Path | None:
        for cand in (
            self._raiz / "instancias" / classe,
            self._raiz / "referencias" / "instancias" / classe,
            self._raiz / classe,
        ):
            if cand.is_dir():
                return cand
        return None

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros, prazo_ms
        base = self._base_da_classe(classe)
        termo_norm = _normalizar_termo(termo) if termo else None
        todos = self._varrer_arvore(base, classe, termo_norm) if base is not None else []
        total = len(todos)
        versao_atual = hashlib.sha256(
            "\n".join(it["chave"] for it in todos).encode("utf-8")
        ).hexdigest()[:16]

        mudou: dict[str, str] | None = None
        avisos: list[str] = []
        filtrados = todos
        if cursor is not None:
            if cursor.versao_retrato != versao_atual:
                mudou = {"de": cursor.versao_retrato, "para": versao_atual}
                avisos.append("versao_alterada_entre_paginas")
            filtrados = [it for it in todos if it["chave"] > cursor.ultima_chave]

        fatia = filtrados[: limite + 1]
        tem_mais = len(fatia) > limite
        pagina = fatia[:limite]
        prox_tupla = (0, pagina[-1]["chave"]) if (tem_mais and pagina) else None

        return PaginaBruta(
            classe=classe,
            versao=versao_atual,
            digest=None,
            universo_fechado=True,
            total=total,
            itens=tuple(pagina),
            proxima_tupla=prox_tupla,
            mudou=mudou,
            avisos=tuple(avisos),
        )
