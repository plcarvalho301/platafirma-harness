"""`infra medir rede` (bin/_infra/medir-rede): os três túneis, a porta achada pelo socket do processo, a chave
de serviço dos consumidores e o código de saída (spec eixos-do-host R2 a R8; card #3919).

O cloudflared de cada túnel é um servidor HTTP em loopback que responde `/ready` e `/metrics`; o /proc é uma
árvore de mentira onde o processo da unit possui o socket em escuta daquele servidor; systemctl, docker,
`acervo` e `sinal` são scripts à frente do PATH. Nada toca o host.
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

BIN = Path(__file__).resolve().parents[2] / "bin"
MEDIR = BIN / "_infra" / "medir-rede"
SHA = "c" * 40
METRICAS = (
    "# HELP cloudflared_tunnel_ha_connections Number of active ha connections\n"
    "cloudflared_tunnel_ha_connections 4\n"
    'cloudflared_tunnel_tunnel_register_success{error="none"} 4\n'
    'cloudflared_tunnel_tunnel_register_success{error="timeout"} 2\n'
    "cloudflared_tunnel_total_requests 77\n"
)
PORTA_OK = {"estado_leitura": "lida", "causa": None, "fonte": None, "latencia_externa_ms": 183.0,
            "dur_ms_porta": 41.0, "erros_transporte": 0, "erro_verbo": None}


def _carregar():
    carregador = importlib.machinery.SourceFileLoader("medir_rede_bin", str(MEDIR))
    spec = importlib.util.spec_from_loader(carregador.name, carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


medir_rede = _carregar()
eixos = medir_rede.eixos


def _script(caminho: Path, corpo: str) -> Path:
    caminho.write_text("#!/usr/bin/env bash\n" + corpo, encoding="utf-8")
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC)
    return caminho


def _cloudflared(pronto=(200, {"status": 200, "readyConnections": 4}), metricas=METRICAS):
    """Um cloudflared de mentira: devolve (servidor, estado) e responde conforme `estado`."""
    estado = SimpleNamespace(pronto=pronto, metricas=metricas)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/ready":
                status, corpo = estado.pronto
                dados = json.dumps(corpo).encode()
            elif self.path == "/metrics":
                status, dados = 200, estado.metricas.encode()
            else:
                status, dados = 404, b""
            self.send_response(status)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    estado.srv = srv
    estado.porta = srv.server_port
    return estado


def _proc(raiz: Path, pid: int, porta_real: int, decoy: int = 9):
    """/proc de mentira: o processo possui dois sockets em escuta (a métrica e um que ninguém atende), um
    socket de outro dono e uma conexão que não está em LISTEN."""
    pasta = raiz / str(pid)
    if pasta.exists():       # a unit reiniciou: o processo refaz os sockets
        shutil.rmtree(pasta)
    (pasta / "fd").mkdir(parents=True)
    (pasta / "net").mkdir()
    for fd, inode in (("3", 9001), ("4", 9002), ("5", 9003)):
        os.symlink(f"socket:[{inode}]", pasta / "fd" / fd)

    def linha(n, porta, estado, inode):
        return (f"  {n}: 0100007F:{porta:04X} 00000000:0000 {estado} 00000000:00000000 00:00000000 "
                f"00000000  1001        0 {inode} 1 0000000000000000 100 0 0 10 0")

    (pasta / "net" / "tcp").write_text("\n".join([
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode",
        linha(0, decoy, "0A", 9002),          # em escuta, do processo, mas ninguém responde
        linha(1, porta_real, "0A", 9001),     # a métrica
        linha(2, 4000, "0A", 9999),           # em escuta, de outro processo
        linha(3, 4001, "01", 9003),           # do processo, mas conexão estabelecida, não LISTEN
    ]) + "\n", encoding="utf-8")


def _mundo(tmp_path, monkeypatch, *, ops_pid=1111, rec_pid=2222, registro=None, labels=None, porta=PORTA_OK,
           acervo_quebrado=False):
    m = SimpleNamespace()
    m.ops, m.rec, m.borda = _cloudflared(), _cloudflared(), _cloudflared()
    proc = tmp_path / "proc"
    _proc(proc, 1111, m.ops.porta)
    _proc(proc, 2222, m.rec.porta)
    contagem = tmp_path / "chamadas-da-sonda"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _script(bindir / "systemctl", f'''
case "$*" in
  *ops-tunnel.service) echo "MainPID={ops_pid}" ;;
  *recuperacao-tunnel.service) echo "MainPID={rec_pid}" ;;
  *) echo "Unit $4 could not be found." >&2; exit 1 ;;
esac
''')
    labels = labels if labels is not None else {
        "com.docker.compose.project": "platafirma-core", "com.docker.compose.service": "cloudflared",
        "com.docker.compose.project.config_files": f"/opt/platafirma/platafirma-core/{SHA}/docker-compose.yml"}
    _script(bindir / "docker", f"echo '{json.dumps(labels)}'\n")
    registro = registro if registro is not None else {
        "ops-tunnel.service": "core/ops-tunnel", "recuperacao-tunnel.service": "core/recuperacao-tunnel"}
    topologia = [{"slug": "core", "compose": "/opt/platafirma/current/core/docker-compose.yml"}]
    corpo_acervo = 'echo "acervo stack: psql falhou" >&2; exit 3\n' if acervo_quebrado else (
        'if [ "$1 $2" = "stack ver" ]; then\n'
        f"  echo '{json.dumps(topologia)}'; exit 0\nfi\n"
        'if [ "$1 $2" = "stack resolver" ]; then\n'
        + "".join(f'  [ "$3" = "{u}" ] && {{ echo "{c}"; exit 0; }}\n' for u, c in registro.items())
        + '  echo "unit_sem_stack: $3" >&2; exit 1\nfi\nexit 2\n')
    acervo = _script(bindir / "acervo", corpo_acervo)
    sinal = _script(bindir / "sinal", f'echo >> "{contagem}"\necho \'{json.dumps(porta)}\'\n')
    monkeypatch.setenv("PATH", f"{bindir}:{os.environ['PATH']}")
    monkeypatch.setenv("INFRA_PROC", str(proc))
    monkeypatch.setenv("INFRA_ACERVO", str(acervo))
    monkeypatch.setenv("INFRA_SINAL", str(sinal))
    monkeypatch.setenv("INFRA_REDE_BORDA_METRICA", f"127.0.0.1:{m.borda.porta}")
    monkeypatch.setenv("INFRA_REDE_TIMEOUT", "3")
    m.proc, m.contagem, m.bindir = proc, contagem, bindir
    return m


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    m = _mundo(tmp_path, monkeypatch)
    yield m
    for s in (m.ops, m.rec, m.borda):
        s.srv.shutdown()


def tunel(j, nome):
    return next(t for t in j["tuneis"] if t["tunel"] == nome)


# --- o que a medida traz ------------------------------------------------------------------------

def test_os_tres_tuneis_vem_lidos_com_conexoes_e_reconexoes(mundo):
    j = medir_rede.medir()
    assert j["estado_leitura"] == "lida" and j["eixo"] == "rede" and j["valor"] is None
    assert [t["tunel"] for t in j["tuneis"]] == ["ops", "recuperacao", "wiki"]
    assert all(t["estado_leitura"] == "lida" and t["causa"] is None for t in j["tuneis"])
    assert all(t["conexoes_borda"] == 4 and t["reconexoes_acumuladas"] == 6 for t in j["tuneis"])
    assert eixos.validar(j) == []


def test_a_porta_do_ops_traz_latencia_de_fora_ao_lado_do_tempo_da_porta(mundo):
    ops = tunel(medir_rede.medir(), "ops")
    assert ops["latencia_externa_ms"] == 183.0 and ops["dur_ms_porta"] == 41.0 and ops["erros_transporte"] == 0
    assert tunel(medir_rede.medir(), "wiki")["latencia_externa_ms"] is None, "a latência de fora é só do ops"


def test_a_sonda_chama_a_porta_uma_vez_por_medida(mundo):
    medir_rede.medir()
    assert mundo.contagem.read_text().count("\n") == 1


def test_porta_nao_medida_nao_derruba_o_eixo_e_nunca_vira_zero(tmp_path, monkeypatch):
    porta = {"estado_leitura": "nao_consegui_olhar", "causa": "sem_credencial_da_sonda",
             "fonte": "segredos/keycloak/sonda", "latencia_externa_ms": None, "dur_ms_porta": None,
             "erros_transporte": 0, "erro_verbo": None}
    m = _mundo(tmp_path, monkeypatch, porta=porta)
    try:
        j = medir_rede.medir()
    finally:
        for s in (m.ops, m.rec, m.borda):
            s.srv.shutdown()
    ops = tunel(j, "ops")
    assert j["estado_leitura"] == "lida" and ops["estado_leitura"] == "lida"
    assert ops["latencia_externa_ms"] is None and ops["porta_nao_lida"] == "sem_credencial_da_sonda"
    assert "porta não medida (sem_credencial_da_sonda)" in eixos.frase(j)


# --- a porta achada pelo socket do processo ------------------------------------------------------

def test_porta_trocada_por_reinicio_e_achada_de_novo(mundo):
    primeira = tunel(medir_rede.medir(), "ops")["metrica"]
    assert primeira == f"127.0.0.1:{mundo.ops.porta}"
    novo = _cloudflared()
    try:
        _proc(mundo.proc, 1111, novo.porta)     # a unit reiniciou e o cloudflared abriu a métrica em outra porta
        assert tunel(medir_rede.medir(), "ops")["metrica"] == f"127.0.0.1:{novo.porta}"
    finally:
        novo.srv.shutdown()


def test_nenhuma_porta_de_metrica_de_ops_ou_recuperacao_esta_escrita_no_codigo():
    fonte = MEDIR.read_text(encoding="utf-8")
    for porta in ("20241", "20242", "20244", "20245"):
        assert porta not in fonte


def test_socket_de_outro_processo_e_conexao_estabelecida_nao_entram(tmp_path):
    _proc(tmp_path, 7, 4242)
    assert medir_rede.portas_em_escuta(7, tmp_path) == [9, 4242]


# --- fonte muda ----------------------------------------------------------------------------------

def test_fonte_muda_sai_nao_consegui_olhar_valor_nulo_e_saida_5(mundo, capsys):
    mundo.ops.srv.shutdown()
    mundo.ops.srv.server_close()
    assert medir_rede.main(["--json"]) == 5
    j = json.loads(capsys.readouterr().out)
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["valor"] is None
    assert j["causa"] == "tunel_sem_leitura" and "ops" in j["fonte"]
    ops = tunel(j, "ops")
    assert ops["estado_leitura"] == "nao_consegui_olhar" and ops["causa"] == "metrica_fora"
    assert "conexoes_borda" not in ops, "o túnel que não leu não tem número, nunca zero"
    assert tunel(j, "wiki")["estado_leitura"] == "lida", "o que se leu dos outros fica"


def test_unit_parada_nao_consegui_olhar_com_a_causa(tmp_path, monkeypatch):
    m = _mundo(tmp_path, monkeypatch, rec_pid=0)
    try:
        j = medir_rede.medir()
    finally:
        for s in (m.ops, m.rec, m.borda):
            s.srv.shutdown()
    rec = tunel(j, "recuperacao")
    assert (rec["estado_leitura"], rec["causa"]) == ("nao_consegui_olhar", "unit_parada")
    assert eixos.codigo_de_saida(j) == 5


def test_borda_fora_do_ar_nao_consegui_olhar(mundo, capsys):
    mundo.borda.srv.shutdown()
    mundo.borda.srv.server_close()
    assert medir_rede.main(["--json"]) == 5
    assert tunel(json.loads(capsys.readouterr().out), "wiki")["causa"] == "metrica_fora"


# --- medida não reprova --------------------------------------------------------------------------

def test_valor_alto_e_zero_conexoes_lidas_saem_0(mundo, capsys):
    mundo.ops.metricas = 'cloudflared_tunnel_tunnel_register_success{error="none"} 250000\n'
    mundo.rec.pronto = (503, {"status": 503, "readyConnections": 0})
    mundo.borda.pronto = (200, {"status": 200, "readyConnections": 4})
    assert medir_rede.main(["--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert tunel(j, "ops")["reconexoes_acumuladas"] == 250000
    assert tunel(j, "recuperacao")["conexoes_borda"] == 0 and tunel(j, "recuperacao")["estado_leitura"] == "lida"


def test_porta_lenta_ou_com_erro_de_verbo_tambem_sai_0(tmp_path, monkeypatch, capsys):
    porta = {**PORTA_OK, "latencia_externa_ms": 90000.0, "erros_transporte": 1, "erro_verbo": "execucao"}
    m = _mundo(tmp_path, monkeypatch, porta=porta)
    try:
        assert medir_rede.main([]) == 0
    finally:
        for s in (m.ops, m.rec, m.borda):
            s.srv.shutdown()
    assert "90000 ms por fora" in capsys.readouterr().out


def test_contador_de_reconexao_ausente_sai_nulo_e_nunca_zero(mundo):
    mundo.ops.metricas = "cloudflared_tunnel_ha_connections 4\n"
    ops = tunel(medir_rede.medir(), "ops")
    assert ops["reconexoes_acumuladas"] is None and ops["conexoes_borda"] == 4


def test_valor_da_metrica_soma_as_series_e_devolve_none_quando_nao_existe():
    assert medir_rede.valor_da_metrica(METRICAS, medir_rede.REGISTROS_NA_BORDA) == 6
    assert medir_rede.valor_da_metrica(METRICAS, ("nao_existe",)) is None
    assert medir_rede.valor_da_metrica("cloudflared_tunnel_ha_connections_extra 9\n", medir_rede.CONEXOES_NA_BORDA) is None


# --- a chave de serviço dos consumidores ---------------------------------------------------------

def test_consumidores_resolvem_pelos_dois_caminhos(mundo):
    j = medir_rede.medir()
    por_tunel = {c["tunel"]: c for c in j["consumidores"]}
    assert por_tunel["ops"]["servico"] == "core/ops-tunnel" and por_tunel["ops"]["unit"] == "ops-tunnel.service"
    assert por_tunel["recuperacao"]["servico"] == "core/recuperacao-tunnel"
    assert por_tunel["wiki"]["servico"] == "core/cloudflared" and por_tunel["wiki"]["conteiner"].endswith("cloudflared-1")
    assert por_tunel["ops"]["pid"] == 1111


def test_unit_fora_do_registro_e_conteiner_fora_de_compose_saem_como_desvio_nunca_somem(tmp_path, monkeypatch):
    m = _mundo(tmp_path, monkeypatch, registro={"ops-tunnel.service": "core/ops-tunnel"}, labels={})
    try:
        j = medir_rede.medir()
    finally:
        for s in (m.ops, m.rec, m.borda):
            s.srv.shutdown()
    por_tunel = {c["tunel"]: c for c in j["consumidores"]}
    assert por_tunel["recuperacao"]["desvio"] == "unit_sem_stack" and "servico" not in por_tunel["recuperacao"]
    assert por_tunel["recuperacao"]["unit"] == "recuperacao-tunnel.service"
    assert por_tunel["wiki"]["desvio"] == "fora_de_compose_e_unit"
    assert j["estado_leitura"] == "lida" and eixos.validar(j) == []


def test_registro_de_stacks_fora_do_ar_nao_vira_desvio_inventado(tmp_path, monkeypatch):
    m = _mundo(tmp_path, monkeypatch, acervo_quebrado=True)
    try:
        j = medir_rede.medir()
    finally:
        for s in (m.ops, m.rec, m.borda):
            s.srv.shutdown()
    assert j["estado_leitura"] == "nao_consegui_olhar" and j["causa"] == "registro_de_stack_indisponivel"
    assert j["consumidores"] == [] and len(j["tuneis"]) == 3, "o que se leu dos túneis fica"


# --- a frase e a saída ---------------------------------------------------------------------------

def test_a_frase_impressa_e_a_funcao_unica_aplicada_ao_json(mundo, capsys):
    j = medir_rede.medir()
    assert eixos.imprimir_saida(j, como_json=False) == 0
    assert capsys.readouterr().out.strip() == eixos.frase(j)
    assert "ops com 4 conexões na borda, 6 reconexões desde a partida" in eixos.frase(j)


def test_o_ato_so_le_e_nao_grava_nada_na_instancia(mundo):
    instancia = Path(os.environ["PLATAFIRMA_INSTANCIA"])
    antes = sorted(instancia.rglob("*"))
    medir_rede.medir()
    assert sorted(instancia.rglob("*")) == antes


def test_argumento_desconhecido_sai_2(capsys):
    assert medir_rede.main(["--ram"]) == 2
    assert "não conhece --ram" in capsys.readouterr().err


def test_pela_linha_de_comando_o_json_sai_valido_e_o_codigo_acompanha(mundo):
    p = subprocess.run([sys.executable, str(MEDIR), "--json"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert eixos.validar(json.loads(p.stdout)) == []
