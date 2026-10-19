"""card — confere o corpo e os comentarios de um card do rastreador.

Duas reguas, pelo nivel do card:

- story e task: as secoes obrigatorias da arq:0096, como sempre foi;
- epico e feature: a lista de verificacao antipadroes-de-discovery (card #3421), lida do
  acervo. O corpo e o two-pager (criterios T e L); os comentarios sao os tipados do
  parecer (criterios C, F2, F4 e L). So roda o criterio que a lista declara com detector;
  os de detector «leitura» (T7, C6, L5) ficam fora. Tudo sai como aviso: bloqueante e da
  F3 do epico #3365, nunca deste lint.

Texto e cura de cada criterio vem da lista servida; aqui mora so o detector, por id. A
lista que ganhar criterio novo com detector sem detector aqui sai em `avisos` (o que
ficou sem medir), nunca em silencio.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path

from .resultado import Apontamento

# ------------------------------------------------------------------ reguas

CHAVE_ADR = "arq-0096"
REV_ADR = 1
CHAVE_DISCOVERY = "antipadroes-de-discovery"

CAMPOS_STORY = [
    "Negócio:",
    "Ambiente:",
    "Onde:",
    "Passos:",
    "Aceite:",
    "Travas:",
    "Entrega:",
    "Referencial:",
    "Raio de ataque:",
    "Comportamento esperado:",
]

CAMPOS_TASK = [
    "Problema encontrado:",
    "Solução proposta:",
    "Referencial:",
    "Raio de ataque:",
    "Comportamento esperado:",
]

# arq:0096 item 4: a aposta e exigida na saida de captada; a forma, na saida de em-lapidacao.
# Apetite e Aberto ficam fora da recusa; o indice (Produtos documentais, Sai quando, Quebra)
# so fica completo na formalizacao. Continuidade saiu do molde (comentario #2088 do #3408).
ROTULOS_APOSTA = ["Problema", "Resultado", "Medida", "Fora"]
ROTULOS_FORMA = ["Solução", "Peças"]
ESTADOS_SO_APOSTA = {"captada"}

# todo rotulo que abre secao no corpo, para saber onde a anterior termina
ROTULOS_TWO_PAGER = [
    "Problema", "Solução", "Peças", "Fora", "Resultado", "Medida", "Apetite", "Aberto",
    "Produtos documentais", "Sai quando", "Quebra",
    # do esqueleto velho e dos rotulos de fonte: nao sao do molde, mas fecham a secao anterior
    "Continuidade", "Base", "Fontes",
]
ROTULOS_DE_FONTE = ["Base", "Fontes"]

# Retrocompatibilidade de import: quem lia as listas por nivel
CAMPOS_FEATURE = [f"{r}:" for r in ROTULOS_APOSTA + ROTULOS_FORMA]
CAMPOS_EPIC = list(CAMPOS_FEATURE)

# limiares da lista (L1 e L2; palpite que firma com a F1, #3407) e do L3
LIMITE_PARAGRAFO = 400
LIMITE_FRASE = 40
CODIGOS_NO_PARENTESES = 2
TIMEOUT_TAREFAS = 30
RC_INDETERMINAVEL = 5

RE_TIPO = re.compile(r"^(insumo|pergunta|buraco|requisito|decisão|fecho)( \(.+\))?[: ]")
# comentarios de delivery (registro de negocio, conferencia, registro de trabalho) tem os
# tipos da F3 e ficam fora do C1 (contraponto da lista)
PREFIXOS_DELIVERY = ("conferencia", "registro de negocio", "registro de trabalho")
RE_APOSTA = re.compile(r"^decisão \(dono\):\s*apostar", re.IGNORECASE)
RE_FECHO = re.compile(r"^fecho(?: #\d+)?:")
RE_FECHO_PROPRIO = re.compile(r"^fecho #(\d+)")

CADEIRAS = (
    "dono", "gestao estrategica", "ia", "engenharia", "arquiteto", "arquitetura", "seguranca",
    "politicas publicas", "produto", "inteligencia", "direito", "dados", "ti",
)

RE_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
RE_ITEM_NUMERADO = re.compile(r"^\s*\d+\.\s+")
RE_LINK_ALVO = re.compile(r"\]\([^)]*\)")
RE_URL = re.compile(r"https?://\S+")
RE_CODIGO = re.compile(r"#\d+|\b(?:arq|org|ont|dt):\d+")
RE_TEM_LINK = re.compile(r"\]\(|https?://")
RE_NUMERO_CARD = re.compile(r"#\d+")

# bloco que `tarefas ler` acrescenta no fim do corpo, com uma filha por linha (emenda de
# 15/10/2026 à arq:0096: a Quebra sai do molde, e a filha se le daqui, nao do corpo)
RE_FILHAS_CABECALHO = re.compile(r"^\s*filhas\s*(?:\([^)]*\))?\s*:\s*$")

def _tem_filha(texto: str) -> bool:
    """True com ao menos uma filha no bloco que `tarefas ler` acrescenta no fim do corpo."""
    dentro = False
    for linha in texto.splitlines():
        if RE_FILHAS_CABECALHO.match(linha):
            dentro = True
            continue
        if dentro:
            if not linha.strip():
                break
            if RE_NUMERO_CARD.search(linha):
                return True
    return False

_ACENTOS = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeiooouc" "AAAAEEIOOOUC")


def _sem_acento(s: str) -> str:
    return s.translate(_ACENTOS)


def _norm_estado(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").strip().lower()
    s = re.sub(r"\(.*?\)", "", s).strip()
    return _sem_acento(s).replace(" ", "-")


def _visivel(s: str) -> str:
    """O texto como se le: sem alvo de link nem URL solta."""
    return RE_URL.sub("", RE_LINK_ALVO.sub("]", s))


# ------------------------------------------------------------------ cabecalho e nivel

RE_CABECALHO = re.compile(r"^#(\d+)\s+·\s+(\S+)\s+·\s+([^\[·]+)")


def ler_cabecalho(texto: str) -> dict[str, str]:
    """`#N · nivel · estado` da saida de `tarefas ler`; {} quando o texto nao a traz."""
    for linha in texto.splitlines()[:6]:
        m = RE_CABECALHO.match(linha.strip())
        if m:
            return {"numero": m.group(1), "nivel": m.group(2).strip(), "estado": m.group(3).strip()}
    return {}


def _nivel_canonico(bruto: str) -> str | None:
    low = _sem_acento(bruto.lower())
    if low in ("epico", "epic"):
        return "epic"
    if low in ("feature", "story", "task"):
        return low
    return None


def detectar_nivel(texto: str) -> str:
    """story, task, feature ou epic. O cabecalho `#N · nivel ·` decide; sem ele, o palpite
    pelas primeiras linhas (o titulo pode conter a palavra, e por isso vem depois)."""
    cab = ler_cabecalho(texto)
    nivel = _nivel_canonico(cab["nivel"]) if cab else None
    if nivel:
        return nivel
    for linha in texto.splitlines()[:5]:
        low = linha.lower()
        if "task" in low:
            return "task"
        if "feature" in low:
            return "feature"
        if "épico" in low or "epico" in low or "epic" in low:
            return "epic"
        if "story" in low:
            return "story"
    return "story"


# ------------------------------------------------------------------ corpo em secoes

def _re_rotulo(rotulo: str) -> re.Pattern:
    r = re.escape(rotulo)
    return re.compile(rf"^\s*(?:\*\*)?{r}(?:\*\*)?\s*:(?:\*\*)?\s?(.*)$")


_RES_ROTULO = {r: _re_rotulo(r) for r in ROTULOS_TWO_PAGER}


class Secao:
    __slots__ = ("linha", "linhas", "rotulo")

    def __init__(self, rotulo: str, linha: int):
        self.rotulo = rotulo
        self.linha = linha  # numero da linha do rotulo, base 1
        self.linhas: list[tuple[int, str]] = []  # (numero, texto) do conteudo, sem o rotulo

    def texto(self) -> str:
        return "\n".join(t for _, t in self.linhas)

    def nao_vazias(self) -> list[tuple[int, str]]:
        return [(n, t) for n, t in self.linhas if t.strip()]


def _rotulo_da_linha(linha: str) -> tuple[str, str] | None:
    for rotulo, rx in _RES_ROTULO.items():
        m = rx.match(linha)
        if m:
            return rotulo, m.group(1)
    return None


def secoes_do_corpo(texto: str) -> dict[str, Secao]:
    """Rotulo -> Secao. A secao vai da linha do rotulo ate o proximo rotulo, ou ate a lista
    de filhas que `tarefas ler` poe no fim."""
    secoes: dict[str, Secao] = {}
    atual: Secao | None = None
    for n, linha in enumerate(texto.splitlines(), 1):
        if linha.startswith(("filhas (", "filhas:")):
            atual = None
            continue
        achou = _rotulo_da_linha(linha)
        if achou:
            rotulo, resto = achou
            atual = Secao(rotulo, n)
            secoes.setdefault(rotulo, atual)
            if resto.strip():
                atual.linhas.append((n, resto))
        elif atual is not None:
            atual.linhas.append((n, linha))
    return secoes


# ------------------------------------------------------------------ comentarios

RE_COMENTARIO = re.compile(r"^--- #(\d+) · (.+?) · (.+?) ---\s*$")


class Comentario:
    __slots__ = ("autor", "data", "id", "linhas")

    def __init__(self, cid: str, autor: str, data: str):
        self.id = cid
        self.autor = autor
        self.data = data
        self.linhas: list[str] = []

    def nao_vazias(self) -> list[tuple[int, str]]:
        return [(i, t) for i, t in enumerate(self.linhas, 1) if t.strip()]

    def primeira(self) -> str:
        nv = self.nao_vazias()
        return nv[0][1].strip() if nv else ""

    def tipo(self) -> str | None:
        m = RE_TIPO.match(self.primeira())
        return m.group(1) if m else None

    def delivery(self) -> bool:
        return _sem_acento(self.primeira().lower()).startswith(PREFIXOS_DELIVERY)

    def linha_com(self, prefixo: str) -> int | None:
        for i, t in self.nao_vazias():
            if t.strip().startswith(prefixo):
                return i
        return None


def ler_comentarios(texto: str) -> list[Comentario]:
    """A saida de `tarefas comentarios <id>` em Comentario, na ordem."""
    lista: list[Comentario] = []
    atual: Comentario | None = None
    for linha in (texto or "").splitlines():
        m = RE_COMENTARIO.match(linha)
        if m:
            atual = Comentario(m.group(1), m.group(2).strip(), m.group(3).strip())
            lista.append(atual)
        elif atual is not None:
            atual.linhas.append(linha)
    for c in lista:
        while c.linhas and not c.linhas[-1].strip():
            c.linhas.pop()
    return lista


# ------------------------------------------------------------------ contexto dos detectores

class Contexto:
    def __init__(self, alvo: str, texto: str, comentarios: list[Comentario], estado: str,
                 *, fecha_existe: bool):
        self.alvo = alvo
        self.texto = texto
        self.secoes = secoes_do_corpo(texto)
        self.comentarios = comentarios
        self.estado = _norm_estado(estado)
        self.fecha_existe = fecha_existe
        self.aposta = any(RE_APOSTA.match(c.primeira()) for c in comentarios)
        self.tem_story_filha = _tem_filha(texto)

    def discovery(self) -> list[Comentario]:
        return [c for c in self.comentarios if not c.delivery()]

    def arquivo_comentario(self, c: Comentario) -> str:
        return f"{self.alvo} comentário #{c.id}"


Achado = tuple[str, int, str]  # (arquivo, linha, detalhe)
Detector = Callable[[Contexto], list[Achado]]


def _itens(secao: Secao | None) -> list[tuple[int, str]]:
    if not secao:
        return []
    return [(n, t) for n, t in secao.linhas if RE_ITEM.match(t)]


# --- T · two-pager ---------------------------------------------------------

def _t1(ctx: Contexto) -> list[Achado]:
    exigidos = list(ROTULOS_APOSTA)
    if ctx.estado not in ESTADOS_SO_APOSTA:
        exigidos += ROTULOS_FORMA
    achados = [(ctx.alvo, 1, f"rótulo «{r}:» ausente") for r in exigidos if r not in ctx.secoes]
    achados += [(ctx.alvo, ctx.secoes[r].linha, f"rótulo de fontes «{r}:» no corpo")
                for r in ROTULOS_DE_FONTE if r in ctx.secoes]
    return achados


def _t2(ctx: Contexto) -> list[Achado]:
    s = ctx.secoes.get("Medida")
    if s and len(s.nao_vazias()) > 1:
        return [(ctx.alvo, s.linha, f"Medida em {len(s.nao_vazias())} linhas")]
    return []


_T3_FORA = [
    re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),                # data 11/10 ou 11/10/2026
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),                           # data ISO
    RE_NUMERO_CARD,                                                 # numero de card
    re.compile(r"\b(?:arq|org|ont|dt)\s*:\s*\d+", re.IGNORECASE),   # numero de ADR e registro
    re.compile(r"\b(?:ADR|minuta)\s+\d+", re.IGNORECASE),           # «a ADR 0096», «minuta 0046»
    re.compile(r"\b[A-Z]{1,2}\d+\b"),                               # identificador: F3, R1, D2
]


def _t3(ctx: Contexto) -> list[Achado]:
    s = ctx.secoes.get("Problema")
    if not s:
        return []
    achados = []
    for n, t in s.linhas:
        resto = _visivel(t)
        for rx in _T3_FORA:
            resto = rx.sub(" ", resto)
        m = re.search(r"\S*\d\S*", resto)
        if m:
            achados.append((ctx.alvo, n, f"número «{m.group(0)}» no Problema"))
    return achados


_T4_ABERTURAS = {"ao", "aos", "a", "as", "à", "às", "no", "nos", "na", "nas", "quando",
                 "em", "enquanto", "depois", "antes", "durante", "se", "o", "os", "um", "uma"}
_RE_INFINITIVO = re.compile(r"^[a-zà-ú]+(?:ar|er|ir)$")


def _t4(ctx: Contexto) -> list[Achado]:
    achados = []
    for n, t in _itens(ctx.secoes.get("Solução")):
        corpo = RE_ITEM.sub("", t, count=1).lstrip("[*_ ")
        palavra = re.match(r"[\wÀ-ú]+", corpo)
        if not palavra or palavra.group(0).lower() in _T4_ABERTURAS:
            continue
        w = palavra.group(0)
        if w[0].islower() or _RE_INFINITIVO.match(w.lower()):
            achados.append((ctx.alvo, n, f"item abre com «{w}», sem momento nem pessoa"))
    return achados


_T5 = [
    (re.compile(r"\b[\w.-]+@[\w./-]+"), "repo@"),
    (re.compile(r"`[^`]+`"), "identificador entre crases"),
    (re.compile(r"(?<![\w/])(?:[\w.-]+/)+[\w.-]+\.\w{1,5}\b"), "caminho de arquivo"),
]


def _t5(ctx: Contexto) -> list[Achado]:
    achados = []
    for s in ctx.secoes.values():
        for n, t in s.linhas:
            vis = _visivel(t)
            for rx, nome in _T5:
                m = rx.search(vis)
                if m:
                    achados.append((ctx.alvo, n, f"{nome} «{m.group(0)}» em {s.rotulo}"))
                    break
    return achados


def _t6(ctx: Contexto) -> list[Achado]:
    return [(ctx.alvo, n, "item de Peças sem «N.»")
            for n, t in _itens(ctx.secoes.get("Peças")) if not RE_ITEM_NUMERADO.match(t)]


_RE_T8 = re.compile(r"\b(proibid[oa]s?|nunca|não se pode)\b", re.IGNORECASE)


def _t8(ctx: Contexto) -> list[Achado]:
    s = ctx.secoes.get("Fora")
    if not s:
        return []
    return [(ctx.alvo, n, f"«{m.group(1)}» no Fora") for n, t in s.linhas if (m := _RE_T8.search(t))]


_RE_CADEIRA = re.compile(r"\b(" + "|".join(re.escape(c) for c in CADEIRAS) + r")\b")


def _t9(ctx: Contexto) -> list[Achado]:
    s = ctx.secoes.get("Aberto")
    if not ctx.aposta or not s:
        return []
    achados = []
    for n, t in s.nao_vazias():
        low = _sem_acento(t.lower())
        if "fica aberto de proposito" not in low and not _RE_CADEIRA.search(low):
            achados.append((ctx.alvo, n, "linha do Aberto sem cadeira nem «fica aberto de propósito»"))
    return achados


def _t10(ctx: Contexto) -> list[Achado]:
    achados = []
    prod, sol = ctx.secoes.get("Produtos documentais"), ctx.secoes.get("Solução")
    spec_servida = prod and re.search(r"\bspec\b", prod.texto(), re.IGNORECASE) and RE_TEM_LINK.search(prod.texto())
    if spec_servida and sol and not RE_TEM_LINK.search(sol.texto()):
        achados.append((ctx.alvo, sol.linha, "spec servida em Produtos documentais e Solução sem link"))
    pecas = ctx.secoes.get("Peças")
    # filha de story (emenda de 15/10/2026: a Quebra sai do molde, a filha se le do que
    # `tarefas ler` acrescenta no fim do corpo); #N conta como link: o rastreador liga o
    # numero ao card da story
    if ctx.tem_story_filha and pecas and not (RE_TEM_LINK.search(pecas.texto()) or RE_NUMERO_CARD.search(pecas.texto())):
        achados.append((ctx.alvo, pecas.linha, "feature com story filha e Peças ainda em texto, sem link nem número"))
    return achados


# --- C · comentario tipado ------------------------------------------------

def _c1(ctx: Contexto) -> list[Achado]:
    return [(ctx.arquivo_comentario(c), 1, f"primeira linha sem tipo: «{c.primeira()[:60]}»")
            for c in ctx.discovery() if not c.tipo()]


def _c2(ctx: Contexto) -> list[Achado]:
    return [(ctx.arquivo_comentario(c), 1, "buraco sem linha «Remendo:»")
            for c in ctx.discovery() if c.tipo() == "buraco" and c.linha_com("Remendo:") is None]


def _c3(ctx: Contexto) -> list[Achado]:
    return [(ctx.arquivo_comentario(c), 1, "requisito sem linha «Confere:»")
            for c in ctx.discovery() if c.tipo() == "requisito" and c.linha_com("Confere:") is None]


def _c4(ctx: Contexto) -> list[Achado]:
    return [(ctx.arquivo_comentario(c), 1, "decisão sem quem decidiu entre parênteses")
            for c in ctx.discovery()
            if c.primeira().startswith("decisão") and not re.match(r"^decisão \(.+\)", c.primeira())]


def _c5(ctx: Contexto) -> list[Achado]:
    achados = []
    for c in ctx.discovery():
        arq = ctx.arquivo_comentario(c)
        if ctx.fecha_existe and RE_FECHO_PROPRIO.match(c.primeira()):
            achados.append((arq, 1, "fecho em comentário próprio, com `tarefas comentar --fecha` no ar"))
            continue
        nv = c.nao_vazias()
        ultima = nv[-1][0] if nv else 0
        for i, t in nv:
            if not t.strip().startswith("fecho:"):
                continue
            if c.tipo() == "insumo":
                achados.append((arq, i, "linha «fecho:» em comentário insumo"))
            elif i != ultima:
                achados.append((arq, i, "linha «fecho:» que não é a última do comentário"))
    return achados


_RE_MEDIDA_CASO = re.compile(r"[\w.-]+@|\bspec\b", re.IGNORECASE)


def _c7(ctx: Contexto) -> list[Achado]:
    achados = []
    for c in ctx.discovery():
        if c.tipo() != "buraco":
            continue
        i = c.linha_com("Caso:")
        if i is None:
            achados.append((ctx.arquivo_comentario(c), 1, "buraco sem linha «Caso:»"))
        elif not _RE_MEDIDA_CASO.search(c.linhas[i - 1]):
            achados.append((ctx.arquivo_comentario(c), i, "«Caso:» sem repo@ nem nome de spec"))
    return achados


# --- F · formalizacao (o que se le no card) -------------------------------

_RE_DESTINO = re.compile(
    r"\b[DR]\d+\b|\b(?:spec|adr|guia|padr[aã]o|levantamento|lista|styleguide|anexo|skill|runbook"
    r"|benchmark|parecer)\b|\b(?:arq|org|ont):\d+", re.IGNORECASE)


def _f2(ctx: Contexto) -> list[Achado]:
    achados = []
    for c in ctx.discovery():
        for i, t in c.nao_vazias():
            s = t.strip()
            if RE_FECHO.match(s) and re.search(r"\b(formalizada|aceito)\b", s) \
                    and not _RE_DESTINO.search(s.split(":", 1)[1]):
                achados.append((ctx.arquivo_comentario(c), i, "fecho de formalização sem destino"))
    return achados


def _f4(ctx: Contexto) -> list[Achado]:
    if not ctx.aposta:
        return []
    fechados_fora = {m.group(1) for c in ctx.comentarios if (m := RE_FECHO_PROPRIO.match(c.primeira()))}
    return [(ctx.arquivo_comentario(c), 1, f"{c.tipo()} aberto em card com «decisão (dono): apostar e formalizar»")
            for c in ctx.discovery()
            if c.tipo() in ("pergunta", "buraco", "requisito")
            and c.linha_com("fecho:") is None and c.id not in fechados_fora]


# --- L · legibilidade -------------------------------------------------------

_L_LINHAS_FIXAS = ("Caso:", "Confere:")


def _linhas_de_prosa(arquivo: str, linhas: list[tuple[int, str]], *, comentario: bool) -> list[Achado]:
    saida: list[Achado] = []
    cerca = False
    for n, t in linhas:
        st = t.strip()
        if st.startswith("```"):
            cerca = not cerca
            continue
        fixa = comentario and (st.startswith(_L_LINHAS_FIXAS) or RE_FECHO.match(st))
        if not (cerca or st.startswith("|") or fixa):
            saida.append((arquivo, n, _visivel(t)))
    return saida


def _prosa(ctx: Contexto) -> list[Achado]:
    """(arquivo, linha, texto visivel) de toda linha de prosa: o corpo do two-pager e o
    argumento dos comentarios de discovery. Fora: bloco de codigo, tabela, linha fixa,
    a primeira linha do comentario e o fecho."""
    saida: list[Achado] = []
    for s in ctx.secoes.values():
        saida += _linhas_de_prosa(ctx.alvo, s.linhas, comentario=False)
    for c in ctx.discovery():
        saida += _linhas_de_prosa(ctx.arquivo_comentario(c), c.nao_vazias()[1:], comentario=True)
    return saida


def _l1(ctx: Contexto) -> list[Achado]:
    return [(arq, n, f"parágrafo de {len(t.strip())} caracteres sem quebra")
            for arq, n, t in _prosa(ctx) if len(t.strip()) > LIMITE_PARAGRAFO]


def _l2(ctx: Contexto) -> list[Achado]:
    achados = []
    for arq, n, t in _prosa(ctx):
        maior = max((len(f.split()) for f in re.split(r"(?<=[.!?])\s+", t.strip())), default=0)
        if maior > LIMITE_FRASE:
            achados.append((arq, n, f"frase de {maior} palavras"))
    return achados


def _l3(ctx: Contexto) -> list[Achado]:
    achados = []
    for arq, n, t in _prosa(ctx):
        grupos = [g for g in re.findall(r"\(([^()]*)\)", t) if len(RE_CODIGO.findall(g)) >= CODIGOS_NO_PARENTESES]
        corpo = RE_ITEM.sub("", t, count=1)
        if grupos:
            achados.append((arq, n, f"dois ou mais códigos no mesmo parênteses: «({grupos[0][:60]})»"))
        elif RE_CODIGO.search(corpo) and not re.search(r"[A-Za-zÀ-ú]{3,}", RE_CODIGO.sub("", corpo)):
            achados.append((arq, n, "linha só com código, sem o nome do que aponta"))
    return achados


DETECTORES: dict[str, Detector] = {
    "T1": _t1, "T2": _t2, "T3": _t3, "T4": _t4, "T5": _t5, "T6": _t6, "T8": _t8, "T9": _t9,
    "T10": _t10,
    "C1": _c1, "C2": _c2, "C3": _c3, "C4": _c4, "C5": _c5, "C7": _c7,
    "F2": _f2, "F4": _f4,
    "L1": _l1, "L2": _l2, "L3": _l3,
}
# criterios com detector na lista que nao se leem no card: F1, F5 e F6 sao do documento
# derivado (ADR e spec), F3 e da story derivada, que segue a arq:0096 inteira
FORA_DO_CARD = {"F1", "F3", "F5", "F6"}


# ------------------------------------------------------------------ fontes externas

def _tarefas_bin() -> str:
    sob = os.environ.get("PF_LINT_TAREFAS")
    if sob:
        return sob
    local = Path(__file__).resolve().parent.parent / "tarefas"
    return str(local) if local.exists() else "tarefas"


def fecha_no_ar() -> bool:
    """`tarefas comentar --fecha` existe? Decide a terceira perna do C5 (spec comentario-tipado R11).

    Verbo ilegivel conta como «nao existe»: a perna fica sem apontar, que e o lado do aviso
    que nao acusa o que pode estar certo."""
    sob = os.environ.get("PF_LINT_FECHA")
    if sob in ("0", "1"):
        return sob == "1"
    caminho = Path(_tarefas_bin())
    if not caminho.is_file():
        return False
    return "--fecha" in caminho.read_text(encoding="utf-8", errors="replace")


def _tarefas(*args: str) -> str:
    chamada = f"tarefas {' '.join(args)}"
    try:
        proc = subprocess.run([_tarefas_bin(), *args], capture_output=True, text=True,
                              timeout=TIMEOUT_TAREFAS, check=False)
    except (subprocess.SubprocessError, OSError) as e:
        raise ValueError(RC_INDETERMINAVEL, f"{chamada} nao respondeu ({type(e).__name__})") from None
    if proc.returncode != 0:
        primeira = (proc.stderr or proc.stdout).strip().splitlines()[:1]
        raise ValueError(RC_INDETERMINAVEL,
                         f"{chamada} saiu {proc.returncode}: {primeira[0] if primeira else ''}")
    return proc.stdout


# ------------------------------------------------------------------ verificacao

# arq:0096, emenda de 15/10/2026: o titulo e o rotulo onde se clica, ate 60 caracteres, em todo
# nivel. Aviso, nunca bloqueante (#3887).
LIMITE_TITULO = 60
CURA_TITULO = "o título é o rótulo onde se clica; a lista do que entra vai ao corpo"

def ler_titulo(texto: str) -> str | None:
    """O titulo da saida de `tarefas ler`: a linha `# <titulo>` no topo. None sem ela: o lint
    nao adivinha titulo de arquivo ou stdin que nao a traz."""
    for linha in texto.splitlines()[:3]:
        if linha.startswith("# "):
            return linha[2:].strip() or None
    return None

def _conferir_titulo(nome_alvo: str, conteudo: str) -> list[Apontamento]:
    titulo = ler_titulo(conteudo)
    if titulo is None or len(titulo) <= LIMITE_TITULO:
        return []
    return [Apontamento(
        nome_alvo, 1,
        f"título com {len(titulo)} caracteres, acima do teto de {LIMITE_TITULO} (arq:0096)",
        CURA_TITULO,
        severidade="aviso",
        id="CARD_TITULO",
    )]

def _conferir_adr(nome_alvo: str, conteudo: str, nivel: str) -> list[Apontamento]:
    campos_esperados = CAMPOS_TASK if nivel == "task" else CAMPOS_STORY
    apontamentos: list[Apontamento] = []
    linhas = [linha.strip() for linha in conteudo.splitlines()]
    for rotulo in campos_esperados:
        rotulo_sem = rotulo.rstrip(":")
        formas = (rotulo, f"**{rotulo}**", f"**{rotulo_sem}**:", f"{rotulo_sem}:")
        if not any(s.startswith(formas) for s in linhas):
            apontamentos.append(Apontamento(
                nome_alvo, 1,
                f"secao obrigatoria '{rotulo_sem}' ausente no corpo de {nivel}",
                f"acrescentar a secao '{rotulo}' conforme arq:0096",
                severidade="aviso",
                id=f"CARD_{rotulo_sem.upper()}",
            ))
    return apontamentos


def conferir_discovery(nome_alvo: str, conteudo: str, comentarios: list[Comentario], lista: dict,
                       estado: str = "", *, fecha_existe: bool = False) -> tuple[list[Apontamento], list[str]]:
    """Roda os detectores literais da lista sobre o two-pager e os comentarios.
    Devolve (apontamentos, avisos); avisos e o que a lista pede e o lint nao mede."""
    ctx = Contexto(nome_alvo, conteudo, comentarios, estado, fecha_existe=fecha_existe)
    apontamentos: list[Apontamento] = []
    avisos: list[str] = []
    for item in lista.get("itens", []):
        cid = (item.get("id") or "").strip()
        detector_lista = _sem_acento((item.get("detector") or "").strip().lower())
        if not cid or detector_lista == "leitura" or cid in FORA_DO_CARD:
            continue
        detector = DETECTORES.get(cid)
        if detector is None:
            avisos.append(f"{cid} tem detector na lista e nao tem no lint card: nao medido")
            continue
        o_que = (item.get("o_que_fere") or cid).strip()
        cura = (item.get("cura") or "ver a lista antipadroes-de-discovery").strip()
        apontamentos += [Apontamento(arquivo, linha, f"{cid} {o_que} [{detalhe}]", cura,
                                     severidade="aviso", id=cid)
                         for arquivo, linha, detalhe in detector(ctx)]
    return apontamentos, avisos


def _carregar(alvo: str, raiz: Path | str | None) -> tuple[str, str] | Apontamento:
    """(conteudo, nome do alvo) de arquivo, stdin ou numero de card; Apontamento se o arquivo
    nao se le."""
    numero = re.fullmatch(r"#?(\d+)", alvo.strip())
    if numero:
        return _tarefas("ler", numero.group(1)), f"#{numero.group(1)}"
    if alvo == "-":
        return sys.stdin.read(), "-"
    caminho = Path(alvo)
    if not caminho.is_absolute() and raiz:
        caminho = Path(raiz) / alvo
    try:
        return caminho.read_text(encoding="utf-8", errors="replace"), alvo
    except OSError as e:
        return Apontamento(alvo, 1, f"nao consegui ler arquivo do card: {e}",
                           "fornecer arquivo legivel, '-' para stdin ou o numero do card",
                           severidade="bloqueante")


def verificar_card_regua(
    alvo: str = "-",
    texto: str | None = None,
    raiz: Path | str | None = None,
    *,
    comentarios: str | None = None,
    lista: dict | None = None,
    fecha_existe: bool | None = None,
) -> tuple[list[Apontamento], str, int | None, list[str]]:
    """(apontamentos, chave da regua, rev, avisos).

    `alvo` e arquivo, '-' (stdin) ou numero de card (`3408` ou `#3408`): com numero, o corpo
    vem de `tarefas ler` e os comentarios de `tarefas comentarios`. Erro de fonte levanta
    ValueError(rc, msg), com rc 5 (indeterminavel), como as outras classes."""
    alvo = alvo or "-"
    if texto is not None:
        conteudo, nome_alvo = texto, alvo
    else:
        carregado = _carregar(alvo, raiz)
        if isinstance(carregado, Apontamento):
            return [carregado], CHAVE_ADR, REV_ADR, []
        conteudo, nome_alvo = carregado

    nivel = detectar_nivel(conteudo)
    titulo = _conferir_titulo(nome_alvo, conteudo)
    if nivel in ("story", "task"):
        return titulo + _conferir_adr(nome_alvo, conteudo, nivel), CHAVE_ADR, REV_ADR, []

    if lista is None:
        from .lista import resolver_lista
        lista = resolver_lista(CHAVE_DISCOVERY)
        if not lista:
            raise ValueError(RC_INDETERMINAVEL, f"lista de verificacao '{CHAVE_DISCOVERY}' nao servida pelo acervo")
    if comentarios is None and texto is None and nome_alvo.startswith("#"):
        comentarios = _tarefas("comentarios", nome_alvo[1:])
    if fecha_existe is None:
        fecha_existe = fecha_no_ar()
    estado = ler_cabecalho(conteudo).get("estado", "")
    apontamentos, avisos = conferir_discovery(
        nome_alvo, conteudo, ler_comentarios(comentarios or ""), lista, estado, fecha_existe=fecha_existe)
    return titulo + apontamentos, CHAVE_DISCOVERY, lista.get("rev"), avisos


def verificar_card(
    alvo: str = "-",
    texto: str | None = None,
    raiz: Path | str | None = None,
) -> list[Apontamento]:
    """Compatibilidade: so os apontamentos de verificar_card_regua."""
    return verificar_card_regua(alvo=alvo, texto=texto, raiz=raiz)[0]
