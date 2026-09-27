"""Contrato de `metrica abertura` (card #3145).

`abertura` e o ex-`bin/conta-abertura` (miolo `bin/_conta/conta-abertura.py`),
movido para `bin/_metrica/abertura.py` como modulo importavel e virado ato de
`bin/metrica`. Os args (`<cadeira>`, `--tudo`, `--json`, `--chapeu`) e o contrato de
saida (default TEXTO, `--json` pede maquina) sao os que `conta-abertura` sempre
teve — o INVERSO do resto de `metrica` (default JSON, `--resumo` pede texto), de
proposito: e o contrato herdado que este ato promete manter.

Isolamento: `conftest.py` ja tira toda variavel de plataforma do ambiente
(`lib/teste_isolado.py`). Este arquivo cria, por teste, uma morada publicada
propria (`PLATAFIRMA_INSTANCIA`/`PF_ABERTURA_DIR` hermeticos) com 1-2 cadeiras
fixture — sem ela `monta()` (bin/monta-sessao) recusa com "morada nao publicada"
antes mesmo de olhar a cadeira. `PF_BIN` aponta para stubs de `mesa`/`fila`/
`minuta`/`tarefas` (as pecas-verbo do catalogo de abertura): sem eles, a suíte
chamaria os verbos REAIS contra servicos que o isolamento redireciona para a
porta 9 — mais lento e nao determinístico para o que este arquivo mede (contagem
de tokens e forma do JSON, nao o comportamento desses verbos, que tem teste
proprio).
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "metrica"

STUB_VERBO = """#!/bin/sh
# stub fixture: qualquer subcomando do verbo, saida curta deterministica, exit 0 —
# sem isso o teste chamaria mesa/fila/minuta/tarefas REAIS contra servico ausente.
echo "stub $(basename "$0") $* -- fixture ok"
"""


def _escreve(base: Path, rel: str, texto: str) -> Path:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def morada_de(raiz: Path) -> Path:
    return raiz / "var" / "abertura-publicada"


def _publica(raiz: Path, abertura_src: Path, sha: str = "0" * 40) -> None:
    """Publica `abertura_src/` na morada, no formato que `monta-sessao` le
    (MANIFEST.json + `current` -> `refs/<sha>/abertura`). Sem MANIFEST.json, `m["frescor"]`
    fica `indisponivel` e `monta()` recusa TUDO com "morada nao publicada" — gate que
    vem antes da propria validacao de cadeira (arq:0097)."""
    ref = morada_de(raiz) / "refs" / sha
    if ref.exists():
        shutil.rmtree(ref)
    ref.mkdir(parents=True)
    shutil.copytree(abertura_src, ref / "abertura")
    arquivos = [p for p in (ref / "abertura").rglob("*") if p.is_file()]
    (ref / "MANIFEST.json").write_text(json.dumps({
        "sha": sha, "sha_curto": sha[:7], "ref": "origin/main", "tree_sha": "t" * 40,
        "publicado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "publicado_por": "fixture",
        "n_arquivos": len(arquivos),
        "n_bytes": sum(p.stat().st_size for p in arquivos),
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    current = morada_de(raiz) / "current"
    if current.is_symlink() or current.exists():
        current.unlink()
    current.symlink_to(Path("refs") / sha)


def _monta_raiz(tmp_path: Path) -> Path:
    """Raiz hermetica: morada publicada com 2 cadeiras fixture + stubs de verbo."""
    raiz = tmp_path / "raiz"
    fonte = tmp_path / "abertura-fonte"
    _escreve(fonte, "teste/persona.md",
             "Você é Testildo Testonildo, a persona fixture do contrato de "
             "`metrica abertura` (card #3145). Corpo curto de proposito: o que este "
             "arquivo mede e a FORMA do pacote, nao o conteudo da persona.\n")
    _escreve(fonte, "outra/persona.md",
             "Você é Outrilda Outronildo, segunda cadeira fixture — existe so para "
             "exercitar `--tudo` com mais de uma cadeira.\n")
    _publica(raiz, fonte)

    stubs = raiz / "stubs-bin"
    for nome in ("mesa", "fila", "minuta", "tarefas"):
        _executavel(_escreve(stubs, nome, STUB_VERBO))
    return raiz


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    return _monta_raiz(tmp_path)


def _run(args: list[str], raiz: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if raiz is not None:
        # PLATAFIRMA_INSTANCIA guia o default de PF_ABERTURA_DIR em monta-sessao; o
        # isolamento global (conftest.py) ja preenche PF_ABERTURA_DIR com A PROPRIA
        # morada vazia dele, entao sobrescrever so PLATAFIRMA_INSTANCIA nao bastaria
        # — as duas entram explicitas, para nao depender de qual delas o isolamento
        # deixou setada por ultimo.
        env["PLATAFIRMA_INSTANCIA"] = str(raiz)
        env["PF_ABERTURA_DIR"] = str(morada_de(raiz))
        env["PF_BIN"] = str(raiz / "stubs-bin")
    env.pop("PF_FITA", None)
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60, check=False)


# --- uso e ajuda --------------------------------------------------------------


def test_metrica_sem_arg_e_uso_incorreto_exit_2():
    proc = _run([])
    assert proc.returncode == 2
    assert "uso" in proc.stderr.lower()


def test_metrica_abertura_ajuda_imprime_uso_exit_0():
    proc = _run(["abertura", "--ajuda"])
    assert proc.returncode == 0
    assert "metrica abertura" in proc.stdout
    assert "--tudo" in proc.stdout
    assert "--json" in proc.stdout


# --- abertura <cadeira> --json --------------------------------------------------


def test_abertura_cadeira_json_sobre_fixture(raiz):
    proc = _run(["abertura", "teste", "--json"], raiz)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    assert dados["metodo_tokens"]
    total = dados["total"]
    assert total["cadeira"] == "teste"
    assert total["pecas"] > 0
    assert total["tokens"] >= 0
    # a peca `persona` existe no fixture e nao pode sair indisponivel: e o unico
    # arquivo real que este teste escreveu de proposito.
    pecas_persona = [p for p in dados["pecas"] if p["peca"] == "persona"]
    assert pecas_persona, dados["pecas"]
    assert pecas_persona[0]["frescor"] == "fresco"
    assert pecas_persona[0]["tokens"] > 0


def test_abertura_cadeira_texto_sem_json_tem_cabecalho_e_total(raiz):
    """Default (sem `--json`) e TEXTO — o inverso do resto de `metrica`, contrato
    herdado de `conta-abertura` que este ato promete manter."""
    proc = _run(["abertura", "teste"], raiz)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("# teste —")
    with pytest.raises(json.JSONDecodeError):
        json.loads(proc.stdout)


# --- --tudo ----------------------------------------------------------------


def test_abertura_tudo_json_lista_as_duas_cadeiras_com_pecas(raiz):
    proc = _run(["abertura", "--tudo", "--json"], raiz)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    nomes = {c["total"]["cadeira"] for c in dados["cadeiras"]}
    assert nomes == {"teste", "outra"}
    for c in dados["cadeiras"]:
        # --tudo pede a quebra por peca; sem a flag, `pecas` sai None (ver
        # `test_abertura_json_sem_tudo_omite_pecas_por_cadeira` abaixo).
        assert c["pecas"] is not None
        assert len(c["pecas"]) == c["total"]["pecas"]


def test_abertura_json_sem_tudo_omite_pecas_por_cadeira(raiz):
    proc = _run(["abertura", "--json"], raiz)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    assert len(dados["cadeiras"]) == 2
    assert all(c["pecas"] is None for c in dados["cadeiras"])


# --- cadeira inexistente -----------------------------------------------------


def test_abertura_cadeira_inexistente_exit_1(raiz):
    proc = _run(["abertura", "cadeira-que-nao-existe", "--json"], raiz)
    assert proc.returncode == 1
    dados = json.loads(proc.stdout)
    assert "desconhecida" in dados["erro"]
    assert set(dados["cadeiras_validas"]) == {"teste", "outra"}


def test_abertura_morada_nao_publicada_e_dependencia_ausente_exit_3(tmp_path):
    """Gate de morada (arq:0097) vem ANTES da validacao de cadeira: sem ela, o erro
    e "nao publicado", nunca "cadeira desconhecida" — e o exit e 3 (dependencia
    ausente), nao 1 (o achado seria falso: nao se sabe se a cadeira existe)."""
    raiz = tmp_path / "raiz-sem-morada"
    (morada_de(raiz)).mkdir(parents=True)
    proc = _run(["abertura", "teste", "--json"], raiz)
    assert proc.returncode == 3
    dados = json.loads(proc.stdout)
    assert "nao publicad" in dados["erro"]
    assert "desconhecida" not in dados["erro"]
