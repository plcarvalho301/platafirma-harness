"""Monta a ficha de UMA obra (card #3189, ato temporário `acervo censo obra`).

Blocos A (identidade e fixidez), B (formato), C (texto), I (estrutura derivável) e J (catálogo lado a lado)
saem daqui; D a H (PDF, EPUB, MOBI, OOXML, texto) vêm dos leitores `censo_<formato>.py`, um por formato.
Só leitura: os bytes chegam por `buscar(objeto)`; nada é gravado. Não levanta: falha vira `erro` na ficha.
"""
from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
import zipfile
from collections import defaultdict

import censo_estrutura

VERSAO_FICHA = 1
PRAZO_OBRA_S = 600.0
SHA_VAZIO = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# formato_id -> (módulo do leitor, chave do bloco)
LEITORES = {
    "pdf": ("censo_pdf", "pdf"), "epub": ("censo_epub", "epub"), "mobi": ("censo_mobi", "mobi"),
    "docx": ("censo_ooxml", "ooxml"), "pptx": ("censo_ooxml", "ooxml"), "xlsx": ("censo_ooxml", "ooxml"),
    "html": ("censo_texto", "texto"), "md": ("censo_texto", "texto"), "txt": ("censo_texto", "texto"),
}
# extensões que combinam com cada formato identificado pelos bytes
EXTENSOES = {
    "pdf": {"pdf"}, "epub": {"epub"}, "mobi": {"mobi", "azw", "azw3", "prc", "pdb"}, "docx": {"docx"},
    "pptx": {"pptx"}, "xlsx": {"xlsx"}, "html": {"html", "htm", "xhtml", "shtml"},
    "md": {"md", "markdown", "mdown", "mkd", "txt"},
    "txt": {"txt", "text", "md", "markdown", "csv", "tsv", "log", "rst", "adoc", "tex", "srt", "vtt"},
    "json": {"json", "jsonl", "geojson"}, "mhtml": {"mhtml", "mht", "eml"}, "zip": {"zip", "jar"},
    "xml": {"xml", "xhtml", "svg", "opf", "ncx", "rdf", "owl"}, "rtf": {"rtf"}, "png": {"png"},
    "jpeg": {"jpg", "jpeg"}, "gif": {"gif"}, "ole2": {"doc", "xls", "ppt", "msg", "docx", "xlsx", "pptx"},
    "odf": {"odt", "ods", "odp", "odg"},
}
_EXT_VALIDA = re.compile(r"^[a-z][a-z0-9]{1,5}$")
_RE_PUA = re.compile("[" + chr(0xE000) + "-" + chr(0xF8FF) + "]")
_RE_LIG = re.compile("[" + chr(0xFB00) + "-" + chr(0xFB06) + "]")
_RE_HTML = re.compile(r"<!doctype\s+html|<html[\s>]|<head[\s>]|<body[\s>]", re.I)
_RE_MD = re.compile(r"^(#{1,6}\s+\S|[-*+]\s+\S|\d+\.\s+\S|>\s?\S|```|\|.+\|\s*$)", re.M)
_RE_MD_LINK = re.compile(r"\[[^\]\n]+\]\([^)\n]+\)")
_RE_PDF_VERSAO = re.compile(rb"%PDF-(\d\.\d)")
_INDICATIVO = re.compile(r"^([1-9]\d*(?:\.[1-9]\d*){0,4}) \S")


# ---------------------------------------------------------------- B: formato pelos bytes

def _f(formato_id, nome, versao, mime, base, tentativo=False):
    return {"formato_id": formato_id, "nome": nome, "versao": versao, "mime": mime, "base": base,
            "tentativo": tentativo}


def _bom_texto(dados: bytes) -> str | None:
    if dados[:3] == b"\xef\xbb\xbf":
        return "utf-8"
    if dados[:4] in (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"):
        return "utf-32"
    if dados[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    return None


def _amostra_texto(dados: bytes) -> str | None:
    """Texto decodificado da cabeça do arquivo, ou None se não parece texto."""
    cab = dados[:65536]
    bom = _bom_texto(cab)
    if bom in ("utf-16", "utf-32"):
        try:
            return cab.decode(bom, "replace")
        except (UnicodeError, LookupError):
            return None
    if b"\x00" in cab[:8192]:
        return None
    dec = __import__("codecs").getincrementaldecoder("utf-8")()
    try:
        return dec.decode(cab, final=False)
    except UnicodeDecodeError:
        pass
    imprimiveis = sum(1 for b in cab[:8192] if 32 <= b < 127 or b in (9, 10, 13) or b >= 160)
    return cab.decode("cp1252", "replace") if imprimiveis >= 0.95 * len(cab[:8192]) else None


def _zip_info(dados: bytes):
    """(formato, membros, criptografado) para contêiner zip; None se não abre como zip."""
    try:
        z = zipfile.ZipFile(io.BytesIO(dados))
    except (zipfile.BadZipFile, ValueError, OSError):
        return None
    infos = z.infolist()
    nomes = [i.filename for i in infos]
    cripto = [i.filename for i in infos if i.flag_bits & 0x1]
    conj = set(nomes)
    fmt = None
    if "mimetype" in conj:
        try:
            mt = z.read("mimetype")[:120].decode("ascii", "replace").strip()
        except Exception:                                   # noqa: BLE001 — leitura do zip pode falhar de vários jeitos
            mt = ""
        if mt == "application/epub+zip":
            fmt = _f("epub", "EPUB", None, mt, "zip com o membro mimetype = application/epub+zip")
        elif mt.startswith("application/vnd.oasis.opendocument"):
            fmt = _f("odf", "OpenDocument", None, mt, "zip com o membro mimetype = " + mt)
    if fmt is None and "[Content_Types].xml" in conj:
        for marca, fid, nome, mime in (
            ("word/document.xml", "docx", "Word (OOXML)", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("ppt/presentation.xml", "pptx", "PowerPoint (OOXML)", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("xl/workbook.xml", "xlsx", "Excel (OOXML)", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ):
            if marca in conj:
                fmt = _f(fid, nome, None, mime, f"zip com [Content_Types].xml e {marca}")
                break
        if fmt is None:
            fmt = _f("zip", "OOXML sem parte principal reconhecida", None, "application/zip", "zip com [Content_Types].xml", True)
    if fmt is None and "META-INF/container.xml" in conj:
        fmt = _f("epub", "EPUB", None, "application/epub+zip", "zip com META-INF/container.xml e sem mimetype", True)
    if fmt is None:
        fmt = _f("zip", "ZIP", None, "application/zip", "zip sem parte principal reconhecida")
    topo: list[str] = []
    for n in nomes:
        p = n.split("/", 1)[0]
        if p and p not in topo:
            topo.append(p)
    return fmt, {"zip": True, "membros_total": len(nomes), "membros_topo": topo[:50], "criptografado": bool(cripto),
                 "membros_criptografados": len(cripto)}, cripto


def detectar(dados: bytes) -> tuple[list[dict], dict | None]:
    """Candidatos de formato pelos bytes (nunca pela extensão) e o contêiner, se for zip."""
    if not dados:
        return [], None
    cands: list[dict] = []
    conteiner = None
    i = dados.find(b"%PDF-", 0, 1024)
    if i >= 0:
        m = _RE_PDF_VERSAO.match(dados[i:i + 12])
        cands.append(_f("pdf", "PDF", m.group(1).decode() if m else None, "application/pdf", f"%PDF- no byte {i}"))
    if dados[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
        zi = _zip_info(dados)
        if zi:
            cands.append(zi[0])
            conteiner = zi[1]
    if len(dados) >= 78 and dados[60:68] in (b"BOOKMOBI", b"TEXtREAd"):
        cands.append(_f("mobi", "Mobipocket/PalmDOC", None, "application/x-mobipocket-ebook",
                        "PalmDB tipo/criador " + dados[60:68].decode("ascii")))
    if dados[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        cands.append(_f("ole2", "OLE2 Compound File", None, "application/x-ole-storage", "assinatura D0CF11E0"))
    if dados[:5] == b"{\\rtf":
        cands.append(_f("rtf", "RTF", None, "application/rtf", "{\\rtf no byte 0"))
    for sig, fid, nome, mime in ((b"\x89PNG\r\n\x1a\n", "png", "PNG", "image/png"),
                                 (b"\xff\xd8\xff", "jpeg", "JPEG", "image/jpeg"),
                                 (b"GIF8", "gif", "GIF", "image/gif")):
        if dados.startswith(sig):
            cands.append(_f(fid, nome, None, mime, f"assinatura no byte 0"))
    if cands:
        return cands, conteiner
    amostra = _amostra_texto(dados)
    if amostra is None:
        return [], None
    topo = amostra.lstrip(chr(0xFEFF) + " \t\r\n")
    if topo.startswith("<?xml") and _RE_HTML.search(topo[:4000]):
        return [_f("html", "XHTML", None, "application/xhtml+xml", "declaração XML e marcas html")], None
    if _RE_HTML.search(topo[:2000]):
        return [_f("html", "HTML", None, "text/html", "marca html/doctype/head/body no início")], None
    if topo.startswith("<?xml"):
        return [_f("xml", "XML", None, "application/xml", "declaração XML")], None
    if re.match(r"(?i)(mime-version:|content-type:\s*multipart/related|from:.*\n(?:.*\n){0,12}?mime-version:)", topo) \
            and "boundary=" in topo[:4000]:
        return [_f("mhtml", "MHTML", None, "message/rfc822", "cabeçalho MIME com boundary")], None
    if topo[:1] in ("{", "[") and len(dados) <= 20_000_000:
        try:
            json.loads(dados.decode("utf-8-sig"))
            return [_f("json", "JSON", None, "application/json", "documento JSON válido", True)], None
        except (ValueError, UnicodeError):
            pass
    linhas = amostra.count("\n") + 1
    if len(_RE_MD.findall(amostra)) >= 3 or _RE_MD_LINK.search(amostra) or re.search(r"(?m)^#{1,6}\s+\S", amostra):
        if len(_RE_MD.findall(amostra)) >= max(2, linhas // 50) or re.search(r"(?m)^#{1,6}\s+\S", amostra):
            return [_f("md", "Markdown", None, "text/markdown", "texto com marcas de Markdown (sem assinatura)", True)], None
    return [_f("txt", "Plain text", None, "text/plain", "texto sem marcas reconhecidas (sem assinatura)", True)], None


def _identificar_sf(dados: bytes) -> dict | None:
    """Siegfried (`sf -json`), se o host o tiver; senão None. Devolve as marcas do PRONOM."""
    sf = os.environ.get("PLATAFIRMA_SF") or shutil.which("sf") or ("/usr/local/bin/sf" if os.path.exists("/usr/local/bin/sf") else None)
    if not sf:
        return None
    try:
        with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
            tmp.write(dados)
            tmp.flush()
            r = subprocess.run([sf, "-json", "-nr", tmp.name], capture_output=True, timeout=120)
        j = json.loads(r.stdout.decode("utf-8", "replace"))
        matches = (j.get("files") or [{}])[0].get("matches") or []
        return {"ferramenta": {"nome": "siegfried", "versao": j.get("siegfried"), "assinaturas": j.get("signature"),
                               "identificadores": j.get("identifiers")},
                "matches": [{"nome": m.get("format"), "versao": m.get("version"), "registro": m.get("id"),
                             "mime": m.get("mime"), "base": m.get("basis"), "aviso": m.get("warning"),
                             "namespace": m.get("ns")} for m in matches]}
    except Exception:                                       # noqa: BLE001 — sem sf legível, cai no identificador próprio
        return None


def extensao_de(nome: str | None) -> str:
    e = os.path.splitext(nome or "")[1].lstrip(".").lower()
    return e


def situacao_identificacao(cands: list[dict], ext: str, sf: dict | None = None) -> str:
    if sf and sf["matches"]:
        ms = [m for m in sf["matches"] if m.get("registro") and m["registro"] != "UNKNOWN"]
        if not ms and not cands:
            return "desconhecido"
        if len(ms) > 1:
            return "disjuncao"
        if ms and "extension mismatch" in (ms[0].get("aviso") or "").lower():
            return "extensao_diverge"
    if not cands:
        return "desconhecido"
    if len(cands) > 1:
        return "disjuncao"
    c = cands[0]
    if _EXT_VALIDA.match(ext) and ext not in EXTENSOES.get(c["formato_id"], set()):
        return "extensao_diverge"
    return "tentativo" if c["tentativo"] else "identificado"


# ---------------------------------------------------------------- C: texto

def metricas_texto(texto: str) -> dict:
    return {
        "caracteres": len(texto),
        "normalizacao_unicode": {"nfc": unicodedata.is_normalized("NFC", texto),
                                 "nfd": unicodedata.is_normalized("NFD", texto)},
        "ligaduras": len(_RE_LIG.findall(texto)),
        "substituicao": texto.count(chr(0xFFFD)),
        "uso_privado": len(_RE_PUA.findall(texto)),
    }


def detectar_lingua(texto: str) -> tuple[dict | None, str | None, str | None]:
    """(lingua, motivo da lacuna, versão da biblioteca) nos primeiros 20 mil caracteres."""
    amostra = texto[:20000]
    if len(amostra.strip()) < 40:
        return None, "texto curto demais para detectar língua", None
    try:
        from langdetect import DetectorFactory, detect_langs
    except ImportError:
        return None, "langdetect ausente no ambiente", None
    try:
        DetectorFactory.seed = 0
        r = detect_langs(amostra)
    except Exception as e:                                   # noqa: BLE001
        return None, f"langdetect falhou: {type(e).__name__}", None
    try:
        from importlib.metadata import version
        v = version("langdetect")
    except Exception:                                        # noqa: BLE001
        v = None
    return ({"codigo": r[0].lang, "confianca": round(r[0].prob, 4),
             "candidatas": [{"codigo": x.lang, "confianca": round(x.prob, 4)} for x in r[:3]],
             "amostra_caracteres": len(amostra)}, None, v)


# ---------------------------------------------------------------- J: catálogo

def _caixa_espacada(t: str) -> bool:
    toks = t.split(" ")
    return len(toks) >= 3 and all(len(x) == 1 and x.isalpha() and x.isupper() for x in toks[:2])


def analisar_secoes(secoes: list) -> dict:
    """R4 só com o catálogo: nível x indicativo, irmãs curtas na mesma página, caixa espaçada."""
    nd, ex_n, caixa, ex_c = 0, [], 0, []
    grupos: dict = defaultdict(list)
    for s in secoes or []:
        titulo, nivel, pag = (s + [None, None, None])[:3]
        t = (titulo or "").strip()
        m = _INDICATIVO.match(t)
        if m and not t.endswith(".") and nivel is not None and nivel != len(m.group(1).split(".")):
            nd += 1
            if len(ex_n) < 5:
                ex_n.append(f"{t[:40]} (nível {nivel})")
        if _caixa_espacada(t):
            caixa += 1
            if len(ex_c) < 5:
                ex_c.append(t[:30])
        if t and len(t.split()) <= 2:
            grupos[(pag, nivel)].append(t)
    irmas = [t for v in grupos.values() if len(v) >= 2 for t in v]
    return {"nivel_diverge_indicativo": nd, "nivel_diverge_exemplos": ex_n,
            "irmas_curtas": len(irmas), "irmas_exemplos": irmas[:5],
            "caixa_espacada": caixa, "caixa_exemplos": ex_c}


def bloco_catalogo(item: dict) -> dict:
    imp = item.get("impressao") or {}
    metodo = imp.get("metodo") or {}
    servindo = bool(imp)
    n = item.get("secoes_n") or 0
    maior, total = item.get("maior_chars"), item.get("texto_chars")
    return {
        "titulo": item.get("titulo"),
        "expurgada": bool(item.get("expurgada")),
        "impressao_servindo": servindo,
        "n_impressoes_servindo": item.get("n_servindo") or 0,
        "impressoes_por_estado": item.get("estados") or {},
        "aceite_universo": servindo and not item.get("expurgada"),
        "metodo_perfil": metodo.get("perfil"),
        "needs_ocr": metodo.get("needs_ocr"),
        "metodo": metodo,
        "espelho": bool(imp.get("tem_espelho")),
        "secoes_n": n,
        "secoes_nivel_max": item.get("nivel_max"),
        "secoes_n_nivel1": item.get("n_nivel1") or 0,
        "secoes_n_nivel2": item.get("n_nivel2") or 0,
        "maior_secao_chars": maior,
        "maior_secao_fracao": round(maior / total, 4) if maior and total else None,
        "texto_chars": total,
        "trechos_n": item.get("trechos_n") or 0,
        "trechos_texto_n": item.get("trechos_texto_n") or 0,
        "secoes_analise": analisar_secoes(item.get("secoes") or []),
    }


# ---------------------------------------------------------------- a ficha

def _ler_com_leitor(fid: str, dados: bytes, ctx: dict) -> tuple[dict | None, str | None]:
    modulo, _ = LEITORES[fid]
    try:
        mod = importlib.import_module(modulo)
    except Exception as e:                                   # noqa: BLE001
        return None, f"leitor {modulo} indisponível: {type(e).__name__}: {e}"
    try:
        return mod.ler(dados, ctx), None
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:                                   # noqa: BLE001 — o leitor não deveria levantar
        return None, f"leitor {modulo} levantou {type(e).__name__}: {e}"


def montar_ficha(item: dict, buscar, prazo_s: float = PRAZO_OBRA_S) -> dict:
    """A ficha da obra `item` (linha do universo). `buscar(objeto) -> (bytes|None, motivo|None)`."""
    t0 = time.monotonic()
    objeto = item.get("objeto") or ""
    nome = item.get("arquivo")
    chave = objeto.split("/", 1)[1] if "/" in objeto else objeto
    ficha: dict = {
        "versao_ficha": VERSAO_FICHA, "obra_id": item["obra_id"], "objeto": objeto, "categoria": "file",
        "relacao_obra": {"tipo": "estrutural", "obra_id": item["obra_id"]},
        "nome_original": nome, "extensao": extensao_de(nome),
        "bytes": None, "sha256_guardado": chave or None, "sha256_calculado": None, "fixidez_confere": None,
        "objeto_ausente": False, "objeto_vazio": False,
        "formato_id": None, "formatos": [], "situacao_identificacao": None, "conteiner": None,
        "inibidor": None, "aplicacoes_criadoras": [], "encoding": None, "lingua_declarada": None,
        "texto": None, "estrutura_declarada": [], "estrutura": None,
        "catalogo": bloco_catalogo(item), "lacunas": {}, "bibliotecas": {}, "erro": None, "tempos_ms": {},
    }
    try:
        dados, motivo = buscar(objeto)
        ficha["tempos_ms"]["buscar"] = round(1000 * (time.monotonic() - t0))
        if dados is None:
            if motivo == "ausente":
                ficha["objeto_ausente"] = True
                ficha["situacao_identificacao"] = "desconhecido"
                ficha["formatos"] = [{"nome": "unknown", "versao": None, "registro": None, "mime": None, "base": "objeto ausente"}]
            else:
                ficha["erro"] = f"buscar: {motivo}"
            return ficha
        ficha["bytes"] = len(dados)
        ficha["sha256_calculado"] = hashlib.sha256(dados).hexdigest()
        ficha["fixidez_confere"] = ficha["sha256_calculado"] == (chave or "").lower()
        ficha["objeto_vazio"] = len(dados) == 0
        t1 = time.monotonic()
        cands, conteiner = detectar(dados)
        sf = _identificar_sf(dados) if dados else None
        ficha["conteiner"] = conteiner
        if sf and sf["matches"]:
            ficha["identificador"] = sf["ferramenta"]
            ficha["formatos"] = [{k: m[k] for k in ("nome", "versao", "registro", "mime", "base", "aviso")} for m in sf["matches"]]
        else:
            ficha["formatos"] = [{"nome": c["nome"], "versao": c["versao"], "registro": None, "mime": c["mime"],
                                  "base": c["base"]} for c in cands] or [
                {"nome": "unknown", "versao": None, "registro": None, "mime": None, "base": "nenhuma assinatura reconhecida"}]
            ficha["lacunas"]["registro_pronom"] = "sem siegfried/fido no host: identificação por assinatura própria, registro PRONOM nulo"
        fid = cands[0]["formato_id"] if len(cands) >= 1 else None
        ficha["formato_id"] = fid
        ficha["situacao_identificacao"] = situacao_identificacao(cands, ficha["extensao"], sf)
        if conteiner and conteiner.get("criptografado"):
            ficha["inibidor"] = {"tipo": "Password protection", "alvo": f"{conteiner['membros_criptografados']} membros do zip"}
        ficha["tempos_ms"]["identificar"] = round(1000 * (time.monotonic() - t1))
        texto, paginas, pseudo = None, None, False
        if fid in LEITORES and dados:
            t2 = time.monotonic()
            ctx = {"nome_original": nome, "formato_id": fid, "bytes": len(dados),
                   "prazo_s": max(5.0, prazo_s - (t2 - t0))}
            env, motivo_leitor = _ler_com_leitor(fid, dados, ctx)
            ficha["tempos_ms"]["leitor"] = round(1000 * (time.monotonic() - t2))
            if env is None:
                ficha["lacunas"]["leitor"] = motivo_leitor
                ficha["erro_leitor"] = motivo_leitor
            else:
                bloco = LEITORES[fid][1]
                ficha["texto_formato" if bloco == "texto" else bloco] = env.get(bloco)   # `texto` já é o bloco C da ficha
                ficha["aplicacoes_criadoras"] = env.get("aplicacoes_criadoras") or []
                ficha["inibidor"] = env.get("inibidor") or ficha["inibidor"]
                ficha["lingua_declarada"] = env.get("lingua_declarada")
                ficha["encoding"] = env.get("encoding")
                ficha["estrutura_declarada"] = env.get("estrutura_declarada") or []
                ficha["lacunas"].update({f"{fid}.{k}" if k != "prazo" else "prazo": v for k, v in (env.get("lacunas") or {}).items()})
                ficha["bibliotecas"].update(env.get("bibliotecas") or {})
                if env.get("erro"):
                    ficha["erro_leitor"] = env["erro"]
                texto, paginas = env.get("_texto"), env.get("_paginas")
        if texto:
            ficha["texto"] = metricas_texto(texto)
            lingua, motivo_l, ver = detectar_lingua(texto)
            ficha["texto"]["lingua_detectada"] = lingua
            if motivo_l:
                ficha["lacunas"]["lingua_detectada"] = motivo_l
            if ver:
                ficha["bibliotecas"]["langdetect"] = ver
        if fid == "pdf" and paginas:
            ficha["estrutura"] = censo_estrutura.derivar(paginas)
        elif fid in ("txt", "md") and texto:
            pgs, pseudo = censo_estrutura.paginas_de_texto(texto)
            ficha["estrutura"] = censo_estrutura.derivar(pgs, pseudo)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:                                   # noqa: BLE001 — a obra que não abre vira linha com erro
        ficha["erro"] = f"{type(e).__name__}: {e}"[:300]
    ficha["tempos_ms"]["total"] = round(1000 * (time.monotonic() - t0))
    return ficha
