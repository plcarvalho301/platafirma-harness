"""Contrato de consulta e retorno do verbo motor (DTs 537, 538 e 552)."""
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from recuperacao.roteador_chapeu import _normaliza


def resolver_conceitos(valores: list[str], itens: list[dict]) -> tuple[list[str], list[str]]:
    """Slug exato tem precedência; rótulo ambíguo nunca escolhe pelo primeiro."""
    slugs = {c["slug"] for c in itens}
    indice = {}
    for c in itens:
        outros = c.get("outros_rotulos") or []
        if isinstance(outros, str):
            outros = re.split(r"[/,]", outros)
        for nome in [c["slug"], c.get("rotulo", ""), *outros]:
            chave = _normaliza(nome)
            if chave:
                indice.setdefault(chave, set()).add(c["slug"])
    resolvidos, avisos = [], []
    for valor in valores:
        candidatos = {valor} if valor in slugs else indice.get(_normaliza(valor), set())
        if len(candidatos) == 1:
            slug = next(iter(candidatos))
            if slug not in resolvidos:
                resolvidos.append(slug)
        elif candidatos:
            avisos.append(f"conceito {valor!r} ambiguo: {', '.join(sorted(candidatos))}; informe o slug")
        else:
            avisos.append(f"conceito {valor!r} nao reconhecido no catalogo; a busca seguiu sem ele")
    return resolvidos, avisos


def completar(resp: dict, particao: str, texto: str, avisos: list[str] | tuple = ()) -> dict:
    """Acrescenta informação sem alterar ranking, cobertura ou texto recuperado."""
    resp["texto_solicitado"] = texto
    if texto == "nenhum":
        resp["aviso_texto"] = "texto nao solicitado; use --texto trecho ou --texto secao"
    if avisos:
        resp["avisos_conceitos"] = list(avisos)
    if particao in ("biblioteca", "casa"):
        for fonte in resp.get("fontes") or []:
            sid = fonte.get("secao_id")
            if isinstance(sid, str) and re.fullmatch(
                    r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", sid):
                fonte["ler"] = shlex.join(["acervo", "ler", particao, "secao", sid])
    return resp
