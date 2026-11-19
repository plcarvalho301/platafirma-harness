"""As três coletas que o descanso dispara em segundo plano (regra 30 da F4269, t1 da S4335).

  encerramento  o evento `sessao_encerrada`, desfecho `descanso` (substitui o carimbo mem:<cadeira> da casa velha)
  observacoes   cada observação que a cadeira entregou ao descanso vira uma mensagem de tipo afirmacao, com a
                própria cadeira em `destinatario` e, quando a observação não diz outro, em `quem`; emite
                `coleta_observacoes` com quantas gravou e quantas recusou
  arestas       o que a fita puxou de fora da cadeira: cada tool chamada na sessão cujo `# dono:` no cabeçalho do
                bin é outra cadeira vira uma mensagem da porta à cadeira, com o para quê da tool no enunciado, os
                giros em `apoio` e as pontas que têm ficha em `etiqueta`; emite `coleta_arestas`

A categoria do caderno (lição, preferência do dono, premissa, aresta) não se grava: não tem ficha e não é etiqueta
(decisões 5271 e 5274). O que distingue uma coleta da outra é a forma: a preferência do dono leva o dono em `quem` e a
conversa em `cita`, a lição leva o caso em `apoio`, a aresta leva as pontas em `etiqueta`. Os giros auto-relatados da
casa velha não entram: giro é telemetria, não evento da árvore. Cada coleta roda sozinha: a que falha emite
`coleta_falhou` com o nome e o erro, e as outras seguem.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import oplog  # noqa: E402
from descanso import eventos  # noqa: E402
from descanso.publicar import Recusada, SemDestino, fichario_do_ambiente, publicar  # noqa: E402

NOMES = ("encerramento", "observacoes", "arestas")
QUEM_DA_PORTA = "porta"
TIPO_DA_COLETA = "afirmacao"
APOIO_MAX = 20
_CAMPO = {"dono": re.compile(r"^#\s*dono:\s*(\S+)", re.MULTILINE),
          "use_para": re.compile(r"^#\s*use para:\s*(.+)$", re.MULTILINE)}


def chave_da_cadeira(cadeira: str) -> str:
    """A chave de ficha da cadeira no fichário (persona:<slug>)."""
    return f"persona:{cadeira}"


def _bin() -> Path:
    return Path(os.environ.get("PF_BIN") or (_LIB.parent / "bin"))


def cabecalho_da_tool(tool: str, bin_dir: Path | None = None) -> dict:
    """`dono` e `use_para` do cabeçalho do bin da tool; {} quando não há bin."""
    if not tool or "/" in tool or tool.startswith("."):
        return {}
    try:
        cabeca = (Path(bin_dir or _bin()) / tool).read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return {}
    return {c: m.group(1).strip() for c, rx in _CAMPO.items() if (m := rx.search(cabeca))}


def _emitir(ctx: dict, evento: str, **campos) -> bool:
    return oplog.emitir({"tool": eventos.TOOL, "evento": evento, "sessao_id": ctx["sessao_id"],
                         "cadeira": ctx["cadeira"], "sobre": ctx["sessao_id"], "correlacao": ctx["sujeito"],
                         **campos}, diretorio_=ctx.get("diretorio"))


def coleta_encerramento(ctx: dict) -> dict:
    ok = eventos.emitir_encerrada(ctx["sessao_id"], sujeito=ctx["sujeito"], cadeira=ctx["cadeira"],
                                  desfecho="descanso", diretorio_=ctx.get("diretorio"))
    if not ok:
        raise RuntimeError("oplog não gravou a sessao_encerrada")
    return {"desfecho": "descanso"}


def coleta_observacoes(ctx: dict) -> dict:
    gravadas = recusadas = 0
    propria = chave_da_cadeira(ctx["cadeira"])
    for obs in ctx.get("observacoes") or []:
        dado = dict(obs) if isinstance(obs, dict) else {"enunciado": str(obs)}
        dado.setdefault("quem", propria)
        dado.setdefault("destinatario", [propria])
        dado.setdefault("tipo-de-mensagem", TIPO_DA_COLETA)
        dado.setdefault("correlacao", ctx["sessao_id"])
        try:
            _, gravou = publicar(dado, ctx.get("gravador"), ctx.get("fichario"))
        except Recusada:
            recusadas += 1
            continue
        gravadas += int(gravou)
    _emitir(ctx, "coleta_observacoes", gravadas=gravadas, recusadas=recusadas)
    return {"gravadas": gravadas, "recusadas": recusadas}


def arestas_da_sessao(ctx: dict) -> dict:
    """(tool, dono) -> {use_para, apoio}: os giros da sessão em tool de outra cadeira, com o evento_id de cada um."""
    h = ctx.get("hoje") or oplog.hoje_local()
    # +1 dia: o arquivo do dia sai no fuso da máquina, e hoje_local é o fuso da porta
    leitura = oplog.ler(h - timedelta(days=2), h + timedelta(days=1), diretorio_=ctx.get("diretorio"),
                        sessao=ctx["sessao_id"])
    arestas: dict = defaultdict(lambda: {"use_para": None, "apoio": []})
    for reg in leitura:
        if reg.get("evento") not in oplog.EVENTOS_DE_GIRO:
            continue
        tool = str(reg.get("tool") or "")
        cab = cabecalho_da_tool(tool, ctx.get("bin"))
        if cab.get("dono") and cab["dono"] != ctx["cadeira"]:
            a = arestas[(tool, cab["dono"])]
            a["use_para"] = cab.get("use_para")
            if reg.get("evento_id"):
                a["apoio"].append(reg["evento_id"])
    return dict(arestas)


def coleta_arestas(ctx: dict) -> dict:
    arestas = arestas_da_sessao(ctx)
    fichario = ctx.get("fichario") or fichario_do_ambiente()
    propria = chave_da_cadeira(ctx["cadeira"])
    pontas = sorted({propria} | {chave_da_cadeira(dono) for _, dono in arestas})
    try:
        com_ficha = fichario.existentes(pontas) if arestas else set()
    except SemDestino:
        com_ficha = set()       # a etiqueta anota e não sustenta: sem fichário, a ponta fica de fora
    gravadas = recusadas = 0
    for (tool, dono), a in sorted(arestas.items()):
        para_que = f" para {a['use_para']}" if a["use_para"] else ""
        try:
            _, gravou = publicar({
                "enunciado": f"a sessão de {ctx['cadeira']} chamou {tool}, de {dono},{para_que}"
                             f" ({len(a['apoio'])} vez(es))",
                "quem": QUEM_DA_PORTA, "destinatario": [propria], "tipo-de-mensagem": TIPO_DA_COLETA,
                "correlacao": ctx["sessao_id"], "sobre": ctx["sessao_id"], "apoio": a["apoio"][:APOIO_MAX],
                "etiqueta": [p for p in (propria, chave_da_cadeira(dono)) if p in com_ficha],
            }, ctx.get("gravador"), fichario)
        except Recusada:
            recusadas += 1
            continue
        gravadas += int(gravou)
    _emitir(ctx, "coleta_arestas", arestas=len(arestas), gravadas=gravadas, recusadas=recusadas)
    return {"arestas": len(arestas), "gravadas": gravadas, "recusadas": recusadas}


COLETAS = {"encerramento": coleta_encerramento, "observacoes": coleta_observacoes, "arestas": coleta_arestas}


def rodar(ctx: dict, coletas: dict | None = None) -> dict:
    """Roda cada coleta sozinha. A que levanta vira `coleta_falhou` no oplog, e as outras seguem."""
    saida = {}
    for nome, fn in (coletas or COLETAS).items():
        try:
            saida[nome] = fn(ctx)
        except Exception as erro:  # noqa: BLE001
            saida[nome] = {"erro": repr(erro)}
            _emitir(ctx, "coleta_falhou", coleta=nome, erro=repr(erro))
    return saida


def ler_contexto(caminho: str | Path) -> dict:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))
