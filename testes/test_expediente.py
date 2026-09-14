"""Suíte de testes para `bin/expediente` (spec_expediente §1, §2, §3, §4, §5, §7, #3053).

Cobre um caso por ato e por etapa do §4:
- sem PF_CADEIRA → 3
- ato inválido → 2 uma vez
- --chapeu fora do vocabulário → 2 com a lista
- catálogo ausente → 3
- peça que falha → 0 com indisponivel
- rotear fallback → 0 e slug null
- --sem-acervo não chama motor
- cadernos é a ÚLTIMA peça
- --json é objeto.
Hermetismo: PF_RAIZ temporário com stubs executáveis de persona/mesa/motor em <raiz>/bin.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

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


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


@pytest.fixture()
def raiz_hermetica(tmp_path: Path) -> Path:
    """Cria árvore hermética com stubs executáveis em bin/ e rotas de chapéu."""
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

    # Cria rotas-chapeu na morada hermética
    abertura_dir = raiz / "var" / "abertura-publicada" / "current" / "abertura"
    abertura_dir.mkdir(parents=True, exist_ok=True)
    rotas_data = {
        "ia": {
            "contexto": ["janela de contexto", "orcamento de tokens"],
            "diretriz": ["diretriz estrategica"],
        }
    }
    (abertura_dir / "rotas-chapeu.json").write_text(
        json.dumps(rotas_data, ensure_ascii=False), encoding="utf-8"
    )
    # Cria os diretórios dos chapéus para rotas_do_disco
    (abertura_dir / "ia" / "contexto").mkdir(parents=True, exist_ok=True)
    (abertura_dir / "ia" / "diretriz").mkdir(parents=True, exist_ok=True)

    return raiz


def _run_expediente(args: list[str], raiz: Path, *, stdin_data: str = "",
                    env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PF_RAIZ"] = str(raiz)
    env["PATH"] = f"{raiz / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    env["PF_ABERTURA_DIR"] = str(raiz / "var" / "abertura-publicada")
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
# Casos do contrato (§4 e regras duras)
# ------------------------------------------------------------------------------

def test_sem_pf_cadeira_exit_3(raiz_hermetica):
    """Etapa 2: sem PF_CADEIRA -> exit 3 'sem cadeira: a porta não injetou'."""
    # montar sem PF_CADEIRA
    proc = _run_expediente(["montar"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc.returncode == 3
    assert "sem cadeira: a porta não injetou" in proc.stderr

    # montar com --json
    proc_json = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc_json.returncode == 3
    dados = json.loads(proc_json.stdout)
    assert "sem cadeira: a porta não injetou" in dados["erro"]

    # rotear sem PF_CADEIRA
    proc_rot = _run_expediente(["rotear"], raiz_hermetica, env_extra={"PF_CADEIRA": ""})
    assert proc_rot.returncode == 3
    assert "sem cadeira: a porta não injetou" in proc_rot.stderr


def test_ato_invalido_exit_2_uma_vez(raiz_hermetica):
    """Etapa 1: ato inválido ou ausente -> exit 2 uma vez."""
    # sem ato
    proc = _run_expediente([], raiz_hermetica)
    assert proc.returncode == 2
    assert "uso:" in proc.stderr
    assert "montar" in proc.stderr
    assert "rotear" in proc.stderr
    assert "catalogo" in proc.stderr

    # ato desconhecido
    proc_invalido = _run_expediente(["desconhecido"], raiz_hermetica)
    assert proc_invalido.returncode == 2
    assert "ato desconhecido: 'desconhecido'" in proc_invalido.stderr

    # com --json
    proc_invalido_json = _run_expediente(["desconhecido", "--json"], raiz_hermetica)
    assert proc_invalido_json.returncode == 2
    dados = json.loads(proc_invalido_json.stdout)
    assert "desconhecido" in dados["erro"]


def test_chapeu_fora_do_vocabulario_exit_2_com_lista(raiz_hermetica):
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

    # com --json
    proc_json = _run_expediente(
        ["montar", "--chapeu", "invalido", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_json.returncode == 2
    dados = json.loads(proc_json.stdout)
    assert "fora do vocabulário da cadeira 'ia'" in dados["erro"]


def test_catalogo_ausente_exit_3(raiz_hermetica):
    """Etapa 3: catálogo ausente -> exit 3 'catálogo: ausente'."""
    env_cat = {"PF_CADEIRA": "ia", "PF_CATALOGO_AUSENTE": "1"}

    # catalogo
    proc_cat = _run_expediente(["catalogo"], raiz_hermetica, env_extra=env_cat)
    assert proc_cat.returncode == 3
    assert "catálogo: ausente" in proc_cat.stderr

    # catalogo com --json
    proc_cat_json = _run_expediente(["catalogo", "--json"], raiz_hermetica, env_extra=env_cat)
    assert proc_cat_json.returncode == 3
    dados = json.loads(proc_cat_json.stdout)
    assert "catálogo: ausente" in dados["erro"]

    # montar
    proc_montar = _run_expediente(["montar"], raiz_hermetica, env_extra=env_cat)
    assert proc_montar.returncode == 3
    assert "catálogo: ausente" in proc_montar.stderr


def test_peca_que_falha_exit_0_com_indisponivel(raiz_hermetica):
    """Etapa 4: verbo que falha -> frescor: indisponivel + motivo, exit 0."""
    env_falha = {
        "PF_CADEIRA": "ia",
        "STUB_MESA_VER": "falha",
        "STUB_PERSONA_CONDUTA": "falha",
    }
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra=env_falha)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)

    por_peca = {p["peca"]: p for p in dados["pecas"]}
    assert por_peca["conduta"]["frescor"] == "indisponivel"
    assert "falha simulada" in por_peca["conduta"]["motivo"]
    assert por_peca["conduta"]["conteudo"] is None
    assert por_peca["conduta"]["tokens"] == 0

    assert por_peca["mesa"]["frescor"] == "indisponivel"
    assert "msg-mem fora do ar" in por_peca["mesa"]["motivo"]

    # Peça funcional sai fresca
    assert por_peca["persona"]["frescor"] == "fresco"
    assert por_peca["persona"]["conteudo"] == "# persona ia (stub)"

    # Avisos declaram as indisponibilidades
    assert any("conduta" in a and "indisponível" in a for a in dados["avisos"])
    assert any("mesa" in a and "indisponível" in a for a in dados["avisos"])


def test_rotear_fallback_exit_0_e_slug_null(raiz_hermetica):
    """Etapa 5: roteador fallback -> exit 0 e slug null."""
    # ato rotear
    proc_rot = _run_expediente(
        ["rotear", "--json"],
        raiz_hermetica,
        stdin_data="pergunta generica sem rotulos",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_rot.returncode == 0
    d_rot = json.loads(proc_rot.stdout)
    assert d_rot["slug"] is None
    assert d_rot["via"] == "fallback"

    # ato montar com fallback
    proc_montar = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="pergunta generica sem rotulos",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_montar.returncode == 0
    d_montar = json.loads(proc_montar.stdout)
    assert d_montar["chapeu"] is None
    assert d_montar["roteador"]["via"] == "fallback"
    assert d_montar["roteador"]["slug"] is None
    assert any("chapéu não roteado (fallback)" in a for a in d_montar["avisos"])


def test_sem_acervo_nao_chama_motor(raiz_hermetica):
    """Regra 9: --sem-acervo não chama o motor."""
    log_motor = raiz_hermetica / "motor.log"
    env = {
        "PF_CADEIRA": "ia",
        "STUB_MOTOR_LOG": str(log_motor),
    }
    proc = _run_expediente(
        ["montar", "--sem-acervo", "--json"],
        raiz_hermetica,
        stdin_data="preciso de informacao",
        env_extra=env,
    )
    assert proc.returncode == 0
    assert not log_motor.exists()
    dados = json.loads(proc.stdout)
    pecas_ids = [p["peca"] for p in dados["pecas"]]
    assert "acervo-consultado" not in pecas_ids


def test_cadernos_e_a_ultima_peca(raiz_hermetica):
    """Regra 5: cadernos é a ÚLTIMA peça injetada, sempre."""
    # Caso 1: sem pergunta
    proc1 = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc1.returncode == 0
    d1 = json.loads(proc1.stdout)
    assert d1["pecas"][-1]["peca"] == "cadernos"

    # Caso 2: com pergunta e acervo
    proc2 = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="consulta acervo",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc2.returncode == 0
    d2 = json.loads(proc2.stdout)
    assert d2["pecas"][-1]["peca"] == "cadernos"

    # Caso 3: com chapéu forçado
    proc3 = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"],
        raiz_hermetica,
        stdin_data="consulta acervo",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc3.returncode == 0
    d3 = json.loads(proc3.stdout)
    assert d3["pecas"][-1]["peca"] == "cadernos"


def test_json_e_objeto(raiz_hermetica):
    """Regra 12: --json devolve objeto no topo."""
    # montar
    proc_m = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_m.returncode == 0
    dados_m = json.loads(proc_m.stdout)
    assert isinstance(dados_m, dict)
    assert "cadeira" in dados_m
    assert "pacote" in dados_m
    assert "pecas" in dados_m

    # rotear
    proc_r = _run_expediente(
        ["rotear", "--json"],
        raiz_hermetica,
        stdin_data="orcamento de tokens",
        env_extra={"PF_CADEIRA": "ia"},
    )
    assert proc_r.returncode == 0
    dados_r = json.loads(proc_r.stdout)
    assert isinstance(dados_r, dict)
    assert dados_r["slug"] == "contexto"

    # catalogo
    proc_c = _run_expediente(["catalogo", "--json"], raiz_hermetica)
    assert proc_c.returncode == 0
    dados_c = json.loads(proc_c.stdout)
    assert isinstance(dados_c, list)
    assert len(dados_c) == 7
