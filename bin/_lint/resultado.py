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

Apontamentos, agrupados (linhas_agrupadas):
      <arquivo>
        <criterio> — cura: <cura>
          <linha>[, <linha>...]: <detalhe do detector>
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Iterator, List, Optional


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
    resumo: bool = False,
) -> int:
    lista = list(apontamentos)
    linha, exit_code = linha_ancora_lint(classe, alvo, lista, chave, rev)
    if resumo:
        # contagem por regra, sem a lista: o que cabe numa tela quando o repo tem centenas
        contagem: dict[str, list] = {}
        for a in lista:
            chave_id = a.id or "-"
            contagem.setdefault(chave_id, [0, a.severidade])[0] += 1
        if como_json:
            print(json.dumps({"ancora": linha, "classe": classe, "alvo": alvo, "chave": chave,
                              "rev": rev, "contagem": {k: {"n": n, "severidade": s}
                                                        for k, (n, s) in contagem.items()}},
                             ensure_ascii=False))
            return exit_code
        print(linha)
        for k, (n, s) in sorted(contagem.items(), key=lambda kv: -kv[1][0]):
            print(f"    {k:<8} {n:>5}  {s}")
        return exit_code
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
    for texto in linhas_agrupadas(lista):
        print(texto)
    return exit_code


def _partes(o_que_fere: str) -> tuple[str, str]:
    """(criterio, detalhe): o detalhe e o colchete do fim, `[ERA001: ...]`, quando ha."""
    if o_que_fere.endswith("]") and " [" in o_que_fere:
        criterio, detalhe = o_que_fere.rsplit(" [", 1)
        return criterio, detalhe[:-1]
    return o_que_fere, ""


def linhas_agrupadas(apontamentos: Iterable[Apontamento]) -> Iterator[str]:
    """A lista em texto, sem repetir o que se repete: o arquivo aparece uma vez; dentro dele,
    cada criterio uma vez, com a cura; embaixo, as linhas do arquivo com o detalhe do detector.
    Detalhes da mesma linha se juntam com « · », e linhas com o mesmo detalhe, numa so.

        bin/curar
          D15 numero ou texto magico — cura: De nome a constante.
            237: PLR2004: Magic value used in comparison, ...
          R1 chamada que sai do processo sem prazo — cura: De prazo a toda chamada externa.
            309, 341, 364: S113: Probable use of `requests` call without timeout
    """
    arquivos: dict[str, dict[tuple[str, str], dict[int, list[str]]]] = {}
    for a in apontamentos:
        criterio, detalhe = _partes(a.o_que_fere)
        detalhes = arquivos.setdefault(a.arquivo, {}).setdefault((criterio, a.cura), {}).setdefault(a.linha, [])
        if detalhe and detalhe not in detalhes:
            detalhes.append(detalhe)
    for arquivo, criterios in arquivos.items():
        yield f"  {arquivo}"
        for (criterio, cura), por_linha in criterios.items():
            yield f"    {criterio} — cura: {cura}"
            por_detalhe: dict[str, list[int]] = {}
            for ln in sorted(por_linha):
                por_detalhe.setdefault(" · ".join(por_linha[ln]), []).append(ln)
            for detalhe, linhas in por_detalhe.items():
                numeros = ", ".join(str(ln) for ln in linhas)
                yield f"      {numeros}: {detalhe}" if detalhe else f"      {numeros}"
