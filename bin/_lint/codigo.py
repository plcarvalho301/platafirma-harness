"""codigo — a classe `codigo` do lint: aplica a lista `antipadroes-de-codigo` ao codigo da bancada.

A regua e a lista, nao a configuracao de cada repositorio (spec_lint §3). Cada criterio cujo
detector diz `ruff <codigo>` ou `shellcheck <codigo>` vira regra selecionada no analisador da
linguagem; o apontamento sai com o `#`, o texto e a cura do criterio. Predicados da casa: o
BASH_SET_E e a contagem de linhas de script de shell. Criterio de leitura nao gera apontamento.

O arquivo se classifica pelo que e, nao pela raiz em que esta: `.py`, ou sem extensao com
shebang de python, vai ao ruff; `.sh`, ou shebang de shell, ao shellcheck. Antes (#2856 linha
190) a raiz sem manifesto python caia no ramo de shell e o ruff nao rodava: verde falso.

Modos de falha que este modulo trata: lista ausente sai 5; ruff necessario e ausente sai 3;
codigo da lista que o ruff instalado nao conhece fica fora da selecao e vira aviso (selecionar
codigo desconhecido faz o ruff sair 2 e nao medir nada); shellcheck ausente nao derruba a
medida do python, e o que deixou de medir vai em aviso, nunca em silencio.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "antipadroes-de-codigo"

# Fora do PATH, o analisador vem pelo uvx, com versao presa: a regua nao muda quando o
# indice publica versao nova.
RUFF_UVX = ["uvx", "ruff@0.16.10"]
SHELLCHECK_UVX = ["uvx", "--from", "shellcheck-py>=0.11,<0.12", "shellcheck"]
PRAZO_ANALISADOR_S = 300
LOTE_ARQUIVOS = 400

_RE_RUFF = re.compile(r"\bruff\s+([A-Z]+[0-9]+)\b")
_RE_SHELLCHECK = re.compile(r"\bshellcheck\s+(SC[0-9]{4})\b")
_RE_PISO_LINHAS = re.compile(r"mais de (\d+) linhas")
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
    ruff: Dict[str, dict] = field(default_factory=dict)
    shellcheck: Dict[str, dict] = field(default_factory=dict)
    set_e: Optional[dict] = None
    linhas_shell: Optional[Tuple[dict, int]] = None


def ler_regua(lista: dict) -> Regua:
    """Le os detectores mecanicos dos criterios da lista."""
    regua = Regua(rev=lista.get("rev") or 1)
    for item in lista.get("itens", []):
        detector = item.get("detector", "")
        for cod in _RE_RUFF.findall(detector):
            regua.ruff.setdefault(cod, item)
        for cod in _RE_SHELLCHECK.findall(detector):
            regua.shellcheck.setdefault(cod, item)
        if "BASH_SET_E" in detector:
            regua.set_e = item
        if "contagem de linhas" in detector:
            m = _RE_PISO_LINHAS.search(item.get("o_que_fere", ""))
            regua.linhas_shell = (item, int(m.group(1)) if m else 100)
    return regua


# ------------------------------------------------------------------ arquivos


def _cabeca(p: Path) -> str:
    try:
        with p.open("rb") as f:
            return f.readline(200).decode("utf-8", "replace")
    except OSError:
        return ""


def linguagem(p: Path) -> Optional[str]:
    """'python', 'shell' ou None, pela extensao ou, sem extensao, pelo shebang."""
    suf = p.suffix.lower()
    if suf in (".py", ".pyi"):
        return "python"
    if suf in (".sh", ".bash"):
        return "shell"
    if suf:
        return None
    cab = _cabeca(p)
    if _RE_SHEBANG_PY.match(cab):
        return "python"
    if _RE_SHEBANG_SH.match(cab):
        return "shell"
    return None


def _listar(raiz: Path, alvo: Optional[str]) -> List[Path]:
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


def _e_teste(rel: str) -> bool:
    partes = Path(rel).parts
    nome = partes[-1]
    return (nome.startswith("test_") or nome == "conftest.py"
            or any(x in ("tests", "testes", "test") for x in partes[:-1]))


def _e_entrada(rel: str, arquivo: Path) -> bool:
    partes = Path(rel).parts
    return (partes[0] in ("bin", "scripts", "tooling") or arquivo.name == "__main__.py"
            or _cabeca(arquivo).startswith("#!"))


# ------------------------------------------------------------------ analisadores


def _binario(nome: str, via_uvx: List[str]) -> Optional[List[str]]:
    achado = shutil.which(nome)
    if achado:
        return [achado]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, *via_uvx[1:]]
    return None


def _rodar(cmd: List[str], raiz: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=raiz, capture_output=True, text=True,
                              timeout=PRAZO_ANALISADOR_S, check=False)
    except subprocess.TimeoutExpired as e:
        raise ValueError(3, f"{cmd[0]} passou de {PRAZO_ANALISADOR_S} s; rode com alvo menor") from e
    except OSError as e:
        raise ValueError(3, f"falha ao executar {cmd[0]}: {e}") from e


def _em_lotes(seq: List[str]) -> Iterable[List[str]]:
    for i in range(0, len(seq), LOTE_ARQUIVOS):
        yield seq[i:i + LOTE_ARQUIVOS]


def _apontar(rel: str, linha: int, item: dict, cod: str, msg: str) -> Apontamento:
    return Apontamento(
        rel, linha,
        f"{item.get('id', '?')} {item.get('o_que_fere', '')} [{cod}: {msg}]",
        item.get("cura", "corrigir conforme a lista"),
        severidade=item.get("severidade", "aviso"),
        id=item.get("id"),
    )


def _ruff(raiz: Path, arquivos: List[Path], regua: Regua, avisos: List[str]) -> List[Apontamento]:
    if not arquivos or not regua.ruff:
        return []
    ruff = _binario("ruff", RUFF_UVX)
    if not ruff:
        raise ValueError(3, "linter python (ruff) ausente: nem `ruff` no PATH nem `uvx`")

    conhecidas = _rodar([*ruff, "rule", "--all", "--output-format", "json"], raiz)
    try:
        existentes = {r["code"] for r in json.loads(conhecidas.stdout)}
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(3, f"ruff nao listou as regras: {conhecidas.stderr.strip()[:300]}") from e
    selecao = sorted(c for c in regua.ruff if c in existentes)
    fora = sorted(set(regua.ruff) - existentes)
    if fora:
        avisos.append(f"codigos da lista que o ruff instalado nao conhece, fora da medida: {', '.join(fora)}")
    if not selecao:
        return []

    rels = [str(a.relative_to(raiz)) for a in arquivos]
    achados: List[Apontamento] = []
    for lote in _em_lotes(rels):
        proc = _rodar([*ruff, "check", "--isolated", "--no-cache", "--output-format", "json",
                       "--select", ",".join(selecao), *lote], raiz)
        if proc.returncode not in (0, 1):
            raise ValueError(3, f"ruff saiu {proc.returncode}: {proc.stderr.strip()[:400]}")
        for d in json.loads(proc.stdout or "[]"):
            cod = d.get("code") or ""
            item = regua.ruff.get(cod)
            if not item:
                continue
            caminho = Path(d["filename"])
            rel = str(caminho.relative_to(raiz)) if caminho.is_absolute() else str(caminho)
            if cod in _FORA_EM_TESTE and _e_teste(rel):
                continue
            if cod in _FORA_EM_ENTRADA and _e_entrada(rel, raiz / rel):
                continue
            achados.append(_apontar(rel, d.get("location", {}).get("row", 1), item, cod,
                                    d.get("message", "")))
    return achados


def _shellcheck(raiz: Path, arquivos: List[Path], regua: Regua, avisos: List[str]) -> List[Apontamento]:
    if not arquivos or not regua.shellcheck:
        return []
    sc = _binario("shellcheck", SHELLCHECK_UVX)
    if not sc:
        avisos.append(f"shellcheck ausente (nem no PATH nem por uvx): {len(regua.shellcheck)} "
                      f"regras de shell da lista nao medidas em {len(arquivos)} arquivos")
        return []
    rels = [str(a.relative_to(raiz)) for a in arquivos]
    incluir = ",".join(sorted(regua.shellcheck))
    achados: List[Apontamento] = []
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


def _set_e(raiz: Path, arquivos: List[Path], item: dict) -> List[Apontamento]:
    """Funcao que termina num `[ ... ] && ...` sob `set -e`: o status falso vaza como erro."""
    achados: List[Apontamento] = []
    for f in arquivos:
        try:
            linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(f.relative_to(raiz))
        nome, ultima, dentro = "", "", False
        for i, linha in enumerate(linhas, 1):
            if re.match(r"^[a-zA-Z_0-9]+ *\(\) *\{", linha):
                dentro, nome, ultima = True, linha.split("(", 1)[0].strip(), ""
            elif dentro and linha.strip() == "}":
                if re.match(r"^[ \t]*\[.*\][ \t]*&&", ultima) and "||" not in ultima:
                    achados.append(_apontar(rel, i - 1, item, "BASH_SET_E",
                                            f"{nome} termina com condicional sob set -e sem return/exit"))
                dentro = False
            elif dentro and linha.strip() and not linha.strip().startswith("#"):
                ultima = linha
    return achados


def _linhas_shell(raiz: Path, arquivos: List[Path], item: dict, piso: int) -> List[Apontamento]:
    achados: List[Apontamento] = []
    for f in arquivos:
        try:
            n = sum(1 for _ in f.open("rb"))
        except OSError:
            continue
        if n > piso:
            achados.append(_apontar(str(f.relative_to(raiz)), 1, item, "linhas",
                                    f"{n} linhas, piso {piso}"))
    return achados


# ------------------------------------------------------------------ stack (lint detectar)


def detectar_stack(raiz: Path) -> Optional[Tuple[str, str]]:
    """Stack do repositorio para `lint detectar`: (stack, comando)."""
    if any((raiz / n).exists() for n in ("pyproject.toml", ".ruff.toml", "ruff.toml", ".ruff_cache")):
        return "python", "ruff check"
    pkg = raiz / "package.json"
    if pkg.is_file():
        try:
            if '"lint"' in pkg.read_text(encoding="utf-8", errors="replace"):
                return "node", "npm run lint"
        except OSError:
            pass
    if (raiz / "bin").is_dir() or any(raiz.glob("*.sh")):
        return "bash", "shellcheck"
    return None


def raiz_da_stack(raiz: Path, alvo: Optional[str] = None) -> Path:
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
    alvo: Optional[str] = None,
) -> Tuple[List[Apontamento], str, int, List[str]]:
    """Aplica a lista ao alvo. Devolve (apontamentos, chave, rev, avisos).

    Levanta ValueError(exit, msg): 5 sem a lista no acervo, 3 com o analisador necessario
    ausente ou quebrado.
    """
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")
    regua = ler_regua(lista)
    raiz = Path(raiz).resolve()

    por_lingua: Dict[str, List[Path]] = {"python": [], "shell": []}
    for arq in _listar(raiz, alvo):
        lingua = linguagem(arq)
        if lingua:
            por_lingua[lingua].append(arq)

    avisos: List[str] = []
    achados = _ruff(raiz, por_lingua["python"], regua, avisos)
    achados += _shellcheck(raiz, por_lingua["shell"], regua, avisos)
    if regua.set_e:
        achados += _set_e(raiz, por_lingua["shell"], regua.set_e)
    if regua.linhas_shell:
        item, piso = regua.linhas_shell
        achados += _linhas_shell(raiz, por_lingua["shell"], item, piso)
    achados.sort(key=lambda a: (a.arquivo, a.linha, a.id or ""))
    return achados, CHAVE_LISTA, regua.rev, avisos
