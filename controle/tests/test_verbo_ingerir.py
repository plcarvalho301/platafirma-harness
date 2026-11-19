# componente: componente:verbo-ingerir
"""Suíte consolidada do verbo `ingerir` (componente:verbo-ingerir).

Reúne os testes de:
- resumo, tabela de plano e sha256 da pasta (`bin/ingerir`);
- triagem da caixa de entrada, Portão 1 com subpastas e expurgo da chegada (`bin/_ingerir`);
- flags `--drive`, `--lote`, `--origem`, exclusividade de fontes e `rclone copy` sem apagar;
- registro da chegada em `POST /acervo/chegada` e lista de exceções fora da carga;
- coluna `Formato (ficha)` no plano e despertar do conversor sob demanda antes do POST do lote.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2]
REPO = str(HARNESS_DIR)
RAIZ = HARNESS_DIR
INGERIR = HARNESS_DIR / "bin" / "ingerir"
BIN_ACERVO = str(HARNESS_DIR / "bin" / "acervo")
BIN_INGERIR = str(INGERIR)

if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))
if str(HARNESS_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR / "lib"))

if "requests" not in sys.modules:
    sys.modules["requests"] = MagicMock()

try:
    import raizes as _raizes_check  # noqa: F401
except ModuleNotFoundError:
    _mod_raizes = types.ModuleType("raizes")
    _mod_raizes.instancia = lambda: Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    _mod_raizes.release = lambda: Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    sys.modules["raizes"] = _mod_raizes

try:
    from lib import motor_enderecos as _me_check  # noqa: F401
except (ModuleNotFoundError, ImportError):
    _mod_me = types.ModuleType("lib.motor_enderecos")
    _mod_me.api_acervo = lambda: "http://127.0.0.1:8000"
    sys.modules["lib.motor_enderecos"] = _mod_me
    if "lib" in sys.modules:
        sys.modules["lib"].motor_enderecos = _mod_me

from bin._ingerir import carga, expurgar_chegada  # noqa: E402

_loader = SourceFileLoader("ingerir_mod", str(INGERIR))
_spec = importlib.util.spec_from_loader("ingerir_mod", _loader)
ingerir = importlib.util.module_from_spec(_spec)
_loader.exec_module(ingerir)

calcular_sha256_pasta = ingerir.calcular_sha256_pasta
formatar_resumo_veredito_e_excecoes = ingerir.formatar_resumo_veredito_e_excecoes
formatar_tabela_plano = ingerir.formatar_tabela_plano


# --- resumo, saída e sha256 ----------------------------------------------------------------------------------------

def test_calcular_sha256_pasta():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        (d / "sub").mkdir()
        (d / "a.txt").write_text("conteudo a", encoding="utf-8")
        (d / "sub" / "b.txt").write_text("conteudo b", encoding="utf-8")

        sha1 = calcular_sha256_pasta(str(d))
        assert len(sha1) == 64

        sha2 = calcular_sha256_pasta(str(d))
        assert sha1 == sha2

        (d / "sub" / "b.txt").write_text("conteudo b alterado", encoding="utf-8")
        sha3 = calcular_sha256_pasta(str(d))
        assert sha3 != sha1


def test_formatar_resumo_veredito_e_excecoes_sem_excecoes():
    lote = {
        "id": "lote-123",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 2, "edicao": 0, "ja_ingerido": 0, "bloqueada": 0, "reprovado": 0},
        "itens": [
            {"posicao": 1, "arquivo": "doc1.pdf", "veredito": "criar", "portoes": []},
            {"posicao": 2, "arquivo": "doc2.pdf", "veredito": "criar", "portoes": []},
        ],
    }
    texto = formatar_resumo_veredito_e_excecoes(lote, fase="plano")
    assert "Plano de Ingestão: lote lote-123" in texto
    assert "total=2 | criar=2" in texto
    assert "Exceções e recusas:" not in texto


def test_formatar_resumo_veredito_e_excecoes_com_excecoes_e_recusa():
    lote = {
        "id": "lote-456",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 1, "edicao": 0, "ja_ingerido": 1, "bloqueada": 1, "reprovado": 1},
        "itens": [
            {"posicao": 1, "arquivo": "doc1.pdf", "veredito": "criar", "portoes": []},
            {
                "posicao": 2,
                "arquivo": "vazio.pdf",
                "veredito": "bloqueada",
                "portoes": [{"portao": "origem", "resultado": "bloqueada", "title": "ArquivoVazio", "detail": "0 bytes"}],
            },
            {
                "posicao": 3,
                "arquivo": "antigo.pdf",
                "veredito": "ja_ingerido",
                "portoes": [{"portao": "ja_ingerido", "resultado": "ja_ingerido", "title": "JaIngerido"}],
            },
            {
                "posicao": 4,
                "arquivo": "suspeito.pdf",
                "veredito": "reprovado",
                "portoes": [{"portao": "identidade", "resultado": "reprovado", "title": "SuspeitaEstacionada", "detail": "degrau 4"}],
            },
        ],
    }
    texto = formatar_resumo_veredito_e_excecoes(lote, fase="plano")
    assert "Plano de Ingestão: lote lote-456" in texto
    assert "Exceções e recusas:" in texto
    assert "[bloqueada] vazio.pdf: origem:ArquivoVazio — 0 bytes" in texto
    assert "[ja_ingerido] antigo.pdf: ja_ingerido:JaIngerido" in texto
    assert "[reprovado] suspeito.pdf: identidade:SuspeitaEstacionada — degrau 4" in texto


def test_formatar_tabela_vs_resumo():
    lote = {
        "id": "lote-789",
        "autor": "devops",
        "motor": "rag",
        "ate": "catalogar",
        "ocr": False,
        "colecao": "firma",
        "resumo": {"criar": 1, "edicao": 0, "ja_ingerido": 0, "bloqueada": 0, "reprovado": 0},
        "itens": [
            {"posicao": 1, "arquivo": "doc.pdf", "titulo": "Um Documento", "veredito": "criar", "portoes": []},
        ],
    }
    tabela = formatar_tabela_plano(lote)
    resumo = formatar_resumo_veredito_e_excecoes(lote, fase="plano")

    assert "Formato (ficha)" in tabela
    assert "Formato (ficha)" not in resumo
    assert "Resumo: total=1 | criar=1" in resumo


# --- carga da caixa de entrada e triagem ---------------------------------------------------------------------------

def test_portao_1_compara_manifesto_com_subpastas(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "raiz.pdf").write_text("conteudo raiz")
    sub = staging / "setor" / "2026"
    sub.mkdir(parents=True)
    (sub / "relatorio.pdf").write_text("conteudo relatorio")

    manifesto_ok = ["raiz.pdf", "setor/2026/relatorio.pdf"]
    ok, msg = carga.conferir_manifesto_portao_1(manifesto_ok, staging)
    assert ok is True
    assert "PORTÃO 1 aprovado: 2 arquivo(s)" in msg

    manifesto_incompleto = ["raiz.pdf", "setor/2026/relatorio.pdf", "setor/2026/faltou.pdf"]
    ok, msg = carga.conferir_manifesto_portao_1(manifesto_incompleto, staging)
    assert ok is False
    assert "diverge do staging" in msg or "lote incompleto" in msg


def test_escanear_pasta_triagem_separa_excecoes(tmp_path: Path):
    pasta = tmp_path / "lote"
    pasta.mkdir()

    (pasta / "livro.pdf").write_text("conteudo pdf")
    sub = pasta / "artigos" / "ti"
    sub.mkdir(parents=True)
    (sub / "paper.docx").write_text("conteudo docx")
    (pasta / "vazio.pdf").write_bytes(b"")
    (pasta / "meta.json").write_text('{"item": 1}')
    (pasta / "planilha.csv").write_text("a,b,c\n1,2,3")
    (pasta / "dados.ods").write_bytes(b"ods-fake")
    (pasta / "linhas.jsonl").write_text('{"k": "v"}\n')
    (pasta / "livro.sidecar.json").write_text('{"autor": "x"}')

    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)

    nomes_obras = {o["nome"] for o in obras}
    assert nomes_obras == {"livro.pdf", "paper.docx"}

    paper_item = next(o for o in obras if o["nome"] == "paper.docx")
    assert paper_item["pasta_origem"] == "artigos/ti"

    estados_excecoes = {e["nome"]: e["estado"] for e in excecoes}
    assert estados_excecoes["vazio.pdf"] == "vazio"
    assert estados_excecoes["meta.json"] == "json_comum"
    assert estados_excecoes["planilha.csv"] == "auxiliar"
    assert estados_excecoes["dados.ods"] == "auxiliar"
    assert estados_excecoes["linhas.jsonl"] == "auxiliar"
    assert estados_excecoes["livro.sidecar.json"] == "auxiliar"

    assert "vazio.pdf" not in nomes_obras
    assert "meta.json" not in nomes_obras
    assert "planilha.csv" not in nomes_obras


def test_expurgar_chegada_regra_20(tmp_path: Path):
    chegada_dir = tmp_path / "chegada"
    chegada_dir.mkdir()

    agora = 1700000000.0

    item_8_dias = chegada_dir / "sha256_antigo_8_dias"
    item_8_dias.mkdir()
    (item_8_dias / "arquivo.pdf").write_text("antigo")
    ts_8_dias = agora - (8 * 86400)
    os.utime(item_8_dias, (ts_8_dias, ts_8_dias))

    item_6_dias = chegada_dir / "sha256_recente_6_dias"
    item_6_dias.mkdir()
    (item_6_dias / "arquivo.pdf").write_text("recente")
    ts_6_dias = agora - (6 * 86400)
    os.utime(item_6_dias, (ts_6_dias, ts_6_dias))

    removidos = expurgar_chegada.expurgar_chegada(chegada_dir, dias=7, agora=agora)

    assert "sha256_antigo_8_dias" in removidos
    assert "sha256_recente_6_dias" not in removidos

    assert not item_8_dias.exists()
    assert item_6_dias.exists()


# --- --drive, --lote, --origem e rclone copy ----------------------------------------------------------------------

def _acha_python():
    """O primeiro python que tenha `requests`: o venv de teste pode nao ter, e
    `bin/ingerir` abre por `env python3`, que cai no python do PATH."""
    candidatos = [
        "/opt/platafirma/current/venv/acervo/bin/python",
        "/opt/platafirma/current/venv/harness/bin/python",
        sys.executable,
        shutil.which("python3"),
        "/usr/bin/python3",
    ]
    for cand in dict.fromkeys(candidatos):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return sys.executable


PY = _acha_python()


def _roda(argv, env):
    return subprocess.run(argv, env=env, capture_output=True, text=True, check=False)


def _executavel(caminho, conteudo):
    caminho.write_text(conteudo)
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def env_py(tmp_path):
    """Ambiente cujo `python3` e o que tem `requests`. Um script, nao um link: o link
    perderia o pyvenv.cfg ao lado do executavel."""
    pasta = tmp_path / "py"
    pasta.mkdir()
    (pasta / "raizes.py").write_text(
        "import os\nfrom pathlib import Path\n"
        "def instancia(): return Path(os.environ.get('PLATAFIRMA_INSTANCIA', '/srv/platafirma/casa'))\n",
        encoding="utf-8",
    )
    (pasta / "lib").mkdir()
    (pasta / "lib" / "motor_enderecos.py").write_text(
        "def api_acervo(): return 'http://127.0.0.1:8000'\n",
        encoding="utf-8",
    )
    _executavel(pasta / "python3", f'#!/bin/sh\nPYTHONPATH="{pasta}:$PYTHONPATH" exec {shlex.quote(PY)} "$@"\n')
    return dict(os.environ, PATH=f"{pasta}:{os.environ.get('PATH', '')}", PYTHONPATH=str(pasta))


def _env_drive(tmp_path, env_py, fake_bin):
    """Ambiente do --drive: rclone falso na frente e o staging numa pasta do teste,
    nunca em ~/AI/entrada (o teste nao toca o staging real)."""
    return dict(env_py, PF_ENTRADA_RAIZ=str(tmp_path / "entrada"),
                PATH=f"{fake_bin}:{env_py['PATH']}")


def test_ingerir_ajuda_mostra_drive_e_bucket(env_py):
    r = _roda([BIN_INGERIR, "--ajuda"], env_py)
    assert r.returncode == 2
    assert "--drive [<pasta>]" in r.stderr
    assert "--colecao, --bucket" in r.stderr


def test_ingerir_para_em_catalogar_sem_motor(env_py):
    r = _roda([BIN_INGERIR, "--ajuda"], env_py)
    assert "(default: catalogar)" in r.stderr
    assert "--motor <inst>]" not in r.stderr.splitlines()[1]


def _lote_sem_servidor(tmp_path, env_py, *extra):
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "obra.md").write_text("# Obra\n")
    env = dict(env_py, RAG_API_BASE="http://127.0.0.1:9")
    return _roda([BIN_INGERIR, "--lote", str(pasta), *extra], env)


def test_ingerir_sem_motor_nao_recusa_por_uso(tmp_path, env_py):
    r = _lote_sem_servidor(tmp_path, env_py)
    assert r.returncode != 2
    assert "obrigatório" not in r.stderr
    assert "aviso" not in r.stderr


def test_ingerir_ate_vetor_diz_que_encadeia_ate_o_ar(tmp_path, env_py):
    r = _lote_sem_servidor(tmp_path, env_py, "--ate", "vetor")
    assert r.returncode != 2
    assert "encadeia obra a obra até Transcrever, Indexar e pôr no ar" in r.stderr
    assert "motor rag indexar; acervo promover" in r.stderr
    assert "--promover" not in r.stderr


def test_ingerir_motor_em_catalogar_e_ignorado(tmp_path, env_py):
    r = _lote_sem_servidor(tmp_path, env_py, "--motor", "rag")
    assert "--motor e --ocr só valem com --ate além de catalogar" in r.stderr


def test_ingerir_exclusividade_fontes(env_py):
    r = _roda([BIN_INGERIR, "--lote", "/tmp/a", "--drive"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    r = _roda([BIN_INGERIR, "--origem", "gdrive:x", "--drive"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    r = _roda([BIN_INGERIR, "--motor", "rag"], env_py)
    assert r.returncode == 2
    assert "informe --lote <pasta>, --origem <gdrive:pasta|url> ou --drive [<pasta>]" in r.stderr


def test_acervo_ingerir_dispatch_drive(env_py):
    r = _roda([BIN_ACERVO, "ingerir", "--drive", "--lote", "x"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    r_bib = _roda([BIN_ACERVO, "ingerir", "biblioteca", "--drive", "--lote", "x"], env_py)
    assert r_bib.returncode == 2
    assert "mutuamente exclusivos" in r_bib.stderr


def test_portao_1_divergencia_aborta(tmp_path, env_py):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _executavel(fake_bin / "rclone", """#!/usr/bin/env bash
if [ "$1" = "copy" ]; then
    dest="$3"
    mkdir -p "$dest"
    touch "$dest/arq1.pdf" "$dest/arq2.pdf"
    exit 0
elif [ "$1" = "lsf" ]; then
    echo "arq1.pdf"
    echo "arq2.pdf"
    echo "arq3.pdf"
    exit 0
fi
exit 0
""")

    env = _env_drive(tmp_path, env_py, fake_bin)
    r = _roda([BIN_INGERIR, "--drive", "Teste/lote", "--motor", "rag"], env)
    assert r.returncode == 1
    assert "PORTÃO 1: contagem de rclone lsf (3) diverge do staging (2) — lote incompleto" in r.stderr


def test_portao_1_aprovado(tmp_path, env_py):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _executavel(fake_bin / "rclone", """#!/usr/bin/env bash
if [ "$1" = "copy" ]; then
    dest="$3"
    mkdir -p "$dest"
    touch "$dest/doc1.pdf" "$dest/doc2.pdf"
    exit 0
elif [ "$1" = "lsf" ]; then
    echo "doc1.pdf"
    echo "doc2.pdf"
    exit 0
fi
exit 0
""")

    env = _env_drive(tmp_path, env_py, fake_bin)
    r = _roda([BIN_INGERIR, "--drive", "--motor", "rag"], env)
    assert "PORTÃO 1 aprovado: 2 arquivo(s) conferidos no staging" in r.stderr


def test_drive_copia_sem_apagar_e_o_portao_1_acusa_o_que_sobrou_no_staging(tmp_path, env_py):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _executavel(fake_bin / "rclone", """#!/usr/bin/env bash
if [ "$1" = "copy" ]; then
    dest="$3"
    mkdir -p "$dest"
    touch "$dest/doc1.pdf" "$dest/doc2.pdf"
    exit 0
elif [ "$1" = "lsf" ]; then
    echo "doc1.pdf"
    echo "doc2.pdf"
    exit 0
elif [ "$1" = "sync" ]; then
    exit 9
fi
exit 0
""")

    raiz = tmp_path / "entrada"
    staging = raiz / f"drive-{time.strftime('%Y%m%d')}-entrada"
    staging.mkdir(parents=True)
    (staging / "doc1.pdf").touch()
    (staging / "saiu-do-drive.pdf").touch()

    env = _env_drive(tmp_path, env_py, fake_bin)
    r = _roda([BIN_INGERIR, "--drive", "--motor", "rag"], env)
    assert r.returncode == 1
    assert "PORTÃO 1: contagem de rclone lsf (2) diverge do staging (3) — lote incompleto" in r.stderr
    assert (staging / "saiu-do-drive.pdf").exists()


# --- registro da chegada em POST /acervo/chegada -------------------------------------------------------------------

class _Erro(Exception):
    pass


class RequestsFalso:
    """O `requests` do ingerir: guarda o que recebeu e devolve a resposta combinada."""

    def __init__(self, status=201, corpo=None, falha=None):
        self.chamadas, self._status, self._corpo, self._falha = [], status, corpo or {}, falha
        self.exceptions = SimpleNamespace(RequestException=_Erro)

    def post(self, url, json=None, headers=None, timeout=None):
        self.chamadas.append((url, json, headers))
        if self._falha:
            raise self._falha
        return SimpleNamespace(status_code=self._status, text="corpo", json=lambda: self._corpo)


@pytest.fixture
def pasta(tmp_path):
    raiz = tmp_path / "entrada"
    (raiz / "sub").mkdir(parents=True)
    (raiz / "a.pdf").write_bytes(b"%PDF conteudo a")
    (raiz / "sub" / "b.epub").write_bytes(b"conteudo b")
    (raiz / "vazio.pdf").write_bytes(b"")
    (raiz / "dados.json").write_text("{}")
    (raiz / "planilha.csv").write_text("arquivo,titulo\na.pdf,A\n")
    (raiz / "fila.jsonl").write_text("{}\n")
    (raiz / ".oculto").write_text("x")
    return raiz


def _sha(texto: bytes) -> str:
    return hashlib.sha256(texto).hexdigest()


def test_a_triagem_separa_obra_de_excecao_e_nunca_deixa_item_sumir(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    assert sorted(o["rel"] for o in obras) == ["a.pdf", "sub/b.epub"]
    estados = {e["rel"]: e["estado"] for e in excecoes}
    assert estados == {"vazio.pdf": "vazio", "dados.json": "json_comum", "planilha.csv": "auxiliar",
                       "fila.jsonl": "auxiliar"}


def test_os_itens_da_chegada_levam_a_procedencia_e_a_classificacao_presa_ao_arquivo(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    itens = carga.itens_da_chegada(obras, excecoes, {"a.pdf": {"dominio": "dados"}})
    por_nome = {i["nome"]: i for i in itens}
    assert por_nome["b.epub"]["pasta_origem"] == "sub" and por_nome["a.pdf"]["pasta_origem"] == ""
    assert por_nome["a.pdf"]["classificacao"] == {"dominio": "dados"}
    assert por_nome["a.pdf"]["sha256"] == _sha(b"%PDF conteudo a")
    assert "classificacao" not in por_nome["b.epub"]
    assert por_nome["vazio.pdf"]["estado"] == "vazio" and por_nome["vazio.pdf"]["tamanho"] == 0
    assert len(itens) == 6


def test_a_classificacao_so_vai_com_o_item_que_chegou_como_obra(pasta):
    obras, excecoes, _ = carga.escanear_pasta_triagem(pasta)
    itens = carga.itens_da_chegada(obras, excecoes, {"planilha.csv": {"dominio": "x"}, "vazio.pdf": {"dominio": "y"}})
    assert not any("classificacao" in i for i in itens if i["estado"] != "chegado")


def test_as_excecoes_saem_com_estado_e_causa():
    linhas = carga.linhas_das_excecoes([
        {"rel": "z.csv", "nome": "z.csv", "estado": "auxiliar", "motivo": "arquivo auxiliar ou planilha"},
        {"rel": "a/vazio.pdf", "nome": "vazio.pdf", "estado": "vazio", "motivo": "arquivo vazio (0 bytes); não é obra servível"},
    ])
    assert linhas[0] == "Fora da carga (não viraram obra):"
    assert "  [vazio] a/vazio.pdf: arquivo vazio (0 bytes); não é obra servível" in linhas
    assert "  [auxiliar] z.csv: arquivo auxiliar ou planilha" in linhas
    assert carga.linhas_das_excecoes([]) == []


def test_com_apply_a_chegada_vai_ao_servidor_com_o_lote_e_cada_estado(pasta, monkeypatch):
    falso = RequestsFalso(corpo={"registrados": 6, "por_estado": {}, "recusados": []})
    monkeypatch.setattr(ingerir, "requests", falso)
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {"a.pdf": {"dominio": "dados"}},
                                                {"authorization": "Bearer t"}, registrar=True)
    (url, corpo, headers), = falso.chamadas
    assert url.endswith("/acervo/chegada") and headers == {"authorization": "Bearer t"}
    assert corpo["lote_id"] == "L1" and len(corpo["itens"]) == 6
    assert {i["estado"] for i in corpo["itens"]} == {"chegado", "vazio", "json_comum", "auxiliar"}
    assert linhas[0] == "Fora da carga (não viraram obra):" and len(linhas) == 5


def test_sem_apply_o_plano_lista_as_excecoes_e_nao_grava_nada(pasta, monkeypatch):
    falso = RequestsFalso()
    monkeypatch.setattr(ingerir, "requests", falso)
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=False)
    assert falso.chamadas == [] and len(linhas) == 5


def test_chegada_que_falha_vira_aviso_e_o_lote_segue(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(falha=_Erro("caiu")))
    linhas = ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert len(linhas) == 5
    assert "a chegada não registrou (_Erro); o lote segue" in capsys.readouterr().err


def test_chegada_recusada_pelo_servidor_vira_aviso(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(status=500))
    ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert "a chegada não registrou (500)" in capsys.readouterr().err


def test_item_que_o_servidor_recusa_aparece_no_aviso(pasta, monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso(corpo={"recusados": [{"sha256": "abc", "motivo": "tamanho"}]}))
    ingerir.registrar_chegada_da_carga(str(pasta), "L1", {}, {}, registrar=True)
    assert "chegada recusou abc: tamanho" in capsys.readouterr().err


def test_no_json_a_lista_vai_para_o_stderr_e_a_saida_de_dados_fica_pura(capsys):
    linhas = ["Fora da carga (não viraram obra):", "  [vazio] x.pdf: vazio"]
    ingerir.mostrar_excecoes_da_carga(linhas, como_json=True)
    saida = capsys.readouterr()
    assert saida.out == "" and "[vazio] x.pdf" in saida.err
    ingerir.mostrar_excecoes_da_carga(linhas, como_json=False)
    assert "[vazio] x.pdf" in capsys.readouterr().out
    ingerir.mostrar_excecoes_da_carga([], como_json=False)
    assert capsys.readouterr().out == ""


def test_pasta_que_nao_se_le_nao_derruba_o_lote(monkeypatch, capsys):
    monkeypatch.setattr(ingerir, "requests", RequestsFalso())
    monkeypatch.setattr(ingerir, "escanear_pasta_triagem", lambda p: (_ for _ in ()).throw(OSError("sem permissão")))
    assert ingerir.registrar_chegada_da_carga("/x", "L1", {}, {}, registrar=True) == []
    assert "a triagem da chegada falhou" in capsys.readouterr().err


# --- Formato (ficha) no plano e despertar do conversor sob demanda -------------------------------------------------

FICHAS = {
    "minto-pyramid.pdf": {"formato": "JSON", "versao": None, "tipo": "application/json",
                          "identificacao": "identificado", "paginas": None, "paginas_ocr": None},
    "red-team.pdf": {"formato": "GZIP", "versao": None, "tipo": None,
                     "identificacao": "identificado", "paginas": None, "paginas_ocr": None},
    "livro.pdf": {"formato": "PDF", "versao": "1.7", "tipo": "application/pdf",
                  "identificacao": "identificado", "paginas": 23, "paginas_ocr": 2},
}


class _Resposta:
    def __init__(self, status: int, corpo: dict | None = None):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo) if corpo is not None else ""

    def json(self):
        return self._corpo


def _requests_falso(visto: dict):
    """O `requests` que o verbo usa, contra uma rag-api de mentira que devolve o plano do lote."""
    modulo = types.ModuleType("requests")
    modulo.Response = _Resposta
    modulo.exceptions = types.SimpleNamespace(RequestException=OSError)

    def put(url, data=None, headers=None, **_):
        data.read()
        return _Resposta(201)

    def post(url, json=None, headers=None, **_):
        visto["lote"] = json
        itens = []
        for posicao, item in enumerate(json["itens"]):
            portoes = [{"portao": "origem", "resultado": "aprovado"},
                       {"portao": "ficha", "resultado": "aprovado", "ficha": FICHAS[item["arquivo"]]}]
            itens.append({"posicao": posicao, "arquivo": item["arquivo"], "titulo": item["titulo"],
                          "veredito": "criar", "portoes": portoes})
        return _Resposta(201, {"id": "lote-1", "autor": json["autor"], "ate": json["ate"], "ocr": False,
                               "colecao": json["colecao"], "resumo": {"criar": len(itens)}, "itens": itens})

    modulo.put, modulo.post = put, post
    return modulo


def _mod(monkeypatch, visto: dict | None = None):
    monkeypatch.setitem(sys.modules, "requests", _requests_falso(visto if visto is not None else {}))
    loader = importlib.machinery.SourceFileLoader("ingerir_ficha", str(INGERIR))
    spec = importlib.util.spec_from_loader("ingerir_ficha", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _item(ficha=None, resultado="aprovado"):
    portao = {"portao": "ficha", "resultado": resultado}
    if ficha is not None:
        portao["ficha"] = ficha
    return {"portoes": [{"portao": "origem", "resultado": "aprovado"}, portao]}


def test_a_celula_diz_formato_versao_paginas_e_ocr(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item(FICHAS["livro.pdf"])) == "PDF 1.7 · 23p · 2 OCR"
    assert mod.descrever_ficha(_item(FICHAS["minto-pyramid.pdf"])) == "JSON"
    assert mod.descrever_ficha(_item(FICHAS["red-team.pdf"])) == "GZIP"


def test_pdf_sem_pagina_de_ocr_nao_poe_ocr_na_celula(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item({**FICHAS["livro.pdf"], "paginas_ocr": 0})) == "PDF 1.7 · 23p"


def test_ficha_que_o_conversor_nao_leu_no_plano_sai_com_interrogacao(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha(_item(None, "indisponivel")) == "?"


def test_item_sem_portao_ficha_sai_com_traco_e_formato_desconhecido_se_diz(monkeypatch):
    mod = _mod(monkeypatch)
    assert mod.descrever_ficha({"portoes": [{"portao": "ja_ingerido", "resultado": "ja_ingerido"}]}) == "-"
    assert mod.descrever_ficha({}) == "-"
    assert mod.descrever_ficha(_item({"formato": None, "identificacao": "desconhecido"})) == "desconhecido"


def test_o_plano_de_uma_pasta_de_teste_mostra_a_ficha_de_cada_arquivo(monkeypatch, tmp_path, capsys):
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "minto-pyramid.pdf").write_bytes(b'{"piramide": [1, 2]}')
    (pasta / "red-team.pdf").write_bytes(b"\x1f\x8b\x08\x00" + b"x" * 40)
    (pasta / "livro.pdf").write_bytes(b"%PDF-1.7\n" + b"0" * 100)
    monkeypatch.setenv("HOME", str(tmp_path))
    visto: dict = {}
    mod = _mod(monkeypatch, visto)
    monkeypatch.setattr(mod.subprocess, "run", lambda argv, **_: visto.setdefault("acordar", argv))
    monkeypatch.setattr(sys, "argv", ["ingerir", "--lote", str(pasta), "--tabela"])
    with pytest.raises(SystemExit) as saida:
        mod.main()
    assert saida.value.code == 0
    out = capsys.readouterr().out
    assert "Formato" in out
    linhas = {arq: linha for linha in out.splitlines() for arq in FICHAS if linha[4:].startswith(arq)}
    assert set(linhas) == set(FICHAS), out
    assert "JSON" in linhas["minto-pyramid.pdf"] and "GZIP" in linhas["red-team.pdf"]
    assert "PDF" not in linhas["minto-pyramid.pdf"].replace("minto-pyramid.pdf", "")
    assert "PDF 1.7 · 23p · 2 OCR" in linhas["livro.pdf"]
    assert all("formato" not in item and "tipo" not in item for item in visto["lote"]["itens"])


def test_o_plano_sem_apply_acorda_o_conversor_antes_do_lote(monkeypatch, tmp_path, capsys):
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "livro.pdf").write_bytes(b"%PDF-1.7\n" + b"0" * 100)
    monkeypatch.setenv("HOME", str(tmp_path))
    ordem: list[str] = []
    visto: dict = {}
    mod = _mod(monkeypatch, visto)
    post_original = mod.requests.post

    def post(url, **kw):
        ordem.append("post")
        return post_original(url, **kw)

    def run(argv, **_):
        ordem.append(" ".join(argv[-2:]))

    monkeypatch.setattr(mod.requests, "post", post)
    monkeypatch.setattr(mod.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["ingerir", "--lote", str(pasta)])
    with pytest.raises(SystemExit) as saida:
        mod.main()
    assert saida.value.code == 0
    assert ordem[0].endswith("conversor-sob-demanda acordar"), ordem
    assert ordem[1] == "post", ordem
