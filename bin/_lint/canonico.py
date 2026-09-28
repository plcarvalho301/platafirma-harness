"""canonico — ADR e spec não citam minuta (ordem do dono, 28/09/2026; régua arq:0028).

O canônico é o documento que se consulta para saber o que vale agora, e não carrega o log
da própria mudança (arq:0028). Minuta é deliberação em trânsito: morre na formalização e o
número se reusa. ADR que cite «fechando a minuta 0038» passa a apontar para outra minuta
quando 0038 renasce com outro assunto (a arq:0115 apontou para o processamento de texto,
#3060). O dente é este: o pre-commit recusa linha ACRESCENTADA a ADR ou spec que cite
minuta por número, ou pela decisão da minuta («resolvidas na minuta»).

Escopo do detector:
  - arquivos: `.md` dentro de uma pasta `decisions/` (ADR, de qualquer família) e
    `spec_*.md` (spec);
  - só as linhas que o commit acrescenta: menção legada não trava edição de outro
    trecho, e a limpeza das 25 ADRs de 28/09 (inteligencia) já tirou o estoque;
  - a minuta como instrumento (a espécie, o verbo `minuta ler`, o molde «minuta NNNN» sem
    número) não é citação e passa.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple

from .resultado import Apontamento

# «minuta 0038», «minuta nº 12», «minutas 0012», «minuta 0038, A1»
_RE_NUMERO = re.compile(r"\bminutas?\s+(?:n[º°o.]\s*)?\d{1,4}\b", re.I)
# «resolvidas na minuta», «fechada na minuta», «decidido na minuta», «conforme a minuta»
_RE_DECISAO = re.compile(
    r"\b(?:resolvid|fechad|decidid|aprovad|acordad)\w*\s+n[ao]s?\s+minutas?\b"
    r"|\bfechando\s+a\s+minuta\b|\bconforme\s+a\s+minuta\b",
    re.I,
)
_RE_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

CURA = ("tirar a citação: pôr a decisão do dono com data e as cadeiras que tinham posição, "
        "ou o canônico que fechou a matéria (arq:0028)")


def e_canonico(caminho: str) -> bool:
    p = PurePosixPath(caminho)
    if p.suffix.lower() != ".md":
        return False
    if p.name.startswith("spec_"):
        return True
    return "decisions" in p.parts[:-1]


def citacao(linha: str) -> Optional[str]:
    """O trecho que cita minuta, ou None."""
    m = _RE_NUMERO.search(linha) or _RE_DECISAO.search(linha)
    return m.group(0) if m else None


def _linhas_acrescentadas(raiz: Path, arquivo: str) -> list[tuple[int, str]]:
    p = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--no-color", "--", arquivo],
        cwd=raiz, capture_output=True, text=True,
    )
    if p.returncode != 0:
        return []
    saida: list[tuple[int, str]] = []
    n = 0
    for bruta in p.stdout.splitlines():
        m = _RE_HUNK.match(bruta)
        if m:
            n = int(m.group(1))
            continue
        if bruta.startswith("+++"):
            continue
        if bruta.startswith("+"):
            saida.append((n, bruta[1:]))
            n += 1
    return saida


def canonicos_no_stage(raiz: Path | str) -> list[str]:
    p = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=raiz, capture_output=True, text=True,
    )
    nomes = [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []
    return [n for n in nomes if e_canonico(n)]


def bloqueantes_no_stage(raiz: Path | str) -> Tuple[list[Apontamento], Optional[str]]:
    """Para o pre-commit: (apontamentos bloqueantes, aviso). Nunca lança."""
    raiz = Path(raiz)
    achados: list[Apontamento] = []
    for arquivo in canonicos_no_stage(raiz):
        for n, texto in _linhas_acrescentadas(raiz, arquivo):
            trecho = citacao(texto)
            if trecho:
                achados.append(Apontamento(
                    arquivo, n, f"canônico cita minuta: «{trecho}»", CURA,
                    severidade="bloqueante"))
    return achados, None
