"""`acervo retirar biblioteca conceito <slug> --motivo "…" [--em <slug>] [--apply] [--json]` (DT 807).

- sem --em: apaga do tesauro o conceito sem obra, sem filho e sem aresta, com a ficha;
- com --em <que fica>: funde o conceito no que fica (obras, filhos, arestas e rótulos passam a ele) e apaga o
  absorvido com a ficha.

Nada fica marcado como retirado ou fundido: o que existiu fica no export versionado do tesauro, que o --apply
regenera no clone de conhecimento (commit e push são de quem gravou). Voltar é definir o conceito de novo.

Plano seco sem --apply. Saída: 0 fez ou planejou aprovado · 1 plano reprovado ou recusa de mérito · 2 uso ·
3 serviço fora · 4 política.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pipeline_cliente as pc

USO = 'uso: acervo retirar biblioteca conceito <slug> --motivo "…" [--em <slug>] [--apply] [--json]'
ACERVO = Path(__file__).resolve().parents[1] / "acervo"


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


def _exportar() -> str:
    """Regenera o export versionado do tesauro (o mesmo `acervo exportar` que o definir e o relacionar chamam)."""
    r = subprocess.run(["bash", str(ACERVO), "exportar"], capture_output=True, text=True, check=False)
    saida = (r.stdout + r.stderr).strip()
    if r.returncode:
        return f"export NÃO regenerado — rode `acervo exportar` e faça o commit: {saida[-300:]}"
    i = saida.rfind("bancada:")
    return "export regenerado no clone — commit e push são seus: " + (saida[i:] if i >= 0 else saida[-300:])


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "retirar" or argv[1].startswith("-"):
        print(USO, file=sys.stderr)
        return 2
    slug, resto = argv[1], argv[2:]
    motivo = _valor(resto, "--motivo")
    em = _valor(resto, "--em")
    if not motivo:
        print(f"acervo retirar biblioteca conceito: falta --motivo\n{USO}", file=sys.stderr)
        return 2
    aplicar = "--apply" in resto
    corpo = {"motivo": motivo, "autor": _autor(), "aplicar": aplicar}
    if em:
        corpo["em"] = em
    rota = "fusao" if em else "retirada"
    try:
        plano = pc.chamar("POST", f"/acervo/conceitos/{urllib.parse.quote(slug, safe='')}/{rota}", corpo)
    except pc.Falha as e:
        print(f"acervo retirar biblioteca conceito {slug}: {e.mensagem}", file=sys.stderr)
        return e.codigo
    print(json.dumps(plano, ensure_ascii=False, indent=2))
    if plano.get("modo") == "plano":
        print("plano seco — repita com --apply para gravar" if plano.get("aprovado")
              else "REPROVADO — nada gravado", file=sys.stderr)
    elif aplicar:
        print(_exportar(), file=sys.stderr)
    return 0 if plano.get("aprovado", True) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
