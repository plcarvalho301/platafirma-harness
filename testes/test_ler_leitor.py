"""Testes do daemon e do cliente do leitor único (story #4442, t7)."""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "lib") not in sys.path:
    sys.path.insert(0, str(RAIZ / "lib"))

from leitura.cliente import ClienteLeitor, ErroClienteLeitor
from leitura.daemon import (
    DaemonLeitor,
    combinar_codigos_saida,
    enviar_quadro_json,
    receber_quadro_json,
)
from leitura.moradas import ErroMorada, RegistroMoradas
from leitura.moradas.git import AdaptadorGit
from leitura.resolvedor import ClasseAlcance, VistaAlcance
from leitura.tipos import (
    AlvoResolvido,
    ContextoChamada,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)


def test_producao_registra_as_moradas_e_le_so_a_credencial_do_banco(tmp_path: Path) -> None:
    from leitura.daemon import CredencialAusente, dsn_casa_db, ler_credencial, montar_moradas_producao

    creds = tmp_path / "creds"
    creds.mkdir()
    (creds / "casa-db").write_text("s3nh@/x\n", encoding="utf-8")
    env = {"CREDENTIALS_DIRECTORY": str(creds), "PF_RELEASE_CURRENT": str(tmp_path)}
    assert ler_credencial("casa-db", env) == "s3nh@/x"
    assert dsn_casa_db(env) == "postgresql://pf_leitor_ro:s3nh%40%2Fx@127.0.0.1:5439/casa"

    avisos: list[dict[str, Any]] = []
    reg = montar_moradas_producao(env, avisar=avisos.append)
    for morada in ("git", "banco", "wiki", "fila", "rastreador", "cofre"):
        assert reg.obter(morada) is not None
    with pytest.raises(ErroMorada) as exc_balde:
        reg.obter("balde")
    assert exc_balde.value.saida == 3
    assert [a["morada"] for a in avisos] == ["balde"]

    # Sem a credencial o banco fica de fora e sai 3 na chamada, com o motivo no log
    avisos.clear()
    reg_sem = montar_moradas_producao({"PF_RELEASE_CURRENT": str(tmp_path)}, avisar=avisos.append)
    with pytest.raises(ErroMorada) as exc_banco:
        reg_sem.obter("banco")
    assert exc_banco.value.saida == 3
    assert [a["morada"] for a in avisos] == ["banco", "balde"]
    with pytest.raises(CredencialAusente):
        ler_credencial("casa-db", {"CREDENTIALS_DIRECTORY": str(tmp_path / "vazio")})


class _MoradaSimulada:
    """Adaptador configurável para exercitar latência, falhas 1/3/5 e contagem de chamadas."""

    def __init__(self, itens: dict[str, bytes], *, atraso_s: float = 0.0) -> None:
        self._itens = dict(itens)
        self._atraso_s = atraso_s
        self.chamadas: list[str] = []
        self.barreira_inicio: threading.Event | None = None
        self.barreira_liberar: threading.Event | None = None

    def ler_objeto(self, alvo: AlvoResolvido, _sel: SeletorParte, _prazo: int) -> ObjetoBruto:
        self.chamadas.append(alvo.chave_canonica)
        if self.barreira_inicio is not None:
            self.barreira_inicio.set()
        if self.barreira_liberar is not None:
            self.barreira_liberar.wait(timeout=3.0)
        if self._atraso_s > 0:
            time.sleep(self._atraso_s)
        if alvo.chave_canonica.endswith(":erro3"):
            raise ErroMorada(Recusa(3, "morada-sem-resposta", "morada:git", alvo.chave_pedida))
        if alvo.chave_canonica.endswith(":erro5"):
            raise ErroMorada(Recusa(5, "tempo-esgotado", "morada:git", alvo.chave_pedida))
        dados = self._itens.get(alvo.chave_canonica)
        if dados is None:
            raise ErroMorada(Recusa(1, "chave-inexistente", "morada:git", alvo.chave_pedida))
        return ObjetoBruto(
            alvo=alvo,
            versao="v1",
            dados=dados,
            nome_arquivo=f"{alvo.classe}.md",
            total_bytes=len(dados),
        )

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros, termo, prazo_ms
        chaves = sorted(k for k in self._itens if k.startswith(f"{classe}:"))
        if cursor is not None:
            chaves = [k for k in chaves if k > cursor.ultima_chave]
        tem_mais = len(chaves) > limite
        pag = chaves[:limite]
        itens = tuple({"chave": k, "rotulo": k, "resumo_curto": ""} for k in pag)
        prox = (0, pag[-1]) if (tem_mais and pag) else None
        return PaginaBruta(classe, "v1", None, True, len(self._itens), itens, prox)


def _vista_teste() -> VistaAlcance:
    return VistaAlcance(
        verbos_aceitam_ler=frozenset({"busca"}),
        alcance_verbo={"busca": frozenset({"*"})},
        classes={
            "ato": ClasseAlcance("ato", "git", "busca", molde="ato/<slug>.md"),
        },
    )


def _subir_daemon(
    daemon: DaemonLeitor, sock_path: Path
) -> threading.Thread:
    t = threading.Thread(target=daemon.servir_caminho, args=(sock_path,), daemon=True)
    t.start()
    fim = time.monotonic() + 2.0
    while not sock_path.exists() and time.monotonic() < fim:
        time.sleep(0.01)
    return t


def _ctx(sujeito: str = "engenharia", prazo_ms: int = 3_000) -> ContextoChamada:
    return ContextoChamada(
        sujeito_jwt=None,
        sujeito=sujeito,
        sessao_id="s1",
        ordem_id="o1",
        verbo="busca",
        origem_autenticada="cli",
        origem_declarada="cli",
        prazo_ms=prazo_ms,
    )


def test_combinar_precedencia_multi_chave() -> None:
    assert combinar_codigos_saida([0, 0]) == 0
    assert combinar_codigos_saida([0, 1]) == 1
    assert combinar_codigos_saida([1, 2]) == 2
    assert combinar_codigos_saida([2, 4]) == 4
    assert combinar_codigos_saida([4, 3]) == 3
    assert combinar_codigos_saida([3, 5, 4, 2, 1, 0]) == 5


def test_daemon_ler_listar_telemetria_e_cursor_por_sujeito() -> None:
    telemetria: list[dict[str, Any]] = []
    morada = _MoradaSimulada({"ato:ler": b"linha 1\nlinha 2\n", "ato:escrever": b"esc\n"})
    daemon = DaemonLeitor(
        moradas=RegistroMoradas({"git": morada}),
        vista=_vista_teste(),
        uids_autorizados=frozenset({os.getuid()}),
        ler_release=lambda: "rel-abc",
        telemetria=telemetria.append,
        segredo_cursor=b"segredo-fixo-teste",
    )
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        sock = Path(tmp) / "leitor.sock"
        th = _subir_daemon(daemon, sock)
        try:
            cli = ClienteLeitor(sock)
            resp = cli.ler(_ctx(), ["ato:ler"])
            assert resp["ok"] is True
            assert resp["exit_code"] == 0
            assert resp["release"] == "rel-abc"
            assert "ato:ler · versão v1" in resp["resultado"]["cabecalho"]
            assert resp["resultado"]["conteudo"] == "linha 1\nlinha 2\n"
            assert telemetria[-1]["release"] == "rel-abc"
            assert telemetria[-1]["morada"] == "git"
            assert telemetria[-1]["conta_chamadora"]

            # Listar com cursor amarrado ao sujeito
            p1 = cli.listar(_ctx(sujeito="alice"), "ato", limite=1)
            assert p1["ok"] is True
            assert p1["resultado"]["parcial"] is True
            cur = p1["resultado"]["cursor"]
            assert cur

            # Mesmo sujeito avança para página 2
            p2 = cli.listar(_ctx(sujeito="alice"), "ato", limite=1, cursor=cur)
            assert p2["ok"] is True
            assert len(p2["resultado"]["itens"]) == 1

            # Outro sujeito reusando cursor sai 2 continuacao-divergente
            p_outro = cli.listar(_ctx(sujeito="bob"), "ato", limite=1, cursor=cur)
            assert p_outro["ok"] is False
            assert p_outro["exit_code"] == 2
            assert p_outro["recusa"]["codigo"] == "continuacao-divergente"
        finally:
            daemon.parar()
            th.join(timeout=2.0)


def test_multi_chave_estagio5_negada_exista_ou_nao_e_chamador_nao_autorizado() -> None:
    morada = _MoradaSimulada({"ato:ok": b"valido\n", "ato:segredo-ok": b"nao-deve-ler\n"})
    negadas = {"ato:segredo-ok", "ato:nao-existe-negada"}

    def _autorizar(_suj: str, _verbo: str, _forma: str, _cl: str, chave: str) -> bool:
        return chave not in negadas

    daemon = DaemonLeitor(
        moradas=RegistroMoradas({"git": morada}),
        vista=_vista_teste(),
        uids_autorizados=frozenset({os.getuid()}),
        autorizador=_autorizar,
        ler_release=lambda: "rel-1",
        telemetria=lambda _e: None,
    )
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        sock = Path(tmp) / "leitor.sock"
        th = _subir_daemon(daemon, sock)
        try:
            cli = ClienteLeitor(sock)
            # Multi-chave: ok + duplicada + inexistente (1) + negada existente (4) + negada inexistente (4)
            resp = cli.ler(
                _ctx(),
                ["ato:ok", "ato:ok", "ato:falta", "ato:segredo-ok", "ato:nao-existe-negada"],
            )
            assert resp["exit_code"] == 4
            assert resp["resumo"]["total"] == 5
            assert resp["resumo"]["ok"] == 2
            assert [it["exit_code"] for it in resp["itens"]] == [0, 0, 1, 4, 4]
            # Nenhuma chave negada abriu a morada; duplicada executou só uma vez
            assert morada.chamadas.count("ato:ok") == 1
            assert "ato:segredo-ok" not in morada.chamadas
            assert "ato:nao-existe-negada" not in morada.chamadas

            # Precedência 5 > 3 > 4 > 1
            resp_p = cli.ler(_ctx(), ["ato:ok", "ato:erro3", "ato:erro5", "ato:segredo-ok"])
            assert resp_p["exit_code"] == 5
        finally:
            daemon.parar()
            th.join(timeout=2.0)

    # Chamador não autorizado no SO_PEERCRED sai 4 sem abrir morada
    morada2 = _MoradaSimulada({"ato:ok": b"valido\n"})
    daemon_unauth = DaemonLeitor(
        moradas=RegistroMoradas({"git": morada2}),
        vista=_vista_teste(),
        uids_autorizados=frozenset({os.getuid() + 9999}),
        ler_release=lambda: "rel-1",
        telemetria=lambda _e: None,
    )
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        sock = Path(tmp) / "leitor.sock"
        th = _subir_daemon(daemon_unauth, sock)
        try:
            resp_u = ClienteLeitor(sock).ler(_ctx(), ["ato:ok"])
            assert resp_u["ok"] is False
            assert resp_u["exit_code"] == 4
            assert resp_u["recusa"]["codigo"] == "acesso-negado"
            assert morada2.chamadas == []
        finally:
            daemon_unauth.parar()
            th.join(timeout=2.0)


def test_vagas_pesadas_leitor_ocupado_saida_3() -> None:
    morada = _MoradaSimulada({"ato:pesado": b"dados\n"})
    morada.barreira_inicio = threading.Event()
    morada.barreira_liberar = threading.Event()

    daemon = DaemonLeitor(
        moradas=RegistroMoradas({"git": morada}),
        vista=_vista_teste(),
        uids_autorizados=frozenset({os.getuid()}),
        vagas_pesadas=1,
        espera_vaga_ms=80,
        ler_release=lambda: "rel-1",
        telemetria=lambda _e: None,
    )
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        sock = Path(tmp) / "leitor.sock"
        th = _subir_daemon(daemon, sock)
        try:
            cli = ClienteLeitor(sock)
            res_primeira: list[dict[str, Any]] = []

            def _rodar_primeira() -> None:
                res_primeira.append(cli.ler(_ctx(), ["ato:pesado"], pesada=True))

            t1 = threading.Thread(target=_rodar_primeira)
            t1.start()
            assert morada.barreira_inicio.wait(timeout=2.0)

            # Segunda leitura pesada encontra vaga cheia -> saída 3 leitor-ocupado
            res_segunda = cli.ler(_ctx(), ["ato:pesado"], pesada=True)
            assert res_segunda["ok"] is False
            assert res_segunda["exit_code"] == 3
            assert res_segunda["recusa"]["codigo"] == "leitor-ocupado"
            assert res_segunda["recusa"]["proximo"] == "busca ler ato:pesado"

            morada.barreira_liberar.set()
            t1.join(timeout=2.0)
            assert res_primeira[0]["ok"] is True
        finally:
            morada.barreira_liberar.set()
            daemon.parar()
            th.join(timeout=2.0)


def test_cliente_repeticao_unica_em_queda_e_troca_de_release() -> None:
    # 1. Queda na primeira conexão, sucesso na repetição única
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        sock_path = Path(tmp) / "flaky.sock"
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(sock_path))
        srv.listen(4)
        tentativas = {"n": 0}

        def _servir_duas() -> None:
            for i in range(2):
                conn, _ = srv.accept()
                tentativas["n"] += 1
                if i == 0:
                    # Derruba conexão na primeira tentativa
                    conn.close()
                else:
                    _ = receber_quadro_json(conn)
                    enviar_quadro_json(conn, {"ok": True, "exit_code": 0, "release": "rel-nova"})
                    conn.close()

        t = threading.Thread(target=_servir_duas, daemon=True)
        t.start()
        try:
            resp = ClienteLeitor(sock_path).ler(_ctx(), ["ato:ok"])
            assert resp["ok"] is True
            assert resp["release"] == "rel-nova"
            assert tentativas["n"] == 2
        finally:
            t.join(timeout=2.0)
            srv.close()

    # 2. Soquete ausente sai 3 morada-sem-resposta (nunca 5)
    with pytest.raises(ErroClienteLeitor) as exc_aus:
        ClienteLeitor(Path("/tmp/nao-existe-leitor-4442.sock")).ler(_ctx(), ["ato:ok"])
    assert exc_aus.value.saida == 3
    assert exc_aus.value.recusa.codigo == "morada-sem-resposta"

    # 3. Troca de release recicla o daemon e nova instância serve na release nova
    release_atual = {"v": "rel-1"}
    with tempfile.TemporaryDirectory(prefix="leitor-t7-") as tmp:
        raiz_git = Path(tmp) / "rel"
        (raiz_git / "ato").mkdir(parents=True)
        (raiz_git / "ato" / "ler.md").write_text("ok\n", encoding="utf-8")
        sock = Path(tmp) / "leitor.sock"

        d1 = DaemonLeitor(
            moradas=RegistroMoradas({"git": AdaptadorGit(raiz_git)}),
            vista=_vista_teste(),
            uids_autorizados=frozenset({os.getuid()}),
            ler_release=lambda: release_atual["v"],
            telemetria=lambda _e: None,
        )
        t1 = _subir_daemon(d1, sock)
        r1 = ClienteLeitor(sock).ler(_ctx(), ["ato:ler"])
        assert r1["ok"] is True
        assert r1["release"] == "rel-1"

        # Promove release: d1 detecta mudança na próxima conexão e sai sem servir release velha
        release_atual["v"] = "rel-2"
        with pytest.raises(ErroClienteLeitor) as exc_rec:
            ClienteLeitor(sock).ler(_ctx(), ["ato:ler"])
        assert exc_rec.value.saida == 3
        t1.join(timeout=2.0)
        assert d1.release_mudou is True

        # Nova instância sobe já na release nova
        d2 = DaemonLeitor(
            moradas=RegistroMoradas({"git": AdaptadorGit(raiz_git)}),
            vista=_vista_teste(),
            uids_autorizados=frozenset({os.getuid()}),
            ler_release=lambda: release_atual["v"],
            telemetria=lambda _e: None,
        )
        t2 = _subir_daemon(d2, sock)
        try:
            r2 = ClienteLeitor(sock).ler(_ctx(), ["ato:ler"])
            assert r2["ok"] is True
            assert r2["release"] == "rel-2"
        finally:
            d2.parar()
            t2.join(timeout=2.0)
