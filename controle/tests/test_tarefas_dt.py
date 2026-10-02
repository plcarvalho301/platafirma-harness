"""`bin/tarefas dt` (card #3175): o balde de débito técnico em linhas no corpo do #2856.

Roda o script de verdade com `curl` sombreado por função bash exportada: GET devolve o
item enlatado (com o corpo do balde em HTML), PATCH grava o corpo enviado. `jq` e
`python3` são os reais do host; sem `jq`, o teste pula. A data de hoje vem de `DT_HOJE`.

Aceite coberto:
- `listar` e `vencidos` leem as linhas de «## Abertos» com a idade pela data da medição;
- `admitir` numera pelo maior número das duas seções e grava UM PATCH só com `descricao`;
- `admitir` sem --evidencia, ou com data fora de AAAA-MM-DD, recusa sem chamar a API;
- `matar` tira a linha pela porta do rito, registra em «## Saídas» e some com o marcador
  «(nenhuma…)»; porta sem âncora recusa sem PATCH; card da porta `card` é lido antes;
- linha que não está aberta sai 1; corpo sem as seções sai 3; nenhum dos dois grava.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "tarefas"

if not shutil.which("jq") or not shutil.which("bash"):
    pytest.skip("dt precisa de bash e jq reais", allow_module_level=True)

CORPO = ("<p>Balde de débito técnico.</p>"
         "<p>## Abertos</p>"
         "<p>1. [2026-08-01] repo — falha velha · repo commitar exit 1<br>"
         "3. [2026-09-20] teste — falha nova · teste rodar exit 2</p>"
         "<p>## Saídas</p>"
         "<p>(nenhuma desde a mudança de regime)</p>")

WRAPPER = r"""
curl() {
  local metodo="" url="" corpo=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -X) metodo="$2"; shift 2 ;;
      -d) [ "$2" = "@-" ] && corpo="$(cat)"; shift 2 ;;
      -H) shift 2 ;;
      http*) url="$1"; shift ;;
      *) shift ;;
    esac
  done
  printf '%s\n' "$metodo $url" >> "$FAKE_LOG"
  if [ "$metodo" = PATCH ]; then
    printf '%s' "$corpo" > "$FAKE_CORPO"
    printf '%s' '{"id": 2856}'
    return 0
  fi
  cat "$FAKE_RESPOSTA"
}
export -f curl
exec bash "$FAKE_SCRIPT" "$@"
"""


def _run(args, tmp_path: Path, *, corpo: str = CORPO):
    env = dict(os.environ)
    env.pop("PF_CADEIRA", None)
    env.pop("TAREFAS_DT_PAI", None)
    env["TAREFAS_BASE"] = "http://127.0.0.1:9/api"
    env["DT_HOJE"] = "2026-09-27"
    env["FAKE_LOG"] = str(tmp_path / "chamadas.log")
    env["FAKE_CORPO"] = str(tmp_path / "corpo.json")
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps({"id": 2856, "titulo": "Balde", "descricao": corpo}),
                        encoding="utf-8")
    env["FAKE_RESPOSTA"] = str(resposta)
    env["FAKE_SCRIPT"] = str(SCRIPT)
    proc = subprocess.run(["bash", "-c", WRAPPER, "_", *args], env=env,
                          capture_output=True, text=True, timeout=30, check=False)
    log = tmp_path / "chamadas.log"
    chamadas = log.read_text().splitlines() if log.exists() else []
    enviado = tmp_path / "corpo.json"
    patch = json.loads(enviado.read_text()) if enviado.exists() else None
    return proc, chamadas, patch


def _texto(patch) -> list[str]:
    """O corpo enviado, de volta a linhas de texto."""
    assert set(patch) == {"descricao"}
    t = re.sub(r"</p>|<br>", "\n", patch["descricao"])
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return [l for l in t.splitlines() if l.strip()]


def test_listar_mostra_as_abertas_com_idade(tmp_path):
    proc, chamadas, patch = _run(["dt", "listar"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert chamadas == ["GET http://127.0.0.1:9/api/itens/2856"]
    assert patch is None
    assert "1\t57d\trepo — falha velha · repo commitar exit 1" in proc.stdout
    assert "3\t7d\tteste — falha nova · teste rodar exit 2" in proc.stdout


def test_vencidos_so_acima_de_30_dias(tmp_path):
    proc, _, _ = _run(["dt", "vencidos"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "1\t57d" in proc.stdout
    assert "falha nova" not in proc.stdout


def test_listar_desde_pula_as_linhas_antes_do_numero(tmp_path):
    """#2856 linha 143: a lista inteira passa dos 50 KB que a porta serve; --desde lê só o fim."""
    proc, _, _ = _run(["dt", "listar", "--desde", "2"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "falha velha" not in proc.stdout
    assert "3\t7d\tteste — falha nova · teste rodar exit 2" in proc.stdout


def test_listar_curto_tira_a_evidencia(tmp_path):
    proc, _, _ = _run(["dt", "listar", "--curto"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "1\t57d\trepo — falha velha\n" in proc.stdout
    assert "repo commitar exit 1" not in proc.stdout


@pytest.mark.parametrize("args", [
    ["dt", "listar", "--sem-isso"],
    ["dt", "listar", "--desde", "x"],
    ["dt", "listar", "--desde"],
])
def test_listar_com_opcao_ruim_recusa_sem_chamar_a_api(tmp_path, args):
    proc, chamadas, _ = _run(args, tmp_path)
    assert proc.returncode == 2
    assert chamadas == []


def test_admitir_numera_pelo_maior_e_grava_um_patch(tmp_path):
    corpo = CORPO.replace("<p>(nenhuma desde a mudança de regime)</p>",
                          "<p>7. [2026-08-02] velha → morre por obsolescência em 2026-09-01: x</p>")
    proc, chamadas, patch = _run(["dt", "admitir", "cai no meio", "--medido-em", "2026-09-27",
                                  "--evidencia", "infra up exit 124", "--verbo", "infra"],
                                 tmp_path, corpo=corpo)
    assert proc.returncode == 0, proc.stderr
    assert chamadas == ["GET http://127.0.0.1:9/api/itens/2856",
                        "PATCH http://127.0.0.1:9/api/itens/2856"]
    linhas = _texto(patch)
    nova = "8. [2026-09-27] infra — cai no meio · infra up exit 124"
    assert nova in linhas
    assert linhas.index(nova) < linhas.index("## Saídas")
    assert linhas.index(nova) == linhas.index("3. [2026-09-20] teste — falha nova · teste rodar exit 2") + 1
    assert "débito 8 admitido" in proc.stdout


@pytest.mark.parametrize("extra", [
    ["--medido-em", "2026-09-27"],
    ["--medido-em", "27/09", "--evidencia", "x"],
    ["--evidencia", "x"],
])
def test_admitir_sem_medicao_recusa_sem_chamar_api(tmp_path, extra):
    proc, chamadas, patch = _run(["dt", "admitir", "algo", *extra], tmp_path)
    assert proc.returncode == 2
    assert chamadas == []
    assert patch is None
    assert "rito §1" in proc.stderr


def test_matar_obsoleto_move_para_saidas(tmp_path):
    proc, _, patch = _run(["dt", "matar", "1", "--porta", "obsoleto",
                           "--ancora", "repo commitar exit 0 em 27/09"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    linhas = _texto(patch)
    assert not any(l.startswith("1. [2026-08-01]") and "→" not in l for l in linhas)
    saida = ("1. [2026-08-01] repo — falha velha · repo commitar exit 1 → morre por "
             "obsolescência em 2026-09-27: repo commitar exit 0 em 27/09")
    assert saida in linhas
    assert linhas.index(saida) > linhas.index("## Saídas")
    assert not any(l.startswith("(nenhuma") for l in linhas)


@pytest.mark.parametrize("args", [
    ["dt", "matar", "1", "--porta", "obsoleto"],
    ["dt", "matar", "1", "--porta", "decisao"],
    ["dt", "matar", "1", "--porta", "card"],
    ["dt", "matar", "1", "--porta", "englobado"],
    ["dt", "matar", "1", "--porta", "sumiu"],
    ["dt", "matar", "um", "--porta", "obsoleto", "--ancora", "x"],
])
def test_matar_sem_ancora_ou_porta_invalida_recusa(tmp_path, args):
    proc, chamadas, patch = _run(args, tmp_path)
    assert proc.returncode == 2
    assert chamadas == []
    assert patch is None


def test_matar_porta_card_le_o_card_e_ancora_nele(tmp_path):
    proc, chamadas, patch = _run(["dt", "matar", "3", "--porta", "card", "--card", "#4000"],
                                 tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert chamadas[0] == "GET http://127.0.0.1:9/api/itens/4000"
    assert any(l.endswith("→ vira card em 2026-09-27: #4000") for l in _texto(patch))


def test_matar_linha_fechada_sai_1_sem_gravar(tmp_path):
    proc, chamadas, patch = _run(["dt", "matar", "2", "--porta", "obsoleto", "--ancora", "x"],
                                 tmp_path)
    assert proc.returncode == 1
    assert patch is None
    assert "PATCH" not in " ".join(chamadas)


def test_corpo_sem_secoes_sai_3(tmp_path):
    proc, _, patch = _run(["dt", "listar"], tmp_path, corpo="<p>texto solto</p>")
    assert proc.returncode == 3
    assert patch is None
