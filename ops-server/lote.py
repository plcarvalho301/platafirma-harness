"""Iterador unico do lote da porta, com a regra do lote encadeado (card:3149 passo 7;
spec_ambiente-de-desenvolvimento §6; comentario #939 secao A do card).

Modulo puro -- sem mcp, sem porta, sem rede -- para a regra de parada morar num lugar so
e o teste a provar sem subir a porta. `run_command commands[]` e o `lote` da tool de verbo
chamam `itera`; o que roda cada item (execve, PDP, auditoria, poda) fica com quem chama.

Regra de continuacao por LISTA BRANCA: a cadeia segue so se o item terminou com exit 0
(fez) ou 1 (nao fez por merito: ja feito, ja em dia, nao existe). Todo o resto para,
inclusive o que nem tem exit: recusa da porta conta como 2, negado pelo PDP como 4,
timeout e erro de execucao como 5, exit fora da tabela da arq:0110 (126, 127, 128 do git,
>128 por sinal) como 5. Uma lista negra (2..5) deixaria 127 e 128 passarem como "seguir".

Tres estados por item, nunca fundidos: rodou (o resultado) · nao rodou (a cadeia parou
antes) · omitido por teto (CAP de bytes do lote). Teto no meio de um lote encadeado devolve
`lote_next` e NAO declara parada: nao houve falha, houve limite. Retomar e rerodar a cadeia
inteira: cada ato devolve "ja feito" (exit 0) para o que ja fez, e o prefixo vira no-op.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

SEGUE = (0, 1)


def exit_do_item(r: Any) -> int:
    """O exit que conta para a cadeia (tabela da arq:0110 §4)."""
    if not isinstance(r, dict):
        return 5
    if r.get("recusado"):
        return 2
    e = r.get("exit_code")
    if isinstance(e, int) and not isinstance(e, bool):
        return e if 0 <= e <= 5 else 5
    if r.get("regra"):          # negado pela politica de acesso (PDP)
        return 4
    return 5                    # timeout, erro de execucao, forma desconhecida


def _texto(campo: Any) -> str:
    if isinstance(campo, dict):
        return str(campo.get("texto") or "")
    return str(campo or "")


def linha_do_item(r: Any) -> str:
    """Primeira linha util: o que a cadeira le para decidir sem abrir o item."""
    if not isinstance(r, dict):
        return str(r)[:200]
    for fonte in (_texto(r.get("stdout")), _texto(r.get("stderr")),
                  str(r.get("motivo") or ""), str(r.get("erro") or "")):
        for linha in fonte.splitlines():
            if linha.strip():
                return linha.strip()[:200]
    return ""


def resumo_cadeia(resultados: list, parou_em: int | None) -> dict:
    itens, nao_rodou = [], []
    for i, r in enumerate(resultados):
        if isinstance(r, dict) and r.get("nao_rodou"):
            nao_rodou.append(i)
            itens.append({"n": i, "exit": None, "linha": "não rodou"})
        elif isinstance(r, dict) and r.get("omitido_por_teto"):
            itens.append({"n": i, "exit": None, "linha": "omitido por teto"})
        else:
            itens.append({"n": i, "exit": exit_do_item(r), "linha": linha_do_item(r)})
    if parou_em is not None:
        topo = itens[parou_em]["exit"]
        motivo = f"parou em {parou_em}: {itens[parou_em]['linha']}"
    else:
        rodados = [x["exit"] for x in itens if x["exit"] is not None]
        topo = 0 if all(e == 0 for e in rodados) else 1
        motivo = None
    return {"encadeado": True, "exit": topo, "parou_em": parou_em, "motivo": motivo,
            "nao_rodou": nao_rodou, "itens": itens}


async def itera(itens: list, roda: Callable[[int, Any, list], Awaitable[dict]], *,
                encadeado: bool = False, cap: int | None = None,
                bytes_de: Callable[[dict], int] | None = None) -> dict:
    """Roda os itens em ordem. `roda(i, item, resultados_ate_aqui)` devolve o resultado do
    item. Sem `encadeado`, erro num item nao derruba os outros (comportamento de sempre)."""
    resultados: list = []
    acumulado, lote_next, parou_em = 0, None, None
    for i, x in enumerate(itens):
        if cap is not None and acumulado >= cap:
            lote_next = i
            break
        r = await roda(i, x, resultados)
        resultados.append(r)
        if bytes_de is not None:
            acumulado += bytes_de(r) or 0
        if encadeado and exit_do_item(r) not in SEGUE:
            parou_em = i
            break
    for _ in range(len(resultados), len(itens)):
        if parou_em is not None:
            resultados.append({"nao_rodou": True, "motivo": f"a cadeia parou no item {parou_em}"})
        else:
            resultados.append({"omitido_por_teto": True})
    out = {"lote": resultados, "lote_n": len(itens), "lote_next": lote_next}
    if encadeado:
        out["cadeia"] = resumo_cadeia(resultados, parou_em)
    return out


def bytes_stdout(r: dict) -> int:
    so = r.get("stdout") if isinstance(r, dict) else None
    return so.get("bytes_total", 0) if isinstance(so, dict) else 0
