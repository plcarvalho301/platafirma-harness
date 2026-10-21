"""`sinal`: serviço fora há mais de 10 min abre incidente no rastreador (card #3253, pós-morte #3251).

Contrato verificado:
- Se um serviço permanece com estado 'fora' por >= 10 minutos (600s), sinal chama tarefas criar --incidente.
- O incidente é criado exatamente uma vez por episódio de indisponibilidade (idempotente).
- Quando o serviço volta a ficar 'no-ar', fora_desde e incidente_id são limpos.
- Serviços com 'sem-sinal' ou 'degradado' não disparam incidente.
- Runtime fora há mais de 10 min também abre incidente.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SINAL_PATH = RAIZ / "bin" / "sinal"


def _carregar_sinal():
    loader = importlib.machinery.SourceFileLoader("sinal_bin", str(SINAL_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


sinal = _carregar_sinal()


def test_parse_dt():
    dt1 = sinal.parse_dt("2026-10-05T17:00:00+00:00")
    assert dt1.tzinfo is not None
    assert dt1.year == 2026

    dt2 = sinal.parse_dt("2026-10-05T17:00:00Z")
    assert dt2.tzinfo is not None
    assert dt1 == dt2


def test_servico_no_ar_limpa_estado():
    agora = datetime(2026, 10, 5, 17, 30, 0, tzinfo=timezone.utc)
    item = {"estado": "no-ar", "exercitado": "healthcheck"}
    anterior_item = {
        "estado": "fora",
        "fora_desde": "2026-10-05T17:00:00+00:00",
        "incidente_id": "3200",
    }
    chamadas = []
    sinal.processa_estado_item("teste-svc", item, anterior_item, agora, abre_incidente_fn=lambda n, i: chamadas.append((n, i)))
    assert len(chamadas) == 0
    assert "fora_desde" not in item
    assert "incidente_id" not in item


def test_servico_fora_menos_de_10_min():
    agora = datetime(2026, 10, 5, 17, 5, 0, tzinfo=timezone.utc)
    fora_inicio = (agora - timedelta(minutes=5)).isoformat(timespec="seconds")
    item = {"estado": "fora", "motivo": "exited 127"}
    anterior_item = {"estado": "fora", "fora_desde": fora_inicio}

    chamadas = []
    sinal.processa_estado_item("teste-svc", item, anterior_item, agora, abre_incidente_fn=lambda n, i: chamadas.append((n, i)))

    assert len(chamadas) == 0
    assert item["fora_desde"] == fora_inicio
    assert "incidente_id" not in item


def test_servico_fora_mais_de_10_min_abre_incidente():
    agora = datetime(2026, 10, 5, 17, 15, 0, tzinfo=timezone.utc)
    fora_inicio = (agora - timedelta(minutes=11)).isoformat(timespec="seconds")
    item = {"estado": "fora", "motivo": "connection refused"}
    anterior_item = {"estado": "fora", "fora_desde": fora_inicio}

    chamadas = []

    def mock_abre(nome, info):
        chamadas.append((nome, info))
        return "3295"

    sinal.processa_estado_item("rag-extractor-api", item, anterior_item, agora, abre_incidente_fn=mock_abre)

    assert len(chamadas) == 1
    assert chamadas[0][0] == "rag-extractor-api"
    assert item["fora_desde"] == fora_inicio
    assert item["incidente_id"] == "3295"


def test_servico_fora_com_incidente_ja_aberto_nao_duplica():
    agora = datetime(2026, 10, 5, 17, 20, 0, tzinfo=timezone.utc)
    fora_inicio = (agora - timedelta(minutes=16)).isoformat(timespec="seconds")
    item = {"estado": "fora", "motivo": "connection refused"}
    anterior_item = {
        "estado": "fora",
        "fora_desde": fora_inicio,
        "incidente_id": "3295",
    }

    chamadas = []
    sinal.processa_estado_item("rag-extractor-api", item, anterior_item, agora, abre_incidente_fn=lambda n, i: chamadas.append((n, i)))

    assert len(chamadas) == 0
    assert item["fora_desde"] == fora_inicio
    assert item["incidente_id"] == "3295"


def test_sem_sinal_e_degradado_nao_disparam_incidente():
    agora = datetime(2026, 10, 5, 17, 30, 0, tzinfo=timezone.utc)
    item_sem_sinal = {"estado": "sem-sinal", "motivo": "sem sonda"}
    item_degradado = {"estado": "degradado", "motivo": "starting"}

    chamadas = []
    sinal.processa_estado_item("mcp", item_sem_sinal, None, agora, abre_incidente_fn=lambda n, i: chamadas.append((n, i)))
    sinal.processa_estado_item("web", item_degradado, None, agora, abre_incidente_fn=lambda n, i: chamadas.append((n, i)))

    assert len(chamadas) == 0
    assert "fora_desde" not in item_sem_sinal
    assert "fora_desde" not in item_degradado


def test_runtime_fora_mais_de_10_min():
    agora = datetime(2026, 10, 5, 17, 15, 0, tzinfo=timezone.utc)
    fora_inicio = (agora - timedelta(minutes=12)).isoformat(timespec="seconds")
    dados = {
        "servicos": {},
        "runtime": {"estado": "fora", "motivo": "docker run alpine:3 failed"},
    }
    anterior = {
        "servicos": {},
        "runtime": {"estado": "fora", "fora_desde": fora_inicio},
    }

    chamadas = []

    def mock_abre(nome, info):
        chamadas.append((nome, info))
        return "3296"

    sinal.reconcilia_com_anterior(dados, anterior, agora_dt=agora, abre_incidente_fn=mock_abre)

    assert len(chamadas) == 1
    assert chamadas[0][0] == "runtime"
    assert dados["runtime"]["incidente_id"] == "3296"


def test_ciclo_completo_reconciliacao():
    t0 = datetime(2026, 10, 5, 15, 0, 0, tzinfo=timezone.utc)

    # 15:00: tudo no ar
    dados1 = {"servicos": {"api": {"estado": "no-ar"}}, "runtime": {"estado": "no-ar"}}
    rec1 = sinal.reconcilia_com_anterior(dados1, None, agora_dt=t0)
    assert "fora_desde" not in rec1["servicos"]["api"]

    # 15:01: api cai
    t1 = t0 + timedelta(minutes=1)
    dados2 = {"servicos": {"api": {"estado": "fora", "motivo": "crash"}}, "runtime": {"estado": "no-ar"}}
    chamadas = []
    rec2 = sinal.reconcilia_com_anterior(dados2, rec1, agora_dt=t1, abre_incidente_fn=lambda n, i: chamadas.append(n))
    assert len(chamadas) == 0
    assert rec2["servicos"]["api"]["fora_desde"] is not None
    assert "incidente_id" not in rec2["servicos"]["api"]

    # 15:06: 5 minutos fora
    t2 = t0 + timedelta(minutes=6)
    dados3 = {"servicos": {"api": {"estado": "fora", "motivo": "crash"}}, "runtime": {"estado": "no-ar"}}
    rec3 = sinal.reconcilia_com_anterior(dados3, rec2, agora_dt=t2, abre_incidente_fn=lambda n, i: chamadas.append(n))
    assert len(chamadas) == 0
    assert rec3["servicos"]["api"]["fora_desde"] == rec2["servicos"]["api"]["fora_desde"]

    # 15:11: 10 minutos fora -> abre incidente
    t3 = t0 + timedelta(minutes=11)
    dados4 = {"servicos": {"api": {"estado": "fora", "motivo": "crash"}}, "runtime": {"estado": "no-ar"}}
    inc_chamadas = []
    rec4 = sinal.reconcilia_com_anterior(dados4, rec3, agora_dt=t3, abre_incidente_fn=lambda n, i: inc_chamadas.append(n) or "3301")
    assert inc_chamadas == ["api"]
    assert rec4["servicos"]["api"]["incidente_id"] == "3301"

    # 15:12: 11 minutos fora -> não duplica incidente
    t4 = t0 + timedelta(minutes=12)
    dados5 = {"servicos": {"api": {"estado": "fora", "motivo": "crash"}}, "runtime": {"estado": "no-ar"}}
    inc_chamadas2 = []
    rec5 = sinal.reconcilia_com_anterior(dados5, rec4, agora_dt=t4, abre_incidente_fn=lambda n, i: inc_chamadas2.append(n) or "3302")
    assert len(inc_chamadas2) == 0
    assert rec5["servicos"]["api"]["incidente_id"] == "3301"

    # 15:15: serviço recupera
    t5 = t0 + timedelta(minutes=15)
    dados6 = {"servicos": {"api": {"estado": "no-ar"}}, "runtime": {"estado": "no-ar"}}
    rec6 = sinal.reconcilia_com_anterior(dados6, rec5, agora_dt=t5)
    assert "fora_desde" not in rec6["servicos"]["api"]
    assert "incidente_id" not in rec6["servicos"]["api"]


# --- log e estado do conteiner no incidente (card #3469): #3382 e #3383 ficaram sem causa porque o log
# saiu com a recriacao do conteiner. O docker e o `tarefas` sao falsos (roda trocado); o que se prova e
# o corpo que chega ao `tarefas criar --incidente`.

SEGREDOS = ("hunter2", "abc123tokenvalue", "s3cr3tpw", "zzz999", "SuperSecretCookie42",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk")

LOG_COM_SEGREDO = (
    "2026-10-12T14:00:01Z listening on 8080\n"
    "2026-10-12T14:00:02Z DB_PASSWORD=hunter2 conectando\n"
    "2026-10-12T14:00:03Z Authorization: Bearer abc123tokenvalue\n"
    "2026-10-12T14:00:04Z dsn postgres://app:s3cr3tpw@db:5432/kc\n"
    "2026-10-12T14:00:05Z GET /health?token=zzz999&x=1 503\n"
    '2026-10-12T14:00:06Z {"cookie_secret": "SuperSecretCookie42", "nivel": "warn"}\n'
    "2026-10-12T14:00:07Z jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk\n"
    "2026-10-12T14:00:08Z db fora, tentando de novo (errors=remount-ro)\n"
)

def _estado(saude="unhealthy", saida="curl: (7) Failed to connect to localhost port 8080"):
    return {
        "Status": "running", "Running": True, "ExitCode": 0, "OOMKilled": False,
        "StartedAt": "2026-10-12T13:00:00Z", "FinishedAt": "0001-01-01T00:00:00Z",
        "Health": {"Status": saude, "FailingStreak": 3, "Log": [
            {"Start": "2026-10-12T14:00:00Z", "End": "2026-10-12T14:00:01Z", "ExitCode": 0, "Output": "ok"},
            {"Start": "2026-10-12T14:01:00Z", "End": "2026-10-12T14:01:01Z", "ExitCode": 1, "Output": saida},
        ]},
    }

class DockerETarefasFalsos:
    """Troca `roda` e `shutil.which`: responde o docker conforme a mesa e anota o `tarefas criar`."""

    def __init__(self, monkeypatch, estado=None, log="", ps="", *, docker_ok=True):
        self.chamadas = []
        self.criado = None
        self.estado, self.log, self.ps, self.docker_ok = estado, log, ps, docker_ok
        monkeypatch.setattr(sinal, "roda", self.roda)
        monkeypatch.setattr(sinal.shutil, "which", lambda nome: "/falso/tarefas")

    def roda(self, cmd, timeout=20):
        self.chamadas.append(list(cmd))
        if cmd[0] == "/falso/tarefas":
            self.criado = {"titulo": cmd[2], "desc": cmd[cmd.index("--desc") + 1], "cmd": list(cmd)}
            return 0, "item 4242 criado", ""
        if not self.docker_ok:
            return 1, "", "Cannot connect to the Docker daemon"
        if cmd[:2] == ["docker", "inspect"]:
            return 0, json.dumps(self.estado) + "\t2", ""
        if cmd[:2] == ["docker", "logs"]:
            return 0, self.log, ""
        if cmd[:2] == ["docker", "ps"]:
            return 0, self.ps, ""
        return 125, "", "comando nao previsto no teste: " + " ".join(cmd)

    def docker(self, verbo):
        return [c for c in self.chamadas if c[:2] == ["docker", verbo]]

FORA = {"estado": "fora", "fora_desde": "2026-10-12T14:00:00+00:00", "exercitado": "healthcheck do contendor",
        "motivo": "curl: (7) Failed to connect to localhost port 8080"}

def test_incidente_nasce_com_conteiner_hora_ultima_saida_e_log(monkeypatch):
    log = "".join(f"2026-10-12T14:00:{i:02d}Z linha-de-log-{i}\n" for i in range(1, 6))
    f = DockerETarefasFalsos(monkeypatch, estado=_estado(), log=log)
    assert sinal.abre_incidente("keycloak", dict(FORA)) == "4242"
    desc = f.criado["desc"]
    assert "platafirma-core-keycloak-1" in desc                       # contendor
    assert re.search(r"Capturado em: 20\d\d-\d\d-\d\dT", desc)         # hora
    assert "Failed to connect to localhost port 8080" in desc          # ultima saida da sonda
    assert "unhealthy" in desc and "falhas seguidas 3" in desc and "reinicios 2" in desc
    for i in range(1, 6):
        assert f"linha-de-log-{i}" in desc                             # log
    assert "--incidente" in f.criado["cmd"]
    assert f.criado["desc"].startswith("Detectado por sinal")          # o corpo de antes continua la

def test_log_pede_so_as_ultimas_linhas_e_o_corpo_e_limitado(monkeypatch):
    log = "".join(f"linha numero {i:04d}\n" for i in range(2000))
    f = DockerETarefasFalsos(monkeypatch, estado=_estado(), log=log)
    sinal.abre_incidente("keycloak", dict(FORA))
    assert f.docker("logs")[0][:5] == ["docker", "logs", "--tail", str(sinal.LINHAS_DE_LOG), "--timestamps"]
    desc = f.criado["desc"]
    assert "linha numero 1999" in desc and "linha numero 0000" not in desc
    assert len(desc) < sinal.LIMITE_DO_LOG + 2000

def test_segredo_do_log_e_da_sonda_nao_chega_ao_corpo(monkeypatch):
    saida = "curl: (22) 401 token=zzz999 Authorization: Bearer abc123tokenvalue"
    f = DockerETarefasFalsos(monkeypatch, estado=_estado(saida=saida), log=LOG_COM_SEGREDO)
    info = dict(FORA, motivo=saida)
    sinal.abre_incidente("keycloak", info)
    for segredo in SEGREDOS:
        assert segredo not in f.criado["desc"], segredo
        assert segredo not in f.criado["titulo"], segredo
    assert "listening on 8080" in f.criado["desc"]                     # o que nao e segredo fica
    assert "errors=remount-ro" in f.criado["desc"]

def test_servico_sem_conteiner_abre_o_incidente_sem_chamar_o_docker(monkeypatch):
    f = DockerETarefasFalsos(monkeypatch)
    info = {"estado": "fora", "fora_desde": "2026-10-12T14:00:00+00:00", "motivo": "Result=exit-code"}
    assert sinal.abre_incidente("casa-site-publicar", info) == "4242"
    assert f.docker("inspect") == [] and f.docker("logs") == []
    assert "sem contêiner" in f.criado["desc"]

def test_docker_fora_nao_impede_o_incidente(monkeypatch):
    f = DockerETarefasFalsos(monkeypatch, docker_ok=False)
    assert sinal.abre_incidente("keycloak", dict(FORA)) == "4242"
    assert "indisponível" in f.criado["desc"]
    assert "platafirma-core-keycloak-1" in f.criado["desc"]

def test_estado_ilegivel_nao_impede_o_incidente(monkeypatch):
    f = DockerETarefasFalsos(monkeypatch, estado=None)                 # inspect devolve "null\t2"
    assert sinal.abre_incidente("keycloak", dict(FORA)) == "4242"
    assert "indisponível" in f.criado["desc"]

def test_sonda_externa_acha_o_conteiner_pelo_host_da_url(monkeypatch):
    nomes = "platafirma-core-oauth2-proxy-harness-1\nplatafirma-core-oauth2-proxy-1\nplatafirma-core-cloudflared-1\n"
    DockerETarefasFalsos(monkeypatch, ps=nomes)
    assert sinal.contendor_do_servico("oauth2-proxy") == "platafirma-core-oauth2-proxy-1"
    assert sinal.contendor_do_servico("oauth2-proxy-harness") == "platafirma-core-oauth2-proxy-harness-1"
    assert sinal.contendor_do_servico("cloudflared") == "platafirma-core-cloudflared-1"
    assert sinal.contendor_do_servico("mcp") is None
    assert sinal.contendor_do_servico("gpu-host") is None

def test_sonda_do_cloudflared_usa_a_porta_de_metricas_fixada_no_core():
    # O compose do core fixa `--metrics 0.0.0.0:20243` (spec eixos-do-host R6). Sonda em 20241 acusou
    # queda falsa com o tunel de pe (#3935).
    urls = {n: url for n, _posto, url, _exige, _proibido in sinal.POR_SONDA_EXTERNA}
    assert urls["cloudflared"] == "http://cloudflared:20243/ready"

def test_redigir_tira_so_o_segredo():
    for segredo in SEGREDOS:
        assert segredo not in sinal.redigir(LOG_COM_SEGREDO)
    saida = sinal.redigir(LOG_COM_SEGREDO)
    assert "DB_PASSWORD=***" in saida
    assert "postgres://app:***@db:5432/kc" in saida
    assert "token=***&x=1" in saida
    assert "listening on 8080" in saida

def test_redigir_deixa_passar_linha_sem_segredo():
    limpo = ("2026-10-12T14:00:00Z GET /opt/platafirma/current/harness/bin/sinal 200 12ms\n"
             "keycloak-db: database system is ready to accept connections\n"
             "contendor platafirma-core-keycloak-1 reiniciado, tentativa 3\n")
    assert sinal.redigir(limpo) == limpo

def test_redigir_bloco_de_chave_privada():
    texto = "antes\n-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\ndepois\n"
    saida = sinal.redigir(texto)
    assert "MIIEvQ" not in saida and "antes" in saida and "depois" in saida

# --- gpu-host (pos-morte do #3401): driver descasado da biblioteca acusa antes da recriacao

def test_gpu_sem_nvidia_smi_e_sem_sinal(monkeypatch):
    monkeypatch.setattr(sinal.shutil, "which", lambda nome: None)
    e = sinal.do_gpu()
    assert e["estado"] == "sem-sinal"
    assert "nvidia-smi ausente" in e["motivo"]


def test_gpu_descasada_e_fora_com_o_erro_do_nvml(monkeypatch):
    monkeypatch.setattr(sinal.shutil, "which", lambda nome: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(sinal, "roda", lambda cmd, timeout=20: (
        18, "", "Failed to initialize NVML: Driver/library version mismatch\nNVML library version: 595.99"))
    e = sinal.do_gpu()
    assert e["estado"] == "fora"
    assert e["motivo"] == "Failed to initialize NVML: Driver/library version mismatch"
    assert e["exercitado"] == "nvidia-smi -L"


def test_gpu_lida_e_no_ar(monkeypatch):
    monkeypatch.setattr(sinal.shutil, "which", lambda nome: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(sinal, "roda", lambda cmd, timeout=20: (
        0, "GPU 0: NVIDIA GeForce RTX 5060 Ti (UUID: GPU-x)", ""))
    assert sinal.do_gpu()["estado"] == "no-ar"


def test_gpu_fora_mais_de_10_min_abre_incidente():
    t0 = datetime(2026, 10, 10, 15, 0, 0, tzinfo=timezone.utc)
    fora = {"servicos": {"gpu-host": {"estado": "fora", "motivo": "Driver/library version mismatch",
                                     "lido_em": t0.isoformat()}}}
    rec = sinal.reconcilia_com_anterior(fora, None, agora_dt=t0)
    abertos = []
    depois = {"servicos": {"gpu-host": {"estado": "fora", "motivo": "Driver/library version mismatch"}}}
    rec2 = sinal.reconcilia_com_anterior(depois, rec, agora_dt=t0 + timedelta(minutes=11),
                                         abre_incidente_fn=lambda n, i: abertos.append(n) or "3999")
    assert abertos == ["gpu-host"]
    assert rec2["servicos"]["gpu-host"]["incidente_id"] == "3999"

# --- raiz-host (pos-morte do #3204, card #3467): a raiz foi a somente leitura em 30/09 e so se soube
# por escrita que falhou. A sonda le a montagem de `/`; o arquivo de montagens vai por parametro
# (ponto de montagem falso), nunca o /proc/mounts do host.

MONTAGENS_RW = (
    "sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0\n"
    "/dev/nvme0n1p2 / ext4 rw,relatime,errors=remount-ro 0 0\n"
    "/dev/nvme0n1p1 /boot/efi vfat rw,relatime 0 0\n"
)
MONTAGENS_RO = MONTAGENS_RW.replace("/ ext4 rw,relatime", "/ ext4 ro,relatime")

def _montagens(tmp_path, texto):
    arq = tmp_path / "mounts"
    arq.write_text(texto, encoding="utf-8")
    return str(arq)

def test_raiz_rw_e_no_ar(tmp_path):
    e = sinal.do_raiz(_montagens(tmp_path, MONTAGENS_RW))
    assert e["estado"] == "no-ar"
    assert "motivo" not in e

def test_raiz_ro_e_fora_com_motivo(tmp_path):
    e = sinal.do_raiz(_montagens(tmp_path, MONTAGENS_RO))
    assert e["estado"] == "fora"
    assert "somente leitura" in e["motivo"]
    assert e["exercitado"]

def test_raiz_so_conta_a_montagem_de_barra_nao_a_de_outro_ponto(tmp_path):
    # /boot/efi em ro nao e a raiz; ro como substring de outra opcao (errors=remount-ro) tambem nao
    texto = MONTAGENS_RW.replace("/boot/efi vfat rw", "/boot/efi vfat ro")
    assert sinal.do_raiz(_montagens(tmp_path, texto))["estado"] == "no-ar"

def test_raiz_a_ultima_montagem_de_barra_vence(tmp_path):
    texto = MONTAGENS_RO + "/dev/nvme0n1p2 / ext4 rw,relatime 0 0\n"
    assert sinal.do_raiz(_montagens(tmp_path, texto))["estado"] == "no-ar"
    texto = MONTAGENS_RW + "/dev/nvme0n1p2 / ext4 ro,relatime 0 0\n"
    assert sinal.do_raiz(_montagens(tmp_path, texto))["estado"] == "fora"

def test_raiz_sem_arquivo_de_montagens_e_sem_sinal_nunca_fora(tmp_path):
    e = sinal.do_raiz(str(tmp_path / "nao-existe"))
    assert e["estado"] == "sem-sinal"
    assert e["motivo"]

def test_raiz_sem_linha_de_barra_e_sem_sinal(tmp_path):
    e = sinal.do_raiz(_montagens(tmp_path, "sysfs /sys sysfs rw 0 0\n"))
    assert e["estado"] == "sem-sinal"

def test_raiz_ro_mais_de_10_min_abre_incidente(tmp_path):
    t0 = datetime(2026, 10, 12, 15, 0, 0, tzinfo=timezone.utc)
    ro = sinal.do_raiz(_montagens(tmp_path, MONTAGENS_RO))
    ro["lido_em"] = t0.isoformat()
    rec = sinal.reconcilia_com_anterior({"servicos": {"raiz-host": ro}}, None, agora_dt=t0)
    abertos = []
    depois = {"servicos": {"raiz-host": sinal.do_raiz(_montagens(tmp_path, MONTAGENS_RO))}}
    rec2 = sinal.reconcilia_com_anterior(depois, rec, agora_dt=t0 + timedelta(minutes=11),
                                         abre_incidente_fn=lambda n, i: abertos.append(n) or "4001")
    assert abertos == ["raiz-host"]
    assert rec2["servicos"]["raiz-host"]["incidente_id"] == "4001"

def test_coleta_traz_raiz_host(tmp_path, monkeypatch):
    # a sonda esta ligada a coleta: sem isto ela existiria e nunca rodaria
    monkeypatch.setenv("SINAL_MONTAGENS", _montagens(tmp_path, MONTAGENS_RO))
    monkeypatch.setattr(sinal, "roda", lambda cmd, timeout=20: (125, "", "docker ausente"))
    monkeypatch.setattr(sinal.shutil, "which", lambda nome: None)
    dados = sinal.coleta()
    assert dados["servicos"]["raiz-host"]["estado"] == "fora"
    assert dados["servicos"]["raiz-host"]["lido_em"]
