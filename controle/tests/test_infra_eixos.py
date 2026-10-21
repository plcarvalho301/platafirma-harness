"""bin/_infra/eixos.py: o JSON, a frase, a chave de serviço e o teto que os quatro eixos têm em comum
(spec eixos-do-host R2 a R5; card #3919).

Sem docker, sem systemd e sem banco: o contêiner chega como labels, o registro de stacks como lista, a unit
como função e o cgroup como árvore de /proc de mentira.
"""
import importlib.util
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

ARQ = Path(__file__).resolve().parents[2] / "bin" / "_infra" / "eixos.py"
_spec = importlib.util.spec_from_file_location("eixos", ARQ)
eixos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eixos)

AGORA = datetime(2026, 10, 21, 15, 4, 5, 123456, tzinfo=timezone.utc)
SHA = "a" * 40
ID_CONTEINER = "b" * 64
TOPOLOGIA = [
    {"slug": "core", "compose": "/opt/platafirma/current/core/docker-compose.yml"},
    {"slug": "eventos", "compose": ["/opt/platafirma/current/core/deploy/eventos/docker-compose.yml"]},
]


def labels_do_core(servico="cloudflared", projeto="platafirma-core"):
    return {
        "com.docker.compose.project": projeto,
        "com.docker.compose.service": servico,
        "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml",
    }


# O que a RAM tem de próprio (R9): cache e total à parte do uso, a pressão do kernel e as mortes por limite da janela.
RAM = {"cache_bytes": 2 << 30, "total_bytes": 30 << 30, "pressao_avg10": 0.5, "pressao_avg60": 0.3,
       "pressao_avg300": 0.1, "mortes": []}


def executavel(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


# --- o JSON -------------------------------------------------------------------------------------

def test_carimbo_em_utc_com_milissegundo():
    assert eixos.carimbo(AGORA) == "2026-10-21T15:04:05.123Z"


def test_montar_traz_os_campos_de_topo_comuns_aos_quatro_eixos():
    j = eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=8 << 30, unidade="bytes",
                     teto=30 << 30, teto_fonte="/proc/meminfo:MemTotal", **RAM)
    assert set(j) >= {"eixo", "carimbo", "instrumento", "estado_leitura", "causa", "fonte", "valor", "unidade",
                      "teto", "teto_fonte", "janela", "consumidores", "limiar", "limiar_por", "schema_v"}
    assert j["schema_v"] == eixos.SCHEMA_V
    assert j["limiar"] is None and j["limiar_por"] is None, "limiar vazio até a rotina de pactuar"
    assert j["janela"] == 0


def test_nao_consegui_olhar_nao_leva_valor_e_exige_causa_e_fonte():
    j = eixos.montar("vram", "infra-medir-vram", agora=AGORA, estado="nao_consegui_olhar",
                     causa="driver_fora", fonte="nvidia-smi")
    assert j["valor"] is None and j["unidade"] is None
    with pytest.raises(ValueError, match="nunca zero"):
        eixos.montar("vram", "infra-medir-vram", agora=AGORA, estado="nao_consegui_olhar",
                     causa="driver_fora", fonte="nvidia-smi", valor=0, unidade="bytes")
    with pytest.raises(ValueError, match="causa em slug"):
        eixos.montar("vram", "infra-medir-vram", agora=AGORA, estado="nao_consegui_olhar", fonte="nvidia-smi")
    with pytest.raises(ValueError, match="fonte que não respondeu"):
        eixos.montar("vram", "infra-medir-vram", agora=AGORA, estado="nao_consegui_olhar", causa="driver_fora")


def test_leitura_lida_sem_valor_so_na_rede():
    with pytest.raises(ValueError, match="sem valor"):
        eixos.montar("cpu", "infra-medir-cpu", agora=AGORA)
    j = eixos.montar("rede", "infra-medir-rede", agora=AGORA,
                     tuneis=[{"tunel": "ops", "estado_leitura": "lida", "causa": None}])
    assert j["valor"] is None


@pytest.mark.parametrize("campos, motivo", [
    ({"valor": 1}, "valor e unidade vão juntos"),
    ({"valor": 1, "unidade": "bananas"}, "unidade fora de"),
    ({"valor": 1, "unidade": "bytes", "teto": 5}, "teto e teto_fonte vão juntos"),
    ({"valor": 1, "unidade": "bytes", "janela": -1}, "janela"),
])
def test_validar_recusa_o_que_a_ficha_recusaria(campos, motivo):
    with pytest.raises(ValueError, match=motivo):
        eixos.montar("ram", "infra-medir-ram", agora=AGORA, **campos)


def test_consumidor_tem_servico_ou_desvio_nunca_os_dois_nem_nenhum():
    medida = {"valor": 0.1, "unidade": "threads"}      # o consumidor de cpu traz as threads dele (#3921)
    base = dict(agora=AGORA, valor=0.4, unidade="threads", teto=12, teto_fonte="/proc/cpuinfo:processor")
    ok = [{**medida, "servico": "core/cloudflared"}, {**medida, "desvio": "unit_sem_stack", "unit": "x.service"}]
    eixos.montar("cpu", "infra-medir-cpu", consumidores=ok, **base)
    for ruim in ({}, {"servico": "core/x", "desvio": "unit_sem_stack"}, {"desvio": "inventado"}, {"servico": "sem-barra"}):
        with pytest.raises(ValueError, match="consumidores"):
            eixos.montar("cpu", "infra-medir-cpu", consumidores=[{**medida, **ruim}], **base)


def test_valor_alto_nao_muda_o_codigo_de_saida():
    j = eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=29 << 30, unidade="bytes",
                     teto=30 << 30, teto_fonte="/proc/meminfo:MemTotal", **RAM)
    assert eixos.codigo_de_saida(j) == 0
    nao = eixos.montar("ram", "infra-medir-ram", agora=AGORA, estado="nao_consegui_olhar",
                       causa="ilegivel", fonte="/proc/meminfo")
    assert eixos.codigo_de_saida(nao) == 5


# --- a frase ------------------------------------------------------------------------------------

def test_frase_de_ram_diz_uso_cache_total_pressao_mortes_e_quem_consome():
    j = eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=8 << 30, unidade="bytes",
                     teto=30 << 30, teto_fonte="/proc/meminfo:MemTotal", janela=3600,
                     consumidores=[{"servico": "core/keycloak"},
                                   {"desvio": "fora_de_compose_e_unit", "executavel": "claude", "pid": 4242,
                                    "linha_de_comando": "claude -p juiz"}],
                     **{**RAM, "mortes": [{"servico": "core/keycloak", "ts": "2026-10-21T14:10:09.000Z",
                                          "fonte": "docker_events"}]})
    assert eixos.frase(j) == (
        "Memória às 15:04:05 UTC: uso real 8 GiB de 30 GiB (/proc/meminfo:MemTotal); "
        "cache que o kernel devolve 2 GiB, à parte; pressão do kernel 0,5/0,3/0,1% em 10, 60 e 300 s; "
        "1 morte por limite em 1 h: core/keycloak às 14:10:09 UTC; consumidores: core/keycloak, "
        "sem dono (fora_de_compose_e_unit: claude, pid 4242, claude -p juiz).")


@pytest.mark.parametrize("segundos, dito", [(3600, "1 h"), (7200, "2 h"), (300, "5 min"), (90, "90 s")])
def test_a_janela_das_mortes_e_dita_na_unidade_inteira_mais_grande(segundos, dito):
    j = eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=1 << 30, unidade="bytes", janela=segundos, **RAM)
    assert f"nenhuma morte por limite em {dito}" in eixos.frase(j)


# --- o que a RAM exige do JSON (R9) ---------------------------------------------------------------

@pytest.mark.parametrize("tira, motivo", [
    ("cache_bytes", "cache_bytes"), ("total_bytes", "total_bytes"), ("pressao_avg60", "pressao_avg60"),
    ("mortes", "mortes deve ser lista"),
])
def test_ram_lida_sem_o_que_e_dela_nao_cumpre_o_schema(tira, motivo):
    campos = {k: v for k, v in RAM.items() if k != tira}
    with pytest.raises(ValueError, match=motivo):
        eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=1 << 30, unidade="bytes", **campos)


def test_ram_mede_em_bytes():
    with pytest.raises(ValueError, match="ram mede em bytes"):
        eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=0.4, unidade="fracao", **RAM)


def test_morte_tem_chave_de_servico_ou_desvio_hora_e_fonte():
    ok = {"servico": "core/keycloak", "ts": "2026-10-21T14:10:09.000Z", "fonte": "journal"}
    eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=1 << 30, unidade="bytes", **{**RAM, "mortes": [ok]})
    for ruim, motivo in (({**ok, "servico": None}, "mortes\\[0\\]: servico ou desvio"),
                         ({**ok, "ts": "ontem"}, "ts fora de"), ({**ok, "fonte": "palpite"}, "fonte fora de")):
        with pytest.raises(ValueError, match=motivo):
            eixos.montar("ram", "infra-medir-ram", agora=AGORA, valor=1 << 30, unidade="bytes",
                         **{**RAM, "mortes": [ruim]})


def test_ram_que_nao_leu_nao_carrega_nada_de_ram():
    j = eixos.montar("ram", "infra-medir-ram", agora=AGORA, estado="nao_consegui_olhar", causa="psi_indisponivel",
                     fonte="/proc/pressure/memory")
    assert eixos.validar(j) == [] and "cache_bytes" not in j


def test_frase_de_leitura_que_falhou_diz_a_fonte_e_nunca_um_numero():
    j = eixos.montar("cpu", "infra-medir-cpu", agora=AGORA, estado="nao_consegui_olhar",
                     causa="ilegivel", fonte="/proc/pressure/cpu")
    assert eixos.frase(j) == "Processamento às 15:04:05 UTC: não consegui olhar /proc/pressure/cpu (ilegivel)."


def test_imprimir_saida_escreve_a_frase_gerada_do_json_e_o_json(capsys):
    j = eixos.montar("cpu", "infra-medir-cpu", agora=AGORA, valor=3, unidade="threads",
                     teto=12, teto_fonte="/proc/cpuinfo:processor")
    assert eixos.imprimir_saida(j, como_json=False) == 0
    assert capsys.readouterr().out.strip() == eixos.frase(j)
    assert eixos.imprimir_saida(j, como_json=True) == 0
    assert json.loads(capsys.readouterr().out) == j


def test_frase_de_rede_conta_conexoes_reconexoes_e_porta():
    tuneis = [
        {"tunel": "ops", "estado_leitura": "lida", "causa": None, "conexoes_borda": 4, "reconexoes_acumuladas": 1,
         "latencia_externa_ms": 183.0, "dur_ms_porta": 41.0, "erros_transporte": 0},
        {"tunel": "recuperacao", "estado_leitura": "nao_consegui_olhar", "causa": "metrica_fora"},
    ]
    j = eixos.montar("rede", "infra-medir-rede", agora=AGORA, tuneis=tuneis, consumidores=[{"servico": "core/ops-tunnel"}])
    assert eixos.frase(j) == (
        "Rede às 15:04:05 UTC: ops com 4 conexões na borda, 1 reconexão desde a partida, "
        "a porta leva 183 ms por fora contra 41 ms que ela mesma registrou; "
        "recuperacao não consegui olhar (metrica_fora); consumidores: core/ops-tunnel.")


# --- o teto lido da máquina ---------------------------------------------------------------------

def test_teto_de_ram_e_de_threads_saem_da_maquina_e_dizem_a_fonte(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:       31457280 kB\nMemFree: 1 kB\n", encoding="utf-8")
    assert eixos.teto_ram(str(meminfo)) == (31457280 * 1024, f"{meminfo}:MemTotal")
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text("processor\t: 0\nmodel\t: x\nprocessor\t: 1\n", encoding="utf-8")
    assert eixos.teto_threads(str(cpuinfo)) == (2, f"{cpuinfo}:processor")


def test_teto_que_nao_se_le_e_erro_de_leitura_nunca_zero(tmp_path):
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.teto_ram(str(tmp_path / "nao-existe"))
    assert e.value.causa == "ilegivel"
    vazio = tmp_path / "meminfo"
    vazio.write_text("MemFree: 1 kB\n", encoding="utf-8")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.teto_ram(str(vazio))
    assert e.value.causa == "memtotal_ausente"


def test_teto_de_vram_pelo_driver(tmp_path):
    smi = executavel(tmp_path / "nvidia-smi", "echo 16311\n")
    assert eixos.teto_vram(str(smi))[0] == 16311 * (1 << 20)
    quebrado = executavel(tmp_path / "smi-quebrado", "echo 'Driver/library version mismatch' >&2; exit 18\n")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.teto_vram(str(quebrado))
    assert e.value.causa == "driver_fora"


# --- a pressão do kernel, o que a frase diz de cada consumidor e o schema da VRAM e do processamento (#3921) ---

def test_pressao_le_a_linha_some_do_psi_e_arquivo_que_falta_e_erro_de_leitura_nunca_zero(tmp_path):
    psi = tmp_path / "cpu"
    psi.write_text("some avg10=1.50 avg60=0.80 avg300=0.40 total=9\nfull avg10=9.00 avg60=9.00 avg300=9.00 total=0\n",
                   encoding="utf-8")
    assert eixos.pressao(str(psi)) == {"pressao_avg10": 1.5, "pressao_avg60": 0.8, "pressao_avg300": 0.4}
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.pressao(str(tmp_path / "nao-existe"))
    assert e.value.causa == "psi_ausente"
    psi.write_text("full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n", encoding="utf-8")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.pressao(str(psi))
    assert e.value.causa == "psi_ilegivel"


def test_a_frase_diz_o_reservado_o_sm_e_as_threads_de_cada_consumidor():
    j = eixos.montar("vram", "infra-medir-vram", agora=AGORA, valor=7 << 30, unidade="bytes", teto=16 << 30,
                     teto_fonte="nvidia-smi", sm_placa_fracao=0.5, consumidores=[
                         {"servico": "busca/embedder", "reservado_bytes": 4 << 30, "sm_fracao": 0.12},
                         {"desvio": "unit_sem_stack", "unit": "bench.service", "pid": 7, "reservado_bytes": 300 << 20,
                          "sm_fracao": None}])
    assert eixos.frase(j) == ("VRAM às 15:04:05 UTC: 7 GiB de 16 GiB (nvidia-smi); SM da placa 50%; consumidores: "
                              "busca/embedder (4 GiB reservados, SM 12%), sem dono (unit_sem_stack: bench.service, pid 7) "
                              "(300 MiB reservados, SM sem amostra).")
    c = eixos.montar("cpu", "infra-medir-cpu", agora=AGORA, valor=0.5, unidade="threads", teto=12, teto_fonte="x",
                     consumidores=[{"servico": "core/keycloak", "valor": 0.25, "unidade": "threads"}])
    assert eixos.frase(c) == "Processamento às 15:04:05 UTC: 0,5 threads de 12 threads (x); consumidores: core/keycloak (0,25 threads)."


def test_o_schema_da_vram_recusa_soma_rotulada_como_total_e_consumidor_sem_reservado():
    base = dict(agora=AGORA, valor=7 << 30, unidade="bytes", teto=16 << 30, teto_fonte="x")
    ok = {"servico": "busca/embedder", "reservado_bytes": 4 << 30, "sm_fracao": None}
    assert eixos.montar("vram", "i", consumidores=[ok], **base)["consumidores"] == [ok]
    with pytest.raises(ValueError, match="não se rotula como total"):
        eixos.montar("vram", "i", consumidores=[ok], total_dos_processos=4 << 30, **base)
    with pytest.raises(ValueError, match="reservado_bytes"):
        eixos.montar("vram", "i", consumidores=[{"servico": "busca/embedder", "sm_fracao": 0.1}], **base)
    with pytest.raises(ValueError, match="sm_fracao"):
        eixos.montar("vram", "i", consumidores=[{"servico": "busca/embedder", "reservado_bytes": 1}], **base)
    with pytest.raises(ValueError, match="mede em bytes"):
        eixos.montar("vram", "i", **{**base, "unidade": "contagem"})


def test_o_schema_do_processamento_pede_threads_teto_e_consumidor_em_threads():
    base = dict(agora=AGORA, valor=1.5, unidade="threads", teto=12, teto_fonte="x")
    eixos.montar("cpu", "i", consumidores=[{"servico": "core/keycloak", "valor": 0.2, "unidade": "threads"}], **base)
    with pytest.raises(ValueError, match="mede em threads"):
        eixos.montar("cpu", "i", **{**base, "unidade": "fracao"})
    with pytest.raises(ValueError, match="declara o teto"):
        eixos.montar("cpu", "i", **{k: v for k, v in base.items() if k not in ("teto", "teto_fonte")})
    with pytest.raises(ValueError, match="consumidores\\[0\\]: valor"):
        eixos.montar("cpu", "i", consumidores=[{"servico": "core/keycloak"}], **base)


def test_inspecionar_conteiner_devolve_nome_e_labels_e_falha_com_a_causa(tmp_path, monkeypatch):
    executavel(tmp_path / "docker", 'case "$*" in *abc*) printf \'/meu-conteiner\\t{"a":"b"}\\n\' ;; '
                                    '*) echo "No such object" >&2; exit 1 ;; esac\n')
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    assert eixos.inspecionar_conteiner("abc123") == ("meu-conteiner", {"a": "b"})
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.inspecionar_conteiner("zzz")
    assert e.value.causa == "conteiner_fora"


def test_a_linha_de_comando_sai_com_o_valor_de_segredo_mascarado_e_cortada():
    linha = ("oauth2-proxy --provider=oidc --client-secret=abc123 --cookie-secure=true --cookie-secret xyz789 "
             "--cookie-name=_oauth2_proxy MY_API_KEY=k1 --token-url=https://idp/token -v")
    assert eixos.linha_sem_segredo(linha) == (
        "oauth2-proxy --provider=oidc --client-secret=*** --cookie-secure=true --cookie-secret *** "
        "--cookie-name=_oauth2_proxy MY_API_KEY=*** --token-url=*** -v")
    assert eixos.linha_sem_segredo("claude -p julgar --caso 12") == "claude -p julgar --caso 12"
    longa = eixos.linha_sem_segredo("python " + "x" * 500)
    assert len(longa) == eixos.LIMITE_DA_LINHA_DE_COMANDO + 1 and longa.endswith("…")


def test_o_processo_resolvido_traz_a_linha_de_comando_ja_mascarada(tmp_path):
    pasta = tmp_path / "77"
    pasta.mkdir()
    (pasta / "cgroup").write_text("0::/user.slice/session-3.scope\n", encoding="utf-8")
    (pasta / "comm").write_text("servidor\n", encoding="utf-8")
    (pasta / "cmdline").write_bytes(b"servidor\0--db-password=hunter2\0--porta=8080\0")
    r = eixos.resolver_pid(77, proc=tmp_path, inspecionar=lambda _: ("x", {}), resolver_unit=lambda _: None,
                           topologia=TOPOLOGIA)
    assert r["linha_de_comando"] == "servidor --db-password=*** --porta=8080" and "hunter2" not in str(r)


def test_conteiner_que_sumiu_entre_a_amostra_e_a_inspecao_vira_desvio_e_docker_fora_continua_falha(tmp_path):
    pasta = tmp_path / "88"
    pasta.mkdir()
    (pasta / "cgroup").write_text(f"0::/user.slice/app.slice/docker-{ID_CONTEINER}.scope\n", encoding="utf-8")

    def sumiu(_):
        raise eixos.ErroDeLeitura("conteiner_fora", "docker inspect")

    def docker_fora(_):
        raise eixos.ErroDeLeitura("docker_fora", "docker inspect")

    r = eixos.resolver_pid(88, proc=tmp_path, inspecionar=sumiu, resolver_unit=lambda _: None, topologia=TOPOLOGIA)
    assert (r["pid"], r["desvio"], r["detalhe"]) == (88, "fora_de_compose_e_unit", "conteiner_sumiu")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.resolver_pid(88, proc=tmp_path, inspecionar=docker_fora, resolver_unit=lambda _: None, topologia=TOPOLOGIA)
    assert e.value.causa == "docker_fora"


# --- a chave de serviço: contêiner -------------------------------------------------------------

def test_conteiner_de_compose_registrado_resolve_para_stack_barra_servico():
    r = eixos.chave_de_conteiner("platafirma-core-cloudflared-1", labels_do_core(), TOPOLOGIA)
    assert r == {"conteiner": "platafirma-core-cloudflared-1", "servico": "core/cloudflared"}


def test_conteiner_sem_label_de_projeto_sai_fora_de_compose_e_unit():
    r = eixos.chave_de_conteiner("kind_gould", {}, TOPOLOGIA)
    assert r == {"conteiner": "kind_gould", "desvio": "fora_de_compose_e_unit"}


def test_conteiner_de_compose_que_o_registro_nao_conhece_tambem_e_desvio():
    labels = labels_do_core()
    labels["com.docker.compose.project.config_files"] = f"/opt/platafirma/platafirma-outro/{SHA}/docker-compose.yml"
    r = eixos.chave_de_conteiner("outro-x-1", labels, TOPOLOGIA)
    assert r["desvio"] == "fora_de_compose_e_unit" and "servico" not in r


def test_duas_stacks_no_mesmo_compose_desempatam_pelo_projeto_ou_nao_resolvem():
    duas = [{"slug": "borda", "compose": "/o/current/core/docker-compose.yml"},
            {"slug": "platafirma-core", "compose": "/o/current/core/docker-compose.yml"}]
    assert eixos.stack_do_conteiner(labels_do_core(), duas) == "platafirma-core"
    duas[1]["slug"] = "harness-borda"
    assert eixos.stack_do_conteiner(labels_do_core(), duas) is None


# --- a chave de serviço: unit ------------------------------------------------------------------

def test_unit_registrada_resolve_e_unit_fora_do_registro_sai_unit_sem_stack():
    registro = {"ops-tunnel.service": "core/ops-tunnel"}
    assert eixos.chave_de_unit("ops-tunnel.service", registro.get) == {"unit": "ops-tunnel.service", "servico": "core/ops-tunnel"}
    assert eixos.chave_de_unit("dbus.service", registro.get) == {"unit": "dbus.service", "desvio": "unit_sem_stack"}


@pytest.mark.parametrize("corpo, esperado", [
    ("echo core/ops-tunnel\n", "core/ops-tunnel"),
    ("echo 'unit_sem_stack: x.service' >&2; exit 1\n", None),
])
def test_resolvedor_do_registro_le_o_acervo_stack_resolver(tmp_path, corpo, esperado):
    acervo = executavel(tmp_path / "acervo", corpo)
    assert eixos.resolvedor_do_registro(acervo)("x.service") == esperado


def test_registro_fora_do_ar_e_erro_de_leitura_e_nao_desvio(tmp_path):
    acervo = executavel(tmp_path / "acervo", "echo 'acervo stack: psql falhou' >&2; exit 3\n")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.resolvedor_do_registro(acervo)("x.service")
    assert e.value.causa == "registro_de_stack_indisponivel"


def test_carregar_topologia_le_o_json_do_acervo(tmp_path):
    acervo = executavel(tmp_path / "acervo", f"echo '{json.dumps(TOPOLOGIA)}'\n")
    assert eixos.carregar_topologia(acervo) == TOPOLOGIA
    ruim = executavel(tmp_path / "acervo2", "echo 'isto nao e json'\n")
    with pytest.raises(eixos.ErroDeLeitura) as e:
        eixos.carregar_topologia(ruim)
    assert e.value.causa == "registro_de_stack_ilegivel"


# --- a chave de serviço: pelo pid ---------------------------------------------------------------

def proc_de_mentira(tmp_path, pid, cgroup, comm="python3", cmdline=b"python3\0x.py\0"):
    pasta = tmp_path / str(pid)
    pasta.mkdir()
    (pasta / "cgroup").write_text(cgroup, encoding="utf-8")
    (pasta / "comm").write_text(comm + "\n", encoding="utf-8")
    (pasta / "cmdline").write_bytes(cmdline)
    return tmp_path


def test_processo_em_conteiner_de_compose_resolve_pelo_cgroup(tmp_path):
    proc = proc_de_mentira(tmp_path, 100, f"0::/user.slice/user@1001.service/user.slice/docker-{ID_CONTEINER}.scope\n")
    r = eixos.resolver_pid(
        100, proc=proc, topologia=TOPOLOGIA, resolver_unit=lambda u: None,
        inspecionar=lambda i: ("platafirma-core-cloudflared-1", labels_do_core()) if i == ID_CONTEINER else pytest.fail(i))
    assert r["servico"] == "core/cloudflared" and r["pid"] == 100 and r["conteiner"] == "platafirma-core-cloudflared-1"


def test_processo_de_unit_registrada_resolve_pelo_registro_e_ignora_o_user_service(tmp_path):
    proc = proc_de_mentira(tmp_path, 200, "0::/user.slice/user-1001.slice/user@1001.service/app.slice/ops-tunnel.service\n")
    r = eixos.resolver_pid(200, proc=proc, topologia=TOPOLOGIA, inspecionar=None,
                           resolver_unit={"ops-tunnel.service": "core/ops-tunnel"}.get)
    assert r["servico"] == "core/ops-tunnel" and r["unit"] == "ops-tunnel.service"


def test_processo_de_unit_fora_do_registro_sai_unit_sem_stack(tmp_path):
    proc = proc_de_mentira(tmp_path, 300, "0::/user.slice/user@1001.service/app.slice/xdg-desktop-portal.service\n")
    r = eixos.resolver_pid(300, proc=proc, topologia=TOPOLOGIA, inspecionar=None, resolver_unit=lambda u: None)
    assert r["desvio"] == "unit_sem_stack" and r["unit"] == "xdg-desktop-portal.service"


def test_processo_solto_sai_fora_de_compose_e_unit_com_pid_e_linha_de_comando(tmp_path):
    proc = proc_de_mentira(tmp_path, 400, "0::/user.slice/user-1001.slice/session-3.scope\n",
                           comm="claude", cmdline=b"claude\0-p\0juiz\0")
    r = eixos.resolver_pid(400, proc=proc, topologia=TOPOLOGIA, inspecionar=None, resolver_unit=lambda u: None)
    assert r == {"pid": 400, "executavel": "claude", "linha_de_comando": "claude -p juiz",
                 "desvio": "fora_de_compose_e_unit"}


def test_processo_que_sumiu_nao_some_da_lista(tmp_path):
    r = eixos.resolver_pid(999, proc=tmp_path, topologia=TOPOLOGIA, inspecionar=None, resolver_unit=lambda u: None)
    assert r["desvio"] == "fora_de_compose_e_unit" and r["pid"] == 999
