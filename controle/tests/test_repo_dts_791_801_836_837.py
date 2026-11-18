"""Cobertura dos DTs 791, 801, 836 e 837 em bin/repo."""

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN_REPO = RAIZ / "bin" / "repo"
IDENT = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(*args: str, cwd: Path | None = None) -> str:
    env = {**os.environ, **IDENT}
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return proc.stdout.strip()


def _montar(tmp_path: Path, nome: str = "demo", arquivos: dict[str, str] | None = None) -> Path:
    origem = tmp_path / f"{nome}-origem.git"
    semente = tmp_path / f"{nome}-semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    for rel, conteudo in (arquivos or {"LEIA.md": "x\n"}).items():
        destino = semente / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    _git("add", ".", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir(exist_ok=True)
    _git("clone", str(origem), str(bancada / nome))
    return bancada


def _publicar_producao(tmp_path: Path, bancada: Path, nome: str = "demo") -> str:
    sha = _git("rev-parse", "HEAD", cwd=bancada / nome)
    fam = tmp_path / "release" / nome
    (fam / sha).mkdir(parents=True)
    (fam / "current").symlink_to(fam / sha)
    return sha


def _repo(tmp_path: Path, bancada: Path, *args, sessao: str = "s1"):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "engenharia",
        "PF_SESSAO": sessao,
        "PF_TAREFAS_BIN": "/bin/true",
        **IDENT,
    }
    return subprocess.run(
        ["bash", str(BIN_REPO), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_dt801_abrir_da_producao_com_slug_sem_card(tmp_path: Path) -> None:
    """DT-801: --da-producao com --slug sem card abre ramo <cadeira>/<slug> no sha de producao."""
    bancada = _montar(tmp_path)
    sha = _publicar_producao(tmp_path, bancada)

    r = _repo(tmp_path, bancada, "abrir", "demo", "--da-producao", "--slug", "dt-798")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "dt-798"
    assert (wt / ".git").exists()
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt) == "engenharia/dt-798"
    assert _git("rev-parse", "HEAD", cwd=wt) == sha

    r_inv = _repo(tmp_path, bancada, "abrir", "demo", "--da-producao", "--slug", "-invalido")
    assert r_inv.returncode == 2


def test_dt791_abrir_mantem_executor_formalizado(tmp_path: Path) -> None:
    """DT-791: repo abrir move story para em-refinamento-tecnico sem sobrescrever executor ja definido."""
    bancada = _montar(tmp_path)
    log = tmp_path / "tarefas.log"
    tarefas_mock = tmp_path / "tarefas-mock"
    tarefas_mock.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "log = os.environ['TAREFAS_LOG']\n"
        "with open(log, 'a', encoding='utf-8') as f:\n"
        "    f.write(' '.join(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['api', 'GET']:\n"
        "    print(json.dumps({'classe': 'tecnico', 'nivel_nome': 'story', 'estado': 'priorizada', "
        "'estado_fase': 'execucao', 'cadeira': 'gestao-estrategica', 'executor': 'engenharia'}))\n"
        "elif sys.argv[1] == 'mover':\n"
        "    print('movido')\n",
        encoding="utf-8",
    )
    tarefas_mock.chmod(0o755)

    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "gestao-estrategica",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": str(tarefas_mock),
        "TAREFAS_LOG": str(log),
        **IDENT,
    }
    r = subprocess.run(
        ["bash", str(BIN_REPO), "abrir", "demo", "4334"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "executor mantido (engenharia)" in r.stdout
    assert "card #4334: em-refinamento-tecnico" in r.stdout
    chamadas = log.read_text(encoding="utf-8").splitlines()
    assert not any(c.startswith("editar ") for c in chamadas), chamadas


def test_dt836_commitar_multiplos_m_preserva_paragrafos_na_ordem(tmp_path: Path) -> None:
    """DT-836: cada -m em repo commitar vira um paragrafo da mensagem, na ordem."""
    bancada = _montar(tmp_path)
    r_open = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "dt-msg")
    assert r_open.returncode == 0, r_open.stderr
    wt = bancada / "wt" / "demo" / "engenharia" / "dt-msg"

    (wt / "nota.txt").write_text("linha 1\n", encoding="utf-8")
    r_cm = _repo(
        tmp_path,
        bancada,
        "commitar",
        "demo",
        "-m",
        "titulo do commit",
        "-m",
        "Co-Authored-By: Par",
        "-m",
        "Claude-Session: s1",
        "nota.txt",
    )
    assert r_cm.returncode == 0, r_cm.stderr
    msg = _git("log", "-1", "--format=%B", cwd=wt)
    assert msg == "titulo do commit\n\nCo-Authored-By: Par\n\nClaude-Session: s1"

    (wt / "nota2.txt").write_text("linha 2\n", encoding="utf-8")
    r_tudo = _repo(
        tmp_path,
        bancada,
        "commitar",
        "demo",
        "--tudo",
        "-m",
        "segundo titulo",
        "-m",
        "corpo dois",
    )
    assert r_tudo.returncode == 0, r_tudo.stderr
    msg2 = _git("log", "-1", "--format=%B", cwd=wt)
    assert msg2 == "segundo titulo\n\ncorpo dois"


def test_dt837_procurar_padrao_com_hifen_apos_repo(tmp_path: Path) -> None:
    """DT-837: repo procurar aceita padrao comecando com hifen apos <repo> sem exigir --."""
    bancada = _montar(
        tmp_path,
        arquivos={"dir1/a.txt": "ok\n--forcar aqui\n", "dir2/b.txt": "sem flag\n"},
    )
    assert _repo(tmp_path, bancada, "abrir", "demo", "--slug", "dt-busca").returncode == 0

    r1 = _repo(tmp_path, bancada, "procurar", "demo", "--forcar")
    assert r1.returncode == 0, r1.stderr
    assert "dir1/a.txt:2:--forcar aqui" in r1.stdout

    r2 = _repo(tmp_path, bancada, "procurar", "demo", "-F", "--forcar", "dir1")
    assert r2.returncode == 0, r2.stderr
    assert "dir1/a.txt:2:--forcar aqui" in r2.stdout

    r_err = _repo(tmp_path, bancada, "procurar", "--opcaoinvalida", "demo", "ok")
    assert r_err.returncode == 2
