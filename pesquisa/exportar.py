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
