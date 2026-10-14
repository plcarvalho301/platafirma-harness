"""As leituras da face motor: consultas, trabalhos, histórico de medida, pendências e a prévia (card #3513, U2 e U3).

O rag-api é um servidor de brinquedo; o docker é um script de brinquedo que responde ao psql (pelo marcador que
cada consulta traz no começo do SQL), ao `docker exec … python` da sombra de bench e ao `inspect`; a instância é um
diretório temporário. O verbo roda de verdade, em subprocesso. O que o psql de brinquedo não prova é o SQL em si:
os testes conferem o texto que chegou (filtro, origem, a prévia fora da lista e da série), não o plano do banco.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "bin" / "_motor"))

import consultas as consultasmod  # noqa: E402
import historico as historicomod  # noqa: E402
import pendencias as pendenciasmod  # noqa: E402
import trabalhos as trabalhosmod  # noqa: E402

DOCKER_FALSO = """#!{python}
import json, os, sys
a = sys.argv[1:]
estado = json.load(open(os.environ["FAKE_DOCKER"]))
if a and a[0] == "inspect":
    print("PATH=/bin")
elif a and a[0] == "exec" and "psql" in a and "-v" in a:                       # SQL no stdin (consultas)
    sql = sys.stdin.read()
    open(os.environ["FAKE_SQL_LOG"], "a").write(sql + "\\n=====\\n")
    if estado.get("psql_fora"):
        sys.stderr.write("psql: could not connect")
        sys.exit(2)
    marcador = sql.split("*/")[0].replace("/*", "").strip()
    print(json.dumps(estado.get("psql", {{}}).get(marcador)))
elif a and a[0] == "exec" and "psql" in a and "-c" in a:                       # titulos do gabarito (medir)
    print("doc-a\\toid-a\\tObra A")
    print("doc-b\\toid-b\\tObra B")
elif a and a[0] == "exec" and "python" in a:                                   # a sombra de bench no conteiner
    if estado.get("conteiner_fora"):
        sys.stderr.write("Error response from daemon: container is not running")
        sys.exit(1)
    print(json.dumps(estado["conteiner"]))
elif a and a[0] == "exec" and "sh" in a:                                       # o tail da sombra (--sombra-ver)
    print("embeddando 3/20\\n--- pip:\\n--- fim:\\nsem arquivo fim")
elif a and a[0] == "exec" and "cat" in a:                                      # resultado.json: ainda nao ha
    sys.exit(1)
else:
    sys.exit(0)
"""

GABARITO = [
    {"id": "q1", "pergunta": "qual o prazo de resposta", "alvo_section_id": "doc-a#sec-1", "estrato": "T1"},
    {"id": "q2", "pergunta": "o que significa o termo", "alvo_obra_ids": ["oid-b"], "estrato": "T2-sentido"},
    {"id": "q3", "pergunta": "assunto que o acervo nao tem", "relevancia": "negativa"},
]


class _S:
    """O estado do rag-api de brinquedo."""
    trabalhos: list
    troca_estado: dict
    trabalhos_fora: bool
    ajustes: dict
    corpos: list
    lote: dict


class _API(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, codigo, corpo):
        dado = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/facets":
            return self._json(200, {"indice": {"acervo_sha": "abcdef1234567890", "embed_model": "m", "embed_backend": "b",
                                               "geracao": {"numero": 3, "parametros": {"embedder": "Nemotron"}}}})
        if p == "/motor/trabalhos":
            if _S.trabalhos_fora:
                return self._json(503, {"title": "Aquecendo", "detail": "subindo"})
            return self._json(200, {"itens": _S.trabalhos, "proximo": None, "lido_em": "2026-10-14T12:00:00+00:00"})
        if p == "/motor/geracoes/servindo/ajustes":
            if _S.ajustes_fora:
                return self._json(503, {"title": "Aquecendo", "detail": "subindo"})
            return self._json(200, {"particao": "biblioteca", "geracao": 3, "geracao_id": "g3-id", "ajustes": _S.ajustes,
                                    "lido_em": "2026-10-14T12:00:00+00:00"})
        if p == "/motor/trocas/biblioteca":
            if _S.troca_fora:
                return self._json(503, {"title": "Aquecendo", "detail": "subindo"})
            return self._json(200, _S.troca_estado)
        if p.startswith("/motor/indexacoes/lote/"):
            if _S.lote.get("fora"):
                return self._json(503, {"title": "Aquecendo", "detail": "subindo"})
            return self._json(200, _S.lote)
        self._json(404, {})

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        if urlparse(self.path).path == "/search":
            _S.corpos.append(corpo)
            pergunta = corpo.get("pergunta")
            if pergunta == "qual o prazo de resposta":
                fontes = [{"obra": "Obra A", "section_id": "doc-a#sec-1"}]
            elif pergunta == "o que significa o termo":
                fontes = [{"obra": "X"}, {"obra": "Obra B"}]
            else:
                fontes = [{"obra": "X"}]
            cobertura = "fraca" if pergunta == "assunto que o acervo nao tem" else "boa"
            return self._json(200, {"fontes": fontes, "cobertura": cobertura, "sinal": {"medida": "sim", "valor": 0.4},
                                    "tempos_ms": {"embed": 10.0, "vetorial": 20.0, "total": 40.0}})
        self._json(404, {})


@pytest.fixture
def motor(tmp_path):
    _S.trabalhos, _S.trabalhos_fora, _S.corpos, _S.lote = [], False, [], {}
    _S.ajustes_fora = _S.troca_fora = False
    _S.ajustes = {"aviso_de_cobertura_fraca": 0.342,
                  "virada": {"autorizada_por": "o dono disse sim", "em": "2026-10-08T15:00:00+00:00", "autor": "ia"}}
    _S.troca_estado = {"particao": "biblioteca", "servindo": {"geracao": 3, "id": "g3-id", "embedder": "Nemotron"},
                       "sombra": None, "lote": None, "ambiente": {}}
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"

    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    (instancia / "var" / "sinal").mkdir(parents=True)
    (instancia / "var" / "sinal" / "servicos.json").write_text(
        json.dumps({"servicos": {"rag-extractor-api": {"estado": "no-ar"}}}))
    medicoes = instancia / "var" / "medicoes" / "rag"
    medicoes.mkdir(parents=True)
    gabarito = tmp_path / "gabarito.jsonl"
    gabarito.write_text("\n".join(json.dumps(x) for x in GABARITO))

    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    estado = tmp_path / "docker-estado.json"
    estado.write_text(json.dumps({"psql": {}, "conteiner": {"agora": 1.0, "sombras": []}}))
    sql_log = tmp_path / "sql.log"

    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": "rag-extractor-api", "stack": "rag", "servico": "rag-api",
        "endpoint": f"{base}/search", "facets": f"{base}/facets", "token_em": "rag/RAG_API_TOKEN",
        "ajustes_da_geracao": f"{base}/motor/geracoes/servindo/ajustes", "trabalhos": f"{base}/motor/trabalhos",
        "troca": f"{base}/motor/trocas", "indexacao": f"{base}/motor/indexacoes/lote",
        "medicoes_em": "var/medicoes/rag",
        "banco": {"container": "rag-extractor-pg", "db": "rag_extractor", "user": "rag"},
        "ajustes": [], "nao_e_ajuste": {}}}))

    def grava_docker(**kw):
        e = json.loads(estado.read_text())
        e.update(kw)
        estado.write_text(json.dumps(e))

    def roda(*args, ato, env_extra=None, stdin=None):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia", "FAKE_DOCKER": str(estado),
               "FAKE_SQL_LOG": str(sql_log), "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        env.pop("PF_CHAPEU", None)
        env.update(env_extra or {})
        return subprocess.run([sys.executable, str(MOTOR), "rag", ato, *args], capture_output=True, text=True,
                              env=env, timeout=90, check=False, input=stdin)

    def sqls():
        return sql_log.read_text().split("\n=====\n") if sql_log.exists() else []

    def salva_medicao(nome, corpo):
        (medicoes / nome).write_text(json.dumps(corpo))

    yield roda, grava_docker, sqls, salva_medicao, instancia, gabarito, _S
    servidor.shutdown()


# --- tarefa 7: consultas ------------------------------------------------------------------------

PERGUNTA_LONGA = ("como o orgao deve tratar o pedido de acesso quando o requerente nao indica o motivo, "
                  "o prazo corre da data do protocolo ou da data do aviso de recebimento, e quem responde "
                  "em caso de recurso na segunda instancia dentro do mesmo ministerio?")


def _evento(**c):
    base = {"id": "e1", "criado_em": "2026-10-14 10:00:00+00", "sessao_id": None, "particao": "biblioteca",
            "origem": "busca", "cadeira": "ia", "chapeu": "recuperacao", "necessidade": "prazo de resposta",
            "pergunta": PERGUNTA_LONGA, "cobertura": "fraca", "tempos_ms": {"embed": 10, "total": 55.5},
            "geracao_id": "g3-id", "parametros": None}
    base.update(c)
    return base


def test_consultas_traz_a_pergunta_inteira_a_cobertura_a_origem_e_o_tempo(motor):
    roda, grava, sqls, *_ = motor
    grava(psql={"consultas:lista": [_evento()], "consultas:contagem": {"populacao": 1, "cadeira": 1, "chapeu": 1,
                                                                        "cobertura": 1, "tempos_ms": 1, "no_filtro": 1}})
    r = roda("biblioteca", "--json", ato="consultas")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    (x,) = d["itens"]
    assert x["pergunta"] == PERGUNTA_LONGA and x["cobertura"] == "fraca" and x["origem"] == "busca"
    assert x["tempos_ms"]["total"] == 55.5
    assert d["lido_em"] and d["fonte"].startswith("acervo.evento_recuperacao")
    texto = roda("biblioteca", ato="consultas").stdout
    assert PERGUNTA_LONGA in texto and "55.5 ms" in texto


def test_linha_anterior_a_migracao_diz_nao_consegui_olhar_e_cobertura_fora_do_contrato_tambem(motor):
    roda, grava, *_ = motor
    grava(psql={"consultas:lista": [_evento(cobertura=None, tempos_ms=None, cadeira=None, chapeu=None),
                                    _evento(id="e2", cobertura="vazia")],
                "consultas:contagem": {"populacao": 2, "no_filtro": 2}})
    d = json.loads(roda("biblioteca", "--json", ato="consultas").stdout)
    antiga, torta = d["itens"]
    assert antiga["cobertura"] is None and antiga["cobertura_leitura"] == "nao consegui olhar"
    assert antiga["tempos_leitura"] == "nao consegui olhar"
    assert torta["cobertura"] is None and "valor fora do contrato" in torta["cobertura_leitura"]


def test_a_previa_fica_fora_da_lista_salvo_quem_a_pede_pela_origem(motor):
    roda, grava, sqls, *_ = motor
    grava(psql={"consultas:lista": [], "consultas:contagem": {"populacao": 0, "no_filtro": 0}})
    roda("biblioteca", "--json", ato="consultas")
    assert "e.origem <> 'previa'" in sqls()[0]
    roda("biblioteca", "--json", "--origem", "previa", ato="consultas")
    assert "e.origem IN ('previa')" in sqls()[2] and "<> 'previa'" not in sqls()[2]


def test_filtro_sobre_campo_raro_diz_quantas_linhas_o_tem(motor):
    roda, grava, sqls, *_ = motor
    grava(psql={"consultas:lista": [_evento()], "consultas:contagem": {"populacao": 300, "cadeira": 280, "chapeu": 12,
                                                                        "cobertura": 250, "tempos_ms": 250, "no_filtro": 12}})
    d = json.loads(roda("biblioteca", "--chapeu", "recuperacao", "--json", ato="consultas").stdout)
    assert d["preenchimento"]["chapeu"] == {"com": 12, "de": 300}
    assert d["no_filtro"] == 12 and d["na_populacao"] == 300
    assert "filtro por chapeu: so 12 de 300 linhas" in d["avisos"][0]
    assert "e.chapeu = 'recuperacao'" in sqls()[0]
    assert "so 12 de 300" in roda("biblioteca", "--chapeu", "recuperacao", ato="consultas").stdout


def test_filtros_de_periodo_cadeira_cobertura_e_texto_entram_no_sql(motor):
    roda, grava, sqls, *_ = motor
    grava(psql={"consultas:lista": [], "consultas:contagem": {}})
    roda("biblioteca", "--desde", "2026-10-08", "--ate", "2026-10-10", "--cadeira", "ia", "--cobertura", "fraca",
         "--texto", "d'agua", "--limite", "7", "--json", ato="consultas")
    s = sqls()[0]
    assert "(e.criado_em AT TIME ZONE 'UTC') >= '2026-10-08'::timestamp" in s
    assert "< ('2026-10-10'::date + 1)" in s
    assert "e.cadeira = 'ia'" in s and "e.cobertura = 'fraca'" in s and "LIMIT 7" in s
    assert "'d''agua'" in s                                  # a aspa do texto nao escapa do literal
    roda("biblioteca", "--cobertura", "sem-leitura", "--json", ato="consultas")
    assert "e.cobertura IS NULL" in sqls()[2]


def test_consultas_com_o_banco_fora_sai_3_e_diz_o_motivo_no_json(motor):
    roda, grava, *_ = motor
    grava(psql_fora=True)
    r = roda("biblioteca", "--json", ato="consultas")
    assert r.returncode == 3
    assert "nao respondeu" in json.loads(r.stdout)["nao_consegui_olhar"] and "nao respondeu" in r.stderr


@pytest.mark.parametrize("args", [("--desde", "ontem"), ("--limite", "0"), ("--limite", "x"), ("--origem", "lua"),
                                  ("--cobertura", "otima"), ("--chapeu", "a b"), ("--sem-isso",), ("--cadeira",)])
def test_consultas_flags_invalidas_saem_2(motor, args):
    roda, *_ = motor
    assert roda("biblioteca", *args, ato="consultas").returncode == 2


def test_por_dia_a_serie_comeca_no_dia_da_migracao_e_conta_o_que_ficou_fora_do_denominador(motor):
    roda, grava, sqls, *_ = motor
    grava(psql={
        "consultas:dia-view": [
            {"dia": "2026-10-07", "particao": "biblioteca", "total": 0, "boa": 0, "fraca": 0, "nenhuma": 0, "ausente": 0,
             "sem_indice": 0},
            {"dia": "2026-10-08", "particao": "biblioteca", "total": 10, "boa": 7, "fraca": 2, "nenhuma": 1, "ausente": 0,
             "sem_indice": 0}],
        "consultas:dia-linhas": [{"dia": "2026-10-07", "linhas": 5, "sem_cobertura": 5},
                                 {"dia": "2026-10-08", "linhas": 12, "sem_cobertura": 2}]})
    d = json.loads(roda("biblioteca", "--por-dia", "--json", ato="consultas").stdout)
    assert d["serie_comeca_em"] == "2026-10-08"
    antes, dia = d["dias"]
    assert antes["taxa_fraca"] is None and "nao consegui olhar" in antes["nao_consegui_olhar"]
    assert antes["linhas_fora_do_denominador"] == 5
    assert dia["taxa_fraca"] == 0.2 and dia["linhas_fora_do_denominador"] == 2
    ind = d["indicador"]
    assert ind["quem_configurou"] == "ia" and "sem limiar configurado" in ind["regra"] and ind["hora"] and ind["fonte"]
    assert "10 busca(s)" in ind["amostra"] and "7 linha(s)" in ind["amostra"]       # 5 de antes + 2 do dia
    # a serie so conta busca e abertura: a previa, a medida, a sombra e o autoteste ficam de fora do SQL
    assert "e.origem IN ('busca', 'abertura')" in sqls()[1]
    texto = roda("biblioteca", "--por-dia", ato="consultas").stdout
    assert "a serie comeca em 2026-10-08" in texto and "taxa fraca 0.200" in texto


# --- tarefa 8: trabalhos ------------------------------------------------------------------------

AGORA = 1_760_000_000.0
SOMBRA_PARADA = "20261005T223538"


def _sombra(sid, **c):
    base = {"id": sid, "fim": None, "fim_mtime": None, "log_mtime": AGORA - 9 * 86400, "dir_mtime": AGORA - 9 * 86400,
            "vivo": False, "ultima_linha": "embeddando 3/20"}
    base.update(c)
    return base


def test_a_sombra_de_05_10_sem_processo_e_sem_fim_aparece_parada_nao_rodando(motor):
    roda, grava, *_ = motor
    grava(conteiner={"agora": AGORA, "sombras": [_sombra(SOMBRA_PARADA)]})
    d = json.loads(roda("--json", ato="trabalhos").stdout)
    (t,) = d["itens"]
    assert t["id"] == SOMBRA_PARADA and t["tipo"] == "sombra-de-bench"
    assert t["estado"] == "parado" and t["desde"] and "nenhum processo" in t["motivo"]
    assert d["resumo"]["parados"] == 1
    texto = roda(ato="trabalhos").stdout
    assert "PARADO desde" in texto and "rodando" not in texto.lower()


def test_sombra_com_processo_vivo_e_log_recente_esta_viva_e_log_calado_alem_do_limiar_esta_parada(motor):
    roda, grava, *_ = motor
    grava(conteiner={"agora": AGORA, "sombras": [_sombra("20261014T100000", vivo=True, log_mtime=AGORA - 60)]})
    assert json.loads(roda("--json", ato="trabalhos").stdout)["itens"][0]["estado"] == "vivo"
    grava(conteiner={"agora": AGORA, "sombras": [_sombra("20261014T100000", vivo=True, log_mtime=AGORA - 5000)]})
    t = json.loads(roda("--json", ato="trabalhos").stdout)["itens"][0]
    assert t["estado"] == "parado" and "limiar" in t["motivo"] and t["limiar_s"] == 1800
    t = json.loads(roda("--json", ato="trabalhos", env_extra={"SOMBRA_LIMIAR_S": "10000"}).stdout)["itens"][0]
    assert t["estado"] == "vivo"


def test_sombra_terminada_nao_e_trabalho_em_curso(motor):
    roda, grava, *_ = motor
    grava(conteiner={"agora": AGORA, "sombras": [_sombra("20261001T100000", fim=0, fim_mtime=AGORA - 100)]})
    d = json.loads(roda("--json", ato="trabalhos").stdout)
    assert d["itens"] == [] and d["resumo"]["sombras_concluidas_fora_da_lista"] == 1


def test_trabalhos_junta_os_lotes_do_rag_e_as_sombras_pelo_mesmo_vocabulario(motor):
    roda, grava, sqls, salva, inst, gab, S = motor
    S.trabalhos = [{"id": "11111111-1111-4111-8111-111111111111", "tipo": "troca", "particao": "biblioteca",
                    "iniciado_em": "2026-10-14T09:00:00+00:00", "progresso": {"total": 40, "feitos": 12},
                    "ultimo_batimento": "2026-10-14T09:30:00+00:00", "limiar_s": 300, "estado": "vivo",
                    "desde": "2026-10-14T09:00:00+00:00", "motivo": None}]
    grava(conteiner={"agora": AGORA, "sombras": [_sombra(SOMBRA_PARADA)]})
    d = json.loads(roda("--json", ato="trabalhos").stdout)
    assert [t["tipo"] for t in d["itens"]] == ["troca", "sombra-de-bench"]          # do mais novo ao mais velho
    assert {t["fonte"] for t in d["itens"]} == {"rag-api GET /motor/trabalhos",
                                                "sombra de bench no conteiner (/tmp/sombra-<id>)"}
    assert d["resumo"]["em_curso"] == 2 and d["nao_consegui_olhar"] == {}
    assert "12/40" in roda(ato="trabalhos").stdout


def test_trabalhos_com_uma_fonte_fora_diz_nao_consegui_olhar_e_sai_0_com_as_duas_fora_sai_5(motor):
    roda, grava, sqls, salva, inst, gab, S = motor
    S.trabalhos_fora = True
    grava(conteiner={"agora": AGORA, "sombras": [_sombra(SOMBRA_PARADA)]})
    r = roda("--json", ato="trabalhos")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert "rag-api" in d["nao_consegui_olhar"] and d["itens"][0]["id"] == SOMBRA_PARADA
    grava(conteiner_fora=True)
    r = roda("--json", ato="trabalhos")
    assert r.returncode == 5
    assert set(json.loads(r.stdout)["nao_consegui_olhar"]) == {"rag-api", "sombras de bench"}


def test_sombra_ver_de_pasta_ausente_nao_diz_rodando(motor):
    """O contrato antigo imprimia «rodando» para toda sombra sem `fim`, existisse ela ou nao (o conteiner recriado
    em 10/10 levou /tmp junto)."""
    roda, grava, *_ = motor
    grava(conteiner={"agora": AGORA, "sombras": []})
    r = roda("biblioteca", "--sombra-ver", SOMBRA_PARADA, ato="medir")
    assert r.returncode == 1 and "nao existe no conteiner" in r.stderr
    assert "rodando" not in r.stdout


def test_sombra_ver_sem_processo_e_sem_fim_diz_parada_desde_quando(motor):
    roda, grava, *_ = motor
    grava(conteiner={"agora": AGORA, "sombras": [_sombra(SOMBRA_PARADA)]})
    r = roda("biblioteca", "--sombra-ver", SOMBRA_PARADA, ato="medir")
    assert r.returncode == 0, r.stderr
    assert "estado: parado desde" in r.stdout and "nenhum processo" in r.stdout and "rodando" not in r.stdout
    grava(conteiner={"agora": AGORA, "sombras": [_sombra(SOMBRA_PARADA, vivo=True, log_mtime=AGORA - 30)]})
    assert "estado: vivo" in roda("biblioteca", "--sombra-ver", SOMBRA_PARADA, ato="medir").stdout


def test_sombra_ver_com_o_conteiner_fora_diz_nao_consegui_olhar(motor):
    roda, grava, *_ = motor
    grava(conteiner_fora=True)
    r = roda("biblioteca", "--sombra-ver", SOMBRA_PARADA, ato="medir")
    assert "nao consegui olhar o estado" in r.stdout and "rodando" not in r.stdout


# --- tarefa 6: histórico de medida --------------------------------------------------------------

def _rodada(em, gnum, hit1, abst_ok, *, rotulo="", sombra=None, gabarito="harness/avaliacao/gabarito.jsonl"):
    return {"em": em, "rotulo": rotulo, "k": 5, "geracao": sombra, "gabarito": gabarito,
            "indice": {"geracao": {"numero": gnum, "parametros": {"embedder": f"E{gnum}"}}},
            "metricas": {"geral": {"n": 50, "hit@1": hit1, "hit@3": 0.8, "hit@5": 0.9, "mrr": 0.7},
                         "abstencao": {"n": 22, "ok": abst_ok, "abstencao": f"{abst_ok}/22", "taxa": round(abst_ok / 22, 3)}},
            "latencia_ms": {"mediana": 420.0, "p90": 900.0}, "perguntas": []}


def test_historico_de_medida_lista_desde_06_10_com_o_marco_da_g3_em_08_10_e_os_ajustes(motor):
    roda, grava, sqls, salva, instancia, *_ = motor
    salva("20261006T100000.json", _rodada("2026-10-06T10:00:00-0300", 2, 0.60, 10))
    salva("20261007T100000.json", _rodada("2026-10-07T10:00:00-0300", 2, 0.62, 11))
    salva("20261009T100000.json", _rodada("2026-10-09T10:00:00-0300", 3, 0.70, 15))
    salva("20261010T100000-nova.json", _rodada("2026-10-10T10:00:00-0300", 4, 0.72, 16, rotulo="nova", sombra="g4"))
    salva("20261011T100000-calibracao.json", {"em": "2026-10-11T10:00:00-0300", "resultado": {}})   # nao e rodada
    (instancia / "var" / "motor").mkdir(parents=True)
    (instancia / "var" / "motor" / "ajustes-historico.jsonl").write_text(json.dumps(
        {"em": "2026-10-12T09:00:00-03:00", "slug": "aviso-de-cobertura-fraca", "antes": 0.342, "depois": 0.35,
         "geracao": 3, "sujeito": "ia", "fundamento": "cala T2 demais", "origem": "cadeira"}) + "\n")
    r = roda("biblioteca", "--historico", "--json", ato="medir")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert [p["em"][:10] for p in d["medicoes"]] == ["2026-10-06", "2026-10-07", "2026-10-09", "2026-10-10"]
    assert d["medicoes"][3]["sombra"] == "g4" and d["medicoes"][2]["geracao"] == 3
    viradas = [m for m in d["marcos"] if m["tipo"] == "virada"]
    g3 = next(m for m in viradas if m["geracao"] == 3)
    assert g3["em"] == "2026-10-08T15:00:00+00:00" and g3["inferido"] is False and g3["autorizada_por"] == "o dono disse sim"
    g2 = next(m for m in viradas if m["geracao"] == 2)
    assert g2["inferido"] is True and g2["em"].startswith("2026-10-06")
    assert not any(m["geracao"] == 4 for m in viradas)                      # sombra nao gera marco
    ajuste = next(m for m in d["marcos"] if m["tipo"] == "ajuste")
    assert ajuste["quem"] == "ia" and ajuste["fundamento"] == "cala T2 demais" and ajuste["antes"] == 0.342
    horas = [historicomod.utc(m["em"]) for m in d["marcos"]]
    assert horas == sorted(horas) and len(d["marcos"]) == 3                       # g2, g3 e o ajuste, em ordem
    texto = roda("biblioteca", "--historico", ato="medir").stdout
    assert "virada para a g3" in texto and "aviso-de-cobertura-fraca: 0.342 -> 0.35" in texto
    filtrado = json.loads(roda("biblioteca", "--historico", "--desde", "2026-10-09", "--json", ato="medir").stdout)
    assert len(filtrado["medicoes"]) == 2


def test_historico_sem_a_virada_da_geracao_infere_o_marco_da_bateria(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    salva("a.json", _rodada("2026-10-06T10:00:00-0300", 2, 0.6, 10))
    salva("b.json", _rodada("2026-10-09T10:00:00-0300", 3, 0.7, 15))
    S.ajustes = {"aviso_de_cobertura_fraca": 0.342}          # a rota responde, mas a geracao nao guarda `virada`
    d = json.loads(roda("biblioteca", "--historico", "--json", ato="medir").stdout)
    viradas = [m for m in d["marcos"] if m["tipo"] == "virada"]
    assert [m["geracao"] for m in viradas] == [2, 3] and all(m["inferido"] for m in viradas)
    assert d["nao_consegui_olhar"] == {}


def test_historico_com_o_rag_fora_diz_por_que_a_virada_e_inferida(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    salva("b.json", _rodada("2026-10-09T10:00:00-0300", 3, 0.7, 15))
    S.ajustes_fora = True
    d = json.loads(roda("biblioteca", "--historico", "--json", ato="medir").stdout)
    assert "geracao servindo" in d["nao_consegui_olhar"] and "inferida" in d["nao_consegui_olhar"]["geracao servindo"]
    assert d["marcos"][0]["inferido"] is True


def test_historico_sem_nenhuma_rodada_diz_isso(motor):
    roda, *_ = motor
    d = json.loads(roda("biblioteca", "--historico", "--json", ato="medir").stdout)
    assert d["medicoes"] == [] and d["marcos"] == []
    assert "0 medicao" in roda("biblioteca", "--historico", ato="medir").stdout


def test_a_hora_da_bateria_e_a_do_rag_se_comparam_em_utc():
    assert historicomod.utc("2026-10-08T12:00:00-0300") == historicomod.utc("2026-10-08T15:00:00+00:00")
    assert historicomod.utc("2026-10-08T12:00:00-0300") > historicomod.utc("2026-10-08T14:00:00+00:00")


# --- tarefa 5: os quatro atos em JSON -----------------------------------------------------------

def test_medir_em_json_traz_o_bloco_de_cada_indicador_o_delta_e_a_hora(motor):
    roda, grava, sqls, salva, instancia, gabarito, S = motor
    primeira = roda("biblioteca", "--gabarito", str(gabarito), "--rotulo", "um", "--json", ato="medir")
    assert primeira.returncode == 0, primeira.stderr
    assert primeira.stdout.lstrip().startswith("{")                        # o progresso foi ao stderr
    segunda = roda("biblioteca", "--gabarito", str(gabarito), "--rotulo", "dois", "--json", ato="medir")
    d = json.loads(segunda.stdout)
    por_nome = {i["nome"]: i for i in d["indicadores"]}
    h1 = por_nome["acerto na primeira posicao (hit@1)"]
    assert h1["valor"] == 0.5                                              # q1 em 1o, q2 em 2o
    for i in d["indicadores"]:
        assert i["hora"] and i["fonte"] and i["mede"] and i["amostra"] and i["regra"] and i["quem_configurou"] == "ia"
        assert "sem limiar configurado" in i["regra"]
    assert por_nome["abstencao nas negativas"]["valor"] == 1.0
    assert por_nome["latencia mediana (ms, total)"]["valor"] == 40.0
    fase = por_nome["latencia por fase: embed (ms)"]
    assert fase["valor"] == {"mediana": 10.0, "p90": 10.0}
    assert d["delta"]["contra"] and d["delta"]["rotulo"] == "um" and d["delta"]["familias"]["geral"]["hit@1"] == 0.0
    assert d["lido_em"] and d["arquivo"].endswith("-dois.json") and d["indice"]["geracao"]["numero"] == 3


def test_medir_json_nao_vale_para_calibrar_nem_sombra(motor):
    roda, *_ = motor
    assert roda("biblioteca", "--sombra", "x", "--json", ato="medir").returncode == 2


def test_indexar_relatorio_em_json_tem_hora_fonte_e_o_motivo_quando_o_rag_esta_fora(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    lote = "33333333-3333-4333-8333-333333333333"
    S.lote = {"lote": lote, "estado": "concluido", "por_estado": {"montada": 3}, "embedados": 100, "ms": 5000}
    d = json.loads(roda("biblioteca", "--relatorio", lote, "--json", ato="indexar").stdout)
    assert d["lote"] == lote and d["lido_em"] and d["fonte"].endswith(lote)
    S.lote = {"fora": True}
    r = roda("biblioteca", "--relatorio", lote, "--json", ato="indexar")
    assert r.returncode == 3 and "HTTP 503" in json.loads(r.stdout)["nao_consegui_olhar"]


# --- tarefa 5: o estado da troca e as pendências (R23) ------------------------------------------

SOMBRA_G4 = {"geracao": 4, "id": "g4-id", "estado": "em_construcao", "embedder": "Outro",
             "cobertura": {"aprovadas": 100, "total": 100, "percentual": 100.0, "trechos_embedados": 37000,
                           "trechos_total": 37000}}


def test_trocar_estado_json_com_sombra_medida_traz_a_pendencia_com_os_sete_campos(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    S.troca_estado = {**S.troca_estado, "sombra": SOMBRA_G4}
    salva("a.json", _rodada("2026-10-09T10:00:00-0300", 3, 0.70, 15, rotulo="g3"))
    salva("b.json", _rodada("2026-10-10T10:00:00-0300", 4, 0.74, 16, rotulo="g4", sombra="g4"))
    d = json.loads(roda("biblioteca", "--estado", "--json", ato="trocar").stdout)
    assert d["lido_em"] and d["fonte"].startswith("rag-api GET") and d["servindo"]["geracao"] == 3
    (p,) = d["pendencias"]
    assert set(p) >= {"pergunta", "opcoes", "recomendada", "efeito_se_ninguem_decidir", "aberta_por", "cadeira_dona"}
    assert [o["opcao"] for o in p["opcoes"]] == ["virar", "descartar"]
    assert all(o["ato"].startswith("motor rag trocar biblioteca --") and o["custo"] for o in p["opcoes"])
    assert "--virar g4" in p["opcoes"][0]["ato"] and "--descartar g4" in p["opcoes"][1]["ato"]
    assert p["recomendada"] == "virar" and "0.74 contra 0.7" in p["motivo_da_recomendacao"]
    assert p["cadeira_dona"] == "ia" and "g4" in p["aberta_por"]
    assert p["efeito_se_ninguem_decidir"] != "fica pendente"


def test_depois_de_virar_ou_descartar_a_lista_volta_vazia(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    salva("b.json", _rodada("2026-10-10T10:00:00-0300", 4, 0.74, 16, rotulo="g4", sombra="g4"))
    S.troca_estado = {**S.troca_estado, "sombra": None}                      # a sombra deixou de existir
    assert json.loads(roda("biblioteca", "--estado", "--json", ato="trocar").stdout)["pendencias"] == []


def test_sombra_ainda_nao_medida_nao_abre_pendencia(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    S.troca_estado = {**S.troca_estado, "sombra": SOMBRA_G4}
    assert json.loads(roda("biblioteca", "--estado", "--json", ato="trocar").stdout)["pendencias"] == []


def test_sombra_pior_que_o_servido_recomenda_descartar_e_sem_servido_comparavel_nao_recomenda(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    S.troca_estado = {**S.troca_estado, "sombra": SOMBRA_G4}
    salva("b.json", _rodada("2026-10-10T10:00:00-0300", 4, 0.50, 12, sombra="g4"))
    sem = json.loads(roda("biblioteca", "--estado", "--json", ato="trocar").stdout)["pendencias"][0]
    assert sem["recomendada"] is None and "sem medida da g3" in sem["motivo_da_recomendacao"]
    salva("a.json", _rodada("2026-10-09T10:00:00-0300", 3, 0.70, 15))
    pior = json.loads(roda("biblioteca", "--estado", "--json", ato="trocar").stdout)["pendencias"][0]
    assert pior["recomendada"] == "descartar" and "0.5 contra 0.7" in pior["motivo_da_recomendacao"]


def test_trocar_estado_json_com_o_rag_fora_diz_nao_consegui_olhar_e_pendencias_nula(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    S.troca_fora = True
    r = roda("biblioteca", "--estado", "--json", ato="trocar")
    assert r.returncode == 3
    d = json.loads(r.stdout)
    assert d["pendencias"] is None and "HTTP 503" in d["nao_consegui_olhar"] and d["lido_em"] and d["fonte"]


# --- tarefa 9: a prévia -------------------------------------------------------------------------

BUSCA = ("biblioteca", "--sem-lint", "--necessidade", "prazo de resposta do pedido de acesso", "--texto", "nenhum")


def test_previa_manda_a_origem_previa_e_os_valores_por_chamada(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    r = roda(*BUSCA, "--previa", "--piso", "0.61", "--piso-revisor", "0.7", "--instrucao", "Ache o trecho", "--rastro",
             ato="buscar")
    assert r.returncode == 0, r.stderr
    corpo = S.corpos[-1]
    assert corpo["origem"] == "previa" and corpo["aviso_de_cobertura_fraca"] == 0.61
    assert corpo["aviso_com_revisor"] == 0.7 and corpo["instrucao_da_pergunta"] == "Ache o trecho"
    assert corpo["rastro"] is True


@pytest.mark.parametrize("piso", ["0,61", "1.5", "0", "-0.2", "alto"])
def test_previa_recusa_piso_torto_antes_de_a_busca_rodar(motor, piso):
    roda, grava, sqls, salva, instancia, gab, S = motor
    r = roda(*BUSCA, "--previa", "--piso", piso, ato="buscar")
    assert r.returncode == 2
    assert S.corpos == []


def test_piso_e_instrucao_so_valem_na_previa(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    for extra in (("--piso", "0.6"), ("--piso-revisor", "0.6"), ("--instrucao", "x")):
        r = roda(*BUSCA, *extra, ato="buscar")
        assert r.returncode == 2 and "so valem na --previa" in r.stderr
    assert S.corpos == []


def test_previa_nao_combina_com_outra_origem_e_a_busca_comum_segue_igual(motor):
    roda, grava, sqls, salva, instancia, gab, S = motor
    assert roda(*BUSCA, "--previa", "--origem", "bench", ato="buscar").returncode == 2
    assert roda(*BUSCA, "--origem", "previa", ato="buscar").returncode == 0      # a mesma origem, por extenso
    assert S.corpos[-1]["origem"] == "previa"
    assert roda(*BUSCA, ato="buscar").returncode == 0
    comum = S.corpos[-1]
    assert comum["origem"] == "busca" and "rastro" not in comum and "aviso_de_cobertura_fraca" not in comum


# --- as formas puras ----------------------------------------------------------------------------

def test_serie_por_dia_sem_nenhum_dia_com_cobertura_nao_tem_comeco():
    s = consultasmod.serie_por_dia([], [{"dia": "2026-10-01", "linhas": 3, "sem_cobertura": 3}])
    assert s["serie_comeca_em"] is None and s["dias"][0]["nao_consegui_olhar"]


def test_estado_da_sombra_sem_hora_legivel_e_indeterminavel():
    t = trabalhosmod.estado_da_sombra({"id": "20261005T223538", "vivo": True, "agora": 1.0, "log_mtime": None,
                                       "dir_mtime": None}, 1800)
    assert t["estado"] == "indeterminavel" and "nao consegui olhar" in t["motivo"]


def test_recomendacao_sem_acerto_na_medida_nao_recomenda():
    r, motivo = pendenciasmod.recomenda({"metricas": {}}, {"metricas": {"geral": {"hit@1": 0.7}}}, 3)
    assert r is None and "acerto" in motivo
