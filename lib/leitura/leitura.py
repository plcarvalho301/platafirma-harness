"""leitura.py — a leitura de arquivo da porta: `ler_arquivo` (spec ler-arquivo, DT 919).

Puro no núcleo (`le`): não importa FastMCP, não fala com a rede, não grava auditoria.
`ler` envolve `le` com o confinamento de morada, segredos e fila (`morada.py`, achado 921)
e a gramática `caminho!membro` para membros de ZIP/EPUB/OOXML.
"""
from __future__ import annotations

import ast
import bisect
import codecs
import hashlib
import io
import json
import os
import re
import stat as _stat
import threading
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from typing import Any

from . import formatos as _formatos
from .morada import (
    eh_segredo,
    nega_morada_leitura,
    resolver_leitura_relativo,
)
from .morada import (
    sob_fila as _sob_fila,
)

# --- réguas da spec (§13.1) --------------------------------------------------------------------
ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
VARREDURA_MAX = 256 * 1024 * 1024    # acima disto, versão por stat e varredura até a página
UTF16_MAX = 16 * 1024 * 1024         # transcodificação em memória de UTF-16/32
SUMARIO_MAX = 8 * 1024 * 1024
MARCO = 1_024                        # um marco de posição a cada MARCO linhas
INDICES_MAX = 64                     # entradas do cache de índice
CACHE_EXTRA_BYTES_MAX = 32 * 1024 * 1024  # orçamento global de texto extraído em Indice.extra (DT 899)
CABECA_TIPO = 8_192                  # bytes que decidem o tipo real
LA_TEM_MAX = 40
# --- réguas de implementação, não de contrato --------------------------------------------------
BLOCO = 1024 * 1024                  # leitura da varredura (§7.1.1)
PASSO = 1024                         # leitura de quem anda linha a linha
POSICOES_MAX = 4_096                 # posições aprendidas por índice
_SEM_CAMADA_LISTA_MAX = 8
_UTF8_CONT_MIN = 0x80
_UTF8_CONT_MAX = 0xBF
_UTF8_4B = 0xF0
_UTF8_3B = 0xE0
_UTF8_2B = 0xC0
_UTF8_CONT_MAX_PASSOS = 3

FIM = "fim do arquivo"
TOOL = "ler_arquivo"
MODOS = ("texto", "sumario", "pagina", "visivel")
ENC_BINARIO = {"decidido": "utf-8", "por": "binario", "invalidos": 0, "julgado": True}

_NL = re.compile(b"\n")
_SURROGATO = re.compile("[\udc80-\udcff]")       # byte inválido sob surrogateescape
_ASCII = bytes(range(128))
_CP1252_INDEFINIDOS = (b"\x81", b"\x8d", b"\x8f", b"\x90", b"\x9d")

# Assinaturas de formato binário (§7.2.1). A extensão nunca decide; só dá nome ao tipo.
_ASSINATURAS = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),
    (b"PK\x07\x08", "application/zip"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"\x1f\x8b", "application/gzip"),
    (b"\x7fELF", "application/x-elf"),
    (b"SQLite format 3\x00", "application/vnd.sqlite3"),
)
_MOBI_MARCA = (60, b"BOOKMOBI")
_ESCRITORIO = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".epub": "application/epub+zip",
}
# UTF-32 antes de UTF-16: o BOM de UTF-32 LE começa com o de UTF-16 LE.
_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)
_TIPO_POR_EXT = {
    ".py": "text/x-python",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".sh": "text/x-shellscript",
    ".sql": "application/sql",
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".csv": "text/csv",
    ".xml": "application/xml",
    ".php": "text/x-php",
    ".htm": "text/html",
    ".xhtml": "text/html",
    ".mhtml": _formatos.MHTML,
    ".mht": _formatos.MHTML,
}
_ANALISADOR = {
    "text/markdown": "markdown",
    "text/x-python": "python",
    "application/json": "json",
}


# ============================================================== índice e versão (§7.1)
@dataclass
class Indice:
    """O que a varredura tira do arquivo, e o que as páginas servidas ensinam depois."""

    versao: str
    tamanho: int
    linhas_total: int | None          # None: varredura parou antes do fim (versão por stat)
    marcos: list[int]                 # marcos[k] = byte onde começa a linha k*MARCO + 1
    multibyte: int                    # sequências UTF-8 multibyte válidas
    invalidos: int                    # bytes que não decodificam em UTF-8
    cp1252_invalidos: int             # bytes sem caractere em cp1252
    cabeca: bytes                     # os primeiros CABECA_TIPO bytes
    por_stat: bool = False
    inicios: dict = field(default_factory=dict)      # linha -> byte em que ela começa
    pontos: dict = field(default_factory=dict)       # byte -> linha que contém o byte
    extra: dict = field(default_factory=dict)        # sumário e contagens por encoding pedido
    dados: bytes | None = None        # só na volta da varredura com `guarda`; nunca no cache

    def aprende(self, linha: int | None, byte: int, *, inicio: bool) -> None:
        """Toda página servida diz onde a próxima começa: a continuação não relê nada."""
        if linha is None:
            return
        with _TRAVA:
            if inicio:
                if len(self.inicios) >= POSICOES_MAX:
                    self.inicios.pop(next(iter(self.inicios)))
                self.inicios[linha] = byte
            if len(self.pontos) >= POSICOES_MAX:
                self.pontos.pop(next(iter(self.pontos)))
            self.pontos[byte] = linha


def varre(fh: Any, ate: int | None = None, *, guarda: bool = False) -> Indice:
    """Uma passada em blocos de 1 MiB: sha256, linhas, marcos e validação de UTF-8."""
    h = hashlib.sha256()
    dec = codecs.getincrementaldecoder("utf-8")("surrogateescape")
    nl = pos = multibyte = invalidos = cp_inv = 0
    marcos = [0]
    proximo = MARCO
    cabeca = ultimo = b""
    partes = [] if guarda else None
    parcial = False
    while True:
        blk = fh.read(BLOCO)
        if not blk:
            break
        if not pos:
            cabeca = blk[:CABECA_TIPO]
        if partes is not None:
            partes.append(blk)
        h.update(blk)
        n = blk.count(b"\n")
        if nl + n >= proximo:
            for m in islice(_NL.finditer(blk), proximo - nl - 1, None, MARCO):
                marcos.append(pos + m.end())
            proximo = ((nl + n) // MARCO + 1) * MARCO
        nl += n
        if not (blk.isascii() and not dec.getstate()[0]):
            s = dec.decode(blk)
            inv = len(_SURROGATO.findall(s)) if _SURROGATO.search(s) else 0
            ascii_n = len(blk) - len(blk.translate(None, _ASCII))
            multibyte += len(s) - ascii_n - inv
            invalidos += inv
            cp_inv += sum(blk.count(b) for b in _CP1252_INDEFINIDOS)
        pos += len(blk)
        ultimo = blk[-1:]
        if ate is not None and nl + 1 >= ate:
            parcial = True
            break
    invalidos += len(dec.decode(b"", final=True))
    total = None if parcial else nl + (1 if pos and ultimo != b"\n" else 0)
    return Indice(
        versao=h.hexdigest()[:12],
        tamanho=pos,
        linhas_total=total,
        marcos=marcos,
        multibyte=multibyte,
        invalidos=invalidos,
        cp1252_invalidos=cp_inv,
        cabeca=cabeca,
        por_stat=parcial,
        dados=b"".join(partes) if partes is not None else None,
    )


_INDICES: OrderedDict = OrderedDict()
_EXTRA_LRU: OrderedDict[tuple[int, Any], tuple[Indice, Any, int]] = OrderedDict()
_EXTRA_ESTADO = {"bytes": 0}
_TRAVA = threading.Lock()


def esvazia_cache() -> None:
    """Para o bench e os testes: a próxima leitura de cada arquivo é a frio."""
    with _TRAVA:
        _INDICES.clear()
        _EXTRA_LRU.clear()
        _EXTRA_ESTADO["bytes"] = 0


def _extra_obter(idx: Indice, chave: Any) -> Any:
    """Leitura thread-safe de `idx.extra` sob `_TRAVA` (DT 899)."""
    with _TRAVA:
        val = idx.extra.get(chave)
        if val is not None:
            k = (id(idx), chave)
            if k in _EXTRA_LRU:
                _EXTRA_LRU.move_to_end(k)
        return val


def _extra_gravar(idx: Indice, chave: Any, valor: Any, custo_bytes: int = 64) -> Any:
    """Gravação thread-safe em `idx.extra` com orçamento global `CACHE_EXTRA_BYTES_MAX` (DT 899)."""
    k = (id(idx), chave)
    with _TRAVA:
        if k in _EXTRA_LRU:
            _, _, antigo = _EXTRA_LRU.pop(k)
            _EXTRA_ESTADO["bytes"] = max(0, _EXTRA_ESTADO["bytes"] - antigo)
        idx.extra[chave] = valor
        _EXTRA_LRU[k] = (idx, chave, custo_bytes)
        _EXTRA_ESTADO["bytes"] += custo_bytes
        while _EXTRA_ESTADO["bytes"] > CACHE_EXTRA_BYTES_MAX and len(_EXTRA_LRU) > 1:
            _, (alvo_idx, alvo_chave, bytes_alvo) = _EXTRA_LRU.popitem(last=False)
            alvo_idx.extra.pop(alvo_chave, None)
            _EXTRA_ESTADO["bytes"] = max(0, _EXTRA_ESTADO["bytes"] - bytes_alvo)
        return valor


def _extra_unidade_obter(idx: Indice, tipo: str, u: int) -> tuple[str, bool] | None:
    return _extra_obter(idx, ("unidade", tipo, u))


def _extra_unidade_gravar(idx: Indice, tipo: str, u: int, par: tuple[str, bool]) -> tuple[str, bool]:
    custo = len(par[0].encode("utf-8", "replace")) + 64
    return _extra_gravar(idx, ("unidade", tipo, u), par, custo_bytes=custo)


def _indice(p: Path, fh: Any, st: Any) -> tuple[Indice, bytes | None]:
    """(índice, bytes do arquivo se a varredura acabou de lê-los)."""
    k = (str(p), st.st_size, st.st_mtime_ns, st.st_ino)
    with _TRAVA:
        idx = _INDICES.get(k)
        if idx is not None:
            _INDICES.move_to_end(k)
            return idx, None
    fh.seek(0)
    idx = varre(fh, guarda=st.st_size <= SUMARIO_MAX)
    dados, idx.dados = idx.dados, None
    if dados is not None:
        _sumario_na_varredura(idx, p.name, dados)
    with _TRAVA:
        _INDICES[k] = idx
        while len(_INDICES) > INDICES_MAX:
            _INDICES.popitem(last=False)
    return idx, dados


def indice_de(p: Any, *, abre: Any = open) -> Indice:
    """Índice da versão atual do arquivo, pelo cache de INDICES_MAX entradas."""
    p = Path(p)
    with abre(p, "rb") as fh:
        st = os.fstat(fh.fileno())
        if st.st_size > VARREDURA_MAX:
            return _indice_grande(fh, st, 1)
        return _indice(p, fh, st)[0]


def _indice_grande(fh: Any, st: Any, ate: int) -> Indice:
    """Acima de VARREDURA_MAX: varre só até a linha pedida; versão por stat (§7.1.3)."""
    fh.seek(0)
    idx = varre(fh, ate=ate)
    idx.versao = f"s{st.st_size}-m{st.st_mtime_ns}"
    idx.tamanho = st.st_size
    idx.por_stat = True
    idx.linhas_total = None
    return idx


def _sumario_na_varredura(idx: Indice, nome: str, dados: bytes) -> None:
    tp = tipo_real(idx.cabeca, nome)
    if tp["binario"] or tp["tipo"] not in _ANALISADOR or (tp["bom"] or "utf-8") != "utf-8":
        return
    enc = decide_encoding(idx, tp)
    idx.extra["sumario"] = sumario(
        tp["tipo"], dados.decode(enc["decidido"], "replace"), idx.linhas_total
    )


# ============================================================== tipo e encoding (§7.2, §7.3)
def tipo_real(cabeca: bytes, nome: str) -> dict:
    """Decide pelos bytes; a extensão só dá nome ao tipo de texto (§7.2, §7.4.4)."""
    ext = Path(nome).suffix.lower()
    for bom, enc in _BOMS:
        if cabeca.startswith(bom):
            tipo = _formatos.tipo_texto(cabeca, _TIPO_POR_EXT.get(ext, "text/plain"))
            return {"tipo": tipo, "binario": False, "bom": enc}
    for assinatura, tipo in _ASSINATURAS:
        if cabeca.startswith(assinatura):
            if tipo == "application/zip":
                tipo = _ESCRITORIO.get(ext, tipo)
            return {"tipo": tipo, "binario": True, "bom": None}
    if _formatos.e_webp(cabeca):
        return {"tipo": _formatos.WEBP, "binario": True, "bom": None}
    if cabeca[_MOBI_MARCA[0] : _MOBI_MARCA[0] + 8] == _MOBI_MARCA[1]:
        return {"tipo": _formatos.MOBI, "binario": True, "bom": None}
    if b"\x00" in cabeca:
        return {"tipo": "application/octet-stream", "binario": True, "bom": None}
    tipo = _formatos.tipo_texto(cabeca, _TIPO_POR_EXT.get(ext, "text/plain"))
    return {"tipo": tipo, "binario": False, "bom": None}


def afina_tipo(tp: dict, fh: Any) -> dict:
    """ZIP se decide pelo que há dentro (EPUB, DOCX, PPTX, XLSX ou ZIP de outro tipo)."""
    if tp["binario"] and (tp["tipo"] == "application/zip" or tp["tipo"] in _ESCRITORIO.values()):
        return {**tp, "tipo": _formatos.tipo_do_zip(fh)}
    return tp


def decide_encoding(
    indice: Indice,
    tipo: dict,
    pedido: str | None = None,
    invalidos: int | None = None,
) -> dict:
    """As cinco linhas da §7.3, na ordem; a primeira que decide encerra."""
    if pedido:
        return {"decidido": pedido, "por": "pedido", "invalidos": invalidos or 0, "julgado": True}
    if tipo.get("bom"):
        inv = indice.invalidos if tipo["bom"] == "utf-8" else (invalidos or 0)
        return {"decidido": tipo["bom"], "por": "bom", "invalidos": inv, "julgado": True}
    if indice.invalidos == 0:
        return {
            "decidido": "utf-8",
            "por": "estrito",
            "invalidos": 0,
            "julgado": not indice.por_stat,
        }
    if indice.multibyte > indice.invalidos:
        return {
            "decidido": "utf-8",
            "por": "maioria",
            "invalidos": indice.invalidos,
            "julgado": False,
        }
    return {
        "decidido": "cp1252",
        "por": "suposto",
        "invalidos": indice.cp1252_invalidos,
        "julgado": False,
    }


def _conta_invalidos(fh: Any, enc: str) -> int:
    fh.seek(0)
    dec = codecs.getincrementaldecoder(enc)("surrogateescape")
    n = 0
    while True:
        blk = fh.read(BLOCO)
        if not blk:
            break
        s = dec.decode(blk)
        if _SURROGATO.search(s):
            n += len(_SURROGATO.findall(s))
    return n + len(dec.decode(b"", final=True))


# ============================================================== páginas (§4, §5)
@dataclass
class Fatia:
    dados: bytes
    linhas: tuple[int | None, int | None] | None   # faixa servida, base 1; None = por bytes
    ini: int                                       # [ini, fim) em bytes
    fim: int
    linha_longa: dict | None = None
    pulados: int = 0                  # bytes pulados até a fronteira de caractere
    linha_inicio: int | None = None   # leitura por bytes: a linha em que a página começa
    lido: bytes = b""                 # linha longa: o que já se leu a partir de `ini`


def _anda_linhas(fh: Any, pos: int, n: int, tamanho: int) -> tuple[int, bytes]:
    if n <= 0:
        return pos, b""
    fh.seek(pos)
    while True:
        blk = fh.read(PASSO)
        if not blk:
            return tamanho, b""
        c = blk.count(b"\n")
        if c >= n:
            fim = next(islice(_NL.finditer(blk), n - 1, None)).end()
            return pos + fim, blk[fim:]
        n -= c
        pos += len(blk)


def _ancora(indice: Indice, a: int) -> tuple[int, int]:
    k = min((a - 1) // MARCO, len(indice.marcos) - 1)
    linha, byte = k * MARCO + 1, indice.marcos[k]
    with _TRAVA:
        exato = indice.inicios.get(a)
        if exato is not None:
            return a, exato
        for ln, b in indice.inicios.items():
            if linha < ln <= a:
                linha, byte = ln, b
    return linha, byte


def _preenche_buffer_linhas(
    fh: Any, ini: int, sobra: bytes, pedidas: int | None, orcamento: int
) -> bytearray:
    buf = bytearray(sobra[:orcamento])
    fh.seek(ini + len(buf))
    if pedidas is None:
        buf += fh.read(orcamento - len(buf))
        return buf
    vistas = buf.count(b"\n")
    while vistas < pedidas and len(buf) < orcamento:
        mais = fh.read(min(PASSO, orcamento - len(buf)))
        if not mais:
            break
        vistas += mais.count(b"\n")
        buf += mais
    return buf


def _calcula_corte_linhas(buf: bytearray, pedidas: int | None, *, no_fim: bool) -> int:
    if pedidas:
        m = next(islice(_NL.finditer(buf), pedidas - 1, None), None)
        if m:
            return m.end()
    corte = buf.rfind(b"\n") + 1
    if no_fim and corte < len(buf) and (not pedidas or buf.count(b"\n", 0, corte) < pedidas):
        return len(buf)
    return corte


def pagina_linhas(fh: Any, indice: Indice, a: int, b: int | None, orcamento: int) -> Fatia:
    """Linhas inteiras de `a` até `b` (ou até o orçamento), sem partir linha (§4.2)."""
    linha, byte = _ancora(indice, a)
    ini, sobra = _anda_linhas(fh, byte, a - linha, indice.tamanho)
    fim = _fim_conhecido(indice, a)
    if fim is not None and fim - ini > orcamento:
        return Fatia(
            b"",
            None,
            ini,
            ini,
            linha_longa={"linha": a, "bytes": fim - ini, "byte_ini": ini},
        )
    pedidas = (b - a + 1) if b else None
    buf = _preenche_buffer_linhas(fh, ini, sobra, pedidas, orcamento)
    corte = _calcula_corte_linhas(buf, pedidas, no_fim=ini + len(buf) >= indice.tamanho)
    if corte == 0:
        if ini >= indice.tamanho:
            return Fatia(b"", None, ini, ini)
        fim = _fim_da_linha(fh, ini + len(buf), indice.tamanho)
        return Fatia(
            b"",
            None,
            ini,
            ini,
            lido=bytes(buf),
            linha_longa={"linha": a, "bytes": fim - ini, "byte_ini": ini},
        )
    dados = bytes(buf[:corte])
    n = dados.count(b"\n") + (0 if dados.endswith(b"\n") else 1)
    return Fatia(dados, (a, a + n - 1), ini, ini + corte)


def _fim_conhecido(indice: Indice, a: int) -> int | None:
    if indice.linhas_total is not None and a == indice.linhas_total:
        return indice.tamanho
    with _TRAVA:
        seguinte = indice.inicios.get(a + 1)
    if seguinte is not None:
        return seguinte
    k, resto = divmod(a, MARCO)
    return indice.marcos[k] if resto == 0 and k < len(indice.marcos) else None


def _fim_da_linha(fh: Any, ini: int, tamanho: int) -> int:
    fh.seek(ini)
    pos = ini
    while True:
        blk = fh.read(BLOCO)
        if not blk:
            return tamanho
        i = blk.find(b"\n")
        if i >= 0:
            return pos + i + 1
        pos += len(blk)


def _inicio_antes(fh: Any, pos: int) -> int:
    while pos > 0:
        de = max(0, pos - BLOCO)
        fh.seek(de)
        blk = fh.read(pos - de)
        i = blk.rfind(b"\n")
        if i >= 0:
            return de + i + 1
        pos = de
    return 0


def pagina_cauda(fh: Any, indice: Indice, n: int, orcamento: int) -> Fatia:
    """As últimas linhas inteiras que cabem no orçamento, até `n` (§4.4)."""
    tam = indice.tamanho
    ini = max(0, tam - orcamento)
    fh.seek(ini)
    buf = fh.read(tam - ini)
    corte = 0
    if ini > 0:
        i = buf.find(b"\n")
        corte = i + 1 if i >= 0 else len(buf)
    corpo = buf[corte:]
    k = corpo.count(b"\n") + (0 if not corpo or corpo.endswith(b"\n") else 1)
    if k > n:
        corte += next(islice(_NL.finditer(corpo), k - n - 1, None)).end()
        k = n
    total = indice.linhas_total
    if k == 0:
        li = _inicio_antes(fh, ini)
        return Fatia(
            b"",
            None,
            li,
            li,
            linha_longa={"linha": total, "bytes": tam - li, "byte_ini": li},
        )
    a = (total - k + 1) if total is not None else None
    return Fatia(buf[corte:], (a, total), ini + corte, tam)


def _e_continuacao(b: int) -> bool:
    return _UTF8_CONT_MIN <= b <= _UTF8_CONT_MAX


def _tamanho_da_sequencia(lider: int) -> int:
    if lider >= _UTF8_4B:
        return 4
    if lider >= _UTF8_3B:
        return 3
    if lider >= _UTF8_2B:
        return 2
    return 1


def _continuacoes(buf: bytes, i: int) -> int:
    n = 0
    while n < _UTF8_CONT_MAX_PASSOS and i + n < len(buf) and _e_continuacao(buf[i + n]):
        n += 1
    return n


def pagina_bytes(fh: Any, offset: int, orcamento: int, encoding: str, tamanho: int) -> Fatia:
    """De `offset` até o orçamento, alinhado a caractere em UTF-8 (§5)."""
    fh.seek(offset)
    return _fatia_de_bytes(fh, fh.read(orcamento), offset, encoding, tamanho)


def _fatia_de_bytes(fh: Any, buf: bytes, offset: int, encoding: str, tamanho: int) -> Fatia:
    if encoding.replace("_", "-").lower() not in ("utf-8", "utf8"):
        return Fatia(buf, None, offset, offset + len(buf))
    pulados = _continuacoes(buf, 0)
    j = len(buf)
    if offset + len(buf) < tamanho:
        k = len(buf) - 1
        while k > pulados and len(buf) - 1 - k < _UTF8_CONT_MAX_PASSOS and _e_continuacao(buf[k]):
            k -= 1
        if k >= pulados and buf[k] >= _UTF8_2B and k + _tamanho_da_sequencia(buf[k]) > len(buf):
            j = k
        if j <= pulados:
            fh.seek(offset + len(buf))
            buf += fh.read(7)
            pulados = _continuacoes(buf, 0)
            j = min(len(buf), pulados + 1 + _continuacoes(buf, pulados + 1))
    ini = offset + pulados
    return Fatia(buf[pulados:j], None, ini, offset + j, pulados=pulados)


def _linha_do_byte(fh: Any, indice: Indice, offset: int) -> int | None:
    k = bisect.bisect_right(indice.marcos, offset) - 1
    base, linha = indice.marcos[k], k * MARCO + 1
    with _TRAVA:
        exato = indice.pontos.get(offset)
        if exato is not None:
            return exato
        for b, ln in indice.pontos.items():
            if base < b <= offset:
                base, linha = b, ln
    if indice.por_stat and base == indice.marcos[-1] and offset > base:
        return None
    fh.seek(base)
    falta = offset - base
    while falta > 0:
        blk = fh.read(min(BLOCO, falta))
        if not blk:
            break
        linha += blk.count(b"\n")
        falta -= len(blk)
    return linha


# ============================================================== sumário (§8)
_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
_CERCA = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _pula_frontmatter(linhas: list[str]) -> int:
    if not linhas or linhas[0].rstrip("\r") != "---":
        return 0
    for j in range(1, len(linhas)):
        if linhas[j].rstrip("\r") in ("---", "..."):
            return j + 1
    return 0


def _atualiza_cerca(cerca: str | None, lin: str) -> tuple[str | None, bool]:
    m = _CERCA.match(lin)
    if not m:
        return cerca, False
    marca = m.group(1)
    if cerca is None:
        return marca, True
    if marca[0] == cerca[0] and len(marca) >= len(cerca) and lin.strip() == marca:
        return None, True
    return cerca, True


def _sumario_markdown(linhas: list[str], total: int) -> list:
    cerca: str | None = None
    titulos = []
    for i in range(_pula_frontmatter(linhas), len(linhas)):
        lin = linhas[i].rstrip("\r")
        cerca, mudou = _atualiza_cerca(cerca, lin)
        if mudou or cerca is not None:
            continue
        m = _ATX.match(lin)
        if m:
            titulos.append((len(m.group(1)), (m.group(2) or "").strip(), i + 1))
    itens = []
    for j, (nivel, titulo, ini) in enumerate(titulos):
        fim = next((ini2 - 1 for nivel2, _t, ini2 in titulos[j + 1 :] if nivel2 <= nivel), total)
        itens.append([nivel, titulo, ini, fim])
    return itens


_DEFS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _item_py(no: Any, nivel: int) -> list:
    if isinstance(no, ast.ClassDef):
        rotulo = f"class {no.name}"
    else:
        rotulo = f"{'async def' if isinstance(no, ast.AsyncFunctionDef) else 'def'} {no.name}"
    return [
        nivel,
        rotulo,
        min([d.lineno for d in no.decorator_list] + [no.lineno]),
        no.end_lineno,
    ]


def _sumario_python(texto: str) -> list:
    itens = []
    for no in ast.parse(texto).body:
        if isinstance(no, _DEFS):
            itens.append(_item_py(no, 1))
            itens.extend(_item_py(f, 2) for f in no.body if isinstance(f, _DEFS))
    return itens


_JSON_TIPO = (
    (bool, "booleano"),
    (dict, "objeto"),
    (list, "lista"),
    (str, "texto"),
    (int, "número"),
    (float, "número"),
    (type(None), "nulo"),
)


def _sumario_json(texto: str) -> list | str:
    dado = json.loads(texto)
    if not isinstance(dado, dict):
        return f"JSON de primeiro nível não é objeto ({type(dado).__name__})"
    itens = []
    for k, v in dado.items():
        nome = next(n for t, n in _JSON_TIPO if isinstance(v, t))
        tam = f" ({len(v)})" if isinstance(v, (dict, list, str)) else ""
        itens.append([1, f"{k}: {nome}{tam}", None, None])
    return itens


def sumario(tipo: str, texto: str, total: int | None = None) -> tuple[list | None, str | None]:
    """Só a estrutura que o analisador do formato declara (§8.1)."""
    por = _ANALISADOR.get(tipo)
    if not por:
        return None, f"sem analisador de sumário para {tipo}"
    try:
        if por == "markdown":
            linhas = texto.split("\n")
            if total is None:
                total = len(linhas) - (1 if texto.endswith("\n") else 0)
            return _sumario_markdown(linhas, total), None
        if por == "python":
            return _sumario_python(texto), None
        r = _sumario_json(texto)
        return (None, r) if isinstance(r, str) else (r, None)
    except SyntaxError as e:
        return None, f"python não analisa: {e.msg} (linha {e.lineno})"
    except (ValueError, RecursionError) as e:
        return None, f"{por} não analisa: {e}"


# ============================================================== diretório e caminho (§9)
def _entradas(p: Path, nega: Any, termo: str = "") -> tuple[list[tuple[str, int | None]], int]:
    nomes, ocultas = [], 0
    t_filtro = termo.strip().casefold() if termo else ""
    with os.scandir(p) as it:
        for e in it:
            if nega and nega(Path(e.path)):
                ocultas += 1
                continue
            if t_filtro and t_filtro not in e.name.casefold():
                continue
            try:
                if e.is_dir():
                    nomes.append((f"{e.name}/", None))
                elif e.is_file():
                    nomes.append((e.name, e.stat().st_size))
                else:
                    nomes.append((e.name, None))
            except OSError:
                nomes.append((e.name, None))
    nomes.sort()
    return nomes, ocultas


def lista_diretorio(p: Any, nega: Any = None, termo: str = "") -> tuple[str, int, int]:
    """(texto da listagem, entradas, ocultas pela negativa)."""
    nomes, ocultas = _entradas(Path(p), nega, termo=termo)
    texto = "".join(f"{n}  {t}\n" if t is not None else f"{n}\n" for n, t in nomes)
    return texto, len(nomes), ocultas


def vizinhanca(p: Any, nega: Any = None) -> dict:
    """Para o caminho que não existe: o ancestral mais próximo que existe e o que há nele."""
    p = Path(p)
    anc = p.parent
    while not anc.exists() and anc != anc.parent:
        anc = anc.parent
    r: dict[str, Any] = {"existe_ate": str(anc)}
    if not anc.is_dir() or (nega and nega(anc)):
        return r
    try:
        nomes, _ocultas = _entradas(anc, nega)
    except OSError:
        return r
    r.update(la_tem=[n for n, _t in nomes[:LA_TEM_MAX]], la_tem_total=len(nomes))
    return r


# ============================================================== retorno (§3.2)
def _n(x: Any) -> str:
    return "?" if x is None else f"{x:,}".replace(",", ".")


def cabecalho(**kw: Any) -> str:
    """Ordem fixa: avisos, caminho, tipo, faixa, bytes, encoding, substituições, versão."""
    avisos = kw.get("avisos") or ()
    depois = kw.get("depois") or ()
    partes = [*avisos, kw["curto"], kw["tipo"], kw["faixa"]]
    servidos = kw.get("servidos")
    if servidos is not None:
        partes.append(f"{_n(servidos)} de {_n(kw['total'])} bytes")
    encoding = kw.get("encoding")
    if encoding:
        partes.append(f"{encoding['decidido']} ({encoding['por']})")
    substituicoes = kw.get("substituicoes")
    if substituicoes is not None:
        partes.append(f"substituições {substituicoes}")
    versao = kw["versao"]
    partes.append(f"versão por stat {versao}" if kw.get("por_stat") else f"versão {versao}")
    return " · ".join([*partes, *depois])


def continuacao(args: dict | None) -> tuple[str, dict | None]:
    """(`proximo`, `proximo_args`): chamada literal da página seguinte e objeto."""
    if not args:
        return FIM, None
    corpo = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items())
    return f"{TOOL}({corpo})", args


_CLASSE_EXIT = {
    "gramatica": 2,
    "faixa": 2,
    "caminho": 1,
    "binario": 1,
    "recusado": 4,
}


def envelope_erro(exit_code: int, falta: str, proximo: str | None = None, **extra: Any) -> dict:
    """Forma única de recusa ou erro da porta (arq:0064 §6)."""
    d = dict(extra)
    d["exit_code"] = exit_code
    d["falta"] = falta
    if proximo:
        d["proximo"] = proximo
    return d


def _erro(msg: str, classe: str, **extra: Any) -> dict:
    exit_code = extra.pop("exit_code", _CLASSE_EXIT.get(classe, 2))
    falta = extra.pop("falta", msg)
    proximo = extra.pop("proximo", None)
    if proximo is None:
        cura = extra.get("cura")
        if isinstance(cura, str) and cura.startswith(f"{TOOL}("):
            proximo = cura
    return envelope_erro(exit_code, falta, proximo, erro=msg, **extra, classe_erro=classe)


def _faixa(linhas: Any, p: Path | None = None) -> tuple | dict:
    """(a, b, cauda) de `"a-b"`, `"a-"`, `"-n"` ou `"n"`, base 1 (estrito: recusa 0-, 5-2, -0)."""
    if linhas in (None, ""):
        return 1, None, None
    s = str(linhas)
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d*)\s*", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2)) if m.group(2) else None
        if a >= 1 and (b is None or b >= a):
            return a, b, None
    m = re.fullmatch(r"\s*-\s*(\d+)\s*", s)
    if m and int(m.group(1)) >= 1:
        return None, None, int(m.group(1))
    m = re.fullmatch(r"\s*(\d+)\s*", s)
    if m and int(m.group(1)) >= 1:
        n = int(m.group(1))
        return n, n, None
    alvo = f'"{p}"' if p is not None else "…"
    return _erro(
        f'linhas={linhas!r}: use "a-b", "a-" ou "-n" (base 1, extremos incluídos)',
        "gramatica",
        cura=f'{TOOL}(caminho={alvo}, linhas="1-")',
    )


def _alem_do_fim(p: Path, total: Any) -> dict:
    return _erro(
        "faixa além do fim",
        "faixa",
        caminho=str(p),
        linhas_total=total,
        cura=f'{TOOL}(caminho="{p}", linhas="-100")',
    )


@dataclass
class _Pedido:
    curto: str
    faixa: tuple[int | None, int | None, int | None] | None
    modo: str
    orcamento: int
    versao: str | None
    offset: int | None
    pedido: str | None
    pedido_bytes: int | None
    paginas: Any
    dpi: int
    membro: str | None
    termo: str
    linhas: Any = None
    nega: Any = None
    abre: Any = open


def _valida_faixa_offset(p: Path, linhas: Any, offset: Any) -> Any:
    if offset is None:
        return _faixa(linhas, p)
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return _erro(f"offset={offset!r}: inteiro a partir de 0", "gramatica")
    return None


def _valida_modo_paginas(
    p: Path, modo: str, linhas: Any, offset: Any, paginas: Any
) -> dict | None:
    if modo not in MODOS:
        return _erro(f'modo={modo!r}: use "texto", "sumario", "pagina" ou "visivel"', "gramatica")
    if modo == "sumario" and (linhas not in (None, "") or offset is not None):
        return _erro(
            'modo="sumario" não aceita linhas nem offset: o sumário é do arquivo '
            "inteiro, e a faixa de cada item se lê depois por linhas",
            "gramatica",
            cura=f'{TOOL}(caminho="{p}", modo="sumario")',
        )
    if paginas not in (None, "") and (offset is not None or modo == "sumario"):
        return _erro(
            "paginas não vai com offset nem com sumário: a unidade se lê por linhas "
            "dentro do texto devolvido (§7.4.1)",
            "gramatica",
            cura=f'{TOOL}(caminho="{p}", paginas="{paginas}")',
        )
    return None


def _valida_opcoes(p: Path, opcoes: dict[str, Any]) -> _Pedido | dict:
    linhas = opcoes.get("linhas")
    modo = opcoes.get("modo", "texto")
    max_bytes = opcoes.get("max_bytes", ORCAMENTO_PADRAO)
    offset = opcoes.get("offset")
    encoding = opcoes.get("encoding")
    paginas = opcoes.get("paginas")
    dpi = opcoes.get("dpi", _formatos.DPI_PADRAO)
    membro = opcoes.get("membro")
    curto = f"{opcoes.get('curto') or str(p)}!{membro}" if membro else (opcoes.get("curto") or str(p))
    erro_mp = _valida_modo_paginas(p, modo, linhas, offset, paginas)
    if erro_mp is not None:
        return erro_mp
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi < 1:
        return _erro(f"dpi={dpi!r}: inteiro de 36 a {_formatos.DPI_MAX}", "gramatica")
    faixa = _valida_faixa_offset(p, linhas, offset)
    if isinstance(faixa, dict):
        return faixa
    if encoding:
        try:
            encoding = codecs.lookup(encoding).name
        except LookupError:
            return _erro(f"encoding={encoding!r} desconhecido", "gramatica")
    orcamento = max(1, min(int(max_bytes or ORCAMENTO_PADRAO), ORCAMENTO_MAX))
    pedido_bytes = max_bytes if max_bytes and max_bytes != ORCAMENTO_PADRAO else None
    return _Pedido(
        curto=curto,
        faixa=faixa,
        modo=modo,
        orcamento=orcamento,
        versao=opcoes.get("versao"),
        offset=offset,
        pedido=encoding,
        pedido_bytes=pedido_bytes,
        paginas=paginas,
        dpi=dpi,
        membro=membro,
        termo=opcoes.get("termo", ""),
        linhas=linhas,
        nega=opcoes.get("nega"),
        abre=opcoes.get("abre", open),
    )


def _le_estavel(p: Path, ped: _Pedido) -> dict:
    with ped.abre(p, "rb") as fh:
        for _tentativa in range(2):
            st0 = os.fstat(fh.fileno())
            r = _le_arquivo(fh, p, st0, ped)
            st1 = os.fstat(fh.fileno())
            if (st0.st_size, st0.st_mtime_ns) == (st1.st_size, st1.st_mtime_ns):
                break
        else:
            if "cabecalho" in r:
                r["cabecalho"] = "ARQUIVO INSTÁVEL · " + r["cabecalho"]
            r["instavel"] = True
    if ped.offset is not None and ped.linhas not in (None, "") and "cabecalho" in r:
        r["cabecalho"] += " · linhas ignorado: vale offset"
    return r


# ============================================================== a leitura (§13.1, `le`)
def le(p: Any, **opcoes: Any) -> dict:
    """O retorno da §3.2, sem poda e sem confinamento de morada (recebe `nega`)."""
    p = Path(p)
    ped = _valida_opcoes(p, opcoes)
    if isinstance(ped, dict):
        return ped
    try:
        st = os.stat(p)
    except (FileNotFoundError, NotADirectoryError):
        v = vizinhanca(p, ped.nega)
        return _erro(
            "não existe",
            "caminho",
            caminho=str(p),
            **v,
            cura=f'{TOOL}(caminho="{v["existe_ate"]}")',
        )
    except OSError as e:
        return _erro(f"não consegui ler: {e.strerror}", "caminho", caminho=str(p), exit_code=5)
    if _stat.S_ISDIR(st.st_mode):
        return _le_diretorio(p, ped)
    if not _stat.S_ISREG(st.st_mode):
        return _erro(
            "existe mas não é arquivo comum (socket, fifo ou dispositivo)",
            "caminho",
            caminho=str(p),
        )
    if ped.termo:
        return _erro(
            "termo só se aplica a diretório: filtra a listagem pelo nome",
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}")',
        )
    return _le_estavel(p, ped)


def _fatia_diretorio(p: Path, dados: bytes, idx: Indice, ped: _Pedido, n: int) -> Fatia | dict:
    fh = io.BytesIO(dados)
    a, b, cauda = ped.faixa or (1, None, None)
    if n == 0:
        return Fatia(b"", None, 0, 0)
    if cauda:
        f = pagina_cauda(fh, idx, cauda, ped.orcamento)
    elif a is not None and a > n:
        return _alem_do_fim(p, n)
    else:
        f = pagina_linhas(fh, idx, a or 1, b, ped.orcamento)
    if f.linha_longa:
        ll = f.linha_longa
        return Fatia(
            dados[ll["byte_ini"] : ll["byte_ini"] + ll["bytes"]],
            (ll["linha"], ll["linha"]),
            ll["byte_ini"],
            ll["byte_ini"] + ll["bytes"],
        )
    return f


def _cabecalho_diretorio(ped: _Pedido, f: Fatia, n: int, ocultas: int, versao: str) -> str:
    partes = [ped.curto, f"diretório · {_n(n)} entradas"]
    if f.linhas:
        partes.append(f"linhas {_n(f.linhas[0])}–{_n(f.linhas[1])}")
        if f.linhas[1] is not None and f.linhas[1] < n:
            partes.append(f"linhas=-{f.linhas[1] - (f.linhas[0] or 1) + 1} para as últimas")
    if ped.termo:
        partes.append(f"filtro termo={ped.termo!r}")
    if ocultas:
        partes.append(f"{_n(ocultas)} fora por negativa")
    partes.append(f"versão {versao}")
    return " · ".join(partes)


def _le_diretorio(p: Path, ped: _Pedido) -> dict:
    if ped.faixa is None:
        return _erro(
            "offset não se aplica a diretório: a listagem pagina por linhas",
            "gramatica",
            cura=f'{TOOL}(caminho="{p}")',
        )
    try:
        nomes_pares, ocultas = _entradas(p, ped.nega, termo=ped.termo)
    except OSError as e:
        return _erro(f"não consegui listar: {e.strerror}", "caminho", caminho=str(p))
    texto = "".join(f"{nm}  {t}\n" if t is not None else f"{nm}\n" for nm, t in nomes_pares)
    n = len(nomes_pares)
    dados = texto.encode("utf-8", "surrogateescape")
    idx = varre(io.BytesIO(dados))
    f = _fatia_diretorio(p, dados, idx, ped, n)
    if isinstance(f, dict):
        return f
    seguinte = f.linhas[1] + 1 if f.linhas and f.linhas[1] is not None and f.linhas[1] < n else None
    pargs: dict[str, Any] | None = {"caminho": str(p), "linhas": f"{seguinte}-"} if seguinte else None
    if pargs and ped.termo:
        pargs["termo"] = ped.termo
    proximo, proximo_args = continuacao(pargs)
    r: dict[str, Any] = {
        "cabecalho": _cabecalho_diretorio(ped, f, n, ocultas, idx.versao),
        "conteudo": f.dados.decode("utf-8", "replace"),
        "proximo": proximo,
        "proximo_args": proximo_args,
        "caminho": str(p),
        "tipo": "inode/directory",
        "entradas": [nm for nm, _t in nomes_pares],
        "total": n,
        "linhas": list(f.linhas) if f.linhas else None,
        "linhas_total": n,
        "bytes": [f.ini, f.fim],
        "bytes_total": len(dados),
        "versao": idx.versao,
        "diretorio": True,
        "ocultas": ocultas,
    }
    if ped.termo:
        r["termo"] = ped.termo
    return {k: v for k, v in r.items() if v is not None}


def _transcodifica(fh: Any, enc: str) -> tuple[bytes, int]:
    fh.seek(0)
    texto = fh.read().decode(enc, "surrogateescape")
    inv = 0
    if _SURROGATO.search(texto):
        inv = len(_SURROGATO.findall(texto))
        texto = _SURROGATO.sub("\ufffd", texto)
    return texto.encode("utf-8"), inv


def _le_arquivo(fh: Any, p: Path, st: Any, ped: _Pedido) -> dict:
    if st.st_size > VARREDURA_MAX:
        idx, dados = _indice_grande(fh, st, (ped.faixa[0] or 1) if ped.faixa else 1), None
    else:
        idx, dados = _indice(p, fh, st)
    tp = afina_tipo(tipo_real(idx.cabeca, p.name), fh)
    if ped.membro:
        return _le_membro(fh, p, idx, tp, ped)
    return _le_corpo(fh, p, idx, tp, (ped, dados))


def _indice_memoria(chave: tuple, dados: bytes, versao_override: str | None = None) -> Indice:
    with _TRAVA:
        midx = _INDICES.get(chave)
    if midx is None:
        midx = varre(io.BytesIO(dados))
        if versao_override is not None:
            midx.versao = versao_override
        with _TRAVA:
            _INDICES[chave] = midx
            while len(_INDICES) > INDICES_MAX:
                _INDICES.popitem(last=False)
    return midx


def _le_membro(fh: Any, p: Path, idx: Indice, tp: dict, ped: _Pedido) -> dict:
    """`caminho!membro`: o membro de um ZIP (EPUB, OOXML ou ZIP) lido como arquivo."""
    membro = ped.membro or ""
    if tp["tipo"] not in (
        _formatos.ZIP,
        _formatos.EPUB,
        _formatos.DOCX,
        _formatos.PPTX,
        _formatos.XLSX,
    ):
        return _erro(
            f"{tp['tipo']} não tem membro: `!` só se aplica a ZIP, EPUB e OOXML",
            "gramatica",
            caminho=str(p),
        )
    try:
        doc = _formatos.abre(tp["tipo"], fh=fh, caminho=p)
    except Exception as e:                                    # noqa: BLE001
        return _erro(f"não abre: {e}", "binario", caminho=str(p), tipo=tp["tipo"])
    try:
        dados = _formatos.membro_de(doc, membro)
    except KeyError:
        nomes = [n for n, _t in doc.membros]
        return _erro(
            "membro não existe",
            "caminho",
            caminho=f"{p}!{membro}",
            la_tem=nomes[:LA_TEM_MAX],
            la_tem_total=len(nomes),
            cura=f'{TOOL}(caminho="{p}")',
        )
    except _formatos.ErroDescompressao as e:
        return envelope_erro(
            2,
            f"descompressão recusada ({e})",
            recusado=True,
            motivo="descompressao",
            caminho=f"{p}!{membro}",
            classe_erro="gramatica",
        )
    except ValueError as e:
        return envelope_erro(
            2,
            f"membro recusado ({e})",
            recusado=True,
            motivo=str(e),
            caminho=f"{p}!{membro}",
            classe_erro="gramatica",
        )
    finally:
        doc.fecha()
    midx = _indice_memoria((f"{p}!{membro}", len(dados), idx.versao, 0), dados)
    fonte = io.BytesIO(dados)
    mtp = afina_tipo(tipo_real(midx.cabeca, membro), fonte)
    return _le_corpo(fonte, Path(f"{p}!{membro}"), midx, mtp, (ped, dados))


def _le_gzip(fh: Any, p: Path, idx: Indice, ped: _Pedido) -> dict:
    """GZIP guardado no acervo: descomprime em fluxo até MEMBRO_MAX e razão máxima (DT 832/899)."""
    try:
        dados = _formatos.ler_gzip_seguro(
            fh,
            _formatos.MEMBRO_MAX,
            tamanho_comprimido=idx.tamanho,
        )
    except _formatos.ErroDescompressao as e:
        return envelope_erro(
            2,
            f"descompressão recusada ({e})",
            recusado=True,
            motivo="descompressao",
            caminho=str(p),
            bytes_total=idx.tamanho,
            versao=idx.versao,
            classe_erro="gramatica",
        )
    except (OSError, EOFError, zlib.error) as e:
        return _erro(
            f"gzip não abre: {type(e).__name__}: {str(e)[:160]}",
            "binario",
            caminho=str(p),
            tipo="application/gzip",
            bytes_total=idx.tamanho,
            versao=idx.versao,
        )
    midx = _indice_memoria((f"{p}!gunzip", len(dados), idx.versao, 0), dados, idx.versao)
    fonte = io.BytesIO(dados)
    nome = p.name[:-3] if p.name.lower().endswith(".gz") else p.name
    mtp = afina_tipo(tipo_real(midx.cabeca, nome), fonte)
    r = _le_corpo(fonte, p, midx, mtp, (ped, dados))
    if "cabecalho" in r:
        r["cabecalho"] += f" · descomprimido de gzip ({_n(idx.tamanho)} bytes)"
    if "recusado" not in r and "erro" not in r:
        r["gzip"] = {"bytes_comprimidos": idx.tamanho, "bytes": len(dados)}
    return r


def _despacha_binario(fh: Any, p: Path, idx: Indice, tp: dict, ped: _Pedido) -> dict:
    tipo = tp["tipo"]
    if tipo == "application/gzip":
        return _le_gzip(fh, p, idx, ped)
    if tipo in _formatos.LEITORES:
        return _le_formato(fh, p, idx, tp, (ped, None))
    return envelope_erro(
        2,
        f"{tipo} não está na tabela de formatos do acervo (spec ler-arquivo §7.4) e não se lê como texto",
        recusado=True,
        motivo="sem_leitor",
        tipo=tipo,
        caminho=str(p),
        bytes_total=idx.tamanho,
        versao=idx.versao,
        cura=(
            f"{tipo} não está na tabela de formatos do acervo (spec ler-arquivo "
            "§7.4) e não se lê como texto. Tipo do acervo que cai aqui é defeito "
            "da tool: abra incidente."
        ),
        classe_erro="binario",
    )


def _prepara_fonte_texto(
    fh: Any, p: Path, idx: Indice, tp: dict, par: tuple[_Pedido, bytes | None]
) -> tuple[Any, Indice, tuple, dict, str] | dict:
    ped, dados = par
    fonte, fidx, depois = (io.BytesIO(dados) if dados is not None else fh), idx, ()
    inv = None
    if tp["bom"] and tp["bom"] != "utf-8":
        if idx.tamanho > UTF16_MAX:
            return envelope_erro(
                2,
                f"arquivo {tp['bom']} excede o limite de 16 MiB para transcodificação em memória",
                recusado=True,
                motivo=f"{tp['bom']} acima de 16 MiB",
                caminho=str(p),
                bytes_total=idx.tamanho,
                versao=idx.versao,
                cura="a porta transcodifica UTF-16/32 em memória só até 16 MiB",
                classe_erro="gramatica",
            )
        utf8, inv = _transcodifica(fonte, tp["bom"])
        fonte = io.BytesIO(utf8)
        fidx = varre(fonte)
        fidx.versao = idx.versao
        depois = (f"transcodificado de {tp['bom'][:6]}",)
    if ped.pedido:
        inv = _extra_obter(idx, ("invalidos", ped.pedido))
        if inv is None:
            inv = _extra_gravar(
                idx, ("invalidos", ped.pedido), _conta_invalidos(fh, ped.pedido), custo_bytes=64
            )
    enc = decide_encoding(idx, tp, ped.pedido, inv)
    leitura_enc = "utf-8" if fidx is not idx else enc["decidido"]
    return fonte, fidx, depois, enc, leitura_enc


def _fatia_texto(fonte: Any, p: Path, fidx: Indice, ped: _Pedido, leitura_enc: str) -> Fatia | dict:
    if ped.offset is not None:
        if ped.offset > fidx.tamanho:
            return _erro(
                "offset além do fim",
                "faixa",
                caminho=str(p),
                bytes_total=fidx.tamanho,
                cura=f'{TOOL}(caminho="{p}", linhas="-100")',
            )
        f = pagina_bytes(fonte, ped.offset, ped.orcamento, leitura_enc, fidx.tamanho)
        f.linha_inicio = _linha_do_byte(fonte, fidx, f.ini)
        return f
    a, b, cauda = ped.faixa or (1, None, None)
    if cauda:
        f = pagina_cauda(fonte, fidx, cauda, ped.orcamento)
    else:
        if fidx.linhas_total is not None and a is not None and a > fidx.linhas_total:
            return _alem_do_fim(p, fidx.linhas_total)
        f = pagina_linhas(fonte, fidx, a or 1, b, ped.orcamento)
        if f.ini >= fidx.tamanho and not f.dados and not f.linha_longa:
            return _alem_do_fim(p, None)
    if f.linha_longa:
        ll = f.linha_longa
        if f.lido:
            f = _fatia_de_bytes(
                fonte, f.lido[: ped.orcamento], ll["byte_ini"], leitura_enc, fidx.tamanho
            )
        else:
            f = pagina_bytes(fonte, ll["byte_ini"], ped.orcamento, leitura_enc, fidx.tamanho)
        f.linha_longa, f.linha_inicio = ll, ll["linha"]
    return f


def _valida_texto_modo(p: Path, tipo: str, ped: _Pedido) -> dict | None:
    if ped.modo == "pagina":
        return _erro(
            f'modo="pagina" é imagem da unidade: {tipo} não tem página nem imagem; '
            'leia com modo="texto"',
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}")',
        )
    if ped.paginas not in (None, ""):
        return _erro(
            f"paginas só vale em formato com unidade fixa (PDF, EPUB, PPTX, XLSX): "
            f"{tipo} se lê por linhas",
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}", linhas="1-")',
        )
    return None


def _avisos_texto(ped: _Pedido, idx: Indice, enc: dict) -> tuple[list[str], dict | None]:
    avisos, mudou = [], None
    if ped.versao and ped.versao != idx.versao:
        mudou = {"de": ped.versao, "para": idx.versao}
        avisos.append(
            f"ARQUIVO MUDOU desde a versão {ped.versao} · as linhas lidas antes podem ter mudado"
        )
    if not enc["julgado"]:
        avisos.append("NÃO JULGADO")
    return avisos, mudou


def _le_corpo(fh: Any, p: Path, idx: Indice, tp: dict, par: tuple[_Pedido, bytes | None]) -> dict:
    ped, dados = par
    tipo = tp["tipo"]
    if tp["binario"]:
        return _despacha_binario(fh, p, idx, tp, ped)
    if ped.modo == "visivel" and tipo in (_formatos.HTML, _formatos.MHTML):
        return _le_formato(fh, p, idx, tp, (ped, dados))
    erro_modo = _valida_texto_modo(p, tipo, ped)
    if erro_modo is not None:
        return erro_modo
    prep = _prepara_fonte_texto(fh, p, idx, tp, (ped, dados))
    if isinstance(prep, dict):
        return prep
    fonte, fidx, depois, enc, leitura_enc = prep
    avisos, mudou = _avisos_texto(ped, idx, enc)
    base = {
        "caminho": str(p),
        "bytes_total": idx.tamanho,
        "versao": idx.versao,
        "encoding": enc,
        "tipo": tipo,
    }
    if ped.modo == "sumario":
        return _le_sumario(
            fonte,
            fidx,
            tp,
            ped,
            {
                "enc": leitura_enc,
                "base": base,
                "avisos": avisos,
                "mudou": mudou,
                "usa_cache": not ped.pedido and fidx is idx,
            },
        )
    if idx.tamanho == 0:
        r = {
            "cabecalho": " · ".join(
                [*avisos, ped.curto, tipo, "arquivo vazio (0 bytes)", f"versão {idx.versao}"]
            ),
            "conteudo": "",
            "proximo": FIM,
            **base,
            "linhas_total": 0,
            "bytes": [0, 0],
        }
        return _com_mudou(r, mudou)
    f = _fatia_texto(fonte, p, fidx, ped, leitura_enc)
    if isinstance(f, dict):
        return f
    extra_args = {
        **({"max_bytes": ped.orcamento} if ped.pedido_bytes else {}),
        **({"encoding": ped.pedido} if ped.pedido else {}),
    }
    return _monta_pagina(
        f,
        fidx,
        tp,
        p,
        {
            "ped": ped,
            "enc": enc,
            "leitura_enc": leitura_enc,
            "base": base,
            "avisos": avisos,
            "depois": depois,
            "mudou": mudou,
            "extra_args": extra_args,
        },
    )


def _com_mudou(r: dict, mudou: Any) -> dict:
    if mudou:
        r["mudou"] = mudou
    return r


def _faixa_e_prox_linhas(
    f: Fatia, idx: Indice, p: Path, faixa: Any, *, no_fim: bool
) -> tuple[str, dict | None, list]:
    a, b_real = f.linhas or (None, None)
    faixa_txt = f"linhas {_n(a)}–{_n(b_real)} de {_n(idx.linhas_total)}"
    if b_real is not None:
        idx.aprende(b_real + 1, f.fim, inicio=True)
    pedido_b = faixa[1] if faixa else None
    if no_fim or b_real is None:
        prox = None
    elif pedido_b and b_real < pedido_b:
        prox = {"caminho": str(p), "linhas": f"{b_real + 1}-{pedido_b}"}
    else:
        prox = {"caminho": str(p), "linhas": f"{b_real + 1}-"}
    return faixa_txt, prox, [a, b_real]


def _faixa_e_prox_bytes(
    f: Fatia, idx: Indice, p: Path, *, no_fim: bool
) -> tuple[str, dict | None, None]:
    faixa_txt = f"bytes {_n(f.ini)}–{_n(f.fim)} de {_n(idx.tamanho)}"
    if f.linha_longa:
        ll = f.linha_longa
        faixa_txt = (
            f"linha {_n(ll['linha'])} tem {_n(ll['bytes'])} bytes, acima do "
            f"orçamento · {faixa_txt}"
        )
    if f.linha_inicio is not None:
        faixa_txt += f" · começa na linha {_n(f.linha_inicio)}"
        idx.aprende(f.linha_inicio + f.dados.count(b"\n"), f.fim, inicio=f.dados.endswith(b"\n"))
    if f.pulados:
        faixa_txt += f" · {f.pulados} bytes pulados até a fronteira de caractere"
    prox = None if no_fim else {"caminho": str(p), "offset": f.fim}
    return faixa_txt, prox, None


def _monta_pagina(f: Fatia, idx: Indice, tp: dict, p: Path, ctx: dict[str, Any]) -> dict:
    ped: _Pedido = ctx["ped"]
    curto, enc, base = ped.curto, ctx["enc"], ctx["base"]
    depois, mudou = ctx["depois"], ctx["mudou"]
    total_l = idx.linhas_total
    avisos = list(ctx["avisos"])
    ll = f.linha_longa
    if ll:
        idx.aprende(ll["linha"], ll["byte_ini"], inicio=True)
        avisos.append("LINHA LONGA")
    texto = f.dados.decode(ctx["leitura_enc"], "replace")
    no_fim = f.fim >= idx.tamanho
    if f.linhas is not None:
        faixa_txt, prox, linhas_campo = _faixa_e_prox_linhas(f, idx, p, ped.faixa, no_fim=no_fim)
    else:
        faixa_txt, prox, linhas_campo = _faixa_e_prox_bytes(f, idx, p, no_fim=no_fim)
    if prox:
        prox["versao"] = idx.versao
        prox.update(ctx["extra_args"])
    proximo, proximo_args = continuacao(prox)
    cab = cabecalho(
        curto=curto,
        tipo=tp["tipo"],
        faixa=faixa_txt,
        servidos=len(f.dados),
        total=idx.tamanho,
        encoding=enc,
        substituicoes=texto.count("\ufffd"),
        versao=idx.versao,
        por_stat=idx.por_stat,
        avisos=tuple(avisos),
        depois=depois,
    )
    r: dict[str, Any] = {
        "cabecalho": cab,
        "conteudo": texto,
        "proximo": proximo,
        "proximo_args": proximo_args,
        **base,
        "linhas": linhas_campo,
        "linhas_total": total_l,
        "bytes": [f.ini, f.fim],
    }
    if ll:
        r["linha_longa"] = ll
    if (f.ini > 0 or not no_fim) and tp["tipo"] in _ANALISADOR and idx.tamanho <= SUMARIO_MAX:
        r["sumario"] = f'{TOOL}(caminho="{p}", modo="sumario")'
    return _com_mudou(
        {k: v for k, v in r.items() if v is not None or k == "linhas_total"},
        mudou,
    )


def _cabe(itens: list, orcamento: int) -> bool:
    return len(json.dumps(itens, ensure_ascii=False).encode()) <= orcamento


def _enxuga_sumario(itens: list, orcamento: int) -> tuple[list, str]:
    servir, nota = itens, ""
    nivel = max((i[0] for i in itens), default=1)
    while nivel > 1 and not _cabe(servir, orcamento):
        servir = [i for i in servir if i[0] < nivel]
        nivel -= 1
        nota = f"só até o nível {nivel} (orçamento)"
    if not _cabe(servir, orcamento):
        lo, hi = 0, len(servir)
        while lo < hi:
            meio = (lo + hi + 1) // 2
            lo, hi = (meio, hi) if _cabe(servir[:meio], orcamento) else (lo, meio - 1)
        nota = f"primeiros {lo} de {len(servir)} itens (orçamento)"
        servir = servir[:lo]
    return servir, nota


def _le_sumario(fh: Any, idx: Indice, tp: dict, ped: _Pedido, ctx: dict[str, Any]) -> dict:
    por = _ANALISADOR.get(tp["tipo"])
    cached = _extra_obter(idx, "sumario") if ctx["usa_cache"] else None
    if idx.tamanho > SUMARIO_MAX:
        itens, motivo = None, "arquivo acima de 8 MiB: sumário não se calcula"
    elif not por:
        itens, motivo = None, f"sem analisador de sumário para {tp['tipo']}"
    elif cached is not None:
        itens, motivo = cached
    else:
        fh.seek(0)
        itens, motivo = sumario(tp["tipo"], fh.read().decode(ctx["enc"], "replace"), idx.linhas_total)
    partes = [*ctx["avisos"], ped.curto, tp["tipo"], "sumário"]
    if itens is not None:
        itens, nota = _enxuga_sumario(itens, ped.orcamento)
        partes.append(f"{_n(len(itens))} itens")
        if nota:
            partes.append(nota)
    else:
        partes.append(f"sem sumário: {motivo}")
    partes.append(f"versão {idx.versao}")
    r: dict[str, Any] = {
        "cabecalho": " · ".join(partes),
        "sumario": itens,
        "sumario_por": por,
        **ctx["base"],
        "linhas_total": idx.linhas_total,
    }
    if itens is None:
        r["motivo"] = motivo
    return _com_mudou(r, ctx["mudou"])


# ============================================================== formatos do acervo (§7.4)
def _faixa_unidades(paginas: Any, n: int, p: Path) -> Any:
    if paginas in (None, ""):
        return 1, None
    f = _faixa(paginas)
    if isinstance(f, dict):
        f["erro"] = f["erro"].replace("linhas=", "paginas=", 1)
        f["cura"] = f'{TOOL}(caminho="{p}", paginas="1-")'
        return f
    a, b, cauda = f
    if cauda:
        return max(1, n - cauda + 1), None
    if a > n:
        return _erro(
            "página além do fim",
            "faixa",
            caminho=str(p),
            paginas_total=n,
            cura=f'{TOOL}(caminho="{p}", paginas="{n}-{n}")',
        )
    return a, (min(b, n) if b else None)


def _marca(doc: Any, u: int) -> str:
    return f"<!-- p. {u} -->"


def _unidade_texto(doc: Any, idx: Indice, tipo: str, u: int) -> tuple[str, bool]:
    cached = _extra_unidade_obter(idx, tipo, u)
    if cached is not None:
        return cached
    try:
        corpo = doc.texto(u)
    except _formatos.ErroDescompressao:
        raise
    except Exception as e:                                    # noqa: BLE001
        corpo = f"<!-- unidade não lida: {type(e).__name__}: {str(e)[:120]} -->\n"
    vazia = not corpo.strip()
    if doc.unidade == "nenhuma":
        texto = corpo
    elif vazia and doc.unidade == "pagina":
        texto = (
            f'{_marca(doc, u)}\n<!-- sem camada de texto: leia com modo="pagina", '
            f'paginas="{u}-{u}" -->\n\n'
        )
    else:
        texto = f"{_marca(doc, u)}\n{corpo}\n"
    return _extra_unidade_gravar(idx, tipo, u, (texto, vazia and doc.unidade == "pagina"))


def _le_formato(fh: Any, p: Path, idx: Indice, tp: dict, par: tuple[_Pedido, bytes | None]) -> dict:
    ped, dados = par
    tipo = tp["tipo"]
    if ped.offset is not None:
        return _erro(
            f"offset não se aplica a {tipo}: a unidade se lê por paginas e linhas",
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}")',
        )
    base = {"caminho": str(p), "bytes_total": idx.tamanho, "versao": idx.versao, "tipo": tipo}
    avisos, mudou = [], None
    if ped.versao and ped.versao != idx.versao:
        mudou = {"de": ped.versao, "para": idx.versao}
        avisos.append(
            f"ARQUIVO MUDOU desde a versão {ped.versao} · as páginas lidas antes podem ter mudado"
        )
    if ped.modo == "sumario":
        return _com_mudou(
            {
                "cabecalho": " · ".join(
                    [
                        *avisos,
                        ped.curto,
                        tipo,
                        "sumário",
                        f"sem sumário: sem analisador de sumário para {tipo}",
                        f"versão {idx.versao}",
                    ]
                ),
                "sumario": None,
                "sumario_por": None,
                "motivo": f"sem analisador de sumário para {tipo}",
                **base,
            },
            mudou,
        )
    enc = dict(ENC_BINARIO)
    try:
        if not tp["binario"] and tipo in (_formatos.HTML, _formatos.MHTML):
            if dados is None:
                fh.seek(0)
                dados = fh.read()
            doc = _formatos.abre(tipo, dados=dados, encoding=ped.pedido)
            enc = decide_encoding(idx, tp, ped.pedido)
        else:
            doc = _formatos.abre(
                tipo,
                fh=fh,
                caminho=None if "!" in str(p) else p,
                dados=(fh.getvalue() if isinstance(fh, io.BytesIO) else None),
            )
    except _formatos.ErroDescompressao as e:
        return _erro_descompressao(e, p, tipo, idx)
    except Exception as e:                                    # noqa: BLE001
        return _erro(
            f"{tipo} não abre: {type(e).__name__}: {str(e)[:200]}",
            "binario",
            caminho=str(p),
            tipo=tipo,
            bytes_total=idx.tamanho,
            versao=idx.versao,
            cura=(
                "arquivo corrompido ou cifrado: confira o objeto no balde "
                "(`acervo ler biblioteca objeto`)"
            ),
        )
    try:
        return _pagina_formato(
            doc,
            p,
            idx,
            tp,
            {"enc": enc, "ped": ped, "base": base, "avisos": avisos, "mudou": mudou},
        )
    except _formatos.ErroDescompressao as e:
        return _erro_descompressao(e, p, tipo, idx)
    finally:
        doc.fecha()


def _erro_descompressao(exc: Exception, p: Path, tipo: str, idx: Indice) -> dict[str, Any]:
    return envelope_erro(
        2,
        f"descompressão recusada ({exc})",
        recusado=True,
        motivo="descompressao",
        caminho=str(p),
        tipo=tipo,
        bytes_total=idx.tamanho,
        versao=idx.versao,
        classe_erro="gramatica",
    )


def _pagina_formato_imagem(doc: Any, p: Path, idx: Indice, tp: dict, ctx: dict[str, Any]) -> dict:
    tipo = tp["tipo"]
    ped: _Pedido = ctx["ped"]
    a, b, b_fim, n = ctx["a"], ctx["b"], ctx["b_fim"], ctx["n"]
    com_unidade, rotulo = ctx["com_unidade"], ctx["rotulo"]
    base, avisos, mudou = ctx["base"], ctx["avisos"], ctx["mudou"]
    if doc.unidade == "imagem":
        png, mime, ex = doc.imagem(1)
        dim = ex.get("dimensoes")
        cab = [
            *avisos,
            ped.curto,
            tipo,
            "imagem" + (f" · {dim[0]}×{dim[1]} px" if dim else ""),
            f"{_n(len(png))} bytes",
            f"versão {idx.versao}",
        ]
        return _com_mudou(
            {
                "cabecalho": " · ".join(cab),
                "proximo": FIM,
                "imagens": [
                    {
                        "pagina": 1,
                        "png": png,
                        "mime": mime,
                        "largura": dim[0] if dim else None,
                        "altura": dim[1] if dim else None,
                    }
                ],
                **base,
            },
            mudou,
        )
    if not doc.render:
        prox = f'{TOOL}(caminho="{p}"' + (f', paginas="{a}-{b_fim}")' if com_unidade else ")")
        return envelope_erro(
            2,
            f"{tipo} ainda não tem renderizador livre na imagem da porta (spec ler-arquivo §7.4.2) — leia como texto",
            prox,
            recusado=True,
            motivo="sem_render",
            tipo=tipo,
            caminho=str(p),
            bytes_total=idx.tamanho,
            versao=idx.versao,
            cura=f"{tipo} ainda não tem renderizador livre na imagem da porta (spec ler-arquivo §7.4.2); o texto vale: {prox}",
            classe_erro="gramatica",
        )
    imagens, total, u = [], 0, a
    while u <= b_fim and (not imagens or total < _formatos.IMAGEM_TETO):
        try:
            png, mime, ex = doc.imagem(u, ped.dpi)
        except Exception as e:                                # noqa: BLE001
            return _erro(
                f"{rotulo} {u} não renderiza: {type(e).__name__}: {str(e)[:160]}",
                "binario",
                caminho=str(p),
                **base,
            )
        dim = ex.get("dimensoes") or (None, None)
        imagens.append(
            {
                "pagina": u,
                "png": png,
                "mime": mime,
                "largura": dim[0],
                "altura": dim[1],
                "dpi": ex.get("dpi"),
            }
        )
        total += len(png)
        u += 1
    ult = u - 1
    prox = None
    if ult < b_fim:
        prox = {
            "caminho": str(p),
            "paginas": f"{ult + 1}-{b}" if b else f"{ult + 1}-",
            "modo": "pagina",
            "versao": idx.versao,
        }
        if ped.dpi != _formatos.DPI_PADRAO:
            prox["dpi"] = ped.dpi
    proximo, proximo_args = continuacao(prox)
    cab = [
        *avisos,
        ped.curto,
        tipo,
        f"{rotulo} {_n(a)}–{_n(ult)} de {_n(n)} · imagem",
        f"{len(imagens)} PNG · {_n(total)} bytes · {imagens[0].get('dpi') or ''} dpi".replace(
            " ·  dpi", ""
        ),
        f"versão {idx.versao}",
    ]
    r = {
        "cabecalho": " · ".join(cab),
        "proximo": proximo,
        "proximo_args": proximo_args,
        "imagens": imagens,
        "paginas": [a, ult],
        **base,
    }
    return _com_mudou({k: v for k, v in r.items() if v is not None}, mudou)


def _corta_unidade_grande(
    partes: list[str], orcamento: int, lb: int
) -> tuple[list[str], int, int, dict | None]:
    buf: list[str] = []
    acum, longa = 0, None
    for x in partes:
        bx = len(x.encode("utf-8"))
        if buf and acum + bx > orcamento:
            break
        if not buf and bx > orcamento:
            longa = {"linha": lb + 1, "bytes": bx}
        buf.append(x)
        acum += bx
        lb += 1
    return buf, acum, lb, longa


def _coleta_unidades_texto(
    doc: Any, idx: Indice, tipo: str, estado: dict[str, Any]
) -> dict[str, Any]:
    u, b_fim, pulo = estado["u"], estado["b_fim"], estado["pulo"]
    orcamento, lb = estado["orcamento"], estado["la"] - 1
    buf: list[str] = []
    acum, longa, sem_camada = 0, None, []
    primeira_u = ultima_u = u
    while u <= b_fim:
        texto, vazia = _unidade_texto(doc, idx, tipo, u)
        partes, pulo = texto.splitlines(keepends=True)[pulo:], 0
        tam = sum(len(x.encode("utf-8")) for x in partes)
        if buf and acum + tam > orcamento:
            break
        if vazia:
            sem_camada.append(u)
        ultima_u = u
        if not buf and tam > orcamento:
            buf, acum, lb, longa = _corta_unidade_grande(partes, orcamento, lb)
            if len(buf) == len(partes):
                u += 1
            break
        buf.extend(partes)
        acum, lb, u = acum + tam, lb + len(partes), u + 1
    return {
        "buf": buf,
        "acum": acum,
        "lb": lb,
        "u": u,
        "longa": longa,
        "sem_camada": sem_camada,
        "primeira_u": primeira_u,
        "ultima_u": ultima_u,
    }


def _pagina_formato(doc: Any, p: Path, idx: Indice, tp: dict, ctx: dict[str, Any]) -> dict:
    tipo = tp["tipo"]
    ped: _Pedido = ctx["ped"]
    avisos, mudou = ctx["avisos"], ctx["mudou"]
    n = max(1, doc.n)
    com_unidade = doc.unidade not in ("nenhuma", "imagem")
    extra_args = {
        **({"max_bytes": ped.orcamento} if ped.pedido_bytes else {}),
        **({"encoding": ped.pedido} if ped.pedido else {}),
        **({"modo": "visivel"} if ped.modo == "visivel" else {}),
    }
    if ped.paginas not in (None, "") and not com_unidade:
        return _erro(
            f"{tipo} não tem unidade fixa ({doc.unidade}): leia por linhas; a página "
            "do DOCX é do renderizador (spec espelho-de-leitura §2.6)",
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}", linhas="1-")',
        )
    fu = _faixa_unidades(ped.paginas, n, p)
    if isinstance(fu, dict):
        return fu
    a, b = fu
    b_fim = b if b is not None else n
    rotulo = _formatos.ROTULO.get(doc.unidade, "unidade")
    base = {**ctx["base"], "unidade": doc.unidade}
    if com_unidade:
        base["paginas_total"] = n
    if doc.nomes:
        base["nomes"] = doc.nomes[a - 1 : b_fim][:200]
    if doc.membros and tipo in (_formatos.ZIP, _formatos.EPUB):
        base["membros_total"] = len(doc.membros)
    subctx = {
        **ctx,
        "base": base,
        "a": a,
        "b": b,
        "b_fim": b_fim,
        "n": n,
        "com_unidade": com_unidade,
        "rotulo": rotulo,
        "extra_args": extra_args,
    }
    if ped.modo == "pagina":
        return _pagina_formato_imagem(doc, p, idx, tp, subctx)
    if doc.unidade == "imagem":
        dim = doc.dimensoes
        cab = [
            "IMAGEM",
            *avisos,
            ped.curto,
            tipo,
            "imagem" + (f" · {dim[0]}×{dim[1]} px" if dim else ""),
            f"0 de {_n(idx.tamanho)} bytes",
            f"versão {idx.versao}",
        ]
        return _com_mudou(
            {
                "cabecalho": " · ".join(cab),
                "conteudo": "",
                "proximo": FIM,
                "aviso": 'imagem não tem texto: leia com modo="pagina"',
                "cura": f'{TOOL}(caminho="{p}", modo="pagina")',
                **base,
                "linhas_total": 0,
            },
            mudou,
        )
    return _pagina_formato_texto(doc, p, idx, tp, subctx)


def _avanca_ate_linha(
    doc: Any, idx: Indice, tipo: str, intervalo: tuple[int, int, int]
) -> tuple[int, int]:
    a, b_fim, la = intervalo
    linha, u = 1, a
    while u <= b_fim:
        k = _unidade_texto(doc, idx, tipo, u)[0].count("\n")
        if linha + k > la:
            break
        linha, u = linha + k, u + 1
    return linha, u


def _aviso_sem_camada(sem_camada: list[int]) -> str:
    lista = ", ".join(str(x) for x in sem_camada[:_SEM_CAMADA_LISTA_MAX])
    if len(sem_camada) > _SEM_CAMADA_LISTA_MAX:
        lista += f" +{len(sem_camada) - _SEM_CAMADA_LISTA_MAX}"
    return f"SEM CAMADA DE TEXTO p. {lista}"


def _prox_formato_texto(
    p: Path, idx: Indice, ctx: dict[str, Any], lb: int, lb_pedido: int | None
) -> dict:
    prox = {
        "caminho": str(p),
        "linhas": f"{lb + 1}-{lb_pedido}" if lb_pedido else f"{lb + 1}-",
        "versao": idx.versao,
        **ctx["extra_args"],
    }
    if ctx["com_unidade"]:
        a, b = ctx["a"], ctx["b"]
        prox["paginas"] = f"{a}-{b}" if b else f"{a}-"
    return prox


def _pagina_formato_texto(doc: Any, p: Path, idx: Indice, tp: dict, ctx: dict[str, Any]) -> dict:
    tipo = tp["tipo"]
    ped: _Pedido = ctx["ped"]
    a, b_fim, n = ctx["a"], ctx["b_fim"], ctx["n"]
    com_unidade, rotulo = ctx["com_unidade"], ctx["rotulo"]
    base, avisos, mudou, enc = ctx["base"], list(ctx["avisos"]), ctx["mudou"], ctx["enc"]
    if ped.faixa and ped.faixa[2]:
        return _erro(
            'linhas="-n" não se aplica a formato do acervo: use paginas',
            "gramatica",
            caminho=str(p),
            cura=f'{TOOL}(caminho="{p}", paginas="{n}-{n}")',
        )
    la = (ped.faixa[0] if ped.faixa else 1) or 1
    lb_pedido = ped.faixa[1] if ped.faixa else None
    linha, u = _avanca_ate_linha(doc, idx, tipo, (a, b_fim, la))
    if u > b_fim:
        return _alem_do_fim(p, linha - 1)
    col = _coleta_unidades_texto(
        doc,
        idx,
        tipo,
        {"u": u, "b_fim": b_fim, "pulo": la - linha, "orcamento": ped.orcamento, "la": la},
    )
    buf, acum, lb = col["buf"], col["acum"], col["lb"]
    longa, sem_camada = col["longa"], col["sem_camada"]
    primeira_u, ultima_u = col["primeira_u"], col["ultima_u"]
    acabou = col["u"] > b_fim
    if lb_pedido and lb >= lb_pedido:
        buf, lb, acabou = buf[: len(buf) - (lb - lb_pedido)], lb_pedido, True
    conteudo = "".join(buf)
    prox = None if acabou else _prox_formato_texto(p, idx, ctx, lb, lb_pedido)
    proximo, proximo_args = continuacao(prox)
    if sem_camada:
        avisos.append(_aviso_sem_camada(sem_camada))
    if longa:
        avisos.append("LINHA LONGA")
    prefixo = f"{rotulo} {_n(primeira_u)}–{_n(ultima_u)} de {_n(n)} · " if com_unidade else ""
    total_linhas = _total_linhas(idx, tipo, a, b_fim)
    sufixo = f" de {_n(total_linhas)}" if total_linhas is not None else ""
    faixa_txt = f"{prefixo}linhas {_n(la)}–{_n(lb)}{sufixo}"
    cab = cabecalho(
        curto=ped.curto,
        tipo=tipo,
        faixa=faixa_txt,
        servidos=acum,
        total=idx.tamanho,
        encoding=enc,
        substituicoes=conteudo.count("\ufffd"),
        versao=idx.versao,
        avisos=tuple(avisos),
    )
    r: dict[str, Any] = {
        "cabecalho": cab,
        "conteudo": conteudo,
        "proximo": proximo,
        "proximo_args": proximo_args,
        **base,
        "encoding": enc,
        "linhas": [la, lb],
        "linhas_total": total_linhas,
        "bytes_servidos": acum,
    }
    if com_unidade:
        r["paginas"] = [primeira_u, ultima_u]
    if sem_camada:
        r["sem_texto"] = sem_camada
        r["cura"] = (
            f'{TOOL}(caminho="{p}", modo="pagina", paginas="{sem_camada[0]}-{sem_camada[0]}")'
        )
    if longa:
        r["linha_longa"] = longa
    return _com_mudou(
        {k: v for k, v in r.items() if v is not None or k == "linhas_total"},
        mudou,
    )


def _total_linhas(idx: Indice, tipo: str, a: int, b: int) -> int | None:
    with _TRAVA:
        pares = [idx.extra.get(("unidade", tipo, k)) for k in range(a, b + 1)]
    if all(par is not None for par in pares):
        return sum(par[0].count("\n") for par in pares if par is not None)
    return None


# ============================================================== lote (§10) e releitura (§11)
def servidos(r: dict) -> int:
    """Bytes que o item serviu à fita: texto da página + bytes de PNG (§7.4.5)."""
    n = 0
    for img in r.get("imagens") or ():
        if isinstance(img.get("png"), (bytes, bytearray)):
            n += len(img["png"])
        elif isinstance(img.get("base64"), str):
            n += len(img["base64"]) * 3 // 4
    t = r.get("conteudo", r.get("content"))
    if isinstance(t, str):
        return n + len(t.encode("utf-8", "replace"))
    if isinstance(r.get("sumario"), list):
        return n + len(json.dumps(r["sumario"], ensure_ascii=False).encode())
    return n


def lote(itens: list, le_item: Any, teto: int) -> dict:
    """Itens em ordem; o teto conta bytes servidos; erro num item não derruba os outros (§10)."""
    resultados, acumulado, lote_next = [], 0, None
    for i, item in enumerate(itens):
        if acumulado >= teto:
            lote_next = i
            break
        r = le_item(i, item)
        acumulado += servidos(r)
        resultados.append(r)
    resultados += [{"omitido_por_teto": True} for _ in range(len(itens) - len(resultados))]
    return {"lote": resultados, "lote_n": len(itens), "lote_next": lote_next}


_NA_RELEITURA = (
    "conteudo",
    "content",
    "caminho",
    "path",
    "versao",
    "truncated",
    "next_offset",
    "poda",
    "poda_aviso",
)


def enxuga_releitura(r: dict) -> dict:
    """Releitura igual sai só com o aviso e a alça; o resto segue inteiro."""
    if (r.get("poda") or {}).get("modo") != "igual":
        return r
    return {k: r[k] for k in _NA_RELEITURA if k in r}


# ============================================================== fachada confinada (`ler`)
def _separa_membro(caminho: str | Path, membro: str | None) -> tuple[Path, str | None]:
    if membro is not None:
        return Path(caminho), membro
    bruto = str(caminho)
    if "!" in bruto:
        base_str, cand = bruto.split("!", 1)
        if cand and not Path(bruto).exists():
            return Path(base_str), cand
    return Path(caminho), None


def ler(caminho: str | Path, **opcoes: Any) -> dict[str, Any]:
    """Leitura confinada às moradas declaradas (achado 921), delegando o contrato a `le`."""
    instancia: Path | None = opcoes.get("instancia")
    bancada: Path | None = opcoes.get("bancada")
    release: Path | None = opcoes.get("release")
    pdp: Path | None = opcoes.get("pdp")
    cadeira: str = str(opcoes.get("cadeira") or "")
    p, membro_ef = _separa_membro(caminho, opcoes.get("membro"))

    if eh_segredo(p, instancia=instancia, pdp=pdp, release_dir=release):
        motivo = "segredo: fora do alcance da leitura de arquivo"
        return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
    if _sob_fila(p, instancia=instancia):
        motivo = "caminho sob a fila — use o verbo `fila`"
        return envelope_erro(4, motivo, 'fila(ato="status")', recusado=True, path=str(p), motivo=motivo)

    if not p.is_absolute():
        p_res, err_rel = resolver_leitura_relativo(str(p), bancada_dir=bancada, cadeira=cadeira)
        if err_rel or p_res is None:
            motivo = err_rel or "fora de morada"
            return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
        p = p_res
        if eh_segredo(p, instancia=instancia, pdp=pdp, release_dir=release):
            motivo = "segredo: fora do alcance da leitura de arquivo"
            return envelope_erro(4, motivo, recusado=True, path=str(p), motivo=motivo)
        if _sob_fila(p, instancia=instancia):
            motivo = "caminho sob a fila — use o verbo `fila`"
            return envelope_erro(
                4, motivo, 'fila(ato="status")', recusado=True, path=str(p), motivo=motivo
            )

    err_morada = nega_morada_leitura(p, instancia=instancia, bancada_dir=bancada, release_dir=release)
    if err_morada:
        return envelope_erro(4, err_morada, recusado=True, path=str(p), motivo=err_morada)

    def _nega(q: Path) -> bool:
        return (
            eh_segredo(q, instancia=instancia, pdp=pdp, release_dir=release)
            or _sob_fila(q, instancia=instancia)
            or nega_morada_leitura(
                q, instancia=instancia, bancada_dir=bancada, release_dir=release
            )
            is not None
        )

    max_bytes = opcoes.get("max_bytes")
    dpi = opcoes.get("dpi")
    return le(
        p,
        linhas=opcoes.get("linhas"),
        paginas=opcoes.get("paginas"),
        termo=opcoes.get("termo") or "",
        modo=opcoes.get("modo", "texto"),
        encoding=opcoes.get("encoding"),
        dpi=_formatos.DPI_PADRAO if dpi is None else dpi,
        max_bytes=ORCAMENTO_PADRAO if max_bytes is None else max_bytes,
        versao=opcoes.get("versao"),
        offset=opcoes.get("offset"),
        membro=membro_ef,
        nega=_nega,
    )
