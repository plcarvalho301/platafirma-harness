"""A porta sem a pasta de trabalho da conta (card #3010, desenho §1/§3/§6).

Aceite coberto, tudo com as raizes em tmp:
- a porta importa sem bancada declarada e nao cria diretorio em bancada nenhuma;
- log, rascunho, derrame e abertura derivam da instancia; bin e PDP, da release;
- run_command sem cwd roda na casa da conta; cwd relativo e relativo a bancada
  declarada, e sem ela a chamada e recusada;
- read_file relativo sem bancada recusa; absoluto le;
- read_file nega <instancia>/segredos por construcao;
- write_file: morada = rascunho da fita + clones/worktrees da bancada declarada;
  release e log sao negados; sem bancada, clone fica fora de alcance.

    PLATAFIRMA_BANCADA nao precisa existir: o teste declara e desdeclara por monkeypatch.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-raizes-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
# Raiz herdada so vale se ja for tmp (outro modulo de teste chegou antes): o teste
# escreve em rascunho e log, e nunca pode cair numa instancia de verdade.
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)
# Arranque SEM bancada: nem variavel nem arquivo de declaracao.
_BANCADA_ANTES = os.environ.pop("PLATAFIRMA_BANCADA", None)
os.environ.setdefault("PLATAFIRMA_ARQUIVO_BANCADA", str(_TMP / "sem-declaracao"))

import poda  # noqa: E402
import server as s  # noqa: E402

if _BANCADA_ANTES is not None:
    os.environ["PLATAFIRMA_BANCADA"] = _BANCADA_ANTES


@pytest.fixture
def sem_bancada(monkeypatch, tmp_path):
    monkeypatch.delenv("PLATAFIRMA_BANCADA", raising=False)
    monkeypatch.setenv("PLATAFIRMA_ARQUIVO_BANCADA", str(tmp_path / "nao-declarada"))


@pytest.fixture
def bancada(monkeypatch, tmp_path):
    b = tmp_path / "bancada"
    (b / "platafirma-harness" / "bin").mkdir(parents=True)
    (b / "wt" / "platafirma-core" / "fabrica").mkdir(parents=True)
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(b))
    return b


@pytest.fixture
def sem_pep():
    with patch.object(s, "_autoriza", return_value=None), patch.object(s, "_audit"):
        yield


def test_nenhuma_raiz_resolve_para_a_casa_da_conta():
    """Toda raiz de producao da porta deriva de PF_RELEASE_RAIZ ou PLATAFIRMA_INSTANCIA."""
    inst, rel = Path(os.environ["PLATAFIRMA_INSTANCIA"]), Path(os.environ["PF_RELEASE_RAIZ"])
    assert s.LOG_DIR == inst / "var/log/ops"
    assert s.TMP_FITA == inst / "var/tmp"
    assert s.PERSONAS == inst / "var/abertura-publicada/current/abertura"
    assert poda.DERRAME == inst / "var/tmp/retornos"
    assert s.BIN_VERBOS == rel / "current/harness/bin"
    assert s.PDP_DIR == rel / "current/politica-acesso"


def test_arranque_sem_bancada_nao_cria_nada():
    assert not (_TMP / "sem-declaracao").exists()
    assert not any(p.name == "bancada" for p in _TMP.iterdir())


def test_path_do_subprocesso_traz_o_bin_da_release():
    assert s._env_subprocesso()["PATH"].split(":")[0] == str(s.BIN_VERBOS)


def test_run_command_sem_cwd_roda_na_casa(sem_bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd"))
    assert r["exit_code"] == 0
    assert r["stdout"]["texto"].strip() == str(Path(os.path.expanduser("~")).resolve())


def test_run_command_cwd_relativo_sem_bancada_recusa(sem_bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd", cwd="platafirma-core"))
    assert r["recusado"] and "bancada" in r["motivo"]


def test_run_command_cwd_relativo_e_na_bancada(bancada, sem_pep):
    with patch.object(s, "PF_RUN_SO_VERBO", False), patch.object(s, "PF_GATE", False):
        r = asyncio.run(s.run_command(command="pwd", cwd="platafirma-harness"))
    assert r["stdout"]["texto"].strip() == str((bancada / "platafirma-harness").resolve())


def test_read_file_relativo_sem_bancada_recusa_e_absoluto_le(sem_bancada, sem_pep, monkeypatch):
    r = s.read_file(path="platafirma-harness/ops-server/requirements.txt")
    assert r.get("recusado") and "bancada" in r["motivo"]
    # a árvore em teste entra na morada de leitura (card #3279): sem isto o absoluto recusa
    monkeypatch.setattr(s, "_MORADAS_LEITURA", (*s._MORADAS_LEITURA, str(OPS_SERVER_DIR)))
    r = s.read_file(path=str(OPS_SERVER_DIR / "requirements.txt"))
    assert "mcp==" in r["content"]


def test_read_file_nega_segredos_de_qualquer_instancia(tmp_path, monkeypatch, sem_pep):
    monkeypatch.setattr(s, "_RAIZES_DE_INSTANCIA", (Path("/srv/platafirma"), tmp_path))
    seg = tmp_path / "outra" / "segredos" / "core"
    seg.mkdir(parents=True)
    (seg / "POSTGRES").write_text("nao-leia")
    r = s.read_file(path=str(seg / "POSTGRES"))
    assert r.get("recusado") and r["motivo"].startswith("segredo")
    assert s._sob_segredos_de_instancia(Path("/srv/platafirma/casa/segredos/x/Y"))


@pytest.fixture
def fita(monkeypatch):
    """Declara a fita da chamada: a porta resolve o sessao_id para esta ordem_id."""
    def _declara(ordem):
        monkeypatch.setattr(s, "_sessao_resolve", lambda sid: {
            "sessao_id": "sid-teste", "ordem_id": ordem, "cadeira": "engenharia",
            "sujeito": "", "origem_sessao": ""})
    return _declara


def test_write_file_rascunho_sem_sessao_id_recusa(sem_bancada, sem_pep):
    """#3280 (F4 do #3277): sem sessao_id a ordem_id resolve a \"-\", e o \"-\" nao pode
    derrotar o confinamento por fita: recusa, e nenhuma subpasta nasce."""
    r = s.write_file(path=str(s.TMP_FITA / "o-SEM-SESSAO-x" / "probe.txt"), content="x\n")
    assert r.get("recusado") and "fita declarada" in r["motivo"], r
    r = s.write_file(path=str(s.TMP_FITA / "-" / "probe.txt"), content="x\n")
    assert r.get("recusado") and "fita declarada" in r["motivo"], r
    assert not (s.TMP_FITA / "o-SEM-SESSAO-x").exists()


def test_write_file_rascunho_com_fita_so_na_propria_subpasta(sem_bancada, sem_pep, fita):
    fita("o-minha")
    ok = s.write_file(path=str(s.TMP_FITA / "o-minha" / "probe.txt"), content="x\n", sessao_id="sid-teste")
    assert ok.get("ok"), ok
    alheia = s.write_file(path=str(s.TMP_FITA / "o-outra" / "probe.txt"), content="x\n", sessao_id="sid-teste")
    assert alheia.get("recusado") and "nao e a pasta desta fita" in alheia["motivo"], alheia


def test_write_file_sem_bancada_so_rascunho(sem_bancada, sem_pep, fita):
    fita("o-teste")
    ok = s.write_file(path=str(s.TMP_FITA / "o-teste" / "nota.md"), content="x\n", sessao_id="sid-teste")
    assert ok.get("ok"), ok
    r = s.write_file(path="platafirma-core/README.md", content="x\n")
    assert r.get("recusado") and "bancada" in r["motivo"]


def test_write_file_na_bancada_worktree_e_bin(bancada, sem_pep):
    r = s.write_file(path="wt/platafirma-core/fabrica/nota.md", content="x\n")
    assert r.get("ok"), r
    assert (bancada / "wt/platafirma-core/fabrica/nota.md").is_file()
    sem_shebang = s.write_file(path="platafirma-harness/bin/verbo", content="echo\n")
    assert sem_shebang.get("recusado") and "shebang" in sem_shebang["motivo"]
    verbo = s.write_file(path="platafirma-harness/bin/verbo", content="#!/bin/sh\necho\n")
    assert verbo.get("ok"), verbo
    assert os.access(bancada / "platafirma-harness/bin/verbo", os.X_OK)
    fora = s.write_file(path="outro-lugar/x.md", content="x\n")
    assert fora.get("recusado") and "fora de morada" in fora["motivo"]


def test_write_file_hook_no_hooks_do_harness_sem_extensao_com_shebang(bancada, sem_pep):
    """#3376: hooks/<nome> do harness e morada de hook como bin/ e de verbo: sem extensao,
    com shebang, executavel. Fora do harness, ou fora de bin/ e hooks/, segue recusado."""
    sem = s.write_file(path="platafirma-harness/hooks/pre-push", content="echo\n")
    assert sem.get("recusado") and "shebang" in sem["motivo"]
    ok = s.write_file(path="platafirma-harness/hooks/pre-push", content="#!/usr/bin/env bash\nexit 0\n")
    assert ok.get("ok"), ok
    assert os.access(bancada / "platafirma-harness/hooks/pre-push", os.X_OK)
    # reescrever mantem o modo
    de_novo = s.write_file(path="platafirma-harness/hooks/pre-push", content="#!/usr/bin/env bash\nexit 1\n")
    assert de_novo.get("ok"), de_novo
    assert os.access(bancada / "platafirma-harness/hooks/pre-push", os.X_OK)
    # hooks/ de outro repositorio nao e morada de hook
    outro = s.write_file(path="platafirma-core/hooks/pre-push", content="#!/bin/sh\nexit 0\n")
    assert outro.get("recusado") and "tipo" in outro["motivo"], outro
    # outro diretorio do harness segue recusado
    scripts = s.write_file(path="platafirma-harness/scripts/x", content="#!/bin/sh\nexit 0\n")
    assert scripts.get("recusado") and "tipo" in scripts["motivo"], scripts


def test_write_file_verbo_no_bin_da_bancada_por_cadeira_e_card(bancada, sem_pep):
    """card:3149 passo 3: a bancada e wt/platafirma-harness/<cadeira>/<card>/; o bin/ dela e
    morada de verbo como o do worktree plano (medido em 26/09: a porta recusava)."""
    (bancada / "wt" / "platafirma-harness" / "ti" / "3150-x" / "bin").mkdir(parents=True)
    r = s.write_file(path="wt/platafirma-harness/ti/3150-x/bin/verbo", content="#!/bin/sh\necho\n")
    assert r.get("ok"), r
    fora_do_bin = s.write_file(path="wt/platafirma-harness/ti/3150-x/deploy/unidade", content="x\n")
    assert fora_do_bin.get("recusado") and "tipo" in fora_do_bin["motivo"]


def test_write_file_nao_recria_bancada_nem_worktree(monkeypatch, tmp_path, sem_pep):
    """Bancada declarada e apagada (ou worktree nunca aberto): recusa, e nada nasce."""
    apagada = tmp_path / "bancada-apagada"
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(apagada))
    r = s.write_file(path="wt/platafirma-core/fabrica/nota.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    r = s.write_file(path="platafirma-core/README.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    assert not apagada.exists()
    viva = tmp_path / "bancada-viva"
    (viva / "wt" / "platafirma-core").mkdir(parents=True)
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(viva))
    r = s.write_file(path="wt/platafirma-core/outra-cadeira/nota.md", content="x\n")
    assert r.get("recusado") and "repo abrir" in r["motivo"], r
    assert not (viva / "wt" / "platafirma-core" / "outra-cadeira").exists()


def test_write_file_aceita_o_suporte_platafirma_casa(bancada, sem_pep):
    """arq:0115 §1.2: platafirma-casa e o suporte do documento de casa — worktree por cadeira
    (wt/platafirma-casa/<cadeira>) e clone (<bancada>/platafirma-casa) sao morada de escrita."""
    assert "platafirma-casa" in s.CLONES
    (bancada / "wt" / "platafirma-casa" / "dados").mkdir(parents=True)
    (bancada / "platafirma-casa").mkdir()
    wt = s.write_file(path="wt/platafirma-casa/dados/spec/acervo.md", content="# Acervo\n")
    assert wt.get("ok"), wt
    assert (bancada / "wt/platafirma-casa/dados/spec/acervo.md").is_file()
    diag = s.write_file(path="wt/platafirma-casa/dados/spec/acervo.1.mmd", content="graph TD; a-->b\n")
    assert diag.get("ok"), diag
    clone = s.write_file(path="platafirma-casa/adr/arq/0001-x.md", content="# 0001\n")
    assert clone.get("ok"), clone
    # worktree de cadeira que nao foi aberto segue recusado: write_file nao cria bancada
    nunca = s.write_file(path="wt/platafirma-casa/outra/x.md", content="x\n")
    assert nunca.get("recusado") and "repo abrir" in nunca["motivo"], nunca


def test_write_file_aceita_o_rastreador(bancada, sem_pep):
    """#3132: platafirma-rastreador e morada de escrita como os demais clones da stack."""
    assert "platafirma-rastreador" in s.CLONES
    (bancada / "wt" / "platafirma-rastreador" / "engenharia").mkdir(parents=True)
    (bancada / "platafirma-rastreador").mkdir()
    wt = s.write_file(path="wt/platafirma-rastreador/engenharia/api/nota.md", content="x\n")
    assert wt.get("ok"), wt
    clone = s.write_file(path="platafirma-rastreador/api/app.py", content="x = 1\n")
    assert clone.get("ok"), clone
    nunca = s.write_file(path="wt/platafirma-rastreador/outra/x.md", content="x\n")
    assert nunca.get("recusado") and "repo abrir" in nunca["motivo"], nunca

def test_write_file_aceita_php_e_mjs(bancada, sem_pep):
    """#3133: skin da wiki (.php) e provas do rastreador (.mjs) sao texto plano."""
    for nome in ("SkinPlataFirma.php", "2751_hierarquia_do_cartao.mjs"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/{nome}", content="x\n")
        assert r.get("ok"), (nome, r)
    binario = s.write_file(path="wt/platafirma-core/fabrica/x.exe", content="x\n")
    assert binario.get("recusado"), binario

def test_write_file_aceita_fonte_de_diagrama(bancada, sem_pep):
    """spec_porta-so-verbo §4.1: .mmd/.d2 sao fonte canonica de diagrama (ADR 0001/0051)."""
    mmd = s.write_file(path="wt/platafirma-core/fabrica/x.mmd", content="graph TD; a-->b\n")
    assert mmd.get("ok"), mmd
    d2 = s.write_file(path="wt/platafirma-core/fabrica/x.d2", content="a -> b\n")
    assert d2.get("ok"), d2


def test_write_file_aceita_texto_de_build_por_nome(bancada, sem_pep):
    """Dockerfile, .dockerignore e VERDES (baseline do pre-push) pelo nome; conf do nginx
    pela extensao .conf."""
    for nome in ("Dockerfile", ".dockerignore", "VERDES", "nginx.conf"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/site/{nome}", content="x\n")
        assert r.get("ok"), (nome, r)
    # o nome casa inteiro: arquivo sem extensao qualquer segue recusado
    outro = s.write_file(path="wt/platafirma-core/fabrica/site/Makefile", content="x\n")
    assert outro.get("recusado") and "Dockerfile" in outro["motivo"], outro


def test_write_file_aceita_unit_systemd(bancada, sem_pep):
    """#2856 linha 160 (card #3252): unit systemd nova (.service, .timer, .path, .socket) e
    texto plano de deploy; entrava so por write .txt + `repo git mv`."""
    for nome in ("cdi-gpu.service", "cdi-gpu.timer", "cdi-gpu.path", "cdi-gpu.socket"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/deploy/{nome}", content="[Unit]\n")
        assert r.get("ok"), (nome, r)
        assert (bancada / "wt/platafirma-core/fabrica/deploy" / nome).is_file()
    # maiuscula na extensao segue a mesma regra (ext e comparada em minuscula)
    assert s.write_file(path="wt/platafirma-core/fabrica/deploy/X.SERVICE", content="x\n").get("ok")
    # a lista cresceu so nessas quatro: outra extensao de unit segue recusada
    mount = s.write_file(path="wt/platafirma-core/fabrica/deploy/x.mount", content="x\n")
    assert mount.get("recusado") and "tipo" in mount["motivo"], mount


def test_write_file_aceita_tsv(bancada, sem_pep):
    """#3477: tabela TSV (platafirma-core, deploy/segredos/mapa.tsv) e texto plano; sem
    `.tsv` na lista a citacao a corrigir nela so saia por write .txt + `repo git mv`."""
    r = s.write_file(path="wt/platafirma-core/fabrica/deploy/segredos/mapa.tsv",
                     content="nome\tstack\n")
    assert r.get("ok"), r
    assert (bancada / "wt/platafirma-core/fabrica/deploy/segredos/mapa.tsv").read_text() == "nome\tstack\n"
    # maiuscula na extensao segue a mesma regra (ext e comparada em minuscula)
    assert s.write_file(path="wt/platafirma-core/fabrica/deploy/MAPA.TSV", content="x\n").get("ok")
    # a lista cresceu so em .tsv: planilha e CSV seguem recusados
    for nome in ("mapa.csv", "mapa.xlsx"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/deploy/{nome}", content="x\n")
        assert r.get("recusado") and "tipo" in r["motivo"], (nome, r)


def test_write_file_aceita_turtle(bancada, sem_pep):
    """#2856 linha 320 (card #3755): a shape SHACL e o grafo de nucleo da raiz sao Turtle,
    texto plano; sem `.ttl` na lista a estrutura da entidade nao tinha como ser escrita."""
    r = s.write_file(path="wt/platafirma-core/fabrica/ontologia/shapes/fichario.ttl",
                     content="@prefix pf: <https://platafirma.org/pf/> .\n")
    assert r.get("ok"), r
    assert (bancada / "wt/platafirma-core/fabrica/ontologia/shapes/fichario.ttl").is_file()
    # a lista cresceu so em .ttl: outra serializacao de RDF segue recusada
    for nome in ("nucleo.owl", "nucleo.rdf", "nucleo.nt"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/ontologia/{nome}", content="x\n")
        assert r.get("recusado") and "tipo" in r["motivo"], (nome, r)


def test_write_file_aceita_jsonl(bancada, sem_pep):
    """#3909 (peca 8 da #3506): o gabarito de avaliacao e JSON Lines, texto plano; sem
    `.jsonl` na lista a reenderecacao dele pela chave da secao nao tinha como ser escrita."""
    r = s.write_file(path="wt/platafirma-core/fabrica/avaliacao/gabarito.jsonl",
                     content='{"id": "a"}\n')
    assert r.get("ok"), r
    assert (bancada / "wt/platafirma-core/fabrica/avaliacao/gabarito.jsonl").read_text() == '{"id": "a"}\n'
    # a lista cresceu so em .jsonl: outra serializacao de linhas segue recusada
    for nome in ("gabarito.ndjson", "gabarito.csv"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/avaliacao/{nome}", content="x\n")
        assert r.get("recusado") and "tipo" in r["motivo"], (nome, r)


def test_write_file_aceita_dockerfile_com_sufixo(bancada, sem_pep):
    """#2856 linha 40: Dockerfile.<sufixo> (Dockerfile.gpu, Dockerfile.dev) e o mesmo texto
    de build do Dockerfile; o ponto exige sufixo, e outro nome segue recusado."""
    for nome in ("Dockerfile.gpu", "Dockerfile.dev"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/site/{nome}", content="FROM x\n")
        assert r.get("ok"), (nome, r)
    for nome in ("Dockerfile.", "Dockerfilex", "dockerfile.gpu", "Makefile.gpu"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/site/{nome}", content="x\n")
        assert r.get("recusado") and "tipo" in r["motivo"], (nome, r)


def test_write_file_aceita_codigo_de_front_jsx_ts_tsx(bancada, sem_pep):
    """#2856 linhas 237 e 240: componente JSX/TSX e TypeScript sao texto plano que o build de
    front le; sem as extensoes a prova de front so entrava por .js e `repo git mv`."""
    for nome in ("Tela.jsx", "api.ts", "Tela.tsx", "tipos.d.ts", "TELA.TSX"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/front/{nome}", content="x\n")
        assert r.get("ok"), (nome, r)
    # a lista cresceu so nessas tres: outro formato de componente segue recusado
    for nome in ("Tela.vue", "Tela.svelte", "api.mts"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/front/{nome}", content="x\n")
        assert r.get("recusado") and "tipo" in r["motivo"], (nome, r)


def test_write_file_aceita_gitignore_e_operacao_e_recusa_segredo_por_nome(bancada, sem_pep):
    """#2856 linhas 173 e 195: lista nominal, nunca regra de dotfile: `.env` e afins seguem fora."""
    for nome in (".gitignore", ".operacao"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/docs/{nome}", content="x\n")
        assert r.get("ok"), (nome, r)
    for nome in (".env", ".npmrc", ".netrc"):
        r = s.write_file(path=f"wt/platafirma-core/fabrica/docs/{nome}", content="x\n")
        assert r.get("recusado"), (nome, r)


def test_write_file_trecho_de_varias_linhas_casa_como_texto(bancada, sem_pep):
    """#2856 linhas 4, 193 e 217: o `antes` com parenteses, colchetes e quebra de linha casa como
    texto; antes o fallback escapava o texto inteiro, deixava uma barra solta e levantava
    re.error «unbalanced parenthesis» no lugar de dizer quantas vezes o trecho ocorre."""
    caminho = "wt/platafirma-core/fabrica/docs/spec.md"
    alvo = bancada / caminho
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text("a (b)\nc [--json]\n  d (0) e\n", encoding="utf-8")
    # casa uma vez, com parenteses e colchetes
    ok = s.write_file(path=caminho, trecho={"antes": "a (b)\nc [--json]", "depois": "A\nC"})
    assert ok.get("ok"), ok
    assert alvo.read_text(encoding="utf-8") == "A\nC\n  d (0) e\n"
    # nao casa: diz 0 vez(es), sem excecao
    zero = s.write_file(path=caminho, trecho={"antes": "x (y)\nz [--json]", "depois": "?"})
    assert zero.get("recusado") and "0 vez" in zero["motivo"], zero
    # parenteses desbalanceados em uma linha so casam como texto
    alvo.write_text("f(0\ng\n", encoding="utf-8")
    um = s.write_file(path=caminho, trecho={"antes": "f(0", "depois": "f(1"})
    assert um.get("ok"), um
    assert alvo.read_text(encoding="utf-8") == "f(1\ng\n"
    # a quebra e o recuo entre linhas sao tolerados (o que o fallback de varias linhas pedia)
    alvo.write_text("p (1)\n    q [2]\n", encoding="utf-8")
    t = s.write_file(path=caminho, trecho={"antes": "p (1)\nq [2]", "depois": "P\nQ"})
    assert t.get("ok"), t
    assert alvo.read_text(encoding="utf-8") == "P\nQ\n"
    # duas ocorrencias recusam, com a contagem
    alvo.write_text("k (1)\nm\nk (1)\nm\n", encoding="utf-8")
    dois = s.write_file(path=caminho, trecho={"antes": "k (1)\nm", "depois": "x"})
    assert dois.get("recusado") and "2 vez" in dois["motivo"], dois


def test_write_file_nega_release_e_log(bancada, sem_pep):
    rel = s.write_file(path=str(s.BIN_VERBOS / "x.md"), content="x\n")
    assert rel.get("recusado") and "release" in rel["motivo"]
    log = s.write_file(path=str(s.LOG_DIR / "x.txt"), content="x\n")
    assert log.get("recusado") and "log" in log["motivo"]


def test_derrame_devolve_caminho_absoluto(monkeypatch, tmp_path):
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "retornos")
    caminho = poda.derrama("sessao-x", "g1.txt", "inteiro")
    assert Path(caminho).is_absolute() and Path(caminho).read_text() == "inteiro"
