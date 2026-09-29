"""Regras R1 a R9 do censo: a ficha do arquivo contra o catálogo (card #3189, ato temporário).

Só funções puras sobre dicts (uma linha de ficha.jsonl). Não toca banco, balde nem rede.
Cada contradição é um dict {obra_id, regra, clausula, arquivo, catalogo, nota}: o TSV e o resumo saem daí.
Não corrige nada: a cura é decisão de dados depois do levantamento.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

REGRAS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")
CLAUSULAS = {
    "R1": ("formato não confere com a extensão, ou não identificado",),
    "R2": ("fixidez, objeto ausente ou vazio",),
    "R3": ("corte falhou",),
    "R4": ("hierarquia",),
    "R5": ("camada de texto",),
    "R6": ("texto",),
    "R7": ("a expurgada com impressão servindo", "b servindo com 0 trecho",
           "c não expurgada sem impressão servindo", "d perfil 'pdf' em formato com perfil próprio"),
    "R8": ("a mesmo nome_original", "b mesmo título normalizado e mesmo formato", "c título é nome de arquivo"),
    "R9": ("inibidor",),
}
# limiares de partida, decisão de dados (⚪ a revisar na tabela)
ENTRADAS_MIN = 5            # R3: estrutura declarada com 5 ou mais entradas
SECOES_POUCAS = 3           # R3: catálogo com 3 seções ou menos
FRACAO_MAIOR_SECAO = 0.5    # R3: uma seção com mais de 50% do texto
GLIFOS_MAX = 0.20           # R5: mais de 20% de glifos sem caminho para Unicode
_LINGUA = {"por": "pt", "pt-br": "pt", "eng": "en", "spa": "es", "fra": "fr", "fre": "fr", "deu": "de",
           "ger": "de", "ita": "it", "lat": "la", "nld": "nl", "dut": "nl"}
_NOMES_DE_ARQUIVO_OK = re.compile(r"^(?=.*[\d_])[\w.-]+$")   # sem espaço e com dígito ou sublinhado: cara de nome de arquivo


def _c(ficha: dict, regra: str, clausula: str, arquivo, catalogo, nota: str) -> dict:
    return {"obra_id": ficha["obra_id"], "regra": regra, "clausula": clausula,
            "arquivo": _txt(arquivo), "catalogo": _txt(catalogo), "nota": nota}


def _txt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return str(v)


def _norm_titulo(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", t.lower()).strip()


def _lingua_base(v) -> str | None:
    if not v:
        return None
    v = str(v).strip().lower().replace("_", "-")
    base = v.split("-")[0]
    return _LINGUA.get(v) or _LINGUA.get(base) or base


def _formato_id(ficha: dict) -> str | None:
    return ficha.get("formato_id")


def _estrutura_max(ficha: dict) -> tuple[int, int, str | None]:
    """(entradas, profundidade, fonte) da maior estrutura que o arquivo declara."""
    melhor = (0, 0, None)
    for e in ficha.get("estrutura_declarada") or []:
        if (e.get("entradas") or 0) > melhor[0]:
            melhor = (e["entradas"], e.get("profundidade") or 0, e.get("fonte"))
    est = ficha.get("estrutura") or {}
    n = (est.get("sumario_entradas") or {}).get("entradas") or 0
    if n > melhor[0]:
        melhor = (n, 1, "sumario_entradas")
    n = (est.get("indicativos") or {}).get("contagem") or 0
    if n > melhor[0]:
        melhor = (n, (est.get("indicativos") or {}).get("profundidade_max") or 1, "indicativos")
    return melhor


def r1(f: dict) -> list[dict]:
    sit = f.get("situacao_identificacao")
    if sit in ("extensao_diverge", "desconhecido", "disjuncao"):
        nomes = [x.get("nome") for x in f.get("formatos") or []]
        return [_c(f, "R1", "", f"{sit}: {','.join(str(n) for n in nomes) or '-'}", f.get("nome_original"),
                   f"extensão .{f.get('extensao') or '-'} e formato pelos bytes")]
    return []


def r2(f: dict) -> list[dict]:
    out = []
    if f.get("objeto_ausente"):
        out.append(_c(f, "R2", "", "objeto_ausente", f.get("objeto"), "a chave não existe no balde"))
    if f.get("objeto_vazio"):
        out.append(_c(f, "R2", "", "objeto_vazio (0 byte)", f.get("objeto"), "o arquivo-raiz não tem conteúdo"))
    if f.get("fixidez_confere") is False:
        out.append(_c(f, "R2", "", f"sha256 calculado {f.get('sha256_calculado')}", f.get("sha256_guardado"),
                      "fixidez não confere"))
    return out


def r3(f: dict) -> list[dict]:
    cat = f.get("catalogo") or {}
    if not cat.get("impressao_servindo"):
        return []
    secoes = cat.get("secoes_n") or 0
    out = []
    entradas, prof, fonte = _estrutura_max(f)
    if entradas >= ENTRADAS_MIN and secoes <= SECOES_POUCAS:
        out.append(_c(f, "R3", "estrutura", f"{fonte}: {entradas} entradas", f"{secoes} seções",
                      "o arquivo declara estrutura e o corte a perdeu"))
    porte = (f.get("estrutura") or {}).get("porte")
    if porte == "livro" and secoes == 1:
        out.append(_c(f, "R3", "livro", f"livro ({(f.get('estrutura') or {}).get('paginas')} páginas)", "1 seção",
                      "livro cortado em uma seção só"))
    frac = cat.get("maior_secao_fracao")
    if frac is not None and frac > FRACAO_MAIOR_SECAO and secoes > 1:
        out.append(_c(f, "R3", "concentracao", "-", f"maior seção {round(100 * frac)}% do texto",
                      f"{secoes} seções, uma com {cat.get('maior_secao_chars')} caracteres"))
    return out


def r4(f: dict) -> list[dict]:
    cat = f.get("catalogo") or {}
    if not cat.get("impressao_servindo"):
        return []
    out = []
    _, prof, fonte = _estrutura_max(f)
    if prof >= 2 and (cat.get("secoes_n") or 0) > 0 and not cat.get("secoes_n_nivel2"):
        out.append(_c(f, "R4", "nivel2", f"{fonte}: profundidade {prof}", "sem seção de nível 2",
                      "o arquivo declara hierarquia e o catálogo tem um nível só"))
    an = cat.get("secoes_analise") or {}
    if an.get("nivel_diverge_indicativo"):
        out.append(_c(f, "R4", "nivel-indicativo", "-", f"{an['nivel_diverge_indicativo']} seções",
                      "nível do catálogo diferente do número de componentes do indicativo; ex.: "
                      + "; ".join(an.get("nivel_diverge_exemplos") or [])))
    if an.get("irmas_curtas"):
        out.append(_c(f, "R4", "excesso-de-corte", "-", f"{an['irmas_curtas']} seções",
                      "seções de 1 ou 2 palavras irmãs na mesma página; ex.: " + "; ".join(an.get("irmas_exemplos") or [])))
    if an.get("caixa_espacada"):
        out.append(_c(f, "R4", "caixa-espacada", "-", f"{an['caixa_espacada']} seções",
                      "título em caixa espaçada; ex.: " + "; ".join(an.get("caixa_exemplos") or [])))
    return out


def r5(f: dict) -> list[dict]:
    cat = f.get("catalogo") or {}
    ct = (f.get("pdf") or {}).get("camada_texto") or {}
    out = []
    ocr = ct.get("paginas_ocr") or []
    if ocr and cat.get("needs_ocr") is False:
        out.append(_c(f, "R5", "ocr", f"{len(ocr)} páginas no critério de OCR (<500 caracteres úteis e imagem >50%)",
                      "needs_ocr=false", "páginas de imagem servidas como se tivessem texto; ex.: "
                      + ",".join(str(p) for p in ocr[:10])))
    gl = ct.get("paginas_glifos_sem_caminho_gt20") or []
    if gl:
        out.append(_c(f, "R5", "glifos", f"{len(gl)} páginas com >20% de glifos sem caminho para Unicode",
                      cat.get("metodo_perfil"), "camada de texto que sai lixo (⚪ limiar de partida); ex.: "
                      + ",".join(str(p) for p in gl[:10])))
    if ct.get("marcado_com_fontes_sem_mapeamento"):
        out.append(_c(f, "R5", "marcado", "PDF marcado com fontes sem mapeamento", "-", "viola ISO 32000-2 14.8.2.6"))
    return out


def r6(f: dict) -> list[dict]:
    out = []
    enc = f.get("encoding") or {}
    if enc.get("declarado_bate") is False:
        out.append(_c(f, "R6", "charset", f"declarado {enc.get('declarado')}", f"detectado {enc.get('detectado')}",
                      "charset declarado diferente do detectado"))
    txt = f.get("texto") or {}
    if (txt.get("substituicao") or 0) > 0:
        out.append(_c(f, "R6", "substituicao", f"{txt['substituicao']} U+FFFD", "-", "caractere de substituição no texto"))
    nfc = (txt.get("normalizacao_unicode") or {}).get("nfc")
    if nfc is False:
        out.append(_c(f, "R6", "nfc", "não está em NFC", "-", "texto fora da forma de normalização NFC"))
    decl, det = _lingua_base(f.get("lingua_declarada")), _lingua_base((txt.get("lingua_detectada") or {}).get("codigo"))
    if decl and det and decl != det:
        out.append(_c(f, "R6", "lingua", f"declarada {f.get('lingua_declarada')}", f"detectada {det}",
                      "língua declarada diferente da detectada"))
    return out


def r7(f: dict) -> list[dict]:
    cat = f.get("catalogo") or {}
    out = []
    if cat.get("expurgada") and cat.get("impressao_servindo"):
        out.append(_c(f, "R7", "a", "-", "expurgada com impressão servindo", "obra expurgada ainda serve"))
    if cat.get("impressao_servindo") and (cat.get("trechos_n") or 0) == 0:
        out.append(_c(f, "R7", "b", "-", "impressão servindo com 0 trecho", "serve e não tem texto: nenhuma busca a acha"))
    if not cat.get("expurgada") and not cat.get("impressao_servindo"):
        out.append(_c(f, "R7", "c", "-", f"sem impressão servindo (estados: {_txt(cat.get('impressoes_por_estado'))})",
                      "obra viva que nada serve"))
    fid = f.get("formato_id")
    if cat.get("impressao_servindo") and str(cat.get("metodo_perfil") or "").lower() == "pdf" and fid and fid != "pdf":
        out.append(_c(f, "R7", "d", f"formato {fid}", "perfil 'pdf' (rótulo padrão)",
                      "perfil não é formato: o formato tem perfil estrutural próprio"))
    return out


def r9(f: dict) -> list[dict]:
    inib = f.get("inibidor")
    if inib and inib.get("tipo") != "Font obfuscation":
        return [_c(f, "R9", "", f"{inib.get('tipo')}: {inib.get('alvo')}", "-", "o arquivo tem inibidor de leitura")]
    return []


def avaliar_obra(f: dict) -> list[dict]:
    """Contradições de uma obra por R1 a R7 e R9 (R8 é entre obras: `avaliar_identidade`)."""
    if f.get("erro") and not f.get("objeto_ausente"):
        return []
    out: list[dict] = []
    for regra in (r1, r2, r3, r4, r5, r6, r7, r9):
        out += regra(f)
    return out


def avaliar_identidade(fichas: list[dict]) -> list[dict]:
    """R8: candidatos a identidade (lista, não veredito)."""
    out: list[dict] = []
    por_nome: dict[str, list[dict]] = defaultdict(list)
    por_titulo: dict[tuple, list[dict]] = defaultdict(list)
    for f in fichas:
        cat = f.get("catalogo") or {}
        if cat.get("expurgada"):
            continue
        nome = f.get("nome_original")
        if nome:
            por_nome[nome].append(f)
        t = _norm_titulo(cat.get("titulo") or "")
        if t and f.get("formato_id"):
            por_titulo[(t, f["formato_id"])].append(f)
        # ont:0091 A1: título que é nome de arquivo
        titulo = (cat.get("titulo") or "").strip()
        if titulo and (titulo == nome or (" " not in titulo and _NOMES_DE_ARQUIVO_OK.match(titulo))
                       or titulo.lower().endswith(tuple("." + e for e in ("pdf", "epub", "md", "html", "htm", "txt", "mobi", "docx")))):
            out.append(_c(f, "R8", "c", f"nome_original {nome}", f"título '{titulo[:80]}'", "o título da obra é nome de arquivo"))
    for nome, grupo in sorted(por_nome.items()):
        if len(grupo) > 1:
            ids = ",".join(g["obra_id"][:8] for g in grupo)
            for g in grupo:
                out.append(_c(g, "R8", "a", f"nome_original {nome}", f"obras {ids}", "mesmo nome de arquivo em obras diferentes"))
    for (t, fmt), grupo in sorted(por_titulo.items()):
        if len(grupo) > 1:
            ids = ",".join(g["obra_id"][:8] for g in grupo)
            for g in grupo:
                out.append(_c(g, "R8", "b", f"formato {fmt}", f"título '{t[:60]}' em {ids}", "mesmo título normalizado e mesmo formato"))
    return out


# casos que o card manda o estágio 1 reproduzir: (nome, casamento por prefixo de obra_id ou regex do arquivo, regra)
CASOS_CONHECIDOS = (
    {"caso": "Bringhurst (nav do EPUB, 1 seção)", "prefixo": "dc9412e9", "regra": "R3"},
    {"caso": "LoC Formats (5 seções no HTML, 1 no catálogo)", "prefixo": "3aedf83b", "regra": "R3"},
    {"caso": "e-ARQ Brasil v2 (0d9fc4f8): texto numa seção só", "prefixo": "0d9fc4f8", "regra": "R3"},
    {"caso": "e-ARQ Brasil v2 (0d9fc4f8): duas obras, um documento", "prefixo": "0d9fc4f8", "regra": "R8"},
    {"caso": "e-ARQ Brasil v2 (af864268): duas obras, um documento", "prefixo": "af864268", "regra": "R8"},
    {"caso": "Tschichold: 55 seções e caixa espaçada", "prefixo": "5ed120e6", "regra": "R4"},
    {"caso": "NBR 6029: 4.2.3.5 no nível 2 e Apêndice como seção", "prefixo": "46107bee", "regra": "R4"},
    {"caso": "Portigal: objeto de 0 byte", "arquivo": r"interviewing users", "regra": "R2", "clausula_obra": "objeto_vazio"},
    {"caso": "Condorcet: servindo com 0 trecho", "arquivo": r"condorcet", "regra": "R7"},
    {"caso": "Alf Ross: servindo com 0 trecho", "arquivo": r"alf.?ross|state.and.state.organs", "regra": "R7"},
    {"caso": "EPUB 3.3: título '1'", "prefixo": "7e752159", "regra": "R8"},
    {"caso": "IN ITI nº 35: NÃO cai no critério de OCR", "arquivo": r"\bITI\b.*\b35\b|in.?iti.?0?35", "regra": "R5", "clausula": "ocr", "nao": True},
)


def conferir_casos(fichas: list[dict], contradicoes: list[dict]) -> list[dict]:
    """Cada caso conhecido: achou a obra? caiu na regra indicada? (`nao`: não pode cair)."""
    por_obra: dict[str, set] = defaultdict(set)
    for c in contradicoes:
        por_obra[c["obra_id"]].add((c["regra"], c["clausula"]))
    res = []
    for caso in CASOS_CONHECIDOS:
        if "prefixo" in caso:
            alvo = [f for f in fichas if f["obra_id"].startswith(caso["prefixo"])]
        else:
            rx = re.compile(caso["arquivo"], re.I)
            alvo = [f for f in fichas if rx.search(f.get("nome_original") or "") or rx.search((f.get("catalogo") or {}).get("titulo") or "")]
        if not alvo:
            res.append({"caso": caso["caso"], "obras": [], "ok": None, "nota": "obra não encontrada na ficha"})
            continue
        cai = []
        for f in alvo:
            regras = por_obra.get(f["obra_id"], set())
            if caso.get("clausula"):
                cai.append(any(r == caso["regra"] and c == caso["clausula"] for r, c in regras))
            else:
                cai.append(any(r == caso["regra"] for r, _ in regras))
        ok = (not any(cai)) if caso.get("nao") else any(cai)
        res.append({"caso": caso["caso"], "obras": [f["obra_id"][:8] for f in alvo], "regra": caso["regra"],
                    "ok": ok, "nota": "não podia cair e caiu" if caso.get("nao") and not ok else ("" if ok else "a regra não pegou")})
    return res


def resumir(fichas: list[dict], contradicoes: list[dict]) -> dict:
    """Contagens do resumo.json: por formato, situação, regra e cláusula."""
    fmt = {f["obra_id"]: f.get("formato_id") or "desconhecido" for f in fichas}
    por_formato = Counter(fmt.values())
    regras = {}
    for r in REGRAS:
        cs = [c for c in contradicoes if c["regra"] == r]
        regras[r] = {
            "avaliadas": len(fichas),
            "violacoes": len(cs),
            "obras": len({c["obra_id"] for c in cs}),
            "por_clausula": dict(sorted(Counter(c["clausula"] or "-" for c in cs).items())),
            "por_formato": dict(sorted(Counter(fmt.get(c["obra_id"], "desconhecido") for c in cs).items())),
        }
    return {
        "obras_com_ficha": len(fichas),
        "por_formato": dict(sorted(por_formato.items())),
        "situacao_identificacao": dict(sorted(Counter(f.get("situacao_identificacao") or "sem" for f in fichas).items())),
        "erros": sum(1 for f in fichas if f.get("erro")),
        "aceite_universo": sum(1 for f in fichas if (f.get("catalogo") or {}).get("aceite_universo")),
        "regras": regras,
        "casos_conhecidos": conferir_casos(fichas, contradicoes),
    }


def linhas_tsv(contradicoes: list[dict], fichas_por_id: dict[str, dict]) -> list[str]:
    """contradicoes.tsv: obra_id, regra, valor do arquivo, valor do catálogo, nota (+ arquivo e formato)."""
    def limpa(s):
        return str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")
    cab = "obra_id\tregra\tvalor_do_arquivo\tvalor_do_catalogo\tnota\tarquivo\tformato"
    out = [cab]
    for c in sorted(contradicoes, key=lambda c: (c["regra"], c["clausula"], c["obra_id"])):
        f = fichas_por_id.get(c["obra_id"], {})
        nota = (f"[{c['clausula']}] " if c["clausula"] else "") + c["nota"]
        out.append("\t".join(limpa(x) for x in (c["obra_id"], c["regra"], c["arquivo"], c["catalogo"], nota,
                                               f.get("nome_original") or "-", f.get("formato_id") or "-")))
    return out
