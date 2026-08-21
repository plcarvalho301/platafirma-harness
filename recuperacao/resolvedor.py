"""Resolvedor — chave estrutural → coordenada humana (#2311, F3).

`spec_recuperador.md` §10.5–6. Duas coisas que este módulo NÃO faz, e são o motivo
de ele existir apartado do gate:

1. **Não abre conexão própria.** A consulta ao índice entra injetada (`consulta`),
   e no serviço ela é `recuperar`. §10.2: o gate herda disjuntor e cache de graça;
   um resolvedor com driver próprio devolveria os dois pela janela.
2. **Não reescreve a chave.** A chave gravada no artefato é sempre a da
   **seção-folha**. O resolvedor sobe ao ancestral titulado SÓ para a coordenada
   humana — gravar a chave do ancestral colapsaria seções distintas numa citação
   só e envenenaria o dedupe da fita (`arq:0065` §7).

## Âncora-ruído e a degradação declarada

Âncora sem nenhuma letra latina (número solto, marca de página) não vira coordenada:
o rótulo seria plausível e errado. A escada de degradação é, nesta ordem —

    seção-folha titulada → ancestral titulado → obra + página → obra

— e o degrau usado sai NOMEADO em `Coordenada.degrau`. Derivar título do corpo do
trecho está descartado: fabrica coordenada com aparência de certa, que é o dano que
o §10 existe para impedir.

## Os cinco estados

`arq:0064` §5, item 4. São cinco, não três, e a distinção é de classe: `zero
obra-âncora` é derivável; `lacuna` é juízo, e juízo não se deriva. O resolvedor
DERIVA os quatro deriváveis e lê `lacuna` de `acervo.conceito_lacuna` quando a
consulta a informar — nunca a infere da ausência de obra.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum

from .envelope import ContratoViolado, Procedencia
from .fontes import Fonte

# --------------------------------------------------------------------- estados

class EstadoConceito(StrEnum):
    """Tabela de `arq:0064` §5 (item 4). `LACUNA` não é derivável — só declarada."""

    ANCORADO = "ancorado"
    DECLARADO_NAO_SERVINDO = "declarado-nao-servindo"
    LACUNA = "lacuna-declarada"
    SEM_OBRA_NAO_JULGADO = "sem-obra-nao-julgado"
    ORFAO = "orfao"


#: Estados que abrem hoje (spec §10.6). `LACUNA` entra com a primeira linha da
#: tabela `acervo.conceito_lacuna` e não segura a fase.
DERIVAVEIS_HOJE = (
    EstadoConceito.ANCORADO,
    EstadoConceito.DECLARADO_NAO_SERVINDO,
    EstadoConceito.SEM_OBRA_NAO_JULGADO,
    EstadoConceito.ORFAO,
)


class Degrau(StrEnum):
    """Qual nível da escada sustentou a coordenada. Sai no artefato, declarado."""

    SECAO = "secao"
    ANCESTRAL = "ancestral-titulado"
    PAGINA = "obra-pagina"
    OBRA = "obra"
    NENHUM = "sem-coordenada"


# ------------------------------------------------------------ leitura da chave

_RE_ACERVO = re.compile(r"^acervo:(?P<objeto>[0-9a-f]{8,64})#(?P<ancora>[^:]+?)(?::p(?P<parte>\d+))?$")
_RE_WIKI = re.compile(r"^wiki:(?P<page_id>[^#]+)#(?P<secao>.+)$")


@dataclass(frozen=True, slots=True)
class ChaveLida:
    """Decomposição da chave estrutural do §4. `parte` é a PARTE, âncora é de SEÇÃO."""

    fonte: Fonte
    objeto: str
    ancora: str | None = None
    parte: int | None = None

    @property
    def chave_da_secao(self) -> str:
        """A chave sem `:p<idx>` — a unidade citável é a seção, não a parte (§4)."""
        if self.fonte != Fonte("acervo") or self.ancora is None:
            raise ContratoViolado("chave_da_secao só vale para acervo")
        return f"acervo:{self.objeto}#{self.ancora}"


def le_chave(chave: str) -> ChaveLida:
    """Lê a chave estrutural. Não valida existência — isso é a consulta ao índice."""
    texto = str(chave).strip()
    if m := _RE_ACERVO.match(texto):
        parte = m.group("parte")
        return ChaveLida(
            fonte=Fonte("acervo"),
            objeto=m.group("objeto"),
            ancora=m.group("ancora"),
            parte=int(parte) if parte is not None else None,
        )
    if m := _RE_WIKI.match(texto):
        return ChaveLida(fonte=Fonte("wiki"), objeto=m.group("page_id"), ancora=m.group("secao"))
    for fonte in Fonte:
        for prefixo in _prefixos(fonte):
            if texto.startswith(prefixo):
                return ChaveLida(fonte=fonte, objeto=texto[len(prefixo):])
    raise ContratoViolado(f"chave sem prefixo de fonte conhecida: {texto!r}")


def _prefixos(fonte: Fonte) -> tuple[str, ...]:
    from .fontes import PREFIXO_CHAVE

    return PREFIXO_CHAVE[fonte]


# --------------------------------------------------------------- âncora-ruído

def tem_letra_latina(texto: str) -> bool:
    """Predicado da âncora-ruído. Decompõe acento antes de olhar (NFD): `§4-bis`
    manda normalização declarada ao caractere, e `ação` tem de contar como letra."""
    for ch in unicodedata.normalize("NFD", str(texto)):
        if "a" <= ch.lower() <= "z":
            return True
    return False


def ancora_ruido(ancora: str | None) -> bool:
    """Âncora sem letra latina: número solto, marca de página, item numerado."""
    return not ancora or not tem_letra_latina(ancora)


# ---------------------------------------------------------------- coordenada

@dataclass(frozen=True, slots=True)
class Coordenada:
    """A coordenada humana do §10.5, e o degrau que a sustentou.

    `chave` e `versao` continuam sendo os da SEÇÃO-FOLHA, sempre — mesmo quando o
    texto legível veio do ancestral.
    """

    obra: str
    chave: str
    versao: str
    hierarquia: tuple[str, ...] = ()
    pagina: int | None = None
    degrau: Degrau = Degrau.SECAO
    estado: EstadoConceito | None = None

    def __post_init__(self) -> None:
        if not str(self.obra).strip():
            raise ContratoViolado("coordenada sem obra não é coordenada")
        if not str(self.chave).strip():
            raise ContratoViolado("coordenada sem chave: procedência é obrigatória (§3, inv. 1)")
        object.__setattr__(self, "hierarquia", tuple(h for h in self.hierarquia if str(h).strip()))
        if self.degrau in (Degrau.SECAO, Degrau.ANCESTRAL) and not self.hierarquia:
            raise ContratoViolado(f"degrau {self.degrau} sem hierarquia: degrau mente")
        if self.degrau is Degrau.PAGINA and self.pagina is None:
            raise ContratoViolado("degrau obra-pagina sem página")

    def para_texto(self) -> str:
        """Forma do §10.5. Sem hierarquia e sem página, sai obra + chave: curto e
        honesto vale mais que completo e fabricado."""
        partes = [self.obra, *self.hierarquia]
        cabeca = " › ".join(partes)
        if self.pagina is not None:
            cabeca = f"{cabeca}, p. {self.pagina}"
        return f"{cabeca} — {self.chave} @ impressão {self.versao}"

    def para_json(self) -> dict:
        d: dict = {
            "obra": self.obra,
            "chave": self.chave,
            "versao": self.versao,
            "degrau": str(self.degrau),
            "texto": self.para_texto(),
        }
        if self.hierarquia:
            d["hierarquia"] = list(self.hierarquia)
        if self.pagina is not None:
            d["pagina"] = self.pagina
        if self.estado is not None:
            d["estado"] = str(self.estado)
        return d


class NaoResolve(Exception):
    """A chave não resolve no índice. Erro que instrui (`arq:0064` §6): traz o que
    falta e o próximo passo — o gate do #2310 o converte em `falta`/`proximo`."""

    def __init__(self, chave: str, falta: str, proximo: str = "") -> None:
        self.chave, self.falta, self.proximo = chave, falta, proximo
        super().__init__(f"{chave}: {falta}")

    def para_json(self) -> dict:
        d = {"chave": self.chave, "falta": self.falta}
        if self.proximo:
            d["proximo"] = self.proximo
        return d


# ---------------------------------------------------------------- resolvedor

@dataclass(slots=True)
class Secao:
    """O que a consulta ao índice devolve por seção. Campos do modelo
    `docs/modelo-acervo-secao.md`; ausência é `None`, nunca string vazia."""

    obra: str
    ancora: str
    impressao: str
    titulo: str | None = None
    hierarquia: tuple[str, ...] = ()
    pagina: int | None = None
    qualidade: str | None = None
    servindo: bool = True
    obras: int = 1
    obras_servindo: int = 1
    classificado: bool = True
    lacuna: bool = False
    ancestrais: tuple[str, ...] = field(default_factory=tuple)


class Resolvedor:
    """Chave estrutural → `Coordenada`. `consulta` é injetada (§10.2)."""

    def __init__(self, consulta) -> None:
        self._consulta = consulta

    # -- estado do conceito ------------------------------------------------
    @staticmethod
    def estado(s: Secao) -> EstadoConceito:
        if s.lacuna:
            return EstadoConceito.LACUNA          # juízo declarado, nunca derivado
        if not s.classificado:
            return EstadoConceito.ORFAO
        if s.obras >= 1 and s.obras_servindo >= 1:
            return EstadoConceito.ANCORADO
        if s.obras >= 1:
            return EstadoConceito.DECLARADO_NAO_SERVINDO
        return EstadoConceito.SEM_OBRA_NAO_JULGADO

    # -- resolução ---------------------------------------------------------
    def resolve(self, proc: Procedencia) -> Coordenada:
        lida = le_chave(proc.chave)
        s = self._consulta(lida)
        if s is None:
            raise NaoResolve(
                proc.chave,
                falta="a chave não resolve em nenhuma impressão do índice",
                proximo=f"recuperar --fonte {lida.fonte} --chave {lida.objeto}",
            )
        if not isinstance(s, Secao):
            raise ContratoViolado("consulta devolveu algo que não é Secao")

        hierarquia, pagina, degrau = self._escada(s)
        return Coordenada(
            obra=s.obra,
            chave=proc.chave,                     # SEMPRE a da folha (§10, arq:0065 §7)
            versao=proc.versao.valor,
            hierarquia=hierarquia,
            pagina=pagina,
            degrau=degrau,
            estado=self.estado(s),
        )

    @staticmethod
    def _escada(s: Secao) -> tuple[tuple[str, ...], int | None, Degrau]:
        """seção titulada → ancestral titulado → obra+página → obra."""
        if s.titulo and not ancora_ruido(s.ancora):
            return (*s.hierarquia, s.titulo), s.pagina, Degrau.SECAO
        titulados = tuple(a for a in s.ancestrais if a and tem_letra_latina(a))
        if titulados:
            return titulados, s.pagina, Degrau.ANCESTRAL
        if s.pagina is not None:
            return (), s.pagina, Degrau.PAGINA
        return (), None, Degrau.OBRA
