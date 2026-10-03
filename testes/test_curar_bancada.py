"""#3187: `curar --reextrair <lista> --bancada <pasta>` contra um servidor HTTP falso do CONTRATO.

O servidor falso (http.server em thread, loopback, porta livre) implementa
POST /acervo/obras/{id}/conversoes como o card descreve: 200 com {relatorio, arquivos} mesmo
quando a conversão reprovou ou o método falhou; 404 obra inexistente; 422 método indisponível;
5xx imprevisto. `curar` roda como subprocesso (importa `requests`, que o venv de teste pode não
ter: usa-se o primeiro python que tenha). "bancada" aqui é só a pasta de saída da linha de comando.

Situações por obra (revisão 2): ok | reprovada | n/a | falha | erro | já feito.
  falha = o MÉTODO falhou (200 com relatorio.erro e erro_tipo conversao/timeout/subprocesso/ausente):
          é DADO (grava relatorio.json, conta como feita, exit 0);
  erro  = a obra NÃO foi obtida (HTTP 4xx/5xx, rede, título, erro_tipo indisponivel, gravação,
          conferência): exit 1, nunca marca feito.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def U(n: int) -> str:
    """uuid de teste; os 8 primeiros caracteres identificam a obra na saída."""
    return f"{n:08x}-0000-4000-8000-000000000000"


# ------------------------------------------------------------------ corpos do contrato

def md_e_indice(oid: str):
    md = f"# Obra {oid[:8]}\n\ncorpo em português: ação, coração\n"
    indice = json.dumps({"secoes": [{"ancora": "a"}]}, ensure_ascii=False, indent=2) + "\n"
    return md, indice


def _relatorio(oid, metodo, md=None, indice=None, **over):
    rel = {
        "versao_relatorio": 1, "gerado_em": "2026-09-28T12:00:00Z", "obra_id": oid, "titulo": "T",
        "objeto": "acervo/abc", "arquivo": "norma.pdf", "metodo": metodo, "aplicavel": True,
        "tipo": "application/pdf", "tipo_por": "assinatura", "classe": "B", "bytes_origem": 1234,
        "reprovado": False, "causa": None, "criterio": None,
        "cabecalho": {"blocos": 812, "papeis": {"paragrafo": 600}, "substituicoes": 0},
        "fidelidade": {"aplicavel": True, "classe": "B", "tamanho_referencia": 250000,
                       "perda": {"paragrafo": 12, "titulo": 3}, "insercao": {"paragrafo": 3},
                       "duplicacao": {}, "ordem": 0, "irrecuperavel": 0, "erro": None},
        "tempos_ms": {"converter": 1234, "total": 2200},
        "erro": None, "erro_tipo": None,
    }
    if md is not None:
        rel["sha256_md"] = hashlib.sha256(md.encode("utf-8")).hexdigest()
        rel["bytes_md"] = len(md.encode("utf-8"))
    if indice is not None:
        rel["sha256_indice"] = hashlib.sha256(indice.encode("utf-8")).hexdigest()
        rel["bytes_indice"] = len(indice.encode("utf-8"))
    rel.update(over)
    return rel


def corpo_ok(oid, metodo="perfil", **over):
    md, indice = md_e_indice(oid)
    return 200, {"ato": "converter-em-bancada", "obra_id": oid, "titulo": "T", "objeto": "acervo/abc",
                 "relatorio": _relatorio(oid, metodo, md, indice, **over),
                 "arquivos": {"espelho.md": md, "indice.json": indice}}


def corpo_reprovada(oid, metodo="perfil"):
    return corpo_ok(oid, metodo, reprovado=True, causa="portao construcao: sem blocos de corpo")


def corpo_na(oid, metodo="perfil"):   # o `metodo` do relatório é o pedido; n/a vale para qualquer um
    rel = _relatorio(oid, metodo, aplicavel=False, tipo="application/x-mobipocket-ebook", arquivo="l.mobi",
                     classe="C", cabecalho=None,
                     fidelidade={"aplicavel": False, "classe": "C", "motivo": "sem R",
                                 "tamanho_referencia": None})
    return 200, {"ato": "converter-em-bancada", "obra_id": oid, "relatorio": rel}


def corpo_sha_diverge(oid, metodo="perfil"):
    status, corpo = corpo_ok(oid, metodo)
    corpo["relatorio"]["sha256_md"] = "0" * 64
    return status, corpo


def corpo_bytes_diverge(oid, metodo="perfil"):
    status, corpo = corpo_ok(oid, metodo)
    corpo["relatorio"]["bytes_indice"] += 1
    return status, corpo


def corpo_falha(oid, metodo="perfil", erro_tipo="timeout", texto="timeout de 900s na conversão"):
    """200 com relatorio.erro: o MÉTODO falhou nesta obra. erro_tipo=None = relatório antigo (sem o campo)."""
    rel = _relatorio(oid, metodo, erro=texto, erro_tipo=erro_tipo, cabecalho=None, fidelidade=None)
    if erro_tipo is None:
        del rel["erro_tipo"]
    return 200, {"ato": "converter-em-bancada", "obra_id": oid, "relatorio": rel}


def corpo_indisponivel(oid, metodo="docling"):
    """200 com erro_tipo indisponivel: o método NÃO roda no ambiente do servidor (não é resultado)."""
    return corpo_falha(oid, metodo, erro_tipo="indisponivel", texto="docling não instalado no servidor")


def corpo_medida_indeterminada(oid, metodo="perfil", **over):
    """A conversão vale; a MEDIDA de fidelidade é que estourou o prazo."""
    fid = {"aplicavel": True, "classe": "B", "tamanho_referencia": 250000, "perda": {}, "insercao": {},
           "duplicacao": {}, "ordem": 0, "irrecuperavel": 0,
           "erro": "timeout de 900s na medida de fidelidade"}
    return corpo_ok(oid, metodo, fidelidade=fid, **over)


def devagar(segundos, resposta):
    """cenário que demora `segundos` antes de responder."""
    def cenario(_corpo):
        time.sleep(segundos)
        return resposta
    return cenario


# ------------------------------------------------------------------ servidor falso

class Falso:
    def __init__(self):
        self.cenarios = {}   # obra_id -> (status, obj) | callable(corpo_do_post) -> (status, obj)
        self.titulos = {}    # título -> (obra_id, casamento)
        self.atraso_get = 0  # segundos antes de responder o GET de título
        self.chamadas = []   # (verbo, caminho, corpo, cabeçalhos em minúsculas)
        falso = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _resp(self, status, obj):
                dados = obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                try:
                    self.wfile.write(dados)
                except OSError:      # o cliente desistiu (timeout): normal nos testes de prazo
                    pass

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                cab = {k.lower(): v for k, v in self.headers.items()}
                falso.chamadas.append(("POST", self.path, corpo, cab))
                m = re.match(r"^/acervo/obras/([^/]+)/conversoes$", self.path)
                if m:
                    cen = falso.cenarios.get(m.group(1))
                    if cen is None:
                        return self._resp(404, {"title": "ObraNaoEncontrada", "status": 404,
                                                "detail": "obra inexistente"})
                    status, obj = cen(corpo) if callable(cen) else cen
                    return self._resp(status, obj)
                m = re.match(r"^/acervo/obras/([^/]+)/reextracoes$", self.path)
                if m:
                    return self._resp(200, {"modo": "plano", "titulo": "T", "obra_id": m.group(1),
                                            "objeto": "acervo/abc", "metodo_alvo": "perfil",
                                            "espelho_atual": None})
                self._resp(404, {"title": "RotaInexistente", "status": 404})

            def do_GET(self):
                cab = {k.lower(): v for k, v in self.headers.items()}
                falso.chamadas.append(("GET", self.path, None, cab))
                if falso.atraso_get:
                    time.sleep(falso.atraso_get)
                m = re.match(r"^/acervo/obras/([^/]+)/situacao", self.path)
                if m and unquote(m.group(1)) in falso.titulos:
                    oid, casamento = falso.titulos[unquote(m.group(1))]
                    return self._resp(200, {"obra_id": oid, "titulo": unquote(m.group(1)),
                                            "casamento": casamento})
                self._resp(404, {"title": "ObraNaoEncontrada", "status": 404,
                                 "detail": "sem essa obra"})

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()

    def posts(self):
        return [c for c in self.chamadas if c[0] == "POST" and c[1].endswith("/conversoes")]

    def parar(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def falso():
    f = Falso()
    yield f
    f.parar()


def _env(url):
    return {**os.environ, "MOTOR_ACERVO_URL": url, "RAG_API_TOKEN": "tok-teste",
            "PYTHONDONTWRITEBYTECODE": "1"}


def curar(url, *args, umask=None):
    return subprocess.run([PY, str(CURAR), *args], capture_output=True, text=True, env=_env(url),
                          timeout=120, check=False,
                          preexec_fn=(lambda: os.umask(umask)) if umask is not None else None)


# Roda o curar EM PROCESSO NOVO mas com o módulo carregado por um driver que executa `pre` (Python)
# antes de main(): serve para encurtar constantes de prazo e para observar chamadas (o servidor
# falso é que demora; nada de grep no fonte).
DRIVER = """
import atexit, importlib.machinery, importlib.util, json, os, sys
caminho, pre = sys.argv[1], sys.argv[2]
loader = importlib.machinery.SourceFileLoader("curar_teste", caminho)
spec = importlib.util.spec_from_loader("curar_teste", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
exec(pre, {"m": m, "sys": sys, "os": os, "json": json, "atexit": atexit})
sys.exit(m.main(sys.argv[3:]))
"""

REGISTRA_REQUESTS = """
import requests
_reg = []
_post, _get = requests.post, requests.get
def post(*a, **k):
    _reg.append(["POST", k.get("timeout")])
    return _post(*a, **k)
def get(*a, **k):
    _reg.append(["GET", k.get("timeout")])
    return _get(*a, **k)
requests.post, requests.get = post, get
atexit.register(lambda: open(os.environ["REG"], "w").write(json.dumps(_reg)))
"""


def curar_com(url, pre, tmp_path, *args):
    """(processo, registro) — `pre` pode gravar JSON em os.environ['REG'] via atexit."""
    reg = tmp_path / "reg.json"
    env = {**_env(url), "REG": str(reg)}
    r = subprocess.run([PY, "-c", DRIVER, str(CURAR), pre, *args], capture_output=True, text=True,
                       env=env, timeout=120, check=False)
    return r, (json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else None)


def por_obra(r):
    """{primeiros 8 do id: linha} das linhas por obra (as que não são o total)."""
    res = {}
    for linha in r.stdout.splitlines():
        if linha.startswith("total"):
            continue
        partes = linha.split()
        idx = 2 if linha.startswith("já feito") else 1
        res[partes[idx]] = linha
    return res


def total(r):
    return next(linha for linha in r.stdout.splitlines() if linha.startswith("total"))


def sem_tmp(pasta: Path):
    return [p for p in pasta.rglob("*") if p.name.startswith(".tmp-")] == []


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ------------------------------------------------------------------ o lote misto

def cenario_misto(falso):
    a, b, c, d, e, f, g = (U(i) for i in range(0xa, 0x11))
    falso.cenarios[a] = corpo_ok(a)
    falso.cenarios[b] = corpo_reprovada(b)
    falso.cenarios[c] = corpo_na(c)
    # d: sem cenário = 404
    falso.cenarios[e] = (500, {"title": "boom", "status": 500, "detail": "kaput"})
    falso.cenarios[f] = corpo_sha_diverge(f)
    falso.cenarios[g] = corpo_falha(g)
    return a, b, c, d, e, f, g


def test_lote_misto_cada_obra_no_seu_destino_e_uma_falha_nao_derruba_as_outras(falso, tmp_path):
    a, b, c, d, e, f, g = cenario_misto(falso)
    r = curar(falso.url, "--reextrair", ",".join([a, b, c, d, e, f, g]), "--bancada", str(tmp_path),
              "--autor", "engenharia")
    assert r.returncode == 1, r.stdout + r.stderr
    linhas = por_obra(r)
    assert len(linhas) == 7
    assert linhas[a[:8]].startswith("ok ")
    for pedaco in ("pdf", "classe=B", "blocos=812", "perda=15", "2200ms"):
        assert pedaco in linhas[a[:8]], linhas[a[:8]]
    assert linhas[b[:8]].startswith("reprovada") and "[portao construcao" in linhas[b[:8]]
    assert linhas[c[:8]].startswith("n/a ") and "blocos=-" in linhas[c[:8]] and "perda=-" in linhas[c[:8]]
    assert linhas[d[:8]].startswith("erro") and "404" in linhas[d[:8]]
    assert linhas[e[:8]].startswith("erro") and "500" in linhas[e[:8]] and "kaput" in linhas[e[:8]]
    assert linhas[f[:8]].startswith("erro") and "sha256" in linhas[f[:8]]
    assert linhas[g[:8]].startswith("falha") and "timeout de 900s" in linhas[g[:8]]
    assert total(r).startswith("total  7 obra(s)  ok=1  reprovada=1  n/a=1  falha=1  erro=3  já feito=0")

    base = tmp_path / "perfil"
    md, indice = md_e_indice(a)
    assert ler(base / a / "espelho.md") == md
    assert ler(base / a / "indice.json") == indice
    rel = json.loads(ler(base / a / "relatorio.json"))
    assert rel["versao_relatorio"] == 1 and rel["obra_id"] == a
    assert not (base / a / "erro.txt").exists()
    # reprovada: relatório e arquivos (reprovar é dado)
    assert (base / b / "relatorio.json").exists() and (base / b / "espelho.md").exists()
    # n/a: relatório sem arquivos
    assert (base / c / "relatorio.json").exists() and not (base / c / "espelho.md").exists()
    # 404 e 500: nada de relatório; a falha fica registrada ao lado
    for x, texto in ((d, "404"), (e, "500")):
        assert not (base / x / "relatorio.json").exists()
        assert texto in ler(base / x / "erro.txt")
    # divergência de sha (A3): o que gravou FICA, mas NÃO sobra relatorio.json válido — o relatório
    # recebido vai para relatorio.invalido.json e erro.txt diz o porquê
    assert (base / f / "espelho.md").exists() and (base / f / "indice.json").exists()
    assert not (base / f / "relatorio.json").exists()
    assert (base / f / "relatorio.invalido.json").exists()
    assert "sha256" in ler(base / f / "erro.txt")
    # falha do método (A1): o servidor devolveu o dado; relatório gravado, sem erro.txt, sem arquivos
    assert json.loads(ler(base / g / "relatorio.json"))["erro"] == "timeout de 900s na conversão"
    assert not (base / g / "erro.txt").exists() and not (base / g / "espelho.md").exists()
    assert sem_tmp(tmp_path)


def test_bytes_divergentes_do_indice_tambem_sao_erro(falso, tmp_path):
    x = U(0x20)
    falso.cenarios[x] = corpo_bytes_diverge(x)
    r = curar(falso.url, "--reextrair", x, "--bancada", str(tmp_path))
    assert r.returncode == 1
    erro = ler(tmp_path / "perfil" / x / "erro.txt")
    assert "indice.json" in erro and "bytes_indice" in erro
    assert (tmp_path / "perfil" / x / "indice.json").exists()
    assert not (tmp_path / "perfil" / x / "relatorio.json").exists()


def test_todas_obtidas_exit_0_reprovada_e_na_sao_dados(falso, tmp_path):
    a, b, c = U(1), U(2), U(3)
    falso.cenarios.update({a: corpo_ok(a), b: corpo_reprovada(b), c: corpo_na(c)})
    r = curar(falso.url, "--reextrair", f"{a}, {b} ,{c}", "--bancada", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert total(r).startswith("total  3 obra(s)  ok=1  reprovada=1  n/a=1  falha=0  erro=0")
    assert list(por_obra(r)) == [a[:8], b[:8], c[:8]]   # na ordem dada


# ------------------------------------------------------------------ A1: falha do método x obra não obtida

@pytest.mark.parametrize("erro_tipo", ["conversao", "timeout", "subprocesso", None])
def test_a1_falha_do_metodo_e_dado_exit_0_grava_conta_como_feita_e_a_retomada_pula(falso, tmp_path, erro_tipo):
    a = U(1)
    falso.cenarios[a] = corpo_falha(a, erro_tipo=erro_tipo)      # None = relatório antigo, vale conversao
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    r = curar(falso.url, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert por_obra(r)[a[:8]].startswith("falha "), r.stdout
    assert total(r).startswith("total  1 obra(s)  ok=0  reprovada=0  n/a=0  falha=1  erro=0  já feito=0")
    pasta = tmp_path / "perfil" / a
    assert json.loads(ler(pasta / "relatorio.json"))["erro"] and not (pasta / "erro.txt").exists()
    r2 = curar(falso.url, *args)                                   # retomada: já feito, sem novo POST
    assert r2.returncode == 0 and por_obra(r2)[a[:8]].startswith("já feito")
    assert len(falso.posts()) == 1


def test_a1_erro_tipo_indisponivel_nao_e_dado_e_erro_exit_1_sem_marcar_feito(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_indisponivel(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path), "--metodo", "docling")
    r = curar(falso.url, *args)
    assert r.returncode == 1, r.stdout + r.stderr
    linha = por_obra(r)[a[:8]]
    assert linha.startswith("erro") and "indisponível" in linha
    assert total(r).startswith("total  1 obra(s)  ok=0  reprovada=0  n/a=0  falha=0  erro=1")
    pasta = tmp_path / "docling" / a
    assert not (pasta / "relatorio.json").exists() and "indisponível" in ler(pasta / "erro.txt")
    r2 = curar(falso.url, *args)                                   # não ficou feito: tenta de novo
    assert r2.returncode == 1 and len(falso.posts()) == 2


def test_a1_erro_tipo_desconhecido_tambem_nao_e_dado(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_falha(a, erro_tipo="inventado")
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 1 and por_obra(r)[a[:8]].startswith("erro")
    assert not (tmp_path / "perfil" / a / "relatorio.json").exists()


def test_a1_relatorio_de_outra_versao_nao_e_obtido(falso, tmp_path):
    a = U(1)
    status, corpo = corpo_ok(a)
    corpo["relatorio"]["versao_relatorio"] = 3
    falso.cenarios[a] = (status, corpo)
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 1 and "versão" in por_obra(r)[a[:8]]
    assert not (tmp_path / "perfil" / a / "relatorio.json").exists()


def test_a1_relatorio_v2_do_servico_e_obtido_e_relido_como_integro(falso, tmp_path):
    # #3205: o conversor como serviço devolve versao_relatorio 2; é dado, grava e o refazer reconhece
    a = U(1)
    status, corpo = corpo_ok(a)
    corpo["relatorio"]["versao_relatorio"] = 2
    corpo["relatorio"].update(versao_imagem="b888ffa", paginas=3, prazo_s=150, pico_memoria_kb=1024)
    falso.cenarios[a] = (status, corpo)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    r = curar(falso.url, *args)
    assert r.returncode == 0 and por_obra(r)[a[:8]].startswith("ok")
    rel = json.loads(ler(tmp_path / "perfil" / a / "relatorio.json"))
    assert rel["versao_relatorio"] == 2 and rel["versao_imagem"] == "b888ffa"
    # sem --refazer a obra já está feita: o cliente reconhece o relatório v2 como íntegro
    r = curar(falso.url, *args)
    assert r.returncode == 0 and por_obra(r)[a[:8]].startswith("já feito")
    obra, = _agregador().agregar(str(tmp_path))["obras"]
    assert obra["perfil"]["estado"] == "medido"


# ------------------------------------------------------------------ A2: a medida falhou, a conversão não

@pytest.mark.parametrize("fabrica, situacao", [(corpo_medida_indeterminada, "ok "),
                                                (lambda o: corpo_medida_indeterminada(
                                                    o, reprovado=True, causa="portao x"), "reprovada")])
def test_a2_fidelidade_erro_e_dado_com_a_marca_medida_indeterminada(falso, tmp_path, fabrica, situacao):
    a, b = U(1), U(2)
    falso.cenarios.update({a: fabrica(a), b: corpo_ok(b)})
    args = ("--reextrair", f"{a},{b}", "--bancada", str(tmp_path))
    r = curar(falso.url, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    linhas = por_obra(r)
    assert linhas[a[:8]].startswith(situacao) and "medida-indeterminada" in linhas[a[:8]]
    assert "perda=-" in linhas[a[:8]]
    assert "medida-indeterminada" not in linhas[b[:8]]
    assert total(r).startswith("total  2 obra(s)")
    assert (tmp_path / "perfil" / a / "relatorio.json").exists()
    r2 = curar(falso.url, *args)                       # a retomada pula (refazer é decisão do operador)
    assert r2.returncode == 0 and len(falso.posts()) == 2
    assert all(linha.startswith("já feito") for linha in por_obra(r2).values())
    assert "medida-indeterminada" in por_obra(r2)[a[:8]]
    r3 = curar(falso.url, *args, "--refazer")
    assert len(falso.posts()) == 4 and r3.returncode == 0


def test_a2_json_traz_medida_indeterminada_true_so_na_obra_afetada(falso, tmp_path):
    a, b = U(1), U(2)
    falso.cenarios.update({a: corpo_medida_indeterminada(a), b: corpo_ok(b)})
    r = curar(falso.url, "--reextrair", f"{a},{b}", "--bancada", str(tmp_path), "--json")
    assert r.returncode == 0
    obras = {o["obra_id"]: o for o in json.loads(r.stdout)["obras"]}
    assert obras[a]["medida_indeterminada"] is True and obras[b]["medida_indeterminada"] is False
    assert obras[a]["situacao"] == "ok"


# ------------------------------------------------------------------ retomada e --refazer

def test_retomada_segunda_rodada_pula_o_que_ja_esta_feito(falso, tmp_path):
    a, b, c = U(1), U(2), U(3)
    falso.cenarios.update({a: corpo_ok(a), b: corpo_reprovada(b), c: corpo_na(c)})
    args = ("--reextrair", f"{a},{b},{c}", "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 0
    assert len(falso.posts()) == 3
    r = curar(falso.url, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(falso.posts()) == 3                       # nenhuma chamada nova
    assert all(linha.startswith("já feito") for linha in por_obra(r).values())
    assert total(r).startswith("total  3 obra(s)  ok=0  reprovada=0  n/a=0  falha=0  erro=0  já feito=3")


def test_refazer_converte_de_novo_mesmo_o_que_ja_estava_feito(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    curar(falso.url, *args)
    r = curar(falso.url, *args, "--refazer")
    assert r.returncode == 0 and len(falso.posts()) == 2
    assert por_obra(r)[a[:8]].startswith("ok ")


def test_retomada_refaz_so_o_que_falhou_e_limpa_erro_txt_e_invalido(falso, tmp_path):
    a, f, e = U(1), U(2), U(3)
    falso.cenarios.update({a: corpo_ok(a), f: corpo_sha_diverge(f), e: (503, {"detail": "fora"})})
    args = ("--reextrair", f"{a},{f},{e}", "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 1
    assert (tmp_path / "perfil" / f / "erro.txt").exists()
    assert (tmp_path / "perfil" / f / "relatorio.invalido.json").exists()
    falso.cenarios[f] = corpo_ok(f)            # o servidor consertou f
    falso.cenarios[e] = corpo_ok(e)            # e e voltou
    antes = len(falso.posts())
    r = curar(falso.url, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(falso.posts()) - antes == 2      # a não foi refeita
    linhas = por_obra(r)
    assert linhas[a[:8]].startswith("já feito")
    assert linhas[f[:8]].startswith("ok ") and linhas[e[:8]].startswith("ok ")
    for x in (f, e):
        assert (tmp_path / "perfil" / x / "relatorio.json").exists()
        assert not (tmp_path / "perfil" / x / "erro.txt").exists()
        assert not (tmp_path / "perfil" / x / "relatorio.invalido.json").exists()


def test_relatorio_valido_sem_os_arquivos_declarados_nao_conta_como_feito(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    curar(falso.url, *args)
    (tmp_path / "perfil" / a / "espelho.md").write_text("truncado", encoding="utf-8")
    r = curar(falso.url, *args)
    assert por_obra(r)[a[:8]].startswith("ok ") and len(falso.posts()) == 2


def test_a5_retomada_confere_o_sha256_e_nao_so_o_tamanho(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    curar(falso.url, *args)
    espelho = tmp_path / "perfil" / a / "espelho.md"
    original = espelho.read_bytes()
    corrompido = original.replace(b"corpo", b"CORPO")           # MESMO tamanho, conteúdo diferente
    assert len(corrompido) == len(original) and corrompido != original
    espelho.write_bytes(corrompido)
    r = curar(falso.url, *args)
    assert por_obra(r)[a[:8]].startswith("ok ") and len(falso.posts()) == 2
    assert espelho.read_bytes() == original                     # refeito
    r = curar(falso.url, *args)                                 # íntegro de novo: pula
    assert por_obra(r)[a[:8]].startswith("já feito") and len(falso.posts()) == 2


# ------------------------------------------------------------------ A3: nada de relatorio.json inválido

def test_a3_refazer_com_post_que_falha_nao_toca_o_relatorio_antigo_nem_escreve_erro_txt(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path), "--refazer")
    assert curar(falso.url, *args).returncode == 0
    pasta = tmp_path / "perfil" / a
    antes = {n: (pasta / n).read_bytes() for n in ("relatorio.json", "espelho.md", "indice.json")}
    falso.cenarios[a] = (500, {"detail": "kaput"})
    r = curar(falso.url, *args)
    assert r.returncode == 1 and por_obra(r)[a[:8]].startswith("erro") and "500" in r.stdout
    assert {n: (pasta / n).read_bytes() for n in antes} == antes
    assert not (pasta / "erro.txt").exists()
    # servidor fora do ar, idem
    falso.parar()
    r = curar(falso.url, *args)
    assert r.returncode == 1 and "rede:" in r.stdout
    assert {n: (pasta / n).read_bytes() for n in antes} == antes and not (pasta / "erro.txt").exists()
    falso.__init__()      # a fixture chama parar() no fim: dá-lhe um servidor vivo para parar


def test_a3_refazer_com_200_valido_mas_conferencia_falha_deixa_so_o_invalido(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path), "--refazer")
    assert curar(falso.url, *args).returncode == 0
    pasta = tmp_path / "perfil" / a
    assert (pasta / "relatorio.json").exists()
    falso.cenarios[a] = corpo_sha_diverge(a)
    r = curar(falso.url, *args)
    assert r.returncode == 1 and "sha256" in por_obra(r)[a[:8]]
    assert not (pasta / "relatorio.json").exists()                 # o antigo saiu, o novo não nasceu
    assert (pasta / "relatorio.invalido.json").exists() and "sha256" in ler(pasta / "erro.txt")
    assert (pasta / "espelho.md").exists()                         # o que já tinha sido gravado fica
    falso.cenarios[a] = corpo_ok(a)                                # sem --refazer: não está feito
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 0 and por_obra(r)[a[:8]].startswith("ok ")
    assert not (pasta / "erro.txt").exists() and not (pasta / "relatorio.invalido.json").exists()


def test_a3_arquivo_que_nao_veio_como_texto_tambem_invalida_sem_deixar_relatorio(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    curar(falso.url, *args)
    status, corpo = corpo_ok(a)
    corpo["arquivos"]["indice.json"] = 12345
    falso.cenarios[a] = (status, corpo)
    r = curar(falso.url, *args, "--refazer")
    assert r.returncode == 1 and "não veio como texto" in r.stdout
    assert not (tmp_path / "perfil" / a / "relatorio.json").exists()


def test_a3_ordem_de_gravacao_relatorio_antigo_sai_antes_dos_arquivos_e_o_novo_vem_por_ultimo(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 0
    pre = """
ordem = []
_gravar = m._bancada_gravar
def gravar(caminho, dados):
    pasta = os.path.dirname(caminho)
    ordem.append([os.path.basename(caminho), os.path.exists(os.path.join(pasta, "relatorio.json"))])
    return _gravar(caminho, dados)
m._bancada_gravar = gravar
atexit.register(lambda: open(os.environ["REG"], "w").write(json.dumps(ordem)))
"""
    r, ordem = curar_com(falso.url, pre, tmp_path, *args, "--refazer")
    assert r.returncode == 0, r.stdout + r.stderr
    # relatorio.json ANTIGO já não existe quando o primeiro arquivo novo é gravado; o novo é o último
    assert ordem == [["espelho.md", False], ["indice.json", False], ["relatorio.json", False]]


def test_a3_erro_txt_so_nasce_sem_relatorio_valido(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = (500, {"detail": "kaput"})
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 1 and "500" in ler(tmp_path / "perfil" / a / "erro.txt")


# ------------------------------------------------------------------ revisão 3 (segundo revisor independente)

def _agregador():
    """O agregador (`acervo listar obra bancada`), para conferir o MESMO relatório dos dois lados."""
    caminho = RAIZ / "bin" / "_acervo" / "bancada_conversao.py"
    spec = importlib.util.spec_from_file_location("bancada_conversao_teste", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def corpo_so_espelho(oid, metodo="perfil"):
    """200 válido cujo relatório só declara (e a resposta só traz) o espelho.md."""
    md, _ = md_e_indice(oid)
    return 200, {"ato": "converter-em-bancada", "obra_id": oid, "relatorio": _relatorio(oid, metodo, md, None),
                 "arquivos": {"espelho.md": md}}


@pytest.mark.parametrize("nova, situacao", [(corpo_falha, "falha "), (corpo_na, "n/a ")],
                         ids=["falha-do-metodo", "n-a"])
def test_d2_refazer_com_200_sem_arquivos_remove_espelho_e_indice_da_rodada_anterior(falso, tmp_path, nova,
                                                                                 situacao):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 0
    pasta = tmp_path / "perfil" / a
    assert (pasta / "espelho.md").exists() and (pasta / "indice.json").exists()
    falso.cenarios[a] = nova(a)                       # 200 novo, sem 'arquivos'
    r = curar(falso.url, *args, "--refazer")
    assert r.returncode == 0, r.stdout + r.stderr
    assert por_obra(r)[a[:8]].startswith(situacao)
    assert not (pasta / "espelho.md").exists() and not (pasta / "indice.json").exists()
    assert json.loads(ler(pasta / "relatorio.json")) == falso.cenarios[a][1]["relatorio"]
    assert not (pasta / "erro.txt").exists() and sem_tmp(tmp_path)
    r2 = curar(falso.url, *args)                      # o relatório novo está íntegro: retomada pula
    assert por_obra(r2)[a[:8]].startswith("já feito") and len(falso.posts()) == 2


def test_d2_refazer_que_traz_so_um_dos_arquivos_troca_esse_e_remove_o_outro(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 0
    falso.cenarios[a] = corpo_so_espelho(a)
    r = curar(falso.url, *args, "--refazer")
    assert r.returncode == 0 and por_obra(r)[a[:8]].startswith("ok "), r.stdout + r.stderr
    pasta = tmp_path / "perfil" / a
    assert ler(pasta / "espelho.md") == md_e_indice(a)[0] and not (pasta / "indice.json").exists()
    assert "sha256_indice" not in json.loads(ler(pasta / "relatorio.json"))
    assert not (pasta / "erro.txt").exists()


def test_d4_uuid_em_maiusculas_e_normalizado_deduplicado_e_a_pasta_e_minuscula(falso, tmp_path):
    a, b = U(0xab), U(0xcd)
    assert a.upper() != a and b.upper() != b
    falso.cenarios.update({a: corpo_ok(a), b: corpo_ok(b)})
    # maiúsculas + repetição: 4 entradas, 2 obras; vale a ordem da PRIMEIRA ocorrência (b antes de a)
    r = curar(falso.url, "--reextrair", f"{b.upper()},{a.upper()},{b},{a}", "--bancada", str(tmp_path / "s"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c[1].split("/")[3] for c in falso.posts()] == [b, a]
    assert sorted(p.name for p in (tmp_path / "s" / "perfil").iterdir()) == sorted([a, b])
    assert total(r).startswith("total  2 obra(s)  ok=2") and list(por_obra(r)) == [b[:8], a[:8]]
    # o mesmo por arquivo de lista
    lista = tmp_path / "obras.txt"
    lista.write_text(f"{a.upper()}\n{a}\n# {b}\n{b.upper()}\n", encoding="utf-8")
    antes = len(falso.posts())
    r = curar(falso.url, "--reextrair", f"@{lista}", "--bancada", str(tmp_path / "t"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c[1].split("/")[3] for c in falso.posts()][antes:] == [a, b]
    assert sorted(p.name for p in (tmp_path / "t" / "perfil").iterdir()) == sorted([a, b])
    # e a retomada reconhece a pasta em minúsculas quando a lista vem em maiúsculas
    r = curar(falso.url, "--reextrair", a.upper(), "--bancada", str(tmp_path / "t"))
    assert por_obra(r)[a[:8]].startswith("já feito") and len(falso.posts()) == antes + 2
    # título que o servidor resolve para um UUID em maiúsculas: mesma normalização (POST e pasta)
    falso.titulos["Norma Maiuscula"] = (b.upper(), "exato")
    r = curar(falso.url, "--reextrair", "Norma Maiuscula", "--bancada", str(tmp_path / "u"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [p.name for p in (tmp_path / "u" / "perfil").iterdir()] == [b]
    assert falso.posts()[-1][1] == f"/acervo/obras/{b}/conversoes"


def test_d5_aplicavel_false_com_erro_e_na_no_cliente_e_no_agregador_para_o_mesmo_relatorio(falso, tmp_path):
    a, b, c = U(1), U(2), U(3)

    def na_com_erro(oid, erro_tipo):
        status, corpo = corpo_na(oid)
        corpo["relatorio"].update(erro="boom", erro_tipo=erro_tipo)
        return status, corpo

    falso.cenarios.update({a: na_com_erro(a, "conversao"), b: na_com_erro(b, "timeout"),
                           c: na_com_erro(c, "indisponivel")})
    args = ("--reextrair", f"{a},{b},{c}", "--bancada", str(tmp_path))
    r = curar(falso.url, *args)
    linhas = por_obra(r)
    # precedencia: indisponivel > aplicavel false > falha
    assert linhas[a[:8]].startswith("n/a ") and linhas[b[:8]].startswith("n/a "), r.stdout
    assert linhas[c[:8]].startswith("erro") and "indisponível" in linhas[c[:8]]
    assert total(r).startswith("total  3 obra(s)  ok=0  reprovada=0  n/a=2  falha=0  erro=1")
    assert r.returncode == 1
    for x in (a, b):
        assert (tmp_path / "perfil" / x / "relatorio.json").exists()
    assert not (tmp_path / "perfil" / c / "relatorio.json").exists()
    # a retomada lê o mesmo relatório gravado como n/a
    r2 = curar(falso.url, "--reextrair", f"{a},{b}", "--bancada", str(tmp_path), "--json")
    assert {o["situacao_gravada"] for o in json.loads(r2.stdout)["obras"]} == {"n/a"}
    # o AGREGADOR, sobre o mesmo relatório: n/a (método não cobre o tipo) antes do erro; pendente no indisponivel
    bc = _agregador()
    outro = corpo_ok(U(9), "docling")[1]["relatorio"]
    for x in (a, b):
        gravado = json.loads(ler(tmp_path / "perfil" / x / "relatorio.json"))
        d = bc.decidir(x, gravado, outro)
        assert d["vencedor"] == "n/a" and d["na"] == "método não cobre o tipo", x
    d = bc.decidir(c, falso.cenarios[c][1]["relatorio"], outro)
    assert d["vencedor"] == "pendente" and d["pendentes"] == ["perfil"]


def test_d6_refazer_que_falha_sobre_relatorio_nao_integro_renomeia_para_invalido_antes_do_erro_txt(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    args = ("--reextrair", a, "--bancada", str(tmp_path))
    assert curar(falso.url, *args).returncode == 0
    pasta = tmp_path / "perfil" / a
    original = (pasta / "relatorio.json").read_bytes()
    assert json.loads(original)["versao_relatorio"] == 1
    (pasta / "espelho.md").write_text("adulterado", encoding="utf-8")     # sha/tamanho não conferem mais
    falso.cenarios[a] = (500, {"detail": "kaput"})
    r = curar(falso.url, *args, "--refazer")
    assert r.returncode == 1 and por_obra(r)[a[:8]].startswith("erro") and "500" in r.stdout
    # estado A3: sem relatorio.json válido; o antigo vira invalido; erro.txt diz o porquê
    assert not (pasta / "relatorio.json").exists()
    assert (pasta / "relatorio.invalido.json").read_bytes() == original
    assert "500" in ler(pasta / "erro.txt")
    obra, = _agregador().agregar(str(tmp_path))["obras"]
    assert obra["perfil"]["estado"] == "pendente" and "relatorio.invalido.json" in obra["perfil"]["problema"]
    assert sem_tmp(tmp_path)


# ------------------------------------------------------------------ A4: pasta de saída testada antes do POST

def test_a4_pasta_que_e_arquivo_exit_2_antes_de_qualquer_post(falso, tmp_path):
    alvo = tmp_path / "isto-e-um-arquivo"
    alvo.write_text("x", encoding="utf-8")
    r = curar(falso.url, "--reextrair", f"{U(1)},Titulo Qualquer", "--bancada", str(alvo))
    assert r.returncode == 2 and "escrever" in r.stderr and str(alvo) in r.stderr
    assert "Traceback" not in r.stderr and r.stdout == ""
    assert falso.chamadas == []


def test_a4_metodo_que_e_arquivo_dentro_da_pasta_exit_2_antes_de_qualquer_post(falso, tmp_path):
    (tmp_path / "perfil").write_text("x", encoding="utf-8")        # <pasta>/perfil existe e é arquivo
    r = curar(falso.url, "--reextrair", U(1), "--bancada", str(tmp_path))
    assert r.returncode == 2 and "escrever" in r.stderr and falso.chamadas == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root escreve em qualquer pasta")
def test_a4_pasta_somente_leitura_exit_2_antes_de_qualquer_post(falso, tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        r = curar(falso.url, "--reextrair", U(1), "--bancada", str(ro))
        assert r.returncode == 2 and "escrever" in r.stderr and falso.chamadas == []
    finally:
        ro.chmod(0o700)


def test_a4_pasta_gravavel_e_testada_sem_deixar_lixo(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path / "nova" / "saida"))
    assert r.returncode == 0 and sem_tmp(tmp_path)
    assert not [p for p in (tmp_path / "nova" / "saida" / "perfil").iterdir() if p.is_file()]


# ------------------------------------------------------------------ A5: modo dos arquivos

@pytest.mark.parametrize("umask, modo", [(0o022, 0o644), (0o027, 0o640), (0o077, 0o600), (0o002, 0o644)])
def test_a5_arquivos_gravados_com_0644_menos_a_umask(falso, tmp_path, umask, modo):
    a, b = U(1), U(2)
    falso.cenarios.update({a: corpo_ok(a), b: (500, {"detail": "kaput"})})
    r = curar(falso.url, "--reextrair", f"{a},{b}", "--bancada", str(tmp_path), umask=umask)
    assert r.returncode == 1
    for caminho in [tmp_path / "perfil" / a / n for n in ("espelho.md", "indice.json", "relatorio.json")] \
            + [tmp_path / "perfil" / b / "erro.txt"]:
        assert stat.S_IMODE(caminho.stat().st_mode) == modo, caminho


# ------------------------------------------------------------------ listas

def test_lista_por_arquivo_ignora_vazias_e_comentarios(falso, tmp_path):
    a, b = U(1), U(2)
    falso.cenarios.update({a: corpo_ok(a), b: corpo_ok(b)})
    lista = tmp_path / "obras.txt"
    lista.write_text(f"# piloto\n\n{a}\n   \n# {U(9)}\n  {b}  \n{a}\n", encoding="utf-8")
    r = curar(falso.url, "--reextrair", f"@{lista}", "--bancada", str(tmp_path / "saida"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c[1].split("/")[3] for c in falso.posts()] == [a, b]   # sem o comentado, sem repetir
    assert total(r).startswith("total  2 obra(s)  ok=2")


def test_a6_lista_com_bom_de_editor_e_lida_como_utf_8_sig(falso, tmp_path):
    a, b = U(1), U(2)
    falso.cenarios.update({a: corpo_ok(a), b: corpo_ok(b)})
    lista = tmp_path / "obras.txt"
    lista.write_bytes(b"\xef\xbb\xbf" + f"{a}\n{b}\n".encode("utf-8"))
    r = curar(falso.url, "--reextrair", f"@{lista}", "--bancada", str(tmp_path / "saida"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert [c[1].split("/")[3] for c in falso.posts()] == [a, b]


def test_a6_lista_que_nao_e_utf_8_e_uso_errado_com_mensagem_e_sem_traceback(falso, tmp_path):
    lista = tmp_path / "obras.txt"
    lista.write_bytes(b"\xff\xfe" + "a\nb\n".encode("utf-16-le") + b"\x80\x81")    # utf-16 + lixo
    r = curar(falso.url, "--reextrair", f"@{lista}", "--bancada", str(tmp_path / "saida"))
    assert r.returncode == 2 and "utf-8" in r.stderr and "Traceback" not in r.stderr
    assert falso.chamadas == [] and not (tmp_path / "saida").exists()


def test_lista_por_arquivo_inexistente_e_uso_errado(falso, tmp_path):
    r = curar(falso.url, "--reextrair", f"@{tmp_path}/nao-existe.txt", "--bancada", str(tmp_path))
    assert r.returncode == 2 and falso.posts() == []


def test_metodo_docling_vira_o_segmento_de_pasta_e_o_corpo_do_contrato(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a, "docling")
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path), "--metodo", "docling",
              "--autor", "engenharia", "--timeout-s", "300")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "docling" / a / "relatorio.json").exists() and not (tmp_path / "perfil" / a).exists()
    (_, caminho, corpo, cab), = falso.posts()
    assert caminho == f"/acervo/obras/{a}/conversoes"
    assert corpo == {"autor": "engenharia", "metodo": "docling", "timeout_s": 300}
    assert cab["authorization"] == "Bearer tok-teste" and cab["traceparent"].startswith("00-")


def test_corpo_default_do_contrato_e_metodo_perfil(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path), "--autor", "engenharia")
    assert falso.posts()[0][2] == {"autor": "engenharia", "metodo": "perfil", "timeout_s": 1800}


def test_metodo_de_outra_pasta_no_relatorio_e_erro(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a, "docling")     # pedi perfil, veio relatório de docling
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 1 and "outro método" in ler(tmp_path / "perfil" / a / "erro.txt")
    assert not (tmp_path / "perfil" / a / "relatorio.json").exists()


def test_titulo_que_nao_resolve_e_erro_daquela_obra_so(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    falso.titulos["Norma Aproximada"] = (U(7), "aproximado")
    r = curar(falso.url, "--reextrair", f"Titulo Que Nao Existe,Norma Aproximada,{a}", "--bancada",
              str(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0].startswith("erro") and "resolver" in linhas[0]
    assert linhas[1].startswith("erro") and "aproximado" in linhas[1]
    assert linhas[2].startswith("ok ")
    assert total(r).startswith("total  3 obra(s)  ok=1  reprovada=0  n/a=0  falha=0  erro=2")


def test_titulo_exato_resolve_para_o_id(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    falso.titulos["Norma Exata"] = (a, "exato")
    r = curar(falso.url, "--reextrair", "Norma Exata", "--bancada", str(tmp_path))
    assert r.returncode == 0 and (tmp_path / "perfil" / a / "relatorio.json").exists()


def test_servidor_fora_do_ar_e_erro_de_rede_por_obra(tmp_path):
    f = Falso()
    url = f.url
    f.parar()                                       # porta livre e ninguém escutando
    r = curar(url, "--reextrair", f"{U(1)},{U(2)}", "--bancada", str(tmp_path))
    assert r.returncode == 1
    assert len(r.stdout.splitlines()) == 3 and "rede:" in r.stdout


def test_422_metodo_indisponivel_e_erro_da_obra(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = (422, {"title": "MetodoIndisponivel", "status": 422, "detail": "docling fora"})
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path), "--metodo", "docling")
    assert r.returncode == 1 and "indisponível" in r.stdout and "docling fora" in r.stdout


# ------------------------------------------------------------------ A6: prazos (servidor falso que demora)

def test_a6_os_prazos_declarados_no_post_e_no_get_de_titulo(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    falso.titulos["Norma Exata"] = (U(2), "exato")
    falso.cenarios[U(2)] = corpo_ok(U(2))
    r, reg = curar_com(falso.url, REGISTRA_REQUESTS, tmp_path, "--reextrair", f"Norma Exata,{a}",
                       "--bancada", str(tmp_path / "s"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert reg == [["GET", [10, 60]], ["POST", [10, 1800 + 120]], ["POST", [10, 1800 + 120]]]
    r, reg = curar_com(falso.url, REGISTRA_REQUESTS, tmp_path, "--reextrair", a, "--bancada",
                       str(tmp_path / "t"), "--timeout-s", "300")
    assert reg == [["POST", [10, 300 + 120]]]


def test_a6_post_lento_estoura_o_prazo_de_leitura_e_vira_erro_daquela_obra(falso, tmp_path):
    a, b = U(1), U(2)
    falso.cenarios[a] = devagar(6, corpo_ok(a))
    falso.cenarios[b] = corpo_ok(b)
    t0 = time.monotonic()
    r, _ = curar_com(falso.url, "m._BANCADA_MARGEM_HTTP_S = 0", tmp_path, "--reextrair", f"{a},{b}",
                     "--bancada", str(tmp_path / "s"), "--timeout-s", "1")
    assert time.monotonic() - t0 < 5.5                        # não esperou o servidor terminar
    assert r.returncode == 1, r.stdout + r.stderr
    linhas = por_obra(r)
    assert linhas[a[:8]].startswith("erro") and "rede:" in linhas[a[:8]] and "ReadTimeout" in linhas[a[:8]]
    assert linhas[b[:8]].startswith("ok ")                    # a lenta não derrubou a outra
    assert "ReadTimeout" in ler(tmp_path / "s" / "perfil" / a / "erro.txt")


def test_a6_get_lento_de_titulo_estoura_o_prazo_e_nao_chega_ao_post(falso, tmp_path):
    falso.titulos["Norma Lenta"] = (U(1), "exato")
    falso.cenarios[U(1)] = corpo_ok(U(1))
    falso.atraso_get = 6
    t0 = time.monotonic()
    r, _ = curar_com(falso.url, "m._BANCADA_TIMEOUT_RESOLVER = (10, 1)", tmp_path, "--reextrair",
                     "Norma Lenta", "--bancada", str(tmp_path / "s"))
    assert time.monotonic() - t0 < 5.5
    assert r.returncode == 1 and "resolver" in r.stdout and falso.posts() == []


# ------------------------------------------------------------------ --json

def test_json_imprime_so_o_resumo_estruturado(falso, tmp_path):
    a, b, c, d, e, f, g = cenario_misto(falso)
    r = curar(falso.url, "--reextrair", ",".join([a, b, c, d, g]), "--bancada", str(tmp_path), "--json")
    assert r.returncode == 1
    resumo = json.loads(r.stdout)                    # stdout inteiro é um JSON só
    assert resumo["metodo"] == "perfil" and resumo["total"] == 5 and resumo["exit_code"] == 1
    assert resumo["contagem"] == {"ok": 1, "reprovada": 1, "n/a": 1, "falha": 1, "erro": 1, "já feito": 0}
    obras = {o["obra_id"]: o for o in resumo["obras"]}
    assert [o["situacao"] for o in resumo["obras"]] == ["ok", "reprovada", "n/a", "erro", "falha"]
    assert obras[a]["arquivo_relatorio"] == str(tmp_path / "perfil" / a / "relatorio.json")
    assert obras[a]["arquivos"] == ["espelho.md", "indice.json"]
    assert obras[c]["arquivos"] == [] and obras[d]["arquivo_relatorio"] is None
    assert obras[g]["erro_tipo"] == "timeout" and obras[g]["arquivo_relatorio"] is not None
    assert "404" in obras[d]["causa"]
    assert "ok" in r.stderr                         # o andamento vai para o stderr


# ------------------------------------------------------------------ uso errado (exit 2)

@pytest.mark.parametrize("extra, trecho", [
    (["--apply"], "bancada não escreve no acervo"),
    (["--metodo", "../fora"], "nome de pasta"),
    (["--timeout-s", "0"], "positivo"),
    (["--recortar", "x"], "--recortar"),
])
def test_uso_errado_exit_2_sem_tocar_o_servidor(falso, tmp_path, extra, trecho):
    r = curar(falso.url, "--reextrair", U(1), "--bancada", str(tmp_path), *extra)
    assert r.returncode == 2 and trecho in r.stderr
    assert falso.chamadas == [] and not (tmp_path / "perfil").exists()


def test_bancada_sem_reextrair_e_refazer_sem_bancada_exit_2(falso, tmp_path):
    r = curar(falso.url, "--bancada", str(tmp_path))
    assert r.returncode == 2 and "--reextrair" in r.stderr
    r = curar(falso.url, "--reextrair", U(1), "--refazer")
    assert r.returncode == 2 and "--bancada" in r.stderr
    r = curar(falso.url, "--reextrair", ",", "--bancada", str(tmp_path))
    assert r.returncode == 2 and "vazia" in r.stderr
    assert falso.chamadas == []


# ------------------------------------------------------------------ o que já existia

def test_reextrair_de_uma_obra_sem_bancada_continua_igual(falso):
    a = U(1)
    r = curar(falso.url, "--reextrair", a)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Plano de reextração" in r.stdout
    assert [c[1] for c in falso.chamadas] == [f"/acervo/obras/{a}/reextracoes"]


def test_acervo_curar_obra_repassa_o_lote_para_o_curar(falso, tmp_path):
    # bin/acervo -> _acervo/curar -> bin/curar: `acervo curar obra --reextrair ... --bancada ...`
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    fio = tmp_path / "fio"          # `python3` do PATH = o que tem `requests` (o shebang do sub-ato)
    fio.mkdir()
    (fio / "python3").symlink_to(PY)
    env = {**_env(falso.url), "PATH": f"{fio}{os.pathsep}{os.environ.get('PATH', '')}"}
    r = subprocess.run(["bash", str(RAIZ / "bin" / "acervo"), "curar", "biblioteca", "--reextrair", a,
                        "--bancada", str(tmp_path)], capture_output=True, text=True, env=env,
                       timeout=120, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("ok ") and (tmp_path / "perfil" / a / "espelho.md").exists()


def test_ajuda_do_curar_descreve_o_lote_e_as_situacoes(falso):
    r = curar(falso.url, "--ajuda")
    assert r.returncode == 0
    for trecho in ("--bancada <pasta>", "--refazer", "id1,id2", "@arquivo", "não escreve no acervo",
                   "ok|reprovada|n/a|falha|erro|já feito", "medida-indeterminada", "relatorio.invalido.json"):
        assert trecho in r.stdout, trecho


# ------------------------------------------------------------------ --modo medida (#3207)

def corpo_medida(oid, metodo="docling", paginas=12, com_calha=2, **over):
    """200 do modo `medida`: só a porta ao MuPDF. Sem arquivos, sem fidelidade, sem blocos."""
    medida = {"detectores": {"versao": 1}, "paginas": paginas, "paginas_com_calha": com_calha,
              "calhas_por_pagina": {str(p): [[220.0, 320.0]] for p in range(3, 3 + com_calha)},
              "paginas_ilegiveis": [], "tempo_ms": 300}
    rel = _relatorio(oid, metodo, cabecalho=None, fidelidade=None, tempos_ms={"total": 340}, medida=medida, **over)
    return 200, {"ato": "converter-em-bancada", "modo": "medida", "obra_id": oid, "titulo": "T",
                 "objeto": "acervo/abc", "relatorio": rel}


def test_modo_medida_vai_no_corpo_grava_so_o_relatorio_e_a_linha_traz_paginas_e_calha(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_medida(a, paginas=12, com_calha=2)
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path), "--metodo", "docling", "--modo", "medida",
              "--autor", "engenharia")
    assert r.returncode == 0, r.stdout + r.stderr
    (_, caminho, corpo, _cab), = falso.posts()
    assert caminho == f"/acervo/obras/{a}/conversoes"
    assert corpo == {"autor": "engenharia", "metodo": "docling", "timeout_s": 1800, "modo": "medida"}
    pasta = tmp_path / "docling" / a
    assert (pasta / "relatorio.json").exists()
    assert not (pasta / "espelho.md").exists() and not (pasta / "indice.json").exists()
    assert json.loads(ler(pasta / "relatorio.json"))["medida"]["paginas_com_calha"] == 2
    linha = r.stdout.splitlines()[0]
    assert linha.startswith("ok ") and "paginas=12" in linha and "calha=2" in linha and "classe=" not in linha
    assert "medida  1 de 1 obra(s) com calha  2 de 12 página(s) com calha" in r.stdout


def test_a_retomada_da_medida_pula_a_obra_feita_e_mostra_a_medida_gravada(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_medida(a, paginas=12, com_calha=2)
    argv = ("--reextrair", a, "--bancada", str(tmp_path), "--metodo", "docling", "--modo", "medida")
    assert curar(falso.url, *argv).returncode == 0
    r = curar(falso.url, *argv)
    assert r.returncode == 0 and len(falso.posts()) == 1  # nenhum POST novo
    linha = r.stdout.splitlines()[0]
    assert linha.startswith("já feito") and "paginas=12" in linha and "calha=2" in linha


def test_o_resumo_json_da_medida_conta_as_obras_e_as_paginas_com_calha(falso, tmp_path):
    a, b = U(1), U(2)
    falso.cenarios.update({a: corpo_medida(a, paginas=12, com_calha=2), b: corpo_medida(b, paginas=5, com_calha=0)})
    r = curar(falso.url, "--reextrair", f"{a},{b}", "--bancada", str(tmp_path), "--metodo", "docling",
              "--modo", "medida", "--json")
    assert r.returncode == 0, r.stdout + r.stderr
    resumo = json.loads(r.stdout)
    assert resumo["modo"] == "medida"
    assert resumo["medida"] == {"obras_medidas": 2, "obras_com_calha": 1, "paginas": 17, "paginas_com_calha": 2}
    assert [o["medida"] for o in resumo["obras"]] == [{"paginas": 12, "com_calha": 2}, {"paginas": 5, "com_calha": 0}]


def test_o_modo_bancada_explicito_vai_no_corpo_e_o_padrao_segue_sem_ele(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path), "--modo", "bancada", "--autor", "engenharia")
    assert falso.posts()[0][2] == {"autor": "engenharia", "metodo": "perfil", "timeout_s": 1800, "modo": "bancada"}


def test_a_bancada_sem_modo_nao_ganha_a_linha_de_medida(falso, tmp_path):
    a = U(1)
    falso.cenarios[a] = corpo_ok(a)
    r = curar(falso.url, "--reextrair", a, "--bancada", str(tmp_path))
    assert r.returncode == 0 and "calha" not in r.stdout and "medida  " not in r.stdout
    assert "classe=B" in r.stdout


@pytest.mark.parametrize("extra, trecho", [
    (["--modo", "outro"], "--modo é bancada ou medida"),
    (["--modo", ""], "--modo é bancada ou medida"),
    (["--modo", "MEDIDA"], "--modo é bancada ou medida"),
])
def test_modo_invalido_e_uso_errado_sem_tocar_o_servidor(falso, tmp_path, extra, trecho):
    r = curar(falso.url, "--reextrair", U(1), "--bancada", str(tmp_path), *extra)
    assert r.returncode == 2 and trecho in r.stderr
    assert falso.chamadas == [] and not (tmp_path / "perfil").exists()


def test_modo_sem_bancada_e_uso_errado(falso):
    r = curar(falso.url, "--reextrair", U(1), "--modo", "medida")
    assert r.returncode == 2 and "--bancada" in r.stderr and falso.chamadas == []


def test_ajuda_do_curar_descreve_o_modo_medida(falso):
    r = curar(falso.url, "--ajuda")
    assert r.returncode == 0
    for trecho in ("--modo bancada|medida", "calhas de duas", "pela porta ao MuPDF", "páginas com calha"):
        assert trecho in r.stdout, trecho
