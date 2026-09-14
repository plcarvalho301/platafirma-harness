"""Suíte de testes herméticos para `bin/expediente` (spec_expediente §1-§7, #3053).

Cobre um caso por ato e por etapa do §4:
- uso: ato ausente / ato desconhecido / flags de ajuda -> 2
- sem PF_CADEIRA -> 3 ("sem cadeira: a porta não injetou")
- slug com prefixo (claudinho-/claudinha-) ou caracteres inválidos -> 3
- catálogo ausente -> 3
- peça falha -> 0 com frescor indisponivel + motivo
- roteador ausente -> 0 com via fallback declarado e slug null
- --chapeu inválido -> 2 listando os válidos
- registro sem senha -> 0 com registrado: false
- ordem de injeção -> cadernos SEMPRE por último
- --sem-acervo -> omite a peça e não chama motor
- catalogo lista as 7 peças declaradas
- formato --json -> objeto no topo
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin" / "expediente"

PERSONA_STUB = """#!/bin/sh
sub="${1:-}"
case "$sub" in
  conduta)
    case "${STUB_PERSONA_CONDUTA:-ok}" in
      ok) printf "# conduta do dono (stub)\\n" ;;
      falha) echo "persona conduta: falha simulada no stub" >&2; exit 1 ;;
    esac
    ;;
  foto)
    case "${STUB_PERSONA_FOTO:-ok}" in
      ok) printf "ia (Elias Elefante) · ativa\\nfabrica (Fábrica) · ativa\\n" ;;
      falha) echo "persona foto: falha simulada no stub" >&2; exit 1 ;;
    esac
    ;;
  ler)
    cad="${2:-}"
    chapeu=""
    if [ "${3:-}" = "--chapeu" ]; then
      chapeu="${4:-}"
    fi
    if [ -n "$chapeu" ]; then
      if [ "$chapeu" = "invalido" ] || [ "$chapeu" = "chapeu_invalido" ]; then
        echo "nao-existe: chapeu $chapeu em $cad — validos: contexto diretriz" >&2
        exit 1
      fi
      printf "# chapeu %s em %s (stub)\\n" "$chapeu" "$cad"
    else
      case "${STUB_PERSONA_LER:-ok}" in
        ok) printf "# persona %s (stub)\\n" "$cad" ;;
        falha) echo "persona ler: falha simulada no stub" >&2; exit 1 ;;
      esac
    fi
    ;;
  *)
    echo "stub persona: comando desconhecido '$sub'" >&2
    exit 2
    ;;
esac
"""

MESA_STUB = """#!/bin/sh
sub="${1:-}"
case "$sub" in
  ver)
    case "${STUB_MESA_VER:-ok}" in
      ok) printf "# mesa ver (stub)\\n" ;;
      falha) echo "mesa ver: msg-mem fora do ar (stub)" >&2; exit 1 ;;
    esac
    ;;
  caderno)
    case "${STUB_MESA_CADERNO:-ok}" in
      ok) printf "caderno %s (stub)\\n" "${2:-<indice>}" ;;
      falha) echo "mesa caderno: fora do ar (stub)" >&2; exit 1 ;;
    esac
    ;;
  *)
    echo "stub mesa: subcomando desconhecido '$sub'" >&2
    exit 2
    ;;
esac
"""

MOTOR_STUB = """#!/bin/sh
if [ -n "${STUB_MOTOR_LOG:-}" ]; then
  echo "$@" >> "$STUB_MOTOR_LOG"
fi
case "${STUB_MOTOR_MODO:-ok}" in
  ok)
    echo '{"fontes": [{"n": 1, "obra": "casa/doc.md", "section_id": "s1"}], "cobertura": "alta", "contexto": "trecho do acervo consultado (stub)", "sinal": {"valor": 0.8, "piso": 0.5}}'
    ;;
  falha)
    echo "motor rag buscar: conexao recusada (stub)" >&2
    exit 1
    ;;
esac
"""

ROTEADOR_STUB = """#!/bin/sh
pergunta="$(cat)"
case "$pergunta" in
  *"janela"*|*"contexto"*|*"tokens"*)
    echo '{"via": "deterministico", "slug": "contexto", "acertos": {"contexto": 1}, "motivo": null}'
    ;;
  *"diretriz"*)
    echo '{"via": "deterministico", "slug": "diretriz", "acertos": {"diretriz": 1}, "motivo": null}'
    ;;
  *"mudo"*)
    echo "conceitos do golden record mudos" >&2
    exit 3
    ;;
  *)
    echo '{"via": "fallback", "slug": null, "acertos": {}, "motivo": "nenhum rotulo canonico casou na pergunta"}'
    ;;
esac
"""


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


@pytest.fixture()
def raiz_hermetica(tmp_path: Path) -> Path:
    """Cria árvore hermética com stubs executáveis em bin/ e bin/_expediente/roteador."""
    raiz = tmp_path / "raiz"
    bin_dir = raiz / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    p_persona = bin_dir / "persona"
    p_persona.write_text(PERSONA_STUB, encoding="utf-8")
    _executavel(p_persona)

    p_mesa = bin_dir / "mesa"
    p_mesa.write_text(MESA_STUB, encoding="utf-8")
    _executavel(p_mesa)

    p_motor = bin_dir / "motor"
    p_motor.write_text(MOTOR_STUB, encoding="utf-8")
    _executavel(p_motor)

    # Sub-ato roteador
    exp_dir = bin_dir / "_expediente"
    exp_dir.mkdir(parents=True, exist_ok=True)
    p_rot = exp_dir / "roteador"
    p_rot.write_text(ROTEADOR_STUB, encoding="utf-8")
    _executavel(p_rot)

    return raiz


def _run_expediente(args: list[str], raiz: Path, *, stdin_data: str = "",
                    env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PF_RAIZ"] = str(raiz)
    env["PATH"] = f"{raiz / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(
        cmd,
        input=stdin_data,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


# ------------------------------------------------------------------------------
# Etapa 1: Uso
# ------------------------------------------------------------------------------

def test_uso_sem_ato_exit_2(raiz_hermetica):
    """Etapa 1: sem ato -> exit 2 em stderr."""
    proc = _run_expediente([], raiz_hermetica)
    assert proc.returncode == 2
    assert "uso:" in proc.stderr or "erro:" in proc.stderr


def test_uso_ato_desconhecido_exit_2(raiz_hermetica):
    """Etapa 1: ato desconhecido -> exit 2."""
    proc = _run_expediente(["desconhecido"], raiz_hermetica)
    assert proc.returncode == 2
    assert "desconhecido" in proc.stderr

    proc_json = _run_expediente(["desconhecido", "--json"], raiz_hermetica)
    assert proc_json.returncode == 2
    d = json.loads(proc_json.stdout)
    assert "desconhecido" in d["erro"]


# ------------------------------------------------------------------------------
# Etapa 2: Identidade / PF_CADEIRA
# ------------------------------------------------------------------------------

def test_sem_pf_cadeira_exit_3(raiz_hermetica):
    """Etapa 2: PF_CADEIRA ausente -> exit 3 'sem cadeira: a porta não injetou'."""
    proc = _run_expediente(["montar"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc.returncode == 3
    assert "sem cadeira: a porta não injetou" in proc.stderr

    proc_json = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc_json.returncode == 3
    d = json.loads(proc_json.stdout)
    assert "sem cadeira: a porta não injetou" in d["erro"]

    proc_rot = _run_expediente(["rotear"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc_rot.returncode == 3
    assert "sem cadeira: a porta não injetou" in proc_rot.stderr


def test_slug_com_prefixo_exit_3(raiz_hermetica):
    """Etapa 2: PF_CADEIRA com prefixo claudinho-/claudinha- ou não slug puro -> exit 3."""
    for cad_invalida in ("claudinho-ia", "claudinha-fabrica", "ia com espaco", "ia/chapeu"):
        proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": cad_invalida})
        assert proc.returncode == 3
        d = json.loads(proc_json := proc.stdout)
        assert "sem cadeira: a porta não injetou" in d["erro"]


# ------------------------------------------------------------------------------
# Etapa 1b: Chapéu fora do vocabulário
# ------------------------------------------------------------------------------

def test_chapeu_fora_do_vocabulario_exit_2(raiz_hermetica):
    """Etapa 1: --chapeu fora do vocabulário -> exit 2 listando os válidos."""
    proc = _run_expediente(
        ["montar", "--chapeu", "invalido"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc.returncode == 2
    assert "fora do vocabulário da cadeira 'ia'" in proc.stderr
    assert "contexto" in proc.stderr
    assert "diretriz" in proc.stderr

    proc_json = _run_expediente(
        ["montar", "--chapeu", "invalido", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_json.returncode == 2
    d = json.loads(proc_json.stdout)
    assert "fora do vocabulário da cadeira 'ia'" in d["erro"]


# ------------------------------------------------------------------------------
# Etapa 3: Catálogo
# ------------------------------------------------------------------------------

def test_catalogo_ausente_exit_3(raiz_hermetica):
    """Etapa 3: catálogo ausente -> exit 3."""
    env = {"PF_CADEIRA": "ia", "PF_CATALOGO_AUSENTE": "1"}

    proc_c = _run_expediente(["catalogo"], raiz_hermetica, env_extra=env)
    assert proc_c.returncode == 3
    assert "catálogo: ausente" in proc_c.stderr

    proc_cj = _run_expediente(["catalogo", "--json"], raiz_hermetica, env_extra=env)
    assert proc_cj.returncode == 3
    d = json.loads(proc_cj.stdout)
    assert "catálogo: ausente" in d["erro"]

    proc_m = _run_expediente(["montar"], raiz_hermetica, env_extra=env)
    assert proc_m.returncode == 3
    assert "catálogo: ausente" in proc_m.stderr


def test_catalogo_lista_as_7(raiz_hermetica):
    """Spec §7: catalogo lista as 7 peças com campos conformes."""
    proc = _run_expediente(["catalogo", "--json"], raiz_hermetica)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert isinstance(dados, list)
    assert len(dados) == 7

    pecas_esperadas = [
        "conduta",
        "persona",
        "alias-cadeiras",
        "mesa",
        "acervo-consultado",
        "chapeu",
        "cadernos",
    ]
    pecas_obtidas = [p["peca"] for p in dados]
    assert pecas_obtidas == pecas_esperadas

    # Confere donos
    donos = {p["peca"]: p["dono"] for p in dados}
    assert donos["acervo-consultado"] == "dados"
    assert donos["conduta"] == "gestao-estrategica"
    assert donos["mesa"] == "gestao-estrategica"


# ------------------------------------------------------------------------------
# Etapa 4: Peça falha
# ------------------------------------------------------------------------------

def test_peca_falha_exit_0_com_indisponivel(raiz_hermetica):
    """Etapa 4: peça falha -> exit 0, frescor indisponivel + motivo no aviso."""
    env = {
        "PF_CADEIRA": "ia",
        "STUB_MESA_VER": "falha",
        "STUB_PERSONA_CONDUTA": "falha",
    }
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra=env)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)

    por_peca = {p["peca"]: p for p in dados["pecas"]}
    assert por_peca["conduta"]["frescor"] == "indisponivel"
    assert "falha simulada" in por_peca["conduta"]["motivo"]
    assert por_peca["conduta"]["conteudo"] is None
    assert por_peca["conduta"]["tokens"] == 0

    assert por_peca["mesa"]["frescor"] == "indisponivel"
    assert "msg-mem fora do ar" in por_peca["mesa"]["motivo"]

    # Peça sã sai fresca
    assert por_peca["persona"]["frescor"] == "fresco"
    assert por_peca["persona"]["conteudo"] == "# persona ia (stub)"

    # Avisos declaram as indisponibilidades
    assert any("conduta" in a and "indisponível" in a for a in dados["avisos"])
    assert any("mesa" in a and "indisponível" in a for a in dados["avisos"])


# ------------------------------------------------------------------------------
# Etapa 5: Roteador
# ------------------------------------------------------------------------------

def test_rotear_via_deterministico(raiz_hermetica):
    """Etapa 5: roteador com casamento via determinístico."""
    proc = _run_expediente(
        ["rotear", "--json"],
        raiz_hermetica,
        stdin_data="orçamento de tokens e contexto",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["slug"] == "contexto"
    assert d["via"] == "determinístico"


def test_rotear_fallback_exit_0_e_slug_null(raiz_hermetica):
    """Etapa 5: roteador fallback -> exit 0 e slug null."""
    proc = _run_expediente(
        ["rotear", "--json"],
        raiz_hermetica,
        stdin_data="pergunta genérica sem rótulos",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["slug"] is None
    assert d["via"] == "fallback"


def test_roteador_ausente_fallback_declarado(raiz_hermetica):
    """Etapa 5: roteador ausente -> exit 0, via fallback e slug null com aviso."""
    p_rot = raiz_hermetica / "bin" / "_expediente" / "roteador"
    if p_rot.exists():
        p_rot.unlink()

    proc = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="pergunta qualquer",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] is None
    assert d["roteador"]["via"] == "fallback"
    assert d["roteador"]["slug"] is None
    assert any("roteador ausente" in a for a in d["avisos"])


# ------------------------------------------------------------------------------
# Etapa 6: Registro
# ------------------------------------------------------------------------------

def test_registro_sem_senha_registrado_false(raiz_hermetica):
    """Etapa 6: registro sem senha -> exit 0, registrado: false com motivo."""
    env = {
        "PF_CADEIRA": "ia",
        "PF_FITA": "fita-teste-123",
        "SESSAO_PG_PASSWORD": "",
    }
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra=env)
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    reg = d["pacote"]["registro"]
    assert reg["registrado"] is False
    assert "sem senha" in reg["motivo"]


# ------------------------------------------------------------------------------
# Regras de montagem e modificadores
# ------------------------------------------------------------------------------

def test_sem_acervo_omite_peca(raiz_hermetica):
    """--sem-acervo não chama motor e não inclui acervo-consultado."""
    log_motor = raiz_hermetica / "motor.log"
    env = {
        "PF_CADEIRA": "ia",
        "STUB_MOTOR_LOG": str(log_motor),
    }
    proc = _run_expediente(
        ["montar", "--sem-acervo", "--json"],
        raiz_hermetica,
        stdin_data="pergunta com busca",
        env_extra=env,
    )
    assert proc.returncode == 0
    assert not log_motor.exists()
    d = json.loads(proc.stdout)
    pecas = [p["peca"] for p in d["pecas"]]
    assert "acervo-consultado" not in pecas


def test_ordem_injecao_cadernos_ultimo(raiz_hermetica):
    """Cadernos é a ÚLTIMA peça injetada, sempre."""
    # Sem pergunta
    proc1 = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc1.returncode == 0
    d1 = json.loads(proc1.stdout)
    assert d1["pecas"][-1]["peca"] == "cadernos"

    # Com pergunta (acervo entra antes dos cadernos)
    proc2 = _run_expediente(["montar", "--json"], raiz_hermetica, stdin_data="busca", env_extra={"PF_CADEIRA": "ia"})
    assert proc2.returncode == 0
    d2 = json.loads(proc2.stdout)
    assert d2["pecas"][-1]["peca"] == "cadernos"

    # Com chapéu forçado
    proc3 = _run_expediente(["montar", "--chapeu", "contexto", "--json"], raiz_hermetica, stdin_data="busca", env_extra={"PF_CADEIRA": "ia"})
    assert proc3.returncode == 0
    d3 = json.loads(proc3.stdout)
    assert d3["pecas"][-1]["peca"] == "cadernos"


def test_formato_json_e_objeto(raiz_hermetica):
    """--json devolve objeto no topo."""
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert isinstance(d, dict)
    assert "cadeira" in d
    assert "sessao_id" in d
    assert "ordem_id" in d
    assert "pacote" in d
    assert "pecas" in d
    assert "avisos" in d
