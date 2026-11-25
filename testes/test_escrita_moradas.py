# componente: componente:escrita
"""Testes herméticos do protocolo e dos adaptadores git e Olaria (story #4441, t4)."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

HARNESS_ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = HARNESS_ROOT / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from escrita.moradas import ExecucaoMorada, proximo_repeticao_pedido  # noqa: E402
from escrita.moradas.git import MoradaGit  # noqa: E402
from escrita.moradas.olaria import ConfigOlaria, MoradaOlaria  # noqa: E402
from escrita.pedido import gerar_uuidv7, parsear_pedido  # noqa: E402
from escrita.politica import carregar_politica  # noqa: E402
from escrita.portao import (  # noqa: E402
    ContextoAutorizacao,
    CredencialPar,
    carregar_vista_alcance,
    decidir_portao,
)
from escrita.registro import RegistroOperacoes  # noqa: E402
from escrita.resolucao import resolver_alvo  # noqa: E402
from escrita.tipos import ContextoEscrita, RecusaEscrita  # noqa: E402

CONFIG_PATH = HARNESS_ROOT / "registro" / "escrita.yaml"
PORTA_YAML = HARNESS_ROOT / "registro" / "porta.yaml"
CHAVE_TESTE = "segredo-olaria-teste-nao-imprimir"


class _DubleOlaria:
    """Servidor HTTP local em loopback imitando o contrato de ontologia/olaria."""

    def __init__(self) -> None:
        self.fornadas: dict[str, tuple[str, dict[str, Any]]] = {}
        self.fichas: dict[str, tuple[str, str]] = {}
        self.cabecalhos_recebidos: list[dict[str, str]] = []
        self.modo_falha: str | None = None
        duble = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_: object) -> None:
                pass

            def _responder(self, status: int, corpo: dict[str, Any]) -> None:
                dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_POST(self) -> None:
                tam = int(self.headers.get("Content-Length") or 0)
                bruto = self.rfile.read(tam) if tam else b"{}"
                corpo = json.loads(bruto)
                duble.cabecalhos_recebidos.append(dict(self.headers.items()))

                if self.headers.get("X-Olaria-Chave") != CHAVE_TESTE:
                    self._responder(403, {"estado": "sem-permissao"})
                    return
                if duble.modo_falha == "503":
                    self._responder(503, {"estado": "fora-do-ar", "fornada": "desfeita"})
                    return
                if duble.modo_falha == "quebrar":
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    self.connection.close()
                    return
                if duble.modo_falha == "lento":
                    time.sleep(0.4)
                    self._responder(200, {"estado": "gravada", "fornada": "tarde"})
                    return

                if self.path == "/ensaiar":
                    self._responder(
                        200,
                        {"estado": "valida", "mudaria": True, "erros": []},
                    )
                    return

                fornada = self.headers.get("X-Olaria-Pedido") or self.headers.get(
                    "X-Olaria-Fornada", ""
                )
                yaml_txt = str(corpo.get("yaml") or "")
                resumo = hashlib.sha256(yaml_txt.encode("utf-8")).hexdigest()

                if fornada in duble.fornadas:
                    resumo_ant, resp_ant = duble.fornadas[fornada]
                    if resumo_ant != resumo:
                        self._responder(
                            422,
                            {"codigo": "pedido-com-conteudo-diferente", "erro": "payload distinto"},
                        )
                        return
                    self._responder(200, {**resp_ant, "estado": "ja-gravada"})
                    return

                if self.path == "/criar":
                    chave = yaml_txt.splitlines()[0].strip()
                    if chave in duble.fichas:
                        self._responder(422, {"codigo": "ja-existe", "erro": chave})
                        return
                    duble.fichas[chave] = (fornada, yaml_txt)
                    resp = {"estado": "gravada", "fornada": fornada}
                    duble.fornadas[fornada] = (resumo, resp)
                    self._responder(200, resp)
                    return

                if self.path == "/trocar":
                    chave = str(corpo.get("chave") or "")
                    versao = str(corpo.get("versao") or "")
                    if chave not in duble.fichas:
                        self._responder(422, {"codigo": "alvo-inexistente", "erro": chave})
                        return
                    ver_atual, _ = duble.fichas[chave]
                    if ver_atual != versao:
                        self._responder(
                            422, {"codigo": "versao-divergente", "erro": f"{versao} != {ver_atual}"}
                        )
                        return
                    duble.fichas[chave] = (fornada, yaml_txt)
                    resp = {"estado": "gravada", "fornada": fornada}
                    duble.fornadas[fornada] = (resumo, resp)
                    self._responder(200, resp)
                    return

                self._responder(404, {"estado": "nao-existe"})

        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._srv.daemon_threads = True
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._thread.start()
        host, porta = self._srv.server_address
        self.url = f"http://{host}:{porta}"

    def fechar(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()


def _cred_ok() -> CredencialPar:
    return CredencialPar(
        uid=1000,
        gid=1000,
        pid=500,
        usuario="claudinho",
        grupos=frozenset({"claudinho", "platafirma-escrita"}),
    )


def _preparar_execucao(
    verbo: str,
    argv: list[str],
    conteudo: bytes,
    *,
    raiz_bancadas: Path | None = None,
    registro: RegistroOperacoes | None = None,
    prazo_ns: int = 0,
) -> ExecucaoMorada:
    pol = carregar_politica(CONFIG_PATH)
    vista = carregar_vista_alcance(PORTA_YAML)
    auth = ContextoAutorizacao(politica=pol, vista=vista)
    ctx = ContextoEscrita(verbo=verbo, cadeira="engenharia", sujeito="dono")
    ped = parsear_pedido(verbo, argv, conteudo, politica=pol, contexto=ctx)
    dec = decidir_portao(ped, _cred_ok(), auth)
    alvo = resolver_alvo(ped, dec, vista, raiz_bancadas=raiz_bancadas)
    return ExecucaoMorada(
        pedido=ped,
        decisao=dec,
        alvo=alvo,
        politica=pol,
        release="rel-20261125",
        prazo_ns=prazo_ns,
        registro=registro,
    )


def _criar_worktree(tmp_path: Path) -> tuple[Path, Path]:
    clone = tmp_path / "platafirma-harness"
    clone.mkdir()
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "user.name", "t"], check=True)
    (clone / "README.md").write_text("ok\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(clone), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(clone), "commit", "-q", "-m", "init"], check=True)
    wt = tmp_path / "wt" / "platafirma-harness" / "engenharia" / "4441"
    wt.parent.mkdir(parents=True)
    subprocess.run(
        ["git", "-C", str(clone), "worktree", "add", "-q", "-b", "f/4441", str(wt)],
        check=True,
    )
    return tmp_path, wt


def test_olaria_criar_trocar_repeticao_e_ensaiar(tmp_path: Path) -> None:
    duble = _DubleOlaria()
    try:
        cfg = ConfigOlaria(url=duble.url, chave=CHAVE_TESTE)
        assert CHAVE_TESTE not in repr(cfg)
        morada = MoradaOlaria(cfg)
        assert morada.ponto_de_nao_volta == "envio-gravacao-olaria"

        reg = RegistroOperacoes(tmp_path / "operacoes.jsonl")
        pid_criar = gerar_uuidv7()
        ex_criar = _preparar_execucao(
            "ontologia",
            ["criar", "chapeu", "chapeu:back-end", "--pedido", pid_criar],
            b"chapeu:back-end\nnome: Back-end\n",
            registro=reg,
            prazo_ns=time.monotonic_ns() + 10_000_000_000,
        )
        res1 = morada.executar(ex_criar)
        assert res1.alterou is True
        assert res1.ja_gravado is False
        assert res1.fornada == pid_criar
        assert res1.versao == pid_criar
        assert len(duble.fornadas) == 1
        assert len(reg.listar()) == 1
        # Prazo relativo e cabeçalhos de fornada enviados à Olaria
        hdrs = {k.lower(): v for k, v in duble.cabecalhos_recebidos[-1].items()}
        assert hdrs["x-olaria-pedido"] == pid_criar
        assert hdrs["x-olaria-fornada"] == pid_criar
        assert int(hdrs["x-olaria-prazo-ms"]) > 0

        # Repetição idempotente pelo registro local (sem criar nova fornada)
        res_rep_reg = morada.executar(ex_criar)
        assert res_rep_reg.ja_gravado is True
        assert res_rep_reg.alterou is False
        assert res_rep_reg.fornada == pid_criar
        assert len(duble.fornadas) == 1
        assert len(reg.listar()) == 1

        # Repetição idempotente diretamente na Olaria (sem registro local)
        ex_criar_sem_reg = _preparar_execucao(
            "ontologia",
            ["criar", "chapeu", "chapeu:back-end", "--pedido", pid_criar],
            b"chapeu:back-end\nnome: Back-end\n",
            registro=None,
        )
        res_rep_olaria = morada.executar(ex_criar_sem_reg)
        assert res_rep_olaria.ja_gravado is True
        assert res_rep_olaria.alterou is False
        assert res_rep_olaria.fornada == pid_criar
        assert len(duble.fornadas) == 1

        # Trocar com a versão vigente
        pid_trocar = gerar_uuidv7()
        ex_trocar = _preparar_execucao(
            "ontologia",
            ["trocar", "chapeu", "chapeu:back-end", pid_criar, "--pedido", pid_trocar],
            b"chapeu:back-end\nnome: Back-end v2\n",
            registro=reg,
        )
        res_trocar = morada.executar(ex_trocar)
        assert res_trocar.alterou is True
        assert res_trocar.substituiu is True
        assert res_trocar.fornada == pid_trocar
        assert res_trocar.versao_anterior == pid_criar
        assert len(duble.fornadas) == 2
        assert len(reg.listar()) == 2

        # Trocar com versão divergente -> saída 2 versao-divergente
        ex_div = _preparar_execucao(
            "ontologia",
            ["trocar", "chapeu", "chapeu:back-end", pid_criar],
            b"chapeu:back-end\nnome: v3\n",
            registro=reg,
        )
        with pytest.raises(RecusaEscrita) as exc_div:
            morada.executar(ex_div)
        assert exc_div.value.saida == 2
        assert exc_div.value.primeiro.codigo == "versao-divergente"

        # Ensaiar: ensaiado=True, zero fornadas novas e zero linhas de escrita
        ex_ensaio = _preparar_execucao(
            "ontologia",
            ["ensaiar", "trocar", "chapeu", "chapeu:back-end", pid_trocar],
            b"chapeu:back-end\nnome: Ensaio\n",
            registro=reg,
        )
        res_ensaio = morada.executar(ex_ensaio)
        assert res_ensaio.ensaiado is True
        assert res_ensaio.mudaria is True
        assert res_ensaio.alterou is False
        assert res_ensaio.versao is None
        assert res_ensaio.fornada is None
        assert len(duble.fornadas) == 2
        assert len(reg.listar()) == 2
    finally:
        duble.fechar()


def test_olaria_ponto_de_nao_volta_saidas_3_e_5() -> None:
    # 1. Porta fechada -> falha antes do envio -> saída 3 (morada-sem-resposta)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    porta_fechada = sock.getsockname()[1]
    sock.close()

    morada_fora = MoradaOlaria(
        ConfigOlaria(url=f"http://127.0.0.1:{porta_fechada}", chave=CHAVE_TESTE)
    )
    ex_fora = _preparar_execucao(
        "ontologia", ["criar", "chapeu", "chapeu:x"], b"chapeu:x\n"
    )
    with pytest.raises(RecusaEscrita) as exc_conn:
        morada_fora.executar(ex_fora)
    assert exc_conn.value.saida == 3
    assert exc_conn.value.primeiro.codigo == "morada-sem-resposta"

    duble = _DubleOlaria()
    try:
        morada = MoradaOlaria(ConfigOlaria(url=duble.url, chave=CHAVE_TESTE))

        # 2. HTTP 503 (fornada desfeita) -> saída 3
        duble.modo_falha = "503"
        with pytest.raises(RecusaEscrita) as exc_503:
            morada.executar(ex_fora)
        assert exc_503.value.saida == 3
        assert exc_503.value.primeiro.codigo == "morada-sem-resposta"

        # 3. Conexão cai após envio da gravação -> saída 5 com --pedido em proximo
        duble.modo_falha = "quebrar"
        with pytest.raises(RecusaEscrita) as exc_5:
            morada.executar(ex_fora)
        assert exc_5.value.saida == 5
        assert exc_5.value.primeiro.codigo == "resposta-perdida"
        assert f"--pedido {ex_fora.pedido.pedido}" in exc_5.value.primeiro.proximo
        assert exc_5.value.primeiro.proximo == proximo_repeticao_pedido(
            ex_fora.pedido, "chapeu"
        )

        # 4. Timeout após envio da gravação -> saída 5 tempo-esgotado
        duble.modo_falha = "lento"
        ex_timeout = _preparar_execucao(
            "ontologia",
            ["criar", "chapeu", "chapeu:lento"],
            b"chapeu:lento\n",
            prazo_ns=time.monotonic_ns() + 100_000_000,
        )
        with pytest.raises(RecusaEscrita) as exc_to:
            morada.executar(ex_timeout)
        assert exc_to.value.saida == 5
        assert exc_to.value.primeiro.codigo == "tempo-esgotado"
        assert f"--pedido {ex_timeout.pedido.pedido}" in exc_to.value.primeiro.proximo

        # 5. Em ensaiar, falha após envio sai 3 (nunca 5)
        duble.modo_falha = "quebrar"
        ex_ens = _preparar_execucao(
            "ontologia",
            ["ensaiar", "criar", "chapeu", "chapeu:e"],
            b"chapeu:e\n",
        )
        with pytest.raises(RecusaEscrita) as exc_ens:
            morada.executar(ex_ens)
        assert exc_ens.value.saida == 3
        assert exc_ens.value.primeiro.codigo == "morada-sem-resposta"
    finally:
        duble.fechar()


def test_morada_git_gravar_inteiro_trecho_patch_repeticao_e_shebang(tmp_path: Path) -> None:
    raiz, wt = _criar_worktree(tmp_path)
    estado_dir = tmp_path / "estado"
    reg = RegistroOperacoes(estado_dir / "operacoes.jsonl")
    morada = MoradaGit(raiz_bancadas=raiz, estado_dir=estado_dir)
    assert morada.ponto_de_nao_volta == "os.replace"

    # 1. Criar arquivo novo inteiro
    ex1 = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/mod.py"],
        b"x = 1\ny = 2\n",
        raiz_bancadas=raiz,
        registro=reg,
    )
    res1 = morada.executar(ex1)
    arq = wt / "lib" / "mod.py"
    assert res1.alterou is True
    assert res1.ja_gravado is False
    assert res1.substituiu is False
    assert arq.read_text(encoding="utf-8") == "x = 1\ny = 2\n"
    ino1 = os.stat(arq).st_ino

    # 2. Repetição de conteúdo igual sem reescrever inodo
    ex_rep = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/mod.py"],
        b"x = 1\ny = 2\n",
        raiz_bancadas=raiz,
        registro=reg,
    )
    res_rep = morada.executar(ex_rep)
    assert res_rep.ja_gravado is True
    assert res_rep.alterou is False
    assert os.stat(arq).st_ino == ino1

    # 3. Edição por trecho com versão vigente (12 hex)
    ex_trecho = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/mod.py", res1.versao, "--formato", "trecho"],
        json.dumps({"antes": "x = 1", "depois": "x = 10"}).encode(),
        raiz_bancadas=raiz,
        registro=reg,
    )
    res_t = morada.executar(ex_trecho)
    assert res_t.alterou is True
    assert res_t.substituiu is True
    assert res_t.ocorrencias == 1
    assert res_t.versao_anterior == res1.versao
    assert arq.read_text(encoding="utf-8") == "x = 10\ny = 2\n"

    # 4. Edição por patch estrito
    diff = (
        "--- a/lib/mod.py\n"
        "+++ b/lib/mod.py\n"
        "@@ -1,2 +1,2 @@\n"
        " x = 10\n"
        "-y = 2\n"
        "+y = 20\n"
    ).encode()
    ex_patch = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:lib/mod.py", res_t.versao, "--formato", "patch"],
        diff,
        raiz_bancadas=raiz,
        registro=reg,
    )
    res_p = morada.executar(ex_patch)
    assert res_p.alterou is True
    assert res_p.hunks_aplicados == 1
    assert arq.read_text(encoding="utf-8") == "x = 10\ny = 20\n"

    # 5. Executável sem shebang sai 2; com shebang ganha bit de execução
    ex_sem_sb = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:bin/novo.sh"],
        b"echo oi\n",
        raiz_bancadas=raiz,
        registro=reg,
    )
    with pytest.raises(RecusaEscrita) as exc_sb:
        morada.executar(ex_sem_sb)
    assert exc_sb.value.saida == 2
    assert exc_sb.value.primeiro.codigo == "sem-shebang"

    ex_com_sb = _preparar_execucao(
        "repo",
        ["gravar", "componente", "platafirma-harness:bin/novo.sh"],
        b"#!/usr/bin/env bash\necho oi\n",
        raiz_bancadas=raiz,
        registro=reg,
    )
    morada.executar(ex_com_sb)
    modo_sh = stat.S_IMODE(os.stat(wt / "bin" / "novo.sh").st_mode)
    assert modo_sh & stat.S_IXUSR
    assert modo_sh & stat.S_IXGRP
    assert reg.arquivos_gravados_na_bancada("platafirma-harness", "engenharia") == [
        "lib/mod.py",
        "bin/novo.sh",
    ]
