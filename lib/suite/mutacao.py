"""Medida de eficácia da suíte por mutação do código exercitado (#4303)."""
from __future__ import annotations

import argparse
import ast
import gc
import importlib.util
import json
import os
import shutil
import signal
import site
import subprocess
import sys
import tempfile
import time
import types
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MAX_MUTANTES_POR_LINHA = 3
_LIMIAR_LINHAS_AMOSTRA_UM = 40
_NUM_OPERANDOS_BINARIOS = 2
_NUM_ARGS_WORKER = 3
_TIMEOUT_SONDA_S = 30
_TIMEOUT_WORKER_S = 540
_TIMEOUT_OLARIA_S = 15
_MAX_LINHAS_CABECALHO = 15

OPERADORES = (
    "troca_comparacao",
    "negacao_condicao",
    "retorno_none",
    "troca_constante",
)

_TROCA_COMP: dict[type[ast.cmpop], tuple[str, type[ast.cmpop]]] = {
    ast.Eq: ("!=", ast.NotEq),
    ast.NotEq: ("==", ast.Eq),
    ast.Lt: (">=", ast.GtE),
    ast.LtE: (">", ast.Gt),
    ast.Gt: ("<=", ast.LtE),
    ast.GtE: ("<", ast.Lt),
    ast.Is: ("is not", ast.IsNot),
    ast.IsNot: ("is", ast.Is),
    ast.In: ("not in", ast.NotIn),
    ast.NotIn: ("in", ast.In),
}

_ERROS_EXECUCAO_TESTE: tuple[type[BaseException], ...] = (
    BaseException,
)
_SUBPROCESS_RUN_REAL = subprocess.run

_NOMES_IGNORADOS_COPIA = frozenset({
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "node_modules",
    ".ruff_cache",
})


class MutacaoErro(Exception):
    """Impedimento na resolução ou na execução da medida de mutação."""


@dataclass
class Mutante:
    id: str
    arquivo: str
    linha: int
    funcao: str
    operador: str
    antes: str
    depois: str
    morto: bool = False
    morto_por: str | None = None
    _linha_mutada: str = field(default="", repr=False)


@dataclass
class ResultadoCaso:
    caso: str
    linhas_exercitadas: int
    mutantes_exercitados: int
    matou: str | None
    candidato_a_sair: bool


@dataclass
class MedidaComponente:
    componente: str
    mutantes_gerados: int
    mutantes_mortos: int
    escore_amostra: float
    funcoes_mutadas: list[str]
    candidatos_a_sair: list[str]
    mutantes_sobreviventes: list[Mutante]
    casos: list[ResultadoCaso]
    mutantes: list[Mutante]

    def para_dict(self) -> dict[str, Any]:
        return {
            "componente": self.componente,
            "mutantes_gerados": self.mutantes_gerados,
            "mutantes_mortos": self.mutantes_mortos,
            "escore_amostra": round(self.escore_amostra, 4),
            "funcoes_mutadas": list(self.funcoes_mutadas),
            "candidatos_a_sair": list(self.candidatos_a_sair),
            "mutantes_sobreviventes": [
                {k: v for k, v in asdict(m).items() if not k.startswith("_")}
                for m in self.mutantes_sobreviventes
            ],
            "casos": [asdict(c) for c in self.casos],
            "mutantes": [
                {k: v for k, v in asdict(m).items() if not k.startswith("_")}
                for m in self.mutantes
            ],
        }


def _raiz_padrao() -> Path:
    atual = Path(__file__).resolve()
    for p in atual.parents:
        if (p / ".git").exists():
            return p
    return Path.cwd()


def _ler_componente_olaria(chave: str) -> dict[str, Any] | None:
    url = os.environ.get("OLARIA_URL", "").rstrip("/")
    segredo = os.environ.get("OLARIA_CHAVE", "").strip()
    if not url or not segredo:
        return None
    corpo = json.dumps({"classe": "componente", "chaves": [chave], "fichas": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/ler",
        data=corpo,
        headers={
            "Content-Type": "application/json",
            "X-Olaria-Chave": segredo,
            "X-Olaria-Sujeito": os.environ.get("PF_CADEIRA", "engenharia"),
        },
        method="POST",
    )
    dados: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_OLARIA_S) as resp:
            lido = json.loads(resp.read().decode("utf-8"))
            if isinstance(lido, dict):
                dados = lido
    except (OSError, urllib.error.URLError, ValueError):
        dados = {}
    fichas = dados.get("fichas")
    if isinstance(fichas, list) and fichas and isinstance(fichas[0], dict):
        return fichas[0]
    return None


def _cabecalho_componente(arq: Path) -> str | None:
    linhas: list[str] = []
    try:
        linhas = arq.read_text(encoding="utf-8").splitlines()[:_MAX_LINHAS_CABECALHO]
    except OSError:
        linhas = []
    achado: str | None = None
    for linha in linhas:
        s = linha.strip()
        if not s or not s.startswith("#"):
            if s.startswith(('"""', "'''")):
                break
            continue
        corpo = s.lstrip("#").strip()
        if corpo.startswith("componente:"):
            achado = corpo.split(":", 1)[1].strip().removeprefix("componente:")
            break
    return achado


def _caminhos_da_ficha(ficha: dict[str, Any], arvore: Path) -> list[Path]:
    dados = ficha.get("dados") or {}
    bruto_cam = dados.get("caminho")
    lista_cam = [bruto_cam] if isinstance(bruto_cam, str) else list(bruto_cam or [])

    achados: list[Path] = []
    for rel in lista_cam:
        if not rel:
            continue
        cand_direto = arvore / rel
        if cand_direto.exists():
            achados.append(cand_direto.resolve())
    return achados


def _caminhos_por_convencao(slug: str, arvore: Path) -> list[Path]:
    for cand in (
        arvore / slug,
        arvore / "lib" / slug,
        arvore / "src" / slug,
    ):
        if cand.exists():
            return [cand.resolve()]

    achados: list[Path] = []
    for arq_teste in sorted(arvore.rglob("test_*.py")):
        if _cabecalho_componente(arq_teste) == slug:
            pai = arq_teste.parent
            comp_dir = pai.parent if pai.name in ("testes", "tests") else pai
            resolvido = comp_dir.resolve()
            if resolvido not in achados:
                achados.append(resolvido)
    if achados:
        return achados

    if list(arvore.glob("*.py")):
        return [arvore.resolve()]
    return []


def resolver_caminhos_componente(
    componente: str,
    arvore: Path,
    *,
    leitor_componente: Callable[[str], dict[str, Any] | None] | None = None,
) -> tuple[str, list[Path]]:
    """Resolve a chave canônica e os diretórios/arquivos do componente dentro de `arvore`."""
    slug = componente.strip().removeprefix("componente:")
    chave = f"componente:{slug}"
    leitor = leitor_componente or _ler_componente_olaria
    ficha = leitor(chave)

    caminhos = _caminhos_da_ficha(ficha, arvore) if isinstance(ficha, dict) else []
    if not caminhos:
        caminhos = _caminhos_por_convencao(slug, arvore)
    if not caminhos:
        raise MutacaoErro(f"componente '{chave}' não encontrado na árvore {arvore}")
    return chave, caminhos


def _eh_arquivo_teste(arq: Path, raizes_comp: list[Path]) -> bool:
    nome = arq.name
    if nome.startswith("test_") or nome.endswith("_test.py") or nome == "conftest.py":
        return True
    pastas_teste = {"testes", "tests", "apoio", "fixtura"}
    for r in raizes_comp:
        partes = arq.relative_to(r).parts if arq.is_relative_to(r) else arq.parts
        if pastas_teste.intersection(partes):
            return True
    return False


def _classificar_py_da_raiz(
    r: Path,
    raizes_comp: list[Path],
    fontes: list[Path],
    testes: list[Path],
    inits: list[Path],
) -> None:
    if r.is_file() and r.suffix == ".py":
        (testes if _eh_arquivo_teste(r, raizes_comp) else fontes).append(r)
        return
    for arq in sorted(r.rglob("*.py")):
        if "__pycache__" in arq.parts:
            continue
        if arq.name.startswith("test_") or arq.name.endswith("_test.py"):
            testes.append(arq)
        elif _eh_arquivo_teste(arq, raizes_comp) or arq.name == "__main__.py":
            continue
        elif arq.name == "__init__.py":
            inits.append(arq)
        else:
            fontes.append(arq)


def _coletar_arquivos(raizes_comp: list[Path], arvore: Path, slug: str) -> tuple[list[Path], list[Path]]:
    fontes: list[Path] = []
    testes: list[Path] = []
    inits: list[Path] = []

    for r in raizes_comp:
        _classificar_py_da_raiz(r, raizes_comp, fontes, testes, inits)

    if not fontes and inits:
        fontes.extend(inits)

    if not testes:
        testes.extend(
            arq
            for arq in sorted(arvore.rglob("test_*.py"))
            if _cabecalho_componente(arq) == slug and arq not in testes
        )
    return fontes, testes


def _substituir_fatia_linha(linha: str, col_ini: int, col_fim: int, novo_trecho: str) -> str:
    b = linha.encode("utf-8")
    return (b[:col_ini] + novo_trecho.encode("utf-8") + b[col_fim:]).decode("utf-8")


def _extrair_fatia_linha(linha: str, col_ini: int, col_fim: int) -> str:
    b = linha.encode("utf-8")
    return b[col_ini:col_fim].decode("utf-8")


def _marcar_subarvore(raiz_no: ast.AST | None, destino: set[int]) -> None:
    if raiz_no is None:
        return
    for sub in ast.walk(raiz_no):
        destino.add(id(sub))


def _argumentos_da_funcao(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    extras = [a for a in (fn.args.vararg, fn.args.kwarg) if a is not None]
    return [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs, *extras]


def _marcar_constantes_internas(sub: ast.AST, ignorados: set[int]) -> None:
    if isinstance(sub, ast.AnnAssign):
        _marcar_subarvore(sub.annotation, ignorados)
    elif isinstance(sub, ast.JoinedStr):
        for v in sub.values:
            if isinstance(v, ast.Constant):
                ignorados.add(id(v))
            elif isinstance(v, ast.FormattedValue):
                _marcar_subarvore(v.format_spec, ignorados)
    elif isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant) and sub.value.value is None:
        ignorados.add(id(sub.value))


def _nos_ignorados_constante(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    """IDs de nós ast.Constant que são docstrings, anotações de tipo ou especificadores de f-string."""
    ignorados: set[int] = set()
    if (
        func_node.body
        and isinstance(func_node.body[0], ast.Expr)
        and isinstance(func_node.body[0].value, ast.Constant)
        and isinstance(func_node.body[0].value.value, str)
    ):
        ignorados.add(id(func_node.body[0].value))

    for dec in func_node.decorator_list:
        _marcar_subarvore(dec, ignorados)
    _marcar_subarvore(func_node.returns, ignorados)
    for arg in _argumentos_da_funcao(func_node):
        _marcar_subarvore(arg.annotation, ignorados)
    for sub in ast.walk(func_node):
        _marcar_constantes_internas(sub, ignorados)
    return ignorados


def _mutar_comparacoes(nos_linha: list[ast.AST], linha_str: str) -> list[tuple[str, str, str, str]]:
    res: list[tuple[str, str, str, str]] = []
    for no in nos_linha:
        if isinstance(no, ast.Compare) and len(no.ops) == 1 and type(no.ops[0]) in _TROCA_COMP:
            simbolo, _ = _TROCA_COMP[type(no.ops[0])]
            antes_txt = _extrair_fatia_linha(linha_str, no.col_offset, no.end_col_offset)
            esq = _extrair_fatia_linha(linha_str, no.left.col_offset, no.left.end_col_offset)
            dir_no = no.comparators[0]
            dir_txt = _extrair_fatia_linha(linha_str, dir_no.col_offset, dir_no.end_col_offset)
            depois_txt = f"({esq} {simbolo} {dir_txt})"
            nova_l = _substituir_fatia_linha(linha_str, no.col_offset, no.end_col_offset, depois_txt)
            res.append(("troca_comparacao", antes_txt, depois_txt, nova_l))
    return res


def _mutar_condicoes(
    ifs_linha: list[ast.If | ast.IfExp],
    nos_linha: list[ast.AST],
    linha_str: str,
) -> list[tuple[str, str, str, str]]:
    res: list[tuple[str, str, str, str]] = []
    for no_if in ifs_linha:
        t = no_if.test
        antes_txt = _extrair_fatia_linha(linha_str, t.col_offset, t.end_col_offset)
        depois_txt = f"(not ({antes_txt}))"
        nova_l = _substituir_fatia_linha(linha_str, t.col_offset, t.end_col_offset, depois_txt)
        res.append(("negacao_condicao", antes_txt, depois_txt, nova_l))

    for no in nos_linha:
        if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.Not):
            antes_txt = _extrair_fatia_linha(linha_str, no.col_offset, no.end_col_offset)
            opnd = no.operand
            depois_txt = f"({_extrair_fatia_linha(linha_str, opnd.col_offset, opnd.end_col_offset)})"
            nova_l = _substituir_fatia_linha(linha_str, no.col_offset, no.end_col_offset, depois_txt)
            res.append(("negacao_condicao", antes_txt, depois_txt, nova_l))
        elif isinstance(no, ast.BoolOp) and len(no.values) == _NUM_OPERANDOS_BINARIOS:
            antes_txt = _extrair_fatia_linha(linha_str, no.col_offset, no.end_col_offset)
            v0 = _extrair_fatia_linha(linha_str, no.values[0].col_offset, no.values[0].end_col_offset)
            v1 = _extrair_fatia_linha(linha_str, no.values[1].col_offset, no.values[1].end_col_offset)
            op_str = "or" if isinstance(no.op, ast.And) else "and"
            depois_txt = f"({v0} {op_str} {v1})"
            nova_l = _substituir_fatia_linha(linha_str, no.col_offset, no.end_col_offset, depois_txt)
            res.append(("negacao_condicao", antes_txt, depois_txt, nova_l))
    return res


def _mutar_retornos(nos_linha: list[ast.AST], linha_str: str) -> list[tuple[str, str, str, str]]:
    res: list[tuple[str, str, str, str]] = []
    for no in nos_linha:
        if isinstance(no, ast.Return) and no.value is not None:
            if isinstance(no.value, ast.Constant) and no.value.value is None:
                continue
            antes_txt = _extrair_fatia_linha(linha_str, no.col_offset, no.end_col_offset)
            nova_l = _substituir_fatia_linha(linha_str, no.col_offset, no.end_col_offset, "return None")
            res.append(("retorno_none", antes_txt, "return None", nova_l))
    return res


def _valor_constante_mutado(val: Any) -> str | None:
    if val is True:
        return "False"
    if val is False:
        return "True"
    if type(val) is int:
        return "1" if val == 0 else repr(val + 1)
    if type(val) is float:
        return "1.0" if val == 0.0 else repr(val + 1.0)
    if type(val) is str:
        return '""' if val != "" else '"mutado"'
    return None


def _mutar_constantes(
    nos_linha: list[ast.AST],
    linha_str: str,
    ignorados_const: set[int],
) -> list[tuple[str, str, str, str]]:
    res: list[tuple[str, str, str, str]] = []
    for no in nos_linha:
        if isinstance(no, ast.Constant) and id(no) not in ignorados_const:
            depois_txt = _valor_constante_mutado(no.value)
            if depois_txt is not None:
                antes_txt = _extrair_fatia_linha(linha_str, no.col_offset, no.end_col_offset)
                nova_l = _substituir_fatia_linha(linha_str, no.col_offset, no.end_col_offset, depois_txt)
                res.append(("troca_constante", antes_txt, depois_txt, nova_l))
    return res


def _candidatos_da_linha(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    lineno: int,
    linha_str: str,
    ignorados_const: set[int],
) -> list[tuple[str, str, str, str]]:
    """Devolve até MAX_MUTANTES_POR_LINHA tuplas (operador, antes, depois, linha_mutada)."""
    todos_nos = [no for stmt in fn.body for no in ast.walk(stmt)]
    nos_linha = [
        no
        for no in todos_nos
        if getattr(no, "lineno", None) == lineno
        and getattr(no, "end_lineno", None) == lineno
        and getattr(no, "col_offset", None) is not None
        and getattr(no, "end_col_offset", None) is not None
    ]
    ifs_linha = [
        no
        for no in todos_nos
        if isinstance(no, (ast.If, ast.IfExp))
        and getattr(no.test, "lineno", None) == lineno
        and getattr(no.test, "end_lineno", None) == lineno
    ]

    brutos = [
        *_mutar_comparacoes(nos_linha, linha_str),
        *_mutar_condicoes(ifs_linha, nos_linha, linha_str),
        *_mutar_retornos(nos_linha, linha_str),
        *_mutar_constantes(nos_linha, linha_str, ignorados_const),
    ]

    candidatos: list[tuple[str, str, str, str]] = []
    vistos: set[str] = set()
    for op, antes, depois, nova_linha in brutos:
        if len(candidatos) >= MAX_MUTANTES_POR_LINHA:
            break
        if nova_linha != linha_str and nova_linha not in vistos:
            vistos.add(nova_linha)
            candidatos.append((op, antes.strip(), depois.strip(), nova_linha))
    return candidatos


@dataclass
class _FonteMutavel:
    caminho: Path
    rel_nome: str
    linhas: list[str]
    sufixo: str
    linhas_exercitadas: set[int]
    teto_linha: int = MAX_MUTANTES_POR_LINHA
    linhas_ja_mutadas: set[int] = field(default_factory=set)


def _compila_sem_erro(texto_mut: str, caminho: Path) -> bool:
    valido = True
    try:
        compile(texto_mut, str(caminho), "exec")
    except SyntaxError:
        valido = False
    return valido


def _mutantes_da_funcao(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    fonte: _FonteMutavel,
    seq_inicial: int,
) -> list[Mutante]:
    ini_corpo = fn.body[0].lineno if fn.body else fn.lineno + 1
    fim_corpo = fn.end_lineno or fn.lineno
    linhas_fn = sorted(
        lin
        for lin in fonte.linhas_exercitadas
        if ini_corpo <= lin <= fim_corpo and lin not in fonte.linhas_ja_mutadas
    )
    if not linhas_fn:
        return []

    ignorados = _nos_ignorados_constante(fn)
    gerados: list[Mutante] = []
    seq = seq_inicial

    for lin in linhas_fn:
        if not (1 <= lin <= len(fonte.linhas)):
            continue
        cands = _candidatos_da_linha(fn, lin, fonte.linhas[lin - 1], ignorados)
        adicionados = 0
        for op, antes, depois, nova_linha in cands:
            if adicionados >= fonte.teto_linha:
                break
            copia_linhas = list(fonte.linhas)
            copia_linhas[lin - 1] = nova_linha
            if not _compila_sem_erro("\n".join(copia_linhas) + fonte.sufixo, fonte.caminho):
                continue
            gerados.append(
                Mutante(
                    id=f"m{seq}",
                    arquivo=fonte.rel_nome,
                    linha=lin,
                    funcao=fn.name,
                    operador=op,
                    antes=antes,
                    depois=depois,
                    _linha_mutada=nova_linha,
                )
            )
            seq += 1
            adicionados += 1
        if adicionados > 0:
            fonte.linhas_ja_mutadas.add(lin)
    return gerados


def gerar_mutantes_arquivo(
    caminho: Path,
    rel_nome: str,
    linhas_exercitadas: set[int],
    *,
    proximo_id: int = 1,
    teto_por_linha: int = MAX_MUTANTES_POR_LINHA,
) -> list[Mutante]:
    """Gera até `teto_por_linha` mutantes por linha exercitada dentro das funções de `caminho`."""
    if not linhas_exercitadas:
        return []
    texto = caminho.read_text(encoding="utf-8")
    arvore_ast = ast.parse(texto, filename=str(caminho))
    fonte = _FonteMutavel(
        caminho=caminho,
        rel_nome=rel_nome,
        linhas=texto.splitlines(),
        sufixo="\n" if texto.endswith("\n") else "",
        linhas_exercitadas=linhas_exercitadas,
        teto_linha=teto_por_linha,
    )

    funcoes = [
        no
        for no in ast.walk(arvore_ast)
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    funcoes.sort(key=lambda f: (f.lineno, -(f.end_lineno or f.lineno)))

    mutantes: list[Mutante] = []
    seq = proximo_id
    for fn in funcoes:
        novos = _mutantes_da_funcao(fn, fonte, seq)
        mutantes.extend(novos)
        seq += len(novos)
    return mutantes


def _comando_python_pytest() -> list[str]:
    """Escolhe o comando que roda o Python com pytest (e coverage, se disponível)."""
    if importlib.util.find_spec("pytest") is not None:
        return [sys.executable]
    uv = shutil.which("uv") or "/usr/local/bin/uv"
    if os.access(uv, os.X_OK):
        for extras in (["--with", "pytest", "--with", "coverage"], ["--with", "pytest"]):
            r = subprocess.run(
                [uv, "run", "--offline", "--no-project", "--python", sys.executable, *extras, "python", "-c", "import pytest"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SONDA_S,
                check=False,
            )
            if r.returncode == 0:
                return [uv, "run", "--offline", "--no-project", "--python", sys.executable, *extras, "python"]
        return [uv, "run", "--no-project", "--python", sys.executable, "--with", "pytest", "python"]
    return [sys.executable]


def _copiar_item_arvore(item: Path, dest_item: Path, ignorar: Callable[..., set[str]]) -> None:
    if item.is_dir():
        shutil.copytree(item, dest_item, ignore=ignorar, dirs_exist_ok=True)
    else:
        shutil.copy2(item, dest_item)


def _enlazar_ou_copiar(item: Path, dest_item: Path, ignorar: Callable[..., set[str]]) -> None:
    try:
        dest_item.symlink_to(item.resolve())
    except OSError:
        _copiar_item_arvore(item, dest_item, ignorar)


def _povoar_diretorio_copia(
    orig_dir: Path,
    dest_dir: Path,
    rel_atual: Path,
    rels_comp: list[Path],
    ignorar: Callable[..., set[str]],
) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in orig_dir.iterdir():
        if item.name in _NOMES_IGNORADOS_COPIA:
            continue
        rel_item = rel_atual / item.name if str(rel_atual) != "." else Path(item.name)
        dest_item = dest_dir / item.name
        eh_alvo = any(rel_item == rc or rc in rel_item.parents for rc in rels_comp)
        eh_ancestral = any(rel_item in rc.parents for rc in rels_comp)
        if eh_alvo:
            _copiar_item_arvore(item, dest_item, ignorar)
        elif eh_ancestral and item.is_dir():
            _povoar_diretorio_copia(item, dest_item, rel_item, rels_comp, ignorar)
        else:
            _enlazar_ou_copiar(item, dest_item, ignorar)


def _preparar_copia_temporaria(arvore: Path, raizes_comp: list[Path], tmp_raiz: Path) -> tuple[Path, list[Path]]:
    """Cria em `tmp_raiz` uma cópia da árvore onde os caminhos do componente são arquivos reais graváveis."""
    destino_arvore = tmp_raiz / "arvore"
    arvore_res = arvore.resolve()
    rels_comp = [
        r.resolve().relative_to(arvore_res) if r.resolve().is_relative_to(arvore_res) else Path(r.name)
        for r in raizes_comp
    ]
    ignorar = shutil.ignore_patterns(*_NOMES_IGNORADOS_COPIA)
    _povoar_diretorio_copia(arvore_res, destino_arvore, Path("."), rels_comp, ignorar)
    return destino_arvore, [destino_arvore / rc for rc in rels_comp]


def _extrair_code_map(code_obj: types.CodeType) -> dict[tuple[str, int], types.CodeType]:
    mapa: dict[tuple[str, int], types.CodeType] = {}
    pilha = [code_obj]
    while pilha:
        atual = pilha.pop()
        for const in atual.co_consts:
            if isinstance(const, types.CodeType):
                mapa[(const.co_name, const.co_firstlineno)] = const
                pilha.append(const)
    return mapa


def _funcoes_vivas_do_arquivo(arq_str: str) -> list[types.FunctionType]:
    arq_real = os.path.realpath(arq_str)
    achadas: list[types.FunctionType] = []
    for obj in gc.get_objects():
        if isinstance(obj, types.FunctionType):
            co = getattr(obj, "__code__", None)
            if co is not None and os.path.realpath(co.co_filename) == arq_real:
                achadas.append(obj)
    return achadas


def _limpar_caches_modulo(arq_str: str) -> None:
    arq_real = os.path.realpath(arq_str)
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if f and os.path.realpath(f) == arq_real:
            for val in list(vars(mod).values()):
                limpar = getattr(val, "cache_clear", None)
                if callable(limpar):
                    limpar()


@dataclass
class _EstadoFixtureCaso:
    funcargs: dict[str, Any]
    listas: list[tuple[list[Any], list[Any]]]
    dicionarios: list[tuple[dict[Any, Any], dict[Any, Any]]]
    patches_mp: list[tuple[Any, str, Any, Any]]
    mp_obj: Any = None
    tmp_dir: Path | None = None
    tmp_arquivos: dict[Path, bytes] = field(default_factory=dict)


def _capturar_containers(
    obj: Any,
    vistos: set[int],
    listas: list[tuple[list[Any], list[Any]]],
    dicionarios: list[tuple[dict[Any, Any], dict[Any, Any]]],
) -> None:
    oid = id(obj)
    if oid in vistos:
        return
    if isinstance(obj, list):
        vistos.add(oid)
        listas.append((obj, list(obj)))
        for item in obj:
            _capturar_containers(item, vistos, listas, dicionarios)
    elif isinstance(obj, dict):
        vistos.add(oid)
        dicionarios.append((obj, dict(obj)))
        for v in obj.values():
            _capturar_containers(v, vistos, listas, dicionarios)


def _obter_fixture_opcional(item: Any, nome: str, fargs: dict[str, Any]) -> Any:
    if nome in fargs:
        return fargs[nome]
    if nome in getattr(item, "fixturenames", ()):
        req = getattr(item, "_request", None)
        if req is not None and hasattr(req, "getfixturevalue"):
            return req.getfixturevalue(nome)
    return None


def _capturar_estado_fixture(item: Any) -> _EstadoFixtureCaso:
    fargs = dict(getattr(item, "funcargs", None) or {})
    listas: list[tuple[list[Any], list[Any]]] = []
    dicionarios: list[tuple[dict[Any, Any], dict[Any, Any]]] = []
    vistos: set[int] = set()
    for val in fargs.values():
        _capturar_containers(val, vistos, listas, dicionarios)

    mp_obj = _obter_fixture_opcional(item, "monkeypatch", fargs)
    patches_mp = [
        (alvo, nome, getattr(alvo, nome, None), antigo)
        for alvo, nome, antigo in getattr(mp_obj, "_setattr", ())
    ]
    tmp_val = _obter_fixture_opcional(item, "tmp_path", fargs)
    tmp_dir = tmp_val if isinstance(tmp_val, Path) and tmp_val.is_dir() else None
    tmp_arquivos = (
        {p.relative_to(tmp_dir): p.read_bytes() for p in tmp_dir.rglob("*") if p.is_file()}
        if tmp_dir is not None
        else {}
    )

    return _EstadoFixtureCaso(
        funcargs=fargs,
        listas=listas,
        dicionarios=dicionarios,
        patches_mp=patches_mp,
        mp_obj=mp_obj,
        tmp_dir=tmp_dir,
        tmp_arquivos=tmp_arquivos,
    )


def _restaurar_tmp_dir(tmp_dir: Path, arquivos: dict[Path, bytes]) -> None:
    if not tmp_dir.is_dir():
        return
    for item in list(tmp_dir.iterdir()):
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
    for rel, dados in arquivos.items():
        destino = tmp_dir / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(dados)


def _restaurar_estado_fixture(estado: _EstadoFixtureCaso) -> None:
    if estado.tmp_dir is not None:
        _restaurar_tmp_dir(estado.tmp_dir, estado.tmp_arquivos)
    for lista_ref, copia_l in estado.listas:
        lista_ref[:] = list(copia_l)
    for dict_ref, copia_d in estado.dicionarios:
        dict_ref.clear()
        dict_ref.update(copia_d)
    for alvo, nome, val_mock, _antigo in estado.patches_mp:
        setattr(alvo, nome, val_mock)


def _desfazer_patches_fixture(estado: _EstadoFixtureCaso) -> None:
    if estado.mp_obj is not None and hasattr(estado.mp_obj, "undo"):
        estado.mp_obj.undo()
    for alvo, nome, _val_mock, antigo in reversed(estado.patches_mp):
        if type(antigo).__name__ != "Notset":
            setattr(alvo, nome, antigo)


class _ColetorCoberturaPytest:
    def __init__(self, fontes_map: dict[str, str]) -> None:
        self.fontes_map = fontes_map
        self.linhas_por_caso: dict[str, set[tuple[str, int]]] = {}
        self.itens_aprovados: dict[str, Any] = {}
        self.estados_por_caso: dict[str, _EstadoFixtureCaso] = {}
        self.tempo_por_caso: dict[str, float] = {}
        self._atual: str | None = None
        self._falhou: set[str] = set()

    def _trace(self, frame: Any, event: str, _arg: Any) -> Any:
        if self._atual is None:
            return None
        rel = self.fontes_map.get(frame.f_code.co_filename)
        if rel is None:
            return None
        if event == "line":
            self.linhas_por_caso[self._atual].add((rel, frame.f_lineno))
        return self._trace

    def registrar_hooks(self, pytest_mod: Any) -> Any:
        coletor = self

        class _Plugin:
            @pytest_mod.hookimpl(hookwrapper=True)
            def pytest_runtest_call(self, item: Any) -> Any:
                nid = item.nodeid
                coletor._atual = nid
                coletor.linhas_por_caso.setdefault(nid, set())
                coletor.estados_por_caso[nid] = _capturar_estado_fixture(item)
                t0 = time.monotonic()
                antigo_trace = sys.gettrace()
                sys.settrace(coletor._trace)
                try:
                    yield
                finally:
                    sys.settrace(antigo_trace)
                    coletor.tempo_por_caso[nid] = max(0.001, time.monotonic() - t0)
                    coletor._atual = None

            def pytest_runtest_logreport(self, report: Any) -> None:
                if report.failed:
                    coletor._falhou.add(report.nodeid)

            @pytest_mod.hookimpl(trylast=True)
            def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
                for item in session.items:
                    if item.nodeid not in coletor._falhou and item.nodeid in coletor.linhas_por_caso:
                        coletor.itens_aprovados[item.nodeid] = item

        return _Plugin()


def _rodar_item_contra_mutante(
    item: Any,
    estado: _EstadoFixtureCaso,
    skipped_cls: type[BaseException],
    prazo_s: float = 0.25,
) -> bool:
    def _alarme(_sig: int, _frame: Any) -> None:
        raise TimeoutError("mutante excedeu o tempo limite")

    def _run_com_teto(*args: Any, **kwargs: Any) -> Any:
        t_atual = kwargs.get("timeout")
        kwargs["timeout"] = min(float(t_atual), prazo_s) if t_atual is not None else prazo_s
        return _SUBPROCESS_RUN_REAL(*args, **kwargs)

    _restaurar_estado_fixture(estado)
    item.funcargs = dict(estado.funcargs)
    subprocess.run = _run_com_teto  # type: ignore[assignment]
    antigo = signal.signal(signal.SIGALRM, _alarme)
    signal.setitimer(signal.ITIMER_REAL, prazo_s)
    matou = False
    try:
        item.runtest()
        signal.setitimer(signal.ITIMER_REAL, 0.0)
    except skipped_cls:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        matou = False
    except _ERROS_EXECUCAO_TESTE:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        matou = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, antigo)
        subprocess.run = _SUBPROCESS_RUN_REAL  # type: ignore[assignment]
        _desfazer_patches_fixture(estado)
    return matou


@dataclass
class _ContextoAvaliacao:
    coletor: _ColetorCoberturaPytest
    rel_para_abs: dict[str, Path]
    textos_orig: dict[str, str]
    linhas_orig: dict[str, list[str]]
    funcoes_vivas: dict[str, list[types.FunctionType]]
    codes_orig: dict[types.FunctionType, types.CodeType]
    skipped_cls: type[BaseException]

    def _rodar_caso(self, nid: str, m: Mutante, matou_por_caso: dict[str, str | None]) -> bool:
        item = self.coletor.itens_aprovados[nid]
        t_base = self.coletor.tempo_por_caso.get(nid, 0.01)
        prazo = max(0.08, min(1.0, t_base * 6.0))
        matou = _rodar_item_contra_mutante(
            item,
            self.coletor.estados_por_caso[nid],
            self.skipped_cls,
            prazo_s=prazo,
        )
        if matou:
            if matou_por_caso.get(nid) is None:
                matou_por_caso[nid] = m.id
            if not m.morto:
                m.morto = True
                m.morto_por = nid
        return matou

    def _aplicar_mutante(self, m: Mutante) -> list[types.FunctionType]:
        rel = m.arquivo
        arq_path = self.rel_para_abs[rel]
        txt_orig = self.textos_orig[rel]
        copia_l = list(self.linhas_orig[rel])
        copia_l[m.linha - 1] = m._linha_mutada
        txt_mut = "\n".join(copia_l) + ("\n" if txt_orig.endswith("\n") else "")

        mapa_codes = _extrair_code_map(compile(txt_mut, str(arq_path), "exec"))
        trocadas: list[types.FunctionType] = []
        for fn_obj in self.funcoes_vivas.get(rel, []):
            c_orig = self.codes_orig[fn_obj]
            c_novo = mapa_codes.get((c_orig.co_name, c_orig.co_firstlineno))
            if (
                c_novo is not None
                and c_novo.co_freevars == c_orig.co_freevars
                and c_novo.co_cellvars == c_orig.co_cellvars
            ):
                fn_obj.__code__ = c_novo
                trocadas.append(fn_obj)
        if not trocadas:
            arq_path.write_text(txt_mut, encoding="utf-8")
        _limpar_caches_modulo(str(arq_path))
        return trocadas

    def _restaurar_mutante(self, m: Mutante, trocadas: list[types.FunctionType]) -> None:
        rel = m.arquivo
        arq_path = self.rel_para_abs[rel]
        for fn_obj in trocadas:
            fn_obj.__code__ = self.codes_orig[fn_obj]
        if not trocadas:
            arq_path.write_text(self.textos_orig[rel], encoding="utf-8")
        _limpar_caches_modulo(str(arq_path))

    def avaliar_mutante(
        self,
        m: Mutante,
        casos_linha: list[str],
        matou_por_caso: dict[str, str | None],
    ) -> None:
        if not casos_linha:
            return
        trocadas = self._aplicar_mutante(m)
        pendentes = [nid for nid in casos_linha if matou_por_caso.get(nid) is None]
        ja_rodados = set(pendentes)
        try:
            for nid in pendentes:
                self._rodar_caso(nid, m, matou_por_caso)
            if not m.morto:
                any(
                    self._rodar_caso(nid, m, matou_por_caso)
                    for nid in casos_linha
                    if nid not in ja_rodados
                )
        finally:
            self._restaurar_mutante(m, trocadas)


def _avaliar_casos_e_mutantes(
    ctx: _ContextoAvaliacao,
    todos_mutantes: list[Mutante],
    casos_por_linha: dict[tuple[str, int], list[str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    mutantes_por_linha: dict[tuple[str, int], list[Mutante]] = {}
    for m in todos_mutantes:
        mutantes_por_linha.setdefault((m.arquivo, m.linha), []).append(m)

    matou_por_caso: dict[str, str | None] = {nid: None for nid in ctx.coletor.itens_aprovados}
    for m in todos_mutantes:
        casos_ord = sorted(
            casos_por_linha.get((m.arquivo, m.linha), []),
            key=lambda n: ctx.coletor.tempo_por_caso.get(n, 0.01),
        )
        ctx.avaliar_mutante(m, casos_ord, matou_por_caso)

    resultados_casos: list[dict[str, Any]] = []
    candidatos_a_sair: list[str] = []

    for nid in sorted(ctx.coletor.itens_aprovados):
        pares = ctx.coletor.linhas_por_caso.get(nid, set())
        n_muts = sum(len(mutantes_por_linha.get(par, [])) for par in pares)
        matou_id = matou_por_caso.get(nid)
        cand = n_muts > 0 and matou_id is None
        if cand:
            candidatos_a_sair.append(nid)
        resultados_casos.append(
            {
                "caso": nid,
                "linhas_exercitadas": len(pares),
                "mutantes_exercitados": n_muts,
                "matou": matou_id,
                "candidato_a_sair": cand,
            }
        )

    return resultados_casos, candidatos_a_sair


def _recortar_amostra_linhas(
    coletor: _ColetorCoberturaPytest,
    linhas_por_arq: dict[str, set[int]],
) -> tuple[dict[str, set[int]], int]:
    total_linhas = sum(len(s) for s in linhas_por_arq.values())
    if total_linhas <= _LIMIAR_LINHAS_AMOSTRA_UM:
        return linhas_por_arq, MAX_MUTANTES_POR_LINHA
    amostradas: dict[str, set[int]] = {rel: set() for rel in linhas_por_arq}
    for nid in sorted(coletor.itens_aprovados):
        for rel, lin in sorted(coletor.linhas_por_caso.get(nid, set()))[:4]:
            amostradas.setdefault(rel, set()).add(lin)
    for rel, conj in linhas_por_arq.items():
        for lin in sorted(conj)[:12]:
            amostradas.setdefault(rel, set()).add(lin)
    return amostradas, 1


def _executar_worker(arq_cfg_str: str, arq_saida_str: str) -> int:
    import pytest
    from _pytest.outcomes import Skipped

    cfg = json.loads(Path(arq_cfg_str).read_text(encoding="utf-8"))
    for p in reversed(cfg["pythonpath"]):
        if p not in sys.path:
            sys.path.insert(0, p)

    fontes_map: dict[str, str] = {}
    for rel, c in cfg["fontes"].items():
        fontes_map[str(c)] = rel
        fontes_map[os.path.abspath(c)] = rel
        fontes_map[os.path.realpath(c)] = rel
    rel_para_abs = {rel: Path(c) for rel, c in cfg["fontes"].items()}

    coletor = _ColetorCoberturaPytest(fontes_map)
    pytest.main(["-q", "-p", "no:cacheprovider", *cfg["testes"]], plugins=[coletor.registrar_hooks(pytest)])

    linhas_por_arq: dict[str, set[int]] = {rel: set() for rel in rel_para_abs}
    casos_por_linha: dict[tuple[str, int], list[str]] = {}
    for nid, pares in coletor.linhas_por_caso.items():
        if nid in coletor.itens_aprovados:
            for rel, lin in pares:
                linhas_por_arq.setdefault(rel, set()).add(lin)
                casos_por_linha.setdefault((rel, lin), []).append(nid)

    linhas_por_arq, teto_l = _recortar_amostra_linhas(coletor, linhas_por_arq)

    todos_mutantes: list[Mutante] = []
    for rel in sorted(rel_para_abs):
        gerados = gerar_mutantes_arquivo(
            rel_para_abs[rel],
            rel,
            linhas_por_arq.get(rel, set()),
            proximo_id=len(todos_mutantes) + 1,
            teto_por_linha=teto_l,
        )
        todos_mutantes.extend(gerados)

    textos_orig = {rel: p.read_text(encoding="utf-8") for rel, p in rel_para_abs.items()}
    funcoes_vivas = {rel: _funcoes_vivas_do_arquivo(str(p)) for rel, p in rel_para_abs.items()}
    ctx = _ContextoAvaliacao(
        coletor=coletor,
        rel_para_abs=rel_para_abs,
        textos_orig=textos_orig,
        linhas_orig={rel: txt.splitlines() for rel, txt in textos_orig.items()},
        funcoes_vivas=funcoes_vivas,
        codes_orig={fn: fn.__code__ for lista in funcoes_vivas.values() for fn in lista},
        skipped_cls=Skipped,
    )
    resultados_casos, candidatos_a_sair = _avaliar_casos_e_mutantes(ctx, todos_mutantes, casos_por_linha)

    saida = {
        "casos": resultados_casos,
        "candidatos_a_sair": candidatos_a_sair,
        "mutantes": [
            {k: v for k, v in asdict(m).items() if not k.startswith("_")}
            for m in todos_mutantes
        ],
    }
    Path(arq_saida_str).write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
    return 0


def _montar_pythonpath_worker(copia_raizes: list[Path], copia_arvore: Path) -> list[str]:
    pythonpath: list[str] = [str(Path(__file__).resolve().parents[1])]
    for r in copia_raizes:
        d = r if r.is_dir() else r.parent
        for cand in (d, d.parent):
            if str(cand) not in pythonpath:
                pythonpath.append(str(cand))
    if str(copia_arvore) not in pythonpath:
        pythonpath.append(str(copia_arvore))
    for sp in site.getsitepackages():
        if os.path.isdir(sp) and sp not in pythonpath:
            pythonpath.append(sp)
    return pythonpath


def _rodar_subprocesso_worker(
    chave: str,
    copia_arvore: Path,
    copia_raizes: list[Path],
    tmp_raiz: Path,
) -> dict[str, Any]:
    slug = chave.removeprefix("componente:")
    fontes, testes = _coletar_arquivos(copia_raizes, copia_arvore, slug)
    if not fontes:
        raise MutacaoErro(f"nenhum arquivo de código encontrado para {chave}")
    if not testes:
        raise MutacaoErro(f"nenhum arquivo de teste encontrado para {chave}")

    base_rel = copia_raizes[0] if len(copia_raizes) == 1 and copia_raizes[0].is_dir() else copia_arvore
    mapa_fontes = {
        (str(f.relative_to(base_rel)) if f.is_relative_to(base_rel) else f.name): str(f)
        for f in fontes
    }
    pythonpath = _montar_pythonpath_worker(copia_raizes, copia_arvore)
    arq_cfg = tmp_raiz / "entrada.json"
    arq_saida = tmp_raiz / "saida.json"
    arq_cfg.write_text(
        json.dumps(
            {"fontes": mapa_fontes, "testes": [str(t) for t in testes], "pythonpath": pythonpath},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        *_comando_python_pytest(),
        "-c",
        "import sys; from suite.mutacao import _executar_worker; raise SystemExit(_executar_worker(sys.argv[1], sys.argv[2]))",
        str(arq_cfg),
        str(arq_saida),
    ]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": os.pathsep.join(pythonpath)}
    cwd_exec = copia_raizes[0] if copia_raizes[0].is_dir() else copia_arvore
    arq_out = tmp_raiz / "worker.out"
    arq_err = tmp_raiz / "worker.err"
    with arq_out.open("w", encoding="utf-8") as f_out, arq_err.open("w", encoding="utf-8") as f_err:
        proc = subprocess.run(cmd, cwd=cwd_exec, env=env, stdout=f_out, stderr=f_err, timeout=_TIMEOUT_WORKER_S, check=False)
    if not arq_saida.is_file():
        err_txt = arq_err.read_text(encoding="utf-8").strip() if arq_err.is_file() else ""
        out_txt = arq_out.read_text(encoding="utf-8").strip() if arq_out.is_file() else ""
        detalhe = (err_txt[-600:] if err_txt else out_txt[-400:]) or f"exit {proc.returncode}"
        raise MutacaoErro(f"falha ao medir {chave} (exit {proc.returncode}): {detalhe}")
    return json.loads(arq_saida.read_text(encoding="utf-8"))


def medir_componente(
    componente: str,
    arvore: str | Path | None = None,
    *,
    leitor_componente: Callable[[str], dict[str, Any] | None] | None = None,
) -> MedidaComponente:
    """Executa a medida de eficácia por mutação sobre `componente` numa cópia temporária de `arvore`."""
    raiz_arvore = Path(arvore).resolve() if arvore is not None else _raiz_padrao()
    if not raiz_arvore.is_dir():
        raise MutacaoErro(f"árvore '{raiz_arvore}' não existe ou não é diretório")

    chave, raizes_comp = resolver_caminhos_componente(
        componente,
        raiz_arvore,
        leitor_componente=leitor_componente,
    )
    slug = chave.removeprefix("componente:")

    with tempfile.TemporaryDirectory(prefix=f"suite-mutacao-{slug}-") as tmp_str:
        tmp_raiz = Path(tmp_str)
        copia_arvore, copia_raizes = _preparar_copia_temporaria(raiz_arvore, raizes_comp, tmp_raiz)
        bruto = _rodar_subprocesso_worker(chave, copia_arvore, copia_raizes, tmp_raiz)

    mutantes = [Mutante(**m) for m in bruto["mutantes"]]
    casos = [ResultadoCaso(**c) for c in bruto["casos"]]
    gerados = len(mutantes)
    mortos = sum(1 for m in mutantes if m.morto)
    escore = (mortos / gerados) if gerados > 0 else 1.0

    return MedidaComponente(
        componente=chave,
        mutantes_gerados=gerados,
        mutantes_mortos=mortos,
        escore_amostra=escore,
        funcoes_mutadas=sorted({m.funcao for m in mutantes}),
        candidatos_a_sair=list(bruto["candidatos_a_sair"]),
        mutantes_sobreviventes=[m for m in mutantes if not m.morto],
        casos=casos,
        mutantes=mutantes,
    )


def formatar_relatorio(medida: MedidaComponente) -> str:
    pct = round(medida.escore_amostra * 100, 1)
    casos_com_mut = sum(1 for c in medida.casos if c.mutantes_exercitados > 0)
    resumo_amostra = (
        f"amostra: {medida.mutantes_mortos}/{medida.mutantes_gerados} mutantes mortos ({pct}%) · "
        f"{len(medida.mutantes_sobreviventes)} sobrevivente(s) · "
        f"{casos_com_mut} caso(s) exercitam código mutado"
    )
    linhas = [
        f"componente: {medida.componente}",
        resumo_amostra,
        f"funções mutadas: {', '.join(medida.funcoes_mutadas) if medida.funcoes_mutadas else 'nenhuma'}",
    ]
    if medida.candidatos_a_sair:
        linhas.append(f"candidatos a sair ({len(medida.candidatos_a_sair)}):")
        mapa_c = {c.caso: c for c in medida.casos}
        for nid in medida.candidatos_a_sair:
            info = mapa_c.get(nid)
            n_mut = info.mutantes_exercitados if info else 0
            linhas.append(f"  - {nid} (exercita {n_mut} mutante(s), matou 0)")
    else:
        linhas.append("candidatos a sair (0): nenhum")

    if medida.mutantes_sobreviventes:
        linhas.append(f"mutantes sobreviventes ({len(medida.mutantes_sobreviventes)}):")
        for m in medida.mutantes_sobreviventes:
            linhas.append(f"  - {m.arquivo}:{m.linha} ({m.funcao}) [{m.operador}] {m.antes} -> {m.depois}")
    else:
        linhas.append("mutantes sobreviventes (0): nenhum")

    return "\n".join(linhas) + "\n"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m suite medir")
    p.add_argument("componente", help="chave ou slug do componente (ex.: componente:diagrama)")
    p.add_argument("--arvore", default=None, help="caminho da árvore onde o componente será lido")
    p.add_argument("--json", action="store_true", dest="como_json", help="emite o resultado em JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == _NUM_ARGS_WORKER and argv[0] == "--worker":
        return _executar_worker(argv[1], argv[2])
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        medida = medir_componente(args.componente, arvore=args.arvore)
    except MutacaoErro as exc:
        sys.stderr.write(f"suite medir: {exc}\n")
        return 1
    if args.como_json:
        sys.stdout.write(json.dumps(medida.para_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(formatar_relatorio(medida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
