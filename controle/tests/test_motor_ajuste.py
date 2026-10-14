"""`motor rag ajuste`: o valor da geração servindo, o fundamento, o histórico e as recusas (card #3513, U1).

O rag-api é um servidor de brinquedo (as rotas da #3510), o docker é um script de brinquedo que devolve o env
do contêiner, e a instância é um diretório temporário com o arquivo do `sinal`. O verbo roda de verdade, em
subprocesso.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"

SLUG_PISO = "aviso-de-cobertura-fraca"

DOCKER_FALSO = """#!{python}
import os, sys
a = sys.argv[1:]
if a and a[0] == "inspect":
    if os.environ.get("FAKE_DOCKER_FORA"):
        sys.exit(1)
    print(open(os.environ["FAKE_ENV"]).read(), end="")
else:
    sys.exit(0)
"""


def _ajuste(slug, var, fase, onde, codigo, geracao=None):
    b = {"slug": slug, "var": var, "fase": fase, "onde": onde, "faixa": "0 a 1", "codigo": codigo,
         "sobe": f"sobe {slug}", "custa": f"custa {slug}", "medir": f"mede {slug}"}
    if geracao:
        b["geracao"] = geracao
    return b


class _Estado:
    ajustes: dict
    trabalhos: list
    puts: list
    ger_fora: bool


class _API(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _responde(self, codigo, corpo, tipo="application/json"):
        dado = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/motor/geracoes/servindo/ajustes":
            if _Estado.ger_fora:
                return self._responde(503, {"title": "Aquecendo", "detail": "o motor esta subindo"},
                                      "application/problem+json")
            particao = (parse_qs(p.query).get("particao") or ["biblioteca"])[0]
            return self._responde(200, {"particao": particao, "geracao": 3, "geracao_id": "g-id",
                                        "ajustes": dict(_Estado.ajustes), "lido_em": "2026-10-14T12:00:00+00:00"})
        if p.path == "/motor/trabalhos":
            return self._responde(200, {"itens": _Estado.trabalhos, "proximo": None,
                                        "lido_em": "2026-10-14T12:00:00+00:00"})
        self._responde(404, {})

    def do_PUT(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        _Estado.puts.append(corpo)
        if any(t.get("estado") == "vivo" for t in _Estado.trabalhos):
            return self._responde(409, {"title": "LoteEmAndamento", "detail": "ha lote aberto"},
                                  "application/problem+json")
        anterior = _Estado.ajustes.get(corpo["chave"])
        _Estado.ajustes[corpo["chave"]] = corpo["valor"]
        self._responde(200, {"particao": "biblioteca", "geracao": 3, "chave": corpo["chave"],
                             "anterior": anterior, "novo": corpo["valor"], "aplicado_em": "2026-10-14T12:01:00+00:00"})


@pytest.fixture
def motor(tmp_path):
    _Estado.ajustes = {"aviso_de_cobertura_fraca": 0.342, "aviso_com_revisor": 0.79, "veredito_por_conceito": False}
    _Estado.trabalhos = []
    _Estado.puts = []
    _Estado.ger_fora = False
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"

    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    (instancia / "segredos" / "ingestao").mkdir()
    (instancia / "segredos" / "ingestao" / "CHUNK_TOKEN_CEILING").write_text("512\n")
    sinal = instancia / "var" / "sinal"
    sinal.mkdir(parents=True)
    (sinal / "servicos.json").write_text(json.dumps(
        {"servicos": {"rag-extractor-api": {"estado": "no-ar"}, "gpu-host": {"estado": "no-ar"}}}))

    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)
    env_do_conteiner = tmp_path / "env-conteiner.txt"
    env_do_conteiner.write_text("MIN_SIM=0.5\nRRF_K=60\nPATH=/bin\n")

    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": "rag-extractor-api", "stack": "rag", "servico": "rag-api",
        "compose": "/opt/platafirma/current/conhecimento/rag/docker-compose.yml",
        "endpoint": f"{base}/search", "token_em": "rag/RAG_API_TOKEN",
        "ajustes_da_geracao": f"{base}/motor/geracoes/servindo/ajustes",
        "trabalhos": f"{base}/motor/trabalhos",
        "env_da_ingestao": "ingestao",
        "ajustes": [
            _ajuste(SLUG_PISO, "MIN_SIM", "9 montagem", "compose", "0.55", "aviso_de_cobertura_fraca"),
            _ajuste("aviso-com-revisor", "MIN_CE", "9 montagem", "compose", "0.79", "aviso_com_revisor"),
            _ajuste("veredito-por-conceito", "VEREDITO_POR_CONCEITO", "9 montagem", "compose", "false",
                    "veredito_por_conceito"),
            _ajuste("constante-da-fusao", "RRF_K", "7 fusao", "compose", "60"),
            _ajuste("teto-do-trecho", "CHUNK_TOKEN_CEILING", "3 corte", "env", "512"),
        ],
        "nao_e_ajuste": {"EMBED_MODEL": "instalacao"},
    }}))

    def roda(*args, env_extra=None):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia", "FAKE_ENV": str(env_do_conteiner),
               "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}
        env.pop("PF_FUNDAMENTO", None)
        env.pop("PF_SUJEITO", None)
        env.update(env_extra or {})
        return subprocess.run([sys.executable, str(MOTOR), "rag", "ajuste", *args],
                              capture_output=True, text=True, env=env, timeout=60, check=False)

    def historico():
        arq = instancia / "var" / "motor" / "ajustes-historico.jsonl"
        return [json.loads(x) for x in arq.read_text().splitlines()] if arq.exists() else []

    def sinal_diz(estado, servico="rag-extractor-api"):
        servicos = {"rag-extractor-api": {"estado": "no-ar"}, "gpu-host": {"estado": "no-ar"}}
        servicos[servico] = {"estado": estado, "motivo": "healthcheck falhou"}
        (sinal / "servicos.json").write_text(json.dumps({"servicos": servicos}))

    yield roda, historico, sinal_diz
    servidor.shutdown()


# --- tarefa 1: ler o valor da geração, a configuração só como divergente ------------------------

def test_lista_mostra_o_valor_da_geracao_e_o_compose_como_divergente(motor):
    roda, _, _ = motor
    r = roda()
    assert r.returncode == 0, r.stderr
    linha = next(x for x in r.stdout.splitlines() if x.strip().startswith(SLUG_PISO))
    assert "0,342" in linha and "geracao g3" in linha
    assert "o compose diz 0,5, divergente" in linha
    # o que a geracao nao carrega segue pelo compose e pelo env, no formato de sempre
    fusao = next(x for x in r.stdout.splitlines() if x.strip().startswith("constante-da-fusao"))
    assert "(compose)" in fusao
    teto = next(x for x in r.stdout.splitlines() if x.strip().startswith("teto-do-trecho"))
    assert "(env da ingestao)" in teto and "512" in teto


def test_detalhe_em_json_traz_valor_inteiro_origem_e_divergente(motor):
    roda, _, _ = motor
    r = roda(SLUG_PISO, "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["valor"] == 0.342
    assert d["origem"] == "geracao g3"
    assert d["divergente"] == {"compose": "0.5"}
    assert d["fonte"].startswith("rag-api GET /motor/geracoes/servindo/ajustes")
    assert d["lido_em"] and d["geracao"] == 3
    assert d["direcao"] == {"sobe": f"sobe {SLUG_PISO}", "custa": f"custa {SLUG_PISO}"}


def test_lista_em_json_tem_hora_fonte_e_valor_tipado_em_cada_campo(motor):
    roda, _, _ = motor
    d = json.loads(roda("--json").stdout)
    assert d["lido_em"] and d["geracao"]["numero"] == 3
    por_slug = {a["slug"]: a for a in d["ajustes"]}
    assert por_slug["veredito-por-conceito"]["valor"] is False
    assert por_slug["constante-da-fusao"]["valor"] == 60 and por_slug["constante-da-fusao"]["origem"] == "compose"
    assert all(a["fonte"] and a["lido_em"] for a in d["ajustes"])
    assert d["nao_consegui_olhar"] == {}


def test_geracao_fora_diz_nao_consegui_olhar_e_cai_no_compose(motor):
    roda, _, _ = motor
    _Estado.ger_fora = True
    r = roda(SLUG_PISO, "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["origem"] == "compose" and d["valor"] == 0.5
    assert "nao consegui olhar a geracao" in d["nao_consegui_olhar"]
    texto = roda()
    assert "nao consegui olhar a geracao servindo" in texto.stdout


# --- tarefas 2 e 3: escrever pela rota, com fundamento, e o histórico ---------------------------

def test_escrita_sem_fundamento_sai_2_e_nao_toca_a_geracao(motor):
    roda, historico, _ = motor
    r = roda(SLUG_PISO, "0,35")
    assert r.returncode == 2
    assert "sem fundamento" in r.stderr
    assert _Estado.puts == [] and historico() == []


def test_escrita_com_fundamento_muda_o_servido_grava_o_historico_e_volta_pelo_anterior(motor):
    roda, historico, _ = motor
    r = roda(SLUG_PISO, "0,35", "--fundamento", "o piso de 0,342 cala T2 demais")
    assert r.returncode == 0, r.stderr
    assert "0,342 -> 0,35" in r.stdout and "CONFERIDO no servido" in r.stdout
    assert f"volta: motor rag ajuste {SLUG_PISO} 0,342" in r.stdout
    put = _Estado.puts[0]
    assert put["chave"] == "aviso_de_cobertura_fraca" and put["valor"] == 0.35
    assert put["fundamento"] == "o piso de 0,342 cala T2 demais" and put["sujeito"] == "ia"
    assert _Estado.ajustes["aviso_de_cobertura_fraca"] == 0.35

    h = historico()
    assert len(h) == 1
    assert h[0]["slug"] == SLUG_PISO and h[0]["antes"] == 0.342 and h[0]["depois"] == 0.35
    assert h[0]["geracao"] == 3 and h[0]["origem"] == "cadeira" and h[0]["sujeito"] == "ia"
    assert h[0]["fundamento"] == "o piso de 0,342 cala T2 demais"

    mostra = roda("--historico")
    assert mostra.returncode == 0 and "0,342 -> 0,35" in mostra.stdout and "o piso de 0,342 cala" in mostra.stdout

    volta = roda(SLUG_PISO, "0,342", "--fundamento", "volta ao piso da g3")
    assert volta.returncode == 0, volta.stderr
    assert _Estado.ajustes["aviso_de_cobertura_fraca"] == 0.342
    h = historico()
    assert [(x["antes"], x["depois"]) for x in h] == [(0.342, 0.35), (0.35, 0.342)]
    filtrado = json.loads(roda("--historico", SLUG_PISO, "--json").stdout)
    assert len(filtrado["itens"]) == 2


def test_escrita_em_json_confere_e_diz_a_volta(motor):
    roda, _, _ = motor
    r = roda("veredito-por-conceito", "true", "--fundamento", "ligar o predicado", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert d["antes"] is False and d["depois"] is True and d["conferido"] is True
    assert d["origem_do_valor"] == "geracao" and d["origem_do_ato"] == "cadeira" and d["geracao"] == 3
    assert d["volta"].startswith("motor rag ajuste veredito-por-conceito false")


def test_valor_igual_ao_da_geracao_nao_escreve_nem_registra(motor):
    roda, historico, _ = motor
    r = roda(SLUG_PISO, "0,342", "--fundamento", "nada muda")
    assert r.returncode == 0 and "Nada a fazer" in r.stdout
    assert _Estado.puts == [] and historico() == []


def test_valor_fora_da_faixa_volta_400_da_api_como_exit_2(motor, monkeypatch):
    roda, historico, _ = motor
    original = _API.do_PUT

    def recusa(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self._responde(400, {"title": "TrocaInvalida", "detail": "piso fora de (0, 1]"}, "application/problem+json")

    monkeypatch.setattr(_API, "do_PUT", recusa)
    r = roda(SLUG_PISO, "7", "--fundamento", "teste")
    monkeypatch.setattr(_API, "do_PUT", original)
    assert r.returncode == 2 and "TrocaInvalida: piso fora de (0, 1]" in r.stderr
    assert historico() == []


# --- da face ------------------------------------------------------------------------------------

def test_da_face_o_fundamento_vem_da_porta_e_a_flag_e_recusada(motor):
    roda, historico, _ = motor
    r = roda(SLUG_PISO, "0,35", "--fundamento", "outro texto", env_extra={"PF_FUNDAMENTO": "texto do dono"})
    assert r.returncode == 2 and "nao vale vindo da face" in r.stderr
    assert _Estado.puts == []

    ok = roda(SLUG_PISO, "0,35", env_extra={"PF_FUNDAMENTO": "texto do dono"})
    assert ok.returncode == 0, ok.stderr
    assert _Estado.puts[0]["fundamento"] == "texto do dono"
    assert historico()[0]["origem"] == "face" and historico()[0]["fundamento"] == "texto do dono"


def test_da_face_o_ajuste_de_corte_segue_so_leitura(motor):
    roda, _, _ = motor
    r = roda("teto-do-trecho", "1024", env_extra={"PF_FUNDAMENTO": "texto do dono"})
    assert r.returncode == 4 and "#3506" in r.stderr


# --- tarefa 4: as recusas -----------------------------------------------------------------------

def test_trabalho_aberto_recusa_com_exit_4_e_a_causa(motor):
    roda, historico, _ = motor
    _Estado.trabalhos = [{"id": "11111111-1111-4111-8111-111111111111", "tipo": "troca", "estado": "vivo",
                          "progresso": {"total": 40, "feitos": 12}}]
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    assert r.returncode == 4
    assert "trabalho aberto" in r.stderr and "troca" in r.stderr and "12/40" in r.stderr
    assert _Estado.puts == [] and historico() == []


def test_trabalho_parado_nao_segura_e_a_api_e_a_rede_de_baixo(motor):
    roda, _, _ = motor
    _Estado.trabalhos = [{"id": "22222222-2222-4222-8222-222222222222", "tipo": "indexacao", "estado": "parado",
                          "progresso": {"total": 3, "feitos": 1}}]
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    assert r.returncode == 0, r.stderr


def test_409_da_api_tambem_sai_4(motor, monkeypatch):
    roda, historico, _ = motor
    # a lista de trabalhos esta vazia (o verbo nao viu lote), mas o PUT acha lote: a API tem a ultima palavra
    original = _API.do_PUT

    def ocupado(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self._responde(409, {"title": "LoteEmAndamento", "detail": "ha lote aberto"}, "application/problem+json")

    monkeypatch.setattr(_API, "do_PUT", ocupado)
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    monkeypatch.setattr(_API, "do_PUT", original)
    assert r.returncode == 4 and "LoteEmAndamento" in r.stderr
    assert historico() == []


def test_servico_fora_no_sinal_recusa_com_exit_3(motor):
    roda, historico, sinal_diz = motor
    sinal_diz("fora")
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    assert r.returncode == 3 and "fora" in r.stderr and "healthcheck falhou" in r.stderr
    assert _Estado.puts == [] and historico() == []


def test_placa_fora_no_sinal_tambem_recusa_com_exit_3(motor):
    roda, historico, sinal_diz = motor
    sinal_diz("fora", servico="gpu-host")
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    assert r.returncode == 3 and "gpu-host esta fora" in r.stderr
    assert _Estado.puts == [] and historico() == []


def test_sinal_sem_leitura_nao_equivale_a_no_ar_mas_nao_trava(motor):
    roda, _, sinal_diz = motor
    sinal_diz("sem-sinal")
    r = roda(SLUG_PISO, "0,35", "--fundamento", "x")
    assert r.returncode == 0, r.stderr
    assert "sinal de rag-extractor-api: nao consegui olhar" in r.stdout


def test_ajuste_que_reinicia_a_busca_nao_segue_sem_ler_o_sinal(motor):
    roda, historico, sinal_diz = motor
    sinal_diz("sem-sinal")
    r = roda("constante-da-fusao", "80", "--fundamento", "x")
    assert r.returncode == 3 and "nao autoriza reiniciar" in r.stderr
    assert historico() == []


def test_flags_invalidas_saem_2(motor):
    roda, _, _ = motor
    for args in (("--desconhecido",), (SLUG_PISO, "--fundamento"), (SLUG_PISO, "--fundamento", "x"),
                 ("--historico", SLUG_PISO, "0,3")):
        assert roda(*args).returncode == 2, args
    assert roda("nao-existe").returncode == 1
