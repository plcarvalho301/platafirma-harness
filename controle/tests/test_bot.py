"""`bot` (card #3186): declarar, listar, rodar, desligar e caidas.

Hermético: o acervo é um dublê HTTP em 127.0.0.1:0 que implementa o subconjunto do contrato
acervo-escrita 1.1.0 que o bot chama (PUT, GET e DELETE de automacoes; POST de eventos; estado
viva, caida e planejada); `systemctl`, `tarefas`, `agente` e o job são stubs (PATH e PF_BIN); HOME,
XDG_DATA_HOME e a morada das units (PF_UNITS_DIR) são temporários, e nada sai do tmp.

Prova: a ordem fixa de declarar (uso, PUT, unit), a tabela de exit por status, a unit sempre igual ao
que o gerador devolve, o rodar que grava inicio e fim e sai com o exit do que rodou, o desligar que é
o inverso e se repete, e o caidas que abre incidente com a cadeira do dono, sem duplicar.
Não prova: o systemd nem o serviço reais da conta, nem o Postgres atrás do contrato.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT = REPO_ROOT / "bin" / "bot"
loader = SourceFileLoader("bot", str(BOT))
spec = importlib.util.spec_from_loader("bot", loader)
assert spec and spec.loader
bot = importlib.util.module_from_spec(spec)
loader.exec_module(bot)

sys.path.insert(0, str(REPO_ROOT / "lib"))
import units

CAL = "*-*-* 06:45"
SHA = "9403e59c0ffee1234567"        # o sha da release no ar (hex, como o realpath de um checkout)
ORQ = "11111111-1111-4111-8111-111111111111"   # a sessão de quem chamou
ENV_OPS = "/home/claudinho/.config/ops/env"
GERADO = "# GERADO por bot — não editar"

INSTALAR = 'UNITS=(\n  "deploy-harness/sinal.service|0644"\n  "deploy-harness/sinal.timer|0644"\n)\n'
REGISTRO = {"units": {"motor-trim.service": {}, "motor-trim.timer": {}},
            "_fora_deste_instalador": {"prior-secao.service, prior-secao.timer": "setup-prior-secao.sh — dados"}}

# --- o mundo de mentira: stubs ------------------------------------------------------------------

STUB_SYSTEMCTL = """
import json, os, sys
a = sys.argv[1:]
cmd = next(x for x in a if not x.startswith("-"))
with open(os.environ["STUB_LOG"], "a") as f:      # `show` e leitura: loga a parte, o que o bot muda continua em "systemctl"
    f.write(json.dumps({"verbo": "systemctl-show" if cmd == "show" else "systemctl", "argv": a}) + "\\n")
d = json.load(open(os.environ["STUB_SYSTEMD"]))
if d.get("quebrado"):
    print("Failed to connect to bus", file=sys.stderr); sys.exit(1)
if cmd == "list-units":
    if "--state=failed" in a:
        for u in d.get("failed", []):
            print(f"● {u} loaded failed failed x")
    else:
        for u in d.get("timers", []):
            print(f"{u} loaded active waiting x")
    sys.exit(0)
if cmd == "show":
    u = d.get("units", {}).get(a[a.index("show") + 1])
    if u is None:                                    # o systemd responde 0 com LoadState=not-found
        print("LoadState=not-found"); print("FragmentPath=")
    else:
        for k, v in {"LoadState": "loaded", **u}.items():
            print(f"{k}={v}")
    sys.exit(0)
falha = d.get("falha", {}).get(cmd)
if falha:
    print(falha[1], file=sys.stderr); sys.exit(falha[0])
sys.exit(0)
"""
STUB_TAREFAS = """
import json, os, sys
a = sys.argv[1:]
entrada = sys.stdin.read() if a[0] == "criar" else ""
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"verbo": "tarefas", "argv": a, "stdin": entrada}) + "\\n")
if a[0] == "listar":
    if os.environ.get("STUB_TAREFAS_LISTAR_EXIT"):
        print("rastreador fora", file=sys.stderr); sys.exit(int(os.environ["STUB_TAREFAS_LISTAR_EXIT"]))
    # o rastreador de mentira e LAST-WINS: de varios `--estado`, so o ultimo vale (o real pode ser assim)
    estados = [a[i + 1] for i, x in enumerate(a) if x == "--estado"]
    p = os.environ["STUB_TAREFAS_ABERTOS"]
    if estados and os.path.exists(p):
        for i in json.load(open(p)):
            if i["estado"] == estados[-1]:
                print(f"{i['id']}\\t \\t{i['titulo']}")
    sys.exit(0)
if a[0] == "criar":
    if os.environ.get("STUB_TAREFAS_CRIAR_EXIT"):
        print("API recusou", file=sys.stderr); sys.exit(int(os.environ["STUB_TAREFAS_CRIAR_EXIT"]))
    print(f"item 9001 criado: {a[1]}"); sys.exit(0)
sys.exit(9)
"""
STUB_AGENTE = """
import json, os, sys
a = sys.argv[1:]
entrada = sys.stdin.read() if a[0] == "rodar" else ""
env = {k: os.environ.get(k) for k in ("PF_SUJEITO", "PF_SESSAO")}
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"verbo": "agente", "argv": a, "stdin": entrada, "env": env}) + "\\n")
if a[0] == "ler":
    if a[1] in os.environ.get("STUB_AGENTES", "").split(","):
        print("slug: " + a[1]); sys.exit(0)
    print(f"agente: sem declaração {a[1]!r}", file=sys.stderr); sys.exit(1)
if a[0] == "rodar":
    if not entrada.strip():
        print("agente: a tarefa vem em stdin", file=sys.stderr); sys.exit(2)
    print("agente rodou"); sys.exit(int(os.environ.get("STUB_AGENTE_EXIT", "0")))
sys.exit(9)
"""
STUB_FAZ = """
import json, os, signal, sys, time
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"verbo": "faz", "argv": sys.argv[1:], "cadeia": os.environ.get("PF_BOT_SLUGS")}) + "\\n")
if os.environ.get("STUB_FAZ_DORME"):               # o job que demora: marca que comecou e espera o SIGTERM
    def termina(*_):
        open(os.environ["STUB_FAZ_DORME"] + ".term", "w").write("x")
        sys.exit(0)
    signal.signal(signal.SIGTERM, termina)
    open(os.environ["STUB_FAZ_DORME"], "w").write("x")
    time.sleep(30)
print("feito")
sys.exit(int(os.environ.get("STUB_FAZ_EXIT", "0")))
"""
STUB_ANALYZE = """
import json, os, sys
a = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"verbo": "systemd-analyze", "argv": a}) + "\\n")
if "amanha" in " ".join(a):
    print("Failed to parse calendar specification 'amanha as 9': Invalid argument", file=sys.stderr); sys.exit(1)
print("  Original form: " + a[-1])
sys.exit(0)
"""
STUB_BOT = f"""
import os, sys
if len([s for s in os.environ.get("PF_BOT_SLUGS", "").split(",") if s]) > 5:
    sys.exit(99)     # rede de seguranca: sem o freio de recursao do bot o ciclo nao pode crescer sem fim
os.execv(sys.executable, [sys.executable, {str(BOT)!r}, *sys.argv[1:]])
"""


def _stub(pasta: Path, nome: str, corpo: str) -> None:
    arq = pasta / nome
    arq.write_text(f"#!{sys.executable}\n{corpo}")
    arq.chmod(0o755)


# --- o dublê do acervo (contrato acervo-escrita 1.1.0, subconjunto do bot) -----------------------

DECL = ("roda_tipo", "roda_ref", "roda_args", "trigger_tipo", "trigger_arg", "dono", "slo_janela_max")
CAMPOS_EVENTO = {"fonte", "tipo", "ts", "exit_code", "unit", "verbo", "sessao_id", "ordem_id", "sha", "ator", "mensagem"}


def problema(status: int, titulo: str, detalhe: str):
    return status, {"type": "about:blank", "title": titulo, "detail": detalhe, "status": status}


class Acervo:
    def __init__(self, log: Path):
        self.log = log
        self.fichas: dict[str, dict] = {}
        self.retiradas: set[str] = set()
        self.eventos: list[dict] = []
        self.chamadas: list[dict] = []
        self.cadeiras = {"ti", "dados", "ia"}
        self.verbos = {"faz", "conferir"}
        self.pagina = 100
        self.sem_rota = False                      # o recurso não existe: 404 do roteador, sem problem+json
        self.fora = False                          # 503 FonteIndisponivel
        self.recusa_evento: int | None = None      # o POST de evento volta com esse status
        self.estado_forcado: dict[str, str] = {}   # o SLO vencido: o serviço calcula, o bot só lê
        self.demora = 0.0
        self.ao_receber = None

    def poe(self, slug, dono="ti", trigger_tipo="timer", trigger_arg=CAL, slo="P1D", roda_tipo="verbo",
            roda_ref="faz", roda_args=()):
        """Uma ficha ativa direto no dublê (o que um `bot declarar` anterior deixou)."""
        self.fichas[slug] = {"id": str(uuid.uuid4()), "slug": slug, "ciclo": "ativa", "roda_tipo": roda_tipo,
                             "roda_ref": roda_ref, "roda_args": list(roda_args), "trigger_tipo": trigger_tipo,
                             "trigger_arg": trigger_arg if trigger_tipo != "manual" else None, "dono": dono,
                             "slo_janela_max": slo, "declarada_por": dono, "declarada_em": "2026-10-01T09:00:00-03:00",
                             "retirada_em": None}

    def grava_evento(self, slug, tipo, exit_code=None):
        self.eventos.append({"id": str(uuid.uuid4()), "fonte": slug, "automacao_id": self.fichas[slug]["id"],
                             "ts": f"2026-10-01T10:00:{len(self.eventos):02d}-03:00", "tipo": tipo,
                             "exit_code": exit_code})

    def projeta(self, f):
        evs = [e for e in self.eventos if e["automacao_id"] == f["id"]]
        fins = [e for e in evs if e["tipo"] == "fim"]
        if f["slug"] in self.estado_forcado:
            estado = self.estado_forcado[f["slug"]]
        elif fins and fins[-1]["exit_code"] != 0:
            estado = "caida"
        else:
            estado = "viva" if fins else "planejada"
        ultimo = evs[-1] if evs else None
        return {**f, "estado": estado, "rodando": bool(ultimo and ultimo["tipo"] == "inicio"),
                "ultimo_evento": ({k: ultimo.get(k) for k in ("ts", "tipo", "exit_code", "sha")} if ultimo else None)}

    def rota(self, metodo, caminho, q, corpo):
        if caminho == "/acervo/automacoes" and metodo == "GET":
            return self.lista(q)
        m = re.fullmatch(r"/acervo/automacoes/([a-z0-9-]+)", caminho)
        if m and metodo == "PUT":
            return self.put(m.group(1), corpo)
        if m and metodo == "GET":
            return (200, self.projeta(self.fichas[m.group(1)])) if m.group(1) in self.fichas else \
                problema(404, "AutomacaoNaoDeclarada", m.group(1))
        if m and metodo == "DELETE":
            return self.apaga(m.group(1), q)
        if caminho == "/acervo/registro/eventos" and metodo == "POST":
            return self.evento(corpo)
        return 404, None

    def put(self, slug, corpo):
        extras = set(corpo) - {"autor", *DECL}
        if extras:
            return problema(422, "DeclaracaoInvalida", f"campos fora do contrato: {sorted(extras)}")
        if corpo.get("autor") not in self.cadeiras or corpo.get("dono") not in self.cadeiras:
            return problema(422, "CadeiraDesconhecida", f"{corpo.get('autor')}/{corpo.get('dono')}")
        if corpo.get("roda_tipo") == "verbo" and corpo.get("roda_ref") not in self.verbos:
            return problema(422, "VerboDesconhecido", str(corpo.get("roda_ref")))
        if corpo.get("roda_tipo") == "agente" and corpo.get("roda_args"):
            return problema(422, "DeclaracaoInvalida", "roda_args com agente")
        if (corpo.get("trigger_tipo") == "manual") != ("trigger_arg" not in corpo):
            return problema(422, "DeclaracaoInvalida", "trigger_arg presente se e só se não é manual")
        if corpo.get("trigger_tipo") == "timer" and not corpo.get("slo_janela_max"):
            return problema(422, "TimerSemSlo", "timer pede slo_janela_max")
        decl = {k: corpo.get(k) for k in DECL}
        if slug in self.fichas:
            dif = [k for k in DECL if self.fichas[slug].get(k) != decl[k]]
            if dif:
                return problema(409, "DeclaracaoDivergente", f"campos que diferem: {', '.join(dif)}")
            return 200, self.projeta(self.fichas[slug])
        self.poe(slug, **{k: decl[k] for k in ("dono", "trigger_tipo", "trigger_arg", "roda_tipo", "roda_ref",
                                               "roda_args")}, slo=decl["slo_janela_max"])
        self.fichas[slug]["declarada_por"] = corpo["autor"]
        return 201, self.projeta(self.fichas[slug])

    def apaga(self, slug, q):
        if q.get("autor") not in self.cadeiras:
            return problema(422, "CadeiraDesconhecida", str(q.get("autor")))
        if slug in self.fichas:
            self.retiradas.add(slug)
            del self.fichas[slug]
            return 204, None
        if slug in self.retiradas:
            return 204, None
        return problema(404, "AutomacaoNaoDeclarada", slug)

    def lista(self, q):
        itens = [self.projeta(f) for _, f in sorted(self.fichas.items())]
        if q.get("estado"):
            itens = [i for i in itens if i["estado"] == q["estado"]]
        ini = int(q.get("cursor") or 0)
        fim = ini + self.pagina
        return 200, {"itens": itens[ini:fim], "proximo": str(fim) if fim < len(itens) else None}

    def evento(self, corpo):
        if self.recusa_evento:
            return problema(self.recusa_evento, "FonteIndisponivel", "banco nao responde")
        if set(corpo) - CAMPOS_EVENTO:
            return problema(422, "EventoInvalido", f"campos fora do contrato: {sorted(set(corpo) - CAMPOS_EVENTO)}")
        if corpo.get("fonte") not in self.fichas:
            return problema(422, "FonteDesconhecida", str(corpo.get("fonte")))
        if corpo.get("tipo") not in ("inicio", "fim") or (corpo["tipo"] == "fim") != (corpo.get("exit_code") is not None):
            return problema(422, "EventoInvalido", "tipo e exit_code")
        ev = {**corpo, "id": str(uuid.uuid4()), "automacao_id": self.fichas[corpo["fonte"]]["id"],
              "ts": f"2026-10-01T10:00:{len(self.eventos):02d}-03:00"}
        self.eventos.append(ev)
        return 201, ev

    def handler(self):
        acervo = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _despacha(self, metodo):
                url = urlparse(self.path)
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                n = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(n)) if n else None
                acervo.chamadas.append({"metodo": metodo, "caminho": url.path, "query": q, "corpo": corpo,
                                        "auth": self.headers.get("Authorization")})
                with open(acervo.log, "a") as f:
                    f.write(json.dumps({"verbo": "acervo", "metodo": metodo, "caminho": url.path}) + "\n")
                if acervo.ao_receber:
                    acervo.ao_receber(metodo, url.path)
                if acervo.demora:
                    time.sleep(acervo.demora)
                if acervo.sem_rota:
                    status, obj = 404, None
                elif acervo.fora:
                    status, obj = problema(503, "FonteIndisponivel", "banco nao responde")
                else:
                    status, obj = acervo.rota(metodo, url.path, q, corpo)
                if obj is None:
                    dados, tipo = (b"Not Found", "text/plain") if status == 404 else (b"", None)
                else:
                    dados = json.dumps(obj).encode()
                    tipo = "application/problem+json" if status >= 400 else "application/json"
                try:
                    self.send_response(status)
                    if tipo:
                        self.send_header("Content-Type", tipo)
                    self.send_header("Content-Length", str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados)
                except (BrokenPipeError, ConnectionResetError):
                    pass                    # o cliente estourou o teto e fechou o socket: nao ha a quem responder

            def do_GET(self):
                self._despacha("GET")

            def do_PUT(self):
                self._despacha("PUT")

            def do_POST(self):
                self._despacha("POST")

            def do_DELETE(self):
                self._despacha("DELETE")

        return H


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass


# --- fixtures -----------------------------------------------------------------------------------

@pytest.fixture
def mundo(tmp_path, monkeypatch):
    casa, bin_, stub, pasta = tmp_path / "casa", tmp_path / "bin", tmp_path / "stub", tmp_path / "units"
    run = tmp_path / "run"
    for d in (casa, bin_, stub, pasta, run):
        d.mkdir()
    log, sd, abertos = tmp_path / "stub.log", tmp_path / "systemd.json", tmp_path / "abertos.json"
    sd.write_text("{}")
    _stub(stub, "systemctl", STUB_SYSTEMCTL)
    _stub(stub, "systemd-analyze", STUB_ANALYZE)
    _stub(bin_, "tarefas", STUB_TAREFAS)
    _stub(bin_, "agente", STUB_AGENTE)
    _stub(bin_, "faz", STUB_FAZ)
    _stub(bin_, "bot", STUB_BOT)
    # a release: harness é o checkout <sha>, de onde sai o sha do evento; os declarantes de manifesto ficam nela
    checkout = tmp_path / "opt" / "platafirma-harness" / SHA
    (checkout / "deploy-harness").mkdir(parents=True)
    (checkout / "deploy-harness" / "instalar").write_text(INSTALAR)
    rel = tmp_path / "rel"
    (rel / "core" / "deploy").mkdir(parents=True)
    (rel / "core" / "deploy" / "units-da-instancia.json").write_text(json.dumps(REGISTRO))
    (rel / "harness").symlink_to(checkout)
    for k, v in (("HOME", casa), ("XDG_DATA_HOME", casa / ".local" / "share"), ("PF_UNITS_DIR", pasta),
                 ("PF_BIN", bin_), ("PATH", f"{stub}{os.pathsep}{os.environ['PATH']}"), ("STUB_LOG", log),
                 ("STUB_SYSTEMD", sd), ("STUB_TAREFAS_ABERTOS", abertos), ("PLATAFIRMA_RELEASE", rel),
                 ("PF_CADEIRA", "ti"), ("STUB_AGENTES", "revisor"), ("XDG_RUNTIME_DIR", run)):
        monkeypatch.setenv(k, str(v))
    for k in ("PF_SESSAO", "PF_SUJEITO", "PF_ORDEM_ID", "RAG_API_TOKEN", "STUB_FAZ_EXIT", "STUB_AGENTE_EXIT",
              "STUB_TAREFAS_LISTAR_EXIT", "STUB_TAREFAS_CRIAR_EXIT", "PF_BOT_SLUGS", "STUB_FAZ_DORME"):
        monkeypatch.delenv(k, raising=False)

    def chamadas(verbo=None):
        todas = [json.loads(linha) for linha in log.read_text().splitlines()] if log.exists() else []
        return [c for c in todas if verbo is None or c["verbo"] == verbo]

    def sequencia():
        """A ordem em que o mundo foi tocado: systemctl, acervo e job, uma etiqueta por chamada."""
        return [" ".join(c["argv"][1:]) if c["verbo"] == "systemctl" else
                f"{c['metodo']} {c['caminho']}" if c["verbo"] == "acervo" else c["verbo"] for c in chamadas()]

    def systemd(**estado):
        sd.write_text(json.dumps(estado))

    def unit_do_bot(slug, calendario=CAL):
        servico, timer = units.gera_unit({"slug": slug, "trigger_tipo": "timer", "trigger_arg": calendario})
        (pasta / f"{slug}.service").write_text(servico)
        (pasta / f"{slug}.timer").write_text(timer)

    def abre_incidentes(*linhas):
        """(id, titulo) ou (id, titulo, estado); sem estado, `detectado`. O rastreador de mentira filtra por estado."""
        abertos.write_text(json.dumps([{"id": i, "titulo": t, "estado": (e[0] if e else "detectado")}
                                       for i, t, *e in linhas]))

    return SimpleNamespace(pasta=pasta, bin=bin_, rel=rel, checkout=checkout, log=log, chamadas=chamadas,
                           sequencia=sequencia, systemd=systemd, unit_do_bot=unit_do_bot,
                           abre_incidentes=abre_incidentes, tmp=tmp_path, casa=casa, stub=stub, run=run)


@pytest.fixture
def acervo(mundo, monkeypatch):
    # bin/_acervo/registrar faz signal(SIGPIPE, SIG_DFL) ao ser importado (test_casa_arvore, na mesma sessao):
    # o servico que demora escreveria num socket ja fechado pelo cliente e mataria o pytest (exit 141).
    anterior = signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    a = Acervo(mundo.log)
    srv = Servidor(("127.0.0.1", 0), a.handler())
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setattr(bot, "ACERVO_URL", url)
    monkeypatch.setenv("MOTOR_ACERVO_URL", url)       # para o bot quando roda como processo
    yield a
    srv.shutdown()
    srv.server_close()
    signal.signal(signal.SIGPIPE, anterior)


def executa(*argv) -> int:
    try:
        return bot.main(list(argv))
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


def processo(*argv, entrada=None):
    """O bot como a unit o chama: um processo, com o exit de verdade e o stdin herdado."""
    return subprocess.run([sys.executable, str(BOT), *argv], input=entrada, capture_output=True, text=True,
                          check=False, env=os.environ.copy())


def declara(slug="x-job", roda="faz --a 1", trigger=f"timer:{CAL}", dono="ti", slo="1d", autor=None):
    argv = ["declarar", slug, "--roda", roda, "--trigger", trigger, "--dono", dono]
    if slo is not None:
        argv += ["--slo", slo]
    if autor:
        argv += ["--autor", autor]
    return executa(*argv)


def base_systemd(mundo, failed=(), timers=(), units_extra=None, **estado):
    """Os timers de manifesto de pé (um do instalador, um do core, um de fora do instalador) e um de pacote do SO."""
    frag = str(mundo.tmp / "fonte")
    u = {t: {"FragmentPath": f"{frag}/{t}"} for t in ("sinal.timer", "motor-trim.timer", "prior-secao.timer")}
    u["cron-sistema.timer"] = {"FragmentPath": "/usr/lib/systemd/user/cron-sistema.timer"}
    u.update(units_extra or {})
    mundo.systemd(failed=list(failed), timers=["sinal.timer", "motor-trim.timer", "prior-secao.timer",
                                               "cron-sistema.timer", *timers], units=u, **estado)


def frag_do_bot(mundo, slug):
    return {f"{slug}.service": {"FragmentPath": str(mundo.pasta / f"{slug}.service")},
            f"{slug}.timer": {"FragmentPath": str(mundo.pasta / f"{slug}.timer")}}


# --- declarar: a ordem fixa (uso, PUT, unit) -----------------------------------------------------

def test_declarar_timer_grava_a_ficha_e_gera_a_unit_habilitada(mundo, acervo, capsys):
    assert declara(roda='faz --a "b c"') == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["caminho"] == "/acervo/automacoes/x-job"
    assert put["corpo"] == {"autor": "ti", "roda_tipo": "verbo", "roda_ref": "faz", "roda_args": ["--a", "b c"],
                            "trigger_tipo": "timer", "trigger_arg": CAL, "dono": "ti", "slo_janela_max": "P1D"}
    servico, timer = units.gera_unit({"slug": "x-job", "trigger_tipo": "timer", "trigger_arg": CAL})
    assert (mundo.pasta / "x-job.service").read_text() == servico
    assert (mundo.pasta / "x-job.timer").read_text() == timer
    link = mundo.pasta / "timers.target.wants" / "x-job.timer"
    assert link.is_symlink() and os.readlink(link) == str(mundo.pasta / "x-job.timer")
    assert [c["argv"][1:] for c in mundo.chamadas("systemctl")] == [["daemon-reload"], ["start", "x-job.timer"]]
    saida = capsys.readouterr().out
    assert "declarada: x-job" in saida and f"morada: {mundo.pasta}" in saida


def test_a_unit_so_nasce_depois_do_put(mundo, acervo):
    vistos = []
    acervo.ao_receber = lambda metodo, caminho: vistos.append((metodo, (mundo.pasta / "x-job.service").exists()))
    assert declara() == 0
    assert vistos == [("PUT", False)], "no PUT a unit ainda não existe"
    assert (mundo.pasta / "x-job.service").exists()


def test_roda_parte_com_shlex_um_item_por_token(mundo, acervo):
    assert declara(roda="faz 'dois tokens' --x=1 \"e \\\"este\\\"\"", trigger="manual", slo=None) == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["corpo"]["roda_ref"] == "faz"
    assert put["corpo"]["roda_args"] == ["dois tokens", "--x=1", 'e "este"']


def test_timer_sem_slo_sai_2_sem_tocar_o_servico(mundo, acervo, capsys):
    assert declara(slo=None) == 2
    assert "--slo" in capsys.readouterr().err
    assert acervo.chamadas == [] and mundo.chamadas("systemctl") == [] and not list(mundo.pasta.iterdir())


@pytest.mark.parametrize("curto,iso", [("1d", "P1D"), ("6h", "PT6H"), ("30m", "PT30M"), ("90s", "PT90S"),
                                        ("1d12h", "P1DT12H"), ("PT24H", "PT24H")])
def test_slo_curto_vira_iso_8601_no_corpo(mundo, acervo, curto, iso):
    assert declara(slo=curto) == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["corpo"]["slo_janela_max"] == iso


@pytest.mark.parametrize("ruim", ["0h", "-1d", "abc", "1w", "", "P"])
def test_slo_zero_negativo_ou_lixo_sai_2_antes_do_servico(mundo, acervo, ruim):
    assert declara(slo=ruim) == 2
    assert acervo.chamadas == []


def test_evento_sai_4_antes_do_servico(mundo, acervo, capsys):
    assert declara(trigger="evento:fila-x", slo=None) == 4
    assert "evento" in capsys.readouterr().err
    assert declara(trigger="evento:fila-x") == 4
    assert acervo.chamadas == [] and mundo.chamadas("systemctl") == []


def test_agente_com_timer_sai_4_sem_agente_ler_nem_servico(mundo, acervo, capsys):
    assert declara(slug="rev-timer", roda="agente:revisor") == 4
    assert "sujeito de máquina" in capsys.readouterr().err
    assert mundo.chamadas("agente") == [] and acervo.chamadas == [] and not list(mundo.pasta.iterdir())


def test_agente_manual_exige_agente_ler_antes_do_put_e_vai_sem_args(mundo, acervo):
    assert declara(slug="rev-manual", roda="agente:revisor", trigger="manual", slo=None) == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["corpo"] == {"autor": "ti", "roda_tipo": "agente", "roda_ref": "revisor", "roda_args": [],
                            "trigger_tipo": "manual", "dono": "ti"}
    assert mundo.sequencia() == ["agente", "PUT /acervo/automacoes/rev-manual"]
    assert mundo.chamadas("agente")[0]["argv"] == ["ler", "revisor"]
    assert not list(mundo.pasta.iterdir()) and mundo.chamadas("systemctl") == [], "manual não escreve unit"


def test_agente_que_agente_ler_nao_acha_sai_1_sem_put(mundo, acervo, capsys):
    assert declara(slug="rev-manual", roda="agente:fantasma", trigger="manual", slo=None) == 1
    assert "agente ler fantasma saiu 1" in capsys.readouterr().err
    assert acervo.chamadas == []


@pytest.mark.parametrize("trigger", ["manual:x", "timer", "timer:", "timer: ", "cron:x", ""])
def test_gatilho_mal_formado_sai_2_sem_tocar_o_servico(mundo, acervo, trigger):
    assert declara(trigger=trigger) == 2
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


@pytest.mark.parametrize("cal", ["*-*-* 06:45\nExecStart=/bin/sh -c x", "*-*-* 06:45\r\nUser=root", "*-*-* \x1b06:45"])
def test_calendario_com_quebra_de_linha_ou_controle_e_recusado_antes_do_servico(mundo, acervo, cal, capsys):
    assert declara(trigger=f"timer:{cal}") == 2
    assert "calendario invalido" in capsys.readouterr().err
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


@pytest.mark.parametrize("slug", ["X-job", "x_job", "-x", "x--", "x/y", ""])
def test_slug_fora_do_molde_sai_2(mundo, acervo, slug):
    assert declara(slug=slug) == 2
    assert acervo.chamadas == []


def test_declarar_sem_as_flags_do_card_sai_2(mundo, acervo):
    assert executa("declarar", "x-job") == 2
    assert executa("declarar", "x-job", "--roda", "faz", "--trigger", "manual") == 2
    assert acervo.chamadas == []


def test_declaracao_divergente_sai_1_com_os_campos_e_nao_regera_a_unit(mundo, acervo, capsys):
    assert declara() == 0
    antes = (mundo.pasta / "x-job.timer").read_text()
    capsys.readouterr()
    assert declara(trigger="timer:*-*-* 07:00", slo="6h") == 1
    err = capsys.readouterr().err
    assert "DeclaracaoDivergente" in err and "trigger_arg" in err and "slo_janela_max" in err
    assert "desligar e declarar de novo" in err
    assert (mundo.pasta / "x-job.timer").read_text() == antes, "ficha divergente nunca gera unit"


def test_ja_declarada_sai_0_e_escreve_a_unit_que_faltava(mundo, acervo, capsys):
    assert declara() == 0
    for nome in ("x-job.service", "x-job.timer", "timers.target.wants/x-job.timer"):
        (mundo.pasta / nome).unlink()
    capsys.readouterr()
    assert declara() == 0
    assert "já declarada: x-job" in capsys.readouterr().out
    assert units.eh_unit_do_bot((mundo.pasta / "x-job.service").read_text())
    assert units.eh_unit_do_bot((mundo.pasta / "x-job.timer").read_text())
    assert (mundo.pasta / "timers.target.wants" / "x-job.timer").is_symlink()


def test_declarar_de_novo_nao_reescreve_bytes_iguais(mundo, acervo):
    assert declara() == 0
    antes = {n: (mundo.pasta / n).stat().st_ino for n in ("x-job.service", "x-job.timer")}
    assert declara() == 0
    assert {n: (mundo.pasta / n).stat().st_ino for n in antes} == antes, "rename atômico trocaria o inode"


@pytest.mark.parametrize("nome", ["x-job.service", "x-job.timer"])
def test_unit_homonima_sem_cabecalho_sai_4_e_nunca_e_sobrescrita(mundo, acervo, capsys, nome):
    alheia = mundo.pasta / nome
    alheia.write_text("[Unit]\nDescription=de outro\n")
    assert declara() == 4
    assert "unit x-job já existe e não é do bot" in capsys.readouterr().err
    assert alheia.read_text() == "[Unit]\nDescription=de outro\n"
    assert [p.name for p in mundo.pasta.iterdir()] == [nome], "nem a outra unit nem o .wants"
    assert mundo.chamadas("systemctl") == []


def test_verbo_e_cadeira_desconhecidos_saem_1_sem_unit(mundo, acervo, capsys):
    assert declara(roda="inexistente") == 1
    assert "VerboDesconhecido" in capsys.readouterr().err
    assert declara(dono="fantasma") == 1
    assert "CadeiraDesconhecida" in capsys.readouterr().err
    assert declara(autor="fantasma") == 1
    assert not list(mundo.pasta.iterdir()) and mundo.chamadas("systemctl") == []


def test_rota_ausente_sai_3_com_o_nome_do_recurso_e_nao_gera_unit(mundo, acervo, capsys):
    acervo.sem_rota = True
    assert declara() == 3
    err = capsys.readouterr().err
    assert "/acervo/automacoes/x-job" in err and "rota ausente" in err
    assert not list(mundo.pasta.iterdir())


def test_servico_fora_e_503_saem_3_nomeando_o_recurso(mundo, acervo, monkeypatch, capsys):
    acervo.fora = True
    assert declara() == 3
    assert "/acervo/automacoes/x-job" in capsys.readouterr().err
    monkeypatch.setattr(bot, "ACERVO_URL", "http://127.0.0.1:9")
    assert declara() == 3
    err = capsys.readouterr().err
    assert "/acervo/automacoes/x-job" in err and "http://127.0.0.1:9" in err and "não respondeu" in err


def test_servico_que_demora_alem_do_teto_e_indeterminavel(mundo, acervo, monkeypatch, capsys):
    monkeypatch.setattr(bot, "TIMEOUT_S", 0.2)
    acervo.demora = 1.0
    assert declara() == 5
    assert "sem resposta" in capsys.readouterr().err
    assert not list(mundo.pasta.iterdir())


def test_sem_autor_sai_2_e_o_autor_vem_do_flag_ou_do_pf_cadeira(mundo, acervo, monkeypatch, capsys):
    monkeypatch.delenv("PF_CADEIRA")
    assert declara() == 2
    assert "sem autor" in capsys.readouterr().err and acervo.chamadas == []
    assert declara(autor="dados") == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["corpo"]["autor"] == "dados"
    monkeypatch.setenv("PF_CADEIRA", "ia")
    assert declara(slug="outro-job") == 0
    assert [c["corpo"]["autor"] for c in acervo.chamadas if c["metodo"] == "PUT"] == ["dados", "ia"]


def test_wants_sem_escrita_sai_3_nomeando_o_caminho_e_a_ficha_fica(mundo, acervo, capsys):
    (mundo.pasta / "timers.target.wants").write_text("do dono da máquina")      # nem o .wants aceita escrita
    assert declara() == 3
    err = capsys.readouterr().err
    assert "timers.target.wants" in err and "dono da máquina" in err
    assert "x-job" in acervo.fichas and (mundo.pasta / "x-job.timer").exists()
    assert mundo.chamadas("systemctl") == []


def test_o_token_vai_como_bearer_e_nunca_e_impresso(mundo, acervo, monkeypatch, capsys):
    monkeypatch.setenv("RAG_API_TOKEN", "segredo-do-ops-123")
    assert declara() == 0
    assert acervo.chamadas[0]["auth"] == "Bearer segredo-do-ops-123"
    assert executa("listar") == 0
    assert acervo.chamadas[-1]["auth"] == "Bearer segredo-do-ops-123"
    saida = capsys.readouterr()
    assert "segredo-do-ops-123" not in saida.out + saida.err


def test_o_bot_nao_grava_eixo_de_agente_nem_ts(mundo, acervo):
    assert declara() == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert set(put["corpo"]) <= {"autor", *DECL}, "o contrato fecha os campos; modelo, modo e conta são do agente"


# --- listar -------------------------------------------------------------------------------------

def _tres_fichas(acervo):
    acervo.poe("a-job", dono="ti")
    acervo.poe("b-job", dono="dados", trigger_tipo="manual", slo=None)
    acervo.poe("c-job", dono="ia")
    acervo.grava_evento("a-job", "inicio")
    acervo.grava_evento("a-job", "fim", 0)
    acervo.grava_evento("c-job", "inicio")


def test_listar_uma_linha_por_declaracao_e_segue_proximo_numa_chamada_do_usuario(mundo, acervo, capsys):
    _tres_fichas(acervo)
    acervo.pagina = 2
    assert executa("listar") == 0
    linhas = capsys.readouterr().out.splitlines()
    assert len(linhas) == 3
    a, b, c = linhas
    assert a.split()[:2] == ["a-job", "ti"] and f"timer:{CAL}" in a and "fim 0 2026-10-01T10:00:01-03:00" in a
    assert "viva" in a and "rodando" not in a
    assert b.split()[:3] == ["b-job", "dados", "manual"] and "—" in b and "planejada" in b
    assert c.split()[:2] == ["c-job", "ia"] and "inicio 2026-10-01T10:00:02-03:00" in c and c.endswith("rodando")
    gets = [x for x in acervo.chamadas if x["metodo"] == "GET"]
    assert [x["query"] for x in gets] == [{}, {"cursor": "2"}], "duas páginas, uma chamada do usuário"


def test_listar_estado_caida_aceita_acento_filtra_no_servico_e_nao_recalcula(mundo, acervo, capsys):
    _tres_fichas(acervo)
    acervo.estado_forcado["b-job"] = "caida"           # o SLO venceu: o serviço diz, o bot só lê
    assert executa("listar", "--estado", "caída") == 0
    saida = capsys.readouterr().out
    assert [x["query"] for x in acervo.chamadas] == [{"estado": "caida"}]
    assert saida.split()[0] == "b-job" and len(saida.splitlines()) == 1 and "caida" in saida


def test_listar_json_e_a_lista_de_automacoes_do_servico(mundo, acervo, capsys):
    _tres_fichas(acervo)
    assert executa("listar", "--json") == 0
    lista = json.loads(capsys.readouterr().out)
    assert [f["slug"] for f in lista] == ["a-job", "b-job", "c-job"]
    assert all(f["ciclo"] == "ativa" and "estado" in f and "rodando" in f for f in lista)


def test_listar_sem_a_rota_sai_3_e_no_json_a_falha_e_um_objeto_erro(mundo, acervo, capsys):
    acervo.sem_rota = True
    assert executa("listar") == 3
    assert "/acervo/automacoes" in capsys.readouterr().err
    assert executa("listar", "--json") == 3
    saida = capsys.readouterr()
    assert "/acervo/automacoes" in json.loads(saida.out)["erro"]


def test_listar_estado_fora_do_conjunto_sai_2(mundo, acervo):
    assert executa("listar", "--estado", "morta") == 2
    assert acervo.chamadas == []


# --- rodar --------------------------------------------------------------------------------------

def test_rodar_grava_inicio_e_fim_e_sai_com_o_exit_do_que_rodou(mundo, acervo, monkeypatch):
    acervo.poe("x-job", roda_args=["--a", "1"])
    monkeypatch.setenv("STUB_FAZ_EXIT", "7")
    monkeypatch.setenv("PF_SESSAO", ORQ)
    monkeypatch.setenv("PF_ORDEM_ID", "o-1")
    assert executa("rodar", "x-job") == 7
    inicio, fim = acervo.eventos
    assert {k: v for k, v in inicio.items() if k not in ("id", "automacao_id", "ts")} == {
        "fonte": "x-job", "tipo": "inicio", "unit": "x-job.service", "verbo": "faz", "ator": "ti",
        "sessao_id": ORQ, "ordem_id": "o-1"}
    assert fim["tipo"] == "fim" and fim["exit_code"] == 7 and fim["sha"] == SHA and fim["ator"] == "ti"
    assert [c["corpo"].get("ts") for c in acervo.chamadas if c["metodo"] == "POST"] == [None, None], "o ts é do servidor"
    assert mundo.chamadas("faz")[0]["argv"] == ["--a", "1"]
    assert mundo.sequencia() == ["GET /acervo/automacoes/x-job", "POST /acervo/registro/eventos", "faz",
                                 "POST /acervo/registro/eventos"]


def test_ator_sem_cadeira_e_o_bot_do_slug_e_sessao_que_nao_e_uuid_se_omite(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    monkeypatch.delenv("PF_CADEIRA")
    monkeypatch.setenv("PF_SESSAO", "nao-e-uuid")
    assert executa("rodar", "x-job") == 0
    assert [e["ator"] for e in acervo.eventos] == ["bot:x-job", "bot:x-job"]
    assert all("sessao_id" not in e and "ordem_id" not in e for e in acervo.eventos)


def test_sem_release_resolvivel_o_evento_fim_vai_sem_sha(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(mundo.tmp / "nada"))
    assert executa("rodar", "x-job") == 0
    assert all("sha" not in e for e in acervo.eventos), "o sha nunca se inventa"


def test_rodar_com_o_registro_fora_sai_com_o_exit_do_job_e_avisa(mundo, acervo, monkeypatch, capsys):
    acervo.poe("x-job")
    acervo.recusa_evento = 503
    assert executa("rodar", "x-job") == 0
    assert capsys.readouterr().err.count("aviso: o evento") == 2
    monkeypatch.setenv("STUB_FAZ_EXIT", "3")
    assert executa("rodar", "x-job") == 3, "o exit é o do que rodou, não o do registro"
    assert acervo.eventos == []


def test_rodar_sem_o_servico_ou_sem_a_rota_sai_3_e_nao_executa(mundo, acervo, monkeypatch, capsys):
    acervo.poe("x-job")
    acervo.sem_rota = True
    assert executa("rodar", "x-job") == 3
    assert "/acervo/automacoes/x-job" in capsys.readouterr().err
    monkeypatch.setattr(bot, "ACERVO_URL", "http://127.0.0.1:9")
    assert executa("rodar", "x-job") == 3
    assert mundo.chamadas("faz") == [], "a unit fica failed, que é o certo"


def test_rodar_ficha_que_nao_existe_sai_1_sem_executar(mundo, acervo):
    assert executa("rodar", "fantasma") == 1
    assert mundo.chamadas("faz") == [] and acervo.eventos == []


def test_rodar_nao_passa_pelo_shell(mundo, acervo):
    marca = mundo.tmp / "pwned"
    args = [f"x; touch {marca}", "$(id)", "`id`", "a b", "*"]
    acervo.poe("x-job", roda_args=args)
    assert executa("rodar", "x-job") == 0
    assert mundo.chamadas("faz")[0]["argv"] == args and not marca.exists()


def test_rodar_verbo_que_nao_executa_grava_fim_127(mundo, acervo, capsys):
    acervo.poe("x-job", roda_ref="nao-existe")
    assert executa("rodar", "x-job") == 127
    assert acervo.eventos[-1]["tipo"] == "fim" and acervo.eventos[-1]["exit_code"] == 127
    assert "não executou" in capsys.readouterr().err


def test_rodar_como_processo_o_exit_do_bot_e_o_do_job(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    monkeypatch.setenv("STUB_FAZ_EXIT", "7")
    p = processo("rodar", "x-job")
    assert p.returncode == 7, p.stdout + p.stderr
    assert [e["exit_code"] for e in acervo.eventos if e["tipo"] == "fim"] == [7]
    assert "feito" in p.stdout, "a saída do job passa adiante"


def test_rodar_agente_manual_chama_agente_agendado_com_stdin_e_pessoa_de_quem_chamou(mundo, acervo, monkeypatch):
    acervo.poe("rev", roda_tipo="agente", roda_ref="revisor", roda_args=(), trigger_tipo="manual", slo=None)
    monkeypatch.setenv("PF_SUJEITO", "suj-1")
    monkeypatch.setenv("PF_SESSAO", ORQ)
    p = processo("rodar", "rev", entrada="revise isto")
    assert p.returncode == 0, p.stderr
    (chamada,) = mundo.chamadas("agente")
    assert chamada["argv"] == ["rodar", "revisor", "--ligacao", "agendado"]
    assert chamada["stdin"] == "revise isto" and chamada["env"] == {"PF_SUJEITO": "suj-1", "PF_SESSAO": ORQ}
    assert [e["verbo"] for e in acervo.eventos] == ["revisor", "revisor"]


def test_rodar_agente_sem_stdin_propaga_o_exit_2_do_agente(mundo, acervo):
    acervo.poe("rev", roda_tipo="agente", roda_ref="revisor", roda_args=(), trigger_tipo="manual", slo=None)
    p = processo("rodar", "rev", entrada="")
    assert p.returncode == 2
    assert acervo.eventos[-1]["exit_code"] == 2


def test_rodar_ficha_de_agente_com_timer_recusa_4_sem_executar(mundo, acervo, capsys):
    acervo.poe("rev-t", roda_tipo="agente", roda_ref="revisor", roda_args=(), trigger_tipo="timer")
    assert executa("rodar", "rev-t") == 4
    assert "sujeito de máquina" in capsys.readouterr().err
    assert mundo.chamadas("agente") == [] and acervo.eventos == []


# --- desligar -----------------------------------------------------------------------------------

def test_desligar_e_o_inverso_de_declarar_e_a_ficha_so_vai_por_ultimo(mundo, acervo, capsys):
    assert declara() == 0
    ate_aqui = len(mundo.chamadas())
    assert executa("desligar", "x-job") == 0
    novas = mundo.sequencia()[ate_aqui:]
    assert novas == ["GET /acervo/automacoes/x-job", "stop x-job.timer", "stop x-job.service",
                     "reset-failed x-job.service x-job.timer", "daemon-reload", "DELETE /acervo/automacoes/x-job"]
    assert not list(mundo.pasta.rglob("x-job*")), "units e .wants se foram"
    assert acervo.retiradas == {"x-job"} and acervo.chamadas[-1]["query"] == {"autor": "ti"}
    assert "desligada: x-job" in capsys.readouterr().out


def test_desligar_se_repete_sem_dano(mundo, acervo, capsys):
    assert declara() == 0
    assert executa("desligar", "x-job") == 0
    ate_aqui = len(mundo.chamadas())
    capsys.readouterr()
    assert executa("desligar", "x-job") == 0
    assert "já desligada" in capsys.readouterr().out
    assert not [c for c in mundo.chamadas()[ate_aqui:] if c["verbo"] == "systemctl"]


def test_desligar_nunca_toca_unit_sem_o_cabecalho_do_bot(mundo, acervo, capsys):
    acervo.poe("x-job")
    alheia = mundo.pasta / "x-job.service"
    alheia.write_text("[Unit]\nDescription=de outro\n")
    assert executa("desligar", "x-job") == 0
    assert alheia.read_text() == "[Unit]\nDescription=de outro\n"
    assert mundo.chamadas("systemctl") == []
    assert "não é do bot" in capsys.readouterr().err and acervo.retiradas == {"x-job"}


def test_desligar_slug_nunca_declarado_sai_1(mundo, acervo, capsys):
    assert executa("desligar", "fantasma") == 1
    assert "nunca foi declarada" in capsys.readouterr().err


def test_desligar_unit_do_bot_sem_ficha_ativa_limpa_a_unit_e_sai_0(mundo, acervo, capsys):
    mundo.unit_do_bot("orfa")
    assert executa("desligar", "orfa") == 0
    assert "sem ficha ativa; unit removida" in capsys.readouterr().out
    assert not list(mundo.pasta.iterdir())
    assert [c["metodo"] for c in acervo.chamadas] == ["GET"], "sem ficha, nada a retirar"


def test_desligar_ignora_not_loaded(mundo, acervo):
    assert declara() == 0
    mundo.systemd(falha={"stop": [5, "Failed to stop x-job.timer: Unit x-job.timer not loaded."],
                         "reset-failed": [1, "Failed to reset failed state of unit x-job.service: not loaded."]})
    assert executa("desligar", "x-job") == 0
    assert acervo.retiradas == {"x-job"}


def test_desligar_com_systemctl_quebrado_sai_3_e_nao_retira_a_ficha(mundo, acervo, capsys):
    assert declara() == 0
    mundo.systemd(falha={"stop": [1, "Failed to connect to bus: No medium found"]})
    assert executa("desligar", "x-job") == 3
    assert "systemctl --user stop x-job.timer" in capsys.readouterr().err
    assert "x-job" in acervo.fichas and (mundo.pasta / "x-job.timer").exists()
    assert not [c for c in acervo.chamadas if c["metodo"] == "DELETE"]


def test_desligar_manual_sem_unit_nao_chama_systemctl_e_sem_autor_sai_2(mundo, acervo, monkeypatch):
    acervo.poe("m-job", trigger_tipo="manual", slo=None)
    assert executa("desligar", "m-job") == 0
    assert mundo.chamadas("systemctl") == [] and acervo.retiradas == {"m-job"}
    monkeypatch.delenv("PF_CADEIRA")
    assert executa("desligar", "m-job") == 2


# --- caidas -------------------------------------------------------------------------------------

def criados(mundo):
    return [c for c in mundo.chamadas("tarefas") if c["argv"][0] == "criar"]


def test_caidas_com_os_timers_de_manifesto_e_os_jobs_de_sessao_sai_0_sem_incidente(mundo, acervo, capsys):
    base_systemd(mundo, failed=["prior-secao.service", "platafirma-job-agente-3156-20260930T203558.service"])
    assert executa("caidas") == 0
    saida = capsys.readouterr().out
    assert "fora do bot: prior-secao.service failed (release conferir jobs mede)" in saida
    assert "platafirma-job" not in saida, "o job de sessão não vira nem linha informativa"
    assert saida.splitlines()[-1].startswith("conforme")
    assert mundo.chamadas("tarefas") == []


def test_unit_do_bot_failed_abre_incidente_com_a_cadeira_do_dono(mundo, acervo, capsys):
    acervo.poe("x-job", dono="dados")
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1
    (criar,) = criados(mundo)
    assert criar["argv"] == ["criar", "x-job: caída", "--incidente", "--cadeira", "dados", "--desc-stdin"]
    assert "unit x-job.service failed" in criar["stdin"]
    listagens = [c["argv"] for c in mundo.chamadas("tarefas") if c["argv"][0] == "listar"]
    assert listagens == [["listar", "--estado", e] for e in ("detectado", "em-mitigacao", "mitigado")], \
        "uma chamada por estado e sem --cadeira: --estado repetido pode ser last-wins, e a lista do bin diverge da API"
    assert "item 9001 criado: x-job: caída" in capsys.readouterr().out


def test_caidas_nao_duplica_incidente_aberto_de_mesmo_titulo(mundo, acervo, capsys):
    acervo.poe("x-job")
    mundo.unit_do_bot("x-job")
    mundo.abre_incidentes((3204, "host: SSD travou"), (3300, "x-job: caída"))
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1, "continua divergente: o incidente existe, a unit segue caída"
    assert criados(mundo) == []
    assert "incidente já aberto" in capsys.readouterr().out


def test_titulo_parecido_nao_conta_como_incidente_aberto(mundo, acervo):
    acervo.poe("x-job")
    mundo.unit_do_bot("x-job")
    mundo.abre_incidentes((3300, "x-job: caída ontem"), (3301, "outro-x-job: caída"), (3302, "x-job: caida"))
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1
    assert len(criados(mundo)) == 1


def test_estado_caida_do_acervo_abre_incidente_para_o_dono_sem_unit_failed(mundo, acervo, capsys):
    acervo.poe("x-job", dono="ia")
    acervo.estado_forcado["x-job"] = "caida"
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1
    (criar,) = criados(mundo)
    assert criar["argv"][1:5] == ["x-job: caída", "--incidente", "--cadeira", "ia"]
    assert "estado caida no acervo" in criar["stdin"]


def test_unit_failed_e_estado_caida_do_mesmo_slug_viram_um_incidente_so(mundo, acervo):
    acervo.poe("x-job")
    acervo.estado_forcado["x-job"] = "caida"
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, failed=["x-job.service", "x-job.timer"], timers=["x-job.timer"],
                 units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1
    assert len(criados(mundo)) == 1


def test_unit_do_bot_com_ficha_ativa_e_de_pe_e_conforme(mundo, acervo):
    acervo.poe("x-job")
    acervo.grava_evento("x-job", "fim", 0)
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 0
    assert mundo.chamadas("tarefas") == []


def test_unit_orfa_do_bot_vai_a_ti_e_timer_mais_service_sao_um_achado(mundo, acervo):
    mundo.unit_do_bot("orfa")                             # cabeçalho do bot, sem ficha ativa: sem declarante
    base_systemd(mundo, failed=["orfa.service"], timers=["orfa.timer"], units_extra=frag_do_bot(mundo, "orfa"))
    assert executa("caidas") == 1
    (criar,) = criados(mundo)
    assert criar["argv"][1:5] == ["orfa.timer: caída", "--incidente", "--cadeira", "ti"]
    assert "sem declarante" in criar["stdin"]


def test_unit_sem_cabecalho_e_sem_manifesto_tambem_e_orfa(mundo, acervo):
    conta = mundo.casa / ".config" / "systemd" / "user"          # solta na pasta de unit da conta: sem declarante
    conta.mkdir(parents=True)
    (conta / "estranho.timer").write_text("[Timer]\n")
    base_systemd(mundo, timers=["estranho.timer"], units_extra={"estranho.timer": {"FragmentPath": str(conta / "estranho.timer")}})
    assert executa("caidas") == 1
    (criar,) = criados(mundo)
    assert criar["argv"][1:5] == ["estranho.timer: caída", "--incidente", "--cadeira", "ti"]


def test_caidas_nao_olhou_o_systemd_sai_5(mundo, acervo, capsys):
    base_systemd(mundo, quebrado=True)
    assert executa("caidas") == 5
    assert "não consegui olhar" in capsys.readouterr().err
    assert mundo.chamadas("tarefas") == []


def test_caidas_nao_olhou_o_servico_sai_5(mundo, acervo, capsys):
    acervo.fora = True
    base_systemd(mundo)
    assert executa("caidas") == 5
    assert "não consegui olhar" in capsys.readouterr().err
    assert mundo.chamadas("tarefas") == []


def test_caidas_com_declarantes_ilegiveis_sai_5(mundo, acervo, capsys):
    (mundo.checkout / "deploy-harness" / "instalar").unlink()
    base_systemd(mundo)
    assert executa("caidas") == 5
    assert "ilegivel" in capsys.readouterr().err


def test_caidas_sem_poder_listar_incidentes_nao_cria_nenhum_e_sai_5(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    monkeypatch.setenv("STUB_TAREFAS_LISTAR_EXIT", "1")
    assert executa("caidas") == 5
    assert criados(mundo) == [], "sem saber o que está aberto, duplicar é pior"


def test_caidas_que_nao_consegue_abrir_o_incidente_segue_divergente_com_a_causa(mundo, acervo, monkeypatch, capsys):
    acervo.poe("x-job")
    mundo.unit_do_bot("x-job")
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    monkeypatch.setenv("STUB_TAREFAS_CRIAR_EXIT", "1")
    assert executa("caidas") == 1
    err = capsys.readouterr().err
    assert "incidente não aberto" in err and "tarefas criar saiu 1" in err


# --- o gerador, a ajuda e o ato desconhecido -----------------------------------------------------

def test_gerador_e_deterministico_byte_a_byte_e_fixa_o_que_a_ronda_cobra():
    decl = {"slug": "x-job", "trigger_tipo": "timer", "trigger_arg": CAL}
    a, b = units.gera_unit(decl), units.gera_unit(dict(decl))
    assert a == b
    servico, timer = a
    assert servico.splitlines()[0] == timer.splitlines()[0] == GERADO
    assert "ExecStart=/opt/platafirma/current/harness/bin/bot rodar x-job" in servico.splitlines()
    assert f"EnvironmentFile={ENV_OPS}" in servico.splitlines()
    assert f"OnCalendar={CAL}" in timer.splitlines() and "Unit=x-job.service" in timer.splitlines()
    assert servico.endswith("\n") and timer.endswith("\n")
    for texto in (servico, timer):
        assert units.eh_unit_do_bot(texto)
    with pytest.raises(ValueError):
        units.gera_unit({**decl, "trigger_arg": f"{CAL}\nExecStart=/bin/sh"})


def test_ato_desconhecido_sai_2_e_a_ajuda_lista_os_cinco_atos(mundo, acervo, capsys):
    assert executa("parar", "x-job") == 2
    assert "ato desconhecido" in capsys.readouterr().err
    assert executa("--ajuda") == 0
    saida = capsys.readouterr().out
    for ato in ("declarar", "listar", "rodar", "desligar", "caidas"):
        assert ato in saida
    assert executa("declarar", "--help") == 0
    assert "--slo" in capsys.readouterr().out
    assert acervo.chamadas == []


# --- a revisão do card #3186: SIGPIPE, unit alheia, calendário, recursão, incidente, trava, SIGTERM, órfã --------

@pytest.fixture
def sigpipe_padrao():
    """O que bin/_acervo/registrar faz no import quando outro arquivo da mesma sessão o carrega (test_casa_arvore)."""
    anterior = signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    yield
    signal.signal(signal.SIGPIPE, anterior)


def test_o_duble_ignora_sigpipe_mesmo_com_o_padrao_do_registrar_e_devolve_ao_fim(sigpipe_padrao, mundo, acervo):
    assert signal.getsignal(signal.SIGPIPE) == signal.SIG_IGN


def _segura(mundo, nome):
    """Outra execução do bot segurando a trava (flock no arquivo sob XDG_RUNTIME_DIR)."""
    fd = os.open(mundo.run / f"bot-{nome}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


# unit alheia, antes do PUT (só com timer)

@pytest.mark.parametrize("slug", ["sinal", "motor-trim", "prior-secao"])
def test_slug_de_manifesto_com_timer_sai_4_antes_do_put_com_a_unit_fora_da_pasta_do_bot(mundo, acervo, capsys, slug):
    assert declara(slug=slug) == 4
    assert "já existe e não é do bot" in capsys.readouterr().err
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir()) and mundo.chamadas("systemctl") == []


def test_slug_de_job_de_sessao_sai_4_antes_do_put(mundo, acervo, capsys):
    assert declara(slug="platafirma-job-x") == 4
    assert "platafirma-job-" in capsys.readouterr().err
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


def test_erro_de_uso_vem_antes_da_recusa_de_unit_alheia(mundo, acervo):
    assert declara(slug="sinal", slo=None) == 2
    assert acervo.chamadas == []


def test_sem_timer_nao_ha_unit_para_disputar_e_o_systemctl_nem_e_chamado(mundo, acervo):
    mundo.systemd(quebrado=True)
    assert declara(slug="sinal", trigger="manual", slo=None) == 0
    assert mundo.chamadas("systemctl-show") == []


def test_unit_ja_carregada_de_arquivo_sem_o_cabecalho_do_bot_sai_4_antes_do_put(mundo, acervo, capsys):
    alheia = mundo.tmp / "alheia" / "x-job.timer"
    alheia.parent.mkdir()
    alheia.write_text("[Timer]\n")
    mundo.systemd(units={"x-job.timer": {"FragmentPath": str(alheia)}})
    assert declara() == 4
    assert "está carregada de" in capsys.readouterr().err
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())
    assert ["--user", "show", "x-job.timer", "-p", "LoadState,FragmentPath"] in [c["argv"] for c in mundo.chamadas("systemctl-show")]


def test_unit_transiente_carregada_sem_arquivo_tambem_e_alheia(mundo, acervo):
    mundo.systemd(units={"x-job.service": {"FragmentPath": ""}})
    assert declara() == 4
    assert acervo.chamadas == []


def test_unit_carregada_do_proprio_bot_e_livre_e_o_not_found_tambem(mundo, acervo):
    assert declara() == 0                                          # not-found: livre
    mundo.systemd(units=frag_do_bot(mundo, "x-job"))
    assert declara() == 0                                          # carregada, com o cabeçalho do bot: livre


def test_systemctl_ilegivel_antes_do_put_sai_5_e_a_ficha_nao_nasce(mundo, acervo):
    mundo.systemd(quebrado=True)
    assert declara() == 5
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


def test_systemctl_show_passa_timeout_30_ao_sh_e_o_124_vira_motivo(monkeypatch):
    vistos = []

    def falso(args, timeout=None):
        vistos.append((args, timeout))
        return 0, "LoadState=loaded\nFragmentPath=/x/y.timer", ""

    monkeypatch.setattr(units, "sh", falso)
    assert units.systemctl_show("y.timer", ["LoadState", "FragmentPath"]) == (
        {"LoadState": "loaded", "FragmentPath": "/x/y.timer"}, None)
    assert vistos == [(["systemctl", "--user", "show", "y.timer", "-p", "LoadState,FragmentPath"], 30)]
    monkeypatch.setattr(units, "sh", lambda args, timeout=None: (124, "", f"systemctl passou de {timeout}s sem resposta"))
    assert units.systemctl_show("y.timer", ["LoadState"]) == (None, "systemctl passou de 30s sem resposta")


def test_systemctl_que_nao_responde_em_declarar_com_timer_sai_5_antes_do_put(mundo, acervo, monkeypatch, capsys):
    real, show = units.sh, []

    def sh_mudo(args, timeout=None):
        if args[:3] == ["systemctl", "--user", "show"]:
            show.append(timeout)
            return 124, "", f"systemctl passou de {timeout}s sem resposta"      # o rc que o sh devolve no timeout
        return real(args, timeout=timeout)

    monkeypatch.setattr(units, "sh", sh_mudo)
    assert declara() == 5
    assert "systemctl --user show x-job.timer: systemctl passou de 30s sem resposta" in capsys.readouterr().err
    assert show == [30], "o show leva o teto de 30 s; sem ele o systemctl preso seguraria a trava para sempre"
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


def test_declarantes_ilegiveis_antes_do_put_sai_5(mundo, acervo):
    (mundo.checkout / "deploy-harness" / "instalar").unlink()
    assert declara() == 5
    assert acervo.chamadas == []


def test_link_do_wants_que_nao_e_de_unit_do_bot_nao_se_troca(mundo, acervo, capsys):
    alheia = mundo.tmp / "alheia.timer"
    alheia.write_text("[Timer]\n")
    wants = mundo.pasta / "timers.target.wants"
    wants.mkdir()
    (wants / "x-job.timer").symlink_to(alheia)
    assert declara() == 4
    assert "não troco" in capsys.readouterr().err
    assert os.readlink(wants / "x-job.timer") == str(alheia)
    assert mundo.chamadas("systemctl") == []


def test_link_velho_que_aponta_para_unit_do_bot_e_trocado(mundo, acervo):
    velha = mundo.tmp / "velha"
    velha.mkdir()
    (velha / "x-job.timer").write_text(units.gera_unit({"slug": "x-job", "trigger_arg": CAL})[1])
    wants = mundo.pasta / "timers.target.wants"
    wants.mkdir()
    (wants / "x-job.timer").symlink_to(velha / "x-job.timer")
    assert declara() == 0
    assert os.readlink(wants / "x-job.timer") == str(mundo.pasta / "x-job.timer")


# calendário

def test_calendario_que_o_systemd_analyze_recusa_sai_2_antes_do_put(mundo, acervo, capsys):
    assert declara(trigger="timer:amanha as 9") == 2
    assert "recusado pelo systemd-analyze" in capsys.readouterr().err
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())
    assert [c["argv"] for c in mundo.chamadas("systemd-analyze")] == [["--user", "calendar", "amanha as 9"]]


@pytest.mark.parametrize("cal", ["--help", "--version", "-h", "-x *-*-* 06:45"])
def test_calendario_que_comeca_com_hifen_sai_2_sem_chamar_o_systemd_analyze_nem_o_put(mundo, acervo, capsys, cal):
    """Posicional, `--help` seria lido como opção e sairia 0 sem validar nada (o dublê de systemd-analyze faz o mesmo)."""
    assert declara(trigger=f"timer:{cal}") == 2
    assert "começa com hífen" in capsys.readouterr().err
    assert mundo.chamadas("systemd-analyze") == []
    assert [c for c in acervo.chamadas if c["metodo"] == "PUT"] == [] and acervo.chamadas == []
    assert not list(mundo.pasta.iterdir()) and mundo.chamadas("systemctl") == []


def test_calendario_valido_e_medido_pelo_systemd_analyze_antes_do_put(mundo, acervo):
    assert declara() == 0
    seq = mundo.sequencia()
    assert seq.index("systemd-analyze") < seq.index("PUT /acervo/automacoes/x-job")


@pytest.mark.parametrize("cal", ["2099-01-01 \\", "*-*-* %H:00"])
def test_barra_invertida_e_porcento_no_calendario_saem_2_sem_put(mundo, acervo, cal):
    assert declara(trigger=f"timer:{cal}") == 2
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())
    with pytest.raises(ValueError):
        units.gera_unit({"slug": "x-job", "trigger_tipo": "timer", "trigger_arg": cal})


def test_sem_o_binario_systemd_analyze_sai_3_nomeando_o_binario(mundo, acervo, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(mundo.tmp / "sem-nada"))
    assert declara() == 3
    assert "systemd-analyze" in capsys.readouterr().err
    assert acervo.chamadas == []


def test_manual_nao_consulta_o_systemd_analyze(mundo, acervo):
    assert declara(trigger="manual", slo=None) == 0
    assert mundo.chamadas("systemd-analyze") == []


# recursão

@pytest.mark.parametrize("roda", ["bot rodar loop", "/opt/platafirma/current/harness/bin/bot rodar loop"])
def test_declarar_roda_bot_rodar_sai_4_sem_tocar_o_servico(mundo, acervo, capsys, roda):
    assert declara(slug="loop", roda=roda) == 4
    assert "não roda a si mesmo" in capsys.readouterr().err
    assert declara(slug="loop", roda=roda, trigger="manual", slo=None) == 4
    assert acervo.chamadas == [] and not list(mundo.pasta.iterdir())


@pytest.mark.parametrize("roda", ["bot caidas", "bot listar --json", "bot desligar x-job"])
def test_declarar_roda_bot_que_nao_e_rodar_com_timer_chega_ao_put_e_escreve_a_unit(mundo, acervo, roda):
    acervo.verbos.add("bot")                                       # o serviço de verdade conhece o verbo bot
    assert declara(slug="ronda", roda=roda) == 0
    (put,) = [c for c in acervo.chamadas if c["metodo"] == "PUT"]
    assert put["corpo"]["roda_ref"] == "bot" and put["corpo"]["roda_args"] == roda.split()[1:]
    servico = (mundo.pasta / "ronda.service").read_text().splitlines()
    assert servico[0] == GERADO and "ExecStart=/opt/platafirma/current/harness/bin/bot rodar ronda" in servico
    assert units.eh_unit_do_bot((mundo.pasta / "ronda.timer").read_text())


def test_rodar_poe_o_slug_na_cadeia_do_filho_e_acrescenta_a_herdada(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    assert executa("rodar", "x-job") == 0
    assert mundo.chamadas("faz")[0]["cadeia"] == "x-job"
    monkeypatch.setenv("PF_BOT_SLUGS", "a-job,b-job")
    assert executa("rodar", "x-job") == 0
    assert mundo.chamadas("faz")[1]["cadeia"] == "a-job,b-job,x-job"
    assert os.environ["PF_BOT_SLUGS"] == "a-job,b-job", "o ambiente do próprio bot não muda"


def test_rodar_slug_ja_na_cadeia_sai_4_antes_de_gravar_inicio(mundo, acervo, monkeypatch, capsys):
    acervo.poe("x-job")
    monkeypatch.setenv("PF_BOT_SLUGS", "a-job,x-job")
    assert executa("rodar", "x-job") == 4
    assert "recursão" in capsys.readouterr().err
    assert acervo.chamadas == [] and acervo.eventos == [] and mundo.chamadas("faz") == []


def test_ciclo_a_b_a_e_cortado_na_terceira_volta(mundo, acervo):
    acervo.poe("a-job", roda_ref="bot", roda_args=["rodar", "b-job"])
    acervo.poe("b-job", roda_ref="bot", roda_args=["rodar", "a-job"])
    p = processo("rodar", "a-job")
    assert p.returncode == 4, p.stdout + p.stderr
    assert [(e["fonte"], e["tipo"], e.get("exit_code")) for e in acervo.eventos] == [
        ("a-job", "inicio", None), ("b-job", "inicio", None), ("b-job", "fim", 4), ("a-job", "fim", 4)]


# incidente sem duplicar

def test_incidente_aberto_em_qualquer_dos_tres_estados_nao_duplica_com_rastreador_last_wins(mundo, acervo):
    estados = {"a-job": "detectado", "b-job": "em-mitigacao", "c-job": "mitigado"}
    extra = {}
    for i, (slug, estado) in enumerate(estados.items()):
        acervo.poe(slug)
        mundo.unit_do_bot(slug)
        extra.update(frag_do_bot(mundo, slug))
    mundo.abre_incidentes(*[(i, f"{s}: caída", e) for i, (s, e) in enumerate(estados.items())])
    base_systemd(mundo, failed=[f"{s}.service" for s in estados], timers=[f"{s}.timer" for s in estados], units_extra=extra)
    assert executa("caidas") == 1
    assert criados(mundo) == [], "o incidente de qualquer estado aberto já existe"


def test_incidente_fechado_nao_conta_como_aberto(mundo, acervo):
    acervo.poe("x-job")
    mundo.unit_do_bot("x-job")
    mundo.abre_incidentes((7, "x-job: caída", "resolvido"))
    base_systemd(mundo, failed=["x-job.service"], timers=["x-job.timer"], units_extra=frag_do_bot(mundo, "x-job"))
    assert executa("caidas") == 1
    assert len(criados(mundo)) == 1


# exclusão mútua

def test_declarar_com_a_trava_presa_sai_5_sem_put_e_segue_quando_a_trava_cai(mundo, acervo, monkeypatch, capsys):
    monkeypatch.setattr(bot, "ESPERA_TRAVA_S", 0.2)
    fd = _segura(mundo, "units")
    try:
        assert declara() == 5
        assert "segura" in capsys.readouterr().err and acervo.chamadas == []
    finally:
        os.close(fd)
    assert declara() == 0


def test_desligar_com_a_trava_presa_sai_5_sem_tocar_o_servico(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    monkeypatch.setattr(bot, "ESPERA_TRAVA_S", 0.2)
    fd = _segura(mundo, "units")
    try:
        assert executa("desligar", "x-job") == 5
        assert acervo.chamadas == []
    finally:
        os.close(fd)
    assert executa("desligar", "x-job") == 0


def test_caidas_com_a_trava_presa_sai_5_sem_ler_nem_criar(mundo, acervo, monkeypatch):
    monkeypatch.setattr(bot, "ESPERA_TRAVA_S", 0.2)
    fd = _segura(mundo, "caidas")
    try:
        assert executa("caidas") == 5
        assert acervo.chamadas == [] and mundo.chamadas() == []
    finally:
        os.close(fd)


def test_link_criado_por_outra_execucao_no_meio_e_sucesso_e_o_apontado_para_outro_lugar_e_4(mundo, acervo, monkeypatch):
    real = Path.symlink_to

    def corrida(self, alvo, *a, **k):
        real(self, alvo, *a, **k)
        raise FileExistsError(17, "File exists", str(self))

    monkeypatch.setattr(Path, "symlink_to", corrida)
    assert declara() == 0
    assert os.readlink(mundo.pasta / "timers.target.wants" / "x-job.timer") == str(mundo.pasta / "x-job.timer")

    def corrida_alheia(self, alvo, *a, **k):
        real(self, mundo.tmp / "outro.timer", *a, **k)
        raise FileExistsError(17, "File exists", str(self))

    monkeypatch.setattr(Path, "symlink_to", corrida_alheia)
    assert declara(slug="y-job") == 4


# SIGTERM e desligar

def test_rodar_com_sigterm_repassa_ao_filho_grava_fim_143_e_sai_143(mundo, acervo, monkeypatch):
    acervo.poe("x-job")
    marca = mundo.tmp / "dorme"
    monkeypatch.setenv("STUB_FAZ_DORME", str(marca))
    p = subprocess.Popen([sys.executable, str(BOT), "rodar", "x-job"], env=os.environ.copy(),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(500):
            if marca.exists():
                break
            time.sleep(0.02)
        assert marca.exists(), "o job não chegou a começar"
        p.send_signal(signal.SIGTERM)
        out, err = p.communicate(timeout=15)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    assert p.returncode == 143, out + err
    assert Path(f"{marca}.term").exists(), "o filho recebeu o SIGTERM"
    assert [(e["tipo"], e.get("exit_code")) for e in acervo.eventos] == [("inicio", None), ("fim", 143)]


def test_desligar_acha_a_unit_em_outra_morada_e_limpa_o_wants_de_la(mundo, acervo, capsys):
    acervo.poe("x-job")
    dados = mundo.casa / ".local" / "share" / "systemd" / "user"
    dados.mkdir(parents=True)
    servico, timer = units.gera_unit({"slug": "x-job", "trigger_arg": CAL})
    (dados / "x-job.service").write_text(servico)
    (dados / "x-job.timer").write_text(timer)
    wants = mundo.casa / ".config" / "systemd" / "user" / "timers.target.wants"
    wants.mkdir(parents=True)
    (wants / "x-job.timer").symlink_to(dados / "x-job.timer")
    assert executa("desligar", "x-job") == 0
    assert not list(dados.glob("x-job*")) and not os.path.lexists(wants / "x-job.timer")
    assert "units removidas: x-job.service, x-job.timer" in capsys.readouterr().out
    assert ["stop x-job.timer", "stop x-job.service"] == [s for s in mundo.sequencia() if s.startswith("stop")]
    assert acervo.retiradas == {"x-job"}


# o universo de órfã

def test_unit_failed_transiente_de_run_de_etc_ou_de_pacote_vira_so_linha_informativa(mundo, acervo, capsys):
    fora = {"run-r1a2b.service": "", "run-x.service": "/run/user/1000/systemd/transient/run-x.service",
            "etc-job.service": "/etc/systemd/user/etc-job.service", "pacote.service": "/usr/lib/systemd/user/pacote.service"}
    base_systemd(mundo, failed=list(fora), units_extra={u: {"FragmentPath": f} for u, f in fora.items()})
    assert executa("caidas") == 0
    saida = capsys.readouterr().out
    for u in fora:
        assert f"fora do bot: {u} failed" in saida
    assert mundo.chamadas("tarefas") == []


def test_unit_failed_solta_nas_pastas_do_usuario_sem_declarante_continua_orfa(mundo, acervo):
    soltas = {"solta-a.service": mundo.casa / ".config" / "systemd" / "user",
              "solta-b.service": mundo.casa / ".local" / "share" / "systemd" / "user"}
    extra = {}
    for nome, pasta in soltas.items():
        pasta.mkdir(parents=True)
        (pasta / nome).write_text("[Service]\n")
        extra[nome] = {"FragmentPath": str(pasta / nome)}
    base_systemd(mundo, failed=list(soltas), units_extra=extra)
    assert executa("caidas") == 1
    assert sorted(c["argv"][1] for c in criados(mundo)) == ["solta-a.service: caída", "solta-b.service: caída"]


def test_caidas_cria_no_maximo_dez_incidentes_por_rodada_e_conta_o_resto(mundo, acervo, capsys):
    conta = mundo.casa / ".config" / "systemd" / "user"
    conta.mkdir(parents=True)
    nomes = [f"solta{i:02d}.service" for i in range(12)]
    for n in nomes:
        (conta / n).write_text("[Service]\n")
    base_systemd(mundo, failed=nomes, units_extra={n: {"FragmentPath": str(conta / n)} for n in nomes})
    assert executa("caidas") == 1
    assert len(criados(mundo)) == 10
    saida = capsys.readouterr().out
    assert "limite: 2 achado(s) sem incidente nesta rodada" in saida
    assert "solta10.service: caída, solta11.service: caída" in saida


# âncora de fim de linha nos moldes

@pytest.mark.parametrize("ato", ["declarar", "rodar", "desligar"])
def test_slug_com_quebra_de_linha_no_fim_sai_2_sem_tocar_o_servico(mundo, acervo, ato):
    if ato == "declarar":
        assert declara(slug="foo\n") == 2
    else:
        assert executa(ato, "foo\n") == 2
    assert acervo.chamadas == []
    with pytest.raises(ValueError):
        units.nomes_da_unit("foo\n")


def test_roda_ref_com_quebra_de_linha_no_fim_e_recusado_sem_executar(mundo, acervo):
    acervo.poe("x-job", roda_ref="faz\n")
    assert executa("rodar", "x-job") == 4
    assert mundo.chamadas("faz") == [] and acervo.eventos == []


def test_sha_com_quebra_de_linha_no_fim_nao_vira_campo_do_evento(mundo, acervo):
    acervo.poe("x-job")
    torto = mundo.tmp / "opt" / "platafirma-harness" / f"{SHA}\n"
    torto.mkdir()
    (mundo.rel / "harness").unlink()
    (mundo.rel / "harness").symlink_to(torto)
    assert executa("rodar", "x-job") == 0
    assert all("sha" not in e for e in acervo.eventos)
