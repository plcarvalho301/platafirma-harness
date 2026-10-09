"""`motor rag julgar` — o juiz do piloto da escada (card #3350, feature #3340).

Fonte: padrao protocolo-medicao-rag rev 2, «O juiz» 1 a 3 e «Unidade da marca». O juiz é um modelo de
outra família que o escritor (o escritor é qwen; o juiz é Claude, pelo gerador do motor). Ele marca as
mesmas respostas que o dono marcou, sem ver as marcas dele, pelo MESMO critério que a tela mostrou ao
dono (criterio.json servido pela platafirma-ui): grau por resposta, embasamento afirmação por afirmação
e um grau por trecho.

Este módulo é a lógica; a chamada ao modelo entra por função passada por quem chama, para a lógica se
medir sem rede. O prompt sai de juiz_prompt.md com o critério dentro; o hash cobre os dois, e prompt
diferente é outra marca (avaliacao.juiz_marca, UNIQUE por resposta, modelo e hash).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

PROMPT_VERSAO = "juiz-v1"
TENTATIVAS = 3
CHARS_POR_SECAO = 4000
GRAUS_TRECHO = ("responde", "tangencia", "nao")
_PROMPT = Path(__file__).with_name("juiz_prompt.md")


def graus_do_criterio(criterio: dict) -> tuple:
    return tuple(g["id"] for g in criterio["graus"])


def sistema(criterio: dict, modelo_prompt: str | None = None) -> str:
    """O prompt do juiz com o critério que o dono viu, grau a grau, com o exemplo."""
    base = modelo_prompt if modelo_prompt is not None else _PROMPT.read_text(encoding="utf-8")
    graus = "\n".join(f"- {g['id']}: {g['definicao']} Exemplo: {g['exemplo']}" for g in criterio["graus"])
    return (base.replace("{CRITERIO_VERSAO}", str(criterio["criterio_versao"]))
                .replace("{GRAUS}", graus)
                .replace("{DESEMPATE}", criterio.get("desempate", "")))


def prompt_hash(texto_sistema: str) -> str:
    return hashlib.sha256((PROMPT_VERSAO + "\n" + texto_sistema).encode()).hexdigest()


def montar_mensagem(pergunta: str, resposta: str, secoes: list, mapa: list) -> str:
    """`secoes`: [{chave, titulo, texto}] na ordem do rodapé; `mapa`: [{afirmacao, secoes: [chave]}].
    O mapa vai numerado e com o número da seção, não com a chave (a chave não diz nada ao juiz)."""
    num = {s["chave"]: i for i, s in enumerate(secoes, 1)}
    linhas = [f"Pergunta da cadeira: {pergunta}", "", "Resposta:", resposta.strip(), "", "Mapa (afirmação → seções):"]
    if mapa:
        for i, m in enumerate(mapa, 1):
            ns = [str(num[c]) for c in m.get("secoes", []) if c in num]
            linhas.append(f"{i}. {m['afirmacao']} → seções {', '.join(ns) or 'nenhuma da lista'}")
    else:
        linhas.append("(vazio: o escritor não fez afirmação material)")
    linhas += ["", "Seções:"]
    for i, s in enumerate(secoes, 1):
        texto = (s.get("texto") or "").strip() or "(texto da seção não encontrado no acervo)"
        if len(texto) > CHARS_POR_SECAO:
            texto = texto[:CHARS_POR_SECAO].rsplit(" ", 1)[0] + " […]"
        linhas += [f"[{i}] {s['titulo']}", texto, ""]
    return "\n".join(linhas).strip()


def _json_da_saida(texto: str):
    texto = re.sub(r"^```(?:json)?|```$", "", (texto or "").strip(), flags=re.M).strip()
    try:
        return json.loads(texto)
    except ValueError:
        m = re.search(r"\{.*\}", texto, flags=re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None


def interpretar(saida: str, graus: tuple, n_afirmacoes: int, n_secoes: int):
    """O julgamento validado, ou None quando a saída não cumpre o esquema (pede outra tentativa).
    Afirmação ou seção fora da numeração recusa; faltar alguma recusa também: o juiz julga todas."""
    obj = _json_da_saida(saida)
    if not isinstance(obj, dict) or obj.get("qualidade") not in graus or not isinstance(obj.get("embasamento"), bool):
        return None
    pa, pt = obj.get("por_afirmacao"), obj.get("por_trecho")
    if not isinstance(pa, list) or not isinstance(pt, list):
        return None
    afirm = {}
    for x in pa:
        if (not isinstance(x, dict) or not isinstance(x.get("afirmacao"), int) or isinstance(x.get("afirmacao"), bool)
                or not 1 <= x["afirmacao"] <= n_afirmacoes or not isinstance(x.get("sustentada"), bool)):
            return None
        afirm[x["afirmacao"]] = {"afirmacao": x["afirmacao"], "sustentada": x["sustentada"],
                                 "motivo": str(x.get("motivo") or "")[:400]}
    trecho = {}
    for x in pt:
        if (not isinstance(x, dict) or not isinstance(x.get("secao"), int) or isinstance(x.get("secao"), bool)
                or not 1 <= x["secao"] <= n_secoes or x.get("grau") not in GRAUS_TRECHO):
            return None
        trecho[x["secao"]] = {"secao": x["secao"], "grau": x["grau"]}
    if len(afirm) != n_afirmacoes or len(trecho) != n_secoes:
        return None
    return {"qualidade": obj["qualidade"], "embasamento": obj["embasamento"],
            "por_afirmacao": [afirm[i] for i in sorted(afirm)], "por_trecho": [trecho[i] for i in sorted(trecho)],
            "motivo": str(obj.get("motivo") or "")[:600]}


def julgar_resposta(texto_sistema: str, graus: tuple, pergunta: str, resposta: str, secoes: list, mapa: list,
                    gerar) -> dict:
    """Um julgamento. `gerar(sistema, usuario, tentativa)` -> {'texto', 'segundos'}. Saída fora do esquema pede
    outra, até TENTATIVAS; depois disso levanta, e quem chama decide (a resposta fica pendente, não inventada)."""
    usuario = montar_mensagem(pergunta, resposta, secoes, mapa)
    segundos = 0.0
    for tentativa in range(TENTATIVAS):
        g = gerar(texto_sistema, usuario, tentativa)
        segundos += g.get("segundos", 0.0)
        j = interpretar(g["texto"], graus, len(mapa), len(secoes))
        if j is not None:
            j["por_trecho"] = [{**t, "chave": secoes[t["secao"] - 1]["chave"]} for t in j["por_trecho"]]
            j["carimbo"] = {"tentativas": tentativa + 1, "segundos": round(segundos, 2), "chars_entrada": len(usuario)}
            return j
    raise RuntimeError(f"o juiz não devolveu um julgamento no esquema em {TENTATIVAS} tentativas")


def marcas_para_gravar(lote_id: str, julgados: dict, modelo: str, hash_prompt: str) -> dict:
    """O corpo de `motor marcacao juiz gravar`: `julgados[resposta_id]` = saída de julgar_resposta. O motivo do grau
    e o carimbo não têm coluna na 014: ficam no estado em arquivo do ato."""
    return {"lote_id": lote_id, "marcas": [
        {"resposta_id": rid, "qualidade": j["qualidade"], "embasamento": j["embasamento"],
         "por_afirmacao": j["por_afirmacao"], "por_trecho": j["por_trecho"], "modelo": modelo, "prompt_hash": hash_prompt}
        for rid, j in sorted(julgados.items())]}
