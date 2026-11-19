"""Regressivo #4378: integridade de `remocao-no-pr`, bits executáveis, VERDES e anti-espelho morto.

Garante que:
1. Toda entrada de `remocao-no-pr` tem formato `<caminho> | <motivo/substituto>` não vazio.
2. Toda entrada de `remocao-no-pr` saiu de `controle/tests/VERDES` e `testes/VERDES`.
3. Nenhuma suíte de DT crítica de prod entrou em `remocao-no-pr`.
4. `test_fechamento_harness.sh` tem wrapper (`test_deploy_seg_suites.py`) listado no portão.
5. Todo arquivo direto em `bin/` tem bit executável (`0o111`).
6. Quando executado dentro do `platafirma-casa-espelho` com acesso ao `platafirma-harness` servido,
   nenhum arquivo de `outros_repos/harness` é cópia byte a byte idêntica ao `platafirma-harness`.
"""
from __future__ import annotations

import hashlib
import stat
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REMOCAO = RAIZ / "remocao-no-pr"

SUITES_DT_CRITICAS = (
    "controle/tests/test_contrato_casa_direto_em_main.py",
    "controle/tests/test_repo_dts_809_822_853_884.py",
    "controle/tests/test_release_estagio_card.py",
    "controle/tests/test_contrato_infra.py",
    "controle/tests/test_contrato_infra_remover.py",
    "testes/test_release_uv_porta_suite.py",
    "controle/tests/test_metrica_fonte.py",
    "controle/tests/test_curar_conceito.py",
)


def _ler_remocao() -> list[tuple[str, str]]:
    assert REMOCAO.is_file(), f"remocao-no-pr ausente em {REMOCAO}"
    entradas: list[tuple[str, str]] = []
    for i, bruta in enumerate(REMOCAO.read_text(encoding="utf-8").splitlines(), 1):
        linha = bruta.strip()
        if not linha or linha.startswith("#"):
            continue
        assert "|" in linha, f"remocao-no-pr:{i} sem separador '|' de motivo/substituto: {linha!r}"
        caminho, motivo = (p.strip() for p in linha.split("|", 1))
        assert caminho, f"remocao-no-pr:{i} com caminho vazio"
        assert motivo, f"remocao-no-pr:{i} sem motivo/substituto para {caminho!r}"
        entradas.append((caminho, motivo))
    assert entradas, "remocao-no-pr não pode estar vazio"
    return entradas


def _arquivos_verdes(caminho: Path, prefixo: str) -> set[str]:
    if not caminho.is_file():
        return set()
    itens: set[str] = set()
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.strip()
        if not linha or linha.startswith("#"):
            continue
        alvo = linha.split("|", 1)[0].strip()
        if alvo.startswith("tests/"):
            itens.add(f"controle/{alvo}")
        elif alvo.startswith("testes/"):
            itens.add(alvo)
        else:
            itens.add(f"{prefixo}/{alvo}")
    return itens


def test_remocao_no_pr_formato_e_suites_criticas_protegidas():
    entradas = _ler_remocao()
    caminhos = {c for c, _ in entradas}
    assert "ops-server/" in caminhos and "abertura/" in caminhos
    for critica in SUITES_DT_CRITICAS:
        assert critica not in caminhos, f"suíte crítica de prod não pode entrar em remocao-no-pr: {critica}"


def test_remocao_no_pr_fora_dos_verdes_e_fechamento_coberto():
    caminhos = {c for c, _ in _ler_remocao()}
    verdes_controle = _arquivos_verdes(RAIZ / "controle" / "tests" / "VERDES", "controle/tests")
    verdes_testes = _arquivos_verdes(RAIZ / "testes" / "VERDES", "testes")
    todos_verdes = verdes_controle | verdes_testes

    sobrepostos = sorted(caminhos & todos_verdes)
    assert not sobrepostos, f"entradas de remocao-no-pr ainda listadas nos VERDES: {sobrepostos}"

    wrapper = RAIZ / "testes" / "test_deploy_seg_suites.py"
    assert wrapper.is_file(), "wrapper testes/test_deploy_seg_suites.py ausente"
    assert "test_fechamento_harness.sh" in wrapper.read_text(encoding="utf-8")
    assert "testes/test_deploy_seg_suites.py" in todos_verdes


def test_bins_tem_bit_executavel():
    sem_exec = []
    for p in sorted((RAIZ / "bin").iterdir()):
        if p.is_file() and not p.name.startswith("."):
            if not (p.stat().st_mode & stat.S_IXUSR):
                sem_exec.append(p.name)
    assert not sem_exec, f"bin/ sem bit executável: {sem_exec}"


def test_sem_espelho_morto_quando_rodando_no_espelho():
    """Quando rodando em outros_repos/harness do espelho, nenhum arquivo pode ser cópia morta do harness servido."""
    if RAIZ.parent.name != "outros_repos":
        return
    prod_harness = Path("/opt/platafirma/current/harness")
    if not prod_harness.is_dir():
        return
    mortos = []
    for arq in sorted(RAIZ.rglob("*")):
        if not arq.is_file() or "__pycache__" in arq.parts:
            continue
        rel = arq.relative_to(RAIZ)
        if rel.name == "remocao-no-pr":
            continue
        em_prod = prod_harness / rel
        if em_prod.is_file():
            h1 = hashlib.sha256(arq.read_bytes()).hexdigest()
            h2 = hashlib.sha256(em_prod.read_bytes()).hexdigest()
            if h1 == h2:
                mortos.append(str(rel))
    assert not mortos, f"espelhos mortos idênticos a /opt/platafirma/current/harness: {mortos}"
