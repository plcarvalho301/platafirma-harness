"""Roteador de chapéu — responde "qual chapéu?" DENTRO da montagem (P2, recursão).

Este módulo é o passo 2 do `monta-sessao`: entre a identidade (Chamada 1 do P2) e o
chapéu servido (Chamada 2). Ele existe apartado do montador de propósito — a desconfiança
do dono é sobre o fluxo, e fluxo que não se testa isolado não se confia. `casa()` e
`decide()` são funções puras: entram texto + tabela, sai slug ou `None`, sem I/O.

## A pilha, na ordem de disparo (validada 22/08)

- **(a) determinístico** — `decide()`: o rótulo canônico aparece inteiro na pergunta ->
  conta acertos por bloco -> um bloco vence com margem -> o slug dele. É curto-circuito: casou
  com folga, nem chama (b). Fonte dos conceitos: o golden record `acervo.conceito`
  (verbo `acervo listar conceitos`); a tabela de rotas por cadeira e GERADA dele.
  `conceitos.json` foi aposentado como fonte (decisao P2, 22/08) e nao existe em disco.
- **(b) semantico** — `roteia_semantico()`: embedding da pergunta x banco de cenarios (a
  secao (a) de cada chapeu), maximo-sobre-exemplos, limiar + margem. HOJE devolve `None` com
  motivo declarado: nao ha `/embed` no motor servido, e carregar o embedder (~2,4 GB, ~25 s
  a frio) por montagem e proibido. A costura existe; a peca entra quando o endpoint existir.
- **(c) fallback** — nao e codigo deste modulo: e o `None` propagando. O montador, recebendo
  `None`, devolve a identidade + a pergunta "qual chapeu?" — o P2 como esta escrito. Vira a
  minoria medida, nao o caminho.

## Por que margem, nao so maximo

`decide()` exige que o bloco vencedor tenha ESTRITAMENTE mais acertos que o segundo. Maximo
sozinho decide na moeda quando dois blocos empatam, e decidir errado o chapeu e pior que cair
no fallback: o especialista errado responde com a confianca do certo. Empate -> `None` -> (c).

## O que NAO entra aqui

Selecao de CADEIRA (o "abre como TI" do dono) nao e deste modulo — e anterior, e ja resolvida
antes de `monta()`. Aqui a cadeira ja esta fixada; a decisao e so qual dos chapeus DELA vestir.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass

# Limiar/margem de (b): carregados quando o endpoint existir. Ficam nomeados aqui para a
# calibracao ter um lugar, nao espalhada. Sem turno logado, nascem conservadores.
LIMIAR_SEMANTICO = 0.55   # abaixo -> None -> fallback (c)
MARGEM_SEMANTICA = 0.05   # 1o e 2o colados -> None: ambiguidade e sinal, nao moeda


@dataclass(frozen=True, slots=True)
class Rota:
    """Um chapeu candidato: o slug e os rotulos que o disparam (gerados do golden record `acervo.conceito`)."""

    slug: str
    rotulos: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Decisao:
    """O que o roteador decidiu, e por qual via. `slug=None` e o fallback (c)."""

    slug: str | None
    via: str                       # "comando" | "deterministico" | "semantico" | "fallback"
    motivo: str = ""
    acertos: dict | None = None    # bloco -> no de rotulos casados, para o envelope declarar


def _normaliza(texto: str) -> str:
    """Sem acento, sem pontuacao, sem o `s` de plural. Mesma regua do motor (`conceitos.py`),
    reescrita aqui para nao acoplar o montador ao processo do RAG: o plural muda o casamento
    ("gestao de risco" vs "gestao de riscos") e ignora-lo devolve zero em conceito que existe."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto or "")
                         if unicodedata.category(c) != "Mn")
    limpo = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()
    return re.sub(r"\b(\w{3,}?)s\b", r"\1", limpo)


def rotas_do_disco(cadeira: str, raiz_chapeus: str) -> list[Rota]:
    """As rotas da cadeira: um bloco POR chapeu que existe no disco, gerado do golden record `acervo.conceito`.

    Bloco sem chapeu correspondente (ex.: `inferencia`, que e MODO e nao tem `.md`) NAO vira
    rota — rotear para um chapeu inexistente e o erro que `serve_chapeu` pegaria tarde. Cadeira
    sem tabela gerada devolve lista vazia: o roteador cai em (c) inteiro, declarado.
    `conceitos.json` foi aposentado (P2, 22/08); o leitor abaixo ainda procura o caminho
    aposentado, e a troca pela tabela gerada e a retirada rastreada em tombamento.
    """
    base = os.path.join(raiz_chapeus, cadeira)
    caminho = os.path.join(base, "conceitos.json")  # aposentado (P2); ausente -> [] -> (c)
    if not os.path.isfile(caminho):
        return []
    try:
        blocos = json.load(open(caminho, encoding="utf-8")).get("blocos", {})
    except (OSError, json.JSONDecodeError):
        return []
    no_disco = {n[:-3] for n in os.listdir(base) if n.endswith(".md")}
    rotas: list[Rota] = []
    for slug, verbetes in blocos.items():
        if slug not in no_disco:
            continue
        rotulos: list[str] = []
        for v in verbetes:
            rotulos.append(v.get("rotulo", ""))
            alt = v.get("outros_rotulos") or ""
            # `outros_rotulos` vem como string separada por "/" no gerador atual
            rotulos.extend(p.strip() for p in re.split(r"[/;]", alt) if p.strip())
        rotas.append(Rota(slug=slug, rotulos=tuple(r for r in rotulos if r)))
    return rotas


def casa(pergunta: str, rotas: list[Rota]) -> dict[str, int]:
    """Acertos por slug: quantos rotulos da rota aparecem INTEIROS na pergunta, em fronteira
    de palavra. Funcao pura. Lexico e conservador, igual ao `casar()` do motor — o vetor casa
    aproximacao em (b); aqui o que vale e a relacao declarada, nao a semelhanca."""
    alvo = f" {_normaliza(pergunta)} "
    acertos: dict[str, int] = {}
    for rota in rotas:
        n = 0
        vistos: set[str] = set()
        for rotulo in rota.rotulos:
            norm = _normaliza(rotulo)
            if len(norm) >= 3 and norm not in vistos and f" {norm} " in alvo:
                vistos.add(norm)
                n += 1
        if n:
            acertos[rota.slug] = n
    return acertos


def decide(pergunta: str, rotas: list[Rota]) -> Decisao:
    """(a) deterministico. Vencedor por margem estrita, senao `None`. Funcao pura."""
    acertos = casa(pergunta, rotas)
    if not acertos:
        return Decisao(slug=None, via="fallback",
                       motivo="nenhum rotulo canonico casou na pergunta", acertos={})
    ordenado = sorted(acertos.items(), key=lambda kv: kv[1], reverse=True)
    (slug1, n1) = ordenado[0]
    n2 = ordenado[1][1] if len(ordenado) > 1 else 0
    if n1 > n2:
        return Decisao(slug=slug1, via="deterministico",
                       motivo=f"{slug1}: {n1} rotulos vs {n2} do 2o", acertos=acertos)
    return Decisao(slug=None, via="fallback",
                   motivo=f"empate em {n1}: ambiguidade vira pergunta ao modelo", acertos=acertos)


def roteia_semantico(pergunta: str, rotas: list[Rota]) -> Decisao:
    """(b) semantico. Costura declarada: sem `/embed` no motor servido, devolve `None` — nao
    finge. Quando o endpoint existir, aqui entram embed(pergunta) x cenarios, maximo, limiar."""
    return Decisao(slug=None, via="fallback",
                   motivo="roteador semantico inativo: sem endpoint /embed no motor servido "
                          "(carregar o embedder por montagem e proibido — ~2,4 GB, ~25 s)")


def escolhe(pergunta: str | None, cadeira: str, raiz_chapeus: str,
            forcado: str | None = None) -> Decisao:
    """O ponto unico que o montador chama. Ordem: comando explicito -> (a) -> (b) -> (c).

    `forcado` e o `--chapeu <slug>` / comando do dono ja resolvido: vence tudo, sem roteamento.
    `pergunta` vazia (abertura sem turno, ex.: claude.ai antes do 1o prompt) -> direto ao
    fallback, porque nao ha sinal para rotear e chutar chapeu e pior que perguntar.
    """
    rotas = rotas_do_disco(cadeira, raiz_chapeus)
    validos = {r.slug for r in rotas}

    if forcado:
        if not validos or forcado in validos:
            return Decisao(slug=forcado, via="comando", motivo="chapeu forcado")
        return Decisao(slug=None, via="fallback",
                       motivo=f"chapeu forcado '{forcado}' nao existe; validos: {sorted(validos)}")

    if not (pergunta or "").strip():
        return Decisao(slug=None, via="fallback", motivo="sem pergunta: nada para rotear")
    if not rotas:
        return Decisao(slug=None, via="fallback",
                       motivo=f"cadeira '{cadeira}' sem tabela de rotas gerada (golden record acervo.conceito)")

    d = decide(pergunta, rotas)
    if d.slug:
        return d
    s = roteia_semantico(pergunta, rotas)
    if s.slug:
        return s
    # (c): propaga o motivo mais informativo entre deterministico e semantico
    return Decisao(slug=None, via="fallback", motivo=d.motivo, acertos=d.acertos)


if __name__ == "__main__":  # bancada: rota isolada, sem montar sessao
    import sys
    cad = sys.argv[1] if len(sys.argv) > 1 else "IA"
    perg = sys.argv[2] if len(sys.argv) > 2 else "orcamento de janela de contexto"
    raiz = os.path.join(os.environ.get("PF_RAIZ", os.path.expanduser("~/AI")),
                        "platafirma-harness", "abertura")
    dec = escolhe(perg, cad, raiz)
    print(json.dumps({"slug": dec.slug, "via": dec.via, "motivo": dec.motivo,
                      "acertos": dec.acertos}, ensure_ascii=False, indent=2))
