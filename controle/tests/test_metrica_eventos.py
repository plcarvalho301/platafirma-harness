"""O cliente da rota de escrita do banco de eventos de plataforma (bin/_metrica/eventos.py; spec
banco-de-eventos-de-plataforma R6, R7 e R8; card #3922).

Uma rota de mentira em loopback, no lugar do `eventos-api`: ela guarda o que recebe, devolve `inseridos` e `existentes`
como a de verdade, e o teste manda ela recusar, cair ou pedir lote menor. O que se prova: a identidade (o uuid do
exemplo da ficha sai igual), o evento só com campo da ficha, a fila local que não perde amostra com a rota fora, a
recusa que tira só os índices nomeados, e o token que nunca sai em saída nenhuma. Nada toca o host.
"""
import json
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "bin" / "_metrica"))
sys.path.insert(0, str(RAIZ / "bin" / "_infra"))
import eixos  # noqa: E402
import eventos  # noqa: E402

TOKEN = "TOKEN-DA-SONDA-0123456789abcdef"
MINUTO = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)
# A ficha eixo_host e a rota, em platafirma-core@7c062b6 (registros/familias/eixo_host.yaml:contrato_de_escrita).
FICHA_TOPO = {"evento_id", "ts", "instancia", "instrumento", "schema_v", "estado_leitura", "eixo", "janela", "causa",
              "fonte", "valor", "unidade", "teto", "teto_fonte", "limiar", "limiar_por", "pressao_avg10",
              "pressao_avg60", "pressao_avg300", "cache_bytes", "consumidores_omitidos", "valor_omitido",
              "consumidores", "tuneis"}
FICHA_CONSUMIDOR = {"posicao", "valor", "servico", "desvio", "conteiner", "pid", "executavel", "sm_ocupacao", "threads"}
FICHA_TUNEL = {"tunel", "estado_leitura", "causa", "conexoes_borda", "reconexoes", "erros_transporte",
               "latencia_externa_ms"}


# --- a rota de mentira ---------------------------------------------------------------------------------

class Rota:
    """O que a rota viu, e o que o teste manda ela fazer."""

    def __init__(self):
        self.pedidos = []          # (familia, [evento_id]) de cada POST
        self.autorizacoes = []
        self.banco = {}            # (familia, evento_id) -> evento
        self.resposta = None       # (status, corpo) fixo; None = comportamento normal
        self.respostas = []        # uma por POST, na ordem; esgotada, volta ao normal
        self.lote_maximo = None    # acima disso, 413
        self.recusar = set()       # evento_id que a rota recusa com 422
        self.leituras = []

    def tratar(self, familia, eventos_do_lote):
        if self.respostas:
            return self.respostas.pop(0)
        if self.resposta:
            return self.resposta
        if self.lote_maximo and len(eventos_do_lote) > self.lote_maximo:
            return 413, {"tipo": "LoteGrande", "status": 413, "detalhe": "lote grande"}
        recusados = [{"indice": i, "evento_id": e["evento_id"], "motivo": "EventoInvalido", "campo": "valor",
                      "detalhe": "x"} for i, e in enumerate(eventos_do_lote) if e["evento_id"] in self.recusar]
        if recusados:
            return 422, {"tipo": "EventoInvalido", "status": 422, "detalhe": "recusado", "recusados": recusados}
        novos, existentes = [], []
        for e in eventos_do_lote:
            chave = (familia, e["evento_id"])
            (existentes if chave in self.banco else novos).append(e["evento_id"])
            self.banco.setdefault(chave, e)
        return 200, {"familia": familia, "inseridos": novos, "existentes": existentes}


def _servidor(rota):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _responde(self, status, corpo):
            dados = json.dumps(corpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_POST(self):
            rota.autorizacoes.append(self.headers.get("Authorization"))
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            familia = self.path.rsplit("/", 1)[-1]
            rota.pedidos.append((familia, [e["evento_id"] for e in corpo["eventos"]]))
            self._responde(*rota.tratar(familia, corpo["eventos"]))

        def do_GET(self):
            rota.leituras.append((urlparse(self.path).path, parse_qs(urlparse(self.path).query)))
            self._responde(200, {"familia": "eixo_host", "amostras": [], "cobertura": {"estado": "completa"}})

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


@pytest.fixture
def rota():
    r = Rota()
    servidor = _servidor(r)
    r.url = f"http://127.0.0.1:{servidor.server_port}"
    yield r
    servidor.shutdown()


@pytest.fixture
def pasta(tmp_path):
    return tmp_path / "var" / "eventos"


def _evento(n, familia="eixo_host", eixo="ram"):
    return {"evento_id": str(uuid.uuid5(eventos.NAMESPACE, f"{familia}|{eixo}|{n}")), "ts": f"2026-10-21T15:{n % 60:02d}:00Z",
            "eixo": eixo, "janela": 60}


def _fila(pasta, familia="eixo_host"):
    return eventos.Fila(pasta, familia)


def _enviar(rota, fila, familia="eixo_host", **kw):
    return eventos.enviar_fila(familia, fila, url=rota.url, token=TOKEN, timeout=3, **kw)


# --- a identidade --------------------------------------------------------------------------------------

def test_o_namespace_e_o_uuid_do_exemplo_saem_como_a_ficha_declara():
    assert str(eventos.NAMESPACE) == "22db7bee-aaff-5128-a8d1-8d5589868f81"
    assert eventos.id_da_amostra("ram", MINUTO) == "ddefb3cc-723f-5f9b-b56a-924dbcf542b8"


def test_o_id_da_amostra_so_depende_do_eixo_e_do_minuto():
    segundos = MINUTO + timedelta(seconds=37)
    assert eventos.id_da_amostra("ram", segundos) == eventos.id_da_amostra("ram", MINUTO)
    assert eventos.id_da_amostra("cpu", MINUTO) != eventos.id_da_amostra("ram", MINUTO)
    assert eventos.id_da_amostra("ram", MINUTO + timedelta(minutes=1)) != eventos.id_da_amostra("ram", MINUTO)


def test_o_id_da_morte_e_o_uuid_de_boot_pid_e_instante_do_kernel():
    boot = "11111111-2222-3333-4444-555555555555"
    instante = datetime(2026, 10, 14, 17, 46, 40, 123000, tzinfo=timezone.utc)
    esperado = uuid.uuid5(eventos.NAMESPACE, f"morte_limite|{boot}|4242|2026-10-14T17:46:40.123Z")
    assert eventos.id_da_morte(boot, 4242, instante) == str(esperado)
    assert eventos.id_da_morte(boot, 4243, instante) != str(esperado)


def test_o_ts_e_o_minuto_cheio_em_utc():
    assert eventos.minuto_iso(MINUTO.astimezone(timezone(timedelta(hours=-3)))) == "2026-10-21T15:00:00Z"


# --- o evento: só campo da ficha ------------------------------------------------------------------------

def _ram(**extras):
    base = dict(valor=10 << 30, unidade="bytes", teto=30 << 30, teto_fonte="/proc/meminfo:MemTotal", janela=3600,
                cache_bytes=5 << 30, total_bytes=30 << 30, pressao_avg10=0.5, pressao_avg60=0.3, pressao_avg300=0.1,
                mortes=[{"servico": "core/ops-tunnel", "ts": "2026-10-21T14:30:00.000Z", "fonte": "journal",
                         "escopo": "cgroup"}],
                oom_kill_slice=3, consumidores_omitidos=0, valor_omitido=0,
                consumidores=[
                    {"servico": "core/keycloak", "conteiner": "platafirma-core-keycloak-1", "pid": 100,
                     "executavel": "java", "valor": 3 << 30, "unidade": "bytes", "processos": 2},
                    {"desvio": "fora_de_compose_e_unit", "pid": 300, "executavel": "Isolated Web Co",
                     "linha_de_comando": "firefox -contentproc --secret=x", "valor": 4 << 30, "unidade": "bytes",
                     "processos": 3}])
    base.update(extras)
    return eixos.montar("ram", "infra-medir-ram", **base)


def _evento_ram(**kw):
    return eventos.evento_do_eixo(_ram(), minuto=MINUTO, janela_s=60, instancia="host-1", **kw)


def test_o_evento_do_eixo_so_leva_campo_que_a_ficha_nomeia():
    e = _evento_ram()
    assert set(e) <= FICHA_TOPO
    for c in e["consumidores"]:
        assert set(c) <= FICHA_CONSUMIDOR


def test_o_que_o_evento_nao_guarda_fica_no_json_e_na_frase():
    e = _evento_ram()
    for campo in ("total_bytes", "mortes", "oom_kill_slice", "linha_de_comando", "carimbo", "limiar_por"):
        assert campo not in e
    assert all("linha_de_comando" not in c and "processos" not in c and "unit" not in c for c in e["consumidores"])


def test_o_evento_leva_o_envelope_da_amostra_e_a_janela_da_passada():
    e = _evento_ram()
    assert e["evento_id"] == eventos.id_da_amostra("ram", MINUTO) and e["ts"] == "2026-10-21T15:00:00Z"
    assert (e["instancia"], e["instrumento"], e["schema_v"]) == ("host-1", "infra-medir-ram", 1)
    assert e["janela"] == 60, "a janela da amostra é a da passada, não a janela de mortes que o ato leu"
    assert (e["valor"], e["unidade"], e["cache_bytes"]) == (10 << 30, "bytes", 5 << 30)
    assert (e["pressao_avg10"], e["pressao_avg60"], e["pressao_avg300"]) == (0.5, 0.3, 0.1)


def test_o_evento_vai_e_volta_em_json_sem_perder_nada():
    e = _evento_ram()
    assert json.loads(json.dumps(e)) == e


def test_consumidores_saem_do_maior_para_o_menor_com_a_posicao_e_o_executavel_sem_espaco():
    consumidores = _evento_ram()["consumidores"]
    assert [c["posicao"] for c in consumidores] == [1, 2]
    assert consumidores[0]["desvio"] == "fora_de_compose_e_unit" and consumidores[0]["executavel"] == "Isolated_Web_Co"
    assert consumidores[1]["servico"] == "core/keycloak" and consumidores[1]["conteiner"] == "platafirma-core-keycloak-1"
    assert "servico" not in consumidores[0] and "desvio" not in consumidores[1], "um dos dois, nunca os dois"


@pytest.mark.parametrize("texto, esperado", [
    ("java", "java"), ("Isolated Web Co", "Isolated_Web_Co"), ("web content/x", "web_content_x"),
    ("  claude  ", "claude"), ("a" * 300, "a" * 128), ("", None), (None, None), (42, None)])
def test_executavel_sai_na_forma_que_a_rota_aceita(texto, esperado):
    assert eventos.executavel_da_rota(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("platafirma-core-keycloak-1", "platafirma-core-keycloak-1"), ("kind gould", "kind_gould"),
    ("/x", "x"), ("__x", "x"), ("", None), ("///", None), (None, None)])
def test_conteiner_sai_na_forma_que_a_rota_aceita(texto, esperado):
    assert eventos.conteiner_da_rota(texto) == esperado


def test_chave_fora_da_forma_da_rota_vira_desvio_e_nunca_lote_recusado():
    j = _ram(consumidores=[{"servico": "Core/Keycloak", "valor": 1, "unidade": "bytes"},
                           {"servico": "core/landing", "valor": 2, "unidade": "bytes"}])
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h")
    assert [c.get("desvio") for c in e["consumidores"]] == [None, "fora_de_compose_e_unit"]
    assert [c.get("servico") for c in e["consumidores"]] == ["core/landing", None]


def test_so_os_dez_maiores_entram_e_o_resto_vira_omitido_com_o_valor():
    consumidores = [{"desvio": "unit_sem_stack", "pid": 100 + i, "valor": (i + 1) * 100, "unidade": "bytes"}
                    for i in range(13)]
    e = eventos.evento_do_eixo(_ram(consumidores=consumidores, consumidores_omitidos=2, valor_omitido=50),
                               minuto=MINUTO, janela_s=60, instancia="h")
    assert [c["valor"] for c in e["consumidores"]] == [1300 - 100 * i for i in range(10)]
    assert e["consumidores_omitidos"] == 2 + 3 and e["valor_omitido"] == 50 + 100 + 200 + 300


def test_o_que_a_cadencia_deixou_fora_entra_na_conta_dos_omitidos():
    j = _ram()
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h", escolhidos=j["consumidores"][:1],
                               fora=j["consumidores"][1:])
    assert len(e["consumidores"]) == 1
    assert e["consumidores_omitidos"] == 1 and e["valor_omitido"] == 4 << 30, "o que ficou fora era o de 4 GiB"


def test_eixo_sem_corte_nem_omissao_nao_inventa_zero_de_omitidos(tmp_path):
    j = eixos.montar("cpu", "infra-medir-cpu", valor=2.5, unidade="threads", teto=12, teto_fonte="/proc/cpuinfo",
                     pressao_avg10=1.0, pressao_avg60=1.0, pressao_avg300=1.0,
                     consumidores=[{"servico": "core/keycloak", "valor": 1.5, "unidade": "threads"}])
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h")
    assert "consumidores_omitidos" not in e and "valor_omitido" not in e
    assert e["unidade"] == "threads" and e["consumidores"][0]["valor"] == 1.5 and set(e) <= FICHA_TOPO


def test_vram_leva_o_reservado_em_valor_e_o_sm_em_sm_ocupacao_cada_um_no_seu_campo():
    j = eixos.montar("vram", "infra-medir-vram", valor=10 << 30, unidade="bytes", teto=16 << 30,
                     teto_fonte="nvidia-smi", sm_placa_fracao=0.4,
                     consumidores=[{"servico": "motor/busca", "pid": 7, "reservado_bytes": 4 << 30, "sm_fracao": 0.25},
                                   {"servico": "rag/embedder", "pid": 8, "reservado_bytes": 2 << 30, "sm_fracao": None}])
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h")
    primeiro, segundo = e["consumidores"]
    assert (primeiro["valor"], primeiro["sm_ocupacao"]) == (4 << 30, 0.25)
    assert segundo["valor"] == 2 << 30 and "sm_ocupacao" not in segundo, "SM sem amostra é nulo, nunca zero"
    assert "sm_placa_fracao" not in e and "soma" not in "".join(e)


# --- a rede: túneis e a reconexão entre passadas ---------------------------------------------------------

def _rede(reconexoes=(24, 30, 7), conexoes=4, porta=True):
    tuneis = [{"tunel": nome, "estado_leitura": "lida", "causa": None, "conexoes_borda": conexoes,
               "reconexoes_acumuladas": acumulada, "metrica": "127.0.0.1:20241", "pid": 1,
               "latencia_externa_ms": 55.5 if porta and nome == "ops" else None,
               "dur_ms_porta": 41 if porta and nome == "ops" else None,
               "erros_transporte": 0 if porta and nome == "ops" else None, "erro_verbo": None}
              for nome, acumulada in zip(("ops", "recuperacao", "wiki"), reconexoes)]
    return eixos.montar("rede", "infra-medir-rede", tuneis=tuneis, consumidores=[
        {"servico": "core/ops-tunnel", "unit": "ops-tunnel.service", "pid": 1, "tunel": "ops", "valor": conexoes,
         "unidade": "contagem"}])


def test_a_reconexao_do_tunel_e_a_diferenca_entre_duas_leituras():
    estado = {}
    primeira = eventos.diferenciar_reconexoes(_rede((24, 30, 7)), estado)
    assert primeira == {"ops": None, "recuperacao": None, "wiki": None}, "sem leitura anterior, nulo e nunca zero"
    segunda = eventos.diferenciar_reconexoes(_rede((26, 30, 10)), estado)
    assert segunda == {"ops": 2, "recuperacao": 0, "wiki": 3}
    assert estado["reconexoes"] == {"ops": 26, "recuperacao": 30, "wiki": 10}


def test_contagem_menor_que_a_anterior_e_reinicio_e_vale_a_atual():
    estado = {"reconexoes": {"ops": 100, "recuperacao": 5, "wiki": 5}}
    assert eventos.diferenciar_reconexoes(_rede((3, 5, 6)), estado) == {"ops": 3, "recuperacao": 0, "wiki": 1}


def test_tunel_sem_leitura_nao_tem_reconexao_nem_atualiza_a_contagem():
    j = _rede()
    j["tuneis"][1] = {"tunel": "recuperacao", "estado_leitura": "nao_consegui_olhar", "causa": "unit_parada",
                      "fonte": "systemctl --user show recuperacao-tunnel.service"}
    estado = {"reconexoes": {"recuperacao": 9}}
    assert eventos.diferenciar_reconexoes(j, estado)["recuperacao"] is None
    assert estado["reconexoes"]["recuperacao"] == 9


def test_o_evento_de_rede_leva_os_tuneis_pelos_nomes_da_ficha_e_a_latencia_so_no_ops():
    estado = {"reconexoes": {"ops": 20, "recuperacao": 30, "wiki": 7}}
    j = _rede((24, 30, 7))
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h",
                               reconexoes=eventos.diferenciar_reconexoes(j, estado))
    ops, recuperacao, wiki = e["tuneis"]
    assert ops == {"tunel": "ops", "estado_leitura": "lida", "conexoes_borda": 4, "erros_transporte": 0,
                   "reconexoes": 4, "latencia_externa_ms": 55.5}
    assert "latencia_externa_ms" not in recuperacao and "erros_transporte" not in recuperacao
    assert recuperacao["reconexoes"] == 0 and wiki["reconexoes"] == 0
    assert all(set(t) <= FICHA_TUNEL for t in e["tuneis"])
    assert "valor" not in e, "a rede guarda o número nos túneis, não no topo"
    for campo in ("dur_ms_porta", "erro_verbo", "reconexoes_acumuladas", "metrica", "pid"):
        assert all(campo not in t for t in e["tuneis"])


def test_porta_nao_medida_deixa_a_latencia_ausente_e_nunca_zero():
    j = _rede(porta=False)
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h", reconexoes={})
    assert all("latencia_externa_ms" not in t and "erros_transporte" not in t for t in e["tuneis"])
    assert all("reconexoes" not in t for t in e["tuneis"])


def test_tunel_que_nao_leu_sai_com_a_causa_e_sem_numero():
    j = eixos.montar("rede", "infra-medir-rede", estado="nao_consegui_olhar", causa="tunel_sem_leitura",
                     fonte="cloudflared: wiki",
                     tuneis=[{"tunel": "wiki", "estado_leitura": "nao_consegui_olhar", "causa": "metrica_fora",
                              "fonte": "cloudflared 127.0.0.1:20243"},
                             {"tunel": "ops", "estado_leitura": "lida", "causa": None, "conexoes_borda": 4,
                              "reconexoes_acumuladas": 3}])
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h", reconexoes={})
    assert e["estado_leitura"] == "nao_consegui_olhar" and e["causa"] == "tunel_sem_leitura"
    assert e["fonte"] == "cloudflared: wiki" and "valor" not in e
    assert e["tuneis"][0] == {"tunel": "wiki", "estado_leitura": "nao_consegui_olhar", "causa": "metrica_fora"}


# --- a leitura que falhou nunca vira zero ---------------------------------------------------------------

def test_eixo_que_nao_leu_sai_com_causa_e_fonte_e_sem_valor():
    j = eixos.montar("vram", "infra-medir-vram", estado="nao_consegui_olhar", causa="driver_fora",
                     fonte="nvidia-smi --query-gpu")
    e = eventos.evento_do_eixo(j, minuto=MINUTO, janela_s=60, instancia="h")
    assert (e["estado_leitura"], e["causa"], e["fonte"]) == ("nao_consegui_olhar", "driver_fora", "nvidia-smi --query-gpu")
    assert "valor" not in e and "unidade" not in e and e["consumidores"] == []


def test_ato_que_nao_respondeu_vira_nao_consegui_olhar_e_nunca_minuto_calado():
    e = eventos.evento_do_eixo(eventos.leitura_sem_resposta("cpu"), minuto=MINUTO, janela_s=60, instancia="h")
    assert (e["estado_leitura"], e["causa"], e["fonte"]) == ("nao_consegui_olhar", "ato_nao_respondeu", "infra medir cpu")
    assert e["eixo"] == "cpu" and e["instrumento"] == "infra-medir-cpu" and "valor" not in e
    assert e["evento_id"] == eventos.id_da_amostra("cpu", MINUTO)


# --- a fila ---------------------------------------------------------------------------------------------

def test_o_evento_entra_na_fila_antes_do_envio_e_em_ordem(pasta):
    fila = _fila(pasta)
    assert fila.ler() == []
    fila.anexar([_evento(1), _evento(2)])
    fila.anexar([_evento(3)])
    assert [e["ts"] for e in fila.ler()] == ["2026-10-21T15:01:00Z", "2026-10-21T15:02:00Z", "2026-10-21T15:03:00Z"]


def test_o_mesmo_evento_nao_entra_duas_vezes_na_fila(pasta):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    fila.anexar([_evento(1), _evento(2)])
    assert len(fila.ler()) == 2


def test_a_fila_acima_do_teto_perde_o_mais_antigo_e_diz_quantos(pasta, monkeypatch):
    monkeypatch.setattr(eventos, "FILA_TETO", 5)
    fila = _fila(pasta)
    fila.anexar([_evento(n) for n in range(4)])
    descartados = fila.anexar([_evento(n) for n in range(4, 8)])
    assert descartados == 3
    assert [e["evento_id"] for e in fila.ler()] == [_evento(n)["evento_id"] for n in range(3, 8)]


def test_linha_ilegivel_na_fila_nao_derruba_as_outras(pasta):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    with open(fila.caminho, "a", encoding="utf-8") as f:
        f.write("{isto nao e json\n[1,2]\n")
    fila.anexar([_evento(2)])
    assert len(fila.ler()) == 2


def test_a_fila_se_reescreve_sem_deixar_arquivo_provisorio(pasta):
    fila = _fila(pasta)
    fila.anexar([_evento(1), _evento(2)])
    fila.gravar([_evento(2)])
    assert sorted(p.name for p in pasta.iterdir()) == ["fila-eixo_host.jsonl"]


def test_so_uma_passada_toma_a_trava_por_vez(pasta):
    with eventos.trava(pasta) as primeira:
        with eventos.trava(pasta) as segunda:
            assert primeira is True and segunda is False
    with eventos.trava(pasta) as de_novo:
        assert de_novo is True


# --- o envio --------------------------------------------------------------------------------------------

def test_lote_aceito_sai_da_fila_e_vai_com_o_token_da_sonda(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(n) for n in range(4)])
    r = _enviar(rota, fila)
    assert (r["inseridos"], r["existentes"], r["pendentes"], r["erro"]) == (4, 0, 0, None)
    assert fila.ler() == [] and len(rota.pedidos) == 1 and rota.autorizacoes == [f"Bearer {TOKEN}"]


def test_fila_vazia_nao_chama_a_rota(pasta, rota):
    assert _enviar(rota, _fila(pasta))["pendentes"] == 0
    assert rota.pedidos == []


def test_com_a_rota_fora_o_lote_fica_na_fila_e_a_passada_seguinte_o_repoe_sem_perder_amostra(pasta, rota):
    """O banco parado dez minutos: dez passadas com 503, e a que volta fecha as 60 sem buraco."""
    fila = _fila(pasta)
    rota.resposta = (503, {"tipo": "BancoIndisponivel", "status": 503, "detalhe": "banco fora"})
    gerados = []
    for minuto in range(10):
        novos = [{**_evento(minuto * 10 + i), "ts": f"2026-10-21T15:{minuto:02d}:00Z", "eixo": e}
                 for i, e in enumerate(("rede", "ram", "vram", "cpu"))]
        novos = [{**n, "evento_id": eventos.id_da_amostra(n["eixo"], MINUTO + timedelta(minutes=minuto))} for n in novos]
        gerados += novos
        fila.anexar(novos)
        r = _enviar(rota, fila)
        assert r["erro"].startswith("503 BancoIndisponivel") and r["pendentes"] == 4 * (minuto + 1)
    rota.resposta = None
    r = _enviar(rota, fila)
    assert (r["inseridos"], r["pendentes"], r["erro"]) == (40, 0, None)
    assert [e for e in rota.banco.values()] == gerados, "os mesmos eventos, na ordem em que nasceram, nenhum perdido"
    assert rota.pedidos[-1][1] == [g["evento_id"] for g in gerados]


def test_rota_que_caiu_a_meio_da_resposta_e_regravacao_idempotente(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1), _evento(2)])
    rota.banco[("eixo_host", _evento(1)["evento_id"])] = _evento(1)
    r = _enviar(rota, fila)
    assert (r["inseridos"], r["existentes"], r["pendentes"]) == (1, 1, 0)


def test_rede_caida_mantem_a_fila_e_diz_a_causa(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    r = eventos.enviar_fila("eixo_host", fila, url="http://127.0.0.1:9", token=TOKEN, timeout=1)
    assert r["erro"] == "a rota não respondeu" and r["pendentes"] == 1


@pytest.mark.parametrize("status, tipo", [(401, "NaoAutorizado"), (404, "FamiliaDesconhecida"), (503, "ParticaoAusente"),
                                           (500, "ErroInterno")])
def test_401_404_503_e_5xx_mantem_a_fila(pasta, rota, status, tipo):
    fila = _fila(pasta)
    fila.anexar([_evento(1), _evento(2)])
    rota.resposta = (status, {"tipo": tipo, "status": status, "detalhe": "x"})
    r = _enviar(rota, fila)
    assert r["erro"].startswith(f"{status} {tipo}") and r["pendentes"] == 2 and len(rota.pedidos) == 1


def test_lote_recusado_perde_so_os_indices_nomeados_e_o_resto_volta_na_mesma_passada(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(n) for n in range(5)])
    rota.recusar = {_evento(1)["evento_id"], _evento(3)["evento_id"]}
    r = _enviar(rota, fila)
    assert [x["evento_id"] for x in r["recusados"]] == [_evento(1)["evento_id"], _evento(3)["evento_id"]]
    assert (r["inseridos"], r["pendentes"], r["erro"]) == (3, 0, None)
    assert len(rota.pedidos) == 2 and rota.pedidos[1][1] == [_evento(n)["evento_id"] for n in (0, 2, 4)]
    assert fila.ler() == []


def test_o_recusado_nao_se_reenvia_na_passada_seguinte(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1), _evento(2)])
    rota.recusar = {_evento(1)["evento_id"]}
    _enviar(rota, fila)
    pedidos = len(rota.pedidos)
    assert _enviar(rota, fila)["pendentes"] == 0 and len(rota.pedidos) == pedidos


def test_409_de_forma_divergente_tira_os_nomeados_como_o_422(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1), _evento(2)])
    rota.respostas = [(409, {"tipo": "EventoDivergente", "status": 409, "detalhe": "x",
                             "recusados": [{"indice": 0, "evento_id": _evento(1)["evento_id"],
                                            "motivo": "EventoDivergente", "campo": "evento_id", "detalhe": "x"}],
                             "ids": [_evento(1)["evento_id"]]})]
    r = _enviar(rota, fila)
    assert r["recusados"][0]["motivo"] == "EventoDivergente" and (r["inseridos"], r["pendentes"]) == (1, 0)


def test_422_sem_indice_nao_apaga_nada_e_para(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    rota.resposta = (422, {"tipo": "LoteInvalido", "status": 422, "detalhe": "o corpo é um objeto"})
    r = _enviar(rota, fila)
    assert r["erro"].startswith("422 LoteInvalido") and r["pendentes"] == 1 and len(rota.pedidos) == 1


def test_indice_fora_do_lote_nao_apaga_nada_e_nao_gira_sem_fim(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    rota.resposta = (422, {"tipo": "X", "status": 422, "detalhe": "x",
                           "recusados": [{"indice": 7, "evento_id": None, "motivo": "X", "campo": None, "detalhe": "x"}]})
    r = _enviar(rota, fila)
    assert r["pendentes"] == 1 and len(rota.pedidos) == 1 and r["erro"]


def test_lote_grande_demais_e_partido_ao_meio(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(n) for n in range(8)])
    rota.lote_maximo = 3
    r = _enviar(rota, fila)
    assert r["inseridos"] == 8 and r["pendentes"] == 0
    assert [len(p[1]) for p in rota.pedidos] == [8, 4, 2, 2, 2, 2], "o lote que a rota manda partir não gasta o orçamento de cinco"


def test_a_fila_grande_sai_em_lotes_de_mil_e_ate_cinco_por_passada(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([{**_evento(n), "evento_id": str(uuid.uuid4())} for n in range(5600)])
    r = _enviar(rota, fila)
    assert [len(p[1]) for p in rota.pedidos] == [1000] * 5
    assert (r["inseridos"], r["pendentes"]) == (5000, 600)
    assert _enviar(rota, fila)["pendentes"] == 0


def test_prazo_esgotado_para_o_envio_e_mantem_a_fila(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    r = _enviar(rota, fila, prazo=0.0)
    assert r["erro"] == "prazo da passada esgotado" and r["pendentes"] == 1 and rota.pedidos == []


def test_o_token_nunca_sai_no_resumo_nem_na_excecao(pasta, rota):
    fila = _fila(pasta)
    fila.anexar([_evento(1)])
    rota.resposta = (401, {"tipo": "NaoAutorizado", "status": 401, "detalhe": "token inválido"})
    resumos = [_enviar(rota, fila),
               eventos.enviar_fila("eixo_host", fila, url="http://127.0.0.1:9", token=TOKEN, timeout=1)]
    assert TOKEN not in json.dumps(resumos)
    with pytest.raises(eventos.RedeFora) as erro:
        eventos.gravar_lote("http://127.0.0.1:9", "eixo_host", [_evento(1)], TOKEN, 1)
    assert TOKEN not in str(erro.value) and TOKEN not in repr(erro.value)


def test_o_token_vem_do_segredo_da_instancia_e_sem_ele_nao_ha_token(tmp_path, monkeypatch):
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(tmp_path))
    assert eventos.ler_token() is None
    segredo = tmp_path / "segredos" / "eventos"
    segredo.mkdir(parents=True)
    (segredo / "EVENTOS_SONDA_TOKEN").write_text(TOKEN + "\n", encoding="utf-8")
    assert eventos.ler_token() == TOKEN
    (segredo / "EVENTOS_SONDA_TOKEN").write_text("duas\nlinhas\n", encoding="utf-8")
    assert eventos.ler_token() is None


def test_a_leitura_da_serie_vai_pela_api_sem_token(rota):
    status, corpo = eventos.ler_serie("ram", de=MINUTO - timedelta(hours=1), ate=MINUTO, granularidade="amostra",
                                      url=rota.url, timeout=3)
    assert status == 200 and corpo["cobertura"]["estado"] == "completa"
    caminho, consulta = rota.leituras[0]
    assert caminho == "/eventos/eixo_host" and consulta["eixo"] == ["ram"] and consulta["granularidade"] == ["amostra"]
    assert consulta["de"] == ["2026-10-21T14:00:00Z"] and consulta["ate"] == ["2026-10-21T15:00:00Z"]
    assert rota.autorizacoes == []
