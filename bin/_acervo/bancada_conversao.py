"""Agregador da bancada de conversão (card #3187, a serviço do piloto do #3181).

`acervo listar obra bancada <pasta> [--json] [--estratos <arquivo>]` lê o que `curar --reextrair
… --bancada <pasta>` gravou — `<pasta>/perfil/<obra_id>/relatorio.json` e
`<pasta>/docling/<obra_id>/relatorio.json` —, pareia por obra_id e aplica a regra escrita pelo
card #3181 ANTES de rodar:

    Por obra, vence o método com menos perda e menos trecho irrecuperável (§2.9); empate se
    desfaz por inserção, duplicação e ordem, nessa ordem.

Implementação fixada pela engenharia: chave = (perda_total, irrecuperavel, insercao_total,
duplicacao_total, ordem), onde *_total é a soma dos valores de todos os papéis; menor chave
vence; chave igual = empate (o empate fica com o perfil). Engenharia só mede e reporta: nada
aqui decide adoção.

Cada LADO (método) de uma obra cai em UM estado, nesta precedência (B7):

    pendente > n/a (método não cobre o tipo) > n/a (sem referência) > falha do método >
    medida indeterminada > medido

  pendente        sem relatorio.json válido (ausente, ilegível, versão diferente, só erro.txt,
                  só relatorio.invalido.json, erro.txt ao lado) ou erro_tipo 'indisponivel':
                  a obra NÃO foi obtida, é preciso refazer. Não é n/a e não é falha.
  n/a             aplicavel == false (o método não cobre o tipo); classe C ou fidelidade não
                  aplicável (sem referência).
  falha           o MÉTODO falhou nesta obra: erro com erro_tipo conversao/timeout/subprocesso
                  (ou ausente), blocos == 0, ou reprovado sem métricas E sem fidelidade.erro
                  (reprovado com fidelidade.erro é medida indeterminada, não falha). Imputa-se
                  perda = tamanho_referencia e os demais termos 0.
  indeterminada   a MEDIDA falhou (fidelidade.erro) ou não existe (fidelidade nula com
                  relatório sem erro): nada é imputado; a obra sai do teste principal. Um lado
                  em falha e o outro indeterminado, sem tamanho_referencia em nenhum dos dois,
                  é n/a (sem referência): essa checagem vem antes da indeterminada.

Se algum lado está pendente, o piloto está INCOMPLETO (última linha do Markdown; `completo:
false` no JSON).

SOMENTE stdlib (roda no python do sistema, sem venv). Funções puras, sem rede e sem banco.
"""

from __future__ import annotations

import json
import math
import os
import sys

METODOS = ("perfil", "docling")
# versao_relatorio que o agregador lê: 1 (conversor em subprocesso) e 2 (conversor como serviço, #3205).
VERSOES_RELATORIO = (1, 2)
# Tipos em censo: não se sorteia, reporta-se (vitórias, empates, maior irrecuperável).
TIPOS_CENSO = ("docx", "htm", "html", "mhtml", "txt", "xlsx", "mobi", "pptx")
SEM_ESTRATO = "-"
# erro_tipo que significam "o método falhou nesta obra" (dado). 'indisponivel' e qualquer
# valor desconhecido NÃO estão aqui: o método não rodou / não se sabe, é pendente.
TIPOS_FALHA = ("conversao", "timeout", "subprocesso", "ausente")
NA_METODO = "método não cobre o tipo"
NA_REFERENCIA = "sem referência"

_MIME_CURTO = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/epub+zip": "epub",
    "application/x-mobipocket-ebook": "mobi",
    "application/vnd.amazon.ebook": "mobi",
    "application/json": "json",
    "text/plain": "txt",
    "text/markdown": "md",
    "message/rfc822": "mhtml",
    "multipart/related": "mhtml",
    "application/x-mimearchive": "mhtml",
}

REGRA = ("Regra do card #3181 (escrita antes de rodar): por obra, vence o método com menos perda "
         "e menos trecho irrecuperável (§2.9); empate se desfaz por inserção, duplicação e ordem, "
         "nessa ordem. Chave = (perda, irrecuperável, inserção, duplicação, ordem), cada termo a "
         "soma dos papéis; menor chave vence; chave igual = empate (fica com o perfil). "
         "Precedência por lado (método): pendente > n/a (método não cobre o tipo) > n/a (sem "
         "referência: classe C, fidelidade não aplicável) > falha do método > medida "
         "indeterminada > medido. Pendente = relatorio.json válido ausente (ilegível, versão "
         "diferente, só erro.txt) ou método indisponível no servidor: a obra não foi obtida, fica "
         "fora do teste, é contada por método e o piloto fica INCOMPLETO. Falha do método (erro "
         "de conversão, timeout, subprocesso, blocos=0, reprovado sem métricas e sem "
         "fidelidade.erro) tem perda = "
         "tamanho_referencia e os demais termos 0 (marcado com `!`); sem tamanho_referencia em "
         "nenhum lado a obra é n/a (sem referência), e isso vem antes do empate dos dois "
         "falharem e também antes da medida indeterminada (um lado em falha e o outro com a "
         "medida indeterminada, sem tamanho_referencia em nenhum dos dois, é n/a sem referência). "
         "Medida indeterminada (fidelidade.erro, ou fidelidade nula sem erro; reprovado com "
         "fidelidade.erro também) não é "
         "falha: nada se imputa e a obra sai do teste principal. Variantes de sensibilidade: "
         "contam só as obras com a medida indeterminada em um lado e o outro lado medido "
         "(nem falha, nem n/a, nem indeterminado); leitura adotada: no pior caso para o Docling "
         "cada uma dessas obras conta vitória do perfil, no melhor caso conta vitória do "
         "docling. Indeterminado x falha e os dois lados indeterminados ficam fora das "
         "variantes e do teste principal. Engenharia só mede e reporta.")


# ---------------------------------------------------------------- leitura tolerante

def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def _soma(v):
    """papel->caracteres (dict) ou escalar; ausente/estranho conta 0, nunca levanta."""
    if isinstance(v, dict):
        return sum(x for x in (_num(i) for i in v.values()) if x is not None)
    n = _num(v)
    return n if n is not None else 0


def _dict(v):
    return v if isinstance(v, dict) else {}


def _curto(texto, limite=80):
    t = " ".join(str(texto).split())
    return t if len(t) <= limite else t[: limite - 1] + "…"


def tipo_curto(*relatorios):
    """Tipo curto da obra (pdf, docx, html…): pela assinatura (`tipo`, mime) e, sem ela, pela
    extensão do arquivo. Vale o primeiro relatório que souber."""
    for rel in relatorios:
        if not isinstance(rel, dict):
            continue
        mime = str(rel.get("tipo") or "").split(";")[0].strip().lower()
        ext = os.path.splitext(str(rel.get("arquivo") or ""))[1].lstrip(".").lower()
        if mime in _MIME_CURTO:
            return _MIME_CURTO[mime]
        if mime in ("text/html", "application/xhtml+xml"):
            return ext if ext in ("htm", "html") else "html"
        if ext:
            return ext
        if mime:
            return mime.rsplit("/", 1)[-1].rsplit("+", 1)[-1]
    return "?"


def _ler_obra(pasta_obra):
    """(relatorio, None) se a pasta da obra tem relatorio.json VÁLIDO; senão (None, problema) =
    lado PENDENTE. Válido: JSON objeto, versao_relatorio 1 ou 2 e nenhum erro.txt ao lado (o
    cliente só deixa erro.txt onde não há relatório válido; os dois juntos = rodada suspeita)."""
    tem_erro = os.path.isfile(os.path.join(pasta_obra, "erro.txt"))
    caminho = os.path.join(pasta_obra, "relatorio.json")
    if not os.path.isfile(caminho):
        if os.path.isfile(os.path.join(pasta_obra, "relatorio.invalido.json")):
            return None, "só relatorio.invalido.json (gravação ou conferência falhou)"
        if tem_erro:
            return None, "só erro.txt (obra não obtida)"
        return None, "sem relatorio.json"
    try:
        with open(caminho, encoding="utf-8") as f:
            rel = json.load(f)
    except (OSError, ValueError):
        return None, "relatório ilegível"
    if not isinstance(rel, dict):
        return None, "relatório ilegível"
    if rel.get("versao_relatorio") not in VERSOES_RELATORIO:
        return None, "versão do relatório %s fora de 1 e 2" % _curto(repr(rel.get("versao_relatorio")), 20)
    if tem_erro:
        return None, "erro.txt ao lado do relatório (rodada não concluída)"
    return rel, None


def ler_relatorios(pasta):
    """{metodo: {obra_id: (relatorio|None, problema|None)}}. TODA pasta de obra entra: sem
    relatorio.json válido ela vale (None, problema), isto é, PENDENTE — nunca some da conta."""
    achado = {m: {} for m in METODOS}
    for metodo in METODOS:
        raiz = os.path.join(pasta, metodo)
        if not os.path.isdir(raiz):
            continue
        for nome in sorted(os.listdir(raiz)):
            pasta_obra = os.path.join(raiz, nome)
            if nome.startswith(".") or not os.path.isdir(pasta_obra):
                continue
            achado[metodo][nome] = _ler_obra(pasta_obra)
    return achado


def ler_estratos(caminho):
    """TSV `obra_id<TAB>estrato`; prefixo do id basta; linhas vazias e '#' ignoradas; uma
    linha de cabeçalho `obra_id<TAB>estrato` é aceita. Levanta OSError/ValueError."""
    estratos = {}
    with open(caminho, encoding="utf-8") as f:
        for n, linha in enumerate(f.read().splitlines(), 1):
            if not linha.strip() or linha.lstrip().startswith("#"):
                continue
            partes = linha.split("\t", 1)
            if len(partes) < 2 or not partes[0].strip() or not partes[1].strip():
                raise ValueError("%s:%d: esperado obra_id<TAB>estrato" % (caminho, n))
            chave, valor = partes[0].strip().lower(), partes[1].strip()
            if chave in ("obra_id", "obra") and valor.lower() == "estrato":
                continue
            estratos[chave] = valor
    return estratos


def estrato_de(obra_id, estratos):
    if not estratos:
        return SEM_ESTRATO
    oid = obra_id.lower()
    if oid in estratos:
        return estratos[oid]
    melhor = None
    for chave, valor in estratos.items():
        if oid.startswith(chave) and (melhor is None or len(chave) > len(melhor[0])):
            melhor = (chave, valor)
    return melhor[1] if melhor else SEM_ESTRATO


# ---------------------------------------------------------------- decisão por obra

def _lado_vazio():
    return {
        "presente": False, "estado": "pendente", "problema": None,
        "aplicavel": None, "fid_aplicavel": None, "motivo_fid": None, "classe": None,
        "reprovado": False, "erro": None, "erro_tipo": None, "falha": None,
        "indeterminada": None, "imputada": False, "ref": None, "blocos": None,
        "perda": None, "insercao": None, "duplicacao": None, "ordem": None,
        "irrecuperavel": None, "converter_ms": None, "total_ms": None,
    }


def _lado(rel, problema=None):
    """O que a regra precisa de UM método numa obra e o ESTADO dele (B7): pendente | na_metodo |
    na_ref | falha | indeterminada | medido. Campo ausente = ausente, nunca KeyError."""
    lado = _lado_vazio()
    if rel is None:
        lado["problema"] = problema or "sem relatório"
        return lado
    fid = rel["fidelidade"] if isinstance(rel.get("fidelidade"), dict) else None
    cab = _dict(rel.get("cabecalho"))
    tempos = _dict(rel.get("tempos_ms"))
    erro = rel.get("erro") or None
    # relatório antigo, com 'erro' e sem 'erro_tipo', vale "conversao"
    erro_tipo = (rel.get("erro_tipo") or "conversao") if erro else None
    if erro and erro_tipo not in TIPOS_FALHA:
        # 'indisponivel' = o método não roda no ambiente: NÃO é resultado do método, refazer.
        # Valor desconhecido: não se sabe o que significa, também não se conta como dado.
        lado["erro_tipo"] = str(erro_tipo)
        lado["problema"] = ("método indisponível no servidor (refazer): " if erro_tipo == "indisponivel"
                            else "erro_tipo desconhecido %s: " % _curto(repr(erro_tipo), 20)) + _curto(erro, 60)
        return lado
    fid_f = fid or {}
    blocos = _num(cab.get("blocos"))
    classe = str(rel.get("classe") or fid_f.get("classe") or "").upper() or None
    tem_metricas = bool(fid) and fid.get("aplicavel") is not False and not fid.get("erro") \
        and isinstance(fid.get("perda"), dict)
    lado.update(
        presente=True,
        aplicavel=rel.get("aplicavel") is not False,
        fid_aplicavel=(fid.get("aplicavel") is not False) if fid else None,
        motivo_fid=fid_f.get("motivo"),
        classe=classe,
        reprovado=rel.get("reprovado") is True,
        erro=_curto(erro) if erro else None,
        erro_tipo=erro_tipo,
        ref=_num(fid_f.get("tamanho_referencia")),
        blocos=blocos,
        converter_ms=_num(tempos.get("converter")),
        total_ms=_num(tempos.get("total")),
    )
    if rel.get("aplicavel") is False:
        lado["estado"] = "na_metodo"
    elif classe == "C" or (fid and fid.get("aplicavel") is False):
        lado["estado"] = "na_ref"
    elif erro:
        lado["estado"], lado["falha"] = "falha", "%s: %s" % (erro_tipo, _curto(erro, 60))
    elif blocos == 0:
        lado["estado"], lado["falha"] = "falha", "blocos=0"
    elif rel.get("reprovado") is True and not tem_metricas and not (fid and fid.get("erro")):
        # reprovado sem métricas E sem fidelidade.erro: o método falhou. Com fidelidade.erro a
        # MEDIDA é que falhou (B5, indeterminada), não o método: cai no ramo seguinte.
        lado["estado"], lado["falha"] = "falha", "reprovado sem métricas"
    elif not tem_metricas:
        lado["estado"] = "indeterminada"
        lado["indeterminada"] = ("medida falhou: " + _curto(fid["erro"], 60)) if fid and fid.get("erro") \
            else ("fidelidade sem perda medida" if fid else "fidelidade ausente")
    else:
        lado["estado"] = "medido"
        for campo in ("perda", "insercao", "duplicacao", "ordem", "irrecuperavel"):
            lado[campo] = _soma(fid.get(campo))
    return lado


def chave_de(l):
    return (l["perda"], l["irrecuperavel"], l["insercao"], l["duplicacao"], l["ordem"])


def _detalhe_na(nome, l):
    if l["estado"] == "na_metodo":
        return "%s: %s" % (nome, NA_METODO)
    m = l["motivo_fid"]
    if l["classe"] == "C":
        return "%s: classe C (sem R)" % nome + (": " + _curto(m, 60) if m else "")
    return "%s: fidelidade não aplicável" % nome + (": " + _curto(m, 60) if m else "")


def decidir(obra_id, rp, rd, estrato=SEM_ESTRATO, prob_p=None, prob_d=None):
    """Aplica a regra a UMA obra. Devolve o registro com os dois lados e o `vencedor`
    (perfil|docling|empate|n/a|pendente|indeterminada). Só perfil/docling/empate entram no
    teste principal."""
    lp, ld = _lado(rp, prob_p), _lado(rd, prob_d)
    lados = (("perfil", lp), ("docling", ld))
    classes = [l["classe"] for _, l in lados if l.get("classe")]
    d = {
        "obra_id": obra_id,
        "tipo": tipo_curto(rp, rd),
        "estrato": estrato,
        "classe": "C" if "C" in classes else (classes[0] if classes else None),
        "perfil": lp,
        "docling": ld,
        "vencedor": None,
        "motivo": None,
        "na": None,
        "chave": None,
        "pendentes": [],
        "indeterminados": [],
    }
    # B1: qualquer lado pendente tira a obra do teste (não é n/a, não é falha). Vem antes de tudo,
    # inclusive de o outro lado ser n/a.
    pend = [(n, l) for n, l in lados if l["estado"] == "pendente"]
    if pend:
        d["pendentes"] = [n for n, _ in pend]
        d["vencedor"] = "pendente"
        d["motivo"] = "; ".join("%s: %s" % (n, l["problema"]) for n, l in pend)
        return d
    # B2 antes de B3 (entre lados diferentes também)
    for estado, rotulo in (("na_metodo", NA_METODO), ("na_ref", NA_REFERENCIA)):
        for n, l in lados:
            if l["estado"] == estado:
                d["vencedor"], d["na"], d["motivo"] = "n/a", rotulo, _detalhe_na(n, l)
                return d
    # B5: medida indeterminada em algum lado: nada imputado, fora do teste principal
    ind = [n for n, l in lados if l["estado"] == "indeterminada"]
    if ind and any(l["estado"] == "falha" for _, l in lados) and lp["ref"] is None and ld["ref"] is None:
        # um lado em falha e o outro com a medida indeterminada, sem tamanho_referencia em nenhum
        # dos dois: nao ha o que imputar, e 'sem referencia' vem ANTES de 'medida indeterminada'
        d["vencedor"], d["na"], d["motivo"] = "n/a", NA_REFERENCIA, "sem tamanho_referencia em nenhum dos lados"
        return d
    if ind:
        d["indeterminados"] = ind
        d["vencedor"] = "indeterminada"
        d["motivo"] = "; ".join("%s: %s" % (n, l["indeterminada"]) for n, l in lados
                                if l["estado"] == "indeterminada")
        return d
    # B4: falha imputa o tamanho_referencia próprio, ou o do outro lado se faltar; sem referência
    # em nenhum lado a obra é n/a — e isso vem ANTES do empate por falha dos dois.
    ref = lp["ref"] if lp["ref"] is not None else ld["ref"]
    if ref is None:
        d["vencedor"], d["na"], d["motivo"] = "n/a", NA_REFERENCIA, "sem tamanho_referencia em nenhum dos lados"
        return d
    for _, l in lados:
        if l["estado"] == "falha":
            propria = l["ref"] if l["ref"] is not None else ref
            l.update(perda=propria, insercao=0, duplicacao=0, ordem=0, irrecuperavel=0,
                     imputada=True)
    if lp["estado"] == "falha" and ld["estado"] == "falha":
        d["vencedor"], d["motivo"] = "empate", "os dois falharam"
        return d
    kp, kd = chave_de(lp), chave_de(ld)
    d["chave"] = {"perfil": list(kp), "docling": list(kd)}
    if kp < kd:
        d["vencedor"] = "perfil"
    elif kd < kp:
        d["vencedor"] = "docling"
    else:
        d["vencedor"], d["motivo"] = "empate", "chave igual"
    return d


# ---------------------------------------------------------------- estatística

def teste_do_sinal(vit_perfil, vit_docling):
    """Teste do sinal exato, empates descartados: X~Binomial(n, 0.5), n = wp + wd.
    bilateral = min(1, 2*P(X<=min(wp,wd))); unilateral (docling>perfil) = P(X>=wd)."""
    n = vit_perfil + vit_docling
    if n == 0:
        return {"n": 0, "p_bilateral": None, "p_unilateral": None}
    menor = min(vit_perfil, vit_docling)
    cauda = sum(math.comb(n, k) for k in range(0, menor + 1))
    uni = sum(math.comb(n, k) for k in range(vit_docling, n + 1))
    return {"n": n, "p_bilateral": min(1.0, 2 * cauda / 2 ** n), "p_unilateral": uni / 2 ** n}


def _variante(vit_perfil, vit_docling):
    """Uma variante de sensibilidade: só n, vitórias e p unilateral."""
    s = teste_do_sinal(vit_perfil, vit_docling)
    return {"n": s["n"], "vitorias_perfil": vit_perfil, "vitorias_docling": vit_docling,
            "p_unilateral": s["p_unilateral"]}


def mediana(valores):
    xs = sorted(v for v in valores if _num(v) is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def resumir(decs, modo):
    """Resumo de um grupo de obras. modo: 'amostrado' (com p e sensibilidade), 'censo' (com maior
    irrecuperável) ou 'total' (só contagens)."""
    testadas = [d for d in decs if d["vencedor"] in ("perfil", "docling", "empate")]
    nas = [d for d in decs if d["vencedor"] == "n/a"]
    # falha / medida indeterminada só contam em obra que chegou até a comparação (não pendente,
    # não n/a): o lado de uma obra pendente ou n/a não foi avaliado.
    avaliadas = [d for d in decs if d["vencedor"] in ("perfil", "docling", "empate", "indeterminada")]
    r = {
        "obras": len(decs),
        "testadas": len(testadas),
        "vitorias_perfil": sum(1 for d in testadas if d["vencedor"] == "perfil"),
        "vitorias_docling": sum(1 for d in testadas if d["vencedor"] == "docling"),
        "empates": sum(1 for d in testadas if d["vencedor"] == "empate"),
        "n_a": len(nas),
        "n_a_motivos": {},
    }
    for d in nas:
        r["n_a_motivos"][d["na"]] = r["n_a_motivos"].get(d["na"], 0) + 1
    r["n_a_motivos"] = dict(sorted(r["n_a_motivos"].items()))
    r["pendentes"] = {m: sum(1 for d in decs if d[m]["estado"] == "pendente") for m in METODOS}
    r["pendentes_total"] = sum(r["pendentes"].values())
    r["medida_indeterminada"] = {
        m: sum(1 for d in avaliadas if d[m]["estado"] == "indeterminada") for m in METODOS}
    r["falhas"] = {m: sum(1 for d in avaliadas if d[m]["estado"] == "falha") for m in METODOS}
    r["reprovados"] = {m: sum(1 for d in decs if d[m]["presente"] and d[m]["reprovado"])
                       for m in METODOS}
    for campo in ("converter_ms", "total_ms"):
        r["mediana_" + campo] = {
            m: mediana(d[m][campo] for d in decs if d[m]["presente"] and d[m]["aplicavel"])
            for m in METODOS}
    if modo == "amostrado":
        r.update({"sinal_" + k: v for k, v in
                  teste_do_sinal(r["vitorias_perfil"], r["vitorias_docling"]).items()})
        # sensibilidade: SO obra com a medida indeterminada em UM lado e o OUTRO lado medido (nem
        # falha, nem n/a, nem indeterminado). Pior caso para o Docling: todas contam vitória do
        # perfil; melhor caso: todas contam vitória do docling. Indeterminado x falha e os dois
        # lados indeterminados ficam fora das variantes (e do teste principal).
        uma = sum(1 for d in decs if d["vencedor"] == "indeterminada" and len(d["indeterminados"]) == 1
                  and d["perfil" if d["indeterminados"][0] == "docling" else "docling"]["estado"] == "medido")
        r["sensibilidade_pior_caso_docling"] = _variante(r["vitorias_perfil"] + uma, r["vitorias_docling"])
        r["sensibilidade_melhor_caso_docling"] = _variante(r["vitorias_perfil"], r["vitorias_docling"] + uma)
    elif modo == "censo":
        r["maior_irrecuperavel"] = {
            m: max((d[m]["irrecuperavel"] or 0 for d in testadas), default=None)
            for m in METODOS}
    return r


def agregar(pasta, estratos=None):
    achado = ler_relatorios(pasta)
    ids = sorted(set(achado["perfil"]) | set(achado["docling"]))
    decs = []
    for oid in ids:
        rp, pp = achado["perfil"].get(oid, (None, "sem relatorio.json (pasta da obra ausente)"))
        rd, pd = achado["docling"].get(oid, (None, "sem relatorio.json (pasta da obra ausente)"))
        decs.append(decidir(oid, rp, rd, estrato_de(oid, estratos), pp, pd))
    decs.sort(key=lambda d: (d["tipo"], d["estrato"], d["obra_id"]))
    tipos = []
    for tipo in sorted({d["tipo"] for d in decs}):
        grupo = [d for d in decs if d["tipo"] == tipo]
        modo = "censo" if tipo in TIPOS_CENSO else "amostrado"
        item = {"tipo": tipo, "regime": modo}
        item.update(resumir(grupo, modo))
        if tipo == "pdf" and estratos is not None:
            item["estratos"] = []
            for est in sorted({d["estrato"] for d in grupo}):
                sub = {"estrato": est}
                sub.update(resumir([d for d in grupo if d["estrato"] == est], modo))
                item["estratos"].append(sub)
        tipos.append(item)
    total = resumir(decs, "total")
    return {"pasta": pasta, "regra": REGRA, "empate_fica_com": "perfil",
            "completo": total["pendentes_total"] == 0,
            "obras": decs, "tipos": tipos, "total": total}


# ---------------------------------------------------------------- saída

def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else "%.1f" % v
    return str(v)


def _p(v):
    if v is None:
        return "-"
    return "%.4f" % v if v >= 0.0001 or v == 0 else "%.2e" % v


def _esc(s):
    return str(s).replace("|", "/").replace("\n", " ")


def _par(d, campo, marca=False):
    partes = []
    for m in METODOS:
        l = d[m]
        v = _fmt(l.get(campo)) if l["presente"] else "-"
        if marca and l["presente"] and l.get("imputada"):
            v += "!"
        partes.append(v)
    return " / ".join(partes)


def _vencedor_cell(d):
    if d["vencedor"] == "n/a":
        return "n/a: " + _esc(d["motivo"])
    if d["vencedor"] == "pendente":
        return "pendente: " + _esc(d["motivo"])
    if d["vencedor"] == "indeterminada":
        return "medida indeterminada: " + _esc(d["motivo"])
    if d["vencedor"] == "empate" and d["motivo"] == "os dois falharam":
        return "empate (os dois falharam)"
    return d["vencedor"]


def _bloco_resumo(r, modo):
    linhas = []
    linhas.append("- obras: %d · testadas: %d · vitórias perfil %d · docling %d · empates %d · "
                  "n/a %d · pendentes %d · medida indeterminada %d"
                  % (r["obras"], r["testadas"], r["vitorias_perfil"], r["vitorias_docling"],
                     r["empates"], r["n_a"], r["pendentes_total"],
                     sum(r["medida_indeterminada"].values())))
    if r["n_a_motivos"]:
        linhas.append("- n/a por motivo: " + " · ".join(
            "%s %d" % (k, v) for k, v in r["n_a_motivos"].items()))
    if modo == "amostrado":
        linhas.append("- teste do sinal principal (empates descartados): n=%d · p bilateral %s · "
                      "p unilateral (docling>perfil) %s"
                      % (r["sinal_n"], _p(r["sinal_p_bilateral"]), _p(r["sinal_p_unilateral"])))
        for rotulo, chave in (("pior caso para o Docling", "sensibilidade_pior_caso_docling"),
                              ("melhor caso para o Docling", "sensibilidade_melhor_caso_docling")):
            v = r[chave]
            linhas.append("- sensibilidade, %s (um lado indeterminado, o outro medido): n=%d · "
                          "vitórias perfil %d · docling %d · p unilateral %s"
                          % (rotulo, v["n"], v["vitorias_perfil"], v["vitorias_docling"],
                             _p(v["p_unilateral"])))
    linhas += ["", "| métrica | perfil | docling |", "|---|---|---|"]

    def linha(nome, dic):
        linhas.append("| %s | %s | %s |" % (nome, _fmt(dic["perfil"]), _fmt(dic["docling"])))

    linha("mediana tempos_ms.converter", r["mediana_converter_ms"])
    linha("mediana tempos_ms.total", r["mediana_total_ms"])
    linha("reprovados", r["reprovados"])
    linha("pendentes (lados não obtidos)", r["pendentes"])
    linha("medida indeterminada (nada imputado)", r["medida_indeterminada"])
    linha("falhas do método (perda imputada)", r["falhas"])
    if modo == "censo":
        linha("maior irrecuperável observado (entre as testadas)", r["maior_irrecuperavel"])
    return linhas


def render_markdown(res):
    out = ["# Bancada de conversão: perfil x docling", "", "pasta: `%s`" % res["pasta"], "",
           REGRA, "", "## (a) Por obra", ""]
    cab = ["obra", "tipo", "estrato", "classe", "perda p / d", "inserção p / d",
           "duplicação p / d", "ordem p / d", "irrecuperável p / d", "converter ms p / d",
           "vencedor"]
    out.append("| " + " | ".join(cab) + " |")
    out.append("|" + "---|" * len(cab))
    for d in res["obras"]:
        out.append("| " + " | ".join([
            d["obra_id"][:8], d["tipo"], _esc(d["estrato"]), d["classe"] or "-",
            _par(d, "perda", marca=True), _par(d, "insercao"), _par(d, "duplicacao"),
            _par(d, "ordem"), _par(d, "irrecuperavel"), _par(d, "converter_ms"),
            _vencedor_cell(d)]) + " |")
    out += ["", "`!` = método falhou: perda imputada = tamanho_referencia (demais termos 0). "
            "`p / d` = perfil / docling.", "", "## (b) Resumo por tipo", ""]
    for t in res["tipos"]:
        out += ["### %s (%s)" % (t["tipo"], "amostrado" if t["regime"] == "amostrado" else "censo"),
                ""] + _bloco_resumo(t, t["regime"]) + [""]
        for e in t.get("estratos", []):
            out += ["#### %s · estrato %s" % (t["tipo"], _esc(e["estrato"])), ""] \
                + _bloco_resumo(e, t["regime"]) + [""]
    tot = res["total"]
    out += ["## (c) Contagem total", ""] + _bloco_resumo(tot, "total")
    if not res["completo"]:
        out += ["", "PILOTO INCOMPLETO: %d lado(s) pendente(s)" % tot["pendentes_total"]]
    return "\n".join(out) + "\n"


def render_json(res):
    return json.dumps(res, ensure_ascii=False, indent=2) + "\n"


def executar(pasta, quero_json=False, arquivo_estratos=None, out=None, err=None):
    """Ponto de entrada de `acervo listar obra bancada`. Devolve o exit code."""
    out = out or sys.stdout
    err = err or sys.stderr
    if not os.path.isdir(pasta):
        err.write("acervo listar obra bancada: pasta inexistente: %s\n" % pasta)
        return 2
    estratos = None
    if arquivo_estratos is not None:
        try:
            estratos = ler_estratos(arquivo_estratos)
        except (OSError, ValueError) as e:
            err.write("acervo listar obra bancada: --estratos: %s\n" % e)
            return 2
    res = agregar(pasta, estratos)
    if not res["obras"]:
        err.write("acervo listar obra bancada: nenhum relatorio.json em %s/perfil nem em "
                  "%s/docling\n" % (pasta, pasta))
        return 1
    out.write(render_json(res) if quero_json else render_markdown(res))
    return 0
