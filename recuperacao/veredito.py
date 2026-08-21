"""Veredito instrumentado (#2312, F3) — a série que o gate publica por fonte.

`spec_recuperador.md` §11 e §13. Fecha F3: *«série do veredito publicada»*.

## Instrumentar primeiro, não segurar por baseline

A série medida agora **é** o baseline (§13). Não se espera número anterior para começar a
gravar: a primeira release publicada vira a régua da segunda, e segurar a instrumentação
até haver com o que comparar é o jeito garantido de nunca ter com o que comparar.

## Uma linha por CHAVE julgada, não por chamada

O §11 manda uma linha por fonte alcançada na trilha de leitura. Aqui a unidade é outra e
de propósito: o que se julga é a chave citada, e um artefato cita N chaves da mesma fonte.
Agregar na escrita perderia qual chave foi recusada — que é exatamente o que o autor
precisa ler para consertar. As duas identidades do §11 continuam: `sujeito` e `sessao`.

## `estado` ausente vem declarado, nunca omitido

`veredito_por_conceito` está **desligado** (`motor rag ajuste`, 20/08: `veredito-por-conceito
false`), e ligá-lo é decisão de claudinho-dados com baseline off→on. Enquanto isso, a linha
sai com `estado: null` e `estado_medido: false` — campo faltando e campo nulo são
indistinguíveis para quem lê a série depois, e essa é a diferença entre número parcial
declarado e número errado.

## Parcialidade declarada, enquanto o wiki-mcp não tiver paridade

§11: o mesmo esquema tem de valer no `wiki-mcp` (F4, #2316, cadeira claudinho-TI).
Enquanto não valer, a série publica **dizendo que é parcial**, com as fontes cobertas
nomeadas. Série parcial anunciada como completa é o defeito que este campo impede.
"""

from __future__ import annotations

import datetime
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .fontes import Fonte
from .gate import Julgamento, Parecer, Veredito
from .resolvedor import le_chave

TRILHA = os.environ.get(
    "PF_REC_TRILHA", str(Path.home() / "AI" / "var" / "log" / "recuperacao" / "veredito.jsonl")
)

#: Produtores que já escrevem neste esquema. `wiki-mcp` entra em F4 (#2316, TI).
PRODUTORES_COM_PARIDADE = ("ops-mcp",)


def agora() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class LinhaVeredito:
    """Uma chave julgada. `sujeito` e `sessao` são as duas identidades do §11."""

    ts: str
    tool: str
    sujeito: str
    sessao: str
    fonte: str
    chave: str
    julgamento: str
    artefato: str = ""
    release: str = ""
    degrau: str | None = None
    estado: str | None = None
    estado_medido: bool = False

    def para_json(self) -> dict:
        return {
            "ts": self.ts, "tool": self.tool, "sujeito": self.sujeito, "sessao": self.sessao,
            "fonte": self.fonte, "chave": self.chave, "julgamento": self.julgamento,
            "artefato": self.artefato, "release": self.release,
            "degrau": self.degrau, "estado": self.estado, "estado_medido": self.estado_medido,
        }


def linha_de(v: Veredito, *, tool: str, sujeito: str, sessao: str,
             artefato: str = "", release: str = "", estado_medido: bool = False) -> LinhaVeredito:
    coord = v.coordenada
    return LinhaVeredito(
        ts=agora(), tool=tool, sujeito=sujeito, sessao=sessao,
        fonte=str(le_chave(v.chave).fonte), chave=v.chave, julgamento=str(v.julgamento),
        artefato=artefato, release=release,
        degrau=str(coord.degrau) if coord else None,
        estado=str(coord.estado) if (coord and coord.estado and estado_medido) else None,
        estado_medido=estado_medido,
    )


def instrumenta(parecer: Parecer, *, tool: str, sujeito: str, sessao: str,
                artefato: str = "", release: str = "", trilha: str | None = None,
                estado_medido: bool = False) -> list[LinhaVeredito]:
    """Grava a trilha e devolve as linhas. Sem sujeito ou sem sessão não grava: linha
    sem as duas identidades não serve ao §11 e polui a série."""
    if not str(sujeito).strip() or not str(sessao).strip():
        raise ValueError("linha sem sujeito e sessão não é auditoria ciente de delegação (§11)")
    linhas = [
        linha_de(v, tool=tool, sujeito=sujeito, sessao=sessao, artefato=artefato,
                 release=release, estado_medido=estado_medido)
        for v in parecer.vereditos
    ]
    destino = Path(trilha or TRILHA)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as f:
        for linha in linhas:
            f.write(json.dumps(linha.para_json(), ensure_ascii=False) + "\n")
    return linhas


# ------------------------------------------------------------------- a série

@dataclass(frozen=True, slots=True)
class SerieFonte:
    fonte: str
    citavel: int = 0
    aposentada: int = 0
    fabricada: int = 0

    @property
    def total(self) -> int:
        return self.citavel + self.aposentada + self.fabricada

    @property
    def taxa_recusa(self) -> float | None:
        """`None` quando não há caso: 0,0 com denominador zero é número inventado."""
        return None if not self.total else round(self.fabricada / self.total, 4)

    def para_json(self) -> dict:
        return {
            "fonte": self.fonte, "total": self.total, "citavel": self.citavel,
            "aposentada": self.aposentada, "fabricada": self.fabricada,
            "taxa_recusa": self.taxa_recusa,
        }


@dataclass(frozen=True, slots=True)
class Serie:
    por_fonte: tuple[SerieFonte, ...]
    release: str = ""
    parcial: bool = True
    motivo: str = ""
    estado_medido: bool = False
    linhas: int = 0
    fontes_ausentes: tuple[str, ...] = field(default_factory=tuple)

    def para_json(self) -> dict:
        return {
            "release": self.release,
            "linhas": self.linhas,
            "parcial": self.parcial,
            "motivo": self.motivo,
            "estado_medido": self.estado_medido,
            "fontes_ausentes": list(self.fontes_ausentes),
            "por_fonte": [s.para_json() for s in self.por_fonte],
        }

    def para_texto(self) -> str:
        cab = f"veredito · release {self.release or '(sem release)'} · {self.linhas} linhas"
        if self.parcial:
            cab += f"\nPARCIAL — {self.motivo}"
        corpo = [
            f"  {s.fonte:<9} {s.total:>5}  citável {s.citavel:>5}  aposentada {s.aposentada:>4}"
            f"  fabricada {s.fabricada:>4}  recusa "
            + ("—" if s.taxa_recusa is None else f"{s.taxa_recusa:.2%}")
            for s in self.por_fonte
        ]
        return "\n".join([cab, *corpo])


_JULGAMENTO = {
    str(Julgamento.CITAVEL): "citavel",
    str(Julgamento.APOSENTADA): "aposentada",
    str(Julgamento.FABRICADA): "fabricada",
}


def serie(trilha: str | None = None, *, release: str = "",
          produtores: tuple[str, ...] = PRODUTORES_COM_PARIDADE) -> Serie:
    """Lê a trilha JSONL e publica a série por fonte, com a parcialidade declarada.

    Linha malformada não derruba a série e não some: entra na contagem de `linhas`
    apenas quando é legível, e a diferença fica visível contra o arquivo."""
    caminho = Path(trilha or TRILHA)
    contagens: dict[str, Counter] = {}
    vistos_produtores: set[str] = set()
    estado_medido = False
    lidas = 0

    if caminho.exists():
        for bruta in caminho.read_text(encoding="utf-8").splitlines():
            if not bruta.strip():
                continue
            try:
                d = json.loads(bruta)
            except json.JSONDecodeError:
                continue
            if release and d.get("release", "") != release:
                continue
            julg = _JULGAMENTO.get(str(d.get("julgamento")))
            if julg is None:
                continue
            lidas += 1
            contagens.setdefault(str(d.get("fonte")), Counter())[julg] += 1
            vistos_produtores.add(str(d.get("tool", "")))
            estado_medido = estado_medido or bool(d.get("estado_medido"))

    por_fonte = tuple(
        SerieFonte(fonte=f, citavel=c["citavel"], aposentada=c["aposentada"],
                   fabricada=c["fabricada"])
        for f, c in sorted(contagens.items())
    )
    ausentes = tuple(sorted({str(f) for f in Fonte} - set(contagens)))

    fora = sorted(p for p in vistos_produtores if p and p not in produtores)
    motivos = []
    if fora:
        motivos.append(f"produtor sem paridade de esquema declarada: {', '.join(fora)}")
    motivos.append("`wiki-mcp` ainda não escreve neste esquema (#2316, F4, claudinho-TI)")
    if not estado_medido:
        motivos.append("`veredito_por_conceito` desligado: `estado` não medido")

    return Serie(
        por_fonte=por_fonte, release=release, parcial=True, motivo=" · ".join(motivos),
        estado_medido=estado_medido, linhas=lidas, fontes_ausentes=ausentes,
    )


if __name__ == "__main__":  # bancada, não verbo de `bin/`
    import argparse

    p = argparse.ArgumentParser(description="publica a série do veredito (§13, eixo 2)")
    p.add_argument("--trilha", default=None)
    p.add_argument("--release", default="")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    s = serie(a.trilha, release=a.release)
    print(json.dumps(s.para_json(), ensure_ascii=False, indent=2) if a.json else s.para_texto())
