"""Gerador de gold das fontes exatas (#2309) — um só, parametrizado.

`spec_recuperador.md` §13: *«Gerador de gold para fonte exata: um só, parametrizado — lê o
estado, emite pares (predicado → resposta exata). Roda por fonte.»* Cargo e acervo são de
claudinho-dados e não saem daqui.

Schema emitido, o do §13, uma linha JSON por caso:

```
{ id, fonte, classe, entrada, esperado: [ {chave, coordenada?} ],
  resposta_certa: item|vazia|ausente, casamento_esperado?, origem, pontuavel }
```

**Por que isto existe:** sem gold, toda fonte serve `nao-calibrada` (§13), e é o rótulo
honesto do instrumento desligado. `tem_gold` vira `True` por fonte quando o gold dela
existir e for revisado — não quando este gerador rodar.

## O que o gerador pode afirmar sozinho, e o que ele não pode

O gerador lê o estado PELA fonte e emite três classes de caso. Elas não têm o mesmo peso
de prova, e por isso não saem com o mesmo `pontuavel`:

| classe | esperado vem de | `pontuavel` |
|---|---|---|
| `chave-exata` | do ESTADO: a chave existe, logo resolvê-la tem de devolver ela mesma | `true` |
| `chave-inexistente` | do ESTADO: a chave está fora do estado, logo a resposta certa é `vazia` | `true` |
| `termo` | do próprio mecanismo que será medido | `false` até revisão humana |

**O caso `termo` sai despontuável de propósito.** Derivar o esperado do mesmo caminho que
o gold vai julgar é escrever o gabarito com a prova aberta: mudança no recorte por termo
viraria linha nova nos dois lados, sem alarme. É a mesma disciplina da matriz
sujeito × fonte, que é escrita à mão pelo mesmo motivo. Ele é emitido mesmo assim porque
revisar candidato é barato e inventar caso do zero é caro — mas quem o torna pontuável é
uma pessoa, editando o campo.

**`resposta_certa: ausente` não é gerável.** `vazia` é «a fonte respondeu e não há o que
casar»; `ausente` é «a fonte não cobre este assunto», que é juízo sobre o corpus, não
sobre o estado. O §13 já o atribui a gabarito de autor, claudinho-IA, e é onde ele fica.

**O gold congela por versão (§13):** `origem` carrega a fonte, o carimbo da fonte na hora
da geração e a data. Valor absoluto não se interpreta; comparação só vale sobre o mesmo
carimbo.

## Uso

```
python -m recuperacao.gold --fonte board --saida avaliacao/gold-board.jsonl
python -m recuperacao.gold --fonte registro --casos 40 --sem-termo
python -m recuperacao.gold --fonte board fila mesa registro --saida-dir avaliacao/
```

Não vira verbo em `bin/` por ora: é bancada de medição, roda por ato meu, e verbo novo
pede linha no `tool-manifest` (dono claudinho-TI) no mesmo commit.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

from .adaptadores import (
    AdaptadorBoard,
    AdaptadorFila,
    AdaptadorMesa,
    AdaptadorRegistro,
    AdaptadorWiki,
)
from .adaptadores.base import Adaptador
from .fontes import CLASSE, Classe, Fonte

# As exatas que são minhas de ponta a ponta. `wiki` entra pelo caminho NOMINAL
# (`prop=revisions`); o gold de Cargo e o do acervo são de claudinho-dados (§13).
ADAPTADORES: dict[str, type[Adaptador]] = {
    "board": AdaptadorBoard,
    "fila": AdaptadorFila,
    "mesa": AdaptadorMesa,
    "registro": AdaptadorRegistro,
    "wiki": AdaptadorWiki,
}

# Alvo de listagem por fonte: o que faz a fonte devolver estado, não um item só.
#
# A wiki é a única que precisa de SEMENTE, e o motivo está no adaptador: o caminho
# nominal resolve um título e o caminho de prosa é `list=search`, que sem termo devolve
# vazio — não há `list=allpages` exposto ali. A semente enviesa a AMOSTRA (quais páginas
# entram), nunca o gabarito: o esperado de cada caso continua vindo do estado, e é por
# isso que o viés é aceitável e fica declarado aqui em vez de escondido no default.
ALVO_LISTAGEM: dict[str, tuple[str, dict]] = {
    "board": ("", {}),
    "fila": (os.environ.get("PF_CADEIRA", "ia"), {}),
    "mesa": ("", {}),
    "registro": ("", {}),
    "wiki": ("PlataFirma", {}),
}

# Chave fora do estado, por fonte. Não é aleatória: tem de ser bem formada, ou o caso
# mediria o parser de alvo em vez de medir a resolução.
CHAVE_FORA: dict[str, str] = {
    "board": "item:99999999",
    "fila": "caixa:ia/1-0",
    "mesa": "mem:ia:inexistente#0",
    "registro": "adr:9999",
    "wiki": "wiki:PáginaQueNãoExiste_9999",
}

PALAVRA = re.compile(r"[0-9A-Za-zÀ-ÿ]{5,}")
PARADAS = {"claudinho", "claudinha", "platafirma", "item", "card", "para", "pelo", "pela",
           "como", "quando", "sobre", "nivel", "story", "task", "feature", "epico"}


class SemEstado(Exception):
    """A fonte não devolveu estado. Gold vazio é pior que gold ausente: parece medido."""


def _carimbo(a: Adaptador, resultado=None) -> str:
    """O carimbo da BUSCA que gerou os casos, não uma segunda chamada.

    Medido em 20/08/2026: `AdaptadorFila._carimbo()` sem alvo devolve `0-0` por desenho —
    o carimbo da fila é por stream, e sem caixa não há stream a carimbar. Chamá-lo de novo
    aqui carimbava 41 casos da caixa de claudinho-IA com `0-0`, e gold que declara versão
    falsa é pior que gold sem versão: os dois lados da comparação parecem a mesma coleção.
    """
    if resultado is not None and resultado.linha.carimbo:
        return str(resultado.linha.carimbo)
    try:
        return a._carimbo()
    except Exception:  # noqa: BLE001
        return "sem-carimbo"


def _origem(fonte: str, carimbo: str) -> str:
    hoje = datetime.date.today().isoformat()
    return f"gerador:{fonte}@{carimbo} · {hoje} · auto-derivado do estado; sem validacao humana"


def _termo_de(texto: str) -> str | None:
    """Uma palavra distintiva do rótulo do item, para o caso de recorte por termo."""
    for p in PALAVRA.findall(texto or ""):
        if p.lower() not in PARADAS and not p.isdigit():
            return p
    return None


def _rotulo(item) -> str:
    return item.ref or (item.conteudo or "")[:200]


def gera(fonte: str, adaptador: Adaptador | None = None, casos: int = 20,
         com_termo: bool = True, semente: str | None = None) -> list[dict]:
    """Lê o estado pela fonte e emite os casos do §13. Não escreve arquivo."""
    fonte = str(fonte)
    if fonte not in ADAPTADORES:
        raise SemEstado(f"fonte sem gerador aqui: {fonte} (Cargo e acervo são de claudinho-dados)")
    a = adaptador or ADAPTADORES[fonte]()
    classe = CLASSE[Fonte(fonte)]
    if classe is not Classe.EXATA:
        raise SemEstado(f"{fonte} não é classe exata; este gerador é só das exatas (§13)")

    alvo, filtros = ALVO_LISTAGEM.get(fonte, ("", {}))
    if semente is not None:
        alvo = semente
    r = a.busca_declarada(alvo, filtros or None, k=max(casos, 1), texto="nenhum")
    if not r.itens:
        raise SemEstado(f"{fonte} não devolveu estado ({r.linha.cobertura}"
                        f"{'/' + str(r.linha.causa) if r.linha.causa else ''})")

    carimbo = _carimbo(a, r)
    origem = _origem(fonte, carimbo)
    saida: list[dict] = []

    # 1. chave exata — resolver uma chave do estado devolve ela mesma.
    for n, item in enumerate(r.itens[:casos], 1):
        chave = item.procedencia.chave
        saida.append({
            "id": f"{fonte}-chave-{n:03d}",
            "fonte": fonte,
            "classe": str(classe),
            "entrada": chave,
            "esperado": [{"chave": chave}],
            "resposta_certa": "item",
            "casamento_esperado": "exato",
            "origem": origem,
            "pontuavel": True,
        })

    # 2. chave inexistente — a fonte responde, e a resposta certa é `vazia`.
    fora = CHAVE_FORA.get(fonte)
    if fora and fora not in {i.procedencia.chave for i in r.itens}:
        saida.append({
            "id": f"{fonte}-vazia-001",
            "fonte": fonte,
            "classe": str(classe),
            "entrada": fora,
            "esperado": [],
            "resposta_certa": "vazia",
            "origem": origem,
            "pontuavel": True,
        })

    # 3. termo — candidato, despontuável até revisão humana.
    if com_termo:
        for n, item in enumerate(r.itens[:casos], 1):
            termo = _termo_de(_rotulo(item))
            if not termo:
                continue
            saida.append({
                "id": f"{fonte}-termo-{n:03d}",
                "fonte": fonte,
                "classe": str(classe),
                "entrada": termo,
                "esperado": [{"chave": item.procedencia.chave}],
                "resposta_certa": "item",
                "origem": origem + " · CANDIDATO: esperado derivado do mecanismo medido;"
                                  " pontuavel=false ate revisao humana",
                "pontuavel": False,
            })

    return saida


def escreve(casos: list[dict], caminho: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        for c in casos:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    return caminho


def resumo(casos: list[dict]) -> dict:
    return {
        "total": len(casos),
        "pontuaveis": sum(1 for c in casos if c["pontuavel"]),
        "candidatos": sum(1 for c in casos if not c["pontuavel"]),
        "por_resposta_certa": {
            r: sum(1 for c in casos if c["resposta_certa"] == r)
            for r in sorted({c["resposta_certa"] for c in casos})
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="recuperacao.gold", description=__doc__.split("\n")[0])
    p.add_argument("--fonte", nargs="+", required=True, choices=sorted(ADAPTADORES))
    p.add_argument("--casos", type=int, default=20)
    p.add_argument("--sem-termo", action="store_true")
    p.add_argument("--semente", help="alvo de listagem, quando a fonte precisa de um (wiki)")
    p.add_argument("--saida", help="arquivo (só com uma fonte)")
    p.add_argument("--saida-dir", help="diretório; um `gold-<fonte>.jsonl` por fonte")
    a = p.parse_args(argv)

    if a.saida and len(a.fonte) > 1:
        p.error("--saida vale para uma fonte; use --saida-dir")

    codigo = 0
    for fonte in a.fonte:
        try:
            casos = gera(fonte, casos=a.casos, com_termo=not a.sem_termo,
                         semente=a.semente)
        except SemEstado as e:
            # Falha declarada por fonte, e as outras continuam: fonte fora do ar não pode
            # apagar o gold das que responderam.
            print(f"{fonte}: SEM GOLD — {e}", file=sys.stderr)
            codigo = 1
            continue
        destino = a.saida or os.path.join(a.saida_dir or "avaliacao", f"gold-{fonte}.jsonl")
        escreve(casos, destino)
        print(f"{fonte}: {json.dumps(resumo(casos), ensure_ascii=False)} → {destino}")
    return codigo


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
