"""`motor <inst> medir <particao> --contra <outra>`: o top-8 de duas instâncias da busca, lado a lado (card #3844,
tarefa 2; R27 da spec motor).

A virada da busca só se faz com o top-8 idêntico em toda pergunta e nenhum trecho cruzando partição (Trava do #3844:
«qualquer diferença no top-8 ou no ambiente para a virada»). Aqui mora a conta, sem rede: `bin/motor` chama as duas
instâncias e entrega as listas de fontes.

Cruzar partição é a busca nova devolver, numa partição, um trecho que a servida só tem na outra. As partições são
disjuntas na servida, então a interseção do que a nova devolve numa com o que a servida devolve na outra é vazia
quando a fronteira está certa.
"""
from __future__ import annotations

K = 8
LIMITE_NO_TEXTO = 15      # perguntas diferentes que o texto lista; o resto está no JSON salvo


def chave(fonte: dict) -> str:
    """A chave do trecho numa lista de fontes: a seção (`secao_id`, uuid, a chave de dedup do runtime) quando a API a
    serve; `chave` (a forma de `motor buscar`) em seguida; por último obra e coordenada humana, que colapsam
    ocorrências distintas da mesma âncora e por isso só valem sem as duas primeiras."""
    for campo in ("secao_id", "chave"):
        if fonte.get(campo):
            return str(fonte[campo])
    return f"{fonte.get('obra')}|{fonte.get('section_id')}"


def top(fontes, k: int = K) -> list:
    """As chaves das k primeiras fontes, na ordem, sem repetir a mesma seção."""
    vistos, saida = set(), []
    for f in fontes or []:
        c = chave(f)
        if c not in vistos:
            vistos.add(c)
            saida.append(c)
    return saida[:k]


def jaccard(a, b) -> float:
    ca, cb = set(a), set(b)
    return len(ca & cb) / max(len(ca | cb), 1)


def cruzados(servida_na_outra, nova_na_particao) -> list:
    """Os trechos que a nova devolve na partição pedida e a servida só tem na outra."""
    return sorted(set(servida_na_outra) & set(nova_na_particao))


def linha(item: dict, servida: list, nova: list, cruzando: list) -> dict:
    """A linha de uma pergunta: o Jaccard do top-8, se a ordem também é a mesma, o que só uma das duas trouxe."""
    return {"id": item.get("id"), "q": item["q"], "particao": item["particao"], "fonte": item.get("fonte"),
            "jaccard": round(jaccard(servida, nova), 3), "mesma_ordem": servida == nova,
            "so_na_servida": [c for c in servida if c not in set(nova)],
            "so_na_nova": [c for c in nova if c not in set(servida)],
            "cruzados": list(cruzando)}


def resumo(linhas: list) -> dict:
    """A conta da rodada. `limpo` é a condição da virada: ao menos uma pergunta, todas com Jaccard 1,0 e nenhum trecho
    cruzado."""
    n = len(linhas)
    identicas = sum(1 for l in linhas if l["jaccard"] == 1.0)
    cruz = sum(len(l["cruzados"]) for l in linhas)
    return {"perguntas": n, "identicas": identicas,
            "jaccard_minimo": min((l["jaccard"] for l in linhas), default=None),
            "mesma_ordem": sum(1 for l in linhas if l["mesma_ordem"]),
            "diferentes": [l for l in linhas if l["jaccard"] < 1.0],
            "com_cruzamento": [l for l in linhas if l["cruzados"]],
            "cruzados": cruz, "limpo": n > 0 and identicas == n and cruz == 0}


def carimbo_do_indice(indice: dict) -> dict:
    """O que o /facets diz do índice que serve, no que a Trava do #3844 fixa: embedder e geração."""
    ger = (indice or {}).get("geracao") or {}
    return {"embed_model": (indice or {}).get("embed_model"), "embed_backend": (indice or {}).get("embed_backend"),
            "geracao": ger.get("numero"), "embedder_da_geracao": (ger.get("parametros") or {}).get("embedder")}


def carimbos_iguais(a: dict, b: dict) -> bool:
    return a == b


def texto(res: dict, servida: str, nova: str, k: int, a: dict, b: dict) -> str:
    """A primeira linha é o que se cita; depois o carimbo dos dois índices, as perguntas diferentes e o veredito."""
    r = res
    jmin = "-" if r["jaccard_minimo"] is None else f"{r['jaccard_minimo']:.3f}"
    saida = [f"top-{k} identico em {r['identicas']}/{r['perguntas']} perguntas (Jaccard minimo {jmin}) · "
             f"trechos cruzando particao: {r['cruzados']} · {servida} contra {nova}",
             f"indice {servida}: {_carimbo_texto(a)}", f"indice {nova}: {_carimbo_texto(b)}"
             + ("" if carimbos_iguais(a, b) else "  ← DIFERE do da servida")]
    for l in r["diferentes"][:LIMITE_NO_TEXTO]:
        saida.append(f"  diferente ({l['jaccard']}) [{l['particao']}] {l['q'][:90]} · so na servida {len(l['so_na_servida'])}, "
                     f"so na nova {len(l['so_na_nova'])}")
    if len(r["diferentes"]) > LIMITE_NO_TEXTO:
        saida.append(f"  ... mais {len(r['diferentes']) - LIMITE_NO_TEXTO} no JSON salvo")
    for l in r["com_cruzamento"][:LIMITE_NO_TEXTO]:
        saida.append(f"  cruzou ({len(l['cruzados'])}) [{l['particao']}] {l['q'][:90]}")
    if r["limpo"] and carimbos_iguais(a, b):
        saida.append("sem diferenca aberta: a troca dos enderecos pode seguir")
    else:
        saida.append("diferenca aberta: nada se troca (Trava do #3844); volta ao Plano")
    return "\n".join(saida)


def _carimbo_texto(c: dict) -> str:
    return (f"{c.get('embed_model')} ({c.get('embed_backend')}) · geracao g{c.get('geracao')} "
            f"({c.get('embedder_da_geracao')})")


def veredito_limpo(res: dict, a: dict, b: dict) -> bool:
    """Exit 0 do verbo: top-8 idêntico, nenhum cruzamento e o mesmo índice nos dois lados."""
    return bool(res["limpo"]) and carimbos_iguais(a, b)


# --- as leituras da API do acervo (card #3844, unidade 7) ------------------------------------------------
#
# A API do acervo passa a subir sozinha (acervo-guarda, 8102), ao lado da que o rag-extractor-api serve (8100). As
# mesmas leituras, uma a uma, têm de dar o mesmo status e o mesmo corpo nos dois. Os campos que mudam a cada chamada
# (hora, tempo gasto) saem antes de comparar.

LEITURAS_DO_ACERVO = ("/acervo/descoberta", "/acervo/conceitos", "/acervo/ferramental", "/acervo/fontes",
                      "/acervo/fichas/cobertura", "/acervo/conceitos/relacoes/cartilha", "/acervo/automacoes",
                      "/acervo/lotes", "/acervo/particao", "/acervo/obras")
# leituras de uma obra, pelo primeiro id que `/acervo/obras` devolve nos dois lados
LEITURAS_DA_OBRA = ("/acervo/obras/{id}", "/acervo/obras/{id}/situacao", "/acervo/obras/{id}/ficha",
                    "/acervo/obras/{id}/impressoes", "/acervo/obras/{id}/derivacoes")
VOLATEIS = frozenset({"tempos_ms", "lido_em", "agora", "gerado_em", "uptime_s"})
LIMITE_DE_DIFERENCAS = 5


def normaliza(corpo):
    """O corpo sem os campos que mudam a cada chamada, para comparar o resto."""
    if isinstance(corpo, dict):
        return {k: normaliza(v) for k, v in corpo.items() if k not in VOLATEIS}
    if isinstance(corpo, list):
        return [normaliza(v) for v in corpo]
    return corpo


def diferencas(a, b, caminho: str = "$") -> list:
    """Onde dois corpos JSON diferem (no máximo `LIMITE_DE_DIFERENCAS` caminhos): chave que falta, tamanho de lista,
    valor distinto."""
    achados: list = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                achados.append(f"{caminho}.{k}: so em {'a nova' if k in b else 'a servida'}")
            else:
                achados += diferencas(a[k], b[k], f"{caminho}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            achados.append(f"{caminho}: {len(a)} itens na servida, {len(b)} na nova")
        for i, (x, y) in enumerate(zip(a, b)):
            achados += diferencas(x, y, f"{caminho}[{i}]")
    elif a != b:
        achados.append(f"{caminho}: {str(a)[:40]!r} contra {str(b)[:40]!r}")
    return achados[:LIMITE_DE_DIFERENCAS]


def primeiro_id(corpo) -> str | None:
    """O id da primeira obra de `/acervo/obras`, seja a resposta uma lista ou um objeto com a lista dentro."""
    itens = corpo if isinstance(corpo, list) else next((v for v in (corpo or {}).values() if isinstance(v, list)), []) \
        if isinstance(corpo, dict) else []
    for it in itens:
        if isinstance(it, dict) and it.get("id"):
            return str(it["id"])
    return None


def leitura(rota: str, servida, nova) -> dict:
    """A linha de uma leitura. `servida` e `nova` são (status, corpo JSON ou None). Igual é o mesmo status e o mesmo corpo
    sem os campos voláteis; corpo que não é JSON compara o texto."""
    (sa, ca), (sb, cb) = servida, nova
    dif = [] if sa == sb else [f"status {sa} na servida, {sb} na nova"]
    if not dif:
        dif = diferencas(normaliza(ca), normaliza(cb))
    return {"rota": rota, "status_servida": sa, "status_nova": sb, "igual": not dif, "diferencas": dif}


def resumo_das_leituras(linhas: list) -> dict:
    return {"leituras": len(linhas), "iguais": sum(1 for l in linhas if l["igual"]),
            "diferentes": [l for l in linhas if not l["igual"]],
            "limpo": bool(linhas) and all(l["igual"] for l in linhas)}


def texto_das_leituras(res: dict, servida: str, nova: str) -> str:
    saida = [f"leituras do acervo iguais em {res['iguais']}/{res['leituras']} · {nova} contra {servida}"]
    for l in res["diferentes"]:
        saida.append(f"  diferente {l['rota']} ({l['status_servida']} contra {l['status_nova']}): " + "; ".join(l["diferencas"]))
    saida.append("sem diferenca aberta" if res["limpo"] else "diferenca aberta: o acervo-guarda nao serve ainda no lugar do 8100")
    return "\n".join(saida)
