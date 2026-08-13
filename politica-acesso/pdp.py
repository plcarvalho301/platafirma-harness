"""PDP — ponto de decisão de acesso da PlataFirma.

Biblioteca embarcada (`seg:0008`): roda dentro do processo do serviço, sem rede e sem
estado. Entra um pedido, sai uma decisão. Não fala com banco, não emite token, não
executa nada — quem obedece é o PEP, que é o próprio serviço.

Contrato completo, com a régua de atributo ausente:
  wiki PlataFirma:Sec/contrato-de-politica-de-acesso

Regime de avaliação, nesta ordem (a ordem é normativa, não conveniência):
  1. completude   — atributo obrigatório ausente NEGA, e a decisão diz qual faltou
  2. teto         — sigilo do recurso acima da habilitação do sujeito NEGA
  3. veto         — veto vigente sobre o domínio do recurso NEGA
  4. interseção   — domínio E papel E tema do sujeito têm de alcançar o recurso
  5. matriz       — alguma regra tem de permitir a ação sobre aquele recurso
  6. default      — negar

O que NÃO mora aqui, por decisão registrada:
  - exclusão mútua entre papéis: avaliada na EMISSÃO do token, não na decisão, porque
    só o emissor sabe quais emissões estão vivas (`formas/forma-da-exclusao-mutua`).
  - vigência da concessão: quem projeta o token já descontou revogado e vencido
    (view `concessao.vigente`). O PDP confia no token e não consulta o registro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml

# Graus da LAI, em ordem. O número é interno e serve só para comparar; o nome é o termo.
GRAUS = ("publico", "reservado", "secreto", "ultrassecreto")

# Valor reservado de ausência explícita no eixo de tema (mesmo valor do banco).
SEM_TEMA = "-"


class PoliticaInvalida(Exception):
    """Arquivo de política malformado. Falha no carregamento, nunca na decisão:
    política quebrada tem de derrubar o boot do serviço, não virar negativa silenciosa."""


@dataclass(frozen=True)
class Sujeito:
    """O que o token carrega. Nenhum campo é opcional por conveniência: ausência é
    tratada como falta de atributo, e falta de atributo nega."""

    id: str | None = None
    natureza: str | None = None           # pessoa | cadeira | servico
    papeis: tuple[str, ...] = ()
    dominios: tuple[str, ...] = ()
    temas: tuple[str, ...] = ()
    vetos: tuple[str, ...] = ()           # domínios vetados (eixo negativo)
    habilitacao: str = "publico"          # grau máximo que o sujeito pode ver


@dataclass(frozen=True)
class Recurso:
    """O que o serviço sabe do alvo. Só o serviço conhece isto — é a razão de o PDP
    morar nele (`seg:0003`)."""

    tipo: str                              # comando | documento | registro | ...
    id: str = "*"                          # identificador ou padrão glob do alvo
    dominio: str | None = None
    tema: str = SEM_TEMA
    sigilo: str = "publico"


@dataclass(frozen=True)
class Decisao:
    permitido: bool
    motivo: str
    regra: str | None = None               # id da regra que decidiu
    faltou: tuple[str, ...] = ()           # atributos ausentes que impediram decidir

    @property
    def por_atributo_ausente(self) -> bool:
        """Distinção que o serviço PRECISA logar separada: negativa por regra é a
        política funcionando; negativa por atributo ausente é defeito de projeção."""
        return bool(self.faltou)

    def como_dicionario(self) -> dict:
        return {
            "permitido": self.permitido,
            "motivo": self.motivo,
            "regra": self.regra,
            "faltou": list(self.faltou),
        }


class Politica:
    """O PAP carregado em memória. Imutável depois de construída."""

    def __init__(self, dados: dict):
        self.versao = dados.get("versao")
        if self.versao != 1:
            raise PoliticaInvalida(f"versao de politica nao suportada: {self.versao!r}")

        eixos = dados.get("eixos") or {}
        # Árvore do eixo de domínio: {valor: pai|None}. Só domínio tem hierarquia.
        self.dominios: dict[str, str | None] = {
            valor: (corpo or {}).get("pai")
            for valor, corpo in (eixos.get("dominio") or {}).items()
        }
        self.papeis: dict[str, dict] = dict(eixos.get("papel") or {})
        self.temas: dict[str, dict] = dict(eixos.get("tema") or {})

        for valor, pai in self.dominios.items():
            if pai is not None and pai not in self.dominios:
                raise PoliticaInvalida(f"dominio {valor!r} aponta para pai inexistente {pai!r}")

        self.regras: list[dict] = list(dados.get("regras") or [])
        vistos: set[str] = set()
        for regra in self.regras:
            ident = regra.get("id")
            if not ident:
                raise PoliticaInvalida("regra sem id")
            if ident in vistos:
                raise PoliticaInvalida(f"id de regra repetido: {ident!r}")
            vistos.add(ident)
            if regra.get("efeito") not in ("permite", "nega"):
                raise PoliticaInvalida(f"regra {ident!r}: efeito tem de ser permite ou nega")

    @classmethod
    def de_arquivo(cls, caminho: str | Path) -> "Politica":
        texto = Path(caminho).read_text(encoding="utf-8")
        return cls(yaml.safe_load(texto) or {})

    def linhagem(self, dominio: str) -> list[str]:
        """Do domínio até a raiz. Concessão no pai alcança o filho; o contrário não."""
        cadeia, atual, guarda = [], dominio, 0
        while atual is not None and guarda < 64:
            cadeia.append(atual)
            atual = self.dominios.get(atual)
            guarda += 1
        return cadeia


def _casa(padrao: str, valor: str) -> bool:
    """`*` casa qualquer coisa; o resto é glob. Padrão de comando é glob de propósito:
    a alternativa era regex, que ninguém revisa direito num merge request."""
    return padrao == "*" or fnmatch(valor, padrao)


def _alcanca_dominio(politica: Politica, concedidos: tuple[str, ...], alvo: str) -> bool:
    """O sujeito alcança o alvo se detém o próprio alvo ou qualquer ancestral dele."""
    linhagem = set(politica.linhagem(alvo))
    return any(d in linhagem for d in concedidos)


def _regra_casa(regra: dict, sujeito: Sujeito, acao: str, recurso: Recurso,
                politica: Politica) -> bool:
    quando = regra.get("quando") or {}

    papel = quando.get("papel")
    if papel is not None and papel not in sujeito.papeis:
        return False

    dominio = quando.get("dominio")
    # Direcao da heranca: regra escrita no PAI alcanca recurso no FILHO. O inverso nao —
    # regra sobre `plataforma-identidade` nao pode capturar recurso em `plataforma`.
    if dominio is not None and dominio not in set(politica.linhagem(recurso.dominio)):
        return False

    tipo = quando.get("tipo")
    if tipo is not None and tipo != recurso.tipo:
        return False

    acoes = regra.get("acoes") or ["*"]
    if not any(_casa(p, acao) for p in acoes):
        return False

    sobre = regra.get("sobre") or ["*"]
    return any(_casa(p, recurso.id) for p in sobre)


def decide(sujeito: Sujeito, acao: str, recurso: Recurso, politica: Politica) -> Decisao:
    """A única função que o serviço chama. Sempre devolve Decisao; nunca levanta."""

    # 1. Completude. Atributo ausente nega, e a decisão nomeia o que faltou — sem isso
    #    o operador não distingue "não pode" de "o token veio quebrado".
    faltou: list[str] = []
    if not sujeito.papeis:
        faltou.append("sujeito.papeis")
    if not sujeito.dominios:
        faltou.append("sujeito.dominios")
    if recurso.dominio is None:
        faltou.append("recurso.dominio")
    if recurso.sigilo not in GRAUS:
        faltou.append("recurso.sigilo")
    if sujeito.habilitacao not in GRAUS:
        faltou.append("sujeito.habilitacao")
    if faltou:
        return Decisao(False, "atributo obrigatorio ausente", faltou=tuple(faltou))

    if recurso.dominio not in politica.dominios:
        return Decisao(False, f"dominio {recurso.dominio!r} fora do vocabulario",
                       faltou=("recurso.dominio",))

    # 2. Teto de sigilo, antes da interseção: recurso classificado segue protegido ainda
    #    que os três eixos coincidam.
    if GRAUS.index(recurso.sigilo) > GRAUS.index(sujeito.habilitacao):
        return Decisao(False,
                       f"teto de sigilo: recurso {recurso.sigilo}, habilitacao {sujeito.habilitacao}",
                       regra="teto")

    # 3. Veto. Nega mesmo com concessão vigente, e vale para a linhagem inteira.
    if _alcanca_dominio(politica, sujeito.vetos, recurso.dominio):
        return Decisao(False, f"veto vigente sobre o dominio {recurso.dominio}", regra="veto")

    # 4. Interseção dos três eixos.
    if not _alcanca_dominio(politica, sujeito.dominios, recurso.dominio):
        return Decisao(False, f"sujeito nao alcanca o dominio {recurso.dominio}",
                       regra="intersecao")
    if recurso.tema != SEM_TEMA and recurso.tema not in sujeito.temas:
        return Decisao(False, f"sujeito sem designacao no tema {recurso.tema}",
                       regra="intersecao")

    # 5. Matriz. Negativa explícita vence permissão, independentemente da ordem no arquivo.
    for regra in politica.regras:
        if regra.get("efeito") == "nega" and _regra_casa(regra, sujeito, acao, recurso, politica):
            return Decisao(False, regra.get("motivo") or "negado por regra", regra=regra["id"])

    for regra in politica.regras:
        if regra.get("efeito") == "permite" and _regra_casa(regra, sujeito, acao, recurso, politica):
            return Decisao(True, regra.get("motivo") or "permitido por regra", regra=regra["id"])

    # 6. Default.
    return Decisao(False, "nenhuma regra permite esta acao sobre este recurso",
                   regra="default")
