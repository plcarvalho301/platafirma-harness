"""metrica com fonte (card #3353): a leitura da partição `log` do acervo, que `dia`, `verbos` e `turnos` usam.

    D5.5  GET /acervo/log/dias               a linhagem: cobertura, motivo e versão do extrator por dia
    D5.7  GET /acervo/log/giros/medida       giros por tool, ato, classe, origem e cadeira (contagem ou latência)
    D5.8  GET /acervo/log/turnos/medida      sessão > turno > giro, sempre por `turno_fonte`

MODULO IMPORTAVEL (como `abertura`): `bin/metrica` o carrega e passa a API, a data de hoje e a pergunta «o
bruto desse dia não existe?». Aqui não se abre arquivo de log: quem lê o bruto é só `lib/oplog`.

DIA SEM PASSADA NÃO É ZERO. O dia fechado que a partição não tem sai `ausente` com o motivo, e nunca com
contagem: `sem_arquivo` (o bruto do dia não existe), `nao_extraido` (existe e a passada não rodou),
`extracao_falhou` (a passada reprovou). O dia ABERTO (hoje) sai `ausente` com `dia_aberto`: D5.1 recusa dia
aberto, e a partição só o recebe depois da meia-noite. Quem quer o número de hoje lê o bruto (`--fonte bruto`).

O QUE A PARTIÇÃO NÃO RESPONDE, e sai declarado em `so_no_bruto` em vez de sumir: D5.7 agrega por dia, hora,
tool, ato, classe, origem e cadeira, então a fita (`ordem_id`), a cadeia de erro, o pedido de ajuda e a
deduplicação por lote só existem no bruto. A partição não leva argumento, e é por isso que `casos`, `tateio` e
`comportamento` ficam no bruto (D5.9).

A CONTA DE ERRO é a da classe do giro (arq:0110 §4): erro é `gramatica`, `negada`, `execucao` ou `interrompida`;
`ok` e `negativa` (o veredito exit 1) não são. O bruto de antes de 15/09 contava `exit != 0` fora de predicado;
as duas contas diferem na `negativa` de verbo que não é predicado, e `negativas` sai à parte para a diferença
não sumir.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

import oplog_extracao as extracao

FONTE = "partição"
BRUTO = "bruto"
MOTIVO_ABERTO = "dia_aberto"

CLASSES = extracao.CLASSES
CLASSES_DE_ERRO = ("gramatica", "negada", "execucao", "interrompida")

# O que o bruto responde e a partição não: o texto do aviso e o ato que o traz.
SO_NO_BRUTO_DIA = ("giros_por_fita", "profundidade_de_cadeia", "giros_de_help")
SO_NO_BRUTO_VERBOS = ("giros_distintos", "erros_distintos", "taxa_distinta", "ajuda", "itens e lotes do transporte")

# Os sinais que `casos`, `tateio` e `comportamento` leem do bruto e que a partição ainda NÃO leva (D1: o giro
# não tem esses campos). Antes do primeiro corte (#3354) cada um precisa atravessar, ou o ato perde a leitura.
SINAIS_QUE_FALTAM = {
    "classe_erro": "tateio, verbos: caminho, faixa, binario, gramatica e recusado; a `classe` do giro os junta em "
                   "negativa, gramatica e negada",
    "evento": "tateio, casos, dia: sem_verbo, cwd_recusado e escrita_recusada; a `classe` os junta com o exit 2 em "
              "gramatica, e a recusa da porta deixa de se separar do uso invalido",
    "verbo recusado": "casos: o nome do verbo que a porta recusou (hoje texto digitado, que não atravessa)",
    "ajuda": "dia, tateio, comportamento: o pedido de ajuda se deduz do argumento (--help), que não atravessa",
    "veredito": "dia, tateio: `repo git ... grep` sem achado é veredito e se deduz do argumento",
    "via": "verbos: o despachante do lote (malote ou run_command) que carrega o item",
    "poda_modo": "verbos: o modo da poda (inteiro, igual, intocavel) dos bytes servidos pelo transporte",
}


def dias_entre(desde: str, ate: str) -> list[str]:
    a, b = date.fromisoformat(desde), date.fromisoformat(ate)
    return [(a + timedelta(days=n)).isoformat() for n in range((b - a).days + 1)]


# --- a cobertura (D5.5) -----------------------------------------------------------------------------

def cobertura(api, dias: list[str], hoje: date, bruto_ausente, detalhe: bool = False) -> list[dict]:
    """Uma linha por dia pedido, todos, em ordem: `{dia, cobertura, motivo, versao_extrator}`. `ausente` leva o
    motivo; `completo` e `parcial` não. Com `detalhe`, também o sha256 e a passada (as contagens que fecham a
    conta do dia). `bruto_ausente(dia)` diz se o arquivo do bruto não existe: separa `sem_arquivo` de
    `nao_extraido`, que a API não sabe (ela só conhece o dia que alguém declarou)."""
    fechados = [d for d in dias if date.fromisoformat(d) < hoje]
    achados: dict[str, dict] = {}
    if fechados:
        _, corpo = api.chamar("GET", "/acervo/log/dias", params={"desde": fechados[0], "ate": fechados[-1]})
        achados = {linha["dia"]: linha for linha in (corpo or {}).get("itens", [])}
    saida = []
    for d in dias:
        if d not in fechados:
            saida.append({"dia": d, "cobertura": "ausente", "motivo": MOTIVO_ABERTO, "versao_extrator": None})
            continue
        linha = achados.get(d) or {}
        cob = linha.get("cobertura") or "ausente"
        motivo = None
        if cob == "ausente":
            motivo = linha.get("motivo") or "nao_extraido"
            if motivo == "nao_extraido" and bruto_ausente(d):
                motivo = "sem_arquivo"
        item = {"dia": d, "cobertura": cob, "motivo": motivo, "versao_extrator": linha.get("versao_extrator")}
        if detalhe and cob != "ausente":
            item["sha256"] = linha.get("sha256")
            item["passada"] = linha.get("passada")
        saida.append(item)
    return saida


def _ausentes(cob: list[dict]) -> list[str]:
    return [c["dia"] for c in cob if c["cobertura"] == "ausente"]


def _versoes(cob: list[dict]) -> list[str]:
    return sorted({c["versao_extrator"] for c in cob if c.get("versao_extrator")})


# --- as medidas (D5.7, D5.8) --------------------------------------------------------------------------

def medir_giros(api, desde: str, ate: str, por: list[str], medida: str = "contagem") -> dict:
    _, corpo = api.chamar("GET", "/acervo/log/giros/medida",
                          params={"desde": desde, "ate": ate, "por": ",".join(por), "medida": medida})
    return corpo or {}


def medir_turnos(api, desde: str, ate: str, por: list[str]) -> dict:
    params = {"desde": desde, "ate": ate}
    if por:
        params["por"] = ",".join(por)
    _, corpo = api.chamar("GET", "/acervo/log/turnos/medida", params=params)
    return corpo or {}


# --- a conta dos giros: uma só, para as duas fontes ---------------------------------------------------

def contas(por_tool_e_classe: Counter, por_origem: Counter) -> dict:
    """As chaves que `metrica dia` dá nas DUAS fontes, com as mesmas regras de agrupamento, para a conferência
    ser uma diferença de dois JSON: giros por tool e classe, por tool, por classe e por origem."""
    por_tool, por_classe = Counter(), Counter()
    for (tool, classe), n in por_tool_e_classe.items():
        por_tool[tool] += n
        por_classe[classe] += n
    def ordem(c: Counter) -> dict:
        return dict(sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0]))))
    return {
        "giros_tipo_giro": sum(por_tool_e_classe.values()),
        "giros_por_origem": ordem(por_origem),
        "giros_por_classe": ordem(por_classe),
        "giros_por_tool": ordem(por_tool),
        "giros_por_tool_e_classe": {f"{t}:{c}": n for (t, c), n in sorted(por_tool_e_classe.items())},
    }


def contas_do_bruto(giros: list[dict]) -> dict:
    """Das linhas do bruto que o dia lê (`giros_do_dia`): só as que a partição guardaria como `giro` entram, pela
    MESMA regra do extrator (`tipo_particao`, `classe_do_giro`, `origem_do_evento`). A linha que não tem
    tradução fica fora e conta em `sem_traducao`."""
    por_tc, por_origem, sem = Counter(), Counter(), Counter()
    for g in giros:
        reg = g["bruto"]
        try:
            if extracao.tipo_particao(reg) != "giro":
                continue
            bloco = extracao.bloco_giro(reg)
        except extracao.SemTraducao as e:
            sem[e.evento] += 1
            continue
        por_tc[(bloco["tool"], bloco["classe"])] += 1
        por_origem[extracao.origem_do_evento(reg)] += 1
    r = contas(por_tc, por_origem)
    if sem:
        r["sem_traducao"] = dict(sorted(sem.items()))
    return r


# --- metrica dia ---------------------------------------------------------------------------------------

def _regra_de_erro() -> dict:
    return {"erro": list(CLASSES_DE_ERRO), "fora_do_erro": [c for c in CLASSES if c not in CLASSES_DE_ERRO]}


def dia_da_particao(api, dia: str, hoje: date, bruto_ausente, cadeira: str | None = None) -> dict:
    """`metrica dia` pela partição. O dia sem passada sai `ausente` com o motivo e sem uma única contagem."""
    cob = cobertura(api, [dia], hoje, bruto_ausente, detalhe=True)
    base = {"dia": dia, "fonte": FONTE, "versao_extrator": cob[0].get("versao_extrator"), "cobertura": cob}
    if cob[0]["cobertura"] == "ausente":
        return {**base, "resultado": "ausente", "motivo": cob[0]["motivo"], "so_no_bruto": list(SO_NO_BRUTO_DIA)}
    por = ["tool", "ato", "classe", "origem"] + (["cadeira"] if cadeira else [])
    series = medir_giros(api, dia, dia, por).get("series", [])
    if cadeira:
        series = [s for s in series if (s.get("chave") or {}).get("cadeira") == cadeira]
    por_tc, por_origem, erros_ato = Counter(), Counter(), defaultdict(Counter)
    negativas = erros = 0
    for s in series:
        chave, n = s.get("chave") or {}, int(s.get("n") or 0)
        tool, classe = chave.get("tool"), chave.get("classe")
        por_tc[(tool, classe)] += n
        por_origem[chave.get("origem")] += n
        if classe in CLASSES_DE_ERRO:
            erros += n
            erros_ato[tool][chave.get("ato") or "-"] += n
        elif classe == "negativa":
            negativas += n
    c = contas(por_tc, por_origem)
    erros_por_verbo = {t: {"total": sum(a.values()), "por_ato": dict(sorted(a.items()))}
                       for t, a in sorted(erros_ato.items(), key=lambda kv: (-sum(kv[1].values()), kv[0] or ""))}
    r = {**base,
         "total": {"giros": c["giros_tipo_giro"], "erros": erros, "negativas": negativas,
                   "por_origem": c["giros_por_origem"]},
         **{k: v for k, v in c.items() if k != "giros_tipo_giro"},
         "giros_tipo_giro": c["giros_tipo_giro"],
         "erros_por_verbo": erros_por_verbo,
         "regra_de_erro": _regra_de_erro(),
         "so_no_bruto": list(SO_NO_BRUTO_DIA)}
    if cadeira:
        r["cadeira"] = cadeira
    return r


# --- metrica verbos ------------------------------------------------------------------------------------

COLS_VERBOS_PARTICAO = ("verbo", "giros", "erros", "taxa", "gramatica", "execucao", "negativa", "negada",
                        "interrompida")


def verbos_da_particao(api, dias: list[str], rotulo: str, hoje: date, bruto_ausente, transporte: tuple,
                       cadeira: str | None = None) -> dict:
    """`metrica verbos` pela partição, numa janela de dias. Dia sem passada fica fora da conta e dentro de
    `cobertura` (e de `dias_sem_log`) com o motivo: a taxa da janela é a dos dias que a partição tem."""
    cob = cobertura(api, dias, hoje, bruto_ausente)
    base = {"dia": rotulo, "dias": dias, "dias_sem_log": _ausentes(cob), "fonte": FONTE,
            "versoes_extrator": _versoes(cob), "cobertura": cob}
    if len(_ausentes(cob)) == len(dias):
        return {**base, "resultado": "ausente", "so_no_bruto": list(SO_NO_BRUTO_VERBOS)}
    por = ["tool", "ato", "classe"] + (["cadeira"] if cadeira else [])
    series = medir_giros(api, dias[0], dias[-1], por).get("series", [])
    if cadeira:
        series = [s for s in series if (s.get("chave") or {}).get("cadeira") == cadeira]
    por_tool: dict = defaultdict(lambda: Counter())
    for s in series:
        chave, n = s.get("chave") or {}, int(s.get("n") or 0)
        por_tool[chave.get("tool")][chave.get("classe")] += n
    linhas = {}
    for tool, cl in por_tool.items():
        giros = sum(cl.values())
        erros = sum(cl[c] for c in CLASSES_DE_ERRO)
        linhas[tool] = {"giros": giros, "erros": erros, "taxa": round(erros / giros, 4) if giros else 0,
                        "gramatica": cl["gramatica"], "execucao": cl["execucao"], "negativa": cl["negativa"],
                        "negada": cl["negada"], "interrompida": cl["interrompida"]}
    verbo = {t: d for t, d in linhas.items() if t not in transporte}
    transp = {t: linhas[t] for t in transporte if t in linhas}
    ordenado = dict(sorted(verbo.items(), key=lambda kv: (-kv[1]["erros"], -kv[1]["giros"], kv[0] or "")))
    tg, te = sum(d["giros"] for d in verbo.values()), sum(d["erros"] for d in verbo.values())
    r = {**base, "por_verbo": ordenado,
         "transporte": dict(sorted(transp.items(), key=lambda kv: -kv[1]["giros"])),
         "total": {"verbos": len(verbo), "giros": tg, "erros": te, "taxa": round(te / tg, 4) if tg else 0},
         "regra_de_erro": _regra_de_erro(),
         "so_no_bruto": list(SO_NO_BRUTO_VERBOS)}
    if cadeira:
        r["cadeira"] = cadeira
    return r


def verbos_csv(r: dict) -> list[str]:
    """Uma linha por verbo. As colunas são as da partição (a conta de erro é a da classe), e não as da planilha
    antiga: `giros_distintos`, `erros_distintos`, `taxa_distinta` e `ajuda` só o bruto tem."""
    linhas = [",".join(COLS_VERBOS_PARTICAO)]
    for t, d in r.get("por_verbo", {}).items():
        linhas.append(",".join([t or "-"] + [str(d[c]) for c in COLS_VERBOS_PARTICAO[1:]]))
    return linhas


# --- metrica turnos ------------------------------------------------------------------------------------

POR_TURNOS = ("dia", "superficie", "cadeira", "origem")


def turnos_da_particao(api, dias: list[str], rotulo: str, hoje: date, bruto_ausente, por: list[str]) -> dict:
    """`metrica turnos` pela partição (D5.8). `turno_fonte` está na chave de toda série, e nada aqui soma séries
    de fontes diferentes. Série sem `turno_fonte` é contrato violado: levanta, não completa."""
    cob = cobertura(api, dias, hoje, bruto_ausente)
    base = {"dia": rotulo, "dias": dias, "dias_sem_log": _ausentes(cob), "fonte": FONTE,
            "versoes_extrator": _versoes(cob), "cobertura": cob, "por": por}
    if len(_ausentes(cob)) == len(dias):
        return {**base, "resultado": "ausente"}
    r = medir_turnos(api, dias[0], dias[-1], por)
    series = r.get("series", [])
    for s in series:
        if "turno_fonte" not in (s.get("chave") or {}):
            raise extracao.Falha(5, "D5.8 devolveu uma série sem `turno_fonte` na chave: o contrato foi violado "
                                    "e as séries de fontes diferentes não podem ser lidas separadas")
    return {**base, "giros_sem_turno": r.get("giros_sem_turno", 0),
            "turno_fontes": sorted({s["chave"]["turno_fonte"] for s in series}),
            "soma_entre_fontes": "nunca", "series": series}


# --- o texto (--resumo) --------------------------------------------------------------------------------

def _cabecalho(ato: str, r: dict) -> str:
    versao = r.get("versao_extrator") or ", ".join(r.get("versoes_extrator") or []) or "-"
    return f"== metrica {ato} — {r['dia']} · fonte: {r['fonte']} · extrator {versao} =="


def _cobertura_texto(cob: list[dict]) -> list[str]:
    if len(cob) == 1:
        c = cob[0]
        return [f"cobertura: {c['cobertura']}" + (f" ({c['motivo']})" if c.get("motivo") else "")]
    conta = Counter(c["cobertura"] for c in cob)
    linhas = ["cobertura: " + " · ".join(f"{k}={v}" for k, v in sorted(conta.items()))]
    for c in cob:
        if c["cobertura"] != "completo":
            linhas.append(f"  {c['dia']}  {c['cobertura']}" + (f" ({c['motivo']})" if c.get("motivo") else ""))
    return linhas


def dia_texto(r: dict) -> list[str]:
    linhas = [_cabecalho("dia", r), *_cobertura_texto(r["cobertura"])]
    if r.get("resultado") == "ausente":
        linhas.append(f"ausente: {r['motivo']} — a partição não tem esse dia, e dia sem passada não é zero")
        return linhas
    t = r["total"]
    linhas.append(f"{t['giros']} giros · {t['erros']} erros · {t['negativas']} negativas")
    linhas.append("origem: " + " · ".join(f"{k}={v}" for k, v in t["por_origem"].items()))
    linhas.append("classe: " + " · ".join(f"{k}={v}" for k, v in r["giros_por_classe"].items()))
    linhas.append("")
    linhas.append("giros por verbo (top 15):")
    for k, v in list(r["giros_por_tool"].items())[:15]:
        linhas.append(f"  {v:6d}  {k}")
    linhas.append("")
    linhas.append("erros por verbo:")
    for tool, d in r["erros_por_verbo"].items():
        atos = " ".join(f"{a}={n}" for a, n in d["por_ato"].items())
        linhas.append(f"  {d['total']:6d}  {tool}  ({atos})")
    linhas.append("")
    linhas.append("só no bruto (--fonte bruto): " + ", ".join(r["so_no_bruto"]))
    return linhas


def verbos_texto(r: dict) -> list[str]:
    linhas = [_cabecalho("verbos", r), *_cobertura_texto(r["cobertura"])]
    if r.get("resultado") == "ausente":
        linhas.append("ausente: nenhum dia da janela está na partição")
        return linhas
    t = r["total"]
    linhas.append(f"{t['giros']} giros · {t['erros']} erros · taxa {t['taxa']:.1%} · {t['verbos']} verbos")
    linhas.append(f"{'verbo':16s} {'giros':>6s} {'erros':>6s} {'taxa':>7s} {'gram':>5s} {'exec':>5s} "
                  f"{'negat':>5s} {'negad':>5s} {'inter':>5s}")
    for v, d in r["por_verbo"].items():
        linhas.append(f"{(v or '-'):16s} {d['giros']:6d} {d['erros']:6d} {d['taxa']:7.1%} {d['gramatica']:5d} "
                      f"{d['execucao']:5d} {d['negativa']:5d} {d['negada']:5d} {d['interrompida']:5d}")
    if r.get("transporte"):
        linhas.append("")
        linhas.append("transporte (não é verbo da planilha):")
        for v, d in r["transporte"].items():
            linhas.append(f"  {v:14s} {d['giros']:6d} giros · {d['erros']:5d} erros")
    linhas.append("")
    linhas.append("só no bruto (--fonte bruto): " + ", ".join(r["so_no_bruto"]))
    return linhas


def turnos_texto(r: dict) -> list[str]:
    linhas = [_cabecalho("turnos", r), *_cobertura_texto(r["cobertura"])]
    if r.get("resultado") == "ausente":
        linhas.append("ausente: nenhum dia da janela está na partição")
        return linhas
    linhas.append(f"{len(r['series'])} séries · {r['giros_sem_turno']} giros sem turno (anteriores à #3345) · "
                  f"séries de turno_fonte diferentes não se somam")
    for s in r["series"]:
        chave = " ".join(f"{k}={v}" for k, v in s["chave"].items())
        linhas.append(f"- {chave}: {s.get('sessoes', '-')} sessões · {s.get('turnos', '-')} turnos"
                      + (f" · ajuste: {s['ajuste']}" if s.get("ajuste") else ""))
        linhas.append("    giros por turno: " + " · ".join(f"{k}={v}" for k, v in s["giros_por_turno"].items()))
        linhas.append("    turnos por sessão: " + " · ".join(f"{k}={v}" for k, v in s["turnos_por_sessao"].items()))
    return linhas
