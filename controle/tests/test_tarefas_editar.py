"""`bin/tarefas editar` (card #3134): o PATCH do corpo com nome de ato.

Roda o script de verdade com `curl` sombreado por função bash exportada, que grava o
método, a URL e o corpo enviados e devolve uma resposta enlatada. `jq` e `python3` são os
reais do host (o verbo depende dos dois); sem `jq`, o teste pula.

Aceite coberto:
- `--desc-stdin` manda um único PATCH em /itens/<id>, com `descricao` em HTML e SEM `estado`;
- `--titulo` sozinho manda só `titulo`;
- sem título nem corpo, e com corpo vazio, recusa com exit 2 sem chamar a API;
- recusa da API sai com exit 1 e a mensagem da máquina em stderr.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "tarefas"

if not shutil.which("jq") or not shutil.which("bash"):
    pytest.skip("editar precisa de bash e jq reais", allow_module_level=True)

RESPOSTA = {"id": 42, "titulo": "card de teste", "estado": "em-execucao",
            "estado_nome": "Em execução", "pai": None}

WRAPPER = r"""
curl() {
  local metodo="" url="" corpo="" a
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
  printf '%s' "$corpo" > "$FAKE_CORPO"
  if [ -n "${FAKE_RECUSA:-}" ]; then
    printf '%s' '{"erro": "recusado pela maquina"}'
    return 22
  fi
  cat "$FAKE_RESPOSTA"
}
export -f curl
exec bash "$FAKE_SCRIPT" "$@"
"""


def _run(args, tmp_path: Path, *, stdin: str | None = None, recusa: bool = False):
    env = dict(os.environ)
    env.pop("PF_CADEIRA", None)
    env["TAREFAS_BASE"] = "http://127.0.0.1:9/api"
    env["FAKE_LOG"] = str(tmp_path / "chamadas.log")
    env["FAKE_CORPO"] = str(tmp_path / "corpo.json")
    resposta = tmp_path / "resposta.json"
    resposta.write_text(json.dumps(RESPOSTA), encoding="utf-8")
    env["FAKE_RESPOSTA"] = str(resposta)
    env["FAKE_SCRIPT"] = str(SCRIPT)
    if recusa:
        env["FAKE_RECUSA"] = "1"
    proc = subprocess.run(["bash", "-c", WRAPPER, "_", *args], env=env, input=stdin,
                          capture_output=True, text=True, timeout=20, check=False)
    log = tmp_path / "chamadas.log"
    chamadas = log.read_text().splitlines() if log.exists() else []
    corpo_p = tmp_path / "corpo.json"
    corpo = json.loads(corpo_p.read_text()) if corpo_p.exists() and corpo_p.read_text() else None
    return proc, chamadas, corpo


def test_desc_stdin_manda_patch_so_do_corpo(tmp_path):
    proc, chamadas, corpo = _run(["editar", "#42", "--desc-stdin"], tmp_path,
                                 stdin="Negócio: #1\n\nAceite: <sai 0>\n")
    assert proc.returncode == 0, proc.stderr
    assert chamadas == ["PATCH http://127.0.0.1:9/api/itens/42"]
    assert set(corpo) == {"descricao"}
    assert corpo["descricao"] == "<p>Negócio: #1</p><p>Aceite: &lt;sai 0&gt;</p>"
    assert "item 42 editado: card de teste" in proc.stdout
    assert "(inalterado)" in proc.stdout


def test_titulo_sozinho_manda_so_titulo(tmp_path):
    proc, chamadas, corpo = _run(["editar", "42", "--titulo", "novo título"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert corpo == {"titulo": "novo título"}
    assert "estado" not in corpo


def test_titulo_e_desc_juntos(tmp_path):
    proc, _, corpo = _run(["editar", "42", "--titulo", "t", "--desc", "corpo"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert corpo == {"titulo": "t", "descricao": "<p>corpo</p>"}


@pytest.mark.parametrize("args,stdin", [
    (["editar", "42"], None),
    (["editar", "42", "--desc-stdin"], "   \n\n"),
])
def test_nada_a_editar_ou_corpo_vazio_recusa_sem_chamar_api(tmp_path, args, stdin):
    proc, chamadas, _ = _run(args, tmp_path, stdin=stdin)
    assert proc.returncode == 2
    assert chamadas == []


def test_opcao_desconhecida_recusa(tmp_path):
    proc, chamadas, _ = _run(["editar", "42", "--estado", "entregue"], tmp_path)
    assert proc.returncode == 2
    assert chamadas == []


def test_recusa_da_api_sai_1_com_a_mensagem(tmp_path):
    proc, _, _ = _run(["editar", "42", "--titulo", "t"], tmp_path, recusa=True)
    assert proc.returncode == 1
    assert "recusado pela maquina" in proc.stderr
