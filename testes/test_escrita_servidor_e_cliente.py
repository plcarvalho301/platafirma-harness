"""Suíte hermética da t5 (#4441): servidor por soquete, cliente e fachada da escrita."""
from __future__ import annotations

import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

_HARNESS = Path(__file__).resolve().parents[1]
_LIB = _HARNESS / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from escrita import (  # noqa: E402
    ConfigCliente,
    ContextoEscrita,
    OpcoesExecucao,
    RecusaEscrita,
    executar_ato_escrever,
    verbo_esta_ligado,
)
from escrita.__main__ import executar_cli  # noqa: E402
from escrita.cliente import consultar_saude, enviar_escrita  # noqa: E402
from escrita.moradas import ExecucaoMorada  # noqa: E402
from escrita.pedido import gerar_uuidv7, parsear_pedido  # noqa: E402
from escrita.politica import PoliticaEscrita, carregar_politica  # noqa: E402
from escrita.servidor import (  # noqa: E402
    ConfigServidor,
    ServidorEscritor,
    criar_autorizador_pdp,
    ler_quadro,
)
from escrita.tipos import ResultadoEscrita  # noqa: E402


def _politica_ligada(verbos: frozenset[str] = frozenset({"repo"})) -> PoliticaEscrita:
    base = carregar_politica(_HARNESS / "registro" / "escrita.yaml")
    return replace(base, verbos_ligados=verbos)


def _criar_bancada_git(
    tmp_path: Path, repo: str = "demo", cadeira: str = "engenharia"
) -> tuple[Path, Path]:
    base_repo = tmp_path / repo
    base_repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(base_repo)], check=True)
    subprocess.run(
        ["git", "-C", str(base_repo), "config", "user.email", "t@example.com"], check=True
    )
    subprocess.run(
        ["git", "-C", str(base_repo), "config", "user.name", "Tester"], check=True
    )
    (base_repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(base_repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(base_repo), "commit", "-q", "-m", "init"], check=True)

    raiz_wt = tmp_path / "wt"
    wt_dir = raiz_wt / repo / cadeira / "4441-teste"
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(base_repo), "worktree", "add", "-q", "-b", "fabrica/4441-teste", str(wt_dir)],
        check=True,
    )
    return tmp_path, wt_dir


def _subir_servidor(
    cfg: ConfigServidor,
) -> tuple[ServidorEscritor, threading.Thread]:
    srv = ServidorEscritor(cfg)
    srv.iniciar()
    th = threading.Thread(target=srv.servir, kwargs={"instalar_sinais": False}, daemon=True)
    th.start()
    return srv, th


def test_saude_e_escrita_pela_fachada(tmp_path: Path) -> None:
    raiz_wt, wt_dir = _criar_bancada_git(tmp_path)
    rel_a = tmp_path / "releases" / "r-20261125-aaa"
    rel_a.mkdir(parents=True)
    rel_link = tmp_path / "current"
    rel_link.symlink_to(rel_a)

    sock_path = tmp_path / "escritor.sock"
    pol = _politica_ligada(frozenset({"repo"}))
    cfg = ConfigServidor(
        socket_path=sock_path,
        raiz_bancadas=raiz_wt,
        estado_dir=tmp_path / "estado",
        politica=pol,
        release_link=rel_link,
        uid_escritor=os.geteuid(),
        autorizador_sujeito=lambda *_: True,
        poll_intervalo_s=0.05,
    )
    srv, th = _subir_servidor(cfg)
    try:
        saude = consultar_saude(sock_path)
        assert saude["ok"] is True
        assert saude["release"] == "r-20261125-aaa"

        ctx = ContextoEscrita(verbo="repo", cadeira="engenharia", sujeito="megafone")
        res = executar_ato_escrever(
            "repo",
            ["gravar", "componente", "demo:app/mod.py"],
            b"print('ok')\n",
            opcoes=OpcoesExecucao(contexto=ctx, politica=pol, socket_path=sock_path),
        )
        assert res.alterou is True
        assert res.release == "r-20261125-aaa"
        assert (wt_dir / "app" / "mod.py").read_text(encoding="utf-8") == "print('ok')\n"
    finally:
        srv.parar("fim-teste")
        th.join(timeout=3.0)


def test_soquete_ausente_e_prazo_expirado_saem_3(tmp_path: Path) -> None:
    pol = _politica_ligada(frozenset({"repo"}))
    sock_ausente = tmp_path / "nao-existe.sock"
    with pytest.raises(RecusaEscrita) as exc_saude:
        consultar_saude(sock_ausente)
    assert exc_saude.value.saida == 3
    assert exc_saude.value.primeiro.codigo == "escritor-indisponivel"

    ctx = ContextoEscrita(verbo="repo", cadeira="engenharia", sujeito="megafone")
    with pytest.raises(RecusaEscrita) as exc_ausente:
        executar_ato_escrever(
            "repo",
            ["gravar", "componente", "demo:a.txt"],
            b"ola\n",
            opcoes=OpcoesExecucao(contexto=ctx, politica=pol, socket_path=sock_ausente),
        )
    assert exc_ausente.value.saida == 3
    assert exc_ausente.value.primeiro.codigo == "escritor-indisponivel"

    ctx_vencido = ContextoEscrita(
        verbo="repo",
        cadeira="engenharia",
        sujeito="megafone",
        prazo_ns=time.monotonic_ns() - 10_000,
    )
    with pytest.raises(RecusaEscrita) as exc_prazo:
        executar_ato_escrever(
            "repo",
            ["gravar", "componente", "demo:a.txt"],
            b"ola\n",
            opcoes=OpcoesExecucao(contexto=ctx_vencido, politica=pol, socket_path=sock_ausente),
        )
    assert exc_prazo.value.saida == 3


def test_saida_5_com_pedido_em_proximo_apos_ponto_de_nao_volta(tmp_path: Path) -> None:
    """Se a conexão cai ou estoura o prazo após envio, cliente sai 5 com --pedido em proximo."""
    sock_path = tmp_path / "lento.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(4)

    def _servir_mudo() -> None:
        conn, _ = srv.accept()
        try:
            _ = ler_quadro(conn, teto_bytes=65536)
            time.sleep(0.4)
        finally:
            conn.close()

    def _servir_quebra() -> None:
        conn, _ = srv.accept()
        try:
            _ = ler_quadro(conn, teto_bytes=65536)
        finally:
            conn.close()

    pol = _politica_ligada(frozenset({"repo"}))
    pid_timeout = gerar_uuidv7()
    t1 = threading.Thread(target=_servir_mudo, daemon=True)
    t1.start()
    ctx = ContextoEscrita(
        verbo="repo",
        cadeira="engenharia",
        sujeito="megafone",
        prazo_ns=time.monotonic_ns() + 80_000_000,
    )
    argv = ["gravar", "componente", "demo:arq.txt", "--pedido", pid_timeout]
    pedido = parsear_pedido("repo", argv, b"oi\n", politica=pol, contexto=ctx)
    with pytest.raises(RecusaEscrita) as exc_to:
        enviar_escrita(
            pedido,
            argv,
            b"oi\n",
            ConfigCliente(politica=pol, socket_path=sock_path, folga_s=0.02),
        )
    t1.join(timeout=2.0)
    assert exc_to.value.saida == 5
    assert exc_to.value.primeiro.codigo == "tempo-esgotado"
    assert f"--pedido {pid_timeout}" in exc_to.value.primeiro.proximo

    pid_drop = gerar_uuidv7()
    t2 = threading.Thread(target=_servir_quebra, daemon=True)
    t2.start()
    ctx2 = ContextoEscrita(verbo="repo", cadeira="engenharia", sujeito="megafone")
    argv2 = ["gravar", "componente", "demo:arq.txt", "--pedido", pid_drop]
    pedido2 = parsear_pedido("repo", argv2, b"oi\n", politica=pol, contexto=ctx2)
    with pytest.raises(RecusaEscrita) as exc_drop:
        enviar_escrita(
            pedido2,
            argv2,
            b"oi\n",
            ConfigCliente(politica=pol, socket_path=sock_path, folga_s=0.5),
        )
    t2.join(timeout=2.0)
    srv.close()
    assert exc_drop.value.saida == 5
    assert exc_drop.value.primeiro.codigo == "resposta-perdida"
    assert f"--pedido {pid_drop}" in exc_drop.value.primeiro.proximo


def test_drenagem_em_voo_na_parada_e_troca_de_release(tmp_path: Path) -> None:
    raiz_wt, _ = _criar_bancada_git(tmp_path)
    rel_1 = tmp_path / "releases" / "r-001"
    rel_2 = tmp_path / "releases" / "r-002"
    rel_1.mkdir(parents=True)
    rel_2.mkdir(parents=True)
    rel_link = tmp_path / "current"
    rel_link.symlink_to(rel_1)

    entrou = threading.Event()
    liberar = threading.Event()

    class _MoradaLenta:
        nome = "git"
        ponto_de_nao_volta = "os.replace"

        def executar(self, execucao: ExecucaoMorada) -> ResultadoEscrita:
            entrou.set()
            liberar.wait(timeout=3.0)
            return ResultadoEscrita(
                chave=execucao.pedido.chave,
                classe=execucao.decisao.classe,
                forma=execucao.pedido.forma,
                morada="git",
                release=execucao.release,
                pedido=execucao.pedido.pedido,
                alterou=True,
                ja_gravado=False,
                substituiu=False,
                bytes=3,
                versao="a" * 12,
                versao_completa="a" * 40,
            )

    sock_path = tmp_path / "dreno.sock"
    pol = _politica_ligada(frozenset({"repo"}))
    cfg = ConfigServidor(
        socket_path=sock_path,
        raiz_bancadas=raiz_wt,
        estado_dir=tmp_path / "estado",
        politica=pol,
        moradas={"git": _MoradaLenta()},
        release_link=rel_link,
        uid_escritor=os.geteuid(),
        autorizador_sujeito=lambda *_: True,
        poll_intervalo_s=0.05,
    )
    srv, th = _subir_servidor(cfg)

    resultado_cliente: list[ResultadoEscrita] = []

    def _chamar() -> None:
        ctx = ContextoEscrita(verbo="repo", cadeira="engenharia", sujeito="megafone")
        res = executar_ato_escrever(
            "repo",
            ["gravar", "componente", "demo:slow.txt"],
            b"abc",
            opcoes=OpcoesExecucao(contexto=ctx, politica=pol, socket_path=sock_path),
        )
        resultado_cliente.append(res)

    tc = threading.Thread(target=_chamar)
    tc.start()
    assert entrou.wait(timeout=2.0)

    novo_link = tmp_path / "current.new"
    novo_link.symlink_to(rel_2)
    os.replace(novo_link, rel_link)
    time.sleep(0.12)
    assert th.is_alive()

    liberar.set()
    tc.join(timeout=3.0)
    th.join(timeout=3.0)
    assert not th.is_alive()
    assert srv.motivo_saida == "release-trocada"
    assert len(resultado_cliente) == 1
    assert resultado_cliente[0].release == "r-001"


def test_varredura_de_temporarios_orfaos_na_largada(tmp_path: Path) -> None:
    raiz_wt, wt_dir = _criar_bancada_git(tmp_path)
    antigo = wt_dir / ".pf-esc-orfao123.tmp"
    recente = wt_dir / ".pf-esc-ativo456.tmp"
    antigo.write_text("lixo", encoding="utf-8")
    recente.write_text("novo", encoding="utf-8")
    passado = time.time() - 3600
    os.utime(antigo, (passado, passado))

    pol = _politica_ligada(frozenset({"repo"}))
    cfg = ConfigServidor(
        socket_path=tmp_path / "orfao.sock",
        raiz_bancadas=raiz_wt,
        estado_dir=tmp_path / "estado",
        politica=pol,
        uid_escritor=os.geteuid(),
        idade_orfao_s=60.0,
    )
    srv = ServidorEscritor(cfg)
    srv.iniciar()
    try:
        assert not antigo.exists()
        assert recente.exists()
        assert any(".pf-esc-orfao123.tmp" in item for item in srv.orfaos_removidos)
    finally:
        srv._fechar_soquete()


def test_fachada_verbo_desligado_e_cli_erro_ultima_linha(tmp_path: Path) -> None:
    pol_desligada = _politica_ligada(frozenset())
    assert verbo_esta_ligado("repo", politica=pol_desligada) is False

    chamado: list[str] = []

    def _fallback(ped) -> ResultadoEscrita:
        chamado.append(ped.chave)
        return ResultadoEscrita(
            chave=ped.chave,
            classe="componente",
            forma=ped.forma,
            morada="git",
            release="local",
            pedido=ped.pedido,
            alterou=True,
            ja_gravado=False,
            substituiu=False,
            bytes=2,
            versao="b" * 12,
        )

    res = executar_ato_escrever(
        "repo",
        ["gravar", "componente", "demo:x.py"],
        b"ok",
        opcoes=OpcoesExecucao(politica=pol_desligada, fallback_desligado=_fallback),
    )
    assert res.versao == "b" * 12
    assert chamado == ["demo:x.py"]

    out = io.StringIO()
    err = io.StringIO()
    rc = executar_cli(
        ["repo", "editar", "componente", "demo:x.py"],
        stdin=io.BytesIO(b"x"),
        stdout=out,
        stderr=err,
        socket_path=tmp_path / "ausente.sock",
    )
    assert rc == 2
    assert out.getvalue() == ""
    ultima = json.loads(err.getvalue().strip().splitlines()[-1])
    assert ultima["erro"]["codigo"] == "variante-nao-executa"


def test_autorizador_pdp_produzido_para_t5(tmp_path: Path) -> None:
    """Prova a fiação do autorizador de sujeito contra DecisorAcesso real."""
    core_dir = Path("/home/claudinho/AI/wt/platafirma-core/engenharia/4441-ato-escrever")
    if not (core_dir / "acesso" / "politica.yaml").is_file():
        pytest.skip("bancada platafirma-core indisponível neste ambiente")
    auth_fn = criar_autorizador_pdp(core_dir / "acesso", core_dir=core_dir)
    assert auth_fn is not None
    assert auth_fn("sujeito-inexistente-xyz", "engenharia", "repo", "gravar") is False
    assert auth_fn("megafone", "engenharia", "repo", "gravar") is True
