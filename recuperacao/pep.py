"""PEP por fonte — o ponto que IMPÕE a decisão do PDP dentro do `recuperar` (§6).

`spec_recuperador.md` §6, card #2303.

A divisão de papéis é a canônica de controle de acesso baseado em atributo, e não é
invenção da casa: o PDP avalia e emite a decisão, o PEP a impõe no caminho do pedido,
o PIP fornece atributo e o PAP guarda a política — os quatro pontos funcionais do
mecanismo (NIST SP 800-162 §2.4.3; CSA Security Guidance v3.0 §12.7, que descreve o PEP
como podendo ser tão simples quanto um `if` no serviço). Aqui: PDP é
`politica-acesso/pdp.py` (biblioteca embarcada, `seg:0008`), PAP é `politica.yaml`,
PIP é `sujeitos.yaml` (projeção interina, enquanto o token não carrega os atributos),
e PEP é este módulo, chamado por `recuperar()` **antes** de qualquer adaptador rodar.

Cinco decisões, e o porquê de cada uma:

1. **Uma chamada por fonte, nunca uma por pedido.** Cada fonte carrega o seu par
   `(dominio, sobre)` do §5 — `fontes.py` já os declara. Um PEP único, com um domínio
   só, faria a concessão de uma matéria valer pela outra: é exatamente o que `seg:0009`
   separa quando distingue `plataforma-acervo` de `plataforma-wiki`.

2. **Negativa em qualquer fonte nega o pedido inteiro** (§6). Não há busca parcial:
   nem entre fontes, nem entre alvos da mesma fonte. Pedido de três domínios com
   concessão de dois não vira busca em dois — vira recusa, e o par `falta`/`proximo`
   diz o que pedir de novo. O envelope de recusa mantém a invariante 4 (uma linha por
   fonte pedida) e todas saem com `sem-concessao`, porque a unidade autorizada é o
   PEDIDO: quem não teve o pedido concedido não teve fonte alcançada.

3. **Fail-closed em toda falha do mecanismo.** Política ilegível, sujeito fora da
   projeção, atributo ausente: nega. O default do PDP já é negar (regime §6 do
   `pdp.py`); aqui a régua se repete porque o erro de carregamento não chega ao PDP —
   ele nem é chamado. Negar por falha de mecanismo é o mesmo que negar por regra, e a
   trilha registra qual dos dois foi.

4. **A ação é o verbo humano que já rege a matéria**, não um verbo novo: `rag_buscar`
   no acervo, `wiki_ler` na wiki, `msg_ler` na fila. O recuperador não amplia o alcance
   de ninguém — ele herda a concessão que já existe. Board, mesa e registro não têm
   verbo de leitura no PAP e ficam em `recuperar`: quem tem regra ampla (`operador`,
   `reino`) passa; quem tem concessão nominal não passa sem regra nova, que é merge no
   PAP e não linha de código.

5. **Alvo ausente vira `<prefixo>*`, nunca `*`.** `sobre` vazio vira `*` dentro do PDP,
   e `*` entrega a matéria inteira — a própria `politica.yaml` avisa disso. O prefixo
   por fonte mantém o alvo dentro da matéria e deixa a concessão nominal (que nomeia
   recorte, como `acervo:firma/*`) negar o pedido genérico, como deve.

O que NÃO mora aqui: a identidade. Quem é o sujeito é do host — dentro de tool, o
contexto do FastMCP é a única fonte honesta (mesma razão de `_quem` no `ops-server`).
Este módulo recebe o `sujeito` já resolvido e não tenta adivinhá-lo: biblioteca que
inventa identidade é biblioteca que autoriza a si mesma.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

from .envelope import Causa, Cobertura, Envelope, LinhaFonte
from .fontes import DOMINIO, PREFIXO_SOBRE, TIPO, Fonte

# §6 — a ação por fonte. Verbo humano onde ele existe no PAP; `recuperar` onde não há.
ACAO: dict[str, str] = {
    "acervo": "rag_buscar",
    "wiki": "wiki_ler",
    "fila": "msg_ler",
    "board": "recuperar",
    "mesa": "recuperar",
    "registro": "recuperar",
}

_RAIZ = Path(__file__).resolve().parents[1]


def _dir_politica() -> Path:
    return Path(os.environ.get("PF_POLITICA_DIR") or (_RAIZ / "politica-acesso"))


@dataclass(frozen=True, slots=True)
class Negativa:
    """A negativa auditada de UMA fonte. `regra` distingue falha de mecanismo de
    decisão de política: `projecao` e `politica` são mecanismo, o resto é regra do PAP."""

    fonte: Fonte
    alvo: str
    regra: str
    motivo: str
    por_atributo_ausente: bool = False

    def como_dict(self) -> dict:
        return {"fonte": str(self.fonte), "sobre": self.alvo, "regra": self.regra,
                "motivo": self.motivo}


class PEP:
    """Ponto de imposição. Um por processo; relê o PAP quando o mtime muda.

    `auditor` é injetado pelo host: a trilha do §11 é do consumidor, não da biblioteca.
    Sem auditor, o PEP decide igual e não registra — e é por isso que o `ops-mcp` passa
    o dele. Assinatura: `auditor(evento: dict) -> None`.
    """

    def __init__(self, dir_politica: Path | str | None = None,
                 auditor: Callable[[dict], None] | None = None) -> None:
        self.dir = Path(dir_politica) if dir_politica else _dir_politica()
        self.auditor = auditor
        self._carimbo: tuple[int, int] | None = None
        self._politica = None
        self._sujeitos: dict = {}
        self._erro: str | None = None

    # ---- PAP e PIP ------------------------------------------------------------------

    def _carrega(self) -> None:
        pol_f, suj_f = self.dir / "politica.yaml", self.dir / "sujeitos.yaml"
        try:
            carimbo = (pol_f.stat().st_mtime_ns, suj_f.stat().st_mtime_ns)
        except OSError as e:
            self._carimbo, self._politica, self._sujeitos = None, None, {}
            self._erro = f"politica ilegivel: {e}"
            return
        if self._carimbo == carimbo and self._erro is None:
            return
        try:
            if str(self.dir) not in sys.path:
                sys.path.insert(0, str(self.dir))
            import yaml
            from pdp import Politica

            self._politica = Politica.de_arquivo(pol_f)
            self._sujeitos = (yaml.safe_load(suj_f.read_text(encoding="utf-8")) or {}
                              ).get("sujeitos") or {}
            self._carimbo, self._erro = carimbo, None
        except Exception as e:  # noqa: BLE001 — política quebrada NEGA, não estoura
            self._carimbo, self._politica, self._sujeitos = carimbo, None, {}
            self._erro = f"{type(e).__name__}: {e}"

    def _audita(self, **ev) -> None:
        if self.auditor is not None:
            self.auditor(ev)

    # ---- decisão --------------------------------------------------------------------

    def alvo_padrao(self, fonte: Fonte) -> str:
        """`<prefixo>*` — dentro da matéria, nunca `*`."""
        return f"{PREFIXO_SOBRE[Fonte(fonte)]}*"

    def acao(self, fonte: Fonte) -> str:
        return ACAO.get(str(fonte), "recuperar")

    def autoriza_fonte(self, sujeito: str, fonte: Fonte,
                       alvos: Iterable[str] | None = None,
                       acao: str | None = None) -> Negativa | None:
        """`None` = a fonte pode ser alcançada. `Negativa` = não pode, com o motivo.

        Um recurso por alvo pedido: qualquer alvo negado nega a FONTE inteira, jamais
        vira busca nos alvos que sobraram.
        """
        f = Fonte(fonte)
        alvos = [a for a in (alvos or []) if a] or [self.alvo_padrao(f)]
        acao = acao or self.acao(f)

        self._carrega()
        if self._erro:
            self._audita(evento="pep_indisponivel", fonte=str(f), sujeito=sujeito,
                         motivo=self._erro)
            return Negativa(f, alvos[0], "politica",
                            f"politica de acesso indisponivel — nego por default: {self._erro}")
        if not sujeito:
            self._audita(evento="pep_negou", fonte=str(f), regra="identidade",
                         motivo="sem identidade")
            return Negativa(f, alvos[0], "identidade", "nao autenticado",
                            por_atributo_ausente=True)

        atrib = self._sujeitos.get(sujeito)
        if not atrib:
            self._audita(evento="pep_negou", fonte=str(f), sujeito=sujeito,
                         regra="projecao", motivo="sujeito sem atributos declarados")
            return Negativa(f, alvos[0], "projecao",
                            f"sujeito {sujeito!r} nao tem atributos em "
                            "politica-acesso/sujeitos.yaml — o PDP nega por atributo ausente",
                            por_atributo_ausente=True)

        from pdp import Recurso, Sujeito, decide

        s = Sujeito(id=sujeito, natureza=atrib.get("natureza"),
                    papeis=tuple(atrib.get("papeis") or ()),
                    dominios=tuple(atrib.get("dominios") or ()),
                    temas=tuple(atrib.get("temas") or ()),
                    vetos=tuple(atrib.get("vetos") or ()),
                    habilitacao=atrib.get("habilitacao", "publico"))
        recurso_tipo, recurso_dom = TIPO[f], DOMINIO[f]
        for alvo in alvos:
            d = decide(s, acao, Recurso(tipo=recurso_tipo, id=alvo, dominio=recurso_dom),
                       self._politica)
            if not d.permitido:
                self._audita(evento="pep_negou", fonte=str(f), sujeito=sujeito,
                             acao=acao, sobre=alvo, regra=d.regra, motivo=d.motivo,
                             por_atributo_ausente=d.por_atributo_ausente)
                return Negativa(f, alvo, d.regra or "default", d.motivo or "negado por default",
                                por_atributo_ausente=d.por_atributo_ausente)
        self._audita(evento="pep_permitiu", fonte=str(f), sujeito=sujeito, acao=acao,
                     sobre=alvos)
        return None

    def autoriza(self, sujeito: str,
                 pedidos: Mapping[Fonte, Iterable[str]] | Iterable[Fonte],
                 acao: str | None = None) -> list[Negativa]:
        """Uma chamada por fonte alcançada. Devolve TODAS as negativas, não a primeira.

        Parar na primeira economizaria uma decisão e cobraria uma ida e volta por fonte
        negada: o chamador precisa saber o pedido inteiro que não passa, não o primeiro
        pedaço dele.
        """
        if isinstance(pedidos, Mapping):
            pares = [(Fonte(f), list(a or [])) for f, a in pedidos.items()]
        else:
            pares = [(Fonte(f), []) for f in pedidos]
        negativas = [n for f, alvos in pares
                     if (n := self.autoriza_fonte(sujeito, f, alvos, acao)) is not None]
        return negativas


# ---- recusa: a forma que o consumidor enxerga ----------------------------------------

def recusa_por_concessao(fontes: Iterable[Fonte],
                         negativas: Iterable[Negativa]) -> Envelope:
    """Envelope de recusa TOTAL: nenhuma fonte foi alcançada, e todas aparecem.

    Uma linha por fonte pedida (invariante 4), todas `fonte-nao-indexada` com
    `sem-concessao` — a unidade autorizada é o pedido, e o pedido não passou. `falta` e
    `proximo` nomeiam qual alvo derrubou e o que pedir de novo, que é o par "erro que
    instrui" do §3: negativa que não diz o próximo passo custa uma rodada inteira.
    """
    negativas = list(negativas)
    linhas = [LinhaFonte(fonte=Fonte(f), cobertura=Cobertura.FONTE_NAO_INDEXADA,
                         causa=Causa.SEM_CONCESSAO) for f in fontes]
    if negativas:
        alvos = ", ".join(n.alvo for n in negativas)
        regras = ", ".join(sorted({n.regra for n in negativas}))
        falta = f"concessao para {alvos} (regra: {regras})"
        restantes = sorted(str(l.fonte) for l in linhas
                           if l.fonte not in {n.fonte for n in negativas})
        sobra = (f" — {', '.join(restantes)} "
                 + ("segue alcancavel" if len(restantes) == 1 else "seguem alcancaveis")
                 ) if restantes else ""
        proximo = ("repetir sem "
                   + ", ".join(sorted({str(n.fonte) for n in negativas})) + sobra)
    else:  # defensivo: recusa sem negativa é bug do chamador, e sai declarada
        falta, proximo = "concessao", "revisar o pedido"
    return Envelope(linhas=linhas, itens=[], falta=falta, proximo=proximo)


__all__ = ["ACAO", "Negativa", "PEP", "recusa_por_concessao"]
