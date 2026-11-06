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
               # o conversor de verdade nunca acorda num teste: o roteiro falso só anota a chamada
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
    # e só até catalogar: o espelho é etapa do job, no servidor, e não roda dentro desta chamada
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


def test_obra_barrada_num_portao_do_encadeamento_nao_impede_o_job_das_outras(servidor, tmp_path):
    # `ingerir --ate chunk` sai 1 quando um portao barra uma obra, com o lote concluido
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


def test_lote_ja_ingerido_nao_cria_job_nem_acorda_conversor(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    lote = _lote()
    for item in lote["itens"]:
        item.update(veredito="ja_ingerido", estado="pulado")
    ingerir, _ = _ingerir_falso(tmp_path, lote)
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 1 and "nao tem obra para o job" in r.stderr
    assert servidor.criacoes() == []
    assert not servidor.conversor_chamadas.exists()


def test_lote_misto_conta_so_as_obras_criadas(servidor, tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    lote = _lote()
    lote["itens"][0].update(veredito="ja_ingerido", estado="pulado")
    ingerir, _ = _ingerir_falso(tmp_path, lote)
    r = servidor.rodar(str(pasta), "--apply", ingerir=ingerir)
    assert r.returncode == 0, r.stderr
    assert "1 obra(s)" in r.stderr


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
    # antes desta entrega: `bin/acervo` caía em «biblioteca: command not found» ao chamar `pipeline`
    r = servidor.rodar("--job", JOB, via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert f"job: {JOB}" in r.stdout
    assert "command not found" not in r.stderr


def test_a_ajuda_geral_do_acervo_sai_inteira_e_sem_executar_o_texto_de_uso():
    # a crase sem escape no texto de uso do pipeline virava substituicao de comando: «Retoma:» e «estado:» saiam
    # vazios, com «syntax error» no stderr (carta 20261105T182521-dados, ponto 4)
    env = {**os.environ, "PF_CADEIRA": "dados"}
    r = subprocess.run(["bash", str(ACERVO), "--ajuda"], capture_output=True, text=True, env=env,
                       stdin=subprocess.DEVNULL, timeout=60, check=False)
    assert r.returncode == 2
    assert "Retoma: `pipeline --lote <id>`; estado: `pipeline --job <id>`" in r.stderr
    assert "syntax error" not in r.stderr and "command not found" not in r.stderr
    assert "--liberar <sha256|obra>" in r.stderr
    # as outras duas crases soltas do texto de uso, mais antigas que a 4120: uma rodava `biblioteca objeto` (command not
    # found) e a outra rodava `motor raciocinador` de verdade a cada pedido de ajuda
    assert "(antes `biblioteca objeto`: o nome velho recusa" in r.stderr
    assert "o raciocinador e `motor raciocinador`" in r.stderr
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
    r = servidor.rodar("--lote", LOTE)  # a retomada também: o conversor pode ter dormido
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


# #4128: o mesmo job em todas as páginas; a união recupera toda exceção sem repetir.
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
