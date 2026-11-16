"""Testes regressivos dos DTs 723, 724 e 725 em ops-server/server.py (#2856)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from pathlib import Path
from unittest.mock import MagicMock, patch

import redis

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for caminho_mod in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso", HARNESS_DIR / "lib"):
    if str(caminho_mod) not in sys.path:
        sys.path.insert(0, str(caminho_mod))

_TMP = Path(tempfile.mkdtemp(prefix="ops-dt-723-724-725-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for nome_var, subpasta in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(nome_var, "").startswith(tempfile.gettempdir()):
        os.environ[nome_var] = str(_TMP / subpasta)

import oplog
import poda
import server as s

SID = "11111111-2222-4333-8444-555555555555"
IDENT_TOKEN = {
    "sujeito": "b6986be0-c5b6-4693-839f-73c90b79b25a",
    "sub": "b6986be0-c5b6-4693-839f-73c90b79b25a",
    "username": "megafone",
    "azp": "claudinho-mcp",
    "sid": "sid-login",
    "jti": "jti-1",
}
IDENT_SESSAO = {
    "sessao_id": SID,
    "ordem_id": "o1",
    "cadeira": "engenharia",
    "sujeito": IDENT_TOKEN["sujeito"],
    "origem_sessao": "",
}


def _aguarda_fio_prazo(rid: str) -> dict:
    nome_fio = f"prazo-{rid}"
    for fio in list(threading.enumerate()):
        if fio.name == nome_fio:
            fio.join(timeout=10.0)
    caminho = s.RESULTADO_DIR / f"{rid}.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def _linhas_oplog(pasta: Path) -> list[dict]:
    saida = []
    for arq in sorted(pasta.glob("ops-*.jsonl")):
        for linha_txt in arq.read_text(encoding="utf-8").splitlines():
            saida.append(json.loads(linha_txt))
    return saida


class _ValkeyCasFake:
    """Dublê de Valkey com suporte a WATCH/MULTI/EXEC e TTL para testar concorrência (DT 725)."""

    def __init__(self, inicial: dict[str, str], ttl_inicial: int = 172800):
        self._trava = threading.Lock()
        self.dados = dict(inicial)
        self.versao = {chave: 0 for chave in inicial}
        self.ttls = {chave: ttl_inicial for chave in inicial}
        self.conflitos_watch = 0
        self.barreira_leitura: threading.Barrier | None = None

    def get(self, chave: str) -> str | None:
        with self._trava:
            return self.dados.get(chave)

    def set(self, chave: str, valor: str, *, keepttl: bool = False, ex: int | None = None) -> bool:
        with self._trava:
            self.dados[chave] = valor
            self.versao[chave] = self.versao.get(chave, 0) + 1
            if not keepttl:
                self.ttls[chave] = ex if ex is not None else -1
            return True

    def pipeline(self) -> _PipeCasFake:
        return _PipeCasFake(self)


class _PipeCasFake:
    def __init__(self, banco: _ValkeyCasFake):
        self._banco = banco
        self._vigiadas: dict[str, int] = {}
        self._em_multi = False
        self._fila: list[tuple[str, str, bool]] = []
        self._usou_barreira = False

    def watch(self, chave: str) -> bool:
        with self._banco._trava:
            self._vigiadas[chave] = self._banco.versao.get(chave, 0)
        return True

    def unwatch(self) -> bool:
        self._vigiadas.clear()
        return True

    def get(self, chave: str) -> str | None:
        valor = self._banco.get(chave)
        barreira = self._banco.barreira_leitura
        if barreira is not None and not self._usou_barreira:
            self._usou_barreira = True
            try:
                barreira.wait(timeout=2.0)
            except threading.BrokenBarrierError:
                pass
        return valor

    def multi(self) -> None:
        self._em_multi = True
        self._fila.clear()

    def set(self, chave: str, valor: str, *, keepttl: bool = False) -> None:
        if not self._em_multi:
            self._banco.set(chave, valor, keepttl=keepttl)
            return
        self._fila.append((chave, valor, keepttl))

    def execute(self) -> list[bool]:
        with self._banco._trava:
            for chave, versao_lida in self._vigiadas.items():
                if self._banco.versao.get(chave, 0) != versao_lida:
                    self._banco.conflitos_watch += 1
                    self._vigiadas.clear()
                    self._em_multi = False
                    self._fila.clear()
                    raise redis.WatchError("Chave modificada concorrentemente")
            resultados = []
            for chave, valor, keepttl in self._fila:
                self._banco.dados[chave] = valor
                self._banco.versao[chave] = self._banco.versao.get(chave, 0) + 1
                if not keepttl:
                    self._banco.ttls[chave] = -1
                resultados.append(True)
            self._vigiadas.clear()
            self._em_multi = False
            self._fila.clear()
            return resultados

    def reset(self) -> None:
        self._vigiadas.clear()
        self._em_multi = False
        self._fila.clear()


# --- DT 723 -----------------------------------------------------------------------

def test_dt723_verbo_2mb_em_stderr_e_exit_1_devolve_teto_e_caminho_do_cru(tmp_path, monkeypatch):
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "derrame")
    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('E' * 2_000_000); sys.stdout.write('S' * 120_000); sys.exit(1)",
    ]
    res = s._run_verbo_blocking(cmd, None, 30, IDENT_SESSAO, 10.0)
    servido = s._serve(res, tool="teste", alca="teste rodar", ident=IDENT_SESSAO)

    assert servido["exit_code"] == 1
    err = servido["stderr"]
    assert err["truncado"] is True
    assert err["bytes_total"] == 2_000_000
    assert len(err["texto"].encode("utf-8")) == s.CAP
    assert err.get("cru") and Path(err["cru"]).is_file()
    assert len(Path(err["cru"]).read_text(encoding="utf-8")) == 2_000_000

    out = servido["stdout"]
    assert out["truncado"] is True
    assert out["bytes_total"] == 120_000
    assert len(out["texto"].encode("utf-8")) == s.CAP
    assert out.get("cru") and Path(out["cru"]).is_file()
    assert len(Path(out["cru"]).read_text(encoding="utf-8")) == 120_000


def test_dt723_conclusao_apos_prazo_derrama_stdout_e_stderr_acima_do_teto(tmp_path, monkeypatch):
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "derrame")
    pasta_res = tmp_path / "porta"
    pasta_res.mkdir()
    script = (
        "import sys, time; time.sleep(0.25); "
        "sys.stdout.write('O' * 80_000); sys.stderr.write('R' * 90_000); sys.exit(1)"
    )
    with patch.object(s, "RESULTADO_DIR", pasta_res), patch.object(s, "_audit"):
        em_andamento = s._run_verbo_blocking(
            [sys.executable, "-c", script], None, 10, IDENT_SESSAO, 0.05
        )
        assert em_andamento.get("em_andamento") is True
        final = _aguarda_fio_prazo(em_andamento["id"])

    assert final["exit_code"] == 1
    assert final["stdout"]["truncado"] is True
    assert len(final["stdout"]["texto"].encode("utf-8")) == s.CAP
    assert Path(final["stdout"]["cru"]).read_text(encoding="utf-8") == "O" * 80_000

    assert final["stderr"]["truncado"] is True
    assert len(final["stderr"]["texto"].encode("utf-8")) == s.CAP
    assert Path(final["stderr"]["cru"]).read_text(encoding="utf-8") == "R" * 90_000


def test_dt723_truncado_so_e_true_quando_bytes_ficam_fora_do_entregue(tmp_path, monkeypatch):
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "derrame")
    rc_mudo = MagicMock(
        get=MagicMock(return_value=None),
        hget=MagicMock(return_value=None),
        incr=MagicMock(return_value=1),
    )
    monkeypatch.setattr(s, "_rc", lambda: rc_mudo)

    curto = s._cap(b"ok\n", sessao_id=SID)
    assert curto["truncado"] is False and "cru" not in curto

    # Perfil cosmético acima de CAP entrega o texto semântico inteiro (modo=derrame): truncado é False
    semantico = "\n".join(f"[{i}] linha semântica distinta {i} " + ("palavra " * 15) for i in range(500))
    bruto_sem = semantico.encode("utf-8")
    assert len(bruto_sem) > s.CAP
    env_sem = {
        "exit_code": 0,
        "stdout": s._cap(bruto_sem, sessao_id=SID, nome="sem-stdout.txt"),
        "stderr": s._cap(b"", sessao_id=SID, nome="sem-stderr.txt"),
    }
    servido_sem = s._serve(
        env_sem, tool="motor", alca="motor buscar x", ident=IDENT_SESSAO, cosmetica=True
    )
    assert servido_sem["stdout"]["truncado"] is False
    assert servido_sem["stdout"].get("cru") and Path(servido_sem["stdout"]["cru"]).is_file()

    # Perfil comum acima de CAP corta o miolo: truncado é True e o cru integral está no caminho
    prosa_grande = "\n".join(
        "abcdefghij"[i % 10] * (i % 7 + 3) + " bloco " + ("z" * 60) for i in range(900)
    )
    bruto_prosa = prosa_grande.encode("utf-8")
    assert len(bruto_prosa) > s.CAP
    env_corte = {
        "exit_code": 0,
        "stdout": s._cap(bruto_prosa, sessao_id=SID, nome="prosa-stdout.txt"),
        "stderr": s._cap(b"", sessao_id=SID, nome="prosa-stderr.txt"),
    }
    servido_corte = s._serve(
        env_corte, tool="tarefas", alca="tarefas listar", ident=IDENT_SESSAO, cosmetica=False
    )
    assert servido_corte["stdout"]["truncado"] is True
    caminho_cru = servido_corte["stdout"].get("cru")
    assert caminho_cru and Path(caminho_cru).read_text(encoding="utf-8") == prosa_grande


# --- DT 724 -----------------------------------------------------------------------

def test_dt724_vinte_chamadas_simultaneas_a_audit_gravam_identidade_completa(tmp_path):
    assert isinstance(s._em_audit, ContextVar)
    barreira = threading.Barrier(20)

    def _quem_sincronizado() -> dict:
        try:
            barreira.wait(timeout=2.0)
        except threading.BrokenBarrierError:
            pass
        return dict(IDENT_TOKEN)

    def _dispara(indice: int) -> None:
        s._audit(
            tool="tarefas",
            evento="verbo",
            ato="ler",
            args=str(indice),
            cadeira="engenharia",
            sessao_id=SID,
            ordem_id=f"o-{indice}",
            exit_code=0,
            erro=None,
            bytes_produzidos=10,
            bytes_servidos=10,
            tokens=3,
            metodo_tokens="qwen2.5",
            lavado=[],
        )

    with (
        patch.object(s, "LOG_DIR", tmp_path),
        patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))),
        patch.object(s, "_quem", side_effect=_quem_sincronizado),
        ThreadPoolExecutor(max_workers=20) as pool,
    ):
        futuros = [pool.submit(_dispara, idx) for idx in range(20)]
        for fut in futuros:
            fut.result(timeout=10.0)

    linhas = _linhas_oplog(tmp_path)
    assert len(linhas) == 20
    for linha in linhas:
        erros = oplog.validar(linha)
        assert erros == [], f"linha inválida: {erros} -> {linha}"
        for chave_id, valor_esp in IDENT_TOKEN.items():
            assert linha.get(chave_id) == valor_esp, f"faltou {chave_id} na linha: {linha}"


def test_dt724_fio_pos_prazo_recebe_identidade_por_argumento(tmp_path):
    pasta_res = tmp_path / "porta"
    pasta_res.mkdir()
    pasta_log = tmp_path / "log"
    pasta_log.mkdir()
    thread_principal = threading.get_ident()

    def _quem_so_na_thread_chamadora() -> dict:
        if threading.get_ident() == thread_principal:
            return dict(IDENT_TOKEN)
        return {}

    with (
        patch.object(s, "RESULTADO_DIR", pasta_res),
        patch.object(s, "LOG_DIR", pasta_log),
        patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))),
        patch.object(s, "_quem", side_effect=_quem_so_na_thread_chamadora),
    ):
        res = s._run_verbo_blocking(
            [sys.executable, "-c", "import time; time.sleep(0.25)"],
            None,
            10,
            IDENT_SESSAO,
            0.05,
        )
        assert res.get("em_andamento") is True
        _aguarda_fio_prazo(res["id"])

    linhas = _linhas_oplog(pasta_log)
    assert len(linhas) == 1
    evento = linhas[0]
    assert evento["evento"] == "verbo_concluido_apos_prazo"
    for chave_id, valor_esp in IDENT_TOKEN.items():
        assert evento.get(chave_id) == valor_esp


# --- DT 725 -----------------------------------------------------------------------

def test_dt725_chamadas_paralelas_turno_e_chapeu_preservam_ambos_os_campos(tmp_path):
    chave = f"sessao:{SID}"
    inicial = {
        chave: json.dumps({"cadeira": "engenharia", "ordem_id": "o1", "sujeito": IDENT_TOKEN["sujeito"]})
    }
    banco = _ValkeyCasFake(inicial, ttl_inicial=172800)
    banco.barreira_leitura = threading.Barrier(2)
    s._CARIMBOS.clear()

    def _abre_turno() -> None:
        s._carimba_turno(dict(IDENT_SESSAO), "T9", "resolver todos", "hook")

    def _troca_chapeu() -> None:
        s._chapeu_do_giro(
            "persona", "ler", ["engenharia", "--chapeu", "back-end"], {"exit_code": 0}, dict(IDENT_SESSAO)
        )

    with (
        patch.object(s, "_rc", return_value=banco),
        patch.object(s, "LOG_DIR", tmp_path),
        patch.object(s, "_quem", return_value=IDENT_TOKEN),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        f1 = pool.submit(_abre_turno)
        f2 = pool.submit(_troca_chapeu)
        f1.result(timeout=5.0)
        f2.result(timeout=5.0)
        s._escopo_do_giro("repo", "abrir", ["platafirma-harness", "4073"], {"exit_code": 0}, dict(IDENT_SESSAO))

    gravado = json.loads(banco.get(chave))
    assert gravado["cadeira"] == "engenharia"
    assert gravado["turno_id"] == "T9"
    assert gravado["turno_valor"] == "T9"
    assert gravado["turno_fonte"] == "hook"
    assert gravado["chapeu"] == "back-end"
    assert gravado["escopo_atual"] == "#4073"
    assert banco.ttls[chave] == 172800
    assert banco.conflitos_watch >= 1
