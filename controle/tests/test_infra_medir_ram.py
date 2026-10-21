"""`infra medir ram` (bin/_infra/medir-ram): uso real, cache e total em campos distintos, a pressão do kernel, os
maiores consumidores por chave de serviço e as mortes por limite da janela (spec eixos-do-host R4 e R9; card #3920).

O /proc, o meminfo e o PSI são árvores de mentira; docker, journalctl e `acervo` são scripts à frente do PATH. A
morte por limite é provocada no dublê: o docker diz de um evento oom e o journal, de uma unit morta pelo OOM killer.
Nada toca o host.
"""
import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[2] / "bin"
MEDIR = BIN / "_infra" / "medir-ram"
SHA = "c" * 40
ID_KEYCLOAK = "b" * 64
GIB_KB = 1 << 20

PSI = "some avg10=0.50 avg60=0.30 avg300=0.10 total=123456\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
LABELS_KEYCLOAK = {
    "com.docker.compose.project": "platafirma-core", "com.docker.compose.service": "keycloak",
    "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml"}
TOPOLOGIA = [{"slug": "core", "compose": "/opt/platafirma/current/core/docker-compose.yml"}]
# 17:46:40 UTC de 14/10/2026, o instante do kernel que o docker repete no evento
EVENTO_OOM = {"status": "oom", "Type": "container", "Action": "oom", "time": 1792000000, "timeNano": 1792000000123456789,
              "Actor": {"ID": ID_KEYCLOAK, "Attributes": {**LABELS_KEYCLOAK, "name": "platafirma-core-keycloak-1"}}}
# 17:30:00 UTC; o systemd diz da mesma morte duas vezes, com 2 s de diferença
JOURNAL = [
    {"MESSAGE": "ops-tunnel.service: A process of this unit has been killed by the OOM killer.",
     "USER_UNIT": "ops-tunnel.service", "__REALTIME_TIMESTAMP": "1791999000000000"},
    {"MESSAGE": "ops-tunnel.service: Failed with result 'oom-kill'.",
     "USER_UNIT": "ops-tunnel.service", "__REALTIME_TIMESTAMP": "1791999002000000"},
    {"MESSAGE": "ops-tunnel.service: Started Tunel da porta.", "USER_UNIT": "ops-tunnel.service",
     "__REALTIME_TIMESTAMP": "1791999100000000"},
]


def _carregar():
    carregador = importlib.machinery.SourceFileLoader("medir_ram_bin", str(MEDIR))
    spec = importlib.util.spec_from_loader(carregador.name, carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


medir_ram = _carregar()
eixos = medir_ram.eixos


def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


def _meminfo(caminho: Path, disponivel_kb=20 * GIB_KB, total_kb=30 * GIB_KB, sem_disponivel=False) -> Path:
    linhas = [f"MemTotal:       {total_kb} kB", "MemFree:         1000 kB"]
    if not sem_disponivel:
        linhas.append(f"MemAvailable:   {disponivel_kb} kB")
    linhas += [f"Buffers:        {1 * GIB_KB} kB", f"Cached:         {4 * GIB_KB} kB",
               f"SReclaimable:   {1 * GIB_KB} kB", f"Shmem:          {1 * GIB_KB} kB"]
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def _processo(proc: Path, pid: int, cgroup: str, rss_kb: int | None, comm="python3", cmdline=b"python3\0x.py\0"):
    pasta = proc / str(pid)
    pasta.mkdir(parents=True)
    status = f"Name:\t{comm}\n" + ("" if rss_kb is None else f"VmRSS:\t{rss_kb} kB\n")
    (pasta / "status").write_text(status, encoding="utf-8")
    (pasta / "cgroup").write_text(cgroup, encoding="utf-8")
    (pasta / "comm").write_text(comm + "\n", encoding="utf-8")
    (pasta / "cmdline").write_bytes(cmdline)


def _mundo(tmp_path, monkeypatch, *, eventos=(EVENTO_OOM,), journal=JOURNAL, docker_events_ok=True,
           journal_estado="ok", registro_ok=True, disponivel_kb=20 * GIB_KB, sem_disponivel=False, psi=PSI):
    m = type("Mundo", (), {})()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    proc = tmp_path / "proc"
    proc.mkdir()
    _processo(proc, 100, f"0::/user.slice/user@1001.service/user.slice/docker-{ID_KEYCLOAK}.scope\n", 2 * GIB_KB,
              comm="java")
    _processo(proc, 101, f"0::/user.slice/user@1001.service/user.slice/docker-{ID_KEYCLOAK}.scope\n", 1 * GIB_KB,
              comm="java")
    _processo(proc, 200, "0::/user.slice/user@1001.service/app.slice/ops-tunnel.service\n", 500_000, comm="cloudflared")
    _processo(proc, 300, "0::/user.slice/user-1001.slice/session-3.scope\n", 4 * GIB_KB, comm="claude",
              cmdline=b"claude\0-p\0juiz\0")
    _processo(proc, 400, "0::/\n", None, comm="kthreadd")
    _processo(proc, 500, "0::/user.slice/user@1001.service/app.slice/xdg-desktop-portal.service\n", 100_000,
              comm="xdg-portal")
    eventos_arq = tmp_path / "eventos.jsonl"
    eventos_arq.write_text("".join(json.dumps(e) + "\n" for e in eventos), encoding="utf-8")
    journal_arq = tmp_path / "journal.jsonl"
    journal_arq.write_text("".join(json.dumps(e) + "\n" for e in journal), encoding="utf-8")
    _script(bindir / "docker", f'''
case "$1" in
  inspect) printf '%s\\t%s\\n' "/platafirma-core-keycloak-1" '{json.dumps(LABELS_KEYCLOAK)}' ;;
  events) {'cat "' + str(eventos_arq) + '"' if docker_events_ok else 'echo "Cannot connect to the Docker daemon" >&2; exit 1'} ;;
  *) exit 2 ;;
esac
''')
    corpo_journal = {
        "ok": f'cat "{journal_arq}"\n',
        "sem_permissao": 'echo "No journal files were opened due to insufficient permissions." >&2\nexit 0\n',
        "fora": 'echo "Failed to connect to bus" >&2\nexit 1\n',
    }[journal_estado]
    _script(bindir / "journalctl", corpo_journal)
    registro = {"ops-tunnel.service": "core/ops-tunnel"}
    corpo_acervo = 'echo "acervo stack: psql falhou" >&2; exit 3\n' if not registro_ok else (
        'if [ "$1 $2" = "stack ver" ]; then\n'
        f"  echo '{json.dumps(TOPOLOGIA)}'; exit 0\nfi\n"
        'if [ "$1 $2" = "stack resolver" ]; then\n'
        + "".join(f'  [ "$3" = "{u}" ] && {{ echo "{c}"; exit 0; }}\n' for u, c in registro.items())
        + '  echo "unit_sem_stack: $3" >&2; exit 1\nfi\nexit 2\n')
    acervo = _script(bindir / "acervo", corpo_acervo)
    meminfo = _meminfo(tmp_path / "meminfo", disponivel_kb=disponivel_kb, sem_disponivel=sem_disponivel)
    pressao = tmp_path / "psi-memory"
    if psi is not None:
        pressao.write_text(psi, encoding="utf-8")
    slice_events = tmp_path / "memory.events"
    slice_events.write_text("low 0\nhigh 0\nmax 0\noom 2\noom_kill 3\n", encoding="utf-8")
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("INFRA_PROC", str(proc))
    monkeypatch.setenv("INFRA_MEMINFO", str(meminfo))
    monkeypatch.setenv("INFRA_PRESSAO_MEMORIA", str(pressao))
    monkeypatch.setenv("INFRA_SLICE_EVENTS", str(slice_events))
    monkeypatch.setenv("INFRA_ACERVO", str(acervo))
    m.proc, m.bindir = proc, bindir
    return m


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    return _mundo(tmp_path, monkeypatch)


def por_servico(j):
    return {c["servico"]: c for c in j["consumidores"] if c.get("servico")}


def desvios(j):
    return [c for c in j["consumidores"] if c.get("desvio")]


# --- uso, cache e total: três campos, nunca somados ---------------------------------------------------

def test_uso_cache_e_total_saem_em_campos_distintos(mundo):
    j = medir_ram.medir()
    assert j["estado_leitura"] == "lida" and j["eixo"] == "ram" and j["unidade"] == "bytes"
    assert j["valor"] == 10 * GIB_KB * 1024, "uso real: MemTotal menos MemAvailable"
    assert j["cache_bytes"] == 5 * GIB_KB * 1024, "cache: Buffers + Cached + SReclaimable menos Shmem"
    assert j["total_bytes"] == 30 * GIB_KB * 1024 and j["teto"] == j["total_bytes"]
    assert j["teto_fonte"].endswith(":MemTotal"), "o teto se lê da máquina e diz a fonte (R5)"
    assert eixos.validar(j) == []


def test_o_cache_nao_entra_na_conta_do_uso(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, disponivel_kb=25 * GIB_KB)
    j = medir_ram.medir()
    assert j["valor"] == 5 * GIB_KB * 1024, "o uso só muda com MemAvailable; o cache não o infla nem o abate"
    assert j["cache_bytes"] == 5 * GIB_KB * 1024


def test_nenhum_campo_do_json_soma_uso_e_cache(mundo):
    j = medir_ram.medir()
    soma = j["valor"] + j["cache_bytes"]
    for campo, valor in j.items():
        if campo not in ("valor", "cache_bytes") and isinstance(valor, (int, float)) and not isinstance(valor, bool):
            assert valor != soma, f"{campo} repete uso + cache"


def test_a_pressao_do_kernel_traz_as_tres_medias(mundo):
    j = medir_ram.medir()
    assert (j["pressao_avg10"], j["pressao_avg60"], j["pressao_avg300"]) == (0.5, 0.3, 0.1)


# --- quem consome, por chave de serviço ----------------------------------------------------------------

def test_o_conteiner_de_compose_soma_os_processos_e_leva_a_chave(mundo):
    j = medir_ram.medir()
    keycloak = por_servico(j)["core/keycloak"]
    assert keycloak["valor"] == 3 * GIB_KB * 1024, "os dois processos do mesmo cgroup somam"
    assert keycloak["conteiner"] == "platafirma-core-keycloak-1" and keycloak["pid"] == 100
    assert "linha_de_comando" not in keycloak, "argumento é conteúdo: só o desvio carrega a linha"


def test_a_unit_registrada_resolve_pelo_registro(mundo):
    ops = por_servico(medir_ram.medir())["core/ops-tunnel"]
    assert ops["unit"] == "ops-tunnel.service" and ops["valor"] == 500_000 * 1024


def test_processo_sem_dono_e_unit_fora_do_registro_saem_como_desvio_e_nunca_somem(mundo):
    j = medir_ram.medir()
    por_motivo = {d["desvio"]: d for d in desvios(j)}
    assert por_motivo["fora_de_compose_e_unit"]["executavel"] == "claude"
    assert por_motivo["fora_de_compose_e_unit"]["linha_de_comando"] == "claude -p juiz"
    assert por_motivo["unit_sem_stack"]["unit"] == "xdg-desktop-portal.service"
    assert all("servico" not in d for d in desvios(j))


def test_consumidores_vem_do_maior_para_o_menor_e_thread_de_kernel_fica_fora(mundo):
    j = medir_ram.medir()
    valores = [c["valor"] for c in j["consumidores"]]
    assert valores == sorted(valores, reverse=True) and j["consumidores"][0]["desvio"] == "fora_de_compose_e_unit"
    assert all(c.get("executavel") != "kthreadd" for c in j["consumidores"])


def test_so_os_dez_maiores_entram_e_o_resto_e_contado_e_somado(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    for i in range(13):
        _processo(proc, 1000 + i, f"0::/user.slice/user-1001.slice/session-{i}.scope\n", (i + 1) * 1000)
    maiores, omitidos, valor_omitido = medir_ram.consumidores(proc, lambda u: None, TOPOLOGIA)
    assert len(maiores) == 10 and omitidos == 3
    assert valor_omitido == (1 + 2 + 3) * 1000 * 1024, "os três menores"
    assert all(c["desvio"] == "fora_de_compose_e_unit" for c in maiores), "sem dono, e declarado, nunca omitido"


def test_o_json_declara_o_que_ficou_fora_da_lista(mundo):
    j = medir_ram.medir()
    assert j["consumidores_omitidos"] == 0 and j["valor_omitido"] == 0


# --- as mortes por limite ------------------------------------------------------------------------------

def test_a_morte_provocada_no_duble_aparece_na_janela_com_a_chave_do_servico(mundo):
    j = medir_ram.medir()
    docker = next(m for m in j["mortes"] if m["fonte"] == "docker_events")
    assert docker["servico"] == "core/keycloak" and docker["conteiner"] == "platafirma-core-keycloak-1"
    assert docker["ts"] == "2026-10-14T17:46:40.123Z", "o instante do evento, não o da detecção"
    assert docker["escopo"] == "cgroup"
    assert eixos.validar(j) == []


def test_a_morte_de_unit_vem_do_journal_com_a_chave_do_registro_e_conta_uma_vez(mundo):
    j = medir_ram.medir()
    journal = [m for m in j["mortes"] if m["fonte"] == "journal"]
    assert len(journal) == 1, "a morte e a falha por oom-kill, a 2 s uma da outra, são a mesma morte"
    assert journal[0]["servico"] == "core/ops-tunnel" and journal[0]["unit"] == "ops-tunnel.service"
    assert journal[0]["ts"] == "2026-10-14T17:30:00.000Z"


def test_as_mortes_saem_em_ordem_de_instante(mundo):
    assert [m["fonte"] for m in medir_ram.medir()["mortes"]] == ["journal", "docker_events"]


def test_o_contador_do_slice_diz_que_houve_morte_sem_culpado(mundo):
    j = medir_ram.medir()
    assert j["oom_kill_slice"] == 3
    assert "3 oom_kill desde a partida" in eixos.frase(j)


def test_nenhuma_morte_e_resposta_lida_e_nao_ausencia(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, eventos=(), journal=())
    j = medir_ram.medir()
    assert j["estado_leitura"] == "lida" and j["mortes"] == []
    assert "nenhuma morte por limite em 1 h" in eixos.frase(j)


def test_morte_de_conteiner_fora_de_compose_sai_como_desvio(tmp_path, monkeypatch):
    avulso = {**EVENTO_OOM, "Actor": {"ID": "c" * 64, "Attributes": {"name": "kind_gould"}}}
    _mundo(tmp_path, monkeypatch, eventos=(avulso,), journal=())
    morte = medir_ram.medir()["mortes"][0]
    assert morte["desvio"] == "fora_de_compose_e_unit" and morte["conteiner"] == "kind_gould"


# --- fonte muda: nunca zero ----------------------------------------------------------------------------

def test_journal_sem_permissao_nao_vira_zero_morte(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, journal_estado="sem_permissao")
    assert medir_ram.main(["--json"]) == 5
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["causa"] == "journal_sem_leitura"
    assert j["valor"] is None and "mortes" not in j, "quem não leu não tem número, nunca zero"


def test_journal_fora_do_ar_nao_consegui_olhar(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, journal_estado="fora")
    j = medir_ram.medir()
    assert (j["estado_leitura"], j["causa"]) == ("nao_consegui_olhar", "journal_sem_leitura")


def test_docker_events_fora_do_ar_nao_consegui_olhar(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, docker_events_ok=False)
    j = medir_ram.medir()
    assert (j["estado_leitura"], j["causa"], j["fonte"]) == ("nao_consegui_olhar", "docker_events_fora", "docker events")


def test_meminfo_sem_memavailable_nao_inventa_uso(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, sem_disponivel=True)
    j = medir_ram.medir()
    assert (j["estado_leitura"], j["causa"]) == ("nao_consegui_olhar", "memavailable_ausente")
    assert j["valor"] is None and eixos.codigo_de_saida(j) == 5


def test_psi_indisponivel_nao_consegui_olhar(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, psi=None)
    j = medir_ram.medir()
    assert (j["estado_leitura"], j["causa"]) == ("nao_consegui_olhar", "psi_indisponivel")


def test_registro_de_stacks_fora_do_ar_nao_vira_desvio_inventado(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, registro_ok=False)
    j = medir_ram.medir()
    assert (j["estado_leitura"], j["causa"]) == ("nao_consegui_olhar", "registro_de_stack_indisponivel")
    assert j["consumidores"] == []


# --- medida não reprova ---------------------------------------------------------------------------------

def test_memoria_quase_toda_usada_sai_0(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, disponivel_kb=1000)
    assert medir_ram.main(["--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["valor"] > 29 * GIB_KB * 1024 and j["estado_leitura"] == "lida"


# --- a frase e a linha de comando ----------------------------------------------------------------------

def test_a_frase_impressa_e_a_funcao_unica_aplicada_ao_json(mundo, capsys):
    j = medir_ram.medir()
    assert eixos.imprimir_saida(j, como_json=False) == 0
    frase = eixos.frase(j)
    assert capsys.readouterr().out.strip() == frase
    assert "uso real 10 GiB de 30 GiB" in frase and "cache que o kernel devolve 5 GiB, à parte" in frase
    assert "pressão do kernel 0,5/0,3/0,1% em 10, 60 e 300 s" in frase
    assert "2 mortes por limite em 1 h: core/ops-tunnel às 17:30:00 UTC, core/keycloak às 17:46:40 UTC" in frase
    assert "sem dono (fora_de_compose_e_unit: claude, pid 300, claude -p juiz)" in frase


def test_janela_ajustavel_e_dita_na_frase(mundo, capsys):
    assert medir_ram.main(["--janela", "300"]) == 0
    assert "em 5 min" in capsys.readouterr().out
    assert medir_ram.medir(300)["janela"] == 300


@pytest.mark.parametrize("args", [["--janela"], ["--janela", "0"], ["--janela", "abc"], ["--vram"], ["rede"]])
def test_uso_errado_sai_2(args, capsys):
    assert medir_ram.main(args) == 2
    assert "uso: infra medir ram" in capsys.readouterr().err


def test_o_ato_so_le_e_nao_grava_nada(mundo, tmp_path):
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    medir_ram.medir()
    assert sorted(p.name for p in tmp_path.rglob("*")) == antes


def test_pela_linha_de_comando_o_json_sai_valido(mundo):
    p = subprocess.run([sys.executable, str(MEDIR), "--json"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    j = json.loads(p.stdout)
    assert eixos.validar(j) == [] and j["total_bytes"] != j["valor"]
