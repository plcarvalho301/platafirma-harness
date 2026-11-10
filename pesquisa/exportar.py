"""exportar — leva o que um trabalho coletou à área de chegada do acervo, um arquivo por página.

O trabalho guarda tudo o que o verbo tocou: corpo bruto, resposta HTTP ao lado, derivado em
Markdown, releituras do cache e tentativas que falharam. O `acervo pipeline <pasta>` lê a pasta
como veio, e a pasta do trabalho lhe entrega a mesma página duas ou três vezes (bruto e
derivado), os `.resposta.json` como candidatos a obra e as tentativas vazias. Este ato escolhe,
por URL, o último bruto íntegro do manifesto e o copia para `~/AI/entrada/<rótulo>`, com o
nome tirado do endereço, e deixa ao lado `PROCEDENCIA.jsonl` (auxiliar, que o pipeline não faz
obra) com URL, sha256, trabalho e linha de origem de cada arquivo.

Íntegro é: linha de `ler` com `n`, status 2xx, `bruto` gravado e o sha256 do arquivo em disco
igual ao da linha. O último critério barra o bruto que outro ato sobrescreveu (#2856 linha 555).
Nada é sobrescrito no destino: arquivo de mesmo nome e mesmo sha256 fica como está; com outro
sha256, o item volta como conflito e o destino não muda.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import manifesto as M

RAIZ_ENTRADA = Path(os.environ.get("PF_ENTRADA_DIR", str(Path.home() / "AI" / "entrada")))
_RE_ROTULO = re.compile(r"^[a-z0-9][a-z0-9._-]{0,80}$")


_RE_TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
_RE_H1 = re.compile(r"^\s*(?:title:\s*[\"']?(.+?)[\"']?\s*$|#\s+(.+?)\s*$)", re.M)


def _titulo(corpo: bytes, ext: str) -> str | None:
    """O título da página, que o pipeline usa como título provisório de HTML pelo nome do arquivo.

    Nomear pelo endereço deixava páginas diferentes com nomes 90% iguais
    (`..._providers_azure` e `..._providers_adfs`), e a checagem de identidade do pipeline as
    reprovava como obra ambígua (plano do lote pesquisa-aquisicao-ti-20261110: 24 de 28).
    """
    import html as _h
    if ext in ("html", "htm"):
        m = _RE_TITLE.search(corpo[:200_000])
        if m:
            t = _h.unescape(m.group(1).decode("utf-8", "replace"))
            return " ".join(t.split()) or None
        return None
    if ext in ("md", "markdown", "txt"):
        m = _RE_H1.search(corpo[:50_000].decode("utf-8", "replace"))
        if m:
            return (m.group(1) or m.group(2) or "").strip() or None
    return None


def _limpo(t: str) -> str:
    t = re.sub(r"[^\w .()&+,-]+", " ", t, flags=re.UNICODE)
    return " ".join(t.split()).strip(" .")[:150]


def _nome(url: str, ext: str) -> str:
    p = urlsplit(url)
    caminho = p.path.strip("/")
    for sufixo in ("index.md", "index.html"):
        if caminho.endswith(sufixo):
            caminho = caminho[: -len(sufixo)].strip("/")
    base = f"{p.netloc}/{caminho}" if caminho else p.netloc
    if p.query:
        base += "-" + p.query
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_.")[:180] or "pagina"
    return f"{base}.{ext}"


def escolher(trab: "M.Trabalho", excluir: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Por URL, a última linha íntegra. Devolve (escolhidas, puladas com motivo)."""
    filtros = [re.compile(x) for x in (excluir or [])]
    ultima: dict[str, dict] = {}
    pulados: list[dict] = []
    for i, ln in enumerate(trab.linhas(), 1):
        if ln.get("ato") != "ler" or ln.get("nao_achado"):
            continue
        url, bruto, sha = ln.get("url"), ln.get("bruto"), ln.get("sha256")
        status = ln.get("status")
        if not (url and bruto and sha and isinstance(ln.get("n"), int)):
            continue
        if not (isinstance(status, int) and 200 <= status < 300):
            continue
        ultima[url] = {**ln, "_linha": i}
    escolhidas = []
    for url, ln in ultima.items():
        if any(f.search(url) for f in filtros):
            pulados.append({"url": url, "motivo": "excluida"})
            continue
        p = Path(ln["bruto"])
        if not p.is_file():
            pulados.append({"url": url, "motivo": "bruto-ausente", "bruto": str(p)})
            continue
        if M.sha256_bytes(p.read_bytes()) != ln["sha256"]:
            pulados.append({"url": url, "motivo": "bruto-nao-confere", "bruto": str(p)})
            continue
        escolhidas.append(ln)
    return escolhidas, pulados


_RE_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_RE_FRONT_TITLE = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.M)
_RE_CERCA = re.compile(r"^\s*(```|~~~)")


def _markdown_da_pagina(trab: "M.Trabalho", ln: dict) -> str | None:
    """O Markdown da página: o derivado do extrator, ou o bruto quando o site já serve Markdown."""
    d = trab.derivado / f"{ln['n']}.md"
    if d.is_file():
        return d.read_text(encoding="utf-8", errors="replace")
    b = Path(ln["bruto"])
    if b.suffix.lower() in (".md", ".markdown", ".txt"):
        return b.read_text(encoding="utf-8", errors="replace")
    return None


def _secao(md: str, url: str) -> tuple[str, str]:
    """(título, corpo) da página, sem frontmatter, com os títulos rebaixados um nível.

    O documento juntado tem um H1 só, o do site; cada página vira H2 e o que era H2 vira H3.
    Linha dentro de bloco de código não é título e não muda.
    """
    titulo = None
    m = _RE_FRONT.match(md)
    if m:
        t = _RE_FRONT_TITLE.search(m.group(1))
        titulo = t.group(1).strip() if t else None
        md = md[m.end():]
    linhas, dentro, h1_tirado = [], False, False
    for linha in md.splitlines():
        if _RE_CERCA.match(linha):
            dentro = not dentro
        elif not dentro and linha.startswith("#"):
            nivel = len(linha) - len(linha.lstrip("#"))
            texto = linha[nivel:].strip()
            if nivel == 1 and not h1_tirado and (titulo is None or texto == titulo):
                titulo = titulo or texto
                h1_tirado = True
                continue
            linha = "#" * min(nivel + 1, 6) + linha[nivel:]
        linhas.append(linha)
    titulo = titulo or (urlsplit(url).path.strip("/") or urlsplit(url).netloc)
    return " ".join(titulo.split()), "\n".join(linhas).strip()


def _ordem(url: str) -> tuple:
    """Página-mãe antes das filhas: ordena pelos segmentos do caminho."""
    p = urlsplit(url)
    segs = [s for s in p.path.split("/") if s and s not in ("index.md", "index.html")]
    return (p.netloc, segs)


def juntar(trab: "M.Trabalho", titulo: str, rotulo: str | None = None,
           excluir: list[str] | None = None, *, raiz: Path | None = None) -> dict[str, Any]:
    """O site coletado vira UM arquivo Markdown, uma obra: um H1 com o título dado e uma seção
    H2 por página, na ordem do caminho, cada uma com a URL de origem.

    Uma documentação de produto é uma obra, como um manual em PDF; exportada página a página,
    o site entrava no acervo como dezenas de obras (lote acervo-aquisicao-ti-20261110: 62 do
    Cloudflare Tunnel e 36 do OAuth2 Proxy). Página sem Markdown (sem derivado e com bruto que
    não é Markdown) volta em `pulados` e não entra calada.
    """
    rotulo = rotulo or f"pesquisa-{trab.slug}"
    if not _RE_ROTULO.match(rotulo):
        raise ValueError(f"rotulo-invalido:{rotulo}")
    base = _limpo(titulo or "")
    if not base:
        raise ValueError("titulo-vazio")
    destino = (raiz or RAIZ_ENTRADA) / rotulo
    destino.mkdir(parents=True, exist_ok=True)
    escolhidas, pulados = escolher(trab, excluir)
    escolhidas.sort(key=lambda ln: _ordem(ln.get("url_final") or ln["url"]))
    partes = [f"---\ntitle: \"{titulo}\"\n---\n\n# {titulo}\n"]
    paginas = []
    for ln in escolhidas:
        url = ln.get("url_final") or ln["url"]
        md = _markdown_da_pagina(trab, ln)
        if md is None:
            pulados.append({"url": ln["url"], "motivo": "sem-markdown"})
            continue
        t, corpo = _secao(md, url)
        partes.append(f"\n## {t}\n\nFonte: <{url}>\n\n{corpo}\n")
        paginas.append({"url": ln["url"], "url_final": ln.get("url_final"), "titulo": t,
                        "sha256": ln["sha256"], "n": ln["n"], "linha_manifesto": ln["_linha"],
                        "coletado_em": ln.get("ts")})
    if not paginas:
        raise ValueError("nenhuma-pagina-com-markdown")
    texto = "".join(partes).encode("utf-8")
    sha = M.sha256_bytes(texto)
    alvo = destino / f"{base}.md"
    conflitos = []
    if alvo.exists() and M.sha256_bytes(alvo.read_bytes()) != sha:
        conflitos.append({"arquivo": alvo.name, "motivo": "outro-sha256-no-destino"})
    elif not alvo.exists():
        tmp = alvo.with_suffix(".md.parcial")
        tmp.write_bytes(texto)
        tmp.replace(alvo)
        with (destino / "PROCEDENCIA.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"arquivo": alvo.name, "sha256": sha, "trabalho": trab.slug,
                                 "juntado_de": paginas}, ensure_ascii=False) + "\n")
    linha = trab.grava_linha({"ato": "exportar", "juntar": True, "destino": str(destino),
                              "status": 200, "arquivo": alvo.name, "paginas": len(paginas),
                              "pulados": len(pulados), "conflitos": len(conflitos)})
    return {"destino": str(destino), "arquivo": alvo.name, "sha256": sha,
            "paginas": len(paginas), "pulados": pulados, "conflitos": conflitos,
            "ok_destino": not conflitos, "manifesto": trab.ref_manifesto(linha)}


def exportar(trab: "M.Trabalho", rotulo: str | None = None, excluir: list[str] | None = None,
             *, raiz: Path | None = None) -> dict[str, Any]:
    rotulo = rotulo or f"pesquisa-{trab.slug}"
    if not _RE_ROTULO.match(rotulo):
        raise ValueError(f"rotulo-invalido:{rotulo}")
    destino = (raiz or RAIZ_ENTRADA) / rotulo
    destino.mkdir(parents=True, exist_ok=True)
    escolhidas, pulados = escolher(trab, excluir)
    exportados, conflitos = [], []
    procedencia = destino / "PROCEDENCIA.jsonl"
    usados: set[str] = set()
    for ln in escolhidas:
        origem = Path(ln["bruto"])
        ext = origem.suffix.lstrip(".") or "bin"
        url_nome = ln.get("url_final") or ln["url"]
        titulo = _titulo(origem.read_bytes(), ext)
        base = _limpo(titulo) if titulo else ""
        if not base:
            nome = _nome(url_nome, ext)
        else:
            nome = f"{base}.{ext}"
            ocupado = (destino / nome)
            if nome in usados or (ocupado.exists() and M.sha256_bytes(ocupado.read_bytes()) != ln["sha256"]):
                cauda = [s for s in urlsplit(url_nome).path.split("/") if s and s not in ("index.md", "index.html")]
                nome = f"{base} ({'-'.join(cauda[-2:]) or urlsplit(url_nome).netloc}).{ext}"
        usados.add(nome)
        alvo = destino / nome
        if alvo.exists():
            if M.sha256_bytes(alvo.read_bytes()) == ln["sha256"]:
                exportados.append({"url": ln["url"], "arquivo": alvo.name, "ja_estava": True})
                continue
            conflitos.append({"url": ln["url"], "arquivo": alvo.name, "motivo": "outro-sha256-no-destino"})
            continue
        shutil.copyfile(origem, alvo)
        if M.sha256_bytes(alvo.read_bytes()) != ln["sha256"]:
            alvo.unlink(missing_ok=True)
            conflitos.append({"url": ln["url"], "arquivo": alvo.name, "motivo": "copia-nao-confere"})
            continue
        with procedencia.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "arquivo": alvo.name, "url": ln["url"], "url_final": ln.get("url_final"),
                "sha256": ln["sha256"], "trabalho": trab.slug, "n": ln["n"],
                "linha_manifesto": ln["_linha"], "coletado_em": ln.get("ts"),
                "estrategia": ln.get("estrategia"),
            }, ensure_ascii=False) + "\n")
        exportados.append({"url": ln["url"], "arquivo": alvo.name})
    linha = trab.grava_linha({"ato": "exportar", "destino": str(destino), "status": 200,
                              "exportados": len(exportados), "pulados": len(pulados),
                              "conflitos": len(conflitos)})
    return {"destino": str(destino), "exportados": exportados, "pulados": pulados,
            "conflitos": conflitos, "total": len(exportados), "ok_destino": not conflitos,
            "manifesto": trab.ref_manifesto(linha)}
