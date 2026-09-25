"""Contrato de `bin/monta-sessao --json` / `--sem-atualizar` (card #204, item 2).

Reescrito para o modelo de árvore única `abertura/` (arq:0073): persona, chapéu,
ferramental e caderno moram em `abertura/<cadeira>[/<slug>]/`; o nome canônico vem
do ledger de vínculo (`registro/eventos-org.jsonl`), não mais da linha 1 da persona
— a persona nova traz o ALIAS ali, não o slug. As peças de chapéu (chapeu, ferramental,
caderno-chapeu) só entram na 2ª chamada (`--chapeu <slug>`), servidas por catálogo.

Contrato: `{cadeira, nome_canonico, morada, pacote, pecas, chapeu, roteador, avisos}`,
peças em envelope uniforme. `fila` não é peça de abertura (verbo on-demand, ordem do
dono).

arq:0097 (runtime não lê working tree git): a abertura vem da MORADA PUBLICADA em
`$PF_ABERTURA_DIR/current/abertura`, e a chave `repos` do pacote deu lugar a `morada`.
O fixture publica a morada E mantém o clone git — de propósito: o clone existe para
provar que o montador NÃO o lê.

Isolamento: catálogo, morada e repositório vivem sob um `PF_RAIZ` hermético. O verbo
`mesa` entra por subprocess; `env_verbo()` prepende `{PF_RAIZ}/bin` no PATH, então o
stub mora em `<raiz>/bin/mesa` — e o stub de `git`, ao lado dele.
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
SCRIPT = REPO_ROOT / "bin" / "monta-sessao"

MESA_STUB = """#!/bin/sh
set -eu
sub="${1:-}"
case "$sub" in
  ver)
    case "${MESA_STUB_MODO:-ok}" in
      ok) printf '[abertura] escrito ha 3 min\\\\nresumo da fita anterior\\\\n' ;;
      falha) echo "mesa: msg-mem fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  caderno)
    case "${CADERNO_STUB_MODO:-ok}" in
      ok) printf 'caderno %s (stub)\\\\n' "${2:-<indice>}" ;;
      falha) echo "mesa: caderno fora do ar (stub)" 1>&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub mesa: subcomando nao coberto: $sub" 1>&2
    exit 2
    ;;
esac
"""

# Delator, não bloqueador: registra a chamada e ainda assim falha, para que um `git`
# que voltasse ao caminho de serviço apareça como linha no log E como pacote quebrado.
GIT_STUB = """#!/bin/sh
echo "$@" >> "${PF_GIT_LOG:?}"
echo "git nao pode ser chamado no caminho de servico (arq:0097)" 1>&2
exit 99
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _escreve(base: Path, rel: str, texto: str) -> Path:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def _peca(id_, artefato, *, evento="abertura", volatilidade="estavel"):
    return {
        "id": id_,
        "dono": "fixture",
        "artefato": artefato,
        "regime": "valor",
        "gatilho": {"evento": evento, "condicao": "fixture"},
        "volatilidade": volatilidade,
    }


def morada_de(raiz: Path) -> Path:
    """A morada publicada da raiz hermética — o contrato de `publicar-abertura`."""
    return raiz / "var" / "abertura-publicada"


def _publica(raiz: Path, sha: str = "0" * 40, publicado_em: str | None = None) -> None:
    """Publica a árvore do clone na morada, no formato de `publicar-abertura`.

    Cópia, não git: o contrato que este teste guarda é o de LEITURA da morada. Que a
    árvore saia de um commit imutável por `git archive` é contrato do publicador, e
    tem teste próprio — repetí-lo aqui só acoplaria este arquivo ao git de novo.
    """
    origem = raiz / "platafirma-harness" / "abertura"
    ref = morada_de(raiz) / "refs" / sha
    if ref.exists():
        shutil.rmtree(ref)
    ref.mkdir(parents=True)
    shutil.copytree(origem, ref / "abertura")
    arquivos = [p for p in (ref / "abertura").rglob("*") if p.is_file()]
    (ref / "MANIFEST.json").write_text(json.dumps({
        "sha": sha,
        "sha_curto": sha[:7],
        "ref": "origin/main",
        "tree_sha": "t" * 40,
        "publicado_em": publicado_em or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "publicado_por": "publicar-abertura",
        "n_arquivos": len(arquivos),
        "n_bytes": sum(p.stat().st_size for p in arquivos),
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    current = morada_de(raiz) / "current"
    if current.is_symlink() or current.exists():
        current.unlink()
    current.symlink_to(Path("refs") / sha)


def _monta_raiz(tmp_path: Path) -> Path:
    """Raiz hermética no modelo abertura/: árvore + ledger + git + morada publicada."""
    raiz = tmp_path / "raiz"
    harness = raiz / "platafirma-harness"


    # persona NOVA: alias na linha 1, sem FERRAMENTAL. O canônico sai do ledger.
    _escreve(harness, "abertura/teste/persona.md",
             "Você é Testildo Testonildo, a persona fixture do contrato de monta-sessao.\n\n"
             "Resto do corpo, irrelevante para o contrato --json.\n")
    _escreve(harness, "abertura/fabrica/persona.md",
             "Você é Fabrildo Forasteiro, persona fixture fora do quadro.\n")
    _escreve(harness, "abertura/oficio.md", "# ofício comum\n\nfixture.\n")
    _escreve(harness, "abertura/dono.md", "# conduta do dono\n\nfixture.\n")
    _escreve(harness, "abertura/antirreabertura.md", "# antirreabertura\n\nfixture.\n")
    _escreve(harness, "abertura/teste/caderno.md", "# caderno head\n\nfixture.\n")
    # perna 2 (chapéu rh da cadeira teste)
    _escreve(harness, "abertura/teste/rh/chapeu.md", "# chapéu rh\n\nfixture.\n")
    _escreve(harness, "abertura/teste/rh/ferramental.md", "# ferramental rh\n\nfixture.\n")

    # ledger de vínculo: golden do canônico (arq:0073 §1). Schema real tem "tipo"
    # (nao "evento") e "alias" — #2438 deriva o mapa alias-cadeiras destes campos.
    _escreve(harness, "registro/eventos-org.jsonl",
             json.dumps({"cadeira": "claudinho-teste", "tipo": "PROVIMENTO",
                        "alias": "Testildo Testonildo"}) + "\n" +
             json.dumps({"cadeira": "claudinho-engenharia", "tipo": "PROVIMENTO"}) + "\n")

    # Fonte VIVA de identidade (arq:0073 §1, incidente/ordem do dono): a árvore
    # abertura/ e o aliases.json. O ledger acima permanece como HISTÓRICO (consulta),
    # NÃO é lido para resolver identidade. `teste` tem alias; `engenharia` é cadeira
    # viva sem alias, para exercitar a nota de omissão declarada.
    _escreve(harness, "abertura/engenharia/persona.md", "# engenharia\n\nfixture.\n")
    _escreve(harness, "abertura/aliases.json",
             json.dumps({"teste": "Testildo Testonildo"}, ensure_ascii=False) + "\n")

    _executavel(_escreve(raiz, "bin/mesa", MESA_STUB))
    _executavel(_escreve(raiz, "bin/git", GIT_STUB))

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

    _publica(raiz)
    return raiz


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    return _monta_raiz(tmp_path)


def _run(args, raiz: Path, *, mesa_modo: str = "ok",
         caderno_modo: str = "ok") -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PF_RAIZ"] = str(raiz)
    # raizes.instancia() (lib/raizes.py, card #3010) le PLATAFIRMA_INSTANCIA, nao
    # PF_RAIZ: sem esta linha o montador resolvia MORADA (e SESSAO_SEGREDO) contra
    # a instancia REAL da conta (default /srv/platafirma/casa), e a hermeticidade
    # que este arquivo promete no docstring era so promessa. Achado ao investigar o
    # KeyError 'morada' e o 'cadeira desconhecida' falsos: os dois eram o montador
    # lendo abertura-publicada de producao, onde 'teste' nao e cadeira.
    env["PLATAFIRMA_INSTANCIA"] = str(raiz)
    # `git` do stub à frente do real: no caminho de serviço não deve haver git nenhum,
    # e o que houver fica registrado em PF_GIT_LOG.
    env["PATH"] = f"{raiz / 'bin'}{os.pathsep}" + env.get("PATH", "")
    env["PF_GIT_LOG"] = str(raiz / "git-chamado.log")
    env["MESA_STUB_MODO"] = mesa_modo
    env["CADERNO_STUB_MODO"] = caderno_modo
    env.pop("PF_FITA", None)
    env.pop("PF_FORA_DO_QUADRO", None)
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20, check=False)


# --- arq:0097: nada de working tree no caminho de serviço --------------------


def test_morada_nao_publicada_e_erro_com_a_cura_nomeada(raiz):
    """Ausência se declara. Sem morada a sessão não abre — e o erro traz o ato que a
    cura, não um diagnóstico de cadeira desconhecida (o gate vem antes da validação
    de cadeira justamente por isso)."""
    (morada_de(raiz) / "current").unlink()
    proc = _run(["teste", "--json"], raiz)
    assert proc.returncode == 1
    dados = json.loads(proc.stdout)
    assert "nao publicado" in dados["erro"]
    assert "desconhecida" not in dados["erro"]
    assert dados["morada"]["frescor"] == "indisponivel"
    assert dados["morada"]["motivo"]
    assert any("publicar-abertura" in a for a in dados["avisos"])


def test_publicado_em_ilegivel_vira_idade_desconhecida_nao_zero(tmp_path):
    """Idade desconhecida se declara como desconhecida. Carimbo ilegível virando 0.0
    seria o falso-verde 'acabou de publicar' — pior que a ausência."""
    raiz = _monta_raiz(tmp_path)
    _publica(raiz, publicado_em="ontem de manhã")
    dados = json.loads(_run(["teste", "--json"], raiz).stdout)
    assert dados["morada"]["idade_h"] is None
    assert not any("morada publicada ha" in a for a in dados["avisos"])


# --- resto do contrato ------------------------------------------------------


def test_sem_cadeira_e_uso_incorreto_exit_2(raiz):
    proc = _run(["--json"], raiz)
    assert proc.returncode == 2
    dados = json.loads(proc.stdout)
    assert dados["erro"]
