#!/usr/bin/env python3
# _identidade.py — biblioteca de identidade da raiz da casa (acervo.entidade*, arq:0108).
# Os três passos da spec_acervo.md §3:
#   1. validar_forma: valida seletor contra entidade_classe.forma_chave (exit 2 se invalido)
#   2. resolver_canon: busca exata em chave_humana; se 0, busca em entidade_alias
#      (0 -> exit 1 com 4 linhas fixas; 1 -> uuid; >1 -> exit 2 com candidatos)
#   3. obter_substrato: busca endereco (repo@path) em acervo.entidade_suporte
# Documento de casa NAO passa mais por aqui para ser lido: `acervo ler casa` resolve a chave
# em acervo.casa (arq:0115 §3, §11; _acervo/casa). Esta biblioteca segue servindo `resolver`,
# `curar alias` e o Sobre: de `listar casa --sobre`, e a negativa de 4 linhas de todos.
# Nenhum caminho de repo de release: o suporte da casa e um so (SUPORTE, arq:0115 §1.2).
import json
import os
import re
import signal
import subprocess
import sys

try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass

PG = "rag-extractor-pg"
DB = "rag_extractor"
USR = "rag"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _suporte import SUPORTE  # noqa: E402  (suporte da particao casa, arq:0115 §1.2)

# Forma da chave de adr (arq:0115 §3.2): a mesma RE_ADR de _acervo/casa. Mora no cliente
# porque a 060 tira adr de entidade_classe (§6.2).
FORMA_ADR = r"^(?:([a-z]+):)?(\d{1,4})$"
# Especies de documento de casa que ainda tem classe em entidade_classe ate a 060.
DOC_CASA = ("adr", "spec", "parecer")


def morre(msg, code=2):
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def _lit(s):
    return "'" + str(s).replace("'", "''") + "'"


def psql_exec(sql):
    """Executa comando DDL/DML no rag_extractor."""
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", "unix:///run/user/1001/docker.sock")
    try:
        res = subprocess.run(
            ["docker", "exec", "-i", PG, "psql", "-U", USR, "-d", DB, "-c", sql],
            capture_output=True, text=True, env=env)
    except FileNotFoundError:
        morre("acervo identidade: 'docker' nao encontrado no PATH.", 3)

    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        if "is not running" in stderr or "could not connect" in stderr or "Connection refused" in stderr:
            morre("acervo identidade: banco de dados indisponivel (rag_extractor):\n%s" % stderr, 5)
        morre("acervo identidade: psql falhou (rc=%s):\n%s" % (res.returncode, stderr), 3)

    return res.stdout.strip()


def psql_json(sql, alvo="query"):
    """Executa SELECT no rag_extractor e devolve estrutura desserializada de JSON."""
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", "unix:///run/user/1001/docker.sock")
    try:
        res = subprocess.run(
            ["docker", "exec", "-i", PG, "psql", "-U", USR, "-d", DB, "-tA", "-c", sql],
            capture_output=True, text=True, env=env)
    except FileNotFoundError:
        morre("acervo identidade: 'docker' nao encontrado no PATH.", 3)

    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        if "is not running" in stderr or "could not connect" in stderr or "Connection refused" in stderr:
            morre("acervo identidade: banco de dados indisponivel (rag_extractor):\n%s" % stderr, 5)
        morre("acervo identidade: psql falhou (rc=%s):\n%s" % (res.returncode, stderr), 3)

    saida = res.stdout.strip()
    if not saida:
        return []
    try:
        return json.loads(saida)
    except (ValueError, TypeError) as e:
        morre("acervo identidade %s: psql nao devolveu JSON parseavel (%s):\n  %s"
              % (alvo, e, saida[:200]), 3)


def validar_forma(classe, seletor):
    """Passo 1 da spec §3.
    Valida se a classe existe e se o seletor casa com forma_chave.
    Retorna (canonico, numero_sem_serie).

    adr: a forma da chave mora AQUI (FORMA_ADR, a mesma de _acervo/casa), nao em
    entidade_classe.forma_chave: a 060 tira adr/spec/parecer de entidade_classe (arq:0115
    §6.2). Classe de documento de casa que ja saiu de entidade_classe recusa (exit 2)
    apontando `acervo ler casa`, em vez de morrer com "classe nao existe".
    """
    if classe == "adr" and not re.match(FORMA_ADR, seletor.strip()):
        morre("acervo: seletor '%s' invalido para classe 'adr'. Forma esperada: %s"
              % (seletor.strip(), FORMA_ADR), 2)
    classes_info = psql_json(
        "select coalesce(json_agg(row_to_json(t)), '[]') from ("
        "  select slug, forma_chave from acervo.entidade_classe where slug = %s"
        ") t;" % _lit(classe), "classe"
    )
    if not classes_info and classe in DOC_CASA:
        morre("acervo resolver: '%s' e especie de documento de casa, que se le pela chave em "
              "acervo.casa (arq:0115 §6.2, §11):\n  acervo ler casa %s %s"
              % (classe, classe, seletor.strip()), 2)
    if not classes_info:
        vivas = psql_json(
            "select coalesce(json_agg(slug order by slug),'[]') from acervo.entidade_classe;",
            "classes vivas"
        )
        morre("acervo: classe '%s' nao existe em acervo.entidade_classe.\n"
              "  classes vivas: %s" % (classe, ", ".join(vivas)), 2)

    forma = FORMA_ADR if classe == "adr" else classes_info[0].get("forma_chave")
    s = seletor.strip()
    if classe == "minuta" and re.match(r"^\d+$", s):
        s = f"arq:{s.zfill(4)}"
    if forma:
        m = re.match(forma, s)
        if not m:
            morre("acervo: seletor '%s' invalido para classe '%s'. Forma esperada: %s"
                  % (s, classe, forma), 2)
        if classe in ("adr", "minuta"):
            serie = m.group(1) if m.lastindex and m.lastindex >= 1 else None
            num = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
            num_pad = num.zfill(4)
            if serie:
                return f"{serie}:{num_pad}", None
            else:
                return f"arq:{num_pad}", num_pad

    return s, None


def resolver_canon(classe, canon, numero_sem_serie=None):
    """Passo 2 da spec §3.
    Busca exata em chave_humana; se zero, busca em entidade_alias.
    Retorna lista de candidatos [{'id': ..., 'chave_humana': ..., 'via': ...}].
    """
    if numero_sem_serie:
        sql = """
        select coalesce(json_agg(row_to_json(t)), '[]') from (
          select e.id, e.chave_humana, 'exato' as via
            from acervo.entidade e
           where e.classe = {classe}
             and (e.chave_humana = {canon} or e.chave_humana like '%:' || {num})
          union all
          select e.id, e.chave_humana, 'alias' as via
            from acervo.entidade e
            join acervo.entidade_alias a on a.entidade_id = e.id
           where e.classe = {classe}
             and (a.alias = {canon} or a.alias = {num})
             and not exists (
               select 1 from acervo.entidade e2
                where e2.classe = {classe}
                  and (e2.chave_humana = {canon} or e2.chave_humana like '%:' || {num})
             )
        ) t;
        """.format(classe=_lit(classe), canon=_lit(canon), num=_lit(numero_sem_serie))
    else:
        sql = """
        select coalesce(json_agg(row_to_json(t)), '[]') from (
          select e.id, e.chave_humana, 'exato' as via
            from acervo.entidade e
           where e.classe = {classe} and e.chave_humana = {canon}
          union all
          select e.id, e.chave_humana, 'alias' as via
            from acervo.entidade e
            join acervo.entidade_alias a on a.entidade_id = e.id
           where e.classe = {classe} and a.alias = {canon}
             and not exists (
               select 1 from acervo.entidade e2
                where e2.classe = {classe} and e2.chave_humana = {canon}
             )
        ) t;
        """.format(classe=_lit(classe), canon=_lit(canon))

    return psql_json(sql, "resolver_canon")


def _parecidos_casa(especie, seletor):
    """Chaves parecidas DENTRO da especie, em acervo.casa (arq:0115 §3): pg_trgm sobre a
    chave (ou repo@path, sem chave) e sobre o titulo."""
    rows = psql_json(
        """
        select coalesce(json_agg(row_to_json(t) order by t.sim desc), '[]') from (
          select u.candidato, u.sim from (
            select coalesce(c.chave, c.repo || '@' || c.path) as candidato,
                   greatest(similarity(coalesce(c.chave, c.path), {alvo}),
                            similarity(coalesce(c.titulo, ''), {alvo})) as sim
              from acervo.casa c
              join acervo.especie_tipo e on e.id = c.especie_id
             where e.slug = {especie}
          ) u where u.sim > 0.2 order by u.sim desc, u.candidato limit 5
        ) t;
        """.format(alvo=_lit(seletor), especie=_lit(especie)), "parecidos"
    )
    return [r["candidato"] for r in rows[:5]]


def _varrido_casa():
    """Linha `varrido:` da leitura de casa: SO o ponteiro do suporte (arq:0115 §1.2) em
    casa_fonte. As fontes de antes da arq:0115 (repos de release) seguem em casa_fonte, porque
    o servidor so insere; nao se nomeiam aqui. Linhas vivas vindas delas entram como contagem."""
    cf = psql_json(
        "select coalesce(json_agg(row_to_json(t)), '[]') from ("
        "  select sha, to_char(ingerido_em, 'DD/MM HH24:MI') as dt from acervo.casa_fonte"
        "   where repo = %s order by ingerido_em desc limit 1"
        ") t;" % _lit(SUPORTE), "casa_fonte"
    )
    legado = psql_json(
        "select json_build_object('n', count(*)) from acervo.casa "
        "where repo <> %s and retirada_em is null;" % _lit(SUPORTE), "legado"
    )
    fonte = (f"fonte {SUPORTE}@{cf[0]['sha'][:12]}, ingerido {cf[0]['dt']}" if cf
             else f"fonte {SUPORTE}: nunca ingerida")
    n = int(legado.get("n") or 0) if isinstance(legado, dict) else 0
    extra = f"; {n} linha(s) viva(s) de antes do suporte (legado)" if n else ""
    return f"acervo.casa ({fonte}{extra})"

def gerar_negativa(classe, seletor, casa=False):
    """Gera as 4 linhas fixas da spec §4 para exit 1.

    casa=True: `classe` e especie de acervo.especie_tipo e o seletor e chave de documento
    de casa (arq:0115 §3); parecidos vem das chaves de acervo.casa. Senao, `classe` e classe
    da raiz e parecidos vem de chave_humana/alias."""
    # 3 e 4. vizinho e cura: documento de casa mora no suporte platafirma-casa e entra pela
    # ingestao por sha (arq:0115 §1.2, §8.1); nada de caminho de repo de release.
    if casa:
        top = _parecidos_casa(classe, seletor)
        parecidos_str = ", ".join(top) if top else "(nenhuma chave parecida)"
        vizinho = f"acervo listar casa {classe}"
        cura = (f"documento de casa entra por git: PR em {SUPORTE} -> merge em main -> "
                f"acervo ingerir casa {SUPORTE}")
        return (
            f"varrido:   {_varrido_casa()}\n"
            f"parecidos: {parecidos_str}\n"
            f"vizinho:   {vizinho}\n"
            f"cura:      {cura}"
        )

    # 1. varrido: um ponteiro por repositorio (spec_acervo §2): o ultimo sha ingerido de CADA
    # repo em casa_fonte. Sem linha nenhuma, o acervo declara que nao sabe de que sha veio.
    cf = psql_json(
        "select coalesce(json_agg(row_to_json(t)), '[]') from ("
        "  select distinct on (repo) repo, sha, to_char(ingerido_em, 'DD/MM HH24:MI') as dt "
        "  from acervo.casa_fonte order by repo, ingerido_em desc"
        ") t;", "casa_fonte"
    )
    if cf:
        varrido = "acervo.casa (" + "; ".join(
            f"{r['repo']}@{r['sha'][:12]}, ingerido {r['dt']}" for r in cf) + ")"
    else:
        varrido = "acervo.casa (sem ponteiro de fonte: nenhuma ingestao registrou sha)"

    # 2. parecidos (pg_trgm)
    parecidos_rows = psql_json(
        """
        select coalesce(json_agg(row_to_json(t)), '[]') from (
          select distinct on (candidato) candidato, alias_de, sim from (
            select e.chave_humana as candidato, null::text as alias_de,
                   similarity(e.chave_humana, {alvo}) as sim
              from acervo.entidade e
             where e.classe = {classe}
            union all
            select a.alias as candidato, e.chave_humana as alias_de,
                   similarity(a.alias, {alvo}) as sim
              from acervo.entidade_alias a
              join acervo.entidade e on e.id = a.entidade_id
             where e.classe = {classe}
          ) sub
          where sim > 0.2
          order by candidato, sim desc
        ) t;
        """.format(alvo=_lit(seletor), classe=_lit(classe)), "parecidos"
    )
    parecidos_rows.sort(key=lambda r: r.get("sim", 0), reverse=True)
    top5 = parecidos_rows[:5]
    if top5:
        p_strs = []
        for r in top5:
            cand = r["candidato"]
            alias_de = r.get("alias_de")
            if alias_de:
                p_strs.append(f"{cand} ({alias_de})")
            else:
                p_strs.append(cand)
        parecidos_str = ", ".join(p_strs)
    else:
        parecidos_str = "(nenhuma chave parecida)"

    # 3. vizinho: a ficha de documento de casa (adr, spec, parecer) se le pela chave em
    # acervo.casa; as demais classes, pelo texto do suporte.
    if classe in ("adr", "spec", "parecer"):
        vizinho = f"acervo listar casa {classe}"
    else:
        vizinho = f"repo procurar {SUPORTE} --termo {seletor}"

    # 4. cura
    cura = (f"documento de casa entra por git: PR em {SUPORTE} -> merge em main -> "
            f"acervo ingerir casa {SUPORTE}")

    return (
        f"varrido:   {varrido}\n"
        f"parecidos: {parecidos_str}\n"
        f"vizinho:   {vizinho}\n"
        f"cura:      {cura}"
    )


def obter_substrato(entidade_id):
    """Passo 3 da spec §3.
    Busca substrato em acervo.entidade_suporte para o entidade_id.
    """
    rows = psql_json(
        """
        select coalesce(json_agg(row_to_json(t)), '[]') from (
          select tipo, endereco, golden
            from acervo.entidade_suporte
           where entidade_id = %s
           order by golden desc, id asc
           limit 1
        ) t;
        """ % _lit(entidade_id), "obter_substrato"
    )
    if not rows:
        return None
    r = rows[0]
    endereco = r["endereco"]
    if "@" in endereco:
        repo, path = endereco.split("@", 1)
    else:
        repo, path = None, endereco
    return {
        "tipo": r["tipo"],
        "endereco": endereco,
        "repo": repo,
        "path": path,
        "golden": r.get("golden", False)
    }


def resolver_identidade(classe, seletor):
    """Pipeline completo de identidade: valida forma, resolve canônico.
    Retorna ficha (dict) ou encerra o processo com o código correto.
    """
    canon, num_sem_serie = validar_forma(classe, seletor)
    cand = resolver_canon(classe, canon, num_sem_serie)
    if not cand:
        diag = gerar_negativa(classe, seletor)
        morre("acervo resolver: '%s' nao existe em '%s'.\n%s"
              % (seletor, classe, diag), 1)
    if len(cand) > 1:
        linhas = [f"  {c['id']}  (via {c['via']}, chave_humana={c['chave_humana']})" for c in cand]
        morre("acervo resolver: '%s' ambiguo em '%s' (%d fichas):\n%s"
              % (seletor, classe, len(cand), "\n".join(linhas)), 2)
    return cand[0]
