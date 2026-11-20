"""casa_por_caminho — bloqueia citações a caminhos e artefatos da casa velha (F4073, #4348, #4414).

A casa nova mora na Olaria e no repositório platafirma-casa. Código, skill,
configuração ou documento em core, harness, posto e conhecimento não pode citar o
repositório extinto de arquitetura, as pastas numeradas da casa velha
(1-orientacao a 6-artefato), originais/, abertura/dono.md nem var/abertura-publicada.

Dois usos: o pre-commit recusa a forma em linha ACRESCENTADA (bloqueante); `varrer`
(usado por `lint fossil` e pelo portão) varre a árvore inteira.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .resultado import Apontamento

# Literais partidos para o próprio módulo não disparar o detector nem o pre-commit vigente.
_EXTINTO = "platafirma-" + "arquitetura"
_PASTAS_NUM = (
    r"(?<![-\w])(?:"
    + "1-" + "orientacao"
    + "|" + "2-" + "comportamento"
    + "|" + "3-" + "(?:estrutura|sistema|organizacao)"
    + "|" + "4-" + "(?:operacao|capacidade|processo)"
    + "|" + "5-" + "(?:conhecimento|execucao|referencia)"
    + "|" + "6-" + "artefato"
    + r")(?![-\w])"
)
_ORIGINAIS = r"(?<![-\w])" + "origi" + "nais/"
_DONO_MD = r"(?<![-\w])" + "abertura/" + r"dono\.md(?![-\w])"
_ABERTURA_PUB = r"(?<![-\w])" + "var/abertura-" + r"publicada(?![-\w])"

_RE = re.compile(
    re.escape(_EXTINTO) + r"[/@][\w.\-]"
    + r"|" + _PASTAS_NUM
    + r"|" + _ORIGINAIS
    + r"|" + _DONO_MD
    + r"|" + _ABERTURA_PUB
)

# O detector e o teste dele carregam as formas de propósito.
ISENTOS_SUFIXO = (
    "bin/_lint/casa_por_caminho.py",
    "controle/tests/test_contrato_casa_por_caminho.py",
)
# Migrações SQL históricas já aplicadas em produção são imutáveis (trava do #4348).
ISENTOS_MIGRACAO_SQL = (
    "rag/db/init/159_schema_analise.sql",
    "rag/db/init/161_grant_mineracao_ocel.sql",
)
# Arquivos em transição pertencentes a F4376 / E3650 (retirada do suporte da casa velha,
# casa-site, vault-ontologia e bloco temporário de tombamento do posto).
ISENTOS_TRANSICAO_E3650 = (
    "bin/acervo",
    "bin/_acervo/_identidade.py",
    "bin/_acervo/_suporte.py",
    "bin/_acervo/listar",
    "bin/curar",
    "bin/repo",
    "registro/venvs.json",
    "casa-site/publicar.py",
    "casa-site/tests/test_publicar.py",
    "rag/tests/test_casa_admissao.py",
    "posto/AGENTS.md",
    "posto/gerado/claude-ai/preferencias.md",
    "posto/gerado/gemini-web/instrucoes.md",
    "ferramentas/vault-ontologia/vault.sh",
    "ferramentas/vault-ontologia/vault_ontologia.py",
    "ferramentas/vault-ontologia/testes/test_vault_ontologia.py",
)
CURA = (
    "ler pela Olaria (`ontologia ler <classe> <chave>`) ou pela busca da casa nova; "
    "remover referências à casa velha"
)
ID = "CASA_POR_CAMINHO"


def _isento(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    return (
        norm.endswith(ISENTOS_SUFIXO)
        or norm.endswith(ISENTOS_MIGRACAO_SQL)
        or norm.endswith(ISENTOS_TRANSICAO_E3650)
    )


def forma(linha: str) -> Optional[str]:
    """O trecho que cita a casa velha por caminho/repositório, ou None."""
    m = _RE.search(linha)
    return m.group(0) if m else None


def _no_stage(raiz: Path) -> list[str]:
    p = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=raiz, capture_output=True, text=True,
    )
    nomes = [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []
    return [n for n in nomes if not _isento(n)]


def bloqueantes_no_stage(raiz: Path | str) -> Tuple[list[Apontamento], Optional[str]]:
    """Para o pre-commit: (apontamentos bloqueantes, aviso). Nunca lança."""
    from .canonico import _linhas_acrescentadas

    raiz = Path(raiz)
    achados: list[Apontamento] = []
    for arquivo in _no_stage(raiz):
        for n, texto in _linhas_acrescentadas(raiz, arquivo):
            trecho = forma(texto)
            if trecho:
                achados.append(Apontamento(
                    arquivo, n, f"cita caminho ou artefato da casa velha: «{trecho}»", CURA,
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
    """Varre a árvore (ou subárvore `alvo`) procurando citações à casa velha. Pula binário e arquivo grande."""
    raiz = Path(raiz)
    achados: list[Apontamento] = []
    for arq in _arquivos(raiz, alvo):
        try:
            rel = str(arq.relative_to(raiz))
        except ValueError:
            rel = arq.name
        if _isento(rel):
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
                    rel, i, f"cita caminho ou artefato da casa velha: «{trecho}»", CURA,
                    severidade="aviso", id=ID))
    return achados
