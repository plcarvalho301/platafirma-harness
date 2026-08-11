"""Contrato de `bin/monta-sessao --json` / `--sem-atualizar` (card #390, LOTE 1).

`monta-sessao` é bash e fala com o mundo por três verbos externos (`git`,
`mesa`, `fila`) além do sistema de arquivos. Isola com um PATH de teste:
  - `git` real (já está no PATH do git-bash) — a raiz da fixture nunca é um
    repositório git de verdade, então `git -C <repo> pull` falha rápido e sem
    rede ("fatal: not a git repository"), exatamente o caminho de erro que o
    script já trata com o aviso em stderr. Isso também serve pra provar
    --sem-atualizar: com a flag, esse aviso não aparece porque o loop nem roda.
  - `mesa`/`fila` — stubs escritos à mão (não existe `bin/fila` neste repo
    ainda, só `fila_streams.py`; e não há Redis/msg-mem nesta máquina), cada
    um com um "modo" selecionável por env var pra cobrir disponível/vazio/
    indisponível sem precisar de infra viva.
  - `PF_RAIZ` aponta pra uma fixture hermética com
    platafirma-harness/personas/persona-<C>.md e
    platafirma-arquitetura/docs/org-template-canonico.md — nunca contra
    ~/AI real (não existe nesta máquina do jeito que o script presume).

Camada 1 do modelo de teste do card (NOTAS-390.md): por verbo com --json, um
teste de formato + um de falha. Regressão do texto sem --json também é
coberta aqui porque é a mesma função que ganhou o desvio de --json.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "monta-sessao"


def _achar_bash() -> str:
    """No Windows, "bash" no PATH pode resolver pro launcher do WSL
    (C:\\WINDOWS\\system32\\bash.exe, sem distro instalada) em vez do
    git-bash. Preferir o git-bash explicitamente."""
    candidatos = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for c in candidatos:
        if Path(c).is_file():
            return c
    achado = shutil.which("bash")
    if achado:
        return achado
    pytest.skip("nenhum bash (git-bash) encontrado")


BASH = _achar_bash()

# --- stubs de mesa/fila -------------------------------------------------
# Só os subcomandos que monta-sessao de fato chama: `mesa ver`, `mesa
# caderno` (sem slot) e `fila status <persona>`. Modo por env var pra cada
# teste escolher disponível/vazio/indisponível sem precisar de infra viva.

FAKE_MESA = r"""#!/usr/bin/env bash
set -euo pipefail
sub="${1:-}"
case "$sub" in
  ver)
    case "${MESA_STUB_MODO:-ok}" in
      ok)    printf '[abertura] escrito ha 3 min\nresumo da fita anterior\n\n' ;;
      vazia) printf 'mesa vazia\n' ;;
      falha) echo "mesa: msg-mem fora do ar (stub)" >&2; exit 1 ;;
    esac
    ;;
  caderno)
    case "${CADERNO_STUB_MODO:-ok}" in
      ok)    printf 'cadernos: nenhum (stub)\n' ;;
      falha) echo "mesa: caderno fora do ar (stub)" >&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub mesa: subcomando nao coberto: $sub" >&2
    exit 2
    ;;
esac
"""

FAKE_FILA = r"""#!/usr/bin/env bash
set -euo pipefail
sub="${1:-}"; persona="${2:-}"
case "$sub" in
  status)
    case "${FILA_STUB_MODO:-ok}" in
      ok)      printf '%s: 2 nova(s) \xc2\xb7 5 no historico (7 dias)\n' "$persona" ;;
      vazia)   printf '%s: caixa vazia\n' "$persona" ;;
      fechada) echo "erro: caixa de $persona fechada pelo porteiro (stub)" >&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub fila: subcomando nao coberto: $sub" >&2
    exit 2
    ;;
esac
"""


@pytest.fixture()
def bin_stub(tmp_path: Path) -> Path:
    d = tmp_path / "stubbin"
    d.mkdir()
    mesa = d / "mesa"
    fila = d / "fila"
    mesa.write_text(FAKE_MESA, encoding="utf-8", newline="\n")
    fila.write_text(FAKE_FILA, encoding="utf-8", newline="\n")
    for p in (mesa, fila):
        p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return d


# --- fixture de RAIZ (PF_RAIZ) -------------------------------------------
# platafirma-harness/personas/persona-<C>.md e
# platafirma-arquitetura/docs/org-template-canonico.md — a forma mínima que
# o script espera, nunca o ~/AI real.

MANIFESTO_REL = "platafirma-harness/tool-manifest/manifesto-teste.md"
GERAL_REL = "platafirma-harness/tool-manifest/TODA-CADEIRA.md"
ORG_REL = "platafirma-arquitetura/docs/org-template-canonico.md"


def _escreve(raiz: Path, rel: str, texto: str) -> Path:
    caminho = raiz / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return caminho


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    r = tmp_path / "raiz"
    _escreve(
        r,
        "platafirma-harness/personas/persona-teste.md",
        "Você é ClaudinhoTeste, a persona fixture do card #390.\n\n"
        f"FERRAMENTAL: {MANIFESTO_REL}\n\n"
        "Resto do corpo, irrelevante pro contrato --json.\n",
    )
    _escreve(r, MANIFESTO_REL, "# manifesto de teste\n\nferramental fixture.\n")
    _escreve(r, GERAL_REL, "# GERAL\n\noperacional comum, fixture.\n")
    _escreve(r, ORG_REL, "# org canônico\n\nfixture.\n")
    return r


def _run(
    args,
    raiz: Path,
    bin_stub: Path,
    tmp_path: Path,
    *,
    mesa_modo: str = "ok",
    fila_modo: str = "ok",
    caderno_modo: str = "ok",
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = str(bin_stub) + os.pathsep + env.get("PATH", "")
    env["PF_RAIZ"] = str(raiz)
    env["MESA_STUB_MODO"] = mesa_modo
    env["FILA_STUB_MODO"] = fila_modo
    env["CADERNO_STUB_MODO"] = caderno_modo
    home_falso = tmp_path / "home-falso"
    home_falso.mkdir(exist_ok=True)
    env["HOME"] = str(home_falso)
    cmd = [BASH, str(SCRIPT), *args]
    return subprocess.run(
        cmd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20,
        check=False,
    )


# --- formato, caminho feliz ------------------------------------------------


def test_json_e_objeto_unico_bem_formado(raiz, bin_stub, tmp_path):
    """--json: stdout é só o objeto — nada de texto humano misturado (a régua
    "nada de mistura" cai se sobrar qualquer coisa: json.loads reclamaria de
    "Extra data")."""
    proc = _run(["teste", "--json"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.count("\n") == 1  # uma linha só, o objeto
    dados = json.loads(proc.stdout)

    assert dados["cadeira"] == "teste"
    assert dados["persona"] == {
        "presente": True,
        "caminho": "platafirma-harness/personas/persona-teste.md",
        "nome_resolvido": "ClaudinhoTeste",
    }
    assert dados["manifesto"] == {"presente": True, "caminho": MANIFESTO_REL}
    assert dados["org"] == {"caminho": ORG_REL, "presente": True}
    assert dados["mesa"]["disponivel"] is True
    assert isinstance(dados["mesa"]["resumo"], str) and dados["mesa"]["resumo"]
    assert dados["cadernos"]["disponivel"] is True
    assert isinstance(dados["cadernos"]["resumo"], str) and dados["cadernos"]["resumo"]
    assert dados["fila"]["disponivel"] is True
    assert "ClaudinhoTeste" in dados["fila"]["resumo"]
    assert dados["atualizado"] is True


def test_json_atualizado_reflete_sem_atualizar_e_pula_o_pull(raiz, bin_stub, tmp_path):
    """--sem-atualizar: atualizado:false no objeto, e o loop de `git pull`
    nem roda — sem ele, git falharia contra a fixture (não é repo) e
    avisaria em stderr; com a flag, esse aviso não deve aparecer."""
    proc_com = _run(["teste", "--json"], raiz, bin_stub, tmp_path)
    proc_sem = _run(["teste", "--json", "--sem-atualizar"], raiz, bin_stub, tmp_path)

    assert proc_com.returncode == 0 and proc_sem.returncode == 0
    assert json.loads(proc_com.stdout)["atualizado"] is True
    assert json.loads(proc_sem.stdout)["atualizado"] is False

    assert "não atualizou" in proc_com.stderr
    assert "não atualizou" not in proc_sem.stderr


def test_sem_atualizar_sem_json_tambem_pula_o_pull(raiz, bin_stub, tmp_path):
    """--sem-atualizar sozinha (sem --json) também deve funcionar: só pula o
    pull, texto continua saindo."""
    proc = _run(["teste", "--sem-atualizar"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    assert "não atualizou" not in proc.stderr
    assert proc.stdout.startswith("== cadeira: ClaudinhoTeste ==")


@pytest.mark.parametrize(
    "args",
    [
        ["teste", "--json", "--sem-atualizar"],
        ["--json", "--sem-atualizar", "teste"],
        ["--sem-atualizar", "--json", "teste"],
        ["--json", "teste", "--sem-atualizar"],
    ],
    ids=["cadeira-primeiro", "flags-primeiro", "flags-invertidas", "cadeira-no-meio"],
)
def test_flags_juntas_ou_separadas_em_qualquer_ordem(raiz, bin_stub, tmp_path, args):
    proc = _run(args, raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["cadeira"] == "teste"
    assert dados["atualizado"] is False


def test_json_nome_nao_resolvido_vira_null_e_fila_fica_indisponivel(
    raiz, bin_stub, tmp_path
):
    """Linha 1 da persona não bate no padrão "Você é <nome>," -> nome_resolvido
    é null (nunca string vazia camuflada) e fila nem tenta rodar — não tem
    como saber a caixa sem o nome."""
    _escreve(
        raiz,
        "platafirma-harness/personas/persona-semnome.md",
        "Isto não segue \"Você é <nome>,\" -- nome não resolve.\n\n"
        f"FERRAMENTAL: {MANIFESTO_REL}\n",
    )
    proc = _run(["semnome", "--json", "--sem-atualizar"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["persona"]["nome_resolvido"] is None
    assert dados["fila"]["disponivel"] is False
    assert dados["fila"]["resumo"] is not None  # motivo curto, não silêncio


def test_json_manifesto_ausente_quando_persona_nao_declara_ferramental(
    raiz, bin_stub, tmp_path
):
    _escreve(
        raiz,
        "platafirma-harness/personas/persona-semmanifesto.md",
        "Você é SemManifesto, persona sem linha FERRAMENTAL.\n",
    )
    proc = _run(["semmanifesto", "--json", "--sem-atualizar"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["manifesto"] == {"presente": False, "caminho": None}


def test_json_manifesto_declarado_mas_arquivo_sumiu(raiz, bin_stub, tmp_path):
    """Declarado (caminho não é null) mas ausente em disco (presente:false) —
    as duas informações não colapsam numa só, senão "sumiu" e "nunca
    declarou" ficariam indistinguíveis."""
    _escreve(
        raiz,
        "platafirma-harness/personas/persona-manifestosumido.md",
        "Você é ManifestoSumido, aponta pra manifesto que não existe.\n\n"
        "FERRAMENTAL: platafirma-harness/tool-manifest/nao-existe.md\n",
    )
    proc = _run(
        ["manifestosumido", "--json", "--sem-atualizar"], raiz, bin_stub, tmp_path
    )
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["manifesto"]["presente"] is False
    assert dados["manifesto"]["caminho"] == "platafirma-harness/tool-manifest/nao-existe.md"


def test_json_mesa_indisponivel_nao_derruba_o_resto(raiz, bin_stub, tmp_path):
    """mesa fora do ar (msg-mem indisponível): disponivel:false, mas o resto
    do objeto (persona/manifesto/org/fila) continua saindo — indisponível
    parcial nunca vira falha do verbo inteiro nem stdout vazio."""
    proc = _run(
        ["teste", "--json", "--sem-atualizar"],
        raiz,
        bin_stub,
        tmp_path,
        mesa_modo="falha",
    )
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["mesa"]["disponivel"] is False
    assert dados["persona"]["presente"] is True
    assert dados["fila"]["disponivel"] is True


def test_json_cadernos_indisponivel_nao_derruba_o_resto(raiz, bin_stub, tmp_path):
    """`mesa caderno` fora do ar: disponivel:false, motivo curto em resumo, e
    o resto do objeto (persona/manifesto/org/mesa/fila) continua saindo —
    mesma régua de indisponibilidade parcial que já vale pra mesa/fila."""
    proc = _run(
        ["teste", "--json", "--sem-atualizar"],
        raiz,
        bin_stub,
        tmp_path,
        caderno_modo="falha",
    )
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["cadernos"]["disponivel"] is False
    assert dados["cadernos"]["resumo"] is not None
    assert dados["mesa"]["disponivel"] is True
    assert dados["persona"]["presente"] is True


def test_json_fila_fechada_vira_disponivel_false_com_motivo(raiz, bin_stub, tmp_path):
    proc = _run(
        ["teste", "--json", "--sem-atualizar"],
        raiz,
        bin_stub,
        tmp_path,
        fila_modo="fechada",
    )
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert dados["fila"]["disponivel"] is False
    assert dados["fila"]["resumo"] is not None


# --- falha -------------------------------------------------------------


def test_json_cadeira_desconhecida_vira_objeto_de_erro(raiz, bin_stub, tmp_path):
    """Regra dura: nunca stdout vazio em falha. Exit 1 preservado (o mesmo
    que o modo texto já usava)."""
    proc = _run(["fantasma", "--json"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 1
    assert proc.stdout.count("\n") == 1
    dados = json.loads(proc.stdout)
    assert dados.get("erro")
    assert dados["cadeiras_validas"] == ["teste"]


def test_json_sem_cadeira_vira_objeto_de_erro_exit_2(raiz, bin_stub, tmp_path):
    """Uso incorreto (sem argumento nenhum): exit 2 preservado, mesma régua
    de erro-nunca-vazio."""
    proc = _run(["--json"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 2
    dados = json.loads(proc.stdout)
    assert dados.get("erro")
    assert dados["cadeiras_validas"] == ["teste"]


def test_sem_json_cadeira_desconhecida_mantem_texto_e_exit_1(raiz, bin_stub, tmp_path):
    """Mesma falha, sem --json: confirma que o padrão de texto (stderr com a
    lista de cadeiras válidas, stdout vazio) não mudou."""
    proc = _run(["fantasma"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "não existe" in proc.stderr
    assert "teste" in proc.stderr


# --- regressão do texto sem --json -----------------------------------------


def test_sem_json_mantem_saida_de_texto_atual(raiz, bin_stub, tmp_path):
    """Regra dura: saída sem --json não muda uma linha. Confere os
    marcadores "===== <arquivo> =====" e os blocos de mesa/fila que já
    existiam antes desta mudança."""
    proc = _run(["teste"], raiz, bin_stub, tmp_path)
    assert proc.returncode == 0
    linhas = proc.stdout.splitlines()
    assert linhas[0] == "== cadeira: ClaudinhoTeste =="
    assert "===== platafirma-harness/personas/persona-teste.md =====" in linhas
    assert f"===== {MANIFESTO_REL} =====" in linhas
    assert f"===== {ORG_REL} =====" in linhas
    assert "===== mesa: teste =====" in linhas
    assert "===== fila: ClaudinhoTeste =====" in linhas
    # nada de objeto JSON escapado por engano no texto solto
    assert "{" not in proc.stdout
