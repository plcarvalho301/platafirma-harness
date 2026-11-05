"""#4120, U13: `acervo pipeline` — o ato único, cliente fino do job do servidor.

Sem --apply mostra o plano do lote e não cria job. Com --apply incorpora a pasta (por `bin/ingerir`, aqui trocado
por um cliente de mentira que imprime o lote), cria o job no servidor e devolve o id sem esperar o job inteiro,
então a chamada fica abaixo dos 600 s da porta. `--lote <id>` cria ou retoma o job de um lote já aplicado, e
`--job <id>` mostra o estado. O servidor é falso; o ato roda de verdade, como subprocesso.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PIPELINE = RAIZ / "bin" / "_acervo" / "pipeline"
ACERVO = RAIZ / "bin" / "acervo"
LOTE = "33333333-3333-4333-8333-333333333333"
JOB = "44444444-4444-4444-8444-444444444444"

ETAPAS = ("triagem", "catalogacao", "duplicata", "classificar", "promocao")


def _job(estado="pausado", classificar="pausado"):
    etapas = []
    for obra in ("o1", "o2"):
        for nome in ETAPAS:
            estado_etapa = "concluido" if ETAPAS.index(nome) < 3 else ("pausado" if nome == "classificar" else "pendente")
            if nome == "classificar":
                estado_etapa = classificar
            etapas.append({"id": f"{obra}-{nome}", "obra_id": obra, "etapa": nome, "estado": estado_etapa})
    return {"id": JOB, "pasta": "entrada", "lote_id": LOTE, "estado": estado, "erro": None, "etapas": etapas}


class _Handler(BaseHTTPRequestHandler):
    falso: "Falso"

    def log_message(self, *a):
        pass

    def _resp(self, status, obj):
        dados = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        self.falso.chamadas.append(("GET", self.path, None))
        if self.path.split("?")[0] == f"/acervo/jobs/{JOB}":
            return self._resp(200, self.falso.job)
        return self._resp(404, {"title": "NaoEncontrado", "detail": f"Job {self.path} não encontrado"})

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"null")
        self.falso.chamadas.append(("POST", self.path, corpo))
        if self.path == "/acervo/jobs":
            if self.falso.post_jobs_status != 201:
                return self._resp(self.falso.post_jobs_status, {"title": "Conflito", "detail": "lote sem obra"})
            return self._resp(201, {**self.falso.job, "pasta": corpo["pasta"], "lote_id": corpo["lote_id"],
                                    "etapas_criadas": 10})
        return self._resp(404, {"title": "NaoEncontrado", "detail": self.path})


class Falso:
    def __init__(self):
        self.chamadas = []
        self.job = _job()
        self.post_jobs_status = 201
        handler = type("H", (_Handler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def criacoes(self):
        return [c for c in self.chamadas if c[0] == "POST"]

    def rodar(self, *argv, ingerir=None, url=None, via_acervo=False):
        env = {**os.environ, "MOTOR_ACERVO_URL": url or self.url, "RAG_API_URL": "", "RAG_API_BASE": "",
               "RAG_API_TOKEN": "tok-pipe", "PF_CADEIRA": "dados"}
        if ingerir:
            env["PF_INGERIR"] = str(ingerir)
        cmd = ["bash", str(ACERVO), "pipeline", *argv] if via_acervo else [sys.executable, str(PIPELINE), *argv]
        return subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL,
                              timeout=60, check=False)


@pytest.fixture
def servidor():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


def _ingerir_falso(tmp_path, lote, codigo=0, ruido=""):
    """Um `ingerir` que imprime o lote, como o --json dele, e sai com `codigo`. Guarda os argumentos que recebeu."""
    gravado = tmp_path / "argumentos.json"
    script = tmp_path / "ingerir_falso.py"
    script.write_text(textwrap.dedent(f"""
        import json, sys
        json.dump(sys.argv[1:], open({str(gravado)!r}, "w"))
        sys.stdout.write({ruido!r})
        print(json.dumps({lote!r}, indent=2))
        sys.stderr.write("ingerir: resumo do lote\\n")
        sys.exit({codigo})
    """))
    return script, gravado


def _lote(estado="concluido", itens=2, **extra):
    return {"id": LOTE, "estado": estado,
            "itens": [{"posicao": i, "veredito": "criar", "estado": "feito", "obra_id": f"obra-{i}"} for i in range(itens)],
            **extra}


def test_apply_incorpora_cria_o_job_e_devolve_o_id(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, gravado = _ingerir_falso(tmp_path, _lote())
    t0 = time.monotonic()
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 0, r.stderr
    assert f"job: {JOB}" in r.stdout
    assert time.monotonic() - t0 < 600
    # o ingerir recebeu a pasta, o --apply e o --json que o ato lê
    assert json.loads(gravado.read_text()) == ["--lote", str(pasta), "--apply", "--json"]
    # o job nasce sobre o lote que o ingerir aplicou
    assert servidor.criacoes() == [("POST", "/acervo/jobs", {"pasta": str(pasta), "lote_id": LOTE})]
    assert f"lote: {LOTE} · 2 obra(s)" in r.stderr


def test_resumo_do_job_conta_cada_etapa_e_diz_quem_espera_a_sessao(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, _ = _ingerir_falso(tmp_path, _lote())
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert "estado: pausado" in r.stdout and "obras: 2" in r.stdout
    assert "triagem: concluido 2" in r.stdout
    assert "classificar: pausado 2" in r.stdout
    assert f"2 obra(s) esperam a classificação da sessão: acervo catalogar biblioteca obra --job {JOB}" in r.stdout


def test_ingerir_com_excecao_ou_reprovado_ainda_cria_o_job_das_obras_que_entraram(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    for codigo in (2, 3):
        servidor.chamadas.clear()
        ingerir, _ = _ingerir_falso(tmp_path, _lote())
        ingerir.write_text(ingerir.read_text().replace("sys.exit(0)", f"sys.exit({codigo})"))
        r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
        assert r.returncode == 0, (codigo, r.stderr)
        assert f"ingerir saiu {codigo}" in r.stderr
        assert len(servidor.criacoes()) == 1


def test_lote_sem_obra_nao_cria_job(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    lote = {"id": LOTE, "estado": "concluido", "itens": [
        {"posicao": 0, "veredito": "reprovado", "estado": "pulado", "obra_id": None},
        {"posicao": 1, "veredito": "bloqueada", "estado": "pulado", "obra_id": None}]}
    ingerir, _ = _ingerir_falso(tmp_path, lote, codigo=3)
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 1
    assert "nao tem obra para o job" in r.stderr
    assert servidor.criacoes() == []


def test_lote_que_falhou_nao_cria_job(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, _ = _ingerir_falso(tmp_path, _lote(estado="falhou"), codigo=1)
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 1 and "terminou em 'falhou'" in r.stderr
    assert servidor.criacoes() == []


def test_o_lote_se_le_mesmo_com_aviso_antes_do_json(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, _ = _ingerir_falso(tmp_path, _lote(), ruido="conversor acordado {pid 12}\n")
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 0, r.stderr
    assert len(servidor.criacoes()) == 1


def test_saida_que_nao_e_lote_sai_5_e_nao_cria_job(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    script = tmp_path / "ingerir_mudo.py"
    script.write_text("print('nada de json aqui')\n")
    r = servidor.rodar(str(pasta), "--apply", ingerir=script)
    assert r.returncode == 5 and "nao li o lote" in r.stderr
    assert servidor.criacoes() == []


def test_sem_apply_so_mostra_o_plano_do_ingerir_e_nao_cria_job(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, gravado = _ingerir_falso(tmp_path, _lote())
    r = servidor.rodar(str(pasta), ingerir=ingerir)
    assert r.returncode == 0
    assert json.loads(gravado.read_text()) == ["--lote", str(pasta)]  # sem --apply, sem --json
    assert "plano seco" in r.stderr
    assert servidor.chamadas == []


def test_lote_existente_cria_ou_retoma_o_job(servidor):
    r = servidor.rodar("--lote", LOTE)
    assert r.returncode == 0, r.stderr
    assert servidor.criacoes() == [("POST", "/acervo/jobs", {"pasta": f"lote:{LOTE}", "lote_id": LOTE})]
    assert f"job: {JOB}" in r.stdout


def test_job_mostra_o_estado_sem_criar_nada(servidor):
    r = servidor.rodar("--job", JOB)
    assert r.returncode == 0, r.stderr
    assert "classificar: pausado 2" in r.stdout
    assert servidor.criacoes() == []


def test_espera_vai_ao_servidor_e_nunca_passa_do_teto(servidor):
    r = servidor.rodar("--job", JOB, "--espera", "30")
    assert r.returncode == 0, r.stderr
    assert ("GET", f"/acervo/jobs/{JOB}?espera=30", None) in servidor.chamadas
    alta = servidor.rodar("--job", JOB, "--espera", "601")
    assert alta.returncode == 2 and "o teto do servidor" in alta.stderr


def test_json_devolve_o_job_inteiro(servidor):
    r = servidor.rodar("--job", JOB, "--json")
    assert r.returncode == 0 and json.loads(r.stdout)["id"] == JOB


def test_job_que_o_servidor_nao_conhece_sai_1(servidor):
    r = servidor.rodar("--job", "00000000-0000-4000-8000-000000000000")
    assert r.returncode == 1 and "NaoEncontrado" in r.stderr


def test_servidor_fora_sai_3(servidor):
    r = servidor.rodar("--job", JOB, url="http://127.0.0.1:9")
    assert r.returncode == 3 and "rota fora" in r.stderr


def test_servidor_que_recusa_o_job_sai_1_com_a_causa(servidor):
    servidor.post_jobs_status = 409
    r = servidor.rodar("--lote", LOTE)
    assert r.returncode == 1 and "lote sem obra" in r.stderr


@pytest.mark.parametrize("argv, trecho", [
    ((), "informe uma so fonte"),
    (("--lote", LOTE, "--job", JOB), "informe uma so fonte"),
    (("--lote", LOTE, "--apply"), "--apply acompanha <pasta>"),
    (("--job", JOB, "--semsentido"), "argumento que o ato nao le"),
    (("--job", JOB, "--espera", "-1"), "o teto do servidor"),
])
def test_uso_errado_sai_2_sem_falar_com_o_servidor(servidor, argv, trecho):
    r = servidor.rodar(*argv)
    assert r.returncode == 2 and trecho in r.stderr
    assert servidor.chamadas == []


def test_pasta_inexistente_sai_1(servidor, tmp_path):
    r = servidor.rodar(str(tmp_path / "nao-existe"), "--apply")
    assert r.returncode == 1 and "pasta nao encontrada" in r.stderr


def test_o_ato_existe_na_porta_do_acervo(servidor):
    # antes desta entrega: `bin/acervo` caía em «biblioteca: command not found» ao chamar `pipeline`
    r = servidor.rodar("--job", JOB, via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert f"job: {JOB}" in r.stdout
    assert "command not found" not in r.stderr
