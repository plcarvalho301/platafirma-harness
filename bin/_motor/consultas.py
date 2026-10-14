"""O log de recuperação como o dono o lê (card #3513, tarefa 7; spec plano-de-controle-face-motor R1 a R3 e R19).

`motor rag consultas <particao>` lista as linhas de `acervo.evento_recuperacao` com filtro por período, cadeira,
chapéu, origem, cobertura e texto; cada linha traz a pergunta inteira, a cobertura, a origem e o tempo por fase.
Com `--por-dia` dá a série diária de cobertura (a view `acervo.cobertura_diaria`, só das origens busca e abertura),
com as linhas sem cobertura gravada contadas à parte: a taxa só tem as que a gravaram no denominador.

Três regras de honestidade (arq:0110 §4):
- campo que o evento antigo não tem (cobertura, tempo por fase, cadeira, geração, parâmetros) sai «nao consegui
  olhar», nunca zero nem vazio; cobertura fora dos cinco valores do contrato também;
- filtro sobre campo que poucas linhas têm diz quantas o têm;
- a prévia (origem `previa`) fica no log mas fora da lista e da série, salvo quem a pede pela origem.

Este módulo monta a consulta e arruma o que volta; quem fala com o banco é o `motor`.
"""
from __future__ import annotations

import re

NAO_CONSEGUI = "nao consegui olhar"
COBERTURAS = ("boa", "fraca", "nenhuma", "ausente", "sem-indice")
ORIGENS_DA_SERIE = ("busca", "abertura")          # a lista da view acervo.cobertura_diaria (103)
ORIGENS = ("abertura", "busca", "bench", "sombra", "autoteste", "previa")
LIMITE_PADRAO, LIMITE_MAXIMO = 50, 1000

OPCOES = {"--desde": 1, "--ate": 1, "--cadeira": 1, "--chapeu": 1, "--origem": 1, "--cobertura": 1,
          "--texto": 1, "--limite": 1, "--por-dia": 0, "--json": 0}
USO = ("motor <inst> consultas <particao> [--desde <data>] [--ate <data>] [--cadeira <slug>] [--chapeu <slug>]\n"
       "                     [--origem <o>[,<o>…]] [--cobertura boa|fraca|nenhuma|ausente|sem-indice|sem-leitura]\n"
       "                     [--texto <trecho>] [--limite N] [--por-dia] [--json]")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")
_SLUG = re.compile(r"^[\w.-]+$")


def le_argv(argv: list[str]) -> dict:
    """Os filtros e as opções, conferidos. `ValueError` com a causa é uso incorreto (exit 2)."""
    f: dict = {"limite": LIMITE_PADRAO, "por_dia": False, "json": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        n = OPCOES.get(a)
        if n is None:
            raise ValueError(f"argumento desconhecido {a!r}")
        if n and (i + 1 >= len(argv) or argv[i + 1].startswith("--")):
            raise ValueError(f"{a} exige um valor")
        v = argv[i + 1] if n else True
        i += 1 + n
        if a in ("--desde", "--ate"):
            if not _DATA.match(v):
                raise ValueError(f"{a} exige AAAA-MM-DD ou AAAA-MM-DDTHH:MM, veio {v!r}")
            f[a[2:]] = v
        elif a in ("--cadeira", "--chapeu"):
            if not _SLUG.match(v):
                raise ValueError(f"{a} exige um slug, veio {v!r}")
            f[a[2:]] = v
        elif a == "--origem":
            lista = [x for x in v.split(",") if x]
            torta = [x for x in lista if x not in ORIGENS]
            if not lista or torta:
                raise ValueError(f"--origem aceita {'|'.join(ORIGENS)}, veio {v!r}")
            f["origem"] = lista
        elif a == "--cobertura":
            if v not in COBERTURAS + ("sem-leitura",):
                raise ValueError(f"--cobertura aceita {'|'.join(COBERTURAS)}|sem-leitura, veio {v!r}")
            f["cobertura"] = v
        elif a == "--texto":
            if not v.strip():
                raise ValueError("--texto vazio")
            f["texto"] = v.strip()
        elif a == "--limite":
            try:
                f["limite"] = int(v)
            except ValueError:
                raise ValueError(f"--limite exige inteiro, veio {v!r}") from None
            if not 1 <= f["limite"] <= LIMITE_MAXIMO:
                raise ValueError(f"--limite vai de 1 a {LIMITE_MAXIMO}")
        elif a == "--por-dia":
            f["por_dia"] = True
        else:
            f["json"] = True
    return f


# ---------------------------------------------------------------- o SQL

def _periodo(f: dict, lit) -> list[str]:
    w = []
    if f.get("desde"):
        w.append(f"(e.criado_em AT TIME ZONE 'UTC') >= {lit(f['desde'])}::timestamp")
    if f.get("ate"):
        w.append(f"(e.criado_em AT TIME ZONE 'UTC') < ({lit(f['ate'])}::date + 1)" if len(f["ate"]) == 10
                 else f"(e.criado_em AT TIME ZONE 'UTC') <= {lit(f['ate'])}::timestamp")
    return w


def _base(f: dict, particao: str, lit) -> list[str]:
    """O que delimita a população: dispara, partição, período, origem e texto. A previa fica de fora, salvo
    pedida pela origem. Os filtros de campo (cadeira, chapéu, cobertura) entram à parte."""
    w = ["e.disparou", f"e.particao = {lit(particao)}"] + _periodo(f, lit)
    origens = f.get("origem")
    w.append(f"e.origem IN ({', '.join(lit(o) for o in origens)})" if origens
             else "(e.origem IS NULL OR e.origem <> 'previa')")
    if f.get("texto"):
        w.append("strpos(lower(coalesce(e.necessidade, '') || ' ' || coalesce(e.pergunta, '')), "
                 f"lower({lit(f['texto'])})) > 0")
    return w


def _de_campo(f: dict, lit) -> list[str]:
    w = []
    if f.get("cadeira"):
        w.append(f"e.cadeira = {lit(f['cadeira'])}")
    if f.get("chapeu"):
        w.append(f"e.chapeu = {lit(f['chapeu'])}")
    c = f.get("cobertura")
    if c == "sem-leitura":
        w.append("e.cobertura IS NULL")
    elif c:
        w.append(f"e.cobertura = {lit(c)}")
    return w


def sql_lista(f: dict, particao: str, lit) -> str:
    w = " AND ".join(_base(f, particao, lit) + _de_campo(f, lit))
    return ("/* consultas:lista */ SELECT coalesce(json_agg(t ORDER BY t.criado_em DESC, t.id), '[]'::json) FROM ("
            "SELECT e.id::text AS id, e.criado_em::text AS criado_em, e.sessao_id::text AS sessao_id, e.particao, "
            "e.origem, e.cadeira, e.chapeu, e.necessidade, e.pergunta, e.cobertura, e.tempos_ms, "
            "e.geracao_id::text AS geracao_id, e.parametros "
            f"FROM acervo.evento_recuperacao e WHERE {w} "
            f"ORDER BY e.criado_em DESC, e.id LIMIT {int(f['limite'])}) t")


def sql_contagem(f: dict, particao: str, lit) -> str:
    """Numa chamada: a população, quantas têm cada campo e quantas passam nos filtros de campo."""
    base = " AND ".join(_base(f, particao, lit))
    campo = " AND ".join(_de_campo(f, lit)) or "true"
    return ("/* consultas:contagem */ SELECT json_build_object('populacao', count(*), "
            "'cadeira', count(e.cadeira), 'chapeu', count(nullif(e.chapeu, '-')), 'cobertura', count(e.cobertura), "
            "'tempos_ms', count(e.tempos_ms), "
            f"'no_filtro', count(*) FILTER (WHERE {campo})) FROM acervo.evento_recuperacao e WHERE {base}")


def sql_dia_da_view(f: dict, particao: str, lit) -> str:
    w = [f"particao = {lit(particao)}"]
    if f.get("desde"):
        w.append(f"dia >= {lit(f['desde'][:10])}::date")
    if f.get("ate"):
        w.append(f"dia <= {lit(f['ate'][:10])}::date")
    return ("/* consultas:dia-view */ SELECT coalesce(json_agg(t ORDER BY t.dia), '[]'::json) FROM ("
            "SELECT dia::text AS dia, particao, total, boa, fraca, nenhuma, ausente, sem_indice "
            f"FROM acervo.cobertura_diaria WHERE {' AND '.join(w)}) t")


def sql_dia_linhas(f: dict, particao: str, lit) -> str:
    """As linhas de cada dia que a view considera (as mesmas origens), com e sem cobertura: a diferença é o que
    ficou fora do denominador da taxa."""
    w = ["e.disparou", f"e.particao = {lit(particao)}",
         f"e.origem IN ({', '.join(lit(o) for o in ORIGENS_DA_SERIE)})"] + _periodo(f, lit)
    return ("/* consultas:dia-linhas */ SELECT coalesce(json_agg(t ORDER BY t.dia), '[]'::json) FROM ("
            "SELECT (e.criado_em AT TIME ZONE 'UTC')::date::text AS dia, count(*) AS linhas, "
            "count(*) FILTER (WHERE e.cobertura IS NULL) AS sem_cobertura "
            f"FROM acervo.evento_recuperacao e WHERE {' AND '.join(w)} GROUP BY 1) t")


# ---------------------------------------------------------------- arrumar o que volta

def _cobertura(valor) -> dict:
    if valor in COBERTURAS:
        return {"cobertura": valor, "cobertura_leitura": None}
    return {"cobertura": None,
            "cobertura_leitura": NAO_CONSEGUI if valor is None else f"{NAO_CONSEGUI} (valor fora do contrato: {valor!r})"}


def linha(row: dict) -> dict:
    """Uma linha do log na forma da saída: a pergunta inteira, e `nao consegui olhar` onde o evento não tem."""
    out = {"id": row.get("id"), "criado_em": row.get("criado_em"), "origem": row.get("origem"),
           "particao": row.get("particao"), "cadeira": row.get("cadeira"), "chapeu": row.get("chapeu"),
           "necessidade": row.get("necessidade"), "pergunta": row.get("pergunta"),
           "geracao_id": row.get("geracao_id"), "parametros": row.get("parametros"),
           "tempos_ms": row.get("tempos_ms"), "sessao_id": row.get("sessao_id")}
    out.update(_cobertura(row.get("cobertura")))
    out["tempos_leitura"] = None if row.get("tempos_ms") else NAO_CONSEGUI
    return out


def preenchimento(c: dict) -> dict:
    """Quantas linhas da população têm cada campo (o `de` é a população)."""
    return {k: {"com": int(c.get(k) or 0), "de": int(c.get("populacao") or 0)}
            for k in ("cadeira", "chapeu", "cobertura", "tempos_ms")}


def avisos_de_filtro(f: dict, c: dict) -> list[str]:
    """Filtro sobre campo que quase nenhuma linha tem diz quantas o têm, em vez de mostrar zero (R19)."""
    p = preenchimento(c)
    out = []
    for campo in ("cadeira", "chapeu", "cobertura"):
        if f.get(campo):
            out.append(f"filtro por {campo}: so {p[campo]['com']} de {p[campo]['de']} linhas da populacao tem {campo}")
    return out


def serie_por_dia(view: list[dict], linhas: list[dict]) -> dict:
    """A série diária: a view (total, as cinco coberturas) junto das linhas sem cobertura de cada dia.

    A taxa de cobertura fraca é fraca/total sobre as linhas que gravaram a cobertura; o dia sem nenhuma diz
    `nao consegui olhar` e quantas linhas ficaram fora. A série começa no primeiro dia com cobertura gravada."""
    por_dia = {x["dia"]: x for x in linhas}
    dias = []
    for v in view:
        extra = por_dia.pop(v["dia"], {"linhas": 0, "sem_cobertura": 0})
        total = int(v["total"])
        dias.append({"dia": v["dia"], "particao": v["particao"], "total": total,
                     "boa": int(v["boa"]), "fraca": int(v["fraca"]), "nenhuma": int(v["nenhuma"]),
                     "ausente": int(v["ausente"]), "sem_indice": int(v["sem_indice"]),
                     "linhas_fora_do_denominador": int(extra["sem_cobertura"]),
                     "taxa_fraca": round(int(v["fraca"]) / total, 4) if total else None,
                     "nao_consegui_olhar": None if total else
                     f"{NAO_CONSEGUI}: {extra['sem_cobertura']} linha(s) sem cobertura gravada, anteriores a 101"})
    # o dia que tem linhas mas a view nem lista (nenhuma com cobertura) também é dia sem leitura
    for dia, extra in sorted(por_dia.items()):
        dias.append({"dia": dia, "particao": None, "total": 0, "boa": 0, "fraca": 0, "nenhuma": 0, "ausente": 0,
                     "sem_indice": 0, "linhas_fora_do_denominador": int(extra["sem_cobertura"]), "taxa_fraca": None,
                     "nao_consegui_olhar": f"{NAO_CONSEGUI}: {extra['sem_cobertura']} linha(s) sem cobertura gravada"})
    dias.sort(key=lambda d: d["dia"])
    com_leitura = [d["dia"] for d in dias if d["total"]]
    return {"serie_comeca_em": com_leitura[0] if com_leitura else None, "dias": dias}


def indicador_da_taxa(serie: dict, lido_em: str) -> dict:
    """O bloco do indicador (R5, R6): o que mede, a amostra, a regra e quem configurou; sem limiar, sem nível."""
    dias = serie["dias"]
    total = sum(d["total"] for d in dias)
    fora = sum(d["linhas_fora_do_denominador"] for d in dias)
    return {"nome": "taxa diaria de cobertura fraca",
            "mede": "fracao das buscas dirigidas e de abertura cuja cobertura declarada foi fraca, por dia (UTC)",
            "amostra": f"{total} busca(s) com cobertura gravada em {len(dias)} dia(s); {fora} linha(s) sem "
                       "cobertura ficaram fora do denominador",
            "regra": "sem limiar configurado: medida nova entra como aviso, sem nivel de risco (R6)",
            "quem_configurou": "ia", "hora": lido_em, "fonte": "acervo.cobertura_diaria (banco rag)"}


def texto_da_lista(itens: list[dict], conta: dict, f: dict, particao: str, lido_em: str) -> str:
    desde = f" desde {f['desde']}" if f.get("desde") else ""
    cab = (f"consultas do log ({particao}{desde}): {conta.get('no_filtro', len(itens))} no filtro de "
           f"{conta.get('populacao', '?')} na populacao; mostro {len(itens)} · lido {lido_em}")
    saida = [cab]
    saida += [f"  ({a})" for a in avisos_de_filtro(f, conta)]
    for x in itens:
        ms = (x["tempos_ms"] or {}).get("total")
        quem = "/".join(p for p in (x["cadeira"], x["chapeu"]) if p and p != "-") or "-"
        saida.append(f"  {x['criado_em']}  {x['origem'] or '-':<9} {x['cobertura'] or NAO_CONSEGUI:<16} {quem}  "
                     f"{('%s ms' % ms) if ms is not None else NAO_CONSEGUI}")
        saida.append(f"      {x['pergunta'] or x['necessidade'] or NAO_CONSEGUI}")
    return "\n".join(saida)


def texto_por_dia(serie: dict, ind: dict) -> str:
    saida = [f"cobertura por dia (UTC): a serie comeca em {serie['serie_comeca_em'] or NAO_CONSEGUI} · "
             f"{ind['amostra']}"]
    for d in serie["dias"]:
        if d["nao_consegui_olhar"]:
            saida.append(f"  {d['dia']}  {d['nao_consegui_olhar']}")
        else:
            saida.append(f"  {d['dia']}  {d['particao']}  total {d['total']:>4}  boa {d['boa']:>4}  fraca {d['fraca']:>4}  "
                         f"nenhuma {d['nenhuma']:>3}  ausente {d['ausente']:>3}  sem-indice {d['sem_indice']:>3}  "
                         f"taxa fraca {d['taxa_fraca']:.3f}  fora do denominador {d['linhas_fora_do_denominador']}")
    return "\n".join(saida)
