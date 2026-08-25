#!/usr/bin/env python3
"""carga incremental — enriquece obras JÁ catalogadas (stubs) com a classificação.

O caminho que o `migrar-acervo` (migrador full-schema) não faz e por isso #2477: em
schema populado a obra já existe — a catalogação (`carregar-acervo`) cria o stub com
titulo=nome-do-arquivo e objeto/objeto_id/arquivo nulos, faceta nenhuma. Aqui a linha
de `Classificacao` vira UPDATE desse stub. Nunca rebuild, nunca toca vocabulário; a FK
(dominio/especie/subdominio) é resolvida contra o schema vivo.

Casamento da obra:
  objeto = 'acervo/'||sha256                          (já classificada — idempotente)
  OU (objeto IS NULL AND titulo = nome-sem-extensao)  (o stub fresco da catalogacao)

DRY-RUN por default; `--apply` escreve numa transacao. Slug de vocabulario que nao
existe no schema vivo ABORTA antes de escrever, nomeando — nunca grava FK nula em
silencio (o erro no1 da conferencia). Classificador: curador `time-platafirma`.
"""
import csv
import os
import subprocess
import sys

CUR = "00000000-0000-0000-0000-000000000002"  # curador time-platafirma
PG = ["docker", "exec", "-i", "rag-extractor-pg", "psql", "-U", "rag", "-d", "rag_extractor"]


def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def psql(sql, tuples_only=False):
    args = PG + (["-tAF|"] if tuples_only else []) + ["-v", "ON_ERROR_STOP=1", "-c", sql]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr)
        raise SystemExit(f"carga_incremental: psql falhou (rc={r.returncode})")
    return r.stdout


def g(row, k):
    return (row.get(k) or "").strip()


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        raise SystemExit("uso: carga_incremental.py <classificacao.csv> [--apply]")
    with open(paths[0], newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f)]
    if not rows:
        raise SystemExit("carga_incremental: classificacao vazia")

    # --- valida vocabulario contra o schema vivo, antes de qualquer escrita -----
    def existe(tabela, valores):
        if not valores:
            return set()
        lst = ",".join(q(v) for v in valores)
        out = psql(f"select slug from acervo.{tabela} where slug in ({lst})", tuples_only=True)
        return {l.strip() for l in out.splitlines() if l.strip()}

    doms = {g(r, "dominio_sugerido") for r in rows if g(r, "dominio_sugerido")}
    esps = {g(r, "especie_sugerida") for r in rows if g(r, "especie_sugerida")}
    subs = {g(r, "subdominio_sugerido") for r in rows if g(r, "subdominio_sugerido")}
    faltam = (
        [f"dominio '{v}'" for v in sorted(doms - existe("dominio", doms))]
        + [f"especie '{v}'" for v in sorted(esps - existe("especie_tipo", esps))]
        + [f"subdominio '{v}'" for v in sorted(subs - existe("subdominio", subs))]
    )
    if faltam:
        raise SystemExit("RECUSADO — vocabulario inexistente no schema vivo:\n  " + "\n  ".join(faltam))

    # --- monta um UPDATE por obra ----------------------------------------------
    stmts = []
    for r in rows:
        arq = g(r, "arquivo")
        if not arq:
            raise SystemExit("RECUSADO — linha sem coluna 'arquivo'")
        stem = os.path.splitext(arq)[0]
        sha = g(r, "sha256")
        sets = [
            f"titulo={q(g(r, 'titulo') or stem)}",
            f"arquivo={q(arq)}",
            f"emitido_por={q(g(r, 'emitido_por') or '{}')}::text[]",
            f"id_canonico=NULLIF({q(g(r, 'id_canonico'))},'')",
            f"publicacao=NULLIF({q(g(r, 'publicacao'))},'')",
            f"anotacao=NULLIF({q(g(r, 'anotacao'))},'')",
            f"classificado_por={q(CUR)}::uuid",
            "classificado_em=now()",
        ]
        if sha:
            sets.append(f"objeto={q('acervo/' + sha)}")  # objeto_id é gerado a partir de objeto
        if g(r, "dominio_sugerido"):
            sets.append(f"dominio_id=(select id from acervo.dominio where slug={q(g(r, 'dominio_sugerido'))})")
        if g(r, "especie_sugerida"):
            sets.append(f"especie_id=(select id from acervo.especie_tipo where slug={q(g(r, 'especie_sugerida'))})")
        if g(r, "subdominio_sugerido"):
            sets.append(f"subdominio_id=(select id from acervo.subdominio where slug={q(g(r, 'subdominio_sugerido'))})")
        if sha:
            where = f"(objeto={q('acervo/' + sha)} or (objeto is null and titulo={q(stem)}))"
        else:
            where = f"(titulo={q(stem)})"
        stmts.append(f"update acervo.obra set {', '.join(sets)} where {where};")

    sql = "begin;\n" + "\n".join(stmts) + "\ncommit;"

    if not apply:
        print("(dry-run) UPDATE(s) que rodariam:\n")
        print(sql)
        print(f"\n{len(stmts)} obra(s) na classificacao. Rode com --apply.")
        return

    # executa e mede o casamento pos-escrita
    print(psql(sql))
    casadas = ",".join(q("acervo/" + g(r, "sha256")) for r in rows if g(r, "sha256"))
    if casadas:
        out = psql(
            f"select titulo, coalesce(array_to_string(emitido_por,', '),'') "
            f"from acervo.obra where objeto in ({casadas}) order by titulo",
            tuples_only=True,
        )
        print("obras enriquecidas:")
        for l in out.splitlines():
            if l.strip():
                print("  " + l)
    print(f"APLICADO — {len(stmts)} obra(s).")


if __name__ == "__main__":
    main()
