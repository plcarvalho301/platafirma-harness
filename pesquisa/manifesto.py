"""Manifesto por trabalho e layout em disco (spec §4.8, §2.3).

    ~/AI/var/pesquisa/<trabalho>/
      bruto/          # imutável: byte como veio, nome de origem
      derivado/       # .headers, .md, traduções — tudo que o verbo ou o modelo produziu
      MANIFESTO.jsonl # fonte única; `manifesto --md` renderiza

Consequência não depende de lembrança (§2.3): todo ato grava a linha SEM flag. O
trabalho default é a ordem da sessão (`PF_ORDEM_ID`); sem sessão, `manual-<data>`.

`n` é o índice do artefato dentro do trabalho — o que o modelo cita como `[m:<n>]`.
Ele é estável: o próximo `n` é `max(n no manifesto)+1`, para que reabrir um trabalho
continue a numeração em vez de sobrescrever bruto/derivado.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any

RAIZ_VAR = Path(os.environ.get("PF_PESQUISA_DIR", str(Path.home() / "AI" / "var" / "pesquisa")))
UA = "PlataFirma-pesquisa/1.0 (+https://platafirma.org; verbo pesquisar; robots respeitado)"


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256_texto(texto: str) -> str:
    return sha256_bytes(texto.encode("utf-8"))


def agora_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug_trabalho(explicito: str | None) -> str:
    if explicito:
        return explicito
    ordem = os.environ.get("PF_ORDEM_ID")
    if ordem:
        return ordem
    return "manual-" + _dt.date.today().isoformat()


class Trabalho:
    """Uma pasta de trabalho: cria o layout, numera artefatos, escreve o manifesto."""

    def __init__(self, slug: str, *, raiz: Path | None = None) -> None:
        self.slug = slug
        self.dir = (raiz or RAIZ_VAR) / slug
        self.bruto = self.dir / "bruto"
        self.derivado = self.dir / "derivado"
        self.manifesto = self.dir / "MANIFESTO.jsonl"
        for d in (self.bruto, self.derivado):
            d.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- leitura
    def linhas(self) -> list[dict[str, Any]]:
        if not self.manifesto.exists():
            return []
        out = []
        for ln in self.manifesto.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
        return out

    def proximo_n(self) -> int:
        maior = 0
        for ln in self.linhas():
            n = ln.get("n")
            if isinstance(n, int) and n > maior:
                maior = n
        return maior + 1

    # ---------------------------------------------------------------- escrita
    def grava_linha(self, campos: dict[str, Any]) -> int:
        """Anexa uma linha ao MANIFESTO.jsonl. Devolve o índice (1-based) da linha."""
        campos.setdefault("ts", agora_utc())
        campos.setdefault("ua", UA)
        with self.manifesto.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(campos, ensure_ascii=False) + "\n")
        return len(self.linhas())

    def guarda_bruto(self, n: int, dados: bytes, ext: str = "html") -> Path:
        p = self.bruto / f"{n}.{ext}"
        p.write_bytes(dados)
        return p

    def guarda_derivado(self, n: int, texto: str, ext: str) -> Path:
        p = self.derivado / f"{n}.{ext}"
        p.write_text(texto, encoding="utf-8")
        return p

    def ref_manifesto(self, linha: int) -> dict[str, Any]:
        return {"arquivo": str(self.manifesto), "linha": linha}
