"""Adaptador do acervo — a única fonte semântica das seis.

Dois papéis, dois donos (arq:0119 §1.2 e §4; migração 079, `ferramental_fonte_papel`): a
BUSCA pelo sentido é da capacidade `motor` (dona ia) e devolve só endereço — obra, seção,
escore, cobertura; a LEITURA do texto pelo endereço é da capacidade `conhecimento` (dona
dados), na rota `POST /acervo/secoes/consulta`. O adaptador encadeia as duas e não monta
texto por conta própria (#3312).

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

# arq:0119 §1.2 e §3: a busca (capacidade motor, dona ia) devolve endereço, escore e
# cobertura; a consulta termina com a fonte entregue pelo acervo (capacidade conhecimento,
# dona dados). Por isso o adaptador pede à busca SEMPRE `texto="nenhum"` e, quando o
# chamador quer texto, lê a seção na rota de leitura pelo `secao_id` que a busca devolveu —
# a mesma rota que o verbo `acervo ler <particao> secao` consome, e é isso que faz o texto
# servido aqui ser o mesmo do verbo no mesmo endereço (#3312).
ROTA_BUSCA = "/acervo/trechos/consulta"
ROTA_LEITURA = "/acervo/secoes/consulta"
LOTE_LEITURA = 50  # teto da rota de leitura por chamada

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
        d = self._http("/acervo/facetas")
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
        # A busca devolve só o endereço; o texto vem da leitura (arq:0119 §1.2).
        corpo = {"pergunta": pergunta, "k": k, "texto": "nenhum"}
        for eixo in ("dominio", "subdominio", "frente", "colecao"):
            if filtros.get(eixo):
                corpo[eixo] = filtros[eixo]
        if filtros.get("rerank"):
            corpo["rerank"] = True
        d = self._http(ROTA_BUSCA, corpo)
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
        textos: dict[str, str] = {}
        if texto != "nenhum" and fontes:
            particao = ((d.get("filtro") or {}).get("particao") or "").strip()
            ids = [str(f["secao_id"]).lower() for f in fontes if f.get("secao_id")]
            textos = self._le_secoes(particao, ids)
        return [self._item(f, texto, carimbo,
                           textos.get(str(f.get("secao_id") or "").lower()))
                for f in fontes]

    def _le_secoes(self, particao: str, ids: list[str]) -> dict[str, str]:
        """O texto de cada seção pela rota de leitura do acervo, chaveado pelo `secao_id`.

        A partição vem uma vez por resposta da busca (`filtro.particao`); cada busca é
        numa partição só. Seção que a leitura não serve (`nao_achadas`: fora de serviço,
        retirada, só parte não textual) fica sem texto, e o item sai por `ref` — nunca com
        texto de outra seção. Falha de transporte da leitura levanta: a fonte não entregou.
        """
        if not particao or not ids:
            return {}
        unicos = list(dict.fromkeys(ids))
        saida: dict[str, str] = {}
        for i in range(0, len(unicos), LOTE_LEITURA):
            lote = unicos[i:i + LOTE_LEITURA]
            r = self._http(ROTA_LEITURA, {"particao": particao, "secao_ids": lote})
            for s in r.get("secoes") or []:
                sid, corpo = str(s.get("secao_id") or "").lower(), s.get("texto")
                if sid in lote and corpo is not None:
                    saida[sid] = corpo
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
        corpo = secao
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
