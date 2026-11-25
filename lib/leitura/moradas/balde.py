"""Adaptador da morada `balde` (objetos imutáveis por sha256) do componente leitura (story #4442, t6)."""
from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .. import formatos as F
from ..extrator import ErroExtrator, extrair_em_subprocesso, extrair_via_socket
from ..morada import eh_segredo
from ..nucleo import CABECA_TIPO, detectar_formato
from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada, montar_pagina_bruta, normalizar_termo

_RE_SHA256 = re.compile(r"^[0-9a-f]{64}$")

AbridorObjetoBalde = Callable[[str, int], tuple[int, str] | None]
ListadorBalde = Callable[[int], Sequence[Mapping[str, str]]]
ExtratorFn = Callable[[int, Mapping[str, Any], int], dict[str, Any]]


def _extrair_sha(alvo: AlvoResolvido) -> str:
    bruto = alvo.endereco.split(":", 1)[1] if ":" in alvo.endereco else alvo.endereco
    return bruto.strip().lower()


def _fechar_silencioso(fd: int) -> None:
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass


def _abrir_em_diretorio(raiz: Path, sha: str) -> tuple[int, str] | None:
    candidatos = (raiz / sha, raiz / sha[:2] / sha)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    for cand in candidatos:
        try:
            fd = os.open(str(cand), flags)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="morada:balde",
                    recebido=sha,
                    regra="disponibilidade-morada-balde",
                    cura=f"erro ao abrir objeto no balde: {exc}",
                    proximo=f"acervo ler objeto:{sha}",
                )
            ) from None
        return fd, cand.name
    return None


def _listar_em_diretorio(raiz: Path) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    try:
        entradas = sorted(os.scandir(raiz), key=lambda e: e.name)
    except OSError:
        return itens
    for entrada in entradas:
        if entrada.is_symlink():
            continue
        if entrada.is_file(follow_symlinks=False) and _RE_SHA256.fullmatch(entrada.name):
            itens.append({"sha256": entrada.name, "nome": entrada.name})
    return itens


def _montar_pedido_extrator(alvo: AlvoResolvido, seletor: SeletorParte) -> dict[str, Any]:
    pedido: dict[str, Any] = {
        "chave": alvo.chave_pedida,
        "modo": seletor.modo,
        "dpi": seletor.dpi,
        "max_bytes": seletor.max_bytes,
    }
    if seletor.membro is not None:
        pedido["membro"] = seletor.membro
    if seletor.paginas is not None:
        pedido["paginas"] = list(seletor.paginas)
    if seletor.cauda_paginas is not None:
        pedido["cauda_paginas"] = seletor.cauda_paginas
    return pedido


def _ler_fd_completo(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    partes: list[bytes] = []
    while True:
        bloco = os.read(fd, 65_536)
        if not bloco:
            break
        partes.append(bloco)
    return b"".join(partes)


def criar_abridor_bytes(mapa: Mapping[str, tuple[bytes, str]]) -> AbridorObjetoBalde:
    """Auxiliar para testes: cria abridor que entrega descritor real via arquivo temporário."""

    def _abrir(sha: str, _prazo_ms: int) -> tuple[int, str] | None:
        par = mapa.get(sha)
        if par is None:
            return None
        conteudo, nome = par
        with tempfile.TemporaryFile() as tmp:
            tmp.write(conteudo)
            tmp.flush()
            tmp.seek(0)
            dup_fd = os.dup(tmp.fileno())
        return dup_fd, nome

    return _abrir


class AdaptadorBalde:
    """Abre objetos imutáveis por sha256 e encaminha descritor de binários ao extrator isolado."""

    def __init__(
        self,
        *,
        raiz_local: Path | None = None,
        abridor: AbridorObjetoBalde | None = None,
        listador: ListadorBalde | None = None,
        socket_extrator: Path | str | None = None,
        extrator: ExtratorFn | None = None,
    ) -> None:
        self._raiz = raiz_local
        self._abridor = abridor
        self._listador = listador
        self._socket_extrator = Path(socket_extrator) if socket_extrator else None
        self._extrator = extrator

    def _abrir_fd(self, sha: str, prazo_ms: int) -> tuple[int, str] | None:
        if self._abridor is not None:
            return self._abridor(sha, prazo_ms)
        if self._raiz is not None:
            return _abrir_em_diretorio(self._raiz, sha)
        raise ErroMorada(
            Recusa(
                saida=3,
                codigo="morada-sem-resposta",
                onde="morada:balde",
                recebido=sha,
                regra="disponibilidade-morada-balde",
                cura="nenhum provedor de balde configurado nesta instância",
                proximo=f"acervo ler objeto:{sha}",
            )
        )

    def _chamar_extrator(self, fd: int, pedido: Mapping[str, Any], prazo_ms: int) -> dict[str, Any]:
        if self._extrator is not None:
            return self._extrator(fd, pedido, prazo_ms)
        if self._socket_extrator is not None:
            return extrair_via_socket(self._socket_extrator, fd, pedido, prazo_ms=prazo_ms)
        return extrair_em_subprocesso(fd, pedido, prazo_ms=prazo_ms)

    def _precisa_extrator(self, mime: str, seletor: SeletorParte, *, eh_binario: bool) -> bool:
        return (
            mime in F.FORMATOS_ISOLADOS
            or seletor.membro is not None
            or seletor.paginas is not None
            or seletor.cauda_paginas is not None
            or seletor.modo == "pagina"
            or (eh_binario and mime in F.LEITORES)
        )

    def _extrair_para_objeto(
        self, fd: int, alvo: AlvoResolvido, seletor: SeletorParte, nome: str, prazo_ms: int
    ) -> ObjetoBruto:
        sha = _extrair_sha(alvo)
        pedido = _montar_pedido_extrator(alvo, seletor)
        try:
            resp = self._chamar_extrator(fd, pedido, prazo_ms)
        except ErroExtrator as exc:
            raise ErroMorada(exc.recusa) from None
        if resp.get("imagens") is not None and resp.get("conteudo") is None:
            corpo = json.dumps(resp["imagens"], ensure_ascii=False).encode("utf-8")
        else:
            corpo = str(resp.get("conteudo") or "").encode("utf-8")
        avisos = tuple(str(a) for a in (resp.get("avisos") or ()))
        return ObjetoBruto(
            alvo=alvo,
            versao=sha,
            dados=corpo,
            nome_arquivo=nome or f"{sha}.txt",
            total_bytes=len(corpo),
            avisos=avisos,
        )

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto:
        sha = _extrair_sha(alvo)
        if not _RE_SHA256.fullmatch(sha):
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="chave-mal-formada",
                    onde="morada:balde",
                    recebido=alvo.chave_pedida,
                    regra="sha256-objeto-balde",
                    cura="objetos no balde exigem hash sha256 hexadecimal de 64 caracteres",
                    proximo="",
                )
            )
        if seletor.versao_pedida and seletor.versao_pedida.lower() != sha:
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="versao-divergente",
                    onde="--versao",
                    recebido=seletor.versao_pedida,
                    regra="versao-imutavel-balde",
                    cura=f"a versão do objeto imutável é o próprio sha256 {sha}",
                    proximo=f"acervo ler {alvo.chave_pedida}",
                )
            )

        aberto = self._abrir_fd(sha, prazo_ms)
        if aberto is None:
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:balde",
                    recebido=alvo.chave_pedida,
                    regra="objeto-existente-no-balde",
                    cura=f"objeto sha256 {sha} não encontrado no balde (universo aberto)",
                    proximo="busca buscar",
                )
            )

        fd, nome = aberto
        try:
            if nome and eh_segredo(Path(nome)):
                raise ErroMorada(
                    Recusa(
                        saida=4,
                        codigo="segredo-fora-do-leitor",
                        onde="morada:balde",
                        recebido=alvo.chave_pedida,
                        regra="vedacao-de-segredo",
                        cura="objeto vedado no leitor geral",
                        proximo="",
                    )
                )
            os.lseek(fd, 0, os.SEEK_SET)
            cabeca = os.read(fd, CABECA_TIPO)
            os.lseek(fd, 0, os.SEEK_SET)
            mime, eh_binario = detectar_formato(cabeca, nome or sha)

            if self._precisa_extrator(mime, seletor, eh_binario=eh_binario):
                return self._extrair_para_objeto(fd, alvo, seletor, nome, prazo_ms)

            dados = _ler_fd_completo(fd)
            return ObjetoBruto(
                alvo=alvo,
                versao=sha,
                dados=dados,
                nome_arquivo=nome or sha,
                total_bytes=len(dados),
            )
        finally:
            _fechar_silencioso(fd)

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros
        if self._listador is not None:
            brutos = list(self._listador(prazo_ms))
        elif self._raiz is not None:
            brutos = _listar_em_diretorio(self._raiz)
        else:
            brutos = []

        termo_n = normalizar_termo(termo) if termo else None
        itens: list[dict[str, str]] = []
        for reg in brutos:
            sha = str(reg.get("sha256") or "")
            nome = str(reg.get("nome") or sha)
            if not sha or eh_segredo(Path(nome)):
                continue
            chave = f"{classe}:{sha}"
            if termo_n and termo_n not in normalizar_termo(chave) and termo_n not in normalizar_termo(nome):
                continue
            itens.append({"chave": chave, "rotulo": nome, "resumo_curto": sha[:12]})

        return montar_pagina_bruta(
            classe, itens, limite=limite, cursor=cursor, universo_fechado=False
        )
