"""Gate de procedência — a chave citada confere contra o índice (#2310, F3).

`spec_recuperador.md` §10. Roda em `minuta escrever`, ADR e `fechar decisão`.

**O gate não abre conexão própria a banco.** Ele confere **chamando `recuperar`**, e por
isso herda disjuntor e cache de graça (§10.2). `recuperar` entra injetado; no serviço é a
biblioteca deste mesmo pacote, e no teste é uma função.

## Predicado em dois passos, e por que são dois

    (a) a chave resolve em QUALQUER impressão?  → procedência válida
    (b) está servindo?                          → citável hoje

Colapsar os dois num só reprovaria citação legítima de impressão aposentada como se fosse
chave fabricada — que é o erro caro, porque manda o autor reescrever uma citação correta.
São dois vereditos distintos e só um deles recusa.

## O que o gate grava

Coordenada humana (§10.5), resolvida pelo `resolvedor` — a chave gravada continua sendo a
da seção-folha. A gravação é idempotente: rodar o gate duas vezes no mesmo artefato não
duplica coordenada.

## Estado do conceito não é veredito de chave

O degrau de `arq:0064` §5 viaja no veredito para quem quiser aplicá-lo, mas o gate NÃO
barra por estado: exigir citação de conceito que o acervo não ancora transfere a falha de
"não citou" para "citou vizinho que não responde", que é pior por ser invisível.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .envelope import Envelope, Procedencia
from .fontes import PREFIXO_CHAVE, Fonte
from .resolvedor import Coordenada, NaoResolve, Resolvedor, le_chave

# ------------------------------------------------------------------ extração

#: Uma alternância dos prefixos declarados em `fontes.PREFIXO_CHAVE` — nunca uma lista
#: escrita à mão aqui: fonte nova no catálogo tem de aparecer no gate sem edição.
_PREFIXOS = sorted({p for ps in PREFIXO_CHAVE.values() for p in ps}, key=len, reverse=True)
_RE_CHAVE = re.compile(
    r"(?<![\w:])(" + "|".join(re.escape(p) for p in _PREFIXOS) + r")([^\s,;)\]}\"'»]+)"
)

#: Marca de coordenada já gravada. Serve à idempotência do §10.5.
_JA_GRAVADA = " @ impressão "


def extrai_chaves(texto: str) -> list[str]:
    """As chaves de procedência citadas no artefato, na ordem, sem repetição."""
    vistas: dict[str, None] = {}
    for m in _RE_CHAVE.finditer(str(texto)):
        vistas.setdefault(m.group(0).rstrip(".,;:"), None)
    return list(vistas)


# ------------------------------------------------------------------ veredito

class Julgamento(StrEnum):
    """Só `FABRICADA` recusa. Os outros dois passam, com registro distinto."""

    CITAVEL = "citavel"                    # resolve e está servindo
    APOSENTADA = "declarada-nao-servindo"  # resolve, não serve — não é fabricada
    FABRICADA = "fabricada"                # não resolve em impressão nenhuma


@dataclass(frozen=True, slots=True)
class Veredito:
    chave: str
    julgamento: Julgamento
    coordenada: Coordenada | None = None
    falta: str = ""
    proximo: str = ""

    @property
    def recusa(self) -> bool:
        return self.julgamento is Julgamento.FABRICADA

    def para_json(self) -> dict:
        d: dict = {"chave": self.chave, "julgamento": str(self.julgamento)}
        if self.coordenada is not None:
            d["coordenada"] = self.coordenada.para_json()
        if self.falta:
            d["falta"] = self.falta
        if self.proximo:
            d["proximo"] = self.proximo
        return d


@dataclass(frozen=True, slots=True)
class Parecer:
    """O que o gate devolve ao verbo: os vereditos e o artefato com as coordenadas."""

    vereditos: tuple[Veredito, ...]
    texto: str

    @property
    def aprovado(self) -> bool:
        return not any(v.recusa for v in self.vereditos)

    @property
    def recusadas(self) -> tuple[Veredito, ...]:
        return tuple(v for v in self.vereditos if v.recusa)

    def para_json(self) -> dict:
        return {
            "aprovado": self.aprovado,
            "vereditos": [v.para_json() for v in self.vereditos],
        }


# ---------------------------------------------------------------------- gate

class Gate:
    """`recuperar(chave, servindo=True) -> Envelope` entra injetado (§10.2)."""

    def __init__(self, recuperar, resolvedor: Resolvedor) -> None:
        self._recuperar = recuperar
        self._resolvedor = resolvedor

    # -- passo (a) e (b) ---------------------------------------------------
    def _procedencia(self, chave: str, *, servindo: bool) -> Procedencia | None:
        env = self._recuperar(chave, servindo=servindo)
        if env is None:
            return None
        if not isinstance(env, Envelope):
            raise TypeError("recuperar tem de devolver Envelope: o gate lê o contrato, não o binário")
        alvo = le_chave(chave)
        for item in env.itens:
            lido = le_chave(item.procedencia.chave)
            if lido.fonte is alvo.fonte and lido.objeto == alvo.objeto and lido.ancora == alvo.ancora:
                return item.procedencia
        return None

    def confere(self, chave: str) -> Veredito:
        if proc := self._procedencia(chave, servindo=True):
            return self._com_coordenada(chave, proc, Julgamento.CITAVEL)
        if proc := self._procedencia(chave, servindo=False):
            return self._com_coordenada(chave, proc, Julgamento.APOSENTADA)
        fonte = le_chave(chave).fonte
        return Veredito(
            chave=chave,
            julgamento=Julgamento.FABRICADA,
            falta="a chave não resolve em nenhuma impressão do índice",
            proximo=f"recuperar --fonte {fonte} --chave {chave}",
        )

    def _com_coordenada(self, chave: str, proc: Procedencia, julgamento: Julgamento) -> Veredito:
        try:
            coord = self._resolvedor.resolve(proc)
        except NaoResolve as e:
            # Resolve no índice mas não vira coordenada: degradação DECLARADA, não recusa.
            return Veredito(chave=chave, julgamento=julgamento, falta=e.falta, proximo=e.proximo)
        return Veredito(chave=chave, julgamento=julgamento, coordenada=coord)

    # -- o artefato --------------------------------------------------------
    def julga(self, texto: str) -> Parecer:
        """Confere todas as chaves citadas e grava as coordenadas resolvidas."""
        vereditos = tuple(self.confere(c) for c in extrai_chaves(texto))
        return Parecer(vereditos=vereditos, texto=self.grava(texto, vereditos))

    @staticmethod
    def grava(texto: str, vereditos) -> str:
        """Idempotente: chave que já vem seguida da impressão não é reescrita."""
        saida = str(texto)
        for v in vereditos:
            if v.coordenada is None:
                continue
            alvo, novo = v.chave, v.coordenada.para_texto()
            pos = 0
            while (i := saida.find(alvo, pos)) != -1:
                fim = i + len(alvo)
                if saida[fim:fim + len(_JA_GRAVADA)] == _JA_GRAVADA:
                    pos = fim
                    continue
                saida = saida[:i] + novo + saida[fim:]
                pos = i + len(novo)
        return saida


def fontes_citadas(texto: str) -> set[Fonte]:
    """Quais das seis o artefato cita. Insumo do eixo 2 (#2317)."""
    return {le_chave(c).fonte for c in extrai_chaves(texto)}
