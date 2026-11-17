"""`acervo retirar|restaurar biblioteca conceito <slug> --motivo "…" [--em <slug>] [--apply] [--json]` (DT 807).

- retirar: tira do tesauro o conceito sem obra, sem filho e sem aresta, com volta (`acervo restaurar`);
- retirar --em <que fica>: funde o conceito no que fica (obras, filhos, arestas e rótulos passam a ele) e o
  tira do tesauro sem volta;
- restaurar: devolve o conceito retirado com o mesmo id, os rótulos e a ficha; o fundido não volta.

Plano seco sem --apply. Saída: 0 fez ou planejou aprovado · 1 plano reprovado ou recusa de mérito · 2 uso ·
3 serviço fora · 4 política.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

import pipeline_cliente as pc

USO = ('uso: acervo retirar biblioteca conceito <slug> --motivo "…" [--em <slug>] [--apply] [--json]\n'
       '     acervo restaurar biblioteca conceito <slug> --motivo "…" [--apply] [--json]')


def _valor(argv: list[str], nome: str) -> str | None:
    if nome in argv:
        i = argv.index(nome)
        return argv[i + 1] if i + 1 < len(argv) else None
    for a in argv:
        if a.startswith(nome + "="):
            return a.split("=", 1)[1]
    return None


def _autor() -> str:
    cad = (os.environ.get("PF_CADEIRA") or os.environ.get("PF_CONTA") or "").strip().lower()
    autor = cad.removeprefix("claudinho-").removeprefix("claudinha-") or "dados"
    return "time-platafirma" if autor in {"engenharia", "ti", "ia", "arquiteto", "seguranca"} else autor


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("retirar", "restaurar") or argv[1].startswith("-"):
        print(USO, file=sys.stderr)
        return 2
    ato, slug, resto = argv[0], argv[1], argv[2:]
    motivo = _valor(resto, "--motivo")
    em = _valor(resto, "--em")
    if not motivo:
        print(f"acervo {ato} biblioteca conceito: falta --motivo\n{USO}", file=sys.stderr)
        return 2
    if em and ato == "restaurar":
        print("acervo restaurar biblioteca conceito: --em só vale para retirar (fusão)", file=sys.stderr)
        return 2
    rota = {"retirar": "fusao" if em else "retirada", "restaurar": "restauracao"}[ato]
    corpo = {"motivo": motivo, "autor": _autor(), "aplicar": "--apply" in resto}
    if em:
        corpo["em"] = em
    try:
        plano = pc.chamar("POST", f"/acervo/conceitos/{urllib.parse.quote(slug, safe='')}/{rota}", corpo)
    except pc.Falha as e:
        print(f"acervo {ato} biblioteca conceito {slug}: {e.mensagem}", file=sys.stderr)
        return e.codigo
    print(json.dumps(plano, ensure_ascii=False, indent=2))
    if plano.get("modo") == "plano":
        print("plano seco — repita com --apply para gravar" if plano.get("aprovado")
              else "REPROVADO — nada gravado", file=sys.stderr)
    return 0 if plano.get("aprovado", True) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
