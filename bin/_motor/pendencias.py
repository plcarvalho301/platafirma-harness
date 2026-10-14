"""A decisão pendente do motor, como estado do objeto (card #3513, tarefa 5; spec R23; arq:0124 R10, R12).

Pendência não é armazenamento novo: é o que o estado da troca diz quando o objeto ficou num ponto que pede o
dono. Hoje há uma: a sombra de geração montada e medida, que espera virar ou descartar. Cada pendência traz os
sete campos do contrato comum (a pergunta; as opções, cada uma com o ato que a executa; o custo de cada uma; a
recomendada; o efeito se ninguém decidir; quem abriu; a cadeira dona do objeto). Fecha quando o ato da opção
escolhida roda, e então a lista volta vazia porque a sombra deixou de existir.

A recomendada sai de uma regra simples e declarada, ⚪ hipótese até o dono marcar a sua: virar se o acerto na
primeira posição e as abstenções corretas da sombra não são piores que os do servido, medidos no mesmo gabarito;
sem medida comparável do servido, não recomenda e diz por quê.
"""
from __future__ import annotations

TRECHOS_POR_S = 37.0          # a vazão que a montagem da g3 mediu; o plano da troca a usa como hipótese


def _da_geracao(m: dict, sombra: dict) -> bool:
    return m.get("geracao") in {sombra.get("id"), f"g{sombra.get('geracao')}", str(sombra.get("geracao"))}


def medicoes_da_sombra(rodadas: list[dict], sombra: dict) -> list[dict]:
    return [m for m in rodadas if m.get("geracao") and _da_geracao(m, sombra)]


def _numero(rodada: dict) -> int | None:
    g = ((rodada.get("indice") or {}).get("geracao") or {}).get("numero")
    return g if isinstance(g, int) else None


def _servido_comparavel(rodadas: list[dict], servindo: dict, gabarito) -> dict | None:
    for m in reversed(rodadas):                      # `rodadas` vem em ordem de hora
        if not m.get("geracao") and m.get("gabarito") == gabarito and _numero(m) == servindo.get("geracao"):
            return m
    return None


def _acerto(m: dict) -> tuple[float | None, int | None]:
    met = m.get("metricas") or {}
    h1 = (met.get("geral") or {}).get("hit@1")
    ab = met.get("abstencao")
    return h1, (ab.get("ok") if isinstance(ab, dict) else None)


def recomenda(sombra_m: dict, servido_m: dict | None, n_servindo: int) -> tuple[str | None, str]:
    if servido_m is None:
        return None, (f"sem medida da g{n_servindo} no mesmo gabarito para comparar: rode `motor rag medir "
                      "biblioteca` no servido antes de decidir")
    h_s, a_s = _acerto(sombra_m)
    h_v, a_v = _acerto(servido_m)
    if h_s is None or h_v is None:
        return None, "a medida de uma das duas nao traz o acerto na primeira posicao"
    pior = []
    if h_s < h_v:
        pior.append(f"acerto na 1a posicao {h_s} contra {h_v}")
    if a_s is not None and a_v is not None and a_s < a_v:
        pior.append(f"abstencoes corretas {a_s} contra {a_v}")
    if pior:
        return "descartar", "a sombra mede pior que o servido: " + "; ".join(pior)
    return "virar", (f"a sombra mede igual ou melhor que a g{n_servindo}: acerto na 1a posicao {h_s} contra {h_v}"
                     + (f", abstencoes corretas {a_s} contra {a_v}" if a_s is not None and a_v is not None else ""))


def pendencias(estado: dict, rodadas: list[dict]) -> list[dict]:
    """As pendências do estado da troca: [] sem sombra ou com sombra ainda não medida."""
    sombra, servindo = estado.get("sombra"), estado.get("servindo")
    if not sombra or not servindo:
        return []
    medidas = medicoes_da_sombra(rodadas, sombra)
    if not medidas:
        return []
    ultima = medidas[-1]
    g, n_ser = sombra["geracao"], servindo["geracao"]
    particao = estado.get("particao") or "biblioteca"
    cob = sombra.get("cobertura") or {}
    horas = (cob.get("trechos_total") or 0) / TRECHOS_POR_S / 3600
    recomendada, motivo = recomenda(ultima, _servido_comparavel(rodadas, servindo, ultima.get("gabarito")), n_ser)
    completa = cob.get("total") and cob.get("aprovadas") == cob.get("total")
    return [{
        "id": f"virar-ou-descartar-g{g}",
        "pergunta": f"A g{g} ({sombra.get('embedder')}) esta montada em sombra e medida: virar a {particao} para "
                    f"ela ou descartar?",
        "opcoes": [
            {"opcao": "virar",
             "ato": f"motor rag trocar {particao} --virar g{g} --apply --confirma g{g} --sim \"<o sim do dono>\" "
                    "--ajuste aviso_de_cobertura_fraca=<piso>",
             "custo": f"expurga a g{n_ser} ({servindo.get('embedder')}) e nao volta: voltar e uma troca nova, "
                      "de horas de GPU" + ("" if completa else "; a cobertura da sombra ainda nao chegou a 100%, "
                                                              "e a virada so aplica com 100%"),
             "volta": False},
            {"opcao": "descartar",
             "ato": f"motor rag trocar {particao} --descartar g{g} --apply --confirma g{g}",
             "custo": f"perde a montagem da g{g}: refazer custa cerca de {horas:.1f} h a {TRECHOS_POR_S:.0f} "
                      f"trechos/s (hipotese do plano); a g{n_ser} segue servindo",
             "volta": False}],
        "recomendada": recomendada, "motivo_da_recomendacao": motivo,
        "efeito_se_ninguem_decidir": f"a g{g} segue em sombra e a g{n_ser} segue servindo; nenhum outro trabalho de "
                                     "GPU abre enquanto a sombra ocupa o lote, e o disco da sombra continua gasto",
        "aberta_por": f"medicao {ultima.get('rotulo') or ultima.get('_arquivo')} de {ultima.get('em')} na g{g}",
        "cadeira_dona": "ia"}]
