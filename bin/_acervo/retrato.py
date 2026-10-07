"""retrato — `acervo listar biblioteca obra --situacao --retrato [--guardar] [--json]` (#3324, arq:0121 §9).

O retrato da biblioteca, com data: cabeçalho fixo (base, data, geração servindo, papéis da base), uma
linha por obra do catálogo e um rodapé que soma cada entidade por estado e fecha com `count(*)` de
`acervo.obra`. A linha que não fecha sai escrita (§9.3). Não é verbo novo: é o ato `--situacao`
(arq:0110 um verbo por folha; arq:0106).

De onde vem cada coluna:
  - catálogo (rag): obra, situação, exposição, impressão servindo (id, método, qualidade do espelho);
  - motor, pela projeção REST /acervo/obras (arq:0121 §12.2): geração, embedder e dimensão do índice
    servindo e a cobertura (trechos com vetor sobre trechos elegíveis). O harness não lê motor.vetor
    linha a linha (arq:0045, Morada): a contagem é agregada no banco pela projeção;
  - invariantes violados: as funções `i1`…`i13` de bin/_release/conferir/predicados_acervo.py, as mesmas
    que o `release conferir acervo` usa para o gate contra o retrato.

`--guardar` grava em acervo.retrato (cabeçalho, rodapé, total) e acervo.retrato_obra (as linhas), no banco
rag, que tem cópia (§9.1); nunca em arquivo. Se o retrato e o `--situacao` de hoje divergirem numa obra, não
guarda: é defeito do servido ou da consulta, e decide-se com o caso na mão.

Não corrige nada que o retrato mostre: a cura é do estágio dono (arq:0121 §11.2).
"""
import datetime
import json
import os
import subprocess
import sys

HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.insert(0, os.path.join(HARNESS, "bin", "_release", "conferir"))

import predicados_acervo as pa

BASE = "biblioteca"
PG, DB, USR = "rag-extractor-pg", "rag_extractor", "rag"

# arq:0121 §1.3 e §2.1; guia ciclo-de-vida-do-dado-do-acervo §2: os papéis valem para a base inteira
PAPEIS = {
    "proprietario": "dono, sem delegação",
    "curador": "dados",
    "custodia": "ti (rag-extractor-pg, motor-pg, balde MinIO)",
    "copia": "backup de cada banco e do balde, por ti (infra backup)",
    "metodo": "dados na extração e no corte; ia no índice, no vetor e na faceta",
}
CAMPOS_PROJECAO = ["obra_id", "servivel", "degrau", "impressao_id", "geracao", "embedder", "dimensao",
                   "trechos_com_vetor", "trechos_elegiveis"]
QUALIDADES = ("servível", "servível imperfeito", "não servível", "não julgado", "sem espelho",
              "sem impressão servindo")
SERVE_POR_TRECHO = ("servível", "servível imperfeito")
MOSTRAR = 10


def qualidade_do_espelho(imp):
    """A classe do espelho da impressão servindo pela régua vigente (a de `--qualidade`)."""
    if imp is None:
        return "sem impressão servindo"
    if not imp["espelho"]:
        return "sem espelho"
    if imp["servivel"] is None:
        return "não julgado"
    if not imp["servivel"]:
        return "não servível"
    return "servível imperfeito" if imp["imperfeita"] else "servível"


def _cobertura(proj_item, imp):
    """completa | parcial | sem vetor | sem índice | sem impressão servindo."""
    if imp is None:
        return "sem impressão servindo"
    if not proj_item or proj_item.get("geracao") is None:
        return "sem índice"
    vet, eleg = proj_item.get("trechos_com_vetor") or 0, proj_item.get("trechos_elegiveis") or 0
    if vet == 0:
        return "sem vetor"
    return "completa" if vet == eleg else "parcial"


def linhas_do_retrato(d, atual, proj):
    """Uma linha por obra do catálogo, retiradas incluídas. `proj` é {obra_id: item da projeção}."""
    por = pa._servindo_por_obra(d)
    codigos = {}
    for codigo, chaves in atual.items():
        for chave in chaves or []:
            obra = pa.obra_da_chave(chave, d)
            if obra:
                codigos.setdefault(obra, set()).add(codigo)
    ordem = list(pa.INVARIANTES)
    linhas = []
    for o in d["obras"]:
        imps = por.get(o["id"], [])
        imp = imps[0] if imps else None
        item = proj.get(o["id"])
        geracao = None
        if imp is not None and item and item.get("geracao") is not None:
            geracao = {"numero": item["geracao"], "embedder": item.get("embedder"),
                       "dimensao": item.get("dimensao")}
        linhas.append({
            "obra_id": o["id"], "titulo": o["titulo"],
            "situacao": "retirada" if o["retirada"] else "viva",
            "exposicao": pa.EXPOSICAO.get(o["marcacao"], o["marcacao"]),
            "impressao_id": imp["id"] if imp else None,
            "impressao_metodo": imp["metodo"] if imp else None,
            "espelho_qualidade": qualidade_do_espelho(imp),
            "geracao": geracao,
            "trechos_com_vetor": (item or {}).get("trechos_com_vetor") if imp is not None else None,
            "trechos_elegiveis": (item or {}).get("trechos_elegiveis") if imp is not None else None,
            "cobertura": _cobertura(item, imp),
            "invariantes": sorted(codigos.get(o["id"], ()), key=ordem.index),
        })
    return linhas


def divergencias_com_situacao(linhas, proj):
    """Onde o retrato e o `--situacao` de hoje divergem numa obra: a impressão que serve e o `servivel`."""
    achados = []
    for linha in linhas:
        item = proj.get(linha["obra_id"])
        if linha["situacao"] == "retirada" or item is None:
            continue
        serve = item.get("degrau") in ("ancorado", "orfao")
        esperado = item.get("impressao_id") if serve else None
        if linha["impressao_id"] != esperado:
            achados.append(f"{linha['obra_id']}: impressão servindo {linha['impressao_id']} no retrato, "
                           f"{esperado} no --situacao")
        servivel = linha["espelho_qualidade"] in SERVE_POR_TRECHO
        if bool(item.get("servivel")) != servivel:
            achados.append(f"{linha['obra_id']}: servível {servivel} no retrato, "
                           f"{bool(item.get('servivel'))} no --situacao")
    return achados


def _soma(linhas, chave):
    soma = {}
    for linha in linhas:
        valor = chave(linha)
        soma[valor] = soma.get(valor, 0) + 1
    return dict(sorted(soma.items(), key=lambda kv: str(kv[0])))


def montar_rodape(linhas, total, resumo):
    """A soma por estado de cada entidade e o fecho com `count(*)` de acervo.obra (arq:0121 §9.3)."""
    somas = {
        "obra": _soma(linhas, lambda linha: linha["situacao"]),
        "exposicao": _soma(linhas, lambda linha: linha["exposicao"]),
        "impressao_servindo": _soma(linhas, lambda linha: "com" if linha["impressao_id"] else "sem"),
        "espelho_qualidade": _soma(linhas, lambda linha: linha["espelho_qualidade"]),
        "indice_servindo": _soma(linhas, lambda linha: (
            f"geração {linha['geracao']['numero']}" if linha["geracao"]
            else ("sem índice" if linha["impressao_id"] else "sem impressão servindo"))),
        "cobertura": _soma(linhas, lambda linha: linha["cobertura"]),
    }
    nao_fecha = [f"{entidade}: soma {sum(estados.values())} ≠ {total} (count(*) de acervo.obra)"
                 for entidade, estados in somas.items() if sum(estados.values()) != total]
    if len(linhas) != total:
        nao_fecha.append(f"linhas do retrato: {len(linhas)} ≠ {total} (count(*) de acervo.obra)")
    return {**{k: v for k, v in somas.items()},
            "invariantes": {c: {"classe": r["classe"], "n": r["n"], "chaves": r["chaves"]}
                            for c, r in resumo.items()},
            "total": total, "fecha": not nao_fecha, "nao_fecha": nao_fecha}


def cabecalho(d, agora):
    geracao = next((g for g in d["motor"].get("geracoes") or []
                    if g["particao"] == pa.BIBLIOTECA and g["estado"] == "servindo"), None)
    return {"base": BASE, "tirado_em": agora, "papeis": PAPEIS,
            "geracao_servindo": None if geracao is None else {
                "numero": geracao["numero"], "embedder": geracao.get("embedder"),
                "dimensao_trecho": geracao.get("dimensao_trecho"),
                "dimensao_faceta": geracao.get("dimensao_faceta")}}


def montar(d, atual, proj, agora):
    """O retrato inteiro: {cabecalho, linhas, rodape, total, divergencias}. `d` é o de `coletar`, `atual`
    o de `avaliar_invariantes`, `proj` o {obra_id: item} da projeção /acervo/obras."""
    linhas = linhas_do_retrato(d, atual, proj)
    total = d["total"] if d["total"] is not None else len(linhas)
    resumo = pa.resumo(atual, d)
    return {"cabecalho": cabecalho(d, agora), "linhas": linhas, "total": total,
            "rodape": montar_rodape(linhas, total, resumo),
            "divergencias": divergencias_com_situacao(linhas, proj)}


def texto(retrato):
    """O retrato em linhas: cabeçalho, uma linha por obra, rodapé."""
    cab, rod = retrato["cabecalho"], retrato["rodape"]
    g = cab["geracao_servindo"]
    saida = [f"retrato da {cab['base']} · {cab['tirado_em']}",
             "geração servindo: " + (f"{g['numero']} ({g['embedder']}, trecho {g['dimensao_trecho']}, "
                                     f"faceta {g['dimensao_faceta']})" if g else "nenhuma"),
             "papéis: " + " · ".join(f"{k}: {v}" for k, v in cab["papeis"].items()), ""]
    for linha in retrato["linhas"]:
        g = linha["geracao"]
        ger = (f"g{g['numero']} d{g['dimensao']} vet {linha['trechos_com_vetor']}/{linha['trechos_elegiveis']}"
               if g else linha["cobertura"])
        imp = (f"imp {linha['impressao_id'][:8]} {(linha['impressao_metodo'] or '-')[:8]} "
               f"{linha['espelho_qualidade']}") if linha["impressao_id"] else linha["espelho_qualidade"]
        violados = " · violados: " + ",".join(linha["invariantes"]) if linha["invariantes"] else ""
        saida.append(f"{linha['obra_id'][:8]}  {linha['situacao']:8} {linha['exposicao'] or '-':7} {imp} · "
                     f"{ger}{violados}  {linha['titulo']}")
    saida += ["", f"rodapé · count(*) acervo.obra = {rod['total']}"]
    for entidade in ("obra", "exposicao", "impressao_servindo", "espelho_qualidade", "indice_servindo",
                     "cobertura"):
        estados = rod[entidade]
        saida.append(f"  {entidade}: " + " · ".join(f"{k} {v}" for k, v in estados.items())
                     + f"  = {sum(estados.values())}")
    abertas = [f"{c} {r['n']}" for c, r in rod["invariantes"].items() if r["n"]]
    nao_medidos = [c for c, r in rod["invariantes"].items() if r["n"] is None]
    saida.append("  invariantes violados: " + (" · ".join(abertas) if abertas else "nenhum")
                 + (f"  (não medidos: {', '.join(nao_medidos)})" if nao_medidos else ""))
    saida.append("  fecha: sim" if rod["fecha"] else "  NÃO FECHA: " + "; ".join(rod["nao_fecha"]))
    for achado in retrato["divergencias"][:MOSTRAR]:
        saida.append(f"  DIVERGE do --situacao: {achado}")
    if len(retrato["divergencias"]) > MOSTRAR:
        saida.append(f"  … +{len(retrato['divergencias']) - MOSTRAR} divergência(s) com o --situacao")
    return "\n".join(saida)


def _tag(*cargas):
    """Uma etiqueta de dollar-quote que não aparece em nenhuma das cargas."""
    n = 0
    while any(f"$r{n}$" in c for c in cargas):
        n += 1
    return f"$r{n}$"


def sql_guardar(retrato, tirado_por):
    """O INSERT do cabeçalho e das linhas, numa transação só. Devolve o resumo em uma linha de json."""
    cab = json.dumps(retrato["cabecalho"], ensure_ascii=False)
    rod = json.dumps(retrato["rodape"], ensure_ascii=False)
    colunas = ("obra_id", "titulo", "situacao", "exposicao", "impressao_id", "impressao_metodo",
               "espelho_qualidade", "geracao", "trechos_com_vetor", "trechos_elegiveis", "invariantes")
    linhas = json.dumps([{c: linha[c] for c in colunas} for linha in retrato["linhas"]], ensure_ascii=False)
    tag = _tag(cab, rod, linhas, tirado_por)
    return f"""begin;
with r as (
  insert into acervo.retrato (base, tirado_em, tirado_por, cabecalho, rodape, total)
  values ('{BASE}', {tag}{retrato['cabecalho']['tirado_em']}{tag}::timestamptz, {tag}{tirado_por}{tag},
          {tag}{cab}{tag}::jsonb, {tag}{rod}{tag}::jsonb, {int(retrato['total'])})
  returning id, tirado_em
), l as (
  insert into acervo.retrato_obra (retrato_id, obra_id, titulo, situacao, exposicao, impressao_id,
         impressao_metodo, espelho_qualidade, geracao, trechos_com_vetor, trechos_elegiveis, invariantes)
  select r.id, x.obra_id, x.titulo, x.situacao, x.exposicao, x.impressao_id, x.impressao_metodo,
         x.espelho_qualidade, x.geracao, x.trechos_com_vetor, x.trechos_elegiveis,
         coalesce(x.invariantes, '{{}}')
    from r, json_to_recordset({tag}{linhas}{tag}::json) as x(obra_id uuid, titulo text, situacao text,
         exposicao text, impressao_id uuid, impressao_metodo text, espelho_qualidade text, geracao jsonb,
         trechos_com_vetor int, trechos_elegiveis int, invariantes text[])
  returning retrato_id
)
select json_build_object('id', (select id::text from r), 'tirado_em', (select tirado_em from r),
                         'linhas', (select count(*) from l));
commit;
"""


def _escrever(sql):
    """Roda o script no rag-extractor-pg (stdin) e devolve a última linha de json que ele imprimiu."""
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    try:
        p = subprocess.run(["docker", "exec", "-i", PG, "psql", "-U", USR, "-d", DB, "-qtA",
                            "-v", "ON_ERROR_STOP=1"], input=sql, capture_output=True, text=True,
                           env=env, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise pa.Indeterminavel(f"{PG}: {e}") from None
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or f"psql saiu {p.returncode}").strip().splitlines()
        raise pa.Indeterminavel(f"{PG}: {msg[0] if msg else p.returncode}")
    ultima = [linha for linha in p.stdout.splitlines() if linha.strip()][-1:]
    try:
        return json.loads(ultima[0])
    except (IndexError, ValueError):
        raise pa.Indeterminavel(f"{PG}: o INSERT não devolveu o resumo") from None


def _projecao():
    sys.path.insert(0, HARNESS)
    from recuperacao.adaptadores import motor_acervo_rest
    from recuperacao.adaptadores.base import FonteIndisponivel
    try:
        itens = motor_acervo_rest.obras(CAMPOS_PROJECAO).get("itens", [])
    except FonteIndisponivel as e:
        raise pa.Indeterminavel(f"estado das obras fora do ar ({e})") from None
    return {i["obra_id"]: i for i in itens}


def _quem():
    """Quem tirou o retrato: `<cadeira>/<sujeito>@<sessão>`, do que a porta injeta. O sujeito (PF_SUJEITO, o `sub`
    do token) é o que autentica: sem ele não há quem assine, e a cadeira e a sessão só completam a trilha."""
    sujeito = os.environ.get("PF_SUJEITO", "").strip()
    if not sujeito:
        return None
    cadeira = (os.environ.get("PF_CADEIRA") or os.environ.get("PF_CONTA") or "").strip().lower()
    for prefixo in ("claudinho-", "claudinha-"):
        cadeira = cadeira.removeprefix(prefixo)
    sessao = (os.environ.get("PF_SESSAO") or os.environ.get("PF_SESSAO_ID") or "").strip()
    return f"{cadeira or '-'}/{sujeito[:8]}@{sessao[:8] or '-'}"


def executar(quero_json=False, guardar=False, ler=None, balde=None, orfaos=None, projecao=None,
             escrever=None, agora=None, quem=None):
    """O ato: 0 retrato que fecha, 1 retrato que não fecha ou que diverge do `--situacao`, 4 `--guardar`
    sem identidade, 5 fonte que não respondeu. As portas (`ler`, `projecao`, `escrever`…) trocam-se no teste."""
    ler = ler or pa.psql_json
    quem = quem if quem is not None else _quem()
    if guardar and not quem:
        sys.stderr.write("acervo listar --retrato --guardar: sem PF_SUJEITO não há quem tirou o retrato "
                         "(recusa; o sujeito vem do token, pela porta).\n")
        return 4
    agora = agora or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        d = pa.coletar(ler, balde=balde, orfaos=orfaos)
        proj = (projecao or _projecao)()
    except pa.Indeterminavel as e:
        sys.stderr.write(f"indeterminável: {e}\n")
        return 5
    retrato = montar(d, pa.avaliar_invariantes(d), proj, agora)
    if quero_json:
        print(json.dumps(retrato, ensure_ascii=False, indent=2))
    else:
        print(texto(retrato))
    if d["balde"] is None:
        sys.stderr.write(pa.POR_ARQUIVO + "\n")
    if guardar:
        if retrato["divergencias"]:
            sys.stderr.write(f"não guardei: o retrato diverge do --situacao em {len(retrato['divergencias'])} "
                             "obra(s); é defeito do servido ou da consulta, decide-se com o caso na mão.\n")
            return 1
        try:
            guardado = (escrever or _escrever)(sql_guardar(retrato, quem))
        except pa.Indeterminavel as e:
            sys.stderr.write(f"indeterminável: não guardei ({e})\n")
            return 5
        if guardado.get("linhas") != len(retrato["linhas"]):
            sys.stderr.write(f"retrato guardado pela metade: {guardado.get('linhas')} de "
                             f"{len(retrato['linhas'])} linhas\n")
            return 1
        sys.stderr.write(f"retrato guardado: {guardado['id']} · {retrato['cabecalho']['tirado_em']} · "
                         f"total {retrato['total']} · {guardado['linhas']} linha(s) · acervo.retrato\n")
    return 0 if retrato["rodape"]["fecha"] and not retrato["divergencias"] else 1
