"""Adaptador da wiki — a decisão da casa, lida pelo Cargo e pela API do MediaWiki.

`spec_recuperador.md` §5: contrato = API do MediaWiki; carimbo = `rev_id` / `rc_id`;
classe exata; `dominio = plataforma-wiki`; `tipo = wiki`; prefixo de `sobre` =
`wiki:<ns>/*`. §4: chave = `wiki:<page_id>#<seção>`, versão = `rev_id`.

**Ao contrato, nunca ao binário, e nunca ao MCP.** O `wiki-mcp` é outro consumidor da
mesma API, com a mesma dignidade deste — encadear um no outro acoplaria a recuperação à
superfície de ferramenta de outra cadeira e faria toda mudança de forma do MCP virar
quebra aqui. Os dois falam `api.php`.

**Três caminhos de busca, e a escolha é do alvo, não do chamador:**

| entrada | ato do MediaWiki | por quê |
|---|---|---|
| `wiki:<Título>` ou `<Título>[#seção]` | `prop=revisions` | alvo nominal: uma página, com id e revid |
| `filtros={"tabela": …}` | `action=cargoquery` | faceta DECLARADA — predicado, não varredura de prosa |
| termo livre | `list=search` | significado na prosa; o que o Cargo não indexa |

`page_id`, e não título, porque **título é volátil e id não é**: mover a página troca o
título e preserva o `page_id`, e chave que muda em renomeação é chave que envelhece calada
no artefato que a citou. O título vai no `ref`, para humano ler.

**O `rc_id` é o carimbo da fonte inteira**, e o `rev_id` é a versão do item — os dois são
pedidos pela spec e não são a mesma coisa: `rc_id` é o ledger de mudanças da wiki, cresce
a cada edição de qualquer página, e responde "a wiki mudou desde a última leitura?" sem
varrer nada.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request

from ..envelope import Casamento, Causa, Item, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

API = os.environ.get("MW_API_URL", "http://127.0.0.1:8080/api.php")
TIMEOUT_S = float(os.environ.get("MW_TIMEOUT_S", "10"))
UA = "platafirma-recuperador/1.0 (claudinho-IA)"

# Namespaces que o `sobre` do PEP nomeia. O corte de alcance é do PEP (§6); aqui o mapa
# serve para projetar `wiki:<ns>/<título>` no `ref`, que é o que o PEP recebe como alvo.
NS_PREFIXO = {0: "principal", 4: "PlataFirma", 12: "Ajuda", 3000: "Frente", 3004: "Operar"}

# Namespaces de CONTEÚDO da busca em prosa. O default da API é só o ns 0, e com ele
# `PlataFirma:`, `Frente:` e `Operar:` somem da busca sem erro nenhum.
#
# DIVERGE do `search_pages` do wiki-mcp DE PROPÓSITO, e o §5 manda declarar em vez de
# copiar: o `CONTENT_NS` de lá é `0|4|12|3000`, e a docstring da própria tool diz cobrir
# `Operar:` — que é o ns **3004**, não o 3000 (3000 é `Frente:`). Medido no siteinfo em
# 20/08/2026. Replicar o engano faria o adaptador bater com o verbo humano por errar
# igual; o achado vai a claudinho-dados, dono da wiki, com a medição.
CONTENT_NS = "0|4|12|3000|3004"


class AdaptadorWiki(Adaptador):
    fonte = Fonte.WIKI
    tem_gold = False  # §13 — vira True com o gold da wiki (#2309)

    def __init__(self, api: str = API, timeout_s: float = TIMEOUT_S,
                 abre_url=None) -> None:
        self.api, self.timeout_s = api, timeout_s
        self._abre = abre_url or self._abre_url  # injeção: o teste de contrato não sai à rede

    # ---- transporte -----------------------------------------------------------------

    def _abre_url(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # noqa: S310
            return r.read()

    def _api(self, **params) -> dict:
        """Erro de rede vira `FonteIndisponivel`, nunca exceção crua: quem precisa saber
        é o disjuntor, e quem transforma em linha é `busca_declarada` (§5)."""
        import json

        url = f"{self.api}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
        try:
            bruto = self._abre(url)
        except urllib.error.URLError as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, f"{self.api}: {e}") from e
        except TimeoutError as e:
            raise FonteIndisponivel(Causa.TIMEOUT, self.api) from e
        except Exception as e:  # noqa: BLE001
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"{self.api}: {e}") from e
        try:
            d = json.loads(bruto)
        except ValueError as e:
            raise FonteIndisponivel(Causa.FORA_DO_AR, "resposta não é JSON") from e
        if isinstance(d, dict) and "error" in d:
            # PARSE do JSON, nunca código de status: o MediaWiki devolve 200 com erro
            # dentro (mesma disciplina do compose da wiki).
            raise FonteIndisponivel(Causa.FORA_DO_AR, str(d["error"].get("code", "erro")))
        return d

    # ---- carimbo --------------------------------------------------------------------

    def _carimbo(self) -> str:
        """`rc_id` do topo do ledger de mudanças recentes."""
        d = self._api(action="query", list="recentchanges", rclimit=1, rcprop="ids")
        rc = (d.get("query", {}).get("recentchanges") or [{}])[0]
        if not rc.get("rcid"):
            raise FonteIndisponivel(Causa.SEM_INDICE, "recentchanges vazio")
        return f"rc:{rc['rcid']}"

    # ---- alvo -----------------------------------------------------------------------

    @staticmethod
    def alvo_e_secao(alvo: str) -> tuple[str, str]:
        """`wiki:PlataFirma:Sec/contrato#§3` → (`PlataFirma:Sec/contrato`, `§3`)."""
        alvo = (alvo or "").strip()
        if alvo.startswith("wiki:"):
            alvo = alvo[len("wiki:"):]
        titulo, _, secao = alvo.partition("#")
        return titulo.strip(), secao.strip()

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = filtros or {}
        if filtros.get("tabela"):
            return self._por_cargo(filtros, k)
        titulo, secao = self.alvo_e_secao(alvo)
        if not titulo:
            return []
        itens = self._por_titulo(titulo, secao, texto)
        if itens:
            return itens
        return self._por_termo(titulo, k)

    # -- nominal --

    def _por_titulo(self, titulo: str, secao: str, texto: str) -> list[Item]:
        prop = "ids|content" if texto in ("secao", "trecho") else "ids"
        d = self._api(action="query", prop="revisions", titles=titulo,
                      rvprop=prop, rvslots="main", formatversion=2)
        paginas = d.get("query", {}).get("pages") or []
        saida = []
        for p in paginas:
            if p.get("missing") or not p.get("pageid"):
                continue
            saida.append(self._item(p, secao, texto, Casamento.EXATO))
        return saida

    # -- faceta declarada --

    def _por_cargo(self, filtros: dict, k: int) -> list[Item]:
        """Cargo é PREDICADO sobre campo declarado, e é por isso que ele entra aqui em vez
        de `list=search`: valor de faceta não se procura na prosa (`query_cargo`, tool-manifest)."""
        campos = filtros.get("campos") or "_pageName=pagina"
        if "_pageName" not in campos:
            campos = f"_pageName=pagina,{campos}"
        d = self._api(action="cargoquery", tables=filtros["tabela"], fields=campos,
                      where=filtros.get("where", ""), limit=min(k, 100))
        titulos = []
        for linha in d.get("cargoquery") or []:
            t = (linha.get("title") or {}).get("pagina")
            if t:
                titulos.append(t)
        return self._resolve_em_lote(titulos[:k], Casamento.EXATO)

    # -- prosa --

    def _por_termo(self, termo: str, k: int) -> list[Item]:
        d = self._api(action="query", list="search", srsearch=termo,
                      srnamespace=CONTENT_NS, srlimit=min(k, 50), srprop="",
                      formatversion=2)
        achados = d.get("query", {}).get("search") or []
        return self._resolve_em_lote([a["title"] for a in achados], Casamento.APROXIMADO)

    def _resolve_em_lote(self, titulos: list[str], casamento: Casamento) -> list[Item]:
        """UMA chamada para N títulos. `revid` por página é obrigatório (§4) e resolver um
        a um custaria N idas à fonte por consulta — o teto de 50 é o da própria API."""
        if not titulos:
            return []
        saida = []
        for i in range(0, len(titulos), 50):
            lote = titulos[i:i + 50]
            d = self._api(action="query", prop="revisions", titles="|".join(lote),
                          rvprop="ids", formatversion=2)
            for p in d.get("query", {}).get("pages") or []:
                if p.get("missing") or not p.get("pageid"):
                    continue
                saida.append(self._item(p, "", "nenhum", casamento))
        return saida

    # ---- projeção -------------------------------------------------------------------

    def _item(self, pagina: dict, secao: str, texto: str, casamento: Casamento) -> Item:
        rev = (pagina.get("revisions") or [{}])[0]
        revid = rev.get("revid")
        if not revid:
            raise FonteIndisponivel(Causa.SEM_INDICE,
                                    f"página {pagina.get('pageid')} sem revid")
        chave = f"wiki:{pagina['pageid']}" + (f"#{secao}" if secao else "")
        proc = Procedencia(fonte=Fonte.WIKI, chave=chave,
                           versao=Versao(tipo=VersaoTipo.REVID, valor=str(revid)))
        ns = NS_PREFIXO.get(pagina.get("ns", 0), str(pagina.get("ns", 0)))
        rotulo = f"{pagina.get('title', '?')} · wiki:{ns}"
        if texto == "nenhum":
            return Item(procedencia=proc, ref=rotulo, casamento=casamento)
        corpo = ((rev.get("slots") or {}).get("main") or {}).get("content") or rev.get("content")
        if corpo is None:
            return Item(procedencia=proc, ref=rotulo, casamento=casamento)
        if texto == "trecho":
            corpo = corpo[:800] + ("\n[…]" if len(corpo) > 800 else "")
        return Item(procedencia=proc, conteudo=corpo, casamento=casamento)
