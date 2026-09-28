"""diagrama — compila .mmd (mermaid) e .d2 no Kroki da casa (card #3096).

`lint diagrama <repo>[@<chave>] <alvo>` compila o alvo (um arquivo `.mmd`/`.d2`, ou uma
pasta — todo diagrama dentro dela) no Kroki publicado pela casa e aponta o arquivo e,
quando o Kroki devolve, a linha do erro. Kroki fora de alcance não é diagrama quebrado:
sai 5 (indeterminavel), nunca 1 — o mesmo padrão de `conferir diagrama` (card #3099,
arq:0110). O pre-commit roda esta classe sobre os diagramas em stage e recusa o commit
com o que não compila; Kroki fora do ar aí só avisa — a trava desta story é que ele NUNCA
barra o commit (sai 5 na chamada avulsa; no hook, sem bloqueante nenhum, o commit segue).

Dois leitores do mesmo detector, como em `organizacao` (card #3118):
  - `lint diagrama <repo> <alvo>` mede um alvo escolhido e relata (aviso ou erro, na
    forma comum do lint);
  - o pre-commit roda só sobre os diagramas em stage e recusa o que não compila.
"""
from __future__ import annotations

import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from .resultado import Apontamento

EXTENSOES = {".mmd": "mermaid", ".d2": "d2"}

# Kroki pela porta PUBLICADA da casa (card #3099): nunca pelo IP da rede do conteiner —
# no docker rootless da conta ele nao e roteavel do host ("No route to host").
_ENDPOINT_PADRAO = "http://127.0.0.1:8095"

# «Parse error on line 4» (mermaid) · «arquivo.d2:4:1: ...» (d2) — a melhor pista que o
# Kroki devolve pro numero da linha; sem casar, a linha cai no arquivo (1), nunca inventada.
_RE_LINHA_MERMAID = re.compile(r"\bline\s+(\d+)\b", re.I)
_RE_LINHA_D2 = re.compile(r":(\d+):\d+:")


def _endpoint() -> str:
    endpoint = os.environ.get("KROKI_URL")
    if endpoint:
        return endpoint.rstrip("/")
    try:
        p = subprocess.run(
            ["docker", "port", "plataforma-wiki-kroki-1", "8000/tcp"],
            capture_output=True, text=True, timeout=5,
        )
        linha = p.stdout.splitlines()[0].strip() if p.returncode == 0 and p.stdout.strip() else ""
        if linha:
            return ("http://" + linha.replace("0.0.0.0:", "127.0.0.1:")).rstrip("/")
    except (OSError, subprocess.SubprocessError):
        pass
    return _ENDPOINT_PADRAO


def _linha_do_erro(corpo: str, tipo: str) -> int:
    padrao = _RE_LINHA_MERMAID if tipo == "mermaid" else _RE_LINHA_D2
    m = padrao.search(corpo)
    return int(m.group(1)) if m else 1


def compilar(caminho: Path) -> Tuple[str, Optional[Apontamento]]:
    """Compila um diagrama isolado no Kroki. Nunca lança.

    Devolve (status, apontamento): status em 'ok' (apontamento None), 'quebrado'
    (severidade 'bloqueante' — o Kroki recusou) ou 'kroki' (severidade 'aviso' — não
    consegui falar com o Kroki; nunca vira defeito confirmado).
    """
    caminho = Path(caminho)
    ext = caminho.suffix.lower()
    tipo = EXTENSOES.get(ext)
    if tipo is None:
        return "quebrado", Apontamento(
            str(caminho), 1, f"extensao nao suportada: {ext} (esperado .mmd ou .d2)",
            "usar .mmd (mermaid) ou .d2", severidade="bloqueante")
    try:
        corpo = caminho.read_text(encoding="utf-8")
    except OSError as e:
        return "quebrado", Apontamento(
            str(caminho), 1, f"nao consegui ler {caminho}: {e}",
            "conferir o caminho", severidade="bloqueante")

    endpoint = _endpoint()
    req = urllib.request.Request(
        f"{endpoint}/{tipo}/svg", data=corpo.encode("utf-8"),
        headers={"Content-Type": "text/plain"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return "ok", None
            return "quebrado", Apontamento(
                str(caminho), 1, f"Kroki retornou status {resp.status}",
                "corrigir o diagrama e recompilar", severidade="bloqueante")
    except urllib.error.HTTPError as e:
        corpo_erro = e.read().decode("utf-8", errors="replace")
        linha = _linha_do_erro(corpo_erro, tipo)
        primeira = corpo_erro.strip().splitlines()[0] if corpo_erro.strip() else f"Kroki recusou (HTTP {e.code})"
        return "quebrado", Apontamento(
            str(caminho), linha, primeira, "corrigir o diagrama e recompilar",
            severidade="bloqueante")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Kroki inalcancavel (conexao recusada, DNS, timeout) -- nao consegui olhar,
        # nunca defeito confirmado no diagrama (card #3142, mesmo padrao de #3099).
        return "kroki", Apontamento(
            str(caminho), 1, f"nao consegui falar com o Kroki em {endpoint}: {e}",
            "conferir se o Kroki da casa esta no ar", severidade="aviso")


def _diagramas_de(raiz: Path, alvo: str) -> list[Path]:
    p = (raiz / alvo)
    if p.is_file():
        return [p] if p.suffix.lower() in EXTENSOES else []
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if f.suffix.lower() in EXTENSOES)
    return []


def _relativizar(apt: Optional[Apontamento], raiz: Path) -> Optional[Apontamento]:
    """Apontamento.arquivo relativo a raiz -- a convencao de todo `lint` (organizacao,
    repo, superficie...): caminho absoluto so confundiria com o de outro clone."""
    if apt is None:
        return None
    apt.arquivo = os.path.relpath(apt.arquivo, str(raiz))
    return apt


def verificar_diagrama(raiz: Path | str, alvo: str) -> Tuple[list[Apontamento], int]:
    """`lint diagrama <repo> <alvo>`: (apontamentos, exit_code).

    0 tudo compila (ou nada a compilar) · 1 ao menos um diagrama quebrado · 5 nada
    quebrou mas o Kroki ficou fora de alcance para ao menos um (nada medido de verdade).
    """
    raiz = Path(raiz)
    caminhos = _diagramas_de(raiz, alvo)
    if not caminhos:
        return [], 0

    quebrados: list[Apontamento] = []
    indeterminaveis: list[Apontamento] = []
    for c in caminhos:
        status, apt = compilar(c)
        apt = _relativizar(apt, raiz)
        if status == "quebrado":
            quebrados.append(apt)
        elif status == "kroki":
            indeterminaveis.append(apt)

    if quebrados:
        return quebrados, 1
    if indeterminaveis:
        return indeterminaveis, 5
    return [], 0


def diagramas_no_stage(raiz: Path | str) -> list[Path]:
    p = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        cwd=raiz, capture_output=True, text=True,
    )
    nomes = [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []
    raiz = Path(raiz)
    return [raiz / n for n in nomes if Path(n).suffix.lower() in EXTENSOES]


def bloqueantes_no_stage(raiz: Path | str) -> Tuple[list[Apontamento], Optional[str]]:
    """Para o pre-commit: (apontamentos bloqueantes, aviso).

    Kroki fora de alcance NÃO bloqueia — vira só aviso (trava desta story, #3096): o
    commit segue mesmo sem medir o diagrama.
    """
    caminhos = diagramas_no_stage(raiz)
    if not caminhos:
        return [], None

    quebrados: list[Apontamento] = []
    indeterminaveis: list[Apontamento] = []
    for c in caminhos:
        status, apt = compilar(c)
        apt = _relativizar(apt, raiz)
        if status == "quebrado":
            quebrados.append(apt)
        elif status == "kroki":
            indeterminaveis.append(apt)

    aviso = None
    if indeterminaveis and not quebrados:
        nomes = ", ".join(a.arquivo for a in indeterminaveis)
        aviso = f"Kroki fora de alcance: diagrama(s) nao verificado(s) neste commit — {nomes}"
    return quebrados, aviso
