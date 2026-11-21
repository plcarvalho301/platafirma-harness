# componente: componente:verbo-tarefas
"""Testes dos DTs 38, 97, 455 e 539 em `bin/tarefas`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "tarefas"

if not shutil.which("jq") or not shutil.which("bash"):
    pytest.skip("tarefas precisa de bash e jq reais", allow_module_level=True)

WRAPPER = r"""
curl() {
  local metodo="" url="" corpo="" com_status=0
  while [ $# -gt 0 ]; do
    case "$1" in
      -X) metodo="$2"; shift 2 ;;
      -d) [ "$2" = "@-" ] && corpo="$(cat)"; shift 2 ;;
      -H) shift 2 ;;
      -w) com_status=1; shift 2 ;;
      http*) url="$1"; shift ;;
      *) shift ;;
    esac
  done
  printf '%s\n' "$metodo $url" >> "$FAKE_LOG"
  [ -n "$corpo" ] && printf '%s' "$corpo" > "$FAKE_CORPO"
  case "$url" in
    */registro)
      printf '%s' '{"estados":[{"estado":"em-execucao","fase":"execucao","natureza":"aberta"},{"estado":"entregue","fase":"terminal","natureza":"terminal"}]}'
      ;;
    */itens/42)
      if [ "$metodo" = "PATCH" ]; then
        printf '%s' '{"id":42,"titulo":"card 42","estado":"em-execucao","pai":null}'
      else
        printf '%s' '{"id":42,"chave":"42","nivel":1,"nivel_nome":"feature","titulo":"Feature 42","estado":"em-execucao","estado_nome":"Em execução","estado_fase":"execucao","estado_derivado":null,"cadeira":"engenharia","ancestrais":[],"bloqueia":[],"bloqueado_por":[],"sign_offs":[],"descricao":"<p>Aceite: &#x27;aspas hex&#x27;, &#39;decimal&#39; &amp; &quot;aspas&quot;</p>","filhas":[{"id":101,"chave":"101","estado":"em-execucao","cadeira":"engenharia","titulo":"Story aberta","travada":false},{"id":102,"chave":"102","estado":"entregue","cadeira":"engenharia","titulo":"Story entregue","travada":false}]}'
      fi
      ;;
    */itens/699)
      printf '%s' '{"id":699,"chave":"699","nivel":1,"nivel_nome":"feature","titulo":"Feature 699","estado":"em-execucao","estado_nome":"Em execução","estado_fase":"execucao","estado_derivado":null,"cadeira":"engenharia","ancestrais":[],"bloqueia":[],"bloqueado_por":[],"sign_offs":[],"descricao":"<p>Peças:</p><ol><li>primeira peça</li><li>segunda peça</li></ol><p>Fora:</p><ul><li>item fora</li></ul>","filhas":[]}'
      ;;
    */itens\?*)
      printf '%s' '{"itens":[{"id":101,"chave":"101","titulo":"Story aberta","estado":"em-execucao","estado_fase":"execucao","estado_derivado":null}],"estados":[]}'
      ;;
    */balde/528)
      printf '%s' '{"numero":528,"stack":"motor"}'
      ;;
    *)
      printf '%s' '{}'
      ;;
  esac
  if [ "$com_status" -eq 1 ]; then
    printf '\n200'
  fi
}
export -f curl
"""


def _run(args: list[str], tmp_path: Path, extra_env: dict[str, str] | None = None):
    log = tmp_path / "calls.log"
    corpo = tmp_path / "corpo.json"
    env = {
        **os.environ,
        "TAREFAS_BASE": "http://127.0.0.1:8120/api",
        "PF_CADEIRA": "engenharia",
        "FAKE_LOG": str(log),
        "FAKE_CORPO": str(corpo),
        **(extra_env or {}),
    }
    cmd = f'{WRAPPER}\nbash "{SCRIPT}" ' + " ".join(json.dumps(a) for a in args)
    proc = subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    body = json.loads(corpo.read_text(encoding="utf-8")) if corpo.exists() and corpo.read_text(encoding="utf-8").strip() else None
    return proc, calls, body


def test_dt38_sub_sem_pai(tmp_path: Path):
    for argv in (["sub", "42", "--sem-pai"], ["sub", "--sem-pai", "42"]):
        proc, calls, body = _run(argv, tmp_path)
        assert proc.returncode == 0, proc.stderr
        assert "agora está sem pai" in proc.stdout
        assert "PATCH http://127.0.0.1:8120/api/itens/42" in calls
        assert body == {"pai": None}


def test_dt97_ler_todas_filhas_e_listar_pai(tmp_path: Path):
    proc_abertas, _, _ = _run(["ler", "42"], tmp_path)
    assert proc_abertas.returncode == 0, proc_abertas.stderr
    assert "Story aberta" in proc_abertas.stdout
    assert "Story entregue" not in proc_abertas.stdout

    proc_todas, _, _ = _run(["ler", "42", "--todas-filhas"], tmp_path)
    assert proc_todas.returncode == 0, proc_todas.stderr
    assert "filhas (todas):" in proc_todas.stdout
    assert "Story aberta" in proc_todas.stdout
    assert "Story entregue" in proc_todas.stdout

    proc_listar, calls, _ = _run(["listar", "--pai", "42"], tmp_path)
    assert proc_listar.returncode == 0, proc_listar.stderr
    assert any("GET http://127.0.0.1:8120/api/itens?pai=42" in c for c in calls), calls


def test_dt455_para_texto_decodifica_entidades_hex_e_dec(tmp_path: Path):
    proc, _, _ = _run(["ler", "42"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "&#x27;" not in proc.stdout
    assert "&#39;" not in proc.stdout
    assert "Aceite: 'aspas hex', 'decimal' & \"aspas\"" in proc.stdout


def test_dt539_dt_restack(tmp_path: Path):
    acervo_fake = tmp_path / "acervo"
    acervo_fake.write_text('#!/usr/bin/env bash\necho \'[{"slug":"harness"},{"slug":"motor"}]\'\n', encoding="utf-8")
    acervo_fake.chmod(0o755)

    proc, calls, body = _run(
        ["dt", "restack", "528", "--stack", "motor", "--motivo", "movendo para motor"],
        tmp_path,
        {"PF_ACERVO_BIN": str(acervo_fake)},
    )
    assert proc.returncode == 0, proc.stderr
    assert "débito 528 movido para a stack motor: movendo para motor" in proc.stdout
    assert "PATCH http://127.0.0.1:8120/api/balde/528" in calls
    assert body == {"stack": "motor"}

    proc_bad, _, _ = _run(
        ["dt", "restack", "528", "--stack", "inventada"],
        tmp_path,
        {"PF_ACERVO_BIN": str(acervo_fake)},
    )
    assert proc_bad.returncode == 4
    assert "fora do catálogo do acervo" in proc_bad.stderr


def test_dts_699_700_718_para_texto_preserva_numeracao_de_ol(tmp_path: Path):
    proc, _, _ = _run(["ler", "699"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "1. primeira peça" in proc.stdout
    assert "2. segunda peça" in proc.stdout
    assert "  - item fora" in proc.stdout
