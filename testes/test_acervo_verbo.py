# componente: componente:verbo-acervo
"""Suíte consolidada do verbo `acervo` (componente:verbo-acervo).

Reúne os testes de:
- `acervo pipeline` (`bin/_acervo/pipeline` e despacho em `bin/acervo`);
- `acervo ler biblioteca posicao <obra>` (`bin/_acervo/posicao`);
- `acervo listar biblioteca obra --situacao --retrato --diferenca` (`bin/_acervo/retrato.py`);
- atos do padrão da casa nova para `conceito` e `indicacao` (`bin/_acervo/tesauro.py`).
"""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PIPELINE = RAIZ / "bin" / "_acervo" / "pipeline"
POSICAO = RAIZ / "bin" / "_acervo" / "posicao"
LISTAR = RAIZ / "bin" / "_acervo" / "listar"
ACERVO = RAIZ / "bin" / "acervo"

_CAMINHOS_PY = [
    RAIZ / "bin" / "_release" / "conferir",
    RAIZ / "bin" / "_acervo",
    Path("/opt/platafirma/current/harness"),
    Path("/opt/platafirma/current/harness/lib"),
    Path("/opt/platafirma/current/harness/bin/_acervo"),
    Path("/opt/platafirma/current/harness/bin/_release/conferir"),
]
for _p in _CAMINHOS_PY:
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_pypath_partes = [str(p) for p in _CAMINHOS_PY if p.exists()]
if os.environ.get("PYTHONPATH"):
    _pypath_partes.append(os.environ["PYTHONPATH"])
os.environ["PYTHONPATH"] = os.pathsep.join(_pypath_partes)

import predicados_acervo as pa  # noqa: E402
import retrato  # noqa: E402
import tesauro as ts  # noqa: E402


# --- acervo pipeline (bin/_acervo/pipeline) ------------------------------------------------------------------------

LOTE = "33333333-3333-4333-8333-333333333333"
JOB = "44444444-4444-4444-8444-444444444444"
ETAPAS = ("triagem", "espelhar", "catalogacao", "duplicata", "classificar", "indexar", "promocao")


def _job(estado="pausado", classificar="pausado"):
    etapas = []
    for obra in ("o1", "o2"):
        for nome in ETAPAS:
            estado_etapa = "concluido" if ETAPAS.index(nome) < 4 else ("pausado" if nome == "classificar" else "pendente")
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
        if self.path == "/acervo/jobs/liberar":
            return self._resp(200, self.falso.resposta_liberar)
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
        self.resposta_liberar = {"job_id": JOB, "liberadas": [{"obra_id": "o1", "titulo": "Obra Um"}], "recusadas": []}
        handler = type("H", (_Handler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def criacoes(self):
        return [c for c in self.chamadas if c[0] == "POST"]

    def rodar(self, *argv, ingerir=None, url=None, via_acervo=False, conversor_sai=0):
        env = {**os.environ, "MOTOR_ACERVO_URL": url or self.url, "RAG_API_URL": "", "RAG_API_BASE": "",
               "RAG_API_TOKEN": "tok-pipe", "PF_CADEIRA": "dados",
               "PF_CONVERSOR_SOB_DEMANDA": str(self.conversor), "CONVERSOR_SAI": str(conversor_sai)}
        if ingerir:
            env["PF_INGERIR"] = str(ingerir)
        cmd = ["bash", str(ACERVO), "pipeline", *argv] if via_acervo else [sys.executable, str(PIPELINE), *argv]
        return subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL,
                              timeout=60, check=False)


@pytest.fixture
def servidor(tmp_path):
    f = Falso()
    f.conversor = tmp_path / "conversor_falso.sh"
    f.conversor_chamadas = tmp_path / "conversor_chamadas.txt"
    f.conversor.write_text(f'#!/usr/bin/env bash\necho "$@" >> {f.conversor_chamadas}\nexit "${{CONVERSOR_SAI:-0}}"\n')
    try:
        yield f
    finally:
        f.fechar()


def _ingerir_falso(tmp_path, lote, codigo=0, ruido=""):
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
    assert json.loads(gravado.read_text()) == ["--lote", str(pasta), "--apply", "--json"]
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


def test_obra_barrada_num_portao_do_encadeamento_nao_impede_o_job_das_outras(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, _ = _ingerir_falso(tmp_path, _lote(), codigo=1)
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 0, r.stderr
    assert "ingerir saiu 1" in r.stderr and len(servidor.criacoes()) == 1


def test_o_resumo_diz_duplicata_com_par_e_promocao_que_ficou_para_depois(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    servidor.job = _job(estado="concluido", classificar="concluido")
    for e in servidor.job["etapas"]:
        if e["obra_id"] == "o1" and e["etapa"] == "duplicata":
            e["detalhe"] = {"pares": [{"obra_id": "o2", "classificacao": "duplicata_provavel"}],
                            "duplicata_provavel": True}
        if e["etapa"] == "promocao":
            e["estado"], e["detalhe"] = "concluido", {"promovida": False, "motivo": "transcrita exige trechos"}
    ingerir, _ = _ingerir_falso(tmp_path, _lote())
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert "duplicata: 1 obra(s) com par, 1 provavel(is)" in r.stdout
    assert "promocao: 2 obra(s) ainda sem promocao" in r.stdout


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
    assert json.loads(gravado.read_text()) == ["--lote", str(pasta)]
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


def test_json_devolve_o_resumo_versionado(servidor):
    r = servidor.rodar("--job", JOB, "--json")
    assert r.returncode == 0
    res = json.loads(r.stdout)
    assert res["id"] == JOB and res["versao"] == 1
    assert "etapas" not in res
    assert res["por_etapa"]["triagem"] == {"concluido": 2}


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
    r = servidor.rodar("--job", JOB, via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert f"job: {JOB}" in r.stdout
    assert "command not found" not in r.stderr


def test_a_ajuda_geral_do_acervo_sai_inteira_e_sem_executar_o_texto_de_uso():
    env = {**os.environ, "PF_CADEIRA": "dados"}
    r = subprocess.run(["bash", str(ACERVO), "--ajuda"], capture_output=True, text=True, env=env,
                       stdin=subprocess.DEVNULL, timeout=60, check=False)
    assert r.returncode == 2
    assert "Retoma: `pipeline --lote <id>`; estado: `pipeline --job <id>`" in r.stderr
    assert "syntax error" not in r.stderr and "command not found" not in r.stderr
    assert "--liberar <sha256|obra>" in r.stderr
    assert "(antes `biblioteca objeto`: o nome velho recusa" in r.stderr
    assert "spec acervo" in r.stderr
    assert "nenhum python do rag" not in r.stderr and "uso: motor raciocinador" not in r.stderr


def test_liberar_por_pasta_manda_os_itens_ao_servidor_e_diz_quem_saiu(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    r = servidor.rodar(str(pasta), "--liberar", "o1")
    assert r.returncode == 0, r.stderr
    assert "liberada: o1 · Obra Um" in r.stdout and f"job: {JOB} · retomado" in r.stdout
    assert servidor.criacoes() == [("POST", "/acervo/jobs/liberar", {"itens": ["o1"], "pasta": str(pasta)})]


def test_liberar_por_job_ou_por_lote_leva_varios_itens(servidor):
    r = servidor.rodar("--job", JOB, "--liberar", "o1", "a" * 64)
    assert r.returncode == 0, r.stderr
    r = servidor.rodar("--lote", LOTE, "--liberar", "o2", via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert servidor.criacoes() == [
        ("POST", "/acervo/jobs/liberar", {"itens": ["o1", "a" * 64], "job_id": JOB}),
        ("POST", "/acervo/jobs/liberar", {"itens": ["o2"], "lote_id": LOTE}),
    ]


def test_liberar_o_que_nao_esta_estacionado_sai_1_com_o_motivo(servidor):
    servidor.resposta_liberar = {"job_id": JOB, "liberadas": [], "recusadas": [
        {"item": "zzz", "motivo": "a obra não está estacionada neste job"}]}
    r = servidor.rodar("--job", JOB, "--liberar", "zzz")
    assert r.returncode == 1
    assert "recusada: zzz — a obra não está estacionada neste job" in r.stderr
    assert "retomado" not in r.stdout


def test_liberar_nao_combina_com_apply(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    r = servidor.rodar(str(pasta), "--apply", "--liberar", "o1")
    assert r.returncode == 2 and "nao combina com --apply" in r.stderr
    assert servidor.chamadas == []


def test_o_resumo_lista_a_obra_estacionada_com_o_par_ao_lado(servidor):
    servidor.job = _job(estado="estacionado", classificar="pendente")
    for e in servidor.job["etapas"]:
        if e["obra_id"] == "o1" and e["etapa"] == "duplicata":
            e["estado"] = "estacionado"
            e["detalhe"] = {"duplicata_provavel": True, "pares": [
                {"obra_id": "o2", "classificacao": "duplicata_provavel", "jaccard": 0.91}]}
    r = servidor.rodar("--job", JOB)
    assert r.returncode == 0, r.stderr
    assert "estado: estacionado" in r.stdout and "duplicata: concluido 1 · estacionado 1" in r.stdout
    assert "1 obra(s) estacionada(s) esperam o dono (duplicata provavel)" in r.stdout
    assert f"acervo pipeline --job {JOB} --liberar <obra>" in r.stdout
    assert "o1 ↔ o2 (Jaccard 0.91)" in r.stdout
    assert "indexar: pendente 2" in r.stdout


def test_o_resumo_conta_a_etapa_espelhar(servidor):
    r = servidor.rodar("--job", JOB)
    assert r.returncode == 0, r.stderr
    assert "espelhar: concluido 2" in r.stdout
    assert r.stdout.index("triagem:") < r.stdout.index("espelhar:") < r.stdout.index("catalogacao:")


def test_o_conversor_acorda_antes_de_criar_o_job_porque_o_espelho_roda_no_servidor(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    ingerir, _ = _ingerir_falso(tmp_path, _lote())
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 0, r.stderr
    assert servidor.conversor_chamadas.read_text().split() == ["acordar"]
    r = servidor.rodar("--lote", LOTE)
    assert r.returncode == 0, r.stderr
    assert servidor.conversor_chamadas.read_text().split() == ["acordar", "acordar"]


def test_ver_o_estado_ou_liberar_nao_acorda_o_conversor(servidor):
    servidor.rodar("--job", JOB)
    servidor.rodar("--job", JOB, "--liberar", "o1")
    assert not servidor.conversor_chamadas.exists()


def test_conversor_que_nao_acorda_avisa_e_o_job_sai_assim_mesmo(servidor):
    r = servidor.rodar("--lote", LOTE, conversor_sai=3)
    assert r.returncode == 0, r.stderr
    assert "o conversor nao acordou (3)" in r.stderr and "acervo pipeline --lote <id>" in r.stderr
    assert f"job: {JOB}" in r.stdout and len(servidor.criacoes()) == 1


def test_excecoes_paginadas_e_contagem_global_sem_perder_detalhe(servidor):
    servidor.job["etapas"] = [
        {"id": str(i), "obra_id": f"obra-{i:03}", "etapa": "espelhar",
         "estado": "falhou", "erro": f"erro {i}", "detalhe": {"causa": i}}
        for i in range(47)]
    vistos = []
    for parte, quantidade in [(1, 20), (2, 20), (3, 7)]:
        r = servidor.rodar("--job", JOB, "--json", "--parte", str(parte))
        assert r.returncode == 0, r.stderr
        res = json.loads(r.stdout)
        assert res["obras"] == 47
        assert res["por_etapa"] == {"espelhar": {"falhou": 47}}
        pag = res["excecoes"]
        assert pag["total"] == 47 and pag["partes"] == 3
        assert pag["proxima_parte"] == (parte + 1 if parte < 3 else None)
        assert len(pag["itens"]) == quantidade
        vistos.extend(pag["itens"])
    assert vistos == servidor.job["etapas"]


def test_tabela_preserva_o_contrato_integral(servidor):
    r = servidor.rodar("--job", JOB, "--json", "--tabela")
    assert r.returncode == 0 and json.loads(r.stdout) == servidor.job


def test_estado_desconhecido_erro_e_detalhe_nao_somem(servidor):
    servidor.job["etapas"] = [
        {"id": str(i), "obra_id": str(i), "etapa": "nova",
         "estado": estado, **extra}
        for i, (estado, extra) in enumerate([
            ("inedito", {}), ("concluido", {"erro": "falha tardia"}),
            ("concluido", {"detalhe": {"aviso": "nao promover"}}),
            ("pendente", {}), ("executando", {}), ("concluido", {})])]
    r = servidor.rodar("--job", JOB, "--json")
    res = json.loads(r.stdout)
    assert res["etapas_total"] == 6 and res["excecoes"]["total"] == 3
    assert {e["id"] for e in res["excecoes"]["itens"]} == {"0", "1", "2"}
    texto = servidor.rodar("--job", JOB).stdout
    assert "nova:" in texto and "inedito 1" in texto


def test_pagina_inexistente_e_combinacao_ambigua_recusam(servidor):
    for flags in [("--parte", "0"), ("--parte", "2"), ("--parte", "2", "--tabela")]:
        r = servidor.rodar("--job", JOB, *flags)
        assert r.returncode == 2, (flags, r.stdout, r.stderr)


def test_job_grande_sem_excecao_tem_saida_constante(servidor):
    servidor.job["etapas"] = [
        {"id": str(i), "obra_id": str(i), "etapa": "triagem", "estado": "concluido"}
        for i in range(10000)]
    r = servidor.rodar("--job", JOB, "--json")
    assert r.returncode == 0
    res = json.loads(r.stdout)
    assert res["obras"] == 10000 and res["excecoes"]["total"] == 0
    assert res["por_etapa"] == {"triagem": {"concluido": 10000}}
    assert len(r.stdout.encode()) < 1500


def test_detalhe_de_sucesso_regular_nao_vira_excecao(servidor):
    casos = [
        ("espelhar", {"metodo": "perfil", "trechos": 5, "servivel": True,
                      "ja_selada": False, "julgamento": "servível", "impressao_id": "i"}),
        ("duplicata", {"pares": [], "sem_espelho": False, "duplicata_provavel": False}),
        ("classificar", {"especie": "livro", "conceitos": ["c"], "nenhum_cobre": False, "versao_ficha": 2}),
        ("indexar", {"indexada": True, "lote_motor": "l", "gate_aprovado": True}),
        ("promocao", {"promovida": True, "motivo": None}),
    ]
    servidor.job["etapas"] = [
        {"id": str(i), "obra_id": "o1", "etapa": nome, "estado": "concluido", "detalhe": d}
        for i, (nome, d) in enumerate(casos)]
    r = servidor.rodar("--job", JOB, "--json")
    assert json.loads(r.stdout)["excecoes"]["total"] == 0
    for e in servidor.job["etapas"]:
        e["detalhe"]["aviso_novo"] = "visivel"
    r = servidor.rodar("--job", JOB, "--json")
    assert json.loads(r.stdout)["excecoes"]["total"] == 5


def test_medida_compara_mesmo_job_sem_fingir_uso_do_modelo(servidor):
    servidor.job["etapas"] = [
        {"id": str(i), "obra_id": str(i), "etapa": "triagem", "estado": "concluido"}
        for i in range(200)]
    r = servidor.rodar("--job", JOB, "--medida")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["job"] == JOB and res["obras"] == 200
    assert "não medidos" in res["escopo"]
    antes, depois = res["series"]["antes_json_integral"], res["series"]["depois_json"]
    assert depois["media"] < antes["media"] / 10
    assert depois["p90"] == depois["media"] and depois["metodo"]


# --- acervo ler biblioteca posicao (bin/_acervo/posicao) -----------------------------------------------------------

OBRA = "55555555-5555-4555-8555-555555555555"
TITULO = "Nota Técnica: Como elaborar modelo lógico de programa"


class _HandlerPosicao(BaseHTTPRequestHandler):
    falso: "FalsoPosicao"

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.falso.chamadas.append(self.path)
        if self.path.endswith("/situacao") and (OBRA in self.path or "T%C3%ADtulo" in self.path or "Nota" in self.path):
            corpo, status = {"obra_id": OBRA, "titulo": TITULO}, 200
        else:
            corpo, status = {"title": "ObraNaoEncontrada", "detail": self.path}, 404
        dados = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


class FalsoPosicao:
    def __init__(self):
        self.chamadas = []
        handler = type("HP", (_HandlerPosicao,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def servidor_posicao():
    f = FalsoPosicao()
    try:
        yield f
    finally:
        f.fechar()


def _motor(tmp_path, saida: str, codigo: int = 0):
    gravado = tmp_path / "args.json"
    script = tmp_path / "motor_falso.py"
    script.write_text(textwrap.dedent(f"""
        import json, sys
        json.dump(sys.argv[1:], open({str(gravado)!r}, "w"))
        sys.stdout.write({saida!r})
        sys.stderr.write("motor: erro de teste\\n" if {codigo} else "")
        sys.exit({codigo})
    """))
    return script, gravado


def _rodar(servidor_posicao, motor, *argv, via_acervo=False):
    env = {**os.environ, "MOTOR_ACERVO_URL": servidor_posicao.url, "RAG_API_URL": "", "RAG_API_BASE": "",
           "RAG_API_TOKEN": "t", "PF_MOTOR": str(motor)}
    cmd = ["bash", str(ACERVO), "ler", "biblioteca", "posicao", *argv] if via_acervo else [sys.executable, str(POSICAO), *argv]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=60, check=False)


def _fonte(o, n, secao="a"):
    nome = TITULO if o == OBRA else f"Outra obra {o}"
    return {"n": n, "obra": nome, "arquivo": f"{o}.pdf", "section_id": secao, "secao_id": f"id-{o}-{secao}",
            "sim": 0.3, "score": 0.02, "texto": None}


def _busca(*obras, por_trecho=False):
    itens = []
    for o in obras:
        itens.append(_fonte(o, len(itens) + 1))
        if por_trecho:
            itens.append(_fonte(o, len(itens) + 1, secao="b"))
    return json.dumps({"fontes": itens, "cobertura": "fraca", "sinal": {"medida": "sim"}})


def test_obra_na_terceira_posicao_sai_0_com_a_posicao(servidor_posicao, tmp_path):
    motor, gravado = _motor(tmp_path, _busca("x", "y", OBRA, "z"))
    r = _rodar(servidor_posicao, motor, OBRA)
    assert r.returncode == 0, r.stderr
    assert f"posicao: 3 de 10 · {TITULO} ({OBRA})" in r.stdout
    assert json.loads(gravado.read_text()) == ["rag", "buscar", "biblioteca", "--origem", "autoteste", "--k", "10",
                                                "--texto", "nenhum", TITULO]


def test_a_posicao_conta_obra_e_nao_trecho(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, _busca("x", "y", OBRA, por_trecho=True))
    r = _rodar(servidor_posicao, motor, OBRA)
    assert "posicao: 3 de 10" in r.stdout


def test_obra_fora_das_k_primeiras_sai_1_e_diz_quantas_vieram(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, _busca("a", "b", "c", OBRA))
    r = _rodar(servidor_posicao, motor, OBRA, "--k", "3")
    assert r.returncode == 1
    assert "fora das 3 primeiras (3 obra(s) vieram)" in r.stdout


def test_json_diz_posicao_e_se_esta_entre_as_k(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor_posicao, motor, OBRA, "--json", "--k", "5")
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"obra_id": OBRA, "titulo": TITULO, "k": 5, "posicao": 1,
                                    "entre_as_k_primeiras": True, "vieram": 1}


def test_a_resposta_com_obra_aninhada_tambem_se_le(servidor_posicao, tmp_path):
    corpo = json.dumps({"resultado": {"secoes": [{"obra": "x"}, {"documento": {"obra_id": OBRA}}]}})
    motor, _ = _motor(tmp_path, corpo)
    assert _rodar(servidor_posicao, motor, OBRA).returncode == 0


def test_o_titulo_casa_sem_diferenca_de_caixa_acento_composto_ou_espaco(servidor_posicao, tmp_path):
    variante = "  NOTA TÉCNICA:  Como elaborar modelo lógico de programa "
    corpo = json.dumps({"fontes": [{"n": 1, "obra": "Outra"}, {"n": 2, "obra": variante}]})
    motor, _ = _motor(tmp_path, corpo)
    r = _rodar(servidor_posicao, motor, OBRA)
    assert r.returncode == 0 and "posicao: 2 de 10" in r.stdout


def test_quando_o_motor_traz_o_id_o_id_decide_e_nao_o_titulo(servidor_posicao, tmp_path):
    corpo = json.dumps({"fontes": [{"obra_id": "outro-id", "obra": TITULO}, {"obra_id": OBRA, "obra": TITULO}]})
    motor, _ = _motor(tmp_path, corpo)
    assert "posicao: 2 de 10" in _rodar(servidor_posicao, motor, OBRA).stdout
    corpo = json.dumps({"fontes": [{"obra_id": "outro-id", "obra": TITULO}]})
    motor, _ = _motor(tmp_path, corpo)
    assert _rodar(servidor_posicao, motor, OBRA).returncode == 1


def test_resposta_sem_fontes_diz_fora_das_k_e_sai_1(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, json.dumps({"fontes": [], "cobertura": "fraca"}))
    r = _rodar(servidor_posicao, motor, OBRA)
    assert r.returncode == 1 and "fora das 10 primeiras (0 obra(s) vieram)" in r.stdout


def test_busca_que_falha_sai_5_ou_3_com_a_causa(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, "", codigo=1)
    r = _rodar(servidor_posicao, motor, OBRA)
    assert r.returncode == 5 and "a busca saiu 1: motor: erro de teste" in r.stderr
    motor3, _ = _motor(tmp_path, "", codigo=3)
    assert _rodar(servidor_posicao, motor3, OBRA).returncode == 3


def test_saida_que_nao_e_json_sai_5(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, "nada de json")
    r = _rodar(servidor_posicao, motor, OBRA)
    assert r.returncode == 5 and "nao e JSON" in r.stderr


def test_obra_que_o_acervo_nao_conhece_sai_1(servidor_posicao, tmp_path):
    motor, gravado = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor_posicao, motor, "00000000-0000-4000-8000-000000000000")
    assert r.returncode == 1 and "ObraNaoEncontrada" in r.stderr
    assert not gravado.exists()


def test_servico_fora_sai_3(tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    env = {**os.environ, "MOTOR_ACERVO_URL": "http://127.0.0.1:9", "RAG_API_URL": "", "RAG_API_BASE": "", "PF_MOTOR": str(motor)}
    r = subprocess.run([sys.executable, str(POSICAO), OBRA], capture_output=True, text=True, env=env, timeout=60, check=False)
    assert r.returncode == 3 and "rota fora" in r.stderr


@pytest.mark.parametrize("argv, trecho", [
    ((), "falta a obra"),
    ((OBRA, "--k", "0"), "--k vai de 1 a 100"),
    ((OBRA, "--k", "101"), "--k vai de 1 a 100"),
    ((OBRA, "--semsentido"), "argumento que o ato nao le"),
])
def test_uso_errado_sai_2_sem_buscar(servidor_posicao, tmp_path, argv, trecho):
    motor, gravado = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor_posicao, motor, *argv)
    assert r.returncode == 2 and trecho in r.stderr
    assert not gravado.exists()


def test_a_origem_da_busca_e_uma_que_o_motor_aceita_e_manda_texto_literal():
    motor = (RAIZ / "bin" / "motor").read_text(encoding="utf-8")
    literais = re.search(r"^ORIGENS_LITERAIS = \(([^)]*)\)", motor, re.M).group(1)
    todas = re.search(r"^ORIGENS = \(([^)]*)\)", motor, re.M).group(1)
    nomes = lambda s: {x.strip().strip('"') for x in s.split(",") if x.strip()}  # noqa: E731
    texto = POSICAO.read_text(encoding="utf-8")
    origem = re.search(r'^ORIGEM = "([^"]+)"', texto, re.M).group(1)
    assert origem in nomes(todas) and origem in nomes(literais)


def test_o_ato_esta_na_porta_do_acervo(servidor_posicao, tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor_posicao, motor, OBRA, via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert "posicao: 1 de 10" in r.stdout


# --- retrato e diferença (bin/_acervo/retrato.py) ------------------------------------------------------------------

AGORA = "2026-10-07T22:00:00Z"


def _obra(i, marcacao="transcrita e indexada", retirada=False):
    return {"id": i, "titulo": f"Obra {i}", "retirada": retirada, "tem_autoria": True, "marcacao": marcacao,
            "objeto": f"acervo/sha-{i}", "objeto_id": f"sha-{i}", "ficha_ok": True}


def _imp(i, obra, servivel=True, faixas=None, marcada=False):
    imp = {"id": i, "obra": obra, "estado": "servindo", "metodo": "a1b2c3d4e5f6", "espelho": True,
           "digest": f"dig-{i}", "regua": "7", "servivel": servivel, "imperfeita": False, "reclamada": False}
    if faixas is not None:
        imp.update(faixas=faixas, marcada=marcada)
    return imp


def _ix(i, imp, obra, n=3):
    return {"id": i, "imp": imp, "obra": obra, "estado": "servindo", "gran": "trecho", "part": "biblioteca",
            "geracao_servindo": True, "n": n, "h": "h"}


def _dados():
    d = {
        "obras": [_obra("o1"), _obra("o2", marcacao="inteira"), _obra("o3", retirada=True)],
        "impressoes": [_imp("i1", "o1", faixas=3, marcada=True), _imp("i2", "o2", faixas=1)],
        "aposentadas": [], "total": 3,
        "trechos": {"i1": {"imp": "i1", "n": 3, "h": "h"}, "i2": {"imp": "i2", "n": 0, "h": "z"}},
        "motor": {"geracoes": [{"id": "g1", "particao": "biblioteca", "estado": "servindo", "numero": 1,
                                "embedder": "Qwen/Qwen3-Embedding-0.6B", "dimensao_trecho": "1024",
                                "dimensao_faceta": "256"}],
                  "indices": [_ix("x1", "i1", "o1")], "faceta_alvo_errado": []},
        "i13": {"obra": [], "casa": [], "existentes": ["i1", "i2"]}, "i13_motor": ["i1"],
        "versao": 7, "balde": {"espelhos": {("sha-o1", "dig-i1"), ("sha-o2", "dig-i2")},
                               "objetos": {"acervo/sha-o1", "acervo/sha-o2", "acervo/sha-o3"}},
        "espelhos_orfaos": 0,
    }
    return pa.completar(d)


PROJECAO = {
    "o1": {"obra_id": "o1", "servivel": True, "degrau": "ancorado", "impressao_id": "i1", "geracao": 1,
           "embedder": "Qwen/Qwen3-Embedding-0.6B", "dimensao": 1024, "trechos_com_vetor": 3,
           "trechos_elegiveis": 3},
    "o2": {"obra_id": "o2", "servivel": True, "degrau": "ancorado", "impressao_id": "i2", "geracao": None,
           "embedder": None, "dimensao": None, "trechos_com_vetor": 0, "trechos_elegiveis": 0},
}


def _retrato(d=None, proj=None):
    d = d or _dados()
    return retrato.montar(d, pa.avaliar_invariantes(d), PROJECAO if proj is None else proj, AGORA)


@pytest.fixture
def par():
    antes = _retrato()
    depois = copy.deepcopy(antes)
    depois["cabecalho"]["tirado_em"] = "2026-11-06T10:00:00Z"
    o2 = depois["linhas"][1]
    o2.update(exposicao="trecho", cobertura="completa", invariantes=[])
    depois["linhas"].pop(2)
    novo = copy.deepcopy(depois["linhas"][0])
    novo.update(obra_id="o4", titulo="Obra o4")
    depois["linhas"].append(novo)
    depois["rodape"]["obra"] = {"viva": 3}
    return antes, depois


def test_quem_entrou_e_quem_saiu(par):
    dif = retrato.diferenca(*par)
    assert [o["obra_id"] for o in dif["entraram"]] == ["o4"]
    assert [o["obra_id"] for o in dif["sairam"]] == ["o3"]
    assert dif["de"] == "2026-10-07T22:00:00Z" and dif["para"] == "2026-11-06T10:00:00Z"


def test_o_que_mudou_na_obra_que_ficou(par):
    dif = retrato.diferenca(*par)
    assert [o["obra_id"] for o in dif["mudaram"]] == ["o2"]
    mudancas = dif["mudaram"][0]["mudancas"]
    assert mudancas["exposicao"] == ["arquivo", "trecho"]
    assert mudancas["cobertura"] == ["sem índice", "completa"]
    assert mudancas["invariantes"] == [["I11"], []]
    assert "situacao" not in mudancas


def test_o_rodape_so_traz_a_entidade_que_se_mexeu(par):
    dif = retrato.diferenca(*par)
    assert dif["rodape"]["obra"] == {"antes": {"retirada": 1, "viva": 2}, "depois": {"viva": 3}}
    assert "espelho_qualidade" not in dif["rodape"]


def test_retratos_iguais_dizem_que_nada_mudou():
    r = _retrato()
    dif = retrato.diferenca(r, copy.deepcopy(r))
    assert dif["entraram"] == dif["sairam"] == dif["mudaram"] == [] and dif["rodape"] == {}
    assert "nada mudou entre os dois retratos" in retrato.texto_diferenca(dif)


def test_o_texto_diz_o_antes_e_o_depois_de_cada_campo(par):
    texto = retrato.texto_diferenca(retrato.diferenca(*par))
    assert "obras: 3 -> 3 (entraram 1, saíram 1, mudaram 1)" in texto
    assert "entraram: o4" in texto and "saíram: o3" in texto
    assert "exposicao arquivo -> trecho" in texto and "cobertura sem índice -> completa" in texto
    assert "rodapé obra:" in texto


def test_o_texto_corta_a_lista_longa_e_aponta_o_json(par):
    antes, depois = par
    for i in range(retrato.MOSTRAR + 3):
        extra = copy.deepcopy(depois["linhas"][0])
        extra.update(obra_id=f"n{i:02d}", titulo=f"Nova {i}")
        depois["linhas"].append(extra)
    texto = retrato.texto_diferenca(retrato.diferenca(antes, depois))
    assert f"… +{3 + 1} que entraram" in texto
    assert "diferenca.entraram no --json" in texto


def test_executar_com_antes_junta_a_diferenca_ao_json(par, capsys):
    antes, _ = par
    ler = lambda sql: None  # noqa: E731
    original = retrato.pa.coletar
    try:
        retrato.pa.coletar = lambda ler, balde=None, orfaos=None: _dados()
        saida = retrato.executar(
            quero_json=True, ler=ler, balde=None, orfaos=None,
            projecao=lambda: PROJECAO,
            agora="2026-11-06T10:00:00Z", quem="t", antes=antes,
        )
    finally:
        retrato.pa.coletar = original
    corpo = json.loads(capsys.readouterr().out)
    assert "diferenca" in corpo and corpo["diferenca"]["para"] == "2026-11-06T10:00:00Z"
    assert corpo["diferenca"]["de"] == "2026-10-07T22:00:00Z"
    assert isinstance(saida, int)


def test_diferenca_sem_retrato_e_recusada_sem_tocar_em_banco():
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--diferenca", "x.json"],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "--diferenca so vale com --retrato" in r.stderr


def test_arquivo_que_nao_e_retrato_e_recusado(tmp_path):
    ruim = tmp_path / "antes.json"
    ruim.write_text(json.dumps({"qualquer": "coisa"}))
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--retrato", "--diferenca", str(ruim)],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "nao e um retrato" in r.stderr


def test_arquivo_ausente_e_recusado(tmp_path):
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--retrato", "--diferenca",
                        str(tmp_path / "nao-existe.json")],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "nao li" in r.stderr


# --- conceito e indicacao (bin/_acervo/tesauro.py) -----------------------------------------------------------------

def _acha_python() -> str | None:
    candidatos = [
        "/opt/platafirma/venvs/acervo/bin/python",
        "/opt/platafirma/current/venv/acervo/bin/python",
        sys.executable,
        shutil.which("python3") or "",
    ]
    for cand in candidatos:
        if cand and Path(cand).is_file():
            r = subprocess.run([cand, "-c", "import requests"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return cand
    return None


class ServidorFalso:
    def __init__(self) -> None:
        self.chamadas: list[tuple[str, str, dict | None]] = []
        self.status_forcado: int | None = None
        self.corpo_forcado: dict | None = None
        self.atraso_s: float = 0.0
        self.versao_atual = "a1b2c3d4e5f6"
        self.pedidos: dict[str, tuple[dict, dict]] = {}
        srv_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _responder(self, status: int, corpo: dict) -> None:
                if srv_ref.atraso_s > 0:
                    time.sleep(srv_ref.atraso_s)
                dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                ct = "application/problem+json" if status >= 400 else "application/json"
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def _ler_corpo(self) -> dict:
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}")

            def do_GET(self) -> None:
                srv_ref.chamadas.append(("GET", self.path, None))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                if self.path == "/acervo/conceitos/inexistente":
                    self._responder(404, {"title": "ConceitoNaoEncontrado", "detail": "inexistente"})
                    return
                if self.path.startswith("/acervo/conceitos/") and self.path.endswith("/relacoes"):
                    self._responder(200, {"itens": [], "proximo": None})
                    return
                if self.path.startswith("/acervo/conceitos/"):
                    slug = self.path.rsplit("/", 1)[1]
                    self._responder(200, {
                        "id": "15a606f0-611f-4f44-b0e6-3ab7b445f44b",
                        "slug": slug,
                        "rotulo": "Técnica legislativa",
                        "lingua": "pt",
                        "definicao": "Arte de redigir leis.",
                        "natureza": "modelo",
                        "estatuto": "doutrinario",
                        "endereco": None,
                        "mais_amplo": None,
                        "filhos_exclusivos": False,
                        "obras_vivas": 2,
                        "rotulos": [{"rotulo": "Técnica legislativa", "lingua": "pt", "papel": "preferido"}],
                        "rotulos_alternativos": [{"rotulo": "legistics", "lingua": "en"}],
                        "versao": srv_ref.versao_atual,
                    })
                    return
                if self.path == "/acervo/conceitos":
                    self._responder(200, {"itens": [
                        {"slug": "tecnica-legislativa", "rotulo": "Técnica legislativa",
                         "outros_rotulos": "legistics / redacao normativa",
                         "natureza": "modelo", "estatuto": "doutrinario"},
                        {"slug": "revisao-de-codigo", "rotulo": "Revisão de código",
                         "outros_rotulos": ["code review", "peer review"],
                         "natureza": "processo", "estatuto": "doutrinario"},
                    ], "proximo": None})
                    return
                if self.path.startswith("/acervo/indicacoes/"):
                    chave = self.path.rsplit("/", 1)[1]
                    if chave == "nao-existe":
                        self._responder(404, {"title": "IndicacaoNaoEncontrada", "detail": chave})
                        return
                    self._responder(200, {
                        "tipo": "termo",
                        "termo": "licença de software",
                        "slug": chave,
                        "obras_contagem": 0,
                        "obras": [],
                        "de_obra_retirada": ["ind-ret-1"],
                        "destino": {"acao": "sem_garantia", "motivo": "nenhuma obra viva sustenta o termo"},
                        "versao": "998877665544",
                    })
                    return
                if self.path.startswith("/acervo/indicacoes"):
                    self._responder(200, {"versao": "112233445566", "itens": [
                        {"id": "ind-1", "termo": "licença de software", "slug": "licenca-de-software",
                         "estado": "pendente", "obra_id": "obra-r", "obra_retirada": True},
                    ], "proximo": None})
                    return
                self._responder(404, {"title": "NaoEncontrado", "detail": self.path})

            def do_POST(self) -> None:
                corpo = self._ler_corpo()
                srv_ref.chamadas.append(("POST", self.path, corpo))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                if self.path == "/acervo/conceitos":
                    aplicar = bool(corpo.get("aplicar"))
                    resp = {
                        "modo": "aplicado" if aplicar else "plano",
                        "aprovado": True,
                        "versao": "f6e5d4c3b2a1",
                        "conceito": corpo,
                    }
                    if aplicar:
                        resp["id"] = "cid-novo"
                    self._responder(201 if aplicar else 200, resp)
                    return
                if self.path == "/acervo/indicacoes":
                    aplicar = bool(corpo.get("aplicar"))
                    decisao = corpo.get("decisao")
                    termos = corpo.get("termos") or []
                    if decisao == "descartar":
                        if not aplicar:
                            self._responder(200, {
                                "plano": True, "aprovado": True,
                                "itens": [], "descartes": [{"termo": "licença de software", "indicacoes": 1}],
                            })
                        else:
                            self._responder(201, {
                                "aplicado": True, "aprovado": True,
                                "criados": [], "ligados_a_existente": [], "sem_garantia": [],
                                "indicacoes_admitidas": 0, "indicacoes_descartadas": 1,
                                "motivo": corpo.get("motivo"),
                            })
                        return
                    tem_sem_garantia = ("licenca-de-software" in termos) or (not termos)
                    itens = [
                        {"termo": "protocolo HTTP", "slug": "protocolo-http", "obras_contagem": 1,
                         "obras": ["o1"], "indicacao_ids": ["i1"], "de_obra_retirada": [],
                         "acao": "ligar_existente", "conceito": "http"},
                        {"termo": "filtragem de URL", "slug": "filtragem-de-url", "obras_contagem": 2,
                         "obras": ["o2", "o3"], "indicacao_ids": ["i2", "i3"], "de_obra_retirada": ["i4"],
                         "acao": "criar", "conceito": "filtragem-de-url"},
                    ]
                    if tem_sem_garantia:
                        itens.append({
                            "termo": "licença de software", "slug": "licenca-de-software",
                            "obras_contagem": 0, "obras": [], "indicacao_ids": ["i5"],
                            "de_obra_retirada": ["i5"], "acao": "sem_garantia",
                            "motivo": "nenhuma obra viva sustenta o termo; descarte-o",
                        })
                    if not aplicar:
                        aprovado = not (decisao == "admitir" and tem_sem_garantia)
                        self._responder(200, {
                            "plano": True, "aprovado": aprovado, "total_termos": len(itens),
                            "itens": itens, "descartes": [{"termo": t, "indicacoes": 1} for t in (corpo.get("descartar") or [])],
                        })
                        return
                    if decisao == "admitir" and tem_sem_garantia:
                        self._responder(422, {
                            "title": "IndicacaoReprovada",
                            "detail": "obra retirada não sustenta indicação como garantia literária: licença de software",
                            "plano": {"aprovado": False, "itens": itens},
                        })
                        return
                    self._responder(201, {
                        "aplicado": True, "aprovado": True,
                        "criados": [{"id": "c-novo", "slug": "filtragem-de-url", "rotulo": "filtragem de URL"}],
                        "ligados_a_existente": [{"id": "c-http", "slug": "http", "termo": "protocolo HTTP"}],
                        "sem_garantia": [],
                        "indicacoes_admitidas": 3,
                        "indicacoes_descartadas": 1,
                        "motivo": corpo.get("motivo"),
                    })
                    return
                self._responder(404, {"title": "NaoEncontrado", "detail": self.path})

            def do_PATCH(self) -> None:
                corpo = self._ler_corpo()
                srv_ref.chamadas.append(("PATCH", self.path, corpo))
                if srv_ref.status_forcado is not None:
                    self._responder(srv_ref.status_forcado, srv_ref.corpo_forcado or {})
                    return
                aplicar = bool(corpo.get("aplicar"))
                ped_id = corpo.get("pedido")
                limpo = {k: v for k, v in corpo.items() if k not in ("pedido", "aplicar")}
                if aplicar and ped_id and ped_id in srv_ref.pedidos:
                    gravado_limpo, resp_grav = srv_ref.pedidos[ped_id]
                    if gravado_limpo != limpo:
                        self._responder(422, {"title": "PedidoComConteudoDiferente", "detail": ped_id})
                        return
                    self._responder(200, {**resp_grav, "pedido": ped_id, "estado_pedido": "ja-gravada"})
                    return
                if "versao" in corpo and corpo["versao"] != srv_ref.versao_atual:
                    self._responder(409, {
                        "title": "VersaoDiferente",
                        "detail": "versão divergente",
                        "versao_esperada": corpo["versao"],
                        "versao_atual": srv_ref.versao_atual,
                    })
                    return
                resp = {
                    "modo": "aplicado" if aplicar else "plano",
                    "aprovado": True,
                    "id": "15a606f0-611f-4f44-b0e6-3ab7b445f44b",
                    "versao_antes": srv_ref.versao_atual,
                    "versao": "c0ffee123456",
                    "conceito": {"slug": "tecnica-legislativa", "rotulo": corpo.get("rotulo") or "Técnica legislativa"},
                    "antes": {"rotulo": "Técnica legislativa", "definicao": "Antiga", "rotulos": []},
                    "depois": {
                        "rotulo": corpo.get("rotulo") or "Técnica legislativa",
                        "definicao": corpo.get("definicao") or "Antiga",
                        "rotulos": [{"rotulo": "Técnica legislativa", "lingua": corpo.get("lingua") or "pt", "papel": "preferido"}],
                    },
                    "colisoes": [],
                    "motivo": corpo.get("motivo"),
                    "emitido_por": corpo.get("autor") or "time-platafirma",
                }
                if aplicar and ped_id:
                    srv_ref.pedidos[ped_id] = (limpo, resp)
                    resp = {**resp, "pedido": ped_id, "estado_pedido": "gravada"}
                self._responder(200, resp)

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}"
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()

    def fechar(self) -> None:
        self._http.shutdown()
        self._http.server_close()
        self._thread.join(timeout=5)

    def env(self) -> dict[str, str]:
        py = _acha_python()
        env = {
            **os.environ,
            "MOTOR_ACERVO_URL": self.url,
            "RAG_API_URL": self.url,
            "RAG_API_BASE": self.url,
            "PF_CADEIRA": "engenharia",
        }
        if py:
            env["PATH"] = str(Path(py).parent) + os.pathsep + env.get("PATH", "")
        return env

    def rodar(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(ACERVO), *args],
            env=self.env(),
            capture_output=True,
            text=True,
            timeout=30,
        )


@pytest.fixture
def srv():
    s = ServidorFalso()
    try:
        yield s
    finally:
        s.fechar()


def _checar_erro_6_campos(proc: subprocess.CompletedProcess[str], exit_esperado: int, codigo: str) -> dict:
    assert proc.returncode == exit_esperado, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    if exit_esperado in (2, 3, 4, 5):
        ultima = [ln for ln in proc.stderr.splitlines() if ln.strip()][-1]
        obj_err = json.loads(ultima)["erro"]
        for k in ("codigo", "onde", "recebido", "regra", "cura", "proximo"):
            assert k in obj_err, (k, obj_err)
        assert obj_err["codigo"] == codigo
        return obj_err
    assert codigo in proc.stdout
    for trecho in ("recebido:", "regra:", "cura:", "proximo:"):
        assert trecho in proc.stdout
    return {}


@pytest.mark.parametrize("argv", [
    ("ler", "biblioteca", "conceito", "--help"),
    ("listar", "biblioteca", "conceito", "--help"),
    ("criar", "biblioteca", "conceito", "--help"),
    ("trocar", "biblioteca", "conceito", "--help"),
    ("renomear", "biblioteca", "conceito", "--help"),
    ("listar", "biblioteca", "indicacao", "--help"),
    ("ler", "biblioteca", "indicacao", "--help"),
    ("admitir", "biblioteca", "indicacao", "--help"),
    ("descartar", "biblioteca", "indicacao", "--help"),
    ("ensaiar", "--help"),
    ("curar", "conceitos", "--help"),
])
def test_help_por_ato_sai_0_sem_chamar_rede(srv, argv):
    r = srv.rodar(*argv)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()
    assert srv.chamadas == []


def test_ler_e_listar_conceito_primeira_linha_fixa_e_404_sai_1(srv):
    r = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    assert r.returncode == 0, r.stderr
    primeira = r.stdout.splitlines()[0]
    assert primeira == f"conceito · versao {srv.versao_atual} · tecnica-legislativa"
    assert "pt" in r.stdout and "en|legistics" in r.stdout

    rj = srv.rodar("ler", "conceito", "tecnica-legislativa", "--json")
    assert rj.returncode == 0
    assert json.loads(rj.stdout)["versao"] == srv.versao_atual

    rl = srv.rodar("listar", "biblioteca", "conceito", "--natureza", "modelo")
    assert rl.returncode == 0
    assert rl.stdout.splitlines()[0].startswith("conceito · versao ")
    assert rl.stdout.splitlines()[0].endswith("· 1 itens")

    # DT 1386: --termo casa também outros_rotulos como str (' / ') e como list
    r_str = srv.rodar("listar", "biblioteca", "conceito", "--termo", "legistics")
    assert r_str.returncode == 0
    assert "tecnica-legislativa" in r_str.stdout and r_str.stdout.splitlines()[0].endswith("· 1 itens")
    r_lst = srv.rodar("listar", "biblioteca", "conceito", "--termo", "peer review")
    assert r_lst.returncode == 0
    assert "revisao-de-codigo" in r_lst.stdout and r_lst.stdout.splitlines()[0].endswith("· 1 itens")

    r404 = srv.rodar("ler", "biblioteca", "conceito", "inexistente")
    _checar_erro_6_campos(r404, 1, "conceito-inexistente")


def test_gravar_em_classe_guardada_recusa_com_2_e_proximo(srv):
    r = srv.rodar("gravar", "biblioteca", "conceito", "tecnica-legislativa")
    err = _checar_erro_6_campos(r, 2, "ato-recusado")
    assert "acervo ler biblioteca conceito tecnica-legislativa" in err["proximo"]
    assert srv.chamadas == []


def test_dry_run_em_ato_de_escrita_recusa_com_2_e_aponta_ensaiar(srv):
    r = srv.rodar("criar", "biblioteca", "conceito", "x", "--dry-run")
    err = _checar_erro_6_campos(r, 2, "variante-de-flag")
    assert "ensaiar criar" in err["proximo"]
    assert srv.chamadas == []


def test_criar_e_ensaiar_criar_conceito(srv):
    re_ens = srv.rodar(
        "ensaiar", "criar", "biblioteca", "conceito", "code-review",
        "--rotulo", "Code review", "--lingua", "en",
        "--definicao", "Exame sistemático de código.",
        "--natureza", "processo", "--estatuto", "doutrinario",
        "--rotulo-alt", "pt|revisão de código",
    )
    assert re_ens.returncode == 0, re_ens.stderr
    assert re_ens.stdout.splitlines()[0].startswith("ensaio aprovado · criar conceito:code-review")
    assert srv.chamadas[-1][2]["aplicar"] is False

    r_cr = srv.rodar(
        "criar", "biblioteca", "conceito", "code-review",
        "--rotulo", "Code review", "--lingua", "en",
        "--definicao", "Exame sistemático de código.",
        "--natureza", "processo", "--estatuto", "doutrinario",
        "--rotulo-alt", "pt|revisão de código",
    )
    assert r_cr.returncode == 0, r_cr.stderr
    linhas = r_cr.stdout.splitlines()
    assert ts.validar_uuid(linhas[0])
    assert linhas[1].startswith("criada conceito:code-review · versao ")
    assert srv.chamadas[-1][2]["aplicar"] is True

    # DT 1394: --motivo-aresta separado para a ligação hierárquica
    r_ma = srv.rodar(
        "ensaiar", "criar", "biblioteca", "conceito", "code-review-2",
        "--rotulo", "Code review 2", "--lingua", "en",
        "--definicao", "Exame.", "--natureza", "processo", "--estatuto", "doutrinario",
        "--pai", "tecnica-legislativa", "--tipo", "generica", "--motivo-aresta", "motivo da aresta",
    )
    assert r_ma.returncode == 0, r_ma.stderr
    assert srv.chamadas[-1][2]["pai"]["motivo"] == "motivo da aresta"


def test_trocar_conceito_versao_rotulos_idempotencia_e_recusas(srv):
    r_slug = srv.rodar("trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
                       "--slug", "outro", "--motivo", "m")
    err_s = _checar_erro_6_campos(r_slug, 2, "flag-nao-aplicavel")
    assert "renomear" in err_s["proximo"]

    r_v = srv.rodar("trocar", "biblioteca", "conceito", "tecnica-legislativa", "000000000000",
                    "--lingua", "pt", "--motivo", "revisao de rotulos")
    _checar_erro_6_campos(r_v, 1, "versao-diferente")
    assert "acervo ler biblioteca conceito tecnica-legislativa" in r_v.stdout

    r_ens = srv.rodar(
        "ensaiar", "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--sem-rotulo-alt", "velho",
        "--motivo", "revisao de rotulos",
    )
    assert r_ens.returncode == 0, r_ens.stderr
    assert r_ens.stdout.splitlines()[0].startswith("ensaio aprovado · trocar conceito:tecnica-legislativa")
    assert srv.chamadas[-1][2]["aplicar"] is False

    ped = ts.gerar_uuid7()
    r1 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "revisao de rotulos",
        "--pedido", ped,
    )
    assert r1.returncode == 0, r1.stderr
    assert r1.stdout.splitlines()[0] == ped
    assert r1.stdout.splitlines()[1].startswith("gravada conceito:tecnica-legislativa")

    r2 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "revisao de rotulos",
        "--pedido", ped,
    )
    assert r2.returncode == 0
    assert r2.stdout.splitlines()[1].startswith("ja-gravada conceito:tecnica-legislativa")

    r3 = srv.rodar(
        "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
        "--lingua", "en", "--motivo", "outro", "--pedido", ped,
    )
    _checar_erro_6_campos(r3, 1, "pedido-com-conteudo-diferente")


def test_indicacao_listar_ler_admitir_e_descartar_com_garantia_viva(srv):
    rl = srv.rodar("listar", "biblioteca", "indicacao")
    assert rl.returncode == 0, rl.stderr
    assert rl.stdout.splitlines()[0].startswith("indicacao · versao ")
    assert "ligar ao existente http" in rl.stdout
    assert "sem garantia (só obra retirada)" in rl.stdout

    rler = srv.rodar("ler", "biblioteca", "indicacao", "licenca-de-software")
    assert rler.returncode == 0
    assert rler.stdout.splitlines()[0] == "indicacao · versao 998877665544 · licenca-de-software"

    r_ens_fail = srv.rodar("ensaiar", "admitir", "biblioteca", "indicacao", "todas", "--motivo", "triagem")
    _checar_erro_6_campos(r_ens_fail, 1, "garantia-retirada")

    r_adm_fail = srv.rodar("admitir", "biblioteca", "indicacao", "todas", "--motivo", "triagem")
    _checar_erro_6_campos(r_adm_fail, 1, "garantia-retirada")

    r_adm_ok = srv.rodar(
        "admitir", "biblioteca", "indicacao", "todas",
        "--termos", "protocolo-http,filtragem-de-url", "--motivo", "obras vivas conferidas",
    )
    assert r_adm_ok.returncode == 0, r_adm_ok.stderr
    assert ts.validar_uuid(r_adm_ok.stdout.splitlines()[0])
    assert "1 criado(s) · 1 ligado(s) ao existente" in r_adm_ok.stdout

    r_desc_flag = srv.rodar(
        "descartar", "biblioteca", "indicacao", "todas",
        "--termos", "licenca-de-software", "--natureza", "modelo", "--motivo", "m",
    )
    _checar_erro_6_campos(r_desc_flag, 2, "flag-nao-aplicavel")

    r_desc = srv.rodar(
        "descartar", "biblioteca", "indicacao", "todas",
        "--termos", "licenca-de-software", "--motivo", "obra de garantia foi retirada",
    )
    assert r_desc.returncode == 0, r_desc.stderr
    assert "1 descartada(s)" in r_desc.stdout


def test_codigos_de_saida_3_4_e_5(srv):
    srv.status_forcado = 403
    srv.corpo_forcado = {"title": "Forbidden", "detail": "negado"}
    r4 = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    _checar_erro_6_campos(r4, 4, "acesso-recusado")

    srv.status_forcado = 503
    srv.corpo_forcado = {"title": "FonteIndisponivel", "detail": "banco fora"}
    r3 = srv.rodar("ler", "biblioteca", "conceito", "tecnica-legislativa")
    _checar_erro_6_campos(r3, 3, "servico-indisponivel")
    srv.status_forcado = None

    ped = ts.gerar_uuid7()
    orig_req = ts.urllib.request.urlopen

    def _timeout_urlopen(*args, **kwargs):
        raise TimeoutError("prazo esgotado")

    ts.urllib.request.urlopen = _timeout_urlopen
    try:
        rc = ts.main([
            "trocar", "biblioteca", "conceito", "tecnica-legislativa", srv.versao_atual,
            "--lingua", "pt", "--motivo", "teste", "--pedido", ped,
        ])
        assert rc == 5
    finally:
        ts.urllib.request.urlopen = orig_req


def test_atos_transicionais_recusam_flags_indevidas_e_enviam_motivo(srv):
    if _acha_python():
        r_indev = srv.rodar(
            "definir", "biblioteca", "conceito", "tecnica-legislativa",
            "--lingua", "pt", "--endereco", "https://x.org", "--motivo", "m",
        )
        assert r_indev.returncode == 2
        assert "--endereco" in r_indev.stderr

        r_hum = srv.rodar(
            "definir", "biblioteca", "conceito", "tecnica-legislativa",
            "--lingua", "pt", "--rotulo-alt", "en|legistics", "--motivo", "revisao de rotulos",
        )
        assert r_hum.returncode == 0, r_hum.stderr
        assert "Plano de descrição e rótulos" in r_hum.stdout
        assert "pt|Técnica legislativa (preferido)" in r_hum.stdout

    r_cur_desc = srv.rodar(
        "curar", "conceitos", "--indicacoes", "todas",
        "--descartar", "licenca-de-software", "--motivo", "obra retirada",
    )
    assert r_cur_desc.returncode == 0, r_cur_desc.stderr
    assert srv.chamadas[-1][2]["motivo"] == "obra retirada"

    r_cur_unk = srv.rodar("curar", "conceitos", "--indicacoes", "todas", "--flag-inexistente")
    assert r_cur_unk.returncode == 2
