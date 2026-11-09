"""Testes dos DTs 355 e 489:
- DT 355: tarefas ler <id> --cabecalho (só a linha de cabeçalho)
- DT 489: tarefas listar-tudo --ultimos <n> (ordena por data desc, com data)
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
    pytest.skip("precisa de bash e jq reais", allow_module_level=True)

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
  case "$url" in
    */registro)
      printf '%s' '{"estados":[{"estado":"entregue","fase":"terminal","nome":"Entregue"}]}'
      return 0 ;;
    */itens/42)
      printf '%s' '{"id":42,"titulo":"card de teste","estado":"entregue","estado_nome":"Entregue","estado_fase":"terminal","nivel_nome":"story","cadeira":"engenharia","tipo_demanda":"tecnico","executor":"devops","descricao":"<p>corpo longo que nao deve sair no cabecalho</p>","ancestrais":[],"bloqueia":[],"bloqueado_por":[],"sign_offs":[],"filhas":[]}'
      return 0 ;;
    */itens*)
      printf '%s' '{"itens":[{"id":10,"titulo":"Dez","estado":"entregue","estado_nome":"Entregue","estado_fase":"terminal","ultimo_movimento":"2026-11-01 10:00:00+00:00"},{"id":20,"titulo":"Vinte","estado":"entregue","estado_nome":"Entregue","estado_fase":"terminal","ultimo_movimento":"2026-11-08 10:00:00+00:00"},{"id":30,"titulo":"Trinta","estado":"entregue","estado_nome":"Entregue","estado_fase":"terminal","ultimo_movimento":"2026-11-05 10:00:00+00:00"}],"estados":[{"estado":"entregue","fase":"terminal"}],"total":3}'
      return 0 ;;
    *)
      printf '%s' '{}'
      return 0 ;;
  esac
}
export -f curl
exec bash "$FAKE_SCRIPT" "$@"
"""


def _roda(args, tmp_path: Path) -> subprocess.CompletedProcess:
    script_sh = tmp_path / "wrapper.sh"
    script_sh.write_text(WRAPPER, encoding="utf-8")
    env = dict(os.environ)
    env["FAKE_SCRIPT"] = str(SCRIPT)
    env["FAKE_LOG"] = str(tmp_path / "curl.log")
    env["TAREFAS_BASE"] = "http://127.0.0.1:8120/api"
    return subprocess.run(
        ["bash", str(script_sh), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_dt355_ler_cabecalho(tmp_path):
    proc = _roda(["ler", "42", "--cabecalho"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "# card de teste" in proc.stdout
    assert "#42 · story · Entregue (terminal) · cadeira: engenharia · originação: tecnico · executor: devops" in proc.stdout
    assert "corpo longo que nao deve sair no cabecalho" not in proc.stdout


def test_dt489_listar_tudo_ultimos(tmp_path):
    proc = _roda(["listar-tudo", "--estado", "entregue", "--ultimos", "2"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.strip().splitlines()
    assert len(linhas) == 2
    assert linhas[0] == "20\tx\t2026-11-08\tVinte"
    assert linhas[1] == "30\tx\t2026-11-05\tTrinta"


def test_dt489_listar_tudo_sem_ultimos_mantem_hoje(tmp_path):
    proc = _roda(["listar-tudo", "--estado", "entregue"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.strip().splitlines()
    assert len(linhas) == 3
    assert linhas[0] == "10\tx\tDez"
    assert linhas[1] == "20\tx\tVinte"
    assert linhas[2] == "30\tx\tTrinta"
