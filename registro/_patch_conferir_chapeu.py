#!/usr/bin/env python3
"""Ensina `conferir peca` a aceitar o placeholder {chapeu} no artefato.

O fluxo de duas chamadas (P2) introduziu peças de chapéu cujo artefato resolve
{chapeu} alem de {cadeira} (ex.: personas/chapeus/{cadeira}/catalogo-{chapeu}.md).
O validador so admitia {cadeira} e reprovava as novas. read->assert->write.
"""
from __future__ import annotations
import pathlib

ALVO = pathlib.Path.home() / "AI" / "platafirma-harness" / "bin" / "conferir"
src = ALVO.read_text(encoding="utf-8")

velho = (
    '    if "{" in path:\n'
    '        resto = re.sub(r"\\{cadeira\\}", "*", path)\n'
    '        if "{" in resto:\n'
    '            return "placeholder desconhecido: so {cadeira} e admitido"\n'
)
novo = (
    '    if "{" in path:\n'
    '        resto = re.sub(r"\\{cadeira\\}|\\{chapeu\\}", "*", path)\n'
    '        if "{" in resto:\n'
    '            return "placeholder desconhecido: so {cadeira} e {chapeu} sao admitidos"\n'
)
assert src.count(velho) == 1, f"esperava 1 ocorrencia do bloco, achei {src.count(velho)}"
ALVO.write_text(src.replace(velho, novo), encoding="utf-8")
print(f"OK — {ALVO}: placeholder {{chapeu}} admitido")
