"""Operações POSIX atômicas sobre descritores de diretório para a morada git."""
from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import secrets
import stat
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .tipos import ErroEscrita, RecusaEscrita

MODO_DIR_BANCADA = (
    stat.S_ISGID
    | stat.S_IRWXU
    | stat.S_IRWXG
    | stat.S_IROTH
    | stat.S_IXOTH
)
MODO_ARQ_COMUM = (
    stat.S_IRUSR
    | stat.S_IWUSR
    | stat.S_IRGRP
    | stat.S_IWGRP
    | stat.S_IROTH
)
MODO_ARQ_EXEC = MODO_ARQ_COMUM | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
MODO_TMP_INICIAL = stat.S_IRUSR | stat.S_IWUSR
_BITS_EXEC = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
PREFIXO_TMP = ".pf-esc-"
SUFIXO_TMP = ".tmp"
_FLAGS_DIR_SEGURO = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FLAGS_ARQ_LEITURA = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
_FLAGS_TMP_CRIACAO = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC


@dataclass(frozen=True)
class DestinoIO:
    """Parâmetros agrupados de localização, trava e prazo para escrita atômica."""

    raiz_wt: Path
    componentes_bancada: tuple[str, ...]
    componentes_alvo: tuple[str, ...]
    estado_dir: Path
    prazo_ns: int = 0
    passo_ms: int = 25
    teto_leitura_bytes: int = 0


@dataclass(frozen=True)
class ResultadoIO:
    """Metadados devolvidos após a operação atômica em disco."""

    alterou: bool
    ja_gravado: bool
    substituiu: bool
    bytes_gravados: int
    versao_anterior: str | None
    versao_nova: str
    modo_final: int


@dataclass(frozen=True)
class AlvoLido:
    """Resultado tipado da leitura segura de um alvo existente ou ausente."""

    existe: bool
    dados: bytes = b""
    modo: int | None = None


def blob_sha1(dados: bytes) -> str:
    """Calcula o SHA-1 completo do blob git (equivalente a git hash-object -t blob)."""
    cab = f"blob {len(dados)}\0".encode("ascii")
    return hashlib.sha1(cab + dados, usedforsecurity=False).hexdigest()


def _erro_atalho(onde: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=4,
            codigo="caminho-com-atalho",
            onde=onde,
            recebido=onde,
            regra="travessia e alvo recusam links simbólicos via O_NOFOLLOW",
            cura="aponte para um caminho real dentro da bancada sem symlinks",
            proximo="",
        )
    )


def _erro_superficie(onde: str, detalhe: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=4,
            codigo="superficie-vedada",
            onde=onde,
            recebido=detalhe,
            regra="alvo deve ser arquivo regular com st_nlink == 1",
            cura="remova FIFO, dispositivo ou vínculo múltiplo antes de gravar",
            proximo="",
        )
    )


def _erro_trava_ocupada(onde: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="bancada-ocupada",
            onde=onde,
            recebido="prazo esgotado na trava",
            regra="escritas na mesma bancada aguardam a trava até o prazo",
            cura="repita a chamada quando a escrita concorrente concluir",
            proximo="",
        )
    )


def _erro_prazo_antes_replace(onde: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="morada-sem-resposta",
            onde=onde,
            recebido="prazo esgotado antes da troca atômica",
            regra="operação expirada antes do ponto de não volta sai 3",
            cura="repita a chamada com prazo suficiente",
            proximo="",
        )
    )


def _erro_alvo_grande(onde: str, teto_bytes: int) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=2,
            codigo="tamanho-excedido",
            onde=onde,
            recebido=f">{teto_bytes} bytes",
            regra=f"alvo existente excede o teto de leitura de {teto_bytes} bytes",
            cura="edite o arquivo fora do ato escrever ou reduza o tamanho do alvo",
            proximo="",
        )
    )


def _erro_os_antes_replace(onde: str, exc: OSError) -> RecusaEscrita:
    if exc.errno == errno.ENOSPC:
        return RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="sem-espaco",
                onde=onde,
                recebido=str(exc),
                regra="sem espaço em disco antes da troca atômica",
                cura="libere espaço em disco e repita a chamada",
                proximo="",
            )
        )
    if exc.errno in (errno.EACCES, errno.EPERM):
        return RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="bancada-sem-permissao",
                onde=onde,
                recebido=str(exc),
                regra=(
                    "a bancada não dá escrita ao grupo platafirma-escrita; "
                    "repetir a chamada falha igual"
                ),
                cura=(
                    "reabra a bancada com repo abrir <repo> <card> --slug <slug>, que põe o "
                    "grupo platafirma-escrita e o setgid nela, e grave de novo"
                ),
                proximo="repo abrir",
            )
        )
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="morada-sem-resposta",
            onde=onde,
            recebido=str(exc),
            regra="falha de sistema de arquivos antes do ponto de não volta",
            cura="verifique o estado da bancada e repita",
            proximo="",
        )
    )


def abrir_diretorio_seguro(
    raiz_fd: int, componentes: Sequence[str], *, criar_ausentes: bool = False
) -> int:
    """Desce componente a componente a partir de `raiz_fd` com O_NOFOLLOW."""
    atual_fd = os.dup(raiz_fd)
    try:
        for comp in componentes:
            if comp in ("", ".", "..") or "/" in comp:
                raise RecusaEscrita(
                    ErroEscrita(
                        saida=4,
                        codigo="fora-de-morada",
                        onde=comp,
                        recebido=comp,
                        regra="segmento inválido na travessia de diretório",
                        cura="use apenas segmentos simples relativos",
                        proximo="",
                    )
                )
            prox_fd = _abrir_ou_criar_dir(atual_fd, comp, criar_ausentes=criar_ausentes)
            os.close(atual_fd)
            atual_fd = prox_fd
        return atual_fd
    except Exception:
        os.close(atual_fd)
        raise


def _criar_e_abrir_dir(pai_fd: int, nome: str) -> int:
    try:
        os.mkdir(nome, MODO_DIR_BANCADA, dir_fd=pai_fd)
        novo_fd = os.open(nome, _FLAGS_DIR_SEGURO, dir_fd=pai_fd)
    except OSError as exc:
        raise _erro_os_antes_replace(nome, exc) from exc
    try:
        os.fchmod(novo_fd, MODO_DIR_BANCADA)
        os.fsync(pai_fd)
    except OSError as exc:
        os.close(novo_fd)
        raise _erro_os_antes_replace(nome, exc) from exc
    return novo_fd


def _abrir_ou_criar_dir(pai_fd: int, nome: str, *, criar_ausentes: bool) -> int:
    try:
        return os.open(nome, _FLAGS_DIR_SEGURO, dir_fd=pai_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise _erro_atalho(nome) from exc
        if exc.errno == errno.ENOENT and criar_ausentes:
            return _criar_e_abrir_dir(pai_fd, nome)
        if exc.errno == errno.ENOTDIR:
            st = os.stat(nome, dir_fd=pai_fd, follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode):
                raise _erro_atalho(nome) from exc
            raise _erro_superficie(nome, "componente não é diretório") from exc
        raise _erro_os_antes_replace(nome, exc) from exc


def _adquirir_flock(
    lock_fd: int, arq_trava: Path, *, prazo_ns: int, passo_ms: int
) -> None:
    adquirido = False
    while not adquirido:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            adquirido = True
        except BlockingIOError:
            if prazo_ns > 0 and time.monotonic_ns() >= prazo_ns:
                raise _erro_trava_ocupada(str(arq_trava)) from None
            time.sleep(passo_ms / 1000.0)


@contextmanager
def trava_bancada(
    estado_dir: Path,
    raiz_bancada_fd: int,
    *,
    prazo_ns: int = 0,
    passo_ms: int = 25,
) -> Iterator[None]:
    """Toma LOCK_EX | LOCK_NB no estado do escritor, chaveado por (st_dev, st_ino)."""
    st = os.fstat(raiz_bancada_fd)
    estado_dir.mkdir(parents=True, exist_ok=True)
    arq_trava = estado_dir / f"lock-{st.st_dev}-{st.st_ino}.flock"
    lock_fd = os.open(
        str(arq_trava), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, MODO_TMP_INICIAL
    )
    try:
        _adquirir_flock(lock_fd, arq_trava, prazo_ns=prazo_ns, passo_ms=passo_ms)
        yield
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _ler_fd_inteiro(fd: int, *, teto_bytes: int = 0, onde: str = "") -> bytes:
    partes: list[bytes] = []
    total = 0
    bloco = os.read(fd, 65_536)
    while bloco:
        total += len(bloco)
        if teto_bytes > 0 and total > teto_bytes:
            raise _erro_alvo_grande(onde, teto_bytes)
        partes.append(bloco)
        bloco = os.read(fd, 65_536)
    return b"".join(partes)


def ler_alvo_seguro(pai_fd: int, nome: str, *, teto_bytes: int = 0) -> AlvoLido:
    """Abre o alvo com O_NONBLOCK | O_NOFOLLOW e confere S_ISREG, st_nlink == 1 e teto."""
    try:
        fd = os.open(nome, _FLAGS_ARQ_LEITURA, dir_fd=pai_fd)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return AlvoLido(existe=False)
        if exc.errno == errno.ELOOP:
            raise _erro_atalho(nome) from exc
        if exc.errno == errno.ENXIO:
            raise _erro_superficie(nome, "FIFO ou dispositivo") from exc
        raise _erro_os_antes_replace(nome, exc) from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise _erro_superficie(nome, f"modo {oct(st.st_mode)}")
        if st.st_nlink != 1:
            raise _erro_superficie(nome, f"st_nlink={st.st_nlink}")
        if teto_bytes > 0 and st.st_size > teto_bytes:
            raise _erro_alvo_grande(nome, teto_bytes)
        dados = _ler_fd_inteiro(fd, teto_bytes=teto_bytes, onde=nome)
        return AlvoLido(existe=True, dados=dados, modo=stat.S_IMODE(st.st_mode))
    finally:
        os.close(fd)


def calcular_modo_final(modo_anterior: int | None, *, executavel: bool) -> int:
    """Calcula modo final preservando bit executável e compensando UMask=0077."""
    if modo_anterior is not None:
        return MODO_ARQ_EXEC if ((modo_anterior & _BITS_EXEC) or executavel) else MODO_ARQ_COMUM
    return MODO_ARQ_EXEC if executavel else MODO_ARQ_COMUM


def _conferir_destino_antes_replace(pai_fd: int, nome: str) -> None:
    st: os.stat_result | None = None
    try:
        st = os.stat(nome, dir_fd=pai_fd, follow_symlinks=False)
    except FileNotFoundError:
        st = None
    if st is None:
        return
    if stat.S_ISLNK(st.st_mode):
        raise _erro_atalho(nome)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise _erro_superficie(nome, f"modo={oct(st.st_mode)} nlink={st.st_nlink}")


def _escrever_todos(fd: int, dados: bytes) -> None:
    visao = memoryview(dados)
    enviados = 0
    while enviados < len(dados):
        escritos = os.write(fd, visao[enviados:])
        enviados += escritos


def gravar_atomico_em_dir(
    pai_fd: int,
    nome: str,
    dados: bytes,
    *,
    modo_final: int,
    prazo_ns: int = 0,
) -> None:
    """Grava temporário .pf-esc-*.tmp, aplica fchmod, sincroniza, troca e faz fsync do pai."""
    tmp_nome = f"{PREFIXO_TMP}{secrets.token_hex(8)}{SUFIXO_TMP}"
    tmp_fd = -1
    trocou = False
    try:
        tmp_fd = os.open(tmp_nome, _FLAGS_TMP_CRIACAO, MODO_TMP_INICIAL, dir_fd=pai_fd)
        _escrever_todos(tmp_fd, dados)
        os.fchmod(tmp_fd, modo_final)
        os.fsync(tmp_fd)
        os.close(tmp_fd)
        tmp_fd = -1
        _conferir_destino_antes_replace(pai_fd, nome)
        if prazo_ns > 0 and time.monotonic_ns() >= prazo_ns:
            raise _erro_prazo_antes_replace(nome)
        os.replace(tmp_nome, nome, src_dir_fd=pai_fd, dst_dir_fd=pai_fd)
        trocou = True
        os.fsync(pai_fd)
    except RecusaEscrita:
        _limpar_tmp(pai_fd, tmp_fd, tmp_nome)
        raise
    except OSError as exc:
        if not trocou:
            _limpar_tmp(pai_fd, tmp_fd, tmp_nome)
            raise _erro_os_antes_replace(nome, exc) from exc
        raise RecusaEscrita(
            ErroEscrita(
                saida=5,
                codigo="falha-disco",
                onde=nome,
                recebido=str(exc),
                regra="falha de fsync após o ponto de não volta (os.replace)",
                cura="repita com o mesmo --pedido para conferir o estado",
                proximo="",
            )
        ) from exc


def _limpar_tmp(pai_fd: int, tmp_fd: int, tmp_nome: str) -> None:
    if tmp_fd >= 0:
        try:
            os.close(tmp_fd)
        except OSError:
            pass
    try:
        os.unlink(tmp_nome, dir_fd=pai_fd)
    except OSError:
        pass


def executar_escrita_atomica(
    destino: DestinoIO,
    transformador: Callable[[bytes | None], tuple[bytes, bool]],
) -> ResultadoIO:
    """Executa a sequência POSIX completa sob trava da bancada no estado do escritor."""
    try:
        raiz_fd = os.open(str(destino.raiz_wt), _FLAGS_DIR_SEGURO)
    except OSError as exc:
        raise _erro_os_antes_replace(str(destino.raiz_wt), exc) from exc
    try:
        bancada_fd = abrir_diretorio_seguro(
            raiz_fd, destino.componentes_bancada, criar_ausentes=False
        )
        try:
            with trava_bancada(
                destino.estado_dir,
                bancada_fd,
                prazo_ns=destino.prazo_ns,
                passo_ms=destino.passo_ms,
            ):
                pai_fd = abrir_diretorio_seguro(
                    bancada_fd, destino.componentes_alvo[:-1], criar_ausentes=True
                )
                try:
                    nome = destino.componentes_alvo[-1]
                    existente = ler_alvo_seguro(
                        pai_fd, nome, teto_bytes=destino.teto_leitura_bytes
                    )
                    dados_atuais = existente.dados if existente.existe else None
                    modo_anterior = existente.modo if existente.existe else None
                    versao_anterior = (
                        blob_sha1(dados_atuais) if dados_atuais is not None else None
                    )
                    novos_dados, executavel = transformador(dados_atuais)
                    versao_nova = blob_sha1(novos_dados)
                    modo_final = calcular_modo_final(
                        modo_anterior, executavel=executavel
                    )
                    if dados_atuais is not None and versao_nova == versao_anterior:
                        return ResultadoIO(
                            alterou=False,
                            ja_gravado=True,
                            substituiu=False,
                            bytes_gravados=len(novos_dados),
                            versao_anterior=versao_anterior,
                            versao_nova=versao_nova,
                            modo_final=modo_anterior or modo_final,
                        )
                    gravar_atomico_em_dir(
                        pai_fd,
                        nome,
                        novos_dados,
                        modo_final=modo_final,
                        prazo_ns=destino.prazo_ns,
                    )
                    return ResultadoIO(
                        alterou=True,
                        ja_gravado=False,
                        substituiu=dados_atuais is not None,
                        bytes_gravados=len(novos_dados),
                        versao_anterior=versao_anterior,
                        versao_nova=versao_nova,
                        modo_final=modo_final,
                    )
                finally:
                    os.close(pai_fd)
        finally:
            os.close(bancada_fd)
    finally:
        os.close(raiz_fd)


def _varrer_dir_orfaos(
    dfd: int, prefixo: str, corte_mtime: float, removidos: list[str]
) -> None:
    for nome in os.listdir(dfd):
        if nome == ".git":
            continue
        try:
            st = os.stat(nome, dir_fd=dfd, follow_symlinks=False)
        except OSError:
            continue
        rel = f"{prefixo}/{nome}" if prefixo else nome
        if stat.S_ISDIR(st.st_mode):
            try:
                sub_fd = os.open(nome, _FLAGS_DIR_SEGURO, dir_fd=dfd)
            except OSError:
                continue
            try:
                _varrer_dir_orfaos(sub_fd, rel, corte_mtime, removidos)
            finally:
                os.close(sub_fd)
        elif (
            stat.S_ISREG(st.st_mode)
            and nome.startswith(PREFIXO_TMP)
            and nome.endswith(SUFIXO_TMP)
            and st.st_mtime < corte_mtime
        ):
            try:
                os.unlink(nome, dir_fd=dfd)
                removidos.append(rel)
            except OSError:
                continue


def varrer_temporarios_orfaos(
    raiz_bancada: Path,
    estado_dir: Path,
    idade_min_s: float,
    *,
    prazo_ns: int = 0,
) -> list[str]:
    """Remove `.pf-esc-*.tmp` mais velhos que `idade_min_s` sob a trava da bancada."""
    bancada_fd = os.open(str(raiz_bancada), _FLAGS_DIR_SEGURO)
    removidos: list[str] = []
    try:
        with trava_bancada(estado_dir, bancada_fd, prazo_ns=prazo_ns):
            corte = time.time() - idade_min_s
            _varrer_dir_orfaos(bancada_fd, "", corte, removidos)
    finally:
        os.close(bancada_fd)
    return removidos
