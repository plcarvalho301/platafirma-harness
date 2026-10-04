"""predicados_stack — detectores que leem a stack inteira de uma vez, nao um arquivo.

Um linter de arquivo unico nao ve o que so aparece no cruzamento: o cliente que desiste antes
do servidor que ele chama, duas camadas que repetem a mesma chamada, a lista copiada em dois
modulos, o modulo que usa a biblioteca que a stack inteira trocou. Aqui cada predicado monta
um indice sobre todos os arquivos Python do repositorio (e dos repositorios passados com
`--com`) e aponta no arquivo em escopo. A lista diz a que criterio cada um responde.
"""
from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .predicados import Achado, Contexto, e_sono, e_teste, externa, nome, sem_aninhadas

Funcao = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Def:
    rel: str
    caminho: Path
    no: Funcao


def funcoes(ctx: Contexto, arquivos: list[Path]) -> Iterator[Def]:
    for rel, p, arvore in ctx.arvores(arquivos):
        for n in ast.walk(arvore):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield Def(rel, p, n)


def chamados(fn: ast.AST) -> Iterator[tuple[str, ast.Call]]:
    """(nome curto, chamada) de toda chamada no corpo, na ordem do fonte, sem entrar em funcao
    aninhada."""
    todas = sorted((n for n in sem_aninhadas(fn) if isinstance(n, ast.Call)),
                   key=lambda n: (n.lineno, n.col_offset))
    for n in todas:
        yield nome(n.func).rsplit(".", 1)[-1], n


def _em_escopo(ctx: Contexto) -> set[Path]:
    return set(ctx.py)


# ------------------------------------------------------------------ prazo e repeticao entre servicos


def _numero(no: ast.AST | None) -> float | None:
    """Prazo literal: numero, ou o ultimo de uma tupla (conexao, leitura)."""
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)) and not isinstance(no.value, bool):
        return float(no.value)
    if isinstance(no, ast.Tuple) and no.elts:
        return _numero(no.elts[-1])
    return None


def prazo_da_chamada(c: ast.Call) -> float | None:
    for k in c.keywords:
        if k.arg == "timeout":
            return _numero(k.value)
    return None


_ROTA = re.compile(r"^/[\w/{}<>:.-]*$")
_METODOS_ROTA = {"get", "post", "put", "patch", "delete", "route", "api_route", "websocket"}


def rotas(ctx: Contexto) -> dict[str, Def]:
    """Caminho HTTP servido -> funcao que o trata, pelos decoradores `@app.post("/x")`."""
    achadas: dict[str, Def] = {}
    for d in funcoes(ctx, ctx.py_repo):
        for dec in d.no.decorator_list:
            if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr in _METODOS_ROTA and dec.args
                    and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str)
                    and _ROTA.match(dec.args[0].value)):
                achadas[_normal_rota(dec.args[0].value)] = d
    return achadas


def _normal_rota(caminho: str) -> str:
    return re.sub(r"\{[^}]*\}|<[^>]*>", "*", caminho.rstrip("/")) or "/"


def _texto_url(no: ast.AST) -> str:
    """O que se le de literal numa URL montada por f-string, + ou constante."""
    partes = [v.value for v in ast.walk(no) if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    return "*".join(partes)


def rota_chamada(c: ast.Call, servidas: dict[str, Def]) -> Def | None:
    if not (externa(c) and c.args):
        return None
    url = _texto_url(c.args[0])
    for caminho, d in servidas.items():
        literal = caminho.split("*")[0]
        if len(literal) > 1 and literal in url:
            return d
    return None


def _maior_prazo(fn: ast.AST, defs: dict[str, list[Def]], profundidade: int = 2) -> float | None:
    """Maior prazo literal de chamada externa na funcao e nas que ela chama, ate a profundidade."""
    prazos = [p for _, c in chamados(fn) if externa(c) and (p := prazo_da_chamada(c)) is not None]
    if profundidade:
        for curto, _ in chamados(fn):
            for d in defs.get(curto, []):
                if d.no is not fn and (p := _maior_prazo(d.no, defs, profundidade - 1)) is not None:
                    prazos.append(p)
    return max(prazos, default=None)


def _por_nome(ctx: Contexto) -> dict[str, list[Def]]:
    indice: dict[str, list[Def]] = defaultdict(list)
    for d in funcoes(ctx, ctx.py_repo):
        indice[d.no.name].append(d)
    return indice


def prazo_invertido(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Cliente que desiste antes do servidor que ele chama: o servidor segue trabalhando depois
    que ninguem espera mais a resposta (R2)."""
    servidas = rotas(ctx)
    if not servidas:
        return
    defs = _por_nome(ctx)
    for d in funcoes(ctx, ctx.py):
        for _, c in chamados(d.no):
            alvo = rota_chamada(c, servidas)
            cliente = prazo_da_chamada(c)
            if alvo is None or cliente is None:
                continue
            servidor = _maior_prazo(alvo.no, defs)
            if servidor is not None and servidor >= cliente:
                yield Achado(d.rel, c.lineno, f"o cliente desiste em {cliente:g} s e o servidor "
                                              f"({alvo.rel}:{alvo.no.lineno}) espera até {servidor:g} s")


def _repete(fn: ast.AST) -> bool:
    """A funcao tem laco que dorme ou trata excecao em volta de chamada externa."""
    for laco in (n for n in sem_aninhadas(fn) if isinstance(n, (ast.For, ast.While, ast.AsyncFor))):
        corpo = list(sem_aninhadas(laco))
        tenta = any(isinstance(n, ast.ExceptHandler) or (isinstance(n, ast.Call) and e_sono(n)) for n in corpo)
        if tenta and any(isinstance(n, ast.Call) and externa(n) for n in corpo):
            return True
    return False


def _repete_ate(d: Def, defs: dict[str, list[Def]], profundidade: int = 2) -> Def | None:
    """A funcao, ou alguma que ela chama ate a profundidade, que repete."""
    if _repete(d.no):
        return d
    if profundidade:
        for curto, _ in chamados(d.no):
            for x in defs.get(curto, []):
                if x.no is not d.no and (achada := _repete_ate(x, defs, profundidade - 1)):
                    return achada
    return None


def repeticao_em_camadas(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Funcao que repete chama outra que tambem repete, no mesmo processo ou pela rota HTTP do
    servidor: as tentativas multiplicam (R5)."""
    defs = _por_nome(ctx)
    servidas = rotas(ctx)
    for d in funcoes(ctx, ctx.py):
        if not _repete(d.no):
            continue
        for curto, c in chamados(d.no):
            alvos = [x for x in defs.get(curto, []) if x.no is not d.no]
            rota = rota_chamada(c, servidas)
            alvos += [rota] if rota else []
            for chamado in alvos:
                if (alvo := _repete_ate(chamado, defs)):
                    yield Achado(d.rel, c.lineno, f"repete e chama {alvo.no.name} "
                                                  f"({alvo.rel}:{alvo.no.lineno}), que também repete")
                    break


# ------------------------------------------------------------------ o que se copia entre modulos


MINIMO_ITENS = 4
SEMELHANCA_GEMEAS = 0.6


def _colecoes(ctx: Contexto) -> Iterator[tuple[str, int, str, frozenset[str]]]:
    """(arquivo, linha, nome, itens) de toda colecao literal de texto no topo de modulo."""
    for rel, _, arvore in ctx.arvores(ctx.py_repo):
        for st in arvore.body:
            alvo = st.targets[0] if isinstance(st, ast.Assign) and len(st.targets) == 1 else (
                st.target if isinstance(st, ast.AnnAssign) else None)
            valor = st.value if isinstance(st, (ast.Assign, ast.AnnAssign)) else None
            if not isinstance(alvo, ast.Name) or valor is None:
                continue
            fontes = valor.keys if isinstance(valor, ast.Dict) else getattr(valor, "elts", [])
            itens = frozenset(v.value for v in fontes if isinstance(v, ast.Constant) and isinstance(v.value, str))
            if len(itens) >= MINIMO_ITENS:
                yield rel, st.lineno, alvo.id, itens


def listas_gemeas(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Duas colecoes que quase coincidem em modulos diferentes: o mesmo conjunto mantido em dois
    lugares, que ja divergiu (D3)."""
    todas = list(_colecoes(ctx))
    escopo = {ctx.rel(p) for p in ctx.py}
    for rel, linha, nome_a, a in todas:
        if rel not in escopo:
            continue
        for rel_b, linha_b, nome_b, b in todas:
            if (rel_b, linha_b) == (rel, linha) or a == b:
                continue
            comuns = a & b
            if len(comuns) / len(a | b) >= SEMELHANCA_GEMEAS:
                difere = sorted(a ^ b)[:4]
                yield Achado(rel, linha, f"{nome_a} e {nome_b} ({rel_b}:{linha_b}) têm {len(comuns)} itens "
                                         f"em comum e divergem em {', '.join(difere)}")
                break


_ESCOLHAS = {
    "http": {"requests": "requests", "httpx": "httpx", "urllib.request": "urllib.request"},
    "caminho": {"os.path": "os.path", "pathlib": "pathlib"},
}
FATIA_DOMINANTE = 0.7
MINIMO_MODULOS = 5


def _usos(arvore: ast.Module) -> set[str]:
    usos: set[str] = set()
    for n in ast.walk(arvore):
        if isinstance(n, ast.Import):
            usos |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            usos.add(n.module)
        elif isinstance(n, ast.Attribute) and nome(n).startswith("os.path."):
            usos.add("os.path")
    return usos


def idioma_da_stack(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Modulo que usa a biblioteca que a stack trocou: requests onde a stack usa httpx, os.path
    onde usa pathlib (G4)."""
    por_arquivo = {rel: _usos(a) for rel, _, a in ctx.arvores(ctx.py_repo) if not e_teste(rel)}
    escopo = {ctx.rel(p) for p in ctx.py}
    for opcoes in _ESCOLHAS.values():
        contagem = Counter(op for usos in por_arquivo.values() for op in opcoes if op in usos)
        total = sum(contagem.values())
        if total < MINIMO_MODULOS:
            continue
        dominante, n = contagem.most_common(1)[0]
        if n / total < FATIA_DOMINANTE:
            continue
        for rel in escopo & set(por_arquivo):
            usos = por_arquivo[rel]
            minoria = [op for op in opcoes if op in usos and op != dominante]
            if minoria and dominante not in usos:
                yield Achado(rel, 1, f"usa {minoria[0]}; a stack usa {dominante} em {n} de {total} módulos")


MINIMO_CHAVES = 4
MINIMO_FUNCOES_FORMA = 3


def forma_repetida(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """O mesmo dicionario literal (mesmas chaves) montado em tres funcoes ou mais: um tipo sem
    nome (D11)."""
    sitios: dict[frozenset[str], list[tuple[str, int, str]]] = defaultdict(list)
    for d in funcoes(ctx, ctx.py_repo):
        for n in sem_aninhadas(d.no):
            if isinstance(n, ast.Dict) and len(n.keys) >= MINIMO_CHAVES and all(
                    isinstance(k, ast.Constant) and isinstance(k.value, str) for k in n.keys):
                sitios[frozenset(k.value for k in n.keys)].append((d.rel, n.lineno, d.no.name))
    escopo = {ctx.rel(p) for p in ctx.py}
    for chaves, onde in sitios.items():
        if len({f for _, _, f in onde}) < MINIMO_FUNCOES_FORMA:
            continue
        for rel, linha, _ in onde:
            if rel in escopo:
                yield Achado(rel, linha, f"dict com as chaves {', '.join(sorted(chaves)[:5])} "
                                         f"montado em {len(onde)} lugares")


# ------------------------------------------------------------------ fila e concorrencia


_UPDATE_ESTADO = re.compile(r"\bUPDATE\b.+\bSET\b.+\b(estado|status|situacao)\b", re.IGNORECASE | re.DOTALL)
_TRAVA_SQL = re.compile(r"SKIP\s+LOCKED|FOR\s+UPDATE|pg_advisory", re.IGNORECASE)


def reivindica_sem_trava(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Funcao que muda o estado de um item por SQL sem `FOR UPDATE SKIP LOCKED` nem trava
    consultiva: dois executores pegam o mesmo item (F2)."""
    for d in funcoes(ctx, ctx.py):
        textos = [(n.lineno, n.value) for n in sem_aninhadas(d.no)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if any(_TRAVA_SQL.search(t) for _, t in textos):
            continue
        for linha, t in textos:
            if _UPDATE_ESTADO.search(t):
                yield Achado(d.rel, linha, "UPDATE de estado sem FOR UPDATE SKIP LOCKED")
                break


def concorrencia_sem_teto(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Pool sem `max_workers`, thread criada por item num laco, ou gather sobre uma lista sem
    semaforo (F9)."""
    for d in funcoes(ctx, ctx.py):
        semaforo = any(nome(c.func).endswith("Semaphore") for _, c in chamados(d.no))
        for n in sem_aninhadas(d.no):
            if isinstance(n, ast.Call):
                nm = nome(n.func)
                if nm.endswith(("ThreadPoolExecutor", "ProcessPoolExecutor")) and not n.args and not n.keywords:
                    yield Achado(d.rel, n.lineno, f"{nm.rsplit('.', 1)[-1]} sem max_workers")
                elif nm.endswith("gather") and any(isinstance(a, ast.Starred) for a in n.args) and not semaforo:
                    yield Achado(d.rel, n.lineno, "gather sobre uma lista inteira, sem semáforo")
            elif isinstance(n, (ast.For, ast.AsyncFor)) and any(
                    isinstance(m, ast.Call) and nome(m.func).endswith("Thread") for m in sem_aninhadas(n)):
                yield Achado(d.rel, n.lineno, "uma thread por item do laço")


def corrotina_sem_await(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Chamada de `async def` do mesmo modulo como comando solto: a corrotina nunca roda (C2)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        assincronas = {n.name for n in ast.walk(arvore) if isinstance(n, ast.AsyncFunctionDef)}
        for n in ast.walk(arvore):
            if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                    and nome(n.value.func).rsplit(".", 1)[-1] in assincronas):
                yield Achado(rel, n.lineno, f"{nome(n.value.func)}() sem await")


def cancela_thread(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`wait_for` sobre `to_thread` ou `run_in_executor`: o prazo cancela a espera, a thread
    continua rodando (C5)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for n in ast.walk(arvore):
            if isinstance(n, ast.Call) and nome(n.func).endswith("wait_for") and any(
                    isinstance(m, ast.Call) and nome(m.func).endswith(("to_thread", "run_in_executor"))
                    for m in ast.walk(n)):
                yield Achado(rel, n.lineno, "wait_for sobre thread: a thread não é cancelada")


# ------------------------------------------------------------------ erro, saida, processo


_VAZIOS = (None, 0, False, "")


def _devolve_vazio(handler: ast.ExceptHandler) -> bool:
    corpo = [s for s in handler.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    if len(corpo) != 1 or not isinstance(corpo[0], ast.Return):
        return False
    valor = corpo[0].value
    return (valor is None or (isinstance(valor, ast.Constant) and valor.value in _VAZIOS)
            or (isinstance(valor, (ast.List, ast.Dict, ast.Tuple)) and not getattr(valor, "elts", None)
                and not getattr(valor, "keys", None)))


def erro_vira_vazio(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`except` cujo corpo so devolve None, 0, False ou vazio: o chamador nao sabe que falhou (R11)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for h in ast.walk(arvore):
            if isinstance(h, ast.ExceptHandler) and _devolve_vazio(h):
                yield Achado(rel, h.lineno, "a falha vira valor vazio, sem causa")


def _sucesso(st: ast.stmt) -> str | None:
    if isinstance(st, ast.Return) and isinstance(st.value, ast.Constant) and st.value.value is True:
        return "return True"
    if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) and nome(st.value.func) in ("sys.exit", "exit")
            and (not st.value.args or (isinstance(st.value.args[0], ast.Constant) and st.value.args[0].value == 0))):
        return "sys.exit(0)"
    return None


def verde_na_falha(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`except` que devolve sucesso: `return True` ou `sys.exit(0)` (R13, L6)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for h in ast.walk(arvore):
            if isinstance(h, ast.ExceptHandler):
                for st in h.body:
                    if (forma := _sucesso(st)):
                        yield Achado(rel, st.lineno, f"{forma} dentro de except")


def _usos_do_nome(fn: ast.AST, alvo: str) -> list[ast.AST]:
    return [n for n in ast.walk(fn) if isinstance(n, ast.Name) and n.id == alvo]


def filho_sem_espera(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """`Popen` guardado num nome que a funcao nunca espera, mata, devolve nem entrega (L3)."""
    for d in funcoes(ctx, ctx.py):
        for n in sem_aninhadas(d.no):
            if not (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.Call) and nome(n.value.func).endswith("Popen")):
                continue
            proc = n.targets[0].id
            if not _espera(d.no, proc) and not _entregue(d.no, proc):
                yield Achado(d.rel, n.lineno, f"{proc} = Popen(...) sem wait, communicate nem kill")


def _espera(fn: ast.AST, proc: str) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and isinstance(n.func.value, ast.Name) and n.func.value.id == proc
               and n.func.attr in ("wait", "communicate", "kill", "terminate", "poll")
               for n in ast.walk(fn))


def _entregue(fn: ast.AST, proc: str) -> bool:
    """O processo sai da funcao: devolvido, guardado em atributo ou passado adiante."""
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and n.value is not None and _usos_do_nome(n.value, proc):
            return True
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) for t in n.targets) and _usos_do_nome(n.value, proc):
            return True
        if isinstance(n, ast.Call) and any(_usos_do_nome(a, proc) for a in n.args):
            return True
    return False


_SERVE = ("serve_forever", "run_forever", "uvicorn.run")


def servico_sem_sigterm(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Modulo que serve para sempre (servidor, laco que dorme) e nao trata SIGTERM (L5)."""
    for rel, p, arvore in ctx.arvores(ctx.py):
        if e_teste(rel) or "SIGTERM" in ctx.texto(p):
            continue
        for n in ast.walk(arvore):
            serve = isinstance(n, ast.Call) and nome(n.func).endswith(_SERVE)
            laco = (isinstance(n, ast.While) and isinstance(n.test, ast.Constant) and n.test.value
                    and any(isinstance(m, ast.Call) and e_sono(m) for m in sem_aninhadas(n)))
            if serve or laco:
                yield Achado(rel, n.lineno, "serve sem tratar SIGTERM")
                break


def fd_herdado(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Subprocesso com `close_fds=False`: o filho herda todo descritor aberto (L8)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        for n in ast.walk(arvore):
            if isinstance(n, ast.Call) and any(
                    k.arg == "close_fds" and isinstance(k.value, ast.Constant) and k.value.value is False
                    for k in n.keywords):
                yield Achado(rel, n.lineno, "close_fds=False")


_NOME_DE_ESTADO = re.compile(r"estado|state|config|registro|manifest|cache|indice|index|json", re.IGNORECASE)


def escrita_no_lugar(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Arquivo de estado escrito no lugar, sem temporario e rename: queda no meio deixa o arquivo
    pela metade (L1)."""
    for d in funcoes(ctx, ctx.py):
        if any(curto in ("replace", "rename", "mkstemp", "NamedTemporaryFile") for curto, _ in chamados(d.no)):
            continue
        for curto, c in chamados(d.no):
            escreve = ((curto == "open" and len(c.args) > 1 and isinstance(c.args[1], ast.Constant)
                        and str(c.args[1].value).startswith("w"))
                       or curto in ("write_text", "write_bytes"))
            alvo = ast.unparse(c.args[0]) if curto == "open" and c.args else (
                ast.unparse(c.func.value) if isinstance(c.func, ast.Attribute) else "")
            if escreve and _NOME_DE_ESTADO.search(alvo):
                yield Achado(d.rel, c.lineno, f"{alvo} escrito no lugar, sem temporário e rename")


# ------------------------------------------------------------------ fronteira e resposta


_METODO_HTTP = {"get", "post", "put", "patch", "delete", "request"}
_CONFERE_STATUS = {"status_code", "raise_for_status", "ok", "is_success", "is_error", "status"}


def resposta_sem_status(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Resposta HTTP guardada e usada sem a funcao conferir o status: o erro do servidor vira
    dado (G2)."""
    for d in funcoes(ctx, ctx.py):
        atributos = {n.attr for n in ast.walk(d.no) if isinstance(n, ast.Attribute)}
        if atributos & _CONFERE_STATUS:
            continue
        for n in sem_aninhadas(d.no):
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and externa(n.value)
                    and nome(n.value.func).rsplit(".", 1)[-1] in _METODO_HTTP):
                yield Achado(d.rel, n.lineno, f"{nome(n.value.func)} sem conferir o status da resposta")


_ESTRUTURADA = {"git": ("--porcelain", "-z", "--format", "--pretty"), "docker": ("--format",),
                "ip": ("-j", "-json"), "lsblk": ("-J", "--json"), "systemctl": ("show", "--output"),
                "ruff": ("--output-format",), "gh": ("--json",), "kubectl": ("-o",)}
_RECORTE = {"split", "splitlines", "partition", "rsplit"}


def saida_recortada(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Saida de texto de um programa lida por recorte, quando ele tem saida estruturada (A4)."""
    for d in funcoes(ctx, ctx.py):
        recorta = any(curto in _RECORTE for curto, _ in chamados(d.no))
        if not recorta:
            continue
        for _, c in chamados(d.no):
            if not (c.args and isinstance(c.args[0], ast.List) and c.args[0].elts):
                continue
            argv = [e.value for e in c.args[0].elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            programa = Path(argv[0]).name if argv else ""
            if programa in _ESTRUTURADA and not any(a.startswith(_ESTRUTURADA[programa]) for a in argv):
                yield Achado(d.rel, c.lineno, f"saída de {programa} lida por recorte; ele tem "
                                              f"{' ou '.join(_ESTRUTURADA[programa])}")


_BANCO = re.compile(r"(cursor|execute|fetchall|fetchone|psycopg\.connect|sqlite3\.connect)$")


def tratador_no_banco(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Funcao de rota HTTP que fala direto com o banco (A2)."""
    escopo = set(ctx.py)
    for d in rotas(ctx).values():
        if d.caminho not in escopo:
            continue
        for _, c in chamados(d.no):
            if _BANCO.search(nome(c.func)):
                yield Achado(d.rel, c.lineno, f"a rota {d.no.name} chama {nome(c.func)} direto")
                break


# ------------------------------------------------------------------ desenho e teste


def repasse(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Funcao cujo corpo so repassa os mesmos argumentos a outra: camada sem abstracao (D8)."""
    for d in funcoes(ctx, ctx.py):
        if d.no.decorator_list or d.no.name.startswith("__"):
            continue
        corpo = [s for s in d.no.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        if len(corpo) != 1 or not isinstance(corpo[0], ast.Return) or not isinstance(corpo[0].value, ast.Call):
            continue
        params = [a.arg for a in d.no.args.args if a.arg not in ("self", "cls")]
        chamada = corpo[0].value
        passados = [a.id for a in chamada.args if isinstance(a, ast.Name)]
        passados += [k.value.id for k in chamada.keywords if isinstance(k.value, ast.Name)]
        if params and passados == params and len(chamada.args) + len(chamada.keywords) == len(params):
            yield Achado(d.rel, d.no.lineno, f"{d.no.name} só repassa para {nome(chamada.func)}")


PREPARACAO_MAXIMA = 15


def preparacao_longa(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Teste com mais de quinze comandos antes da primeira afirmacao (T6)."""
    for d in funcoes(ctx, ctx.py):
        if not (e_teste(d.rel) and d.no.name.startswith("test")):
            continue
        antes = 0
        for st in d.no.body:
            if isinstance(st, ast.Assert) or any(isinstance(n, ast.Assert) for n in ast.walk(st)):
                break
            antes += 1
        if antes > PREPARACAO_MAXIMA:
            yield Achado(d.rel, d.no.lineno, f"{antes} comandos antes da primeira afirmação")


def _pergunta_por_teste(n: ast.AST) -> str | None:
    if isinstance(n, ast.Constant) and n.value == "PYTEST_CURRENT_TEST":
        return "PYTEST_CURRENT_TEST"
    if isinstance(n, ast.Compare) and any(
            isinstance(v, ast.Constant) and v.value == "pytest" for v in [n.left, *n.comparators]) and any(
            nome(v) == "sys.modules" for v in [n.left, *n.comparators]):
        return "pytest em sys.modules"
    return None


def teste_em_producao(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Codigo de producao que pergunta se esta sob teste (T8)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        if e_teste(rel):
            continue
        for n in ast.walk(arvore):
            if (forma := _pergunta_por_teste(n)):
                yield Achado(rel, n.lineno, f"código de produção pergunta se está sob teste ({forma})")


_IDA_AO_BANCO = {"execute", "fetchone", "fetchall", "query"}


def ida_por_item(ctx: Contexto, item: dict) -> Iterator[Achado]:
    """Laco sobre itens com uma ida ao banco ou a rede por volta, onde um lote bastava (G5)."""
    for d in funcoes(ctx, ctx.py):
        for laco in (n for n in sem_aninhadas(d.no) if isinstance(n, (ast.For, ast.AsyncFor))):
            if isinstance(laco.iter, ast.Call) and nome(laco.iter.func) == "range":
                continue
            for curto, c in chamados(laco):
                http = externa(c) and curto in _METODO_HTTP
                if curto in _IDA_AO_BANCO or http:
                    yield Achado(d.rel, laco.lineno, f"uma chamada {nome(c.func)} por item do laço")
                    break


# ------------------------------------------------------------------ registro

PREDICADOS_STACK = {
    "PRAZO_INVERTIDO": (prazo_invertido, False),
    "REPETICAO_EM_CAMADAS": (repeticao_em_camadas, True),
    "LISTAS_GEMEAS": (listas_gemeas, True),
    "IDIOMA_DA_STACK": (idioma_da_stack, False),
    "FORMA_REPETIDA": (forma_repetida, True),
    "REIVINDICA_SEM_TRAVA": (reivindica_sem_trava, True),
    "CONCORRENCIA_SEM_TETO": (concorrencia_sem_teto, False),
    "CORROTINA_SEM_AWAIT": (corrotina_sem_await, False),
    "CANCELA_THREAD": (cancela_thread, False),
    "ERRO_VIRA_VAZIO": (erro_vira_vazio, True),
    "VERDE_NA_FALHA": (verde_na_falha, True),
    "FILHO_SEM_ESPERA": (filho_sem_espera, True),
    "SERVICO_SEM_SIGTERM": (servico_sem_sigterm, True),
    "FD_HERDADO": (fd_herdado, False),
    "ESCRITA_NO_LUGAR": (escrita_no_lugar, True),
    "RESPOSTA_SEM_STATUS": (resposta_sem_status, True),
    "SAIDA_RECORTADA": (saida_recortada, True),
    "TRATADOR_NO_BANCO": (tratador_no_banco, False),
    "REPASSE": (repasse, False),
    "PREPARACAO_LONGA": (preparacao_longa, False),
    "TESTE_EM_PRODUCAO": (teste_em_producao, False),
    "IDA_POR_ITEM": (ida_por_item, True),
}

# leem o repositorio inteiro (e os de --com), nao so o escopo
DO_REPOSITORIO_STACK = {"PRAZO_INVERTIDO", "REPETICAO_EM_CAMADAS", "LISTAS_GEMEAS", "IDIOMA_DA_STACK",
                        "FORMA_REPETIDA", "TRATADOR_NO_BANCO"}
