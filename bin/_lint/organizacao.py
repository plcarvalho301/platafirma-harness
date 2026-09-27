"""organizacao — antipadrões de organização documental (card #3118).

A régua é a lista de verificação `checklist-antipadroes-organizacao-documental` do
acervo: ela diz, por classe, o antipadrão, a severidade e a cura. Aqui mora só o
detector mecânico de cada classe, escolhido pelo id da lista (AP1, AP2...). Classe cujo
detector na lista é «leitura» não se roda. Classe nova na lista sem detector aqui sai
listada como «sem detector», nunca calada.

Dois leitores do mesmo detector (spec_lint §1):
  - `lint organizacao <repo>` roda as de severidade aviso sobre o rastreado e relata;
  - o pre-commit roda as de severidade bloqueante sobre o que está no stage, em
    repositório declarado em registro/organizacao-bloqueia.json, e recusa.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "checklist-antipadroes-organizacao-documental"

EXT_IMAGEM = (".svg", ".png", ".pdf")
MANIFESTOS = ("pyproject.toml", "package.json", "Dockerfile", "Makefile")
MARCAS_FOSSIL = ("handoff", "demanda", "rascunho", "rodada")
NOME_OK = re.compile(r"^[A-Za-z0-9._-]+$")
DATA = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}|\d{8})(?!\d)")
TITULO_SERIE = re.compile(r"^#\s+([a-z]+:\d{4}\b|\d{4}\s+—)")
PONTEIRO_NU = re.compile(r"(?<![\w/`])(?:[a-z]+:\d{4}\b|#\d{3,5}\b|§\s?\d+)")
CABECALHO_META = re.compile(r"^[A-ZÀ-Ú][\wÀ-ú ]{0,30}:\s")

# (arquivo, linha, detalhe)
Achado = Tuple[str, int, str]


# --------------------------------------------------------------------- leitura

def _ler(raiz: Path, rel: str) -> Optional[str]:
    try:
        return (raiz / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _md(arquivos: Iterable[str]) -> list[str]:
    return [a for a in arquivos if a.lower().endswith(".md")]


# ------------------------------------------------------------------ detectores

def ap1(raiz, arquivos, todos):
    """arquivo em docs/ com data no nome"""
    return [(a, 1, "data no nome de arquivo em docs/") for a in arquivos
            if a.startswith("docs/") and DATA.search(os.path.basename(a))]


def ap2(raiz, arquivos, todos):
    """dois arquivos de conteúdo idêntico"""
    primeiro: dict[str, str] = {}
    achados = []
    julgar = set(arquivos)
    for a in sorted(todos):
        try:
            dado = (raiz / a).read_bytes()
        except OSError:
            continue
        if not dado.strip():
            continue  # vazio (__init__.py, .gitkeep) não é cópia de nada
        h = hashlib.sha256(dado).hexdigest()
        if h in primeiro:
            if a in julgar:
                achados.append((a, 1, f"mesmo conteúdo que {primeiro[h]}"))
        else:
            primeiro[h] = a
    return achados


def ap3(raiz, arquivos, todos):
    """nome com marca de trabalho de fita"""
    achados = []
    for a in arquivos:
        nome = a.lower()
        marca = next((m for m in MARCAS_FOSSIL if m in nome), None)
        if marca:
            achados.append((a, 1, f"marca de fita «{marca}» no caminho"))
    return achados


def ap4(raiz, arquivos, todos):
    """.md com cabeçalho Espécie:"""
    achados = []
    for a in _md(arquivos):
        texto = _ler(raiz, a) or ""
        for n, linha in enumerate(texto.splitlines()[:20], 1):
            if re.match(r"^Esp[ée]cie:\s*\S", linha):
                achados.append((a, n, "documento de casa (tem Espécie:) em repositório de software"))
                break
    return achados


def ap5(raiz, arquivos, todos):
    """nome fora de [A-Za-z0-9._-]"""
    achados = []
    for a in arquivos:
        ruim = next((p for p in a.split("/") if not NOME_OK.match(p)), None)
        if ruim:
            achados.append((a, 1, f"nome opaco: «{ruim}»"))
    return achados


def ap7(raiz, arquivos, todos):
    """.md cujo título abre com número de série"""
    achados = []
    for a in _md(arquivos):
        texto = _ler(raiz, a) or ""
        for n, linha in enumerate(texto.splitlines(), 1):
            if linha.startswith("# "):
                if TITULO_SERIE.match(linha):
                    achados.append((a, n, f"título com chave própria: «{linha[2:40]}»"))
                break
    return achados


def ap8(raiz, arquivos, todos):
    """raiz sem README, ou pasta com manifesto sem README"""
    presentes = set(todos)
    achados = []
    if "README.md" not in presentes:
        achados.append(("README.md", 1, "raiz sem README.md"))
    pastas = {os.path.dirname(a) for a in arquivos
              if os.path.basename(a) in MANIFESTOS and os.path.dirname(a)}
    for p in sorted(pastas):
        if f"{p}/README.md" not in presentes:
            achados.append((f"{p}/README.md", 1, f"{p}/ sobe ou testa sozinha e não tem README.md"))
    return achados


def ap9(raiz, arquivos, todos):
    """imagem ao lado do arquivo que a gera"""
    por_dir: dict[str, set[str]] = {}
    for a in todos:
        por_dir.setdefault(os.path.dirname(a), set()).add(os.path.basename(a))
    achados = []
    for a in arquivos:
        base = os.path.basename(a)
        ext = os.path.splitext(base)[1].lower()
        if ext not in EXT_IMAGEM:
            continue
        stem = base[: -len(ext)]
        vizinhos = [v for v in por_dir.get(os.path.dirname(a), ())
                    if os.path.splitext(v)[1].lower() not in EXT_IMAGEM]
        fonte = next((v for v in vizinhos
                      if v == stem or os.path.splitext(v)[0] == stem), None)
        if fonte:
            achados.append((a, 1, f"render ao lado da fonte {fonte}"))
    return achados


def ap11(raiz, arquivos, todos):
    """AGENTS.md ou CLAUDE.md fora da raiz"""
    return [(a, 1, "instrumento de agente fora da raiz") for a in arquivos
            if "/" in a and os.path.basename(a) in ("AGENTS.md", "CLAUDE.md")]


def ap12(raiz, arquivos, todos):
    """ponteiro nu em corpo de prosa (a parte mecânica)"""
    achados = []
    for a in _md(arquivos):
        texto = _ler(raiz, a)
        if not texto:
            continue
        cerca = False
        no_cabecalho = False
        for n, linha in enumerate(texto.splitlines(), 1):
            limpa = linha.strip()
            if limpa.startswith("```"):
                cerca = not cerca
                continue
            if cerca:
                continue
            if limpa.startswith("# "):
                no_cabecalho = True
                continue
            if no_cabecalho:
                # bloco de metadado logo abaixo do título (Espécie:, Sobre:...) é endereço
                if not limpa or CABECALHO_META.match(limpa):
                    continue
                no_cabecalho = False
            if (not limpa or limpa.startswith(("|", "[^", "#", ">"))
                    or CABECALHO_META.match(limpa)):
                continue
            sem_codigo = re.sub(r"`[^`]*`", "", linha)
            m = PONTEIRO_NU.search(sem_codigo)
            if m:
                achados.append((a, n, f"ponteiro nu «{m.group(0)}» em prosa"))
    return achados


DETECTORES: dict[str, Callable[[Path, list, list], list[Achado]]] = {
    "AP1": ap1, "AP2": ap2, "AP3": ap3, "AP4": ap4, "AP5": ap5, "AP7": ap7,
    "AP8": ap8, "AP9": ap9, "AP11": ap11, "AP12": ap12,
}


# ------------------------------------------------------------------- o motor

def _rastreados(raiz: Path) -> list[str]:
    p = subprocess.run(["git", "ls-files", "-z"], cwd=raiz, capture_output=True, text=True)
    return [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []


def _no_stage(raiz: Path) -> list[str]:
    p = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
                       cwd=raiz, capture_output=True, text=True)
    return [x for x in p.stdout.split("\0") if x] if p.returncode == 0 else []


def aplicar(lista: dict, raiz: Path, arquivos: list[str], todos: list[str],
            severidades: Iterable[str]) -> list[Apontamento]:
    """Roda sobre `arquivos` os detectores das classes da lista cuja severidade está em
    `severidades`. `todos` é o rastreado inteiro (para vizinhança: cópia, fonte, README)."""
    severidades = set(severidades)
    apontamentos = []
    for item in lista.get("itens", []):
        cid = item.get("id", "")
        sev = item.get("severidade", "")
        if sev not in severidades or item.get("detector", "").strip() == "leitura":
            continue
        detector = DETECTORES.get(cid)
        cura = item.get("cura", "ver a lista de verificação")
        nome = item.get("o_que_fere", cid)
        if detector is None:
            apontamentos.append(Apontamento(
                CHAVE_LISTA, 1, f"{cid} {nome}: classe da lista sem detector no lint",
                "acrescentar o detector em bin/_lint/organizacao.py", severidade="aviso",
                id=cid))
            continue
        for arq, linha, detalhe in detector(raiz, arquivos, todos):
            apontamentos.append(Apontamento(
                arq, linha, f"{cid} {nome}: {detalhe}", cura, severidade=sev, id=cid))
    return apontamentos


def verificar_organizacao(
    raiz: Path | str,
    alvo: Optional[str] = None,
    com_bloqueantes: bool = False,
) -> Tuple[list[Apontamento], str, Optional[int]]:
    """`lint organizacao`: avisos sobre o rastreado (ou o alvo). `com_bloqueantes` põe
    também os bloqueantes no relatório — para contagem, nunca para reprovar."""
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")
    raiz = Path(raiz)
    todos = _rastreados(raiz)
    arquivos = todos
    if alvo:
        a = alvo.rstrip("/")
        arquivos = [x for x in todos if x == a or x.startswith(a + "/")]
    sev = ("aviso", "bloqueante") if com_bloqueantes else ("aviso",)
    return aplicar(lista, raiz, arquivos, todos, sev), CHAVE_LISTA, lista.get("rev", 1)


def bloqueantes_no_stage(raiz: Path | str) -> tuple[list[Apontamento], Optional[str]]:
    """Para o pre-commit: (apontamentos bloqueantes no stage, aviso). O aviso sai quando a
    lista não está servida — aí não se verifica, e se diz."""
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        return [], f"lista {CHAVE_LISTA} indisponivel no acervo: organizacao nao verificada neste commit"
    raiz = Path(raiz)
    todos = sorted(set(_rastreados(raiz)) | set(_no_stage(raiz)))
    return aplicar(lista, raiz, _no_stage(raiz), todos, ("bloqueante",)), None
