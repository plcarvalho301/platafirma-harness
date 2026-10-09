"""`motor rag parear biblioteca` — o par mínimo da consulta montada (card #3360, passo 9; spec motor §2b).

Sobre as perguntas do piloto da escada, três formas de consultar o motor, com a MESMA geração, o MESMO k e o
embedder fixo (só muda o texto que chega a ele):

  A  `servido`  a chamada de hoje, como a cadeira a fez e o log guardou (avaliacao/escada-sentido-v1.jsonl)
  C  `frase`    a frase que o DONO escreveu para aquela necessidade (a cadeira não a redige: seria a inferência
                que o par mede)
  D  `montada`  a lista que `motor buscar` monta a partir da frase: a frase e a frase com os rótulos do chapéu
                (sem o pedido, porque as chamadas do piloto são anteriores ao #3345 e não o gravaram)

Cada braço vira uma resposta, escrita pelo mesmo modelo, prompt e semente do escritor da escada, e o escritor
vê a FRASE como pergunta nos três: assim o que difere entre as respostas é só o que foi recuperado. O dono
julga as respostas na mesma tela, com o mesmo critério (v1). Ao lado, o que ele já julgou do piloto, para não
depender da memória.

Com `--do-log` (card #3378) a população não é o piloto: são as chamadas do log com eleito, e os braços são dois, na mesma
geração e com o mesmo escritor:

  C  `frase`   a busca de hoje: a necessidade do evento, sem chapéu
  E  `eleito`  a mesma necessidade com o chapéu do evento e `eleicao_chapeu: true` no corpo, só na requisição

Só a lógica mora aqui; a busca, o ollama e o contêiner entram por `bin/motor`.
"""
from __future__ import annotations

import json
import random
import re
import secrets

import consulta
import escritor

BRACOS_DO_PAR = ("servido", "frase", "montada")
LETRA = {"servido": "A", "frase": "C", "montada": "D", "eleito": "E"}
NOME = {"servido": "a chamada de hoje", "frase": "a sua frase", "montada": "a lista montada"}

# `parear --do-log` (card #3378): a população são as chamadas do log com eleito; dois braços, mesma geração, mesmo k e
# mesmo escritor. C é a busca de hoje (a necessidade, sem chapéu); E é a mesma necessidade com o chapéu e
# `eleicao_chapeu: true` no corpo, só na requisição.
BRACOS_DO_LOG = ("frase", "eleito")
NOME_LOG = {"frase": "a busca de hoje (a necessidade, sem chapéu)", "eleito": "a busca com o eleito do chapéu"}


# --- entrada: as frases do dono ------------------------------------------------------------------------

def ler_frases(texto: str, ids_do_piloto) -> dict:
    """{pergunta_id: {"frase", "chapeu", "cadeira"}}. O arquivo é um objeto JSON: a chave é o id da pergunta do
    piloto; o valor, a frase (string) ou {"frase", "chapeu"?, "cadeira"?}. ValueError diz o que está errado."""
    try:
        bruto = json.loads(texto)
    except ValueError as e:
        raise ValueError(f"o arquivo de frases não é JSON ({e})") from None
    if not isinstance(bruto, dict) or not bruto:
        raise ValueError("o arquivo de frases é um objeto JSON {pergunta_id: frase}, com ao menos uma")
    ids = set(ids_do_piloto)
    fora = sorted(k for k in bruto if k not in ids)
    if fora:
        raise ValueError(f"pergunta(s) que não são do piloto: {', '.join(fora)}")
    out = {}
    for pid, v in bruto.items():
        item = {"frase": v} if isinstance(v, str) else v
        if not isinstance(item, dict) or not isinstance(item.get("frase"), str) or not item["frase"].strip():
            raise ValueError(f"{pid}: falta a frase")
        for campo in ("chapeu", "cadeira"):
            if item.get(campo) is not None and not isinstance(item[campo], str):
                raise ValueError(f"{pid}: {campo} é texto")
        out[pid] = {"frase": " ".join(item["frase"].split()), "chapeu": (item.get("chapeu") or "").strip() or None,
                    "cadeira": (item.get("cadeira") or "").strip() or None}
        if out[pid]["chapeu"] and not out[pid]["cadeira"]:
            raise ValueError(f"{pid}: o chapeu {out[pid]['chapeu']!r} vem com a cadeira (rotas-chapeu.json e cadeira → chapeu)")
    return out


# --- as três consultas ---------------------------------------------------------------------------------

def consultas(pergunta_do_log: str, frase: str, rotulos) -> dict:
    """{braco: consulta enviada à API}. A lista de D só entra quando difere da frase sozinha: sem chapéu (sem
    rótulos) a lista montada é a própria frase, e D seria C com outro nome."""
    out = {"servido": pergunta_do_log, "frase": frase}
    lista = getattr(consulta, "montar_com_rotulos", consulta.montar)(frase, rotulos)
    if lista != [frase]:
        out["montada"] = lista
    return out


def jaccard_dos_bracos(recuperado: dict) -> dict:
    """Jaccard do top-8 de C e de D contra A (as chaves são o uuid da seção)."""
    a = recuperado.get("servido") or []
    return {LETRA[b] + "xA": round(escritor.jaccard(recuperado[b], a), 3)
            for b in ("frase", "montada") if b in recuperado}


def consultas_do_log(necessidade: str, cadeira: str, chapeu: str, rotulos) -> dict:
    """{braco: {"pergunta", "corpo"}} do `parear --do-log` (card #3378). `pergunta` é a necessidade do evento nos dois
    braços; `corpo` é o que se soma ao corpo da requisição. O braço `frase` não manda `chapeu` nem `eleicao_chapeu` (a busca
    de hoje); o `eleito` manda o chapéu {cadeira, chapeu, rotulos} e `eleicao_chapeu: true`, só nesta requisição."""
    return {"frase": {"pergunta": necessidade, "corpo": {}},
            "eleito": {"pergunta": necessidade,
                       "corpo": {"chapeu": {"cadeira": cadeira, "chapeu": chapeu, "rotulos": list(rotulos)},
                                 "eleicao_chapeu": True}}}


def jaccard_eleito(recuperado: dict) -> dict:
    """Jaccard do top-8 do eleito (E) contra a busca de hoje (C); {} se falta um dos dois braços."""
    if "eleito" in recuperado and "frase" in recuperado:
        return {"ExC": round(escritor.jaccard(recuperado["eleito"], recuperado["frase"]), 3)}
    return {}


# --- o que o dono já julgou ----------------------------------------------------------------------------

def julgamentos_anteriores(lote: dict, eventos: list) -> dict:
    """Do lote anterior (`lote ler <id> --com-braco`) e dos eventos da tela: por pergunta, a qualidade e o
    embasamento que o dono deu à resposta de cada braço, e qual ele preferiu (1, 2, 3 é a ordem em que a tela
    mostrou as respostas). Vale o ÚLTIMO evento de cada resposta e de cada pergunta (o dono revisou).
    Pergunta excluída aparece como {"excluida": motivo}."""
    braco_da = {r["resposta_id"]: r["braco"] for r in lote.get("respostas") or []}
    ordem = {p["pergunta_id"]: [r["resposta_id"] for r in p.get("respostas") or []]
             for p in (lote.get("corpo") or {}).get("perguntas") or []}
    pergunta_da = {r["resposta_id"]: r["pergunta_id"] for r in lote.get("respostas") or []}
    out: dict = {}
    for e in sorted(eventos, key=lambda x: x.get("id", 0)):
        tipo = e.get("tipo")
        if tipo == "marca" and e.get("resposta_id") in braco_da:
            pid = pergunta_da[e["resposta_id"]]
            out.setdefault(pid, {}).setdefault("marcas", {})[braco_da[e["resposta_id"]]] = {
                "qualidade": e.get("qualidade"), "embasamento": e.get("embasamento")}
        elif tipo == "preferencia":
            pid = e.get("pergunta_id")
            escolha = e.get("escolha")
            if escolha in ("1", "2", "3") and int(escolha) <= len(ordem.get(pid, [])):
                preferiu = braco_da.get(ordem[pid][int(escolha) - 1])
            else:
                preferiu = escolha        # «empate», ou a ordem não se resolveu
            out.setdefault(pid, {})["preferiu"] = preferiu
        elif tipo == "exclusao":
            out[e.get("pergunta_id")] = {"excluida": e.get("motivo")}
    return out


def resumo_do_julgamento(j: dict | None) -> str:
    if not j:
        return "sem julgamento anterior"
    if "excluida" in j:
        return f"excluída por você ({j['excluida']})"
    marcas = ", ".join(f"{LETRA.get(b, b)}={m['qualidade']}{'' if m['embasamento'] else ' sem embasamento'}"
                       for b, m in sorted((j.get("marcas") or {}).items()))
    pref = j.get("preferiu")
    pref = LETRA.get(pref, pref)
    return f"{marcas or 'sem marca'}" + (f"; preferiu {pref}" if pref else "")


# --- o lote que o dono julga ---------------------------------------------------------------------------

def montar_lote_par(lote_id: str, versao_id: str, criterio_versao: str, perguntas: list, resultados: dict,
                    carimbo: dict, semente: str, ativo: bool) -> dict:
    """O envelope que `motor marcacao lote gravar` manda, com os braços do par. `perguntas`: [{id, frase, cadeira,
    data}]; `resultados[pid][braco]` = saída de escritor.escrever_resposta. O texto da pergunta que a tela mostra é
    a frase do dono. As respostas se embaralham dentro da pergunta e o resposta_id é opaco."""
    corpo_p, internas = [], []
    for p in perguntas:
        pid = p["id"]
        rodando = list(resultados[pid].items())
        random.Random(f"{semente}/{pid}").shuffle(rodando)
        respostas = []
        for braco, r in rodando:
            rid = "re-" + secrets.token_hex(6)
            respostas.append({"resposta_id": rid, "texto": r["resposta"],
                              "secoes": [{"chave": s["chave"], "titulo": s["titulo"]} for s in r["rodape"]]})
            internas.append({"resposta_id": rid, "pergunta_id": pid, "braco": braco,
                             "secoes": [{"chave": s["chave"], "titulo": s["titulo"], "secao_id": s.get("secao_id")}
                                        for s in r["rodape"]],
                             "mapa": r["mapa"],
                             "carimbo": {**r["carimbo"], "palavras": r["palavras"], "rodape_de_consulta": r["de_consulta"]}})
        corpo_p.append({"pergunta_id": pid, "texto": p["frase"], "cadeira": p["cadeira"], "data": p["data"],
                        "respostas": respostas})
    corpo = {"lote_id": lote_id, "criterio_versao": criterio_versao, "passada": "primeira", "perguntas": corpo_p}
    return {"lote_id": lote_id, "gabarito_versao_id": versao_id, "criterio_versao": criterio_versao,
            "passada": "primeira", "ativo": ativo, "corpo": corpo, "carimbo": carimbo, "respostas": internas}


def conferir_aceite_par(envelope: dict, n_perguntas: int) -> list:
    """Os problemas do lote do par: [] = conforme. Cada pergunta tem duas ou três respostas (D some quando não há
    rótulos), nenhuma igual à outra, todas com seção no rodapé e sem marca [n] no meio do texto."""
    p = []
    perguntas = envelope["corpo"]["perguntas"]
    if len(perguntas) != n_perguntas:
        p.append(f"{len(perguntas)} perguntas, esperava {n_perguntas}")
    for q in perguntas:
        textos = [r["texto"] for r in q["respostas"]]
        if not 2 <= len(textos) <= 3:
            p.append(f"{q['pergunta_id']}: {len(textos)} respostas, esperava 2 ou 3")
        if len(set(textos)) < len(textos):
            p.append(f"{q['pergunta_id']}: duas respostas de texto idêntico")
        for r in q["respostas"]:
            if not r["secoes"]:
                p.append(f"{q['pergunta_id']}: resposta sem seção no rodapé")
            if re.search(r"\[\d+\]", r["texto"]):
                p.append(f"{q['pergunta_id']}: marca [n] no meio do texto")
    for chave in ("acervo", "motor", "vocabulario", "gabarito", "escritor", "par"):
        if not envelope["carimbo"].get(chave):
            p.append(f"carimbo sem a versão «{chave}»")
    return p


# --- o que o dono lê -----------------------------------------------------------------------------------

def linha_da_tabela(i: int, pid: str, frase: str, jacc: dict, tem_montada: bool, j: dict | None) -> str:
    cxa = jacc.get("CxA", "-")
    dxa = jacc.get("DxA", "-") if tem_montada else "= C (sem chapéu)"
    return f"| {i} | {pid[4:]} | {frase[:60]} | {cxa} | {dxa} | {resumo_do_julgamento(j)} |"


def tabela(linhas: list) -> str:
    return "\n".join(["| # | pergunta | sua frase | Jaccard C×A | Jaccard D×A | o que você julgou antes |",
                      "|---|---|---|---|---|---|", *linhas])


def blocos_markdown(itens: list) -> str:
    """Um bloco por pergunta: a chamada de hoje, a frase, o julgamento anterior e os títulos do top-8 de cada
    braço. `itens`: [{id, pergunta_do_log, frase, recuperado, jaccard, julgamento}]."""
    out = []
    for i, it in enumerate(itens, 1):
        out += [f"### {i}. {it['frase']}", "", f"- chamada de hoje (A): `{it['pergunta_do_log'][:140]}`",
                f"- você julgou antes: {resumo_do_julgamento(it.get('julgamento'))}",
                "- Jaccard do top-8 contra A: " + (", ".join(f"{k} {v}" for k, v in it["jaccard"].items()) or "-"), ""]
        for b in BRACOS_DO_PAR:
            if b in it["recuperado"]:
                out.append(f"**{LETRA[b]} — {NOME[b]}**")
                out += [f"{n}. {s['titulo'][:110]}" for n, s in enumerate(it["recuperado"][b], 1)] or ["(nenhuma seção)"]
                out.append("")
    return "\n".join(out)


# --- o que o dono lê, sobre as chamadas do log (card #3378) ---------------------------------------------------

def linha_da_tabela_log(i: int, pid: str, necessidade: str, cadeira: str, chapeu: str, jacc: dict) -> str:
    return f"| {i} | {pid} | {necessidade[:60]} | {cadeira}/{chapeu} | {jacc.get('ExC', '-')} |"


def tabela_log(linhas: list) -> str:
    return "\n".join(["| # | evento | necessidade | cadeira/chapéu | Jaccard E×C |", "|---|---|---|---|---|", *linhas])


def blocos_markdown_log(itens: list) -> str:
    """Um bloco por chamada do log: a necessidade, o evento, o Jaccard do top-8 E×C e os títulos de cada braço.
    `itens`: [{id, frase, cadeira, chapeu, recuperado, jaccard}]."""
    out = []
    for i, it in enumerate(itens, 1):
        out += [f"### {i}. {it['frase']}", "", f"- evento do log: `{it['id']}` · {it['cadeira']}/{it['chapeu']}",
                "- Jaccard do top-8, E contra C: " + (", ".join(f"{k} {v}" for k, v in it["jaccard"].items()) or "-"), ""]
        for b in BRACOS_DO_LOG:
            if b in it["recuperado"]:
                out.append(f"**{LETRA[b]} — {NOME_LOG[b]}**")
                out += [f"{n}. {s['titulo'][:110]}" for n, s in enumerate(it["recuperado"][b], 1)] or ["(nenhuma seção)"]
                out.append("")
    return "\n".join(out)
