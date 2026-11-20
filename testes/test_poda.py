"""Testes da poda no harness por processo e resolvedor único de ato (story #4342, t3)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(HARNESS_LIB) not in sys.path:
    sys.path.insert(0, str(HARNESS_LIB))

from poda import (
    LedgerSessao,
    atos_que_escrevem,
    lavar,
    podar_envelope,
    resolver_ato,
)

FACES_MOTOR = {"motor": {"instancia": "rag", "sem_instancia": ["listar"]}}


def _criar_bin_motor(pasta: Path) -> Path:
    arq = pasta / "motor"
    arq.write_text(
        "#!/usr/bin/env bash\n"
        "# poda: cosmetica@buscar\n"
        "# atos: listar (leitura, texto), buscar (leitura, busca), trocar (escrita, geracao)\n"
        "exit 0\n",
        encoding="utf-8",
    )
    arq.chmod(0o755)
    return arq


def test_resolvedor_unico_de_ato_para_verbo_com_instancia(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    assert resolver_ato([str(bin_motor), "rag", "trocar", "g1"], binario=bin_motor, faces=FACES_MOTOR) == "trocar"
    assert resolver_ato([str(bin_motor), "rag", "buscar", "casa", "x"], binario=bin_motor, faces=FACES_MOTOR) == "buscar"
    assert resolver_ato([str(bin_motor), "listar"], binario=bin_motor, faces=FACES_MOTOR) == "listar"
    assert resolver_ato([str(bin_motor), "rag", "listar"], binario=bin_motor, faces=FACES_MOTOR) == "listar"
    assert resolver_ato(["/bin/repo", "--flag", "abrir", "x"]) == "abrir"


def test_motor_rag_trocar_nao_deduplica_e_listar_nao_escapa_do_teto(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    derrame = tmp_path / "derrame"
    ledger = tmp_path / "ledger"

    env_trocar = {"exit_code": 0, "stdout": {"texto": "geracao g2 ativada\n", "truncado": False, "bytes_total": 19}}
    r1 = podar_envelope(
        env_trocar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "trocar", "g2"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag trocar g2",
        derrame_dir=derrame,
        ledger_dir=ledger,
        faces=FACES_MOTOR,
    )
    r2 = podar_envelope(
        env_trocar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "trocar", "g2"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag trocar g2",
        derrame_dir=derrame,
        ledger_dir=ledger,
        faces=FACES_MOTOR,
    )
    assert r1["stdout"]["texto"] == "geracao g2 ativada\n"
    assert r2["stdout"]["texto"] == "geracao g2 ativada\n"
    assert "[igual ao giro" not in r2["stdout"]["texto"]
    assert r2["poda"]["ato_efetivo"] == "trocar"
    assert r2["poda"]["ledger"] == "escrita"

    # Listagem grande (motor listar / motor rag listar) NÃO escapa do teto
    lista_grande = "\n".join(f"item-{i:04d} valor-{i}" for i in range(4000))
    env_listar = {
        "exit_code": 0,
        "stdout": {"texto": lista_grande, "truncado": False, "bytes_total": len(lista_grande)},
    }
    rl = podar_envelope(
        env_listar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "listar"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag listar",
        derrame_dir=derrame,
        ledger_dir=ledger,
        cap=4096,
        faces=FACES_MOTOR,
    )
    assert rl["stdout"]["truncado"] is True
    assert len(rl["stdout"]["texto"].encode("utf-8")) <= 4096 + 200
    assert Path(rl["stdout"]["cru"]).exists()
    assert rl["poda"]["modo"] == "corte"


def test_poda_por_processo_deduplica_leitura_e_respeita_inteiro(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    env_sub = {**os.environ, "PYTHONPATH": str(HARNESS_LIB)}
    payload = {
        "envelope": {"exit_code": 0, "stdout": {"texto": "lista pequena", "truncado": False, "bytes_total": 13}},
        "verbo": "motor",
        "argv": [str(bin_motor), "listar"],
        "binario": str(bin_motor),
        "sessao_id": "s-proc",
        "alca": "motor listar",
        "derrame_dir": str(tmp_path / "derrame"),
        "ledger_dir": str(tmp_path / "ledger"),
        "faces": FACES_MOTOR,
    }
    p1 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out1 = json.loads(p1.stdout)
    assert out1["stdout"]["texto"] == "lista pequena"

    p2 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out2 = json.loads(p2.stdout)
    assert "[igual ao giro 1" in out2["stdout"]["texto"]

    payload["inteiro"] = True
    p3 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out3 = json.loads(p3.stdout)
    assert out3["stdout"]["texto"] == "lista pequena"


def test_atos_que_escrevem_nao_polui_cache_com_caminho_inexistente(tmp_path: Path):
    ficticio = tmp_path / "nao-existe"
    assert atos_que_escrevem("x", ficticio) == frozenset()
    ficticio.write_text("#!/bin/sh\n# atos: gravar (escrita, x)\n", encoding="utf-8")
    assert "gravar" in atos_que_escrevem("x", ficticio)


def test_ledger_distancia_expira_apos_teto_e_reenvia_inteiro(tmp_path: Path):
    ledger = LedgerSessao(tmp_path / "ledger.json")
    g1 = ledger.proximo_giro()
    d1 = ledger.olha("acervo ler x", "conteudo-estavel", g1, distancia_max=3)
    assert d1["modo"] == "inteiro"
    assert d1["ledger"] == "novo"

    g2 = ledger.proximo_giro()
    d2 = ledger.olha("acervo ler x", "conteudo-estavel", g2, distancia_max=3)
    assert d2["modo"] == "igual"
    assert d2["giro_ref"] == g1

    for _ in range(3):
        ledger.proximo_giro()
    g6 = ledger.proximo_giro()
    d6 = ledger.olha("acervo ler x", "conteudo-estavel", g6, distancia_max=3)
    assert d6["modo"] == "inteiro"
    assert d6["ledger"] == "expirado"
    assert d6["texto"] == "conteudo-estavel"


def test_lavador_preserva_json_com_campo_lista_longa(tmp_path: Path):
    payload_json = json.dumps(
        {
            "fontes": [
                {"n": i, "obra": f"Obra {i}", "texto": "trecho " * 40}
                for i in range(1, 20)
            ],
            "cobertura": "boa",
        },
        ensure_ascii=False,
    )
    assert len(payload_json.encode("utf-8")) > 2_000

    lavado, rel = lavar(payload_json)
    assert "blob" not in rel["classes"]
    assert json.loads(lavado)["cobertura"] == "boa"
    assert len(json.loads(lavado)["fontes"]) == 19

    bin_motor = _criar_bin_motor(tmp_path)
    out = podar_envelope(
        {"exit_code": 0, "stdout": {"texto": payload_json, "truncado": False, "bytes_total": len(payload_json)}},
        verbo="motor",
        argv=[str(bin_motor), "rag", "buscar", "casa", "teste"],
        binario=bin_motor,
        sessao_id="s-json",
        alca="motor buscar",
        derrame_dir=tmp_path / "derrame",
        ledger_dir=tmp_path / "ledger",
        faces=FACES_MOTOR,
    )
    assert "blob" not in out["poda"]["lavado"]
    assert json.loads(out["stdout"]["texto"])["cobertura"] == "boa"


def test_poda_constitutiva_nao_mutila_conteudo_longo_nem_repeticoes(tmp_path: Path):
    bin_doc = tmp_path / "docbin"
    bin_doc.write_text("#!/bin/sh\n# poda: constitutiva\n# atos: ler (leitura, x)\n", encoding="utf-8")
    texto = ("linha igual\n" * 6) + ("a" * 2500)
    out = podar_envelope(
        {"exit_code": 0, "stdout": {"texto": texto, "truncado": False, "bytes_total": len(texto)}},
        verbo="docbin",
        argv=[str(bin_doc), "ler"],
        binario=bin_doc,
        sessao_id="s-const",
        alca="docbin ler",
        derrame_dir=tmp_path / "derrame",
        ledger_dir=tmp_path / "ledger",
    )
    assert out["poda"]["perfil"] == "constitutiva"
    assert "blob" not in out["poda"]["lavado"]
    assert "repeticao" not in out["poda"]["lavado"]
    assert out["stdout"]["texto"] == texto


def test_pf_poda_zero_desliga_poda_no_envelope(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PF_PODA", "0")
    bin_motor = _criar_bin_motor(tmp_path)
    bruto = "\x1b[31m" + ("x" * 3000) + "\x1b[0m"
    out = podar_envelope(
        {"exit_code": 0, "stdout": {"texto": bruto, "truncado": False, "bytes_total": len(bruto)}},
        verbo="motor",
        argv=[str(bin_motor), "listar"],
        binario=bin_motor,
        sessao_id="s-off",
        alca="motor listar",
        derrame_dir=tmp_path / "derrame",
        ledger_dir=tmp_path / "ledger",
        cap=500,
        faces=FACES_MOTOR,
    )
    assert out["poda"]["desligada"] is True
    assert out["stdout"]["texto"] == bruto
    assert out["stdout"]["truncado"] is False
