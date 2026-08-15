# web — a tela: le controle/estado.json (nunca executa verbo em resposta a
# GET das rotas do agregador), duas acoes (POST) que chamam verbo e nada alem
# dele.
# capacidade: expediente
# dono: claudinho-TI
"""LOTE 3 do card #390. Starlette + uvicorn (mesmo stack de ops-server/
osint-server em platafirma-core — precedente local, nao stack novo). Sem
framework de front e sem build: o front vem pronto do release platafirma/ui,
copiado para dentro da imagem (arq:0056) e servido por /estatico/pf-ui/.

Exclusao dura: cloudflared e oauth2-proxy nunca sao alvo aceito por
/acoes/reiniciar, mesmo se alguem forjar o POST direto sem passar pela tela.

/feito e leitura derivada (spec: "sem estado proprio"). Commits vem de
`git log` direto — nao ha verbo em bin/ pra isso hoje, e e leitura pura,
sem escrita e sem side effect, entao e a excecao deliberada e estreita a
regra "verbo por tras" (que existe pra nao duplicar ACAO, nao pra proibir
todo `git log`). Cards fechados vem de `tarefas listar-tudo --json` (card
#394 — data de fechamento por card, pra agrupar por dia e ligar a commits
que se referenciam, conforme a spec).
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import render
from .agregador import ESTADO_PATH
from .estado_leitura import carregar_estado
from .verbos import BIN, chamar

REPO_HARNESS = Path(__file__).resolve().parents[2]

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


_CARD_REF_RE = re.compile(r"#(\d+)")


def _commits_por_dia(limite_dias: int = 14) -> dict[str, list[dict]]:
    """{"AAAA-MM-DD": [{"sha","mensagem","card_ref"}, ...]} — card_ref e o
    id do card citado como "#<id>" na mensagem (nossa própria convenção de
    commit, ex. "LOTE 3 (#390): ..."), ou None se a mensagem não cita nada."""
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO_HARNESS), "log", f"--since={limite_dias} days ago",
             "--date=short", "--format=%ad%x09%h%x09%s"],
            capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
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
        m = _CARD_REF_RE.search(msg)
        por_dia.setdefault(data, []).append(
            {"sha": sha, "mensagem": msg, "card_ref": int(m.group(1)) if m else None}
        )
    return por_dia


def _cards_fechados_por_dia(limite_dias: int = 14) -> dict[str, list[dict]]:
    """{"AAAA-MM-DD": [{"id","titulo"}, ...]}, so cards fechados dentro da
    janela — lido de `tarefas listar-tudo --json` (card #394), que já
    normaliza a data-zero do Go em null pra card aberto."""
    r = chamar(["tarefas", "listar-tudo", TAREFAS_PROJETO_PADRAO, "--json"], timeout=20)
    if not r.ok or not isinstance(r.dados, list):
        return {}
    corte = datetime.now(UTC) - timedelta(days=limite_dias)
    por_dia: dict[str, list[dict]] = {}
    for card in r.dados:
        if not card.get("fechado") or not card.get("fechado_em"):
            continue
        try:
            fechado_em = datetime.fromisoformat(card["fechado_em"])
        except ValueError:
            continue
        if fechado_em < corte:
            continue
        dia = fechado_em.strftime("%Y-%m-%d")
        por_dia.setdefault(dia, []).append({"id": card["id"], "titulo": card.get("titulo") or ""})
    return por_dia


def _monta_feito(limite_dias: int = 14) -> list[dict]:
    """Agrupa por dia (data de fechamento pro card, data do commit pro
    commit) e liga card a commit por referência "#<id>" na mensagem — ligado
    aparece aninhado sob o card, nunca duplicado na lista de órfãos. Commit
    sem referência, ou que referencia um card fora da janela/não encontrado,
    é órfão de verdade."""
    commits_por_dia = _commits_por_dia(limite_dias)
    cards_por_dia = _cards_fechados_por_dia(limite_dias)

    todos_commits = [c for lista in commits_por_dia.values() for c in lista]
    ids_conhecidos = {c["id"] for lista in cards_por_dia.values() for c in lista}

    dias = sorted(set(commits_por_dia) | set(cards_por_dia), reverse=True)
    resultado = []
    for dia in dias:
        cards_dia = []
        for card in cards_por_dia.get(dia, []):
            ligados = [c for c in todos_commits if c["card_ref"] == card["id"]]
            cards_dia.append({
                "id": card["id"], "titulo": card["titulo"],
                "commits": [{"sha": c["sha"], "mensagem": c["mensagem"]} for c in ligados],
            })
        orfaos = [
            {"sha": c["sha"], "mensagem": c["mensagem"]}
            for c in commits_por_dia.get(dia, [])
            if c["card_ref"] is None or c["card_ref"] not in ids_conhecidos
        ]
        if cards_dia or orfaos:
            resultado.append({"data": dia, "cards": cards_dia, "commits": orfaos})
    return resultado


async def feito(request):
    # Leitura derivada, sem estado proprio — nao passa pelo agregador; e uma
    # navegacao deliberada, nao o loop de revalidacao de 60s dos 4 blocos.
    # _monta_feito() bloqueia (git log + tarefas listar-tudo) — threadpool,
    # mesma razao das duas acoes abaixo.
    dias = await run_in_threadpool(_monta_feito)
    return HTMLResponse(render.render_feito(dias))


# --- estatico ------------------------------------------------------------


TELA_CSS_PATH = Path(__file__).resolve().parent / "estatico" / "tela.css"


async def tela_css(request):
    if not TELA_CSS_PATH.is_file():
        return PlainTextResponse("tela.css nao encontrado nesta instancia", status_code=404)
    return PlainTextResponse(TELA_CSS_PATH.read_text(encoding="utf-8"), media_type="text/css")


# O front da PlataFirma (pf-ui.css, pf-ui.js, fontes/, versao.txt, origem.txt)
# nao tem handler proprio: e diretorio servido inteiro, porque as fontes sao
# referenciadas pelo proprio CSS por caminho relativo (./fontes/...) e precisam
# responder sob a mesma base. StaticFiles e do proprio starlette — sem stack
# novo, sem dependencia nova.
#
# check_dir=False de proposito: o diretorio so existe DENTRO da imagem (o
# Dockerfile o preenche por COPY --from do release). No clone de
# desenvolvimento ele nao existe, e a escolha e 404 na rota em vez de derrubar
# o app inteiro no import — o resto da tela nao depende disto pra responder.


# --- acoes (POST) — cada uma chama o verbo e nada alem dele -----------------


def _run_fila_enviar(destinatario: str, tipo: str, assunto: str, corpo: str):
    env = dict(os.environ)
    env["PF_CADEIRA"] = PF_CADEIRA_TELA
    caminho = BIN / "fila_streams.py"
    return subprocess.run(
        [str(caminho), "enviar", destinatario, "--tipo", tipo, "--assunto", assunto],
        input=corpo, capture_output=True, text=True, encoding="utf-8", env=env, timeout=15, check=False,
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
                           encoding="utf-8", timeout=15, check=False)


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


def cria_app(pf_ui_dir: Path | None = None) -> Starlette:
    """`pf_ui_dir` existe pro teste poder apontar um diretorio de mentira: o
    StaticFiles resolve o diretorio no __init__, entao monkeypatch depois de
    montado nao pega. Em producao fica no default, que e o que veio na imagem."""
    rotas = [
        Route("/", recepcao),
        Route("/cadeira/{slug}", cadeira),
        Route("/feito", feito),
        Route("/estatico/tela.css", tela_css),
        Mount(
            render.PF_UI_BASE,
            app=StaticFiles(
                directory=render.PF_UI_DIR if pf_ui_dir is None else pf_ui_dir,
                check_dir=False,
            ),
            name="pf-ui",
        ),
        Route("/acoes/despachar-recado", despachar_recado, methods=["POST"]),
        Route("/acoes/reiniciar", reiniciar, methods=["POST"]),
    ]
    return Starlette(routes=rotas)


app = cria_app()
