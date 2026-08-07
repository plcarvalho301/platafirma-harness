#!/usr/bin/env python3
"""G0 -- geracao local sobre as 34 sondas do estrato firmabot.

O contexto NAO e re-recuperado: usa o campo `contexto` ja congelado em
resultados/G0-rag-base/T0-*.json (acervo_sha 24ed2cbf...). Assim a unica
variavel entre arms e o gerador -- recuperacao identica, prompt identico,
amostragem identica.

Uso:  g0_geracao.py <modelo-ollama> <dir-resultado>
Ex.:  g0_geracao.py granite4:latest G0-granite4
"""
import json, sys, time, re, pathlib, urllib.request, urllib.error, datetime

BASE = pathlib.Path("/home/claudinho/AI/platafirma-harness/avaliacao/gold-set-firmabot")
RAGB = BASE / "resultados" / "G0-rag-base"
OLLAMA = "http://127.0.0.1:11434"

SISTEMA = (
    "Voce responde APENAS com base nas fontes numeradas fornecidas.\n"
    "Regras, sem excecao:\n"
    "1. Toda frase cita a fonte entre colchetes, ex.: [3].\n"
    "2. Use so as fontes que tratam do conceito EXATO perguntado; fonte vizinha nao serve.\n"
    "3. Se nenhuma fonte cobrir o conceito perguntado, diga que o acervo nao cobre. "
    "Nao responda pela vizinha, nao complete com conhecimento proprio.\n"
    "Responda em portugues do Brasil, direto, sem preambulo."
)

OPCOES = {"temperature": 0, "seed": 42, "num_ctx": 16384, "num_predict": 900}


def post(path, payload, timeout=900):
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path):
    with urllib.request.urlopen(OLLAMA + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


NAO_COBRE = re.compile(
    r"n[ãa]o\s+(?:cobre|cobrem|h[áa]|existe|traz|abordam?|tratam?|contempla)"
    r"|nenhuma\s+(?:das\s+)?fontes?|acervo\s+n[ãa]o|fontes?\s+fornecidas?\s+n[ãa]o",
    re.I)


def medir(resposta, n_fontes):
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", resposta) if f.strip()]
    com_cite = [f for f in frases if re.search(r"\[\d+\]", f)]
    cites = [int(x) for x in re.findall(r"\[(\d+)\]", resposta)]
    return {
        "chars": len(resposta),
        "frases": len(frases),
        "frases_com_citacao": len(com_cite),
        "taxa_citacao": round(len(com_cite) / len(frases), 3) if frases else 0.0,
        "fontes_citadas": sorted(set(cites)),
        "citacoes_fora_do_intervalo": sorted({c for c in cites if c < 1 or c > n_fontes}),
        "declarou_nao_cobertura": bool(NAO_COBRE.search(resposta)),
    }


def main():
    modelo, dirname = sys.argv[1], sys.argv[2]
    out = BASE / "resultados" / dirname
    out.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(RAGB.glob("T0-*.json"))
    assert len(arquivos) == 34, f"esperava 34 sondas, achei {len(arquivos)}"

    linhas, ps_amostra = [], None
    for i, arq in enumerate(arquivos, 1):
        d = json.load(open(arq))
        r = d["retorno"]
        contexto = r.get("contexto") or ""
        fontes = r.get("fontes", [])
        nn, pergunta = d["n"], d["pergunta"]

        user = f"PERGUNTA: {pergunta}\n\nFONTES:\n{contexto}"
        t0 = time.time()
        corpo = {
            "model": modelo, "stream": False, "keep_alive": "10m",
            "think": False,
            "options": OPCOES,
            "messages": [{"role": "system", "content": SISTEMA},
                         {"role": "user", "content": user}],
        }
        try:
            resp = post("/api/chat", corpo)
        except urllib.error.HTTPError:
            corpo.pop("think")
            resp = post("/api/chat", corpo)
        dt = int((time.time() - t0) * 1000)
        texto = resp.get("message", {}).get("content", "") or ""
        raciocinio = resp.get("message", {}).get("thinking") or ""
        if i == 1:
            ps_amostra = get("/api/ps")

        m = medir(texto, len(fontes))
        rec = {
            "sonda": "G0", "n": nn, "bloco": d["bloco"],
            "persona": "persona-nao-declarada",
            "modelo": modelo,
            "pergunta": pergunta,
            "contexto_de": {"rodada": "G0-rag-base", "acervo_sha": d.get("acervo_sha"),
                            "n_fontes": len(fontes), "chars_contexto": len(contexto),
                            "cobertura_rag": r.get("cobertura")},
            "amostragem": OPCOES,
            "chamada_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "latencia_ms": dt,
            "tokens": {k: resp.get(k) for k in
                       ("prompt_eval_count", "eval_count", "eval_duration",
                        "prompt_eval_duration", "load_duration", "total_duration")},
            "medidas": m,
            "resposta_vazia": texto.strip() == "",
            "raciocinio_chars": len(raciocinio),
            "resposta": texto,
        }
        json.dump(rec, open(out / f"G0-{nn}-persona-nao-declarada.json", "w"),
                  ensure_ascii=False, indent=1)
        tps = (resp.get("eval_count") or 0) / ((resp.get("eval_duration") or 1) / 1e9)
        linhas.append({"n": nn, "bloco": d["bloco"], "latencia_ms": dt,
                       "tok_s": round(tps, 1), **m})
        print(f"{nn} {dt:>6}ms {tps:5.1f} tok/s cit={m['taxa_citacao']} "
              f"nao_cobre={m['declarou_nao_cobertura']}", file=sys.stderr, flush=True)

    json.dump({"modelo": modelo, "ps_apos_primeira_sonda": ps_amostra,
               "amostragem": OPCOES, "sistema": SISTEMA, "linhas": linhas},
              open(out / "_resumo.json", "w"), ensure_ascii=False, indent=1)
    post("/api/chat", {"model": modelo, "messages": [], "keep_alive": 0})
    print(f"OK {modelo}: 34 sondas em {out}")


if __name__ == "__main__":
    main()
