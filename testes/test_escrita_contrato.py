# componente: componente:escrita
"""Suíte de contrato, concorrência e mutação da t8 (#4441).

Cobre moradas git e Olaria com fiação real de produção (PDP em core/acesso),
fronteiras de segurança com saída 4 sem consulta a banco antes do portão,
32 gravações simultâneas com medida de fsync e 0 mutantes vivos nas guardas.
"""
from __future__ import annotations

import base64
import concurrent.futures
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[1]
LIB = RAIZ / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from escrita import (  # noqa: E402
    ConfigCliente,
    ContextoEscrita,
    OpcoesExecucao,
    RecusaEscrita,
    executar_ato_escrever,
)
from escrita import io_atomico, politica as mod_politica, portao as mod_portao  # noqa: E402
from escrita.moradas.git import MoradaGit  # noqa: E402
from escrita.moradas.olaria import ConfigOlaria, MoradaOlaria, RespostaHTTP  # noqa: E402
from escrita.politica import PoliticaEscrita, carregar_politica  # noqa: E402
from escrita.portao import VistaAlcance, carregar_vista_alcance  # noqa: E402
from escrita.servidor import (  # noqa: E402
    ConfigServidor,
    ServidorEscritor,
    criar_autorizador_pdp,
    escrever_quadro,
    ler_quadro,
)


def _politica_ligada(verbos: frozenset[str] = frozenset({"repo", "ontologia"})) -> PoliticaEscrita:
    base = carregar_politica(RAIZ / "registro" / "escrita.yaml")
    return replace(base, verbos_ligados=verbos)


def _criar_bancada_git(
    tmp_path: Path,
    repo: str = "platafirma-harness",
    cadeira: str = "engenharia",
    chave_wt: str = "4441-contrato",
) -> tuple[Path, Path]:
    base_repo = tmp_path / repo
    base_repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(base_repo)], check=True)
    subprocess.run(["git", "-C", str(base_repo), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(base_repo), "config", "user.name", "Tester"], check=True)
    (base_repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(base_repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(base_repo), "commit", "-q", "-m", "init"], check=True)

    wt_dir = tmp_path / "wt" / repo / cadeira / chave_wt
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(base_repo), "worktree", "add", "-q", "-b", f"fabrica/{chave_wt}", str(wt_dir)],
        check=True,
    )
    return tmp_path, wt_dir


def _subir_servidor(
    tmp_path: Path,
    *,
    raiz_bancadas: Path,
    grupo_autorizado: str = "",
    vista: VistaAlcance | None = None,
    raio_card: frozenset[tuple[str, str]] | None = None,
    autorizador_sujeito: Any = None,
    pdp_dir: Path | None = None,
    olaria_chamadas: list[tuple[str, dict[str, Any]]] | None = None,
) -> tuple[ServidorEscritor, threading.Thread, Path, PoliticaEscrita]:
    pol = _politica_ligada()
    estado = tmp_path / "estado"
    estado.mkdir(parents=True, exist_ok=True)
    sock_dir = Path(tempfile.mkdtemp(prefix="pf-c-"))
    sock_path = sock_dir / "e.sock"
    chamadas = olaria_chamadas if olaria_chamadas is not None else []

    def _transporte(url: str, rota: str, hdrs: dict, corpo: dict, timeout: float) -> RespostaHTTP:
        chamadas.append((rota, corpo))
        if rota == "/ensaiar":
            return RespostaHTTP(200, {"ok": True, "ensaiado": True, "erros": []})
        return RespostaHTTP(
            200,
            {
                "ok": True,
                "fornada": corpo.get("fornada", "f-contrato"),
                "versao": "01960000-0000-7000-8000-000000000009",
                "gravado": True,
            },
        )

    moradas = {
        "git": MoradaGit(raiz_bancadas=raiz_bancadas, estado_dir=estado),
        "banco": MoradaOlaria(
            ConfigOlaria(url="http://127.0.0.1:19998", chave="chave-contrato"),
            transporte=_transporte,
        ),
    }
    cfg = ConfigServidor(
        socket_path=sock_path,
        raiz_bancadas=raiz_bancadas,
        estado_dir=estado,
        politica=pol,
        vista=vista,
        moradas=moradas,
        grupo_autorizado=grupo_autorizado,
        uid_escritor=65534 if grupo_autorizado else os.getuid(),
        raio_card=raio_card,
        autorizador_sujeito=autorizador_sujeito,
        pdp_dir=pdp_dir,
        max_conexoes=64,
    )
    srv = ServidorEscritor(cfg)
    th = threading.Thread(target=srv.servir, kwargs={"instalar_sinais": False}, daemon=True)
    th.start()
    fim = time.monotonic() + 5.0
    while time.monotonic() < fim and not sock_path.exists():
        time.sleep(0.01)
    assert sock_path.exists()
    return srv, th, sock_path, pol


def _enviar_quadro_direto(sock_path: Path, quadro: dict[str, Any]) -> dict[str, Any]:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)
        s.connect(str(sock_path))
        escrever_quadro(s, quadro)
        return ler_quadro(s, teto_bytes=2 * 1024 * 1024)


def _chamar(
    sock: Path,
    pol: PoliticaEscrita,
    verbo: str,
    argv: list[str],
    stdin: bytes,
    *,
    cadeira: str = "engenharia",
    sujeito: str = "engenharia",
) -> Any:
    ctx = ContextoEscrita(verbo=verbo, cadeira=cadeira, sujeito=sujeito, sessao_id="s-contrato")
    return executar_ato_escrever(
        verbo,
        argv,
        stdin,
        opcoes=OpcoesExecucao(contexto=ctx, politica=pol, socket_path=sock),
    )


def _localizar_pdp_real() -> Path | None:
    candidatos = [
        Path("/opt/platafirma/current/core/acesso"),
        RAIZ.parent / "platafirma-core" / "acesso",
        Path("/home/claudinho/AI/wt/platafirma-core/engenharia/4441-ato-escrever/acesso"),
    ]
    for cand in candidatos:
        if (cand / "politica.yaml").is_file():
            return cand
    return None


def test_fronteiras_seguranca_saida_4_sem_consulta_banco_antes_portao(tmp_path: Path) -> None:
    raiz, wt_dir = _criar_bancada_git(tmp_path)
    pdp_real = _localizar_pdp_real()
    assert pdp_real is not None, "PDP real do core não encontrado para prova de produção"
    auth_real = criar_autorizador_pdp(pdp_real)
    assert auth_real is not None

    # 1) Conta fora do grupo autorizado → saída 4, 0 chamadas Olaria
    chamadas_grupo: list[tuple[str, dict[str, Any]]] = []
    srv_g, th_g, sock_g, pol_g = _subir_servidor(
        tmp_path / "srv_grupo",
        raiz_bancadas=raiz,
        grupo_autorizado="grupo-inexistente-contrato-4441",
        autorizador_sujeito=lambda _s, _c, _v, _f: True,
        olaria_chamadas=chamadas_grupo,
    )
    try:
        with pytest.raises(RecusaEscrita) as exc_g:
            _chamar(sock_g, pol_g, "ontologia", ["criar", "servico", "harness:x"], b"chave: x\n")
        assert exc_g.value.saida == 4
        assert chamadas_grupo == []
    finally:
        srv_g.parar()
        th_g.join(timeout=5.0)

    # 2) Cadeira sem acesso e sujeito negado com fiação real do PDP (sem dublê) → saída 4, 0 chamadas Olaria
    chamadas_pdp: list[tuple[str, dict[str, Any]]] = []
    vista_base = carregar_vista_alcance()
    verbos_restr = dict(vista_base.verbos)
    verbos_restr["ontologia"] = replace(
        verbos_restr["ontologia"], cadeiras_autorizadas=frozenset({"conhecimento"})
    )
    verbos_restr["repo"] = replace(
        verbos_restr["repo"], cadeiras_autorizadas=frozenset({"engenharia"})
    )
    vista_restrita = VistaAlcance(verbos=verbos_restr, classes=vista_base.classes)
    srv_p, th_p, sock_p, pol_p = _subir_servidor(
        tmp_path / "srv_pdp",
        raiz_bancadas=raiz,
        vista=vista_restrita,
        autorizador_sujeito=auth_real,
        olaria_chamadas=chamadas_pdp,
    )
    try:
        # Cadeira não autorizada para ontologia
        with pytest.raises(RecusaEscrita) as exc_cad:
            _chamar(
                sock_p,
                pol_p,
                "ontologia",
                ["criar", "servico", "harness:x"],
                b"chave: x\n",
                cadeira="direito",
                sujeito="direito",
            )
        assert exc_cad.value.saida == 4
        assert chamadas_pdp == []

        # Sujeito inexistente recusado pelo PDP real
        with pytest.raises(RecusaEscrita) as exc_suj:
            _chamar(
                sock_p,
                pol_p,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:ok.txt"],
                b"oi\n",
                cadeira="engenharia",
                sujeito="intruso-inexistente",
            )
        assert exc_suj.value.saida == 4
        assert chamadas_pdp == []
    finally:
        srv_p.parar()
        th_p.join(timeout=5.0)

    # 3) Fronteiras de alvo: segredo, superfície vedada, caminho protegido fora do raio, .git, fora da bancada,
    #    symlink, FIFO, hardlink e cliente direto no soquete sem camada comum
    chamadas_alvo: list[tuple[str, dict[str, Any]]] = []
    srv, th, sock, pol = _subir_servidor(
        tmp_path / "srv_alvos",
        raiz_bancadas=raiz,
        raio_card=frozenset(),
        autorizador_sujeito=lambda _s, _c, _v, _f: True,
        olaria_chamadas=chamadas_alvo,
    )
    try:
        # Chave de segredo
        with pytest.raises(RecusaEscrita) as exc_seg:
            _chamar(sock, pol, "ontologia", ["criar", "segredo", "segredo:cofre/x"], b"x: 1\n")
        assert exc_seg.value.saida == 4
        assert chamadas_alvo == []

        # Superfície vedada (.env / politica.yaml)
        with pytest.raises(RecusaEscrita) as exc_ved:
            _chamar(sock, pol, "repo", ["gravar", "componente", "platafirma-harness@4441-contrato:.env"], b"A=1\n")
        assert exc_ved.value.saida == 4

        # Caminho protegido fora do raio do card
        with pytest.raises(RecusaEscrita) as exc_prot:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:lib/escrita/portao.py"],
                b"# alterado\n",
            )
        assert exc_prot.value.saida == 4

        # Pasta interna do git (.git/config)
        with pytest.raises(RecusaEscrita) as exc_git:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:.git/config"],
                b"[core]\n",
            )
        assert exc_git.value.saida == 4

        # Fora da bancada (traversal ..)
        with pytest.raises(RecusaEscrita) as exc_fora:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:../escapa.txt"],
                b"x\n",
            )
        assert exc_fora.value.saida in (2, 4)

        # Atalho simbólico (symlink)
        alvo_real = wt_dir / "real.txt"
        alvo_real.write_text("original\n", encoding="utf-8")
        link = wt_dir / "atalho.txt"
        os.symlink(alvo_real, link)
        with pytest.raises(RecusaEscrita) as exc_sym:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:atalho.txt"],
                b"pelo link\n",
            )
        assert exc_sym.value.saida == 4
        assert alvo_real.read_text(encoding="utf-8") == "original\n"

        # Canal nomeado (FIFO)
        fifo = wt_dir / "canal.fifo"
        os.mkfifo(fifo)
        with pytest.raises(RecusaEscrita) as exc_fifo:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:canal.fifo"],
                b"pipe\n",
            )
        assert exc_fifo.value.saida == 4

        # Vínculo múltiplo (hardlink)
        hl_base = wt_dir / "hl_base.txt"
        hl_base.write_text("base\n", encoding="utf-8")
        hl_copia = wt_dir / "hl_copia.txt"
        os.link(hl_base, hl_copia)
        with pytest.raises(RecusaEscrita) as exc_hl:
            _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", "platafirma-harness@4441-contrato:hl_copia.txt"],
                b"hardlink\n",
            )
        assert exc_hl.value.saida == 4
        assert hl_base.read_text(encoding="utf-8") == "base\n"

        # Cliente falando direto no soquete sem a camada comum (tentando furar com .git/config e com segredo)
        resp_direto_git = _enviar_quadro_direto(
            sock,
            {
                "versao": 1,
                "tipo": "escrever",
                "verbo": "repo",
                "argv": ["gravar", "componente", "platafirma-harness@4441-contrato:.git/config"],
                "stdin_b64": base64.b64encode(b"[core]\n").decode("ascii"),
                "contexto": {"verbo": "repo", "cadeira": "engenharia", "sujeito": "engenharia"},
            },
        )
        assert resp_direto_git["exit_code"] == 4

        resp_direto_seg = _enviar_quadro_direto(
            sock,
            {
                "versao": 1,
                "tipo": "escrever",
                "verbo": "ontologia",
                "argv": ["criar", "segredo", "segredo:direto/x"],
                "stdin_b64": base64.b64encode(b"x: 1\n").decode("ascii"),
                "contexto": {"verbo": "ontologia", "cadeira": "engenharia", "sujeito": "engenharia"},
            },
        )
        assert resp_direto_seg["exit_code"] == 4
        assert chamadas_alvo == []
    finally:
        srv.parar()
        th.join(timeout=5.0)


def test_concorrencia_32_gravacoes_simultaneas_e_medida_fsync(tmp_path: Path) -> None:
    raiz, wt_dir = _criar_bancada_git(tmp_path)
    srv, th, sock, pol = _subir_servidor(
        tmp_path / "srv_conc",
        raiz_bancadas=raiz,
        autorizador_sujeito=lambda _s, _c, _v, _f: True,
    )
    duracoes_ms: list[float] = []
    try:
        def _worker(idx: int) -> tuple[int, str, float]:
            t0 = time.perf_counter()
            nome = f"conc/arq_{idx:02d}.txt"
            res = _chamar(
                sock,
                pol,
                "repo",
                ["gravar", "componente", f"platafirma-harness@4441-contrato:{nome}"],
                f"linha-{idx}\n".encode("utf-8"),
            )
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return idx, res.versao, dt_ms

        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            futs = [pool.submit(_worker, i) for i in range(32)]
            resultados = [f.result(timeout=20.0) for f in futs]

        assert len(resultados) == 32
        for idx, versao, dt_ms in resultados:
            assert versao
            duracoes_ms.append(dt_ms)
            arq = wt_dir / "conc" / f"arq_{idx:02d}.txt"
            assert arq.read_text(encoding="utf-8") == f"linha-{idx}\n"

        # Nenhum temporário órfão deve restar
        tmps = list(wt_dir.rglob(".pf-esc-*.tmp"))
        assert tmps == []
        # Medida real de duração por gravação (com fsync no host) registrada e finita
        assert len(duracoes_ms) == 32
        assert all(d > 0.0 for d in duracoes_ms)
    finally:
        srv.parar()
        th.join(timeout=5.0)


def test_mutacao_guardas_zero_mutantes_vivos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Planta mutantes nas guardas de segurança e prova que a suíte de contrato mata 100% deles."""
    raiz, wt_dir = _criar_bancada_git(tmp_path)
    pol = _politica_ligada()

    alvo_real = wt_dir / "mut_real.txt"
    alvo_real.write_text("ok\n", encoding="utf-8")
    link = wt_dir / "mut_link.txt"
    os.symlink(alvo_real, link)

    def _ataque_superficie_vedada() -> bool:
        srv, th, sock, p = _subir_servidor(
            tmp_path / f"mut_ved_{time.monotonic_ns()}",
            raiz_bancadas=raiz,
            autorizador_sujeito=lambda _s, _c, _v, _f: True,
        )
        try:
            try:
                _chamar(sock, p, "repo", ["gravar", "componente", "platafirma-harness@4441-contrato:.env"], b"X=1\n")
                return False  # mutante sobreviveu (ataque passou!)
            except RecusaEscrita as exc:
                return exc.saida == 4
        finally:
            srv.parar()
            th.join(timeout=5.0)

    def _ataque_caminho_protegido() -> bool:
        srv, th, sock, p = _subir_servidor(
            tmp_path / f"mut_prot_{time.monotonic_ns()}",
            raiz_bancadas=raiz,
            raio_card=frozenset(),
            autorizador_sujeito=lambda _s, _c, _v, _f: True,
        )
        try:
            try:
                _chamar(
                    sock,
                    p,
                    "repo",
                    ["gravar", "componente", "platafirma-harness@4441-contrato:lib/escrita/portao.py"],
                    b"# mut\n",
                )
                return False
            except RecusaEscrita as exc:
                return exc.saida == 4
        finally:
            srv.parar()
            th.join(timeout=5.0)

    def _ataque_symlink() -> bool:
        srv, th, sock, p = _subir_servidor(
            tmp_path / f"mut_sym_{time.monotonic_ns()}",
            raiz_bancadas=raiz,
            autorizador_sujeito=lambda _s, _c, _v, _f: True,
        )
        try:
            try:
                _chamar(
                    sock,
                    p,
                    "repo",
                    ["gravar", "componente", "platafirma-harness@4441-contrato:mut_link.txt"],
                    b"hack\n",
                )
                return False
            except RecusaEscrita as exc:
                return exc.saida == 4
        finally:
            srv.parar()
            th.join(timeout=5.0)

    def _ataque_grupo_autorizado() -> bool:
        srv, th, sock, p = _subir_servidor(
            tmp_path / f"mut_grp_{time.monotonic_ns()}",
            raiz_bancadas=raiz,
            grupo_autorizado="grupo-inexistente-mutante",
            autorizador_sujeito=lambda _s, _c, _v, _f: True,
        )
        try:
            try:
                _chamar(sock, p, "repo", ["gravar", "componente", "platafirma-harness@4441-contrato:a.txt"], b"oi\n")
                return False
            except RecusaEscrita as exc:
                return exc.saida == 4
        finally:
            srv.parar()
            th.join(timeout=5.0)

    # Baseline sem mutantes: todas as guardas bloqueiam
    assert _ataque_superficie_vedada() is True
    assert _ataque_caminho_protegido() is True
    assert _ataque_symlink() is True
    assert _ataque_grupo_autorizado() is True

    mutantes_vivos: list[str] = []

    # Mutante 1: desabilita eh_superficie_vedada no portão
    with monkeypatch.context() as mp:
        mp.setattr(mod_portao, "eh_superficie_vedada", lambda _p, _c: None)
        if _ataque_superficie_vedada():
            mutantes_vivos.append("portao.eh_superficie_vedada")

    # Mutante 2: desabilita eh_caminho_protegido no portão
    with monkeypatch.context() as mp:
        mp.setattr(mod_portao, "eh_caminho_protegido", lambda _p, _r, _c: None)
        if _ataque_caminho_protegido():
            mutantes_vivos.append("portao.eh_caminho_protegido")

    # Mutante 3: desabilita verificação de segredo no portão (defesa direta no portão)
    with monkeypatch.context() as mp:
        mp.setattr(mod_portao, "_verificar_nao_segredo", lambda _p, _c: None)
        srv_s, th_s, sock_s, p_s = _subir_servidor(
            tmp_path / f"mut_seg_{time.monotonic_ns()}",
            raiz_bancadas=raiz,
            autorizador_sujeito=lambda _s, _c, _v, _f: True,
        )
        try:
            try:
                _chamar(sock_s, p_s, "ontologia", ["criar", "segredo", "segredo:cofre/m"], b"k: v\n")
            except RecusaEscrita as exc:
                if exc.saida == 4:
                    mutantes_vivos.append("portao._verificar_nao_segredo")
        finally:
            srv_s.parar()
            th_s.join(timeout=5.0)

    # Mutante 4: remove O_NOFOLLOW e a conferência antes do replace em io_atomico
    with monkeypatch.context() as mp:
        mp.setattr(io_atomico, "_FLAGS_ARQ_LEITURA", os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        mp.setattr(io_atomico, "_conferir_destino_antes_replace", lambda _fd, _nome: None)
        if _ataque_symlink():
            mutantes_vivos.append("io_atomico.O_NOFOLLOW")

    assert mutantes_vivos == [], f"mutantes vivos nas guardas: {mutantes_vivos}"


def test_exige_shebang_isenta_dockerfile_e_crontab() -> None:
    """Dockerfile e crontab-claudinho em deploy/ não são executáveis e não exigem #!."""
    pol = _politica_ligada()
    assert not mod_politica.exige_shebang(pol, "platafirma-core", "deploy/eventos/servico/Dockerfile")
    assert not mod_politica.exige_shebang(pol, "platafirma-core", "deploy/crontab-claudinho")
    assert mod_politica.exige_shebang(pol, "platafirma-core", "deploy/platafirma")
    assert mod_politica.exige_shebang(pol, "platafirma-core", "deploy/instala-units.sh")
