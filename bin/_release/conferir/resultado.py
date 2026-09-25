#!/usr/bin/env python3
"""resultado — o veredito comum de `conferir`: 3 estados, uma ancora, um exit.

arq:0110 par.4 da a tabela de exit geral de todo verbo da casa (0..5). `release
conferir <classe>` e um caso particular: cada classe devolve uma LISTA de itens, cada
item com um veredito de 3 estados (conforme/divergente/indeterminavel), e o exit da
chamada agrega a lista — nao e o exit de um unico ato, e o pior caso da lista:

    0  tudo conforme
    1  ha pelo menos um divergente (divergente pesa mais que indeterminavel: nao
       conseguir olhar nao pode mascarar uma divergencia real)
    5  nenhum divergente, e ao menos um indeterminavel

Nao conseguir olhar nunca sai conforme — por isso Veredito recusa `indeterminavel`
sem motivo, e a construcao de `conforme` nao aceita motivo (motivo em item conforme
e ruido: se precisa explicar, nao e conforme sem ressalva).
"""
import json

ESTADOS = ("conforme", "divergente", "indeterminavel")


class Veredito:
    __slots__ = ("estado", "desde", "motivo")

    def __init__(self, estado, desde=None, motivo=None):
        if estado not in ESTADOS:
            raise ValueError(f"estado invalido: {estado!r} (esperado um de {ESTADOS})")
        if estado != "conforme" and not motivo:
            raise ValueError(f"estado {estado!r} exige motivo")
        self.estado = estado
        self.desde = desde
        self.motivo = motivo

    def dict(self):
        return {
            "estado": self.estado,
            "desde": self.desde if self.desde else "indeterminavel",
            "motivo": self.motivo,
        }

    def __repr__(self):
        return f"Veredito({self.estado!r}, desde={self.desde!r}, motivo={self.motivo!r})"


def conforme(desde=None):
    return Veredito("conforme", desde=desde)


def divergente(motivo, desde=None):
    return Veredito("divergente", desde=desde, motivo=motivo)


def indeterminavel(motivo, desde=None):
    return Veredito("indeterminavel", desde=desde, motivo=motivo)


def agrega(itens):
    """(exit, n_conforme, n_divergente, n_indeterminavel) a partir de [(nome, Veredito), ...]."""
    n_conforme = sum(1 for _, v in itens if v.estado == "conforme")
    n_divergente = sum(1 for _, v in itens if v.estado == "divergente")
    n_indeterminavel = sum(1 for _, v in itens if v.estado == "indeterminavel")
    if n_divergente:
        exit_code = 1
    elif n_indeterminavel:
        exit_code = 5
    else:
        exit_code = 0
    return exit_code, n_conforme, n_divergente, n_indeterminavel


def linha_ancora(classe, alvo, itens, sha_release):
    """A 1a linha do texto, colavel como ancora: ver arq:0110 (gramatica) e o card #3142."""
    exit_code, n_c, n_d, n_i = agrega(itens)
    alvo_str = f" {alvo}" if alvo else ""
    linha = (f"release conferir {classe}{alvo_str}: {n_c} conforme · {n_d} divergente · "
             f"{n_i} não consegui olhar — release {sha_release}")
    return linha, exit_code


def relatorio(classe, alvo, itens, sha_release, como_json=False):
    """Imprime o relatorio (texto ou --json) e devolve o exit code.

    `itens`: lista de (nome, Veredito). Texto: ancora + uma linha por item, com motivo
    quando nao-conforme. JSON: {"ancora", "classe", "alvo", "release", "itens": [...]}."""
    linha, exit_code = linha_ancora(classe, alvo, itens, sha_release)
    if como_json:
        print(json.dumps({
            "ancora": linha,
            "classe": classe,
            "alvo": alvo,
            "release": sha_release,
            "itens": [{"nome": nome, **v.dict()} for nome, v in itens],
        }, ensure_ascii=False))
        return exit_code
    print(linha)
    for nome, v in itens:
        marca = {"conforme": "ok ", "divergente": "NAO", "indeterminavel": "?? "}[v.estado]
        desde = f" (desde {v.desde})" if v.desde else ""
        print(f"    {marca} {nome}{desde}")
        if v.motivo:
            print(f"        {v.motivo}")
    return exit_code
