"""_metrica — sub-pacote do miolo de `metrica` (abertura, tokens e o que vier).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent.parent / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
import oplog

# O giro não guarda o job: guarda os argumentos do ato (`acervo catalogar biblioteca obra --job <id>`). O `lote_id`
# do giro é o do lote do malote que agrupou as chamadas, e não o do acervo: não serve de job.
_RE_JOB_NOS_ARGS = re.compile(r"--job[= ]([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def job_do_evento(ev: dict) -> str:
    """O job de que o giro fala: o campo `job_id`, se o evento o traz, ou o que `--job` diz nos argumentos."""
    direto = str(ev.get("job_id") or "")
    if direto:
        return direto
    achado = _RE_JOB_NOS_ARGS.search(str(ev.get("args") or ""))
    return achado.group(1) if achado else ""


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
        ev_job = job_do_evento(ev)
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


def _por_obra(stats: dict, informadas: int | None) -> tuple[int | None, int | None]:
    """(obras, tokens por obra). O número de obras é o que quem chama informou, ou o que os eventos dizem; sem
    nenhum dos dois não se sabe, e dividir por 1 daria o total com cara de média."""
    n = informadas or len(stats["obras"]) or None
    return n, (round(stats["total_tokens"] / n) if n else None)


def _linha(rotulo: str, ident: str, stats: dict, n: int | None, por_obra: int | None, flag: str) -> str:
    if por_obra is None:
        return (f"{rotulo} {ident}: {stats['total_tokens']} tokens no total; número de obras desconhecido "
                f"(passe {flag} N) ({stats['metodo']})")
    return f"{rotulo} {ident}: {por_obra} tokens/obra ({n} obras · {stats['metodo']})"


def tokens_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="metrica tokens", add_help=False)
    parser.add_argument("--ordem", default="")
    parser.add_argument("--job", default="")
    parser.add_argument("--ato", default="")
    parser.add_argument("--dia", default="")
    parser.add_argument("--desde", default="")
    parser.add_argument("--ate", default="")
    parser.add_argument("--sessao", default="")
    parser.add_argument("--obras-ordem", dest="obras_ordem", type=int, default=0)
    parser.add_argument("--obras-job", dest="obras_job", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-h", "--help", "--ajuda", dest="ajuda", action="store_true")
    args, _ = parser.parse_known_args(argv)

    if args.ajuda:
        print("uso: metrica tokens [--ordem <ordem_id>] [--job <job_id>] [--ato <ato>] [--dia <data> | --desde <data> --ate <data>]\n"
              "                    [--obras-ordem <n>] [--obras-job <n>] [--json]\n"
              "o giro não guarda a obra: sem --obras-ordem e --obras-job o por obra só sai quando o evento a traz")
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
        n_ordem, t_ordem = _por_obra(ordem_stats, args.obras_ordem)
        n_job, t_job = _por_obra(job_stats, args.obras_job)

        if args.json:
            out = {
                "ordem": {
                    "ordem_id": args.ordem,
                    "tokens_total": ordem_stats["total_tokens"],
                    "tokens_por_obra": t_ordem,
                    "obras": n_ordem,
                    "metodo": ordem_stats["metodo"],
                },
                "job": {
                    "job_id": args.job,
                    "tokens_total": job_stats["total_tokens"],
                    "tokens_por_obra": t_job,
                    "obras": n_job,
                    "metodo": job_stats["metodo"],
                }
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(_linha("ordem", args.ordem, ordem_stats, n_ordem, t_ordem, "--obras-ordem"))
            print(_linha("job", args.job, job_stats, n_job, t_job, "--obras-job"))
        return 0

    stats = somar_tokens(eventos, ordem_id=args.ordem or None,
                         job_id=args.job or None, ato=args.ato or None)

    if args.json:
        stats["obras"] = list(stats["obras"])
        stats["por_ato"] = dict(stats["por_ato"])
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        if args.ordem:
            n, por_obra = _por_obra(stats, args.obras_ordem)
            print(_linha("ordem", args.ordem, stats, n, por_obra, "--obras-ordem"))
        elif args.job:
            n, por_obra = _por_obra(stats, args.obras_job)
            print(_linha("job", args.job, stats, n, por_obra, "--obras-job"))
        elif args.ato:
            print(f"ato {args.ato}: {stats['total_tokens']} tokens ({stats['metodo']})")
        else:
            print(f"total: {stats['total_tokens']} tokens em {stats['eventos']} giros ({stats['metodo']})")
            for a, d in sorted(stats["por_ato"].items()):
                print(f"  {a:25s} {d['tokens']:8d} tokens ({d['metodo']})")
    return 0
