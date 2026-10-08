"""Calibração do sinal de abstenção sobre medições salvas (card #3264, passo 6c; arq:0121 §7.3).

`motor rag medir <particao> --calibrar <controle>[,<rodada>…]` lê as medições que a bateria salvou,
uma por rodada (similaridade, revisor, veredito por conceito), e diz, por sinal, o piso e o que ele
custa. Não chama a API: a conta é sobre o valor cru que cada pergunta devolveu.

O critério é o do dono (07/10/2026): vence o sinal que abstém mais das 22 negativas sem obra sem perder
positiva T2 contra a rodada de similaridade da mesma geração. Em números:

1. A rodada de CONTROLE (a primeira) é a similaridade. O piso dela é o que minimiza o erro total
   (positiva T2 que a busca achou e o piso cala + negativa sem obra que o piso serve), e a perda de T2 que
   ela paga nesse piso é o ORÇAMENTO de perda de todas as rodadas. Com menos T2 achadas do que negativas
   o mínimo degenera em calar tudo e o orçamento fica largo: a calibração mostra o orçamento ao lado do
   total de T2 para quem lê ver isso.
2. Cada rodada varre os pisos que seus valores deixam e fica com o que abstém mais negativas sem obra
   dentro desse orçamento; no empate, o menor piso (o que abstém menos).
3. As cinco negativas que ganharam obra no acervo reformado saem à parte: abster nelas é erro, e a conta
   as mostra, nunca as soma às 22.
4. Nenhuma rodada no mínimo de 16 das 22: a partição não vira, e o número vai ao dono.
5. Empate entre rodadas: vence a primeira na ordem em que foram listadas (liste da mais barata à mais cara:
   a similaridade custa nada na consulta, o veredito por conceito também, o revisor custa ~325 ms e ~1,1 GiB).

O piso devolvido é a menor nota que a rodada ainda serve (abstém quem está ABAIXO dele), arredondada a 3
casas como a API devolve.

Linha de pergunta (a que `cmd_medir` salva em `perguntas`): `grupo` (`neg_sem_obra`, `neg_com_obra`, `t2`,
`pos`), `valor` (nota crua do sinal; `None` se a busca voltou vazia), `cobertura` (rótulo da API) e
`veredito` (estado do veredito por conceito, quando a rodada o liga).
"""

from __future__ import annotations

import math

MINIMO_NEGATIVAS = 16


def abstem(linha: dict, piso: float) -> bool:
    """A pergunta sai como «sem cobertura» neste piso: busca vazia, conceito declarado sem obra (veredito
    por conceito, rodada que o liga) ou nota crua abaixo do piso."""
    if linha.get("cobertura") in ("vazia", "ausente", "nenhuma", "sem-indice"):
        return True
    if linha.get("veredito") == "sem_obra":
        return True
    if linha.get("medida") == "codigo_exato":  # achou pelo codigo: sem nota crua, e nao e falta de cobertura
        return False
    valor = linha.get("valor")
    return valor is None or valor < piso


def _conta(linhas: list[dict], grupo: str, piso: float) -> tuple[int, int]:
    do_grupo = [x for x in linhas if x.get("grupo") == grupo]
    if grupo == "t2":
        # Perder positiva T2 e abster numa que a busca ACHOU (tem `rank`): abster numa que ela errou nao
        # tira nada de quem pergunta. Linha sem a chave `rank` conta (medicao que nao a guardou).
        do_grupo = [x for x in do_grupo if x.get("rank", 0) is not None]
    return sum(1 for x in do_grupo if abstem(x, piso)), len(do_grupo)


def _candidatos(linhas: list[dict]) -> list[float]:
    valores = sorted({x["valor"] for x in linhas if x.get("valor") is not None})
    if not valores:
        return [0.0]
    # abstém quem está ABAIXO do piso: o piso logo acima do maior valor abstém todos
    return valores + [round(valores[-1] + 0.001, 6)]


def piso_de_controle(linhas: list[dict]) -> dict:
    """O piso que minimiza o erro total da similaridade: T2 positiva abstida + negativa sem obra servida."""
    melhor = None
    for t in _candidatos(linhas):
        pos, n_pos = _conta(linhas, "t2", t)
        neg, n_neg = _conta(linhas, "neg_sem_obra", t)
        erro = pos + (n_neg - neg)
        if melhor is None or erro < melhor["erro"]:
            melhor = {"piso": t, "erro": erro, "t2_abstidas": pos, "neg_sem_obra": neg}
    return melhor or {"piso": 0.0, "erro": 0, "t2_abstidas": 0, "neg_sem_obra": 0}


def calibrar_rodada(linhas: list[dict], orcamento_t2: int) -> dict:
    """O melhor piso desta rodada dentro do orçamento de perda de T2."""
    melhor = None
    for t in _candidatos(linhas):
        pos, n_pos = _conta(linhas, "t2", t)
        if pos > orcamento_t2:
            continue
        neg, n_neg = _conta(linhas, "neg_sem_obra", t)
        if melhor is None or neg > melhor["neg_sem_obra"]:
            com_obra, n_com = _conta(linhas, "neg_com_obra", t)
            melhor = {"piso": t, "neg_sem_obra": neg, "de_neg_sem_obra": n_neg, "t2_abstidas": pos,
                      "de_t2": n_pos, "neg_com_obra_abstidas": com_obra, "de_neg_com_obra": n_com}
    if melhor is None:  # nem o piso mais baixo cabe no orçamento (rodada que abstém T2 sem piso)
        t = min(_candidatos(linhas))
        pos, n_pos = _conta(linhas, "t2", t)
        neg, n_neg = _conta(linhas, "neg_sem_obra", t)
        com_obra, n_com = _conta(linhas, "neg_com_obra", t)
        melhor = {"piso": t, "neg_sem_obra": neg, "de_neg_sem_obra": n_neg, "t2_abstidas": pos,
                  "de_t2": n_pos, "neg_com_obra_abstidas": com_obra, "de_neg_com_obra": n_com,
                  "fora_do_orcamento": True}
    melhor["piso"] = _arredonda_para_baixo(melhor["piso"])
    return melhor


def _arredonda_para_baixo(valor: float, casas: int = 3) -> float:
    # `int(0.583 * 1000)` e 582: o produto em ponto flutuante cai um ulp abaixo. Arredondar o produto a 6
    # casas antes de cortar mantem o piso no valor que a API devolveu (ela arredonda a 3 casas).
    fator = 10 ** casas
    return math.floor(round(valor * fator, 6)) / fator


def calibrar(rodadas: dict[str, list[dict]], controle: str) -> dict:
    """`rodadas` = {rotulo: linhas}; `controle` = o rótulo da rodada de similaridade."""
    if controle not in rodadas:
        raise KeyError(controle)
    base = piso_de_controle(rodadas[controle])
    orcamento = base["t2_abstidas"]
    saida = {"controle": controle, "orcamento_t2": orcamento, "piso_do_controle": _arredonda_para_baixo(base["piso"]),
             "rodadas": {}}
    for nome, linhas in rodadas.items():
        saida["rodadas"][nome] = calibrar_rodada(linhas, orcamento)
    elegiveis = {n: r for n, r in saida["rodadas"].items() if not r.get("fora_do_orcamento")}
    vencedora = max(elegiveis, key=lambda n: elegiveis[n]["neg_sem_obra"]) if elegiveis else None
    saida["vencedora"] = vencedora
    saida["minimo"] = MINIMO_NEGATIVAS
    saida["atinge_o_minimo"] = bool(vencedora and elegiveis[vencedora]["neg_sem_obra"] >= MINIMO_NEGATIVAS)
    return saida
