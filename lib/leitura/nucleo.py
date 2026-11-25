"""Núcleo puro de fatiamento UTF-8, codificação em 5 passos e sumário (story #4442, t3)."""
from __future__ import annotations

import ast
import codecs
import json
import re
import threading
import tomllib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tipos import ObjetoBruto, Recusa, ResultadoLeitura, SeletorParte

_UTF8_2B_MIN = 0xC2
_UTF8_2B_MAX = 0xDF
_UTF8_3B_MIN = 0xE0
_UTF8_3B_MAX = 0xEF
_UTF8_4B_MIN = 0xF0
_UTF8_4B_MAX = 0xF4
_TAM_TAG_H = 2

ORCAMENTO_PADRAO = 40_000
ORCAMENTO_MAX = 200_000
INTEIRO_MAX = 16 * 1024 * 1024
VARREDURA_MAX = 256 * 1024 * 1024
UTF16_MAX = 16 * 1024 * 1024
SUMARIO_MAX = 8 * 1024 * 1024
MARCO = 1_024
BLOCO_VARREDURA = 1024 * 1024
CACHE_EXTRA_BYTES_MAX = 32 * 1024 * 1024
CABECA_TIPO = 8_192

_UTF8_CONT_MIN = 0x80
_UTF8_CONT_MAX = 0xBF
_UTF8_MAX_RECUO = 3
_MOBI_OFFSET = 60
_MOBI_ASSINATURA = b"BOOKMOBI"
_WEBP_MIN_LEN = 12
_SETEXT_MIN_LEN = 2

_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32-le", True),
    (codecs.BOM_UTF32_BE, "utf-32-be", True),
    (codecs.BOM_UTF8, "utf-8-sig", False),
    (codecs.BOM_UTF16_LE, "utf-16-le", True),
    (codecs.BOM_UTF16_BE, "utf-16-be", True),
)

_ASSINATURAS_BINARIAS = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),
    (b"PK\x07\x08", "application/zip"),
    (b"\x1f\x8b", "application/gzip"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"\x7fELF", "application/x-elf"),
    (b"SQLite format 3\x00", "application/vnd.sqlite3"),
)

_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_SQL_DDL = re.compile(
    r"^\s*(CREATE(?:\s+OR\s+REPLACE)?|ALTER)\s+"
    r"(?:TEMP(?:ORARY)?\s+|UNIQUE\s+|MATERIALIZED\s+)?"
    r"(TABLE|VIEW|INDEX|FUNCTION|TRIGGER|TYPE|SCHEMA)\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.\"`]+)",
    re.IGNORECASE,
)
_RE_JS_DECL = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?"
    r"(class|function|interface|type|const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)"
)
_RE_SH_FUNC = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)")
_RE_SH_VAR = re.compile(r"^([A-Z_][A-Z0-9_]*)=")
_RE_CSS_REGRA = re.compile(r"^\s*(@media\b[^{]+|@keyframes\b[^{]+|[.#A-Za-z][^{@;]+)\s*\{")
_RE_HTML_ESTRUTURA = re.compile(
    r"<(h[1-6]|section|main|nav|article|form)\b([^>]*)>(.*?)</\1>",
    re.IGNORECASE,
)


class ErroNucleo(Exception):
    """Recusa estruturada emitida pelo núcleo puro (saída 1 ou 2)."""

    def __init__(self, recusa: Recusa) -> None:
        self.recusa = recusa
        self.saida = recusa.saida
        super().__init__(recusa.codigo)


class CacheLRUBytes:
    """Cache LRU protegido por trava com teto rígido em bytes reais."""

    def __init__(self, limite_bytes: int = CACHE_EXTRA_BYTES_MAX) -> None:
        self._limite = limite_bytes
        self._trava = threading.Lock()
        self._itens: OrderedDict[str, tuple[Any, int]] = OrderedDict()
        self._bytes_usados = 0

    @property
    def bytes_usados(self) -> int:
        with self._trava:
            return self._bytes_usados

    def obter(self, chave: str) -> Any | None:
        with self._trava:
            par = self._itens.get(chave)
            if par is None:
                return None
            self._itens.move_to_end(chave)
            return par[0]

    def gravar(self, chave: str, valor: Any, peso_bytes: int) -> bool:
        peso = max(0, int(peso_bytes))
        if peso > self._limite:
            return False
        with self._trava:
            anterior = self._itens.pop(chave, None)
            if anterior is not None:
                self._bytes_usados -= anterior[1]
            while self._itens and (self._bytes_usados + peso) > self._limite:
                _, (_, peso_ant) = self._itens.popitem(last=False)
                self._bytes_usados -= peso_ant
            self._itens[chave] = (valor, peso)
            self._bytes_usados += peso
            return True

    def esvaziar(self) -> None:
        with self._trava:
            self._itens.clear()
            self._bytes_usados = 0


CACHE_GLOBAL = CacheLRUBytes(CACHE_EXTRA_BYTES_MAX)


def esvaziar_cache_global() -> None:
    CACHE_GLOBAL.esvaziar()


@dataclass(frozen=True, slots=True)
class IndiceFluxo:
    """Marcos esparsos de linhas e metadados da varredura em blocos."""

    total_bytes: int
    linhas_total: int
    marcos: tuple[int, ...]
    varredura_parcial: bool


def varrer_fluxo(fluxo: Any, *, limite_bytes: int = VARREDURA_MAX) -> IndiceFluxo:
    """Varre fluxo em blocos de 1 MiB até 256 MiB gravando marcos a cada 1024 linhas."""
    pos_ini = fluxo.tell() if hasattr(fluxo, "tell") else 0
    if hasattr(fluxo, "seek"):
        fluxo.seek(0)
    marcos: list[int] = [0]
    total_bytes = 0
    quebras = 0
    parcial = False
    while True:
        restante = limite_bytes - total_bytes
        if restante <= 0:
            if fluxo.read(1):
                parcial = True
            break
        bloco = fluxo.read(min(BLOCO_VARREDURA, restante))
        if not bloco:
            break
        idx = bloco.find(b"\n")
        while idx != -1:
            quebras += 1
            if quebras % MARCO == 0:
                marcos.append(total_bytes + idx + 1)
            idx = bloco.find(b"\n", idx + 1)
        total_bytes += len(bloco)
    if hasattr(fluxo, "seek"):
        fluxo.seek(pos_ini)
    linhas_total = 0 if total_bytes == 0 else (quebras if total_bytes > 0 and _termina_com_nl(fluxo, total_bytes) else quebras + 1)
    return IndiceFluxo(
        total_bytes=total_bytes,
        linhas_total=linhas_total,
        marcos=tuple(marcos),
        varredura_parcial=parcial,
    )


def _termina_com_nl(fluxo: Any, total_bytes: int) -> bool:
    if total_bytes <= 0 or not hasattr(fluxo, "seek"):
        return False
    pos = fluxo.tell()
    fluxo.seek(total_bytes - 1)
    ultimo = fluxo.read(1)
    fluxo.seek(pos)
    return ultimo == b"\n"


def _tem_bom_utf(cabeca: bytes) -> bool:
    return any(cabeca.startswith(bom) for bom, _, _ in _BOMS)


def detectar_formato(cabeca: bytes, nome: str = "") -> tuple[str, bool]:
    """Detecta formato por assinatura mágica; retorna (mime, eh_binario)."""
    for assinatura, mime in _ASSINATURAS_BINARIAS:
        if cabeca.startswith(assinatura):
            return mime, True
    if len(cabeca) >= _WEBP_MIN_LEN and cabeca[:4] == b"RIFF" and cabeca[8:12] == b"WEBP":
        return "image/webp", True
    if (
        len(cabeca) >= _MOBI_OFFSET + len(_MOBI_ASSINATURA)
        and cabeca[_MOBI_OFFSET : _MOBI_OFFSET + len(_MOBI_ASSINATURA)] == _MOBI_ASSINATURA
    ):
        return "application/x-mobipocket-ebook", True
    if b"\x00" in cabeca and not _tem_bom_utf(cabeca):
        return "application/octet-stream", True
    ext = Path(nome).suffix.lower()
    if ext in (".html", ".htm"):
        return "text/html", False
    if ext == ".mhtml":
        return "multipart/related", False
    return "text/plain", False


def _contar_utf8_multibyte_e_invalidos(dados: bytes) -> tuple[int, int]:
    """Conta sequências multibyte UTF-8 válidas versus bytes inválidos isolados."""
    validas = 0
    invalidos = 0
    i = 0
    n = len(dados)
    while i < n:
        b = dados[i]
        if b < _UTF8_CONT_MIN:
            i += 1
            continue
        tam = _tamanho_utf8(b)
        if tam == 0 or i + tam > n:
            invalidos += 1
            i += 1
            continue
        fatia = dados[i : i + tam]
        try:
            fatia.decode("utf-8", errors="strict")
            validas += 1
            i += tam
        except UnicodeDecodeError:
            invalidos += 1
            i += 1
    return validas, invalidos


def _tamanho_utf8(b: int) -> int:
    if _UTF8_2B_MIN <= b <= _UTF8_2B_MAX:
        return 2
    if _UTF8_3B_MIN <= b <= _UTF8_3B_MAX:
        return 3
    if _UTF8_4B_MIN <= b <= _UTF8_4B_MAX:
        return 4
    return 0


def resolver_encoding(
    dados: bytes, *, encoding_pedida: str | None = None
) -> tuple[str, str, bool, tuple[str, ...]]:
    """Cinco passos fixos de resolução de codificação com marca com_perda."""
    if encoding_pedida:
        try:
            return dados.decode(encoding_pedida, errors="strict"), encoding_pedida, False, ()
        except (LookupError, UnicodeDecodeError) as exc:
            raise ErroNucleo(
                Recusa(
                    saida=2,
                    codigo="decodificacao-recusada",
                    onde="--encoding",
                    recebido=encoding_pedida,
                    regra="encoding-explicito-estrito",
                    cura=f"bytes inválidos sob {encoding_pedida}: {exc}",
                    proximo="",
                )
            ) from exc

    for bom, codec, eh_largo in _BOMS:
        if dados.startswith(bom):
            if eh_largo and len(dados) > UTF16_MAX:
                raise ErroNucleo(
                    Recusa(
                        saida=2,
                        codigo="decodificacao-recusada",
                        onde="conteudo",
                        recebido=f"{codec} ({len(dados)} bytes)",
                        regra="teto-utf16-utf32",
                        cura=f"transcodificação {codec} excede o teto de {UTF16_MAX} bytes",
                        proximo="",
                    )
                )
            try:
                corpo = dados[len(bom) :] if codec != "utf-8-sig" else dados
                return corpo.decode(codec, errors="strict"), codec, False, ()
            except UnicodeDecodeError as exc:
                raise ErroNucleo(
                    Recusa(
                        saida=2,
                        codigo="decodificacao-recusada",
                        onde="conteudo",
                        recebido=codec,
                        regra="bom-estrito",
                        cura=f"conteúdo inválido para o BOM {codec}: {exc}",
                        proximo="",
                    )
                ) from exc

    try:
        return dados.decode("utf-8", errors="strict"), "utf-8", False, ()
    except UnicodeDecodeError:
        pass

    validas, invalidos = _contar_utf8_multibyte_e_invalidos(dados)
    if validas > invalidos:
        return (
            dados.decode("utf-8", errors="replace"),
            "utf-8",
            True,
            ("bytes_invalidos_substituidos",),
        )
    return (
        dados.decode("cp1252", errors="replace"),
        "cp1252",
        True,
        ("encoding_inferido: cp1252",),
    )


def _eh_continuacao_utf8(byte: int) -> bool:
    return _UTF8_CONT_MIN <= byte <= _UTF8_CONT_MAX


def _avancar_inicio_utf8(dados: bytes, ini: int) -> int:
    n = len(dados)
    passos = 0
    while ini < n and _eh_continuacao_utf8(dados[ini]) and passos < _UTF8_MAX_RECUO:
        ini += 1
        passos += 1
    return ini


def _recuar_borda_utf8(dados: bytes, fim: int) -> int:
    if fim >= len(dados) or fim <= 0:
        return fim
    recuo = 0
    pos = fim
    while pos > 0 and _eh_continuacao_utf8(dados[pos]) and recuo < _UTF8_MAX_RECUO:
        pos -= 1
        recuo += 1
    return pos if pos > 0 else fim


def _limpar_visivel(texto: str, mime: str) -> str:
    if mime == "text/html":
        return re.sub(r"\n{3,}", "\n\n", _RE_HTML_TAG.sub("", texto)).strip()
    return _RE_MD_LINK.sub(r"\1 (\2)", texto)


def _sumario_python(texto: str) -> list[list[Any]]:
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return []
    itens: list[list[Any]] = []
    _visitar_ast_py(arvore.body, 1, itens)
    return itens


def _visitar_ast_py(nos: list[ast.stmt], nivel: int, saida: list[list[Any]]) -> None:
    for no in nos:
        if isinstance(no, ast.ClassDef):
            saida.append([nivel, f"class {no.name}", no.lineno, no.end_lineno or no.lineno])
            _visitar_ast_py(no.body, nivel + 1, saida)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pref = "async def" if isinstance(no, ast.AsyncFunctionDef) else "def"
            saida.append([nivel, f"{pref} {no.name}", no.lineno, no.end_lineno or no.lineno])
            _visitar_ast_py(no.body, nivel + 1, saida)
        elif isinstance(no, ast.Assign) and nivel == 1:
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id.isupper():
                    saida.append([nivel, f"const {alvo.id}", no.lineno, no.end_lineno or no.lineno])
        elif isinstance(no, ast.If):
            saida.append([nivel, "if", no.lineno, no.end_lineno or no.lineno])
            _visitar_ast_py(no.body, nivel + 1, saida)
            _visitar_ast_py(no.orelse, nivel + 1, saida)


def _sumario_markdown(texto: str) -> list[list[Any]]:
    linhas = texto.splitlines()
    itens: list[list[Any]] = []
    i = 0
    if linhas and linhas[0].strip() == "---":
        i = 1
        while i < len(linhas) and linhas[i].strip() != "---":
            i += 1
        i += 1
    cerca: str | None = None
    while i < len(linhas):
        ln = linhas[i]
        stripped = ln.strip()
        if stripped.startswith(("```", "~~~")):
            marc = stripped[:3]
            cerca = None if cerca == marc else (marc if cerca is None else cerca)
            i += 1
            continue
        if cerca is not None:
            i += 1
            continue
        m_atx = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", ln)
        if m_atx:
            itens.append([len(m_atx.group(1)), m_atx.group(2).strip(), i + 1, i + 1])
        elif i + 1 < len(linhas) and stripped and _eh_sublinhado_setext(linhas[i + 1]):
            nivel = 1 if linhas[i + 1].strip().startswith("=") else 2
            itens.append([nivel, stripped, i + 1, i + 2])
            i += 1
        i += 1
    return itens


def _eh_sublinhado_setext(linha: str) -> bool:
    s = linha.strip()
    return len(s) >= _SETEXT_MIN_LEN and (set(s) == {"="} or set(s) == {"-"})


def _descrever_valor_estruturado(val: Any) -> str:
    if isinstance(val, dict):
        return f"object({len(val)})"
    if isinstance(val, list):
        return f"array({len(val)})"
    return type(val).__name__


def _sumario_dict_dois_niveis(obj: dict[str, Any]) -> list[list[Any]]:
    itens: list[list[Any]] = []
    for k, v in obj.items():
        itens.append([1, f"{k}: {_descrever_valor_estruturado(v)}", 1, 1])
        if isinstance(v, dict):
            for sk, sv in v.items():
                itens.append([2, f"{sk}: {_descrever_valor_estruturado(sv)}", 1, 1])
    return itens


def _sumario_json(texto: str) -> list[list[Any]]:
    try:
        obj = json.loads(texto)
    except json.JSONDecodeError:
        return []
    if isinstance(obj, dict):
        return _sumario_dict_dois_niveis(obj)
    if isinstance(obj, list):
        return [[1, f"array({len(obj)})", 1, 1]]
    return []


def _sumario_toml(texto: str) -> list[list[Any]]:
    try:
        obj = tomllib.loads(texto)
    except tomllib.TOMLDecodeError:
        return []
    return _sumario_dict_dois_niveis(obj)


def _sumario_yaml(texto: str) -> list[list[Any]]:
    """Varredura segura de chaves YAML (1º e 2º nível) sem construtores arbitrários."""
    itens: list[list[Any]] = []
    indent_n2: int | None = None
    for idx, ln in enumerate(texto.splitlines(), start=1):
        s = ln.strip()
        if not s or s.startswith("#") or s in ("---", "..."):
            continue
        m = re.match(r"^(\s*)([A-Za-z0-9_.-]+)\s*:(?:\s|$)", ln)
        if not m:
            continue
        recuo = len(m.group(1))
        chave = m.group(2)
        if recuo == 0:
            indent_n2 = None
            itens.append([1, chave, idx, idx])
        else:
            if indent_n2 is None:
                indent_n2 = recuo
            if recuo == indent_n2:
                itens.append([2, chave, idx, idx])
    return itens


def _sumario_regex(texto: str, padroes: tuple[re.Pattern[str], ...]) -> list[list[Any]]:
    itens: list[list[Any]] = []
    for idx, ln in enumerate(texto.splitlines(), start=1):
        for pad in padroes:
            m = pad.match(ln)
            if m:
                rotulo = " ".join(g.strip() for g in m.groups() if g)
                itens.append([1, rotulo, idx, idx])
                break
    return itens


def _sumario_html(texto: str) -> list[list[Any]]:
    itens: list[list[Any]] = []
    for idx, ln in enumerate(texto.splitlines(), start=1):
        for m in _RE_HTML_ESTRUTURA.finditer(ln):
            tag = m.group(1).lower()
            nivel = int(tag[1]) if tag.startswith("h") and len(tag) == _TAM_TAG_H else 1
            corpo = _RE_HTML_TAG.sub("", m.group(3)).strip() or tag
            itens.append([nivel, f"{tag}: {corpo}", idx, idx])
    return itens


def _detectar_linguagem_sumario(nome: str) -> str:
    ext = Path(nome).suffix.lower()
    mapa = {
        ".py": "python",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sql": "sql",
        ".js": "js",
        ".mjs": "js",
        ".jsx": "js",
        ".ts": "ts",
        ".tsx": "ts",
        ".sh": "shell",
        ".bash": "shell",
        ".css": "css",
        ".html": "html",
        ".htm": "html",
    }
    return mapa.get(ext, "texto")


def _podar_sumario(itens: list[list[Any]], max_bytes: int) -> tuple[list[list[Any]], bool]:
    def _tam(lista: list[list[Any]]) -> int:
        return len(json.dumps(lista, ensure_ascii=False).encode("utf-8"))

    if _tam(itens) <= max_bytes:
        return itens, False
    prof_max = max((it[0] for it in itens), default=1)
    atual = list(itens)
    while prof_max > 1 and _tam(atual) > max_bytes:
        atual = [it for it in atual if it[0] < prof_max]
        prof_max -= 1
    if _tam(atual) <= max_bytes:
        return atual, True
    lo, hi = 0, len(atual)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _tam(atual[:mid]) <= max_bytes:
            lo = mid
        else:
            hi = mid - 1
    return atual[:lo], True


def montar_sumario(texto: str, nome: str, *, max_bytes: int = ORCAMENTO_PADRAO) -> tuple[list[list[Any]], bool]:
    """Monta árvore estrutural até 8 MiB sobre os dez formatos e poda se exceder max_bytes."""
    if len(texto.encode("utf-8")) > SUMARIO_MAX:
        return [], True
    lang = _detectar_linguagem_sumario(nome)
    extratores = {
        "python": _sumario_python,
        "markdown": _sumario_markdown,
        "json": _sumario_json,
        "yaml": _sumario_yaml,
        "toml": _sumario_toml,
        "sql": lambda t: _sumario_regex(t, (_RE_SQL_DDL,)),
        "js": lambda t: _sumario_regex(t, (_RE_JS_DECL,)),
        "ts": lambda t: _sumario_regex(t, (_RE_JS_DECL,)),
        "shell": lambda t: _sumario_regex(t, (_RE_SH_FUNC, _RE_SH_VAR)),
        "css": lambda t: _sumario_regex(t, (_RE_CSS_REGRA,)),
        "html": _sumario_html,
    }
    fn = extratores.get(lang)
    itens = fn(texto) if fn else []
    return _podar_sumario(itens, max_bytes)


def _formatar_cabecalho(
    bruto: ObjetoBruto, parte: str, *, com_perda: bool
) -> str:
    base = f"{bruto.alvo.chave_pedida} · versão {bruto.versao} · {parte}"
    if bruto.alvo.eh_ficha_da_classe:
        base += f" · objeto lido: a ficha da classe {bruto.alvo.classe}"
    if com_perda:
        base += " · com perda"
    return base


def _ler_bytes_brutos(bruto: ObjetoBruto) -> bytes:
    if bruto.dados is not None:
        return bruto.dados
    if bruto.fluxo is not None:
        if hasattr(bruto.fluxo, "seek"):
            bruto.fluxo.seek(0)
        return bytes(bruto.fluxo.read())
    return b""


@dataclass(frozen=True, slots=True)
class _FatiaTexto:
    conteudo: str
    parte: str
    parcial: bool
    bytes: tuple[int, int]
    linhas: tuple[int, int] | None
    linhas_total: int
    total_bytes: int
    avisos: tuple[str, ...] = ()
    proximo: str | None = None
    proximo_args: dict[str, Any] | None = None


def _fatiar_texto_utf8(
    texto_utf8: bytes,
    seletor: SeletorParte,
    *,
    chave_pedida: str,
) -> _FatiaTexto:
    total_bytes = len(texto_utf8)
    linhas_b = texto_utf8.splitlines(keepends=True)
    linhas_total = len(linhas_b)

    if total_bytes == 0:
        if (seletor.linhas and seletor.linhas[0] > 1) or (seletor.offset and seletor.offset > 0):
            raise _erro_faixa_alem(chave_pedida, linhas_total=0, total_bytes=0)
        return _FatiaTexto(
            conteudo="",
            parte="0 bytes",
            parcial=False,
            bytes=(0, 0),
            linhas=None,
            linhas_total=0,
            total_bytes=0,
        )

    if seletor.offset is not None:
        return _fatiar_por_offset(
            texto_utf8, seletor, offset=seletor.offset, chave_pedida=chave_pedida, linhas_total=linhas_total
        )

    return _fatiar_por_linhas(
        texto_utf8, linhas_b, seletor, chave_pedida=chave_pedida, linhas_total=linhas_total
    )


def _erro_faixa_alem(chave_pedida: str, *, linhas_total: int, total_bytes: int) -> ErroNucleo:
    cauda = max(1, linhas_total - 19)
    prox = f"{chave_pedida} --linhas {cauda}-{linhas_total}" if linhas_total > 0 else ""
    return ErroNucleo(
        Recusa(
            saida=1,
            codigo="faixa-alem-do-fim",
            onde="--linhas/--offset",
            recebido=chave_pedida,
            regra="faixa-dentro-do-objeto",
            cura=f"objeto tem {linhas_total} linhas e {total_bytes} bytes",
            proximo=prox,
        )
    )


def _fatiar_por_offset(
    texto_utf8: bytes,
    seletor: SeletorParte,
    *,
    offset: int,
    chave_pedida: str,
    linhas_total: int,
) -> _FatiaTexto:
    total_bytes = len(texto_utf8)
    if offset >= total_bytes:
        raise _erro_faixa_alem(chave_pedida, linhas_total=linhas_total, total_bytes=total_bytes)
    ini = _avancar_inicio_utf8(texto_utf8, offset)
    fim_alvo = min(total_bytes, ini + seletor.max_bytes)
    fim = _recuar_borda_utf8(texto_utf8, fim_alvo)
    if fim <= ini:
        fim = fim_alvo
    trecho = texto_utf8[ini:fim].decode("utf-8", errors="strict")
    parcial = fim < total_bytes
    parte = f"bytes {ini}-{fim} de {total_bytes}" + (" (parcial)" if parcial else "")
    prox = f"--offset {fim}" if parcial else None
    prox_args = {"offset": fim, "max_bytes": seletor.max_bytes} if parcial else None
    return _FatiaTexto(
        conteudo=trecho,
        parte=parte,
        parcial=parcial,
        bytes=(ini, fim),
        linhas=None,
        linhas_total=linhas_total,
        total_bytes=total_bytes,
        proximo=prox,
        proximo_args=prox_args,
    )


def _fatiar_por_linhas(
    texto_utf8: bytes,
    linhas_b: list[bytes],
    seletor: SeletorParte,
    *,
    chave_pedida: str,
    linhas_total: int,
) -> _FatiaTexto:
    total_bytes = len(texto_utf8)
    if seletor.cauda_linhas is not None:
        ini_l = max(1, linhas_total - seletor.cauda_linhas + 1)
        fim_l_ped = linhas_total
    elif seletor.linhas is not None:
        ini_l, fim_l_opt = seletor.linhas
        if ini_l > linhas_total:
            raise _erro_faixa_alem(chave_pedida, linhas_total=linhas_total, total_bytes=total_bytes)
        fim_l_ped = min(linhas_total, fim_l_opt) if fim_l_opt is not None else linhas_total
    else:
        ini_l, fim_l_ped = 1, linhas_total

    byte_ini = sum(len(x) for x in linhas_b[: ini_l - 1])
    primeira = linhas_b[ini_l - 1]
    if len(primeira) > seletor.max_bytes:
        fim_b = _recuar_borda_utf8(texto_utf8, min(total_bytes, byte_ini + seletor.max_bytes))
        if fim_b <= byte_ini:
            fim_b = min(total_bytes, byte_ini + seletor.max_bytes)
        trecho = texto_utf8[byte_ini:fim_b].decode("utf-8", errors="strict")
        parcial = fim_b < total_bytes
        parte = f"bytes {byte_ini}-{fim_b} de {total_bytes}" + (" (parcial)" if parcial else "")
        return _FatiaTexto(
            conteudo=trecho,
            parte=parte,
            parcial=parcial,
            bytes=(byte_ini, fim_b),
            linhas=(ini_l, ini_l),
            linhas_total=linhas_total,
            total_bytes=total_bytes,
            avisos=("linha_longa_fatiada",),
            proximo=f"--offset {fim_b}" if parcial else None,
            proximo_args={"offset": fim_b, "max_bytes": seletor.max_bytes} if parcial else None,
        )

    acumulado = 0
    fim_l = ini_l - 1
    for idx in range(ini_l - 1, fim_l_ped):
        tam = len(linhas_b[idx])
        if acumulado + tam > seletor.max_bytes and fim_l >= ini_l:
            break
        acumulado += tam
        fim_l = idx + 1

    byte_fim = byte_ini + acumulado
    trecho = texto_utf8[byte_ini:byte_fim].decode("utf-8", errors="strict")
    parcial = fim_l < linhas_total
    parte = f"linhas {ini_l}-{fim_l} de {linhas_total}" + (" (parcial)" if parcial else "")
    prox = f"--linhas {fim_l + 1}-" if parcial else None
    prox_args = {"linhas": f"{fim_l + 1}-", "max_bytes": seletor.max_bytes} if parcial else None
    return _FatiaTexto(
        conteudo=trecho,
        parte=parte,
        parcial=parcial,
        bytes=(byte_ini, byte_fim),
        linhas=(ini_l, fim_l),
        linhas_total=linhas_total,
        total_bytes=total_bytes,
        proximo=prox,
        proximo_args=prox_args,
    )


def processar_objeto(bruto: ObjetoBruto, seletor: SeletorParte) -> ResultadoLeitura:
    """Função pura do núcleo: detecta formato, decodifica, fatia ou monta sumário."""
    dados = _ler_bytes_brutos(bruto)
    nome = bruto.nome_arquivo or bruto.alvo.endereco or bruto.alvo.chave_pedida
    mime, eh_binario = detectar_formato(dados[:CABECA_TIPO], nome)

    if eh_binario:
        raise ErroNucleo(
            Recusa(
                saida=1,
                codigo="formato-sem-leitor",
                onde="conteudo",
                recebido=mime,
                regra="formato-suportado",
                cura=f"formato binário {mime} ({len(dados)} bytes) sem extrator neste núcleo",
                proximo="",
            )
        )

    if seletor.paginas is not None or seletor.cauda_paginas is not None:
        raise ErroNucleo(
            Recusa(
                saida=2,
                codigo="combinacao-invalida",
                onde="--paginas",
                recebido=mime,
                regra="paginas-apenas-em-formato-paginado",
                cura="use --linhas ou --offset sobre texto contínuo",
                proximo="",
            )
        )

    texto, _, com_perda, avisos_enc = resolver_encoding(dados, encoding_pedida=seletor.encoding)
    if seletor.modo == "visivel":
        texto = _limpar_visivel(texto, mime)

    if seletor.modo == "sumario":
        itens_sum, parcial_sum = montar_sumario(texto, nome, max_bytes=seletor.max_bytes)
        parte = f"sumário ({len(itens_sum)} itens)" + (" (parcial)" if parcial_sum else "")
        avisos = (*bruto.avisos, *avisos_enc)
        return ResultadoLeitura(
            cabecalho=_formatar_cabecalho(bruto, parte, com_perda=com_perda),
            chave=bruto.alvo.chave_pedida,
            chave_canonica=bruto.alvo.chave_canonica,
            classe=bruto.alvo.classe,
            morada=bruto.alvo.morada,
            versao=bruto.versao,
            parte=parte,
            parcial=parcial_sum,
            com_perda=com_perda,
            avisos=avisos,
            conteudo=None,
            sumario=itens_sum,
            total_bytes=len(dados),
            mudou=bruto.mudou,
        )

    texto_utf8 = texto.encode("utf-8")
    fatia = _fatiar_texto_utf8(texto_utf8, seletor, chave_pedida=bruto.alvo.chave_pedida)
    avisos_totais = (*bruto.avisos, *avisos_enc, *fatia.avisos)
    return ResultadoLeitura(
        cabecalho=_formatar_cabecalho(bruto, fatia.parte, com_perda=com_perda),
        chave=bruto.alvo.chave_pedida,
        chave_canonica=bruto.alvo.chave_canonica,
        classe=bruto.alvo.classe,
        morada=bruto.alvo.morada,
        versao=bruto.versao,
        parte=fatia.parte,
        parcial=fatia.parcial,
        com_perda=com_perda,
        avisos=avisos_totais,
        conteudo=fatia.conteudo,
        bytes=fatia.bytes,
        total_bytes=fatia.total_bytes,
        linhas=fatia.linhas,
        linhas_total=fatia.linhas_total,
        mudou=bruto.mudou,
        proximo=fatia.proximo,
        proximo_args=fatia.proximo_args,
    )
