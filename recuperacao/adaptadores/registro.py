"""Adaptador do registro de decisão — `adr:` · `seg:` · `ont:`.

`spec_recuperador.md` §5: contrato = os arquivos versionados de `decisions/`; carimbo =
sha do commit; classe exata. §4: `chave = adr:<NNNN>` (idem `seg:` e `ont:`), versão =
blob sha do arquivo.

**Três séries, três moradas** — medido em 20/08/2026:

| série | morada |
|---|---|
| `adr:` | `platafirma-arquitetura/macro-global/decisions/` |
| `seg:` | `platafirma-arquitetura/macro-global/capabilities/seguranca/decisions/` |
| `ont:` | `platafirma-conhecimento/ontologia/adr/` |

**O `decisions/INDICE.md` do §5 ainda não existe.** Enquanto não existir, o adaptador
varre o diretório — 70 + 13 + N arquivos, um `listdir` por série. Isso NÃO é
reimplementar a fonte: o contrato de leitura de decisão versionada é o arquivo no ref, e
o índice, quando chegar, será atalho, não outra verdade. Quando existir, este adaptador
passa a lê-lo e esta docstring cai.

Versão = blob sha, tirado do git (`git rev-parse HEAD:<path>`), que é determinístico e
não muda quando só o mtime muda. Sem git alcançável, cai para o sha256 do conteúdo,
declarado no `tipo` da versão — os dois são carimbo honesto, e qual dos dois foi usado
tem de ser legível no envelope.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess

from ..envelope import Causa, Item, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))

SERIES = {
    "adr": ("platafirma-arquitetura", "macro-global/decisions"),
    "seg": ("platafirma-arquitetura", "macro-global/capabilities/seguranca/decisions"),
    "ont": ("platafirma-conhecimento", "ontologia/adr"),
}

CHAVE_RE = re.compile(r"^(adr|seg|ont):(\d{1,4})$", re.IGNORECASE)
ARQUIVO_RE = re.compile(r"^(\d{4})-(.+)\.md$")


class AdaptadorRegistro(Adaptador):
    fonte = Fonte.REGISTRO
    tem_gold = False

    def __init__(self, raiz: str = RAIZ) -> None:
        self.raiz = raiz

    # ---- morada ---------------------------------------------------------------------

    def _dir(self, serie: str) -> str:
        repo, sub = SERIES[serie]
        return os.path.join(self.raiz, repo, sub)

    def _repo(self, serie: str) -> str:
        return os.path.join(self.raiz, SERIES[serie][0])

    def _lista(self, serie: str) -> list[tuple[str, str, str]]:
        """(numero, titulo-slug, caminho) de cada decisão da série."""
        d = self._dir(serie)
        try:
            nomes = sorted(os.listdir(d))
        except OSError as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, f"{serie}: {d}") from e
        saida = []
        for nome in nomes:
            m = ARQUIVO_RE.match(nome)
            if m:
                saida.append((m.group(1), m.group(2), os.path.join(d, nome)))
        return saida

    # ---- carimbo --------------------------------------------------------------------

    def _carimbo(self) -> str:
        """Sha do HEAD do repositório de arquitetura, que é onde `adr:` e `seg:` moram.

        `ont:` mora em outro repo e por isso o carimbo é composto: dois shas, um por
        repositório. Carimbo de uma fonte que se espalha por dois repos e declara só um
        deles envelheceria calado no outro.
        """
        partes = []
        for repo in ("platafirma-arquitetura", "platafirma-conhecimento"):
            partes.append(f"{repo.split('-')[-1]}:{self._sha_head(os.path.join(self.raiz, repo))}")
        return " ".join(partes)

    def _sha_head(self, repo: str) -> str:
        try:
            p = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, timeout=5)
            if p.returncode == 0:
                return p.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return "sem-git"

    def _versao(self, serie: str, caminho: str) -> Versao:
        rel = os.path.relpath(caminho, self._repo(serie))
        try:
            p = subprocess.run(["git", "-C", self._repo(serie), "rev-parse", f"HEAD:{rel}"],
                               capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                return Versao(tipo=VersaoTipo.SHA, valor=p.stdout.strip()[:12])
        except (OSError, subprocess.SubprocessError):
            pass
        with open(caminho, "rb") as fh:
            return Versao(tipo=VersaoTipo.DIGEST, valor=hashlib.sha256(fh.read()).hexdigest()[:12])

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = filtros or {}
        series = [s.lower() for s in filtros.get("serie", SERIES)]
        alvo = (alvo or "").strip()

        m = CHAVE_RE.match(alvo)
        if m:
            serie, num = m.group(1).lower(), m.group(2).zfill(4)
            return self._por_numero(serie, num, texto)

        termos = [t for t in re.split(r"[\s_-]+", alvo.lower()) if t]
        achados = []
        for serie in series:
            if serie not in SERIES:
                continue
            for num, slug, caminho in self._lista(serie):
                alvo_busca = f"{num} {slug.replace('-', ' ')}"
                if not termos or all(t in alvo_busca for t in termos):
                    achados.append(self._item(serie, num, slug, caminho, texto="nenhum"))
        return achados

    def _por_numero(self, serie: str, num: str, texto: str) -> list[Item]:
        for n, slug, caminho in self._lista(serie):
            if n == num:
                return [self._item(serie, n, slug, caminho, texto)]
        return []

    def _item(self, serie: str, num: str, slug: str, caminho: str, texto: str) -> Item:
        chave = f"{serie}:{num}"
        proc = Procedencia(fonte=Fonte.REGISTRO, chave=chave, versao=self._versao(serie, caminho))
        if texto == "nenhum":
            return Item(procedencia=proc, ref=f"{chave} — {slug.replace('-', ' ')}")
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            corpo = fh.read()
        if texto == "trecho":
            corpo = corpo[:800] + ("\n[…]" if len(corpo) > 800 else "")
        return Item(procedencia=proc, conteudo=corpo)
