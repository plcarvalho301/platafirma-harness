"""card — verificacao de corpo de card conforme arq:0096."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from .resultado import Apontamento

CAMPOS_STORY = [
    "Negócio:",
    "Ambiente:",
    "Onde:",
    "Passos:",
    "Aceite:",
    "Travas:",
    "Entrega:",
    "Referencial:",
    "Raio de ataque:",
    "Comportamento esperado:",
]

CAMPOS_TASK = [
    "Problema encontrado:",
    "Solução proposta:",
    "Referencial:",
    "Raio de ataque:",
    "Comportamento esperado:",
]

CAMPOS_FEATURE = [
    "Problema:",
    "Resultado:",
    "Medida:",
    "Fora:",
    "Sai quando:",
    "Continuidade:",
    "Quebra:",
]

CAMPOS_EPIC = [
    "Problema:",
    "Resultado:",
    "Medida:",
    "Fora:",
    "Quebra:",
]


def detectar_nivel(texto: str) -> str:
    """Detecta se e story, task, feature ou epic a partir do cabecalho do card."""
    primeiras = texto.splitlines()[:5]
    for linha in primeiras:
        low = linha.lower()
        if "task" in low:
            return "task"
        if "feature" in low:
            return "feature"
        if "épico" in low or "epico" in low or "epic" in low:
            return "epic"
        if "story" in low:
            return "story"
    return "story"


def verificar_card(
    alvo: str = "-",
    texto: Optional[str] = None,
    raiz: Optional[Path | str] = None,
) -> list[Apontamento]:
    """Verifica se o card atende as secoes obrigatorias de seu nivel segundo arq:0096."""
    if texto is not None:
        conteudo = texto
        nome_alvo = alvo or "-"
    elif alvo == "-":
        conteudo = sys.stdin.read()
        nome_alvo = "-"
    else:
        caminho = Path(alvo)
        if not caminho.is_absolute() and raiz:
            caminho = Path(raiz) / alvo
        try:
            conteudo = caminho.read_text(encoding="utf-8", errors="replace")
            nome_alvo = alvo
        except OSError as e:
            return [
                Apontamento(
                    alvo,
                    1,
                    f"nao consegui ler arquivo do card: {e}",
                    "fornecer arquivo legivel ou '-' para stdin",
                    severidade="bloqueante",
                )
            ]

    nivel = detectar_nivel(conteudo)
    if nivel == "task":
        campos_esperados = CAMPOS_TASK
    elif nivel == "feature":
        campos_esperados = CAMPOS_FEATURE
    elif nivel == "epic":
        campos_esperados = CAMPOS_EPIC
    else:
        campos_esperados = CAMPOS_STORY

    apontamentos: list[Apontamento] = []

    # Procura cada rotulo no texto
    linhas = conteudo.splitlines()
    for rotulo in campos_esperados:
        presente = False
        rotulo_sem_dois_pontos = rotulo.rstrip(":")
        for linha in linhas:
            s = linha.strip()
            # Casa com 'Rotulo:' ou '**Rotulo:**' ou 'Rotulo' no inicio
            if s.startswith(rotulo) or s.startswith(f"**{rotulo}**") or s.startswith(f"**{rotulo_sem_dois_pontos}**:") or s.startswith(f"{rotulo_sem_dois_pontos}:"):
                presente = True
                break
        if not presente:
            apontamentos.append(
                Apontamento(
                    nome_alvo,
                    1,
                    f"secao obrigatoria '{rotulo_sem_dois_pontos}' ausente no corpo de {nivel}",
                    f"acrescentar a secao '{rotulo}' conforme arq:0096",
                    severidade="aviso",
                    id=f"CARD_{rotulo_sem_dois_pontos.upper()}",
                )
            )

    return apontamentos
