"""Medidas de identidade e ciclo da fita, sem expor conteúdo do bruto (#2856 linhas 44 e 197)."""
import argparse
import json
from collections import Counter
from datetime import date, timedelta, datetime

import oplog


def medir(registros):
    fitas = {}
    docs = Counter()
    sem_documento = sondas = 0
    for r in registros:
        if oplog.origem_da_linha(r) == "sonda" or r.get("origem") == "sonda":
            sondas += 1
            continue
        sid = r.get("sessao_id")
        if sid in (None, "", "-"):
            continue
        f = fitas.setdefault(sid, {"sessao_id": sid, "cadeira": r.get("cadeira"),
                                  "abriu": None, "fechou": None, "giros": 0})
        ts = r.get("ts")
        abertura = r.get("tool") in ("monta_sessao", "monta-sessao") and not r.get("evento") and not r.get("erro")
        if abertura and ts:
            f["abriu"] = min(f["abriu"], ts) if f["abriu"] else ts
        if r.get("evento") == "fecho" and ts:
            f["fechou"] = max(f["fechou"], ts) if f["fechou"] else ts
        if oplog.tipo_da_linha(r) == "giro":
            f["giros"] += 1
        if r.get("tool") == "acervo" and r.get("ato") == "ler":
            esp, chave = r.get("documento_especie"), r.get("documento_chave")
            if esp and chave:
                docs[(esp, chave, r.get("cadeira"), sid)] += 1
            else:
                sem_documento += 1
    for f in fitas.values():
        f["integra"] = bool(f["abriu"] and f["fechou"] and f["fechou"] >= f["abriu"])
        f["duracao_s"] = None
        if f["integra"]:
            f["duracao_s"] = (datetime.fromisoformat(f["fechou"]) -
                               datetime.fromisoformat(f["abriu"])).total_seconds()
    return {"fitas": list(fitas.values()), "total_fitas": len(fitas),
            "fitas_integras": sum(f["integra"] for f in fitas.values()),
            "sondas_excluidas": sondas,
            "documentos": [{"especie": k[0], "chave": k[1], "cadeira": k[2],
                             "sessao_id": k[3], "leituras": n} for k, n in docs.items()],
            "leituras_sem_identidade_documento": sem_documento}


def main(ato, argv):
    p = argparse.ArgumentParser(prog="metrica " + ato)
    p.add_argument("dia", nargs="?", default=date.today().isoformat())
    p.add_argument("--desde")
    p.add_argument("--ate")
    p.add_argument("--cadeira")
    p.add_argument("--sessao")
    a = p.parse_args(argv)
    try:
        inicio, fim = date.fromisoformat(a.desde or a.dia), date.fromisoformat(a.ate or a.dia)
        if fim < inicio:
            raise ValueError()
    except ValueError:
        p.error("janela inválida; use AAAA-MM-DD e início anterior ao fim")
    leitura = oplog.ler(inicio.isoformat(), fim.isoformat())
    registros = [r for r in leitura if (not a.cadeira or r.get("cadeira") == a.cadeira)
                 and (not a.sessao or str(r.get("sessao_id") or "").startswith(a.sessao))]
    r = medir(registros)
    dias = [(inicio + timedelta(days=n)).isoformat() for n in range((fim-inicio).days + 1)]
    tamanhos = {d: oplog.tamanho_dia(d) for d in dias}
    r.update(fonte="bruto", desde=str(inicio), ate=str(fim),
             log_bytes_por_dia=tamanhos,
             log_bytes=sum(n for n in tamanhos.values() if n is not None),
             dias_ausentes=[d for d, n in tamanhos.items() if n is None],
             cobertura="só a janela consultada; o bruto expira em 35 dias; abertura ou fecho fora dela não são inferidos",
             linhas_ilegiveis=leitura.ilegiveis)
    if ato == "documentos":
        r.pop("fitas")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0
