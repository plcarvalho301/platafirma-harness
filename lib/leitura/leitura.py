"""Leitura de arquivo por linha, com versão, encoding, formatos e travas (story #4342, DT 900)."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import stat
from collections import deque
from pathlib import Path
from typing import Any

from . import formatos as _formatos
from .morada import (
    eh_segredo,
    nega_morada_leitura,
    resolver_leitura_relativo,
    sob_fila as _sob_fila,
)

ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
VARREDURA_MAX = 256 * 1024 * 1024
BLOCO_HASH = 1024 * 1024
FIM = "fim do arquivo"
MODOS = ("texto", "sumario", "pagina", "visivel")
_RENDERIZAVEIS = frozenset(
    {_formatos.PDF, _formatos.PNG, _formatos.JPEG, _formatos.GIF, _formatos.WEBP}
)  # DT 898: o resto recusa modo pagina/visivel com sem_render (exit 2)

_ASSINATURAS = (
    (b"%PDF-", _formatos.PDF),
    (b"PK\x03\x04", _formatos.ZIP),
    (b"PK\x05\x06", _formatos.ZIP),
    (b"PK\x07\x08", _formatos.ZIP),
    (b"\x89PNG\r\n\x1a\n", _formatos.PNG),
    (b"\xff\xd8\xff", _formatos.JPEG),
    (b"GIF87a", _formatos.GIF),
    (b"GIF89a", _formatos.GIF),
    (b"\x7fELF", "application/x-elf"),
    (b"SQLite format 3\x00", "application/vnd.sqlite3"),
)

def envelope_erro(
    exit_code: int,
    falta: str,
    proximo: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {"exit_code": exit_code, "falta": falta}
    if proximo:
        out["proximo"] = proximo
    out.update(extras)
    return out


def _detectar_tipo(caminho: Path, cabeca: bytes) -> str:
    for sig, mime in _ASSINATURAS:
        if cabeca.startswith(sig):
            if mime == _formatos.ZIP:
                with caminho.open("rb") as fh:
                    return _formatos.tipo_do_zip(fh)
            return mime
    if b"\x00" in cabeca[:4096]:
        return "application/octet-stream"
    guess, _ = mimetypes.guess_type(str(caminho))
    return _formatos.tipo_texto(cabeca, guess or "text/plain")


def _decodificar_bloco(bruto: bytes, encoding_pedido: str | None) -> tuple[str, dict[str, Any]]:
    if encoding_pedido:
        try:
            txt = bruto.decode(encoding_pedido)
            return txt, {"decidido": encoding_pedido, "por": "pedido", "invalidos": 0, "julgado": True}
        except UnicodeDecodeError:
            txt = bruto.decode(encoding_pedido, errors="replace")
            return txt, {
                "decidido": encoding_pedido,
                "por": "pedido",
                "invalidos": txt.count("\ufffd"),
                "julgado": True,
            }
    try:
        return bruto.decode("utf-8"), {"decidido": "utf-8", "por": "estrito", "invalidos": 0, "julgado": True}
    except UnicodeDecodeError:
        try:
            return bruto.decode("cp1252"), {"decidido": "cp1252", "por": "fallback", "invalidos": 0, "julgado": True}
        except UnicodeDecodeError:
            txt = bruto.decode("utf-8", errors="replace")
            return txt, {
                "decidido": "utf-8",
                "por": "replace",
                "invalidos": txt.count("\ufffd"),
                "julgado": True,
            }


def _hash_e_cabeca(
    caminho: Path,
    tamanho: int,
    *,
    esperado_id: tuple[int, int] | None = None,
) -> tuple[str, bytes]:
    """Lê a cabeça e calcula versão em fluxo sem carregar o arquivo inteiro em RAM (DT 900)."""
    with caminho.open("rb") as fh:
        st = os.fstat(fh.fileno())
        if not stat.S_ISREG(st.st_mode):
            raise PermissionError("arquivo especial recusado")
        if esperado_id is not None and (st.st_dev, st.st_ino) != esperado_id:
            raise PermissionError("alvo mudou durante a abertura (TOCTOU)")
        cabeca = fh.read(8192)
        if tamanho > VARREDURA_MAX:
            marca = f"{st.st_size}:{st.st_mtime_ns}:{st.st_ino}".encode()
            return hashlib.sha256(marca).hexdigest()[:12], cabeca
        h = hashlib.sha256(cabeca)
        while True:
            bloco = fh.read(BLOCO_HASH)
            if not bloco:
                break
            h.update(bloco)
    return h.hexdigest()[:12], cabeca


def _parse_linhas(spec: str | None) -> tuple[int, int | None, int | None]:
    """Devolve (ini, fim_pedido, cauda) para 'a-b', 'a-', 'a' ou '-n' (cauda negativa, DT 900)."""
    if not spec or not spec.strip():
        return 1, None, None
    s = spec.strip()
    m_cauda = re.fullmatch(r"-\s*(\d+)", s)
    if m_cauda:
        return 1, None, max(1, int(m_cauda.group(1)))
    m_faixa = re.fullmatch(r"(\d+)\s*-\s*(\d*)", s)
    if m_faixa:
        ini = max(1, int(m_faixa.group(1)))
        fim = int(m_faixa.group(2)) if m_faixa.group(2) else None
        if fim is not None and fim < ini:
            fim = ini
        return ini, fim, None
    n = max(1, int(s))
    return n, n, None


def _ler_linhas_streaming(
    caminho: Path,
    linhas_spec: str | None,
    orcamento: int,
    encoding: str | None,
) -> tuple[str, dict[str, Any], int, int, int, int]:
    """Lê a faixa pedida em fluxo (incluindo cauda negativa -N) sem carregar o arquivo inteiro."""
    ini_req, fim_req, cauda = _parse_linhas(linhas_spec)
    selecionadas: list[bytes] = []
    bytes_acum = 0
    total_linhas = 0
    ini_real = ini_req
    fim_real = ini_req - 1

    if cauda is not None:
        janela: deque[tuple[int, bytes]] = deque(maxlen=cauda)
        with caminho.open("rb") as fh:
            for total_linhas, raw_ln in enumerate(fh, 1):
                janela.append((total_linhas, raw_ln))
        if not janela:
            return "", {"decidido": encoding or "utf-8", "por": "estrito", "invalidos": 0, "julgado": True}, 0, 0, 0, 0
        ini_real = janela[0][0]
        fim_real = ini_real - 1
        for num, raw_ln in janela:
            if selecionadas and bytes_acum + len(raw_ln) > orcamento:
                break
            selecionadas.append(raw_ln)
            bytes_acum += len(raw_ln)
            fim_real = num
    else:
        with caminho.open("rb") as fh:
            for total_linhas, raw_ln in enumerate(fh, 1):
                if total_linhas < ini_req:
                    continue
                if fim_req is not None and total_linhas > fim_req:
                    continue
                if selecionadas and bytes_acum + len(raw_ln) > orcamento:
                    continue
                if fim_real < total_linhas - 1 and selecionadas:
                    continue
                selecionadas.append(raw_ln)
                bytes_acum += len(raw_ln)
                fim_real = total_linhas
        if total_linhas == 0:
            ini_real, fim_real = 0, 0

    bruto_pagina = b"".join(selecionadas)
    conteudo, enc_meta = _decodificar_bloco(bruto_pagina, encoding)
    return conteudo, enc_meta, ini_real, fim_real, total_linhas, len(bruto_pagina)


def ler(
    caminho: str | Path,
    *,
    linhas: str | None = None,
    paginas: str | None = None,
    termo: str | None = None,
    modo: str = "texto",
    encoding: str | None = None,
    dpi: int = _formatos.DPI_PADRAO,
    max_bytes: int | None = None,
    versao: str | None = None,
    instancia: Path | None = None,
    bancada: Path | None = None,
    release: Path | None = None,
    pdp: Path | None = None,
    cadeira: str = "",
) -> dict[str, Any]:
    p = Path(caminho)
    if eh_segredo(p, instancia=instancia, pdp=pdp, release_dir=release):
        motivo = "segredo: fora do alcance da leitura de arquivo"
        return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
    if _sob_fila(p, instancia=instancia):
        motivo = "caminho sob a fila — use o verbo `fila`"
        return envelope_erro(4, motivo, 'fila(ato="status")', recusado=True, path=str(p), motivo=motivo)

    if not p.is_absolute():
        p_res, err_rel = resolver_leitura_relativo(
            str(caminho), bancada_dir=bancada, cadeira=cadeira
        )
        if err_rel or p_res is None:
            motivo = err_rel or "fora de morada"
            return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
        p = p_res
        if eh_segredo(p, instancia=instancia, pdp=pdp, release_dir=release):
            motivo = "segredo: fora do alcance da leitura de arquivo"
            return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
        if _sob_fila(p, instancia=instancia):
            motivo = "caminho sob a fila — use o verbo `fila`"
            return envelope_erro(4, motivo, 'fila(ato="status")', recusado=True, path=str(p), motivo=motivo)

    err_morada = nega_morada_leitura(
        p, instancia=instancia, bancada_dir=bancada, release_dir=release
    )
    if err_morada:
        return envelope_erro(4, err_morada, recusado=True, path=str(p), motivo=err_morada)

    if not p.exists():
        return envelope_erro(1, f"arquivo não encontrado: {p}", erro="nao_existe", caminho=str(p))

    if p.is_dir():
        entradas = [
            e
            for e in sorted(p.iterdir(), key=lambda x: x.name)
            if not eh_segredo(e, instancia=instancia, pdp=pdp, release_dir=release)
            and not _sob_fila(e, instancia=instancia)
            and nega_morada_leitura(
                e, instancia=instancia, bancada_dir=bancada, release_dir=release
            )
            is None
        ]
        if termo:
            t_low = termo.casefold()
            entradas = [e for e in entradas if t_low in e.name.casefold()]
        nomes = [e.name + ("/" if e.is_dir() else "") for e in entradas]
        return {
            "caminho": str(p),
            "tipo": "inode/directory",
            "entradas": nomes,
            "total": len(nomes),
            "conteudo": "\n".join(nomes),
        }

    if termo:
        return envelope_erro(
            2,
            "termo só se aplica a diretório: filtra a listagem pelo nome",
            f'ler_arquivo(caminho="{p}")',
            erro="termo só se aplica a diretório: filtra a listagem pelo nome",
            caminho=str(p),
        )

    alvo = p.resolve()
    st_alvo = os.stat(alvo)
    if not stat.S_ISREG(st_alvo.st_mode):
        motivo = "arquivo especial recusado"
        return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
    tamanho = st_alvo.st_size
    try:
        ver_atual, cabeca = _hash_e_cabeca(
            alvo, tamanho, esperado_id=(st_alvo.st_dev, st_alvo.st_ino)
        )
    except PermissionError as exc:
        return envelope_erro(4, str(exc), recusado=True, path=str(p), motivo=str(exc))
    mudou = {"de": versao, "para": ver_atual} if (versao and versao != ver_atual) else None
    prefixo_aviso = f"ARQUIVO MUDOU desde a versão {versao} · " if mudou else ""

    tipo = _detectar_tipo(p, cabeca)
    if modo in ("pagina", "visivel") and tipo not in _RENDERIZAVEIS:
        falta = f"modo={modo} só renderiza PDF ou imagem; {tipo} sai em modo texto"
        return envelope_erro(
            2,
            falta,
            f'ler_arquivo(caminho="{p}")',
            erro=falta,
            motivo="sem_render",
            caminho=str(p),
            tipo=tipo,
        )
    if tipo in _formatos.LEITORES and tipo != _formatos.HTML and tipo != _formatos.MHTML:
        try:
            extra = _formatos.extrair_texto_formato(p, tipo, paginas=paginas, modo=modo, dpi=dpi)
        except _formatos.ErroDescompressao as e:
            return envelope_erro(
                2,
                f"descompressão recusada ({e})",
                recusado=True,
                motivo="descompressao",
                caminho=str(p),
                tipo=tipo,
            )
        if "erro" in extra:
            return envelope_erro(2, extra["erro"], caminho=str(p), tipo=tipo)
        out_fmt: dict[str, Any] = {
            "caminho": str(p),
            "tipo": tipo,
            "bytes_total": tamanho,
            "versao": ver_atual,
            **extra,
        }
        if mudou:
            out_fmt["mudou"] = mudou
            if "cabecalho" in out_fmt:
                out_fmt["cabecalho"] = prefixo_aviso + out_fmt["cabecalho"]
        return out_fmt
    if tipo == "application/octet-stream" or tipo.startswith("application/x-elf"):
        return envelope_erro(1, f"binário sem leitor ({tipo})", erro="sem_leitor", caminho=str(p), tipo=tipo)

    orcamento = max(1024, min(int(max_bytes or ORCAMENTO_PADRAO), ORCAMENTO_MAX))
    try:
        conteudo, enc_meta, ini, fim_real, total_linhas, bytes_acum = _ler_linhas_streaming(
            p, linhas, orcamento, encoding
        )
    except ValueError:
        return envelope_erro(
            2,
            f'linhas={linhas!r}: use "a-b", "a-" ou "-n" (base 1)',
            f'ler_arquivo(caminho="{p}", linhas="1-")',
            caminho=str(p),
        )

    chegou_fim = fim_real >= total_linhas
    proximo = (
        FIM
        if chegou_fim
        else f'ler_arquivo(caminho="{p}", linhas="{fim_real + 1}-", versao="{ver_atual}")'
    )
    out: dict[str, Any] = {
        "cabecalho": (
            f"{prefixo_aviso}{p.name} · {tipo} · linhas {ini}–{fim_real} de {total_linhas}"
            f" · {bytes_acum} de {tamanho} bytes · {enc_meta['decidido']} · versão {ver_atual}"
        ),
        "conteudo": conteudo,
        "proximo": proximo,
        "caminho": str(p),
        "bytes_total": tamanho,
        "versao": ver_atual,
        "encoding": enc_meta,
        "tipo": tipo,
        "linhas": [ini, fim_real],
        "linhas_total": total_linhas,
    }
    if mudou:
        out["mudou"] = mudou
    if not chegou_fim:
        out["proximo_args"] = {
            "caminho": str(p),
            "linhas": f"{fim_real + 1}-",
            "versao": ver_atual,
        }
    return out
