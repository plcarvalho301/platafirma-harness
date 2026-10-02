"""casa_por_caminho — documento de casa não se lê pelo caminho do arquivo (arq:0115 §11.3).

Desde arq:0115 o documento de casa é ficha do acervo, e o repositório que o suporta,
platafirma-casa, não é unidade de release (§1.2). Verbo, skill ou instrução de agente que lia
o suporte por caminho quebra no movimento, e a cura é ler pelo acervo (§11.3). O incidente
#3225 foi esse caso: `minuta ler` lia `<release>/casa/minuta`, que não existe, e respondia
«não encontrada» para uma minuta publicada. Nada barrava a forma no commit.

Formas que o detector pega numa linha:
  - o repositório extinto de arquitetura seguido de caminho ou de `@` (o suporte de antes);
  - a pasta `casa` da release, em código: `release() / "casa"` e `current/casa`.
A instância (`/srv/platafirma/casa`) e a bancada de main da casa, que os atos de minuta usam
para ESCREVER, não são leitura de produção e não entram.

Dois usos: o pre-commit recusa a forma em linha ACRESCENTADA (bloqueante: o estoque legado
não trava a edição de outro trecho); `lint fossil` relata o estoque, como aviso.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .canonico import _linhas_acrescentadas
from .resultado import Apontamento

_EXTINTO = "platafirma-" + "arquitetura"  # partido: o próprio módulo não casa a forma
_RE = re.compile(
    re.escape(_EXTINTO) + r"[/@][\w.\-]"
    r"|\brelease\(\)\s*/\s*[\"']casa[\"']"
    r"|\bcurrent/casa\b"
)
# o detector e o teste dele carregam as formas de propósito
ISENTOS = ("bin/_lint/casa_por_caminho.py", "controle/tests/test_contrato_casa_por_caminho.py")
CURA = ("ler pelo acervo: `acervo ler casa <espécie> <chave>` ou `acervo listar casa "
        "<espécie>` (arq:0115 §11.3); ponteiro para documento de casa cita a chave, não o "
        "caminho (§3.3)")
ID = "CASA_POR_CAMINHO"


def forma(linha: str) -> Optional[str]:
    """O trecho que lê documento de casa por caminho, ou None."""
    m = _RE.search(linha)
    return m.group(0) if m else None


def _no_stage(raiz: Path) -> list[str]:
    p = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=raiz, capture_output=True, text=True,
    )
    nomes = [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []
    return [n for n in nomes if n not in ISENTOS]


def bloqueantes_no_stage(raiz: Path | str) -> Tuple[list[Apontamento], Optional[str]]:
    """Para o pre-commit: (apontamentos bloqueantes, aviso). Nunca lança."""
    raiz = Path(raiz)
    achados: list[Apontamento] = []
    for arquivo in _no_stage(raiz):
        for n, texto in _linhas_acrescentadas(raiz, arquivo):
            trecho = forma(texto)
            if trecho:
                achados.append(Apontamento(
                    arquivo, n, f"lê documento de casa por caminho: «{trecho}»", CURA,
                    severidade="bloqueante", id=ID))
    return achados, None


def _arquivos(raiz: Path, alvo: Optional[str]) -> list[Path]:
    base = (raiz / alvo) if alvo else raiz
    if base.is_file():
        return [base]
    p = subprocess.run(["git", "ls-files", "-z", "--", str(base)], cwd=raiz,
                       capture_output=True, text=True)
    if p.returncode == 0 and p.stdout:
        return [raiz / x for x in p.stdout.split("\0") if x]
    return [f for f in base.rglob("*") if f.is_file() and ".git" not in f.parts]


def varrer(raiz: Path | str, alvo: Optional[str] = None) -> list[Apontamento]:
    """Para `lint fossil`: o estoque, um aviso por linha. Pula binário e arquivo grande."""
    raiz = Path(raiz)
    achados: list[Apontamento] = []
    for arq in _arquivos(raiz, alvo):
        try:
            rel = str(arq.relative_to(raiz))
        except ValueError:
            rel = arq.name
        if rel in ISENTOS:
            continue
        try:
            if arq.stat().st_size > 1_000_000:
                continue
            bruto = arq.read_bytes()
        except OSError:
            continue
        if b"\0" in bruto[:8192]:
            continue
        for i, linha in enumerate(bruto.decode("utf-8", "replace").splitlines(), 1):
            trecho = forma(linha)
            if trecho:
                achados.append(Apontamento(
                    rel, i, f"lê documento de casa por caminho: «{trecho}»", CURA,
                    severidade="aviso", id=ID))
    return achados
