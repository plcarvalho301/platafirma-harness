"""Guardas de alcance dos binários `ler_arquivo` e `write_file` do harness (achado 921).

Portado de `core/porta/tests/test_alcance_porta_dt921.py` no débito 924 para rodar
na suíte do harness (onde `bin/ler_arquivo`, `bin/write_file`, `lib/leitura` e
`lib/escrita` vivem), mantendo a suíte do core independente do harness.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
BIN_LER = HARNESS_DIR / "bin" / "ler_arquivo"
BIN_WRITE = HARNESS_DIR / "bin" / "write_file"
_PY_HARNESS = Path("/opt/platafirma/current/venv/harness/bin/python")


@pytest.fixture
def ambiente_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Monta release, instância, bancada e PDP em tmp_path sem tocar o host."""
    rel = tmp_path / "release"
    inst = tmp_path / "instancia"
    banc = tmp_path / "bancada"
    pdp = tmp_path / "pdp"

    (rel / "current" / "harness").mkdir(parents=True)
    (inst / "var" / "tmp").mkdir(parents=True)
    (inst / "var" / "fila").mkdir(parents=True)
    (inst / "var" / "log").mkdir(parents=True)
    (inst / "var" / "abertura-publicada").mkdir(parents=True)
    (inst / "segredos").mkdir(parents=True)
    (pdp).mkdir(parents=True)
    (banc / "wt" / "platafirma-core" / "outra-cadeira").mkdir(parents=True)
    (banc / "wt" / "platafirma-casa-espelho" / "seguranca" / "main").mkdir(parents=True)
    (banc / "wt" / "platafirma-casa-espelho" / "seguranca" / "main" / ".git").mkdir()
    (banc / "wt" / "platafirma-harness" / "seguranca" / "main" / "bin").mkdir(parents=True)
    (banc / "wt" / "platafirma-rastreador" / "engenharia").mkdir(parents=True)
    (banc / "platafirma-rastreador").mkdir(parents=True)
    (banc / "entrada").mkdir(parents=True)

    monkeypatch.setenv("PLATAFIRMA_RELEASE_RAIZ", str(rel))
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(inst))
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(banc))
    monkeypatch.setenv("PDP_DIR", str(pdp))

    return {
        "release": rel,
        "instancia": inst,
        "bancada": banc,
        "pdp": pdp,
    }


def _chamar(
    binario: Path,
    payload: dict[str, Any],
    *,
    instancia: Path,
    ordem_id: str = "o-921",
) -> tuple[dict[str, Any], bool]:
    py = str(_PY_HARNESS) if _PY_HARNESS.is_file() else sys.executable
    corpo = {"instancia": str(instancia), **payload}
    if ordem_id:
        corpo.setdefault("ordem_id", ordem_id)
    env = dict(os.environ)
    env["PF_ORDEM_ID"] = ordem_id
    cp = subprocess.run(
        [py, str(binario)],
        input=json.dumps(corpo, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert cp.stdout.strip(), f"rc={cp.returncode} stderr={cp.stderr}"
    dados = json.loads(cp.stdout)
    return dados, cp.returncode != 0


def _motivo(r: dict[str, Any]) -> str:
    assert r.get("recusado") or r.get("erro") or r.get("exit_code", 0) != 0, r
    return str(r.get("motivo") or r.get("falta") or r.get("erro") or "")


@pytest.mark.parametrize("caminho", ["/etc/passwd", "/etc", "/", "/nao-existe-921/x.md"])
def test_ler_arquivo_recusa_fora_da_morada(ambiente_harness: dict[str, Any], caminho: str) -> None:
    r, err = _chamar(BIN_LER, {"caminho": caminho}, instancia=ambiente_harness["instancia"])
    assert err is True
    assert _motivo(r).startswith("fora de morada")


def test_ler_arquivo_fora_da_morada_nomeia_bancada_e_sem_bancada(
    ambiente_harness: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    r, _ = _chamar(BIN_LER, {"caminho": "/etc/passwd"}, instancia=ambiente_harness["instancia"])
    assert str(ambiente_harness["bancada"].resolve()) in _motivo(r)

    monkeypatch.delenv("PLATAFIRMA_BANCADA", raising=False)
    monkeypatch.setenv("PLATAFIRMA_ARQUIVO_BANCADA", str(tmp_path / "sem-bancada"))
    r2, _ = _chamar(BIN_LER, {"caminho": "/etc/passwd"}, instancia=ambiente_harness["instancia"])
    assert "bancada nao declarada" in _motivo(r2)


def test_ler_arquivo_symlink_para_fora_da_morada_nao_escapa(ambiente_harness: dict[str, Any]) -> None:
    elo = ambiente_harness["instancia"] / "var" / "tmp" / "elo.md"
    elo.symlink_to("/etc/passwd")
    r1, err1 = _chamar(BIN_LER, {"caminho": str(elo)}, instancia=ambiente_harness["instancia"])
    assert err1 is True and _motivo(r1).startswith("fora de morada")

    pai = ambiente_harness["bancada"] / "wt" / "saida"
    pai.symlink_to("/etc")
    r2, err2 = _chamar(BIN_LER, {"caminho": str(pai / "passwd")}, instancia=ambiente_harness["instancia"])
    assert err2 is True and _motivo(r2).startswith("fora de morada")


@pytest.mark.parametrize(
    "nome",
    [
        ".env", ".env.local", "id_rsa", "id_ed25519", "authorized_keys",
        ".netrc", ".pgpass", ".git-credentials", "cert.pem", "priv.key", "cofre.kdbx",
    ],
)
def test_ler_arquivo_negativa_de_segredo_vence_morada_e_inexistencia(
    ambiente_harness: dict[str, Any], nome: str
) -> None:
    inexistente = ambiente_harness["bancada"] / "wt" / "platafirma-core" / "outra-cadeira" / nome
    r, err = _chamar(BIN_LER, {"caminho": str(inexistente)}, instancia=ambiente_harness["instancia"])
    assert err is True and "segredo" in _motivo(r).lower()


def test_ler_arquivo_recusa_segredos_pdp_e_fila(ambiente_harness: dict[str, Any]) -> None:
    inst = ambiente_harness["instancia"]
    seg = inst / "segredos" / "token.txt"
    seg.write_text("segredo\n", encoding="utf-8")
    r_seg, err_seg = _chamar(BIN_LER, {"caminho": str(seg)}, instancia=inst)
    assert err_seg is True and "segredo" in _motivo(r_seg).lower()

    pol = ambiente_harness["pdp"] / "politica.yaml"
    pol.write_text("versao: 1\n", encoding="utf-8")
    r_pdp, err_pdp = _chamar(BIN_LER, {"caminho": str(pol)}, instancia=inst)
    assert err_pdp is True and "segredo" in _motivo(r_pdp).lower()

    fila = inst / "var" / "fila" / "msg.txt"
    fila.write_text("carta\n", encoding="utf-8")
    r_fila, err_fila = _chamar(BIN_LER, {"caminho": str(fila)}, instancia=inst)
    assert err_fila is True and "fila" in _motivo(r_fila).lower()


def test_ler_arquivo_legitimo_e_listagem_filtrada(ambiente_harness: dict[str, Any]) -> None:
    inst = ambiente_harness["instancia"]
    rel_f = ambiente_harness["release"] / "current" / "harness" / "guia.md"
    inst_f = inst / "var" / "tmp" / "o-921" / "rascunho.md"
    outra = ambiente_harness["bancada"] / "wt" / "platafirma-core" / "outra-cadeira"
    banc_f = outra / "x.py"

    for arq, txt in ((rel_f, "da release\n"), (inst_f, "do rascunho\n"), (banc_f, "x = 1\n")):
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(txt, encoding="utf-8")
        r, err = _chamar(BIN_LER, {"caminho": str(arq)}, instancia=inst)
        assert err is False and txt.strip() in r["conteudo"]

    (outra / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (outra / "fuga").symlink_to("/etc/passwd")
    r_dir, err_dir = _chamar(BIN_LER, {"caminho": str(outra)}, instancia=inst)
    assert err_dir is False
    assert "x.py" in r_dir["entradas"]
    assert ".env" not in r_dir["entradas"]
    assert "fuga" not in r_dir["entradas"]


def test_write_file_recusa_release_log_fila_abertura_segredo_e_git(
    ambiente_harness: dict[str, Any],
) -> None:
    inst = ambiente_harness["instancia"]
    wt = ambiente_harness["bancada"] / "wt" / "platafirma-casa-espelho" / "seguranca" / "main"
    casos = [
        (ambiente_harness["release"] / "current" / "harness" / "x.py", "release"),
        (inst / "var" / "log" / "a.log", "log"),
        (inst / "var" / "fila" / "m.txt", "fila"),
        (inst / "var" / "abertura-publicada" / "a.md", "imutavel"),
        (inst / "segredos" / "s.txt", "segredo"),
        (wt / ".env", "segredo"),
        (wt / ".git" / "config", ".git"),
    ]
    for destino, esperado in casos:
        r, err = _chamar(BIN_WRITE, {"path": str(destino), "content": "x\n"}, instancia=inst)
        assert err is True, (destino, r)
        assert esperado in _motivo(r).lower(), (destino, r)
        assert not destino.exists()


@pytest.mark.parametrize("nome", ["binario.exe", "arquivo.bin", "foto.png", "bkp.bak", "semext"])
def test_write_file_recusa_extensao_fora_da_lista(ambiente_harness: dict[str, Any], nome: str) -> None:
    inst = ambiente_harness["instancia"]
    destino = ambiente_harness["bancada"] / "wt" / "platafirma-casa-espelho" / "seguranca" / "main" / nome
    r, err = _chamar(BIN_WRITE, {"path": str(destino), "content": "x\n"}, instancia=inst)
    assert err is True and _motivo(r).startswith("tipo:")
    assert not destino.exists()


def test_write_file_aceita_nomes_especiais_entrada_csv_e_bin_com_shebang(
    ambiente_harness: dict[str, Any],
) -> None:
    inst = ambiente_harness["instancia"]
    wt = ambiente_harness["bancada"] / "wt" / "platafirma-casa-espelho" / "seguranca" / "main"
    for nome in ("Dockerfile", "Dockerfile.gpu", "VERDES", ".gitignore", ".conferir-repo"):
        r, err = _chamar(BIN_WRITE, {"path": str(wt / nome), "content": "ok\n"}, instancia=inst)
        assert err is False and r["ok"] is True, (nome, r)

    r_csv, err_csv = _chamar(
        BIN_WRITE,
        {"path": str(ambiente_harness["bancada"] / "entrada" / "dados.csv"), "content": "a,b\n1,2\n"},
        instancia=inst,
    )
    assert err_csv is False and r_csv["ok"] is True
    r_py, err_py = _chamar(
        BIN_WRITE,
        {"path": str(ambiente_harness["bancada"] / "entrada" / "x.py"), "content": "x=1\n"},
        instancia=inst,
    )
    assert err_py is True and _motivo(r_py).startswith("tipo:")

    bin_alvo = ambiente_harness["bancada"] / "wt" / "platafirma-harness" / "seguranca" / "main" / "bin" / "meu-verbo"
    r_sem_sb, err_sem_sb = _chamar(BIN_WRITE, {"path": str(bin_alvo), "content": "print(1)\n"}, instancia=inst)
    assert err_sem_sb is True and "#!" in _motivo(r_sem_sb)
    r_com_sb, err_com_sb = _chamar(
        BIN_WRITE, {"path": str(bin_alvo), "content": "#!/usr/bin/env python3\nprint(1)\n"}, instancia=inst
    )
    assert err_com_sb is False and r_com_sb["ok"] is True


def test_write_file_rascunho_da_fita_e_isolamento_de_ordem(ambiente_harness: dict[str, Any]) -> None:
    inst = ambiente_harness["instancia"]
    tmp_fita = inst / "var" / "tmp"

    r0, err0 = _chamar(BIN_WRITE, {"path": str(tmp_fita / "solto.md"), "content": "x\n"}, instancia=inst)
    assert err0 is True and "subpasta" in _motivo(r0)

    r1, err1 = _chamar(
        BIN_WRITE, {"path": str(tmp_fita / "o-921" / "nota.md"), "content": "x\n"}, instancia=inst, ordem_id=""
    )
    assert err1 is True and "fita declarada" in _motivo(r1)

    r2, err2 = _chamar(
        BIN_WRITE, {"path": str(tmp_fita / "o-outra" / "nota.md"), "content": "x\n"}, instancia=inst, ordem_id="o-921"
    )
    assert err2 is True and "nao e a pasta desta fita" in _motivo(r2)

    r3, err3 = _chamar(
        BIN_WRITE, {"path": str(tmp_fita / "o-921" / "nota.md"), "content": "ok\n"}, instancia=inst, ordem_id="o-921"
    )
    assert err3 is False and r3["ok"] is True


def test_write_file_recusa_clone_inexistente_symlink_traversal_e_teto(
    ambiente_harness: dict[str, Any],
) -> None:
    inst = ambiente_harness["instancia"]
    inex = ambiente_harness["bancada"] / "wt" / "platafirma-rastreador" / "outra" / "x.md"
    r_inex, err_inex = _chamar(BIN_WRITE, {"path": str(inex), "content": "x\n"}, instancia=inst)
    assert err_inex is True and "repo abrir" in _motivo(r_inex)

    wt = ambiente_harness["bancada"] / "wt" / "platafirma-casa-espelho" / "seguranca" / "main"
    real_f = wt / "alvo.md"
    real_f.write_text("orig\n", encoding="utf-8")
    link_f = wt / "link.md"
    link_f.symlink_to(real_f)
    r_lnk, err_lnk = _chamar(BIN_WRITE, {"path": str(link_f), "content": "novo\n"}, instancia=inst)
    assert err_lnk is True and "symlink" in _motivo(r_lnk)

    r_dot, err_dot = _chamar(
        BIN_WRITE, {"path": str(wt / ".." / ".." / "escape.md"), "content": "x\n"}, instancia=inst
    )
    assert err_dot is True and ".." in _motivo(r_dot)

    r_big, err_big = _chamar(
        BIN_WRITE, {"path": str(wt / "grande.txt"), "content": "a" * (1_048_576 + 10)}, instancia=inst
    )
    assert err_big is True and "teto" in _motivo(r_big)
