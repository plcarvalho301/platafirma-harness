"""O histórico de medida, com o marco das gerações e dos ajustes (card #3513, tarefa 6; spec R1, R4).

`motor rag medir <particao> --historico` lê as medições que a bateria já salvou em `medicoes_em` (um JSON por
rodada) e devolve a série em ordem de hora, com os marcos no eixo do tempo: cada virada de geração e cada ajuste
aplicado (o histórico de ajuste da instância). A série de medida e o histórico de ajuste, lidos no mesmo período,
dão o mesmo conjunto de marcos que o gráfico mostra.

De onde sai cada marco:
- ajuste: o JSONL `var/motor/ajustes-historico.jsonl`; quem mudou, quando, antes e depois, o fundamento;
- virada da geração que serve hoje: `ajustes.virada` da geração servindo (a hora, quem autorizou); quando a rota
  não responde, o marco sai da primeira medição que o carimbo do índice atribui à geração, marcado como inferido;
- virada de geração anterior: sempre a primeira medição vista na geração (inferido): o que se sabe é só o que a
  bateria carimbou.

Medição de sombra (`geracao` no arquivo) entra na série marcada `sombra`: não é o servido e não gera marco.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

NAO_CONSEGUI = "nao consegui olhar"


def utc(em: str | None) -> str:
    """A hora em UTC, para comparar e ordenar: a bateria carimba com o fuso do host (`-0300`) e o rag com `+00:00`.
    Sem fuso vale a hora local do host."""
    if not em:
        return ""
    for formato in (None, "%Y-%m-%dT%H:%M:%S%z"):
        try:
            d = datetime.fromisoformat(em) if formato is None else datetime.strptime(em, formato)
        except ValueError:
            continue
        if d.tzinfo is None:
            d = d.astimezone()
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    return em


def _geracao_do_carimbo(m: dict) -> int | None:
    g = ((m.get("indice") or {}).get("geracao") or {}).get("numero")
    return g if isinstance(g, int) else None


def ler_medicoes(diretorio: str) -> tuple[list[dict], list[str]]:
    """As rodadas da bateria (as que têm `metricas`), em ordem de hora, e os arquivos que não abriram."""
    rodadas, ilegiveis = [], []
    try:
        nomes = sorted(f for f in os.listdir(diretorio) if f.endswith(".json"))
    except OSError:
        return [], [f"{diretorio} nao abriu"]
    for nome in nomes:
        try:
            with open(os.path.join(diretorio, nome), encoding="utf-8") as f:
                m = json.load(f)
        except (OSError, ValueError):
            ilegiveis.append(nome)
            continue
        if isinstance(m, dict) and isinstance(m.get("metricas"), dict) and m.get("em"):
            rodadas.append({**m, "_arquivo": nome})
    rodadas.sort(key=lambda m: utc(m["em"]))
    return rodadas, ilegiveis


def _metrica(bloco: dict | None) -> dict | None:
    if not isinstance(bloco, dict):
        return None
    return {k: bloco.get(k) for k in ("n", "hit@1", "hit@3", "hit@5", "mrr") if k in bloco}


def ponto(m: dict) -> dict:
    """Uma medição na forma da série."""
    met = m.get("metricas") or {}
    abst = met.get("abstencao")
    return {"em": m["em"], "arquivo": m["_arquivo"], "rotulo": m.get("rotulo") or None, "k": m.get("k"),
            "geracao": _geracao_do_carimbo(m), "sombra": m.get("geracao") or None,
            "embedder": ((m.get("indice") or {}).get("geracao") or {}).get("parametros", {}).get("embedder")
            or (m.get("indice") or {}).get("embed_model"),
            "bateria": m.get("bateria") or m.get("gabarito"),
            "gabarito": m.get("gabarito") or m.get("bateria"), "bracos": m.get("bracos") or [],
            "geral": _metrica(met.get("geral")), "codigo": _metrica(met.get("codigo")),
            "sentido": _metrica(met.get("sentido")), "t2": _metrica(met.get("t2")),
            "abstencao": ({"ok": abst.get("ok"), "n": abst.get("n"), "taxa": abst.get("taxa")}
                          if isinstance(abst, dict) else m.get("abstencao")),
            "latencia_ms": m.get("latencia_ms")}


def marcos(serie: list[dict], ajustes: list[dict], ger_servindo: dict | None) -> list[dict]:
    """Os marcos da série: viradas (da geração servindo e das vistas pela bateria) e ajustes aplicados."""
    out: list[dict] = []
    vistas: dict[int, str] = {}
    for p in serie:
        if p["sombra"] or p["geracao"] is None:
            continue
        vistas.setdefault(p["geracao"], p["em"])
    virada = ((ger_servindo or {}).get("ajustes") or {}).get("virada")
    n_serv = (ger_servindo or {}).get("geracao")
    for g, primeira in sorted(vistas.items()):
        if g == n_serv and isinstance(virada, dict) and virada.get("em"):
            out.append({"tipo": "virada", "em": virada["em"], "geracao": g, "inferido": False,
                        "titulo": f"virada para a g{g}", "quem": virada.get("autor") or None,
                        "autorizada_por": virada.get("autorizada_por"),
                        "fundamento": virada.get("autorizada_por"), "primeira_medicao_em": primeira})
        else:
            out.append({"tipo": "virada", "em": primeira, "geracao": g, "inferido": True,
                        "titulo": f"primeira medicao vista na g{g}", "quem": None, "autorizada_por": None,
                        "fundamento": None, "primeira_medicao_em": primeira})
    for a in ajustes:
        out.append({"tipo": "ajuste", "em": a.get("em"), "geracao": a.get("geracao"), "inferido": False,
                    "titulo": f"{a.get('slug')}: {a.get('antes')} -> {a.get('depois')}",
                    "quem": a.get("sujeito"), "fundamento": a.get("fundamento"), "slug": a.get("slug"),
                    "antes": a.get("antes"), "depois": a.get("depois"), "origem": a.get("origem")})
    out.sort(key=lambda x: utc(x["em"]))
    return out


def filtrar(serie: list[dict], desde: str | None, rotulo: str | None) -> list[dict]:
    return [p for p in serie if (not desde or utc(p["em"]) >= utc(desde)) and (not rotulo or p["rotulo"] == rotulo)]


def texto(r: dict) -> str:
    s = r["medicoes"]
    primeira = s[0]["em"] if s else NAO_CONSEGUI
    saida = [f"historico de medida ({r['particao']}): {len(s)} medicao(oes), a primeira em {primeira} · "
             f"{len(r['marcos'])} marco(s) · lido {r['lido_em']}"]
    marcos_pend = list(r["marcos"])
    for p in s:
        while marcos_pend and marcos_pend[0]["em"] and utc(marcos_pend[0]["em"]) <= utc(p["em"]):
            m = marcos_pend.pop(0)
            saida.append(f"  == {m['em']}  {m['tipo']}: {m['titulo']}"
                         + (" (inferido da bateria)" if m.get("inferido") else "")
                         + (f"  por {m['quem']}" if m.get("quem") else "")
                         + (f"  porque: {m['fundamento']}" if m.get("fundamento") else ""))
        g = p["geral"] or {}
        ab = p["abstencao"]
        ab_txt = f"{ab['ok']}/{ab['n']}" if isinstance(ab, dict) and ab.get("n") is not None else (ab or "-")
        lat = (p["latencia_ms"] or {}).get("mediana")
        saida.append(f"  {p['em']}  {('sombra ' + str(p['sombra'])) if p['sombra'] else ('g%s' % p['geracao'] if p['geracao'] is not None else 'g?')}"
                     f"  k={p['k']}  hit@1 {g.get('hit@1', '-')}  hit@5 {g.get('hit@5', '-')}  mrr {g.get('mrr', '-')}"
                     f"  abst {ab_txt}  mediana {lat if lat is not None else '-'} ms"
                     + (f"  [{p['rotulo']}]" if p["rotulo"] else ""))
    for m in marcos_pend:
        saida.append(f"  == {m['em']}  {m['tipo']}: {m['titulo']}"
                     + (" (inferido da bateria)" if m.get("inferido") else ""))
    for fonte, motivo in (r.get("nao_consegui_olhar") or {}).items():
        saida.append(f"  {NAO_CONSEGUI}: {fonte} — {motivo}")
    return "\n".join(saida)
