"""Contrato de `bin/tarefas listar --json` (card #390, LOTE 1) e
`bin/tarefas listar-tudo --json` (card #394, data de fechamento pro /feito).

Isola `bin/tarefas` (bash) sem jq real e sem rede — esta máquina de
desenvolvimento não tem nenhum dos dois. `curl`/`jq` são sombreados por
FUNÇÕES bash exportadas (`export -f`) pro processo que roda o script, não
por executáveis soltos num PATH stub: em teste manual, um "curl"/"jq" solto
(mesmo com chmod +x) foi resolvido de forma inconsistente pelo bash deste
Windows — ora achava o real, ora travava — porque o bit de execução
POSIX que o bash-do-git-for-windows enxerga não é o que `Path.chmod()` do
Python (processo nativo Win32, fora do MSYS) escreve. Função exportada não
depende de resolução de PATH nem de bit de execução: é bash puro.

Os stubs cobrem só o que `paginas()`/`linhas_de_card()` de fato usam:
  - curl -sfS -D <hdrfile> <url> -H "Authorization: Bearer <token>"
  - jq -s 'add // []'
  - jq -r '.[] | "\\(.id)\\t\\(if .done then "x" else " " end)\\(.title)"'

Camada 1 do modelo de teste do card (NOTAS-390.md): um teste de formato +
um teste de falha por verbo com --json. Regressão do texto sem --json
também é coberta aqui porque é a mesma função (`listar`) que muda.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "tarefas"


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


def _achar_python_real() -> str:
    """sys.executable é o python real que roda este teste. Não usar
    "python3"/"python" do PATH: nesta máquina isso resolve pro stub da
    Microsoft Store (App Execution Alias), que não executa nada."""
    return str(Path(sys.executable)).replace("\\", "/")


BASH = _achar_bash()
PYTHON_REAL = _achar_python_real()

TAREFAS_FIXAS = [
    {"id": 101, "done": False, "title": "revisar contrato --json"},
    {"id": 102, "done": True, "title": "card fechado (filtro done=false não deveria trazer)"},
    {"id": 103, "done": False, "title": 'título com "aspas" e acento: nível'},
]

# done_at real do Vikunja: ISO quando fechado, e o zero-value do Go
# ("0001-01-01T00:00:00Z") quando aberto — NUNCA JSON null. É esse zero-value
# que listar_tudo --json precisa normalizar pra null de verdade (card #394).
TAREFAS_TUDO_FIXAS = [
    {"id": 201, "done": False, "title": "aberto, sem data de fechamento",
     "done_at": "0001-01-01T00:00:00Z"},
    {"id": 202, "done": True, "title": "fechado ontem",
     "done_at": "2026-08-09T18:53:12-03:00"},
    {"id": 203, "done": True, "title": "fechado hoje, mesmo dia de outro",
     "done_at": "2026-08-10T09:12:00-03:00"},
]

# Só os usos que paginas()/linhas_de_card()/listar_tudo() de fato fazem:
# -s 'add // []' (funde páginas num array só), -r '.[] | "\(.id)\t..."'
# (formata linha tabulada), e -c '[.[] | {id, titulo, fechado, fechado_em}]'
# (listar_tudo --json). Fica em Python (mais simples que reimplementar jq em
# bash); é um arquivo de dados comum, sem exigência de bit de execução — a
# função bash "jq" chama o interpretador real (PYTHON_REAL) explicitamente
# sobre ele.
JQ_STUB_PY = r"""import json
import sys

argv = sys.argv[1:]
data = sys.stdin.read()

if "-s" in argv:
    dec = json.JSONDecoder()
    vals = []
    s = data.strip()
    i = 0
    while i < len(s):
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            break
        obj, i = dec.raw_decode(s, i)
        vals.append(obj)
    out = []
    for v in vals:
        if isinstance(v, list):
            out.extend(v)
    sys.stdout.write(json.dumps(out))
    sys.exit(0)

if "-c" in argv:
    arr = json.loads(data) if data.strip() else []
    out = []
    for item in arr:
        done_at = item.get("done_at")
        out.append({
            "id": item.get("id"),
            "titulo": item.get("title"),
            "fechado": item.get("done"),
            "fechado_em": None if done_at == "0001-01-01T00:00:00Z" else done_at,
        })
    sys.stdout.write(json.dumps(out))
    sys.exit(0)

if "-r" in argv:
    arr = json.loads(data) if data.strip() else []
    for item in arr:
        marca = "x" if item.get("done") else " "
        print(f"{item.get('id')}\t{marca}\t{item.get('title')}")
    sys.exit(0)

sys.stderr.write("fake jq: invocacao nao coberta pelo stub: %r\n" % (argv,))
sys.exit(1)
"""

# Corpo do wrapper que roda em `bash -c`: define curl()/jq() como funções,
# exporta pras subshells/processos filhos e então exec'a bin/tarefas de
# verdade — o exec substitui o processo, então stdout/stderr/exit code
# observados pelo subprocess.run já são os do script real, sem camada extra.
WRAPPER = r"""
curl() {
  local hdr="" args=("$@") i=0
  while [ $i -lt ${#args[@]} ]; do
    case "${args[$i]}" in
      -D) i=$((i+1)); hdr="${args[$i]}" ;;
    esac
    i=$((i+1))
  done
  if [ -n "${FAKE_CURL_FALHAR:-}" ]; then
    echo "fake curl: falha de rede simulada" >&2
    return 7
  fi
  if [ -n "$hdr" ]; then
    printf 'HTTP/1.1 200 OK\r\nx-pagination-total-pages: 1\r\n\r\n' > "$hdr"
  fi
  cat "$FAKE_CURL_BODY"
}
jq() {
  "$FAKE_PYTHON" "$FAKE_JQ_STUB" "$@"
}
export -f curl
export -f jq
exec bash "$FAKE_SCRIPT" "$@"
"""


def _run(
    args,
    tmp_path: Path,
    *,
    body=None,
    falhar: bool = False,
    token: str | None = "tok-de-teste",
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # HOME falso: isola de ~/.claude/vikunja.env e ~/AI/.../.env reais desta
    # máquina — sem isso o teste de "sem credencial" poderia achar um token
    # de verdade e virar um teste que bate na API real por acidente.
    home_falso = tmp_path / "home-falso"
    home_falso.mkdir(exist_ok=True)
    env["HOME"] = str(home_falso)
    env.pop("TAREFAS_ENV", None)
    env.pop("VIKUNJA_TOKEN", None)
    if token is None:
        env.pop("VIKUNJA_API_TOKEN", None)
    else:
        env["VIKUNJA_API_TOKEN"] = token
    if falhar:
        env["FAKE_CURL_FALHAR"] = "1"
    else:
        env.pop("FAKE_CURL_FALHAR", None)

    corpo_path = tmp_path / "corpo.json"
    corpo_path.write_text(
        json.dumps(body if body is not None else TAREFAS_FIXAS), encoding="utf-8"
    )
    jq_stub_path = tmp_path / "jq_stub.py"
    if not jq_stub_path.exists():
        jq_stub_path.write_text(JQ_STUB_PY, encoding="utf-8")

    env["FAKE_CURL_BODY"] = str(corpo_path)
    env["FAKE_PYTHON"] = PYTHON_REAL
    env["FAKE_JQ_STUB"] = str(jq_stub_path).replace("\\", "/")
    env["FAKE_SCRIPT"] = str(SCRIPT).replace("\\", "/")

    cmd = [BASH, "-c", WRAPPER, "_", *args]
    return subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=20, check=False
    )


# --- formato -----------------------------------------------------------------


def test_listar_json_e_o_array_cru_de_paginas(tmp_path):
    """--json: stdout é só o array que paginas() já monta, sem passar por
    linhas_de_card (a régua do card #390 pro verbo mais simples do lote)."""
    proc = _run(["listar", "46", "--json"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    # stdout SÓ o JSON — json.loads falha ("Extra data") se sobrar qualquer
    # texto humano misturado, então isto já valida a régua "nada de mistura".
    dados = json.loads(proc.stdout)
    assert dados == TAREFAS_FIXAS


def test_listar_json_lista_vazia_nao_vira_stdout_vazio(tmp_path):
    """Projeto sem cards: paginas() já normaliza pra [] (add // []); --json
    deve imprimir "[]", não nada — stdout vazio é reservado pra falha."""
    proc = _run(["listar", "46", "--json"], tmp_path, body=[])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == []


def test_listar_sem_json_mantem_texto_tabulado_atual(tmp_path):
    """Regra dura: saída sem --json não muda uma linha."""
    proc = _run(["listar", "46"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    esperado = [
        f"{t['id']}\t{'x' if t['done'] else ' '}\t{t['title']}" for t in TAREFAS_FIXAS
    ]
    assert proc.stdout.splitlines() == esperado


def test_listar_uso_sem_projeto_inalterado(tmp_path):
    """<projeto> ausente: guarda de aridade do bash (${1:?...}) preservada.
    Nota: o exit real hoje é 1 (vem do ${1:?...} do bash), não o 2 que o
    uso() genérico usa pra subcomando desconhecido — comportamento atual
    confirmado rodando o script antes de qualquer edição; preservado como
    estava, não "corrigido" pra 2."""
    proc = _run(["listar"], tmp_path)
    assert proc.returncode == 1
    assert "uso: tarefas listar <projeto>" in proc.stderr
    assert proc.stdout == ""


# --- listar-tudo --json (card #394) -----------------------------------


def test_listar_tudo_json_formato_com_fechado_em(tmp_path):
    """Card #394: titulo/fechado/fechado_em por card, fechado_em como ISO
    quando fechou de verdade."""
    proc = _run(["listar-tudo", "46", "--json"], tmp_path, body=TAREFAS_TUDO_FIXAS)
    assert proc.returncode == 0, proc.stderr
    dados = json.loads(proc.stdout)
    por_id = {d["id"]: d for d in dados}
    assert por_id[202] == {
        "id": 202, "titulo": "fechado ontem", "fechado": True,
        "fechado_em": "2026-08-09T18:53:12-03:00",
    }
    assert por_id[203]["fechado_em"] == "2026-08-10T09:12:00-03:00"


def test_listar_tudo_json_card_aberto_fechado_em_e_null_nao_ausente(tmp_path):
    """A régua do card #394: campo presente e null — nunca a data zero do Go
    (0001-01-01) disfarçada de data real, nunca a chave ausente."""
    proc = _run(["listar-tudo", "46", "--json"], tmp_path, body=TAREFAS_TUDO_FIXAS)
    dados = json.loads(proc.stdout)
    aberto = next(d for d in dados if d["id"] == 201)
    assert "fechado_em" in aberto
    assert aberto["fechado_em"] is None
    assert aberto["fechado"] is False
    assert "0001" not in json.dumps(aberto)


def test_listar_tudo_sem_json_mantem_texto_tabulado_atual(tmp_path):
    """Regra dura: saída sem --json não muda uma linha (inclusive fechados,
    que listar_tudo já trazia antes de --json existir)."""
    proc = _run(["listar-tudo", "46"], tmp_path, body=TAREFAS_TUDO_FIXAS)
    assert proc.returncode == 0, proc.stderr
    esperado = [
        f"{t['id']}\t{'x' if t['done'] else ' '}\t{t['title']}" for t in TAREFAS_TUDO_FIXAS
    ]
    assert proc.stdout.splitlines() == esperado


def test_listar_tudo_json_falha_de_rede_nao_finge_sucesso(tmp_path):
    """Mesmo caminho de paginas() que listar --json — falha vira objeto com
    erro, nunca "[]" nem stdout vazio."""
    proc = _run(["listar-tudo", "46", "--json"], tmp_path, falhar=True)
    assert proc.returncode != 0
    dados = json.loads(proc.stdout)
    assert dados.get("erro")


# --- falha ---------------------------------------------------------------


def test_listar_falha_sem_credencial_sem_json(tmp_path):
    """Sem --json: comportamento intocado — stderr tem o motivo, stdout fica
    vazio, exit 1 preservado."""
    proc = _run(["listar", "46"], tmp_path, token=None)
    assert proc.returncode == 1
    assert "sem credencial" in proc.stderr
    assert proc.stdout == ""


def test_listar_falha_sem_credencial_com_json(tmp_path):
    """carrega_credencial roda antes do dispatch, então --json precisa ser
    detectado ali (não só dentro de listar()) pra régua "nunca stdout vazio
    numa falha" valer também pro caso mais comum de falha do verbo: token
    ausente. stderr continua com o motivo humano; exit 1 preservado."""
    proc = _run(["listar", "46", "--json"], tmp_path, token=None)
    assert proc.returncode == 1
    assert "sem credencial" in proc.stderr
    dados = json.loads(proc.stdout)
    assert "erro" in dados and "credencial" in dados["erro"]


def test_listar_json_falha_de_rede_nao_finge_sucesso(tmp_path):
    """curl falhando dentro de paginas() (não no pré-dispatch de
    carrega_credencial): set -euo pipefail + pipefail propaga a falha pro
    exit code de paginas() (!= 0), mas o estágio interno "jq -s 'add // []'"
    de paginas() degrada QUALQUER stdin vazio pra "[]" — inclusive quando o
    vazio vem de curl tendo falhado no meio do loop, não só de um projeto
    genuinamente sem cards. Sem --json isso já era invisível (o "[]" interno
    era só consumido por linhas_de_card, que itera zero elementos e não
    imprime nada); com --json, paginas() é usado sozinho, então esse "[]"
    passaria a vazar pro stdout como se fosse "zero tarefas" — exatamente o
    "sucesso com zero fake" que a regra dura do LOTE 1 proíbe.

    listar() agora checa o exit code de paginas() explicitamente antes de
    imprimir: sucesso emite o array, falha emite {"erro": ...} e propaga o
    mesmo exit code — nunca o "[]" ambíguo."""
    proc = _run(["listar", "46", "--json"], tmp_path, falhar=True)
    assert proc.returncode != 0
    assert proc.stderr != ""
    dados = json.loads(proc.stdout)
    assert dados.get("erro")


def test_listar_sem_json_falha_de_rede_mesmo_padrao(tmp_path):
    """Mesma falha, sem --json: confirma que o padrão de falha não dependia
    do texto tabulado nem mudou com a introdução da flag."""
    proc = _run(["listar", "46"], tmp_path, falhar=True)
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert proc.stderr != ""
