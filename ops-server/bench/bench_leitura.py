"""bench_leitura.py — o runner do bench de homologação da `ler_arquivo` (spec ler-arquivo §16).

Mede a candidata (`leitura.le` + a poda da §11) contra a referência congelada
(`read_file_ref.read_file`), no mesmo corpus (`corpus.py`) e com o mesmo leitor roteirizado.
É gate: `main()` sai 0 se os dez critérios da §16.5 passam, 1 se algum falha. Não mede modelo
(§16.7): T2 e T3 dizem quanto a leitura custa quando se sabe o que ler.

O leitor roteirizado (§16.3) segue `proximo_args` ou `next_offset` e só olha o texto quando a
tarefa pede. Onde a referência não tem mapa de linha para byte, ela lê da cabeça até cobrir o
trecho; a candidata pede a faixa. O que cada tarefa quer ler sai de um ORÁCULO, fora da medida,
calculado sobre os bytes do arquivo: o fim do trecho em bytes decide quando o leitor para.

Contagem por instrumento, não por relógio (§16.4): chamadas, bytes servidos (o retorno
serializado em JSON, com cabeçalho e continuação), bytes lidos (um invólucro do `open` que
conta o que se pede ao `read`) e defeitos silenciosos. Tempo é relatado (mediana e p95 de cinco
repetições) e não decide nada.

Rode: `pytest ops-server/bench` ou `python ops-server/bench/bench_leitura.py`.
"""
from __future__ import annotations

import codecs
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
for _d in (_AQUI.parent, _AQUI):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import corpus as _corpus                      # noqa: E402
import leitura                                # noqa: E402
import poda                                   # noqa: E402
import read_file_ref as _ref                  # noqa: E402

# ----------------------------------------------------------------------------- limites
# Spec ler-arquivo §16.5. São hipóteses declaradas da spec, não medida: a primeira rodada os
# confirma ou os revisa POR EMENDA da seção, com o número à vista do dono. Limite mudado sem
# emenda não vale — nenhuma constante daqui se altera para fazer o bench passar.
LIMITE_BYTES_T1 = 1.05          # §16.5 critério 4: T1, bytes servidos, candidata ≤ 1,05 × referência
LIMITE_CHAMADAS_T1 = 1.05       # §16.5 critério 5: T1, chamadas, candidata ≤ 1,05 × referência
LIMITE_IO_T1_FRIO = 2.1         # §16.5 critério 8: T1, bytes lidos a frio ≤ 2,1 × referência
LIMITE_IO_T1_QUENTE = 1.05      # §16.5 critério 8: T1, bytes lidos a quente ≤ 1,05 × referência
LIMITE_IO_T23_FRIO = 2          # §16.5 critério 8: T2 e T3, a frio ≤ 2 × referência em toda tarefa
LIMITE_IO_T23_QUENTE = 1        # §16.5 critério 8: T2 e T3, a quente ≤ a referência (razão 1)

# ----------------------------------------------------------------------------- réguas do bench
PAGINA = 40_000                 # §16.3 T1: páginas de 40.000 bytes
LIMIAR_T2_T3 = 40_000           # §16.3: T2 e T3 só em arquivo acima de 40 KB
LINHAS_T2 = 200                 # §16.3 T2: as 200 linhas
MAX_T4 = 40_000                 # §16.3 T4: todo arquivo até 40 KB
REPETICOES = 5                  # §16.4.6: mediana e p95 de cinco repetições
SID = "bench-leitura-u6"        # sessão fixa; cada rodada tem um registro novo, em memória
ANALISADORES = ("text/markdown", "text/x-python", "application/json")
CATEGORIAS = ("fabricado", "versao", "binario", "soma", "encoding", "excecao")


# ============================================================ registro de mentira e invólucro
class RegistroEmMemoria:
    """O que o `Ledger` usa do redis: hget, hset, hdel, get, incr, incrby, expire."""

    def __init__(self):
        self.kv, self.h = {}, {}

    def incr(self, k):
        return self.incrby(k, 1)

    def incrby(self, k, n):
        self.kv[k] = int(self.kv.get(k, 0)) + n
        return self.kv[k]

    def get(self, k):
        return self.kv.get(k)

    def expire(self, k, ttl):
        return True

    def hget(self, k, campo):
        return self.h.get(k, {}).get(campo)

    def hset(self, k, campo, valor):
        self.h.setdefault(k, {})[campo] = valor

    def hdel(self, k, campo):
        return 1 if self.h.get(k, {}).pop(campo, None) is not None else 0


class _Arq:
    """O arquivo aberto em binário, contando os bytes que `read` devolve. `leitura.py` só usa
    `read`, `seek`, `fileno` e o contexto; o resto delega sem contar."""

    def __init__(self, fh, cont):
        self._fh, self._cont = fh, cont

    def read(self, n=-1):
        dados = self._fh.read(n)
        self._cont.lidos += len(dados)
        return dados

    def seek(self, *a):
        return self._fh.seek(*a)

    def tell(self):
        return self._fh.tell()

    def fileno(self):
        return self._fh.fileno()

    def close(self):
        return self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._fh.close()
        return False

    def __getattr__(self, nome):
        return getattr(self._fh, nome)


class Contador:
    def __init__(self):
        self.lidos = 0

    def abre(self, p, modo="rb", *a, **k):
        fh = open(p, modo, *a, **k)
        return _Arq(fh, self) if "b" in modo else fh


def servidos_json(r) -> int:
    """Bytes servidos (§16.4.2): o retorno serializado, o que a fita recebe."""
    return len(json.dumps(r, ensure_ascii=False, default=str).encode("utf-8", "replace"))


def recusou(r: dict) -> bool:
    return bool(r.get("erro") or r.get("recusado"))


# ============================================================ as duas tools, como a porta as serve
def serve_candidata(caminho, *, ledger, abre, curto=None, **kw) -> dict:
    """A porta chama `leitura.le`, tira `classe_erro` e passa o retorno pela poda (§11)."""
    r = leitura.le(Path(caminho), abre=abre, curto=curto, **kw)
    r.pop("classe_erro", None)
    if poda.intocavel(r) or not isinstance(r.get("conteudo"), str) or not r["conteudo"]:
        return r
    giro = ledger.giro()
    modo = kw.get("modo", "texto")
    faixa = (kw.get("linhas") or "1-") if kw.get("offset") is None else f"b{kw['offset']}"
    conteudo = r["conteudo"]
    servido, meta = poda.poda_texto(
        conteudo, cap=max(50_000, len(conteudo.encode("utf-8", "replace"))), cauda=False,
        alca=f"ler_arquivo:{caminho}|{modo}|{faixa}", sessao_id=SID, giro=giro,
        tool="ler_arquivo", ledger=ledger, nome_derrame=f"g{giro:05d}-conteudo.txt")
    r["conteudo"] = servido
    r = poda.enxuga_envelope(r)
    r["poda"] = meta
    aviso = poda.linha_humana(meta)
    if aviso:
        r["poda_aviso"] = aviso
    return r


class Ctx:
    """Uma execução de tarefa: registro novo (a releitura mede igual nas duas tools), contador
    de bytes lidos novo, e a soma do que cada chamada custou."""

    def __init__(self, curto: str | None = None):
        self.cont = Contador()
        self.ledger = poda.Ledger(RegistroEmMemoria(), SID)
        self.curto = curto
        self.chamadas = 0
        self.servidos = 0
        self.tempos: list[float] = []
        self.retornos: list[dict] = []
        self.laco = False

    def _registra(self, r: dict, dt: float) -> dict:
        self.chamadas += 1
        self.servidos += servidos_json(r)
        self.tempos.append(dt)
        self.retornos.append(r)
        return r

    def ler_ref(self, caminho, offset: int = 0, max_bytes: int = PAGINA) -> dict:
        t0 = time.perf_counter()
        r = _ref.read_file(str(caminho), offset, max_bytes, ledger=self.ledger, sessao_id=SID,
                           abre=self.cont.abre)
        return self._registra(r, time.perf_counter() - t0)

    def ler_cand(self, caminho, **kw) -> dict:
        t0 = time.perf_counter()
        r = serve_candidata(caminho, ledger=self.ledger, abre=self.cont.abre, curto=self.curto,
                            **kw)
        return self._registra(r, time.perf_counter() - t0)


# ============================================================ o oráculo (fora da medida)
class Oraculo:
    """Os bytes do arquivo e onde cada linha começa e termina, lidos sem o invólucro."""

    def __init__(self, caminho: Path):
        self.dados = Path(caminho).read_bytes()
        self.nl = [m.end() for m in re.finditer(rb"\n", self.dados)]
        self.total_linhas = len(self.nl) + (1 if self.dados and not self.dados.endswith(b"\n")
                                            else 0)

    def ini_linha(self, a: int) -> int:
        """Byte em que a linha `a` (base 1) começa."""
        if a <= 1:
            return 0
        return self.nl[a - 2] if a - 2 < len(self.nl) else len(self.dados)

    def fim_linha(self, b: int) -> int:
        """Byte logo depois da linha `b` (com o `\\n`, se tem)."""
        return self.nl[b - 1] if 1 <= b <= len(self.nl) else len(self.dados)


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _pula_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def _chaves_json(texto: str) -> list[tuple[str, int, int]]:
    """(chave, início, fim do valor), em caracteres, das chaves do primeiro nível."""
    dec = json.JSONDecoder()
    i = _pula_ws(texto, 0) + 1
    pares = []
    while True:
        i = _pula_ws(texto, i)
        if i >= len(texto) or texto[i] == "}":
            return pares
        chave, j = dec.raw_decode(texto, i)
        j = _pula_ws(texto, j) + 1                      # os dois-pontos
        j = _pula_ws(texto, j)
        _valor, fim = dec.raw_decode(texto, j)
        pares.append((chave, i, fim))
        i = _pula_ws(texto, fim)
        if i < len(texto) and texto[i] == ",":
            i += 1


def item_t2(arq, orc: Oraculo) -> int:
    """A linha de partida de T2: fixa, da ordem do sha256 do caminho mais o nome da tarefa."""
    espaco = max(1, orc.total_linhas - LINHAS_T2 + 1)
    return 1 + int(_sha(f"{arq.nome}|T2"), 16) % espaco


def escolhe_t3(arq, orc: Oraculo) -> tuple[dict | None, str | None]:
    """O item de T3, do sumário calculado FORA da medida com `leitura.sumario`; o primeiro na
    ordem do sha256 do caminho mais o nome da tarefa. (item, motivo de não se aplicar)."""
    tp = leitura.tipo_real(orc.dados[:leitura.CABECA_TIPO], Path(arq.caminho).name)
    if tp["binario"] or tp["tipo"] not in ANALISADORES:
        return None, "sem analisador"
    if tp["bom"] not in (None, "utf-8"):
        return None, f"BOM {tp['bom']}"
    texto = orc.dados.decode("utf-8", "replace")
    itens, motivo = leitura.sumario(tp["tipo"], texto, orc.total_linhas)
    if itens is None:
        return None, motivo
    if tp["tipo"] == "application/json":
        pares = _chaves_json(texto)
        if not pares:
            return None, "JSON sem chaves"
        chave, _ini, fim = min(pares, key=lambda x: _sha(f"{arq.nome}|T3|{x[0]}"))
        return {"tipo": tp["tipo"], "titulo": chave, "ini": None, "fim": None,
                "fim_byte": len(texto[:fim].encode("utf-8", "replace"))}, None
    com_faixa = [i for i in itens if i[2] is not None]
    if not com_faixa:
        return None, "sumário vazio"
    it = min(com_faixa, key=lambda i: _sha(f"{arq.nome}|T3|{i[0]}|{i[1]}|{i[2]}"))
    return {"tipo": tp["tipo"], "nivel": it[0], "titulo": it[1], "ini": it[2], "fim": it[3],
            "ini_byte": orc.ini_linha(it[2]), "fim_byte": orc.fim_linha(it[3])}, None


# ============================================================ o leitor roteirizado
def cabeca_ref(ctx: Ctx, caminho, cobre: int | None = None) -> list[dict]:
    """Referência: da cabeça, `next_offset` a `next_offset`, até o fim ou até cobrir `cobre`."""
    pags, off = [], 0
    while True:
        r = ctx.ler_ref(caminho, off)
        pags.append(r)
        if recusou(r):
            break
        if cobre is not None and r["offset"] + r["bytes_lidos"] >= cobre:
            break
        if not r.get("truncated"):
            break
        off = r["next_offset"]
    return pags


def segue_cand(ctx: Ctx, args: dict, cobre: int | None = None) -> list[dict]:
    """Candidata: segue `proximo_args` até `fim do arquivo` ou até cobrir `cobre` bytes."""
    pags, vistos = [], set()
    while True:
        chave = json.dumps(args, sort_keys=True)
        if chave in vistos:                      # a continuação não andou: laço
            ctx.laco = True
            break
        vistos.add(chave)
        r = ctx.ler_cand(**args)
        pags.append(r)
        pa = r.get("proximo_args")
        if recusou(r) or not pa:
            break
        if cobre is not None and r.get("bytes") and r["bytes"][1] >= cobre:
            break
        args = dict(pa)
    return pags


def faixa_pag(tool: str, r: dict) -> tuple[int, int]:
    if tool == "ref":
        ini = r.get("offset", 0)
        return ini, ini + r.get("bytes_lidos", 0)
    b = r.get("bytes")
    return (b[0], b[1]) if b else (0, 0)


def texto_pag(tool: str, r: dict) -> str:
    return r.get("content" if tool == "ref" else "conteudo") or ""


_BOMS = (codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE, codecs.BOM_UTF32_LE,
         codecs.BOM_UTF32_BE)


def _estrito(dados: bytes) -> bool:
    try:
        dados.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def defeitos_pags(tool: str, orc: Oraculo, pags: list[dict], laco: bool = False
                  ) -> tuple[list[str], bool]:
    """Os defeitos silenciosos de §16.4.4 que uma leitura inteira (T1) deixa ver, e se a soma
    da §6 fecha. Cada defeito abre com a categoria: fabricado, soma, encoding."""
    d: list[str] = []
    paginas = [p for p in pags if not recusou(p)]
    fecha = len(paginas) == len(pags) and not laco
    if laco:
        d.append("soma: a continuação repetiu a chamada sem andar")
    enc = "utf-8"
    if tool == "cand":
        enc = next((p["encoding"]["decidido"] for p in paginas
                    if isinstance(p.get("encoding"), dict)), "utf-8")
    transcodificado = enc.lower().startswith(("utf-16", "utf-32"))
    esperado = orc.dados.decode(enc, "replace")
    textos = [texto_pag(tool, p) for p in paginas]
    n_pag, n_arq = sum(t.count("�") for t in textos), esperado.count("�")
    if n_pag > n_arq:                                              # (1) caractere fabricado
        d.append(f"fabricado: {n_pag - n_arq} caractere(s) de substituição além dos do arquivo")
        fecha = False
    if not transcodificado and paginas:                            # (4) furo, repetição, troca
        pos = 0
        for p, t in zip(paginas, textos):
            a, b = faixa_pag(tool, p)
            if a > pos:
                d.append(f"soma: furo de {a - pos} byte(s) em {pos}")
                fecha = False
            elif a < pos:
                d.append(f"soma: {pos - a} byte(s) trazidos duas vezes em {a}")
                fecha = False
            if t != orc.dados[a:b].decode(enc, "replace"):
                d.append(f"soma: página de {a} a {b} difere dos bytes do arquivo")
                fecha = False
            pos = b
        if fecha and pos != len(orc.dados):
            d.append(f"soma: as páginas param em {pos} de {len(orc.dados)} bytes")
            fecha = False
    if fecha and "".join(textos) != esperado:
        d.append("soma: a concatenação das páginas difere do arquivo")
        fecha = False
    tem_bom = any(orc.dados.startswith(b) for b in _BOMS)          # (5) encoding sem aviso
    if not _estrito(orc.dados) and not tem_bom and paginas:
        if tool == "ref":
            d.append("encoding: arquivo não é UTF-8 estrito e a leitura não avisa")
        elif not all((p.get("encoding") or {}).get("julgado") is False
                     and "NÃO JULGADO" in p.get("cabecalho", "") for p in paginas):
            d.append("encoding: arquivo não é UTF-8 estrito e a página não abre com NÃO JULGADO")
    return d, fecha


# ============================================================ as tarefas
def t1(tool, ctx: Ctx, arq, orc: Oraculo) -> dict:
    if tool == "ref":
        pags = cabeca_ref(ctx, arq.caminho)
    else:
        pags = segue_cand(ctx, {"caminho": str(arq.caminho), "linhas": "1-"})
    defeitos, fecha = defeitos_pags(tool, orc, pags, ctx.laco)
    return {"defeitos": defeitos, "recusou": any(recusou(p) for p in pags),
            "extra": {"soma_fecha": fecha, "paginas": len(pags)}}


def _trecho_certo(orc: Oraculo, pags: list[dict], ini: int, fim: int) -> list[str]:
    """O que a candidata trouxe começa pelos bytes do trecho pedido."""
    paginas = [p for p in pags if not recusou(p)]
    if not paginas:
        return []
    enc = next((p["encoding"]["decidido"] for p in paginas
                if isinstance(p.get("encoding"), dict)), "utf-8")
    esperado = orc.dados[ini:fim].decode(enc, "replace")
    trouxe = "".join(texto_pag("cand", p) for p in paginas)
    if trouxe[:len(esperado)] != esperado:
        return [f"soma: o trecho de {ini} a {fim} voltou diferente dos bytes do arquivo"]
    return []


def t2(tool, ctx: Ctx, arq, orc: Oraculo) -> dict:
    n = item_t2(arq, orc)
    ate = n + LINHAS_T2 - 1
    ini, fim = orc.ini_linha(n), orc.fim_linha(ate)
    defeitos = []
    if tool == "ref":
        pags = cabeca_ref(ctx, arq.caminho, cobre=fim)
    else:
        pags = segue_cand(ctx, {"caminho": str(arq.caminho), "linhas": f"{n}-{ate}"}, cobre=fim)
        defeitos = _trecho_certo(orc, pags, ini, fim)
    return {"defeitos": defeitos, "recusou": any(recusou(p) for p in pags),
            "extra": {"linha": n, "ate": ate, "fim_byte": fim}}


def t3(tool, ctx: Ctx, arq, orc: Oraculo, item: dict) -> dict:
    defeitos, extra = [], {"item": item["titulo"], "fim_byte": item["fim_byte"]}
    if tool == "ref":
        pags = cabeca_ref(ctx, arq.caminho, cobre=item["fim_byte"])
    elif item["ini"] is None:
        # JSON: a faixa do sumário é nula, a candidata usa a estratégia da referência.
        extra["estrategia"] = "da-referencia"
        pags = segue_cand(ctx, {"caminho": str(arq.caminho), "linhas": "1-"},
                          cobre=item["fim_byte"])
    else:
        r1 = ctx.ler_cand(str(arq.caminho), modo="sumario")
        lista = r1.get("sumario")
        achou = isinstance(lista, list) and any(
            i[0] == item["nivel"] and i[1] == item["titulo"] and i[2] == item["ini"]
            and i[3] == item["fim"] for i in lista)
        if achou:
            pags = segue_cand(ctx, {"caminho": str(arq.caminho),
                                    "linhas": f"{item['ini']}-{item['fim']}"},
                              cobre=item["fim_byte"])
            defeitos = _trecho_certo(orc, pags, item["ini_byte"], item["fim_byte"])
        else:
            extra["estrategia"] = "da-referencia (item fora do sumário servido)"
            pags = segue_cand(ctx, {"caminho": str(arq.caminho), "linhas": "1-"},
                              cobre=item["fim_byte"])
        pags = [r1, *pags]
    return {"defeitos": defeitos, "recusou": any(recusou(p) for p in pags), "extra": extra}


def t4(tool, ctx: Ctx, arq, orc: Oraculo) -> dict:
    if tool == "ref":
        ctx.ler_ref(arq.caminho)
        r2 = ctx.ler_ref(arq.caminho)
    else:
        args = {"caminho": str(arq.caminho), "linhas": "1-"}
        ctx.ler_cand(**args)
        r2 = ctx.ler_cand(**args)
    return {"defeitos": [], "recusou": recusou(r2),
            "extra": {"segunda": servidos_json(r2), "modo": (r2.get("poda") or {}).get("modo")}}


def t5(tool, ctx: Ctx, arq, orc: Oraculo) -> dict:
    p = Path(arq.caminho)
    original = _corpus.conteudo_original("mudanca")
    p.write_bytes(original)
    if tool == "ref":
        r1 = ctx.ler_ref(p)
        proximo = {"offset": r1.get("next_offset") or 0}
    else:
        r1 = ctx.ler_cand(str(p), linhas="1-")
        proximo = dict(r1.get("proximo_args") or {})
    p.write_bytes(b"ALTERADA " + original[9:] + b"linha nova\n")      # muda conteúdo e tamanho
    try:
        if tool == "ref":
            r2 = ctx.ler_ref(p, **proximo)
            sinalizou = False                      # a referência não tem versão: nada a sinalizar
        else:
            r2 = ctx.ler_cand(**proximo)
            sinalizou = bool(r2.get("mudou")) and \
                str(r2.get("cabecalho", "")).startswith("ARQUIVO MUDOU")
    finally:
        p.write_bytes(original)
    defeitos = [] if sinalizou else ["versao: a segunda página é de outra versão do arquivo e "
                                     "nada avisa"]
    return {"defeitos": defeitos, "recusou": recusou(r2), "extra": {"sinalizou": sinalizou}}


def t6(tool, ctx: Ctx, arq, orc: Oraculo, caso: str) -> dict:
    """Borda: linha longa, binário e vazio — como cada tool responde."""
    if tool == "ref":
        r = ctx.ler_ref(arq.caminho)
        texto = r.get("content")
        if caso == "binario":
            ok = bool(r.get("erro"))
            defeitos = [] if ok else ["binario: o binário foi servido como texto"]
        elif caso == "linha_longa":
            ok, defeitos = False, []            # a referência não tem a resposta
        else:
            ok, defeitos = texto == "" and not r.get("truncated"), []
        return {"defeitos": defeitos, "recusou": recusou(r),
                "extra": {"ok": ok, "conteudo_bytes": len((texto or "").encode("utf-8"))}}
    r = ctx.ler_cand(str(arq.caminho), linhas="1-")
    if caso == "binario":
        ok = bool(r.get("recusado")) and r.get("motivo") == "binario" and "conteudo" not in r
        defeitos = [] if ok else ["binario: o binário foi servido como texto"]
    elif caso == "linha_longa":
        ok = bool(r.get("linha_longa")) and "LINHA LONGA" in r.get("cabecalho", "") \
            and not r.get("conteudo")
        defeitos = []
    else:
        ok = r.get("proximo") == leitura.FIM and r.get("conteudo") == "" \
            and "arquivo vazio" in r.get("cabecalho", "")
        defeitos = []
    return {"defeitos": defeitos, "recusou": False,
            "extra": {"ok": ok, "conteudo_bytes": len((r.get("conteudo") or "").encode("utf-8")),
                      "proximo": r.get("proximo")}}


def t7(tool, ctx: Ctx, forma: str, caminho: Path, esperado: Path) -> dict:
    if tool == "ref":
        r = ctx.ler_ref(caminho)
        return {"defeitos": [], "recusou": True,
                "extra": {"ok": False, "erro": r.get("erro")}}
    r = ctx.ler_cand(str(caminho))
    if forma == "diretorio":
        ok = bool(r.get("diretorio")) and bool(r.get("conteudo")) and not r.get("erro")
        return {"defeitos": [], "recusou": recusou(r),
                "extra": {"ok": ok, "entradas": r.get("linhas_total")}}
    ok = (r.get("erro") == "não existe" and r.get("existe_ate") == str(esperado)
          and bool(r.get("la_tem")))
    return {"defeitos": [], "recusou": recusou(r),
            "extra": {"ok": ok, "existe_ate": r.get("existe_ate"),
                      "la_tem": len(r.get("la_tem") or []), "parecidos": r.get("parecidos")}}


# ============================================================ medir
def medir(fn, *, curto: str, frio: bool, reps: int = REPETICOES) -> dict:
    """Roda `fn(ctx)` `reps` vezes. A primeira conta chamadas, bytes e defeitos; todas dão
    tempo. `frio`: o cache de índice da candidata é esvaziado antes de cada repetição."""
    primeira, tempos = None, []
    for i in range(reps):
        if frio:
            leitura.esvazia_cache()
        ctx = Ctx(curto)
        try:
            out = fn(ctx)
        except Exception as e:                                        # noqa: BLE001
            out = {"defeitos": [f"excecao: {type(e).__name__}: {e}"], "recusou": True,
                   "extra": {"excecao": True}}
        tempos += ctx.tempos
        if i == 0:
            primeira = {"chamadas": ctx.chamadas, "servidos": ctx.servidos,
                        "lidos": ctx.cont.lidos, **out}
        if primeira["extra"].get("excecao"):
            break
    primeira["tempos"] = tempos
    return primeira


def _linha(tarefa: str, arq, tool: str, estado: str, m: dict) -> dict:
    return {"tarefa": tarefa, "arquivo": arq.nome, "tipo": arq.tipo, "faixa": arq.faixa,
            "bytes": arq.bytes, "tool": tool, "estado": estado, "chamadas": m["chamadas"],
            "servidos": m["servidos"], "lidos": m["lidos"], "tempos": m["tempos"],
            "defeitos": m["defeitos"], "recusou": m["recusou"], "extra": dict(m["extra"])}


def par(linhas: list, tarefa: str, arq, fn_ref, fn_cand, *, quente: bool = True) -> None:
    """A referência uma vez (não tem cache: frio e quente são o mesmo); a candidata a frio e,
    se `quente`, de novo com o cache cheio. A recusa nova sai da comparação das duas."""
    mr = medir(fn_ref, curto=arq.nome, frio=False)
    linhas.append(_linha(tarefa, arq, "ref", "unico", mr))
    mc = medir(fn_cand, curto=arq.nome, frio=True)
    mc["extra"]["recusa_nova"] = bool(mc["recusou"] and not mr["recusou"])
    linhas.append(_linha(tarefa, arq, "cand", "frio" if quente else "unico", mc))
    if quente:
        mq = medir(fn_cand, curto=arq.nome, frio=False)
        mq["extra"]["recusa_nova"] = bool(mq["recusou"] and not mr["recusou"])
        linhas.append(_linha(tarefa, arq, "cand", "quente", mq))


def _fixture_arq(nome: str, caminho: Path, texto: bool = False):
    dados = Path(caminho).read_bytes()
    return _corpus.Arquivo(nome=f"fixture:{nome}", caminho=Path(caminho), origem="fixture",
                           tipo=f"fix:{nome}", faixa=_corpus.faixa_de(len(dados)),
                           bytes=len(dados), sha256=_corpus.sha256_bytes(dados), texto=texto)


def coleta(c: _corpus.Corpus) -> tuple[list, list]:
    """Roda T1–T7 e devolve (linhas de medida, T3 que não se aplicam)."""
    linhas, sem_t3 = [], []
    for arq in c.arquivos:
        orc = Oraculo(arq.caminho)
        par(linhas, "T1", arq, lambda x, a=arq, o=orc: t1("ref", x, a, o),
            lambda x, a=arq, o=orc: t1("cand", x, a, o))
        if arq.bytes > LIMIAR_T2_T3:
            par(linhas, "T2", arq, lambda x, a=arq, o=orc: t2("ref", x, a, o),
                lambda x, a=arq, o=orc: t2("cand", x, a, o))
            item, motivo = escolhe_t3(arq, orc)
            if item is None:
                sem_t3.append({"arquivo": arq.nome, "motivo": motivo})
            else:
                par(linhas, "T3", arq, lambda x, a=arq, o=orc, i=item: t3("ref", x, a, o, i),
                    lambda x, a=arq, o=orc, i=item: t3("cand", x, a, o, i))
        if arq.bytes <= MAX_T4:
            par(linhas, "T4", arq, lambda x, a=arq, o=orc: t4("ref", x, a, o),
                lambda x, a=arq, o=orc: t4("cand", x, a, o), quente=False)
    # T5: o arquivo muda entre a página 1 e a 2.
    arq = _fixture_arq("mudanca", c.fixtures["mudanca"])
    par(linhas, "T5", arq, lambda x: t5("ref", x, arq, None), lambda x: t5("cand", x, arq, None),
        quente=False)
    # T6: borda.
    for caso in ("linha_longa", "binario", "vazio"):
        arq = _fixture_arq(caso, c.fixtures[caso])
        orc = Oraculo(arq.caminho)
        par(linhas, "T6", arq, lambda x, a=arq, o=orc, k=caso: t6("ref", x, a, o, k),
            lambda x, a=arq, o=orc, k=caso: t6("cand", x, a, o, k), quente=False)
    # T7: caminho errado.
    for forma, caminho in c.arvore_erros.items():
        arq = _corpus.Arquivo(nome=f"erro:{forma}", caminho=caminho, origem="fixture",
                              tipo=forma, faixa="-", bytes=0, sha256="")
        esperado = c.arvore_esperado[forma]
        par(linhas, "T7", arq, lambda x, f=forma, p=caminho, e=esperado: t7("ref", x, f, p, e),
            lambda x, f=forma, p=caminho, e=esperado: t7("cand", x, f, p, e), quente=False)
    return linhas, sem_t3


# ============================================================ os dez critérios (§16.5)
def _soma(linhas, tarefa, tool, estado, campo):
    total = 0
    for x in linhas:
        if x["tarefa"] == tarefa and x["tool"] == tool and x["estado"] == estado:
            total += x["extra"][campo] if campo in x["extra"] else x[campo]
    return total


def _razao(c, r):
    if r == 0:
        return None if c == 0 else math.inf
    return c / r


def _fr(x) -> str:
    if x is None:
        return "-"
    return "inf" if x == math.inf else f"{x:.4f}"


def _n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def _instancias(linhas, tarefa):
    """[(ref, cand a frio, cand a quente)] por arquivo, para T2 e T3."""
    idx = {(x["arquivo"], x["tool"], x["estado"]): x for x in linhas if x["tarefa"] == tarefa}
    for (arq, tool, estado), ref in idx.items():
        if tool == "ref":
            yield ref, idx.get((arq, "cand", "frio")), idx.get((arq, "cand", "quente"))


def _criterio(n, descricao, limite, medido, violacoes) -> dict:
    return {"n": n, "descricao": descricao, "limite": limite, "medido": medido,
            "passou": not violacoes, "violacoes": violacoes}


def criterios(linhas: list) -> list[dict]:
    cs = []
    cand = [x for x in linhas if x["tool"] == "cand"]
    # 1. defeitos silenciosos da candidata
    defs = [(x["tarefa"], x["arquivo"], d) for x in cand for d in x["defeitos"]]
    por_cat = {k: sum(1 for _t, _a, d in defs if d.startswith(k + ":")) for k in CATEGORIAS}
    cs.append(_criterio(1, "defeitos silenciosos da candidata: zero", "0",
                        f"{len(defs)} ({', '.join(f'{k} {v}' for k, v in por_cat.items() if v) or 'nenhum'})",
                        [f"{t} {a}: {d}" for t, a, d in defs]))
    # 2. T1 fecha a soma da §6 em todo arquivo do corpus
    abertos = sorted({x["arquivo"] for x in cand if x["tarefa"] == "T1"
                      and not x["extra"].get("soma_fecha")})
    n_t1 = len({x["arquivo"] for x in cand if x["tarefa"] == "T1"})
    cs.append(_criterio(2, "T1 fecha a soma da seção 6 em todo arquivo do corpus",
                        "todos", f"{n_t1 - len(abertos)} de {n_t1} fecham", abertos))
    # 3. recusas novas de arquivo de texto
    recusas = sorted({f"{x['tarefa']} {x['arquivo']}" for x in cand
                      if x["extra"].get("recusa_nova")})
    cs.append(_criterio(3, "recusas novas de arquivo de texto: zero", "0", str(len(recusas)),
                        recusas))
    # 4 e 5. T1, bytes servidos e chamadas, somados no corpus
    sr, sc = _soma(linhas, "T1", "ref", "unico", "servidos"), \
        _soma(linhas, "T1", "cand", "frio", "servidos")
    r4 = _razao(sc, sr)
    cs.append(_criterio(4, "T1: bytes servidos da candidata ≤ 1,05 × a referência (soma no corpus)",
                        f"≤ {LIMITE_BYTES_T1}", f"{_n(sc)} / {_n(sr)} = {_fr(r4)}",
                        [] if r4 is None or r4 <= LIMITE_BYTES_T1 else [f"razão {_fr(r4)}"]))
    cr, cc = _soma(linhas, "T1", "ref", "unico", "chamadas"), \
        _soma(linhas, "T1", "cand", "frio", "chamadas")
    r5 = _razao(cc, cr)
    cs.append(_criterio(5, "T1: chamadas da candidata ≤ 1,05 × a referência (soma no corpus)",
                        f"≤ {LIMITE_CHAMADAS_T1}", f"{_n(cc)} / {_n(cr)} = {_fr(r5)}",
                        [] if r5 is None or r5 <= LIMITE_CHAMADAS_T1 else [f"razão {_fr(r5)}"]))
    # 6. T2 e T3: chamadas e bytes ≤ referência em toda tarefa; mediana da razão < 1
    viol6, partes6 = [], []
    for tarefa in ("T2", "T3"):
        rb, rc_ = [], []
        for ref, frio, _q in _instancias(linhas, tarefa):
            if frio is None:
                continue
            if frio["chamadas"] > ref["chamadas"]:
                viol6.append(f"{tarefa} {ref['arquivo']}: chamadas {frio['chamadas']} > "
                             f"{ref['chamadas']}")
            if frio["servidos"] > ref["servidos"]:
                viol6.append(f"{tarefa} {ref['arquivo']}: bytes servidos {_n(frio['servidos'])} > "
                             f"{_n(ref['servidos'])}")
            rb.append(_razao(frio["servidos"], ref["servidos"]))
            rc_.append(_razao(frio["chamadas"], ref["chamadas"]))
        if rb:
            mb = statistics.median([x for x in rb if x is not None] or [0])
            mc = statistics.median([x for x in rc_ if x is not None] or [0])
            partes6.append(f"{tarefa}: n {len(rb)}, mediana da razão de bytes {_fr(mb)}, "
                           f"de chamadas {_fr(mc)}")
            if not mb < 1:
                viol6.append(f"{tarefa}: mediana da razão de bytes servidos {_fr(mb)} não é < 1")
    cs.append(_criterio(6, "T2 e T3: chamadas e bytes servidos ≤ referência em toda tarefa, e a "
                        "mediana da razão (de bytes servidos) < 1", "≤ 1 por tarefa; mediana < 1",
                        "; ".join(partes6) + f"; {len(viol6)} violação(ões)", viol6))
    # 7. T4: bytes servidos da segunda leitura (somados)
    s4r, s4c = _soma(linhas, "T4", "ref", "unico", "segunda"), \
        _soma(linhas, "T4", "cand", "unico", "segunda")
    ref_t4 = {x["arquivo"]: x for x in linhas if x["tarefa"] == "T4" and x["tool"] == "ref"}
    por_arquivo = sum(1 for x in cand if x["tarefa"] == "T4"
                      and x["extra"]["segunda"] > ref_t4[x["arquivo"]]["extra"]["segunda"])
    n_t4 = len(ref_t4)
    cs.append(_criterio(7, "T4: bytes servidos da segunda leitura ≤ a referência (soma no corpus)",
                        "≤ 1", f"{_n(s4c)} / {_n(s4r)} = {_fr(_razao(s4c, s4r))}; "
                        f"{por_arquivo} de {n_t4} arquivos acima da referência, um a um",
                        [] if s4c <= s4r else [f"segunda leitura {_n(s4c)} > {_n(s4r)}"]))
    # 8. I/O em bytes lidos
    viol8, partes8 = [], []
    lr = _soma(linhas, "T1", "ref", "unico", "lidos")
    lf, lq = _soma(linhas, "T1", "cand", "frio", "lidos"), \
        _soma(linhas, "T1", "cand", "quente", "lidos")
    rf, rq = _razao(lf, lr), _razao(lq, lr)
    partes8.append(f"T1 frio {_n(lf)} / {_n(lr)} = {_fr(rf)}; T1 quente {_n(lq)} / {_n(lr)} = "
                   f"{_fr(rq)}")
    if rf is not None and rf > LIMITE_IO_T1_FRIO:
        viol8.append(f"T1 a frio: razão {_fr(rf)} > {LIMITE_IO_T1_FRIO}")
    if rq is not None and rq > LIMITE_IO_T1_QUENTE:
        viol8.append(f"T1 a quente: razão {_fr(rq)} > {LIMITE_IO_T1_QUENTE}")
    for tarefa in ("T2", "T3"):
        n = pior_f = pior_q = 0
        pf, pq = 0.0, 0.0
        for ref, frio, quente in _instancias(linhas, tarefa):
            if frio is None or quente is None:
                continue
            n += 1
            f, q = _razao(frio["lidos"], ref["lidos"]), _razao(quente["lidos"], ref["lidos"])
            if f is not None:
                pf = max(pf, f)
                if f > LIMITE_IO_T23_FRIO:
                    pior_f += 1
                    viol8.append(f"{tarefa} {ref['arquivo']} a frio: {_n(frio['lidos'])} / "
                                 f"{_n(ref['lidos'])} = {_fr(f)} > {LIMITE_IO_T23_FRIO}")
            if q is not None:
                pq = max(pq, q)
                if q > LIMITE_IO_T23_QUENTE:
                    pior_q += 1
                    viol8.append(f"{tarefa} {ref['arquivo']} a quente: {_n(quente['lidos'])} / "
                                 f"{_n(ref['lidos'])} = {_fr(q)} > {LIMITE_IO_T23_QUENTE}")
        partes8.append(f"{tarefa}: n {n}, pior razão a frio {_fr(pf)} ({pior_f} acima de "
                       f"{LIMITE_IO_T23_FRIO}), a quente {_fr(pq)} ({pior_q} acima de "
                       f"{LIMITE_IO_T23_QUENTE})")
    cs.append(_criterio(8, "I/O em bytes lidos: T1 frio ≤ 2,1 × e quente ≤ 1,05 × (soma); T2 e T3 "
                        "frio ≤ 2 × e quente ≤ referência em toda tarefa",
                        "2,1 / 1,05 ; 2 / 1", "; ".join(partes8), viol8))
    # 9. T7
    t7c = [x for x in cand if x["tarefa"] == "T7"]
    viol9 = [f"{x['tipo']}: {json.dumps(x['extra'], ensure_ascii=False)}" for x in t7c
             if not x["extra"].get("ok")]
    cs.append(_criterio(9, "T7: toda forma de erro de caminho devolve existe_ate e la_tem não "
                        "vazio quando o ancestral existe (e o diretório vira listagem)", "4 de 4",
                        f"{len(t7c) - len(viol9)} de {len(t7c)}", viol9))
    # 10. T5 e T6
    t5c = [x for x in cand if x["tarefa"] == "T5"]
    t6c = [x for x in cand if x["tarefa"] == "T6"]
    viol10 = ["T5: a página 2 não sinalizou `mudou`" for x in t5c
              if not x["extra"].get("sinalizou")]
    viol10 += [f"T6 {x['tipo']}: {json.dumps(x['extra'], ensure_ascii=False)}" for x in t6c
               if not x["extra"].get("ok")]
    cs.append(_criterio(10, "T5 sinaliza `mudou`; T6 recusa o binário, devolve `linha_longa` na "
                        "linha longa e `fim do arquivo` no vazio", "tudo",
                        f"T5 {sum(1 for x in t5c if x['extra'].get('sinalizou'))} de {len(t5c)}; "
                        f"T6 {sum(1 for x in t6c if x['extra'].get('ok'))} de {len(t6c)}",
                        viol10))
    return cs


# ============================================================ o relatório
def _mediana_p95(tempos: list[float]) -> tuple[float, float]:
    if not tempos:
        return 0.0, 0.0
    o = sorted(tempos)
    return statistics.median(o) * 1000, o[min(len(o) - 1, math.ceil(0.95 * len(o)) - 1)] * 1000


def _tabela(linhas: list, tarefa: str, campo_servidos: str = "servidos") -> list[str]:
    """Uma linha por tipo, com as duas tools e a razão; a última, o total da tarefa."""
    rows = [x for x in linhas if x["tarefa"] == tarefa]
    if not rows:
        return [f"{tarefa}: nenhum arquivo no corpus"]
    tipos = sorted({x["tipo"] for x in rows})
    cab = (f"{'tipo':<18}{'n':>4} | {'cham ref':>9}{'cand':>8}{'razão':>7} | "
           f"{'serv ref':>11}{'cand':>11}{'razão':>7} | {'lidos-frio ref':>15}{'cand':>11}"
           f"{'razão':>7} | {'lidos-quente ref':>17}{'cand':>11}{'razão':>7} | "
           f"{'t50 ms ref':>11}{'cand':>8}")
    out = [cab]

    def linha(nome, sel):
        ref = [x for x in sel if x["tool"] == "ref"]
        frio = [x for x in sel if x["tool"] == "cand" and x["estado"] in ("frio", "unico")]
        quente = [x for x in sel if x["tool"] == "cand" and x["estado"] in ("quente", "unico")]

        def s(xs, campo):
            return sum(x["extra"][campo] if campo in x["extra"] else x[campo] for x in xs)

        tr = _mediana_p95([t for x in ref for t in x["tempos"]])[0]
        tc = _mediana_p95([t for x in frio for t in x["tempos"]])[0]
        cr_, cc_ = s(ref, "chamadas"), s(frio, "chamadas")
        sr_, sc_ = s(ref, campo_servidos), s(frio, campo_servidos)
        fr_, fc_ = s(ref, "lidos"), s(frio, "lidos")
        qr_, qc_ = fr_, s(quente, "lidos")
        return (f"{nome:<18}{len(ref):>4} | {_n(cr_):>9}{_n(cc_):>8}{_fr(_razao(cc_, cr_)):>7} | "
                f"{_n(sr_):>11}{_n(sc_):>11}{_fr(_razao(sc_, sr_)):>7} | "
                f"{_n(fr_):>15}{_n(fc_):>11}{_fr(_razao(fc_, fr_)):>7} | "
                f"{_n(qr_):>17}{_n(qc_):>11}{_fr(_razao(qc_, qr_)):>7} | {tr:>11.2f}{tc:>8.2f}")

    for t in tipos:
        out.append(linha(t, [x for x in rows if x["tipo"] == t]))
    out.append(linha("TOTAL", rows))
    return out


def _tabela_curta(linhas: list, tarefa: str) -> list[str]:
    out = []
    for x in linhas:
        if x["tarefa"] == tarefa and x["tool"] == "ref":
            c = next(y for y in linhas if y["tarefa"] == tarefa and y["arquivo"] == x["arquivo"]
                     and y["tool"] == "cand")
            out.append(f"{x['arquivo']:<26} ref: {x['chamadas']} cham, {_n(x['servidos'])} B "
                       f"servidos, {_n(x['lidos'])} B lidos, "
                       f"{json.dumps(x['extra'], ensure_ascii=False)}")
            out.append(f"{'':<26} cand: {c['chamadas']} cham, {_n(c['servidos'])} B servidos, "
                       f"{_n(c['lidos'])} B lidos, {json.dumps(c['extra'], ensure_ascii=False)}")
    return out


def texto_relatorio(c: _corpus.Corpus, linhas: list, sem_t3: list, cs: list, dur: float) -> str:
    L = []
    add = L.append
    add("=" * 100)
    add("BENCH DE HOMOLOGAÇÃO — ler_arquivo contra read_file (spec ler-arquivo §16, card #3263)")
    add("=" * 100)
    repo = [a for a in c.arquivos if a.origem == "repo"]
    add(f"\nCORPUS: {len(repo)} arquivos versionados + "
        f"{len(c.arquivos) - len(repo)} fixtures de texto (+ binário, vazio, mudança e a árvore "
        f"de T7). Faixas em KB = 1.000 bytes. Duração do bench: {dur:.1f} s.")
    add("\n-- corpus (sha256 do conteúdo, bytes, faixa, caminho)")
    for a in c.arquivos:
        add(f"{a.sha256}  {a.bytes:>10}  {a.faixa:<12} {a.nome}")
    add("\n-- células do corpus (extensão/faixa: arquivos que entraram, máximo 5)")
    add("  " + "; ".join(f"{k} {v}" for k, v in c.celulas.items()))
    add(f"-- células VAZIAS ({len(c.celulas_vazias)}): "
        + (", ".join(c.celulas_vazias) if c.celulas_vazias else "nenhuma"))
    if sem_t3:
        add(f"-- T3 não se aplica a {len(sem_t3)} arquivo(s) acima de 40 KB: "
            + "; ".join(f"{x['arquivo']} ({x['motivo']})" for x in sem_t3[:15])
            + (" …" if len(sem_t3) > 15 else ""))
    nomes = {"T1": "T1 inteira", "T2": "T2 trecho (200 linhas, arquivo > 40 KB)",
             "T3": "T3 estrutura (item do sumário, arquivo com analisador > 40 KB)"}
    for t in ("T1", "T2", "T3"):
        add(f"\n== {nomes[t]} — referência vs candidata (bytes servidos = JSON do retorno; "
            f"lidos = bytes pedidos ao read; razão = cand/ref)")
        L.extend(_tabela(linhas, t))
    add("\n== T4 releitura — bytes servidos da SEGUNDA leitura (todo arquivo até 40 KB)")
    L.extend(_tabela(linhas, "T4", campo_servidos="segunda"))
    add("\n== T5 mudou (a página 1, o arquivo muda, a página 2)")
    L.extend(_tabela_curta(linhas, "T5"))
    add("\n== T6 borda (linha longa, binário, vazio)")
    L.extend(_tabela_curta(linhas, "T6"))
    add("\n== T7 caminho errado (uma chamada por forma)")
    L.extend(_tabela_curta(linhas, "T7"))
    add("\n== tempo por chamada, em ms (mediana / p95 de 5 repetições; só relatado)")
    for t in ("T1", "T2", "T3", "T4", "T5", "T6", "T7"):
        partes = []
        for tool in ("ref", "cand"):
            ts = [s for x in linhas if x["tarefa"] == t and x["tool"] == tool for s in x["tempos"]]
            m, p = _mediana_p95(ts)
            partes.append(f"{tool} {m:.2f} / {p:.2f}")
        add(f"  {t}: " + "   ".join(partes))
    add("\n== defeitos silenciosos (§16.4.4) por categoria")
    for tool, nome in (("ref", "referência (informativo)"), ("cand", "candidata (critério 1)")):
        defs = [d for x in linhas if x["tool"] == tool for d in x["defeitos"]]
        add(f"  {nome}: {len(defs)} — " + (", ".join(
            f"{k} {sum(1 for d in defs if d.startswith(k + ':'))}" for k in CATEGORIAS
            if any(d.startswith(k + ':') for d in defs)) or "nenhum"))
    add("\n== OS DEZ CRITÉRIOS (§16.5) — todas as linhas, em toda a árvore")
    for k in cs:
        add(f"{k['n']:>2}. [{'PASSOU' if k['passou'] else 'FALHOU'}] {k['descricao']}")
        add(f"      limite: {k['limite']}   medido: {k['medido']}")
        if not k["passou"]:
            for v in k["violacoes"][:12]:
                add(f"      - {v}")
            if len(k["violacoes"]) > 12:
                add(f"      … e mais {len(k['violacoes']) - 12} (todas no JSON)")
    ok = all(k["passou"] for k in cs)
    add("\n" + "=" * 100)
    add(f"RESULTADO: {'PASSOU' if ok else 'FALHOU'} — "
        f"{sum(1 for k in cs if k['passou'])} de {len(cs)} critérios. Sai {0 if ok else 1}.")
    add("=" * 100)
    return "\n".join(L)


def caminho_saida() -> Path:
    """BENCH_LEITURA_SAIDA; senão var/tmp/<PF_ORDEM_ID>/ da instância, se existe; senão tmp."""
    explicito = os.environ.get("BENCH_LEITURA_SAIDA")
    if explicito:
        return Path(explicito)
    ordem = os.environ.get("PF_ORDEM_ID")
    if ordem:
        d = Path("/srv/platafirma/casa/var/tmp") / ordem
        if d.is_dir():
            return d / "bench-leitura.json"
    return Path(tempfile.gettempdir()) / "bench-leitura.json"


def _sem_tempos(linhas: list) -> list:
    out = []
    for x in linhas:
        m, p = _mediana_p95(x["tempos"])
        y = {k: v for k, v in x.items() if k != "tempos"}
        y.update(tempo_mediana_ms=round(m, 4), tempo_p95_ms=round(p, 4),
                 tempo_chamadas=len(x["tempos"]))
        out.append(y)
    return out


def rodar(*, raiz: Path = _corpus.RAIZ, grava: bool = True) -> dict:
    """Monta o corpus em diretório temporário, roda T1–T7, aplica os critérios e (se `grava`)
    escreve o JSON. Devolve o relatório: `texto`, `criterios`, `passou`, `saida`."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="bench-leitura-") as tmp:
        antigo = poda.DERRAME
        poda.DERRAME = Path(tmp) / "derrame"            # a poda derrama e guarda base de diff
        try:
            c = _corpus.monta(Path(tmp) / "corpus", raiz)
            leitura.esvazia_cache()
            linhas, sem_t3 = coleta(c)
        finally:
            poda.DERRAME = antigo
            leitura.esvazia_cache()
    cs = criterios(linhas)
    dur = time.perf_counter() - t0
    texto = texto_relatorio(c, linhas, sem_t3, cs, dur)
    ok = all(k["passou"] for k in cs)
    saida = None
    if grava:
        saida = caminho_saida()
        try:
            saida.parent.mkdir(parents=True, exist_ok=True)
            saida.write_text(json.dumps({
                "spec": "ler-arquivo §16", "passou": ok, "duracao_s": round(dur, 2),
                "limites": {"bytes_t1": LIMITE_BYTES_T1, "chamadas_t1": LIMITE_CHAMADAS_T1,
                            "io_t1_frio": LIMITE_IO_T1_FRIO, "io_t1_quente": LIMITE_IO_T1_QUENTE,
                            "io_t23_frio": LIMITE_IO_T23_FRIO,
                            "io_t23_quente": LIMITE_IO_T23_QUENTE},
                "corpus": [{"caminho": a.nome, "sha256": a.sha256, "bytes": a.bytes,
                            "faixa": a.faixa, "tipo": a.tipo, "origem": a.origem}
                           for a in c.arquivos],
                "celulas": c.celulas, "celulas_vazias": c.celulas_vazias,
                "t3_nao_se_aplica": sem_t3, "criterios": cs, "linhas": _sem_tempos(linhas),
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError as e:
            texto += f"\n(JSON não gravado em {saida}: {e})"
            saida = None
        else:
            texto += f"\nJSON: {saida}"
    return {"texto": texto, "criterios": cs, "passou": ok, "saida": saida, "linhas": linhas}


def main() -> int:
    r = rodar()
    print(r["texto"])
    return 0 if r["passou"] else 1


if __name__ == "__main__":
    sys.exit(main())
