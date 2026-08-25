#!/usr/bin/env python3
"""Gera o seed de acervo.stack a partir do stacks.json — serializacao JSON FIEL.

Corrige o defeito do seed anterior (#2703): rotas/gate entravam double-encoded
(to_jsonb de string que ja tinha aspas -> "\\"x\\"") e compose-lista entrava como
repr Python ('[''a'', ''b'']') em vez de JSON. Aqui todo campo estruturado passa por
json.dumps e entra como ::jsonb ou text puro, sem embrulho manual.

Contrato das colunas (schema acervo.stack):
  slug text, papel text, critico bool, repo text, compose text (string OU json-lista
  serializada), rotas jsonb, segredos jsonb, reversao jsonb, gate jsonb, profiles jsonb,
  nota text.

`compose` e text no schema: string simples entra crua; lista entra como JSON serializado
(o deploy ja aceita "string ou lista": lista vira varios -f). rotas/gate/segredos/
reversao/profiles sao jsonb: entram como json.dumps(...)::jsonb, valor null vira SQL NULL.

Uso: gerar_seed_stack.py <stacks.json>  > 0076c_acervo_stack_seed.sql
"""
import json
import sys


def sql_str(v):
    """Literal SQL de texto, com escape de aspa simples. None -> NULL."""
    if v is None:
        return "null"
    return "'" + str(v).replace("'", "''") + "'"


def sql_jsonb(v):
    """Valor jsonb: json.dumps + cast, com escape de aspa simples. None -> NULL."""
    if v is None:
        return "null"
    return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"


def sql_compose(v):
    """compose e coluna text: string crua; lista vira JSON serializado (text)."""
    if v is None:
        return "null"
    if isinstance(v, list):
        return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'"
    return sql_str(v)


def main(argv):
    if len(argv) != 1:
        sys.stderr.write(__doc__)
        return 2
    with open(argv[0], encoding="utf-8") as fh:
        doc = json.load(fh)
    stacks = doc["stacks"]

    linhas = []
    for slug, s in stacks.items():
        linhas.append("  (" + ",".join([
            sql_str(slug),
            sql_str(s.get("papel")),
            "true" if s.get("critico") else "false",
            sql_str(s.get("repo")),
            sql_compose(s.get("compose")),
            sql_jsonb(s.get("rotas")),
            sql_jsonb(s.get("segredos")),
            sql_jsonb(s.get("reversao")),
            sql_jsonb(s.get("gate")),
            sql_jsonb(s.get("profiles")),
            sql_str(s.get("_nota")),
        ]) + ")")

    out = []
    out.append("-- 0076c_acervo_stack_seed.sql — seed dos %d stacks. GERADO de stacks.json"
               % len(stacks))
    out.append("-- por gerar_seed_stack.py (#2703). Serializacao JSON FIEL: rotas/gate/segredos/")
    out.append("-- reversao/profiles via json.dumps::jsonb; compose-lista como JSON, nao repr.")
    out.append("-- Idempotente: on conflict (slug) do UPDATE (nao 'do nothing' — o ponto e")
    out.append("-- corrigir linha ja existente com serializacao errada).")
    out.append("begin;")
    out.append("")
    out.append("insert into acervo.stack "
               "(slug,papel,critico,repo,compose,rotas,segredos,reversao,gate,profiles,nota) values")
    out.append(",\n".join(linhas))
    out.append("on conflict (slug) do update set")
    for col in ("papel", "critico", "repo", "compose", "rotas", "segredos",
                "reversao", "gate", "profiles", "nota"):
        out.append(f"  {col} = excluded.{col},")
    out[-1] = out[-1].rstrip(",") + ";"
    out.append("")
    out.append("commit;")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
