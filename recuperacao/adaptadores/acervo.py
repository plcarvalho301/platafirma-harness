"""Adaptador do acervo — a única fonte semântica das seis.

`spec_recuperador.md` §5: contrato = API do rag; classe **semântica**; carimbo =
`indice_carimbo`; `dominio = plataforma-acervo`; `tipo = acervo`; prefixo de `sobre` =
`acervo:<colecao>/*`. §4: chave = `acervo:<sha256 do objeto>#<âncora>[:p<idx>]`, versão =
`impressao.id`.

**É a única que gradua**, e por isso é a única que carrega `sinal`: as outras cinco são
exatas, o retorno é determinístico e não há piso a comparar. A régua viaja no envelope
porque duas chamadas na mesma sessão podem sair com réguas distintas — sem `rerank`, a
medida é distância vetorial com piso `MIN_SIM`; com `rerank`, é o juízo do revisor com
piso `MIN_CE`. Ler o rótulo sem a régua é ler metade.

## Fail-closed na chave, e por quê (achado de 20/08/2026)

`/search` devolve `section_id` no formato **`curto-v1`**: um PREFIXO determinístico do
`document_id` (que é o sha256 do objeto), com 8+ chars. O §4 é explícito — `curto-v1` é
projeção de exibição, **nenhuma chave gravada em artefato o carrega**, e o gate do §10
compara o sha inteiro. O prefixo não é o `objeto_id`, e a API não expõe a forma completa
por requisição: o knob `section_id_curto` é da instância, e desligá-lo pioraria o
`rag_search` de todo mundo.

Logo, o adaptador **não inventa a chave**: sem forma completa, ele levanta
`FonteIndisponivel(SEM_INDICE)`, e a fonte sai declarada como não indexada em vez de
servir procedência que o gate rejeitaria depois. Chave projetada em artefato é o dano que
a invariante 1 existe para impedir.

`PF_ACERVO_CHAVE_CURTA=1` é o **escape de bancada**, para medir latência e token enquanto
a dependência não fecha. Ele existe nomeado e desligado por default: escape que vira
default é a forma mais rápida de a projeção virar chave sem ninguém decidir.

Dois pedidos a claudinho-dados, dono do produto (#2313, e a dependência já declarada no
§4): `section_id` completo por requisição, e `impressao.id` no retorno de cada fonte —
sem o segundo, a versão sai como o `acervo_sha` do índice, que carimba o ÍNDICE e não a
impressão da obra citada.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from ..envelope import Casamento, Causa, Cobertura, Item, Procedencia, Sinal, Versao, VersaoTipo
from ..fontes import Fonte
from .base import Adaptador, FonteIndisponivel

BASE = os.environ.get("RAG_API_URL", "http://127.0.0.1:8100").rstrip("/")
TOKEN = os.environ.get("RAG_API_TOKEN", "")
TIMEOUT_S = float(os.environ.get("RAG_TIMEOUT_S", "10"))
CHAVE_CURTA = os.environ.get("PF_ACERVO_CHAVE_CURTA") == "1"

FORMATO_COMPLETO = "completo-v1"

# `texto="secao"` não devolve a seção POR FONTE: o rag monta uma fita única em `contexto`,
# numerada `[n] (arquivo · section_id) — breadcrumb`, e deixa `fontes[].texto` nulo. É a
# recuperação contextual do §5 do lado deles — o trecho recolado à seção que lhe dá
# sentido —, e sem desmembrar a fita o envelope serviria só rótulo onde a fonte serviu
# texto. O corte casa `[n]` com `fontes[n-1]`, e SÓ vale quando a contagem bate: bloco a
# menos, e o adaptador cai para `ref` em vez de emparelhar texto com a procedência errada,
# que é o pior defeito possível numa citação.
_BLOCO = re.compile(r"^\[(\d+)\] \(", re.MULTILINE)

# Rótulo do rag → enum do §3. O rag não tem `nao-calibrada` nem `fonte-nao-indexada`:
# aquele é juízo do adaptador (§13, sem gold), este é falha de alcance.
COBERTURA = {
    "boa": Cobertura.COBERTA,
    "fraca": Cobertura.FRACA,
    "ausente": Cobertura.AUSENTE,
    "vazia": Cobertura.VAZIA,
}


class AdaptadorAcervo(Adaptador):
    fonte = Fonte.ACERVO
    tem_gold = False  # §13 — o gold do acervo é #2309; até lá, `nao-calibrada`

    def __init__(self, base: str = BASE, token: str = TOKEN, timeout_s: float = TIMEOUT_S,
                 chave_curta: bool = CHAVE_CURTA, http=None) -> None:
        self.base, self.token, self.timeout_s = base, token, timeout_s
        self.chave_curta = chave_curta
        self._http = http or self._chama          # injeção: contrato testa sem sair à rede
        self._ultimo: dict = {}                   # resposta do último `_busca`, para `sinal`
        self._carimbo_cache: str = ""             # constante de sessão (ver `_carimbo`)

    # ---- transporte -----------------------------------------------------------------

    def _chama(self, rota: str, corpo: dict | None = None) -> dict:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(
            f"{self.base}{rota}", data=dados,
            headers={"content-type": "application/json",
                     **({"authorization": f"Bearer {self.token}"} if self.token else {})},
            method="POST" if corpo is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # noqa: S310
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            corpo_erro = e.read()[:200].decode(errors="replace")
            if e.code in (401, 403):
                raise FonteIndisponivel(Causa.SEM_CONCESSAO, corpo_erro) from e
            if e.code == 503:  # a API aquecendo o embedder é fora do ar, não sem índice
                raise FonteIndisponivel(Causa.FORA_DO_AR, "aquecendo") from e
            raise FonteIndisponivel(Causa.FORA_DO_AR, f"HTTP {e.code}: {corpo_erro}") from e
        except (urllib.error.URLError, OSError) as e:
            raise FonteIndisponivel(Causa.SEM_ROTA, f"{self.base}: {e}") from e
        except TimeoutError as e:
            raise FonteIndisponivel(Causa.TIMEOUT, self.base) from e
        except ValueError as e:
            raise FonteIndisponivel(Causa.FORA_DO_AR, "resposta não é JSON") from e

    # ---- carimbo --------------------------------------------------------------------

    def _carimbo(self) -> str:
        """`acervo_sha` de `/facets` — o carimbo do índice inteiro (§8).

        Constante de sessão do lado do rag (card #357): saiu de toda busca e ficou só em
        `/facets`. Por isso é lido UMA vez por instância e memoizado — reenviar em toda
        consulta o que não muda é o que a régua da cadeira chama de contexto gasto em
        campo repetido. Instância nova relê; o `ops-mcp` a recria por processo.
        """
        if self._carimbo_cache:
            return self._carimbo_cache
        d = self._http("/facets")
        sha = ((d.get("indice") or {}).get("acervo_sha") or "").strip()
        if not sha:
            raise FonteIndisponivel(Causa.SEM_INDICE, "/facets sem acervo_sha")
        self._carimbo_cache = f"acervo:{sha[:12]}"
        return self._carimbo_cache

    # ---- busca ----------------------------------------------------------------------

    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        filtros = filtros or {}
        pergunta = (alvo or "").strip()
        if not pergunta:
            return []
        corpo = {"pergunta": pergunta, "k": k, "texto": texto}
        for eixo in ("dominio", "subdominio", "frente", "colecao"):
            if filtros.get(eixo):
                corpo[eixo] = filtros[eixo]
        if filtros.get("rerank"):
            corpo["rerank"] = True
        d = self._http("/search", corpo)
        if d.get("erro"):
            raise FonteIndisponivel(Causa.FORA_DO_AR, str(d["erro"])[:120])
        self._ultimo = d

        formato = d.get("formato_section_id")
        if formato != FORMATO_COMPLETO and not self.chave_curta:
            raise FonteIndisponivel(
                Causa.SEM_INDICE,
                f"`{formato}` é projeção de exibição, não chave estrutural (§4) — "
                "a API não serve a forma completa por requisição (achado 20/08, #2313)")

        # `/search` NÃO devolve o carimbo (card #357 tirou de toda busca) — vem de
        # `/facets`, memoizado. Sem isto a versão sairia `sem-carimbo`, medido em 20/08.
        carimbo = self._carimbo().removeprefix("acervo:")
        fontes = d.get("fontes") or []
        secoes = self._secoes(d, len(fontes)) if texto == "secao" else {}
        return [self._item(f, texto, carimbo, secoes.get(f.get("n")))
                for f in fontes]

    @staticmethod
    def _secoes(d: dict, n_fontes: int) -> dict[int, str]:
        """A fita de `contexto` partida por `[n]`, e só se a contagem bater."""
        fita = d.get("contexto") or ""
        if not fita:
            return {}
        marcas = list(_BLOCO.finditer(fita))
        if len(marcas) != n_fontes:
            return {}
        saida = {}
        for i, m in enumerate(marcas):
            fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(fita)
            saida[int(m.group(1))] = fita[m.start():fim].strip()
        return saida

    def _item(self, f: dict, texto: str, carimbo: str, secao: str | None = None) -> Item:
        sid = (f.get("section_id") or "").strip()
        if not sid:
            raise FonteIndisponivel(Causa.SEM_INDICE, "fonte sem section_id")
        objeto, _, ancora = sid.partition("#")
        chave = f"acervo:{objeto}" + (f"#{ancora}" if ancora else "")
        # `impressao.id` não vem no retorno (achado 20/08): o carimbo do ÍNDICE é o
        # carimbo honesto disponível, e sai marcado como `digest` para que ninguém o leia
        # como versão da impressão.
        versao = Versao(tipo=VersaoTipo.DIGEST, valor=(carimbo or "sem-carimbo")[:12])
        proc = Procedencia(fonte=Fonte.ACERVO, chave=chave, versao=versao)
        casamento = Casamento.EXATO if f.get("codigo_exato") else Casamento.APROXIMADO
        corpo = secao if texto == "secao" else f.get("texto")
        if texto == "nenhum" or corpo is None:
            trilha = " › ".join(f.get("breadcrumb") or [])
            ref = f"{f.get('obra', '?')}" + (f" — {trilha}" if trilha else "")
            return Item(procedencia=proc, ref=ref, casamento=casamento)
        return Item(procedencia=proc, conteudo=corpo, casamento=casamento)

    # ---- juízo ----------------------------------------------------------------------

    def sinal(self, itens: list[Item]) -> Sinal | None:
        """A régua do rag, repassada como está — inclusive `medida`, que diz QUAL régua."""
        s = (self._ultimo or {}).get("sinal") or {}
        if not s.get("medida"):
            return None
        return Sinal(medida=str(s["medida"]), valor=s.get("valor") or 0.0,
                     piso=s.get("piso") or 0.0)

    def cobertura_com_item(self) -> Cobertura:
        """Sem gold, `nao-calibrada` — mesmo quando o rag disse `boa` (§13).

        O rótulo do rag mede distância contra piso; o gold mede se o retorno responde a
        pergunta. Promover um ao outro é o defeito que `arq:0064` §2 nomeia: instrumento
        desligado não vira instrumento por dizer um número.
        """
        return Cobertura.COBERTA if self.tem_gold else Cobertura.NAO_CALIBRADA

    def cobertura_do_rag(self) -> Cobertura | None:
        """O rótulo que o rag serviu, para quem quiser comparar as duas réguas."""
        return COBERTURA.get((self._ultimo or {}).get("cobertura"))
