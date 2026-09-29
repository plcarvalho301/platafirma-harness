"""Card #3189, ato temporário: leitor dos formatos de texto (MD, HTML e TXT).

Lê dos bytes: codificação (BOM, declarada, detectada), cabeçalhos por nível,
título, língua declarada e métricas de linhas. Markdown só pelo markdown-it-py
(opcional, nunca por regex de linha); HTML pelo html.parser da biblioteca padrão.
"""
import codecs
import re
import time
from html.parser import HTMLParser
from importlib import metadata

LIMITE_TEXTO = 4_000_000     # teto de _texto, em caracteres
JANELA_META = 1024           # bytes iniciais onde o charset declarado vale
TITULO_MAX = 300
PASSO_HTML = 200_000         # caracteres por fatia entregue ao parser (o prazo é conferido entre fatias)
LIMITE_DETECTOR = 1_000_000  # bytes entregues ao charset-normalizer
MARGEM_CHAOS = 0.15          # o detector aceita candidatos até 0.2 de caos; ver _preferir_ocidental
SUBST = chr(0xFFFD)
ESC = bytes([0x1B])
C1 = bytes(range(0x80, 0xA0))
NIVEIS = ("1", "2", "3", "4", "5", "6")
TAGS_H = frozenset("h" + n for n in NIVEIS)
PREFERIDOS = ("cp1252", "latin_1", "iso8859_15")   # nomes do charset-normalizer

_BOMS = (
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)
# rótulos da web que o Python não conhece
_ALIAS = {
    "x-sjis": "shift_jis",
    "windows-31j": "cp932",
    "ks_c_5601-1987": "cp949",
    "iso-8859-8-i": "iso8859-8",
    "macintosh": "mac_roman",
}
_BLOCOS = frozenset(
    "address article aside blockquote body br caption dd details dialog div dl dt fieldset "
    "figcaption figure footer form h1 h2 h3 h4 h5 h6 head header hr html li main nav ol p pre "
    "section summary table tbody td tfoot th thead title tr ul".split()
)
_OCULTOS = frozenset(("script", "style", "template"))

_ESPACOS = re.compile(r"[ \t\r\n\f]+")
_ESPACOS_LINHA = re.compile(r"[ \t\r\f]+")
_QUEBRA = re.compile(r"\r\n|\r|\n")
_COMENTARIO = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
_META_CHARSET = re.compile(r"<meta\s[^>]*?charset\s*=\s*[\"']?\s*([A-Za-z0-9_.:-]+)", re.I | re.S)
_XML_ENCODING = re.compile(r"\s*<\?xml\s[^>]*?encoding\s*=\s*[\"']([A-Za-z0-9_.:-]+)[\"']", re.I)
_CHARSET_CONTENT = re.compile(r"charset\s*=\s*[\"']?\s*([^\s;\"']+)", re.I)
_ABRE_H = re.compile(r"<h([1-6])(?![\w:-])", re.I)
_IGNORADOS_MD = re.compile(
    r"<!--.*?(?:-->|\Z)|<(pre|script|style|textarea)\b.*?(?:</\1\s*>|\Z)", re.I | re.S
)
_CHAVE_YAML = re.compile(r"[^\s:#][^:]*:(?:\s|$)")
_LINGUA_FM = re.compile(r"^(?:lang|language|idioma)[ \t]*[:=][ \t]*(.*?)\s*$", re.I | re.M)
_GERADOR = re.compile(r"^(.*?[^\s/,;:-])[\s/]+v?(\d[\w.+-]*)")


# ---------------------------------------------------------------- codificação

def _versao(distribuicao, modulo):
    """Versão instalada da biblioteca (metadados; senão o __version__ do módulo)."""
    try:
        return metadata.version(distribuicao)
    except metadata.PackageNotFoundError:
        return str(getattr(modulo, "__version__", "desconhecida"))


def _canonico(nome):
    """Nome de codec do Python no formato usual da web (utf-8, windows-1252, iso-8859-1)."""
    n = nome.lower().replace("_", "-")
    if n.startswith("cp125") and len(n) == 6:
        return "windows-" + n[2:]
    if n.startswith("iso8859-"):
        return "iso-8859-" + n[8:]
    return n


def _familia(nome):
    """Agrupa utf-16-le/be em utf-16 etc., para comparar com o declarado."""
    for base in ("utf-8", "utf-16", "utf-32"):
        if nome.startswith(base):
            return base
    return nome


def _resolver_codec(rotulo):
    """Nome do codec do Python para um rótulo de charset; None se desconhecido."""
    chave = rotulo.strip().lower()
    try:
        return codecs.lookup(_ALIAS.get(chave, chave)).name
    except LookupError:
        return None


def _estrito(corpo, codec):
    """Decodificação sem erros; None se os bytes não são válidos nesse codec."""
    try:
        return corpo.decode(codec)
    except (ValueError, LookupError):
        return None


def _tolerante(corpo, codec):
    """Decodifica trocando o inválido por U+FFFD; devolve (texto, trocas feitas pelo decodificador)."""
    limpo = _estrito(corpo, codec)
    if limpo is not None:
        return limpo, 0
    texto = corpo.decode(codec, errors="replace")
    literais = corpo.decode(codec, errors="ignore").count(SUBST)  # U+FFFD que já estavam no arquivo
    return texto, texto.count(SUBST) - literais


def _utf8_com_falhas(corpo):
    """UTF-8 remendado (poucos bytes soltos entre muitas sequências válidas):
    (texto, trocas, confiança) ou None. Texto latino de 8 bits quase não forma sequência válida."""
    texto, trocas = _tolerante(corpo, "utf-8")
    validas = len(texto) - len(texto.encode("ascii", errors="ignore")) - texto.count(SUBST)
    if validas >= 10 and trocas * 20 <= validas:
        return texto, trocas, round(validas / (validas + trocas), 4)
    return None


def _tirar_bom(dados):
    """Devolve (nome do BOM ou None, bytes sem o BOM)."""
    for marca, nome in _BOMS:
        if dados.startswith(marca) and (len(marca) != 4 or len(dados) % 4 == 0):
            return nome, dados[len(marca):]
    return None, dados


def _declarado_html(dados, bom, corpo):
    """Charset declarado nos primeiros 1024 bytes: (rótulo ou None, se veio de meta na janela)."""
    trecho = corpo[:JANELA_META - (len(dados) - len(corpo))]  # a janela conta os bytes do BOM
    janela = trecho.decode("latin-1" if bom in (None, "utf-8-sig") else bom, errors="ignore")
    meta = _META_CHARSET.search(_COMENTARIO.sub("", janela))
    xml = _XML_ENCODING.match(janela)
    rotulo = meta.group(1) if meta else (xml.group(1) if xml else None)
    return rotulo, meta is not None


def _utf16_sem_bom(corpo):
    """UTF-16 sem BOM: texto latino tem NUL em um lado dos pares. Devolve (codec, texto) ou None."""
    amostra = corpo[:4096]
    lado = len(amostra) // 2
    if lado < 2:
        return None
    pares, impares = amostra[0::2].count(0), amostra[1::2].count(0)
    if impares >= 0.3 * lado and pares <= 0.02 * lado:
        codec = "utf-16-le"
    elif pares >= 0.3 * lado and impares <= 0.02 * lado:
        codec = "utf-16-be"
    else:
        return None
    texto = _estrito(corpo, codec)
    return (codec, texto) if texto is not None else None


def _detectar(corpo, bibliotecas):
    """Melhor candidato do charset-normalizer: ((codec, confiança), None) ou (None, motivo)."""
    try:
        import charset_normalizer
    except ImportError:
        return None, "sem detector; assumido cp1252"
    bibliotecas["charset-normalizer"] = _versao("charset-normalizer", charset_normalizer)
    try:
        achados = charset_normalizer.from_bytes(corpo[:LIMITE_DETECTOR])
        melhor = achados.best()
        if melhor is None:
            return None, "detector sem candidato; assumido cp1252"
        escolhido = _preferir_ocidental(achados, melhor)
        codec = _resolver_codec(escolhido.encoding)
    except Exception as exc:  # o detector é opcional: falha dele não derruba a leitura
        return None, "detector falhou (%s); assumido cp1252" % type(exc).__name__
    if codec is None:
        return None, "detector devolveu codec desconhecido; assumido cp1252"
    return (codec, round(1.0 - escolhido.chaos, 4)), None


def _preferir_ocidental(achados, melhor):
    """Prefere cp1252/latin-1 quando o detector também os aceita: em texto latino ocidental
    (português, francês) ele escolhe cp1250 e troca ã por ă, õ por ő."""
    if melhor.encoding in PREFERIDOS:
        return melhor
    por_nome = {}
    for achado in achados:
        por_nome.setdefault(achado.encoding, achado)
    for nome in PREFERIDOS:
        achado = por_nome.get(nome)
        if achado is not None and achado.chaos <= melhor.chaos + MARGEM_CHAOS:
            return achado
    return melhor


def _por_declarado(corpo, codec):
    """Decodifica pelo charset declarado; (texto ou None, nome normalizado usado)."""
    nome = _canonico(codec)
    if nome == "iso-8859-1" and len(corpo.translate(None, C1)) != len(corpo):
        texto = _estrito(corpo, "cp1252")  # prática da web: latin-1 declarado com bytes C1 é cp1252
        if texto is not None:
            return texto, "windows-1252"
    return _estrito(corpo, codec), nome


def _por_detector(corpo, enc, dec, lacunas, bibliotecas):
    """Último recurso: detector; sem ele (ou sem candidato), windows-1252 com lacuna."""
    achado, motivo = _detectar(corpo, bibliotecas)
    if achado is None:
        lacunas["encoding"] = motivo
        texto, dec["substituicoes"] = _tolerante(corpo, "cp1252")
        enc["detectado"], enc["confianca"] = "windows-1252", None
        return texto, "cp1252"
    codec, confianca = achado
    texto, dec["substituicoes"] = _tolerante(corpo, codec)
    enc["detectado"], enc["confianca"] = _canonico(codec), confianca
    return texto, "detector"


def _escolher(corpo, bom, cod_decl, enc, dec, lacunas, bibliotecas):
    """Precedência: BOM, UTF-16 sem BOM, ASCII, declarado, UTF-8 (estrito, depois remendado),
    detector, cp1252. Devolve (texto, via)."""
    if bom:
        codec = "utf-8" if bom == "utf-8-sig" else bom
        texto, dec["substituicoes"] = _tolerante(corpo, codec)
        enc["detectado"], enc["confianca"] = _canonico(codec), 1.0
        return texto, "bom"
    largo = _utf16_sem_bom(corpo)
    if largo is not None:
        enc["detectado"], enc["confianca"] = largo[0], None
        return largo[1], "utf16_sem_bom"
    if corpo.isascii() and ESC not in corpo:
        enc["detectado"], enc["confianca"] = "ascii", 1.0
        return corpo.decode("ascii"), "ascii"
    if cod_decl and _familia(_canonico(cod_decl)) not in ("utf-16", "utf-32"):
        texto, nome = _por_declarado(corpo, cod_decl)
        if texto is not None:
            enc["detectado"], enc["confianca"] = nome, (1.0 if nome == "utf-8" else None)
            return texto, "declarado"
    texto = _estrito(corpo, "utf-8")
    if texto is not None:
        enc["detectado"], enc["confianca"] = "utf-8", 1.0
        return texto, "utf8"
    remendado = _utf8_com_falhas(corpo)
    if remendado is not None:
        texto, dec["substituicoes"], confianca = remendado
        enc["detectado"], enc["confianca"] = "utf-8", confianca
        return texto, "utf8"
    return _por_detector(corpo, enc, dec, lacunas, bibliotecas)


def _bate(cod_decl, via, enc, corpo):
    """O declarado é coerente com os bytes? (UTF-8 válido com bytes altos contradiz um legado)."""
    if cod_decl is None:
        return False
    familia = _familia(_canonico(cod_decl))
    if via == "bom":
        return familia == _familia(enc["bom"])
    if familia in ("utf-16", "utf-32"):  # sem BOM, só se os bytes forem mesmo UTF-16/32
        return via == "utf16_sem_bom" and familia == _familia(enc["detectado"])
    if via == "ascii":
        return True
    if via == "utf8" or _estrito(corpo, "utf-8") is not None:
        return familia == "utf-8"
    return via == "declarado"


def _decodificar(dados, html, lacunas, bibliotecas):
    """Devolve (texto, encoding, decode, meta_na_janela)."""
    enc = {"detectado": None, "confianca": None, "bom": None, "declarado": None, "declarado_bate": None}
    dec = {"substituicoes": 0, "erro": None}
    bom, corpo = _tirar_bom(dados)
    enc["bom"] = bom
    rotulo, na_janela = _declarado_html(dados, bom, corpo) if html else (None, False)
    cod_decl = _resolver_codec(rotulo) if rotulo else None
    if rotulo:
        enc["declarado"] = _canonico(cod_decl) if cod_decl else rotulo.lower()
        if cod_decl is None:
            lacunas["charset_declarado"] = "rótulo desconhecido para o Python: " + rotulo
    if not dados:
        lacunas["encoding"] = "arquivo vazio: nada a detectar"
        return "", enc, dec, na_janela
    texto, via = _escolher(corpo, bom, cod_decl, enc, dec, lacunas, bibliotecas)
    if rotulo:
        enc["declarado_bate"] = _bate(cod_decl, via, enc, corpo)
    return texto, enc, dec, na_janela


# ---------------------------------------------------------------- estrutura comum

def _estrutura(fonte, contagem):
    """Uma fonte de estrutura declarada; contagem = {"1": n, ...}. Vazia se não há cabeçalho."""
    niveis = [int(n) for n, q in contagem.items() if q]
    if not niveis:
        return []
    return [{"fonte": fonte, "entradas": sum(contagem.values()),
             "profundidade": max(niveis) - min(niveis) + 1}]


def _estourou(limite):
    return limite is not None and time.monotonic() > limite


def _limite(ctx, inicio):
    try:
        return inicio + float(ctx.get("prazo_s"))
    except (TypeError, ValueError, AttributeError):
        return None


def _definir_texto(r, texto):
    if len(texto) > LIMITE_TEXTO:
        r["lacunas"]["_texto"] = "truncado em %d de %d caracteres" % (LIMITE_TEXTO, len(texto))
    r["_texto"] = texto[:LIMITE_TEXTO]


# ---------------------------------------------------------------- Markdown

def _parece_dados(linhas, marca):
    """Confere que o miolo tem cara de YAML (---) ou TOML (+++), e não de texto entre duas réguas."""
    for linha in linhas:
        if not linha.strip() or linha[0] in " \t#":
            continue
        if marca == "---" and (_CHAVE_YAML.match(linha) or linha.startswith("-")):
            continue
        if marca == "+++" and ("=" in linha or linha.startswith("[")):
            continue
        return False
    return True


def _separar_front_matter(texto):
    """Front matter colado no topo (--- ou +++). Devolve (miolo ou None, texto sem ele)."""
    if not texto.startswith(("---", "+++")):
        return None, texto
    linhas = texto.split("\n")
    marca = linhas[0].rstrip(" \t\r")
    if marca not in ("---", "+++"):
        return None, texto
    fechos = ("---", "...") if marca == "---" else ("+++",)
    for i in range(1, len(linhas)):
        if linhas[i].rstrip(" \t\r") in fechos:
            miolo = linhas[1:i]
            if not _parece_dados(miolo, marca):
                return None, texto
            return "\n".join(miolo), "\n".join(linhas[i + 1:])
    return None, texto


def _lingua_front_matter(miolo):
    """lang, language ou idioma do front matter (primeira ocorrência no nível de cima)."""
    achado = _LINGUA_FM.search(miolo)
    if not achado:
        return None
    valor = achado.group(1)
    citado = re.match(r"([\"'])(.*?)\1", valor)
    valor = citado.group(2) if citado else re.split(r"\s#", valor)[0]
    return valor.strip() or None


def _importar_md():
    try:
        import markdown_it
    except ImportError:
        return None
    return markdown_it


def _niveis_html_cru(conteudo, contagem):
    """Conta <h1>..<h6> de abertura dentro de um bloco de HTML cru (sem comentário, pre, script, style)."""
    for nivel in _ABRE_H.findall(_IGNORADOS_MD.sub("", conteudo)):
        contagem[nivel] += 1


def _contar_tabelas(MarkdownIt, texto, limite, lacunas):
    """Tabelas GFM (extensão, não é CommonMark). Só o bloco: o inline não muda a contagem."""
    if "|" not in texto:  # a linha de cabeçalho da tabela exige pipe
        return 0
    if _estourou(limite):
        lacunas["prazo"] = "prazo estourado antes de contar tabelas GFM"
        return None
    analisador = MarkdownIt("commonmark").enable("table").disable(["inline", "text_join"], True)
    return sum(1 for t in analisador.parse(texto) if t.type == "table_open")


def _contar_md(MarkdownIt, texto, front_matter, limite, lacunas):
    """Bloco md: contagem pelos tokens do parser CommonMark puro (sem a extensão de tabela)."""
    atx = dict.fromkeys(NIVEIS, 0)
    setext = {"1": 0, "2": 0}
    cru = dict.fromkeys(NIVEIS, 0)
    cercas = recuado = 0
    tokens = MarkdownIt("commonmark").disable(["inline", "text_join"], True).parse(texto)
    for t in tokens:
        if t.type == "heading_open":
            alvo = atx if t.markup.startswith("#") else setext
            alvo[t.tag[1]] += 1
        elif t.type == "fence":
            cercas += 1
        elif t.type == "code_block":
            recuado += 1
        elif t.type == "html_block":
            _niveis_html_cru(t.content, cru)
    return {
        "front_matter": front_matter,
        "cabecalhos_atx": atx,
        "cabecalhos_setext": setext,
        "cabecalhos_html_cru": cru,
        "cercas": cercas,
        "codigo_recuado": recuado,
        "tabelas_gfm": _contar_tabelas(MarkdownIt, texto, limite, lacunas),
        "tabelas_gfm_e_extensao": True,
        "tokens_total": len(tokens),  # tokens de bloco (o inline não é aberto)
    }


def _fazer_md(r, texto, limite):
    miolo, resto = _separar_front_matter(texto)
    if miolo is not None:
        r["lingua_declarada"] = _lingua_front_matter(miolo)
    _definir_texto(r, resto)
    lib = _importar_md()
    if lib is None:
        r["lacunas"]["md"] = "markdown-it-py ausente: sem contagem de estrutura (não se conta por regex de linha)"
        return
    r["bibliotecas"]["markdown-it-py"] = _versao("markdown-it-py", lib)
    try:
        md = _contar_md(lib.MarkdownIt, resto, miolo is not None, limite, r["lacunas"])
    except Exception as exc:  # parser falhou: sem contagem, com o motivo
        r["lacunas"]["md"] = "markdown-it-py falhou: " + type(exc).__name__
        return
    r["texto"]["md"] = md
    total = {n: md["cabecalhos_atx"][n] + md["cabecalhos_html_cru"][n] + md["cabecalhos_setext"].get(n, 0)
             for n in NIVEIS}
    r["estrutura_declarada"] = _estrutura("md_cabecalhos", total)


# ---------------------------------------------------------------- HTML

class _LeitorHtml(HTMLParser):
    """Conta cabeçalhos, pega título, lang, meta e junta o texto visível."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.contagem_h = dict.fromkeys(NIVEIS, 0)
        self.titulo_partes = None   # None = nenhum <title> visto
        self.em_titulo = False
        self.lingua = None
        self.meta_charset = None
        self.http_equiv_charset = None
        self.doctype = False
        self.geradores = []
        self.partes = []
        self.ocultos = 0            # profundidade dentro de script/style/template
        self.em_pre = 0
        self.viu_html = False

    @property
    def titulo(self):
        if self.titulo_partes is None:
            return None
        return _ESPACOS.sub(" ", "".join(self.titulo_partes)).strip()[:TITULO_MAX]

    def handle_decl(self, decl):
        if decl.strip().lower().startswith("doctype"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        a = {}
        for nome, valor in attrs:
            a.setdefault(nome, valor)
        if tag == "title" and self.titulo_partes is None:
            self.titulo_partes, self.em_titulo = [], True
            return
        self.em_titulo = False  # qualquer marca encerra o título (ele só tem texto)
        if tag == "html" and not self.viu_html:
            self.viu_html = True
            lingua = (a.get("lang") or a.get("xml:lang") or "").strip()
            self.lingua = lingua or None
        elif tag == "meta":
            self._meta(a)
        elif tag in _OCULTOS:
            self.ocultos += 1
        elif tag == "pre":
            self.em_pre += 1
        elif tag in TAGS_H and not self.ocultos:
            self.contagem_h[tag[1]] += 1
        if tag in _BLOCOS:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.em_titulo = False
        elif tag in _OCULTOS:
            self.ocultos = max(0, self.ocultos - 1)
        elif tag == "pre":
            self.em_pre = max(0, self.em_pre - 1)
        if tag in _BLOCOS:
            self.partes.append("\n")

    def handle_data(self, data):
        if self.em_titulo:
            self.titulo_partes.append(data)
        elif not self.ocultos:
            self.partes.append(data if self.em_pre else _ESPACOS.sub(" ", data))

    def _meta(self, a):
        if self.meta_charset is None and a.get("charset"):
            self.meta_charset = a["charset"].strip().lower()
        equiv = (a.get("http-equiv") or "").strip().lower()
        if equiv == "content-type" and self.http_equiv_charset is None:
            achado = _CHARSET_CONTENT.search(a.get("content") or "")
            if achado:
                self.http_equiv_charset = achado.group(1).lower()
        if (a.get("name") or "").strip().lower() == "generator" and (a.get("content") or "").strip():
            self.geradores.append(a["content"].strip()[:200])

    def texto_visivel(self):
        linhas = (_ESPACOS_LINHA.sub(" ", linha).strip() for linha in "".join(self.partes).split("\n"))
        return "\n".join(linha for linha in linhas if linha)


def _aplicacao(gerador):
    """Separa nome e versão de um <meta name="generator"> quando dá para reconhecer."""
    achado = _GERADOR.match(gerador)
    nome, versao = (achado.group(1), achado.group(2)) if achado else (gerador, None)
    return {"nome": nome, "versao": versao, "data": None, "fonte": "meta_generator"}


def _alimentar_html(leitor, texto, limite, lacunas):
    """Entrega o texto ao parser em fatias, conferindo o prazo entre elas."""
    try:
        for inicio in range(0, len(texto), PASSO_HTML):
            if _estourou(limite):
                lacunas["prazo"] = "prazo estourado durante a leitura do HTML: contagem parcial"
                return
            leitor.feed(texto[inicio:inicio + PASSO_HTML])
        leitor.close()
    except Exception as exc:  # parser tolerante, mas o que já foi lido fica
        lacunas["html"] = "html.parser falhou: " + type(exc).__name__


def _fazer_html(r, texto, limite, na_janela):
    leitor = _LeitorHtml()
    _alimentar_html(leitor, texto, limite, r["lacunas"])
    r["texto"]["html"] = {
        "h": leitor.contagem_h,
        "title": leitor.titulo,
        "lang": leitor.lingua,
        "meta_charset": leitor.meta_charset,
        "meta_charset_na_janela": na_janela,
        "http_equiv_charset": leitor.http_equiv_charset,
        "doctype": leitor.doctype,
    }
    r["lingua_declarada"] = leitor.lingua
    r["estrutura_declarada"] = _estrutura("html_cabecalhos", leitor.contagem_h)
    vistos = []
    for gerador in leitor.geradores:
        if gerador not in vistos:
            vistos.append(gerador)
    r["aplicacoes_criadoras"] = [_aplicacao(g) for g in vistos]
    _definir_texto(r, leitor.texto_visivel())


# ---------------------------------------------------------------- TXT

def _fazer_txt(r, texto):
    linhas = _QUEBRA.split(texto)
    if linhas[-1] == "":  # o último terminador não abre linha nova (vale para texto vazio)
        linhas.pop()
    cheias = [len(linha) for linha in linhas if linha.strip()]
    r["texto"]["txt"] = {
        "linhas": len(linhas),
        "linhas_vazias": len(linhas) - len(cheias),
        "maior_linha": max((len(linha) for linha in linhas), default=0),
        "linha_media": round(sum(cheias) / len(cheias), 2) if cheias else 0.0,
        "form_feed": chr(12) in texto,
        "crlf": "\r\n" in texto,
    }
    _definir_texto(r, texto)


# ---------------------------------------------------------------- entrada

def _envelope(formato, tamanho):
    return {
        "texto": {"formato": formato, "bytes": tamanho, "decode": {"substituicoes": 0, "erro": None},
                  "md": None, "html": None, "txt": None},
        "aplicacoes_criadoras": [],
        "inibidor": None,
        "lingua_declarada": None,
        "estrutura_declarada": [],
        "encoding": None,
        "_texto": None,
        "_paginas": None,
        "lacunas": {},
        "bibliotecas": {},
        "erro": None,
    }


def _preencher(r, dados, ctx, inicio):
    formato = r["texto"]["formato"]
    if formato not in ("md", "html", "txt"):
        r["lacunas"]["formato"] = "formato não coberto por este leitor: %s" % formato
        return
    limite = _limite(ctx, inicio)
    html = formato == "html"
    if html:
        r["lacunas"]["precedencia_html"] = (
            "a spec WHATWG não está no acervo; a precedência (BOM, depois meta ou declaração XML "
            "nos primeiros 1024 bytes, depois UTF-8 estrito) vem da prática"
        )
    texto, enc, dec, na_janela = _decodificar(dados, html, r["lacunas"], r["bibliotecas"])
    r["encoding"] = enc
    r["texto"]["decode"] = dec
    if _estourou(limite):
        _definir_texto(r, texto)
        r["lacunas"]["prazo"] = "prazo estourado depois da decodificação: estrutura não lida"
        return
    if formato == "md":
        _fazer_md(r, texto, limite)
    elif html:
        _fazer_html(r, texto, limite, na_janela)
    else:
        _fazer_txt(r, texto)


def ler(dados, ctx):
    """Lê um arquivo de texto (md, html ou txt). Nunca levanta exceção."""
    inicio = time.monotonic()
    formato = ctx.get("formato_id") if isinstance(ctx, dict) else None
    r = _envelope(formato, len(dados) if hasattr(dados, "__len__") else 0)
    try:
        _preencher(r, bytes(dados), ctx if isinstance(ctx, dict) else {}, inicio)
    except Exception as exc:  # falha inesperada volta em erro (KeyboardInterrupt e SystemExit passam)
        r["erro"] = (type(exc).__name__ + ": " + " ".join(str(exc).split()))[:200]
    return r
