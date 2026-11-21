# componente: componente:verbo-tarefas
"""Testes dos DTs 271, 323, 404 e 592 em `bin/tarefas`."""
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
  local metodo="GET" url="" corpo="" com_status=0
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
    */balde/indicadores*)
      cat "$FAKE_INDICADORES"
      ;;
    */balde\?*)
      cat "$FAKE_BALDE"
      ;;
    */itens/2856)
      if [ -f "$FAKE_ITEM_2856" ]; then
        cat "$FAKE_ITEM_2856"
      else
        printf '%s' '{"erro":"nao existe"}'
        [ "$com_status" -eq 1 ] && printf '\n404'
        return 22
      fi
      ;;
    */itens/900)
      if [ "$metodo" = "PATCH" ]; then
        printf '%s' '{"id":900,"titulo":"Story 900","estado":"em-execucao","estado_nome":"Em execução","pai":null}'
      else
        cat "$FAKE_ITEM_900"
      fi
      ;;
    */modelo/story-refinada)
      cat "$FAKE_MODELO_REFINADA"
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
    if log.exists():
        log.unlink()
    if corpo.exists():
        corpo.unlink()
    env = {
        **os.environ,
        "TAREFAS_BASE": "http://127.0.0.1:8120/api",
        "PF_CADEIRA": "ti",
        "FAKE_LOG": str(log),
        "FAKE_CORPO": str(corpo),
        "FAKE_BALDE": str(tmp_path / "balde.json"),
        "FAKE_INDICADORES": str(tmp_path / "indicadores.json"),
        "FAKE_ITEM_2856": str(tmp_path / "item_2856.json"),
        "FAKE_ITEM_900": str(tmp_path / "item_900.json"),
        "FAKE_MODELO_REFINADA": str(tmp_path / "modelo_refinada.json"),
        **(extra_env or {}),
    }
    cmd = f'{WRAPPER}\nbash "{SCRIPT}" ' + " ".join(json.dumps(a) for a in args)
    proc = subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True)
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    body = (
        json.loads(corpo.read_text(encoding="utf-8"))
        if corpo.exists() and corpo.read_text(encoding="utf-8").strip()
        else None
    )
    return proc, calls, body


def test_dt271_dt_listar_curto_mostra_tamanho_kib_e_avisa_acima_de_100_kib(tmp_path: Path):
    """DT 271: `tarefas dt listar --curto` mostra o tamanho em KiB de #2856 e avisa quando > 100 KiB."""
    balde_pequeno = {
        "situacao": "abertas",
        "stack": None,
        "linhas": [
            {
                "numero": 271,
                "idade_dias": 5,
                "stack": "harness",
                "texto": "dt listar curto sem KiB",
                "raio": ["platafirma-harness@bin/tarefas"],
                "esperado": "exibe KiB",
                "onde": "repro",
                "saida_jeito": None,
                "saida_ancora": None,
            }
        ],
        "total": 1,
    }
    (tmp_path / "balde.json").write_text(json.dumps(balde_pequeno), encoding="utf-8")
    (tmp_path / "item_2856.json").write_text(
        json.dumps({"id": 2856, "descricao": "x" * (40 * 1024)}),
        encoding="utf-8",
    )

    proc_ok, _, _ = _run(["dt", "listar", "--curto"], tmp_path)
    assert proc_ok.returncode == 0, proc_ok.stderr
    assert "corpo #2856: 40 KiB" in proc_ok.stdout
    assert "AVISO: balde de DTs com" not in proc_ok.stdout

    # Passando de 100 KiB (ex.: 115 KiB no corpo do #2856): emite AVISO
    (tmp_path / "item_2856.json").write_text(
        json.dumps({"id": 2856, "descricao": "y" * (115 * 1024)}),
        encoding="utf-8",
    )
    proc_aviso, _, _ = _run(["dt", "listar", "--curto"], tmp_path)
    assert proc_aviso.returncode == 0, proc_aviso.stderr
    assert "corpo #2856: 115 KiB" in proc_aviso.stdout
    assert "AVISO: balde de DTs com 115 KiB (teto 100 KiB)" in proc_aviso.stdout

    # Indicadores com corpo_bytes > 100 KiB também exibe KiB e AVISO
    (tmp_path / "indicadores.json").write_text(
        json.dumps(
            {
                "abertos": 1,
                "por_stack": [
                    {
                        "stack": "harness",
                        "abertos": 1,
                        "mais_velho_numero": 271,
                        "mais_velho_dias": 5,
                    }
                ],
                "semana": {"dias": 7, "entradas": 1, "saidas_total": 0, "saidas": {}},
                "corpo_bytes": 108 * 1024,
            }
        ),
        encoding="utf-8",
    )
    proc_ind, _, _ = _run(["dt", "indicadores"], tmp_path)
    assert proc_ind.returncode == 0, proc_ind.stderr
    assert "AVISO: balde de DTs com 108 KiB (teto 100 KiB)" in proc_ind.stdout


def test_dt323_mover_em_execucao_ignora_palavra_escreve_e_parenteses(tmp_path: Path):
    """DT 323: `mover <id> em-execucao` não trata 'escreve' nem parênteses descritivos como arquivos fora do raio."""
    plano = """### Arquivos no Raio
- `package.json` — dependências
- `platafirma-harness@bin/tarefas` — script principal

### Unidades
| # | unidade | arquivos | verificacao | depende |
|---|---|---|---|---|
| U1 | Atualiza pacotes | escreve: `package.json` (e o lock, pelo npm) | npm test | — |
| U2 | Ajusta CLI | escreve `platafirma-harness@bin/tarefas` (sem mudar contrato) | pytest | U1 |
"""
    (tmp_path / "item_900.json").write_text(
        json.dumps({"id": 900, "titulo": "Story 900", "descricao": plano}),
        encoding="utf-8",
    )
    proc, calls, body = _run(["mover", "900", "em-execucao"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert body == {"estado": "em-execucao"}
    assert any("PATCH http://127.0.0.1:8120/api/itens/900" in c for c in calls)


def test_dt404_modelo_story_refinada_e_unidades_sem_arquivo(tmp_path: Path):
    """DT 404: `modelo story refinada` alinha cabeçalho de Unidades e `mover em-execucao` aceita —/nenhum e coluna escreve descritiva."""
    (tmp_path / "modelo_refinada.json").write_text(
        json.dumps(
            {
                "variante": "story-refinada",
                "texto": "### Unidades\n| # | unidade | escreve |\n| 1 | <passo> | escreve: <repo@caminho> |\n",
                "aviso": None,
            }
        ),
        encoding="utf-8",
    )
    proc_mod, _, _ = _run(["modelo", "story", "refinada"], tmp_path)
    assert proc_mod.returncode == 0, proc_mod.stderr
    assert "| # | escreve | arquivos |" in proc_mod.stdout
    assert "escreve: <repo@caminho>" not in proc_mod.stdout

    plano_sem_arq = """### Arquivos no Raio
- `bin/tarefas`

### Unidades
| # | escreve | arquivos | verificacao | depende |
|---|---|---|---|---|
| U1 | escreve a regra no parser | `bin/tarefas` | pytest | — |
| U2 | valida só no banco (sem tocar arquivo) | — | pytest | U1 |
| U3 | conferência manual | nenhum | pytest | U2 |
"""
    (tmp_path / "item_900.json").write_text(
        json.dumps({"id": 900, "titulo": "Story 900", "descricao": plano_sem_arq}),
        encoding="utf-8",
    )
    proc, calls, _ = _run(["mover", "900", "em-execucao"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert any("PATCH http://127.0.0.1:8120/api/itens/900" in c for c in calls)


def test_dt592_mover_em_execucao_le_coluna_arquivos_pelo_cabecalho_e_cita_coluna_na_recusa(tmp_path: Path):
    """DT 592: identifica a coluna `arquivos` pelo cabeçalho Markdown (`| # | escreve | arquivos | ... |`) e cita a coluna ao recusar."""
    plano_fora = """### Arquivos no Raio
- `bin/tarefas`

### Unidades
| # | escreve | arquivos | verificacao | depende |
|---|---|---|---|---|
| U1 | altera o parser de unidades | `bin/tarefas` | pytest | — |
| U2 | mexe em outro script | `bin/outro_script.sh` | pytest | U1 |
"""
    (tmp_path / "item_900.json").write_text(
        json.dumps({"id": 900, "titulo": "Story 900", "descricao": plano_fora}),
        encoding="utf-8",
    )
    proc, calls, _ = _run(["mover", "900", "em-execucao"], tmp_path)
    assert proc.returncode == 1
    assert "Unidade U2 toca 'bin/outro_script.sh'" in proc.stderr
    assert "coluna 'arquivos'" in proc.stderr
    assert not any("PATCH" in c for c in calls)

    # Fallback para cabeçalho com coluna `escreve` (sem coluna `arquivos`): cita `coluna 'escreve'`
    plano_fallback = """### Arquivos no Raio
- `bin/tarefas`

### Unidades
| # | nome | escreve | depende | prova |
|---|---|---|---|---|
| U1 | passo fora | `bin/fora_do_raio.py` (ajuste extra) | — | pytest |
"""
    (tmp_path / "item_900.json").write_text(
        json.dumps({"id": 900, "titulo": "Story 900", "descricao": plano_fallback}),
        encoding="utf-8",
    )
    proc_fb, calls_fb, _ = _run(["mover", "900", "em-execucao"], tmp_path)
    assert proc_fb.returncode == 1
    assert "Unidade U1 toca 'bin/fora_do_raio.py'" in proc_fb.stderr
    assert "coluna 'escreve'" in proc_fb.stderr
    assert not any("PATCH" in c for c in calls_fb)
