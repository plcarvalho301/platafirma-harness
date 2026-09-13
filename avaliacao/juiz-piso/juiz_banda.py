#!/usr/bin/env python3
"""Runner resumível do juiz estrutural (piso <40 toks), com pool de threads.

Produtiza tmp/judge_smoke.py -> tmp/juiz_piso.py em runner de banda inteira.
Le a banda de tmp/banda_lt40.jsonl, julga cada secao (real|so-titulo|ancora-ruido)
via ollama local, e faz CHECKPOINT linha-a-linha em OUT. NAO escreve no banco:
secao.qualidade so e tocada por juiz_aplica.py, depois da banda inteira julgada.

Resumivel: ao subir, carrega os ids ja julgados (classe != erro) de OUT e pula.
Erro fica no checkpoint marcado e e RE-tentado no proximo lancamento.

Kill-safe: cada resultado e escrito sob lock + flush + fsync antes do proximo;
matar no meio perde no maximo os itens em voo (<= JUIZ_THREADS).

Paralelismo: JUIZ_THREADS requests concorrentes ao ollama. Os pesos nao duplicam
na VRAM (mesmo modelo); so o KV por slot soma. ollama serve em paralelo se
OLLAMA_NUM_PARALLEL >= JUIZ_THREADS (auto costuma bastar).

env:
  JUIZ_MODELO   modelo ollama            (default qwen3.5:9b)
  JUIZ_THREADS  requests concorrentes    (default 1)
  JUIZ_BANDA    entrada jsonl            (default tmp/banda_lt40.jsonl)
  JUIZ_OUT      checkpoint jsonl         (default tmp/juiz_banda.out.jsonl)
  JUIZ_LIMIT    teto de itens NOVOS      (default 0 = banda inteira)
  JUIZ_LOG_A_CADA  cadencia de progresso (default 200)
"""
import json, os, sys, time, threading, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

MODEL     = os.environ.get("JUIZ_MODELO", "qwen3.5:9b")
OLLAMA    = "http://127.0.0.1:11434/api/generate"
BANDA     = os.environ.get("JUIZ_BANDA", "/home/claudinho/AI/tmp/banda_lt40.jsonl")
OUT       = os.environ.get("JUIZ_OUT", "/home/claudinho/AI/tmp/juiz_banda.out.jsonl")
LIMIT     = int(os.environ.get("JUIZ_LIMIT", "0"))
LOG_CADA  = int(os.environ.get("JUIZ_LOG_A_CADA", "200"))
THREADS   = max(1, int(os.environ.get("JUIZ_THREADS", "1")))

PROMPT = """Você classifica se um trecho de seção de um acervo é conteúdo REAL ou LIXO ESTRUTURAL.
Não julgue qualidade nem profundidade — só a estrutura.
Classes:
- real: conteúdo genuíno, mesmo curto (um passo, uma definição, um resumo executivo, uma lista com sentido próprio).
- so-titulo: praticamente só um cabeçalho, sem conteúdo real embaixo.
- ancora-ruido: ruído estrutural (cabeçalho/rodapé corrido, número de página, entrada de sumário/índice, fragmento sem sentido próprio).
Responda SÓ JSON: {{"classe":"real|so-titulo|ancora-ruido","motivo":"ate 8 palavras"}}.
TÍTULO: {titulo}
CORPO: {corpo}"""


def judge(titulo, corpo):
    body = {
        "model": MODEL,
        "prompt": PROMPT.format(titulo=titulo, corpo=corpo),
        "stream": False, "format": "json", "think": False,
        "options": {"temperature": 0, "num_predict": 100, "num_ctx": 2048},
    }
    req = urllib.request.Request(OLLAMA, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.load(r)
    return json.loads(resp["response"])


def norm(cl):
    cl = (cl or "?").strip().lower().replace("ancara", "ancora")
    if cl in ("real", "so-titulo", "ancora-ruido"):
        return cl
    if "ancor" in cl or "ruid" in cl: return "ancora-ruido"
    if "titul" in cl: return "so-titulo"
    if "real" in cl: return "real"
    return "?"


def carrega_feitos(path):
    """ids ja julgados com classe valida (erro NAO conta -> sera re-tentado)."""
    feitos = set()
    if not os.path.exists(path):
        return feitos
    with open(path) as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("classe") and d["classe"] != "erro":
                feitos.add(d["id"])
    return feitos


def avalia(row):
    corpo = (row.get("corpo") or "").replace("\\n", " ").strip()
    try:
        res = judge(row.get("titulo", ""), corpo)
        return row["id"], norm(res.get("classe")), (res.get("motivo") or "")[:60], row.get("toks")
    except Exception as e:
        return row["id"], "erro", str(e)[:60], row.get("toks")


def main():
    banda = []
    with open(BANDA) as f:
        for l in f:
            l = l.strip()
            if l:
                banda.append(json.loads(l))
    total = len(banda)

    feitos = carrega_feitos(OUT)
    pend = [r for r in banda if r["id"] not in feitos]
    if LIMIT > 0:
        pend = pend[:LIMIT]

    print(f"MODELO={MODEL} threads={THREADS} banda={total} ja_feitos={len(feitos)} "
          f"pendentes={len(pend)}{' (teto '+str(LIMIT)+')' if LIMIT else ''}", flush=True)
    if not pend:
        print("nada pendente — banda completa.", flush=True)
        return

    c = Counter(); erros = 0; t0 = time.time()
    lock = threading.Lock()
    out = open(OUT, "a")

    def registra(i, n, sid, cl, motivo, toks):
        nonlocal erros
        with lock:
            c[cl] += 1
            if cl == "erro":
                erros += 1
            out.write(json.dumps({"id": sid, "classe": cl, "motivo": motivo,
                                  "toks": toks}, ensure_ascii=False) + "\n")
            out.flush(); os.fsync(out.fileno())
        if i % LOG_CADA == 0 or i == n:
            dt = time.time() - t0
            ips = i / max(dt, 1e-9)
            falta = (n - i) / max(ips, 1e-9)
            print(f"[{i}/{n}] {ips:.2f} it/s | falta ~{falta/60:.0f} min | "
                  f"erros={erros} | parcial={dict(c)}", flush=True)

    n = len(pend)
    try:
        if THREADS == 1:
            for i, row in enumerate(pend, 1):
                sid, cl, mot, tk = avalia(row)
                registra(i, n, sid, cl, mot, tk)
        else:
            with ThreadPoolExecutor(max_workers=THREADS) as ex:
                futs = [ex.submit(avalia, row) for row in pend]
                for i, fut in enumerate(as_completed(futs), 1):
                    sid, cl, mot, tk = fut.result()
                    registra(i, n, sid, cl, mot, tk)
    finally:
        out.close()

    dt = time.time() - t0
    print(f"FIM lote: {n} itens em {dt/60:.1f} min | dist_lote={dict(c)} | erros={erros}",
          flush=True)
    feitos_agora = len(carrega_feitos(OUT))
    print(f"CHECKPOINT: {feitos_agora}/{total} julgados "
          f"({'COMPLETO' if feitos_agora >= total else 'parcial — relancar p/ retomar'})",
          flush=True)


if __name__ == "__main__":
    main()
