"""leitura — criterios que pedem julgamento: a maquina junta a evidencia, o modelo local julga.

Para cada criterio `leitura <NOME>` da lista, um gerador varre a stack (o indice que os
predicados ja montam) e produz perguntas: um trecho de evidencia, com as linhas numeradas
como no arquivo, e uma questao fechada. O modelo local responde JSON {fere, porque, itens}.
O texto nao sai do perimetro (spec_lint §1: o modelo das classes de leitura e local).

O cruzamento e a forca: a mesma classe montada com valores diferentes em dez modulos so
aparece quando se le a stack inteira de uma vez; o modelo so decide se a divergencia e
decisao espalhada ou razao local. O veredito fica em cache pela evidencia: arquivo que nao
mudou nao volta ao modelo.

Modos de falha: modelo fora do ar para a leitura inteira e vira aviso (nao trava o resto);
resposta que nao e JSON valido conta como nao julgada, nunca como «nao fere»; teto de
perguntas por rodada, e o que passou do teto sai em aviso.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .predicados import Contexto, e_teste, externa, nome, sem_aninhadas
from .predicados_stack import Def, chamados, funcoes, rotas

SISTEMA = ("Você revisa código Python contra um critério de antipadrão. Julgue só pelo que a "
           "evidência mostra; na dúvida, fere=false. 'porque' em português, até 30 palavras, "
           "citando o número da linha. 'itens' só quando a questão pede números.")
ESQUEMA = {"type": "object",
           "properties": {"fere": {"type": "boolean"}, "porque": {"type": "string"},
                          "itens": {"type": "array", "items": {"type": "integer"}}},
           "required": ["fere", "porque"]}
LINHAS_EVIDENCIA = 60
TETO_SAIDA = 200
JANELA = 8192
PRAZO_CHAMADA_S = 180


@dataclass(frozen=True)
class Pergunta:
    arquivo: str
    linha: int
    questao: str
    evidencia: str
    linhas_itens: tuple[int, ...] = ()   # quando a questao pede itens: o item i aponta esta linha


@dataclass
class Julgamento:
    fere: bool
    porque: str
    itens: list[int] = field(default_factory=list)


class ModeloIndisponivel(Exception):
    pass


# ------------------------------------------------------------------ o modelo


def _modelo() -> str:
    return os.environ.get("PF_LINT_MODELO", "qwen3.5:9b")


def _url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def _pasta_cache() -> Path:
    return Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa")) / "var" / "cache" / "lint-leitura"


def _chave(p: Pergunta) -> str:
    return hashlib.sha256(json.dumps([_modelo(), SISTEMA, p.questao, p.evidencia]).encode()).hexdigest()


def _do_cache(chave: str) -> Julgamento | None:
    try:
        dado = json.loads((_pasta_cache() / f"{chave}.json").read_text())
        return Julgamento(bool(dado["fere"]), str(dado["porque"]), list(dado.get("itens") or []))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _ao_cache(chave: str, j: Julgamento) -> None:
    pasta = _pasta_cache()
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump({"fere": j.fere, "porque": j.porque, "itens": j.itens}, f)
        os.replace(tmp, pasta / f"{chave}.json")
    except OSError:
        pass  # cache e economia, nao verdade: sem ele, a proxima rodada pergunta de novo


def perguntar(p: Pergunta) -> Julgamento | None:
    """Veredito do modelo para a pergunta, do cache se a evidencia nao mudou. None quando a
    resposta nao se le; ModeloIndisponivel quando o modelo nao responde."""
    chave = _chave(p)
    if (j := _do_cache(chave)) is not None:
        return j
    pedido = {"model": _modelo(), "stream": False, "think": False, "format": ESQUEMA, "keep_alive": "10m",
              "messages": [{"role": "system", "content": SISTEMA},
                           {"role": "user", "content": f"{p.questao}\n\nEvidência:\n{p.evidencia}"}],
              "options": {"temperature": 0, "num_predict": TETO_SAIDA, "num_ctx": JANELA}}
    req = urllib.request.Request(f"{_url()}/api/chat", data=json.dumps(pedido).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=PRAZO_CHAMADA_S) as r:
            texto = (json.loads(r.read()).get("message") or {}).get("content", "")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ModeloIndisponivel(f"{_url()} ({_modelo()}): {type(e).__name__}: {e}") from e
    try:
        dado = json.loads(texto)
        j = Julgamento(bool(dado["fere"]), str(dado["porque"])[:300], [int(i) for i in dado.get("itens") or []])
    except (ValueError, KeyError, TypeError):
        return None
    _ao_cache(chave, j)
    return j


# ------------------------------------------------------------------ evidencia


def numerado(ctx: Contexto, p: Path, inicio: int, fim: int) -> str:
    linhas = ctx.texto(p).splitlines()[inicio - 1:min(fim, inicio - 1 + LINHAS_EVIDENCIA)]
    return "\n".join(f"{inicio + i:>5} | {t}" for i, t in enumerate(linhas))


def fonte(ctx: Contexto, d: Def) -> str:
    return numerado(ctx, d.caminho, d.no.lineno, getattr(d.no, "end_lineno", d.no.lineno))


def _no_escopo(ctx: Contexto) -> Iterator[Def]:
    yield from funcoes(ctx, ctx.py)


# ------------------------------------------------------------------ geradores: desenho


MINIMO_ACESSOS_INVEJA = 5
FATOR_INVEJA = 2   # le o parametro mais que o dobro do que le o proprio objeto


def _acessos(fn: ast.AST) -> dict[str, int]:
    contagem: dict[str, int] = defaultdict(int)
    for n in sem_aninhadas(fn):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            contagem[n.value.id] += 1
    return contagem


def inveja_de_dados(ctx: Contexto) -> Iterator[Pergunta]:
    """Funcao que le muitos campos de um parametro e poucos do proprio objeto (D7)."""
    for d in _no_escopo(ctx):
        params = [a.arg for a in d.no.args.args if a.arg not in ("self", "cls")]
        acessos = _acessos(d.no)
        proprio = acessos.get("self", 0)
        for p in params:
            if acessos.get(p, 0) >= MINIMO_ACESSOS_INVEJA and acessos[p] > FATOR_INVEJA * proprio:
                yield Pergunta(d.rel, d.no.lineno,
                               f"Critério: inveja de dados. A função `{d.no.name}` lê {acessos[p]} campos de `{p}`. "
                               f"A lógica deveria morar no objeto `{p}`? fere=true se sim.", fonte(ctx, d))
                break


MINIMO_DEFS_DEPOSITO = 15


def arquivo_deposito(ctx: Contexto) -> Iterator[Pergunta]:
    """Modulo grande: as funcoes formam uma responsabilidade ou varias sem relacao (D1)."""
    for rel, _, arvore in ctx.arvores(ctx.py):
        defs = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        if len(defs) < MINIMO_DEFS_DEPOSITO:
            continue
        resumo = "\n".join(f"{n.lineno:>5} | {n.name}: {_doc(n)}" for n in defs)
        yield Pergunta(rel, 1, f"Critério: arquivo-depósito. O módulo tem {len(defs)} definições no topo. Elas "
                               "formam uma responsabilidade só? fere=true se há três ou mais grupos sem relação "
                               "entre si; em 'porque', nomeie os grupos.", resumo)


def _classe_chamada(c: ast.Call) -> str | None:
    curto = nome(c.func).rsplit(".", 1)[-1]
    if curto[:1].isupper() and not curto.endswith(("Error", "Exception", "Warning")) and curto not in ("Path",):
        return curto
    return None


TEXTO_LITERAL_MAXIMO = 80
MINIMO_SITIOS = 2   # divergencia so existe entre duas funcoes ou mais


def _kwargs_literais(c: ast.Call) -> dict[str, object]:
    """Argumentos nomeados de valor literal curto: o que se compara entre um sitio e outro."""
    saida: dict[str, object] = {}
    for k in c.keywords:
        if not (k.arg and isinstance(k.value, ast.Constant)):
            continue
        if isinstance(k.value.value, str) and len(k.value.value) >= TEXTO_LITERAL_MAXIMO:
            continue
        saida[k.arg] = k.value.value
    return saida


def _doc(no: ast.AST | None) -> str:
    texto = ast.get_docstring(no) if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None
    return texto.splitlines()[0][:100] if texto else ""


def instancias_divergentes(ctx: Contexto) -> Iterator[Pergunta]:
    """A mesma classe montada com valores literais diferentes no mesmo parametro, em funcoes
    diferentes da stack: decisao espalhada ou razao local (D9)."""
    sitios: dict[str, list[tuple[Def, ast.Call, dict[str, object]]]] = defaultdict(list)
    for d in funcoes(ctx, ctx.py_repo):
        for _, c in chamados(d.no):
            if (classe := _classe_chamada(c)) and (kw := _kwargs_literais(c)):
                sitios[classe].append((d, c, kw))
    escopo = {ctx.rel(p) for p in ctx.py}
    for classe, onde in sitios.items():
        valores: dict[str, set[str]] = defaultdict(set)
        for _, _, kw in onde:
            for k, v in kw.items():
                valores[k].add(repr(v))
        divergentes = sorted(k for k, vs in valores.items() if len(vs) > 1)
        primeiro = next(((d, c) for d, c, _ in onde if d.rel in escopo), None)
        if not divergentes or primeiro is None or len({id(d.no) for d, _, _ in onde}) < MINIMO_SITIOS:
            continue
        tabela = "\n".join(f"{d.rel}:{c.lineno} em {d.no.name}: "
                           + ", ".join(f"{k}={kw[k]!r}" for k in divergentes if k in kw)
                           for d, c, kw in onde[:20])
        yield Pergunta(primeiro[0].rel, primeiro[1].lineno,
                       f"Critério: a mesma decisão de desenho em vários lugares. `{classe}` é montada em "
                       f"{len(onde)} lugares da stack com valores diferentes em {', '.join(divergentes)}. É uma "
                       "decisão espalhada, que deveria morar num lugar só? fere=true se sim; false se cada "
                       "valor tem razão local evidente.", tabela)


PALAVRAS_COMENTARIO = 12
COMENTARIOS_POR_PERGUNTA = 25
_COMENTARIO_DE_FERRAMENTA = re.compile(r"#\s*(noqa|type:|pragma|shellcheck|fmt:|ruff:)|^#!")


def comentario_redundante(ctx: Contexto) -> Iterator[Pergunta]:
    """Comentario curto que so repete a linha seguinte (D13), um lote por arquivo."""
    for p in ctx.py:
        linhas = ctx.texto(p).splitlines()
        pares, alvos = [], []
        for i, t in enumerate(linhas[:-1]):
            s = t.strip()
            if (s.startswith("#") and not _COMENTARIO_DE_FERRAMENTA.search(s)
                    and len(s.split()) <= PALAVRAS_COMENTARIO and linhas[i + 1].strip()
                    and not linhas[i + 1].strip().startswith("#")):
                pares.append(f"[{len(pares) + 1}] {i + 1:>5} | {s}\n      {i + 2:>5} | {linhas[i + 1].strip()}")
                alvos.append(i + 1)
            if len(pares) == COMENTARIOS_POR_PERGUNTA:
                break
        if pares:
            yield Pergunta(ctx.rel(p), alvos[0],
                           "Critério: comentário que repete o código. Em 'itens', liste os números [n] dos "
                           "comentários que só dizem o que a linha seguinte faz, sem o porquê. fere=true se "
                           "houver algum.", "\n".join(pares), tuple(alvos))


MINIMO_MODULOS_PACOTE = 4


def decomposicao_temporal(ctx: Contexto) -> Iterator[Pergunta]:
    """Pacote dividido pela ordem dos passos, nao pelo que cada modulo sabe (D10)."""
    por_pasta: dict[Path, list[Path]] = defaultdict(list)
    for p in ctx.py:
        por_pasta[p.parent].append(p)
    for arquivos in por_pasta.values():
        if len(arquivos) < MINIMO_MODULOS_PACOTE:
            continue
        resumo = "\n".join(f"{a.name}: {_doc(ctx.arvore(a))}" for a in sorted(arquivos))
        yield Pergunta(ctx.rel(arquivos[0]), 1,
                       "Critério: decomposição temporal. Os módulos desta pasta estão divididos pela ordem dos "
                       "passos de um fluxo (ler, transformar, gravar), de modo que a mesma decisão atravessa "
                       "vários deles? fere=true se sim.", resumo)


# ------------------------------------------------------------------ geradores: concorrencia e falha


def _alvos_de_thread(ctx: Contexto) -> Iterator[tuple[Def, Def]]:
    """(quem dispara, funcao que roda em thread) quando a funcao e do mesmo repositorio."""
    defs: dict[str, list[Def]] = defaultdict(list)
    for d in funcoes(ctx, ctx.py_repo):
        defs[d.no.name].append(d)
    for d in _no_escopo(ctx):
        for curto, c in chamados(d.no):
            alvo = None
            if curto in ("submit", "map") and c.args:
                alvo = c.args[0]
            elif curto == "Thread":
                alvo = next((k.value for k in c.keywords if k.arg == "target"), None)
            if alvo is not None:
                for t in defs.get(nome(alvo).rsplit(".", 1)[-1], []):
                    yield d, t


def thread_para_cpu(ctx: Contexto) -> Iterator[Pergunta]:
    """Trabalho de CPU posto em thread: no CPython as threads nao paralelizam CPU (C4)."""
    for quem, alvo in _alvos_de_thread(ctx):
        yield Pergunta(quem.rel, quem.no.lineno,
                       f"Critério: thread para trabalho de CPU. `{alvo.no.name}` roda em thread. Ela faz só "
                       "cálculo, sem rede, disco, subprocesso ou espera? fere=true se for só CPU.", fonte(ctx, alvo))


def estado_sem_trava(ctx: Contexto) -> Iterator[Pergunta]:
    """Funcao em varias threads que muda estado compartilhado sem trava (C6)."""
    for quem, alvo in _alvos_de_thread(ctx):
        yield Pergunta(alvo.rel, alvo.no.lineno,
                       f"Critério: estado compartilhado entre threads sem trava. `{alvo.no.name}` roda em "
                       "várias threads ao mesmo tempo. Ela altera variável global, atributo de objeto ou "
                       "coleção de fora sem `with lock`? fere=true se sim.", fonte(ctx, alvo))


def repete_permanente(ctx: Contexto) -> Iterator[Pergunta]:
    """Laco de repeticao que repete tambem o erro que repetir nao conserta (R6)."""
    for d in _no_escopo(ctx):
        lacos = [n for n in sem_aninhadas(d.no) if isinstance(n, (ast.For, ast.While))
                 and any(isinstance(m, ast.ExceptHandler) for m in sem_aninhadas(n))
                 and any(isinstance(m, ast.Call) and externa(m) for m in sem_aninhadas(n))]
        if lacos:
            yield Pergunta(d.rel, lacos[0].lineno,
                           "Critério: repetição de erro permanente. O laço repete a chamada na falha. Ele repete "
                           "também erro que repetir não conserta (4xx, validação, arquivo inexistente, erro de "
                           "programação)? fere=true se sim.", fonte(ctx, d))


_SELECT = re.compile(r"\bSELECT\b.+\bFROM\b", re.IGNORECASE | re.DOTALL)


def consulta_sem_limite(ctx: Contexto) -> Iterator[Pergunta]:
    """Consulta sem LIMIT cujo resultado vai inteiro a quem chamou (A5)."""
    for d in _no_escopo(ctx):
        textos = [n for n in sem_aninhadas(d.no) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        sem_limite = [t for t in textos if _SELECT.search(t.value) and "LIMIT" not in t.value.upper()]
        if sem_limite and any(curto == "fetchall" for curto, _ in chamados(d.no)):
            yield Pergunta(d.rel, sem_limite[0].lineno,
                           "Critério: resultado sem limite. A consulta não tem LIMIT e o resultado vai inteiro "
                           "para fetchall. Ele cresce com o dado e chega inteiro a quem chamou (API, CLI, "
                           "memória)? fere=true se sim; false se o conjunto é pequeno por natureza.", fonte(ctx, d))


# ------------------------------------------------------------------ geradores: fila


_FILA = re.compile(r"SKIP\s+LOCKED|\bINSERT\b.+\b(estado|status|situacao)\b", re.IGNORECASE | re.DOTALL)
_PERGUNTAS_FILA = {
    "FILA_RETOMA": "Na subida, o executor retoma ou devolve à fila o item que estava em execução sem dono vivo?",
    "FILA_ESTADO_DAS_LINHAS": "O andamento e o veredito do lote saem de consulta às linhas da fila, não da memória?",
    "FILA_IDEMPOTENTE": "O item tem chave de idempotência, de modo que executar duas vezes não muda o resultado?",
    "FILA_TETO": "A linha conta tentativas, e passado o teto o item vai a estado terminal com a causa?",
    "FILA_IDADE": "Há consulta ou métrica da idade do item pendente mais antigo e da contagem por estado?",
}


def _modulos_de_fila(ctx: Contexto) -> Iterator[tuple[str, str]]:
    for rel, p, arvore in ctx.arvores(ctx.py):
        sql = [n for n in ast.walk(arvore) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and _FILA.search(n.value)]
        if sql:
            nomes = [n.name for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            textos = "\n\n".join(f"{n.lineno:>5} | {n.value.strip()[:400]}" for n in sql[:8])
            yield rel, f"Funções do módulo: {', '.join(nomes)}\n\nSQL:\n{textos}"


def _gerador_fila(chave: str) -> Callable[[Contexto], Iterator[Pergunta]]:
    def gerar(ctx: Contexto) -> Iterator[Pergunta]:
        for rel, evidencia in _modulos_de_fila(ctx):
            yield Pergunta(rel, 1, f"Critério de fila durável. {_PERGUNTAS_FILA[chave]} fere=true se a "
                                   "evidência mostra que NÃO.", evidencia)
    return gerar


# ------------------------------------------------------------------ geradores: teste e rota


TEXTO_DE_FORMA = 40


def _afirma_forma(fn: ast.AST) -> bool:
    """Filtro mecanico antes do modelo: o teste compara texto longo exato ou linha por indice."""
    for n in ast.walk(fn):
        if isinstance(n, ast.Compare) and any(
                isinstance(v, ast.Constant) and isinstance(v.value, str) and len(v.value) >= TEXTO_DE_FORMA
                for v in [n.left, *n.comparators]):
            return True
        if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Call)
                and nome(n.value.func).endswith("splitlines")):
            return True
    return False


def teste_fragil(ctx: Contexto) -> Iterator[Pergunta]:
    """Teste que afirma a forma, nao o comportamento (T4)."""
    for d in _no_escopo(ctx):
        if e_teste(d.rel) and d.no.name.startswith("test") and _afirma_forma(d.no):
            yield Pergunta(d.rel, d.no.lineno,
                           "Critério: teste frágil. Este teste afirma a forma (texto exato, ordem, detalhe de "
                           "implementação) de modo que quebra com mudança que não toca o comportamento? "
                           "fere=true se sim.", fonte(ctx, d))


def rota_sem_contrato(ctx: Contexto) -> Iterator[Pergunta]:
    """Rota HTTP que devolve dicionario montado na mao, sem esquema nem versao (A3)."""
    escopo = set(ctx.py)
    for caminho, d in rotas(ctx).items():
        if d.caminho in escopo:
            yield Pergunta(d.rel, d.no.lineno,
                           f"Critério: contrato sem versão. A rota `{caminho}` devolve uma estrutura que "
                           "outro serviço consome. O formato está fixado em esquema ou modelo declarado, com "
                           "versão? fere=true se é dicionário montado na mão sem esquema nem versão.",
                           fonte(ctx, d))


LEITURAS: dict[str, Callable[[Contexto], Iterator[Pergunta]]] = {
    "INVEJA_DE_DADOS": inveja_de_dados,
    "ARQUIVO_DEPOSITO": arquivo_deposito,
    "INSTANCIAS_DIVERGENTES": instancias_divergentes,
    "COMENTARIO_REDUNDANTE": comentario_redundante,
    "DECOMPOSICAO_TEMPORAL": decomposicao_temporal,
    "THREAD_PARA_CPU": thread_para_cpu,
    "ESTADO_SEM_TRAVA": estado_sem_trava,
    "REPETE_PERMANENTE": repete_permanente,
    "CONSULTA_SEM_LIMITE": consulta_sem_limite,
    "TESTE_FRAGIL": teste_fragil,
    "ROTA_SEM_CONTRATO": rota_sem_contrato,
    **{chave: _gerador_fila(chave) for chave in _PERGUNTAS_FILA},
}

# leem o repositorio inteiro, nao so o escopo
LEITURA_DO_REPOSITORIO = {"INSTANCIAS_DIVERGENTES", "THREAD_PARA_CPU", "ESTADO_SEM_TRAVA", "ROTA_SEM_CONTRATO"}
