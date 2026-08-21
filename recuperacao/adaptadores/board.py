"""Adaptador do board — `item:<id>`.

`spec_recuperador.md` §5: contrato = HTTP do rastreador (`platafirma-rastreador`) mais o
header de identidade; classe exata; carimbo = `evento.id`, ledger monotônico. §4:
`chave = item:<id>`, versão = `evento.id` máximo **do item**.

**Projeta na origem, e é o ponto do card.** `GET /api/itens` era tudo-ou-nada — medido
por claudinho-TI em 20/08/2026: 383 itens, 493.576 bytes, 618 ms, 28 campos por item.
`#2299` entregou `?campos=`, e os seis campos do §5 saem em 56.771 bytes (8,7×). O
adaptador SEMPRE pede a projeção: 440 KB não entram em envelope, e pedir tudo para jogar
fora seria pagar a banda para descumprir o §5 no mesmo ato.

**O item nunca vai por `conteudo`.** O §5 é literal: `id, título, fase, cadeira, nível,
pai` na linha, e o resto por `ref`. Por isso `texto=` não muda o que este adaptador serve
— a descrição do card mora atrás de `GET /api/itens/<id>`, e quem a quiser segue a `ref`.
Servir corpo aqui transformaria uma leitura de estado em despejo de board no contexto.

**Versão por item, e o desvio que ela não tem.** `GET /api/itens/<id>/eventos` devolve o
ledger do item, então `max(evento.id)` do §4 é computável de verdade — medido em
20/08/2026: 5 ms por item no loopback, ~40 ms para k=8, dentro do timeout de 250 ms da
classe exata (§8). Item cujo ledger ainda não tem linha (o ledger começou a ser escrito
em `#2307`) serve `0@<carimbo global>`: declara que o evento não cobre o item e ancora no
carimbo do board inteiro. Preencher com timestamp seria o que o §5 proíbe, e omitir
violaria a invariante 1.

**Carimbo composto, por decisão de `#2307`:** `<max(evento.id)>/<contagem de itens>`. A
contagem cobre a janela em que o ledger ainda não cobre todo ato — apagar-e-criar no
mesmo instante muda a contagem quando o evento não muda — e sai quando o ledger fechar.

**Filtro de linha é da fonte; termo é recorte local.** `cadeira`, `estado`, `nivel` e
`origem` são eixos que a API recusa quando desconhecidos, e vão nela. Busca por termo no
título NÃO existe na API (`?q=` devolve 400, medido) — é filtrada aqui, sobre o que a
projeção já trouxe. Não é reimplementar a fonte: é o mesmo recorte que o adaptador do
registro faz sobre `listdir`, e nenhum estado novo é derivado.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from ..envelope import Causa, Item, Procedencia, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

BASE = os.environ.get("TAREFAS_BASE", "http://127.0.0.1:8120/api")
TIMEOUT_S = float(os.environ.get("PF_BOARD_TIMEOUT_S", "5"))
UA = "platafirma-recuperador/1.0 (claudinho-IA)"

# §5 — a projeção mínima. `id` sai sempre, pedido ou não (#2299): sem ele a chave
# `item:<id>` do §4 não fecha.
CAMPOS = ("id", "titulo", "estado", "cadeira", "nivel", "pai")

# Eixos que a API aceita como filtro de LINHA. Fora desta lista ela devolve 400 nomeando
# o campo — o adaptador não adivinha, repassa o que é dela e recorta o resto aqui.
EIXOS = ("cadeira", "estado", "nivel", "origem")

CHAVE_RE = re.compile(r"^(?:item:|#)?(\d{1,7})$")


class AdaptadorBoard(Adaptador):
    fonte = Fonte.BOARD
    tem_gold = False  # §13 — vira True com o gold das fontes exatas (#2309)

    def __init__(self, base: str = BASE, timeout_s: float = TIMEOUT_S,
                 quem: str | None = None, abre_url=None) -> None:
        self.base = base.rstrip("/")
        self.timeout_s = timeout_s
        # Header de identidade (§5). O rastreador não tem auth por desenho: quem escreve
        # declara o nome, e leitura anônima é leitura legítima. Mandar o nome quando ele
        # existe é o que deixa a trilha do §11 casar com a do rastreador.
        self.quem = quem if quem is not None else os.environ.get("PF_CADEIRA", "")
        self._abre = abre_url or self._abre_url  # injeção: o contrato não sai à rede

    # ---- transporte ---------------------------------------------------------------

    def _abre_url(self, url: str) -> bytes:
        cab = {"User-Agent": UA}
        if self.quem:
            cab["x-auth-request-preferred-username"] = self.quem
        req = urllib.request.Request(url, headers=cab)
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # noqa: S310
            return r.read()

    def _get(self, rota: str, **params) -> dict:
        """Erro de rede vira `FonteIndisponivel`; quem precisa saber é o disjuntor."""
        url = f"{self.base}/{rota.lstrip('/')}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            bruto = self._abre(url)
        except urllib.error.HTTPError as e:
            # 400 do rastreador é recusa de vocabulário, não fonte caída — e a mensagem
            # dele já nomeia o campo. Vai como sem-rota: a rota pedida não existe assim.
            causa = Causa.SEM_ROTA if e.code in (400, 404) else Causa.FORA_DO_AR
            raise FonteIndisponivel(causa, f"{url}: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, f"{url}: {e}") from e
        except TimeoutError as e:
            raise FonteIndisponivel(Causa.TIMEOUT, url) from e
        except Exception as e:  # noqa: BLE001
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"{url}: {e}") from e
        try:
            d = json.loads(bruto)
        except ValueError as e:
            raise FonteIndisponivel(Causa.FORA_DO_AR, "resposta não é JSON") from e
        if isinstance(d, dict) and "erro" in d:
            raise FonteIndisponivel(Causa.SEM_ROTA, str(d["erro"]))
        return d

    # ---- carimbo ------------------------------------------------------------------

    def _carimbo(self) -> str:
        d = self._get("carimbo")
        c = d.get("carimbo")
        n = d.get("itens")
        if n is None:
            raise FonteIndisponivel(Causa.SEM_INDICE, "carimbo sem contagem de itens")
        return f"{0 if c is None else c}/{n}"

    def _carimbo_global(self) -> str:
        try:
            return self._carimbo().split("/", 1)[0]
        except FonteIndisponivel:
            return "0"

    # ---- versão por item ----------------------------------------------------------

    def _versao(self, item_id: int, carimbo_global: str) -> Versao:
        """`max(evento.id)` do item (§4). Sem linha no ledger, `0@<carimbo>` declarado."""
        try:
            d = self._get(f"itens/{item_id}/eventos")
        except FonteIndisponivel:
            return Versao(tipo=VersaoTipo.SEQ, valor=f"0@{carimbo_global}")
        ids = [e.get("id") for e in (d.get("eventos") or []) if isinstance(e.get("id"), int)]
        if not ids:
            return Versao(tipo=VersaoTipo.SEQ, valor=f"0@{carimbo_global}")
        return Versao(tipo=VersaoTipo.SEQ, valor=str(max(ids)))

    # ---- busca --------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = dict(filtros or {})
        alvo = (alvo or "").strip()
        carimbo_global = self._carimbo_global()

        m = CHAVE_RE.match(alvo)
        if m:
            return self._por_id(int(m.group(1)), carimbo_global)

        params = {"campos": ",".join(CAMPOS)}
        for eixo in EIXOS:
            if filtros.get(eixo) not in (None, ""):
                params[eixo] = str(filtros[eixo])
        d = self._get("itens", **params)
        linhas = d.get("itens")
        if linhas is None:
            raise FonteIndisponivel(Causa.SEM_INDICE, "resposta sem `itens`")

        termos = [t for t in re.split(r"[\s_-]+", alvo.lower()) if t]
        achados = []
        for linha in linhas:
            if termos and not all(t in str(linha.get("titulo", "")).lower() for t in termos):
                continue
            achados.append(self._item(linha, carimbo_global))
            if len(achados) >= k:
                break
        return achados

    def _por_id(self, item_id: int, carimbo_global: str) -> list[Item]:
        """Chave exata. Item inexistente é VAZIA, não falha — o §3 separa as duas."""
        try:
            d = self._get(f"itens/{item_id}")
        except FonteIndisponivel as e:
            if e.causa is Causa.SEM_ROTA:
                return []
            raise
        if not d.get("id"):
            return []
        return [self._item(d, carimbo_global)]

    def _item(self, linha: dict, carimbo_global: str) -> Item:
        item_id = linha["id"]
        proc = Procedencia(
            fonte=Fonte.BOARD,
            chave=f"item:{item_id}",
            versao=self._versao(item_id, carimbo_global),
        )
        return Item(procedencia=proc, ref=self._ref(linha))

    @staticmethod
    def _ref(linha: dict) -> str:
        """Os seis campos do §5, numa linha. É a projeção — nunca o corpo do card."""
        # A projeção do #2299 serve `nivel` como número; a rota do item serve também
        # `nivel_nome`. Rotular o número evita `ref` em que `2` fica solto entre nomes.
        nivel = linha.get("nivel_nome") or (
            f"nivel {linha['nivel']}" if linha.get("nivel") is not None else None
        )
        partes = [f"#{linha['id']}", str(linha.get("titulo") or "").strip()]
        cauda = [str(x) for x in (linha.get("estado"), linha.get("cadeira"), nivel) if x not in (None, "")]
        pai = linha.get("pai")
        if pai:
            cauda.append(f"pai #{pai}")
        return f"{' — '.join(p for p in partes if p)} [{' · '.join(cauda)}]"
