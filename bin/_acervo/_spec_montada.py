"""Montagem na leitura da spec (arq:0126 §11 a §13) — o que o golden record serve, no ato.

A spec cita pela chave o que o golden record sabe; `acervo ler casa spec <chave>` monta, depois
do corpo, os blocos derivados: as camadas de Onde mora no mapa, do que a peça depende, como sobe
e como volta, os segredos por referência, os documentos que declaram a peça em `Sobre:` e a data
da última conferência contra produção (acervo.casa.conferida_em, 093). O que a classe ainda não
tem no golden record sai numa lista própria, com a dona da classe (spec entidade-raiz-da-casa).

Puro: `referentes_do_sobre` e `render` não tocam banco; `sql` devolve a consulta que o chamador
roda (um SELECT que devolve um objeto json). Segredo sai só por referência: caminho de pasta ou
nome de variável, nunca valor.
"""

import re

_RE_SOBRE = re.compile(
    r"^[ \t]*(?:[-*+][ \t]+)?(?:\*\*|__)?Sobre(?:\*\*|__)?[ \t]*:[ \t]*(?:\*\*|__)?[ \t]*(?P<v>.*)$",
    re.MULTILINE)
_RE_REF = re.compile(r"(?P<classe>[a-z][a-z0-9_-]*)(?:[ \t]+|:)[ \t]*(?P<chave>\S+)")
_RE_SECAO = re.compile(r"^## ", re.MULTILINE)

# Lacunas do golden record que a spec precisa (pedido do arquiteto de 11/10/2026, G1 a G7),
# com a dona da classe. Sai da lista quando a classe entra no golden record e a montagem a lê.
NAO_MONTADO = (
    ("onde cada peça mora (peça → repositório e caminho)", "G3, arquiteto"),
    ("contrato de cada dependência (serviço → serviço, stack → stack)", "G2, ti"),
    ("pacto de serviço: jornada, SLI, SLO, janela, orçamento", "G4, ti"),
    ("sonda e alerta: condição, quem age, o que faz", "G5, ti"),
    ("alvo de backup, retenção e cópia", "G6, ti"),
    ("quem opera e quem muda cada peça", "G7, arquiteto (verbo) e ti (stack)"),
)


def referentes_do_sobre(corpo):
    """[(classe, chave)] do primeiro `Sobre:` do cabeçalho (texto antes do 1º `## `), na ordem
    escrita. O primeiro é a peça (arq:0126 §1). Item fora da forma `<classe> <chave>` sai."""
    texto = (corpo or "").replace("\r\n", "\n")
    m = _RE_SECAO.search(texto)
    cab = texto[: m.start()] if m else texto
    s = _RE_SOBRE.search(cab)
    if not s:
        return []
    refs = []
    for parte in re.split(r"[;,]", s.group("v")):
        p = parte.strip().strip("`*_").strip()
        r = _RE_REF.fullmatch(p) if p else None
        if r:
            par = (r.group("classe"), r.group("chave").strip("`*_."))
            if par[1] and par not in refs:
                refs.append(par)
    return refs


def _arr(lit, valores):
    return "array[" + ", ".join(lit(v) for v in valores) + "]::text[]" if valores else \
        "array[]::text[]"


def sql(lit, refs, casa_id):
    """A consulta única da montagem: um objeto json com o que cada classe do golden record
    serve para os referentes da spec."""
    por = {}
    for classe, chave in refs:
        por.setdefault(classe, []).append(chave)
    caps, stacks, verbos = (_arr(lit, por.get(k, [])) for k in ("capacidade", "stack", "verbo"))
    peca = refs[0] if refs else ("", "")
    cid = lit(casa_id)
    return f"""
      select json_build_object(
        'fichas', (select coalesce(json_agg(json_build_object('classe', e.classe,
                      'chave', e.chave_humana)), '[]')
                     from acervo.entidade e
                    where e.estado = 'ativa' and (e.classe, e.chave_humana) in (
                          select r.classe, r.chave from (values {", ".join(
                              f"({lit(c)}, {lit(k)})" for c, k in refs) or "(null, null)"})
                          as r(classe, chave))),
        'capacidades', (select coalesce(json_agg(json_build_object('slug', c.slug,
                          'rotulo', c.rotulo, 'descricao', c.descricao, 'pai', p.slug)
                          order by c.slug), '[]')
                          from acervo.ferramental_capacidade c
                          left join acervo.ferramental_capacidade p on p.id = c.pai_id
                         where c.slug = any({caps})),
        'stacks', (select coalesce(json_agg(json_build_object('slug', s.slug, 'papel', s.papel,
                     'critico', s.critico, 'repo', s.repo, 'compose', s.compose,
                     'segredos', s.segredos, 'reversao', s.reversao,
                     'instancias', (select coalesce(json_agg(i.slug order by i.slug), '[]')
                                      from acervo.instancia_roda_em_stack x
                                      join acervo.ferramental_instancia i on i.id = x.instancia_id
                                     where x.stack_id = s.id)) order by s.slug), '[]')
                     from acervo.stack s where s.slug = any({stacks})),
        'verbos', (select coalesce(json_agg(json_build_object('slug', v.slug,
                     'capacidade', c.slug, 'dono', v.dono, 'estado', v.estado,
                     'descricao', v.descricao, 'sucessor', v.sucessor,
                     'instancias', (select coalesce(json_agg(i.slug order by i.slug), '[]')
                                      from acervo.ferramental_instancia i
                                     where i.verbo_id = v.id)) order by v.slug), '[]')
                     from acervo.ferramental_verbo v
                     left join acervo.ferramental_capacidade c on c.id = v.capacidade_id
                    where v.slug = any({verbos})),
        'consumo', (select coalesce(json_agg(row_to_json(t) order by t.verbo, t.servico), '[]')
                      from (select verbo, servico, caminho, versao_min,
                                   array_agg(distinct ato order by ato) as atos
                              from acervo.ferramental_consumo where verbo = any({verbos})
                             group by verbo, servico, caminho, versao_min) t),
        'acesso', (select coalesce(json_agg(row_to_json(t) order by t.verbo, t.modo, t.recurso),
                     '[]')
                     from (select verbo, recurso_id as recurso, modo,
                                  array_agg(distinct ato order by ato) as atos
                             from acervo.ferramental_acesso
                            where verbo = any({verbos}) and recurso_id <> 'nada'
                            group by verbo, recurso_id, modo) t),
        'segredos_env', (select coalesce(json_agg(json_build_object('verbo', verbo,
                           'variavel', variavel) order by verbo, variavel), '[]')
                           from acervo.ferramental_ambiente
                          where verbo = any({verbos}) and segredo),
        'documentos', (select coalesce(json_agg(json_build_object('especie', es.especie,
                         'chave', coalesce(c.chave, c.repo || '@' || c.path),
                         'titulo', c.titulo) order by es.especie, c.chave), '[]')
                         from acervo.entidade_relacao r
                         join acervo.entidade e on e.id = r.para_id
                         join acervo.casa c on c.id = r.de_id
                         join acervo.casa_especie es on es.casa_id = c.id
                        where r.tipo = 'sobre'
                          and e.classe = {lit(peca[0])} and e.chave_humana = {lit(peca[1])}
                          and c.retirada_em is null and c.id <> {cid}::uuid),
        'conferida_em', (select to_char(conferida_em, 'YYYY-MM-DD') from acervo.casa
                          where id = {cid}::uuid));"""


def _lista(v):
    """Lista de texto de um campo jsonb que pode vir como array ou como TEXTO de um array
    (acervo.stack.compose está gravado assim: string json dentro do jsonb)."""
    if isinstance(v, str):
        try:
            import json
            v = json.loads(v)
        except ValueError:
            return [v] if v.strip() else []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if v else []


def _rev(rev):
    if not isinstance(rev, dict) or not rev:
        return "reversão não declarada no golden record"
    partes = [f"volta por `{rev.get('via')}`" if rev.get("via") else "via de volta não declarada"]
    if rev.get("quem"):
        partes.append(f"quem volta: {rev['quem']}")
    if rev.get("janela_min") is not None:
        partes.append(f"janela {rev['janela_min']} min")
    if rev.get("estado"):
        partes.append(f"o que não volta com o código: {rev['estado']}")
    if rev.get("provado_em"):
        partes.append(f"provado em {str(rev['provado_em'])[:10]}")
    return "; ".join(partes)


def render(dados, refs):
    """O bloco em markdown. `dados` é o objeto de `sql`; None = banco fora (uma linha diz)."""
    L = ["", "---", "", "## Montado na leitura", "",
         "_Do golden record, no ato da leitura (arq:0126 §11); não está no arquivo. "
         "Só o arquivo: `--cru`._", ""]
    if dados is None:
        L.append("indisponível: o banco não respondeu; vale só o que está escrito acima.")
        return "\n".join(L) + "\n"
    if not refs:
        L.append("sem `Sobre:` no cabeçalho: não há peça a montar (arq:0126 §1).")
        return "\n".join(L) + "\n"
    conf = dados.get("conferida_em")
    L.append(f"Conferida contra produção: {conf}" if conf else
             "Conferida contra produção: não declarada no Estado (arq:0126 §10).")
    L.append("")

    fichas = {(f["classe"], f["chave"]) for f in dados.get("fichas") or []}
    caps = {c["slug"]: c for c in dados.get("capacidades") or []}
    stacks = {s["slug"]: s for s in dados.get("stacks") or []}
    verbos = {v["slug"]: v for v in dados.get("verbos") or []}

    L.append("### Onde mora no mapa")
    for i, (classe, chave) in enumerate(refs):
        marca = " (a peça)" if i == 0 else ""
        if classe == "capacidade" and chave in caps:
            c = caps[chave]
            txt = c.get("descricao") or c.get("rotulo") or ""
            pai = f"; dentro de {c['pai']}" if c.get("pai") else ""
            L.append(f"- capacidade {chave}{marca}" + (f" — {txt}" if txt else "") + pai)
        elif classe == "verbo" and chave in verbos:
            v = verbos[chave]
            info = [v.get("descricao") or "", f"dono {v['dono']}" if v.get("dono") else "",
                    v.get("estado") or "",
                    f"sucessor {v['sucessor']}" if v.get("sucessor") else "",
                    ("instâncias " + ", ".join(v["instancias"])) if v.get("instancias") else ""]
            L.append(f"- verbo {chave}{marca} — " + " · ".join(x for x in info if x))
        elif classe == "stack" and chave in stacks:
            s = stacks[chave]
            info = [s.get("papel") or "", f"repositório {s['repo']}" if s.get("repo") else "",
                    "crítica" if s.get("critico") else "",
                    ("instâncias " + ", ".join(s["instancias"])) if s.get("instancias") else ""]
            L.append(f"- stack {chave}{marca} — " + " · ".join(x for x in info if x))
        elif (classe, chave) in fichas:
            L.append(f"- {classe} {chave}{marca} — ficha no fichário, sem atributo no golden record")
        else:
            L.append(f"- {classe} {chave}{marca} — não resolve no golden record")
    L.append("")

    consumo, acesso = dados.get("consumo") or [], dados.get("acesso") or []
    if consumo or acesso:
        L.append("### Do que depende")
        for c in consumo:
            onde = f" em {c['caminho']}" if c.get("caminho") else ""
            versao = f" (≥ {c['versao_min']})" if c.get("versao_min") else ""
            L.append(f"- verbo {c['verbo']} consome {c['servico']}{onde}{versao} — "
                     f"atos {', '.join(c.get('atos') or [])}")
        for a in acesso:
            modo = {"le": "lê", "escreve": "escreve"}.get(a.get("modo"), a.get("modo"))
            L.append(f"- verbo {a['verbo']} {modo} {a['recurso']} — "
                     f"atos {', '.join(a.get('atos') or [])}")
        L.append("- o contrato de cada dependência ainda não está no golden record (G2, ti)")
        L.append("")

    if stacks:
        L.append("### Como sobe e como volta")
        for slug, s in stacks.items():
            compose = _lista(s.get("compose"))
            sobe = (f"sobe de {', '.join(compose)}" if compose else "compose não declarado")
            L.append(f"- stack {slug}: {sobe}; {_rev(s.get('reversao'))}")
            nota = (s.get("reversao") or {}).get("nota") if isinstance(s.get("reversao"), dict) else None
            if nota:
                L.append(f"  - {nota}")
        L.append("")

    seg_stack = [(slug, _lista(s.get("segredos"))) for slug, s in stacks.items()
                 if _lista(s.get("segredos"))]
    seg_env = dados.get("segredos_env") or []
    if seg_stack or seg_env:
        L.append("### Segredos por referência")
        for slug, caminhos in seg_stack:
            L.append(f"- stack {slug}: {', '.join(caminhos)}")
        for e in seg_env:
            L.append(f"- verbo {e['verbo']}: variável {e['variavel']}")
        L.append("")

    docs = dados.get("documentos") or []
    peca = f"{refs[0][0]} {refs[0][1]}"
    L.append(f"### Documentos que declaram {peca} em Sobre:")
    if docs:
        for d in docs:
            L.append(f"- {d['especie']} {d['chave']} · {d.get('titulo') or '-'}")
    else:
        L.append(f"- nenhum outro documento de casa declara {peca}")
    L.append("")

    L.append("### Ainda não montado (falta no golden record)")
    for o_que, dona in NAO_MONTADO:
        L.append(f"- {o_que} — {dona}")
    return "\n".join(L) + "\n"
