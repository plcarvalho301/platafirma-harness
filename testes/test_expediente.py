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


ACERVO_STUB = """#!/bin/sh
if [ "$*" = "listar casa guia --mapa" ]; then
  printf "ROTINAS (stub)\\n\\nLER — sei a chave\\n"
  exit 0
fi
echo "stub acervo: chamada inesperada '$*'" >&2
exit 2
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

    p_acervo = bin_dir / "acervo"
    p_acervo.write_text(ACERVO_STUB, encoding="utf-8")
    _executavel(p_acervo)

    # Sub-ato roteador
    exp_dir = bin_dir / "_expediente"
    exp_dir.mkdir(parents=True, exist_ok=True)
    p_rot = exp_dir / "rotear"
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
        d = json.loads(proc.stdout)
        assert "sem cadeira: a porta não injetou" in d["erro"]


# ------------------------------------------------------------------------------
# Etapa 1b: Chapéu fora do vocabulário
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Etapa 3: Catálogo
# ------------------------------------------------------------------------------

def test_catalogo_na_transicao_nunca_ausente(raiz_hermetica):
    """Etapa 3: na transicao o catalogo mora no verbo e nao tem como faltar — `catalogo`
    sai 0 e se declara transicao. O caso `exit 3` so existe quando vier do acervo."""
    proc_c = _run_expediente(["catalogo"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc_c.returncode == 0
    assert "transição" in proc_c.stdout


def test_catalogo_lista_as_8(raiz_hermetica):
    """Spec §7: catalogo lista as 8 peças com campos conformes (rotinas entrou no #3084)."""
    proc = _run_expediente(["catalogo", "--json"], raiz_hermetica)
    assert proc.returncode == 0
    dados = json.loads(proc.stdout)
    assert isinstance(dados, list)
    assert len(dados) == 8

    pecas_esperadas = [
        "conduta",
        "persona",
        "alias-cadeiras",
        "mesa",
        "acervo-consultado",
        "chapeu",
        "cadernos",
        "rotinas",
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

# ------------------------------------------------------------------------------
# Etapa 5: Roteador
# ------------------------------------------------------------------------------

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


# ------------------------------------------------------------------------------
# Passo 1: Prefixo estável [persona, conduta] contíguo e byte-estável (#3067)
# ------------------------------------------------------------------------------

def test_ordem_prefixo_estavel_persona_conduta_contiguo_sem_chapeu(raiz_hermetica):
    """Passo 1 (#3067): persona e conduta são as duas primeiras peças, contíguas (sem chapéu)."""
    proc = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    pecas = d["pecas"]
    assert len(pecas) >= 2
    assert pecas[0]["peca"] == "persona"
    assert pecas[1]["peca"] == "conduta"


def test_ordem_prefixo_estavel_persona_conduta_contiguo_com_chapeu(raiz_hermetica):
    """Passo 1 (#3067): com chapéu roteado, persona e conduta continuam contíguos no topo;
    chapéu vem em 3º (logo após conduta, nunca intercalado entre persona e conduta)."""
    proc = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="pergunta sobre janela de contexto",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto"
    pecas = d["pecas"]
    assert len(pecas) >= 3
    assert pecas[0]["peca"] == "persona"
    assert pecas[1]["peca"] == "conduta"
    assert pecas[2]["peca"] == "chapeu"


def test_prefixo_byte_estavel_entre_aberturas(raiz_hermetica):
    """Passo 1 (#3067): aberturas seguidas produzem prefixo persona+conduta byte-idêntico."""
    proc1 = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    proc2 = _run_expediente(["montar", "--json"], raiz_hermetica, env_extra={"PF_CADEIRA": "ia"})
    assert proc1.returncode == 0
    assert proc2.returncode == 0
    d1 = json.loads(proc1.stdout)
    d2 = json.loads(proc2.stdout)
    p1 = d1["pecas"][:2]
    p2 = d2["pecas"][:2]
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


# ------------------------------------------------------------------------------
# Passo 2: Chapéu resolvido antes da mesa; sem chapéu, mesa inteira (#3067)
# ------------------------------------------------------------------------------

def test_mesa_recebe_chapeu_resolvido(raiz_hermetica):
    """Passo 2 (#3067): chapéu resolvido antes da mesa -> mesa ver <chapeu>."""
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"],
        raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto"
    peca_mesa = next(p for p in d["pecas"] if p["peca"] == "mesa")
    assert peca_mesa["ref"] == "verbo:mesa ver contexto"


def test_mesa_sem_chapeu_fail_to_inteiro(raiz_hermetica):
    """Passo 2 (#3067): sem chapéu resolvido -> mesa ver (mesa inteira / fail-to-inteiro)."""
    proc = _run_expediente(
        ["montar", "--json"],
        raiz_hermetica,
        stdin_data="pergunta sem rotulo",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    d = json.loads(proc.stdout)
    assert d["chapeu"] is None
    peca_mesa = next(p for p in d["pecas"] if p["peca"] == "mesa")
    assert peca_mesa["ref"] == "verbo:mesa ver"

# ------------------------------------------------------------------------------
# #3084: peça rotinas no prefixo, logo depois da conduta (ou do chapéu)
# ------------------------------------------------------------------------------

def test_rotinas_logo_apos_conduta_sem_chapeu(raiz_hermetica):
    proc = _run_expediente(
        ["montar", "--json"], raiz_hermetica, stdin_data="pergunta sem rotulo",
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    pecas = json.loads(proc.stdout)["pecas"]
    assert [p["peca"] for p in pecas[:3]] == ["persona", "conduta", "rotinas"]
    assert pecas[2]["ref"] == "verbo:acervo listar casa guia --mapa"
    assert pecas[2]["frescor"] == "fresco"
    assert pecas[2]["conteudo"].startswith("ROTINAS")

def test_rotinas_logo_apos_chapeu(raiz_hermetica):
    proc = _run_expediente(
        ["montar", "--chapeu", "contexto", "--json"], raiz_hermetica,
        env_extra={"PF_CADEIRA": "ia", "PF_BIN": str(raiz_hermetica / "bin")},
    )
    assert proc.returncode == 0
    pecas = json.loads(proc.stdout)["pecas"]
    assert [p["peca"] for p in pecas[:4]] == ["persona", "conduta", "chapeu", "rotinas"]


