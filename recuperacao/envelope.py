"""Envelope único de leitura das seis fontes — dataclass e vocabulário fechado.

`spec_recuperador.md` §3, `arq:0064` §1 e §2. Importado por todo adaptador; nenhum
adaptador declara enum próprio nem devolve dicionário solto.

O que este módulo entrega é a FALHA DECLARADA, não o trecho devolvido: o que fez o
`rag_search` utilizável foi o envelope, e interface sem envelope é `open()` com outro
nome (`arq:0064` §1).

Invariantes do §3, todas conferidas em `test_contrato_envelope.py`, nenhuma por leitura:

1. Item sem `procedencia` completa não entra — o construtor levanta, não degrada.
2. `sinal` só existe com `medida` preenchida; fonte semântica sem medida não pode
   dizer `coberta` nem `fraca` — as duas são juízo contra piso.
3. Envelope sem itens ≤ 40 tokens (`qwen2.5.json`), em teste que falha o build.
4. Consulta a N fontes devolve N linhas: `linhas[]`, uma por fonte alcançada, nunca
   some. Fonte que não respondeu fica com `fonte-nao-indexada` + `causa`.
5. `sujeito` não entra no envelope — vai à trilha de auditoria (§11).

**Decisão de contrato tomada aqui, e declarada** (dono do envelope: claudinho-IA). A
tabela do §3 lista `cobertura`, `sinal` e `aviso[]` no topo, e a invariante 4 exige uma
linha POR FONTE — que os três campos escalares não conseguem carregar quando há mais de
uma fonte. `linhas[]` é o campo por fonte; `cobertura`, `sinal` e `aviso[]` continuam no
JSON de saída exatamente como o §3 os descreve, porém DERIVADOS das linhas, nunca
redigidos em paralelo. Duas verdades sobre o mesmo fato é o defeito que isto evita.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum

from .fontes import CLASSE, PREFIXO_CHAVE, Classe, Fonte


class ContratoViolado(ValueError):
    """Violação de invariante do §3. Levanta — não degrada, não avisa, não continua.

    O adaptador que produz item inválido tem defeito; envelope que o aceitasse
    entregaria procedência quebrada com cara de boa, que é o dano que o gate do §10
    existe para impedir.
    """


# --------------------------------------------------------------- vocabulário fechado
# Fechado e conferível por máquina (§3). `conferir verbo` reprova valor fora do enum.


class Cobertura(StrEnum):
    """Os seis do §3. A consequência de cada um está escrita em `arq:0064` §2 — rótulo
    sem consequência é decoração pelo critério da própria ADR."""

    COBERTA = "coberta"
    FRACA = "fraca"
    AUSENTE = "ausente"
    NAO_CALIBRADA = "nao-calibrada"
    FONTE_NAO_INDEXADA = "fonte-nao-indexada"
    VAZIA = "vazia"


class Casamento(StrEnum):
    """Como o hit casou com o alvo. Omitido em consulta exata (§3)."""

    EXATO = "exato"
    FLEXIONADO = "flexionado"
    ALTERNATIVO_DE_CHAPEU = "alternativo-de-chapeu"
    APROXIMADO = "aproximado"


class Causa(StrEnum):
    """`aviso.causa` — por que a fonte não entregou."""

    SEM_ROTA = "sem-rota"
    FORA_DO_AR = "fora-do-ar"
    SEM_INDICE = "sem-indice"
    TIMEOUT = "timeout"
    DISJUNTOR_ABERTO = "disjuntor-aberto"
    SEM_CONCESSAO = "sem-concessao"


class VersaoTipo(StrEnum):
    """`procedencia.versao.tipo` — o que carimba a versão do que foi lido."""

    SHA = "sha"
    REVID = "revid"
    SEQ = "seq"
    STREAM_ID = "stream-id"
    DIGEST = "digest"


# ------------------------------------------------------------------------ procedência


@dataclass(frozen=True, slots=True)
class Versao:
    tipo: VersaoTipo
    valor: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "tipo", VersaoTipo(self.tipo))
        except ValueError as e:
            raise ContratoViolado(f"versao.tipo fora do enum: {self.tipo!r}") from e
        if not str(self.valor).strip():
            raise ContratoViolado("versao.valor vazio: carimbo ausente não é carimbo")
        object.__setattr__(self, "valor", str(self.valor))

    def para_json(self) -> dict:
        return {"tipo": str(self.tipo), "valor": self.valor}


@dataclass(frozen=True, slots=True)
class Procedencia:
    """`{fonte, chave, versao, digest?}` — obrigatória, sem exceção (§3, inv. 1).

    A chave é ESTRUTURAL (§4): `curto-v1` é projeção de exibição e nenhuma chave
    gravada em artefato o carrega.
    """

    fonte: Fonte
    chave: str
    versao: Versao
    digest: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "fonte", Fonte(self.fonte))
        except ValueError as e:
            raise ContratoViolado(f"fonte fora do catálogo: {self.fonte!r}") from e
        chave = str(self.chave).strip()
        if not chave:
            raise ContratoViolado("procedencia.chave vazia")
        aceitos = PREFIXO_CHAVE[self.fonte]
        if not chave.startswith(aceitos):
            raise ContratoViolado(
                f"chave {chave!r} não tem prefixo de `{self.fonte}` "
                f"(aceitos: {', '.join(aceitos)})"
            )
        object.__setattr__(self, "chave", chave)
        if not isinstance(self.versao, Versao):
            raise ContratoViolado("procedencia.versao tem de ser Versao")

    def para_json(self) -> dict:
        d = {"fonte": str(self.fonte), "chave": self.chave, "versao": self.versao.para_json()}
        if self.digest:
            d["digest"] = self.digest
        return d


@dataclass(frozen=True, slots=True)
class Expansao:
    """`{conceito_origem, aresta, familia}` — presente quando o hit veio de salto."""

    conceito_origem: str
    aresta: str
    familia: str

    def para_json(self) -> dict:
        return {
            "conceito_origem": self.conceito_origem,
            "aresta": self.aresta,
            "familia": self.familia,
        }


@dataclass(frozen=True, slots=True)
class Sinal:
    """`{medida, valor, piso}` — a RÉGUA viaja no envelope porque duas chamadas na mesma
    sessão podem sair com réguas distintas (`arq:0064` §1)."""

    medida: str
    valor: float
    piso: float

    def __post_init__(self) -> None:
        if not str(self.medida).strip():
            raise ContratoViolado("sinal sem `medida`: número sem régua não é sinal")
        object.__setattr__(self, "valor", float(self.valor))
        object.__setattr__(self, "piso", float(self.piso))

    def para_json(self) -> dict:
        return {"medida": self.medida, "valor": self.valor, "piso": self.piso}


# ------------------------------------------------------------------------------ item


@dataclass(frozen=True, slots=True)
class Item:
    procedencia: Procedencia
    conteudo: str | None = None
    ref: str | None = None
    casamento: Casamento | None = None
    expansao: Expansao | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.procedencia, Procedencia):
            raise ContratoViolado("item sem procedencia completa não entra no envelope")
        tem_conteudo = self.conteudo is not None
        tem_ref = self.ref is not None
        if tem_conteudo and tem_ref:
            raise ContratoViolado("item traz `conteudo` OU `ref`; nunca os dois")
        if not tem_conteudo and not tem_ref:
            raise ContratoViolado("item sem `conteudo` e sem `ref`")
        if self.casamento is not None:
            object.__setattr__(self, "casamento", Casamento(self.casamento))

    @property
    def fonte(self) -> Fonte:
        return self.procedencia.fonte

    def para_json(self) -> dict:
        d: dict = {"procedencia": self.procedencia.para_json()}
        if self.conteudo is not None:
            d["conteudo"] = self.conteudo
        else:
            d["ref"] = self.ref
        if self.casamento is not None:
            d["casamento"] = str(self.casamento)
        if self.expansao is not None:
            d["expansao"] = self.expansao.para_json()
        return d


# ------------------------------------------------------------- linha por fonte (inv. 4)

# Estados em que a fonte ENTREGOU juízo contra piso. Sem `sinal.medida`, fonte semântica
# não pode reivindicar nenhum dos dois — tem de dizer `nao-calibrada` (§3, inv. 2).
_JUIZO_CONTRA_PISO = (Cobertura.COBERTA, Cobertura.FRACA)


@dataclass(frozen=True, slots=True)
class LinhaFonte:
    """Uma linha por fonte alcançada. Fonte que não respondeu NÃO some da lista (§3,
    inv. 4) — é ela que declara o vão, e é ela que a auditoria do §11 grava."""

    fonte: Fonte
    cobertura: Cobertura
    sinal: Sinal | None = None
    carimbo: str | None = None
    causa: Causa | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fonte", Fonte(self.fonte))
        try:
            object.__setattr__(self, "cobertura", Cobertura(self.cobertura))
        except ValueError as e:
            raise ContratoViolado(f"cobertura fora do enum: {self.cobertura!r}") from e
        if self.causa is not None:
            object.__setattr__(self, "causa", Causa(self.causa))
        if self.sinal is not None and not isinstance(self.sinal, Sinal):
            raise ContratoViolado("sinal tem de ser Sinal (com `medida`)")
        semantica = CLASSE[self.fonte] is Classe.SEMANTICA
        if semantica and self.sinal is None and self.cobertura in _JUIZO_CONTRA_PISO:
            raise ContratoViolado(
                f"`{self.fonte}` é semântica e disse `{self.cobertura}` sem sinal: "
                "medida ausente ⇒ cobertura `nao-calibrada`"
            )
        if self.cobertura is Cobertura.FONTE_NAO_INDEXADA and self.causa is None:
            raise ContratoViolado(
                f"`{self.fonte}` veio `fonte-nao-indexada` sem causa: vão sem motivo "
                "é indistinguível de fonte que respondeu nada"
            )

    def para_json(self) -> dict:
        d: dict = {"fonte": str(self.fonte), "cobertura": str(self.cobertura)}
        if self.sinal is not None:
            d["sinal"] = self.sinal.para_json()
        if self.carimbo:
            d["carimbo"] = self.carimbo
        return d


def linha_disjuntor_aberto(fonte: Fonte) -> LinhaFonte:
    """§8 — disjuntor aberto responde em 0 ms, sem tocar a fonte."""
    return LinhaFonte(
        fonte=fonte,
        cobertura=Cobertura.FONTE_NAO_INDEXADA,
        causa=Causa.DISJUNTOR_ABERTO,
    )


# -------------------------------------------------------------------------- agregação

# Ordem de informação, para o caso de N fontes. Duas escadas, e a separação evita o
# defeito de rotular envelope COM item de `vazia` ou `ausente`:
#  (a) havendo item, manda a melhor cobertura entre as fontes que CONTRIBUÍRAM item;
#  (b) não havendo item, manda a mais informativa entre todas as linhas.
_COM_ITEM = (Cobertura.COBERTA, Cobertura.FRACA, Cobertura.NAO_CALIBRADA)
_SEM_ITEM = (
    Cobertura.AUSENTE,
    Cobertura.VAZIA,
    Cobertura.NAO_CALIBRADA,
    Cobertura.FONTE_NAO_INDEXADA,
)


def _melhor(coberturas, escada) -> Cobertura | None:
    for c in escada:
        if c in coberturas:
            return c
    return None


# --------------------------------------------------------------------------- envelope


@dataclass(slots=True)
class Envelope:
    """O retorno de `recuperar()`. Montado de N linhas, uma por fonte (§9)."""

    linhas: list[LinhaFonte]
    itens: list[Item] = field(default_factory=list)
    falta: str | None = None
    proximo: str | None = None
    codigo_exato: bool = False

    def __post_init__(self) -> None:
        if not self.linhas:
            raise ContratoViolado(
                "envelope sem linha de fonte: consulta a N fontes devolve N linhas"
            )
        vistas = [l.fonte for l in self.linhas]
        if len(set(vistas)) != len(vistas):
            raise ContratoViolado(f"fonte repetida em `linhas`: {vistas}")
        for item in self.itens:
            if not isinstance(item, Item):
                raise ContratoViolado("itens[] só aceita Item")
            if item.fonte not in vistas:
                raise ContratoViolado(
                    f"item da fonte `{item.fonte}`, que não tem linha no envelope"
                )
        sem_entrega = {
            l.fonte
            for l in self.linhas
            if l.cobertura in (Cobertura.VAZIA, Cobertura.AUSENTE, Cobertura.FONTE_NAO_INDEXADA)
        }
        for item in self.itens:
            if item.fonte in sem_entrega:
                raise ContratoViolado(
                    f"`{item.fonte}` declarou não-entrega e mesmo assim trouxe item"
                )

    # ---- derivados: o §3 no topo, sem segunda verdade -----------------------------

    @property
    def cobertura(self) -> Cobertura:
        com_item = {i.fonte for i in self.itens}
        if com_item:
            c = {l.cobertura for l in self.linhas if l.fonte in com_item}
            achado = _melhor(c, _COM_ITEM)
            if achado is not None:
                return achado
        return _melhor({l.cobertura for l in self.linhas}, _SEM_ITEM) or Cobertura.VAZIA

    @property
    def sinal(self) -> Sinal | None:
        """Só há sinal no topo quando UMA fonte o produziu. Com duas réguas distintas no
        mesmo envelope, o escalar mentiria — a régua fica nas linhas."""
        sinais = [l.sinal for l in self.linhas if l.sinal is not None]
        return sinais[0] if len(sinais) == 1 else None

    @property
    def aviso(self) -> list[dict]:
        return [
            {"fonte": str(l.fonte), "causa": str(l.causa)}
            for l in self.linhas
            if l.causa is not None
        ]

    # ---- serialização --------------------------------------------------------------

    def para_json(self) -> dict:
        """A forma do §3. `sujeito` não entra, aqui nem em lugar nenhum (inv. 5): ele vai
        à trilha de auditoria, uma linha por fonte."""
        d: dict = {"cobertura": str(self.cobertura), "codigo_exato": self.codigo_exato}
        if self.itens:
            d["itens"] = [i.para_json() for i in self.itens]
        if len(self.linhas) > 1:
            # Com UMA fonte, `linhas` seria a repetição do topo — e o topo já é a forma
            # exata do §3. `linhas` sai quando há o que a forma escalar não carrega.
            #
            # Fonte caída também não repete: `{fonte, fonte-nao-indexada, causa}` já está
            # inteiro em `aviso[]`, e repeti-la custou 209 tokens no envelope de seis
            # fontes caídas (medido 20/08, qwen2.5) — imposto por giro, que é o que a
            # invariante 3 existe para impedir. A união `linhas[].fonte ∪ aviso[].fonte`
            # continua sendo as N fontes consultadas, e isso é testado.
            linhas = [l for l in self.linhas if not self._so_aviso(l)]
            if linhas:
                d["linhas"] = [l.para_json() for l in linhas]
        elif self.linhas[0].carimbo:
            d["carimbo"] = self.linhas[0].carimbo
        sinal = self.sinal
        if sinal is not None:
            d["sinal"] = sinal.para_json()
        if self.falta:
            d["falta"] = self.falta
        if self.proximo:
            d["proximo"] = self.proximo
        aviso = self.aviso
        if aviso:
            d["aviso"] = aviso
        return d

    @staticmethod
    def _so_aviso(linha: LinhaFonte) -> bool:
        """A linha não acrescenta nada ao que `aviso[]` já diz."""
        return (
            linha.causa is not None
            and linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
            and linha.sinal is None
            and not linha.carimbo
        )

    def para_texto(self) -> str:
        """JSON compacto — é esta a forma medida contra o teto de 40 tokens (inv. 3)."""
        return json.dumps(self.para_json(), ensure_ascii=False, separators=(",", ":"))


CAMPOS_PROIBIDOS = ("sujeito",)
