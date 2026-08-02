#!/usr/bin/env python3
"""Gera o artefato classe B (copiado-pra-fora) com carimbo de frescor — spec S2.

    python3 tooling/export/carimbar.py skills/osint/SKILL.md [outro/SKILL.md ...]

Saída: dist/<nome-da-skill>/SKILL.md (+ dist/<nome-da-skill>.zip quando houver zip).
O que sai daqui é o que se sobe ao claude.ai, bit a bit.

Regras da spec que este script materializa:
- carimbo = origem: <repo>@<blob_sha> + fonte: <path> + sincronizado_em: <ISO 8601>;
- granularidade é BLOB, nunca commit: comparar por commit acusa defasagem a cada
  mudança de arquivo vizinho, e falso positivo crônico mata o alarme;
- carimbo à mão é proibido: mente por construção. Este script é o único gerador.

Arquivo sujo ou não commitado aborta: carimbar working copy é a própria mentira que
o carimbo existe para impedir.
"""
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def carimbar(rel: str) -> Path:
    caminho = Path(rel)
    if not caminho.is_file():
        sys.exit(f"não existe: {rel}")
    if git("status", "--porcelain", "--", rel):
        sys.exit(f"sujo ou não commitado: {rel} — commite antes de carimbar")

    blob = git("rev-parse", f"HEAD:{rel}")
    repo = Path(git("rev-parse", "--show-toplevel")).name
    agora = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    texto = caminho.read_text(encoding="utf-8")
    if not texto.startswith("---\n"):
        sys.exit(f"sem frontmatter: {rel}")
    fim = texto.index("\n---\n", 3) + 1
    carimbo = (
        f"origem: {repo}@{blob}\n"
        f"fonte: {rel}\n"
        f"sincronizado_em: {agora}\n"
    )
    saida_texto = texto[:fim] + carimbo + texto[fim:]

    destino = Path("dist") / caminho.parent.name / caminho.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida_texto, encoding="utf-8")

    pacote = destino.parent.with_suffix(".zip")
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(destino, f"{destino.parent.name}/{destino.name}")

    print(f"{destino}  ({repo}@{blob[:12]})")
    print(f"{pacote}")
    return destino


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for alvo in sys.argv[1:]:
        carimbar(alvo)
