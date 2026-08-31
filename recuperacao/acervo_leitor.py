"""Leitor e normalizador do acervo — acesso às entidades de catálogo e cadeia viva.

`spec_leitura-do-conhecimento.md` §2, §4, §5; `arq:0085` §2, §4, §5.
Compartilhado entre `descobrir` (#2952) e `situacao` (#2953).

Três princípios:
1. **Lê o vivo quando alcançável**, e a ontologia do acervo como store canônico em repouso.
2. **Fonte que não alcança o vivo responde `FonteIndisponivel`**, nunca zero silencioso
   (`arq:0085` §4).
3. **Normalização simétrica com unaccent e equivalência espaço/hífen** (§4-bis).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .adaptadores.base import FonteIndisponivel
from .envelope import Causa

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
ACERVO_DIR = os.environ.get("PF_ACERVO_DIR")


def normaliza_termo(texto: str) -> str:
    """Normaliza texto para casamento nos três eixos: unaccent, lowercase e equivalência hífen/espaço."""
    if not texto:
        return ""
    nfd = unicodedata.normalize("NFD", str(texto))
    sem_acento = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    limpo = re.sub(r"[\s\-_/.,;:!?()\[\]{}'\"`]+", " ", sem_acento.lower()).strip()
    return limpo


def radical(palavra: str) -> str:
    """Radical simples em português para casamento flexionado singular/plural/gênero."""
    p = normaliza_termo(palavra)
    if len(p) <= 3:
        return p
    if p.endswith("oes"):
        return p[:-3]
    if p.endswith("ao"):
        return p[:-2]
    if p.endswith("es") and len(p) > 4:
        return p[:-2]
    if p.endswith("s") and len(p) > 3 and not p.endswith("ss"):
        return p[:-1]
    return p


def radicais_de(texto: str) -> list[str]:
    return [radical(w) for w in normaliza_termo(texto).split() if w]


@dataclass(frozen=True, slots=True)
class ObraInfo:
    id: str
    titulo: str
    objeto: str
    arquivo: str | None = None
    colecao: str = "firma"
    dominio: str | None = None
    subdominio: str | None = None
    especie: str | None = None
    emitido_por: tuple[str, ...] = ()
    publicacao: str | None = None
    fichado_em: str | None = None

    @property
    def objeto_id(self) -> str:
        obj = str(self.objeto or "")
        return obj.removeprefix("acervo/").removeprefix("pessoal/")


@dataclass(frozen=True, slots=True)
class ConceitoInfo:
    slug: str
    rotulo: str
    outros_rotulos: tuple[str, ...] = ()
    definicao: str = ""
    mais_amplo: str | None = None


@dataclass(frozen=True, slots=True)
class SubdominioInfo:
    slug: str
    rotulo: str
    dominio: str
    recorte: str = ""


@dataclass(frozen=True, slots=True)
class ImpressaoInfo:
    id: str
    obra_id: str
    estado: str
    criada_em: str | None = None
    fonte_versao: str | None = None


@dataclass(slots=True)
class CatalogoAcervo:
    obras: dict[str, ObraInfo] = field(default_factory=dict)             # id -> ObraInfo
    obras_por_titulo: dict[str, list[ObraInfo]] = field(default_factory=dict)
    conceitos: dict[str, ConceitoInfo] = field(default_factory=dict)     # slug -> ConceitoInfo
    subdominios: dict[str, SubdominioInfo] = field(default_factory=dict) # slug -> SubdominioInfo
    obra_trata_de: dict[str, set[str]] = field(default_factory=dict)     # obra_id -> set[conceito_slug]
    conceito_obras: dict[str, set[str]] = field(default_factory=dict)    # conceito_slug -> set[obra_id]
    subdominio_obras: dict[str, set[str]] = field(default_factory=dict) # subdominio_slug -> set[obra_id]
    impressoes_por_obra: dict[str, list[ImpressaoInfo]] = field(default_factory=dict) # obra_id -> list[ImpressaoInfo]
    carimbo: str = "acervo:v0"


_CACHE_CATALOGO: CatalogoAcervo | None = None
_CACHE_MTIMES: tuple[int, ...] = ()


def _dir_acervo(raiz: str = RAIZ) -> Path:
    if ACERVO_DIR:
        return Path(ACERVO_DIR)
    return Path(raiz) / "platafirma-conhecimento" / "ontologia" / "acervo"


def carrega_catalogo(raiz: str = RAIZ, forcar_releitura: bool = False) -> CatalogoAcervo:
    """Carrega o catálogo do acervo. Lê os JSONLs canônicos com checagem de mtime.

    Levanta `FonteIndisponivel(Causa.SEM_ROTA)` se os arquivos não existirem,
    ou `FonteIndisponivel(Causa.FORA_DO_AR)` se a leitura falhar.
    """
    global _CACHE_CATALOGO, _CACHE_MTIMES

    d = _dir_acervo(raiz)
    if not d.is_dir():
        raise FonteIndisponivel(Causa.SEM_ROTA, f"diretório do acervo ausente: {d}")

    arquivos_necessarios = [
        d / "obra.jsonl",
        d / "conceito.jsonl",
        d / "obra_trata_de.jsonl",
        d / "subdominio.jsonl",
    ]
    for arq in arquivos_necessarios:
        if not arq.is_file():
            raise FonteIndisponivel(Causa.SEM_INDICE, f"arquivo canônico ausente: {arq}")

    try:
        mtimes = tuple(a.stat().st_mtime_ns for a in arquivos_necessarios)
    except OSError as e:
        raise FonteIndisponivel(Causa.SEM_ROTA, f"falha ao acessar acervo: {e}") from e

    if not forcar_releitura and _CACHE_CATALOGO is not None and _CACHE_MTIMES == mtimes:
        return _CACHE_CATALOGO

    cat = CatalogoAcervo()

    # 1. Conceitos
    try:
        with open(d / "conceito.jsonl", encoding="utf-8", errors="replace") as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('{"_gerado"'):
                    continue
                rec = json.loads(l)
                slug = rec.get("slug")
                if not slug:
                    continue
                c = ConceitoInfo(
                    slug=slug,
                    rotulo=rec.get("rotulo") or slug,
                    outros_rotulos=tuple(rec.get("outros_rotulos") or ()),
                    definicao=rec.get("definicao") or "",
                    mais_amplo=rec.get("mais_amplo"),
                )
                cat.conceitos[slug] = c
    except Exception as e:
        raise FonteIndisponivel(Causa.FORA_DO_AR, f"erro ao ler conceitos: {e}") from e

    # 2. Subdomínios
    try:
        with open(d / "subdominio.jsonl", encoding="utf-8", errors="replace") as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('{"_gerado"'):
                    continue
                rec = json.loads(l)
                slug = rec.get("slug")
                if not slug:
                    continue
                s = SubdominioInfo(
                    slug=slug,
                    rotulo=rec.get("rotulo") or slug,
                    dominio=rec.get("dominio") or "",
                    recorte=rec.get("recorte") or "",
                )
                cat.subdominios[slug] = s
    except Exception as e:
        raise FonteIndisponivel(Causa.FORA_DO_AR, f"erro ao ler subdominios: {e}") from e

    # 3. Obras
    try:
        with open(d / "obra.jsonl", encoding="utf-8", errors="replace") as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('{"_gerado"'):
                    continue
                rec = json.loads(l)
                oid = rec.get("id")
                titulo = rec.get("titulo")
                if not oid or not titulo:
                    continue
                obj = rec.get("objeto") or f"acervo/{oid.replace('-', '')}"
                obra = ObraInfo(
                    id=str(oid),
                    titulo=str(titulo),
                    objeto=str(obj),
                    arquivo=rec.get("arquivo"),
                    colecao=rec.get("colecao") or "firma",
                    dominio=rec.get("dominio"),
                    subdominio=rec.get("subdominio"),
                    especie=rec.get("especie"),
                    emitido_por=tuple(rec.get("emitido_por") or ()),
                    publicacao=rec.get("publicacao"),
                    fichado_em=rec.get("fichado_em"),
                )
                cat.obras[obra.id] = obra
                norm_tit = normaliza_termo(obra.titulo)
                cat.obras_por_titulo.setdefault(norm_tit, []).append(obra)

                if obra.subdominio:
                    cat.subdominio_obras.setdefault(obra.subdominio, set()).add(obra.id)

                # Estado de impressão padrão
                imp_id = obra.id
                cat.impressoes_por_obra.setdefault(obra.id, []).append(
                    ImpressaoInfo(
                        id=imp_id,
                        obra_id=obra.id,
                        estado="servindo",
                        criada_em=obra.fichado_em or "2026-08-01T00:00:00Z",
                    )
                )
    except Exception as e:
        raise FonteIndisponivel(Causa.FORA_DO_AR, f"erro ao ler obras: {e}") from e

    # 4. Obra trata de conceito
    try:
        with open(d / "obra_trata_de.jsonl", encoding="utf-8", errors="replace") as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith('{"_gerado"'):
                    continue
                rec = json.loads(l)
                c_slug = rec.get("conceito")
                o_ref = rec.get("obra")
                if not c_slug or not o_ref:
                    continue
                obras_encontradas = []
                if o_ref in cat.obras:
                    obras_encontradas.append(cat.obras[o_ref])
                else:
                    norm_ref = normaliza_termo(o_ref)
                    if norm_ref in cat.obras_por_titulo:
                        obras_encontradas.extend(cat.obras_por_titulo[norm_ref])
                    else:
                        for o in cat.obras.values():
                            if o.arquivo and normaliza_termo(o.arquivo) == norm_ref:
                                obras_encontradas.append(o)

                for o in obras_encontradas:
                    cat.obra_trata_de.setdefault(o.id, set()).add(c_slug)
                    cat.conceito_obras.setdefault(c_slug, set()).add(o.id)
    except Exception as e:
        raise FonteIndisponivel(Causa.FORA_DO_AR, f"erro ao ler obra_trata_de: {e}") from e

    # Carimbo
    try:
        import hashlib

        sha = hashlib.sha256(str(mtimes).encode()).hexdigest()[:12]
        cat.carimbo = f"acervo:{sha}"
    except Exception:
        cat.carimbo = "acervo:v1"

    _CACHE_CATALOGO = cat
    _CACHE_MTIMES = mtimes
    return cat
