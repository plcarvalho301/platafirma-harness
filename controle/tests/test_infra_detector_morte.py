"""`detector-morte` (bin/_infra/detector-morte): a morte por limite de memória no instante do kernel, um evento por morte
(spec eixos-do-host R4 e R9; spec banco-de-eventos-de-plataforma R5 e R6; card #3922).

O journal do kernel, o do usuário, o docker e o registro de stacks são scripts à frente do PATH; nada toca o host. O que
se prova: a mesma morte vista pelo kernel, pelo docker e pelo journal é UM evento, com o uuid de (boot, pid, instante); a
morte que o kernel não registrou não ganha pid e não vira evento; o kernel sem permissão sai `nao_consegui_olhar`, nunca
«nenhuma morte»; e o evento só leva campo da ficha, sem linha de comando.
"""
import importlib.machinery
import importlib.util
import json
import os
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[2] / "bin"
DETECTOR = BIN / "_infra" / "detector-morte"
sys.path.insert(0, str(BIN / "_metrica"))
sys.path.insert(0, str(BIN / "_infra"))
import eventos  # noqa: E402

BOOT = "0a1b2c3d-4e5f-6071-8293-a4b5c6d7e8f9"
ID_KEYCLOAK = "b" * 64
SHA = "c" * 40
GIB_KB = 1 << 20
# 17:46:40.123 UTC de 14/10/2026, o instante do kernel
EPOCH = 1792000000
INSTANTE_US = EPOCH * 1_000_000 + 123_000
AGORA = datetime(2026, 10, 14, 17, 47, 0, tzinfo=timezone.utc)
LABELS_KEYCLOAK = {
    "com.docker.compose.project": "platafirma-core", "com.docker.compose.service": "keycloak",
    "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml"}
TOPOLOGIA = [{"slug": "core", "compose": "/opt/platafirma/current/core/docker-compose.yml"}]
CGROUP_KEYCLOAK = f"/user.slice/user-1001.slice/user@1001.service/user.slice/docker-{ID_KEYCLOAK}.scope"
CGROUP_TUNEL = "/user.slice/user-1001.slice/user@1001.service/app.slice/ops-tunnel.service"
CGROUP_SESSAO = "/user.slice/user-1001.slice/session-3.scope"
FICHA_MORTE = {"evento_id", "ts", "instancia", "instrumento", "schema_v", "estado_leitura", "causa", "fonte", "boot_id",
               "pid", "servico", "desvio", "conteiner", "executavel", "escopo", "limite_bytes", "uso_bytes",
               "detectado_em"}


def _carregar():
    carregador = importlib.machinery.SourceFileLoader("detector_morte_bin", str(DETECTOR))
    spec = importlib.util.spec_from_loader(carregador.name, carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


detector = _carregar()


def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


def _k(mensagem, instante_us=INSTANTE_US, boot=BOOT):
    return {"MESSAGE": mensagem, "__REALTIME_TIMESTAMP": str(instante_us), "_BOOT_ID": boot.replace("-", ""),
            "SYSLOG_IDENTIFIER": "kernel", "_TRANSPORT": "kernel"}


def morte_do_kernel(pid=4242, comm="java", cgroup=CGROUP_KEYCLOAK, constraint="CONSTRAINT_MEMCG", instante_us=INSTANTE_US,
                    limite_kb=GIB_KB, anon_kb=2 * GIB_KB, boot=BOOT):
    """As três linhas que o kernel escreve numa morte por limite, no instante dado."""
    oom = (f"oom-kill:constraint={constraint},nodemask=(null),cpuset=/,mems_allowed=0,oom_memcg={cgroup},"
           f"task_memcg={cgroup},task={comm},pid={pid},uid=1001")
    quem = "Memory cgroup out of memory" if constraint == "CONSTRAINT_MEMCG" else "Out of memory"
    morto = (f"{quem}: Killed process {pid} ({comm}) total-vm:9999999kB, anon-rss:{anon_kb}kB, file-rss:1024kB, "
             f"shmem-rss:0kB, UID:1001 pgtables:5000kB oom_score_adj:0")
    linhas = []
    if constraint == "CONSTRAINT_MEMCG":
        linhas.append(_k(f"memory: usage {limite_kb}kB, limit {limite_kb}kB, failcnt 3", instante_us - 1000, boot))
    return linhas + [_k(oom, instante_us, boot), _k(morto, instante_us + 1000, boot)]


def oom_do_docker(id_conteiner=ID_KEYCLOAK, nome="platafirma-core-keycloak-1", labels=None, segundos=EPOCH):
    return {"status": "oom", "Type": "container", "Action": "oom", "time": segundos,
            "timeNano": segundos * 1_000_000_000 + 100_000_000,
            "Actor": {"ID": id_conteiner, "Attributes": {**(LABELS_KEYCLOAK if labels is None else labels), "name": nome}}}


def do_journal(unit, segundos=EPOCH):
    return [{"MESSAGE": f"{unit}: A process of this unit has been killed by the OOM killer.", "USER_UNIT": unit,
             "__REALTIME_TIMESTAMP": str((segundos + 0) * 1_000_000)},
            {"MESSAGE": f"{unit}: Failed with result 'oom-kill'.", "USER_UNIT": unit,
             "__REALTIME_TIMESTAMP": str((segundos + 2) * 1_000_000)}]


def _mundo(tmp_path, monkeypatch, *, kernel=(), docker_eventos=(), journal=(), kernel_estado="ok",
           docker_events_ok=True, conteiner_existe=True, registro_ok=True, journal_do_usuario_ok=True):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    arquivos = {}
    for nome, linhas in (("kernel", kernel), ("docker", docker_eventos), ("usuario", journal)):
        arquivos[nome] = tmp_path / f"{nome}.jsonl"
        arquivos[nome].write_text("".join(json.dumps(e) + "\n" for e in linhas), encoding="utf-8")
    kernel_corpo = {
        "ok": f'cat "{arquivos["kernel"]}"\n',
        "sem_permissao": 'echo "No journal files were opened due to insufficient permissions." >&2\nexit 0\n',
        "falhou": 'echo "falhou" >&2\nexit 1\n',
    }[kernel_estado]
    usuario_corpo = f'cat "{arquivos["usuario"]}"\n' if journal_do_usuario_ok else 'echo "sem bus" >&2\nexit 1\n'
    _script(bindir / "journalctl", f'''
for a in "$@"; do
  case "$a" in
    -k) {kernel_corpo.strip().replace(chr(10), "; ")}; exit $? ;;
    --user) {usuario_corpo.strip().replace(chr(10), "; ")}; exit $? ;;
  esac
done
exit 2
''')
    inspecao = (f"printf '%s\\t%s\\n' \"/platafirma-core-keycloak-1\" '{json.dumps(LABELS_KEYCLOAK)}'" if conteiner_existe
                else 'echo "Error: No such object" >&2; exit 1')
    eventos_docker = f'cat "{arquivos["docker"]}"' if docker_events_ok else 'echo "Cannot connect to the Docker daemon" >&2; exit 1'
    _script(bindir / "docker", f'''
case "$1" in
  inspect) {inspecao} ;;
  events) {eventos_docker} ;;
  *) exit 2 ;;
esac
''')
    registro = {"ops-tunnel.service": "core/ops-tunnel"}
    corpo_acervo = 'echo "acervo stack: psql falhou" >&2; exit 3\n' if not registro_ok else (
        'if [ "$1 $2" = "stack ver" ]; then\n'
        f"  echo '{json.dumps(TOPOLOGIA)}'; exit 0\nfi\n"
        'if [ "$1 $2" = "stack resolver" ]; then\n'
        + "".join(f'  [ "$3" = "{u}" ] && {{ echo "{c}"; exit 0; }}\n' for u, c in registro.items())
        + '  echo "unit_sem_stack: $3" >&2; exit 1\nfi\nexit 2\n')
    acervo = _script(bindir / "acervo", corpo_acervo)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("INFRA_ACERVO", str(acervo))
    monkeypatch.setenv("SINAL_INSTANCIA", "host-1")


def detectar(**kw):
    return detector.detectar(EPOCH - 300, EPOCH + 60, agora=AGORA)


# --- a mesma morte vista três vezes é uma ----------------------------------------------------------------

def test_a_mesma_morte_vista_pelo_kernel_pelo_docker_e_pelo_journal_vira_um_evento_so(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()],
           journal=do_journal(f"docker-{ID_KEYCLOAK}.scope"))
    r = detectar()
    assert r["estado_leitura"] == "lida" and len(r["mortes"]) == 1
    assert r["vistas_sem_pid"] == [], "as três fontes são a mesma morte: nenhuma sobra"
    esperado = str(uuid.uuid5(eventos.NAMESPACE, f"morte_limite|{BOOT}|4242|2026-10-14T17:46:40.123Z"))
    assert r["mortes"][0]["evento_id"] == esperado


def test_o_evento_da_morte_leva_a_identidade_do_kernel_e_a_chave_do_servico(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()])
    e = detectar()["mortes"][0]
    assert (e["boot_id"], e["pid"], e["ts"]) == (BOOT, 4242, "2026-10-14T17:46:40.123Z"), "o instante do kernel"
    assert e["servico"] == "core/keycloak" and e["conteiner"] == "platafirma-core-keycloak-1" and "desvio" not in e
    assert (e["executavel"], e["escopo"]) == ("java", "cgroup")
    assert e["limite_bytes"] == GIB_KB * 1024 and e["uso_bytes"] == (2 * GIB_KB + 1024) * 1024
    assert (e["instancia"], e["instrumento"], e["schema_v"], e["estado_leitura"]) == ("host-1", "detector-morte", 1, "lida")
    assert e["detectado_em"] == "2026-10-14T17:47:00.000Z", "quando o detector viu, não o instante do kernel"


def test_a_morte_de_unit_sem_o_docker_leva_a_chave_do_registro_e_conta_uma_vez(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(pid=500, comm="cloudflared", cgroup=CGROUP_TUNEL),
           journal=do_journal("ops-tunnel.service"))
    r = detectar()
    assert len(r["mortes"]) == 1 and r["vistas_sem_pid"] == [], "a morte e a falha por oom-kill são a mesma morte"
    assert r["mortes"][0]["servico"] == "core/ops-tunnel" and "conteiner" not in r["mortes"][0]


def test_o_evento_so_leva_campo_da_ficha_e_nunca_a_linha_de_comando(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()])
    e = detectar()["mortes"][0]
    assert set(e) <= FICHA_MORTE and {"evento_id", "ts", "instancia", "instrumento", "schema_v", "estado_leitura", "boot_id",
                                      "pid", "escopo", "detectado_em"} <= set(e)
    assert "linha_de_comando" not in e and "cmdline" not in e and "unit" not in e


def test_a_mesma_morte_lida_duas_vezes_tem_o_mesmo_id_e_a_mesma_forma(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()])
    primeiro, segundo = detectar()["mortes"][0], detectar()["mortes"][0]
    assert primeiro == segundo


def test_duas_mortes_no_mesmo_instante_com_pids_diferentes_sao_dois_eventos(tmp_path, monkeypatch):
    kernel = morte_do_kernel(pid=4242) + morte_do_kernel(pid=4243, comm="python3", cgroup=CGROUP_SESSAO)
    _mundo(tmp_path, monkeypatch, kernel=kernel, docker_eventos=[oom_do_docker()])
    mortes = detectar()["mortes"]
    assert sorted(m["pid"] for m in mortes) == [4242, 4243] and len({m["evento_id"] for m in mortes}) == 2


def test_o_uuid_do_boot_vem_do_journal_com_traco(tmp_path, monkeypatch):
    outro = "ffffffff-0000-1111-2222-333333333333"
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(boot=outro))
    assert detectar()["mortes"][0]["boot_id"] == outro


# --- sem linha do kernel, sem pid, sem evento -------------------------------------------------------------

def test_morte_vista_so_pelo_docker_nao_ganha_pid_e_nao_vira_evento(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=[], docker_eventos=[oom_do_docker()])
    r = detectar()
    assert r["estado_leitura"] == "lida" and r["mortes"] == []
    assert r["vistas_sem_pid"] == [{"fonte": "docker_events", "conteiner": "platafirma-core-keycloak-1",
                                    "ts": "2026-10-14T17:46:40.100Z"}]


def test_morte_vista_so_pelo_journal_do_usuario_nao_ganha_pid_e_nao_vira_evento(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=[], journal=do_journal("ops-tunnel.service"))
    r = detectar()
    assert r["mortes"] == [] and [v["fonte"] for v in r["vistas_sem_pid"]] == ["journal", "journal"]
    assert all(v["unit"] == "ops-tunnel.service" for v in r["vistas_sem_pid"])


def test_a_morte_que_o_kernel_registrou_nao_esconde_a_vista_de_outro_servico(tmp_path, monkeypatch):
    outro = oom_do_docker(id_conteiner="d" * 64, nome="kind_gould", labels={})
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker(), outro])
    r = detectar()
    assert len(r["mortes"]) == 1 and [v["conteiner"] for v in r["vistas_sem_pid"]] == ["kind_gould"]


def test_janela_sem_morte_e_resposta_lida_e_nao_ausencia(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch)
    r = detectar()
    assert (r["estado_leitura"], r["causa"], r["mortes"], r["vistas_sem_pid"]) == ("lida", None, [], [])


# --- fonte muda: nunca zero ------------------------------------------------------------------------------

def test_kernel_sem_permissao_nao_vira_zero_morte(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel_estado="sem_permissao", docker_eventos=[oom_do_docker()])
    r = detectar()
    assert (r["estado_leitura"], r["causa"], r["fonte"]) == ("nao_consegui_olhar", "kernel_sem_permissao", "journalctl -k")
    assert r["mortes"] == []


def test_o_journal_do_kernel_nao_se_le_com_o_aviso_calado(tmp_path, monkeypatch):
    """Sem `-q`: o aviso de falta de permissão é o que separa uma janela sem morte de uma leitura que não leu."""
    chamadas = []
    original = detector._journalctl

    def espia(argumentos, fonte):
        chamadas.append(argumentos)
        return original(argumentos, fonte)

    _mundo(tmp_path, monkeypatch)
    monkeypatch.setattr(detector, "_journalctl", espia)
    detectar()
    do_kernel = next(a for a in chamadas if "-k" in a)
    assert "-q" not in do_kernel and "--quiet" not in do_kernel


def test_kernel_que_falhou_nao_vira_zero_morte(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel_estado="falhou")
    r = detectar()
    assert (r["estado_leitura"], r["causa"]) == ("nao_consegui_olhar", "kernel_sem_leitura")


def test_registro_de_stacks_fora_do_ar_nao_vira_desvio_inventado_e_a_janela_volta(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()], registro_ok=False)
    r = detectar()
    assert (r["estado_leitura"], r["causa"]) == ("nao_consegui_olhar", "registro_de_stack_indisponivel")
    assert r["mortes"] == []


def test_docker_events_fora_e_aviso_e_a_morte_do_kernel_sai_do_mesmo_jeito(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_events_ok=False)
    r = detectar()
    assert r["estado_leitura"] == "lida" and len(r["mortes"]) == 1
    assert r["avisos"] == ["docker events: docker_events_fora"]
    assert r["mortes"][0]["servico"] == "core/keycloak", "o contêiner se resolve pelo docker inspect"


def test_journal_do_usuario_fora_e_aviso_e_nao_derruba_a_morte_do_kernel(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), journal_do_usuario_ok=False)
    r = detectar()
    assert r["estado_leitura"] == "lida" and len(r["mortes"]) == 1
    assert r["avisos"] == ["journalctl --user: journal_do_usuario_fora"]


# --- o que não tem dono ---------------------------------------------------------------------------------

def test_processo_fora_de_compose_e_de_unit_sai_como_desvio_com_o_executavel_sem_espaco(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(pid=900, comm="Web Content", cgroup=CGROUP_SESSAO))
    e = detectar()["mortes"][0]
    assert e["desvio"] == "fora_de_compose_e_unit" and "servico" not in e
    assert e["executavel"] == "Web_Content" and "conteiner" not in e


def test_unit_fora_do_registro_sai_como_unit_sem_stack(tmp_path, monkeypatch):
    cgroup = "/user.slice/user-1001.slice/user@1001.service/app.slice/xdg-desktop-portal.service"
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(pid=901, comm="xdg-portal", cgroup=cgroup))
    e = detectar()["mortes"][0]
    assert e["desvio"] == "unit_sem_stack" and "servico" not in e


def test_conteiner_que_ja_saiu_sem_o_evento_do_docker_sai_como_desvio(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), conteiner_existe=False)
    e = detectar()["mortes"][0]
    assert e["desvio"] == "fora_de_compose_e_unit" and "servico" not in e


def test_oom_global_leva_escopo_global_e_nenhum_limite(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(pid=902, comm="python3", cgroup=CGROUP_SESSAO,
                                                        constraint="CONSTRAINT_NONE"))
    e = detectar()["mortes"][0]
    assert e["escopo"] == "global" and "limite_bytes" not in e and e["uso_bytes"] > 0


def test_kernel_sem_a_linha_oom_kill_ainda_acha_o_pid_pela_linha_killed_process(tmp_path, monkeypatch):
    so_a_morte = [m for m in morte_do_kernel() if m["MESSAGE"].startswith("Memory cgroup out of memory")]
    _mundo(tmp_path, monkeypatch, kernel=so_a_morte)
    e = detectar()["mortes"][0]
    assert e["pid"] == 4242 and e["escopo"] == "cgroup" and e["desvio"] == "fora_de_compose_e_unit"


def test_linha_de_outra_coisa_no_kernel_nao_vira_morte(tmp_path, monkeypatch):
    ruido = [_k("usb 1-1: new high-speed USB device number 2"), _k("EXT4-fs (sda1): re-mounted"),
             {"MESSAGE": [1, 2, 3], "__REALTIME_TIMESTAMP": str(INSTANTE_US)}]
    _mundo(tmp_path, monkeypatch, kernel=ruido)
    assert detectar()["mortes"] == []


# --- a linha de comando ---------------------------------------------------------------------------------

def test_pela_linha_de_comando_o_json_sai_valido_com_exit_0(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()])
    assert detector.main(["--json", "--desde", str(EPOCH - 300), "--ate", str(EPOCH + 60)]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "lida" and len(j["mortes"]) == 1 and j["desde"] == EPOCH - 300


def test_nao_consegui_olhar_sai_5_com_o_json(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, kernel_estado="sem_permissao")
    assert detector.main(["--json", "--desde", str(EPOCH - 300), "--ate", str(EPOCH + 60)]) == 5
    assert json.loads(capsys.readouterr().out)["causa"] == "kernel_sem_permissao"


@pytest.mark.parametrize("args", [["--desde"], ["--desde", "abc"], ["--ate", "-1"], ["--vram"], ["x"],
                                  ["--desde", "100", "--ate", "100"]])
def test_uso_errado_sai_2(args, capsys):
    assert detector.main(args) == 2
    assert "uso: detector-morte" in capsys.readouterr().err


def test_a_janela_nunca_passa_de_um_dia(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch)
    ate = EPOCH + 60
    detector.main(["--json", "--desde", "1", "--ate", str(ate)])
    assert json.loads(capsys.readouterr().out)["desde"] == ate - detector.JANELA_MAXIMA_S


def test_o_ato_so_le_e_nao_grava_nada(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, kernel=morte_do_kernel(), docker_eventos=[oom_do_docker()])
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    detectar()
    assert sorted(p.name for p in tmp_path.rglob("*")) == antes
