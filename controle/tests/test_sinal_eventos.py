"""A passada da série dos eixos dentro do `sinal` (bin/sinal; spec eixos-do-host R15; spec banco-de-eventos-de-plataforma R8
e R13; card #3922).

Três mundos de mentira: um `infra` que conta quantas vezes cada ato roda e devolve o JSON que o teste pôs; um detector de
morte que devolve o que o teste mandou; e uma rota de escrita em loopback que guarda o que recebe. Cada teste anda a passada
minuto a minuto com o relógio na mão. O que se prova: o padrão grava quatro amostras por minuto; eixo em cinco minutos grava de
cinco em cinco, e com um serviço dele em um minuto grava todo minuto; cada ato roda uma vez só por passada; o banco parado dez
minutos não perde amostra; e erro da passada de eventos nunca muda o exit do `sinal`.
"""
import importlib.machinery
import importlib.util
import json
import os
import stat
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SINAL_PATH = RAIZ / "bin" / "sinal"
sys.path.insert(0, str(RAIZ / "bin" / "_metrica"))
sys.path.insert(0, str(RAIZ / "bin" / "_infra"))
import cadencia  # noqa: E402
import eixos  # noqa: E402
import eventos  # noqa: E402

TOKEN = "TOKEN-DA-SONDA-0123456789abcdef"
INICIO = datetime(2026, 10, 21, 15, 0, 7, tzinfo=timezone.utc)   # a passada cai segundos depois do minuto cheio
CADEIA_ATOS = ("rede", "ram", "vram", "cpu")


def _carregar_sinal():
    loader = importlib.machinery.SourceFileLoader("sinal_bin_eventos", str(SINAL_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


sinal = _carregar_sinal()


# --- a rota de mentira ---------------------------------------------------------------------------------

class Rota:
    def __init__(self):
        self.pedidos = []        # (familia, [evento])
        self.autorizacoes = []
        self.banco = {}          # (familia, evento_id) -> evento, na ordem de chegada
        self.resposta = None     # (status, corpo) fixo
        self.leitura = None      # (status, corpo) do GET

    def tratar(self, familia, lote):
        if self.resposta:
            return self.resposta
        novos, existentes = [], []
        for e in lote:
            (existentes if (familia, e["evento_id"]) in self.banco else novos).append(e["evento_id"])
            self.banco.setdefault((familia, e["evento_id"]), e)
        return 200, {"familia": familia, "inseridos": novos, "existentes": existentes}

    def eventos(self, familia="eixo_host"):
        return [e for (f, _), e in self.banco.items() if f == familia]


@pytest.fixture
def rota():
    r = Rota()

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
            r.autorizacoes.append(self.headers.get("Authorization"))
            lote = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["eventos"]
            familia = self.path.rsplit("/", 1)[-1]
            r.pedidos.append((familia, lote))
            self._responde(*r.tratar(familia, lote))

        def do_GET(self):
            self._responde(*(r.leitura or (404, {"tipo": "Nada", "detalhe": "sem leitura"})))

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    r.url = f"http://127.0.0.1:{servidor.server_port}"
    yield r
    servidor.shutdown()


# --- o `infra` e o detector de mentira -------------------------------------------------------------------

def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


def _json_do_eixo(eixo, valor=1 << 30, **extras):
    if eixo == "rede":
        tuneis = [{"tunel": n, "estado_leitura": "lida", "causa": None, "conexoes_borda": 4, "reconexoes_acumuladas": 24,
                   "latencia_externa_ms": 50.0 if n == "ops" else None, "dur_ms_porta": 41 if n == "ops" else None,
                   "erros_transporte": 0 if n == "ops" else None, "erro_verbo": None} for n in ("ops", "recuperacao", "wiki")]
        return eixos.montar("rede", "infra-medir-rede", tuneis=tuneis, consumidores=[
            {"servico": "core/ops-tunnel", "pid": 1, "valor": 4, "unidade": "contagem"}], **extras)
    if eixo == "ram":
        base = dict(valor=valor, unidade="bytes", teto=30 << 30, teto_fonte="/proc/meminfo:MemTotal", janela=60,
                    cache_bytes=1 << 30, total_bytes=30 << 30, pressao_avg10=0.5, pressao_avg60=0.3, pressao_avg300=0.1,
                    mortes=[], oom_kill_slice=0, consumidores_omitidos=0, valor_omitido=0,
                    consumidores=[{"servico": "core/keycloak", "pid": 100, "executavel": "java", "valor": 3 << 30,
                                   "unidade": "bytes"}, {"servico": "core/landing", "pid": 101, "executavel": "nginx",
                                                        "valor": 1 << 30, "unidade": "bytes"}])
        return eixos.montar("ram", "infra-medir-ram", **{**base, **extras})
    if eixo == "vram":
        return eixos.montar("vram", "infra-medir-vram", valor=valor, unidade="bytes", teto=16 << 30,
                            teto_fonte="nvidia-smi", sm_placa_fracao=0.1, consumidores=[
                                {"servico": "motor/busca", "pid": 7, "reservado_bytes": 2 << 30, "sm_fracao": 0.2}], **extras)
    return eixos.montar("cpu", "infra-medir-cpu", valor=2.0, unidade="threads", teto=12, teto_fonte="/proc/cpuinfo:processor",
                        pressao_avg10=1.0, pressao_avg60=1.0, pressao_avg300=1.0, carga_media_1=2.0, carga_media_5=2.0,
                        carga_media_15=2.0, consumidores=[{"servico": "core/keycloak", "valor": 1.5, "unidade": "threads"}],
                        **extras)


class Mundo:
    pass


@pytest.fixture
def mundo(tmp_path, monkeypatch, rota):
    m = Mundo()
    m.rota, m.tmp = rota, tmp_path
    m.instancia = tmp_path / "instancia"
    (m.instancia / "segredos" / "eventos").mkdir(parents=True)
    (m.instancia / "segredos" / "eventos" / "EVENTOS_SONDA_TOKEN").write_text(TOKEN + "\n", encoding="utf-8")
    m.respostas, m.modos, m.chamadas = tmp_path / "respostas", tmp_path / "modos", tmp_path / "chamadas.log"
    m.respostas.mkdir()
    m.modos.mkdir()
    m.chamadas.write_text("", encoding="utf-8")
    m.detector_json, m.detector_saida, m.detector_args = (tmp_path / "detector.json", tmp_path / "detector.exit",
                                                         tmp_path / "detector-args.log")
    m.detector_saida.write_text("0", encoding="utf-8")
    m.detector_args.write_text("", encoding="utf-8")
    m.escrever_detector({"estado_leitura": "lida", "causa": None, "fonte": None, "mortes": [], "vistas_sem_pid": [],
                         "avisos": []})
    for eixo in CADEIA_ATOS:
        m.escrever_eixo(eixo)
    infra = _script(tmp_path / "infra", f'''
eixo="$2"
echo "$eixo $*" >> "{m.chamadas}"
modo=$(cat "{m.modos}/$eixo" 2>/dev/null || echo ok)
case "$modo" in
  ok) cat "{m.respostas}/$eixo.json"; exit 0 ;;
  cinco) cat "{m.respostas}/$eixo.json"; exit 5 ;;
  lixo) echo "isto nao e json"; exit 0 ;;
  falha) echo "uso errado" >&2; exit 2 ;;
  dorme) sleep 5; cat "{m.respostas}/$eixo.json"; exit 0 ;;
esac
''')
    detector = _script(tmp_path / "detector-morte", f'''
echo "$*" >> "{m.detector_args}"
cat "{m.detector_json}"
exit $(cat "{m.detector_saida}")
''')
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(m.instancia))
    monkeypatch.setenv("SINAL_INFRA", str(infra))
    monkeypatch.setenv("SINAL_DETECTOR", str(detector))
    monkeypatch.setenv("SINAL_EVENTOS_URL", rota.url)
    monkeypatch.setenv("SINAL_EVENTOS_TIMEOUT", "3")
    monkeypatch.setenv("SINAL_INSTANCIA", "host-1")
    monkeypatch.delenv("SINAL_CADENCIA", raising=False)
    m.pasta = m.instancia / "var" / "eventos"
    return m


def _escrever_eixo(self, eixo, **extras):
    (self.respostas / f"{eixo}.json").write_text(json.dumps(_json_do_eixo(eixo, **extras)), encoding="utf-8")


def _escrever_detector(self, corpo, saida=0):
    self.detector_json.write_text(json.dumps(corpo), encoding="utf-8")
    self.detector_saida.write_text(str(saida), encoding="utf-8")


def _registro(self, monkeypatch, **campos):
    arquivo = self.tmp / "cadencia.json"
    arquivo.write_text(json.dumps({"padrao_s": 60, **campos}), encoding="utf-8")
    monkeypatch.setenv("SINAL_CADENCIA", str(arquivo))


Mundo.escrever_eixo, Mundo.escrever_detector, Mundo.registro = _escrever_eixo, _escrever_detector, _registro
Mundo.chamou = lambda self: [linha.split()[0] for linha in self.chamadas.read_text(encoding="utf-8").splitlines()]


def passar(minutos):
    """O relógio da passada `minutos` depois do início."""
    return INICIO + timedelta(minutes=minutos)


# --- o padrão: quatro amostras por minuto ---------------------------------------------------------------

def test_com_o_padrao_a_passada_grava_as_quatro_amostras_do_minuto_na_rota(mundo):
    r = sinal.passada_de_eventos(passar(0))
    amostras = mundo.rota.eventos()
    assert sorted(e["eixo"] for e in amostras) == sorted(CADEIA_ATOS) and len(mundo.rota.pedidos) == 1
    for e in amostras:
        assert e["evento_id"] == eventos.id_da_amostra(e["eixo"], datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc))
        assert e["ts"] == "2026-10-21T15:00:00Z", "o minuto da passada, não a hora em que o ato respondeu"
        assert e["janela"] == 60 and e["instancia"] == "host-1" and e["estado_leitura"] == "lida"
    assert r["envio"]["eixo_host"]["inseridos"] == 4 and r["envio"]["eixo_host"]["pendentes"] == 0
    assert mundo.rota.autorizacoes == [f"Bearer {TOKEN}"]


def test_cada_ato_roda_uma_vez_so_por_passada(mundo):
    sinal.passada_de_eventos(passar(0))
    assert sorted(mundo.chamou()) == sorted(CADEIA_ATOS)
    sinal.passada_de_eventos(passar(1))
    assert sorted(mundo.chamou()) == sorted(CADEIA_ATOS * 2)


def test_o_ato_de_ram_recebe_a_janela_da_passada_para_nao_reler_uma_hora_de_mortes(mundo):
    sinal.passada_de_eventos(passar(0))
    linha_do_ram = next(c for c in mundo.chamadas.read_text(encoding="utf-8").splitlines() if c.startswith("ram "))
    assert linha_do_ram == "ram medir ram --json --janela 60"


def test_uma_hora_no_ar_com_o_registro_no_padrao_da_sessenta_amostras_por_eixo(mundo):
    for minuto in range(60):
        sinal.passada_de_eventos(passar(minuto))
    for eixo in CADEIA_ATOS:
        da_serie = [e for e in mundo.rota.eventos() if e["eixo"] == eixo]
        assert len(da_serie) == 60 and len({e["ts"] for e in da_serie}) == 60
    assert not (mundo.pasta / "fila-eixo_host.jsonl").read_text(encoding="utf-8").strip()


def test_o_estado_e_a_fila_ficam_so_na_pasta_da_instancia_e_nada_provisorio_sobra(mundo):
    sinal.passada_de_eventos(passar(0))
    assert sorted(p.name for p in mundo.pasta.iterdir()) == ["cadencia.json", "fila-eixo_host.jsonl", "passada.lock"]
    assert sorted(p.name for p in mundo.instancia.rglob("*") if p.is_file() and "segredos" not in p.parts) == sorted(
        ["cadencia.json", "fila-eixo_host.jsonl", "passada.lock"])


# --- a cadência do registro ------------------------------------------------------------------------------

def test_eixo_em_cinco_minutos_grava_de_cinco_em_cinco_com_janela_de_cinco(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={"ram": 300})
    for minuto in range(12):
        sinal.passada_de_eventos(passar(minuto))
    ram = [e for e in mundo.rota.eventos() if e["eixo"] == "ram"]
    assert [e["ts"][11:16] for e in ram] == ["15:00", "15:05", "15:10"] and {e["janela"] for e in ram} == {300}
    assert mundo.chamou().count("ram") == 3 and mundo.chamou().count("cpu") == 12, "o resto segue no padrão"
    assert len([e for e in mundo.rota.eventos() if e["eixo"] == "cpu"]) == 12


def test_com_um_servico_dele_em_um_minuto_o_eixo_grava_todo_minuto_e_cada_ato_roda_uma_vez(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={"ram": 300}, servicos={"core/keycloak": {"ram": 60}})
    for minuto in range(12):
        sinal.passada_de_eventos(passar(minuto))
    ram = [e for e in mundo.rota.eventos() if e["eixo"] == "ram"]
    assert len(ram) == 12 and {e["janela"] for e in ram} == {60}
    assert mundo.chamou().count("ram") == 12, "uma coleta por passada, e o total vem junto de graça"


def test_o_consumidor_entra_na_amostra_quando_o_intervalo_dele_vence(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={"ram": 300}, servicos={"core/keycloak": {"ram": 60}})
    for minuto in range(6):
        sinal.passada_de_eventos(passar(minuto))
    ram = {e["ts"][11:16]: e for e in mundo.rota.eventos() if e["eixo"] == "ram"}
    assert {c["servico"] for c in ram["15:00"]["consumidores"]} == {"core/keycloak", "core/landing"}, "a lista cheia"
    assert [c["servico"] for c in ram["15:01"]["consumidores"]] == ["core/keycloak"], "só o serviço de um minuto"
    assert ram["15:01"]["consumidores_omitidos"] == 1 and ram["15:01"]["valor_omitido"] == 1 << 30
    assert {c["servico"] for c in ram["15:05"]["consumidores"]} == {"core/keycloak", "core/landing"}


def test_o_registro_muda_a_cadencia_sem_mexer_em_codigo(mundo, monkeypatch):
    for minuto in range(10):
        sinal.passada_de_eventos(passar(minuto))
    com_padrao = len([e for e in mundo.rota.eventos() if e["eixo"] == "vram"])
    mundo.registro(monkeypatch, eixos={"vram": 600})
    for minuto in range(10, 30):
        sinal.passada_de_eventos(passar(minuto))
    depois = len([e for e in mundo.rota.eventos() if e["eixo"] == "vram"]) - com_padrao
    assert com_padrao == 10 and depois == 2, "de um minuto para dez minutos, só com o JSON trocado"


def test_registro_recusado_nao_le_nada_e_diz_a_causa(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={"ram": 90})
    with pytest.raises(cadencia.RegistroInvalido, match="múltiplo de um minuto"):
        sinal.passada_de_eventos(passar(0))
    assert mundo.chamou() == [] and mundo.rota.pedidos == []


# --- o banco mudo não perde amostra ------------------------------------------------------------------------

def test_com_o_banco_parado_dez_minutos_a_reposicao_fecha_as_sessenta_sem_buraco(mundo):
    for minuto in range(25):
        sinal.passada_de_eventos(passar(minuto))
    mundo.rota.resposta = (503, {"tipo": "BancoIndisponivel", "status": 503, "detalhe": "banco fora"})
    for minuto in range(25, 35):
        r = sinal.passada_de_eventos(passar(minuto))
        assert r["envio"]["eixo_host"]["erro"].startswith("503 BancoIndisponivel")
        assert r["envio"]["eixo_host"]["pendentes"] == 4 * (minuto - 24)
    mundo.rota.resposta = None
    for minuto in range(35, 60):
        sinal.passada_de_eventos(passar(minuto))
    for eixo in CADEIA_ATOS:
        da_serie = [e for e in mundo.rota.eventos() if e["eixo"] == eixo]
        assert sorted(e["ts"] for e in da_serie) == [f"2026-10-21T15:{m:02d}:00Z" for m in range(60)], eixo
    assert eventos.Fila(mundo.pasta, "eixo_host").ler() == []


def test_a_fila_vai_ao_disco_antes_do_envio(mundo):
    mundo.rota.resposta = (503, {"tipo": "BancoIndisponivel", "status": 503, "detalhe": "x"})
    sinal.passada_de_eventos(passar(0))
    assert len(eventos.Fila(mundo.pasta, "eixo_host").ler()) == 4 and mundo.rota.eventos() == []


def test_sem_o_token_da_sonda_nada_e_enviado_e_a_fila_guarda(mundo):
    (mundo.instancia / "segredos" / "eventos" / "EVENTOS_SONDA_TOKEN").unlink()
    r = sinal.passada_de_eventos(passar(0))
    assert mundo.rota.pedidos == [] and r["envio"]["eixo_host"]["erro"].startswith("sem token da sonda")
    assert len(eventos.Fila(mundo.pasta, "eixo_host").ler()) == 4


def test_o_token_nunca_sai_na_linha_do_journal(mundo, capsys):
    mundo.rota.resposta = (401, {"tipo": "NaoAutorizado", "status": 401, "detalhe": "x"})
    r = sinal.passada_de_eventos(passar(0))
    linha = sinal._linha_dos_eventos(r)
    assert TOKEN not in linha and "401 NaoAutorizado" in linha
    assert TOKEN not in json.dumps(r, default=str)


def test_outra_passada_em_curso_deixa_esta_de_lado(mundo):
    with eventos.trava(mundo.pasta):
        r = sinal.passada_de_eventos(passar(0))
    assert r == {"pulada": "outra passada de eventos em curso"} and mundo.chamou() == []
    assert "pulada" in sinal._linha_dos_eventos(r)


# --- o ato que não responde -----------------------------------------------------------------------------

@pytest.mark.parametrize("modo", ["lixo", "falha"])
def test_ato_sem_json_ou_com_uso_errado_grava_nao_consegui_olhar_e_nunca_calar_o_minuto(mundo, modo):
    (mundo.modos / "vram").write_text(modo, encoding="utf-8")
    sinal.passada_de_eventos(passar(0))
    vram = next(e for e in mundo.rota.eventos() if e["eixo"] == "vram")
    assert (vram["estado_leitura"], vram["causa"], vram["fonte"]) == ("nao_consegui_olhar", "ato_nao_respondeu",
                                                                       "infra medir vram")
    assert "valor" not in vram and len(mundo.rota.eventos()) == 4, "os outros três eixos gravam do mesmo jeito"


def test_ato_que_demora_mais_que_o_teto_grava_nao_consegui_olhar_sem_esperar_o_neto(mundo, monkeypatch):
    """O ato dorme num `sleep` filho do script: estourado o teto, o grupo inteiro morre, e a passada nao espera o cano."""
    monkeypatch.setattr(sinal, "ATO_TIMEOUT_S", 0.3)
    (mundo.modos / "cpu").write_text("dorme", encoding="utf-8")
    antes = time.monotonic()
    sinal.passada_de_eventos(passar(0))
    assert time.monotonic() - antes < 3, "o `sleep 5` do ato nao segurou a passada"
    cpu = next(e for e in mundo.rota.eventos() if e["eixo"] == "cpu")
    assert (cpu["estado_leitura"], cpu["causa"]) == ("nao_consegui_olhar", "ato_nao_respondeu")


def test_ato_que_saiu_5_com_o_json_grava_a_causa_que_ele_mesmo_deu(mundo):
    (mundo.respostas / "ram.json").write_text(json.dumps(eixos.montar(
        "ram", "infra-medir-ram", estado="nao_consegui_olhar", causa="journal_sem_leitura", fonte="journalctl --user",
        janela=60)), encoding="utf-8")
    (mundo.modos / "ram").write_text("cinco", encoding="utf-8")
    sinal.passada_de_eventos(passar(0))
    ram = next(e for e in mundo.rota.eventos() if e["eixo"] == "ram")
    assert (ram["causa"], ram["fonte"]) == ("journal_sem_leitura", "journalctl --user") and "valor" not in ram


def test_ato_de_outro_eixo_na_saida_nao_vale_como_resposta(mundo):
    (mundo.respostas / "cpu.json").write_text(json.dumps(_json_do_eixo("ram")), encoding="utf-8")
    sinal.passada_de_eventos(passar(0))
    assert next(e for e in mundo.rota.eventos() if e["eixo"] == "cpu")["causa"] == "ato_nao_respondeu"


# --- a rede: reconexão entre passadas -------------------------------------------------------------------

def test_a_reconexao_do_tunel_e_a_diferenca_entre_duas_passadas(mundo):
    sinal.passada_de_eventos(passar(0))
    primeira = next(e for e in mundo.rota.eventos() if e["eixo"] == "rede")
    assert all("reconexoes" not in t for t in primeira["tuneis"]), "sem leitura anterior, nulo e nunca zero"
    j = _json_do_eixo("rede")
    for t in j["tuneis"]:
        t["reconexoes_acumuladas"] = 27
    (mundo.respostas / "rede.json").write_text(json.dumps(j), encoding="utf-8")
    sinal.passada_de_eventos(passar(1))
    segunda = [e for e in mundo.rota.eventos() if e["eixo"] == "rede"][1]
    assert {t["tunel"]: t["reconexoes"] for t in segunda["tuneis"]} == {"ops": 3, "recuperacao": 3, "wiki": 3}


# --- a morte -------------------------------------------------------------------------------------------

MORTE = {"evento_id": "9f0a3f0e-1111-5222-8333-444455556666", "ts": "2026-10-21T14:59:30.123Z", "instancia": "host-1",
         "instrumento": "detector-morte", "schema_v": 1, "estado_leitura": "lida", "boot_id": "0a1b2c3d-4e5f-6071-8293-a4b5c6d7e8f9",
         "pid": 4242, "escopo": "cgroup", "detectado_em": "2026-10-21T15:00:07.000Z", "servico": "core/keycloak"}


def test_a_morte_do_detector_vai_pela_mesma_rota_na_familia_dela(mundo):
    mundo.escrever_detector({"estado_leitura": "lida", "causa": None, "fonte": None, "mortes": [MORTE],
                             "vistas_sem_pid": [], "avisos": []})
    r = sinal.passada_de_eventos(passar(0))
    assert mundo.rota.eventos("morte_limite") == [MORTE] and r["mortes"] == 1
    assert {f for f, _ in mundo.rota.pedidos} == {"eixo_host", "morte_limite"}


def test_o_detector_roda_toda_passada_fora_da_cadencia_do_registro(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={"rede": 3600, "ram": 3600, "vram": 3600, "cpu": 3600})
    for minuto in range(5):
        sinal.passada_de_eventos(passar(minuto))
    assert len(mundo.detector_args.read_text(encoding="utf-8").splitlines()) == 5
    assert mundo.chamou().count("ram") == 1


def test_o_cursor_do_detector_anda_so_quando_ele_leu(mundo):
    sinal.passada_de_eventos(passar(0))
    primeira = mundo.detector_args.read_text(encoding="utf-8").splitlines()[0]
    assert "--desde" not in primeira and f"--ate {int(passar(0).timestamp())}" in primeira
    sinal.passada_de_eventos(passar(1))
    segunda = mundo.detector_args.read_text(encoding="utf-8").splitlines()[1]
    assert f"--desde {int(passar(0).timestamp())} --ate {int(passar(1).timestamp())}" in segunda
    mundo.escrever_detector({"estado_leitura": "nao_consegui_olhar", "causa": "kernel_sem_permissao",
                             "fonte": "journalctl -k", "mortes": [], "vistas_sem_pid": [], "avisos": []}, saida=5)
    sinal.passada_de_eventos(passar(2))
    sinal.passada_de_eventos(passar(3))
    quarta = mundo.detector_args.read_text(encoding="utf-8").splitlines()[3]
    assert f"--desde {int(passar(1).timestamp())} --ate {int(passar(3).timestamp())}" in quarta, \
        "a janela que o detector não leu volta inteira quando a permissão chegar"


def test_detector_sem_permissao_aparece_na_linha_e_nao_derruba_a_serie(mundo):
    mundo.escrever_detector({"estado_leitura": "nao_consegui_olhar", "causa": "kernel_sem_permissao",
                             "fonte": "journalctl -k", "mortes": [], "vistas_sem_pid": [], "avisos": []}, saida=5)
    r = sinal.passada_de_eventos(passar(0))
    linha = sinal._linha_dos_eventos(r)
    assert "morte: nao consegui olhar (kernel_sem_permissao)" in linha and len(mundo.rota.eventos()) == 4
    assert mundo.rota.eventos("morte_limite") == []


def test_morte_vista_sem_pid_aparece_na_linha(mundo):
    mundo.escrever_detector({"estado_leitura": "lida", "causa": None, "fonte": None, "mortes": [],
                             "vistas_sem_pid": [{"fonte": "docker_events", "conteiner": "x", "ts": "t"}],
                             "avisos": ["docker events: docker_events_fora"]})
    linha = sinal._linha_dos_eventos(sinal.passada_de_eventos(passar(0)))
    assert "morte: 0, 1 vista(s) sem pid" in linha and "aviso: docker events: docker_events_fora" in linha


def test_detector_que_nao_respondeu_e_nao_consegui_olhar_e_nao_zero_morte(mundo):
    mundo.detector_json.write_text("isto nao e json", encoding="utf-8")
    r = sinal.passada_de_eventos(passar(0))
    assert r["morte"]["estado_leitura"] == "nao_consegui_olhar" and r["morte"]["causa"] == "detector_nao_respondeu"


# --- o modo à mão ---------------------------------------------------------------------------------------

def test_eventos_ver_mostra_o_que_gravaria_sem_fila_sem_estado_e_sem_enviar(mundo, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sinal", "--eventos", "--ver"])
    assert sinal.main() == 0
    saida = capsys.readouterr().out
    assert saida.count("eixo_host {") == 4 and "eventos: rede lida, ram lida, vram lida, cpu lida" in saida
    assert 'morte {"ate"' in saida and '"estado_leitura": "lida"' in saida, "o que o detector respondeu, para quem confere o kernel"
    assert mundo.rota.pedidos == [] and not mundo.pasta.exists() or not (mundo.pasta / "cadencia.json").exists()
    assert not (mundo.pasta / "fila-eixo_host.jsonl").exists()
    assert TOKEN not in saida


def test_eventos_sem_ver_faz_a_passada_inteira(mundo, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sinal", "--eventos"])
    assert sinal.main() == 0
    assert "eixo_host 4 gravadas" in capsys.readouterr().out and len(mundo.rota.eventos()) == 4


def test_eventos_a_mao_com_registro_recusado_sai_4_com_a_causa(mundo, monkeypatch, capsys):
    mundo.registro(monkeypatch, eixos={"ram": 90})
    monkeypatch.setattr("sys.argv", ["sinal", "--eventos"])
    assert sinal.main() == 4
    assert "múltiplo de um minuto" in capsys.readouterr().err


def _leitura(estado="completa", n=60, coberto=3540):
    return 200, {"familia": "eixo_host", "eixo": "ram", "granularidade": "amostra",
                 "amostras": [{"estado_leitura": "lida"}] * n,
                 "cobertura": {"estado": estado, "esperado_s": 3540, "coberto_s": coberto, "fracao": coberto / 3540}}


def test_serie_diz_amostras_e_cobertura_e_sai_0_quando_completa(mundo, monkeypatch, capsys):
    mundo.rota.leitura = _leitura()
    monkeypatch.setattr("sys.argv", ["sinal", "--serie", "ram", "--horas", "1"])
    assert sinal.main() == 0
    assert "ram: 60 amostras (60 lidas) em 1 h, cobertura completa (3540 de 3540 s)" in capsys.readouterr().out


def test_serie_incompleta_sai_1(mundo, monkeypatch, capsys):
    mundo.rota.leitura = _leitura("parcial", 50, 3000)
    monkeypatch.setattr("sys.argv", ["sinal", "--serie", "cpu"])
    assert sinal.main() == 1
    assert "50 amostras" in capsys.readouterr().out


def test_serie_de_um_dia_para_cima_le_o_agregado_por_hora(mundo, monkeypatch, capsys):
    mundo.rota.leitura = (200, {"familia": "eixo_host", "eixo": "ram", "granularidade": "hora",
                                "horas": [{"estado": "completa", "lidas": 60}, {"estado": "ausente", "lidas": 0}],
                                "cobertura": {"estado": "parcial", "esperado_s": 7200, "coberto_s": 3600, "fracao": 0.5}})
    monkeypatch.setattr("sys.argv", ["sinal", "--serie", "ram", "--horas", "48"])
    assert sinal.main() == 1
    assert "2 horas (1 lidas) em 48 h" in capsys.readouterr().out


def test_serie_com_a_api_fora_sai_5(mundo, monkeypatch, capsys):
    monkeypatch.setenv("SINAL_EVENTOS_URL", "http://127.0.0.1:9")
    monkeypatch.setattr("sys.argv", ["sinal", "--serie", "ram"])
    assert sinal.main() == 5
    assert "nao respondeu" in capsys.readouterr().out


def test_serie_com_a_api_recusando_diz_o_motivo_e_sai_5(mundo, monkeypatch, capsys):
    mundo.rota.leitura = (422, {"tipo": "JanelaLongaDemais", "detalhe": "peça granularidade=hora"})
    monkeypatch.setattr("sys.argv", ["sinal", "--serie", "ram"])
    assert sinal.main() == 5
    assert "422 JanelaLongaDemais" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["--serie"], ["--serie", "disco"], ["--serie", "ram", "--horas"],
                                  ["--serie", "ram", "--horas", "0"], ["--serie", "ram", "--horas", "abc"],
                                  ["--serie", "ram", "x"], ["--serie", "ram", "--horas", "9601"]])
def test_serie_com_uso_errado_sai_2(args, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sinal", *args])
    assert sinal.main() == 2
    assert "uso: sinal --serie" in capsys.readouterr().err


# --- o exit do sinal não muda ----------------------------------------------------------------------------

def _coleta(estado):
    return lambda: {"gerado_em": "2026-10-21T15:00:00+00:00",
                    "runtime": {"estado": "no-ar", "exercitado": "docker run", "lido_em": "2026-10-21T15:00:00+00:00"},
                    "servicos": {"keycloak": {"estado": estado, "exercitado": "x", "motivo": "m",
                                              "lido_em": "2026-10-21T15:00:00+00:00"}}}


@pytest.fixture
def sinal_de_mentira(tmp_path, monkeypatch):
    monkeypatch.setattr(sinal, "SAIDA", str(tmp_path / "servicos.json"))
    monkeypatch.setattr("sys.argv", ["sinal"])


@pytest.mark.parametrize("estado, exit_esperado", [("no-ar", 0), ("fora", 1)])
def test_erro_da_passada_de_eventos_nunca_muda_o_exit_do_sinal(sinal_de_mentira, monkeypatch, capsys, estado, exit_esperado):
    monkeypatch.setattr(sinal, "coleta", _coleta(estado))

    def estoura(*a, **k):
        raise RuntimeError("explodiu")
    monkeypatch.setattr(sinal, "passada_de_eventos", estoura)
    assert sinal.main() == exit_esperado
    saida = capsys.readouterr()
    assert "sinal: eventos: RuntimeError: explodiu" in saida.err and "keycloak" in saida.out


def test_registro_recusado_dentro_do_sinal_vai_a_stderr_e_o_exit_segue(sinal_de_mentira, mundo, monkeypatch, capsys):
    monkeypatch.setattr(sinal, "coleta", _coleta("no-ar"))
    mundo.registro(monkeypatch, eixos={"ram": 90})
    assert sinal.main() == 0
    assert "sinal: eventos: RegistroInvalido" in capsys.readouterr().err


def test_o_sinal_inteiro_grava_a_saude_e_depois_a_serie_e_diz_numa_linha(sinal_de_mentira, mundo, monkeypatch, capsys):
    monkeypatch.setattr(sinal, "coleta", _coleta("no-ar"))
    assert sinal.main() == 0
    linhas = capsys.readouterr().out.splitlines()
    assert linhas[-1].startswith("eventos: rede lida, ram lida, vram lida, cpu lida · morte: 0 · eixo_host 4 gravadas")
    assert any("keycloak" in linha for linha in linhas[:-1]) and len(mundo.rota.eventos()) == 4
    assert json.loads(Path(sinal.SAIDA).read_text(encoding="utf-8"))["servicos"]["keycloak"]["estado"] == "no-ar"


def test_a_linha_dos_eventos_diz_o_que_o_banco_mudo_deixou_na_fila_e_o_que_a_rota_recusou():
    r = {"eixos": {"ram": ("lida", None), "vram": ("nao_consegui_olhar", "driver_fora")}, "amostras": 2, "mortes": 0,
         "morte": {"estado_leitura": "lida", "mortes": [], "vistas_sem_pid": [], "avisos": []}, "descartados": 3,
         "envio": {"eixo_host": {"inseridos": 0, "existentes": 1, "recusados": [{"evento_id": "x"}], "pendentes": 5,
                                 "erro": "503 BancoIndisponivel"}}}
    assert sinal._linha_dos_eventos(r) == (
        "eventos: ram lida, vram nao consegui olhar (driver_fora) · morte: 0 · eixo_host 1 gravadas, 1 recusadas, "
        "5 na fila, erro: 503 BancoIndisponivel · fila cheia: 3 descartada(s) das mais antigas")


def test_nenhum_eixo_vencido_diz_que_nenhum_venceu(mundo, monkeypatch):
    mundo.registro(monkeypatch, eixos={e: 3600 for e in CADEIA_ATOS})
    sinal.passada_de_eventos(passar(0))
    r = sinal.passada_de_eventos(passar(1))
    assert r["eixos"] == {} and "nenhum eixo venceu" in sinal._linha_dos_eventos(r)
