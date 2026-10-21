"""`infra medir vram` (bin/_infra/medir-vram): cada processo da placa na chave de serviço ou em desvio com motivo, o
reservado, o SM e a placa em campos distintos, e o código de saída (spec eixos-do-host R2, R3, R4 e R10; card #3921).

O driver é um `nvidia-smi` de mentira que responde as três consultas; o /proc é uma árvore de mentira com o cgroup,
o comm e a linha de comando de cada pid; `docker`, `acervo` ficam à frente do PATH. Nada toca o host.
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
MEDIR = BIN / "_infra" / "medir-vram"
SHA = "d" * 40
MIB = 1 << 20
ID_DO_EMBEDDER = "a" * 64
ID_DE_COMPOSE_SEM_STACK = "b" * 64
ID_SEM_LABEL = "c" * 64
ESCOPO = "0::/user.slice/user-1001.slice/user@1001.service/app.slice/{unit}"
RESERVADO = {100: 4784, 200: 1926, 300: 300, 400: 100, 500: 50, 600: 10}      # MiB, soma 7170
PLACA_USADA, PLACA_TOTAL, PLACA_SM = 7280, 16311, 12                         # MiB, MiB, %


def _carregar():
    carregador = importlib.machinery.SourceFileLoader("medir_vram_bin", str(MEDIR))
    spec = importlib.util.spec_from_loader(carregador.name, carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


medir_vram = _carregar()
eixos = medir_vram.eixos


def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


def _processo(raiz: Path, pid: int, cgroup: str, comm: str, linha: str):
    pasta = raiz / str(pid)
    pasta.mkdir(parents=True)
    (pasta / "cgroup").write_text(cgroup + "\n", encoding="utf-8")
    (pasta / "comm").write_text(comm + "\n", encoding="utf-8")
    (pasta / "cmdline").write_bytes(linha.replace(" ", "\0").encode() + b"\0")


def _mundo(tmp_path, monkeypatch, *, registro=None, acervo_quebrado=False, processos=True):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    proc = tmp_path / "proc"
    proc.mkdir()
    if processos:
        _processo(proc, 100, f"0::/user.slice/user-1001.slice/user@1001.service/app.slice/docker-{ID_DO_EMBEDDER}.scope",
                  "python", "python -m embedder --porta 8080")
        _processo(proc, 200, ESCOPO.format(unit="ops-mcp.service"), "python", "python -m ops_mcp")
        _processo(proc, 300, ESCOPO.format(unit="bench-embedder.service"), "python", "python bench.py --modelo grande")
        _processo(proc, 400, "0::/user.slice/user-1001.slice/session-3.scope", "claude", "claude -p julgar --caso 12")
        _processo(proc, 600, f"0::/user.slice/user-1001.slice/user@1001.service/app.slice/docker-{ID_SEM_LABEL}.scope",
                  "sleep", "sleep 3600")
        # o pid 500 sumiu do /proc entre o driver listar e o ato ler: não há diretório
    saida_apps = "".join(f"{pid}, {mib}\n" for pid, mib in RESERVADO.items()) if processos else ""
    pmon = ("# gpu         pid   type     sm    mem    enc    dec    jpg    ofa    command\n"
            "# Idx           #    C/G      %      %      %      %      %      %    name\n"
            "    0        100     C     12      3      -      -      -      -    python\n"
            "    0        200     C      0      0      -      -      -      -    python\n"
            "    0        300     C      -      -      -      -      -      -    python\n"
            "    0        400     C      7      1      -      -      -      -    claude\n"
            "    0        600     C      0      0      -      -      -      -    sleep\n") if processos else "# gpu\n"
    smi = _script(bindir / "nvidia-smi", f'''
case "$*" in
  *query-gpu*) [ "${{FAKE_PLACA_RC:-0}}" = 0 ] || exit 9; echo "{PLACA_USADA}, {PLACA_TOTAL}, {PLACA_SM}" ;;
  *query-compute-apps*) [ "${{FAKE_APPS_RC:-0}}" = 0 ] || exit 9; printf '%s' '{saida_apps}' ;;
  pmon*) [ "${{FAKE_PMON_RC:-0}}" = 0 ] || exit 9; printf '%s' '{pmon}' ;;
  *) exit 2 ;;
esac
''')
    labels_embedder = {"com.docker.compose.project": "platafirma-busca", "com.docker.compose.service": "embedder",
                       "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-busca/{SHA}/docker-compose.yml"}
    _script(bindir / "docker", f'''
for ultimo; do :; done
case "$ultimo" in
  {ID_DO_EMBEDDER}) printf '/platafirma-busca-embedder-1\\t%s\\n' '{json.dumps(labels_embedder)}' ;;
  {ID_SEM_LABEL}) printf '/avulso\\t%s\\n' '{{}}' ;;
  *) echo "No such object" >&2; exit 1 ;;
esac
''')
    registro = registro if registro is not None else {"ops-mcp.service": "harness/ops-mcp"}
    topologia = [{"slug": "busca", "compose": "/opt/platafirma/current/busca/docker-compose.yml"}]
    corpo_acervo = 'echo "acervo stack: psql falhou" >&2; exit 3\n' if acervo_quebrado else (
        'if [ "$1 $2" = "stack ver" ]; then\n'
        f"  echo '{json.dumps(topologia)}'; exit 0\nfi\n"
        'if [ "$1 $2" = "stack resolver" ]; then\n'
        + "".join(f'  [ "$3" = "{u}" ] && {{ echo "{c}"; exit 0; }}\n' for u, c in registro.items())
        + '  echo "unit_sem_stack: $3" >&2; exit 1\nfi\nexit 2\n')
    acervo = _script(bindir / "acervo", corpo_acervo)
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("INFRA_NVIDIA_SMI", str(smi))
    monkeypatch.setenv("INFRA_PROC", str(proc))
    monkeypatch.setenv("INFRA_ACERVO", str(acervo))
    for variavel in ("FAKE_PLACA_RC", "FAKE_APPS_RC", "FAKE_PMON_RC"):
        monkeypatch.delenv(variavel, raising=False)
    return SimpleProc(proc, smi)


class SimpleProc:
    def __init__(self, proc, smi):
        self.proc, self.smi = proc, smi


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    return _mundo(tmp_path, monkeypatch)


def por_pid(j):
    return {c["pid"]: c for c in j["consumidores"]}


# --- quem é cada processo (R4) -----------------------------------------------------------------

def test_todo_processo_da_placa_vem_com_chave_ou_com_desvio_e_nenhum_some(mundo):
    j = medir_vram.medir()
    assert j["estado_leitura"] == "lida" and j["eixo"] == "vram"
    assert sorted(por_pid(j)) == sorted(RESERVADO), "o driver listou seis processos e os seis aparecem"
    for c in j["consumidores"]:
        assert (c.get("servico") is None) != (c.get("desvio") is None), c
    assert eixos.validar(j) == []


def test_conteiner_e_unit_resolvem_pelos_dois_caminhos_do_registro(mundo):
    c = por_pid(medir_vram.medir())
    assert c[100]["servico"] == "busca/embedder" and c[100]["conteiner"] == "platafirma-busca-embedder-1"
    assert c[200]["servico"] == "harness/ops-mcp" and c[200]["unit"] == "ops-mcp.service"


def test_o_que_nao_resolve_sai_como_desvio_com_o_motivo_e_nunca_vira_a_unit_de_quem_disparou(mundo):
    c = por_pid(medir_vram.medir())
    assert c[300]["desvio"] == "unit_sem_stack" and c[300]["unit"] == "bench-embedder.service"
    assert c[400]["desvio"] == "fora_de_compose_e_unit"
    assert c[500]["desvio"] == "fora_de_compose_e_unit" and c[500]["detalhe"] == "cgroup_ilegivel"
    assert c[600]["desvio"] == "fora_de_compose_e_unit" and c[600]["conteiner"] == "avulso"
    assert all("servico" not in c[pid] for pid in (300, 400, 500, 600))


def test_pid_e_linha_de_comando_vao_ao_json_e_a_frase(mundo):
    j = medir_vram.medir()
    assert por_pid(j)[400]["linha_de_comando"] == "claude -p julgar --caso 12"
    frase = eixos.frase(j)
    assert "pid 400" in frase and "claude -p julgar --caso 12" in frase


# --- os números, cada um no seu campo (R10) -----------------------------------------------------

def test_placa_reservado_e_sm_ficam_em_campos_distintos(mundo):
    j = medir_vram.medir()
    assert (j["valor"], j["unidade"]) == (PLACA_USADA * MIB, "bytes")
    assert j["teto"] == PLACA_TOTAL * MIB and "memory.total" in j["teto_fonte"]
    assert j["sm_placa_fracao"] == pytest.approx(0.12)
    c = por_pid(j)
    assert c[100]["reservado_bytes"] == 4784 * MIB and c[100]["sm_fracao"] == pytest.approx(0.12)
    assert c[200]["reservado_bytes"] == 1926 * MIB and c[200]["sm_fracao"] == 0.0, "SM lido e parado é zero medido"


def test_sem_amostra_o_sm_do_processo_e_nulo_e_nunca_zero(mundo):
    c = por_pid(medir_vram.medir())
    assert c[300]["sm_fracao"] is None, "o pmon mostrou `-`"
    assert c[500]["sm_fracao"] is None, "o pmon não listou o processo"


def test_a_soma_dos_processos_nao_e_o_total_da_placa_e_nao_se_rotula_como_tal(mundo):
    j = medir_vram.medir()
    soma = sum(c["reservado_bytes"] for c in j["consumidores"])
    assert soma == 7170 * MIB and soma != j["valor"], "a placa segura memória que nenhum processo reclama"
    assert not [k for k in j if k.startswith(("soma", "total"))]
    assert not [k for c in j["consumidores"] for k in c if k.startswith(("soma", "total"))]


def test_o_schema_recusa_soma_rotulada_como_total_e_consumidor_sem_reservado(mundo):
    j = medir_vram.medir()
    assert eixos.validar({**j, "total_dos_processos": 7170}) != []
    sem_reservado = [{k: v for k, v in c.items() if k != "reservado_bytes"} for c in j["consumidores"]]
    assert any("reservado_bytes" in e for e in eixos.validar({**j, "consumidores": sem_reservado}))
    sm_zero_em_vez_de_nulo = [{**c, "sm_fracao": 1.5} for c in j["consumidores"]]
    assert any("sm_fracao" in e for e in eixos.validar({**j, "consumidores": sm_zero_em_vez_de_nulo}))


def test_a_frase_traz_a_placa_o_teto_e_o_reservado_e_o_sm_de_cada_um(mundo):
    frase = eixos.frase(medir_vram.medir())
    assert "VRAM às" in frase and "7,1 GiB de 15,9 GiB" in frase and "SM da placa 12%" in frase
    assert "busca/embedder (4,7 GiB reservados, SM 12%)" in frase
    assert "(300 MiB reservados, SM sem amostra)" in frase


# --- fonte muda (R3) ---------------------------------------------------------------------------

@pytest.mark.parametrize("variavel", ["FAKE_PLACA_RC", "FAKE_APPS_RC"])
def test_driver_que_falha_sai_nao_consegui_olhar_valor_nulo_e_saida_5(mundo, monkeypatch, capsys, variavel):
    monkeypatch.setenv(variavel, "1")
    assert medir_vram.main(["--json"]) == 5
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["valor"] is None and j["causa"] == "driver_fora"
    assert j["consumidores"] == [], "sem a lista de processos não se afirma que ninguém consome"
    assert eixos.validar(j) == []


def test_nvidia_smi_ausente_sai_5_com_a_fonte(mundo, monkeypatch, capsys):
    monkeypatch.setenv("INFRA_NVIDIA_SMI", str(mundo.proc / "nao-existe"))
    assert medir_vram.main([]) == 5
    assert "não consegui olhar" in capsys.readouterr().out


def test_pmon_fora_do_ar_deixa_o_sm_nulo_com_a_causa_e_o_ato_segue_0(mundo, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_PMON_RC", "1")
    assert medir_vram.main(["--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "lida" and j["sm_causa"] == "pmon_fora"
    assert all(c["sm_fracao"] is None for c in j["consumidores"])
    assert eixos.validar(j) == []


def test_registro_de_stacks_fora_do_ar_nao_vira_desvio_inventado(tmp_path, monkeypatch):
    _mundo(tmp_path, monkeypatch, acervo_quebrado=True)
    j = medir_vram.medir()
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["causa"] == "registro_de_stack_indisponivel"
    assert j["valor"] is None and j["consumidores"] == []


# --- medida não reprova -------------------------------------------------------------------------

def test_placa_sem_processo_e_placa_cheia_leem_e_saem_0(tmp_path, monkeypatch, capsys):
    _mundo(tmp_path, monkeypatch, processos=False)
    assert medir_vram.main(["--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["consumidores"] == [] and j["valor"] == PLACA_USADA * MIB and eixos.validar(j) == []


def test_argumento_desconhecido_sai_2(capsys):
    assert medir_vram.main(["--ram"]) == 2
    assert "não conhece --ram" in capsys.readouterr().err


def test_a_frase_impressa_e_a_funcao_unica_aplicada_ao_json(mundo, capsys):
    j = medir_vram.medir()
    assert eixos.imprimir_saida(j, como_json=False) == 0
    assert capsys.readouterr().out.strip() == eixos.frase(j)


def test_pela_linha_de_comando_o_json_sai_valido_e_o_codigo_acompanha(mundo):
    p = subprocess.run([sys.executable, str(MEDIR), "--json"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert eixos.validar(json.loads(p.stdout)) == []
