"""Estágio do portão de acesso do escritor único, antes de qualquer resolução."""
from __future__ import annotations

import grp
import html
import json
import os
import pwd
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

from .caminho import separar_chave_componente
from .politica import PoliticaEscrita, eh_caminho_protegido, eh_superficie_vedada
from .tipos import (
    MORADAS_ESCRITA,
    REGIMES_ESCRITA,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
)

_PORTA_YAML_PADRAO = Path(__file__).resolve().parents[2] / "registro" / "porta.yaml"
_VISTA_ALCANCE_YAML_PADRAO = Path(__file__).resolve().parents[2] / "registro" / "vista-alcance.yaml"
_GRUPO_PADRAO = "platafirma-escrita"
_FORMAS_COMUM = frozenset({"gravar", "retirar", "restaurar"})
_FORMAS_GUARDADA = frozenset({"criar", "trocar", "retirar", "restaurar", "ensaiar"})

AutorizadorSujeito = Callable[[str, str, str, str], bool]
ProvedorRaio = Callable[[str], frozenset[tuple[str, str]]]
ClienteHttpRaio = Callable[[str, float], object]

_RASTREADOR_URL_PADRAO = "http://127.0.0.1:8120/api"
_PRAZO_RAIO_S = 2.0
_ESTADOS_COM_RAIO = frozenset({"em-execucao", "em-mitigacao"})
_RE_CARD_DA_BANCADA = re.compile(r"^(\d+)(?:-|$)")
_RE_DTS_DA_BANCADA = re.compile(r"^dt-((?:\d+)(?:-\d+)*)(?:-|$)")
_RE_ITEM_RAIO = re.compile(r"^\s*(?:-\s*)?`?(platafirma-[a-z0-9-]+)@([^\s·|`]+)")
_RE_ROTULO = re.compile(r"^\s*[A-ZÀ-Ý][^:@]{0,40}:")
_RE_HEADING_HTML = re.compile(r"<\s*h[1-6]\b[^>]*>(.*?)<\s*/h[1-6]\s*>", re.IGNORECASE | re.DOTALL)
_RE_HEADING_MD = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")
_RE_TAG_QUEBRA = re.compile(r"<\s*(?:br\s*/?|/?p|/?li|/?ul|/?ol|/?div|/?h[1-6])\b[^>]*>", re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_NOMES_SECAO_RAIO = ("raio de ataque", "raio emendado", "raio")
_SECOES_RAIO = ("raio de ataque:", "raio emendado:", "raio:")


@dataclass(frozen=True)
class CredencialPar:
    """Identidade de kernel extraída do par no soquete UNIX via SO_PEERCRED."""

    uid: int
    gid: int
    pid: int
    usuario: str = ""
    grupos: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SpecClasse:
    """Declaração de regime, morada e verbo dono de uma classe na vista de alcance."""

    classe: str
    regime: str
    morada: str
    verbo_dono: str
    documentos: tuple[str, ...] = ()
    formas_suportadas: frozenset[str] = frozenset()
    moldes: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.regime not in REGIMES_ESCRITA:
            raise ValueError(f"regime inválido: {self.regime!r}")
        if self.morada not in MORADAS_ESCRITA:
            raise ValueError(f"morada inválida: {self.morada!r}")

    def formas_do_regime(self) -> frozenset[str]:
        """Devolve o conjunto de formas válidas para o regime da classe."""
        return _FORMAS_COMUM if self.regime == "comum" else _FORMAS_GUARDADA

    def molde_para(self, documento: str) -> str | None:
        """Retorna o molde de caminho para o tipo de documento informado, se houver."""
        for doc, molde in self.moldes:
            if doc == documento:
                return molde
        return None


@dataclass(frozen=True)
class SpecVerbo:
    """Alcance de escrita de um verbo no espelho da vista de alcance."""

    verbo: str
    aceita_escrever: bool = False
    classes: frozenset[str] = frozenset()
    cadeiras_autorizadas: frozenset[str] | None = None


@dataclass(frozen=True)
class VistaAlcance:
    """Espelho local da vista de alcance usada pelo portão e pela resolução."""

    verbos: Mapping[str, SpecVerbo]
    classes: Mapping[str, SpecClasse]

    def verbo_dono(self, classe: str) -> str:
        """Retorna o verbo dono da classe ou string vazia se desconhecida."""
        spec = self.classes.get(classe)
        return spec.verbo_dono if spec is not None else ""


@dataclass(frozen=True)
class ContextoAutorizacao:
    """Parâmetros de política e acesso aplicados pelo portão antes da resolução."""

    politica: PoliticaEscrita
    vista: VistaAlcance
    grupo_autorizado: str = _GRUPO_PADRAO
    uid_escritor: int | None = None
    raio_card: frozenset[tuple[str, str]] | None = None
    autorizador_sujeito: AutorizadorSujeito | None = None
    provedor_raio: ProvedorRaio | None = None


@dataclass(frozen=True)
class DecisaoPortao:
    """Resultado imutável de autorização entregue ao estágio de resolução."""

    verbo: str
    classe: str
    forma: str
    regime: str
    morada: str
    sujeito: str
    cadeira: str
    conta_par: str
    uid_par: int
    gid_par: int
    pid_par: int
    detalhes: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def credencial_de_uid(uid: int, gid: int, pid: int) -> CredencialPar:
    """Resolve nome de usuário e grupos do sistema para um par (uid, gid, pid)."""
    grupos: set[str] = set()
    try:
        pw = pwd.getpwuid(uid)
        usuario = pw.pw_name
    except KeyError:
        usuario = f"uid:{uid}"
    try:
        grupos.add(grp.getgrgid(gid).gr_name)
    except KeyError:
        pass
    if not usuario.startswith("uid:"):
        for gr in grp.getgrall():
            if usuario in gr.gr_mem:
                grupos.add(gr.gr_name)
    return CredencialPar(
        uid=uid,
        gid=gid,
        pid=pid,
        usuario=usuario,
        grupos=frozenset(grupos),
    )


def _erro_vista_alcance(onde: str, recebido: str, cura: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="politica-indisponivel",
            onde=onde,
            recebido=recebido,
            regra="registro/vista-alcance.yaml deve existir e declarar o espelho válido da vista de alcance",
            cura=cura,
            proximo="",
        )
    )


def _lista_slugs_vista(valor: object, onde: str, *, permitir_vazia: bool = False) -> tuple[str, ...]:
    if not isinstance(valor, list) or not all(isinstance(item, str) and item.strip() for item in valor):
        raise _erro_vista_alcance(onde, repr(valor), f"declare lista de nomes não vazios em {onde}")
    if not permitir_vazia and not valor:
        raise _erro_vista_alcance(onde, "[]", f"declare ao menos um item em {onde}")
    return tuple(item.strip() for item in valor)


def _ler_espelho_vista_alcance(caminho_vista_yaml: Path | None) -> dict[str, object]:
    alvo = _VISTA_ALCANCE_YAML_PADRAO if caminho_vista_yaml is None else Path(caminho_vista_yaml)
    try:
        bruto = alvo.read_text(encoding="utf-8")
    except OSError as exc:
        raise _erro_vista_alcance(
            str(alvo), str(exc), "confira o arquivo registro/vista-alcance.yaml na release"
        ) from exc
    try:
        dados = yaml.safe_load(bruto)
    except yaml.YAMLError as exc:
        raise _erro_vista_alcance(
            str(alvo), str(exc), "corrija a sintaxe YAML de registro/vista-alcance.yaml"
        ) from exc
    if not isinstance(dados, dict):
        raise _erro_vista_alcance(
            str(alvo), type(dados).__name__, "o topo de registro/vista-alcance.yaml deve ser um objeto"
        )
    versao = dados.get("versao")
    if isinstance(versao, bool) or not isinstance(versao, int) or versao <= 0:
        raise _erro_vista_alcance("vista-alcance.versao", repr(versao), "declare versao inteira positiva")
    return dados


def _carregar_specs_casa(
    casa: dict[str, object],
) -> tuple[dict[str, SpecClasse], dict[str, SpecVerbo]]:
    verbo_dono = str(casa.get("verbo_dono") or "").strip()
    regime_casa = str(casa.get("regime") or "").strip()
    morada_casa = str(casa.get("morada") or "").strip()
    if not verbo_dono or regime_casa not in REGIMES_ESCRITA or morada_casa not in MORADAS_ESCRITA:
        raise _erro_vista_alcance(
            "vista-alcance.casa",
            repr({"verbo_dono": verbo_dono, "regime": regime_casa, "morada": morada_casa}),
            "declare verbo_dono, regime e morada válidos em casa",
        )
    variantes = _lista_slugs_vista(casa.get("variantes", []), "casa.variantes", permitir_vazia=True)
    formas_casa = frozenset(_lista_slugs_vista(casa.get("formas_suportadas"), "casa.formas_suportadas"))
    capacidades = casa.get("capacidades")
    if not isinstance(capacidades, dict) or not capacidades:
        raise _erro_vista_alcance(
            "casa.capacidades", repr(capacidades), "declare o mapa de capacidades em casa.capacidades"
        )
    classes_casa: set[str] = set()
    for cap, lista in capacidades.items():
        classes_casa.update(_lista_slugs_vista(lista, f"casa.capacidades.{cap}"))
    classes_casa.update(
        _lista_slugs_vista(
            casa.get("classes_legadas_escrita", []),
            "casa.classes_legadas_escrita",
            permitir_vazia=True,
        )
    )
    classes = {
        cls: SpecClasse(
            classe=cls,
            regime=regime_casa,
            morada=morada_casa,
            verbo_dono=verbo_dono,
            formas_suportadas=formas_casa,
        )
        for cls in sorted(classes_casa)
    }
    alcance = frozenset(classes_casa)
    verbos_escrita = {
        nome: SpecVerbo(verbo=nome, aceita_escrever=True, classes=alcance)
        for nome in (verbo_dono, *variantes)
    }
    return classes, verbos_escrita


def _carregar_specs_outros_verbos(
    outros: dict[str, object],
    classes: dict[str, SpecClasse],
    verbos_escrita: dict[str, SpecVerbo],
) -> None:
    for nome_verbo, spec in outros.items():
        if not isinstance(spec, dict):
            raise _erro_vista_alcance(
                f"outros_verbos.{nome_verbo}", repr(spec), "declare um objeto por verbo em outros_verbos"
            )
        regime = str(spec.get("regime") or "").strip()
        morada = str(spec.get("morada") or "").strip()
        if regime not in REGIMES_ESCRITA or morada not in MORADAS_ESCRITA:
            raise _erro_vista_alcance(
                f"outros_verbos.{nome_verbo}",
                repr({"regime": regime, "morada": morada}),
                "declare regime e morada válidos",
            )
        formas = frozenset(
            _lista_slugs_vista(spec.get("formas_suportadas"), f"outros_verbos.{nome_verbo}.formas_suportadas")
        )
        cls_verbo = _lista_slugs_vista(spec.get("classes"), f"outros_verbos.{nome_verbo}.classes")
        for cls in cls_verbo:
            classes[cls] = SpecClasse(
                classe=cls,
                regime=regime,
                morada=morada,
                verbo_dono=str(nome_verbo),
                formas_suportadas=formas,
            )
        if bool(spec.get("aceita_escrever", False)):
            verbos_escrita[str(nome_verbo)] = SpecVerbo(
                verbo=str(nome_verbo),
                aceita_escrever=True,
                classes=frozenset(cls_verbo),
            )


def _carregar_specs_da_vista(
    caminho_vista_yaml: Path | None,
) -> tuple[dict[str, SpecClasse], dict[str, SpecVerbo]]:
    dados = _ler_espelho_vista_alcance(caminho_vista_yaml)
    casa = dados.get("casa")
    outros = dados.get("outros_verbos")
    if not isinstance(casa, dict) or not isinstance(outros, dict):
        raise _erro_vista_alcance(
            "vista-alcance", "chaves ausentes", "declare as seções casa e outros_verbos"
        )
    classes, verbos_escrita = _carregar_specs_casa(casa)
    _carregar_specs_outros_verbos(outros, classes, verbos_escrita)
    return classes, verbos_escrita


def _nomes_verbos_porta(caminho_porta_yaml: Path | None) -> list[str]:
    alvo = _PORTA_YAML_PADRAO if caminho_porta_yaml is None else Path(caminho_porta_yaml)
    if not alvo.is_file():
        return []
    dados = yaml.safe_load(alvo.read_text(encoding="utf-8"))
    if not isinstance(dados, dict) or not isinstance(dados.get("verbos"), dict):
        return []
    return [str(nome) for nome in dados["verbos"]]


def carregar_vista_alcance(
    caminho_porta_yaml: Path | None = None,
    *,
    caminho_vista_yaml: Path | None = None,
) -> VistaAlcance:
    """Monta a vista de alcance a partir do espelho estático da release e da porta."""
    classes, verbos_escrita = _carregar_specs_da_vista(caminho_vista_yaml)
    verbos: dict[str, SpecVerbo] = {
        nome: SpecVerbo(verbo=nome, aceita_escrever=False)
        for nome in _nomes_verbos_porta(caminho_porta_yaml)
    }
    verbos.update(verbos_escrita)
    return VistaAlcance(verbos=verbos, classes=classes)


def _erro_acesso(onde: str, recebido: str, regra: str, cura: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=4,
            codigo="acesso-negado",
            onde=onde,
            recebido=recebido,
            regra=regra,
            cura=cura,
            proximo="",
        )
    )


def _verificar_credencial_par(
    credencial: CredencialPar, auth: ContextoAutorizacao
) -> str:
    conta = credencial.usuario or f"uid:{credencial.uid}"
    if auth.uid_escritor is not None and credencial.uid == auth.uid_escritor:
        return conta
    if auth.grupo_autorizado in credencial.grupos:
        return conta
    raise _erro_acesso(
        "soquete",
        conta,
        f"somente contas no grupo {auth.grupo_autorizado} podem chamar o escritor",
        "adicione a conta ao grupo autorizado ou use a porta da casa",
    )


def _verificar_identidade_e_acesso(
    pedido: PedidoEscrita, spec_verbo: SpecVerbo | None, auth: ContextoAutorizacao
) -> tuple[str, str]:
    sujeito = (pedido.contexto.sujeito or "").strip()
    cadeira = (pedido.contexto.cadeira or "").strip()
    if not sujeito or not cadeira:
        raise _erro_acesso(
            "contexto",
            f"sujeito={sujeito!r}, cadeira={cadeira!r}",
            "toda escrita exige sujeito e cadeira declarados",
            "informe sujeito e cadeira válidos no contexto da chamada",
        )
    if (
        spec_verbo is not None
        and spec_verbo.cadeiras_autorizadas is not None
        and cadeira not in spec_verbo.cadeiras_autorizadas
    ):
        raise _erro_acesso(
            "cadeira",
            f"{cadeira} -> {pedido.verbo}",
            f"a cadeira {cadeira} não tem acesso ao verbo {pedido.verbo}",
            "peça a concessão de acesso ou encaminhe à cadeira dona",
        )
    if auth.autorizador_sujeito is not None and not auth.autorizador_sujeito(
        sujeito, cadeira, pedido.verbo, pedido.forma
    ):
        raise _erro_acesso(
            "acesso",
            f"{sujeito}/{cadeira} -> {pedido.verbo}:{pedido.forma}",
            "política de acesso negou a operação para este sujeito",
            "verifique as concessões da cadeira ou do sujeito",
        )
    return sujeito, cadeira


def _classe_inferida(pedido: PedidoEscrita, spec_verbo: SpecVerbo | None) -> str:
    if pedido.classe:
        return pedido.classe
    if ":" in pedido.chave:
        pref = pedido.chave.split(":", 1)[0]
        if pref == "segredo":
            return "segredo"
    if spec_verbo is not None and len(spec_verbo.classes) == 1:
        return next(iter(spec_verbo.classes))
    if ":" in pedido.chave:
        return pedido.chave.split(":", 1)[0]
    return "shape"


def _verificar_nao_segredo(pedido: PedidoEscrita, classe: str) -> None:
    if classe == "segredo" or pedido.chave.startswith("segredo:"):
        raise RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="segredo-recusado",
                onde="classe",
                recebido=pedido.chave or classe,
                regra="o escritor geral recusa a classe segredo",
                cura="use o verbo seg para gravar ou rotacionar segredos",
                proximo="",
            )
        )


def _verificar_verbo_e_classe(
    pedido: PedidoEscrita,
    spec_verbo: SpecVerbo | None,
    classe: str,
    vista: VistaAlcance,
) -> SpecClasse:
    dono = vista.verbo_dono(classe)
    if spec_verbo is None or not spec_verbo.aceita_escrever:
        proximo = f"{dono} {pedido.forma} {classe} {pedido.chave}".strip() if dono else ""
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="ato-nao-aceito",
                onde="verbo",
                recebido=pedido.verbo,
                regra=f"o verbo {pedido.verbo} não aceita o ato escrever",
                cura="chame o verbo dono da classe que aceita escrever",
                proximo=proximo,
            )
        )
    if classe not in spec_verbo.classes:
        proximo = f"{dono} {pedido.forma} {classe} {pedido.chave}".strip() if dono else ""
        raise RecusaEscrita(
            ErroEscrita(
                saida=1,
                codigo="classe-fora-do-verbo",
                onde="classe",
                recebido=f"{pedido.verbo} -> {classe}",
                regra=f"o verbo {pedido.verbo} não alcança a classe {classe}",
                cura=f"use o verbo {dono}" if dono else "consulte o verbo dono da classe",
                proximo=proximo,
            )
        )
    spec_classe = vista.classes.get(classe)
    if spec_classe is None:
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="politica-indisponivel",
                onde="classe",
                recebido=classe,
                regra="classe alcançada pelo verbo não está declarada na vista de alcance",
                cura="confira o espelho da vista de alcance da release",
                proximo="",
            )
        )
    return spec_classe


def _verificar_forma_e_regime(pedido: PedidoEscrita, spec: SpecClasse) -> None:
    if pedido.forma not in spec.formas_do_regime():
        sugestao = "gravar" if spec.regime == "comum" else "criar"
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="forma-fora-do-regime",
                onde="forma",
                recebido=f"{pedido.forma} ({spec.classe}: {spec.regime})",
                regra=f"classe {spec.classe} tem regime {spec.regime} e não aceita {pedido.forma}",
                cura=f"use a forma {sugestao} para a classe {spec.classe}",
                proximo=f"{pedido.verbo} {sugestao} {spec.classe} {pedido.chave}",
            )
        )
    if spec.formas_suportadas and pedido.forma not in spec.formas_suportadas:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="forma-sem-morada",
                onde="forma",
                recebido=f"{pedido.forma} ({spec.classe})",
                regra=f"a forma {pedido.forma} ainda não tem morada ativa nesta entrega",
                cura="use uma forma com morada ativa nesta entrega",
                proximo="",
            )
        )


def _texto_do_corpo(corpo_html: str) -> list[str]:
    """O corpo do card (HTML do rastreador) em linhas de texto, uma por parágrafo, item ou quebra."""
    com_headings = _RE_HEADING_HTML.sub(lambda m: f"\n## {m.group(1)}\n", corpo_html)
    texto = _RE_TAG.sub("", _RE_TAG_QUEBRA.sub("\n", com_headings))
    return [html.unescape(linha) for linha in texto.splitlines()]


def extrair_raio_do_corpo(corpo_html: str) -> frozenset[tuple[str, str]]:
    """Os pares (repo, caminho) do Raio de ataque e do Raio emendado do corpo do card.

    Só essas seções contam: o Referencial também cita `repo@caminho`, e o que ele cita é
    leitura, não licença de gravar. Um heading novo (`## Referencial`, `<h2>Referencial</h2>`)
    ou rótulo novo (`Comportamento esperado:`, `Riscos:`) fecha a seção.
    """
    pares: set[tuple[str, str]] = set()
    dentro = False
    for linha in _texto_do_corpo(corpo_html):
        limpa = linha.strip()
        m_heading = _RE_HEADING_MD.match(limpa)
        if m_heading is not None:
            titulo = m_heading.group(1).strip().rstrip(":").strip().lower()
            dentro = titulo in _NOMES_SECAO_RAIO
            continue
        baixa = limpa.lower()
        rotulo = next((s for s in _SECOES_RAIO if baixa.startswith(s)), None)
        if rotulo is not None:
            dentro = True
            linha = limpa[len(rotulo):]
        elif baixa in _NOMES_SECAO_RAIO:
            dentro = True
            continue
        elif _RE_ROTULO.match(linha):
            dentro = False
        achado = _RE_ITEM_RAIO.match(linha) if dentro else None
        if achado is not None:
            pares.add((achado.group(1), achado.group(2)))
    return frozenset(pares)


def _get_json_rastreador(url: str, prazo_s: float) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=prazo_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _recusa_raio_ilegivel(bancada: str, motivo: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="morada-sem-resposta",
            onde="bancada",
            recebido=bancada,
            regra="caminho protegido exige ler o raio do card da bancada no rastreador",
            cura=f"o rastreador não devolveu o card: {motivo}",
            proximo="",
        )
    )


def _extrair_raio_do_balde(raio: object) -> frozenset[tuple[str, str]]:
    """Extrai pares (repo, caminho) da lista `raio` de uma linha do balde."""
    if isinstance(raio, str):
        itens: list[object] = [raio]
    elif isinstance(raio, list):
        itens = raio
    else:
        return frozenset()
    pares: set[tuple[str, str]] = set()
    for item in itens:
        if not isinstance(item, str):
            continue
        bruto = item.strip()
        if "@" not in bruto:
            continue
        repo, caminho = bruto.split("@", 1)
        repo = repo.strip()
        caminho = caminho.split(":", 1)[0].strip()
        if repo and caminho:
            pares.add((repo, caminho))
    return frozenset(pares)


def criar_provedor_raio(
    url_base: str | None = None,
    *,
    cliente_http: ClienteHttpRaio | None = None,
    prazo_s: float = _PRAZO_RAIO_S,
) -> ProvedorRaio:
    """O raio do card da bancada `<card>-<slug>` ou `<card>`, ou de DTs `dt-<n>`, lido do rastreador.

    Card fora de execução/mitigação ou DT já saído não têm raio aberto (frozenset vazio, saída 4
    no portão); rastreador que não responde sai 3, porque sem o raio não há como decidir e o portão
    não supõe.
    """
    base = (url_base or os.environ.get("PF_RASTREADOR_URL") or _RASTREADOR_URL_PADRAO).rstrip("/")
    http = cliente_http or _get_json_rastreador

    def _raio_dts(numeros: list[str], bancada: str) -> frozenset[tuple[str, str]]:
        pares: set[tuple[str, str]] = set()
        for num in numeros:
            try:
                linha = http(f"{base}/balde/{num}", prazo_s)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    continue
                raise _recusa_raio_ilegivel(bancada, str(exc)) from None
            except (OSError, ValueError, urllib.error.URLError) as exc:
                raise _recusa_raio_ilegivel(bancada, str(exc)) from None
            if not isinstance(linha, Mapping) or linha.get("saida_jeito") is not None:
                continue
            pares.update(_extrair_raio_do_balde(linha.get("raio")))
        return frozenset(pares)

    def _raio(bancada: str) -> frozenset[tuple[str, str]]:
        achado_dt = _RE_DTS_DA_BANCADA.match(bancada)
        if achado_dt is not None:
            return _raio_dts(achado_dt.group(1).split("-"), bancada)
        achado = _RE_CARD_DA_BANCADA.match(bancada)
        if achado is None:
            return frozenset()
        try:
            item = http(f"{base}/itens/{achado.group(1)}", prazo_s)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return frozenset()
            raise _recusa_raio_ilegivel(bancada, str(exc)) from None
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise _recusa_raio_ilegivel(bancada, str(exc)) from None
        if not isinstance(item, Mapping) or item.get("estado") not in _ESTADOS_COM_RAIO:
            return frozenset()
        return extrair_raio_do_corpo(str(item.get("descricao") or ""))

    return _raio


def _raio_da_bancada(
    auth: ContextoAutorizacao, bancada: str | None
) -> frozenset[tuple[str, str]] | None:
    if auth.raio_card is not None:
        return auth.raio_card
    if auth.provedor_raio is None or not bancada:
        return None
    return auth.provedor_raio(bancada)


def _caminho_no_raio(
    repo: str, rel: str, raio_card: frozenset[tuple[str, str]] | None
) -> bool:
    if not raio_card:
        return False
    for r_repo, r_caminho in raio_card:
        if r_repo != repo:
            continue
        if r_caminho.endswith("/"):
            base = r_caminho.rstrip("/")
            if rel == base or rel.startswith(base + "/"):
                return True
        elif rel == r_caminho:
            return True
    return False


def _verificar_protecoes_alvo(
    pedido: PedidoEscrita, spec: SpecClasse, auth: ContextoAutorizacao
) -> None:
    if pedido.permitir_vazio and spec.classe != "componente":
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conflito-de-opcoes",
                onde="--permitir-vazio",
                recebido=spec.classe,
                regra="--permitir-vazio vale apenas para arquivo de componente na bancada",
                cura="remova --permitir-vazio",
                proximo="",
            )
        )
    if spec.classe != "componente":
        if eh_superficie_vedada(auth.politica, pedido.chave):
            raise RecusaEscrita(
                ErroEscrita(
                    saida=4,
                    codigo="superficie-vedada",
                    onde="chave",
                    recebido=pedido.chave,
                    regra="superfície vedada não aceita escrita pelo escritor geral",
                    cura="não altere superfícies vedadas pela porta",
                    proximo="",
                )
            )
        return
    repo, bancada, rel = separar_chave_componente(pedido.chave)
    if eh_superficie_vedada(auth.politica, rel) or eh_superficie_vedada(
        auth.politica, f"{repo}/{rel}"
    ):
        raise RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="superficie-vedada",
                onde="chave",
                recebido=pedido.chave,
                regra="caminho cai em superfície vedada e não aceita gravação",
                cura="não altere segredos, política, trilha, fila, release ou .git",
                proximo="",
            )
        )
    if eh_caminho_protegido(auth.politica, repo, rel) and not _caminho_no_raio(
        repo, rel, _raio_da_bancada(auth, bancada)
    ):
        raise RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="superficie-vedada",
                onde="chave",
                recebido=pedido.chave,
                regra="caminho protegido só aceita gravação dentro do raio do card da bancada",
                cura="inclua o caminho no raio do card aprovado pelo dono",
                proximo="",
            )
        )


_VARIANTES_CLASSE_OLARIA: dict[str, str] = {
    "classes": "shape",
    "shapes": "shape",
    "dicionarios": "dicionario",
    "ligacao": "tipo-de-ligacao",
    "ligacoes": "tipo-de-ligacao",
    "tipos-de-ligacao": "tipo-de-ligacao",
    "tipos_de_ligacao": "tipo-de-ligacao",
    "axiomas": "axioma",
    "tipos-de-evento": "tipo-de-evento",
    "tipos_de_evento": "tipo-de-evento",
}
_CHAVES_ENVELOPE_OLARIA = frozenset(
    {"classe", "classes", "shapes", "dicionarios", "tipos_de_ligacao", "axiomas", "tipos_de_evento", "fichas"}
)


def _normalizar_classe_olaria(classe: str) -> str:
    limpa = classe.strip()
    return _VARIANTES_CLASSE_OLARIA.get(limpa, limpa)


def _extrair_alvo_ficha(item: Mapping[str, object], classe_padrao: str | None) -> tuple[str, str]:
    chave = str(item.get("chave") or "").strip()
    classe_raw = str(item.get("classe") or "").strip()
    if classe_raw:
        classe = _normalizar_classe_olaria(classe_raw)
    elif ":" in chave:
        classe = _normalizar_classe_olaria(chave.split(":", 1)[0])
    elif classe_padrao:
        classe = _normalizar_classe_olaria(classe_padrao)
    else:
        classe = "ficha"
    return classe, (chave or f"{classe}:lote")


_SECOES_CATALOGO_OLARIA: tuple[tuple[str, str], ...] = (
    ("classes", "shape"),
    ("shapes", "shape"),
    ("dicionarios", "dicionario"),
    ("tipos_de_ligacao", "casa"),
    ("axiomas", "casa"),
    ("tipos_de_evento", "casa"),
)


def _alvos_de_secoes_catalogo(doc: Mapping[str, object]) -> list[tuple[str, str]]:
    alvos: list[tuple[str, str]] = []
    classe_unica = doc.get("classe")
    if isinstance(classe_unica, Mapping):
        slug = str(classe_unica.get("slug") or "").strip()
        alvos.append(("shape", f"shape:{slug}" if slug else "shape:lote"))
    for chave_lista, classe_cat in _SECOES_CATALOGO_OLARIA:
        itens = doc.get(chave_lista)
        if not isinstance(itens, list):
            continue
        for item in itens:
            if isinstance(item, Mapping):
                slug = str(item.get("slug") or item.get("classe") or "").strip()
                alvos.append((classe_cat, f"{classe_cat}:{slug}" if slug else f"{classe_cat}:lote"))
    return alvos


def _alvos_de_documento_olaria(
    doc: Mapping[str, object], classe_padrao: str | None
) -> list[tuple[str, str]]:
    alvos: list[tuple[str, str]] = []
    fichas = doc.get("fichas")
    if isinstance(fichas, list):
        alvos.extend(
            _extrair_alvo_ficha(item, classe_padrao)
            for item in fichas
            if isinstance(item, Mapping)
        )
    alvos.extend(_alvos_de_secoes_catalogo(doc))
    tem_envelope = any(k in doc for k in _CHAVES_ENVELOPE_OLARIA)
    if not tem_envelope and ("chave" in doc or "classe" in doc):
        alvos.append(_extrair_alvo_ficha(doc, classe_padrao))
    return alvos


def extrair_alvos_yaml_olaria(
    texto: str, *, classe_padrao: str | None = None
) -> list[tuple[str, str]]:
    """Extrai todos os pares (classe, chave) de um documento ou stream YAML da Olaria."""
    try:
        docs = list(yaml.safe_load_all(texto))
    except yaml.YAMLError as exc:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="yaml",
                recebido=str(exc),
                regra="o lote enviado ao escritor deve ser YAML válido",
                cura="corrija a sintaxe YAML da entrada e repita a chamada",
                proximo="",
            )
        ) from exc
    alvos: list[tuple[str, str]] = []
    for doc in docs:
        if isinstance(doc, Mapping):
            alvos.extend(_alvos_de_documento_olaria(doc, classe_padrao))
    return alvos


def _verbo_eh_morada_banco(spec_verbo: SpecVerbo | None, vista: VistaAlcance) -> bool:
    if spec_verbo is None or not spec_verbo.classes:
        return False
    return all(
        (spec := vista.classes.get(cls)) is not None and spec.morada == "banco"
        for cls in spec_verbo.classes
    )


def _verificar_itens_lote_olaria(
    pedido: PedidoEscrita,
    spec_verbo: SpecVerbo | None,
    auth: ContextoAutorizacao,
) -> None:
    if not pedido.conteudo or not _verbo_eh_morada_banco(spec_verbo, auth.vista):
        return
    alvos = extrair_alvos_yaml_olaria(pedido.conteudo, classe_padrao=pedido.classe)
    if not alvos:
        return
    erros_segredo: list[ErroEscrita] = []
    erros_outros: list[ErroEscrita] = []
    for classe_item, chave_item in alvos:
        ped_item = replace(pedido, classe=classe_item, chave=chave_item)
        try:
            _verificar_nao_segredo(ped_item, classe_item)
        except RecusaEscrita as exc:
            erros_segredo.extend(exc.erros)
            continue
        try:
            spec_item = _verificar_verbo_e_classe(ped_item, spec_verbo, classe_item, auth.vista)
            _verificar_forma_e_regime(ped_item, spec_item)
            _verificar_protecoes_alvo(ped_item, spec_item, auth)
        except RecusaEscrita as exc:
            erros_outros.extend(exc.erros)
    if erros_segredo or erros_outros:
        raise RecusaEscrita([*erros_segredo, *erros_outros])


def decidir_portao(
    pedido: PedidoEscrita,
    credencial: CredencialPar,
    auth: ContextoAutorizacao,
) -> DecisaoPortao:
    """Único ponto de decisão de acesso do escritor, antes de qualquer resolução."""
    conta_par = _verificar_credencial_par(credencial, auth)
    spec_verbo = auth.vista.verbos.get(pedido.verbo)
    sujeito, cadeira = _verificar_identidade_e_acesso(pedido, spec_verbo, auth)
    classe = _classe_inferida(pedido, spec_verbo)
    _verificar_nao_segredo(pedido, classe)
    _verificar_itens_lote_olaria(pedido, spec_verbo, auth)
    spec_classe = _verificar_verbo_e_classe(pedido, spec_verbo, classe, auth.vista)
    _verificar_forma_e_regime(pedido, spec_classe)
    _verificar_protecoes_alvo(pedido, spec_classe, auth)
    return DecisaoPortao(
        verbo=pedido.verbo,
        classe=spec_classe.classe,
        forma=pedido.forma,
        regime=spec_classe.regime,
        morada=spec_classe.morada,
        sujeito=sujeito,
        cadeira=cadeira,
        conta_par=conta_par,
        uid_par=credencial.uid,
        gid_par=credencial.gid,
        pid_par=credencial.pid,
    )
