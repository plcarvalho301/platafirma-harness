"""Leitura do cabeçalho de vínculo (`componente:` e `verifica:`) e das marcas do caso (`exige` e `incidente`)."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_RE_COMENTARIO = re.compile(r"^\s*(?:#|//)\s*(.*?)\s*$")
_RE_CAMPO_CABECALHO = re.compile(r"^(componente|verifica)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_RE_MARCA_LINHA = re.compile(r"^\s*(?:#|//)\s*(exige|incidente)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_RE_CASO_SH = re.compile(r"^\s*(?:function\s+)?(test_[A-Za-z0-9_]+|[A-Za-z0-9_]+_test)\s*\(\s*\)")
_RE_CASO_JS = re.compile(r"""^\s*(?:test|it)\s*\(\s*['"`]([^'"`]+)['"`]""")

# O que cada classe de teste pode verificar, como a shape dela na Olaria declara em `verifica`.
# É a única cópia no código: admissão, consulta e dublês derivam daqui.
ALVOS_FRONTEIRA = ("interface", "contrato-da-porta")
ALVOS_REGRA = ("politica", "gabarito", "configuracao", "controle-de-seguranca")
DESTINOS_VERIFICA = frozenset(ALVOS_FRONTEIRA + ALVOS_REGRA)

# A grafia com hífen é a das chaves antigas e não ganha classe nova.
PREFIXOS_FRONTEIRA = tuple(f"{c}:" for c in ALVOS_FRONTEIRA) + ("interface-", "contrato-")
PREFIXOS_REGRA = tuple(f"{c}:" for c in ALVOS_REGRA) + ("politica-", "gabarito-", "configuracao-")


@dataclass(frozen=True)
class CasoTeste:
    nome: str
    linha: int
    exige: tuple[str, ...] = ()
    incidentes: tuple[int, ...] = ()


@dataclass(frozen=True)
class VinculoArquivo:
    caminho: Path
    componente: str | None
    componente_bruto: str | None
    verifica: str | None
    classe: str | None
    casos: tuple[CasoTeste, ...] = ()
    exige: tuple[str, ...] = ()
    incidentes: tuple[int, ...] = ()

    @property
    def slug_componente(self) -> str | None:
        return extrair_slug_componente(self.componente)

    @property
    def par(self) -> tuple[str, str | None] | None:
        if self.componente is None:
            return None
        return (self.componente, self.verifica)

    @property
    def chave_ficha(self) -> str | None:
        if self.componente is None or self.classe is None:
            return None
        slug_comp = self.slug_componente or self.componente.replace(":", "-")
        if self.verifica is None:
            return f"teste-de-comportamento:{slug_comp}"
        slug_alvo = re.sub(r"[^a-zA-Z0-9_-]+", "-", self.verifica).strip("-")
        return f"{self.classe}:{slug_comp}--{slug_alvo}"

    def como_ficha(self) -> dict[str, Any]:
        if self.componente is None or self.classe is None or self.chave_ficha is None:
            raise ValueError(f"arquivo sem vínculo completo para gerar ficha: {self.caminho}")
        ligacoes: dict[str, Any] = {"sobre": self.componente}
        if self.verifica is not None:
            ligacoes["verifica"] = self.verifica
        if self.exige:
            ligacoes["exige"] = list(self.exige)
        return {
            "classe": self.classe,
            "chave": self.chave_ficha,
            "ligacoes": ligacoes,
        }


def normalizar_componente(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpo = valor.strip()
    if not limpo:
        return None
    if ":" in limpo:
        return limpo
    return f"componente:{limpo}"


def extrair_slug_componente(componente: str | None) -> str | None:
    if componente is None:
        return None
    limpo = componente.strip()
    if limpo.startswith("componente:"):
        return limpo.removeprefix("componente:")
    return limpo


def deduzir_classe(componente: str | None, verifica: str | None) -> str | None:
    if componente is None:
        return None
    if verifica is None:
        return "teste-de-comportamento"
    alvo = verifica.strip().lower()
    if alvo.startswith(PREFIXOS_REGRA):
        return "teste-de-regra"
    if alvo.startswith(PREFIXOS_FRONTEIRA):
        return "teste-de-fronteira"
    return "teste-de-fronteira"


def ler_cabecalho(texto: str) -> tuple[str | None, str | None]:
    """Lê `componente:` e `verifica:` do bloco inicial de comentários do arquivo."""
    componente_bruto: str | None = None
    verifica: str | None = None
    iniciou_comentarios = False

    for i, linha_crua in enumerate(texto.splitlines()):
        linha = linha_crua.lstrip("\ufeff").strip()
        if i == 0 and linha.startswith("#!"):
            continue
        if not linha:
            if iniciou_comentarios:
                break
            continue
        m_com = _RE_COMENTARIO.match(linha)
        if not m_com:
            break
        iniciou_comentarios = True
        m_campo = _RE_CAMPO_CABECALHO.match(m_com.group(1).strip())
        if not m_campo:
            continue
        chave = m_campo.group(1).lower()
        valor = m_campo.group(2).strip()
        if chave == "componente" and componente_bruto is None:
            componente_bruto = valor
        elif chave == "verifica" and verifica is None:
            verifica = valor

    return componente_bruto, verifica


def _parse_incidente(val: Any) -> int | None:
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    if isinstance(val, str):
        limpo = val.strip().lstrip("#")
        if limpo.isdigit():
            return int(limpo)
    return None


def _nome_marca_pytest(func: ast.AST) -> str | None:
    if not isinstance(func, ast.Attribute) or func.attr not in ("exige", "incidente"):
        return None
    base = func.value
    if isinstance(base, ast.Name) and base.id == "mark":
        return func.attr
    if (
        isinstance(base, ast.Attribute)
        and base.attr == "mark"
        and isinstance(base.value, ast.Name)
        and base.value.id == "pytest"
    ):
        return func.attr
    return None


def _extrair_marcas_call(node: ast.AST) -> tuple[list[str], list[int]]:
    if not isinstance(node, ast.Call):
        return [], []
    nome_marca = _nome_marca_pytest(node.func)
    if nome_marca == "exige":
        exige = [
            arg.value.strip()
            for arg in node.args
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.strip()
        ]
        return exige, []
    if nome_marca == "incidente":
        incs = [
            inc
            for arg in node.args
            if isinstance(arg, ast.Constant)
            for inc in (_parse_incidente(arg.value),)
            if inc is not None
        ]
        return [], incs
    return [], []


def _extrair_marcas_expr(expr: ast.AST) -> tuple[list[str], list[int]]:
    if isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
        exige: list[str] = []
        inc: list[int] = []
        for elt in expr.elts:
            e, i = _extrair_marcas_call(elt)
            exige.extend(e)
            inc.extend(i)
        return exige, inc
    return _extrair_marcas_call(expr)


def _marcas_de_comentarios_acima(linhas: list[str], lineno_1based: int) -> tuple[list[str], list[int]]:
    exige: list[str] = []
    incidentes: list[int] = []
    idx = lineno_1based - 2
    while idx >= 0:
        linha = linhas[idx].strip()
        if linha.startswith("@"):
            idx -= 1
            continue
        m = _RE_MARCA_LINHA.match(linha)
        if not m:
            break
        tipo = m.group(1).lower()
        valor = m.group(2).strip()
        if tipo == "exige" and valor:
            exige.insert(0, valor)
        elif tipo == "incidente":
            inc = _parse_incidente(valor)
            if inc is not None:
                incidentes.insert(0, inc)
        idx -= 1
    return exige, incidentes


def _eh_funcao_teste(nome: str) -> bool:
    return nome.startswith("test_") or nome.endswith("_test")


def _marcas_pytestmark_em_corpo(corpo: list[ast.stmt]) -> tuple[list[str], list[int]]:
    exige: list[str] = []
    inc: list[int] = []
    for stmt in corpo:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets
        ):
            e, i = _extrair_marcas_expr(stmt.value)
            exige.extend(e)
            inc.extend(i)
    return exige, inc


def _construir_caso_funcao(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    linhas: list[str],
    prefixo: str,
    base_exige: list[str],
    base_inc: list[int],
) -> CasoTeste | None:
    if not _eh_funcao_teste(fn.name):
        return None
    ex_f = list(base_exige)
    in_f = list(base_inc)
    linha_topo = min([fn.lineno, *(d.lineno for d in fn.decorator_list)])
    c_ex, c_in = _marcas_de_comentarios_acima(linhas, linha_topo)
    ex_f.extend(c_ex)
    in_f.extend(c_in)
    for dec in fn.decorator_list:
        e, i = _extrair_marcas_call(dec)
        ex_f.extend(e)
        in_f.extend(i)
    nome_caso = f"{prefixo}{fn.name}" if prefixo else fn.name
    return CasoTeste(
        nome=nome_caso,
        linha=fn.lineno,
        exige=tuple(dict.fromkeys(ex_f)),
        incidentes=tuple(dict.fromkeys(in_f)),
    )


def _extrair_casos_classe(
    stmt: ast.ClassDef,
    linhas: list[str],
    mod_exige: list[str],
    mod_inc: list[int],
) -> list[CasoTeste]:
    cls_exige = list(mod_exige)
    cls_inc = list(mod_inc)
    for dec in stmt.decorator_list:
        e, i = _extrair_marcas_call(dec)
        cls_exige.extend(e)
        cls_inc.extend(i)
    e_pm, i_pm = _marcas_pytestmark_em_corpo(stmt.body)
    cls_exige.extend(e_pm)
    cls_inc.extend(i_pm)

    casos: list[CasoTeste] = []
    for sub in stmt.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            caso = _construir_caso_funcao(sub, linhas, f"{stmt.name}::", cls_exige, cls_inc)
            if caso is not None:
                casos.append(caso)
    return casos


def _extrair_casos_python(texto: str) -> tuple[list[CasoTeste], list[str], list[int]]:
    linhas = texto.splitlines()
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return _extrair_casos_texto(texto)

    mod_exige, mod_inc = _marcas_pytestmark_em_corpo(arvore.body)
    casos: list[CasoTeste] = []

    for stmt in arvore.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            caso = _construir_caso_funcao(stmt, linhas, "", mod_exige, mod_inc)
            if caso is not None:
                casos.append(caso)
        elif isinstance(stmt, ast.ClassDef) and stmt.name.startswith("Test"):
            casos.extend(_extrair_casos_classe(stmt, linhas, mod_exige, mod_inc))

    todos_exige = list(mod_exige)
    todos_inc = list(mod_inc)
    for c in casos:
        todos_exige.extend(c.exige)
        todos_inc.extend(c.incidentes)
    return casos, list(dict.fromkeys(todos_exige)), list(dict.fromkeys(todos_inc))


def _extrair_casos_texto(texto: str) -> tuple[list[CasoTeste], list[str], list[int]]:
    linhas = texto.splitlines()
    casos: list[CasoTeste] = []
    pendentes_exige: list[str] = []
    pendentes_inc: list[int] = []
    todos_exige: list[str] = []
    todos_inc: list[int] = []

    for idx, linha in enumerate(linhas, start=1):
        m_marca = _RE_MARCA_LINHA.match(linha)
        if m_marca:
            tipo = m_marca.group(1).lower()
            valor = m_marca.group(2).strip()
            if tipo == "exige" and valor:
                pendentes_exige.append(valor)
                todos_exige.append(valor)
            elif tipo == "incidente":
                inc = _parse_incidente(valor)
                if inc is not None:
                    pendentes_inc.append(inc)
                    todos_inc.append(inc)
            continue

        m_sh = _RE_CASO_SH.match(linha)
        m_js = _RE_CASO_JS.match(linha)
        nome_caso = m_sh.group(1) if m_sh else (m_js.group(1) if m_js else None)
        if nome_caso is not None:
            casos.append(
                CasoTeste(
                    nome=nome_caso,
                    linha=idx,
                    exige=tuple(dict.fromkeys(pendentes_exige)),
                    incidentes=tuple(dict.fromkeys(pendentes_inc)),
                )
            )
            pendentes_exige = []
            pendentes_inc = []
        elif linha.strip() and not _RE_COMENTARIO.match(linha):
            pendentes_exige = []
            pendentes_inc = []

    if not casos and (todos_exige or todos_inc):
        casos.append(
            CasoTeste(
                nome="<arquivo>",
                linha=1,
                exige=tuple(dict.fromkeys(todos_exige)),
                incidentes=tuple(dict.fromkeys(todos_inc)),
            )
        )

    return casos, list(dict.fromkeys(todos_exige)), list(dict.fromkeys(todos_inc))


def ler_vinculo(caminho: str | Path) -> VinculoArquivo:
    """Lê o cabeçalho de vínculo e as marcas (`exige` e `incidente`) de um arquivo de teste."""
    arq = Path(caminho)
    texto = arq.read_text(encoding="utf-8", errors="replace")
    comp_bruto, verifica = ler_cabecalho(texto)
    comp_norm = normalizar_componente(comp_bruto)
    classe = deduzir_classe(comp_norm, verifica)

    if arq.suffix == ".py":
        casos, exige, incidentes = _extrair_casos_python(texto)
    else:
        casos, exige, incidentes = _extrair_casos_texto(texto)

    return VinculoArquivo(
        caminho=arq,
        componente=comp_norm,
        componente_bruto=comp_bruto,
        verifica=verifica,
        classe=classe,
        casos=tuple(casos),
        exige=tuple(exige),
        incidentes=tuple(incidentes),
    )
