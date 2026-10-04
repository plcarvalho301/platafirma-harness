"""codigo — a classe `codigo` do lint: aplica a lista `antipadroes-de-codigo` ao codigo da bancada.

A regua e a lista, nao a configuracao de cada repositorio (spec_lint §3). A coluna detector
de cada criterio diz quem o mede, em tres formas:
  `ruff <codigo>`        regra selecionada no ruff;
  `ruff padrão`          as regras que o ruff liga por padrao, alem das nomeadas;
  `shellcheck <codigo>`  regra selecionada no shellcheck;
  `predicado <NOME>`     detector da casa (predicados.py), onde nenhum analisador pronto chega.
O apontamento sai com o `#`, o texto e a cura do criterio. Criterio de leitura nao aponta.

O arquivo se classifica pelo que e, nao pela raiz em que esta: `.py`, ou sem extensao com
shebang de python, e Python; `.sh`, ou shebang de shell, e shell; `.service` e unit. Antes
(#2856 linha 190) a raiz sem manifesto python caia no ramo de shell e o ruff nao rodava.

Modos de falha: lista ausente sai 5; ruff necessario e ausente sai 3; codigo que o ruff
instalado nao conhece fica fora da selecao e vira aviso (selecionar codigo desconhecido faz o
ruff sair 2 e nao medir nada); shellcheck ausente e predicado que quebra nao derrubam o resto,
e o que deixou de medir vai em aviso, nunca em silencio.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .lista import resolver_lista
from .predicados import DO_REPOSITORIO, PREDICADOS, Contexto, e_teste
from .resultado import Apontamento

CHAVE_LISTA = "antipadroes-de-codigo"

# Fora do PATH, o analisador vem pelo uvx, com versao presa: a regua nao muda quando o
# indice publica versao nova.
RUFF_UVX = ["uvx", "ruff@0.16.10"]
SHELLCHECK_UVX = ["uvx", "--from", "shellcheck-py>=0.11,<0.12", "shellcheck"]
PRAZO_ANALISADOR_S = 300
LOTE_ARQUIVOS = 400

_RE_RUFF = re.compile(r"\bruff\s+([A-Z]+[0-9]+)\b")
_RE_RUFF_PADRAO = re.compile(r"\bruff\s+padr[aã]o\b")
_RE_SHELLCHECK = re.compile(r"\bshellcheck\s+(SC[0-9]{4})\b")
_RE_PREDICADO = re.compile(r"\bpredicado\s+([A-Z][A-Z_]+)\b")
_RE_SHEBANG_PY = re.compile(r"^#!.*\bpython[0-9.]*\b")
_RE_SHEBANG_SH = re.compile(r"^#!.*\b(ba|da|k)?sh\b")

_PASTAS_FORA = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache",
                ".pytest_cache", "build", "dist", ".mypy_cache"}

# Regras que, no arquivo de teste ou de ponto de entrada, acusam a forma certa:
# `assert` e o idioma do pytest; `print` e a saida de um verbo de linha de comando.
_FORA_EM_TESTE = {"S101", "T201", "ANN001", "ANN201", "PLR2004"}
_FORA_EM_ENTRADA = {"T201"}


@dataclass
class Regua:
    """O que a lista manda medir, por analisador."""
    rev: int
    ruff: dict[str, dict] = field(default_factory=dict)
    ruff_padrao: dict | None = None
    shellcheck: dict[str, dict] = field(default_factory=dict)
    predicados: dict[str, dict] = field(default_factory=dict)


def ler_regua(lista: dict) -> Regua:
    """Le os detectores mecanicos dos criterios da lista. O primeiro criterio que nomeia
    um codigo ou predicado fica com ele."""
    regua = Regua(rev=lista.get("rev") or 1)
    for item in lista.get("itens", []):
        detector = item.get("detector", "")
        for cod in _RE_RUFF.findall(detector):
            regua.ruff.setdefault(cod, item)
        if _RE_RUFF_PADRAO.search(detector) and regua.ruff_padrao is None:
            regua.ruff_padrao = item
        for cod in _RE_SHELLCHECK.findall(detector):
            regua.shellcheck.setdefault(cod, item)
        for nome in _RE_PREDICADO.findall(detector):
            regua.predicados.setdefault(nome, item)
        if "contagem de linhas" in detector:  # forma da rev 1 e 2 da lista
            regua.predicados.setdefault("LINHAS_SHELL", item)
    return regua


# ------------------------------------------------------------------ arquivos


def _cabeca(p: Path) -> str:
    try:
        with p.open("rb") as f:
            return f.readline(200).decode("utf-8", "replace")
    except OSError:
        return ""


def linguagem(p: Path) -> str | None:
    """'python', 'shell', 'unit' ou None, pela extensao ou, sem extensao, pelo shebang."""
    suf = p.suffix.lower()
    if suf in (".py", ".pyi"):
        return "python"
    if suf in (".sh", ".bash"):
        return "shell"
    if suf == ".service":
        return "unit"
    if suf:
        return None
    cab = _cabeca(p)
    if _RE_SHEBANG_PY.match(cab):
        return "python"
    if _RE_SHEBANG_SH.match(cab):
        return "shell"
    return None


def _listar(raiz: Path, alvo: str | None) -> list[Path]:
    """Arquivos do alvo: os do git (rastreados e novos, sem ignorados), senao a arvore."""
    base = (raiz / alvo).resolve() if alvo else raiz
    if base.is_file():
        return [base]
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z", "--", str(base)],
            cwd=raiz, capture_output=True, timeout=60, check=False,
        )
        if proc.returncode == 0:
            return [raiz / n for n in proc.stdout.decode("utf-8", "replace").split("\0")
                    if n and (raiz / n).is_file()]
    except (OSError, subprocess.SubprocessError):
        pass
    return [p for p in base.rglob("*")
            if p.is_file() and not (set(p.relative_to(raiz).parts) & _PASTAS_FORA)]


def _por_lingua(arquivos: Iterable[Path]) -> dict[str, list[Path]]:
    saida: dict[str, list[Path]] = {"python": [], "shell": [], "unit": []}
    for arq in arquivos:
        lingua = linguagem(arq)
        if lingua:
            saida[lingua].append(arq)
    return saida


def _e_entrada(rel: str, arquivo: Path) -> bool:
    partes = Path(rel).parts
    return (partes[0] in ("bin", "scripts", "tooling") or arquivo.name == "__main__.py"
            or _cabeca(arquivo).startswith("#!"))


# ------------------------------------------------------------------ analisadores


def _binario(nome: str, via_uvx: list[str]) -> list[str] | None:
    achado = shutil.which(nome)
    if achado:
        return [achado]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, *via_uvx[1:]]
    return None


def _rodar(cmd: list[str], raiz: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=raiz, capture_output=True, text=True,
                              timeout=PRAZO_ANALISADOR_S, check=False)
    except subprocess.TimeoutExpired as e:
        raise ValueError(3, f"{cmd[0]} passou de {PRAZO_ANALISADOR_S} s; rode com alvo menor") from e
    except OSError as e:
        raise ValueError(3, f"falha ao executar {cmd[0]}: {e}") from e


def _em_lotes(seq: list[str]) -> Iterable[list[str]]:
    for i in range(0, len(seq), LOTE_ARQUIVOS):
        yield seq[i:i + LOTE_ARQUIVOS]


def _apontar(rel: str, linha: int, item: dict, origem: str, msg: str) -> Apontamento:
    return Apontamento(
        rel, linha,
        f"{item.get('id', '?')} {item.get('o_que_fere', '')} [{origem}: {msg}]",
        item.get("cura", "corrigir conforme a lista"),
        severidade=item.get("severidade", "aviso"),
        id=item.get("id"),
    )


def _selecao_ruff(ruff: list[str], raiz: Path, regua: Regua, avisos: list[str]) -> list[str] | None:
    """Argumentos de selecao do ruff, ou None se nada da lista se mede com ele."""
    conhecidas = _rodar([*ruff, "rule", "--all", "--output-format", "json"], raiz)
    try:
        existentes = {r["code"] for r in json.loads(conhecidas.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(3, f"ruff nao listou as regras: {conhecidas.stderr.strip()[:300]}") from e
    nomeadas = sorted(c for c in regua.ruff if c in existentes)
    fora = sorted(set(regua.ruff) - existentes)
    if fora:
        avisos.append(f"codigos da lista que o ruff instalado nao conhece, fora da medida: {', '.join(fora)}")
    if regua.ruff_padrao:
        # sem --select vale o padrao do ruff; as nomeadas entram por cima
        return ["--extend-select", ",".join(nomeadas)] if nomeadas else []
    return ["--select", ",".join(nomeadas)] if nomeadas else None


def _ruff(raiz: Path, arquivos: list[Path], regua: Regua, avisos: list[str]) -> list[Apontamento]:
    if not arquivos or not (regua.ruff or regua.ruff_padrao):
        return []
    ruff = _binario("ruff", RUFF_UVX)
    if not ruff:
        raise ValueError(3, "linter python (ruff) ausente: nem `ruff` no PATH nem `uvx`")
    selecao = _selecao_ruff(ruff, raiz, regua, avisos)
    if selecao is None:
        return []

    rels = [str(a.relative_to(raiz)) for a in arquivos]
    achados: list[Apontamento] = []
    for lote in _em_lotes(rels):
        proc = _rodar([*ruff, "check", "--isolated", "--no-cache", "--output-format", "json",
                       *selecao, *lote], raiz)
        if proc.returncode not in (0, 1):
            raise ValueError(3, f"ruff saiu {proc.returncode}: {proc.stderr.strip()[:400]}")
        for d in json.loads(proc.stdout or "[]"):
            cod = d.get("code") or "sintaxe"
            item = regua.ruff.get(cod) or regua.ruff_padrao
            if not item:
                continue
            caminho = Path(d["filename"])
            rel = str(caminho.relative_to(raiz)) if caminho.is_absolute() else str(caminho)
            if cod in _FORA_EM_TESTE and e_teste(rel):
                continue
            if cod in _FORA_EM_ENTRADA and _e_entrada(rel, raiz / rel):
                continue
            achados.append(_apontar(rel, d.get("location", {}).get("row", 1), item, cod,
                                    d.get("message", "")))
    return achados


def _shellcheck(raiz: Path, arquivos: list[Path], regua: Regua, avisos: list[str]) -> list[Apontamento]:
    if not arquivos or not regua.shellcheck:
        return []
    sc = _binario("shellcheck", SHELLCHECK_UVX)
    if not sc:
        avisos.append(f"shellcheck ausente (nem no PATH nem por uvx): {len(regua.shellcheck)} "
                      f"regras de shell da lista nao medidas em {len(arquivos)} arquivos")
        return []
    rels = [str(a.relative_to(raiz)) for a in arquivos]
    incluir = ",".join(sorted(regua.shellcheck))
    achados: list[Apontamento] = []
    for lote in _em_lotes(rels):
        proc = _rodar([*sc, "-f", "json1", "-S", "style", f"--include={incluir}", *lote], raiz)
        if proc.returncode not in (0, 1):
            avisos.append(f"shellcheck saiu {proc.returncode} num lote de {len(lote)} arquivos: "
                          f"{proc.stderr.strip()[:300]}")
            continue
        for c in json.loads(proc.stdout or "{}").get("comments", []):
            cod = f"SC{c.get('code')}"
            item = regua.shellcheck.get(cod)
            if item:
                achados.append(_apontar(c.get("file", "?"), c.get("line", 1), item, cod,
                                        c.get("message", "")))
    return achados


def _predicados(ctx: Contexto, regua: Regua, avisos: list[str]) -> list[Apontamento]:
    desconhecidos = sorted(set(regua.predicados) - set(PREDICADOS))
    if desconhecidos:
        avisos.append(f"predicados que a lista nomeia e o lint nao tem, fora da medida: {', '.join(desconhecidos)}")
    achados: list[Apontamento] = []
    for nome, item in regua.predicados.items():
        if nome not in PREDICADOS:
            continue
        funcao, candidata = PREDICADOS[nome]
        try:
            for a in funcao(ctx, item):
                detalhe = f"{a.detalhe} — candidata, confirme lendo" if candidata else a.detalhe
                achados.append(_apontar(a.arquivo, a.linha, item, nome, detalhe))
        except Exception as e:  # noqa: BLE001 — borda: um predicado quebrado nao derruba os outros; vai em aviso
            avisos.append(f"predicado {nome} falhou e ficou fora da medida: {type(e).__name__}: {e}")
    return achados


# ------------------------------------------------------------------ stack (lint detectar)


def detectar_stack(raiz: Path) -> tuple[str, str] | None:
    """Stack do repositorio para `lint detectar`: (stack, comando)."""
    if any((raiz / n).exists() for n in ("pyproject.toml", ".ruff.toml", "ruff.toml", ".ruff_cache")):
        return "python", "ruff check"
    try:
        if '"lint"' in (raiz / "package.json").read_text(encoding="utf-8", errors="replace"):
            return "node", "npm run lint"
    except OSError:  # sem package.json, ou ilegivel: nao e stack node
        pass
    if (raiz / "bin").is_dir() or any(raiz.glob("*.sh")):
        return "bash", "shellcheck"
    return None


def raiz_da_stack(raiz: Path, alvo: str | None = None) -> Path:
    """Projeto que contem o alvo: o diretorio mais proximo com manifesto python ou node (#3074)."""
    raiz = raiz.resolve()
    if not alvo:
        return raiz
    p = (raiz / alvo).resolve()
    d = p if p.is_dir() else p.parent
    while d != raiz and d.is_relative_to(raiz):
        det = detectar_stack(d)
        if det and det[0] in ("python", "node"):
            return d
        d = d.parent
    return raiz


# ------------------------------------------------------------------ a classe


def verificar_codigo(
    raiz: Path | str,
    alvo: str | None = None,
) -> tuple[list[Apontamento], str, int, list[str]]:
    """Aplica a lista ao alvo. Devolve (apontamentos, chave, rev, avisos).

    Levanta ValueError(exit, msg): 5 sem a lista no acervo, 3 com o analisador necessario
    ausente ou quebrado.
    """
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")
    regua = ler_regua(lista)
    raiz = Path(raiz).resolve()

    escopo = _por_lingua(_listar(raiz, alvo))
    py_repo = escopo["python"]
    if alvo and set(regua.predicados) & DO_REPOSITORIO:
        py_repo = _por_lingua(_listar(raiz, None))["python"]
    ctx = Contexto(raiz, escopo["python"], escopo["shell"], escopo["unit"], py_repo)

    avisos: list[str] = []
    achados = _ruff(raiz, escopo["python"], regua, avisos)
    achados += _shellcheck(raiz, escopo["shell"], regua, avisos)
    achados += _predicados(ctx, regua, avisos)

    unicos: dict[tuple[str, int, str, str], Apontamento] = {}
    for a in achados:
        unicos.setdefault((a.arquivo, a.linha, a.id or "", a.o_que_fere), a)
    return sorted(unicos.values(), key=lambda a: (a.arquivo, a.linha, a.id or "")), CHAVE_LISTA, regua.rev, avisos
