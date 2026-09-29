"""Card #3189, ato temporario `acervo censo obra`: leitor de DOCX, PPTX e XLSX (OOXML).

Le so com a biblioteca padrao (zipfile + xml.etree): identidade do pacote,
propriedades (docProps), titulos do DOCX, slides do PPTX, planilhas do XLSX
e o texto. Nada de terceiros, nada de conversao: so contagem e leitura.
"""
import io
import posixpath
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

TETO_TEXTO = 4_000_000            # caracteres de _texto
TETO_PARTE = 32 * 1024 * 1024     # partes pequenas lidas inteiras (props, estilos, slides)
TETO_FLUXO = 256 * 1024 * 1024    # partes lidas em fluxo (corpo do DOCX, sharedStrings)
TETO_LISTA = 2000                 # itens de lista no bloco

PADROES = {"docx": "word/document.xml", "pptx": "ppt/presentation.xml", "xlsx": "xl/workbook.xml"}
FAMILIAS = {"wordprocessingml": "docx", "presentationml": "pptx", "spreadsheetml": "xlsx"}

_SLIDE = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
_NOTA = re.compile(r"^ppt/notesSlides/[^/]+\.xml$")
_TITULO_N = re.compile(r"^(?:heading|t[ií]tulo|titulo|ttulo)\s*([1-9])$")
_TITULO_SEM_N = re.compile(r"^(?:title|t[ií]tulo|titulo|ttulo)$")


class _Recusa(Exception):
    """Parte que nao se le: grande demais ou com entidade XML."""


class _PrazoEstourado(Exception):
    """Acabou o tempo do `ler`."""


class _Prazo:
    """Relogio do `ler` inteiro."""

    def __init__(self, segundos):
        try:
            self.segundos = float(segundos)
        except (TypeError, ValueError):
            self.segundos = None
        self.fim = None if self.segundos is None else time.monotonic() + self.segundos

    def estourou(self):
        return self.fim is not None and time.monotonic() >= self.fim


class _Fluxo:
    """Envolve um membro do zip: confere teto, entidade XML e prazo a cada bloco lido."""

    def __init__(self, fluxo, teto, prazo):
        self.fluxo = fluxo
        self.teto = teto
        self.prazo = prazo
        self.lidos = 0
        self.cauda = b""

    def read(self, n=-1):
        if self.prazo.estourou():
            raise _PrazoEstourado()
        bloco = self.fluxo.read(n if n and n > 0 else 65536)
        self.lidos += len(bloco)
        if self.lidos > self.teto:
            raise _Recusa("parte maior que o teto de leitura")
        janela = self.cauda + bloco
        if b"<!ENTITY" in janela:
            raise _Recusa("XML com declaracao de entidade")
        self.cauda = janela[-8:]
        return bloco


# ---------------------------------------------------------------- utilidades

def _linha(exc):
    """Mensagem de excecao numa linha so."""
    return " ".join(str(exc).split())[:200]


def _partir(tag):
    """'{ns}nome' -> (ns, nome)."""
    if isinstance(tag, str) and tag.startswith("{"):
        ns, _, nome = tag[1:].partition("}")
        return ns, nome
    return "", tag if isinstance(tag, str) else ""


def _local(tag, familia):
    """Nome local se a etiqueta e da familia OOXML (transitional ou strict); senao ''."""
    ns, nome = _partir(tag)
    return nome if ns.endswith("/main") and familia in ns else ""


def _attr(el, nome):
    """Atributo pelo nome local, qualquer que seja o prefixo."""
    for chave, valor in el.attrib.items():
        if chave.rpartition("}")[2] == nome:
            return valor
    return None


def _inteiro(texto):
    if texto is None:
        return None
    try:
        return int(str(texto).strip())
    except ValueError:
        return None


def _valores(raiz):
    """{nome local: texto} dos filhos diretos; vazio vira None."""
    return {_partir(el.tag)[1]: ((el.text or "").strip() or None) for el in raiz}


def _ordenado(contagem):
    """Counter de niveis -> {"1": n, ...} em ordem numerica."""
    return {str(k): contagem[k] for k in sorted(contagem)}


def _envelope(bloco, **campos):
    saida = {
        "ooxml": bloco,
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
    saida.update(campos)
    return saida


def _bloco_vazio(tipo):
    return {
        "tipo": tipo,
        "conteudo_tipo": None,
        "aplicacao": None,
        "core": None,
        "docx": None,
        "pptx": None,
        "xlsx": None,
        "membros_total": None,
    }


def _tipo_do_ctx(ctx):
    formato_id = ctx.get("formato_id")
    return formato_id if formato_id in PADROES else None


# ------------------------------------------------------------ leitura do zip

def _existe(zf, nome):
    try:
        zf.getinfo(nome)
    except KeyError:
        return False
    return True


def _bytes_da_parte(zf, nome, teto):
    """(bytes, None) ou (None, motivo)."""
    try:
        info = zf.getinfo(nome)
    except KeyError:
        return None, "ausente"
    if info.flag_bits & 1:
        return None, "membro cifrado"
    try:
        with zf.open(info) as f:
            dados = f.read(teto + 1)
    except Exception as exc:  # crc, zlib, compressao nao suportada...
        return None, "ilegivel: " + _linha(exc)
    if len(dados) > teto:
        return None, "maior que o teto de leitura"
    return dados, None


def _raiz_xml(zf, nome, teto=TETO_PARTE):
    """(raiz, None) ou (None, motivo) para uma parte XML pequena."""
    dados, motivo = _bytes_da_parte(zf, nome, teto)
    if dados is None:
        return None, motivo
    if b"<!ENTITY" in dados:
        return None, "XML com declaracao de entidade"
    try:
        return ET.fromstring(dados), None
    except (ET.ParseError, ValueError, LookupError) as exc:
        return None, "XML malformado: " + _linha(exc)


def _em_fluxo(zf, nome, prazo, consumidor):
    """Passa os eventos XML do membro ao consumidor. None se deu certo; senao o motivo."""
    try:
        info = zf.getinfo(nome)
    except KeyError:
        return "ausente"
    if info.flag_bits & 1:
        return "membro cifrado"
    try:
        with zf.open(info) as bruto:
            consumidor(ET.iterparse(_Fluxo(bruto, TETO_FLUXO, prazo), events=("start", "end")))
    except _PrazoEstourado:
        return "prazo"
    except _Recusa as exc:
        return str(exc)
    except ET.ParseError as exc:
        return "XML malformado: " + _linha(exc)
    except Exception as exc:  # zip corrompido no meio do membro
        return "ilegivel: " + _linha(exc)
    return None


def _registrar(lacunas, campo, motivo, prazo):
    """Motivo 'prazo' vai em lacunas['prazo']; o resto no campo."""
    if motivo == "prazo":
        lacunas["prazo"] = f"prazo de {prazo.segundos:g} s estourado; resultado parcial"
    else:
        lacunas[campo] = motivo


# ------------------------------------------------------- pacote e relacoes

def _caminho_rels(parte):
    """Caminho do .rels de uma parte; '' e a raiz do pacote."""
    pasta, _, base = parte.rpartition("/")
    return (pasta + "/" if pasta else "") + "_rels/" + base + ".rels"


def _resolver(origem, alvo):
    if alvo.startswith("/"):
        return alvo[1:]
    return posixpath.normpath(posixpath.join(posixpath.dirname(origem), alvo))


def _relacoes(zf, origem):
    """[(tipo, caminho)] das relacoes internas de uma parte."""
    raiz, _ = _raiz_xml(zf, _caminho_rels(origem))
    if raiz is None:
        return []
    saida = []
    for el in raiz:
        if _partir(el.tag)[1] != "Relationship" or el.get("TargetMode") == "External":
            continue
        if el.get("Type") and el.get("Target"):
            saida.append((el.get("Type"), _resolver(origem, el.get("Target"))))
    return saida


def _parte_relacionada(zf, origem, sufixo, padrao):
    """Parte apontada por relacao de tipo terminado em `sufixo`; senao o caminho padrao."""
    for tipo, alvo in _relacoes(zf, origem):
        if tipo.endswith(sufixo) and _existe(zf, alvo):
            return alvo
    return padrao


def _tipos_de_conteudo(zf):
    """({parte: tipo}, {extensao: tipo}) de [Content_Types].xml."""
    raiz, _ = _raiz_xml(zf, "[Content_Types].xml")
    por_parte, por_extensao = {}, {}
    for el in raiz if raiz is not None else []:
        nome = _partir(el.tag)[1]
        if nome == "Override" and el.get("PartName"):
            por_parte[el.get("PartName").lstrip("/")] = el.get("ContentType")
        elif nome == "Default" and el.get("Extension"):
            por_extensao[el.get("Extension").lower()] = el.get("ContentType")
    return por_parte, por_extensao


def _tipo_da_parte(tipos, parte):
    por_parte, por_extensao = tipos
    if parte in por_parte:
        return por_parte[parte]
    return por_extensao.get(parte.rpartition(".")[2].lower())


def _identificar(zf, tipos, formato_id):
    """(tipo, parte principal) lidos do pacote; o formato_id so desempata."""
    parte = None
    for rel_tipo, alvo in _relacoes(zf, ""):
        if rel_tipo.endswith("/officeDocument") and _existe(zf, alvo):
            parte = alvo
            break
    if parte is None:
        for tipo in sorted(PADROES, key=lambda t: t != formato_id):
            if _existe(zf, PADROES[tipo]):
                parte = PADROES[tipo]
                break
    if parte is None:
        return None, None
    conteudo = _tipo_da_parte(tipos, parte) or ""
    for familia, tipo in FAMILIAS.items():
        if familia in conteudo:
            return tipo, parte
    for tipo, padrao in PADROES.items():
        if parte == padrao:
            return tipo, parte
    return None, parte


def _inibidor(infos):
    """Password protection: membro com bit de criptografia ou EncryptedPackage no zip."""
    cifrados = sum(1 for i in infos if i.flag_bits & 1)
    if cifrados:
        return {"tipo": "Password protection", "alvo": f"{cifrados} membros"}
    if any(i.filename.rpartition("/")[2] == "EncryptedPackage" for i in infos):
        return {"tipo": "Password protection", "alvo": "OOXML cifrado"}
    return None


# ------------------------------------------------------------ propriedades

def _ler_app(zf, lacunas):
    """docProps/app.xml -> dict com as chaves de `aplicacao`."""
    app = dict.fromkeys(
        ("application", "app_version", "company", "template", "total_time", "paginas", "palavras", "slides")
    )
    caminho = _parte_relacionada(zf, "", "/extended-properties", "docProps/app.xml")
    raiz, motivo = _raiz_xml(zf, caminho)
    if raiz is None:
        lacunas["aplicacao"] = f"{caminho}: {motivo}"
        return app
    v = _valores(raiz)
    app.update(
        application=v.get("Application"),
        app_version=v.get("AppVersion"),
        company=v.get("Company"),
        template=v.get("Template"),
        total_time=_inteiro(v.get("TotalTime")),
        paginas=_inteiro(v.get("Pages")),
        palavras=_inteiro(v.get("Words")),
        slides=_inteiro(v.get("Slides")),
    )
    return app


def _ler_core(zf, lacunas):
    """docProps/core.xml -> dict com as chaves de `core`."""
    core = dict.fromkeys(("creator", "last_modified_by", "created", "modified", "title", "language"))
    caminho = _parte_relacionada(zf, "", "/core-properties", "docProps/core.xml")
    raiz, motivo = _raiz_xml(zf, caminho)
    if raiz is None:
        lacunas["core"] = f"{caminho}: {motivo}"
        return core
    v = _valores(raiz)
    core.update(
        creator=v.get("creator"),
        last_modified_by=v.get("lastModifiedBy"),
        created=v.get("created"),
        modified=v.get("modified"),
        title=v.get("title"),
        language=v.get("language"),
    )
    return core


def _criadoras(app, core):
    """Uma aplicacao criadora por programa: Application + AppVersion + data de criacao."""
    if not app["application"]:
        return []
    return [{"nome": app["application"], "versao": app["app_version"],
             "data": core["created"], "fonte": "docProps/app.xml"}]


# -------------------------------------------------------------------- DOCX

def _nivel_por_nome(nome):
    """Nivel de titulo pelo nome ou styleId (heading N, titulo N, Title); None se nao e."""
    if not nome:
        return None
    nome = unicodedata.normalize("NFC", nome).strip().lower()
    achou = _TITULO_N.match(nome)
    if achou:
        return int(achou.group(1))
    return 1 if _TITULO_SEM_N.match(nome) else None


def _ler_estilos(raiz):
    """({styleId: {nome, base, outline}}, lingua de docDefaults) de word/styles.xml."""
    estilos, lingua = {}, None
    for el in raiz:
        nome_el = _local(el.tag, "wordprocessingml")
        if nome_el == "docDefaults" and lingua is None:
            for x in el.iter():
                if _local(x.tag, "wordprocessingml") == "lang" and _attr(x, "val"):
                    lingua = _attr(x, "val")
                    break
        elif nome_el == "style" and _attr(el, "styleId"):
            estilos[_attr(el, "styleId")] = _dados_do_estilo(el)
    return estilos, lingua


def _dados_do_estilo(el):
    info = {"nome": None, "base": None, "outline": None}
    for f in el:
        nome = _local(f.tag, "wordprocessingml")
        if nome == "name":
            info["nome"] = _attr(f, "val")
        elif nome == "basedOn":
            info["base"] = _attr(f, "val")
        elif nome == "pPr":
            for g in f:
                if _local(g.tag, "wordprocessingml") == "outlineLvl":
                    info["outline"] = _inteiro(_attr(g, "val"))
    return info


def _resolver_estilo(estilos, sid):
    """(nivel pelo nome, outlineLvl) do estilo, subindo a cadeia basedOn (com guarda de ciclo)."""
    nivel, outline, visto, atual = None, None, set(), sid
    while atual is not None and atual not in visto:
        visto.add(atual)
        est = estilos.get(atual)
        if nivel is None:
            nivel = _nivel_por_nome(atual) or (_nivel_por_nome(est["nome"]) if est else None)
        if est is None:
            break
        if outline is None:
            outline = est["outline"]
        atual = est["base"]
    return nivel, outline


def _eh_fallback(tag):
    """mc:Fallback repete o que mc:Choice ja disse; nao se conta duas vezes."""
    return tag.endswith("}Fallback") and "markup-compatibility" in tag


class _Par:
    """Paragrafo em andamento."""

    __slots__ = ("estilo", "outline", "texto")

    def __init__(self):
        self.estilo = None
        self.outline = None
        self.texto = []


class _Corpo:
    """Acumula o que se le do corpo do DOCX enquanto o XML passa."""

    def __init__(self, estilos):
        self.estilos = estilos
        self.cache = {}
        self.paragrafos = 0
        self.tabelas = 0
        self.secoes = 0
        self.titulos = Counter()
        self.outline = Counter()
        self.linhas = []
        self.tamanho = 0

    def varrer(self, eventos):
        pilha = []      # (nome, elemento) dos ancestrais abertos
        abertos = []    # paragrafos em andamento (caixa de texto aninha paragrafo)
        ignorado = 0    # profundidade dentro de mc:Fallback
        for evento, el in eventos:
            if evento == "start":
                if ignorado or _eh_fallback(el.tag):
                    ignorado += 1
                    pilha.append(("?", el))
                    continue
                nome = _local(el.tag, "wordprocessingml")
                if nome == "p":
                    abertos.append(_Par())
                elif nome == "tbl":
                    self.tabelas += 1
                pilha.append((nome, el))
                continue
            nome = pilha.pop()[0]
            if ignorado:
                ignorado -= 1
            else:
                pai = pilha[-1][0] if pilha else ""
                avo = pilha[-2][0] if len(pilha) > 1 else ""
                self._fim(nome, el, pai, avo, abertos)
            el.clear()
            if pilha:
                pilha[-1][1].remove(el)   # nao segura na memoria o que ja foi lido

    def _fim(self, nome, el, pai, avo, abertos):
        if nome == "t":
            if abertos:
                abertos[-1].texto.append(el.text or "")
        elif nome in ("tab", "br", "cr") and pai == "r":
            if abertos:
                abertos[-1].texto.append(" ")
        elif nome == "pStyle" and pai == "pPr" and avo == "p" and abertos:
            abertos[-1].estilo = _attr(el, "val")
        elif nome == "outlineLvl" and pai == "pPr" and avo == "p" and abertos:
            abertos[-1].outline = _inteiro(_attr(el, "val"))
        elif nome == "sectPr" and (pai == "body" or (pai == "pPr" and avo == "p")):
            self.secoes += 1
        elif nome == "p" and abertos:
            self._fechar(abertos.pop())

    def _estilo(self, sid):
        if sid not in self.cache:
            self.cache[sid] = _resolver_estilo(self.estilos, sid)
        return self.cache[sid]

    def _fechar(self, par):
        self.paragrafos += 1
        nivel_nome, outline_estilo = self._estilo(par.estilo)
        outline = par.outline if par.outline is not None else outline_estilo
        nivel_outline = outline + 1 if outline is not None and 0 <= outline <= 8 else None
        if nivel_outline is not None:
            self.outline[nivel_outline] += 1
        nivel = nivel_nome or nivel_outline
        if nivel is not None:
            self.titulos[nivel] += 1
        if self.tamanho <= TETO_TEXTO:
            linha = "".join(par.texto)
            self.linhas.append(linha)
            self.tamanho += len(linha) + 1

    def texto(self):
        return "\n".join(self.linhas)[:TETO_TEXTO]


def _estrutura_docx(titulos):
    """Uma fonte: os paragrafos-titulo. Profundidade = maior nivel - menor + 1."""
    if not titulos:
        return []
    return [{"fonte": "docx_titulos", "entradas": sum(titulos.values()),
             "profundidade": max(titulos) - min(titulos) + 1}]


def _estilos_docx(zf, parte, lacunas):
    caminho = _parte_relacionada(zf, parte, "/styles", "word/styles.xml")
    raiz, motivo = _raiz_xml(zf, caminho)
    if raiz is None:
        lacunas["estilos_docx"] = f"{caminho}: {motivo}; titulos so pelo styleId"
        return {}, None
    return _ler_estilos(raiz)


def _ler_docx(zf, parte, prazo, lacunas):
    """(bloco, texto, estrutura, lingua de docDefaults) do documento Word."""
    estilos, lingua = _estilos_docx(zf, parte, lacunas)
    corpo = _Corpo(estilos)
    motivo = _em_fluxo(zf, parte, prazo, corpo.varrer)
    if motivo:
        _registrar(lacunas, "docx", motivo, prazo)
        if corpo.paragrafos == 0:
            lacunas.setdefault("_texto", "corpo do docx nao lido")
            return None, None, [], lingua
    if corpo.tamanho > TETO_TEXTO:
        lacunas["_texto"] = f"truncado em {TETO_TEXTO} caracteres"
    bloco = {
        "paragrafos": corpo.paragrafos,
        "titulos_por_nivel": _ordenado(corpo.titulos),
        "paragrafos_titulo": sum(corpo.titulos.values()),
        "outline_lvl": _ordenado(corpo.outline),
        "tabelas": corpo.tabelas,
        "secoes": corpo.secoes,
    }
    return bloco, corpo.texto(), _estrutura_docx(corpo.titulos), lingua


# -------------------------------------------------------------------- PPTX

def _texto_slide(raiz):
    """Um paragrafo por linha; as corridas (a:t) do paragrafo se juntam sem espaco."""
    linhas = []
    for p in raiz.iter():
        if _local(p.tag, "drawingml") == "p":
            linhas.append("".join(t.text or "" for t in p.iter() if _local(t.tag, "drawingml") == "t"))
    return "\n".join(linhas)


def _tem_titulo(raiz):
    """Ha p:sp com p:ph type=title ou ctrTitle."""
    for sp in raiz.iter():
        if _local(sp.tag, "presentationml") != "sp":
            continue
        ns = _partir(sp.tag)[0]
        ph = sp.find(f"{{{ns}}}nvSpPr/{{{ns}}}nvPr/{{{ns}}}ph")
        if ph is not None and ph.get("type") in ("title", "ctrTitle"):
            return True
    return False


def _ler_pptx(zf, prazo, lacunas):
    """(bloco, texto) da apresentacao."""
    nomes = zf.namelist()
    slides = sorted((int(m.group(1)), n) for n in nomes for m in [_SLIDE.match(n)] if m)
    notas = sum(1 for n in nomes if _NOTA.match(n))
    textos, tamanho, com_titulo, ilegiveis = [], 0, 0, 0
    for _, nome in slides:
        if prazo.estourou():
            _registrar(lacunas, "pptx", "prazo", prazo)
            break
        raiz, _ = _raiz_xml(zf, nome)
        if raiz is None:
            ilegiveis += 1
            continue
        com_titulo += _tem_titulo(raiz)
        if tamanho <= TETO_TEXTO:
            textos.append(_texto_slide(raiz))
            tamanho += len(textos[-1]) + 1
    if ilegiveis:
        lacunas["pptx"] = f"{ilegiveis} slides ilegiveis"
    if tamanho > TETO_TEXTO:
        lacunas["_texto"] = f"truncado em {TETO_TEXTO} caracteres"
    bloco = {"slides": len(slides), "slides_com_titulo": com_titulo, "notas": notas}
    return bloco, "\n".join(textos)[:TETO_TEXTO]


# -------------------------------------------------------------------- XLSX

def _texto_si(si):
    """Texto de um <si>: <t> direto ou corridas <r><t>; a fonetica (rPh) fica de fora."""
    partes = []
    for f in si:
        nome = _local(f.tag, "spreadsheetml")
        if nome == "t":
            partes.append(f.text or "")
        elif nome == "r":
            partes.extend(t.text or "" for t in f if _local(t.tag, "spreadsheetml") == "t")
    return "".join(partes)


class _Cadeias:
    """Acumula as sharedStrings, uma por linha, ate o teto."""

    def __init__(self):
        self.linhas = []
        self.tamanho = 0

    def varrer(self, eventos):
        raiz = None
        for evento, el in eventos:
            if raiz is None:
                raiz = el
            if evento != "end" or _local(el.tag, "spreadsheetml") != "si":
                continue
            linha = _texto_si(el)
            self.linhas.append(linha)
            self.tamanho += len(linha) + 1
            if self.tamanho > TETO_TEXTO:
                return
            raiz.clear()   # solta o que ja foi lido

    def texto(self):
        return "\n".join(self.linhas)[:TETO_TEXTO]


def _texto_xlsx(zf, parte, prazo, lacunas):
    caminho = _parte_relacionada(zf, parte, "/sharedStrings", "xl/sharedStrings.xml")
    if not _existe(zf, caminho):
        lacunas["_texto"] = "xlsx sem xl/sharedStrings.xml"
        return None
    cadeias = _Cadeias()
    motivo = _em_fluxo(zf, caminho, prazo, cadeias.varrer)
    if motivo:
        _registrar(lacunas, "_texto", motivo, prazo)
        if not cadeias.linhas:
            lacunas.setdefault("_texto", "sharedStrings nao lido")
            return None
    if cadeias.tamanho > TETO_TEXTO:
        lacunas["_texto"] = f"truncado em {TETO_TEXTO} caracteres"
    return cadeias.texto()


def _ler_xlsx(zf, parte, prazo, lacunas):
    """(bloco, texto) da pasta de trabalho: nomes das planilhas e sharedStrings."""
    raiz, motivo = _raiz_xml(zf, parte)
    if raiz is None:
        lacunas["xlsx"] = f"{parte}: {motivo}"
        return None, _texto_xlsx(zf, parte, prazo, lacunas)
    folhas = [el for el in raiz.iter() if _local(el.tag, "spreadsheetml") == "sheet"]
    nomes = [_attr(el, "name") for el in folhas if _attr(el, "name") is not None]
    bloco = {"planilhas": len(folhas), "nomes": nomes[:TETO_LISTA]}
    return bloco, _texto_xlsx(zf, parte, prazo, lacunas)


# ------------------------------------------------------------------ entrada

def _ler(dados, ctx):
    prazo = _Prazo(ctx.get("prazo_s"))
    try:
        zf = zipfile.ZipFile(io.BytesIO(dados))
    except zipfile.BadZipFile as exc:
        return _envelope(_bloco_vazio(_tipo_do_ctx(ctx)), erro="zip invalido: " + _linha(exc))
    with zf:
        return _ler_pacote(zf, ctx, prazo)


def _ler_conteudo(zf, tipo, parte, prazo, lacunas):
    """({tipo: bloco}, texto, estrutura, lingua de docDefaults) da parte principal."""
    if parte is None or tipo is None:
        return {}, None, [], None
    if prazo.estourou():
        _registrar(lacunas, tipo, "prazo", prazo)
        return {}, None, [], None
    if tipo == "docx":
        bloco, texto, estrutura, lingua = _ler_docx(zf, parte, prazo, lacunas)
        return {"docx": bloco}, texto, estrutura, lingua
    if tipo == "pptx":
        bloco, texto = _ler_pptx(zf, prazo, lacunas)
        return {"pptx": bloco}, texto, [], None
    bloco, texto = _ler_xlsx(zf, parte, prazo, lacunas)
    return {"xlsx": bloco}, texto, [], None


def _ler_pacote(zf, ctx, prazo):
    lacunas = {}
    infos = zf.infolist()
    inibidor = _inibidor(infos)
    tipos = _tipos_de_conteudo(zf)
    tipo, parte = _identificar(zf, tipos, ctx.get("formato_id"))
    tipo = tipo or _tipo_do_ctx(ctx)
    bloco = _bloco_vazio(tipo)
    bloco["membros_total"] = len(infos)
    if parte is None:
        lacunas["parte_principal"] = "membros cifrados" if inibidor else "pacote sem parte principal OOXML"
    else:
        bloco["conteudo_tipo"] = _tipo_da_parte(tipos, parte)
    app, core = _ler_app(zf, lacunas), _ler_core(zf, lacunas)
    bloco["aplicacao"], bloco["core"] = app, core
    criadoras = _criadoras(app, core)
    if not criadoras:
        lacunas["aplicacoes_criadoras"] = "sem Application em docProps/app.xml"

    campos, texto, estrutura, lingua_padrao = _ler_conteudo(zf, tipo, parte, prazo, lacunas)
    bloco.update(campos)
    if texto is None:
        lacunas.setdefault("_texto", "sem camada de texto lida")

    lingua = core["language"] or lingua_padrao
    if lingua is None:
        lacunas["lingua_declarada"] = "sem dc:language" + (" nem w:lang em docDefaults" if tipo == "docx" else "")
    return _envelope(
        bloco,
        aplicacoes_criadoras=criadoras,
        inibidor=inibidor,
        lingua_declarada=lingua,
        estrutura_declarada=estrutura,
        _texto=texto,
        lacunas=lacunas,
    )


def ler(dados, ctx):
    """Le um pacote OOXML (docx, pptx ou xlsx). Nunca levanta excecao."""
    ctx = ctx if isinstance(ctx, dict) else {}
    try:
        return _ler(dados, ctx)
    except Exception as exc:  # falha inesperada volta em `erro`
        erro = f"falha inesperada: {type(exc).__name__}: {_linha(exc)}"
        return _envelope(_bloco_vazio(_tipo_do_ctx(ctx)), erro=erro)
