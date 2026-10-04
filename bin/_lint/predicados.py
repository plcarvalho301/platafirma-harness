"""predicados — detectores da casa para a lista `antipadroes-de-codigo`.

O ruff nao aceita regra de fora: todas as regras dele vem compiladas, e o projeto nao tem
sistema de plugin (docs.astral.sh/ruff/faq). O que a lista pede e nenhum analisador pronto
pega mora aqui: funcao sobre a arvore sintatica (`ast`) do Python, ou sobre o texto do shell
e da unit do systemd. A lista diz a que criterio cada predicado responde, pela coluna
detector (`predicado <NOME>`); este modulo nao conhece criterio nenhum.

Predicado marcado candidato aponta forma suspeita, nao defeito provado: o apontamento diz
«candidata», e a confirmacao e leitura. Um laco que chama subprocesso e espera dentro e o
formato do lote sem fila (#3194), mas tambem o de uma sonda de prontidao legitima.
"""
from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Achado:
    arquivo: str
    linha: int
    detalhe: str


@dataclass
class Contexto:
    """O que os predicados leem: os arquivos em escopo e, para os que olham o repositorio
    inteiro (duplicacao, ciclo de import), todos os arquivos Python dele."""
    raiz: Path
    py: List[Path]
    sh: List[Path]
    units: List[Path]
    py_repo: List[Path]
    _arvores: Dict[Path, Optional[ast.Module]] = field(default_factory=dict)
    _textos: Dict[Path, str] = field(default_factory=dict)

    def rel(self, p: Path) -> str:
        return str(p.relative_to(self.raiz))

    def texto(self, p: Path) -> str:
        if p not in self._textos:
            try:
                self._textos[p] = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._textos[p] = ""
        return self._textos[p]

    def arvore(self, p: Path) -> Optional[ast.Module]:
        """Arvore sintatica, ou None se o arquivo nao compila (o ruff ja acusa a sintaxe)."""
        if p not in self._arvores:
            try:
                self._arvores[p] = ast.parse(self.texto(p), filename=str(p))
            except (SyntaxError, ValueError):
                self._arvores[p] = None
        return self._arvores[p]

    def arvores(self, arquivos: List[Path]) -> Iterator[Tuple[str, Path, ast.Module]]:
        for p in arquivos:
            arvore = self.arvore(p)
            if arvore is not None:
                yield self.rel(p), p, arvore


def e_teste(rel: str) -> bool:
    partes = Path(rel).parts
    nome_arq = partes[-1]
    return (nome_arq.startswith("test_") or nome_arq == "conftest.py"
            or any(x in ("tests", "testes", "test") for x in partes[:-1]))


# ------------------------------------------------------------------ apoio sobre a arvore


def nome(no: ast.AST) -> str:
    """Nome pontuado de um Name, Attribute ou Call: `subprocess.run`, `self._lock`."""
    if isinstance(no, ast.Name):
        return no.id
    if isinstance(no, ast.Attribute):
        base = nome(no.value)
        return f"{base}.{no.attr}" if base else no.attr
    if isinstance(no, ast.Call):
        return nome(no.func)
    return ""


_ESCOPO = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def sem_aninhadas(no: ast.AST) -> Iterator[ast.AST]:
    """Descendentes de `no` sem entrar em funcao, lambda ou classe definidas dentro dele."""
    pilha = list(ast.iter_child_nodes(no))
    while pilha:
        filho = pilha.pop()
        yield filho
        if not isinstance(filho, _ESCOPO):
            pilha.extend(ast.iter_child_nodes(filho))


def _chamadas(no: ast.AST) -> List[ast.Call]:
    return [n for n in sem_aninhadas(no) if isinstance(n, ast.Call)]


_EXTERNA = re.compile(r"^(subprocess\.(run|call|check_call|check_output|Popen)|requests\.\w+|"
                      r"httpx\.\w+|urllib\.request\.urlopen|urlopen|socket\.\w+)$")
_METODO_REDE = {"get", "post", "put", "patch", "delete", "request", "send", "stream"}
_RECEPTOR_REDE = re.compile(r"client|cliente|sess|http|api", re.I)


def externa(chamada: ast.Call) -> bool:
    """Chamada que sai do processo: subprocesso, HTTP, socket."""
    n = nome(chamada.func)
    if _EXTERNA.match(n):
        return True
    partes = n.split(".")
    if partes[-1] == "communicate":
        return True
    receptor = partes[-2] if len(partes) > 1 else ""
    return partes[-1] in _METODO_REDE and bool(_RECEPTOR_REDE.search(receptor))


def e_sono(chamada: ast.Call) -> bool:
    return nome(chamada.func) in ("time.sleep", "asyncio.sleep", "sleep")


def _lacos(arvore: ast.Module):
    return (n for n in ast.walk(arvore) if isinstance(n, (ast.For, ast.AsyncFor, ast.While)))


# ------------------------------------------------------------------ falha, tempo, repeticao


_SEM_PRAZO = {"subprocess.run", "subprocess.call", "subprocess.check_call",
              "subprocess.check_output", "urllib.request.urlopen", "urlopen",
              "socket.create_connection"}


def prazo_externo(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Chamada externa sem `timeout=`. Argumento por `**kw` nao se julga."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for n in ast.walk(arvore):
            if not isinstance(n, ast.Call):
                continue
            nm = nome(n.func)
            if nm not in _SEM_PRAZO and nm.rsplit(".", 1)[-1] != "communicate":
                continue
            chaves = {k.arg for k in n.keywords}
            if None in chaves or "timeout" in chaves:
                continue
            yield Achado(rel, n.lineno, f"{nm} sem timeout")


def recuo_fixo(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Laco com `except` e espera de tempo constante, sem nada sorteado: repeticao em passo fixo."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for laco in _lacos(arvore):
            corpo = list(sem_aninhadas(laco))
            if not any(isinstance(n, ast.ExceptHandler) for n in corpo):
                continue
            chamadas = [n for n in corpo if isinstance(n, ast.Call)]
            if any(nome(c.func).startswith(("random.", "secrets.")) or "jitter" in nome(c.func).lower()
                   for c in chamadas):
                continue
            for c in chamadas:
                if (e_sono(c) and c.args and isinstance(c.args[0], ast.Constant)
                        and isinstance(c.args[0].value, (int, float))):
                    yield Achado(rel, c.lineno, f"espera fixa de {c.args[0].value} s num laço que repete na falha")


def repete_sem_teto(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`while True` que dorme e, na falha, nunca sai: sem raise, e o except nao tem break nem return."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for laco in _lacos(arvore):
            if not (isinstance(laco, ast.While) and isinstance(laco.test, ast.Constant) and laco.test.value):
                continue
            corpo = list(sem_aninhadas(laco))
            tratadores = [n for n in corpo if isinstance(n, ast.ExceptHandler)]
            if not tratadores or not any(isinstance(n, ast.Call) and e_sono(n) for n in corpo):
                continue
            if any(isinstance(n, ast.Raise) for n in corpo):
                continue
            if any(isinstance(m, (ast.Break, ast.Return)) for t in tratadores for m in sem_aninhadas(t)):
                continue
            yield Achado(rel, laco.lineno, "while True que repete na falha sem teto de tentativas")


def lote_sem_fila(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`for` sobre itens que chama o mundo de fora e espera ou repete dentro: o formato do #3194."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for laco in _lacos(arvore):
            # `for _ in range(n)` conta tentativas, nao percorre itens: e a repeticao, nao o lote
            if isinstance(laco, ast.While) or (isinstance(laco.iter, ast.Call) and nome(laco.iter.func) == "range"):
                continue
            corpo = list(sem_aninhadas(laco))
            de_fora = [n for n in corpo if isinstance(n, ast.Call) and externa(n)]
            if not de_fora:
                continue
            espera = any(isinstance(n, ast.Call) and e_sono(n) for n in corpo)
            repete = any(isinstance(n, (ast.While, ast.For, ast.AsyncFor)) and n is not laco
                         and any(isinstance(m, ast.ExceptHandler) for m in sem_aninhadas(n))
                         for n in corpo)
            if espera or repete:
                yield Achado(rel, laco.lineno, f"laço sobre itens chama {nome(de_fora[0].func)} "
                                               f"e {'espera' if espera else 'repete'} dentro dele")


def _escreve_erro(st: ast.stmt) -> bool:
    if not (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)):
        return False
    c = st.value
    nm = nome(c.func)
    ultimo = nm.rsplit(".", 1)[-1]
    if nm == "print" and any(k.arg == "file" for k in c.keywords):
        return True
    if nm == "sys.stderr.write" or ultimo in ("error", "exception", "critical", "warning", "fatal"):
        return True
    return bool(re.search(r"morre|die|erro|falha|uso|usage|aviso|fail", ultimo, re.I))


def _saida_com_erro(st: ast.stmt) -> bool:
    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
        c = st.value
        alvo = nome(c.func) in ("sys.exit", "exit")
    elif isinstance(st, ast.Raise) and isinstance(st.exc, ast.Call):
        c = st.exc
        alvo = nome(c.func) == "SystemExit"
    else:
        return False
    return (alvo and bool(c.args) and isinstance(c.args[0], ast.Constant)
            and isinstance(c.args[0].value, int) and c.args[0].value != 0)


def erro_sem_causa(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`sys.exit(n)` com n diferente de zero sem escrever a causa no comando anterior."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for pai in ast.walk(arvore):
            for campo in ("body", "orelse", "finalbody"):
                bloco = getattr(pai, campo, None)
                if not isinstance(bloco, list):
                    continue
                for i, st in enumerate(bloco):
                    if _saida_com_erro(st) and (i == 0 or not _escreve_erro(bloco[i - 1])):
                        yield Achado(rel, st.lineno, "saída com erro sem a causa escrita antes")


# ------------------------------------------------------------------ Python e concorrencia


def popen_wait(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`Popen` com stdout ou stderr em PIPE esperado por `wait()`: o pipe enche e trava."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        escopos = [arvore] + [n for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for escopo in escopos:
            nos = list(sem_aninhadas(escopo))
            com_pipe: Set[str] = set()
            for n in nos:
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                    alvo, valor = n.targets[0].id, n.value
                elif isinstance(n, ast.withitem) and isinstance(n.optional_vars, ast.Name):
                    alvo, valor = n.optional_vars.id, n.context_expr
                else:
                    continue
                if (isinstance(valor, ast.Call) and nome(valor.func).endswith("Popen")
                        and any(k.arg in ("stdout", "stderr") and nome(k.value).endswith("PIPE")
                                for k in valor.keywords)):
                    com_pipe.add(alvo)
            for n in nos:
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "wait"
                        and isinstance(n.func.value, ast.Name) and n.func.value.id in com_pipe):
                    yield Achado(rel, n.lineno, f"{n.func.value.id}.wait() com saída em PIPE")


def _le_ambiente(no: ast.AST) -> bool:
    for n in ast.walk(no):
        if isinstance(n, ast.Attribute) and nome(n) == "os.environ":
            return True
        if isinstance(n, ast.Call) and nome(n.func) in ("os.getenv", "getenv", "environ.get"):
            return True
        if isinstance(n, ast.Name) and n.id == "environ":
            return True
    return False


def ambiente_na_importacao(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Constante de modulo que le o ambiente: vale o ambiente da importacao, nao o da chamada."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for st in arvore.body:
            if isinstance(st, (ast.Assign, ast.AnnAssign)) and st.value is not None and _le_ambiente(st.value):
                yield Achado(rel, st.lineno, "variável de ambiente lida na importação do módulo")


def trava_com_io(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Chamada externa, espera ou `open` dentro de `with <trava>:`."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for w in ast.walk(arvore):
            if not isinstance(w, (ast.With, ast.AsyncWith)):
                continue
            if not any(re.search(r"lock|trava|mutex", nome(i.context_expr), re.I) for i in w.items):
                continue
            for c in _chamadas(w):
                if externa(c) or e_sono(c) or nome(c.func) == "open":
                    yield Achado(rel, c.lineno, f"{nome(c.func)} com a trava segurada")
                    break


DEGRAUS_ESCADA = 3


def escada_isinstance(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Cadeia if/elif com tres ou mais `isinstance` sobre a mesma expressao."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        vistos: Set[int] = set()
        for n in ast.walk(arvore):
            if not isinstance(n, ast.If) or id(n) in vistos:
                continue
            testes, atual = [], n
            while isinstance(atual, ast.If):
                vistos.add(id(atual))
                testes.append(atual.test)
                atual = atual.orelse[0] if len(atual.orelse) == 1 and isinstance(atual.orelse[0], ast.If) else None
            alvos = [ast.unparse(t.args[0]) for t in testes
                     if isinstance(t, ast.Call) and nome(t.func) == "isinstance" and t.args]
            mais = Counter(alvos).most_common(1)
            if mais and mais[0][1] >= DEGRAUS_ESCADA:
                yield Achado(rel, n.lineno, f"escada de {mais[0][1]} isinstance sobre {mais[0][0]}")


# ------------------------------------------------------------------ Linux


_EXISTE_OS = {"os.path.exists", "os.path.isfile", "os.path.isdir", "os.access"}
_USA_OS = {"open", "os.remove", "os.unlink", "os.rename", "os.replace", "shutil.move"}
_USA_PATH = {"open", "unlink", "read_text", "read_bytes", "write_text", "write_bytes", "rename", "replace"}


def _conferidos(teste: ast.expr) -> Set[str]:
    """Expressoes cuja existencia o teste do `if` confere."""
    alvos: Set[str] = set()
    for c in (n for n in ast.walk(teste) if isinstance(n, ast.Call)):
        if nome(c.func) in _EXISTE_OS and c.args:
            alvos.add(ast.unparse(c.args[0]))
        elif isinstance(c.func, ast.Attribute) and c.func.attr in ("exists", "is_file"):
            alvos.add(ast.unparse(c.func.value))
    return alvos


def _usa(c: ast.Call, alvos: Set[str]) -> bool:
    if nome(c.func) in _USA_OS and c.args:
        return ast.unparse(c.args[0]) in alvos
    return (isinstance(c.func, ast.Attribute) and c.func.attr in _USA_PATH
            and ast.unparse(c.func.value) in alvos)


def confere_e_usa(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`if <existe>(x):` seguido de usar x no corpo: entre conferir e usar, o arquivo muda."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for se in (n for n in ast.walk(arvore) if isinstance(n, ast.If)):
            alvos = _conferidos(se.test)
            if not alvos:
                continue
            for st in se.body:
                for c in (n for n in ast.walk(st) if isinstance(n, ast.Call)):
                    if _usa(c, alvos):
                        yield Achado(rel, c.lineno, f"{nome(c.func)} depois de conferir que existe")


def unit_segundo_plano(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Unit do systemd com `Type=forking` ou `PIDFile=`: servico que se poe em segundo plano."""
    for p in ctx.units:
        for i, linha in enumerate(ctx.texto(p).splitlines(), 1):
            s = linha.strip()
            if re.match(r"Type\s*=\s*forking\b", s) or s.startswith("PIDFile="):
                yield Achado(ctx.rel(p), i, s)


# ------------------------------------------------------------------ desenho e fronteira


def _raizes_import(p: Path, raiz: Path) -> List[Path]:
    d, topo = p.parent, None
    while (d / "__init__.py").exists() and d != raiz:
        topo, d = d, d.parent
    return ([topo.parent] if topo else []) + [p.parent]


def _modulo(partes: List[str], bases: List[Path]) -> Optional[Path]:
    for base in bases:
        alvo = base.joinpath(*partes) if partes else base
        if partes and alvo.with_name(alvo.name + ".py").is_file():
            return alvo.with_name(alvo.name + ".py")
        if (alvo / "__init__.py").is_file():
            return alvo / "__init__.py"
    return None


def _importados(st: ast.stmt, p: Path, raiz: Path) -> List[Path]:
    bases = _raizes_import(p, raiz)
    achados: List[Path] = []
    if isinstance(st, ast.Import):
        for a in st.names:
            alvo = _modulo(a.name.split("."), bases)
            if alvo:
                achados.append(alvo)
    elif isinstance(st, ast.ImportFrom):
        partes = st.module.split(".") if st.module else []
        if st.level:
            base = p.parent
            for _ in range(st.level - 1):
                base = base.parent
            bases = [base]
        for a in st.names:
            sub = _modulo(partes + [a.name], bases)
            if sub:
                achados.append(sub)
            else:
                pacote = _modulo(partes, bases)
                if pacote:
                    achados.append(pacote)
    return achados


Arestas = Dict[Path, List[Tuple[Path, int]]]


def _grafo_de_imports(ctx: Contexto) -> Arestas:
    no_repo = set(ctx.py_repo)
    arestas: Arestas = defaultdict(list)
    for _, p, arvore in ctx.arvores(ctx.py_repo):
        for st in arvore.body:
            for alvo in _importados(st, p, ctx.raiz):
                if alvo in no_repo and alvo != p:
                    arestas[p].append((alvo, st.lineno))
    return arestas


def import_ciclico(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Ciclo entre modulos pelos imports de topo (import local dentro de funcao fica fora)."""
    arestas = _grafo_de_imports(ctx)
    escopo = set(ctx.py)
    for comp in _ciclos(arestas):
        for a in comp & escopo:
            for b, linha in arestas[a]:
                if b in comp:
                    yield Achado(ctx.rel(a), linha, f"importa {ctx.rel(b)}, e o ciclo volta a este "
                                                    f"módulo ({len(comp)} módulos no ciclo)")


def _ciclos(arestas: Arestas) -> List[Set[Path]]:  # noqa: C901 — Tarjan iterativo; partido, nao se confere contra a referencia
    """Componentes fortemente conexas com mais de um modulo (Tarjan, iterativo)."""
    indice: Dict[Path, int] = {}
    baixo: Dict[Path, int] = {}
    pilha: List[Path] = []
    na_pilha: Set[Path] = set()
    componentes: List[Set[Path]] = []
    contador = 0
    for inicio in list(arestas):
        if inicio in indice:
            continue
        trabalho = [(inicio, iter(arestas[inicio]))]
        indice[inicio] = baixo[inicio] = contador
        contador += 1
        pilha.append(inicio)
        na_pilha.add(inicio)
        while trabalho:
            v, filhos = trabalho[-1]
            avancou = False
            for w, _ in filhos:
                if w not in indice:
                    indice[w] = baixo[w] = contador
                    contador += 1
                    pilha.append(w)
                    na_pilha.add(w)
                    trabalho.append((w, iter(arestas.get(w, []))))
                    avancou = True
                    break
                if w in na_pilha:
                    baixo[v] = min(baixo[v], indice[w])
            if avancou:
                continue
            trabalho.pop()
            if trabalho:
                baixo[trabalho[-1][0]] = min(baixo[trabalho[-1][0]], baixo[v])
            if baixo[v] == indice[v]:
                comp: Set[Path] = set()
                while True:
                    w = pilha.pop()
                    na_pilha.discard(w)
                    comp.add(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    componentes.append(comp)
    return componentes


JANELA_DUPLICACAO = 8
_LINHA_VAZIA = {")", "]", "}", "),", "],", "},", "pass", '"""', "'''", "else:", "try:", "finally:"}


def _normalizadas(texto: str) -> List[Tuple[int, str]]:
    saida = []
    for i, linha in enumerate(texto.splitlines(), 1):
        s = linha.strip()
        if not s or s.startswith("#") or s.startswith(("import ", "from ")) or s in _LINHA_VAZIA:
            continue
        saida.append((i, s))
    return saida


def duplicacao(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Bloco de oito linhas significativas iguais em outro lugar do repositorio."""
    j = JANELA_DUPLICACAO
    indice: Dict[int, List[Tuple[str, int, int]]] = defaultdict(list)
    normais: Dict[Path, List[Tuple[int, str]]] = {}
    for p in ctx.py_repo:
        norm = _normalizadas(ctx.texto(p))
        normais[p] = norm
        rel = ctx.rel(p)
        for k in range(len(norm) - j + 1):
            indice[hash(tuple(s for _, s in norm[k:k + j]))].append((rel, norm[k][0], k))

    for p in ctx.py:
        rel = ctx.rel(p)
        norm = normais.get(p) or _normalizadas(ctx.texto(p))
        bloco: Optional[Tuple[int, int, Tuple[str, int]]] = None
        for k in range(len(norm) - j + 1):
            outros = [(r, ln) for r, ln, ix in indice[hash(tuple(s for _, s in norm[k:k + j]))]
                      if r != rel or abs(ix - k) >= j]
            if outros and bloco and bloco[1] == k - 1:
                bloco = (bloco[0], k, bloco[2])
                continue
            if bloco:
                yield _bloco(rel, norm, bloco, j)
                bloco = None
            if outros:
                bloco = (k, k, outros[0])
        if bloco:
            yield _bloco(rel, norm, bloco, j)


def _bloco(rel: str, norm: List[Tuple[int, str]], bloco: Tuple[int, int, Tuple[str, int]], j: int) -> Achado:
    inicio, fim, (outro, linha_outro) = bloco
    linhas = norm[fim + j - 1][0] - norm[inicio][0] + 1
    return Achado(rel, norm[inicio][0], f"bloco de {linhas} linhas igual a {outro}:{linha_outro}")


# ------------------------------------------------------------------ teste


def _testes(ctx: Contexto):
    return ((rel, p, a) for rel, p, a in ctx.arvores(ctx.py) if e_teste(rel))


def teste_condicional(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`if` dentro de funcao de teste. O `if` que so pula o teste (skip, xfail) nao conta."""
    for rel, _, arvore in _testes(ctx):
        for fn in ast.walk(arvore):
            if not (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name.startswith("test")):
                continue
            for n in sem_aninhadas(fn):
                if not isinstance(n, ast.If):
                    continue
                corpo = n.body
                if (len(corpo) == 1 and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Call)
                        and nome(corpo[0].value.func).rsplit(".", 1)[-1] in ("skip", "xfail", "importorskip", "fail")):
                    continue
                yield Achado(rel, n.lineno, f"if dentro de {fn.name}")


_ERRATICO = re.compile(r"^(time\.(time|sleep|monotonic)|(datetime\.)?datetime\.(now|today|utcnow)|"
                       r"random\.\w+|requests\.\w+|httpx\.\w+|socket\.\w+|urllib\.request\.urlopen)$")


def teste_erratico(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Relogio, sorteio ou rede dentro de teste."""
    for rel, _, arvore in _testes(ctx):
        for n in ast.walk(arvore):
            if isinstance(n, ast.Call) and _ERRATICO.match(nome(n.func)):
                yield Achado(rel, n.lineno, f"{nome(n.func)} em teste")


_ESTADO_REAL = ("/srv/platafirma", "/opt/platafirma", "/home/claudinho")


def teste_estado_real(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Caminho do host de producao escrito no teste."""
    for rel, _, arvore in _testes(ctx):
        for n in ast.walk(arvore):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith(_ESTADO_REAL):
                yield Achado(rel, n.lineno, f"caminho real em teste: {n.value[:60]}")


# ------------------------------------------------------------------ shell


def eval_shell(ctx: Contexto, item: dict) -> Iterator[Achado]:
    for p in ctx.sh:
        for i, linha in enumerate(ctx.texto(p).splitlines(), 1):
            if not linha.strip().startswith("#") and re.search(r"(^|[;&|(]\s*|\s)eval\s", linha):
                yield Achado(ctx.rel(p), i, "eval")


def bash_set_e(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Funcao que termina num `[ ... ] && ...` sob `set -e`: o status falso vaza como erro."""
    for p in ctx.sh:
        nome_fn, ultima, dentro = "", "", False
        for i, linha in enumerate(ctx.texto(p).splitlines(), 1):
            if re.match(r"^[a-zA-Z_0-9]+ *\(\) *\{", linha):
                dentro, nome_fn, ultima = True, linha.split("(", 1)[0].strip(), ""
            elif dentro and linha.strip() == "}":
                if re.match(r"^[ \t]*\[.*\][ \t]*&&", ultima) and "||" not in ultima:
                    yield Achado(ctx.rel(p), i - 1, f"{nome_fn} termina com condicional sob set -e sem return/exit")
                dentro = False
            elif dentro and linha.strip() and not linha.strip().startswith("#"):
                ultima = linha


_RE_PISO = re.compile(r"mais de (\d+) linhas")


def linhas_shell(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Script de shell maior que o piso que o texto do criterio da (o padrao, 100)."""
    m = _RE_PISO.search(item.get("o_que_fere", ""))
    piso = int(m.group(1)) if m else 100
    for p in ctx.sh:
        n = len(ctx.texto(p).splitlines())
        if n > piso:
            yield Achado(ctx.rel(p), 1, f"{n} linhas, piso {piso}")


# ------------------------------------------------------------------ registro

# nome na lista -> (funcao, candidata). Candidata: forma suspeita, a leitura confirma.
PREDICADOS: Dict[str, Tuple[Callable[[Contexto, dict], Iterator[Achado]], bool]] = {
    "PRAZO_EXTERNO": (prazo_externo, False),
    "RECUO_FIXO": (recuo_fixo, True),
    "REPETE_SEM_TETO": (repete_sem_teto, True),
    "LOTE_SEM_FILA": (lote_sem_fila, True),
    "ERRO_SEM_CAUSA": (erro_sem_causa, True),
    "POPEN_WAIT": (popen_wait, False),
    "AMBIENTE_NA_IMPORTACAO": (ambiente_na_importacao, False),
    "TRAVA_COM_IO": (trava_com_io, True),
    "ESCADA_ISINSTANCE": (escada_isinstance, False),
    "CONFERE_E_USA": (confere_e_usa, True),
    "UNIT_SEGUNDO_PLANO": (unit_segundo_plano, False),
    "IMPORT_CICLICO": (import_ciclico, False),
    "DUPLICACAO": (duplicacao, False),
    "TESTE_CONDICIONAL": (teste_condicional, False),
    "TESTE_ERRATICO": (teste_erratico, True),
    "TESTE_ESTADO_REAL": (teste_estado_real, True),
    "EVAL_SHELL": (eval_shell, False),
    "BASH_SET_E": (bash_set_e, False),
    "LINHAS_SHELL": (linhas_shell, False),
}

# predicados que leem o repositorio inteiro, nao so o escopo
DO_REPOSITORIO = {"IMPORT_CICLICO", "DUPLICACAO"}
