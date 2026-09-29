"""card #3189, ato temporário: leitor de PDF do censo.

Dos bytes: cabeçalho, linearização e cadeia de revisões. Com pypdf: catálogo, Info/XMP,
sumário embutido, estrutura marcada e, por página, texto, fontes sem caminho para Unicode,
texto invisível e área de imagem. Nunca levanta exceção: falha vira `erro` ou lacuna.
"""
from __future__ import annotations

import contextlib
import html.entities
import importlib.metadata
import io
import logging
import re
import statistics
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

# Limiares de decisão de dados, sem fonte no acervo (card #3189).
LIMIAR_OCR_CARACTERES = 500       # abaixo disto a página tem pouco texto útil
LIMIAR_OCR_AREA = 0.5             # imagem cobrindo mais da metade da página
LIMIAR_SEM_CAMINHO = 0.20         # fração de códigos em fonte sem caminho para Unicode

# Tetos de proteção.
JANELA_CABECALHO = 1024
TETO_ELOS_XREF = 1000
TETO_NOS_PAGINAS = 500_000
TETO_PROFUNDIDADE_PAGINAS = 64
TETO_ITENS_SUMARIO = 200_000
TETO_NOS_ESTRUTURA = 300_000
TETO_NOS_NOMES = 100_000
TETO_LISTA = 2000
TETO_TEXTO = 4_000_000
TETO_TEXTO_PAGINA = 200_000
TETO_XMP = 4_000_000
TETO_DICIONARIO_BYTES = 65_536
PROFUNDIDADE_FORM = 5
PRAZO_PADRAO_S = 60.0
CAIXA_PADRAO = (612.0, 792.0)      # Letter, quando a MediaBox não se lê

_SUBSTITUICAO = chr(0xFFFD)
_BRANCOS = bytes([0, 9, 10, 12, 13, 32])
_IDENTIDADE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_TIPOS_ESTRUTURA = ("H", "H1", "H2", "H3", "H4", "H5", "H6", "Title", "P", "Table", "Figure", "TOC")
_HERDAVEIS = ("/Resources", "/MediaBox", "/CropBox", "/Rotate")
_BASES_COM_CAMINHO = frozenset((
    "/WinAnsiEncoding", "/MacRomanEncoding", "/StandardEncoding", "/MacExpertEncoding", "/PDFDocEncoding",
))
_CMAPS_IDENTIDADE = frozenset(("/Identity-H", "/Identity-V"))
_COLECOES_ASIATICAS = frozenset(("GB1", "CNS1", "Japan1", "Korea1"))
# Nomes tipográficos da AGL que não estão em html.entities (aproximação; ver lacunas["agl"]).
_NOMES_TIPOGRAFICOS = frozenset((
    "space exclam quotedbl numbersign dollar percent ampersand quotesingle parenleft parenright asterisk "
    "plus comma hyphen period slash zero one two three four five six seven eight nine colon semicolon "
    "less equal greater question at bracketleft backslash bracketright asciicircum underscore grave "
    "quoteleft quoteright braceleft bar braceright asciitilde endash emdash bullet ellipsis quotedblleft "
    "quotedblright quotesinglbase quotedblbase dagger daggerdbl perthousand guilsinglleft guilsinglright "
    "guillemotleft guillemotright fi fl ff ffi ffl florin fraction trademark copyright registered section "
    "paragraph degree plusminus multiply divide minus Euro sterling yen cent currency brokenbar dotlessi "
    "dotlessj circumflex tilde macron breve dotaccent dieresis ring cedilla hungarumlaut ogonek caron "
    "ordfeminine ordmasculine exclamdown questiondown logicalnot mu onequarter onehalf threequarters "
    "onesuperior twosuperior threesuperior germandbls ae AE oe OE oslash Oslash lslash Lslash eth Eth thorn "
    "Thorn Scaron scaron Zcaron zcaron Ydieresis nbspace sfthyphen middot periodcentered acute bardbl minute "
    "second infinity lessequal greaterequal notequal approxequal summation product radical integral "
    "partialdiff Delta Omega pi lozenge"
).split())

_RE_CABECALHO = re.compile(rb"%PDF-(\d+)\.(\d+)")
_RE_PRIMEIRO_OBJ = re.compile(rb"\d+\s+\d+\s+obj\s*<<")
_RE_OBJ = re.compile(rb"\d+\s+\d+\s+obj")
_RE_STARTXREF = re.compile(rb"startxref\s+(\d+)")
_RE_PREV = re.compile(rb"/Prev\s+(\d+)")
_RE_LINEARIZED = re.compile(rb"/Linearized\s+[\d.]+")
_RE_L = re.compile(rb"/L(?![A-Za-z])\s*(\d+)")
_RE_E = re.compile(rb"/E(?![A-Za-z])\s*(\d+)")
_RE_TOKENS = re.compile(rb"<<|>>|\(|\)|\\.|<[^<>]*>", re.S)
_RE_UNI = re.compile(r"uni(?:[0-9A-F]{4})+")
_RE_U = re.compile(r"u[0-9A-F]{4,6}")
_RE_DATA_ISO = re.compile(
    r"^\s*(\d{4})(?:-(\d{2})(?:-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(?:[.,]\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?)?)?\s*$"
)
_RE_DATA_PDF = re.compile(
    r"^\s*(?:D:)?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?\s*(?:(Z)|([+-])(\d{2})?'?(\d{2})?'?)?", re.I
)
_RE_VERSAO = re.compile(r"^(?P<nome>\S.*?)[\s/_-]+[vV]?(?P<versao>\d+(?:\.\d+)+)(?![\w.])")


class _PrazoEsgotado(BaseException):
    """Interrompe a extração de uma página quando o prazo do `ler` acaba (uso interno)."""


# ---------------------------------------------------------------- utilidades

def _uma_linha(exc):
    texto = "{}: {}".format(type(exc).__name__, exc)
    return " ".join(texto.split())[:300]


def _res(valor):
    """Resolve referência indireta; NullObject e falha viram None."""
    try:
        if hasattr(valor, "get_object"):
            valor = valor.get_object()
    except Exception:
        return None
    if type(valor).__name__ == "NullObject":
        return None
    return valor


def _obter(dicionario, chave):
    if not isinstance(dicionario, dict):
        return None
    return _res(dicionario.get(chave))


def _int(valor):
    try:
        if isinstance(valor, bool) or valor is None:
            return None
        return int(valor)
    except (TypeError, ValueError):
        return None


def _verdadeiro(valor):
    return getattr(valor, "value", valor) is True


def _texto(valor):
    if valor is None:
        return None
    if isinstance(valor, bytes):
        valor = valor.decode("latin-1", "replace")
    texto = str(valor).strip()
    return texto or None


def _nome(valor):
    texto = _texto(valor)
    return texto[1:] if texto and texto.startswith("/") else texto


def _versao_como_tupla(texto):
    try:
        partes = texto.split(".")
        return (int(partes[0]), int(partes[1]))
    except (AttributeError, IndexError, ValueError):
        return None


def _mediana(valores, casas=1):
    if not valores:
        return None
    m = statistics.median(valores)
    if float(m).is_integer():
        return int(m)
    return round(float(m), casas)


def _lista_teto(paginas):
    return paginas[:TETO_LISTA], len(paginas)


@contextlib.contextmanager
def _pypdf_calado():
    """Silencia o log do pypdf só durante a leitura e devolve o nível depois."""
    log = logging.getLogger("pypdf")
    antes = log.level
    log.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        log.setLevel(antes)


# ---------------------------------------------------------------- datas

def _partes_data(bruto):
    """Devolve (ano, mês, dia, hora, minuto, segundo, fuso) até onde a data for válida."""
    texto = _texto(bruto)
    if not texto:
        return None
    m = _RE_DATA_ISO.match(texto)
    fuso = None
    if m:
        numeros = [int(g) if g else None for g in m.groups()[:6]]
        if m.group(7):
            fuso = _fuso_iso(m.group(7))
    else:
        m = _RE_DATA_PDF.match(texto)
        if not m:
            return None
        numeros = [int(g) if g else None for g in m.groups()[:6]]
        fuso = _fuso_pdf(m)
    limites = ((1, 9999), (1, 12), (1, 31), (0, 23), (0, 59), (0, 59))
    validos = []
    for numero, (baixo, alto) in zip(numeros, limites):
        if numero is None or not baixo <= numero <= alto:
            break
        validos.append(numero)
    if not validos:
        return None
    validos += [None] * (6 - len(validos))
    return tuple(validos) + (fuso,)


def _fuso_iso(texto):
    if texto == "Z":
        return "Z"
    limpo = texto.replace(":", "")
    return "{}{}:{}".format(limpo[0], limpo[1:3], limpo[3:5])


def _fuso_pdf(m):
    if m.group(7):
        return "Z"
    if m.group(8):
        return "{}{}:{}".format(m.group(8), m.group(9) or "00", m.group(10) or "00")
    return None


def _data_iso(bruto):
    """Data do PDF (`D:YYYYMMDDHHmmSSOHH'mm'`) ou ISO parcial, em ISO 8601; None se não se lê."""
    partes = _partes_data(bruto)
    if not partes:
        return None
    ano, mes, dia, hora, minuto, segundo, fuso = partes
    saida = "{:04d}".format(ano)
    if mes is not None:
        saida += "-{:02d}".format(mes)
    if dia is not None:
        saida += "-{:02d}".format(dia)
    if hora is not None:
        saida += "T{:02d}:{:02d}".format(hora, minuto or 0)
        if segundo is not None:
            saida += ":{:02d}".format(segundo)
        if fuso:
            saida += fuso
    return saida


def _data_hora(bruto):
    """Data como datetime com fuso (sem fuso vale UTC), para comparar duas datas."""
    partes = _partes_data(bruto)
    if not partes:
        return None
    ano, mes, dia, hora, minuto, segundo, fuso = partes
    deslocamento = timedelta(0)
    if fuso and fuso != "Z":
        sinal = -1 if fuso[0] == "-" else 1
        deslocamento = sinal * timedelta(hours=int(fuso[1:3]), minutes=int(fuso[4:6]))
    try:
        return datetime(ano, mes or 1, dia or 1, hora or 0, minuto or 0, segundo or 0,
                        tzinfo=timezone(deslocamento))
    except ValueError:
        return None


# ---------------------------------------------------------------- bytes

def _dicionario_em(dados, pos, limite=TETO_DICIONARIO_BYTES):
    """Bytes do primeiro <<...>> balanceado a partir de `pos` (ignora o que há em strings)."""
    ini = dados.find(b"<<", pos, pos + limite)
    if ini < 0:
        return None
    prof = 0
    em_string = 0
    for m in _RE_TOKENS.finditer(dados, ini, ini + limite):
        token = m.group()
        if em_string:
            if token == b"(":
                em_string += 1
            elif token == b")":
                em_string -= 1
        elif token == b"(":
            em_string = 1
        elif token == b"<<":
            prof += 1
        elif token == b">>":
            prof -= 1
            if prof == 0:
                return dados[ini:m.end()]
    return None


def _achar_cabecalho(dados):
    """(offset, versão) de `%PDF-x.y` nos primeiros 1024 bytes (ISO 7.5.2, Tabela 29)."""
    janela = dados[:JANELA_CABECALHO]
    achado = janela.find(b"%PDF-")
    if achado < 0:
        return None, None
    m = _RE_CABECALHO.match(janela, achado)
    versao = "{}.{}".format(int(m.group(1)), int(m.group(2))) if m else None
    return achado, versao


def _linearizacao(dados, origem):
    """Lê o primeiro objeto (ISO Anexo F): {presente, l, e}. Linearizado exige /L = tamanho."""
    trecho = dados[origem:origem + 2048]
    m = _RE_PRIMEIRO_OBJ.search(trecho)
    vazio = {"presente": False, "l": None, "e": None}
    if not m:
        return vazio
    dic = _dicionario_em(trecho, m.end() - 2) or b""
    if not _RE_LINEARIZED.search(dic):
        return vazio
    achado_l = _RE_L.search(dic)
    achado_e = _RE_E.search(dic)
    return {
        "presente": True,
        "l": int(achado_l.group(1)) if achado_l else None,
        "e": int(achado_e.group(1)) if achado_e else None,
    }


def _secao_xref(dados, pos):
    """Lê uma seção xref (tabela+trailer ou xref stream) e devolve o /Prev (ou None); False se ilegível."""
    n = len(dados)
    if pos < 0 or pos >= n:
        return False
    i = pos
    while i < n and dados[i] in _BRANCOS:
        i += 1
    if dados.startswith(b"xref", i):
        t = dados.find(b"trailer", i)
        dic = _dicionario_em(dados, t) if t >= 0 else None
    else:
        m = _RE_OBJ.match(dados, i)
        dic = _dicionario_em(dados, m.end()) if m else None
        if dic is not None and b"/XRef" not in dic:
            dic = None
    if dic is None:
        return False
    prev = _RE_PREV.search(dic)
    return int(prev.group(1)) if prev else None


def _cadeia_xref(dados, base):
    """Cadeia de seções xref pelo último startxref e por /Prev (ISO 7.5.6): (offsets, motivo)."""
    achado = dados.rfind(b"startxref")
    m = _RE_STARTXREF.match(dados, achado) if achado >= 0 else None
    if not m:
        return [], "sem startxref"
    cadeia = []
    vistos = set()
    atual = int(m.group(1))
    while atual is not None:
        if atual in vistos:
            return cadeia, "ciclo em /Prev"
        if len(cadeia) >= TETO_ELOS_XREF:
            return cadeia, "teto de {} elos".format(TETO_ELOS_XREF)
        prev = False
        for deslocamento in ((base, 0) if base else (0,)):
            prev = _secao_xref(dados, atual + deslocamento)
            if prev is not False:
                break
        if prev is False:
            return cadeia, "seção xref ilegível em {}".format(atual)
        vistos.add(atual)
        cadeia.append(atual)
        atual = prev
    return cadeia, None


def _preencher_bytes(dados, pdf, lacunas):
    off, versao = _achar_cabecalho(dados)
    pdf["cabecalho_offset"] = off
    pdf["versao_cabecalho"] = versao
    if off is None:
        lacunas["versao_cabecalho"] = "sem %PDF- nos primeiros {} bytes".format(JANELA_CABECALHO)
    elif versao is None:
        lacunas["versao_cabecalho"] = "%PDF- sem versão legível"
    base = off or 0
    lin = _linearizacao(dados, base)
    pdf["linearizado"] = bool(lin["presente"] and lin["l"] == len(dados))
    cadeia, motivo = _cadeia_xref(dados, base)
    if not cadeia:
        lacunas["revisoes"] = motivo
        return
    n = len(cadeia)
    # Linearizado: seção da primeira página + principal formam uma revisão só (ISO Anexo F).
    if lin["presente"] and n >= 2 and (lin["e"] is None or cadeia[-2] < lin["e"]):
        n -= 1
    pdf["revisoes"] = n
    if motivo:
        lacunas["revisoes"] = "cadeia parcial: " + motivo


# ---------------------------------------------------------------- AGL e fontes

def _componente_agl(nome):
    if nome in _NOMES_TIPOGRAFICOS or nome in html.entities.name2codepoint:
        return True
    if len(nome) == 1 and nome.isascii() and nome.isalnum():
        return True
    return bool(_RE_UNI.fullmatch(nome) or _RE_U.fullmatch(nome))


def _nome_agl(nome):
    """Aproxima "o nome é da Adobe Glyph List" (sem a lista completa; ver lacunas["agl"])."""
    base = nome.lstrip("/").split(".", 1)[0]
    if not base:
        return False
    return all(_componente_agl(parte) for parte in base.split("_"))


def _nao_simbolica(fonte):
    descritor = _obter(fonte, "/FontDescriptor")
    if isinstance(descritor, dict):
        flags = _int(_obter(descritor, "/Flags")) or 0
        return bool(flags & 32) and not flags & 4
    base = (_nome(_obter(fonte, "/BaseFont")) or "").split("+")[-1].lower()
    return base.startswith(("helvetica", "times", "courier", "arial"))


def _nomes_diferencas(codificacao):
    lista = _obter(codificacao, "/Differences")
    if not isinstance(lista, list):
        return []
    nomes = []
    for item in lista:
        item = _res(item)
        if isinstance(item, str) and item != "/.notdef":
            nomes.append(str(item))
    return nomes


def _simples_tem_caminho(fonte):
    nao_simbolica = _nao_simbolica(fonte)
    codificacao = _obter(fonte, "/Encoding")
    if codificacao is None:
        return nao_simbolica
    if isinstance(codificacao, dict):
        base = _obter(codificacao, "/BaseEncoding")
        base_ok = nao_simbolica if base is None else str(base) in _BASES_COM_CAMINHO
        nomes = _nomes_diferencas(codificacao)
        if not all(_nome_agl(n) for n in nomes):
            return False
        # Sem base, /Differences só com nomes da AGL ainda dá caminho (é o caso do pdfTeX).
        return base_ok or bool(nomes)
    return str(codificacao) in _BASES_COM_CAMINHO


def _colecao_asiatica(fonte):
    """Type0 com CIDSystemInfo Adobe-GB1/CNS1/Japan1/Korea1 tem o CMap UCS2 (ISO 9.10.2)."""
    descendentes = _obter(fonte, "/DescendantFonts")
    if not isinstance(descendentes, list) or not descendentes:
        return False
    filha = _res(descendentes[0])
    info = _obter(filha, "/CIDSystemInfo")
    registro = _texto(_obter(info, "/Registry"))
    ordem = _texto(_obter(info, "/Ordering"))
    return registro == "Adobe" and ordem in _COLECOES_ASIATICAS


def _type0_tem_caminho(fonte):
    codificacao = _obter(fonte, "/Encoding")
    if isinstance(codificacao, dict):            # CMap embutido: vale o /UseCMap predefinido
        usa = _obter(codificacao, "/UseCMap")
        if isinstance(usa, str) and str(usa) not in _CMAPS_IDENTIDADE:
            return True
    elif isinstance(codificacao, str) and str(codificacao) not in _CMAPS_IDENTIDADE:
        return True
    return _colecao_asiatica(fonte)


def _classificar_fonte(fonte):
    subtipo = str(_obter(fonte, "/Subtype") or "")
    com_tounicode = _obter(fonte, "/ToUnicode") is not None
    if subtipo == "/Type3":
        tipo, caminho = "type3", com_tounicode
    elif subtipo == "/Type0":
        tipo, caminho = "type0", com_tounicode or _type0_tem_caminho(fonte)
    else:
        tipo, caminho = "simples", com_tounicode or _simples_tem_caminho(fonte)
    return {
        "tipo": tipo,
        "tem_tounicode": com_tounicode,
        "tem_caminho": bool(caminho),
        "bytes": 2 if tipo == "type0" else 1,
    }


class _Fontes:
    """Registro das fontes vistas na passada (uma classificação por objeto de fonte)."""

    def __init__(self):
        self._info = {}
        self._presas = []
        self.usadas = {}

    def obter(self, dicionario_fontes, nome):
        if not isinstance(dicionario_fontes, dict):
            return None
        pego = getattr(dicionario_fontes, "raw_get", dicionario_fontes.get)
        try:
            bruto = pego(nome)
        except KeyError:
            return None
        objeto = _res(bruto)
        if not isinstance(objeto, dict):
            return None
        if hasattr(bruto, "idnum"):
            chave = ("i", bruto.idnum, getattr(bruto, "generation", 0))
        else:
            chave = ("d", id(objeto))
            self._presas.append(objeto)
        if chave not in self._info:
            self._info[chave] = dict(_classificar_fonte(objeto), chave=chave)
        return self._info[chave]

    def marcar(self, info):
        self.usadas[info["chave"]] = info


# ---------------------------------------------------------------- passada por página

def _multiplicar(m1, m2):
    """m1 x m2 em matrizes PDF [a b c d e f] (m1 se aplica primeiro)."""
    return (
        m1[0] * m2[0] + m1[1] * m2[2],
        m1[0] * m2[1] + m1[1] * m2[3],
        m1[2] * m2[0] + m1[3] * m2[2],
        m1[2] * m2[1] + m1[3] * m2[3],
        m1[4] * m2[0] + m1[5] * m2[2] + m2[4],
        m1[4] * m2[1] + m1[5] * m2[3] + m2[5],
    )


def _seis(valores):
    numeros = [float(_res(v)) for v in valores]
    if len(numeros) != 6:
        raise ValueError("matriz sem seis números")
    return tuple(numeros)


class _Varredura:
    """Estado de uma passada de `extract_text`: fonte, modo de texto, CTM, imagens e Forms."""

    def __init__(self, recursos, fontes, fim):
        self.recursos = [recursos]
        self.fontes = fontes
        self.fim = fim
        self.ctm = _IDENTIDADE
        self.fonte = None
        self.modo = 0
        self.pilha = []
        self.base = 0
        self.formas = []
        self.ignorar = 0
        self.codigos = 0
        self.sem_caminho = 0
        self.type3 = 0
        self.invisivel = False
        self.area = 0.0
        self.operadores = 0
        self.falhas = 0

    def antes(self, operador, operandos, cm, tm):
        self.operadores += 1
        if self.operadores % 512 == 0 and time.monotonic() > self.fim:
            raise _PrazoEsgotado()
        try:
            self._antes(operador, operandos)
        except Exception:
            self.falhas += 1

    def depois(self, operador, operandos, cm, tm):
        if operador != b"Do":
            return
        try:
            self._sair_do()
        except Exception:
            self.falhas += 1

    def _antes(self, op, args):
        if op == b"Do":
            self._entrar_do(args)
        elif self.ignorar:
            return
        elif op == b"q":
            self.pilha.append((self.ctm, self.fonte, self.modo))
        elif op == b"Q":
            if len(self.pilha) > self.base:
                self.ctm, self.fonte, self.modo = self.pilha.pop()
        elif op == b"cm":
            self.ctm = _multiplicar(_seis(args), self.ctm)
        elif op == b"Tf":
            self.fonte = self.fontes.obter(_obter(self.recursos[-1], "/Font"), args[0])
        elif op == b"Tr":
            self.modo = int(args[0])
        elif op == b"Tj" or op == b"'":
            self._mostrar(args[0])
        elif op == b'"':
            self._mostrar(args[2])
        elif op == b"TJ":
            for item in args[0]:
                if isinstance(item, (bytes, str)):
                    self._mostrar(item)
        elif op == b"INLINE IMAGE":
            self._somar_imagem()

    def _mostrar(self, texto):
        n = len(texto)
        if not n:
            return
        fonte = self.fonte
        if fonte is not None and fonte["bytes"] == 2:
            n = (n + 1) // 2
        self.codigos += n
        if self.modo == 3:
            self.invisivel = True
        if fonte is None:
            return
        self.fontes.marcar(fonte)
        if fonte["tipo"] == "type3":
            self.type3 += n
        elif not fonte["tem_caminho"]:
            self.sem_caminho += n

    def _somar_imagem(self):
        a, b, c, d = self.ctm[:4]
        self.area += abs(a * d - b * c)

    def _entrar_do(self, args):
        marca = None
        try:
            if not self.ignorar:
                marca = self._resolver_do(args[0])
        finally:
            self.formas.append(marca)

    def _resolver_do(self, nome):
        xobjetos = _obter(self.recursos[-1], "/XObject")
        objeto = _obter(xobjetos, nome)
        subtipo = str(_obter(objeto, "/Subtype") or "")
        if subtipo == "/Image":
            self._somar_imagem()
            return None
        if subtipo != "/Form":
            return None
        if len(self.recursos) > PROFUNDIDADE_FORM:
            self.ignorar += 1
            return ("ignorar",)
        matriz = _obter(objeto, "/Matrix")
        matriz = _seis(matriz) if isinstance(matriz, list) else _IDENTIDADE
        recursos = _obter(objeto, "/Resources")
        salvo = (self.ctm, self.fonte, self.modo, len(self.pilha), self.base)
        self.ctm = _multiplicar(matriz, self.ctm)
        self.base = len(self.pilha)
        self.recursos.append(recursos if isinstance(recursos, dict) else self.recursos[-1])
        return ("form", salvo)

    def _sair_do(self):
        marca = self.formas.pop() if self.formas else None
        if marca is None:
            return
        if marca[0] == "ignorar":
            self.ignorar -= 1
            return
        ctm, fonte, modo, n, base = marca[1]
        del self.pilha[n:]
        self.ctm, self.fonte, self.modo, self.base = ctm, fonte, modo, base
        self.recursos.pop()


def _caracteres_uteis(texto):
    """Conta caracteres do texto extraído sem espaço, controle, U+FFFD nem uso privado."""
    n = 0
    for c in texto:
        if c.isspace() or c == _SUBSTITUICAO:
            continue
        if unicodedata.category(c) in ("Cc", "Co", "Cs"):
            continue
        n += 1
    return n


def _unidade_usuario(pagina):
    try:
        u = _obter(pagina, "/UserUnit")
        return float(u) if u is not None and float(u) > 0 else 1.0
    except (TypeError, ValueError):
        return 1.0


def _area_pagina(pagina):
    """Área da MediaBox em pontos quadrados, UserUnit incluso; (Letter, False) se ilegível."""
    unidade = _unidade_usuario(pagina)
    try:
        x1, y1, x2, y2 = [float(_res(v)) for v in _obter(pagina, "/MediaBox")]
        largura, altura = abs(x2 - x1), abs(y2 - y1)
        if largura > 0 and altura > 0:
            return largura * altura * unidade * unidade, True
    except (TypeError, ValueError):
        pass
    return CAIXA_PADRAO[0] * CAIXA_PADRAO[1] * unidade * unidade, False


def _medir_pagina(pagina, fontes, fim):
    """Uma passada: texto, códigos por tipo de fonte, texto invisível e área de imagem."""
    recursos = _obter(pagina, "/Resources")
    varredura = _Varredura(recursos if isinstance(recursos, dict) else {}, fontes, fim)
    texto = pagina.extract_text(
        visitor_operand_before=varredura.antes, visitor_operand_after=varredura.depois
    ) or ""
    area_pagina, caixa_lida = _area_pagina(pagina)
    unidade = _unidade_usuario(pagina)
    area_imagem = min(1.0, varredura.area * unidade * unidade / area_pagina)
    return {
        "texto": texto[:TETO_TEXTO_PAGINA],
        "uteis": _caracteres_uteis(texto),
        "bruto": len(texto),
        "codigos": varredura.codigos,
        "sem_caminho": varredura.sem_caminho,
        "type3": varredura.type3,
        "invisivel": varredura.invisivel,
        "area": area_imagem,
        "caixa_lida": caixa_lida,
        "falhas": varredura.falhas,
    }


# ---------------------------------------------------------------- catálogo

def _percorrer_paginas(raiz):
    """Travessia própria dos /Kids, sem usar /Count: ([(nó, referência, herdado)], motivo)."""
    arvore = _obter(raiz, "/Pages")
    if not isinstance(arvore, dict):
        return [], "sem /Pages no catálogo"
    folhas = []
    motivo = None
    visitados = {id(arvore)}
    pilha = [(arvore, None, {}, 0)]
    while pilha:
        no, ref, herdado, prof = pilha.pop()
        filhos = _obter(no, "/Kids")
        tipo = str(_obter(no, "/Type") or "")
        if isinstance(filhos, list) and tipo != "/Page":
            if prof >= TETO_PROFUNDIDADE_PAGINAS:
                motivo = "profundidade acima de {}".format(TETO_PROFUNDIDADE_PAGINAS)
                continue
            herdado = dict(herdado)
            for chave in _HERDAVEIS:
                valor = _obter(no, chave)
                if valor is not None:
                    herdado[chave] = valor
            for filho in reversed(list(filhos)):
                objeto = _res(filho)
                if not isinstance(objeto, dict) or not objeto:
                    continue
                if id(objeto) in visitados:
                    motivo = "nó repetido ou ciclo nos /Kids"
                    continue
                if len(visitados) >= TETO_NOS_PAGINAS:
                    motivo = "teto de {} nós".format(TETO_NOS_PAGINAS)
                    break
                visitados.add(id(objeto))
                pilha.append((objeto, filho if hasattr(filho, "idnum") else None, herdado, prof + 1))
        elif not isinstance(filhos, list) and tipo in ("", "/Page"):
            folhas.append((no, ref, herdado))
    return folhas, motivo


def _criar_pagina(pypdf, leitor, no, ref, herdado):
    """Monta a página como o pypdf faz ao achatar a árvore: dicionário + atributos herdados."""
    pagina = pypdf.PageObject(leitor, ref)
    pagina.update(no)
    for chave, valor in herdado.items():
        if chave not in pagina:
            pagina[pypdf.generic.NameObject(chave)] = valor
    return pagina


def _sumario(raiz):
    """Sumário embutido por /First e /Next, sem usar /Count (ISO 12.3.3): (bloco|None, motivo)."""
    contorno = _obter(raiz, "/Outlines")
    if not isinstance(contorno, dict):
        return None, None
    primeiro = _obter(contorno, "/First")
    pilha = [(primeiro, 1)] if isinstance(primeiro, dict) else []
    vistos = set()
    profundidade = 0
    motivo = None
    parar = False
    while pilha and not parar:
        no, nivel = pilha.pop()
        while isinstance(no, dict):
            if id(no) in vistos:
                motivo = "ciclo em /First ou /Next; itens repetidos ignorados"
                break
            if len(vistos) >= TETO_ITENS_SUMARIO:
                motivo = "teto de {} itens; contagem parcial".format(TETO_ITENS_SUMARIO)
                parar = True
                break
            vistos.add(id(no))
            profundidade = max(profundidade, nivel)
            filho = _obter(no, "/First")
            if isinstance(filho, dict):
                pilha.append((filho, nivel + 1))
            no = _obter(no, "/Next")
    return {"entradas": len(vistos), "profundidade": profundidade}, motivo


def _papel(nome, mapa):
    """Resolve o /RoleMap de forma transitiva, com proteção de ciclo (ISO 14.8.4)."""
    visto = set()
    while nome in mapa and nome not in visto:
        visto.add(nome)
        nome = mapa[nome]
    return nome


def _estrutura(raiz_estrutura):
    """Conta os tipos da árvore marcada: (tipos, extras Hn com n>6, motivo)."""
    bruto = _obter(raiz_estrutura, "/RoleMap")
    mapa = {}
    if isinstance(bruto, dict):
        for chave, valor in bruto.items():
            valor = _res(valor)
            if isinstance(valor, str):
                mapa[_nome(chave)] = _nome(valor)
    tipos = dict.fromkeys(_TIPOS_ESTRUTURA, 0)
    extras = {}
    vistos = set()
    motivo = None
    pilha = [_res(raiz_estrutura.get("/K"))]
    while pilha:
        item = _res(pilha.pop())
        if isinstance(item, list):
            pilha.extend(item)
        elif isinstance(item, dict) and id(item) not in vistos:
            vistos.add(id(item))
            if len(vistos) > TETO_NOS_ESTRUTURA:
                motivo = "teto de {} nós; contagem parcial".format(TETO_NOS_ESTRUTURA)
                break
            papel = _obter(item, "/S")
            if isinstance(papel, str):
                nome = _papel(_nome(papel), mapa)
                if nome in tipos:
                    tipos[nome] += 1
                elif re.fullmatch(r"H[1-9][0-9]*", nome or ""):
                    extras[int(nome[1:])] = extras.get(int(nome[1:]), 0) + 1
            pilha.append(item.get("/K"))
    return tipos, extras, motivo


def _contar_nomes(raiz_arvore):
    """Pares de uma árvore de nomes (/Names e /Kids), com proteção de ciclo: (n, motivo)."""
    n = 0
    vistos = set()
    pilha = [raiz_arvore]
    while pilha:
        no = _res(pilha.pop())
        if not isinstance(no, dict) or id(no) in vistos:
            continue
        if len(vistos) >= TETO_NOS_NOMES:
            return n, "teto de {} nós; contagem parcial".format(TETO_NOS_NOMES)
        vistos.add(id(no))
        nomes = _obter(no, "/Names")
        if isinstance(nomes, list):
            n += len(nomes) // 2
        filhos = _obter(no, "/Kids")
        if isinstance(filhos, list):
            pilha.extend(filhos)
    return n, None


def _anexos(raiz):
    """Contagem de /EmbeddedFiles (árvore de nomes) e de /AF (arquivos associados)."""
    arvore = _obter(_obter(raiz, "/Names"), "/EmbeddedFiles")
    embutidos, motivo = _contar_nomes(arvore) if isinstance(arvore, dict) else (0, None)
    af = _obter(raiz, "/AF")
    return {"embeddedfiles": embutidos, "af": len(af) if isinstance(af, list) else 0}, motivo


def _info(leitor):
    """Dicionário Info do trailer, com os valores brutos."""
    info = _res(leitor.trailer.get("/Info"))
    chaves = (("producer", "/Producer"), ("creator", "/Creator"),
              ("creation_date", "/CreationDate"), ("mod_date", "/ModDate"))
    return {campo: _texto(_obter(info, chave)) for campo, chave in chaves}


def _ler_xmp(carga):
    """Extrai as quatro propriedades do XMP. Recusa DOCTYPE/ENTITY (XMP não os usa)."""
    for codec in ("utf-8", "utf-16-le", "utf-16-be"):
        for marca in ("<!DOCTYPE", "<!ENTITY"):
            if marca.encode(codec) in carga:
                raise ValueError("XMP com DOCTYPE/ENTITY recusado")
    raiz = ElementTree.fromstring(carga)

    def valor(espaco, nome):
        chave = "{" + espaco + "}" + nome
        for elemento in raiz.iter():
            atributo = (elemento.attrib.get(chave) or "").strip()
            if atributo:
                return atributo
            if elemento.tag == chave:
                texto = "".join(elemento.itertext()).strip()
                if texto:
                    return texto
        return None

    pdf_ns = "http://ns.adobe.com/pdf/1.3/"
    xmp_ns = "http://ns.adobe.com/xap/1.0/"
    return {
        "pdf_producer": valor(pdf_ns, "Producer"),
        "xmp_creator_tool": valor(xmp_ns, "CreatorTool"),
        "xmp_create_date": valor(xmp_ns, "CreateDate"),
        "xmp_modify_date": valor(xmp_ns, "ModifyDate"),
    }


def _xmp(raiz):
    """(presente, bloco|None, motivo)."""
    fluxo = _obter(raiz, "/Metadata")
    if fluxo is None:
        return False, None, None
    carga = fluxo.get_data()
    if len(carga) > TETO_XMP:
        return True, None, "XMP maior que {} bytes".format(TETO_XMP)
    return True, _ler_xmp(carga), None


def _normalizar(texto):
    return " ".join(texto.split()).casefold()


def _quem_vale(info, xmp):
    """Fonte que vale para o programa criador: XMP, salvo se o /ModDate do Info for mais recente."""
    tem_info = bool(info["producer"] or info["creator"])
    tem_xmp = bool(xmp and (xmp["pdf_producer"] or xmp["xmp_creator_tool"]))
    if not tem_info and not tem_xmp:
        return None
    if not tem_xmp:
        return "info"
    if not tem_info:
        return "xmp"
    pares = ((info["producer"], xmp["pdf_producer"]), (info["creator"], xmp["xmp_creator_tool"]))
    if not any(a and b and _normalizar(a) != _normalizar(b) for a, b in pares):
        return "xmp"
    data_info = _data_hora(info["mod_date"])
    data_xmp = _data_hora(xmp["xmp_modify_date"] or xmp["xmp_create_date"])
    if data_info and data_xmp and data_info > data_xmp:
        return "info"
    return "xmp"


def _nome_versao(texto):
    """Separa `Nome 1.2.3` ou `Nome/1.2.3`; sem versão reconhecível, o nome é o texto inteiro."""
    limpo = " ".join(texto.split())
    m = _RE_VERSAO.match(limpo)
    if m:
        return m.group("nome").strip(" -_/"), m.group("versao")
    return limpo, None


def _aplicacoes(info, xmp, vale):
    """Uma aplicação por programa distinto; a fonte que vale vem primeiro."""
    data_info = _data_iso(info["creation_date"])
    data_xmp = _data_iso(xmp["xmp_create_date"]) if xmp else None
    do_info = [(info["producer"], "pdf_info_producer", data_info),
               (info["creator"], "pdf_info_creator", data_info)]
    do_xmp = []
    if xmp:
        do_xmp = [(xmp["pdf_producer"], "xmp_pdf_producer", data_xmp),
                  (xmp["xmp_creator_tool"], "xmp_creator_tool", data_xmp)]
    unicos = {}
    for texto, fonte, data in (do_info + do_xmp if vale == "info" else do_xmp + do_info):
        if not texto:
            continue
        nome, versao = _nome_versao(texto)
        if (nome, versao) in unicos:
            entrada = unicos[(nome, versao)]
            entrada["fonte"] += "," + fonte
            entrada["data"] = entrada["data"] or data
        else:
            unicos[(nome, versao)] = {"nome": nome, "versao": versao, "data": data, "fonte": fonte}
    return list(unicos.values())


def _maior_versao(*versoes):
    validas = [v for v in versoes if _versao_como_tupla(v) is not None]
    return max(validas, key=_versao_como_tupla) if validas else None


# ---------------------------------------------------------------- criptografia

def _registrar_cifra(bibliotecas):
    """Anota o provedor de cifra que o pypdf usou (cryptography, quando existe)."""
    try:
        from pypdf import _crypt_providers
        nome, versao = _crypt_providers.crypt_provider
    except Exception:
        return
    if nome != "local_crypt_provider":
        bibliotecas[nome] = versao


def _cifra(leitor, pdf, saida):
    """Lê o /Encrypt e tenta a senha vazia. True se o conteúdo ficou legível."""
    dicionario = _res(leitor.trailer.get("/Encrypt"))
    if dicionario is None:
        return True
    filtro = _nome(_obter(dicionario, "/Filter"))
    versao = _int(_obter(dicionario, "/V"))
    bloco = {"filtro": filtro, "v": versao, "r": _int(_obter(dicionario, "/R")),
             "abre_com_senha_vazia": False}
    pdf["criptografado"] = bloco
    alvo = "{} V={}".format(filtro, versao)   # nunca chave nem senha
    try:
        aberto = int(leitor.decrypt("")) > 0
    except Exception as exc:
        saida["inibidor"] = {"tipo": "Encryption", "alvo": alvo}
        saida["lacunas"]["criptografado"] = "não se tentou a senha vazia: " + _uma_linha(exc)
        return False
    if aberto:
        bloco["abre_com_senha_vazia"] = True
        _registrar_cifra(saida["bibliotecas"])
        return True
    tipo = "Password protection" if filtro == "Standard" else "Encryption"
    saida["inibidor"] = {"tipo": tipo, "alvo": alvo}
    saida["lacunas"]["criptografado"] = "a senha vazia não abre; conteúdo ilegível sem a senha"
    return False


# ---------------------------------------------------------------- páginas (agregação)

def _bloco_fontes(fontes):
    usadas = list(fontes.usadas.values())
    return {
        "total": len(usadas),
        "sem_tounicode": sum(1 for f in usadas if not f["tem_tounicode"]),
        "sem_caminho": sum(1 for f in usadas if f["tipo"] != "type3" and not f["tem_caminho"]),
        "type3": sum(1 for f in usadas if f["tipo"] == "type3"),
    }


def _resumo(valores):
    if not valores:
        return {"min": None, "mediana": None, "max": None, "total": 0}
    return {"min": min(valores), "mediana": _mediana(valores), "max": max(valores), "total": sum(valores)}


def _com_lista(paginas, chave):
    lista, total = _lista_teto(paginas)
    return {chave: lista, chave + "_total": total}


def _bloco_paginas(medidas):
    """Estatísticas por página e as listas de páginas em cada critério (1-based)."""
    def onde(criterio):
        return [n for n, m in medidas if criterio(m)]

    def fracao_sem_caminho(m):
        return m["codigos"] and m["sem_caminho"] / m["codigos"] > LIMIAR_SEM_CAMINHO

    areas = [m["area"] for _, m in medidas]
    caracteres = _resumo([m["uteis"] for _, m in medidas])
    caracteres["total_bruto"] = sum(m["bruto"] for _, m in medidas)
    glifos = _resumo([m["sem_caminho"] for _, m in medidas])
    glifos.update(_com_lista(onde(fracao_sem_caminho), "paginas_gt20"))
    imagem = {"mediana": round(statistics.median(areas), 4) if areas else None,
              "max": round(max(areas), 4) if areas else None}
    imagem.update(_com_lista(onde(lambda m: m["area"] > LIMIAR_OCR_AREA), "paginas_gt50"))
    ocr = _com_lista(onde(lambda m: m["uteis"] < LIMIAR_OCR_CARACTERES and m["area"] > LIMIAR_OCR_AREA),
                     "paginas")
    return {
        "caracteres": caracteres,
        "glifos_sem_caminho": glifos,
        "type3": {"total": sum(m["type3"] for _, m in medidas)},
        "texto_invisivel": _com_lista(onde(lambda m: m["invisivel"]), "paginas"),
        "imagem_area": imagem,
        "ocr": ocr,
        "sem_texto": _com_lista(onde(lambda m: m["uteis"] == 0), "paginas"),
    }


def _analisar_paginas(pypdf, leitor, folhas, fim):
    """Uma passada por página até o prazo. Devolve medidas, textos, falhas e a página do prazo."""
    fontes = _Fontes()
    medidas, textos, falhas = [], [], []
    prazo_na_pagina = None
    for numero, (no, ref, herdado) in enumerate(folhas, start=1):
        if time.monotonic() > fim:
            prazo_na_pagina = numero
            break
        try:
            pagina = _criar_pagina(pypdf, leitor, no, ref, herdado)
            medida = _medir_pagina(pagina, fontes, fim)
        except _PrazoEsgotado:
            prazo_na_pagina = numero
            break
        except Exception:
            falhas.append(numero)
            textos.append("")
            continue
        medidas.append((numero, medida))
        textos.append(medida["texto"])
    return fontes, medidas, textos, falhas, prazo_na_pagina


def _lacunas_das_paginas(lacunas, medidas, falhas, prazo_na_pagina, folhas, prazo_s):
    if prazo_na_pagina is not None:
        lacunas["prazo"] = "prazo de {:g}s esgotado na página {}; {} de {} páginas analisadas".format(
            prazo_s, prazo_na_pagina, len(medidas), len(folhas))
    if falhas:
        lacunas["paginas"] = "extração falhou em {} páginas (primeiras: {})".format(
            len(falhas), ", ".join(str(n) for n in falhas[:10]))
    sem_caixa = sum(1 for _, m in medidas if not m["caixa_lida"])
    if sem_caixa:
        lacunas["mediabox"] = "MediaBox ilegível em {} páginas; área assumida como Letter".format(sem_caixa)
    nao_lidos = sum(m["falhas"] for _, m in medidas)
    if nao_lidos:
        lacunas["operadores"] = "{} operadores do conteúdo não foram lidos".format(nao_lidos)
    lacunas["agl"] = ("nome de glifo da AGL aproximado por uniXXXX, uXXXX, html.entities, letra ou dígito "
                      "isolado e lista embutida de nomes tipográficos; a AGL completa não está na "
                      "biblioteca padrão")


# ---------------------------------------------------------------- montagem

_CAMPOS_LEITOS_PELO_PYPDF = (
    "versao_catalogo", "paginas_declaradas", "paginas_percorridas", "paginas_analisadas", "info", "xmp",
    "criador_vale", "sumario_embutido", "marcado", "suspects", "estrutura_presente", "estrutura_tipos",
    "rotulos_pagina", "anexos", "fontes", "paginas", "camada_texto", "lingua_declarada", "_texto", "_paginas",
)


def _bloco_vazio():
    return {
        "versao_cabecalho": None, "cabecalho_offset": None, "versao_catalogo": None, "versao_efetiva": None,
        "revisoes": None, "paginas_declaradas": None, "paginas_percorridas": None,
        "paginas_analisadas": None, "criptografado": None, "linearizado": False, "info": None,
        "xmp_presente": None, "xmp": None, "criador_vale": None, "sumario_embutido": None, "marcado": None,
        "suspects": None, "estrutura_presente": None, "estrutura_tipos": None, "rotulos_pagina": None,
        "anexos": None, "fontes": None, "paginas": None, "camada_texto": None,
    }


def _envelope_vazio():
    return {
        "pdf": _bloco_vazio(), "aplicacoes_criadoras": [], "inibidor": None, "lingua_declarada": None,
        "estrutura_declarada": [], "encoding": None, "_texto": None, "_paginas": None,
        "lacunas": {}, "bibliotecas": {}, "erro": None,
    }


def _lacuna_em_lote(lacunas, campos, motivo):
    for campo in campos:
        lacunas.setdefault(campo, motivo)


def _importar_pypdf(bibliotecas):
    try:
        import pypdf
    except ImportError:
        return None
    try:
        bibliotecas["pypdf"] = importlib.metadata.version("pypdf")
    except importlib.metadata.PackageNotFoundError:
        bibliotecas["pypdf"] = str(getattr(pypdf, "__version__", "desconhecida"))
    return pypdf


def _abrir(pypdf, dados, offset):
    """Abre com strict=False; com lixo antes de `%PDF-`, tenta primeiro os bytes a partir do cabeçalho."""
    tentativas = [dados[offset:], dados] if offset else [dados]
    ultimo = None
    for conteudo in tentativas:
        try:
            return pypdf.PdfReader(io.BytesIO(conteudo), strict=False)
        except Exception as exc:
            ultimo = exc
    raise ultimo


def _seguro(lacunas, campo, funcao, *args):
    """Roda `funcao`; se falhar, devolve None e deixa o motivo em lacunas[campo]."""
    try:
        return funcao(*args)
    except Exception as exc:
        lacunas[campo] = _uma_linha(exc)
        return None


def _catalogo(leitor, raiz, pdf, saida):
    """Campos do catálogo, Info e XMP, cada um isolado: um que falhe não derruba os outros."""
    lacunas = saida["lacunas"]
    versao = _nome(_obter(raiz, "/Version"))
    pdf["versao_catalogo"] = versao if _versao_como_tupla(versao) else None
    pdf["versao_efetiva"] = _maior_versao(pdf["versao_cabecalho"], pdf["versao_catalogo"])
    marca = _obter(raiz, "/MarkInfo")
    pdf["marcado"] = _verdadeiro(_obter(marca, "/Marked"))
    pdf["suspects"] = _verdadeiro(_obter(marca, "/Suspects"))
    pdf["estrutura_presente"] = isinstance(_obter(raiz, "/StructTreeRoot"), dict)
    pdf["rotulos_pagina"] = _obter(raiz, "/PageLabels") is not None
    pdf["paginas_declaradas"] = _int(_obter(_obter(raiz, "/Pages"), "/Count"))
    saida["lingua_declarada"] = _texto(_seguro(lacunas, "lingua_declarada", _obter, raiz, "/Lang"))

    info = _seguro(lacunas, "info", _info, leitor)
    pdf["info"] = info
    resultado = _seguro(lacunas, "xmp", _xmp, raiz)
    presente, xmp, motivo = resultado or (_obter(raiz, "/Metadata") is not None, None, None)
    pdf["xmp_presente"] = presente
    pdf["xmp"] = xmp
    if motivo:
        lacunas["xmp"] = motivo
    if info is not None:
        pdf["criador_vale"] = _quem_vale(info, xmp)
        saida["aplicacoes_criadoras"] = _aplicacoes(info, xmp, pdf["criador_vale"])

    sumario = _seguro(lacunas, "sumario_embutido", _sumario, raiz)
    if sumario:
        pdf["sumario_embutido"], motivo = sumario
        if motivo:
            lacunas["sumario_embutido"] = motivo
    anexos = _seguro(lacunas, "anexos", _anexos, raiz)
    if anexos:
        pdf["anexos"], motivo = anexos
        if motivo:
            lacunas["anexos"] = motivo


def _catalogo_estrutura(raiz, pdf, saida):
    """Contagem por tipo da árvore marcada e a fonte `pdf_estrutura_h` do envelope."""
    lacunas = saida["lacunas"]
    arvore = _obter(raiz, "/StructTreeRoot")
    if not isinstance(arvore, dict):
        return
    resultado = _seguro(lacunas, "estrutura_tipos", _estrutura, arvore)
    if not resultado:
        return
    tipos, extras, motivo = resultado
    pdf["estrutura_tipos"] = tipos
    if motivo:
        lacunas["estrutura_tipos"] = motivo
    niveis = {n: tipos["H{}".format(n)] for n in range(1, 7) if tipos["H{}".format(n)]}
    niveis.update(extras)
    entradas = tipos["H"] + sum(niveis.values())
    if entradas:
        saida["estrutura_declarada"].append(
            {"fonte": "pdf_estrutura_h", "entradas": entradas, "profundidade": max(niveis, default=1)})


def _catalogo_paginas(pypdf, leitor, raiz, pdf, saida, fim, prazo_s):
    """Travessia dos /Kids e a passada por página; preenche o bloco e `_texto`/`_paginas`."""
    lacunas = saida["lacunas"]
    folhas, motivo = _percorrer_paginas(raiz)
    pdf["paginas_percorridas"] = len(folhas)
    if motivo:
        lacunas["paginas_percorridas"] = motivo
    fontes, medidas, textos, falhas, prazo_na_pagina = _analisar_paginas(pypdf, leitor, folhas, fim)
    pdf["paginas_analisadas"] = len(medidas)
    _lacunas_das_paginas(lacunas, medidas, falhas, prazo_na_pagina, folhas, prazo_s)
    pdf["fontes"] = _bloco_fontes(fontes)
    pdf["paginas"] = _bloco_paginas(medidas)
    paginas = pdf["paginas"]
    pdf["camada_texto"] = {
        "paginas_ocr": paginas["ocr"]["paginas_total"],
        "paginas_glifos_sem_caminho_gt20": paginas["glifos_sem_caminho"]["paginas_gt20_total"],
        "marcado_com_fontes_sem_mapeamento": bool(pdf["marcado"] and pdf["fontes"]["sem_caminho"] > 0),
    }
    if textos:
        saida["_paginas"] = textos
        saida["_texto"] = "\n".join(textos)[:TETO_TEXTO]


def _preencher(dados, ctx, saida):
    try:
        prazo_s = float(ctx.get("prazo_s") or PRAZO_PADRAO_S)
    except (TypeError, ValueError):
        prazo_s = PRAZO_PADRAO_S
    fim = time.monotonic() + prazo_s
    pdf, lacunas = saida["pdf"], saida["lacunas"]
    _preencher_bytes(dados, pdf, lacunas)
    pdf["versao_efetiva"] = pdf["versao_cabecalho"]
    pypdf = _importar_pypdf(saida["bibliotecas"])
    if pypdf is None:
        _lacuna_em_lote(lacunas, _CAMPOS_LEITOS_PELO_PYPDF, "pypdf ausente no ambiente")
        return
    with _pypdf_calado():
        try:
            leitor = _abrir(pypdf, dados, pdf["cabecalho_offset"])
        except Exception as exc:
            saida["erro"] = "pypdf não abriu o arquivo: " + _uma_linha(exc)
            _lacuna_em_lote(lacunas, _CAMPOS_LEITOS_PELO_PYPDF, "arquivo não abriu no pypdf")
            return
        if not _cifra(leitor, pdf, saida):
            _lacuna_em_lote(lacunas, _CAMPOS_LEITOS_PELO_PYPDF, "conteúdo cifrado, sem acesso")
            return
        raiz = _res(leitor.trailer.get("/Root"))
        if not isinstance(raiz, dict):
            saida["erro"] = "catálogo (/Root) ilegível"
            _lacuna_em_lote(lacunas, _CAMPOS_LEITOS_PELO_PYPDF, "catálogo ilegível")
            return
        _catalogo(leitor, raiz, pdf, saida)
        _catalogo_estrutura(raiz, pdf, saida)
        sumario = pdf["sumario_embutido"]
        if sumario and sumario["entradas"]:
            saida["estrutura_declarada"].insert(0, {"fonte": "pdf_outline", **sumario})
        _catalogo_paginas(pypdf, leitor, raiz, pdf, saida, fim, prazo_s)


def ler(dados, ctx):
    """Lê o PDF e devolve o envelope do contrato; nunca levanta exceção."""
    saida = _envelope_vazio()
    try:
        _preencher(bytes(dados), ctx or {}, saida)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        saida["erro"] = _uma_linha(exc)
    return saida
