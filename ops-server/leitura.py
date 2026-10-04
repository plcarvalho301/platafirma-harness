"""leitura.py — a leitura de arquivo da porta: `ler_arquivo` (spec ler-arquivo, card #3263).

Puro, no molde do `poda.py`: não importa FastMCP, não fala com a rede, não grava auditoria e
não decide autorização. Recebe o caminho já resolvido e autorizado, mais o predicado de
negativa da porta, e devolve dicionário. É o que deixa os testes de contrato (spec §14) e o
bench (§16) rodarem sem subir a porta.

O contrato, em uma frase: a leitura é por linha, corta só em fronteira, e todo retorno diz o
que foi lido, de que versão do arquivo, com que encoding e como continuar.

Invariante (§6), provado pelo C1 e não por detector: partindo de `linhas="1-"` e seguindo
`proximo_args` até `fim do arquivo`, os `conteudo` somados, codificados no encoding decidido,
são os bytes do arquivo — sem furo e sem sobreposição. Vale para arquivo sem byte inválido:
o byte que não decodifica vira U+FFFD, é contado (`invalidos`, `substituições`) e não volta.

Custo de disco, que é o que o bench mede (§16.5):
- a frio, a varredura lê o arquivo uma vez e a própria chamada serve a página desses bytes
  (até SUMARIO_MAX), então a primeira leitura custa uma passada, não duas;
- o sumário dos formatos com analisador sai da mesma passada e fica no índice;
- a quente, a página lê só o que serve: toda página ensina ao índice onde a seguinte começa
  (`Indice.inicios`, `Indice.pontos`), e a leitura com fim pedido avança em passos de
  PASSO bytes até a última linha, em vez de ler o orçamento inteiro.

Biblioteca padrão só (§13.1): o venv `ops` não tem detector de encoding, e a regra da §7.3
não precisa de um.
"""
from __future__ import annotations

import ast
import bisect
import codecs
import difflib
import hashlib
import io
import json
import os
import re
import stat as _stat
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path

# --- réguas da spec (§13.1). Mudar qualquer uma muda o contrato: emenda da spec antes.
ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
VARREDURA_MAX = 256 * 1024 * 1024    # acima disto, versão por stat e varredura até a página
UTF16_MAX = 16 * 1024 * 1024         # transcodificação em memória de UTF-16/32
SUMARIO_MAX = 8 * 1024 * 1024
MARCO = 1_024                        # um marco de posição a cada MARCO linhas
INDICES_MAX = 64                     # entradas do cache de índice
CABECA_TIPO = 8_192                  # bytes que decidem o tipo real
LA_TEM_MAX = 40
# --- réguas de implementação, não de contrato.
BLOCO = 1024 * 1024                  # leitura da varredura (§7.1.1)
PASSO = 1024                         # leitura de quem anda linha a linha: excede no máximo isto
POSICOES_MAX = 4_096                 # posições aprendidas por índice

FIM = "fim do arquivo"
TOOL = "ler_arquivo"

_NL = re.compile(b"\n")
_SURROGATO = re.compile("[\udc80-\udcff]")       # byte inválido sob surrogateescape
_ASCII = bytes(range(128))
_CP1252_INDEFINIDOS = (b"\x81", b"\x8d", b"\x8f", b"\x90", b"\x9d")

# Assinaturas de formato binário (§7.2.1). A extensão nunca decide; só dá nome ao tipo.
_ASSINATURAS = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"), (b"PK\x05\x06", "application/zip"),
    (b"PK\x07\x08", "application/zip"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"),
    (b"\x1f\x8b", "application/gzip"),
    (b"\x7fELF", "application/x-elf"),
    (b"SQLite format 3\x00", "application/vnd.sqlite3"),
)
_ESCRITORIO = {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
               ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
               ".odt": "application/vnd.oasis.opendocument.text",
               ".ods": "application/vnd.oasis.opendocument.spreadsheet",
               ".epub": "application/epub+zip"}
# UTF-32 antes de UTF-16: o BOM de UTF-32 LE começa com o de UTF-16 LE.
_BOMS = ((codecs.BOM_UTF32_LE, "utf-32-le"), (codecs.BOM_UTF32_BE, "utf-32-be"),
         (codecs.BOM_UTF8, "utf-8"),
         (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be"))
# Nome do tipo pela extensão. Tabela fechada de propósito: `mimetypes` lê /etc/mime.types e
# daria nome diferente em host diferente.
_TIPO_POR_EXT = {".py": "text/x-python", ".md": "text/markdown", ".markdown": "text/markdown",
                 ".json": "application/json", ".yaml": "application/yaml",
                 ".yml": "application/yaml", ".toml": "application/toml",
                 ".sh": "text/x-shellscript", ".sql": "application/sql", ".html": "text/html",
                 ".css": "text/css", ".js": "text/javascript", ".mjs": "text/javascript",
                 ".csv": "text/csv", ".xml": "application/xml", ".php": "text/x-php"}
_ANALISADOR = {"text/markdown": "markdown", "text/x-python": "python",
               "application/json": "json"}


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


def varre(fh, ate: int | None = None, *, guarda: bool = False) -> Indice:
    """Uma passada em blocos de 1 MiB: sha256, linhas, marcos e validação de UTF-8.

    `ate`: número de linha. Para depois do bloco em que essa linha começa (arquivo acima de
    VARREDURA_MAX); o índice sai com `linhas_total=None` e a versão fica para quem chama.
    `guarda`: devolve também os bytes lidos em `Indice.dados`, para a chamada a frio servir
    a página sem reler.

    Inválidos sem caminho lento: o decodificador incremental com `surrogateescape` troca cada
    byte inválido por exatamente um surrogato, e o resto é contagem em C. Sequência partida
    entre blocos fica pendente no decodificador e conta no bloco em que fecha.
    """
    h = hashlib.sha256()
    dec = codecs.getincrementaldecoder("utf-8")("surrogateescape")
    nl = pos = multibyte = invalidos = cp_inv = 0
    marcos = [0]
    proximo = MARCO                  # o newline global depois do qual nasce o próximo marco
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
    return Indice(versao=h.hexdigest()[:12], tamanho=pos, linhas_total=total, marcos=marcos,
                  multibyte=multibyte, invalidos=invalidos, cp1252_invalidos=cp_inv,
                  cabeca=cabeca, por_stat=parcial,
                  dados=b"".join(partes) if partes is not None else None)


# Pequena e limitada (Release It!, «cache size limits must be enforced»): 64 índices, LRU.
# A chave é a identidade da versão no disco; arquivo reescrito por rename muda o inode, e
# escrita no lugar muda tamanho ou mtime. O fstat antes e depois (§7.1.5) fecha o resto.
_INDICES: OrderedDict = OrderedDict()
_TRAVA = threading.Lock()


def esvazia_cache() -> None:
    """Para o bench e os testes: a próxima leitura de cada arquivo é a frio."""
    with _TRAVA:
        _INDICES.clear()


def _indice(p: Path, fh, st) -> tuple[Indice, bytes | None]:
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


def indice_de(p, *, abre=open) -> Indice:
    """Índice da versão atual do arquivo, pelo cache de INDICES_MAX entradas."""
    p = Path(p)
    with abre(p, "rb") as fh:
        st = os.fstat(fh.fileno())
        if st.st_size > VARREDURA_MAX:
            return _indice_grande(fh, st, 1)
        return _indice(p, fh, st)[0]


def _indice_grande(fh, st, ate: int) -> Indice:
    """Acima de VARREDURA_MAX: varre só até a linha pedida; versão por stat (§7.1.3)."""
    fh.seek(0)
    idx = varre(fh, ate=ate)
    idx.versao = f"s{st.st_size}-m{st.st_mtime_ns}"
    idx.tamanho = st.st_size
    idx.por_stat = True
    idx.linhas_total = None
    return idx


def _sumario_na_varredura(idx: Indice, nome: str, dados: bytes) -> None:
    """O sumário sai da passada que já leu o arquivo: pedi-lo depois custaria outra
    leitura inteira. Só para formato com analisador e sem BOM de UTF-16/32."""
    tp = tipo_real(idx.cabeca, nome)
    if tp["binario"] or tp["tipo"] not in _ANALISADOR or (tp["bom"] or "utf-8") != "utf-8":
        return
    enc = decide_encoding(idx, tp)
    idx.extra["sumario"] = sumario(tp["tipo"], dados.decode(enc["decidido"], "replace"),
                                   idx.linhas_total)


# ============================================================== tipo e encoding (§7.2, §7.3)
def tipo_real(cabeca: bytes, nome: str) -> dict:
    """Decide pelos bytes; a extensão só dá nome ao tipo de texto."""
    ext = Path(nome).suffix.lower()
    for bom, enc in _BOMS:
        if cabeca.startswith(bom):
            return {"tipo": _TIPO_POR_EXT.get(ext, "text/plain"), "binario": False, "bom": enc}
    for assinatura, tipo in _ASSINATURAS:
        if cabeca.startswith(assinatura):
            if tipo == "application/zip":
                tipo = _ESCRITORIO.get(ext, tipo)
            return {"tipo": tipo, "binario": True, "bom": None}
    if b"\x00" in cabeca:
        return {"tipo": "application/octet-stream", "binario": True, "bom": None}
    return {"tipo": _TIPO_POR_EXT.get(ext, "text/plain"), "binario": False, "bom": None}


def decide_encoding(indice: Indice, tipo: dict, pedido: str | None = None,
                    invalidos: int | None = None) -> dict:
    """As cinco linhas da §7.3, na ordem; a primeira que decide encerra. `invalidos` é a
    contagem já feita no encoding pedido ou no do BOM de UTF-16/32."""
    if pedido:
        return {"decidido": pedido, "por": "pedido", "invalidos": invalidos or 0,
                "julgado": True}
    if tipo.get("bom"):
        inv = indice.invalidos if tipo["bom"] == "utf-8" else (invalidos or 0)
        return {"decidido": tipo["bom"], "por": "bom", "invalidos": inv, "julgado": True}
    # Varredura parcial (acima de VARREDURA_MAX) não viu o arquivo inteiro: decide pelo que
    # viu e não diz «ok» sobre o resto (§7.3.1).
    if indice.invalidos == 0:
        return {"decidido": "utf-8", "por": "estrito", "invalidos": 0,
                "julgado": not indice.por_stat}
    if indice.multibyte > indice.invalidos:
        return {"decidido": "utf-8", "por": "maioria", "invalidos": indice.invalidos,
                "julgado": False}
    return {"decidido": "cp1252", "por": "suposto", "invalidos": indice.cp1252_invalidos,
            "julgado": False}


def _conta_invalidos(fh, enc: str) -> int:
    """Bytes que não decodificam no encoding pedido: uma passada, só quando há pedido."""
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


def _anda_linhas(fh, pos: int, n: int, tamanho: int) -> tuple[int, bytes]:
    """De `pos` (começo de linha), avança `n` linhas em passos de PASSO bytes. Devolve o
    byte em que a linha de destino começa e o que já se leu depois dele (a página o usa)."""
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
    """(linha, byte) conhecidos mais perto antes da linha `a`: marco ou página já servida."""
    k = min((a - 1) // MARCO, len(indice.marcos) - 1)
    linha, byte = k * MARCO + 1, indice.marcos[k]
    with _TRAVA:
        exato = indice.inicios.get(a)
        if exato is not None:
            return a, exato
        for ln, b in indice.inicios.items():                  # limitado a POSICOES_MAX
            if linha < ln <= a:
                linha, byte = ln, b
    return linha, byte


def pagina_linhas(fh, indice: Indice, a: int, b: int | None, orcamento: int) -> Fatia:
    """Linhas inteiras de `a` até `b` (ou até o orçamento), sem partir linha (§4.2).

    Sem `b`, lê o orçamento de uma vez: a página vai até a última linha que coube. Com `b`,
    lê em passos até a linha `b`, para não pagar o orçamento inteiro por um trecho curto.
    """
    linha, byte = _ancora(indice, a)
    ini, sobra = _anda_linhas(fh, byte, a - linha, indice.tamanho)
    fim = _fim_conhecido(indice, a)
    if fim is not None and fim - ini > orcamento:
        # Linha longa que o índice já mede (a última do arquivo, ou a que precede uma
        # posição conhecida): a página sai sem ler nada.
        return Fatia(b"", None, ini, ini,
                     linha_longa={"linha": a, "bytes": fim - ini, "byte_ini": ini})
    buf = bytearray(sobra[:orcamento])
    fh.seek(ini + len(buf))
    pedidas = (b - a + 1) if b else None
    if pedidas is None:
        buf += fh.read(orcamento - len(buf))
    else:
        vistas = buf.count(b"\n")
        while vistas < pedidas and len(buf) < orcamento:
            mais = fh.read(min(PASSO, orcamento - len(buf)))
            if not mais:
                break
            vistas += mais.count(b"\n")
            buf += mais
    no_fim = ini + len(buf) >= indice.tamanho
    corte = 0
    if pedidas:
        m = next(islice(_NL.finditer(buf), pedidas - 1, None), None)
        if m:
            corte = m.end()
    if not corte:
        corte = buf.rfind(b"\n") + 1
        # A última linha do arquivo, sem `\n`, coube inteira: entra (sem passar de `b`).
        if no_fim and corte < len(buf) and (not pedidas or buf.count(b"\n", 0, corte) < pedidas):
            corte = len(buf)
    if corte == 0:
        if ini >= indice.tamanho:
            return Fatia(b"", None, ini, ini)
        # O buffer inteiro é a linha `a`, sem `\n`: o fim dela se procura dali em diante.
        fim = _fim_da_linha(fh, ini + len(buf), indice.tamanho)
        return Fatia(b"", None, ini, ini,
                     linha_longa={"linha": a, "bytes": fim - ini, "byte_ini": ini})
    dados = bytes(buf[:corte])
    n = dados.count(b"\n") + (0 if dados.endswith(b"\n") else 1)
    return Fatia(dados, (a, a + n - 1), ini, ini + corte)


def _fim_conhecido(indice: Indice, a: int) -> int | None:
    """Byte em que a linha `a` termina, se o índice já sabe sem ler."""
    if indice.linhas_total is not None and a == indice.linhas_total:
        return indice.tamanho
    with _TRAVA:
        seguinte = indice.inicios.get(a + 1)
    if seguinte is not None:
        return seguinte
    k, resto = divmod(a, MARCO)
    return indice.marcos[k] if resto == 0 and k < len(indice.marcos) else None


def _fim_da_linha(fh, ini: int, tamanho: int) -> int:
    """Byte depois do primeiro `\\n` a partir de `ini` (ou `tamanho`, se não há)."""
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


def _inicio_antes(fh, pos: int) -> int:
    """Começo da linha que contém o byte `pos - 1`, lendo para trás."""
    while pos > 0:
        de = max(0, pos - BLOCO)
        fh.seek(de)
        blk = fh.read(pos - de)
        i = blk.rfind(b"\n")
        if i >= 0:
            return de + i + 1
        pos = de
    return 0


def pagina_cauda(fh, indice: Indice, n: int, orcamento: int) -> Fatia:
    """As últimas linhas inteiras que cabem no orçamento, até `n` (§4.4)."""
    tam = indice.tamanho
    ini = max(0, tam - orcamento)
    fh.seek(ini)
    buf = fh.read(tam - ini)
    corte = 0
    if ini > 0:                                       # a primeira linha do buffer veio partida
        i = buf.find(b"\n")
        corte = i + 1 if i >= 0 else len(buf)
    corpo = buf[corte:]
    k = corpo.count(b"\n") + (0 if not corpo or corpo.endswith(b"\n") else 1)
    if k > n:
        corte += next(islice(_NL.finditer(corpo), k - n - 1, None)).end()
        k = n
    total = indice.linhas_total
    if k == 0:                                        # a última linha sozinha passa do orçamento
        li = _inicio_antes(fh, ini)
        return Fatia(b"", None, li, li,
                     linha_longa={"linha": total, "bytes": tam - li, "byte_ini": li})
    a = (total - k + 1) if total is not None else None
    return Fatia(buf[corte:], (a, total), ini + corte, tam)


def _e_continuacao(b: int) -> bool:
    return 0x80 <= b <= 0xBF


def _tamanho_da_sequencia(lider: int) -> int:
    return 4 if lider >= 0xF0 else 3 if lider >= 0xE0 else 2 if lider >= 0xC0 else 1


def _continuacoes(buf, i: int) -> int:
    """Bytes de continuação seguidos a partir de `i`, até 3 (o máximo em UTF-8 válido)."""
    n = 0
    while n < 3 and i + n < len(buf) and _e_continuacao(buf[i + n]):
        n += 1
    return n


def pagina_bytes(fh, offset: int, orcamento: int, encoding: str, tamanho: int) -> Fatia:
    """De `offset` até o orçamento, alinhado a caractere em UTF-8 (§5).

    Lê exatamente o orçamento. O começo pula continuação (§5.2); o fim recua até a
    fronteira, e a sequência que não coube vai inteira para a página seguinte. Só lê além
    do orçamento quando ele é menor que um caractere, e então serve o caractere inteiro
    (até 3 bytes acima), para a leitura andar. Sequência de mais de 3 continuações é
    inválida: o corte nela não fabrica nada que já não estivesse lá, e o fim do arquivo
    nunca se corta.
    """
    fh.seek(offset)
    buf = fh.read(orcamento)
    if encoding.replace("_", "-").lower() not in ("utf-8", "utf8"):
        return Fatia(buf, None, offset, offset + len(buf))
    pulados = _continuacoes(buf, 0)
    j = len(buf)
    if offset + len(buf) < tamanho:
        k = len(buf) - 1
        while k > pulados and len(buf) - 1 - k < 3 and _e_continuacao(buf[k]):
            k -= 1
        if k >= pulados and buf[k] >= 0xC0 and k + _tamanho_da_sequencia(buf[k]) > len(buf):
            j = k
        if j <= pulados:
            buf += fh.read(7)
            pulados = _continuacoes(buf, 0)
            j = min(len(buf), pulados + 1 + _continuacoes(buf, pulados + 1))
    ini = offset + pulados
    return Fatia(buf[pulados:j], None, ini, offset + j, pulados=pulados)


def _linha_do_byte(fh, indice: Indice, offset: int) -> int | None:
    """A linha que contém `offset`, pela âncora conhecida mais perto antes dele."""
    k = bisect.bisect_right(indice.marcos, offset) - 1
    base, linha = indice.marcos[k], k * MARCO + 1
    with _TRAVA:
        exato = indice.pontos.get(offset)
        if exato is not None:
            return exato
        for b, ln in indice.pontos.items():                   # limitado a POSICOES_MAX
            if base < b <= offset:
                base, linha = b, ln
    if indice.por_stat and base == indice.marcos[-1] and offset > base:
        return None                       # além do que a varredura parcial viu
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


def _sumario_markdown(linhas: list[str], total: int) -> list:
    i0 = 0
    if linhas and linhas[0].rstrip("\r") == "---":            # cabeçalho YAML do topo
        for j in range(1, len(linhas)):
            if linhas[j].rstrip("\r") in ("---", "..."):
                i0 = j + 1
                break
    cerca = None
    titulos = []
    for i in range(i0, len(linhas)):
        lin = linhas[i].rstrip("\r")
        m = _CERCA.match(lin)
        if m:
            marca = m.group(1)
            if cerca is None:
                cerca = marca
            elif marca[0] == cerca[0] and len(marca) >= len(cerca) and lin.strip() == marca:
                cerca = None
            continue
        if cerca is None:
            m = _ATX.match(lin)
            if m:
                titulos.append((len(m.group(1)), (m.group(2) or "").strip(), i + 1))
    itens = []
    for j, (nivel, titulo, ini) in enumerate(titulos):
        fim = next((ini2 - 1 for nivel2, _t, ini2 in titulos[j + 1:] if nivel2 <= nivel), total)
        itens.append([nivel, titulo, ini, fim])
    return itens


_DEFS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _item_py(no, nivel: int) -> list:
    if isinstance(no, ast.ClassDef):
        rotulo = f"class {no.name}"
    else:
        rotulo = f"{'async def' if isinstance(no, ast.AsyncFunctionDef) else 'def'} {no.name}"
    return [nivel, rotulo, min([d.lineno for d in no.decorator_list] + [no.lineno]),
            no.end_lineno]


def _sumario_python(texto: str) -> list:
    itens = []
    for no in ast.parse(texto).body:
        if isinstance(no, _DEFS):
            itens.append(_item_py(no, 1))
            itens.extend(_item_py(f, 2) for f in no.body if isinstance(f, _DEFS))
    return itens


_JSON_TIPO = ((bool, "booleano"), (dict, "objeto"), (list, "lista"), (str, "texto"),
              (int, "número"), (float, "número"), (type(None), "nulo"))


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
    """Só a estrutura que o analisador do formato declara (§8.1). Devolve (itens, motivo):
    tipo sem analisador ou arquivo que o analisador rejeita sai `None`, nunca adivinhado."""
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
def _entradas(p: Path, nega) -> tuple[list[tuple[str, int | None]], int]:
    """[(nome com `/` se diretório, bytes ou None)], em ordem, e quantas a negativa tirou."""
    nomes, ocultas = [], 0
    with os.scandir(p) as it:
        for e in it:
            if nega and nega(Path(e.path)):
                ocultas += 1
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


def lista_diretorio(p, nega=None) -> tuple[str, int, int]:
    """(texto da listagem, entradas, ocultas pela negativa). Uma entrada por linha:
    `nome/` para diretório, `nome  <bytes>` para arquivo (§9.2)."""
    nomes, ocultas = _entradas(Path(p), nega)
    texto = "".join(f"{n}  {t}\n" if t is not None else f"{n}\n" for n, t in nomes)
    return texto, len(nomes), ocultas


def vizinhanca(p, nega=None) -> dict:
    """Para o caminho que não existe: o ancestral mais próximo que existe, o que há nele e
    os nomes parecidos com o que faltou. Ancestral sob negativa não lista nada (§9.1.4)."""
    p = Path(p)
    anc = p.parent
    while not anc.exists() and anc != anc.parent:
        anc = anc.parent
    r = {"existe_ate": str(anc)}
    if not anc.is_dir() or (nega and nega(anc)):
        return r
    try:
        nomes, _ocultas = _entradas(anc, nega)
    except OSError:
        return r
    faltou = p.relative_to(anc).parts[0]
    r.update(la_tem=[n for n, _t in nomes[:LA_TEM_MAX]], la_tem_total=len(nomes),
             parecidos=difflib.get_close_matches(faltou, [n.rstrip("/") for n, _t in nomes],
                                                 n=3))
    return r


# ============================================================== retorno (§3.2)
def _n(x) -> str:
    return "?" if x is None else f"{x:,}".replace(",", ".")


def cabecalho(*, curto: str, tipo: str, faixa: str, servidos: int | None, total: int,
              encoding: dict | None, substituicoes: int | None, versao: str,
              por_stat: bool = False, avisos: tuple = (), depois: tuple = ()) -> str:
    """Sempre nesta ordem: caminho, tipo, faixa e total, bytes servidos e total, encoding e
    origem, substituições, versão. Aviso abre a linha, em maiúsculas (§3.2.2)."""
    partes = [*avisos, curto, tipo, faixa]
    if servidos is not None:
        partes.append(f"{_n(servidos)} de {_n(total)} bytes")
    if encoding:
        partes.append(f"{encoding['decidido']} ({encoding['por']})")
    if substituicoes is not None:
        partes.append(f"substituições {substituicoes}")
    partes.append(f"versão por stat {versao}" if por_stat else f"versão {versao}")
    return " · ".join([*partes, *depois])


def continuacao(args: dict | None) -> tuple[str, dict | None]:
    """(`proximo`, `proximo_args`): a chamada literal da página seguinte e a mesma como
    objeto; no fim, `fim do arquivo` e nada."""
    if not args:
        return FIM, None
    corpo = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items())
    return f"{TOOL}({corpo})", args


def _erro(msg: str, classe: str, **extra) -> dict:
    return {"erro": msg, **extra, "classe_erro": classe}


def _faixa(linhas) -> tuple | dict:
    """(a, b, cauda) de `"a-b"`, `"a-"` ou `"-n"`, base 1."""
    if linhas in (None, ""):
        return 1, None, None
    m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d*)\s*", str(linhas))
    if m:
        a, b = int(m.group(1)), int(m.group(2)) if m.group(2) else None
        if a >= 1 and (b is None or b >= a):
            return a, b, None
    m = re.fullmatch(r"\s*-\s*(\d+)\s*", str(linhas))
    if m and int(m.group(1)) >= 1:
        return None, None, int(m.group(1))
    return _erro(f'linhas={linhas!r}: use "a-b", "a-" ou "-n" (base 1, extremos incluídos)',
                 "gramatica", cura=f'{TOOL}(caminho=…, linhas="1-")')


def _alem_do_fim(p: Path, total) -> dict:
    return _erro("faixa além do fim", "faixa", caminho=str(p), linhas_total=total,
                 cura=f'{TOOL}(caminho="{p}", linhas="-100")')


# ============================================================== a leitura (§13.1, `le`)
def le(p, *, linhas=None, modo: str = "texto", max_bytes: int = ORCAMENTO_PADRAO,
       versao: str | None = None, offset: int | None = None, encoding: str | None = None,
       nega=None, curto: str | None = None, abre=open) -> dict:
    """O retorno da §3.2, sem poda.

    `nega(Path) -> bool` é a negativa da porta, aplicada a entrada de diretório e a
    ancestral; o próprio `p` já chega autorizado. `abre` é o `open` (o bench conta por ele
    os bytes lidos). Erro volta com `classe_erro` (caminho, faixa, binario, gramatica,
    recusado), que a porta tira do retorno e grava na auditoria.
    """
    p = Path(p)
    curto = curto or str(p)
    if modo not in ("texto", "sumario"):
        return _erro(f'modo={modo!r}: use "texto" ou "sumario"', "gramatica")
    if modo == "sumario" and (linhas not in (None, "") or offset is not None):
        return _erro('modo="sumario" não aceita linhas nem offset: o sumário é do arquivo '
                     "inteiro, e a faixa de cada item se lê depois por linhas", "gramatica",
                     cura=f'{TOOL}(caminho="{p}", modo="sumario")')
    faixa = None
    if offset is None:
        faixa = _faixa(linhas)
        if isinstance(faixa, dict):
            return faixa
    elif isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        return _erro(f"offset={offset!r}: inteiro a partir de 0", "gramatica")
    orcamento = max(1, min(int(max_bytes or ORCAMENTO_PADRAO), ORCAMENTO_MAX))
    if encoding:
        try:
            encoding = codecs.lookup(encoding).name
        except LookupError:
            return _erro(f"encoding={encoding!r} desconhecido", "gramatica")
    try:
        st = os.stat(p)
    except (FileNotFoundError, NotADirectoryError):
        v = vizinhanca(p, nega)
        return _erro("não existe", "caminho", caminho=str(p), **v,
                     cura=f'{TOOL}(caminho="{v["existe_ate"]}")')
    except OSError as e:
        return _erro(f"não consegui ler: {e.strerror}", "caminho", caminho=str(p))
    if _stat.S_ISDIR(st.st_mode):
        return _le_diretorio(p, curto, faixa, orcamento, nega)
    if not _stat.S_ISREG(st.st_mode):
        return _erro("existe mas não é arquivo comum (socket, fifo ou dispositivo)", "caminho",
                     caminho=str(p))
    pedido_bytes = max_bytes if max_bytes and max_bytes != ORCAMENTO_PADRAO else None
    with abre(p, "rb") as fh:
        for _tentativa in range(2):
            st0 = os.fstat(fh.fileno())
            r = _le_arquivo(fh, p, st0, curto=curto, faixa=faixa, modo=modo,
                            orcamento=orcamento, versao=versao, offset=offset,
                            pedido=encoding, pedido_bytes=pedido_bytes)
            st1 = os.fstat(fh.fileno())
            if (st0.st_size, st0.st_mtime_ns) == (st1.st_size, st1.st_mtime_ns):
                break
        else:                                             # mudou durante a leitura, duas vezes
            if "cabecalho" in r:
                r["cabecalho"] = "ARQUIVO INSTÁVEL · " + r["cabecalho"]
            r["instavel"] = True
    if offset is not None and linhas not in (None, "") and "cabecalho" in r:
        r["cabecalho"] += " · linhas ignorado: vale offset"
    return r


def _le_diretorio(p: Path, curto: str, faixa, orcamento: int, nega) -> dict:
    if faixa is None:
        return _erro("offset não se aplica a diretório: a listagem pagina por linhas",
                     "gramatica", cura=f'{TOOL}(caminho="{p}")')
    try:
        texto, n, ocultas = lista_diretorio(p, nega)
    except OSError as e:
        return _erro(f"não consegui listar: {e.strerror}", "caminho", caminho=str(p))
    dados = texto.encode("utf-8", "surrogateescape")
    fh = io.BytesIO(dados)
    idx = varre(fh)
    a, b, cauda = faixa
    if n == 0:
        f = Fatia(b"", None, 0, 0)
    elif cauda:
        f = pagina_cauda(fh, idx, cauda, orcamento)
    elif a > n:
        return _alem_do_fim(p, n)
    else:
        f = pagina_linhas(fh, idx, a, b, orcamento)
    if f.linha_longa:                     # entrada maior que o orçamento: sai inteira
        ll = f.linha_longa
        f = Fatia(dados[ll["byte_ini"]:ll["byte_ini"] + ll["bytes"]],
                  (ll["linha"], ll["linha"]), ll["byte_ini"], ll["byte_ini"] + ll["bytes"])
    partes = [curto, f"diretório · {_n(n)} entradas"]
    if f.linhas:
        partes.append(f"linhas {_n(f.linhas[0])}–{_n(f.linhas[1])}")
    if ocultas:
        partes.append(f"{_n(ocultas)} fora por negativa")
    partes.append(f"versão {idx.versao}")
    seguinte = f.linhas[1] + 1 if f.linhas and f.linhas[1] < n else None
    proximo, proximo_args = continuacao(
        {"caminho": str(p), "linhas": f"{seguinte}-"} if seguinte else None)
    r = {"cabecalho": " · ".join(partes), "conteudo": f.dados.decode("utf-8", "replace"),
         "proximo": proximo, "proximo_args": proximo_args, "caminho": str(p),
         "linhas": list(f.linhas) if f.linhas else None, "linhas_total": n,
         "bytes": [f.ini, f.fim], "bytes_total": len(dados), "versao": idx.versao,
         "diretorio": True, "ocultas": ocultas}
    return {k: v for k, v in r.items() if v is not None}


def _transcodifica(fh, enc: str) -> tuple[bytes, int]:
    """UTF-16/32 com BOM vira UTF-8 em memória (§7.2.3). O BOM fica como U+FEFF no texto:
    é o que faz as páginas, recodificadas no encoding decidido, darem o arquivo."""
    fh.seek(0)
    texto = fh.read().decode(enc, "surrogateescape")
    inv = 0
    if _SURROGATO.search(texto):
        inv = len(_SURROGATO.findall(texto))
        texto = _SURROGATO.sub("�", texto)
    return texto.encode("utf-8"), inv


def _le_arquivo(fh, p: Path, st, *, curto, faixa, modo, orcamento, versao, offset, pedido,
                pedido_bytes) -> dict:
    if st.st_size > VARREDURA_MAX:
        idx, dados = _indice_grande(fh, st, (faixa[0] or 1) if faixa else 1), None
    else:
        idx, dados = _indice(p, fh, st)
    tp = tipo_real(idx.cabeca, p.name)
    if tp["binario"]:
        return {"recusado": True, "motivo": "binario", "tipo": tp["tipo"], "caminho": str(p),
                "bytes_total": idx.tamanho, "versao": idx.versao,
                "cura": (f"{tp['tipo']} não se lê como texto pela porta, e a porta não converte "
                         "formato. Obra do acervo se lê por `acervo ler biblioteca impressao "
                         "<obra>`."),
                "classe_erro": "binario"}

    # Fonte das páginas: os bytes que a varredura acabou de ler (a frio), o próprio arquivo
    # (a quente), ou o UTF-8 transcodificado de UTF-16/32.
    fonte, fidx, depois = (io.BytesIO(dados) if dados is not None else fh), idx, ()
    inv = None
    if tp["bom"] and tp["bom"] != "utf-8":
        if idx.tamanho > UTF16_MAX:
            return {"recusado": True, "motivo": f"{tp['bom']} acima de 16 MiB",
                    "caminho": str(p), "bytes_total": idx.tamanho, "versao": idx.versao,
                    "cura": "a porta transcodifica UTF-16/32 em memória só até 16 MiB",
                    "classe_erro": "recusado"}
        utf8, inv = _transcodifica(fonte, tp["bom"])
        fonte = io.BytesIO(utf8)
        fidx = varre(fonte)
        fidx.versao = idx.versao
        depois = (f"transcodificado de {tp['bom'][:6]}",)
    if pedido:
        inv = idx.extra.get(("invalidos", pedido))
        if inv is None:
            inv = idx.extra[("invalidos", pedido)] = _conta_invalidos(fh, pedido)
    enc = decide_encoding(idx, tp, pedido, inv)
    leitura_enc = "utf-8" if fidx is not idx else enc["decidido"]

    avisos, mudou = [], None
    if versao and versao != idx.versao:
        mudou = {"de": versao, "para": idx.versao}
        avisos.append(f"ARQUIVO MUDOU desde a versão {versao} · as linhas lidas antes podem "
                      "ter mudado")
    if not enc["julgado"]:
        avisos.append("NÃO JULGADO")
    base = {"caminho": str(p), "bytes_total": idx.tamanho, "versao": idx.versao,
            "encoding": enc}
    extra_args = {}
    if pedido_bytes:
        extra_args["max_bytes"] = orcamento
    if pedido:
        extra_args["encoding"] = pedido

    if modo == "sumario":
        return _le_sumario(fonte, fidx, tp, curto, orcamento, leitura_enc, base, avisos,
                           mudou, usa_cache=not pedido and fidx is idx)

    if idx.tamanho == 0:
        r = {"cabecalho": " · ".join([*avisos, curto, tp["tipo"], "arquivo vazio (0 bytes)",
                                      f"versão {idx.versao}"]),
             "conteudo": "", "proximo": FIM, **base, "linhas_total": 0, "bytes": [0, 0]}
        return _com_mudou(r, mudou)

    if offset is not None:
        if offset > fidx.tamanho:
            return _erro("offset além do fim", "faixa", caminho=str(p),
                         bytes_total=fidx.tamanho, cura=f'{TOOL}(caminho="{p}", linhas="-100")')
        f = pagina_bytes(fonte, offset, orcamento, leitura_enc, fidx.tamanho)
        f.linha_inicio = _linha_do_byte(fonte, fidx, f.ini)
    else:
        a, b, cauda = faixa
        if cauda:
            f = pagina_cauda(fonte, fidx, cauda, orcamento)
        else:
            if fidx.linhas_total is not None and a > fidx.linhas_total:
                return _alem_do_fim(p, fidx.linhas_total)
            f = pagina_linhas(fonte, fidx, a, b, orcamento)
            if f.ini >= fidx.tamanho and not f.dados and not f.linha_longa:
                return _alem_do_fim(p, None)
    return _monta_pagina(f, fidx, tp, p, curto, faixa, enc, leitura_enc, base, avisos,
                         depois, mudou, extra_args)


def _com_mudou(r: dict, mudou) -> dict:
    if mudou:
        r["mudou"] = mudou
    return r


def _monta_pagina(f: Fatia, idx: Indice, tp: dict, p: Path, curto: str, faixa, enc: dict,
                  leitura_enc: str, base: dict, avisos: list, depois: tuple, mudou,
                  extra_args: dict) -> dict:
    total_l = idx.linhas_total
    if f.linha_longa:
        ll = f.linha_longa
        idx.aprende(ll["linha"], ll["byte_ini"], inicio=True)
        cab = cabecalho(curto=curto, tipo=tp["tipo"],
                        faixa=(f"linha {_n(ll['linha'])} tem {_n(ll['bytes'])} bytes, acima "
                               "do orçamento · continua por bytes"),
                        servidos=0, total=idx.tamanho, encoding=enc, substituicoes=0,
                        versao=idx.versao, por_stat=idx.por_stat,
                        avisos=(*avisos, "LINHA LONGA"), depois=depois)
        proximo, proximo_args = continuacao({"caminho": str(p), "offset": ll["byte_ini"],
                                             "versao": idx.versao, **extra_args})
        return _com_mudou({"cabecalho": cab, "conteudo": "", "proximo": proximo,
                           "proximo_args": proximo_args, **base, "linhas_total": total_l,
                           "bytes": [ll["byte_ini"], ll["byte_ini"]], "linha_longa": ll},
                          mudou)

    texto = f.dados.decode(leitura_enc, "replace")
    no_fim = f.fim >= idx.tamanho
    if f.linhas is not None:                                  # por linhas (§4)
        a, b_real = f.linhas
        faixa_txt = f"linhas {_n(a)}–{_n(b_real)} de {_n(total_l)}"
        if b_real is not None:
            idx.aprende(b_real + 1, f.fim, inicio=True)
        pedido_b = faixa[1] if faixa else None
        if no_fim or b_real is None:
            prox = None
        elif pedido_b and b_real < pedido_b:
            prox = {"caminho": str(p), "linhas": f"{b_real + 1}-{pedido_b}"}
        else:
            prox = {"caminho": str(p), "linhas": f"{b_real + 1}-"}
        linhas_campo = [a, b_real]
    else:                                                     # por bytes (§5)
        faixa_txt = f"bytes {_n(f.ini)}–{_n(f.fim)} de {_n(idx.tamanho)}"
        if f.linha_inicio is not None:
            faixa_txt += f" · começa na linha {_n(f.linha_inicio)}"
            idx.aprende(f.linha_inicio + f.dados.count(b"\n"), f.fim,
                        inicio=f.dados.endswith(b"\n"))
        if f.pulados:
            faixa_txt += f" · {f.pulados} bytes pulados até a fronteira de caractere"
        prox = None if no_fim else {"caminho": str(p), "offset": f.fim}
        linhas_campo = None
    if prox:
        prox["versao"] = idx.versao
        prox.update(extra_args)
    proximo, proximo_args = continuacao(prox)
    cab = cabecalho(curto=curto, tipo=tp["tipo"], faixa=faixa_txt, servidos=len(f.dados),
                    total=idx.tamanho, encoding=enc, substituicoes=texto.count("�"),
                    versao=idx.versao, por_stat=idx.por_stat, avisos=tuple(avisos),
                    depois=depois)
    r = {"cabecalho": cab, "conteudo": texto, "proximo": proximo,
         "proximo_args": proximo_args, **base, "linhas": linhas_campo,
         "linhas_total": total_l, "bytes": [f.ini, f.fim]}
    if (f.ini > 0 or not no_fim) and tp["tipo"] in _ANALISADOR and idx.tamanho <= SUMARIO_MAX:
        r["sumario"] = f'{TOOL}(caminho="{p}", modo="sumario")'
    return _com_mudou({k: v for k, v in r.items() if v is not None or k == "linhas_total"},
                      mudou)


def _cabe(itens: list, orcamento: int) -> bool:
    return len(json.dumps(itens, ensure_ascii=False).encode()) <= orcamento


def _le_sumario(fh, idx: Indice, tp: dict, curto: str, orcamento: int, enc_leitura: str,
                base: dict, avisos: list, mudou, *, usa_cache: bool) -> dict:
    por = _ANALISADOR.get(tp["tipo"])
    if idx.tamanho > SUMARIO_MAX:
        itens, motivo = None, "arquivo acima de 8 MiB: sumário não se calcula"
    elif not por:
        itens, motivo = None, f"sem analisador de sumário para {tp['tipo']}"
    elif usa_cache and "sumario" in idx.extra:
        itens, motivo = idx.extra["sumario"]
    else:
        fh.seek(0)
        itens, motivo = sumario(tp["tipo"], fh.read().decode(enc_leitura, "replace"),
                                idx.linhas_total)
    partes = [*avisos, curto, tp["tipo"], "sumário"]
    if itens is not None:
        # Maior que o orçamento: sai primeiro o nível mais fundo (§8.3); só no primeiro
        # nível ainda maior, os primeiros itens que cabem, declarados.
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
        partes.append(f"{_n(len(servir))} itens")
        if nota:
            partes.append(nota)
        itens = servir
    else:
        partes.append(f"sem sumário: {motivo}")
    partes.append(f"versão {idx.versao}")
    r = {"cabecalho": " · ".join(partes), "sumario": itens, "sumario_por": por, **base,
         "linhas_total": idx.linhas_total}
    if itens is None:
        r["motivo"] = motivo
    return _com_mudou(r, mudou)


# ============================================================== lote (§10) e apelido (§12)
def servidos(r: dict) -> int:
    """Bytes que o item serviu à fita: o texto da página, não o tamanho do arquivo."""
    t = r.get("conteudo", r.get("content"))
    if isinstance(t, str):
        return len(t.encode("utf-8", "replace"))
    if isinstance(r.get("sumario"), list):
        return len(json.dumps(r["sumario"], ensure_ascii=False).encode())
    return 0


def lote(itens: list, le_item, teto: int) -> dict:
    """Itens em ordem; o teto conta bytes servidos, e o item que não coube volta
    `omitido_por_teto`. Erro num item não derruba os outros (§10)."""
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


def como_read_file(r: dict) -> dict:
    """O retorno da `ler_arquivo` nas chaves do apelido `read_file` (§12.2).

    `content` TOMA o lugar de `conteudo`, em vez de somar-se a ele: o apelido é a tool que
    toda fita viva ainda chama, e servir o texto duas vezes dobraria o custo de cada leitura
    até o apelido sair. Os demais campos novos ficam.
    """
    if "caminho" in r:
        r["path"] = r.pop("caminho")
    if "conteudo" not in r:
        return r
    ini, fim = r["bytes"]
    acabou = r.get("proximo_args") is None
    r["content"] = r.pop("conteudo")
    r.update(truncated=not acabou, next_offset=None if acabou else fim,
             bytes_lidos=fim - ini, offset=ini)
    return r
