"""Os documentos de comportamento, lidos da árvore da casa nova, com a forma cobrada.

O que fica em vigor numa sessão é ponteiro: o nome e o sha do documento. O texto se lê daqui a cada chamada, e por isso mudar
o documento muda a linha servida sem mexer na memória de trabalho.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

EIXOS = "ontologia/eixos-de-postura.yaml"


def caminho_eixos(base: Path) -> Path:
    """Resolve ontologia/eixos-de-postura.yaml na árvore dada, no conhecimento irmão ou na release no ar (#4402)."""
    for cand in (
        base / EIXOS,
        base.parent / "conhecimento" / EIXOS,
        Path("/opt/platafirma/current/conhecimento") / EIXOS,
    ):
        if cand.is_file():
            return cand
    return base / EIXOS
PASTA = "instancias"
RESERVA = "postura"                      # a postura da casa: a reserva, que não marca eixo
SECAO_DA_POSTURA = "Para que lado puxa"
SECAO_DO_RAMO = "Postura do ramo"
SECOES_DO_CENARIO = ("Condição", "Sinais", "Fim")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ENTIDADE = re.compile(r"^Entidade:\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", re.M)
_TITULO = re.compile(r"^#\s+(.+?)\s*$", re.M)
_TITULO_DE_SECAO = re.compile(r"^##\s+(.+?)\s*$", re.M)
_ITEM = re.compile(r"^-\s+(.*)$", re.M)
_MARCA = re.compile(r"^\[([^\]:]+):\s*([^\]]+)\]\s+(\S.*)$")
_SUPRIME = re.compile(r"^Suprime postura:\s*sim\s*$", re.M | re.I)


class Inexistente(Exception):
    """O documento pedido não está na árvore."""


class Malformado(Exception):
    """O documento está na árvore e não cumpre a forma da entidade."""

    def __init__(self, entidade: str, slug: str, defeitos: list[str]):
        super().__init__(f"{entidade} {slug}: " + "; ".join(defeitos))
        self.entidade, self.slug, self.defeitos = entidade, slug, defeitos


@dataclass(frozen=True)
class Eixo:
    slug: str
    rotulo: str
    ordem: int
    polos: dict          # rótulo em caixa dobrada -> (slug, rótulo)


@dataclass(frozen=True)
class Linha:
    eixo: str            # slug do eixo
    eixo_rotulo: str
    polo: str            # slug do polo
    polo_rotulo: str
    texto: str           # o item, sem a marca
    peca: str            # slug do documento de onde a linha saiu
    sha: str             # sha do blob do documento

    def marcada(self) -> str:
        return f"- [{self.eixo_rotulo}: {self.polo_rotulo}] {self.texto}"

    def rotulo(self) -> str:
        return f"{self.eixo_rotulo}: {self.polo_rotulo}"


def raiz() -> Path:
    """A raiz da árvore da casa nova: PF_CASA_RAIZ, ou PLATAFIRMA_RELEASE/casa."""
    dada = (os.environ.get("PF_CASA_RAIZ") or "").strip()
    if dada:
        return Path(dada)
    release = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    return release / "casa"


def caminho_eixos(base: Path) -> Path:
    """Localiza eixos-de-postura.yaml em PF_EIXOS_POSTURA, na base ou na release do conhecimento."""
    dada = (os.environ.get("PF_EIXOS_POSTURA") or "").strip()
    if dada:
        return Path(dada)
    local = base / EIXOS
    if local.is_file():
        return local
    release = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    return release / "conhecimento" / EIXOS


def slug_de(nome: str) -> str:
    """O nome que o dono escreve vira slug: sem acento, em minúsculas, com hífen no lugar do espaço."""
    sem = "".join(c for c in unicodedata.normalize("NFD", nome) if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s_]+", "-", sem.strip().lower())


def slug_valido(slug: str) -> bool:
    return bool(_SLUG.match(slug or ""))


def sha_do_blob(conteudo: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(conteudo) + conteudo).hexdigest()


def ler_eixos(base: Path) -> dict[str, Eixo]:
    """Os eixos vigentes, por slug. A marca do documento casa com o rótulo, que leva acento."""
    import yaml
    dado = yaml.safe_load(caminho_eixos(base).read_text(encoding="utf-8")) or {}
    eixos = {}
    for e in dado.get("eixos") or ():
        if e.get("estado", "vigente") != "vigente":
            continue
        polos = {p["rotulo"].strip().casefold(): (p["slug"], p["rotulo"].strip()) for p in e.get("polos") or ()}
        eixos[e["slug"]] = Eixo(e["slug"], e["rotulo"].strip(), int(e.get("ordem") or 0), polos)
    return eixos


def ler_documento(base: Path, entidade: str, slug: str) -> tuple[str, str]:
    """(texto, sha do blob) de instancias/<entidade>/<slug>.md. Slug fora da forma e arquivo ausente são inexistentes."""
    if not slug_valido(slug):
        raise Inexistente(f"{entidade} {slug!r}")
    caminho = base / PASTA / entidade / f"{slug}.md"
    try:
        conteudo = caminho.read_bytes()
    except OSError:
        raise Inexistente(f"{entidade} {slug}") from None
    return conteudo.decode("utf-8", errors="replace"), sha_do_blob(conteudo)


def titulo(texto: str) -> str:
    achado = _TITULO.search(texto[:2000])
    return achado.group(1) if achado else ""


def corpo_da_secao(texto: str, rotulo: str) -> str | None:
    for achado in _TITULO_DE_SECAO.finditer(texto):
        if achado.group(1).strip().casefold() == rotulo.casefold():
            seguinte = _TITULO_DE_SECAO.search(texto, achado.end())
            return texto[achado.end():seguinte.start() if seguinte else len(texto)]
    return None


def _confere_entidade(texto: str, entidade: str, slug: str) -> None:
    declarada = _ENTIDADE.search(texto[:2000])
    if declarada is None or declarada.group(1) != entidade:
        raise Malformado(entidade, slug, [f"falta a linha «Entidade: {entidade}» logo abaixo do título"])


def _linhas_marcadas(corpo: str, eixos: dict[str, Eixo], entidade: str, slug: str, sha: str) -> list[Linha]:
    por_rotulo = {e.rotulo.casefold(): e for e in eixos.values()}
    linhas, defeitos, vistos = [], [], set()
    for numero, item in enumerate(_ITEM.findall(corpo), 1):
        marca = _MARCA.match(item)
        if marca is None:
            defeitos.append(f"o item {numero} não abre com a marca «[eixo: polo]»")
            continue
        eixo = por_rotulo.get(marca.group(1).strip().casefold())
        if eixo is None:
            defeitos.append(f"o item {numero} marca o eixo «{marca.group(1).strip()}», que não está na lista dos eixos")
            continue
        polo = eixo.polos.get(marca.group(2).strip().casefold())
        if polo is None:
            defeitos.append(f"o item {numero} marca o polo «{marca.group(2).strip()}», que não é polo do eixo «{eixo.rotulo}»")
            continue
        if eixo.slug in vistos:
            defeitos.append(f"o item {numero} repete o eixo «{eixo.rotulo}»")
            continue
        vistos.add(eixo.slug)
        linhas.append(Linha(eixo.slug, eixo.rotulo, polo[0], polo[1], marca.group(3).strip(), slug, sha))
    if defeitos:
        raise Malformado(entidade, slug, defeitos)
    return linhas


def postura(base: Path, slug: str, eixos: dict[str, Eixo]) -> list[Linha]:
    """As linhas de uma postura, uma por eixo. Levanta Inexistente ou Malformado; a reserva não tem linha de eixo."""
    texto, sha = ler_documento(base, "postura", slug)
    _confere_entidade(texto, "postura", slug)
    corpo = corpo_da_secao(texto, SECAO_DA_POSTURA)
    if corpo is None:
        raise Malformado("postura", slug, [f"falta a seção «{SECAO_DA_POSTURA}»"])
    linhas = _linhas_marcadas(corpo, eixos, "postura", slug, sha)
    if not linhas:
        raise Malformado("postura", slug, [f"a seção «{SECAO_DA_POSTURA}» não tem item"])
    return linhas


def itens_sem_marca(base: Path, entidade: str, slug: str) -> tuple[str, list[str], str]:
    """(título, itens, sha) da seção «Para que lado puxa» de uma inclinação que não marca eixo: a reserva, a circunstância
    e o ritual."""
    texto, sha = ler_documento(base, entidade, slug)
    _confere_entidade(texto, entidade, slug)
    corpo = corpo_da_secao(texto, SECAO_DA_POSTURA)
    itens = [i.strip() for i in _ITEM.findall(corpo or "")]
    if not itens:
        raise Malformado(entidade, slug, [f"falta a seção «{SECAO_DA_POSTURA}», ou ela não tem item"])
    return titulo(texto), itens, sha


def ramo(base: Path, chapeu: str, eixos: dict[str, Eixo]) -> list[Linha]:
    """As linhas da seção Postura do ramo do chapéu. Chapéu sem a seção não traz linha, e isso não é defeito."""
    texto, sha = ler_documento(base, "chapeu", chapeu)
    _confere_entidade(texto, "chapeu", chapeu)
    corpo = corpo_da_secao(texto, SECAO_DO_RAMO)
    return [] if corpo is None else _linhas_marcadas(corpo, eixos, "chapeu", chapeu, sha)


def cenario(base: Path, slug: str) -> tuple[str, str, str]:
    """(título, condição, sha) do cenário, com as três seções cobradas."""
    texto, sha = ler_documento(base, "cenario", slug)
    _confere_entidade(texto, "cenario", slug)
    faltam = [r for r in SECOES_DO_CENARIO if not (corpo_da_secao(texto, r) or "").strip()]
    if faltam:
        raise Malformado("cenario", slug, ["falta a seção " + ", ".join(f"«{r}»" for r in faltam)])
    return titulo(texto), " ".join((corpo_da_secao(texto, "Condição") or "").split()), sha


def ritual_suprime_postura(base: Path, slug: str) -> bool:
    """O ritual declara a supressão com a linha «Suprime postura: sim» no cabeçalho. Ritual que não está na árvore, ou que
    não cumpre a forma, não suprime nada."""
    try:
        texto, _ = ler_documento(base, "ritual", slug)
    except Inexistente:
        return False
    return bool(_SUPRIME.search(texto[:2000]))


def cultura(base: Path, slug: str = "da-casa") -> tuple[str, str]:
    """(texto sem título e sem Entidade, sha) de instancias/cultura/<slug>.md.

    Cobra a linha «Entidade: cultura» e pelo menos uma seção com texto.
    """
    texto, sha = ler_documento(base, "cultura", slug)
    _confere_entidade(texto, "cultura", slug)
    achado = _TITULO_DE_SECAO.search(texto)
    if not achado:
        raise Malformado("cultura", slug, ["falta pelo menos uma seção com texto"])
    corpo = texto[achado.start():].strip()
    if not corpo:
        raise Malformado("cultura", slug, ["falta pelo menos uma seção com texto"])
    return corpo, sha


def apelidos(base: Path) -> list[tuple[str, str]]:
    """Os apelidos das personas da casa nova: lista de (apelido, slug), em ordem de apelido."""
    pasta = base / PASTA / "persona"
    if not pasta.is_dir():
        raise Inexistente("persona")
    resultado = []
    for p in sorted(pasta.glob("*.md")):
        slug = p.stem
        if not slug_valido(slug):
            continue
        conteudo = p.read_bytes()
        texto = conteudo.decode("utf-8", errors="replace")
        _confere_entidade(texto, "persona", slug)
        tit = titulo(texto)
        if not tit:
            raise Malformado("persona", slug, ["falta o título do documento"])
        resultado.append((tit, slug))
    return sorted(resultado, key=lambda par: par[0])
