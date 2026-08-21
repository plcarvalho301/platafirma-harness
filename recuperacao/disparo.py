"""Eixo 2 — taxa de disparo por release (#2317, F4).

`spec_recuperador.md` §13 (eixo 2) e §11 (a trilha que ele lê).

## O que se mede

Disparo é **a sessão ter alcançado o Recuperador**, não o Recuperador ter respondido bem
— isso é o eixo 1. A unidade é a sessão, e a identidade é o `sujeito`: o §11 existe para
que o número seja por sujeito e não por processo.

Lê a trilha de LEITURA (§11), não a do veredito: `{ts, tool, sujeito, sessao, fonte,
cobertura, carimbo, hit|miss, disjuntor}` — uma linha por fonte alcançada.

Equivalente em `jq`, que é a forma que a spec nomeia, e serve de conferência cruzada:

    jq -rs '[.[] | select(.release=="F4") | .sessao] | unique | length' trilha.jsonl

## O denominador não se inventa

Taxa é fração, e a trilha só conhece o numerador: quem NÃO disparou não escreve linha
nenhuma. O total de sessões da release vem de fora (`sessoes_abertas`). Sem ele, esta peça
publica a CONTAGEM e diz `taxa: null` com `denominador: "não medido"` — nunca divide pelo
que tem em mãos. Taxa com denominador improvisado é o número que sobrevive à fita e vira
citação errada seis semanas depois.

## Instrumentar primeiro (§13)

A série com o veredito desligado **é** o baseline. A primeira release publicada é a régua
da segunda; `delta` só existe quando as duas têm denominador medido, e recusa dizer o
contrário.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .fontes import Fonte
from .veredito import PRODUTORES_COM_PARIDADE

TRILHA_LEITURA = os.environ.get(
    "PF_REC_TRILHA_LEITURA", str(Path.home() / "AI" / "var" / "log" / "recuperacao" / "leitura.jsonl")
)


@dataclass(frozen=True, slots=True)
class FonteAlcancada:
    fonte: str
    linhas: int = 0
    hit: int = 0
    miss: int = 0
    disjuntor_aberto: int = 0

    @property
    def taxa_hit(self) -> float | None:
        total = self.hit + self.miss
        return None if not total else round(self.hit / total, 4)

    def para_json(self) -> dict:
        return {
            "fonte": self.fonte, "linhas": self.linhas, "hit": self.hit, "miss": self.miss,
            "disjuntor_aberto": self.disjuntor_aberto, "taxa_hit": self.taxa_hit,
        }


@dataclass(frozen=True, slots=True)
class Disparo:
    """A série do eixo 2 para uma release."""

    release: str = ""
    sessoes: int = 0
    sujeitos: tuple[str, ...] = field(default_factory=tuple)
    linhas: int = 0
    sessoes_abertas: int | None = None
    por_fonte: tuple[FonteAlcancada, ...] = field(default_factory=tuple)
    parcial: bool = True
    motivo: str = ""
    fontes_ausentes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def taxa(self) -> float | None:
        """`None` sem denominador medido. Não há valor de fallback aceitável aqui."""
        if not self.sessoes_abertas:
            return None
        return round(self.sessoes / self.sessoes_abertas, 4)

    @property
    def denominador(self) -> str:
        return "não medido" if not self.sessoes_abertas else str(self.sessoes_abertas)

    def para_json(self) -> dict:
        return {
            "release": self.release, "sessoes_que_dispararam": self.sessoes,
            "sujeitos": list(self.sujeitos), "linhas": self.linhas,
            "denominador": self.denominador, "taxa": self.taxa,
            "parcial": self.parcial, "motivo": self.motivo,
            "fontes_ausentes": list(self.fontes_ausentes),
            "por_fonte": [f.para_json() for f in self.por_fonte],
        }

    def para_texto(self) -> str:
        taxa = "—" if self.taxa is None else f"{self.taxa:.2%}"
        cab = [
            f"eixo 2 · release {self.release or '(sem release)'}",
            f"  disparo    {self.sessoes} sessões / {self.denominador} abertas = {taxa}",
            f"  sujeitos   {len(self.sujeitos)}  ·  linhas {self.linhas}",
        ]
        if self.parcial:
            cab.append(f"  PARCIAL — {self.motivo}")
        corpo = [
            f"  {f.fonte:<9} {f.linhas:>5} linhas  hit "
            + ("—" if f.taxa_hit is None else f"{f.taxa_hit:.2%}")
            + (f"  disjuntor {f.disjuntor_aberto}" if f.disjuntor_aberto else "")
            for f in self.por_fonte
        ]
        return "\n".join([*cab, *corpo])


def serie_disparo(trilha: str | None = None, *, release: str = "",
                  sessoes_abertas: int | None = None,
                  produtores: tuple[str, ...] = PRODUTORES_COM_PARIDADE) -> Disparo:
    """Lê a trilha de leitura do §11 e publica o eixo 2. Linha ilegível não derruba."""
    caminho = Path(trilha or TRILHA_LEITURA)
    sessoes: set[str] = set()
    sujeitos: set[str] = set()
    por_fonte: dict[str, dict] = defaultdict(lambda: {"linhas": 0, "hit": 0, "miss": 0, "disj": 0})
    vistos: set[str] = set()
    lidas = 0

    if caminho.exists():
        for bruta in caminho.read_text(encoding="utf-8").splitlines():
            if not bruta.strip():
                continue
            try:
                d = json.loads(bruta)
            except json.JSONDecodeError:
                continue
            if release and str(d.get("release", "")) != release:
                continue
            fonte = str(d.get("fonte", "")).strip()
            sessao = str(d.get("sessao", "")).strip()
            if not fonte or not sessao:
                continue          # linha sem as duas identidades não conta para o §11
            lidas += 1
            sessoes.add(sessao)
            if sujeito := str(d.get("sujeito", "")).strip():
                sujeitos.add(sujeito)
            vistos.add(str(d.get("tool", "")))
            alvo = por_fonte[fonte]
            alvo["linhas"] += 1
            if d.get("hit") is True:
                alvo["hit"] += 1
            elif d.get("hit") is False:
                alvo["miss"] += 1
            if d.get("disjuntor") in ("aberto", True):
                alvo["disj"] += 1

    linhas_fonte = tuple(
        FonteAlcancada(fonte=f, linhas=v["linhas"], hit=v["hit"], miss=v["miss"],
                       disjuntor_aberto=v["disj"])
        for f, v in sorted(por_fonte.items())
    )

    fora = sorted(p for p in vistos if p and p not in produtores)
    motivos = []
    if fora:
        motivos.append(f"produtor sem paridade declarada: {', '.join(fora)}")
    motivos.append("`wiki-mcp` ainda não escreve neste esquema (#2316, F4, claudinho-TI)")
    if not sessoes_abertas:
        motivos.append("denominador não medido: a taxa sai como contagem")

    return Disparo(
        release=release, sessoes=len(sessoes), sujeitos=tuple(sorted(sujeitos)), linhas=lidas,
        sessoes_abertas=sessoes_abertas, por_fonte=linhas_fonte, parcial=True,
        motivo=" · ".join(motivos),
        fontes_ausentes=tuple(sorted({str(f) for f in Fonte} - set(por_fonte))),
    )


class SemDenominador(Exception):
    """Delta pedido entre séries que não têm denominador medido nas duas pontas."""


def delta(antes: Disparo, depois: Disparo) -> dict:
    """Delta de disparo entre duas releases — o que valida a escada D0–D4 (§13,
    experimento de degrau: D3 na abertura contra D2 na descrição da tool).

    Recusa quando falta denominador em qualquer das pontas: comparar contagem bruta de
    releases com número de sessões diferente é o erro que pareceria funcionar."""
    if antes.taxa is None or depois.taxa is None:
        raise SemDenominador(
            "delta exige denominador medido nas duas releases; sem ele há contagem, não taxa"
        )
    return {
        "antes": {"release": antes.release, "taxa": antes.taxa},
        "depois": {"release": depois.release, "taxa": depois.taxa},
        "delta": round(depois.taxa - antes.taxa, 4),
        "parcial": antes.parcial or depois.parcial,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="eixo 2 — taxa de disparo por release (§13)")
    p.add_argument("--trilha", default=None)
    p.add_argument("--release", default="")
    p.add_argument("--sessoes-abertas", type=int, default=None,
                   help="denominador; sem ele a taxa sai `—` e a contagem continua válida")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    s = serie_disparo(a.trilha, release=a.release, sessoes_abertas=a.sessoes_abertas)
    print(json.dumps(s.para_json(), ensure_ascii=False, indent=2) if a.json else s.para_texto())
