"""Estágio de resolução de alvo e validação de pré-condições de versão, após o portão."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .caminho import (
    BancadaConfinada,
    resolver_bancada,
    separar_chave_componente,
    validar_caminho_relativo,
)
from .portao import DecisaoPortao, SpecClasse, VistaAlcance
from .tipos import AlvoEscrita, ErroEscrita, PedidoEscrita, RecusaEscrita

_TAM_VERSAO_CURTA_GIT = 12


@dataclass(frozen=True)
class EstadoAlvo:
    """Estado atual do alvo na morada para conferência de existência e versão."""

    existe: bool
    versao: str | None = None
    versao_completa: str | None = None


@dataclass(frozen=True)
class AlvoResolvido:
    """Alvo resolvido depois do portão, com bancada confinada quando git."""

    alvo: AlvoEscrita
    bancada: BancadaConfinada | None = None


def normalizar_chave_casa(chave: str) -> str:
    """Normaliza `<classe>` ou `<classe>:` para `shape:<classe>` em objetos da casa."""
    limpa = chave.strip()
    if ":" not in limpa:
        return f"shape:{limpa}"
    if limpa.endswith(":") and ":" not in limpa[:-1]:
        return f"shape:{limpa[:-1]}"
    return limpa


def _resolver_documento(pedido: PedidoEscrita, spec: SpecClasse) -> str | None:
    if not spec.documentos:
        if pedido.documento is not None:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="conflito-de-opcoes",
                    onde="--documento",
                    recebido=pedido.documento,
                    regra=f"a classe {spec.classe} não declara múltiplos documentos",
                    cura="remova a flag --documento",
                    proximo="",
                )
            )
        return None
    if pedido.documento is None:
        if len(spec.documentos) == 1:
            return spec.documentos[0]
        lista = ", ".join(spec.documentos)
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="documento-ambiguo",
                onde="--documento",
                recebido=spec.classe,
                regra=f"a classe {spec.classe} declara mais de um documento ({lista})",
                cura=f"informe --documento com uma das opções: {lista}",
                proximo=f"{pedido.verbo} {pedido.forma} {spec.classe} {pedido.chave} --documento {spec.documentos[0]}",
            )
        )
    if pedido.documento not in spec.documentos:
        lista = ", ".join(spec.documentos)
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="documento-ambiguo",
                onde="--documento",
                recebido=pedido.documento,
                regra=f"documento {pedido.documento} não existe na classe {spec.classe} ({lista})",
                cura=f"informe --documento com uma das opções: {lista}",
                proximo="",
            )
        )
    return pedido.documento


def _resolver_componente(
    pedido: PedidoEscrita,
    decisao: DecisaoPortao,
    raiz_bancadas: Path | None,
) -> AlvoResolvido:
    if raiz_bancadas is not None:
        bancada = resolver_bancada(pedido.chave, decisao.cadeira, raiz_bancadas)
        endereco = f"wt/{bancada.repo}/{bancada.cadeira}/{bancada.chave_bancada}/{bancada.caminho_relativo}"
        alvo = AlvoEscrita(
            classe=decisao.classe,
            chave=pedido.chave,
            regime=decisao.regime,
            morada="git",
            endereco=endereco,
            documento=pedido.documento,
            repo=bancada.repo,
            caminho_relativo=bancada.caminho_relativo,
        )
        return AlvoResolvido(alvo=alvo, bancada=bancada)
    repo, _, rel = separar_chave_componente(pedido.chave)
    componentes = validar_caminho_relativo(rel)
    caminho_rel = "/".join(componentes)
    alvo = AlvoEscrita(
        classe=decisao.classe,
        chave=pedido.chave,
        regime=decisao.regime,
        morada="git",
        endereco=f"{repo}:{caminho_rel}",
        documento=pedido.documento,
        repo=repo,
        caminho_relativo=caminho_rel,
    )
    return AlvoResolvido(alvo=alvo, bancada=None)


def _resolver_documento_git(
    pedido: PedidoEscrita,
    decisao: DecisaoPortao,
    spec: SpecClasse,
    documento: str | None,
) -> AlvoResolvido:
    chave_norm = normalizar_chave_casa(pedido.chave)
    slug = chave_norm.split(":", 1)[1] if ":" in chave_norm else chave_norm
    molde = spec.molde_para(documento) if documento else None
    rel_bruto = molde.replace("<slug>", slug) if molde else f"{spec.classe}/{slug}.md"
    caminho_rel = "/".join(validar_caminho_relativo(rel_bruto))
    alvo = AlvoEscrita(
        classe=decisao.classe,
        chave=chave_norm,
        regime=decisao.regime,
        morada="git",
        endereco=caminho_rel,
        documento=documento,
        repo="platafirma-casa",
        caminho_relativo=caminho_rel,
    )
    return AlvoResolvido(alvo=alvo, bancada=None)


def resolver_alvo(
    pedido: PedidoEscrita,
    decisao: DecisaoPortao,
    vista: VistaAlcance,
    *,
    raiz_bancadas: Path | None = None,
) -> AlvoResolvido:
    """Resolve a chave contra a vista de alcance depois de aprovada pelo portão."""
    spec = vista.classes.get(decisao.classe)
    if spec is None:
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="politica-indisponivel",
                onde="classe",
                recebido=decisao.classe,
                regra="classe decidida pelo portão ausente na vista de alcance",
                cura="verifique o espelho da vista de alcance da release",
                proximo="",
            )
        )
    documento = _resolver_documento(pedido, spec)
    if decisao.morada == "git":
        if decisao.classe == "componente":
            return _resolver_componente(pedido, decisao, raiz_bancadas)
        return _resolver_documento_git(pedido, decisao, spec, documento)
    chave_norm = normalizar_chave_casa(pedido.chave)
    alvo = AlvoEscrita(
        classe=decisao.classe,
        chave=chave_norm,
        regime=decisao.regime,
        morada=decisao.morada,
        endereco=chave_norm,
        documento=documento,
    )
    return AlvoResolvido(alvo=alvo, bancada=None)


def versoes_casam(informada: str, atual: str, *, morada: str) -> bool:
    """Compara a versão recebida com a versão vigente (aceita 12 ou 40 hex no git)."""
    if informada == atual:
        return True
    if morada == "git" and len(informada) == _TAM_VERSAO_CURTA_GIT:
        return atual.startswith(informada)
    return False


def _proximo_ler(verbo: str, alvo: AlvoEscrita) -> str:
    if alvo.classe == "componente":
        return f"{verbo} ler {alvo.chave}"
    return f"busca ler {alvo.chave}"


def _checar_versao_existente(
    pedido: PedidoEscrita, alvo: AlvoEscrita, estado: EstadoAlvo
) -> None:
    if pedido.versao is None:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="versao-ausente",
                onde="versao",
                recebido="(ausente)",
                regra="substituir alvo existente exige informar a versão lida",
                cura="leia a versão vigente do alvo e repita informando-a",
                proximo=_proximo_ler(pedido.verbo, alvo),
            )
        )
    atual = estado.versao_completa or estado.versao or ""
    if atual and not versoes_casam(pedido.versao, atual, morada=alvo.morada):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="versao-divergente",
                onde="versao",
                recebido=pedido.versao,
                regra=f"a versão informada diverge da vigente ({estado.versao or atual[:12]})",
                cura="releia o alvo para obter a versão vigente antes de gravar",
                proximo=_proximo_ler(pedido.verbo, alvo),
            )
        )


def _validar_forma_gravar(
    pedido: PedidoEscrita, alvo: AlvoEscrita, estado: EstadoAlvo
) -> None:
    if not estado.existe:
        if pedido.formato in ("trecho", "patch"):
            raise RecusaEscrita(
                ErroEscrita(
                    saida=1,
                    codigo="alvo-inexistente",
                    onde="chave",
                    recebido=alvo.chave,
                    regra=f"edição por {pedido.formato} exige arquivo existente na bancada",
                    cura="crie o arquivo com --formato inteiro ou confira a chave",
                    proximo=f"{pedido.verbo} gravar {alvo.classe} {alvo.chave}",
                )
            )
        if pedido.versao is not None:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="versao-invalida",
                    onde="versao",
                    recebido=pedido.versao,
                    regra="criar arquivo novo na bancada não aceita versão prévia",
                    cura="remova a versão da chamada para criar o arquivo",
                    proximo=f"{pedido.verbo} gravar {alvo.classe} {alvo.chave}",
                )
            )
        return
    _checar_versao_existente(pedido, alvo, estado)


def validar_precondicao_versao(
    pedido: PedidoEscrita, alvo: AlvoEscrita, estado: EstadoAlvo
) -> None:
    """Valida existência e controle otimista de versão para todas as formas."""
    forma = pedido.forma_ensaiada if pedido.forma == "ensaiar" else pedido.forma
    if forma == "gravar":
        _validar_forma_gravar(pedido, alvo, estado)
        return
    if forma == "criar":
        if estado.existe:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="ja-existe",
                    onde="chave",
                    recebido=alvo.chave,
                    regra="criar exige chave ainda inexistente na morada",
                    cura="use trocar informando a versão vigente",
                    proximo=f"{pedido.verbo} trocar {alvo.classe} {alvo.chave} {estado.versao or ''}".strip(),
                )
            )
        return
    if not estado.existe:
        raise RecusaEscrita(
            ErroEscrita(
                saida=1,
                codigo="alvo-inexistente",
                onde="chave",
                recebido=alvo.chave,
                regra=f"a forma {forma} exige alvo existente na morada",
                cura="confira a chave com busca ou crie o objeto com criar",
                proximo=f"{pedido.verbo} criar {alvo.classe} {alvo.chave}",
            )
        )
    if forma == "trocar" or pedido.versao is not None:
        _checar_versao_existente(pedido, alvo, estado)
