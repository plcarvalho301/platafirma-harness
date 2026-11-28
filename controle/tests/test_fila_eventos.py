"""Testes de contrato de `fila enviar componente:eventos` (#4463)."""
from __future__ import annotations

import http.server
import json
import os
import re
import socket
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN_FILA = str(RAIZ / "bin" / "fila")
NAMESPACE_NEGOCIO = uuid.UUID("18e2a69a-4215-516c-8ee6-18dd0f185f62")
RE_ORIGEM = re.compile(r"^fila:(\d{8}T\d{6}Z)-([a-z0-9_-]+)-[0-9a-f]{8}$")


class _MalhaEspia:
    """Socket TCP falso na porta da malha para provar que `componente:eventos` nunca conecta ao Valkey."""

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(5)
        self._sock.settimeout(0.1)
        self.conexoes = 0
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._parar.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            self.conexoes += 1
            try:
                conn.close()
            except OSError:
                pass

    def fechar(self):
        self._parar.set()
        self._thread.join(timeout=1.0)
        try:
            self._sock.close()
        except OSError:
            pass


class _EventosStub:
    """Servidor HTTP falso que imita POST /eventos/mensagem."""

    def __init__(self, handler_fn=None):
        self.chamadas: list[dict] = []
        self._handler_fn = handler_fn or self._padrao
        stub = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                tam = int(self.headers.get("Content-Length", "0"))
                bruto = self.rfile.read(tam).decode("utf-8") if tam else "{}"
                dado = json.loads(bruto)
                stub.chamadas.append({
                    "path": self.path,
                    "auth": self.headers.get("Authorization"),
                    "body": dado,
                })
                status, resp = stub._handler_fn(dado, len(stub.chamadas))
                corpo = json.dumps(resp, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, format, *args):
                return

        self._srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.url = f"http://127.0.0.1:{self._srv.server_address[1]}"
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()

    @staticmethod
    def _padrao(dado: dict, _n: int) -> tuple[int, dict]:
        ids = [ev["evento_id"] for ev in dado.get("eventos", [])]
        return 200, {"inseridos": ids, "existentes": []}

    def fechar(self):
        self._srv.shutdown()
        self._srv.server_close()


@dataclass
class _Ambiente:
    casa: Path
    malha_port: int
    eventos_url: str | None = None
    credencial: str | None = None
    cadeira: str | None = "engenharia"
    sessao: str | None = "sessao-4463"
    stdin: str | None = None


def _credencial_fixture() -> str:
    return f"fixture-4463-{os.getpid()}"


@pytest.fixture()
def casa_fake(tmp_path: Path) -> Path:
    personas = tmp_path / "instancias" / "persona"
    personas.mkdir(parents=True)
    for slug in ("dados", "engenharia", "conhecimento", "produto"):
        (personas / f"{slug}.md").write_text(f"# {slug}\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def malha_espia():
    m = _MalhaEspia()
    try:
        yield m
    finally:
        m.fechar()


def _rodar(args: list[str], amb: _Ambiente) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PF_CASA_RAIZ": str(amb.casa),
        "FILA_REDIS_HOST": "127.0.0.1",
        "FILA_REDIS_PORT": str(amb.malha_port),
        "PLATAFIRMA_INSTANCIA": str(amb.casa / "instancia-vazia"),
    }
    if amb.eventos_url is not None:
        env["EVENTOS_API_URL"] = amb.eventos_url
    if amb.credencial is not None:
        env["EVENTOS_NEGOCIO_TOKEN"] = amb.credencial
    if amb.cadeira is not None:
        env["PF_CADEIRA"] = amb.cadeira
    if amb.sessao is not None:
        env["PF_SESSAO"] = amb.sessao
    return subprocess.run(
        [sys.executable, BIN_FILA, *args],
        input=amb.stdin,
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
        check=False,
    )


def test_envio_valido_completo_deduplica_e_nao_toca_malha(casa_fake, malha_espia):
    cred = _credencial_fixture()
    stub = _EventosStub()
    try:
        res = _rodar(
            [
                "enviar",
                "componente:eventos",
                "--tipo", "afirmacao",
                "--assunto", "Mapa da teia",
                "--ref", "card:4463",
                "--etiqueta", "capacidade:mensageria",
                "--etiqueta", "card:4463",
                "--etiqueta", "capacidade:mensageria",
                "--apoio", "card:4463",
                "--apoio", "obra:clark2014",
                "--apoio", "card:4463",
                "--cita", "Clark et al. 2014",
                "--responde", "fila:20261128T100000Z-dados-deadbeef",
                "--relacao", "atualiza",
                "--corpo", "Texto estruturado do enunciado.",
            ],
            _Ambiente(casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=cred),
        )
    finally:
        stub.fechar()

    assert res.returncode == 0, res.stderr
    assert malha_espia.conexoes == 0
    origem = res.stdout.strip()
    m = RE_ORIGEM.fullmatch(origem)
    assert m is not None, f"origem fora do formato: {origem!r}"
    assert m.group(2) == "engenharia"

    assert len(stub.chamadas) == 1
    chamada = stub.chamadas[0]
    assert chamada["path"] == "/eventos/mensagem"
    assert chamada["auth"] == f"Bearer {cred}"
    ev = chamada["body"]["eventos"][0]
    assert ev["produtor"] == "harness:fila"
    assert ev["origem"] == origem
    assert ev["evento_id"] == str(uuid.uuid5(NAMESPACE_NEGOCIO, f"mensagem|{origem}"))
    carimbo = m.group(1)
    ts_esperado = f"{carimbo[:4]}-{carimbo[4:6]}-{carimbo[6:8]}T{carimbo[9:11]}:{carimbo[11:13]}:{carimbo[13:15]}Z"
    assert ev["ts"] == ts_esperado
    assert ev["quem"] == "engenharia"
    assert ev["correlacao"] == "sessao-4463"
    assert ev["destinatarios"] == ["componente:eventos"]
    assert ev["tipo_de_mensagem"] == "afirmacao"
    assert ev["enunciado"] == "Mapa da teia\n\nTexto estruturado do enunciado."
    assert ev["sobre"] == "card:4463"
    assert "payload" not in ev
    assert ev["etiquetas"] == ["capacidade:mensageria", "card:4463"]
    assert ev["apoios"] == ["card:4463", "obra:clark2014"]
    assert ev["cita"] == "Clark et al. 2014"
    assert ev["responde_a"] == "fila:20261128T100000Z-dados-deadbeef"
    assert ev["relacao_com_a_anterior"] == "atualiza"


def test_reenvio_ja_existente_sai_zero(casa_fake, malha_espia):
    stub = _EventosStub(
        handler_fn=lambda dado, _n: (200, {"inseridos": [], "existentes": [dado["eventos"][0]["evento_id"]]})
    )
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--corpo", "Mesmo fato reenviado."],
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 0, res.stderr
    assert RE_ORIGEM.fullmatch(res.stdout.strip())
    assert malha_espia.conexoes == 0


@pytest.mark.parametrize(
    ("args_tipo", "tipo_esperado"),
    [
        ([], "afirmacao"),
        (["--tipo", "afirmacao"], "afirmacao"),
        (["--tipo", "negativa"], "negativa"),
        (["--tipo", "pedido"], "pedido"),
        (["--tipo", "recusa"], "recusa"),
        (["--tipo", "decisao"], "decisao"),
        (["--tipo", "contestacao", "--ref", "card:4463"], "contestacao"),
        (["--tipo", "contestacao", "--responde", "fila:20261128T100000Z-dados-11223344"], "contestacao"),
        (["--tipo", "resposta"], "afirmacao"),
        (["--tipo", "minuta"], "afirmacao"),
        (["--tipo", "handoff"], "afirmacao"),
        (["--tipo", "demanda"], "pedido"),
    ],
)
def test_mapeamento_de_tipos_e_padrao(casa_fake, malha_espia, args_tipo, tipo_esperado):
    stub = _EventosStub()
    try:
        cmd = ["enviar", "componente:eventos", *args_tipo, "--corpo", "Corpo do teste."]
        res = _rodar(
            cmd,
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 0, res.stderr
    assert stub.chamadas[0]["body"]["eventos"][0]["tipo_de_mensagem"] == tipo_esperado
    assert malha_espia.conexoes == 0


def test_enunciado_sem_assunto_corpo_posicional_e_stdin(casa_fake, malha_espia):
    stub = _EventosStub()
    cred = _credencial_fixture()
    try:
        res_pos = _rodar(
            ["enviar", "componente:eventos", "Primeira linha.\nSegunda linha."],
            _Ambiente(casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=cred),
        )
        res_stdin = _rodar(
            ["enviar", "componente:eventos"],
            _Ambiente(
                casa=casa_fake,
                malha_port=malha_espia.port,
                eventos_url=stub.url,
                credencial=cred,
                stdin="Vindo do stdin.\n",
            ),
        )
    finally:
        stub.fechar()

    assert res_pos.returncode == 0, res_pos.stderr
    assert res_stdin.returncode == 0, res_stdin.stderr
    assert stub.chamadas[0]["body"]["eventos"][0]["enunciado"] == "Primeira linha.\nSegunda linha."
    assert stub.chamadas[1]["body"]["eventos"][0]["enunciado"] == "Vindo do stdin."
    assert malha_espia.conexoes == 0


@pytest.mark.parametrize(
    ("args_ref", "sobre_esp"),
    [
        (["--ref", "capacidade:busca"], "capacidade:busca"),
        (["--ref", "dados"], "dados"),
        ([], "componente:eventos"),
    ],
)
def test_ref_como_chave_e_ausente_sem_payload(casa_fake, malha_espia, args_ref, sobre_esp):
    stub = _EventosStub()
    try:
        res = _rodar(
            ["enviar", "componente:eventos", *args_ref, "--corpo", "Teste de ref."],
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 0, res.stderr
    ev = stub.chamadas[0]["body"]["eventos"][0]
    assert ev["sobre"] == sobre_esp
    assert "payload" not in ev
    assert malha_espia.conexoes == 0


def test_ref_fora_de_chave_vai_no_payload(casa_fake, malha_espia):
    stub = _EventosStub()
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--ref", "#4463", "--corpo", "Teste de ref livre."],
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 0, res.stderr
    ev = stub.chamadas[0]["body"]["eventos"][0]
    assert ev["sobre"] == "componente:eventos"
    assert ev["payload"] == {"ref": "#4463"}
    assert malha_espia.conexoes == 0


def test_envio_para_cadeira_conecta_a_malha(casa_fake, malha_espia):
    res = _rodar(
        ["enviar", "dados", "--corpo", "Carta normal para cadeira."],
        _Ambiente(casa=casa_fake, malha_port=malha_espia.port, credencial=_credencial_fixture()),
    )
    assert res.returncode == 1
    assert malha_espia.conexoes >= 1


@pytest.mark.parametrize(
    ("args", "cadeira"),
    [
        (["enviar", "componente:eventos", "--tipo", "invalido", "--corpo", "erro"], "engenharia"),
        (["enviar", "componente:eventos", "dados", "--corpo", "mistura"], "engenharia"),
        (["enviar", "dados", "componente:eventos", "--corpo", "mistura"], "engenharia"),
        (["enviar", "componente:eventos", "dados"], "engenharia"),
        (["enviar", "dados", "--etiqueta", "card:4463", "--corpo", "flag"], "engenharia"),
        (["enviar", "dados", "--apoio", "card:4463", "--corpo", "flag"], "engenharia"),
        (["enviar", "dados", "--cita", "fonte", "--corpo", "flag"], "engenharia"),
        (["enviar", "dados", "--relacao", "atualiza", "--corpo", "flag"], "engenharia"),
        (["enviar", "componente:eventos", "--de", "bot:vigia", "--corpo", "bot"], "engenharia"),
        (["enviar", "componente:eventos", "--de", "automacao:vigia", "--corpo", "auto"], "engenharia"),
        (["enviar", "componente:eventos", "--eu", "dados", "--corpo", "divergente"], "engenharia"),
        (["enviar", "componente:eventos", "--de", "dados", "--corpo", "divergente"], "engenharia"),
        (["enviar", "componente:eventos", "--corpo", "fora"], "inexistente"),
        (["enviar", "componente:eventos", "--relacao", "atualiza", "--corpo", "sem responde"], "engenharia"),
        (
            ["enviar", "componente:eventos", "--responde", "fila:x", "--relacao", "invalida", "--corpo", "rel"],
            "engenharia",
        ),
        (["enviar", "componente:eventos", "--tipo", "contestacao", "--corpo", "sem alvo"], "engenharia"),
        (["enviar", "componente:eventos", "--corpo", "a" * 32769], "engenharia"),
        (["enviar", "componente:eventos", "--etiqueta", "   ", "--corpo", "vazio"], "engenharia"),
        (["enviar", "componente:eventos", "--apoio", "", "--corpo", "vazio"], "engenharia"),
        (["enviar", "componente:eventos", "--etiqueta", "card:" + "x" * 510, "--corpo", "longo"], "engenharia"),
        (["enviar", "componente:eventos", "--apoio", "a" * 513, "--corpo", "longo"], "engenharia"),
        (["enviar", "componente:eventos", "--cita", "c" * 513, "--corpo", "longo"], "engenharia"),
        (["enviar", "componente:eventos", "--responde", "r" * 513, "--corpo", "longo"], "engenharia"),
        (["enviar", "componente:eventos", "--ref", "card:" + "x" * 510, "--corpo", "longo"], "engenharia"),
    ],
)
def test_erros_de_borda_saem_2_sem_tocar_malha_nem_rota(casa_fake, malha_espia, args, cadeira):
    stub = _EventosStub()
    try:
        res = _rodar(
            args,
            _Ambiente(
                casa=casa_fake,
                malha_port=malha_espia.port,
                eventos_url=stub.url,
                credencial=_credencial_fixture(),
                cadeira=cadeira,
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 2, f"esperava 2, recebi {res.returncode}: stderr={res.stderr!r}"
    assert malha_espia.conexoes == 0
    assert len(stub.chamadas) == 0


@pytest.mark.parametrize(
    ("status", "corpo_erro", "trecho"),
    [
        (
            422,
            {
                "tipo": "EtiquetaSemFicha",
                "status": 422,
                "detalhe": "etiqueta sem ficha na cópia",
                "recusados": [{"indice": 0, "motivo": "EtiquetaSemFicha", "campo": "etiquetas[0]", "detalhe": "foo"}],
            },
            "EtiquetaSemFicha",
        ),
        (
            409,
            {"tipo": "EventoDivergente", "status": 409, "detalhe": "mesmo id com forma diferente"},
            "EventoDivergente",
        ),
    ],
)
def test_recusa_422_e_409_sai_2_sem_reenviar(casa_fake, malha_espia, status, corpo_erro, trecho):
    stub = _EventosStub(handler_fn=lambda _dado, _n: (status, corpo_erro))
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--etiqueta", "capacidade:x", "--corpo", "Recusado."],
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 2
    assert trecho in res.stderr
    assert len(stub.chamadas) == 1
    assert malha_espia.conexoes == 0


def test_pf_cadeira_ausente_sai_3(casa_fake, malha_espia):
    stub = _EventosStub()
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--corpo", "Sem cadeira."],
            _Ambiente(
                casa=casa_fake,
                malha_port=malha_espia.port,
                eventos_url=stub.url,
                credencial=_credencial_fixture(),
                cadeira=None,
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 3
    assert "monta_sessao" in res.stderr
    assert len(stub.chamadas) == 0
    assert malha_espia.conexoes == 0


def test_token_ausente_sai_3_sem_chamar_rota(casa_fake, malha_espia):
    stub = _EventosStub()
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--corpo", "Sem token."],
            _Ambiente(casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=None),
        )
    finally:
        stub.fechar()

    assert res.returncode == 3
    assert len(stub.chamadas) == 0
    assert malha_espia.conexoes == 0


def test_503_tenta_tres_vezes_com_mesmo_evento_id_e_sai_3(casa_fake, malha_espia):
    stub = _EventosStub(
        handler_fn=lambda _dado, _n: (503, {"tipo": "CopiaDeChavesVelha", "detalhe": "cópia vencida"})
    )
    try:
        res = _rodar(
            ["enviar", "componente:eventos", "--corpo", "Serviço indisponível."],
            _Ambiente(
                casa=casa_fake, malha_port=malha_espia.port, eventos_url=stub.url, credencial=_credencial_fixture()
            ),
        )
    finally:
        stub.fechar()

    assert res.returncode == 3
    assert len(stub.chamadas) == 3
    ids = [c["body"]["eventos"][0]["evento_id"] for c in stub.chamadas]
    origens = [c["body"]["eventos"][0]["origem"] for c in stub.chamadas]
    assert len(set(ids)) == 1
    assert len(set(origens)) == 1
    assert origens[0] in res.stderr
    assert malha_espia.conexoes == 0


def test_separa_destinatarios_e_reconcilia_pel_sem_nameerror_prefixo_bot(monkeypatch):
    """DT 1442: _separa_destinatarios_e_corpo_pos e _reconcilia_pel_respondidas usam PREFIXO_AUTOMACAO."""
    bin_dir = str(RAIZ / "bin")
    if bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)
    from _fila import streams

    monkeypatch.setattr(streams, "personas_validas", lambda: {"engenharia", "dados"})
    dests, corpo = streams._separa_destinatarios_e_corpo_pos(["engenharia", "automacao:vigia"])
    assert dests == ["engenharia", "automacao:vigia"]
    assert corpo is None

    dests_bot, corpo_bot = streams._separa_destinatarios_e_corpo_pos(["engenharia", "bot:vigia"])
    assert dests_bot == ["engenharia", "bot:vigia"]
    assert corpo_bot is None

    dests_msg, corpo_msg = streams._separa_destinatarios_e_corpo_pos(["engenharia", "mensagem posicional"])
    assert dests_msg == ["engenharia"]
    assert corpo_msg == "mensagem posicional"

    class _RcFake:
        def __init__(self):
            self.acks: list[tuple[str, str, str]] = []

        def xpending_range(self, _chave, _grupo, min="-", max="+", count=200):
            return [{"message_id": "1-0"}, {"message_id": "2-0"}]

        def xrange(self, _chave, min="-", max="+"):
            dados = {
                "1-0": {"de": "automacao:vigia", "para": "engenharia", "tipo": "aviso", "msgid": "m1", "corpo": "ok"},
                "2-0": {"de": "bot:antigo", "para": "engenharia", "tipo": "aviso", "msgid": "m2", "corpo": "ok"},
            }
            return [(min, dados[min])] if min in dados else []

        def xack(self, chave, grupo, mid):
            self.acks.append((chave, grupo, mid))

    rc = _RcFake()
    monkeypatch.setattr(streams, "_pares_respondidos_no_stream", lambda _rc, _p, _rem: set())
    vivas = streams._reconcilia_pel_respondidas(rc, "engenharia")
    assert [m["msgid"] for m in vivas] == ["1-0", "2-0"]
