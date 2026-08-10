# estado_leitura — le controle/estado.json pro lado da tela.
# capacidade: expediente
# dono: claudinho-TI
"""Único ponto de leitura do arquivo que o agregador escreve. Ausência do
arquivo (agregador nunca rodou ainda) ou JSON corrompido (leitura no meio de
uma escrita não-atômica de outra versão, ou disco cheio) nunca vira exceção
pra cima — vira dict vazio, e cada bloco de `render.py` já trata chave
ausente como "sem leitura" (idade "—", chip caveat), nunca como saúde."""

from __future__ import annotations

import json
from pathlib import Path


def carregar_estado(caminho: Path) -> dict:
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return {}
    return dados if isinstance(dados, dict) else {}
