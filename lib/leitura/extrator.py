"""Extrator isolado de formatos binários e compostos via SCM_RIGHTS (story #4442, t4).

Roda em instância dedicada (unidade modelo `leitor-extrator@.service` na conta
`pf-leitor-extrator` ou subprocesso confinado com ambiente limpo e rlimits) recebendo
apenas o descritor de arquivo por `SCM_RIGHTS` sobre soquete UNIX, sem rede nem
credenciais do leitor.
"""
from __future__ import annotations

import array
import base64
import hashlib
import io
import json
import os
import resource
import shutil
import signal
import socket
import struct
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import formatos as F
from .tipos import Recusa

_LIB_DIR = Path(__file__).resolve().parents[1]
_CABECA_QUADRO = struct.Struct(">I")
_TAM_CABECA = 4
_MOBI_MIN_BYTES = 68
_MAX_QUADRO_PEDIDO = 1 * 1024 * 1024        # 1 MiB para envelope JSON de pedido
_MAX_QUADRO_RESPOSTA = 32 * 1024 * 1024     # 32 MiB para envelope JSON de resposta
_BLOCO_SOCKET = 65_536
_PRAZO_PADRAO_MS = 10_000
_RLIMIT_CPU_PADRAO_S = 10
_MSG_CMSG_CLOEXEC = getattr(socket, "MSG_CMSG_CLOEXEC", 0)


class ErroExtrator(Exception):
    """Recusa estruturada emitida pelo extrator isolado ou seu cliente."""

    def __init__(self, recusa: Recusa) -> None:
        self.recusa = recusa
        self.saida = recusa.saida
        super().__init__(recusa.codigo)


def _resposta_ok(tipo: str, unidade: str, **campos: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "tipo": tipo,
        "unidade": unidade,
        "conteudo": campos.get("conteudo"),
        "imagens": campos.get("imagens"),
        "parcial": bool(campos.get("parcial", False)),
        "avisos": list(campos.get("avisos") or ()),
        "sem_texto": list(campos.get("sem_texto") or ()),
        "paginas": campos.get("paginas"),
        "paginas_total": campos.get("paginas_total"),
    }


def _recusa_tempo_esgotado(chave: str) -> Recusa:
    return Recusa(
        saida=5,
        codigo="tempo-esgotado",
        onde="extrator",
        recebido=chave,
        regra="prazo-do-extrator",
        cura="extração excedeu o prazo da chamada; tente um recorte menor",
        proximo=f"busca ler {chave} --paginas 1-5" if chave else "",
    )


def _fechar_silencioso(fd: int) -> None:
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            pass


# ------------------------------------------------------------------ enquadramento + SCM_RIGHTS
def _ler_exato(sock: socket.socket, n: int) -> bytes:
    partes: list[bytes] = []
    falta = n
    while falta > 0:
        bloco = sock.recv(min(falta, _BLOCO_SOCKET))
        if not bloco:
            raise EOFError("conexão encerrada antes do fim do quadro")
        partes.append(bloco)
        falta -= len(bloco)
    return b"".join(partes)


def enviar_pedido_com_fd(sock: socket.socket, pedido: Mapping[str, Any], fd: int) -> None:
    """Envia quadro JSON + descritor de arquivo `fd` via `SCM_RIGHTS` (TLPI cap. 61)."""
    corpo = json.dumps(dict(pedido), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(corpo) > _MAX_QUADRO_PEDIDO:
        raise ValueError("pedido excede o teto de enquadramento")
    cabeca = _CABECA_QUADRO.pack(len(corpo))
    fds = array.array("i", [fd])
    sock.sendmsg([cabeca], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])
    sock.sendall(corpo)


def _extrair_unico_fd(ancdata: list[tuple[int, int, bytes]]) -> int:
    fds = array.array("i")
    for cmsg_level, cmsg_type, cmsg_data in ancdata:
        if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
            n_bytes = len(cmsg_data) - (len(cmsg_data) % fds.itemsize)
            fds.frombytes(cmsg_data[:n_bytes])
    if not fds:
        raise ValueError("descritor ausente na mensagem SCM_RIGHTS")
    for extra in fds[1:]:
        _fechar_silencioso(extra)
    return fds[0]


def receber_pedido_com_fd(sock: socket.socket) -> tuple[dict[str, Any], int]:
    """Recebe quadro JSON + descritor de arquivo único via `SCM_RIGHTS`."""
    tam_cmsg = socket.CMSG_SPACE(array.array("i").itemsize * _TAM_CABECA)
    dados, ancdata, _flags, _addr = sock.recvmsg(_TAM_CABECA, tam_cmsg, _MSG_CMSG_CLOEXEC)
    fd_recebido = _extrair_unico_fd(ancdata)
    try:
        if len(dados) < _TAM_CABECA:
            dados += _ler_exato(sock, _TAM_CABECA - len(dados))
        (tamanho,) = _CABECA_QUADRO.unpack(dados)
        if tamanho > _MAX_QUADRO_PEDIDO:
            raise ValueError("quadro de pedido acima do teto")
        pedido = json.loads(_ler_exato(sock, tamanho).decode("utf-8"))
        if not isinstance(pedido, dict):
            raise TypeError("pedido JSON deve ser objeto")
        return pedido, fd_recebido
    except Exception:
        _fechar_silencioso(fd_recebido)
        raise


def enviar_resposta(sock: socket.socket, resposta: Mapping[str, Any]) -> None:
    """Envia quadro JSON de resposta pelo soquete."""
    corpo = json.dumps(dict(resposta), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sock.sendall(_CABECA_QUADRO.pack(len(corpo)) + corpo)


def receber_resposta(sock: socket.socket) -> dict[str, Any]:
    """Recebe quadro JSON de resposta pelo soquete."""
    (tamanho,) = _CABECA_QUADRO.unpack(_ler_exato(sock, _TAM_CABECA))
    if tamanho > _MAX_QUADRO_RESPOSTA:
        raise ValueError("quadro de resposta acima do teto")
    obj = json.loads(_ler_exato(sock, tamanho).decode("utf-8"))
    if not isinstance(obj, dict):
        raise TypeError("resposta JSON inválida")
    return obj


# ------------------------------------------------------------------ núcleo de extração sobre fd
def _validar_caminho_membro(membro: str) -> None:
    partes = membro.split("/") if membro else []
    if not membro or membro.startswith("/") or "\x00" in membro or any(p in ("", "..") for p in partes):
        raise ErroExtrator(
            Recusa(
                saida=2,
                codigo="chave-mal-formada",
                onde="membro",
                recebido=membro,
                regra="seletor-membro-posix-relativo",
                cura="use caminho relativo POSIX sem '/' inicial, '..' nem byte nulo",
                proximo="",
            )
        )


def _detectar_mime_cabeca(cabeca: bytes, fh: io.BufferedIOBase) -> str:
    if cabeca.startswith(b"%PDF-"):
        return F.PDF
    if cabeca.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return F.tipo_do_zip(fh)
    if cabeca.startswith(b"\x1f\x8b"):
        return F.GZIP
    if len(cabeca) >= _MOBI_MIN_BYTES and cabeca[60:68] == b"BOOKMOBI":
        return F.MOBI
    if cabeca.startswith(b"\x89PNG\r\n\x1a\n"):
        return F.PNG
    if cabeca.startswith(b"\xff\xd8\xff"):
        return F.JPEG
    if cabeca.startswith((b"GIF87a", b"GIF89a")):
        return F.GIF
    if F.e_webp(cabeca):
        return F.WEBP
    tipo_txt = F.tipo_texto(cabeca, "text/plain")
    if tipo_txt in (F.HTML, F.MHTML):
        return tipo_txt
    return "application/octet-stream"


def _faixa_paginas(
    total: int,
    paginas: list[int | None] | tuple[int, int | None] | None,
    cauda_paginas: int | None,
    chave: str,
) -> tuple[int, int]:
    if total <= 0:
        return 1, 0
    if cauda_paginas is not None:
        return max(1, total - int(cauda_paginas) + 1), total
    if paginas is not None:
        ini = int(paginas[0])
        fim = total if paginas[1] is None else min(int(paginas[1]), total)
        if ini > total:
            cauda = max(1, total - 4)
            raise ErroExtrator(
                Recusa(
                    saida=1,
                    codigo="pagina-alem-do-fim",
                    onde="--paginas",
                    recebido=f"{ini}-{paginas[1] or ''}",
                    regra="paginas-dentro-do-total",
                    cura=f"o documento tem {total} páginas (paginas_total={total})",
                    proximo=f"busca ler {chave} --paginas {cauda}-{total}" if chave else "",
                )
            )
        return ini, max(ini, fim)
    return 1, total


def _extrair_gzip(fh: io.BufferedIOBase, tamanho_comprimido: int) -> dict[str, Any]:
    dados = F.ler_gzip_seguro(
        fh,
        limite=F.MEMBRO_MAX,
        razao_max=F.RAZAO_COMPRESSAO_MAX,
        tamanho_comprimido=tamanho_comprimido,
    )
    if F.eh_assinatura_pacote(dados[:8]):
        raise F.ErroDescompressao("aninhamento de pacote comprimido além de 1 nível recusado")
    return _resposta_ok(
        tipo=F.GZIP,
        unidade="nenhuma",
        conteudo=dados.decode("utf-8", errors="replace"),
    )


def _extrair_membro_pacote(doc: F.Documento, membro: str, chave: str) -> dict[str, Any]:
    _validar_caminho_membro(membro)
    try:
        bruto_m = F.membro_de(doc, membro, nivel_aninhamento=1)
    except KeyError:
        raise ErroExtrator(
            Recusa(
                saida=1,
                codigo="membro-inexistente",
                onde="membro",
                recebido=membro,
                regra="membro-no-pacote",
                cura=f"o membro {membro!r} não existe no pacote",
                proximo=f"busca ler {chave}" if chave else "",
            )
        ) from None
    return _resposta_ok(
        tipo=doc.tipo,
        unidade="nenhuma",
        conteudo=bruto_m.decode("utf-8", errors="replace"),
        avisos=doc.avisos,
    )


def _extrair_modo_pagina(
    doc: F.Documento,
    ini: int,
    fim: int,
    *,
    dpi: int,
) -> dict[str, Any]:
    if not doc.render:
        raise ErroExtrator(
            Recusa(
                saida=2,
                codigo="combinacao-invalida",
                onde="--modo",
                recebido=doc.tipo,
                regra="modo-pagina-exige-renderizador",
                cura="use --modo texto para formatos sem rasterizador de página",
                proximo="",
            )
        )
    imagens: list[dict[str, Any]] = []
    avisos = list(doc.avisos)
    acumulado = 0
    ultimo = ini - 1
    for p in range(ini, fim + 1):
        img_bytes, mime, extra = doc.imagem(p, dpi=dpi)
        if img_bytes is None:
            continue
        if imagens and (acumulado + len(img_bytes)) > F.IMAGEM_TETO:
            avisos.append("teto_de_imagem_atingido")
            break
        acumulado += len(img_bytes)
        dims = extra.get("dimensoes") or (0, 0)
        imagens.append(
            {
                "pagina": p,
                "mime": mime,
                "largura": int(dims[0]),
                "altura": int(dims[1]),
                "sha256": hashlib.sha256(img_bytes).hexdigest(),
                "base64": base64.b64encode(img_bytes).decode("ascii"),
            }
        )
        ultimo = p
    return _resposta_ok(
        tipo=doc.tipo,
        unidade=doc.unidade,
        imagens=imagens,
        parcial=ultimo < doc.n,
        avisos=avisos,
        paginas=[ini, ultimo] if imagens else None,
        paginas_total=doc.n,
    )


def _extrair_unidades_texto(doc: F.Documento, ini: int, fim: int, chave: str) -> dict[str, Any]:
    partes: list[str] = []
    erros_pagina = 0
    pedidas = max(0, fim - ini + 1)
    for p in range(ini, fim + 1):
        try:
            txt = doc.texto(p)
        except F.ErroDescompressao:
            raise
        except Exception as exc:  # noqa: BLE001
            erros_pagina += 1
            if p not in doc.sem_texto:
                doc.sem_texto.append(p)
            doc.avisos.append(f"pagina_{p}_erro_extracao: {type(exc).__name__}")
            continue
        if txt:
            partes.append(txt)

    if pedidas > 0 and erros_pagina == pedidas and not partes:
        raise ErroExtrator(
            Recusa(
                saida=5,
                codigo="extracao-incompleta",
                onde="extrator",
                recebido=doc.tipo,
                regra="ao-menos-uma-pagina-extraida",
                cura="nenhuma página pedida pôde ser extraída do documento",
                proximo=f"busca ler {chave} --paginas {ini}-{ini}" if chave else "",
            )
        )

    parcial = bool(doc.truncado) or (doc.unidade != "nenhuma" and fim < doc.n)
    return _resposta_ok(
        tipo=doc.tipo,
        unidade=doc.unidade,
        conteudo="\n".join(partes),
        parcial=parcial,
        avisos=doc.avisos,
        sem_texto=sorted(set(doc.sem_texto)),
        paginas=[ini, fim] if doc.unidade != "nenhuma" and doc.n > 0 else None,
        paginas_total=doc.n if doc.unidade != "nenhuma" else None,
    )


def _extrair_documento(
    fh: io.BufferedIOBase,
    tipo: str,
    pedido: Mapping[str, Any],
) -> dict[str, Any]:
    chave = str(pedido.get("chave") or "")
    modo = str(pedido.get("modo") or "texto")
    membro = pedido.get("membro")
    dpi = int(pedido.get("dpi") or F.DPI_PADRAO)
    encoding = pedido.get("encoding")

    doc = F.abre(tipo, fh=fh, encoding=encoding)
    try:
        if membro is not None:
            return _extrair_membro_pacote(doc, str(membro), chave)
        ini, fim = _faixa_paginas(doc.n, pedido.get("paginas"), pedido.get("cauda_paginas"), chave)
        if modo == "pagina":
            return _extrair_modo_pagina(doc, ini, fim, dpi=dpi)
        if doc.tipo == F.ZIP and hasattr(doc, "listar_membros_detalhados"):
            linhas = [
                f"{nome}\t{bruto}\t{comp}\t{razao:.2f}x"
                for nome, bruto, comp, razao in doc.listar_membros_detalhados()
            ]
            return _resposta_ok(
                tipo=doc.tipo,
                unidade=doc.unidade,
                conteudo="\n".join(linhas) + ("\n" if linhas else ""),
                avisos=doc.avisos,
            )
        return _extrair_unidades_texto(doc, ini, fim, chave)
    finally:
        doc.fecha()


def extrair_de_fd(fd: int, pedido: Mapping[str, Any]) -> dict[str, Any]:
    """Executa a extração sobre o descritor já aberto (sem abrir caminho por nome)."""
    dup_fd = os.dup(fd)
    try:
        st = os.fstat(dup_fd)
        os.lseek(dup_fd, 0, os.SEEK_SET)
        with os.fdopen(dup_fd, "rb", closefd=True) as fh:
            dup_fd = -1
            cabeca = fh.read(8192)
            fh.seek(0)
            tipo = _detectar_mime_cabeca(cabeca, fh)
            fh.seek(0)
            if tipo == "application/octet-stream":
                raise ErroExtrator(
                    Recusa(
                        saida=1,
                        codigo="formato-sem-leitor",
                        onde="extrator",
                        recebido=tipo,
                        regra="formato-suportado",
                        cura=f"formato binário sem extrator cadastrado ({st.st_size} bytes)",
                        proximo="",
                    )
                )
            if tipo == F.GZIP:
                return _extrair_gzip(fh, st.st_size)
            return _extrair_documento(fh, tipo, pedido)
    except ErroExtrator as exc:
        return {"ok": False, "saida": exc.saida, "recusa": exc.recusa.campos()}
    except F.ErroDescompressao as exc:
        rec = Recusa(
            saida=2,
            codigo="descompressao-recusada",
            onde="extrator",
            recebido=str(pedido.get("chave") or ""),
            regra="limites-descompressao-e-xml",
            cura=str(exc),
            proximo="",
        )
        return {"ok": False, "saida": 2, "recusa": rec.campos()}
    except MemoryError:
        rec = Recusa(
            saida=5,
            codigo="falta-de-memoria",
            onde="extrator",
            recebido=str(pedido.get("chave") or ""),
            regra="teto-memoria-extrator",
            cura="extração excedeu o teto de memória; tente um recorte menor",
            proximo=f"busca ler {pedido.get('chave')} --paginas 1-5" if pedido.get("chave") else "",
        )
        return {"ok": False, "saida": 5, "recusa": rec.campos()}
    except Exception as exc:  # noqa: BLE001
        rec = Recusa(
            saida=5,
            codigo="extracao-incompleta",
            onde="extrator",
            recebido=type(exc).__name__,
            regra="extracao-isolada",
            cura=f"falha ao extrair documento: {exc}",
            proximo="",
        )
        return {"ok": False, "saida": 5, "recusa": rec.campos()}
    finally:
        _fechar_silencioso(dup_fd)


# ------------------------------------------------------------------ servidor de conexão única
def servir_conexao(conn: socket.socket) -> None:
    """Atende uma única conexão no protocolo SCM_RIGHTS (modelo `Accept=yes`)."""
    fd = -1
    try:
        pedido, fd = receber_pedido_com_fd(conn)
        resp = extrair_de_fd(fd, pedido)
        enviar_resposta(conn, resp)
    except Exception as exc:  # noqa: BLE001
        try:
            rec = Recusa(
                saida=5,
                codigo="extracao-incompleta",
                onde="extrator",
                recebido=type(exc).__name__,
                regra="protocolo-extrator",
                cura=f"falha no atendimento do extrator: {exc}",
                proximo="",
            )
            enviar_resposta(conn, {"ok": False, "saida": 5, "recusa": rec.campos()})
        except OSError:
            pass
    finally:
        _fechar_silencioso(fd)


# ------------------------------------------------------------------ clientes do extrator
def _interpretar_resposta(resp: Mapping[str, Any]) -> dict[str, Any]:
    if resp.get("ok"):
        return dict(resp)
    campos = resp.get("recusa") if isinstance(resp.get("recusa"), dict) else {}
    saida = int(resp.get("saida") or 5)
    raise ErroExtrator(
        Recusa(
            saida=saida,
            codigo=str(campos.get("codigo") or "extracao-incompleta"),
            onde=str(campos.get("onde") or "extrator"),
            recebido=str(campos.get("recebido") or ""),
            regra=str(campos.get("regra") or "extracao-isolada"),
            cura=str(campos.get("cura") or "extração recusada"),
            proximo=str(campos.get("proximo") or ""),
        )
    )


def extrair_via_socket(
    socket_path: str | Path,
    fd: int,
    pedido: Mapping[str, Any],
    *,
    prazo_ms: int = _PRAZO_PADRAO_MS,
) -> dict[str, Any]:
    """Envia `fd` + `pedido` ao soquete do extrator (`leitor-extrator.socket`)."""
    timeout_s = max(0.05, prazo_ms / 1000.0)
    chave = str(pedido.get("chave") or "")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM | getattr(socket, "SOCK_CLOEXEC", 0))
    sock.settimeout(timeout_s)
    try:
        try:
            sock.connect(str(socket_path))
        except (FileNotFoundError, ConnectionRefusedError, PermissionError) as exc:
            raise ErroExtrator(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="extrator",
                    recebido=str(socket_path),
                    regra="soquete-extrator-disponivel",
                    cura=f"soquete do extrator indisponível: {exc}",
                    proximo="",
                )
            ) from None
        enviar_pedido_com_fd(sock, pedido, fd)
        resp = receber_resposta(sock)
        return _interpretar_resposta(resp)
    except TimeoutError:
        raise ErroExtrator(_recusa_tempo_esgotado(chave)) from None
    except (EOFError, BrokenPipeError, ConnectionResetError):
        raise ErroExtrator(
            Recusa(
                saida=5,
                codigo="falta-de-memoria",
                onde="extrator",
                recebido=chave,
                regra="teto-memoria-extrator",
                cura="instância do extrator encerrou abruptamente (limite de memória ou sinal)",
                proximo=f"busca ler {chave} --paginas 1-5" if chave else "",
            )
        ) from None
    finally:
        sock.close()


def _aplicar_rlimits(limite_memoria_bytes: int | None, limite_cpu_s: int) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    if limite_cpu_s > 0:
        resource.setrlimit(resource.RLIMIT_CPU, (limite_cpu_s, limite_cpu_s))
    if limite_memoria_bytes is not None and limite_memoria_bytes > 0:
        resource.setrlimit(resource.RLIMIT_AS, (limite_memoria_bytes, limite_memoria_bytes))


def extrair_em_subprocesso(
    fd: int,
    pedido: Mapping[str, Any],
    *,
    prazo_ms: int = _PRAZO_PADRAO_MS,
    limite_memoria_bytes: int | None = None,
    limite_cpu_s: int = _RLIMIT_CPU_PADRAO_S,
) -> dict[str, Any]:
    """Executa o extrator em subprocesso isolado sem ambiente herdado, via socketpair + SCM_RIGHTS."""
    pai, filho = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    timeout_s = max(0.05, prazo_ms / 1000.0)
    chave = str(pedido.get("chave") or "")
    env_limpo = {
        "PYTHONPATH": str(_LIB_DIR),
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
    }
    proc: subprocess.Popen[bytes] | None = None
    try:
        filho_fd = filho.fileno()
        os.set_inheritable(filho_fd, True)
        cmd_py = [
            sys.executable,
            "-m",
            "leitura.extrator",
            "--fd-socket",
            str(filho_fd),
        ]
        prlimit_bin = shutil.which("prlimit")
        if prlimit_bin:
            cmd = [prlimit_bin, "--core=0", "--fsize=0"]
            if limite_cpu_s > 0:
                cmd.append(f"--cpu={limite_cpu_s}")
            if limite_memoria_bytes is not None and limite_memoria_bytes > 0:
                cmd.append(f"--as={limite_memoria_bytes}")
            cmd.extend(["--", *cmd_py])
        else:
            cmd = [*cmd_py, "--rlimit-cpu", str(limite_cpu_s)]
            if limite_memoria_bytes is not None and limite_memoria_bytes > 0:
                cmd.extend(["--rlimit-as", str(limite_memoria_bytes)])
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env_limpo,
            close_fds=True,
            pass_fds=(filho_fd,),
        )
        filho.close()
        pai.settimeout(timeout_s)
        enviar_pedido_com_fd(pai, pedido, fd)
        resp = receber_resposta(pai)
        proc.communicate(timeout=1.0)
        return _interpretar_resposta(resp)
    except TimeoutError:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=1.0)
        raise ErroExtrator(_recusa_tempo_esgotado(chave)) from None
    except (EOFError, BrokenPipeError, ConnectionResetError):
        rc = proc.wait(timeout=1.0) if proc is not None else -signal.SIGKILL
        codigo = "falta-de-memoria" if rc in (-signal.SIGKILL, -signal.SIGSEGV) else "morto-por-sinal"
        raise ErroExtrator(
            Recusa(
                saida=5,
                codigo=codigo,
                onde="extrator",
                recebido=f"returncode={rc}",
                regra="isolacao-do-extrator",
                cura="o extrator encerrou por limite de recurso ou sinal; tente recorte menor",
                proximo=f"busca ler {chave} --paginas 1-5" if chave else "",
            )
        ) from None
    finally:
        pai.close()
        try:
            filho.close()
        except OSError:
            pass
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=1.0)


def _parsear_args_cli(args: list[str]) -> tuple[int, int | None, int]:
    fd_sock: int | None = None
    limite_as: int | None = None
    limite_cpu = 0
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--fd-socket" and i + 1 < len(args):
            fd_sock = int(args[i + 1])
            i += 2
        elif tok == "--rlimit-as" and i + 1 < len(args):
            limite_as = int(args[i + 1])
            i += 2
        elif tok == "--rlimit-cpu" and i + 1 < len(args):
            limite_cpu = int(args[i + 1])
            i += 2
        else:
            i += 1
    if fd_sock is None:
        fd_sock = 3 if os.environ.get("LISTEN_FDS") == "1" else 0
    return fd_sock, limite_as, limite_cpu


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada de `leitor-extrator@.service` (systemd Accept=yes) ou `--fd-socket`."""
    args = sys.argv[1:] if argv is None else argv
    fd_sock, limite_as, limite_cpu = _parsear_args_cli(args)
    if limite_cpu > 0 or limite_as is not None:
        _aplicar_rlimits(limite_as, limite_cpu)
    conn = socket.socket(fileno=fd_sock)
    try:
        servir_conexao(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
