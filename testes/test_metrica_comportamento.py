"""metrica comportamento (#3090): sinais de ato por cadeira, janela contra base.

Roda o verbo como a unit roda (subprocesso, OPS_LOG_DIR apontado), sobre log sintetico
com um tropeco plantado na janela e ausente da base. E um smoke contra o log real,
quando ele existe na maquina.
"""
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
METRICA = RAIZ / "bin" / "metrica"
JANELA = date(2026, 9, 25)


def _linha(ts, cadeira, ordem, tool, ato, exit_code, sessao="s1"):
    return json.dumps({"ts": ts, "cadeira": cadeira, "ordem_id": ordem, "sessao_id": sessao,
                       "tool": tool, "ato": ato, "exit_code": exit_code, "dur_ms": 300})


def _dia(pasta, d, linhas):
    (pasta / f"ops-{d.isoformat()}.jsonl").write_text("\n".join(linhas) + "\n")


def _roda(pasta, *args):
    env = dict(os.environ, OPS_LOG_DIR=str(pasta))
    return subprocess.run([sys.executable, str(METRICA), "comportamento", *args],
                          capture_output=True, text=True, env=env, timeout=120)


def _log_sintetico(tmp_path):
    # Base: 7 dias, uma fita limpa por dia na cadeira ti.
    for n in range(1, 8):
        d = JANELA - timedelta(n)
        ts = f"{d.isoformat()}T10:00:00"
        _dia(tmp_path, d, [
            _linha(ts, "ti", f"o{n}", "monta_sessao", None, 0),
            _linha(ts, "ti", f"o{n}", "acervo", "ler", 0),
            _linha(ts, "ti", f"o{n}", "release", "promover", 0),
            _linha(ts, "ti", f"o{n}", "release", "conferir", 0),
        ])
    # Janela: uma fita que nao acha documento tres vezes e promove sem conferir.
    ts = f"{JANELA.isoformat()}T10:00:00"
    _dia(tmp_path, JANELA, [
        _linha(ts, "ti", "oj", "monta_sessao", None, 0),
        _linha(ts, "ti", "oj", "acervo", "ler", 1),
        _linha(ts, "ti", "oj", "acervo", "ler", 1),
        _linha(ts, "ti", "oj", "acervo", "ler", 1),
        _linha(ts, "ti", "oj", "acervo", "ler", 0),
        _linha(ts, "ti", "oj", "release", "promover", 0),
    ])


def test_marca_o_que_piorou(tmp_path):
    _log_sintetico(tmp_path)
    r = _roda(tmp_path, JANELA.isoformat())
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert "ti:documento_nao_achado" in d["piorou"]
    s = d["por_cadeira"]["ti"]["sinais"]
    assert s["documento_nao_achado"]["janela"] == 3
    assert s["efeito_sem_conferencia"]["janela"] == 1
    assert s["efeito_sem_conferencia"]["base"] == 0
    assert d["base"] == f"{(JANELA - timedelta(7)).isoformat()}..{(JANELA - timedelta(1)).isoformat()}"


def test_resumo_e_o_texto_da_carta(tmp_path):
    _log_sintetico(tmp_path)
    r = _roda(tmp_path, JANELA.isoformat(), "--resumo")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("Coleta de comportamento (#3090)")
    assert "PIOROU: " in r.stdout and "documento_nao_achado" in r.stdout


def test_sem_log_nenhum_sai_4(tmp_path):
    r = _roda(tmp_path, JANELA.isoformat())
    assert r.returncode == 4
    assert "nao ha ops log" in r.stderr


def test_log_real_roda(capsys):
    real = Path(os.environ.get("OPS_LOG_DIR", "/srv/platafirma/casa/var/log/ops"))
    if not real.is_dir():
        return
    r = _roda(real, "--resumo")
    assert r.returncode in (0, 4), r.stderr
    with capsys.disabled():
        print("\n" + r.stdout)
