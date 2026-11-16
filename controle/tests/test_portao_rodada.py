"""Rodada diária (--origin-main), teto do pequeno e isolamento de rede no verbo `teste` (#3732, DT #312)."""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from test_portao_degrau import DEGRAUS
from test_portao_familia import VERDE, VERMELHO, _arvore, _marca, _run
from test_portao_raio import _rodou, _tres


def _rodada(tmp_path, lista: str, suites: dict[str, str], tarefas_corpo: str | None = None):
    """Família `demo` com uma chave `a`, clonada para a bancada da rodada, e um `tarefas` de fixture
    que grava o que recebe e mantém um balde em arquivo (`dt listar` o lê, `dt admitir` acrescenta)."""
    env, arv = _arvore(tmp_path, {"a": suites}, {"a": lista})
    banc = tmp_path / "bancada"
    banc.mkdir()
    subprocess.run(["git", "clone", "-q", str(arv), str(banc / "demo")], check=True, capture_output=True)
    log, balde = tmp_path / "tarefas.log", tmp_path / "balde.txt"
    stub = tmp_path / "tarefas"
    stub.write_text(tarefas_corpo or (
        "#!/usr/bin/env bash\n"
        f'echo "$*" >> "{log}"\n'
        'case "$1 $2" in\n'
        f'  "dt listar") printf "n\\tidade\\tstack\\tdébito\\n"; cat "{balde}" 2>/dev/null; exit 0 ;;\n'
        f'  "dt admitir") printf "1\\t0d\\tk-a\\t%s\\n" "$3" >> "{balde}"; echo "débito 1 admitido"; exit 0 ;;\n'
        'esac\n'))
    stub.chmod(0o755)
    return dict(env, PLATAFIRMA_BANCADA=str(banc), PF_TESTE_SEM_MEMO="1", PF_TAREFAS_BIN=str(stub)), log, balde


def test_rodada_diaria_traz_o_tempo_de_cada_degrau_por_familia(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, log, _ = _rodada(tmp_path, "test_a1.py\ntest_a2.py | degrau: imagem\n",
                          {"test_a1.py": _marca(marcas, "a1"), "test_a2.py": _marca(marcas, "a2")})
    r = _run(env, "rodar", "demo", "--portao", "--origin-main")
    assert r.returncode == 0, r.stdout + r.stderr
    for deg in ("pequeno", "imagem", "rodada"):
        assert f"degrau {deg} de demo: " in r.stdout, r.stdout
    assert _rodou(marcas) == {"a1", "a2"}
    assert not log.exists(), "dentro do teto não se admite nada"


def test_rodada_diaria_mede_de_novo_e_nao_reaproveita_veredito(tmp_path):
    """Veredito reaproveitado mede 0 s: a rodada existe para medir, e a segunda leva a prova a rodar."""
    marcas = tmp_path / "marcas.txt"
    env, _, _ = _rodada(tmp_path, "test_a1.py\n", {"test_a1.py": _marca(marcas, "a1", 1)})
    env.pop("PF_TESTE_SEM_MEMO")
    for _ in range(2):
        r = _run(env, "rodar", "demo", "--portao", "--origin-main")
        assert r.returncode == 0, r.stdout + r.stderr
        assert _rodou(marcas) == {"a1"}, "a rodada não rodou a prova"
        assert "veredito reaproveitado" not in r.stdout + r.stderr, r.stdout
        marcas.unlink()


def test_pequeno_acima_do_teto_abre_uma_linha_no_balde_e_so_uma(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, log, balde = _rodada(tmp_path, "test_a1.py\n", {"test_a1.py": _marca(marcas, "a1", 2)})
    r = _run(env, "rodar", "demo", "--portao", "--origin-main", "--teto-pequeno", "0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "degrau pequeno de demo: " in r.stdout and "acima do teto de 0 s" in r.stdout, r.stdout
    admitidos = [l for l in log.read_text().splitlines() if l.startswith("dt admitir")]
    assert len(admitidos) == 1, log.read_text()
    assert "o degrau pequeno de demo passa de 0 s" in admitidos[0]
    assert "--stack k-a" in admitidos[0] and "--raio demo@a/VERDES" in admitidos[0], admitidos[0]
    assert "o degrau pequeno de demo passa de" in balde.read_text()
    r = _run(env, "rodar", "demo", "--portao", "--origin-main", "--teto-pequeno", "0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "já há linha aberta" in r.stdout, r.stdout
    assert len([l for l in log.read_text().splitlines() if l.startswith("dt admitir")]) == 1


def test_balde_que_recusa_avisa_e_nao_derruba_a_rodada(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, log, _ = _rodada(tmp_path, "test_a1.py\n", {"test_a1.py": _marca(marcas, "a1", 2)},
                          "#!/usr/bin/env bash\n"
                          'case "$1 $2" in "dt listar") exit 0 ;; *) echo "recusado pelo PDP" >&2; exit 4 ;; esac\n')
    r = _run(env, "rodar", "demo", "--portao", "--origin-main", "--teto-pequeno", "0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "balde: não admiti a linha (recusado pelo PDP)" in r.stderr, r.stderr


def test_vermelho_em_qualquer_degrau_da_rodada_sai_1(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, _, _ = _rodada(tmp_path, "test_a1.py\ntest_v.py | degrau: rodada\n",
                        {"test_a1.py": _marca(marcas, "a1"), "test_v.py": VERMELHO})
    r = _run(env, "rodar", "demo", "--portao", "--origin-main")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "degrau rodada de demo: " in r.stdout and "VERMELHO" in r.stdout, r.stdout


def test_teto_pequeno_so_com_a_rodada_diaria_e_so_inteiro(tmp_path):
    marcas = tmp_path / "marcas.txt"
    env, arv, _ = _tres(tmp_path, marcas, DEGRAUS)
    r = _run(env, "rodar", "demo", "--portao", "--arvore", str(arv), "--teto-pequeno", "5")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--teto-pequeno só com --origin-main" in r.stdout + r.stderr
    r = _run(env, "rodar", "demo", "--portao", "--origin-main", "--teto-pequeno", "cinco")
    assert r.returncode == 2, r.stdout + r.stderr


# --- DT #312 (arq:0129 D3): degrau pequeno python sem rede, loopback por ioctl e uv --offline --------

def _sem_userns() -> bool:
    return subprocess.run(["unshare", "--user", "--map-root-user", "--net", "--", "true"],
                          capture_output=True).returncode != 0


def _servidor_local():
    import socket
    import threading
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(8)

    def aceitar():
        while True:
            try:
                c, _ = s.accept()
                c.sendall(b"ok")
                c.close()
            except OSError:
                return
    threading.Thread(target=aceitar, daemon=True).start()
    return s, s.getsockname()[1]


def test_pequeno_python_roda_sem_rede_com_loopback_ligada_e_externo_sai_vermelho(tmp_path):
    if _sem_userns():
        pytest.skip("este host nao deixa criar namespace de rede (unshare --user --map-root-user --net)")
    srv, porta = _servidor_local()
    try:
        teste_peq = (
            "import socket, threading\n"
            "def test_loopback_proprio_funciona_e_rede_do_host_e_externa_falham():\n"
            "    with socket.socket() as s:\n"
            "        s.settimeout(1)\n"
            f"        try:\n            s.connect(('127.0.0.1', {porta}))\n"
            "            assert False, 'nao devia alcancar o servidor do host no degrau pequeno'\n"
            "        except OSError:\n"
            "            pass\n"
            "    with socket.socket() as s:\n"
            "        s.settimeout(1)\n"
            "        try:\n"
            "            s.connect(('192.0.2.1', 80))\n"
            "            assert False, 'nao devia alcancar endereco externo no degrau pequeno'\n"
            "        except OSError:\n"
            "            pass\n"
            "    srv = socket.socket()\n"
            "    srv.bind(('127.0.0.1', 0))\n"
            "    srv.listen(1)\n"
            "    p = srv.getsockname()[1]\n"
            "    def _acc():\n"
            "        c, _ = srv.accept()\n"
            "        c.sendall(b'ok')\n"
            "        c.close()\n"
            "    threading.Thread(target=_acc, daemon=True).start()\n"
            "    with socket.socket() as cli:\n"
            "        cli.settimeout(2)\n"
            "        cli.connect(('127.0.0.1', p))\n"
            "        assert cli.recv(2) == b'ok'\n"
            "    srv.close()\n"
        )
        teste_rod = (
            "import socket\n"
            "def test_rodada_alcanca_servidor_do_host():\n"
            "    with socket.socket() as s:\n"
            "        s.settimeout(2)\n"
            f"        s.connect(('127.0.0.1', {porta}))\n"
            "        assert s.recv(2) == b'ok'\n"
        )
        teste_ext = (
            "import socket\n"
            "def test_abre_conexao_externa():\n"
            "    with socket.socket() as s:\n"
            "        s.settimeout(1)\n"
            "        s.connect(('192.0.2.1', 80))\n"
        )
        env, arv = _arvore(
            tmp_path,
            {"a": {"test_peq.py": teste_peq, "test_rod.py": teste_rod}},
            {"a": "test_peq.py\ntest_rod.py | degrau: rodada\n"},
        )
        r = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv))
        assert r.returncode == 0, r.stdout + r.stderr
        r_rod = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--degrau", "rodada", "--arvore", str(arv))
        assert r_rod.returncode == 0, r_rod.stdout + r_rod.stderr

        env2, arv2 = _arvore(
            tmp_path / "ext",
            {"a": {"test_ext.py": teste_ext}},
            {"a": "test_ext.py\n"},
        )
        r_ext = _run(dict(env2, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv2))
        assert r_ext.returncode == 1, r_ext.stdout + r_ext.stderr
    finally:
        srv.close()


def test_pequeno_python_aquece_cache_no_preparo_e_roda_uv_offline(tmp_path):
    if _sem_userns():
        pytest.skip("este host nao deixa criar namespace de rede (unshare --user --map-root-user --net)")
    uv_real = shutil.which("uv")
    if not uv_real:
        pytest.skip("uv ausente")
    log = tmp_path / "uv.log"
    wdir = tmp_path / "bin"
    wdir.mkdir()
    uv_wrap = wdir / "uv"
    uv_wrap.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        f'exec "{uv_real}" "$@"\n',
        encoding="utf-8",
    )
    uv_wrap.chmod(0o755)
    env, arv = _arvore(tmp_path, {"a": {"test_ok.py": VERDE}}, {"a": "test_ok.py\n"})
    env["PATH"] = f"{wdir}{os.pathsep}{os.environ.get('PATH', '')}"
    r = _run(dict(env, PF_TESTE_SEM_MEMO="1"), "rodar", "demo", "--portao", "--arvore", str(arv))
    assert r.returncode == 0, r.stdout + r.stderr
    chamadas = log.read_text(encoding="utf-8").splitlines()
    assert any("--version" in c and "--offline" not in c for c in chamadas), chamadas
    assert any("run --offline" in c and "pytest" in c and "--version" not in c for c in chamadas), chamadas
