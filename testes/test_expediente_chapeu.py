# componente: componente:verbo-expediente
"""`expediente montar --chapeu <pedaco>`: o dono nao decora slug.

O que se trava: o nome exato passa calado; um pedaco que casa com um chapeu so da cadeira vira
o slug inteiro, com aviso; pedaco ambiguo sai 2 com as opcoes; o que nao casa segue para a
validacao de sempre. Vale nos dois perfis.
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

_CAMINHOS_PY = [
    REPO_ROOT / "lib",
    Path("/opt/platafirma/current/harness/lib"),
]
_pypath_partes = [str(p) for p in _CAMINHOS_PY if p.exists()]
if os.environ.get("PYTHONPATH"):
    _pypath_partes.append(os.environ["PYTHONPATH"])
os.environ["PYTHONPATH"] = os.pathsep.join(_pypath_partes)

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
if [ "$*" = "listar casa guia --mapa" ]; then echo "ROTINAS (stub)"; exit 0; fi
if [ "$*" = "listar casa modo --json" ]; then
  echo '[{"chave":"varrer"},{"chave":"revisar"},{"chave":"avaliar"},{"chave":"testar"},{"chave":"executar"},{"chave":"consultar"},{"chave":"parecer"},{"chave":"pesquisar"}]'
  exit 0
fi
if [ "$1 $2 $3" = "ler casa modo" ]; then
  if [ "${STUB_ACERVO_MODO:-ok}" = "falha" ]; then echo "acervo: fora do ar (stub)" >&2; exit 3; fi
  if [ "$4" = "revisar" ]; then echo "# modo revisar (stub)"; echo "O que faz: revisa."; exit 0; fi
  echo "nao-existe: modo $4 (stub)" >&2; exit 1
fi
if [ "$1 $2 $3" = "ler casa lista-de-verificacao" ]; then
  if [ "$4" = "ilegivel" ]; then echo "nao-existe: $4 (stub)" >&2; exit 1; fi
  cat <<'EOF'
# lista de verificacao (stub)
## Como se lê
regra geral que nao entra
## Critérios
| id | criterio |
| A1 | README existe |
### subtitulo dentro de Critérios
| A2 | README cabe em 100 linhas |
## Contrapontos
**A1** — pasta sem manifesto nao leva README
## Curas
cura que nao entra
## Rodapé
nota que nao entra
EOF
  exit 0
fi
if [ "$1 $2 $3" = "ler casa padrao" ]; then echo "# padrao inteiro (stub)"; echo "## Qualquer"; echo "corpo do padrao"; exit 0; fi
echo "stub acervo: chamada inesperada '$*'" >&2
exit 2
"""

MOTOR_ARGS_STUB = """#!/bin/sh
for a in "$@"; do echo "$a" >> "$STUB_MOTOR_LOG"; done
echo '{"fontes": [{"n": 1, "obra": "casa/doc.md", "section_id": "s1"}], "cobertura": "alta", "contexto": "trecho (stub)", "sinal": {"valor": 0.8, "piso": 0.5}}'
"""

CHAPEUS = ("agente", "contexto", "engenharia-de-harness")


def _executavel(caminho: Path) -> Path:
    caminho.chmod(caminho.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


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


@pytest.fixture()
def raiz(tmp_path: Path) -> Path:
    r = tmp_path / "raiz"
    bin_dir = r / "bin"
    (bin_dir / "_expediente").mkdir(parents=True)
    for caminho, texto in ((bin_dir / "persona", PERSONA_STUB), (bin_dir / "mesa", MESA_STUB),
                           (bin_dir / "acervo", ACERVO_STUB), (bin_dir / "motor", MOTOR_ARGS_STUB),
                           (bin_dir / "_expediente" / "rotear", ROTEADOR_STUB)):
        caminho.write_text(texto, encoding="utf-8")
        _executavel(caminho)
    return r


@pytest.fixture()
def env(raiz, tmp_path):
    morada = tmp_path / "morada"
    for ch in CHAPEUS:
        d = morada / "current" / "abertura" / "ia" / ch
        d.mkdir(parents=True)
        (d / "chapeu.md").write_text(f"# {ch}\n", encoding="utf-8")
    return {"PF_CADEIRA": "ia", "PF_BIN": str(raiz / "bin"), "PF_ABERTURA_DIR": str(morada),
            "PF_ORIGEM_SESSAO": "11111111-1111-4111-8111-111111111111",
            "STUB_MOTOR_LOG": str(raiz / "motor.log")}


def _monta(raiz, env, chapeu, *extra):
    return _run_expediente(["montar", "--chapeu", chapeu, *extra, "--json"], raiz, env_extra=env)


def test_pedaco_unico_vira_o_slug_inteiro_com_aviso(raiz, env):
    proc = _monta(raiz, env, "harness")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "engenharia-de-harness"
    assert d["roteador"]["slug"] == "engenharia-de-harness"
    assert "chapéu 'harness' resolvido para 'engenharia-de-harness'" in d["avisos"]
    assert d["chapeu"] == "engenharia-de-harness"
    assert d["pecas"]


def test_maiuscula_e_acento_nao_atrapalham(raiz, env):
    d = json.loads(_monta(raiz, env, "Contéxto").stdout)
    assert d["chapeu"] == "contexto"


def test_nome_exato_passa_calado(raiz, env):
    d = json.loads(_monta(raiz, env, "contexto").stdout)
    assert d["chapeu"] == "contexto"
    assert not any("resolvido" in a for a in d["avisos"])


def test_pedaco_ambiguo_sai_2_com_as_opcoes(raiz, env):
    proc = _monta(raiz, env, "en")
    assert proc.returncode == 2
    erro = json.loads(proc.stdout)["erro"]
    assert "ambíguo" in erro and "agente" in erro and "engenharia-de-harness" in erro


def test_o_que_nao_casa_segue_para_a_validacao_de_sempre(raiz, env):
    proc = _monta(raiz, env, "invalido")
    assert proc.returncode == 2
    assert "fora do vocabulário" in json.loads(proc.stdout)["erro"]


def test_apelido_do_titulo_vira_o_slug_com_aviso(raiz, env):
    titulo = Path(env["PF_ABERTURA_DIR"]) / "current" / "abertura" / "ia" / "contexto" / "chapeu.md"
    titulo.write_text("# Contexto (janela, memoria)\n", encoding="utf-8")
    proc = _monta(raiz, env, "Memória")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "contexto"
    assert "chapéu 'Memória' resolvido para 'contexto'" in d["avisos"]


def test_vale_tambem_no_perfil_cadeirinha(raiz, env):
    proc = _monta(raiz, env, "harness", "--perfil", "cadeirinha", "--modo", "revisar")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = json.loads(proc.stdout)
    assert d["chapeu"] == "engenharia-de-harness"
    assert any("resolvido para 'engenharia-de-harness'" in a for a in d["avisos"])
