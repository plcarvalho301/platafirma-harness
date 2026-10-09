"""Todo teste da pasta testes/ da raiz tem lista de portão (card #3326).

Até o #3326, testes/ não estava em gate nenhum: o portão só roda as listas VERDES das chaves
com subárvore (arq:0116 §5-§6), e nenhuma lista citava testes/. Os testes apodreciam sem
barrar nada (medido em 06/10/2026: 9 defasados, dois deles fósseis de verbo apagado e um
que escrevia na tabela acervo.stack de produção).

O que se trava aqui, sem rodar teste nenhum:
- cada testes/test_*.py está em exatamente uma lista: testes/VERDES (chave acervo) ou
  controle/tests/VERDES (chave harness, pelo caminho a partir da raiz);
- cada testes/test_*.sh é chamado por um wrapper .py que está numa das listas;
- toda entrada de testes/ nas listas aponta arquivo que existe.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TESTES = RAIZ / "testes"
LISTA_ACERVO = TESTES / "VERDES"
LISTA_HARNESS = RAIZ / "controle" / "tests" / "VERDES"


def _entradas(lista: Path) -> list[str]:
    # a linha pode trazer o raio depois de `|` (card #3370): aqui so o arquivo
    return [linha.split("|")[0].strip() for linha in lista.read_text(encoding="utf-8").splitlines()
            if linha.strip() and not linha.lstrip().startswith("#")]


def _listados() -> dict[str, list[str]]:
    """nome do arquivo em testes/ -> listas que o citam."""
    donos: dict[str, list[str]] = {}
    for nome in _entradas(LISTA_ACERVO):
        donos.setdefault(nome, []).append("testes/VERDES")
    for entrada in _entradas(LISTA_HARNESS):
        if entrada.startswith("testes/"):
            donos.setdefault(entrada.removeprefix("testes/"), []).append("controle/tests/VERDES")
    return donos


def test_todo_py_de_testes_tem_exatamente_uma_lista():
    donos = _listados()
    sem_lista = sorted(p.name for p in TESTES.glob("test_*.py") if p.name not in donos)
    em_duas = sorted(n for n, listas in donos.items() if len(listas) > 1)
    assert not sem_lista, f"testes/ sem lista de portão (nenhum gate roda): {sem_lista}"
    assert not em_duas, f"testes/ em mais de uma lista (roda em dois venvs): {em_duas}"


def test_toda_entrada_aponta_arquivo_que_existe():
    faltam = sorted(n for n in _listados() if not (TESTES / n).is_file())
    assert not faltam, f"lista de portão cita arquivo que não existe em testes/: {faltam}"


def test_todo_sh_de_testes_roda_por_wrapper_no_portao():
    wrappers = [TESTES / n for n in _listados() if n.endswith(".py")]
    citados: set[str] = set()
    for w in wrappers:
        citados |= set(re.findall(r"test_[\w]+\.sh", w.read_text(encoding="utf-8")))
    orfaos = sorted(p.name for p in TESTES.glob("test_*.sh") if p.name not in citados)
    assert not orfaos, f"testes/*.sh que nenhum wrapper do portão chama: {orfaos}"
