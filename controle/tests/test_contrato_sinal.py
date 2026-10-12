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
