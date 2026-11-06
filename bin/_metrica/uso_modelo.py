"""Uso real do modelo, por chamada, lido dos transcripts do Claude Code (#4128).

A população é a fita inteira. O rótulo de tarefa é informado por quem mede; não filtra
nem infere tarefas a partir do texto da conversa. Nenhum conteúdo da conversa é servido.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from math import ceil
from pathlib import Path
from statistics import mean

import transcript

_CAMPOS_ENTRADA = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")

def _numero(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0

def _serie(valores: list[int], populacao: int) -> dict:
    ordenados = sorted(valores)
    return {"amostras": len(valores), "ausentes": populacao - len(valores),
            "total": sum(valores) if len(valores) == populacao else None,
            "media": mean(valores) if valores else None,
            "p90": ordenados[ceil(len(valores) * 0.9) - 1] if valores else None}

def resumir(pedidos: dict) -> dict:
    """A deduplicação é de transcript.por_pedido: último usage por requestId."""
    n = len(pedidos)
    campos = {}
    for nome, campo in transcript.CAMPOS:
        valores = [uso[campo] for uso in pedidos.values() if _numero(uso.get(campo))]
        campos[nome] = _serie(valores, n)
    totais = [sum(uso[c] for c in _CAMPOS_ENTRADA) for uso in pedidos.values()
              if all(_numero(uso.get(c)) for c in _CAMPOS_ENTRADA)]
    campos["entrada_total"] = _serie(totais, n)
    return {"chamadas": n, "campos": campos}

def _resolver(seletor: str) -> Path | None:
    if _UUID.fullmatch(seletor):
        return transcript.da_sessao(seletor)
    if re.fullmatch(r"[a-z][a-z0-9-]*", seletor):
        return transcript.da_cadeira(seletor)
    raise ValueError("--fita recebe UUID da sessão do Claude Code ou slug da cadeira")

def _ler(seletor: str) -> dict:
    caminho = _resolver(seletor)
    if caminho is None:
        return {"seletor": seletor, "estado": "ausente", "motivo": "transcript do Claude Code não encontrado"}
    pedidos = transcript.por_pedido(caminho)
    if not pedidos:
        return {"seletor": seletor, "fita": caminho.stem, "estado": "indeterminavel",
                "motivo": "transcript ilegível ou sem requestId com usage"}
    return {"seletor": seletor, "fita": caminho.stem, "estado": "medido", **resumir(pedidos)}

def _texto(res: dict) -> str:
    linhas = [f"tarefa: {res['tarefa']} · população: fita inteira · fonte: usage do Claude Code"]
    for rotulo, medicao in res["fitas"].items():
        linhas.append(f"{rotulo}: {medicao.get('fita', medicao['seletor'])} · {medicao['estado']}")
        if medicao["estado"] != "medido":
            linhas.append(medicao["motivo"])
            continue
        linhas.append(f"  chamadas: {medicao['chamadas']} · p90: posto mais próximo, sem interpolação")
        for nome, serie in medicao["campos"].items():
            media = f"{serie['media']:.2f}" if serie["media"] is not None else "indeterminavel"
            p90 = str(serie["p90"]) if serie["p90"] is not None else "indeterminavel"
            linhas.append(f"  {nome}: média {media} · p90 {p90} · ausentes {serie['ausentes']}")
    return "\n".join(linhas)

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="metrica tokens", description=__doc__)
    parser.add_argument("--fita", required=True, help="UUID da sessão Code ou cadeira (última fita disponível)")
    parser.add_argument("--comparar-fita", help="UUID da outra fita Code ou cadeira")
    parser.add_argument("--tarefa", default="fita inteira", help="rótulo da tarefa das fitas dedicadas; não é filtro")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        fitas = {"antes" if args.comparar_fita else "fita": _ler(args.fita)}
        if args.comparar_fita:
            fitas["depois"] = _ler(args.comparar_fita)
    except ValueError as e:
        print(f"metrica tokens: {e}", file=sys.stderr)
        return 2
    resultado = {"versao": 1, "tarefa": args.tarefa, "fonte": "usage do Claude Code",
                 "populacao": "uma fita inteira por tarefa; --tarefa apenas rotula",
                 "p90": "posto mais próximo: ceil(0.9*n)", "fitas": fitas}
    print(json.dumps(resultado, ensure_ascii=False, indent=2) if args.json else _texto(resultado))
    if any(m["estado"] != "medido" for m in fitas.values()):
        return 5
    return 5 if any(s["ausentes"] for m in fitas.values() for s in m["campos"].values()) else 0
