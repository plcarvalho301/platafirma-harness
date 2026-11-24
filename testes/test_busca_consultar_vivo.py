# componente: componente:verbo-busca
"""Suíte viva de `busca consultar` contra o banco `casa` e a release servida (story 4427, t11).

Executa no degrau `rodada` as duas chamadas canônicas de «Como se confere» em
`platafirma-casa@referencias/instancias/verbo/busca.md`; o prazo de 5 segundos por chamada
é garantido pelo próprio `Retrato` do leitor.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"
_RE_CABECALHO_CLASSE = re.compile(
    r"^classe · fornada [0-9a-f-]+ · fichas 1 a (\d+) de \1 · digest v1:[0-9a-f]{64}$"
)


def _executar_consultar(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BIN), "consultar", *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_consultar_classes_cuja_capacidade_e_busca() -> None:
    proc = _executar_consultar("--classe", "classe", "--prop", "capacidade=busca")
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.splitlines()
    assert linhas, "stdout vazio"
    m = _RE_CABECALHO_CLASSE.match(linhas[0])
    assert m is not None and int(m.group(1)) >= 1, f"cabeçalho inesperado: {linhas[0]!r}"
    assert any(ln == "exploracao" or ln.startswith("exploracao · ") for ln in linhas[1:])


def test_consultar_gabaritos_de_modelos_formais_vira_condicao() -> None:
    proc = _executar_consultar("gabaritos de modelos formais")
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.splitlines()
    assert linhas, "stdout vazio"
    assert linhas[0].startswith("nome «gabaritos de modelos formais» virou condição")
    assert " · digest v1:" in linhas[0]
    assert any(
        ln == "gabarito:framework-da-ontologia" or ln.startswith("gabarito:framework-da-ontologia · ")
        for ln in linhas[1:]
    )


def test_dt1369_varias_fichas_voltam_com_definicao_preenchida() -> None:
    import json

    for termo in ("gestão estratégica", "desenvolvimento"):
        proc_txt = _executar_consultar(termo)
        assert proc_txt.returncode == 0, proc_txt.stderr
        linhas = proc_txt.stdout.splitlines()
        assert linhas and linhas[0].startswith(f"nome «{termo}» · "), proc_txt.stdout
        for ln in linhas[1:]:
            assert " ·  · " not in ln, f"definição vazia para {termo!r}: {ln!r}"

        proc_json = _executar_consultar(termo, "--json")
        assert proc_json.returncode == 0, proc_json.stderr
        reg = json.loads(proc_json.stdout)
        assert len(reg["fichas"]) >= 1
        for ficha in reg["fichas"]:
            assert (ficha.get("definicao") or "").strip(), f"definição vazia no JSON para {termo!r}: {ficha!r}"


def test_dt1370_ligacao_vazia_sugere_sentido_oposto() -> None:
    import json

    proc_txt = _executar_consultar("--classe", "chapeu", "--ligacao", "veste=produto")
    assert proc_txt.returncode == 0, proc_txt.stderr
    assert "de 0 · digest v1:" in proc_txt.stdout
    assert "ligacao no sentido oposto: vestido-por=produto (" in proc_txt.stdout

    proc_json = _executar_consultar("--classe", "chapeu", "--ligacao", "veste=produto", "--json")
    assert proc_json.returncode == 0, proc_json.stderr
    reg = json.loads(proc_json.stdout)
    assert reg["total"] == 0
    opostas = reg.get("ligacoes_opostas") or []
    assert any(
        o["propriedade"] == "vestido-por" and o["alvo"] == "produto" and o["contagem"] >= 1
        for o in opostas
    ), opostas
