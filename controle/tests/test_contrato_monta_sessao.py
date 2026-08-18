"""Contrato de `bin/monta-sessao --json` / `--sem-atualizar` (card #204, item 2).

Este arquivo testava um `monta-sessao` que não existe mais: o script virou Python
na fase 5 do #189 (catálogo em `registro/pecas/*.json`, envelope uniforme por peça),
e a suíte antiga continuava chamando-o via bash e afirmando um shape com
`persona`/`manifesto`/`mesa`/`fila` soltos no topo — 17 de 17 vermelhos, vermelhos
antes de qualquer patch (medido em #204). Reescrito do zero contra o contrato real:
`{cadeira, nome_canonico, repos, pacote, pecas, avisos}`, peças em envelope uniforme
(peca/dono/ref/regime/volatilidade/teto_tokens/sha/tokens/frescor/motivo/conteudo).

INSUMO que motivou boa parte da reescrita (#204): `dados["fila"]["disponivel"]` não
existe em forma nenhuma desde harness@2ef6e19 — a fila saiu da abertura por ordem do
dono (é verbo on-demand agora, não peça de abertura). O contrato novo mede o pacote
de peças, não o pacote da fase 4; test_fila_nao_e_peca_de_abertura abaixo é o guarda
de regressão desse ponto específico.

Isolamento: catálogo, personas e repositório vivem sob um `PF_RAIZ` hermético (nunca
~/AI real). O script chama `git` de verdade — contra um bare local, sem rede — e o
verbo `mesa` (`mesa ver` / `mesa caderno`) por subprocess: `env_verbo()` do próprio
script prepende `{PF_RAIZ}/bin` no PATH antes de chamar peça-verbo, então o stub
mora em `<raiz>/bin/mesa` e nem precisa ser injetado por fora. `fila` não é mais
chamado pela abertura e por isso não tem stub aqui — dar-lhe um seria testar
comportamento que o script não tem.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "monta-sessao"

MESA_STUB = """#!/bin/sh
set -eu
sub="${1:-}"
case "$sub" in
  ver)
    case "${MESA_STUB_MODO:-ok}" in
      ok) printf '[abertura] escrito ha 3 min\\nresumo da fita anterior\\n' ;;
      falha) echo "mesa: msg-mem fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  caderno)
    case "${CADERNO_STUB_MODO:-ok}" in
      ok) printf 'cadernos: nenhum (stub)\\n' ;;
      falha) echo "mesa: caderno fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub mesa: subcomando nao coberto: $sub" 1>&2
    exit 2
    ;;
esac
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _escreve(base: Path, rel: str, texto: str) -> Path:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


def _peca(id_, artefato, *, evento="abertura", volatilidade="estavel", teto_tokens=2000, emenda=None):
    obj = {
        "id": id_,
        "dono": "fixture",
        "artefato": artefato,
        "regime": "valor",
        "gatilho": {"evento": evento, "condicao": "fixture"},
        "volatilidade": volatilidade,
    }
    if teto_tokens is not None:
        obj["teto_tokens"] = teto_tokens
    if emenda:
        obj["emenda"] = emenda
    return obj


def _monta_raiz(tmp_path: Path, *, teto_tool_manifest: int = 2000) -> Path:
    """Constrói uma raiz hermética: catálogo + personas + repo git com upstream.

    O repo git real (não só `git init`) é necessário porque `sha_e_frescor` chama
    `git rev-list HEAD..@{upstream}` — sem upstream configurado, a idade do clone
    não tem o que medir e o script cai no ramo "sem upstream conhecido"; COM
    upstream e nada a puxar, cai em "fresco" sem aviso, que é o caminho feliz que a
    maioria dos testes aqui quer, e o mesmo remoto local deixa `pull()` (com
    --atualizar) e o skip de `pull()` (com --sem-atualizar) distinguíveis de fato.
    """
    raiz = tmp_path / "raiz"
    harness = raiz / "platafirma-harness"
    pecas_dir = harness / "registro" / "pecas"

    catalogo = [
        _peca("persona", "platafirma-harness@personas/persona-{cadeira}.md", teto_tokens=2000),
        _peca("org", "platafirma-harness@org/fronteiras.md", volatilidade="morna", teto_tokens=900),
        _peca("tool-manifest-geral", "platafirma-harness@tool-manifest/nucleo.md", teto_tokens=1200),
        _peca("antirreabertura", "platafirma-harness@registro/antirreabertura.md",
              volatilidade="morna", teto_tokens=800),
        _peca("tool-manifest-cadeira", "platafirma-harness@tool-manifest/{cadeira}.md",
              teto_tokens=teto_tool_manifest),
        _peca("mesa", "verbo:mesa ver", volatilidade="volatil", teto_tokens=250),
        _peca("cadernos-indice", "verbo:mesa caderno", volatilidade="volatil", teto_tokens=100),
        _peca("alias-cadeiras", "platafirma-harness@personas/alias-cadeiras.md",
              evento="ato", volatilidade="morna", teto_tokens=None, emenda="org"),
    ]
    for p in catalogo:
        _escreve(pecas_dir, f"{p['id']}.json", json.dumps(p, ensure_ascii=False))

    _escreve(harness, "personas/persona-teste.md",
             "Você é ClaudinhoTeste, a persona fixture do contrato de monta-sessao.\n\n"
             "FERRAMENTAL: platafirma-harness/tool-manifest/teste.md\n\n"
             "Resto do corpo, irrelevante para o contrato --json.\n")
    _escreve(harness, "personas/persona-fabrica.md",
             "Você é ClaudinhoFabricaTeste, persona fixture fora do quadro.\n\n"
             "FERRAMENTAL: platafirma-harness/tool-manifest/fabrica.md\n")
    _escreve(harness, "personas/alias-cadeiras.md", "# Mapa de endereço\n\nfixture.\n")
    _escreve(harness, "org/fronteiras.md", "# org canônico\n\nfixture.\n")
    _escreve(harness, "tool-manifest/nucleo.md", "# núcleo comum\n\nfixture.\n")
    _escreve(harness, "tool-manifest/teste.md", "# manifesto de teste\n\nferramental fixture.\n")
    _escreve(harness, "tool-manifest/fabrica.md", "# manifesto da fábrica\n\nferramental fixture.\n")
    _escreve(harness, "registro/antirreabertura.md", "# antirreabertura\n\nfixture.\n")

    stub = _escreve(raiz, "bin/mesa", MESA_STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)],
                    check=True, capture_output=True, text=True)
    _git(harness, "init", "-q", "-b", "main")
    _git(harness, "config", "user.email", "fixture@test.local")
    _git(harness, "config", "user.name", "fixture")
    _git(harness, "add", "-A")
    _git(harness, "commit", "-q", "-m", "fixture inicial")
    _git(harness, "remote", "add", "origin", str(origin))
    _git(harness, "push", "-q", "-u", "origin", "main")

    return raiz


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    return _monta_raiz(tmp_path)


def _run(args, raiz: Path, *, mesa_modo: str = "ok",
         caderno_modo: str = "ok") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PF_RAIZ"] = str(raiz)
    env["MESA_STUB_MODO"] = mesa_modo
    env["CADERNO_STUB_MODO"] = caderno_modo
    env.pop("PF_FITA", None)  # regra do teste de registro: sessão de mão, sem fita
    env.pop("PF_FORA_DO_QUADRO", None)  # usa o default documentado do script
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20, check=False)


ENVELOPE_CHAVES = {"peca", "dono", "ref", "regime", "volatilidade", "teto_tokens",
                    "sha", "tokens", "frescor", "motivo", "conteudo"}


# --- formato e caminho feliz ------------------------------------------------


def test_json_pacote_e_objeto_unico_com_envelope_uniforme(raiz):
    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 0
    assert proc.stdout.count("\n") == 1  # uma linha só, o objeto
    dados = json.loads(proc.stdout)

    assert dados["cadeira"] == "teste"
    assert dados["nome_canonico"] == "ClaudinhoTeste"
    assert "fila" not in dados  # ver test_fila_nao_e_peca_de_abertura

    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert ENVELOPE_CHAVES <= por_id["org"].keys()  # §6.2: toda peça no mesmo shape
    assert por_id["org"]["frescor"] == "fresco"
    assert por_id["org"]["conteudo"]
    assert "alias-cadeiras" not in por_id  # gatilho "ato": dentro do quadro não entra

    assert dados["pacote"]["pecas"] == len(dados["pecas"])
    assert dados["pacote"]["tokens"] == sum(p["tokens"] for p in dados["pecas"])
    assert dados["pacote"]["metodo_tokens"]
    assert dados["pacote"]["registro"] == {
        "registrado": False, "motivo": "sem PF_FITA — sessao de mao nao tem fita"}

    assert dados["repos"]["platafirma-harness"]["atualizado"] is True
    assert dados["repos"]["platafirma-harness"]["frescor"] == "fresco"


def test_fila_nao_e_peca_de_abertura(raiz):
    """INSUMO do #204: `dados["fila"]["disponivel"]` não existe desde harness@2ef6e19
    — a fila saiu da abertura por ordem do dono. Guarda de regressão: nem chave de
    topo, nem peça na lista, em nenhum dos dois formatos que a suíte antiga media."""
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert "fila" not in dados
    assert "fila" not in {p["peca"] for p in dados["pecas"]}


def test_atualizado_reflete_flag_sem_atualizar(raiz):
    com = json.loads(_run(["teste", "--json"], raiz).stdout)
    sem = json.loads(_run(["teste", "--json", "--sem-atualizar"], raiz).stdout)
    assert com["repos"]["platafirma-harness"]["atualizado"] is True
    assert sem["repos"]["platafirma-harness"]["atualizado"] is False


def test_fora_do_quadro_troca_org_por_alias_cadeiras(raiz):
    """Cadeira fora do quadro (#161 opção A): org, antirreabertura e
    tool-manifest-geral saem; alias-cadeiras entra forçado, mesmo tendo gatilho
    `ato` (não `abertura`) — é a excepção nominal do dono, não inferência daqui."""
    dados = json.loads(_run(["fabrica", "--json"], raiz).stdout)
    por_id = {p["peca"]: p for p in dados["pecas"]}

    assert "org" not in por_id
    assert "antirreabertura" not in por_id
    assert "tool-manifest-geral" not in por_id
    assert "tool-manifest-cadeira" in por_id  # manifesto da própria cadeira continua

    assert "alias-cadeiras" in por_id
    assert por_id["alias-cadeiras"]["motivo"] == "fora do quadro: org trocado por endereço"


def test_prefixo_claudinho_e_descartado(raiz):
    """`claudinho-teste` e `teste` têm de resolver a mesma persona — o prefixo é
    convenção de quem chama, não faz parte do nome do arquivo de persona."""
    dados = json.loads(_run(["claudinho-teste", "--json"], raiz).stdout)
    assert dados["cadeira"] == "teste"
    assert dados["nome_canonico"] == "ClaudinhoTeste"


def test_cadeira_desconhecida_vira_objeto_de_erro_nunca_stdout_vazio(raiz):
    """Regra dura: nunca stdout vazio em falha. Exit 1 preservado."""
    proc = _run(["fantasma", "--json"], raiz)
    assert proc.returncode == 1
    assert proc.stdout.count("\n") == 1
    dados = json.loads(proc.stdout)
    assert dados["erro"]
    assert "teste" in dados["cadeiras_validas"]
    assert "fabrica" in dados["cadeiras_validas"]


def test_sem_cadeira_e_uso_incorreto_exit_2(raiz):
    proc = _run(["--json"], raiz)
    assert proc.returncode == 2
    dados = json.loads(proc.stdout)
    assert dados["erro"]


# --- indisponibilidade parcial ----------------------------------------------


def test_peca_verbo_indisponivel_nao_derruba_o_pacote(raiz):
    """Peça-verbo fora do ar: `frescor: indisponivel` com motivo, conteúdo None
    — mas o resto do pacote (as outras peças) continua saindo. Indisponibilidade
    parcial nunca é falha do pacote inteiro nem stdout vazio."""
    dados = json.loads(_run(["teste", "--json"], raiz, mesa_modo="falha").stdout)
    por_id = {p["peca"]: p for p in dados["pecas"]}
    assert por_id["mesa"]["frescor"] == "indisponivel"
    assert por_id["mesa"]["motivo"]
    assert por_id["mesa"]["conteudo"] is None
    assert por_id["org"]["frescor"] == "fresco"
    assert dados["pacote"]["pecas"] == len(dados["pecas"])
    assert any("mesa" in a and "indisponível" in a for a in dados["avisos"])


def test_peca_com_teto_excedido_gera_aviso(tmp_path):
    raiz = _monta_raiz(tmp_path, teto_tool_manifest=1)
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert any("tool-manifest-cadeira" in a and "teto declarado" in a
               for a in dados["avisos"])


# --- regressão do texto sem --json ------------------------------------------


def test_sem_json_mantem_marcadores_de_texto(raiz):
    """Regra dura: saída sem --json é o modo texto de sempre — confere os
    marcadores `===== <peca>: <ref> ... =====` e ausência de JSON solto."""
    proc = _run(["teste"], raiz)
    assert proc.returncode == 0
    linhas = proc.stdout.splitlines()
    assert linhas[0] == "== cadeira: ClaudinhoTeste =="
    assert any(l.startswith("===== org: platafirma-harness@org/fronteiras.md")
               for l in linhas)
    assert "{" not in proc.stdout  # nada de JSON escapado por engano no texto solto
