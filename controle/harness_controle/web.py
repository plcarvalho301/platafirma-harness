# web — a tela: le controle/estado.json (nunca executa verbo em resposta a
# GET das rotas do agregador), duas acoes (POST) que chamam verbo e nada alem
# dele.
# capacidade: expediente
# dono: claudinho-TI
"""LOTE 3 do card #390. Starlette + uvicorn (mesmo stack de ops-server/
osint-server em platafirma-core — precedente local, nao stack novo). Sem
framework de front, sem build, sem JavaScript — mesma regua dos wireframes.

Exclusao dura: cloudflared e oauth2-proxy nunca sao alvo aceito por
/acoes/reiniciar, mesmo se alguem forjar o POST direto sem passar pela tela.

/feito e leitura derivada (spec: "sem estado proprio"). Commits vem de
`git log` direto — nao ha verbo em bin/ pra isso hoje, e e leitura pura,
sem escrita e sem side effect, entao e a excecao deliberada e estreita a
regra "verbo por tras" (que existe pra nao duplicar ACAO, nao pra proibir
todo `git log`). Cards fechados vem de `tarefas listar-tudo` (verbo
existente, sem --json — fora do LOTE 1 — entao le o texto tabulado mesmo).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route

from . import render
from .agregador import ESTADO_PATH
from .estado_leitura import carregar_estado
from .verbos import BIN

REPO_HARNESS = Path(__file__).resolve().parents[3]
TOKENS_PATH = Path(
    os.environ.get(
        "TOKENS_CSS_PATH",
        str(REPO_HARNESS.parent / "platafirma-arquitetura" / "design" / "tokens.css"),
    )
)

TIPOS_VALIDOS = {"decisao", "resposta", "pedido", "minuta", "demanda", "handoff"}
PF_CADEIRA_TELA = os.environ.get("PF_CADEIRA_TELA", "claudinho-TI")
TAREFAS_PROJETO_PADRAO = os.environ.get("TAREFAS_PROJETO_PADRAO", "46")


# --- rotas de leitura --------------------------------------------------


async def recepcao(request):
    estado = carregar_estado(ESTADO_PATH)
    return HTMLResponse(render.render_recepcao(estado))


async def cadeira(request):
    slug = request.path_params["slug"]
    estado = carregar_estado(ESTADO_PATH)
    return HTMLResponse(render.render_cadeira(estado, slug))


def _commits_por_dia(limite_dias: int = 14) -> dict[str, list[dict]]:
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_HARNESS), "log", f"--since={limite_dias} days ago",
             "--date=short", "--format=%ad%x09%h%x09%s"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except OSError:
        return {}
    if r.returncode != 0:
        return {}
    por_dia: dict[str, list[dict]] = {}
    for linha in r.stdout.splitlines():
        partes = linha.split("\t", 2)
        if len(partes) != 3:
            continue
        data, sha, msg = partes
        por_dia.setdefault(data, []).append({"sha": sha, "mensagem": msg})
    return por_dia


def _tarefas_texto(argv: list[str], timeout: float = 20) -> list[str]:
    caminho = BIN / argv[0]
    try:
        r = subprocess.run([str(caminho), *argv[1:]], capture_output=True, text=True,
                            timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    return r.stdout.splitlines()


def _monta_feito(limite_dias: int = 14) -> list[dict]:
    commits_por_dia = _commits_por_dia(limite_dias)
    cards_fechados = []
    for linha in _tarefas_texto(["tarefas", "listar-tudo", TAREFAS_PROJETO_PADRAO]):
        partes = linha.split("\t", 2)
        if len(partes) != 3:
            continue
        id_, marca, titulo = partes
        if marca.strip() == "x":
            cards_fechados.append({"id": id_, "titulo": titulo})

    dias = sorted(commits_por_dia, reverse=True)
    resultado = [
        {"data": d, "commits": commits_por_dia[d], "cards": []}
        for d in dias
    ]
    # Cards fechados nao tem data na saida atual de `tarefas` (sem --json,
    # sem campo de data) — aparecem soltos, nao agrupados por dia, ate um
    # follow-up dar --json a `listar-tudo` com a data de fechamento.
    if cards_fechados:
        resultado.append({"data": "cards fechados (sem data disponível hoje)",
                           "commits": [], "cards": cards_fechados})
    return resultado


async def feito(request):
    # Leitura derivada, sem estado proprio — nao passa pelo agregador; e uma
    # navegacao deliberada, nao o loop de revalidacao de 60s dos 4 blocos.
    # _monta_feito() bloqueia (git log + tarefas listar-tudo) — threadpool,
    # mesma razao das duas acoes abaixo.
    dias = await run_in_threadpool(_monta_feito)
    return HTMLResponse(render.render_feito(dias))


# --- estatico ------------------------------------------------------------


async def tokens_css(request):
    if not TOKENS_PATH.is_file():
        return PlainTextResponse("tokens.css nao encontrado nesta instancia", status_code=404)
    return PlainTextResponse(TOKENS_PATH.read_text(encoding="utf-8"), media_type="text/css")


# --- acoes (POST) — cada uma chama o verbo e nada alem dele -----------------


def _run_fila_enviar(destinatario: str, tipo: str, assunto: str, corpo: str):
    env = dict(os.environ)
    env["PF_CADEIRA"] = PF_CADEIRA_TELA
    caminho = BIN / "fila_streams.py"
    return subprocess.run(
        [str(caminho), "enviar", destinatario, "--tipo", tipo, "--assunto", assunto],
        input=corpo, capture_output=True, text=True, env=env, timeout=15, check=False,
    )


async def despachar_recado(request):
    form = await request.form()
    destinatario = (form.get("destinatario") or "").strip()
    tipo = (form.get("tipo") or "").strip()
    assunto = (form.get("assunto") or "").strip()
    corpo = (form.get("corpo") or "").strip()

    if not destinatario or tipo not in TIPOS_VALIDOS or not assunto or not corpo:
        return PlainTextResponse("campos obrigatorios ausentes ou tipo invalido", status_code=400)

    # subprocess.run bloqueia — nunca direto num handler async (travaria o
    # event loop, e com ele as outras rotas, pelos ate 15s do timeout).
    try:
        r = await run_in_threadpool(_run_fila_enviar, destinatario, tipo, assunto, corpo)
    except (OSError, subprocess.TimeoutExpired) as e:
        return PlainTextResponse(f"falha ao despachar: {e}", status_code=502)
    if r.returncode != 0:
        return PlainTextResponse(f"falha ao despachar: {r.stderr.strip()}", status_code=502)
    return RedirectResponse("/#caixas", status_code=303)


# Exclusao dura (spec §5): estes dois nunca sao alvo de restart pela tela,
# mesmo que o POST chegue direto sem passar pelos botoes desabilitados —
# reiniciar por dentro serraria o galho em que a propria tela esta pendurada.
ALVOS_EXCLUIDOS_RESTART = {"cloudflared", "oauth2-proxy"}


def _run_infra_restart(alvo: str):
    caminho = BIN / "infra"
    return subprocess.run([str(caminho), "restart", alvo], capture_output=True, text=True,
                           timeout=15, check=False)


async def reiniciar(request):
    form = await request.form()
    alvo = (form.get("alvo") or "").strip()
    if not alvo:
        return PlainTextResponse("alvo obrigatorio", status_code=400)
    if alvo in ALVOS_EXCLUIDOS_RESTART:
        return PlainTextResponse(f"{alvo} nao e reiniciavel por esta tela (sustenta a propria tela)",
                                  status_code=403)

    try:
        r = await run_in_threadpool(_run_infra_restart, alvo)
    except (OSError, subprocess.TimeoutExpired) as e:
        return PlainTextResponse(f"falha ao reiniciar: {e}", status_code=502)
    if r.returncode != 0:
        return PlainTextResponse(f"falha ao reiniciar: {r.stderr.strip()}", status_code=502)
    return RedirectResponse("/#sinal", status_code=303)


# --- app -------------------------------------------------------------------


def cria_app() -> Starlette:
    rotas = [
        Route("/", recepcao),
        Route("/cadeira/{slug}", cadeira),
        Route("/feito", feito),
        Route("/estatico/tokens.css", tokens_css),
        Route("/acoes/despachar-recado", despachar_recado, methods=["POST"]),
        Route("/acoes/reiniciar", reiniciar, methods=["POST"]),
    ]
    return Starlette(routes=rotas)


app = cria_app()
