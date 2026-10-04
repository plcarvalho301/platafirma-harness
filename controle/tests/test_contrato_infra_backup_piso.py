"""`infra backup`: a ultima geracao abaixo do `piso_bytes` reprova (incidente #3222).

De 16/09 a 02/10/2026 o dump noturno da wiki saiu com 320 bytes e `infra backup` o contou
`ok`: media presenca e idade, e `bytes` somava todas as geracoes. O piso e declarado por
alvo em registro/backups.json; sem ele o alvo se mede como antes. Estes testes rodam o
bin/infra de verdade, contra um registro e diretorios de backup montados em tmp_path.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
INFRA = RAIZ / "bin" / "infra"
REGISTRO_REAL = RAIZ / "registro" / "backups.json"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("python3") is None,
                                reason="sem bash ou python3 no PATH")

PISO = 100 * 1024


def _geracao(diretorio, nome, tamanho, idade_dias):
    p = diretorio / nome
    p.write_bytes(b"x" * tamanho)
    t = time.time() - idade_dias * 86400
    os.utime(p, (t, t))
    return p


def _backup(tmp_path, geracoes, piso=PISO, texto=False):
    """geracoes: [(nome, tamanho, idade_dias)]. Devolve o processo de `infra backup`."""
    dados = tmp_path / "dump"
    dados.mkdir()
    for nome, tamanho, idade in geracoes:
        _geracao(dados, nome, tamanho, idade)
    alvo = {"o_que": "dump de teste", "cobertura": "cron de teste",
            "diretorio": str(dados), "padrao": "*.sql.gz", "alcance": "aqui"}
    if piso is not None:
        alvo["piso_bytes"] = piso
    reg = tmp_path / "backups.json"
    reg.write_text(json.dumps({"alvos": {"wiki": alvo}}))
    env = {**os.environ, "INFRA_BACKUPS": str(reg)}
    args = [] if texto else ["--json"]
    return subprocess.run([BASH, str(INFRA), "backup", *args], capture_output=True,
                          text=True, env=env, timeout=30)


def _alvo(r):
    return json.loads(r.stdout)["alvos"][0]


def test_ultima_geracao_vazia_reprova_mesmo_com_geracao_boa_antes(tmp_path):
    r = _backup(tmp_path, [("w-1.sql.gz", 4_000_000, 1.5), ("w-2.sql.gz", 320, 0.1)])
    assert r.returncode == 1, r.stdout + r.stderr
    a = _alvo(r)
    assert a["estado"] == "abaixo-do-piso"
    assert a["ultimo"] == "w-2.sql.gz" and a["ultimo_bytes"] == 320
    assert a["bytes"] == 4_000_320 and a["piso_bytes"] == PISO


def test_incidente_3222_todas_as_geracoes_de_320_bytes_reprovam(tmp_path):
    r = _backup(tmp_path, [(f"w-{i}.sql.gz", 320, i + 0.1) for i in range(5)])
    assert r.returncode == 1, r.stdout + r.stderr
    assert _alvo(r)["estado"] == "abaixo-do-piso"


def test_ultima_acima_do_piso_passa_mesmo_com_antigas_pequenas(tmp_path):
    ger = [("w-1.sql.gz", 320, 3.0), ("w-2.sql.gz", 320, 2.5), ("w-3.sql.gz", 200_000, 0.1)]
    r = _backup(tmp_path, ger)
    assert r.returncode == 0, r.stdout + r.stderr
    a = _alvo(r)
    assert a["estado"] == "ok" and a["ultimo_bytes"] == 200_000


def test_sem_piso_declarado_o_alvo_se_mede_como_antes(tmp_path):
    r = _backup(tmp_path, [("w-1.sql.gz", 320, 0.1)], piso=None)
    assert r.returncode == 0, r.stdout + r.stderr
    a = _alvo(r)
    assert a["estado"] == "ok" and "piso_bytes" not in a and a["ultimo_bytes"] == 320


def test_piso_nao_esconde_o_atraso(tmp_path):
    r = _backup(tmp_path, [("w-1.sql.gz", 200_000, 5.0)])
    assert r.returncode == 1, r.stdout + r.stderr
    assert _alvo(r)["estado"] == "atrasado"


def test_texto_diz_a_geracao_o_tamanho_e_o_piso(tmp_path):
    r = _backup(tmp_path, [("w-1.sql.gz", 320, 0.1)], texto=True)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "abaixo-do-piso" in r.stdout
    assert "w-1.sql.gz com 320 B, abaixo do piso de 100.0 KiB" in r.stdout


def test_registro_real_declara_piso_para_os_dois_dumps_sql():
    alvos = json.loads(REGISTRO_REAL.read_text(encoding="utf-8"))["alvos"]
    assert alvos["conhecimento-db"]["piso_bytes"] >= PISO
    assert alvos["rag-db"]["piso_bytes"] >= PISO
