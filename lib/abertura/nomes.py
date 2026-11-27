"""Resolução do nome da cadeira e do chapéu pela seção Nomes da persona (regra 36 da F4269, t3 da S4334).

A abertura aceita o slug ou qualquer nome alternativo declarado na seção `## Nomes` da persona para a cadeira e para cada
chapéu, comparando sem acento e sem caixa. Preserva também a resolução do chapéu por apelido do título de `chapeu.md` e por
pedaço único. Quando o nome não casa com nenhuma cadeira ou chapéu, devolve a recusa com a lista das cadeiras e dos chapéus,
cada um com os nomes alternativos.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

_RE_GERENCIA = re.compile(r"^-\s+\*\*([a-z0-9]+(?:-[a-z0-9]+)*)\*\*\s+[—\-–]")
_RE_NOME_CADEIRA = re.compile(
    r"^-\s+cadeira\s+\*\*([a-z0-9]+(?:-[a-z0-9]+)*)\*\*\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
_RE_NOME_CHAPEU = re.compile(
    r"^-\s+chap[eé]u\s+\*\*([a-z0-9]+(?:-[a-z0-9]+)*)\*\*\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def _sem_acento_espaco(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    limpo = "".join(c for c in nfd if unicodedata.category(c) != "Mn").casefold().strip()
    return re.sub(r"\s+", " ", limpo)


def _chave_slug(texto: str) -> str:
    return re.sub(r"[\s_]+", "-", _sem_acento_espaco(texto))


def _extrair_nomes(bruto: str) -> tuple[str, ...]:
    itens: list[str] = []
    for pedaco in (bruto or "").split(","):
        nome = pedaco.strip()
        if not nome or _sem_acento_espaco(nome) == "nenhum":
            continue
        itens.append(nome)
    return tuple(itens)


@dataclass(frozen=True)
class CadeiraDeclarada:
    slug: str
    nomes: tuple[str, ...] = ()
    chapeus: dict[str, tuple[str, ...]] = field(default_factory=dict)
    apelidos_chapeu: dict[str, str] = field(default_factory=dict)

    def formatar_linha(self) -> str:
        nomes_cad = f" ({', '.join(self.nomes)})" if self.nomes else ""
        partes_ch: list[str] = []
        for ch_slug, ch_nomes in self.chapeus.items():
            if ch_nomes:
                partes_ch.append(f"{ch_slug} ({', '.join(ch_nomes)})")
            else:
                partes_ch.append(ch_slug)
        sufixo_ch = f": {', '.join(partes_ch)}" if partes_ch else ""
        return f"- {self.slug}{nomes_cad}{sufixo_ch}"

    def como_dict(self) -> dict:
        return {
            "cadeira": self.slug,
            "nomes": list(self.nomes),
            "chapeus": [
                {"chapeu": ch_slug, "nomes": list(ch_nomes)}
                for ch_slug, ch_nomes in self.chapeus.items()
            ],
        }


def _parsear_bloco_persona(bloco: str) -> tuple[dict[str, tuple[str, ...]], dict[str, dict[str, tuple[str, ...]]]]:
    gerencias_bloco: list[str] = []
    cadeira_atual: str | None = None
    nomes_por_cad: dict[str, tuple[str, ...]] = {}
    chapeus_por_cad: dict[str, dict[str, tuple[str, ...]]] = {}

    for linha in bloco.splitlines():
        s = linha.strip()
        if not s:
            continue
        m_ger = _RE_GERENCIA.match(s)
        if m_ger:
            ch_slug = m_ger.group(1)
            if cadeira_atual:
                chapeus_por_cad.setdefault(cadeira_atual, {}).setdefault(ch_slug, ())
            else:
                gerencias_bloco.append(ch_slug)
            continue
        m_cad = _RE_NOME_CADEIRA.match(s)
        if m_cad:
            cadeira_atual = m_cad.group(1)
            nomes_por_cad[cadeira_atual] = _extrair_nomes(m_cad.group(2))
            mapa_ch = chapeus_por_cad.setdefault(cadeira_atual, {})
            for g in gerencias_bloco:
                mapa_ch.setdefault(g, ())
            gerencias_bloco = []
            continue
        m_ch = _RE_NOME_CHAPEU.match(s)
        if m_ch and cadeira_atual:
            ch_slug = m_ch.group(1)
            chapeus_por_cad.setdefault(cadeira_atual, {})[ch_slug] = _extrair_nomes(m_ch.group(2))
    return nomes_por_cad, chapeus_por_cad


@dataclass(frozen=True)
class SecaoDasCadeiras:
    cadeiras: dict[str, CadeiraDeclarada] = field(default_factory=dict)

    def formatar_lista(self) -> str:
        return "\n".join(c.formatar_linha() for _, c in sorted(self.cadeiras.items()))

    def como_lista(self) -> list[dict]:
        return [c.como_dict() for _, c in sorted(self.cadeiras.items())]

    @classmethod
    def de_texto(cls, texto: str) -> SecaoDasCadeiras:
        """Constrói `SecaoDasCadeiras` a partir do texto gravado de uma ou mais personas (ou fixture de Nomes/Gerências)."""
        blocos = re.split(r"(?m)(?=^#\s+\S)", texto or "") or [texto or ""]
        cadeiras: dict[str, CadeiraDeclarada] = {}
        for bloco in blocos:
            nomes_por_cad, chapeus_por_cad = _parsear_bloco_persona(bloco)
            for cad_slug, nomes in nomes_por_cad.items():
                anterior = cadeiras.get(cad_slug)
                ch_merged = dict(anterior.chapeus) if anterior else {}
                for ch_s, ch_n in chapeus_por_cad.get(cad_slug, {}).items():
                    ch_merged[ch_s] = ch_n or ch_merged.get(ch_s, ())
                cadeiras[cad_slug] = CadeiraDeclarada(
                    slug=cad_slug,
                    nomes=nomes or (anterior.nomes if anterior else ()),
                    chapeus=ch_merged,
                    apelidos_chapeu=dict(anterior.apelidos_chapeu) if anterior else {},
                )
        return cls(cadeiras=cadeiras)

    @classmethod
    def de_pasta(cls, base: Path, abertura_dir: Path | None = None) -> SecaoDasCadeiras:
        pasta_personas = base / "instancias" / "persona"
        textos = [arq.read_text(encoding="utf-8") for arq in sorted(pasta_personas.glob("*.md"))]
        secao = cls.de_texto("\n\n".join(textos))
        if abertura_dir:
            secao = secao.com_abertura_dir(abertura_dir)
        return secao

    def com_abertura_dir(self, abertura_dir: Path) -> SecaoDasCadeiras:
        """Enriquece os chapéus e apelidos de título a partir de `abertura/<cadeira>/<chapeu>/chapeu.md`, se presente."""
        raiz_ab = abertura_dir / "current" / "abertura"
        if not raiz_ab.is_dir():
            raiz_ab = abertura_dir / "abertura"
        if not raiz_ab.is_dir():
            return self

        novas = dict(self.cadeiras)
        for cad_dir in sorted(p for p in raiz_ab.iterdir() if p.is_dir()):
            cad_slug = cad_dir.name
            atual = novas.get(cad_slug, CadeiraDeclarada(slug=cad_slug))
            chapeus = dict(atual.chapeus)
            apelidos = dict(atual.apelidos_chapeu)
            for ch_arq in sorted(cad_dir.glob("*/chapeu.md")):
                ch_slug = ch_arq.parent.name
                chapeus.setdefault(ch_slug, ())
                linhas = ch_arq.read_text(encoding="utf-8").splitlines()
                primeira = linhas[0].strip() if linhas else ""
                m = re.search(r"\(([^()]+)\)\s*$", primeira)
                if m:
                    for ap in m.group(1).split(","):
                        chave = _chave_slug(ap)
                        if chave:
                            apelidos.setdefault(chave, ch_slug)
            novas[cad_slug] = CadeiraDeclarada(
                slug=cad_slug,
                nomes=atual.nomes,
                chapeus=chapeus,
                apelidos_chapeu=apelidos,
            )
        return SecaoDasCadeiras(cadeiras=novas)


@dataclass(frozen=True)
class RecusaDeNome:
    codigo: str
    mensagem: str
    cadeiras: list[dict] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "erro": self.mensagem,
            "codigo": self.codigo,
            "cadeiras": self.cadeiras,
        }


@dataclass(frozen=True)
class Resolucao:
    cadeira: str | None
    chapeu: str | None
    avisos: list[str] = field(default_factory=list)
    recusa: RecusaDeNome | None = None

    @property
    def ok(self) -> bool:
        return self.recusa is None and bool(self.cadeira)

    @property
    def erro(self) -> str | None:
        return self.recusa.mensagem if self.recusa else None

    @property
    def cadeiras(self) -> list[dict]:
        return self.recusa.cadeiras if self.recusa else []


def _raiz_casa_padrao() -> Path:
    if os.environ.get("PF_CASA_RAIZ"):
        return Path(os.environ["PF_CASA_RAIZ"])
    if os.environ.get("PLATAFIRMA_RELEASE"):
        return Path(os.environ["PLATAFIRMA_RELEASE"]) / "casa"
    release_casa = Path("/opt/platafirma/current/casa")
    if (release_casa / "instancias" / "persona").is_dir():
        return release_casa
    return Path(__file__).resolve().parents[4]


def carregar_secao_das_cadeiras(base: Path | None = None, abertura_dir: Path | None = None) -> SecaoDasCadeiras:
    fixture = os.environ.get("PF_NOMES_FIXTURE") or os.environ.get("PF_SECAO_CADEIRAS")
    if fixture:
        caminho = Path(fixture)
        for arq in caminho.parent.glob(caminho.name):
            secao = SecaoDasCadeiras.de_texto(arq.read_text(encoding="utf-8"))
            if abertura_dir:
                secao = secao.com_abertura_dir(abertura_dir)
            return secao
    raiz = base or _raiz_casa_padrao()
    return SecaoDasCadeiras.de_pasta(raiz, abertura_dir=abertura_dir)


def _resolver_cadeira(dado: str, secao: SecaoDasCadeiras) -> tuple[str | None, str | None]:
    bruto = (dado or "").strip()
    if not bruto:
        return None, None
    limpo = bruto
    for pref in ("claudinho-", "claudinha-"):
        if limpo.lower().startswith(pref):
            limpo = limpo[len(pref):]
            break

    if limpo in secao.cadeiras:
        return limpo, None

    alvo_esp = _sem_acento_espaco(limpo)
    alvo_slug = _chave_slug(limpo)

    for slug, decl in secao.cadeiras.items():
        for nome_alt in decl.nomes:
            if alvo_esp == _sem_acento_espaco(nome_alt) or alvo_slug == _chave_slug(nome_alt):
                return slug, f"cadeira '{bruto}' resolvida para '{slug}'"
        if alvo_slug == slug:
            return slug, f"cadeira '{bruto}' resolvida para '{slug}'"

    return None, None


def _resolver_chapeu(
    cadeira: str,
    dado: str,
    decl: CadeiraDeclarada,
    secao: SecaoDasCadeiras,
) -> tuple[str | None, str | None, RecusaDeNome | None]:
    bruto = (dado or "").strip()
    validos = list(decl.chapeus.keys())
    alvo_slug = _chave_slug(bruto)
    alvo_esp = _sem_acento_espaco(bruto)

    if alvo_slug in decl.chapeus:
        return alvo_slug, None, None

    for ch_slug, nomes_alt in decl.chapeus.items():
        for nome_alt in nomes_alt:
            if alvo_esp == _sem_acento_espaco(nome_alt) or alvo_slug == _chave_slug(nome_alt):
                return ch_slug, f"chapéu '{bruto}' resolvido para '{ch_slug}'", None

    if alvo_slug in decl.apelidos_chapeu:
        ch_slug = decl.apelidos_chapeu[alvo_slug]
        return ch_slug, f"chapéu '{bruto}' resolvido para '{ch_slug}'", None

    casam = [c for c in validos if alvo_slug and alvo_slug in c]
    if len(casam) == 1:
        return casam[0], f"chapéu '{bruto}' resolvido para '{casam[0]}'", None
    if len(casam) > 1:
        lista = secao.formatar_lista()
        msg = (
            f"erro: chapéu '{bruto}' ambíguo na cadeira '{cadeira}' — "
            f"casa com {', '.join(casam)}\n{lista}"
        )
        return None, None, RecusaDeNome(codigo="chapeu-ambiguo", mensagem=msg, cadeiras=secao.como_lista())

    lista = secao.formatar_lista()
    msg = (
        f"erro: chapéu '{bruto}' fora do vocabulário da cadeira '{cadeira}' — "
        f"cadeiras e chapéus válidos:\n{lista}"
    )
    return None, None, RecusaDeNome(codigo="nome-nao-casa", mensagem=msg, cadeiras=secao.como_lista())


def resolver(
    cadeira: str,
    chapeu: str | None = None,
    secao: SecaoDasCadeiras | str | None = None,
) -> Resolucao:
    """Resolve `cadeira` e `chapeu` contra `secao`, devolvendo os slugs e avisos ou a recusa com a lista completa."""
    if isinstance(secao, str):
        secao_obj = SecaoDasCadeiras.de_texto(secao)
    elif secao is None:
        secao_obj = carregar_secao_das_cadeiras()
    else:
        secao_obj = secao

    avisos: list[str] = []
    cad_slug, aviso_cad = _resolver_cadeira(cadeira, secao_obj)
    if not cad_slug:
        lista = secao_obj.formatar_lista()
        msg = (
            f"erro: cadeira '{cadeira}' fora do vocabulário — "
            f"cadeiras e chapéus válidos:\n{lista}"
        )
        return Resolucao(
            cadeira=None,
            chapeu=None,
            avisos=[],
            recusa=RecusaDeNome(codigo="nome-nao-casa", mensagem=msg, cadeiras=secao_obj.como_lista()),
        )
    if aviso_cad:
        avisos.append(aviso_cad)

    if not chapeu or not chapeu.strip():
        return Resolucao(cadeira=cad_slug, chapeu=None, avisos=avisos, recusa=None)

    decl = secao_obj.cadeiras[cad_slug]
    ch_slug, aviso_ch, recusa_ch = _resolver_chapeu(cad_slug, chapeu, decl, secao_obj)
    if recusa_ch is not None:
        return Resolucao(cadeira=cad_slug, chapeu=None, avisos=avisos, recusa=recusa_ch)
    if aviso_ch:
        avisos.append(aviso_ch)
    return Resolucao(cadeira=cad_slug, chapeu=ch_slug, avisos=avisos, recusa=None)
