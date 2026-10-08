"""`motor rag escrever biblioteca` — o escritor da escada (card #3349, feature #3340).

Fonte: padrao protocolo-medicao-rag rev 2, «Unidade da marca: a resposta». Para cada pergunta do piloto,
o top-8 de cada braço (o servido; o léxico puro; o terceiro, que no piloto é o servido com revisor) vira
uma resposta, escrita pelo MESMO modelo, o MESMO prompt e a MESMA semente nos três braços. Embaixo de cada
resposta, as seções que ela usou, como rodapé, sem marca no meio do texto; o mapa afirmação→seção fica à
parte e vai ao juiz, nunca à tela. As respostas se embaralham dentro da pergunta e o resposta_id é opaco.

Este módulo é a lógica; as chamadas (busca, contêiner do rag, ollama) entram por funções passadas por
quem chama, para a lógica se medir sem rede.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import time

MODELO = "qwen3.5:9b"
PROMPT_VERSAO = "escritor-v1"
SEMENTE_GERACAO = 42
TEMPERATURA = 0
PALAVRAS = 350
K = 8
CHARS_POR_SECAO = 1800
TENTATIVAS = 3
BRACOS = ("servido", "lexico", "revisor")
SEM_SECOES = "O acervo não devolveu nenhuma seção para esta pergunta."

SISTEMA = """Você responde a uma pergunta de trabalho usando SOMENTE as seções numeradas que vêm abaixo.

Regras:
1. Escreva em português do Brasil, em prosa corrida, em até 350 palavras. Não ponha marca de referência no texto: nada de [1], (3), notas ou links.
2. Cada afirmação material da resposta tem de estar sustentada por pelo menos uma das seções. Se as seções não respondem à pergunta, ou respondem só em parte, diga isso com clareza e diga o que falta. Não complete com conhecimento próprio.
3. Devolva apenas um objeto JSON, sem texto fora dele: {"resposta": "<o texto>", "mapa": [{"afirmacao": "<a afirmação material, numa frase>", "secoes": [<números das seções que a sustentam>]}]}
4. Toda afirmação material do texto aparece uma vez no mapa, com ao menos um número de seção da lista. Se a resposta só diz que as seções não cobrem a pergunta, o mapa é uma lista vazia."""


def prompt_sha256() -> str:
    return hashlib.sha256((PROMPT_VERSAO + "\n" + SISTEMA).encode()).hexdigest()


def titulo_da_fonte(f: dict) -> str:
    """Obra › trilha da seção. A trilha do /search já começa no primeiro título da obra, não no nome dela."""
    obra = (f.get("obra") or "").strip()
    trilha = [x for x in (f.get("breadcrumb") or []) if x]
    return f"{obra} › {' › '.join(trilha)}" if trilha else obra


def blocos_do_contexto(contexto: str) -> dict:
    """n -> texto da seção, do campo `contexto` do /search: blocos `[n] (arquivo · section_id) — trilha` separados
    por linha em branco. `fontes[].texto` vem nulo mesmo com texto='secao': o texto mora aqui. O cabeçalho do
    bloco sai (a trilha já está no título); fica o contexto do pai e o corpo da seção."""
    out = {}
    for parte in re.split(r"\n\n(?=\[\d+\] \()", contexto or ""):
        m = re.match(r"\[(\d+)\] \(", parte)
        if m:
            out[int(m.group(1))] = parte.split("\n", 1)[1].strip() if "\n" in parte else ""
    return out


def secoes_do_servido(resposta: dict, k: int = K) -> list:
    """As seções que o /search devolveu (texto='secao'), na ordem do braço. A chave é o uuid da seção
    (o `section_id` curto repete entre obras); o `section_id` e o arquivo ficam para quem resolver o alvo."""
    blocos = blocos_do_contexto(resposta.get("contexto"))
    out, vistas = [], set()
    for f in resposta.get("fontes") or []:
        chave = f.get("secao_id")
        texto = (f.get("texto") or blocos.get(f.get("n")) or "").strip()
        if not chave or chave in vistas or not texto:
            continue
        vistas.add(chave)
        out.append({"chave": chave, "titulo": titulo_da_fonte(f), "texto": texto, "secao_id": chave,
                    "section_id": f.get("section_id"), "arquivo": f.get("arquivo")})
        if len(out) == k:
            break
    return out


def jaccard(a: list, b: list) -> float:
    ca, cb = {s["chave"] for s in a}, {s["chave"] for s in b}
    return len(ca & cb) / max(len(ca | cb), 1)


def montar_mensagens(pergunta: str, secoes: list) -> list:
    corpo = [f"Pergunta: {pergunta}", "", "Seções:"]
    for i, s in enumerate(secoes, 1):
        texto = s["texto"]
        if len(texto) > CHARS_POR_SECAO:
            texto = texto[:CHARS_POR_SECAO].rsplit(" ", 1)[0] + " […]"
        corpo += [f"[{i}] {s['titulo']}", texto, ""]
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": "\n".join(corpo).strip()}]


def _json_da_saida(texto: str):
    texto = re.sub(r"<think>.*?</think>", "", texto or "", flags=re.S).strip()
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


def interpretar(saida: str, secoes: list):
    """(resposta, mapa, avisos, palavras) ou None quando a saída não é uma resposta. O mapa só guarda afirmação com
    seção da lista; o que não cumpre sai e fica contado em `avisos`."""
    obj = _json_da_saida(saida)
    if not isinstance(obj, dict) or not isinstance(obj.get("resposta"), str) or not obj["resposta"].strip():
        return None
    avisos = []
    texto = obj["resposta"].strip()
    limpo = re.sub(r"\s*\[\d+(?:\s*[,;]\s*\d+)*\]", "", texto)
    if limpo != texto:
        avisos.append("marcas [n] removidas do texto")
        texto = limpo
    palavras = len(texto.split())
    if palavras > int(PALAVRAS * 1.15):
        avisos.append(f"{palavras} palavras, acima do teto de {PALAVRAS}")
    mapa, descartadas = [], 0
    for item in obj.get("mapa") if isinstance(obj.get("mapa"), list) else []:
        nums = item.get("secoes") if isinstance(item, dict) else None
        afirm = (item.get("afirmacao") or "").strip() if isinstance(item, dict) and isinstance(item.get("afirmacao"), str) else ""
        ok = [n for n in nums if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(secoes)] if isinstance(nums, list) else []
        if afirm and ok:
            mapa.append({"afirmacao": afirm, "secoes": [secoes[n - 1]["chave"] for n in sorted(set(ok))]})
        else:
            descartadas += 1
    if descartadas:
        avisos.append(f"{descartadas} afirmação(ões) do mapa sem seção válida, descartada(s)")
    return texto, mapa, avisos, palavras


def rodape(mapa: list, secoes: list) -> tuple:
    """(secoes do rodapé, de_consulta). O rodapé lista as seções que o mapa usa; resposta que só diz que o
    acervo não cobre tem mapa vazio, e o rodapé lista as três primeiras consultadas (de_consulta=True)."""
    usadas = {c for m in mapa for c in m["secoes"]}
    lista = [s for s in secoes if s["chave"] in usadas]
    if lista:
        return lista, False
    return secoes[:3], True


def escrever_resposta(pergunta: str, secoes: list, gerar) -> dict:
    """Uma resposta de um braço. `gerar(mensagens, tentativa)` -> {'texto', 'tokens_prompt', 'tokens_saida', 'segundos'}.
    A mesma regra de nova tentativa vale para os três braços: saída que não é resposta pede outra, até TENTATIVAS."""
    if not secoes:
        return {"resposta": SEM_SECOES, "mapa": [], "rodape": [], "de_consulta": False, "palavras": len(SEM_SECOES.split()),
                "carimbo": {"tentativas": 0, "segundos": 0.0, "tokens_prompt": 0, "tokens_saida": 0,
                            "avisos": ["braço sem nenhuma seção; resposta fixa, sem modelo"]}}
    mensagens = montar_mensagens(pergunta, secoes)
    total = {"segundos": 0.0, "tokens_prompt": 0, "tokens_saida": 0}
    for tentativa in range(TENTATIVAS):
        g = gerar(mensagens, tentativa)
        for k in total:
            total[k] += g.get(k, 0)
        r = interpretar(g["texto"], secoes)
        if r is None:
            continue
        texto, mapa, avisos, palavras = r
        foot, de_consulta = rodape(mapa, secoes)
        if de_consulta:
            avisos.append("mapa vazio: rodapé lista as três primeiras seções consultadas")
        return {"resposta": texto, "mapa": mapa, "rodape": foot, "de_consulta": de_consulta, "palavras": palavras,
                "carimbo": {"tentativas": tentativa + 1, **{k: round(v, 2) if k == "segundos" else v for k, v in total.items()},
                            "avisos": avisos}}
    raise RuntimeError(f"o modelo não devolveu uma resposta em {TENTATIVAS} tentativas")


def escolher_piloto(linhas: list, recusadas: set, n: int = 20) -> list:
    """As n primeiras do piloto, sem as recusadas; cada recusada é reposta pela primeira da reserva, em ordem."""
    piloto = [l for l in linhas if l["papel"] == "piloto"]
    reserva = [l for l in linhas if l["papel"] == "reserva"]
    ficam = [l for l in piloto if l["id"] not in recusadas]
    for l in reserva:
        if len(ficam) >= n:
            break
        if l["id"] not in recusadas:
            ficam.append(l)
    return ficam[:n]


def decidir_terceiro_braco(amostras: list) -> tuple:
    """`amostras`: [(secoes_servido, secoes_revisor, rerank_ms)]. Premissa do card: se o revisor não mudar o top-8
    em nenhuma das perguntas testadas (Jaccard 1 e rerank 0 ms), o terceiro braço passa a ser a expansão."""
    if amostras and all(jaccard(a, b) == 1.0 and ms == 0 for a, b, ms in amostras):
        return "expansao", f"o revisor não mudou o top-8 em {len(amostras)} pergunta(s) (Jaccard 1, rerank 0 ms)"
    return "revisor", "o revisor mudou o top-8 em ao menos uma pergunta testada"


def montar_lote(lote_id: str, versao_id: str, criterio_versao: str, perguntas: list, resultados: dict,
                terceiro: str, carimbo: dict, semente: str, ativo: bool) -> dict:
    """O envelope que `motor marcacao lote gravar` manda: corpo público (sem braço nem mapa) + respostas internas.
    `perguntas`: linhas do piloto na ordem; `resultados[pergunta_id][braco]` = saída de escrever_resposta."""
    corpo_p, internas = [], []
    for p in perguntas:
        pid = p["id"]
        rodando = [("servido", resultados[pid]["servido"]), ("lexico", resultados[pid]["lexico"]),
                   (terceiro, resultados[pid]["terceiro"])]
        random.Random(f"{semente}/{pid}").shuffle(rodando)
        respostas = []
        for braco, r in rodando:
            rid = "re-" + secrets.token_hex(6)
            respostas.append({"resposta_id": rid, "texto": r["resposta"],
                              "secoes": [{"chave": s["chave"], "titulo": s["titulo"]} for s in r["rodape"]]})
            internas.append({"resposta_id": rid, "pergunta_id": pid, "braco": braco,
                             "secoes": [{"chave": s["chave"], "titulo": s["titulo"], "secao_id": s.get("secao_id")} for s in r["rodape"]],
                             "mapa": r["mapa"],
                             "carimbo": {**r["carimbo"], "palavras": r["palavras"], "rodape_de_consulta": r["de_consulta"]}})
        corpo_p.append({"pergunta_id": pid, "texto": p["pergunta"], "cadeira": p["cadeira"], "data": p["data"],
                        "respostas": respostas})
    corpo = {"lote_id": lote_id, "criterio_versao": criterio_versao, "passada": "primeira", "perguntas": corpo_p}
    return {"lote_id": lote_id, "gabarito_versao_id": versao_id, "criterio_versao": criterio_versao, "passada": "primeira",
            "ativo": ativo, "corpo": corpo, "carimbo": carimbo, "respostas": internas}


def conferir_aceite(envelope: dict, n_perguntas: int) -> list:
    """Os problemas do lote contra o aceite do card: [] = conforme."""
    p = []
    internas = envelope["respostas"]
    if len(envelope["corpo"]["perguntas"]) != n_perguntas:
        p.append(f"{len(envelope['corpo']['perguntas'])} perguntas, esperava {n_perguntas}")
    if len(internas) != 3 * n_perguntas:
        p.append(f"{len(internas)} respostas, esperava {3 * n_perguntas}")
    sem_rodape = [r["resposta_id"] for q in envelope["corpo"]["perguntas"] for r in q["respostas"] if not r["secoes"]]
    if sem_rodape:
        p.append(f"{len(sem_rodape)} resposta(s) sem seção no rodapé")
    sem_secao = sum(1 for r in internas for m in r["mapa"] if not m["secoes"])
    if sem_secao:
        p.append(f"{sem_secao} afirmação(ões) sem seção no mapa")
    for chave in ("acervo", "motor", "vocabulario", "gabarito", "escritor"):
        if not envelope["carimbo"].get(chave):
            p.append(f"carimbo sem a versão «{chave}»")
    marcas = [r["resposta_id"] for q in envelope["corpo"]["perguntas"] for r in q["respostas"] if re.search(r"\[\d+\]", r["texto"])]
    if marcas:
        p.append(f"{len(marcas)} resposta(s) com marca [n] no meio do texto")
    return p


def novo_estado(lote_id: str, ids: list, terceiro: str, motivo: str) -> dict:
    return {"lote_id": lote_id, "perguntas": ids, "terceiro_braco": terceiro, "terceiro_motivo": motivo,
            "recuperado": {}, "geradas": {}, "iniciado_em": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
