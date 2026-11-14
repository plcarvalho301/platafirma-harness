"""Regressivos dos DTs 634, 375 e 523."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_dt634_volta_automatica_nao_reverte_abertura_e_stack_grava_servido_real():
    """DT 634: volta automática desliga abertura (`PF_RELEASE_ABERTURA=0`) e `stack` grava `.servido` do contêiner."""
    release_txt = (RAIZ / "bin" / "release").read_text(encoding="utf-8")
    assert 'PF_RELEASE_PORTA=0 PF_RELEASE_ABERTURA=0 "$AQUI/release" reverter "$repo" "$atual"' in release_txt
    assert 'if [ "${PF_RELEASE_ABERTURA:-1}" != 0 ]; then' in release_txt

    stack_txt = (RAIZ / "bin" / "_release" / "stack").read_text(encoding="utf-8")
    assert "sha_servido_no_ar()" in stack_txt
    assert 'gravar_servido "$SERVIDO_REAL"' in stack_txt


def test_dt375_ler_stacks_da_familia_faz_fallback_direto_em_acervo_stack(tmp_path):
    """DT 375: `ler_stacks_da_familia` não trava quando `acervo` falha e lê `acervo.stack` via psql."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "acervo").write_text("#!/usr/bin/env bash\nexit 3\n", encoding="utf-8")
    (fake_bin / "acervo").chmod(0o755)
    (fake_bin / "docker").write_text(
        "#!/usr/bin/env bash\n"
        "printf 'harness-controle|platafirma-harness|controle/compose.yaml|{\"via\": \"promover\"}\\n'\n",
        encoding="utf-8",
    )
    (fake_bin / "docker").chmod(0o755)

    script = (
        f'PATH="{fake_bin}:$PATH"; '
        f'achar_verbo() {{ printf "%s\\n" "{fake_bin}/acervo"; }}; '
        f'source <(sed -n "/^STACKS_PROMOVER=/,/^}}/p" {RAIZ / "bin" / "release"}); '
        f'ler_stacks_da_familia platafirma-harness && printf "PROMOVER=%s\\n" "${{STACKS_PROMOVER[*]}}"'
    )
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "PROMOVER=harness-controle" in p.stdout
    assert "lido direto de acervo.stack" in p.stderr


def test_dt523_bancos_registrados_ignora_fora_da_casa(tmp_path, monkeypatch):
    """DT 523: `registro/bancos.json` declara o 5434 em `_fora_da_casa` e `bancos_registrados()` ignora `_`."""
    import sys

    sys.path.insert(0, str(RAIZ / "lib"))
    from analise.receita import bancos_registrados

    dados_raw = json.loads((RAIZ / "registro" / "bancos.json").read_text(encoding="utf-8"))
    assert "_fora_da_casa" in dados_raw
    assert dados_raw["_fora_da_casa"]["postgres_sistema_5434"]["porta"] == 5434

    monkeypatch.setenv("PF_ANALISE_BANCOS", str(RAIZ / "registro" / "bancos.json"))
    reg = bancos_registrados()
    assert "_fora_da_casa" not in reg
    assert "rag" in reg
