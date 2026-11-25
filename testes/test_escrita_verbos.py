"""Provas herméticas da t7 (#4441): repo gravar, repo abrir/clonar, repo commitar, ontologia e write_file."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LIB = RAIZ / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from escrita.moradas.git import MoradaGit  # noqa: E402
from escrita.moradas.olaria import ConfigOlaria, MoradaOlaria, RespostaHTTP  # noqa: E402
from escrita.politica import carregar_politica  # noqa: E402
from escrita.registro import RegistroOperacoes  # noqa: E402
from escrita.servidor import ConfigServidor, ServidorEscritor  # noqa: E402

BIN_REPO = RAIZ / "bin" / "repo"
BIN_ONTOLOGIA = RAIZ / "bin" / "ontologia"
BIN_WRITE_FILE = RAIZ / "bin" / "write_file"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _criar_origem_git(tmp_path: Path, nome: str = "platafirma-harness") -> Path:
    bare = tmp_path / "remoto" / f"{nome}.git"
    bare.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", str(bare), str(seed)], check=True, capture_output=True)
    _git(seed, "config", "user.name", "Teste")
    _git(seed, "config", "user.email", "teste@platafirma.local")
    (seed / "README.md").write_text("# inicio\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "inicial")
    _git(seed, "push", "-u", "origin", "main")
    return bare


def _iniciar_servidor(
    tmp_path: Path,
    *,
    verbos_ligados: tuple[str, ...],
    raiz_wt: Path,
    estado_dir: Path,
    olaria_handler=None,
) -> tuple[ServidorEscritor, threading.Thread, Path, Path]:
    cfg_yaml = tmp_path / "escrita-test.yaml"
    pol_base = (RAIZ / "registro" / "escrita.yaml").read_text(encoding="utf-8")
    lista = "[" + ", ".join(verbos_ligados) + "]"
    cfg_yaml.write_text(pol_base.replace("verbos_ligados: []", f"verbos_ligados: {lista}"), encoding="utf-8")
    pol = carregar_politica(cfg_yaml)
    sock_path = tmp_path / "escritor.sock"
    estado_dir.mkdir(parents=True, exist_ok=True)

    moradas = {"git": MoradaGit(raiz_bancadas=raiz_wt, estado_dir=estado_dir)}
    if olaria_handler is not None:
        moradas["banco"] = MoradaOlaria(
            ConfigOlaria(url="http://127.0.0.1:19999", chave="chave-teste"),
            transporte=olaria_handler,
        )
    cfg = ConfigServidor(
        socket_path=sock_path,
        raiz_bancadas=raiz_wt,
        estado_dir=estado_dir,
        politica=pol,
        moradas=moradas,
        grupo_autorizado="",
        uid_escritor=os.getuid(),
        autorizador_sujeito=lambda _s, _c, _v, _f: True,
    )
    srv = ServidorEscritor(cfg)
    th = threading.Thread(target=srv.servir, kwargs={"instalar_sinais": False}, daemon=True)
    th.start()
    fim = time.monotonic() + 5.0
    while time.monotonic() < fim and not sock_path.exists():
        time.sleep(0.02)
    assert sock_path.exists(), "soquete do escritor não subiu a tempo"
    return srv, th, sock_path, cfg_yaml


def _parar_servidor(srv: ServidorEscritor, th: threading.Thread) -> None:
    srv.parar()
    th.join(timeout=5.0)


def _preparar_wt_para_escritor(tmp_path: Path, repo_nome: str = "platafirma-harness", cadeira: str = "engenharia") -> tuple[Path, Path]:
    bancada = tmp_path / "bancada"
    bancada.mkdir(parents=True, exist_ok=True)
    bare = _criar_origem_git(tmp_path, repo_nome)
    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": cadeira,
        "PF_SESSAO": "sessao-t7-1",
    }
    res_clonar = subprocess.run(
        [str(BIN_REPO), "clonar", str(bare), repo_nome],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_clonar.returncode == 0, res_clonar.stderr
    wt_dir = bancada / "wt" / repo_nome / cadeira / "4441-t7"
    wt_dir.parent.mkdir(parents=True, exist_ok=True)
    _git(bancada / repo_nome, "worktree", "add", "-b", "fabrica/4441-t7", str(wt_dir), "origin/main")
    return bancada, wt_dir


def test_repo_abrir_e_clonar_configuram_setgid_e_exclusao_temporarios(tmp_path: Path) -> None:
    bancada = tmp_path / "bancada"
    bancada.mkdir()
    bare = _criar_origem_git(tmp_path, "demo-repo")
    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": "engenharia",
        "PF_SESSAO": "sessao-t7-abrir",
    }
    r_clone = subprocess.run(
        [str(BIN_REPO), "clonar", str(bare), "demo-repo"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_clone.returncode == 0, r_clone.stderr
    clone_dir = bancada / "demo-repo"
    assert stat.S_IMODE(clone_dir.stat().st_mode) & stat.S_ISGID
    exc_clone = Path(_git(clone_dir, "rev-parse", "--git-path", "info/exclude").stdout.strip())
    if not exc_clone.is_absolute():
        exc_clone = clone_dir / exc_clone
    assert ".pf-esc-*.tmp" in exc_clone.read_text(encoding="utf-8").splitlines()

    r_abrir = subprocess.run(
        [str(BIN_REPO), "abrir", "demo-repo", "--slug", "t7", "--sem-mover"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r_abrir.returncode == 0, r_abrir.stderr
    wt_dir = bancada / "wt" / "demo-repo" / "engenharia" / "t7"
    assert wt_dir.is_dir()
    assert stat.S_IMODE(wt_dir.stat().st_mode) & stat.S_ISGID
    (wt_dir / ".pf-esc-abc123.tmp").write_text("temp\n", encoding="utf-8")
    st = _git(wt_dir, "status", "--porcelain").stdout.strip()
    assert st == ""


def test_repo_gravar_ligado_e_commitar_sem_lista_lendo_registro_escritor(tmp_path: Path) -> None:
    bancada, wt_dir = _preparar_wt_para_escritor(tmp_path, "demo-repo", "engenharia")
    estado = tmp_path / "estado"
    srv, th, sock, cfg_yaml = _iniciar_servidor(
        tmp_path,
        verbos_ligados=("repo",),
        raiz_wt=bancada,
        estado_dir=estado,
    )
    try:
        env = {
            **os.environ,
            "PLATAFIRMA_BANCADA": str(bancada),
            "PF_CADEIRA": "engenharia",
            "PF_SUJEITO": "engenharia",
            "PF_SESSAO": "sessao-t7-commit",
            "PF_CARD": "4441",
            "PF_ESCRITOR_SOCKET": str(sock),
            "PF_ESCRITA_CONFIG": str(cfg_yaml),
            "PF_ESCRITA_REGISTRO": str(estado / "operacoes.jsonl"),
        }
        r_gravar = subprocess.run(
            [str(BIN_REPO), "gravar", "componente", "demo-repo@4441-t7:notas.txt", "--json"],
            input="conteudo gravado pelo escritor\n",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_gravar.returncode == 0, f"stderr={r_gravar.stderr} stdout={r_gravar.stdout}"
        dados = json.loads(r_gravar.stdout)
        assert dados["ok"] is True
        assert (wt_dir / "notas.txt").read_text(encoding="utf-8") == "conteudo gravado pelo escritor\n"

        _git(wt_dir, "config", "user.name", "Teste")
        _git(wt_dir, "config", "user.email", "teste@platafirma.local")
        r_commit = subprocess.run(
            [str(BIN_REPO), "commitar", "demo-repo@4441-t7", "-m", "4441: grava notas via escritor"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_commit.returncode == 0, f"stderr={r_commit.stderr} stdout={r_commit.stdout}"
        arquivos_commit = _git(wt_dir, "show", "--name-only", "--pretty=format:", "HEAD").stdout.splitlines()
        assert "notas.txt" in arquivos_commit
    finally:
        _parar_servidor(srv, th)


def test_verbos_desligados_operam_sem_escritor_e_repo_gravar_sai_3(tmp_path: Path) -> None:
    pol_prod = carregar_politica(RAIZ / "registro" / "escrita.yaml")
    assert pol_prod.verbos_ligados == frozenset()
    env = {
        **os.environ,
        "PF_CADEIRA": "engenharia",
        "PF_ESCRITOR_SOCKET": str(tmp_path / "inexistente.sock"),
    }
    r = subprocess.run(
        [str(BIN_REPO), "gravar", "componente", "demo-repo:a.txt"],
        input="oi\n",
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 3
    err = json.loads(r.stderr.strip().splitlines()[-1])
    codigo = err.get("codigo") or (err.get("erro") or {}).get("codigo")
    assert codigo == "escritor-indisponivel"


def test_ontologia_ligada_usa_escritor_e_ensaiar_nao_grava(tmp_path: Path) -> None:
    chamadas: list[tuple[str, dict]] = []

    def _transporte(url: str, rota: str, hdrs: dict, corpo: dict, timeout: float) -> RespostaHTTP:
        chamadas.append((rota, corpo))
        if rota == "/ensaiar":
            return RespostaHTTP(200, {"ok": True, "ensaiado": True, "erros": []})
        return RespostaHTTP(
            200,
            {
                "ok": True,
                "fornada": corpo.get("fornada", "f-1"),
                "versao": "01960000-0000-7000-8000-000000000002",
                "gravado": True,
            },
        )

    estado = tmp_path / "estado"
    srv, th, sock, cfg_yaml = _iniciar_servidor(
        tmp_path,
        verbos_ligados=("ontologia",),
        raiz_wt=tmp_path / "wt",
        estado_dir=estado,
        olaria_handler=_transporte,
    )
    try:
        yaml_arq = tmp_path / "ficha.yaml"
        yaml_arq.write_text("classe: servico\nchave: harness:escritor\n", encoding="utf-8")
        env = {
            **os.environ,
            "PF_CADEIRA": "engenharia",
            "PF_SUJEITO": "engenharia",
            "PF_SESSAO": "sessao-t7-ont",
            "PF_ESCRITOR_SOCKET": str(sock),
            "PF_ESCRITA_CONFIG": str(cfg_yaml),
        }
        r_ens = subprocess.run(
            [str(BIN_ONTOLOGIA), "ensaiar", "criar", "servico", "harness:escritor", str(yaml_arq), "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_ens.returncode == 0, f"stderr={r_ens.stderr} stdout={r_ens.stdout}"
        d_ens = json.loads(r_ens.stdout)
        assert d_ens["ensaiado"] is True
        assert RegistroOperacoes(estado / "operacoes.jsonl").listar() == []

        r_criar = subprocess.run(
            [str(BIN_ONTOLOGIA), "criar", "servico", "harness:escritor", str(yaml_arq), "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert r_criar.returncode == 0, f"stderr={r_criar.stderr} stdout={r_criar.stdout}"
        d_criar = json.loads(r_criar.stdout)
        assert d_criar["ok"] is True
        linhas = RegistroOperacoes(estado / "operacoes.jsonl").listar()
        assert len(linhas) == 1
        assert linhas[0].morada == "banco"
    finally:
        _parar_servidor(srv, th)


def test_write_file_depreciado_grava_avisa_sucessor_e_marca_contorno(tmp_path: Path) -> None:
    bancada = tmp_path / "bancada"
    wt_dir = bancada / "wt" / "platafirma-harness" / "engenharia" / "4441"
    wt_dir.mkdir(parents=True)
    alvo = wt_dir / "legado.txt"
    contorno_log = tmp_path / "contorno.jsonl"
    req = {
        "path": str(alvo),
        "content": "via legado\n",
        "bancada": str(bancada),
        "cadeira": "engenharia",
        "ordem_id": "ord-t7",
    }
    env = {
        **os.environ,
        "PF_CADEIRA": "engenharia",
        "PF_CONTORNO_LOG": str(contorno_log),
    }
    r = subprocess.run(
        [str(BIN_WRITE_FILE)],
        input=json.dumps(req),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, f"stderr={r.stderr} stdout={r.stdout}"
    assert "depreciado" in r.stderr.lower()
    assert "repo gravar" in r.stderr
    res = json.loads(r.stdout)
    assert res["ok"] is True
    assert res["contorno"] is True
    assert res["sucessor"] == "repo gravar"
    assert alvo.read_text(encoding="utf-8") == "via legado\n"
    linhas_log = [json.loads(ln) for ln in contorno_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(linhas_log) == 1
    assert linhas_log[0]["contorno"] is True
    assert linhas_log[0]["sucessor"] == "repo gravar"
