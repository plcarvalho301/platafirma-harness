#!/usr/bin/env python3
"""Grava o veredito do juiz em acervo.secao.qualidade e imprime a distribuicao corrigida.

Passo "ai gravo qualidade" — roda DEPOIS da banda inteira julgada por juiz_banda.py.
Gate: recusa escrever se o checkpoint nao cobre a banda inteira, salvo --parcial.
Ate rodar isto, NADA e escrito no campo (secao.qualidade fica 'nao-julgada').

Mapeia a classe do juiz -> vocabulario do CHECK secao_qualidade_check:
  real + tem titulo  -> titulada
  real + sem titulo  -> sem-titulo
  so-titulo          -> so-titulo
  ancora-ruido       -> ancora-ruido
(o schema distingue conteudo real por ter titulo; 'real' e binario do juiz.)

uso:
  python3 juiz_aplica.py            # so escreve se banda completa; imprime dist
  python3 juiz_aplica.py --parcial  # escreve o que houver no checkpoint
  python3 juiz_aplica.py --dry      # nao escreve; so dist do checkpoint
"""
import json, os, subprocess, sys
from collections import Counter

BANDA = os.environ.get("JUIZ_BANDA", "/home/claudinho/AI/tmp/banda_lt40.jsonl")
OUT   = os.environ.get("JUIZ_OUT", "/home/claudinho/AI/tmp/juiz_banda.out.jsonl")
PGC   = ["docker", "exec", "-i", "rag-extractor-pg",
         "psql", "-U", "rag", "-d", "rag_extractor", "-v", "ON_ERROR_STOP=1"]
CLASSES_JUIZ = {"real", "so-titulo", "ancora-ruido"}
PERMITIDOS   = {"titulada", "so-titulo", "ancora-ruido", "sem-titulo", "nao-julgada"}


def psql(sql, stdin=None):
    p = subprocess.run(PGC + (["-tAc", sql] if stdin is None else ["-c", sql]),
                       input=stdin, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("psql falhou: " + p.stderr.strip())
    return p.stdout


def carrega():
    banda_titulo = {}   # id -> tem_titulo(bool)
    with open(BANDA) as f:
        for l in f:
            l = l.strip()
            if l:
                d = json.loads(l)
                banda_titulo[d["id"]] = bool((d.get("titulo") or "").strip())
    veredito = {}       # id -> classe juiz (ultimo valido vence)
    with open(OUT) as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("classe") in CLASSES_JUIZ:
                veredito[d["id"]] = d["classe"]
    return banda_titulo, veredito


def mapeia(classe, tem_titulo):
    if classe == "real":
        return "titulada" if tem_titulo else "sem-titulo"
    return classe  # so-titulo, ancora-ruido ja sao do vocabulario


def main():
    dry = "--dry" in sys.argv
    parcial = "--parcial" in sys.argv
    banda_titulo, veredito = carrega()
    julgados = {k: mapeia(v, banda_titulo.get(k, True))
                for k, v in veredito.items() if k in banda_titulo}
    faltam = len(banda_titulo) - len(julgados)

    ruins = {v for v in julgados.values()} - PERMITIDOS
    if ruins:
        sys.exit(f"ABORTA: valores fora do CHECK: {ruins}")

    print(f"banda={len(banda_titulo)} julgados_validos={len(julgados)} faltam={faltam}")
    print("dist_checkpoint:", dict(Counter(julgados.values())))
    if dry:
        print("--dry: nada escrito.")
        return
    if faltam > 0 and not parcial:
        sys.exit(f"GATE: banda incompleta ({faltam} faltando). "
                 f"Relance juiz_banda.py ou use --parcial. Nada escrito.")

    csv = "".join(f"{sid},{cl}\n" for sid, cl in julgados.items())
    sql = ("begin; create temp table _juiz_tmp(id uuid, classe text); "
           "copy _juiz_tmp(id,classe) from stdin csv; "
           "update acervo.secao s set qualidade=t.classe "
           "from _juiz_tmp t where t.id=s.id; commit;")
    out = psql(sql, stdin=csv)
    print("gravado:", (out.strip().splitlines() or ["ok"])[-1])

    print("\n=== DISTRIBUICAO CORRIGIDA (acervo.secao.qualidade) ===")
    print(psql("select coalesce(qualidade,'<null>'), count(*) "
               "from acervo.secao group by 1 order by 2 desc;").strip())
    print("\n=== dentro da banda <40 ===")
    print(psql(
        "with tk as (select secao_id, sum(token_count) toks from acervo.trecho "
        "where secao_id is not null group by secao_id) "
        "select s.qualidade, count(*) from acervo.secao s join tk on tk.secao_id=s.id "
        "where tk.toks<40 group by 1 order by 2 desc;").strip())


if __name__ == "__main__":
    main()
