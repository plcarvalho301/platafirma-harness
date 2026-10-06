"""acervo — lint da lista antipadroes-do-acervo sobre acervo.obra (colecao firma) e acervo.conceito.

A lista manda: severidade, o que fere e cura saem da tabela dela; os organismos de
normalizacao (T2) e as palavras funcionais (D7) saem dos Contrapontos dela. O codigo
guarda so o predicado de cada detector mecanico, escrito contra o texto do detector na
rev em DETECTORES. Se a lista mudar o texto de um detector, o criterio nao roda e sai
em `nao_rodou` (trava do #3161: divergencia vira emenda da lista, nao ajuste calado no
codigo); bloqueante que nao rodou torna a medida indeterminavel (exit 5).

Leitura so: um SELECT por chamada, pelo transporte de bin/_acervo/listar (psql no
conteiner do acervo, uma linha, JSON). PF_LINT_ACERVO_PSQL troca o transporte por um
executavel que recebe o SQL no stdin e devolve o JSON — os testes apontam fixture aqui.

O D11 (#3318) e a unica excecao ao SELECT: o universo dele e a saida do HermiT, que o gerador da
projecao formal (platafirma-conhecimento, na release) devolve em JSON. PF_LINT_ACERVO_HERMIT
troca o gerador por fixture.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .lista import resolver_lista

CHAVE_LISTA = "antipadroes-do-acervo"
MARCA_CONFERIDO = "[B-titulo: conferido]"

# texto literal da coluna detector na rev 4 — o predicado abaixo implementa este texto
DETECTORES = {
    "A1": "`titulo` sem espaço e com `-` ou `_`, sem `[B-titulo: conferido]` em `anotacao`",
    "A2": "`titulo` contém ` -- `, ` _ `, `Anna's Archive`, `libgen`, `z-lib` ou sequência hexadecimal de 32 caracteres",
    "A3": "`titulo` sem espaço, sem `-` e sem `_`, sem `[B-titulo: conferido]` em `anotacao`",
    "A4": "`titulo` contém `+`, ou não tem letra minúscula e tem 12 letras ou mais, fora da família ato-normativo e sem `[B-titulo: conferido]` em `anotacao`",
    "T1": "`especie_id` nulo",
    "T2": "espécie `norma-tecnica` e nenhum `emitido_por` na lista de organismos de normalização (Contrapontos)",
    "B1": "campo marcado `exige` para a espécie e nulo na obra",
    "B2": "campo marcado `nao comporta` para a espécie e preenchido na obra",
    "B3": "`dominio_id` nulo",
    "B4": "`dominio_id` preenchido e `subdominio_id` nulo",
    "B6": "obra da espécie `lista-de-verificacao` sem linha de derivação",
    "G6": "obra com `retirada_em` preenchido e `retirada_motivo` nulo",
    "S12": "obra com `retirada_em` preenchido que `acervo listar biblioteca obra --sobre <título da obra>` devolve",
    "C1": "obra com 0 ou 1 linha em `obra_trata_de`",
    "D3": "`outros_rotulos` vazio",
    "D4": "conceito com 0 ou 1 obra viva em `obra_trata_de`",
    "D5": "sem `mais_amplo_id`, sem filho e sem aresta em `conceito_relacao`",
    "D6": "`mais_amplo_id` nulo",
    "D7": "slug com mais de três partes fora das palavras funcionais (Contrapontos)",
    "D8": "slug contém `-vs-`, `-versus-`, `-antes-de-` ou `-depois-de-`",
    "D11": "o HermiT sobre a projeção formal acusa a classe `ref:<slug>` equivalente a `owl:Nothing`; o plano de `acervo definir` e `acervo relacionar` mostra a contagem e os nomes que saem",
}

# detector mecanico na lista que este lint ainda nao roda, e por que
SEM_PREDICADO = {
    "C2": "exige os trechos da obra (banco rag), fora da consulta do lint",
    "D2": "exige a pagina do conceito na wiki, fora da consulta do lint",
}

CAMPOS_INCIDENCIA = ("emitido_por", "publicacao", "id_canonico")
TEMPO_HERMIT = 600  # s; o curar roda o gerador duas vezes por plano, aqui e uma

SQL_ESQUEMA = """
select json_build_object(
  'incidencia', (select count(*) = 3 from information_schema.columns
                 where table_schema = 'acervo' and table_name = 'especie_tipo'
                   and column_name in ('incide_emitido_por','incide_publicacao','incide_id_canonico')),
  'derivacao', to_regclass('acervo.obra_deriva_de') is not null,
  'motivo_retirada', exists (select 1 from information_schema.columns
                 where table_schema = 'acervo' and table_name = 'obra'
                   and column_name = 'retirada_motivo'));
"""

# toda obra retirada, de qualquer colecao: G vale tambem para a pessoal (a lista, "Como se le")
SQL_RETIRADA = """
select coalesce(json_agg(row_to_json(t) order by t.id), '[]') from (
  select r.id, r.titulo, r.retirada_motivo is not null as tem_motivo
  from acervo.obra r
  where r.retirada_em is not null
) t;
"""

# obra viva da colecao firma; incide_* por to_jsonb, que devolve nulo se a coluna faltar
SQL_OBRA = """
select coalesce(json_agg(row_to_json(t) order by t.id), '[]') from (
  select o.id, o.titulo, o.anotacao, e.slug as especie, f.slug as familia,
         o.especie_id is not null as tem_especie,
         o.emitido_por, o.publicacao, o.id_canonico,
         to_jsonb(e) ->> 'incide_emitido_por' as incide_emitido_por,
         to_jsonb(e) ->> 'incide_publicacao' as incide_publicacao,
         to_jsonb(e) ->> 'incide_id_canonico' as incide_id_canonico,
         o.dominio_id is not null as tem_dominio,
         o.subdominio_id is not null as tem_subdominio,
         (select count(*) from acervo.obra_trata_de tr where tr.obra_id = o.id) as n_conceitos,
         {derivacao} as deriva
  from acervo.obra o
  join acervo.colecao c on c.id = o.colecao_id and c.slug = 'firma'
  left join acervo.especie_tipo e on e.id = o.especie_id
  left join acervo.familia_tipo f on f.id = e.familia_id
  where o.retirada_em is null
) t;
"""

SQL_CONCEITO = """
select coalesce(json_agg(row_to_json(t) order by t.slug), '[]') from (
  select c.slug, c.outros_rotulos,
         c.mais_amplo_id is not null as tem_mais_amplo,
         exists (select 1 from acervo.conceito f where f.mais_amplo_id = c.id) as tem_filho,
         exists (select 1 from acervo.conceito_relacao r
                 where r.de_id = c.id or r.para_id = c.id) as tem_aresta,
         (select count(*) from acervo.obra_trata_de tr
          join acervo.obra o on o.id = tr.obra_id
          where tr.conceito_id = c.id and o.retirada_em is null) as n_obras_vivas
  from acervo.conceito c
) t;
"""


class ErroAcervo(Exception):
    def __init__(self, rc: int, msg: str):
        super().__init__(msg)
        self.rc = rc
        self.msg = msg


# ---------- transporte ----------

def _psql_json(sql: str) -> Any:
    sob = os.environ.get("PF_LINT_ACERVO_PSQL")
    if sob:
        cmd = [sob]
    else:
        cmd = ["docker", "exec", "-i", "rag-extractor-pg", "psql", "-U", "rag", "-d", "rag_extractor",
               "-tA", "-v", "ON_ERROR_STOP=1", "-f", "-"]
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", "unix:///run/user/1001/docker.sock")
    try:
        proc = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=120, env=env)
    except FileNotFoundError:
        raise ErroAcervo(3, f"'{cmd[0]}' nao encontrado — sem transporte ate o acervo")
    except subprocess.TimeoutExpired:
        raise ErroAcervo(3, "consulta ao acervo passou de 120 s")
    if proc.returncode != 0:
        raise ErroAcervo(3, f"psql falhou (rc={proc.returncode}): {(proc.stderr or '').strip()[:300]}")
    try:
        return json.loads(proc.stdout.strip())
    except ValueError:
        raise ErroAcervo(3, f"acervo nao devolveu JSON: {proc.stdout.strip()[:200]}")


def ler_projecao() -> dict:
    """D11: roda o gerador da projecao formal (platafirma-conhecimento, na release) e devolve o JSON
    dele. Nunca levanta: HermiT fora do ar vira `{"erro": ...}` e so o D11 sai em `nao_rodou`, o
    resto da medida segue. PF_LINT_ACERVO_HERMIT troca o gerador por um executavel que imprime o
    JSON (os testes apontam fixture aqui)."""
    sob = os.environ.get("PF_LINT_ACERVO_HERMIT")
    if sob:
        cmd = [sob]
    else:
        from lib.raizes import release
        raiz = release()
        script = raiz / "conhecimento" / "ontologia" / "projecao" / "gerar-e-raciocinar.py"
        py = os.environ.get("PF_PROJECAO_PYTHON") or str(raiz / "venv" / "acervo" / "bin" / "python")
        if not script.is_file() or not os.path.isfile(py):
            return {"erro": f"sem o gerador ({script}) ou o venv acervo ({py}) na release"}
        cmd = [py, str(script), "--json"]
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", "unix:///run/user/1001/docker.sock")  # o gerador le o banco por docker exec
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TEMPO_HERMIT, env=env, check=False)
    except FileNotFoundError:
        return {"erro": f"'{cmd[0]}' nao encontrado"}
    except subprocess.TimeoutExpired:
        return {"erro": f"projecao formal passou de {TEMPO_HERMIT} s"}
    if proc.returncode != 0:
        return {"erro": f"gerador falhou (rc={proc.returncode}): {(proc.stderr or proc.stdout).strip()[-300:]}"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"erro": f"gerador nao devolveu JSON: {proc.stdout.strip()[-200:]}"}


def ler_achadas(retiradas: List[dict]) -> Tuple[Optional[Dict[str, bool]], str]:
    """S12 (#3317): roda o `acervo listar biblioteca obra --sobre <título> --json` de verdade para cada
    obra retirada e diz se o id dela volta. Mede o verbo servido, não uma cópia do SQL dele. Devolve
    ({id: achada}, "") ou (None, motivo) quando o verbo não respondeu: sem medida nunca vira zero.
    PF_LINT_ACERVO_LISTAR troca o verbo por fixture."""
    exe = os.environ.get("PF_LINT_ACERVO_LISTAR") or str(Path(__file__).resolve().parents[1] / "acervo")
    achadas: Dict[str, bool] = {}
    for r in retiradas:
        titulo = r.get("titulo") or ""
        if not titulo.strip():
            return None, f"obra retirada {r.get('id')} sem título para o --sobre"
        try:
            p = subprocess.run([exe, "listar", "biblioteca", "obra", "--sobre", titulo, "--json"],
                               capture_output=True, text=True, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            return None, f"acervo listar não respondeu: {e}"
        if p.returncode != 0:
            return None, f"acervo listar saiu {p.returncode}: {(p.stderr or p.stdout).strip()[:200]}"
        try:
            linhas = json.loads(p.stdout.strip() or "[]")
        except ValueError:
            if "nenhuma obra encontrada" in p.stdout:
                linhas = []
            else:
                return None, f"acervo listar --json não devolveu JSON: {p.stdout.strip()[:200]}"
        achadas[r["id"]] = any(str(x.get("id")) == str(r["id"]) for x in linhas if isinstance(x, dict))
    return achadas, ""

def ler_acervo() -> Tuple[Dict[str, bool], List[dict], List[dict], List[dict]]:
    esquema = _psql_json(SQL_ESQUEMA)
    derivacao = ("exists (select 1 from acervo.obra_deriva_de d where d.obra_id = o.id)"
                 if esquema.get("derivacao") else "null::boolean")
    obras = _psql_json(SQL_OBRA.replace("{derivacao}", derivacao))
    conceitos = _psql_json(SQL_CONCEITO)
    retiradas = _psql_json(SQL_RETIRADA) if esquema.get("motivo_retirada") else []
    return esquema, obras, conceitos, retiradas


# ---------- contrapontos da lista ----------

def _contraponto(corpo: str, rotulo: str) -> Optional[List[str]]:
    """Lista separada por virgula que segue `**<rotulo>**` ate o primeiro ponto final."""
    plano = re.sub(r"\s+", " ", corpo)
    m = re.search(r"\*\*" + re.escape(rotulo) + r"\*\*\s*(.+?)\.(?:\s|$)", plano)
    if not m:
        return None
    itens = [x.strip().strip("`") for x in m.group(1).split(",")]
    return [x for x in itens if x] or None


def organismos(corpo: str) -> Optional[List[str]]:
    return _contraponto(corpo, "Organismos de normalização que T2 aceita:")


def palavras_funcionais(corpo: str) -> Optional[List[str]]:
    return _contraponto(corpo, "D7 não conta palavra funcional:")


# ---------- predicados ----------

def _vazio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)


def _conferido(o: dict) -> bool:
    return MARCA_CONFERIDO in (o.get("anotacao") or "")


_HEX32 = re.compile(r"[0-9a-fA-F]{32}")


def a1(o):
    t = o.get("titulo") or ""
    return bool(t) and not re.search(r"\s", t) and ("-" in t or "_" in t) and not _conferido(o)


def a2(o):
    t = o.get("titulo") or ""
    b = t.lower()
    return (" -- " in t or " _ " in t or "anna's archive" in b or "anna’s archive" in b
            or "libgen" in b or "z-lib" in b or bool(_HEX32.search(t)))


def a3(o):
    t = o.get("titulo") or ""
    return (bool(t) and not re.search(r"\s", t) and "-" not in t and "_" not in t
            and not _conferido(o))


def a4(o):
    t = o.get("titulo") or ""
    if not t or _conferido(o):
        return False
    if "+" in t:
        return True
    letras = [c for c in t if c.isalpha()]
    return (not any(c.islower() for c in t) and len(letras) >= 12
            and o.get("familia") != "ato-normativo")


def t2(o, orgs):
    if o.get("especie") != "norma-tecnica":
        return False
    aceitos = {x.upper() for x in orgs}
    for e in o.get("emitido_por") or []:
        e = (e or "").strip().upper()
        if e in aceitos or any(tok in aceitos for tok in re.split(r"[\s/:,\-]+", e)):
            return False
    return True


def b1(o):
    return [c for c in CAMPOS_INCIDENCIA if o.get(f"incide_{c}") == "exige" and _vazio(o.get(c))]


def b2(o):
    return [c for c in CAMPOS_INCIDENCIA if o.get(f"incide_{c}") == "nao-comporta" and not _vazio(o.get(c))]


def b6(o):
    return o.get("especie") == "lista-de-verificacao" and o.get("deriva") is False


def g6(o):
    """Obra retirada sem motivo (#3301): o universo de G6 so tem obras retiradas."""
    return not o.get("tem_motivo")


def d7(c, funcionais):
    fora = {x.lower() for x in funcionais}
    return len([p for p in (c.get("slug") or "").split("-") if p and p not in fora]) > 3


def d8(c):
    s = c.get("slug") or ""
    return any(x in s for x in ("-vs-", "-versus-", "-antes-de-", "-depois-de-"))


def d11_sem_medida(projecao: Optional[dict], conceitos: List[dict]) -> Optional[str]:
    """Por que o D11 nao se mediu, ou None se a projecao serve de medida. Bloqueante sem medida
    torna a chamada indeterminavel (exit 5): HermiT fora do ar nunca vira «0 insatisfaziveis»."""
    if projecao is None:
        return "a projecao formal nao foi pedida a esta chamada"
    if projecao.get("erro"):
        return f"HermiT indisponivel: {projecao['erro']}"
    if "consistente" not in projecao:
        return "o gerador da projecao no ar nao diz se a ontologia e consistente (promover platafirma-conhecimento)"
    if projecao["consistente"] is None:
        return f"o HermiT nao rodou: {projecao.get('levantou') or 'sem causa no retorno'}"
    lidos = (projecao.get("resumo") or {}).get("conceitos")
    if lidos != len(conceitos):
        return (f"a projecao leu {lidos} conceitos e o banco tem {len(conceitos)}: "
                "o gerador caiu no export versionado, nao leu o banco")
    return None


def d11(projecao: dict, conceitos: List[dict]) -> List[Tuple[str, str]]:
    """(alvo, descricao) de cada apontamento do D11. Ontologia inconsistente (ABox) derruba toda
    classe `ref:`: sai um apontamento so, `ontologia`, porque nenhuma classe isolada e a causa."""
    if projecao["consistente"] is False:
        return [("ontologia", "ontologia inconsistente: o HermiT derruba todo referente "
                              f"({projecao.get('levantou') or 'sem causa no retorno'})")]
    slug_de = {c["slug"].replace(".", "_"): c["slug"] for c in conceitos}  # o IRI troca `.` por `_`
    return [(slug_de.get(n, n), f"conceito {slug_de.get(n, n)}: referente insatisfazivel")
            for n in projecao.get("insatisfaziveis") or []]


# ---------- medida ----------

def _rotulo_obra(o: dict, extra: str = "") -> str:
    t = (o.get("titulo") or "").replace("\n", " ")
    t = t if len(t) <= 80 else t[:77] + "..."
    return f"obra {o['id']} «{t}»" + (f" [{extra}]" if extra else "")


def medir(lista: dict, esquema: Dict[str, bool], obras: List[dict], conceitos: List[dict],
          retiradas: Optional[List[dict]] = None, projecao: Optional[dict] = None,
          achadas: Optional[Dict[str, bool]] = None, sem_achadas: str = "") -> dict:
    """Roda os detectores mecanicos da lista. Devolve {criterios, nao_rodou, apontamentos}.
    `retiradas` e o universo de G6 e S12: toda obra retirada, de qualquer colecao. `projecao` e o
    JSON do gerador da projecao formal (D11); sem ele, o D11 sai em `nao_rodou`. `achadas` e o
    retorno de `ler_achadas` (S12); None sai em `nao_rodou` com `sem_achadas` de motivo."""
    corpo = lista.get("corpo", "")
    itens = {i["id"]: i for i in lista.get("itens", []) if i.get("id")}
    orgs = organismos(corpo)
    funcionais = palavras_funcionais(corpo)

    por_obra: Dict[str, Callable[[dict], Any]] = {
        "A1": a1, "A2": a2, "A3": a3, "A4": a4,
        "T1": lambda o: not o.get("tem_especie"),
        "B3": lambda o: not o.get("tem_dominio"),
        "B4": lambda o: o.get("tem_dominio") and not o.get("tem_subdominio"),
        "C1": lambda o: (o.get("n_conceitos") or 0) <= 1,
    }
    por_retirada: Dict[str, Callable[[dict], Any]] = {
        "G6": g6,
        "S12": lambda o: bool((achadas or {}).get(o["id"])),  # o catalogo ainda acha a retirada
    }
    por_conceito: Dict[str, Callable[[dict], Any]] = {
        "D3": lambda c: _vazio(c.get("outros_rotulos")),
        "D4": lambda c: (c.get("n_obras_vivas") or 0) <= 1,
        "D5": lambda c: not c.get("tem_mais_amplo") and not c.get("tem_filho") and not c.get("tem_aresta"),
        "D6": lambda c: not c.get("tem_mais_amplo"),
        "D8": d8,
    }
    nao_rodou: List[dict] = []
    if orgs:
        por_obra["T2"] = lambda o: t2(o, orgs)
    else:
        nao_rodou.append({"id": "T2", "motivo": "lista sem o contraponto dos organismos de normalizacao"})
    if funcionais:
        por_conceito["D7"] = lambda c: d7(c, funcionais)
    else:
        nao_rodou.append({"id": "D7", "motivo": "lista sem o contraponto das palavras funcionais"})
    esperam_esquema = set()
    if esquema.get("incidencia"):
        por_obra["B1"] = b1
        por_obra["B2"] = b2
    else:
        esperam_esquema |= {"B1", "B2"}
    if esquema.get("derivacao"):
        por_obra["B6"] = b6
    else:
        esperam_esquema.add("B6")
    if not esquema.get("motivo_retirada"):
        esperam_esquema.add("G6")

    criterios: Dict[str, dict] = {}
    apontamentos: List[dict] = []
    for cid, item in itens.items():
        det = item.get("detector", "")
        if det.startswith("leitura"):
            continue
        base = {"severidade": item.get("severidade", "aviso"), "o_que_fere": item.get("o_que_fere", ""),
                "cura": item.get("cura", ""), "n": 0}
        if cid in SEM_PREDICADO:
            nao_rodou.append({"id": cid, "severidade": base["severidade"], "motivo": SEM_PREDICADO[cid]})
            continue
        if cid not in DETECTORES:
            nao_rodou.append({"id": cid, "severidade": base["severidade"],
                              "motivo": "criterio novo na lista, sem predicado no lint"})
            continue
        if det != DETECTORES[cid]:
            nao_rodou.append({"id": cid, "severidade": base["severidade"],
                              "motivo": "o texto do detector na lista mudou; o lint implementa o da rev 4"})
            continue
        if cid in esperam_esquema:
            base["nota"] = ("espera a coluna retirada_motivo (migracao 078); acusa 0 ate ela existir"
                            if cid == "G6" else "espera o schema da ont:0092; acusa 0 ate ele existir")
            criterios[cid] = base
            continue
        if cid == "S12" and achadas is None:  # o verbo listar nao respondeu ou nao foi chamado
            nao_rodou.append({"id": cid, "severidade": base["severidade"],
                              "motivo": sem_achadas or "acervo listar nao foi chamado nesta medida"})
            continue
        if cid == "D11":  # o universo e a saida do HermiT, nao uma consulta
            falta = d11_sem_medida(projecao, conceitos)
            if falta:
                nao_rodou.append({"id": cid, "severidade": base["severidade"], "motivo": falta})
                continue
            criterios[cid] = base
            for alvo, descricao in d11(projecao, conceitos):
                base["n"] += 1
                apontamentos.append({"id": cid, "severidade": base["severidade"], "tipo": "conceito",
                                     "alvo": alvo, "descricao": descricao, "cura": base["cura"]})
            continue
        if cid in por_obra:
            f, universo, rot = por_obra[cid], obras, "obra"
        elif cid in por_retirada:
            f, universo, rot = por_retirada[cid], retiradas or [], "obra"
        elif cid in por_conceito:
            f, universo, rot = por_conceito[cid], conceitos, "conceito"
        else:
            continue  # T2/D7 sem contraponto: ja em nao_rodou
        criterios[cid] = base
        for x in universo:
            r = f(x)
            if not r:
                continue
            base["n"] += 1
            if rot == "obra":
                alvo = _rotulo_obra(x, ", ".join(r) if isinstance(r, list) else "")
                ident = x["id"]
            else:
                alvo, ident = f"conceito {x['slug']}", x["slug"]
            apontamentos.append({"id": cid, "severidade": base["severidade"], "tipo": rot,
                                 "alvo": ident, "descricao": alvo, "cura": base["cura"]})
    return {"criterios": criterios, "nao_rodou": nao_rodou, "apontamentos": apontamentos}


def _ordem(cid: str) -> Tuple[str, int]:
    m = re.match(r"([A-Z]+)(\d+)", cid)
    return (m.group(1), int(m.group(2))) if m else (cid, 0)


def relatorio(medida: dict, rev: Any, como_json: bool = False, resumo: bool = False) -> int:
    crit = medida["criterios"]
    total = sum(c["n"] for c in crit.values())
    bloq = sum(c["n"] for c in crit.values() if c["severidade"] == "bloqueante")
    bloq_sem_medida = [x["id"] for x in medida["nao_rodou"] if x.get("severidade") == "bloqueante"]
    ancora = (f"«lint acervo firma: {total} apontamentos, {bloq} bloqueantes — "
              f"{CHAVE_LISTA}@rev{rev}»")
    rc = 5 if bloq_sem_medida else (1 if bloq else 0)

    if como_json:
        payload = {"ancora": ancora, "classe": "acervo", "chave": CHAVE_LISTA, "rev": rev,
                   "exit": rc, "criterios": crit, "nao_rodou": medida["nao_rodou"]}
        if not resumo:
            payload["apontamentos"] = medida["apontamentos"]
        print(json.dumps(payload, ensure_ascii=False))
        return rc

    print(ancora)
    for cid in sorted(crit, key=_ordem):
        c = crit[cid]
        nota = f" ({c['nota']})" if c.get("nota") else ""
        print(f"    {cid:<3} {c['severidade']:<10} {c['n']:>5}  {c['o_que_fere']} — cura {c['cura']}{nota}")
    for x in medida["nao_rodou"]:
        print(f"    {x['id']:<3} nao rodou: {x['motivo']}")
    if bloq_sem_medida:
        print(f"indeterminavel: bloqueante sem medida ({', '.join(bloq_sem_medida)})")
    if not resumo:
        for a in sorted(medida["apontamentos"], key=lambda a: (_ordem(a["id"]), a["descricao"])):
            print(f"    {a['id']}: {a['descricao']}")
    return rc


def filtrar(medida: dict, criterios: Optional[List[str]] = None, so_bloqueantes: bool = False) -> dict:
    """Recorta a medida: so os criterios pedidos (`--criterio`) e/ou so os bloqueantes
    (`--so-bloqueantes`). Criterio que a medida nao conhece e uso errado (exit 2), nunca
    recorte vazio calado (#2856 linha 154: a flag ignorada devolvia 384 KB)."""
    if not criterios and not so_bloqueantes:
        return medida
    conhecidos = set(medida["criterios"]) | {x["id"] for x in medida["nao_rodou"]}
    pedidos = {c.strip().upper() for c in (criterios or []) if c.strip()}
    desconhecidos = sorted(pedidos - conhecidos, key=_ordem)
    if desconhecidos:
        raise ErroAcervo(2, f"criterio fora da medida: {', '.join(desconhecidos)} "
                            f"(da lista: {', '.join(sorted(conhecidos, key=_ordem))})")

    def fica(cid: str, severidade: Optional[str]) -> bool:
        return (not pedidos or cid in pedidos) and (not so_bloqueantes or severidade == "bloqueante")

    return {
        "criterios": {k: v for k, v in medida["criterios"].items() if fica(k, v["severidade"])},
        "nao_rodou": [x for x in medida["nao_rodou"] if fica(x["id"], x.get("severidade"))],
        "apontamentos": [a for a in medida["apontamentos"] if fica(a["id"], a["severidade"])],
    }


def verificar_acervo(como_json: bool = False, resumo: bool = False,
                     criterios: Optional[List[str]] = None, so_bloqueantes: bool = False) -> int:
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ErroAcervo(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")
    esquema, obras, conceitos, retiradas = ler_acervo()
    # o HermiT sobe um Java: so roda se o D11 esta na lista e esta chamada nao o recortou para fora
    quer_d11 = (any(i.get("id") == "D11" for i in lista.get("itens", []))
                and (not criterios or "D11" in {c.strip().upper() for c in criterios}))
    projecao = ler_projecao() if quer_d11 else None
    # S12 chama o verbo listar uma vez por obra retirada: so quando a lista o tem e a chamada o pede
    quer_s12 = (any(i.get("id") == "S12" for i in lista.get("itens", []))
                and (not criterios or "S12" in {c.strip().upper() for c in criterios}))
    achadas, sem_achadas = ler_achadas(retiradas) if quer_s12 else (None, "")
    medida = filtrar(medir(lista, esquema, obras, conceitos, retiradas, projecao, achadas, sem_achadas),
                     criterios, so_bloqueantes)
    return relatorio(medida, lista.get("rev"), como_json, resumo)
