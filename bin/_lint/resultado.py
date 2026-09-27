"""resultado — estruturas de dados e formatador de saida de lint.

Conforme arq:0110 e spec_lint:
Exit codes:
  0: limpo (0 apontamentos)
  1: apontamentos (>0 apontamentos)
  2: uso incorreto
  3: linter ausente / falha do linter / dependência ausente
  4: fora da raiz
  5: indeterminavel (sem lista de verificacao ou linter indeterminavel)

Formato de 1a linha (ancora):
  «lint <classe> <alvo>: N apontamentos — <chave>@rev<N>»
  (ou «lint <classe> <alvo>: N apontamentos — repositorio»)

Linha de apontamento:
    <arquivo>:<linha>: <o_que_fere> — cura: <cura>
"""
from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional


class Apontamento:
    __slots__ = ("arquivo", "linha", "o_que_fere", "cura", "severidade", "id")

    def __init__(
        self,
        arquivo: str,
        linha: int,
        o_que_fere: str,
        cura: str,
        severidade: str = "aviso",
        id: Optional[str] = None,
    ):
        self.arquivo = str(arquivo)
        self.linha = int(linha) if linha else 1
        self.o_que_fere = str(o_que_fere)
        self.cura = str(cura)
        self.severidade = str(severidade)  # 'bloqueante' ou 'aviso'
        self.id = id

    def dict(self) -> dict[str, Any]:
        d = {
            "arquivo": self.arquivo,
            "linha": self.linha,
            "o_que_fere": self.o_que_fere,
            "cura": self.cura,
            "severidade": self.severidade,
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    def __repr__(self) -> str:
        return (
            f"Apontamento({self.arquivo!r}, {self.linha!r}, {self.o_que_fere!r}, "
            f"cura={self.cura!r}, severidade={self.severidade!r})"
        )


def linha_ancora_lint(
    classe: str,
    alvo: Optional[str],
    apontamentos: Iterable[Apontamento],
    chave: str,
    rev: Optional[int | str] = None,
) -> tuple[str, int]:
    lista = list(apontamentos)
    n = len(lista)
    if chave == "repositorio":
        ref_str = "repositorio"
    elif rev is not None and str(rev).strip():
        ref_str = f"{chave}@rev{rev}"
    else:
        ref_str = chave

    alvo_str = f" {alvo}" if alvo else ""
    linha = f"«lint {classe}{alvo_str}: {n} apontamentos — {ref_str}»"
    exit_code = 0 if n == 0 else 1
    return linha, exit_code


def relatorio_lint(
    classe: str,
    alvo: Optional[str],
    apontamentos: Iterable[Apontamento],
    chave: str,
    rev: Optional[int | str] = None,
    como_json: bool = False,
) -> int:
    lista = list(apontamentos)
    linha, exit_code = linha_ancora_lint(classe, alvo, lista, chave, rev)
    if como_json:
        payload = {
            "ancora": linha,
            "classe": classe,
            "alvo": alvo,
            "chave": chave,
            "rev": rev,
            "apontamentos": [a.dict() for a in lista],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return exit_code

    print(linha)
    for a in lista:
        print(f"    {a.arquivo}:{a.linha}: {a.o_que_fere} — cura: {a.cura}")
    return exit_code
