#!/usr/bin/env python3
"""Gera o artefato classe B (copiado-pra-fora) com carimbo de frescor — spec S2.

    python3 tooling/export/carimbar.py skills/osint/SKILL.md [outra/SKILL.md ...]

Saída: dist/<nome-da-skill>/ com o SKILL.md carimbado e os arquivos-irmãos da skill
(ex.: reference/), mais dist/<nome-da-skill>.zip com a pasta inteira.
O que sai daqui é o que se sobe ao claude.ai, bit a bit.

Regras da spec que este script materializa:
- carimbo = origem: <repo>@<blob_sha> + fonte: <path> + sincronizado_em: <ISO 8601>;
- skill multi-arquivo: o SKILL.md carrega o carimbo, e os irmãos entram em `bundle:`
  com o blob de cada um — assim uma mudança em qualquer arquivo do pacote muda o
  carimbo (frescor por blob vale para o pacote inteiro, não só o SKILL.md). Skill de
  arquivo único não ganha `bundle:` e sai idêntica ao formato anterior;
- granularidade é BLOB, nunca commit: comparar por commit acusa defasagem a cada
  mudança de arquivo vizinho, e falso positivo crônico mata o alarme;
- carimbo à mão é proibido: mente por construção. Este script é o único gerador.

Arquivo sujo ou não commitado (qualquer um dos rastreados da skill) aborta: carimbar
working copy é a própria mentira que o carimbo existe para impedir.
"""
import shutil
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
    if caminho.name != "SKILL.md":
        sys.exit(f"aponte para um SKILL.md, não para {rel}")
    if not caminho.is_file():
        sys.exit(f"não existe: {rel}")

    skill_dir = caminho.parent  # ex.: skills/prosa

    # Fonte-verdade do que entra no pacote: os arquivos RASTREADOS da skill.
    rastreados = [l for l in git("ls-files", "--", str(skill_dir)).splitlines() if l]
    if rel not in rastreados:
        sys.exit(f"não rastreado: {rel} — commite antes de carimbar")
    for arq in rastreados:
        if git("status", "--porcelain", "--", arq):
            sys.exit(f"sujo ou não commitado: {arq} — commite antes de carimbar")
    irmaos = [p for p in rastreados if p != rel]

    repo = Path(git("rev-parse", "--show-toplevel")).name
    blob = git("rev-parse", f"HEAD:{rel}")
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
    if irmaos:
        carimbo += "bundle:\n"
        for irmao in irmaos:
            iblob = git("rev-parse", f"HEAD:{irmao}")
            dentro = Path(irmao).relative_to(skill_dir).as_posix()
            carimbo += f"  - {dentro}@{iblob}\n"

    saida_texto = texto[:fim] + carimbo + texto[fim:]

    destino_dir = Path("dist") / skill_dir.name
    if destino_dir.exists():
        shutil.rmtree(destino_dir)
    destino_dir.mkdir(parents=True, exist_ok=True)

    destino_skill = destino_dir / caminho.name
    destino_skill.write_text(saida_texto, encoding="utf-8")

    # Irmãos entram bit a bit, do working tree já conferido limpo (== blob de HEAD).
    for irmao in irmaos:
        dentro = Path(irmao).relative_to(skill_dir)
        alvo = destino_dir / dentro
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(irmao, alvo)

    pacote = destino_dir.with_suffix(".zip")
    if pacote.exists():
        pacote.unlink()
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(destino_dir.rglob("*")):
            if arq.is_file():
                arc = f"{destino_dir.name}/{arq.relative_to(destino_dir).as_posix()}"
                z.write(arq, arc)

    print(f"{destino_skill}  ({repo}@{blob[:12]}, {1 + len(irmaos)} arquivo(s))")
    print(f"{pacote}")
    return destino_skill


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for alvo in sys.argv[1:]:
        carimbar(alvo)
