"""Montagem da distribuição rotinas na abertura da sessão (regra 24 da F4269).

Os processos cuja entrega é rotina chegam carregados na abertura quando têm gatilho que os dispare (`dispara`) e resultado
que produzem (`produz`). O processo sem gatilho sai como `Recusa(codigo="processo-sem-gatilho")`, e o sem resultado sai como
`Recusa(codigo="processo-sem-resultado")`, sem derrubar a abertura: o resto é servido.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from postura.casa import FichaDeProcesso


class LeitorDeProcessos(Protocol):
    def processos_de_rotina(self) -> list[FichaDeProcesso]: ...


@dataclass(frozen=True)
class Processo(FichaDeProcesso):
    def como_dict(self) -> dict:
        return {
            "chave": self.chave,
            "classe": self.classe,
            "slug": self.slug,
            "gatilhos": list(self.gatilhos),
            "produz": list(self.produz),
            "conteudo": self.conteudo,
        }


@dataclass(frozen=True)
class Recusa:
    codigo: str
    processo: str = ""
    mensagem: str = ""

    @property
    def chave(self) -> str:
        return self.processo

    def como_dict(self) -> dict:
        d = {"codigo": self.codigo}
        if self.processo:
            d["processo"] = self.processo
        if self.mensagem:
            d["mensagem"] = self.mensagem
        return d


def _raiz_casa() -> Path:
    dada = os.environ.get("PF_CASA_RAIZ")
    return Path(dada) if dada else Path(__file__).resolve().parents[4]


def _carregar_conteudo(ficha: FichaDeProcesso, base: Path | None = None) -> str:
    if ficha.conteudo:
        return ficha.conteudo
    raiz = base or _raiz_casa()
    classe = ficha.classe
    slug = ficha.slug
    if not (classe and slug):
        return ""
    pasta = raiz / "instancias" / classe
    nome = f"{slug}.md"
    for arq in pasta.glob(nome):
        return arq.read_text(encoding="utf-8").strip()
    return ""


def rotinas(leitor: LeitorDeProcessos, base: Path | None = None) -> tuple[list[Processo], list[Recusa]]:
    """Lê os processos de rotina e separa os válidos dos recusados por falta de gatilho ou resultado."""
    servidos: list[Processo] = []
    recusas: list[Recusa] = []
    for ficha in leitor.processos_de_rotina():
        if not ficha.gatilhos:
            recusas.append(
                Recusa(
                    codigo="processo-sem-gatilho",
                    processo=ficha.chave,
                    mensagem=f"processo {ficha.chave} recusado: nenhum gatilho o dispara (processo-sem-gatilho)",
                )
            )
            continue
        if not ficha.produz:
            recusas.append(
                Recusa(
                    codigo="processo-sem-resultado",
                    processo=ficha.chave,
                    mensagem=f"processo {ficha.chave} recusado: não declara capacidade que produz (processo-sem-resultado)",
                )
            )
            continue
        servidos.append(
            Processo(
                chave=ficha.chave,
                gatilhos=tuple(ficha.gatilhos),
                produz=tuple(ficha.produz),
                classe=ficha.classe,
                conteudo=_carregar_conteudo(ficha, base),
            )
        )
    return servidos, recusas


def formatar_rotinas(processos: list[Processo]) -> str:
    """Formata o texto da distribuição rotinas com os processos servidos."""
    if not processos:
        return ""
    blocos: list[str] = []
    for p in processos:
        cabecalho = f"## {p.chave} (gatilho: {', '.join(p.gatilhos)} · produz: {', '.join(p.produz)})"
        if p.conteudo:
            blocos.append(f"{cabecalho}\n\n{p.conteudo}")
        else:
            blocos.append(cabecalho)
    return "\n\n".join(blocos)
