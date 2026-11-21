# componente: componente:verbo-tarefas
"""Testes da DT #450 (#2856 linha 450): `tarefas comentarios --busca <termo> --arvore <id>`."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "tarefas"

if not shutil.which("jq") or not shutil.which("bash"):
    pytest.skip("tarefas precisa de bash e jq reais", allow_module_level=True)

WRAPPER = r"""
curl() {
  local metodo="" url="" com_status=0
  while [ $# -gt 0 ]; do
    case "$1" in
      -X) metodo="$2"; shift 2 ;;
      -d) shift 2 ;;
      -H) shift 2 ;;
      -w) com_status=1; shift 2 ;;
      http*) url="$1"; shift ;;
      *) shift ;;
    esac
  done
  printf '%s\n' "$metodo $url" >> "$FAKE_LOG"
  case "$url" in
    */itens/3650/comentarios)
      printf '%s' '{"comentarios":[{"id":3700,"autor":"produto","carimbo":"2026-11-10","corpo":"Contexto inicial do épico"}]}'
      ;;
    */itens/3974/comentarios)
      printf '%s' '{"comentarios":[{"id":3990,"autor":"arquiteto","carimbo":"2026-11-11","corpo":"Nota da feature\nOutra linha"}]}'
      ;;
    */itens/4061/comentarios)
      printf '%s' '{"comentarios":[{"id":4112,"autor":"dono","carimbo":"2026-11-12","corpo":"Abertura longa\nDecisão: adotar Ficha Índice no painel\nFecho posterior"},{"id":4113,"autor":"engenharia","carimbo":"2026-11-12","corpo":"<p>Primeira linha HTML</p><p>Referência a [caso+1] e ficha índice</p>"}]}'
      ;;
    */itens/4062/comentarios)
      printf '%s' '{"comentarios":[{"id":4120,"autor":"engenharia","carimbo":"2026-11-12","corpo":"Sem relação aqui"}]}'
      ;;
    */itens/9001/comentarios)
      printf '%s' '{"comentarios":[{"id":4200,"autor":"engenharia","carimbo":"2026-11-13","corpo":"Ajuste na ficha índice da task"}]}'
      ;;
    */itens/3650)
      printf '%s' '{"id":3650,"chave":"3650","nivel":0,"titulo":"Epico 3650","filhas":[{"id":3974,"chave":"3974","estado":"em-execucao","titulo":"Feature 3974"}]}'
      ;;
    */itens/3974)
      printf '%s' '{"id":3974,"chave":"3974","nivel":1,"titulo":"Feature 3974","filhas":[{"id":4061,"chave":"4061","estado":"em-execucao","titulo":"Story 4061"},{"id":4062,"chave":"4062","estado":"em-execucao","titulo":"Story 4062"}]}'
      ;;
    */itens/4061)
      printf '%s' '{"id":4061,"chave":"4061","nivel":2,"titulo":"Story 4061","filhas":[{"id":9001,"chave":"4061.t1","estado":"em-execucao","titulo":"Task 1"}]}'
      ;;
    */itens/4062)
      printf '%s' '{"id":4062,"chave":"4062","nivel":2,"titulo":"Story 4062","filhas":[]}'
      ;;
    */itens/9001)
      printf '%s' '{"id":9001,"chave":"4061.t1","nivel":3,"titulo":"Task 1","filhas":[]}'
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


def _run(args: list[str], tmp_path: Path):
    log = tmp_path / "calls.log"
    if log.exists():
        log.unlink()
    env = {
        **os.environ,
        "TAREFAS_BASE": "http://127.0.0.1:8120/api",
        "PF_CADEIRA": "engenharia",
        "FAKE_LOG": str(log),
    }
    cmd = f'{WRAPPER}\nbash "{SCRIPT}" ' + " ".join(shlex.quote(a) for a in args)
    proc = subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return proc, calls


def test_comentarios_busca_arvore_desce_netos_e_tasks(tmp_path: Path):
    for argv in (
        ["comentarios", "--busca", "ficha índice", "--arvore", "3650"],
        ["comentarios", "3650", "--busca", "ficha índice", "--arvore"],
    ):
        proc, calls = _run(argv, tmp_path)
        assert proc.returncode == 0, proc.stderr
        linhas = proc.stdout.strip().splitlines()
        assert "#4112 · #4061 · Decisão: adotar Ficha Índice no painel" in linhas
        assert "#4113 · #4061 · Referência a [caso+1] e ficha índice" in linhas
        assert "#4200 · t1 · Ajuste na ficha índice da task" in linhas
        assert all("Abertura longa" not in l for l in linhas)
        assert all("Primeira linha HTML" not in l for l in linhas)
        assert "GET http://127.0.0.1:8120/api/itens/4061/comentarios" in calls


def test_comentarios_busca_sem_arvore_so_no_card(tmp_path: Path):
    proc, calls = _run(["comentarios", "4061", "--busca", "[caso+1]"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "#4113 · #4061 · Referência a [caso+1] e ficha índice"
    assert "GET http://127.0.0.1:8120/api/itens/9001/comentarios" not in calls


def test_comentarios_busca_sem_match_e_uso_errado(tmp_path: Path):
    proc, _ = _run(["comentarios", "--busca", "nao-existe", "--arvore", "3650"], tmp_path)
    assert proc.returncode == 0
    assert 'nenhum comentário encontrado para "nao-existe"' in proc.stdout

    proc_sem_termo, _ = _run(["comentarios", "3650", "--busca"], tmp_path)
    assert proc_sem_termo.returncode == 2

    proc_sem_id, _ = _run(["comentarios", "--busca", "x", "--arvore"], tmp_path)
    assert proc_sem_id.returncode == 2


def test_comentarios_modo_classico_preservado(tmp_path: Path):
    proc, _ = _run(["comentarios", "4061", "--indice"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "#4112 · dono · 2026-11-12" in proc.stdout
    assert "#4113 · engenharia · 2026-11-12" in proc.stdout
