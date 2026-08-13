#!/usr/bin/env python3
# _persona-org.py — ledger append-only dos atos de organização (interno de `persona`).
# capacidade: organizacao
# dono: claudinha-gestao-estrategica
# Vocabulário emprestado do mdm-rh (dom_tipo_evento): a cadeira é o vínculo,
# a gerência é a função. FOTO se reconstrói por replay; o ledger nunca se edita.
import json, os, pathlib, sys, datetime as dt

RAIZ = pathlib.Path(os.environ.get("PERSONA_REPO", pathlib.Path.home() / "AI/platafirma-harness"))
LEDGER = RAIZ / "personas" / "eventos-org.jsonl"

ATO_EVENTO = {
    "prover":    "PROVIMENTO",
    "designar":  "ALTERACAO_FUNCAO",
    "dispensar": "ALTERACAO_FUNCAO",
    "remover":   "REMOCAO",
    "afastar":   "AFASTAMENTO",
    "reverter":  "RETORNO_VINCULO",
    "desligar":  "DESLIGAMENTO",
}


def opta(argv, nome, default=None):
    if nome in argv:
        i = argv.index(nome)
        if i + 1 < len(argv):
            v = argv[i + 1]
            del argv[i:i + 2]
            return v
        sai(f"{nome} exige valor")
    return default


def sai(msg, cod=2):
    print(f"erro: {msg}", file=sys.stderr)
    sys.exit(cod)


def le():
    if not LEDGER.exists():
        return []
    ev = []
    for n, linha in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha:
            continue
        try:
            ev.append(json.loads(linha))
        except json.JSONDecodeError:
            sai(f"ledger corrompido na linha {n} — não se conserta editando, se corrige com evento novo")
    return sorted(ev, key=lambda e: (e.get("em", ""), e.get("registrado_em", "")))


def grava(reg):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False, sort_keys=True) + "\n")


def foto(ev):
    est = {}
    for e in ev:
        cad = e.get("cadeira")
        t = e["tipo"]
        if t == "PROVIMENTO":
            est.setdefault(cad, {"estado": "ativa", "gerencias": [], "alias": None,
                                 "desde": e["em"], "gatilho": None, "motivo": None})
            est[cad]["estado"] = "ativa"
            est[cad]["desde"] = e["em"]
            if e.get("alias"):
                est[cad]["alias"] = e["alias"]
        elif cad not in est:
            continue
        elif t == "ALTERACAO_FUNCAO":
            g = e.get("gerencia")
            if e["ato"] == "designar" and g not in est[cad]["gerencias"]:
                est[cad]["gerencias"].append(g)
            if e["ato"] == "dispensar" and g in est[cad]["gerencias"]:
                est[cad]["gerencias"].remove(g)
        elif t == "REMOCAO":
            g, para = e.get("gerencia"), e.get("destino")
            if g in est[cad]["gerencias"]:
                est[cad]["gerencias"].remove(g)
            if para in est and g not in est[para]["gerencias"]:
                est[para]["gerencias"].append(g)
        elif t == "AFASTAMENTO":
            est[cad].update(estado="afastada", desde=e["em"], gatilho=e.get("gatilho"))
        elif t == "RETORNO_VINCULO":
            est[cad].update(estado="ativa", desde=e["em"], gatilho=None)
        elif t == "DESLIGAMENTO":
            est[cad].update(estado="desligada", desde=e["em"], motivo=e.get("motivo"))
    return est


def main():
    argv = sys.argv[1:]
    if not argv:
        sai("ato ausente")
    ato = argv.pop(0)

    if ato == "filme":
        ev = le()
        alvo = argv[0] if argv else None
        for e in ev:
            if alvo and e.get("cadeira") != alvo and e.get("destino") != alvo:
                continue
            extra = " · ".join(x for x in (e.get("gerencia"), e.get("destino"),
                                           e.get("gatilho"), e.get("motivo")) if x)
            print(f"{e['em']}  {e['tipo']:<17} {e.get('cadeira') or '—':<28} {extra}")
            if e.get("nota"):
                print(f"{'':12}└ {e['nota']}")
        return

    if ato == "foto":
        est = foto(le())
        for cad, v in sorted(est.items(), key=lambda kv: (kv[1]["estado"], kv[0])):
            marca = {"ativa": " ", "afastada": "~", "desligada": "x"}[v["estado"]]
            alias = f" ({v['alias']})" if v["alias"] else ""
            print(f"{marca} {cad}{alias} · {v['estado']} desde {v['desde']}")
            if v["gatilho"]:
                print(f"    gatilho de volta: {v['gatilho']}")
            if v["motivo"]:
                print(f"    motivo: {v['motivo']}")
            for g in v["gerencias"]:
                print(f"    · {g}")
        return

    if ato not in ATO_EVENTO:
        sai(f"ato desconhecido: {ato}")

    em = opta(argv, "--em", dt.date.today().isoformat())
    nota = opta(argv, "--nota")
    autor = opta(argv, "--autor", os.environ.get("PF_CADEIRA", "desconhecido"))
    gatilho = opta(argv, "--gatilho")
    motivo = opta(argv, "--motivo")
    alias = opta(argv, "--alias")

    reg = {"em": em, "registrado_em": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "ato": ato, "tipo": ATO_EVENTO[ato], "autor": autor}
    if nota:
        reg["nota"] = nota
    if alias:
        reg["alias"] = alias

    if ato in ("prover", "afastar", "reverter", "desligar"):
        if len(argv) != 1:
            sai(f"{ato} <cadeira>")
        reg["cadeira"] = argv[0]
    elif ato in ("designar", "dispensar"):
        if len(argv) != 2:
            sai(f"{ato} <cadeira> <gerencia>")
        reg["cadeira"], reg["gerencia"] = argv
    elif ato == "remover":
        if len(argv) != 3:
            sai("remover <gerencia> <de> <para>")
        reg["gerencia"], reg["cadeira"], reg["destino"] = argv

    if ato == "afastar":
        if not gatilho:
            sai("afastar exige --gatilho: suspensão sem condição de volta é desligamento disfarçado")
        reg["gatilho"] = gatilho
    if ato == "desligar":
        if not motivo:
            sai("desligar exige --motivo")
        reg["motivo"] = motivo

    est = foto(le())
    cad = reg.get("cadeira")
    if ato == "prover" and cad in est and est[cad]["estado"] != "desligada":
        sai(f"{cad} já provida ({est[cad]['estado']} desde {est[cad]['desde']})")
    if ato != "prover" and cad not in est:
        sai(f"{cad} não foi provida — nenhum ato antes do provimento")
    if ato == "reverter" and cad in est and est[cad]["estado"] != "afastada":
        sai(f"{cad} não está afastada ({est[cad]['estado']})")
    if ato == "remover" and reg["destino"] not in est:
        sai(f"destino {reg['destino']} não foi provido")

    grava(reg)
    print(f"{reg['tipo']} · {cad or reg.get('gerencia')} · {em}")


if __name__ == "__main__":
    main()
