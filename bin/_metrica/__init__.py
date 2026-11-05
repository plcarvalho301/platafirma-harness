"""_metrica — sub-pacote do miolo de `metrica` (abertura, tokens e o que vier).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent.parent / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import oplog


def somar_tokens(eventos, por_ato: bool = False, ordem_id: str | None = None,
                 job_id: str | None = None, ato: str | None = None) -> dict:
    """Soma tokens por ato, por ordem e por job (#4120)."""
    res = {
        "total_tokens": 0,
        "eventos": 0,
        "metodos": set(),
        "por_ato": defaultdict(lambda: {"tokens": 0, "eventos": 0, "metodos": set()}),
        "obras": set(),
    }
    for ev in eventos:
        if ev.get("tokens") is None:
            continue
        ev_ordem = str(ev.get("ordem_id") or "")
        ev_job = str(ev.get("job_id") or ev.get("lote_id") or "")
        ev_ato = str(ev.get("ato") or ev.get("tool") or "")

        if ordem_id and ev_ordem != ordem_id:
            continue
        if job_id and ev_job != job_id:
            continue
        if ato and ev_ato != ato:
            continue

        tk = int(ev.get("tokens") or 0)
        metodo = ev.get("metodo_tokens") or "desconhecido"
        res["total_tokens"] += tk
        res["eventos"] += 1
        res["metodos"].add(metodo)

        res["por_ato"][ev_ato]["tokens"] += tk
        res["por_ato"][ev_ato]["eventos"] += 1
        res["por_ato"][ev_ato]["metodos"].add(metodo)

        obra = ev.get("obra_id")
        if obra:
            res["obras"].add(obra)

    res["metodo"] = ", ".join(sorted(res["metodos"])) if res["metodos"] else "tokenizador qwen2.5"
    for a, dados in res["por_ato"].items():
        dados["metodo"] = ", ".join(sorted(dados["metodos"])) if dados["metodos"] else "tokenizador qwen2.5"
        del dados["metodos"]
    del res["metodos"]
    return res


def tokens_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="metrica tokens", add_help=False)
    parser.add_argument("--ordem", default="")
    parser.add_argument("--job", default="")
    parser.add_argument("--ato", default="")
    parser.add_argument("--dia", default="")
    parser.add_argument("--desde", default="")
    parser.add_argument("--ate", default="")
    parser.add_argument("--sessao", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-h", "--help", "--ajuda", dest="ajuda", action="store_true")
    args, _ = parser.parse_known_args(argv)

    if args.ajuda:
        print("uso: metrica tokens [--ordem <ordem_id>] [--job <job_id>] [--ato <ato>] [--dia <data>] [--json]")
        return 0

    hoje = datetime.now().astimezone().date().isoformat()
    desde = args.desde or args.dia or hoje
    ate = args.ate or args.dia or hoje

    try:
        leitura = oplog.ler(desde, ate, sessao=args.sessao or None)
        eventos = list(leitura)
    except Exception as e:
        print(f"metrica tokens: erro ao ler logs ({e})", file=sys.stderr)
        return 4

    if args.ordem and args.job:
        ordem_stats = somar_tokens(eventos, ordem_id=args.ordem)
        job_stats = somar_tokens(eventos, job_id=args.job)

        n_obras_ordem = max(1, len(ordem_stats["obras"]))
        n_obras_job = max(1, len(job_stats["obras"]))

        t_obra_ordem = round(ordem_stats["total_tokens"] / n_obras_ordem)
        t_obra_job = round(job_stats["total_tokens"] / n_obras_job)

        if args.json:
            out = {
                "ordem": {
                    "ordem_id": args.ordem,
                    "tokens_total": ordem_stats["total_tokens"],
                    "tokens_por_obra": t_obra_ordem,
                    "obras": n_obras_ordem,
                    "metodo": ordem_stats["metodo"],
                },
                "job": {
                    "job_id": args.job,
                    "tokens_total": job_stats["total_tokens"],
                    "tokens_por_obra": t_obra_job,
                    "obras": n_obras_job,
                    "metodo": job_stats["metodo"],
                }
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"ordem {args.ordem}: {t_obra_ordem} tokens/obra ({ordem_stats['metodo']})")
            print(f"job {args.job}: {t_obra_job} tokens/obra ({job_stats['metodo']})")
        return 0

    stats = somar_tokens(eventos, ordem_id=args.ordem or None,
                         job_id=args.job or None, ato=args.ato or None)

    if args.json:
        stats["obras"] = list(stats["obras"])
        stats["por_ato"] = dict(stats["por_ato"])
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        if args.ordem:
            n_obras = max(1, len(stats["obras"]))
            t_obra = round(stats["total_tokens"] / n_obras)
            print(f"ordem {args.ordem}: {t_obra} tokens/obra ({stats['metodo']})")
        elif args.job:
            n_obras = max(1, len(stats["obras"]))
            t_obra = round(stats["total_tokens"] / n_obras)
            print(f"job {args.job}: {t_obra} tokens/obra ({stats['metodo']})")
        elif args.ato:
            print(f"ato {args.ato}: {stats['total_tokens']} tokens ({stats['metodo']})")
        else:
            print(f"total: {stats['total_tokens']} tokens em {stats['eventos']} giros ({stats['metodo']})")
            for a, d in sorted(stats["por_ato"].items()):
                print(f"  {a:25s} {d['tokens']:8d} tokens ({d['metodo']})")
    return 0
