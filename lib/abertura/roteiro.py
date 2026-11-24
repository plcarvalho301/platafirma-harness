"""Montagem do roteiro da porta pela ficha `roteiro:porta` e tupla da primeira linha (story 4367, F4269).

A abertura lê a ligação `construido-de` da ficha do roteiro, agrupa as instâncias por classe e serve
uma parte por classe com a instância resolvida para a sessão — descartando `instrucao` (já posta
pelo arranque) e sem derrubar a sessão quando uma peça não tem leitura ou a ficha não está disponível.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from postura.casa import SemBanco

FALLBACK_CLASSES: tuple[str, ...] = (
    "persona",
    "chapeu",
    "cultura",
    "postura",
    "cenario",
    "circunstancia",
)

ORDEM_PADRAO: tuple[str, ...] = (*FALLBACK_CLASSES, "ritual")

CLASSES_IGNORADAS: frozenset[str] = frozenset({"instrucao"})

_RE_TUPLA = re.compile(r"^\(([^()]+)\)$")
_AVISO_CULTURA_FIXA = "cultura é fixa e não se troca nem se tira pela tupla: servindo cultura:da-casa"


def _slug_de(texto: str) -> str:
    sem = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[\s_]+", "-", sem.strip().lower())


@dataclass(frozen=True)
class PecaDoRoteiro:
    classe: str
    chave: str
    posicao: int | None = None

    @property
    def slug(self) -> str:
        prefixo = f"{self.classe}:"
        if self.chave.startswith(prefixo):
            return self.chave[len(prefixo):]
        return self.chave


@dataclass(frozen=True)
class TuplaDaPrimeiraLinha:
    cadeira: str
    chapeu: str | None = None
    overrides: tuple[tuple[str, str], ...] = ()
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class PedidoDeRoteiro:
    cadeira: str
    chapeu: str | None = None
    roteiro: str = "porta"
    overrides: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ParteLida:
    ok: bool
    conteudo: str
    ref: str
    instancias: tuple[str, ...] = ()
    avisos: tuple[str, ...] = ()
    erro: str | None = None


@dataclass(frozen=True)
class ParteServida:
    parte: str
    ref: str
    frescor: str
    motivo: str | None
    conteudo: str | None

    def como_dict(self) -> dict:
        return {
            "parte": self.parte,
            "ref": self.ref,
            "frescor": self.frescor,
            "motivo": self.motivo,
            "conteudo": self.conteudo,
        }


@dataclass(frozen=True)
class RoteiroMontado:
    partes: tuple[ParteServida, ...]
    avisos: tuple[str, ...]
    conteudo: str


class LeitorDoRoteiro(Protocol):
    def construido_de(self, roteiro: str = "porta") -> Sequence[tuple[str, str] | PecaDoRoteiro]: ...


class LeitorDeParte(Protocol):
    def ler(
        self,
        classe: str,
        cadeira: str,
        chapeu: str | None,
        *,
        chave: str | None = None,
    ) -> ParteLida: ...


def _classificar_elemento_tupla(
    elem: str,
    chapeu_atual: str | None,
    overrides: dict[str, str],
    avisos: list[str],
) -> str | None:
    if ":" not in elem:
        if _slug_de(elem) == "cultura":
            avisos.append(_AVISO_CULTURA_FIXA)
        else:
            avisos.append(f"elemento da tupla ignorado (forma esperada classe:chave): '{elem}'")
        return chapeu_atual

    cls_bruta, chave_bruta = elem.split(":", 1)
    cls, chave = _slug_de(cls_bruta), _slug_de(chave_bruta)
    if cls == "cultura":
        avisos.append(_AVISO_CULTURA_FIXA)
        return chapeu_atual
    if not cls or not chave:
        avisos.append(f"elemento da tupla ignorado (forma esperada classe:chave): '{elem}'")
        return chapeu_atual
    if cls == "chapeu" and chapeu_atual is None:
        return chave
    overrides[cls] = chave
    return chapeu_atual


def extrair_tupla(turno: str) -> TuplaDaPrimeiraLinha | None:
    """Reconhece uma tupla sozinha na primeira linha do turno do dono.

    Formas aceitas:
      - `(cadeira)`
      - `(cadeira, chapeu)`
      - `(cadeira, chapeu, classe:chave, ...)`
      - `(cadeira, classe:chave, ...)`

    Se os parênteses não estiverem sozinhos na primeira linha, devolve None.
    """
    linhas = turno.splitlines() if turno else []
    if not linhas:
        return None
    m = _RE_TUPLA.fullmatch(linhas[0].strip())
    if not m:
        return None
    brutos = [item.strip() for item in m.group(1).split(",")]
    if not brutos or any(not item for item in brutos):
        return None

    cadeira = brutos[0]
    chapeu: str | None = None
    resto_inicio = 1
    if len(brutos) > 1 and ":" not in brutos[1] and _slug_de(brutos[1]) != "cultura":
        chapeu = brutos[1]
        resto_inicio = 2

    overrides: dict[str, str] = {}
    avisos: list[str] = []
    for elem in brutos[resto_inicio:]:
        chapeu = _classificar_elemento_tupla(elem, chapeu, overrides, avisos)

    return TuplaDaPrimeiraLinha(
        cadeira=cadeira,
        chapeu=chapeu,
        overrides=tuple(overrides.items()),
        avisos=tuple(avisos),
    )


def _normalizar_pecas(brutas: Iterable[tuple[str, str] | tuple[str, str, int | None] | PecaDoRoteiro]) -> list[PecaDoRoteiro]:
    saida: list[PecaDoRoteiro] = []
    for item in brutas:
        if isinstance(item, PecaDoRoteiro):
            saida.append(item)
        else:
            pos = item[2] if len(item) > 2 else None
            saida.append(PecaDoRoteiro(classe=str(item[0]), chave=str(item[1]), posicao=pos))
    return saida


def _ordenar_classes(
    pecas: list[PecaDoRoteiro],
    avisos: list[str],
    roteiro: str,
) -> tuple[list[str], dict[str, set[str]]]:
    por_classe: dict[str, set[str]] = {}
    posicoes: dict[str, int] = {}
    for p in pecas:
        if p.classe in CLASSES_IGNORADAS:
            continue
        por_classe.setdefault(p.classe, set()).add(p.slug)
        if p.posicao is not None:
            atual = posicoes.get(p.classe)
            if atual is None or p.posicao < atual:
                posicoes[p.classe] = p.posicao

    classes = list(por_classe.keys())
    if posicoes:
        classes.sort(key=lambda c: (posicoes.get(c, 10**9), c))
    else:
        indice = {c: i for i, c in enumerate(ORDEM_PADRAO)}
        classes.sort(key=lambda c: (indice.get(c, len(ORDEM_PADRAO)), c))
        if classes:
            avisos.append(
                f"ficha roteiro:{roteiro} não declarou ordem (posicao): servindo na ordem padrão"
            )
    return classes, por_classe


def _anexar_aviso(avisos: list[str], msg: str) -> None:
    if msg and msg not in avisos:
        avisos.append(msg)


def _carregar_classes_da_ficha(
    leitor_roteiro: LeitorDoRoteiro,
    roteiro: str,
    avisos: list[str],
) -> tuple[list[str], dict[str, set[str]] | None]:
    try:
        brutas = list(leitor_roteiro.construido_de(roteiro))
    except SemBanco as erro:
        _anexar_aviso(
            avisos,
            f"ficha roteiro:{roteiro} indisponível (Olaria fora: {str(erro)[:160]}): servindo a lista padrão",
        )
        return list(FALLBACK_CLASSES), None

    if not brutas:
        _anexar_aviso(
            avisos,
            f"ficha roteiro:{roteiro} ausente ou sem construido-de: servindo a lista padrão",
        )
        return list(FALLBACK_CLASSES), None

    return _ordenar_classes(_normalizar_pecas(brutas), avisos, roteiro)


def _aplicar_overrides(
    classes_ordem: list[str],
    overrides: Sequence[tuple[str, str]],
    avisos: list[str],
) -> dict[str, str]:
    overrides_map: dict[str, str] = {}
    for cls, chave in overrides:
        if cls == "cultura":
            _anexar_aviso(avisos, _AVISO_CULTURA_FIXA)
            continue
        overrides_map[cls] = chave
        if cls not in classes_ordem:
            classes_ordem.append(cls)
    return overrides_map


def _instancia_antecipada_fora(
    classe: str,
    pedido: PedidoDeRoteiro,
    permitidas: set[str],
) -> str | None:
    if "*" in permitidas:
        return None
    alvo_por_classe = {
        "persona": pedido.cadeira,
        "chapeu": pedido.chapeu,
        "cultura": "da-casa",
    }
    alvo = alvo_por_classe.get(classe)
    if alvo and alvo not in permitidas:
        return f"instância '{classe}:{alvo}' não está no construido-de da ficha roteiro:{pedido.roteiro}"
    return None


def _conferir_instancias_lidas(
    classe: str,
    lida: ParteLida,
    permitidas: set[str],
    roteiro: str,
    avisos: list[str],
) -> bool:
    """Confere pertencimento das instâncias resolvidas. Devolve False se nenhuma estiver permitida."""
    if not lida.instancias or "*" in permitidas:
        return True
    faltantes = [inst for inst in lida.instancias if inst not in permitidas]
    for inst in faltantes:
        _anexar_aviso(
            avisos,
            f"instância '{classe}:{inst}' não está no construido-de da ficha roteiro:{roteiro}",
        )
    return len(faltantes) < len(lida.instancias)


def _resolver_parte(
    classe: str,
    pedido: PedidoDeRoteiro,
    leitor_parte: LeitorDeParte,
    *,
    permitidas: set[str] | None,
    chave_override: str | None,
) -> tuple[ParteServida | None, list[str]]:
    avisos_parte: list[str] = []
    if classe == "chapeu" and not pedido.chapeu and not chave_override:
        return None, avisos_parte

    if permitidas is not None and chave_override is None:
        aviso_fora = _instancia_antecipada_fora(classe, pedido, permitidas)
        if aviso_fora:
            return None, [aviso_fora]

    lida = leitor_parte.ler(classe, pedido.cadeira, pedido.chapeu, chave=chave_override)
    for av in lida.avisos:
        _anexar_aviso(avisos_parte, av)

    if not lida.ok:
        msg = (
            f"chave '{classe}:{chave_override}' da tupla não encontrada ou indisponível: {lida.erro or 'sem ficha'}"
            if chave_override
            else f"peça '{classe}' do roteiro sem leitura ou indisponível: {lida.erro or 'sem leitura'}"
        )
        _anexar_aviso(avisos_parte, msg)
        return None, avisos_parte

    if permitidas is not None and chave_override is None and not _conferir_instancias_lidas(
        classe, lida, permitidas, pedido.roteiro, avisos_parte
    ):
        return None, avisos_parte

    conteudo_parte = (lida.conteudo or "").strip()
    if not conteudo_parte:
        return None, avisos_parte

    return ParteServida(
        parte=classe,
        ref=lida.ref,
        frescor="fresco",
        motivo=None,
        conteudo=conteudo_parte,
    ), avisos_parte


def montar_roteiro(
    pedido: PedidoDeRoteiro,
    leitor_roteiro: LeitorDoRoteiro,
    leitor_parte: LeitorDeParte,
) -> RoteiroMontado:
    """Monta o roteiro da porta a partir do `construido-de` da ficha do roteiro."""
    avisos: list[str] = []
    classes_ordem, por_classe = _carregar_classes_da_ficha(leitor_roteiro, pedido.roteiro, avisos)
    overrides_map = _aplicar_overrides(classes_ordem, pedido.overrides, avisos)

    partes_servidas: list[ParteServida] = []
    for classe in classes_ordem:
        servida, novos_avisos = _resolver_parte(
            classe,
            pedido,
            leitor_parte,
            permitidas=por_classe.get(classe, set()) if por_classe is not None else None,
            chave_override=overrides_map.get(classe),
        )
        for av in novos_avisos:
            _anexar_aviso(avisos, av)
        if servida is not None:
            partes_servidas.append(servida)

    conteudo_total = "\n\n".join(p.conteudo for p in partes_servidas if p.conteudo)
    return RoteiroMontado(
        partes=tuple(partes_servidas),
        avisos=tuple(avisos),
        conteudo=conteudo_total,
    )
