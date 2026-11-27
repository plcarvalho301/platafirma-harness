"""casamento — seleção da régua e prova de compatibilidade estrutural `alvo × régua` (card #4454)."""
from __future__ import annotations

from leitura.recusa import Recusa

from .tipos import (
    SERVICO_EXECUTOR_TESTES,
    LeitorFichario,
    PedidoVerificacao,
    ReguaCasada,
    ReguaFicha,
)

_REGRA_CASAMENTO = "ato:verificar §Contra que régua e como ocorre o casamento?"
_REGRA_UNIDADE = "ato:verificar §Qual é a forma e a regra de unidade da chamada?"
_CHAVE_ONTOLOGIA = "gabarito:framework-da-ontologia"


def _carregar_reguas(
    pedido: PedidoVerificacao,
    classe_alvo: str,
    fichario: LeitorFichario,
) -> list[ReguaFicha]:
    chaves = list(pedido.reguas)
    if not chaves:
        padrao = fichario.regua_padrao(classe_alvo)
        if not padrao:
            raise Recusa(
                1,
                "regua-inexistente",
                onde="regua",
                recebido=classe_alvo,
                regra=_REGRA_CASAMENTO,
                cura=f"a classe '{classe_alvo}' não declara régua padrão; informe --regua <chave>",
                proximo=f"{pedido.verbo} verificar {pedido.alvos[0]} --regua gabarito:<slug>",
            )
        chaves = [padrao]

    reguas: list[ReguaFicha] = []
    for chave in chaves:
        ficha = fichario.ler_regua(chave)
        if ficha is None:
            raise Recusa(
                1,
                "regua-inexistente",
                onde="regua",
                recebido=chave,
                regra=_REGRA_CASAMENTO,
                cura=f"a régua '{chave}' não existe no fichário",
                proximo=f"busca consultar --classe gabarito",
            )
        reguas.append(ficha)
    return reguas


def _validar_unidade_e_compatibilidade(
    pedido: PedidoVerificacao,
    classe_alvo: str,
    reguas: list[ReguaFicha],
    fichario: LeitorFichario,
) -> tuple[str, str]:
    formas = {r.forma for r in reguas}
    if len(formas) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="regua",
            recebido=", ".join(r.chave for r in reguas),
            regra=_REGRA_UNIDADE,
            cura="não misture formas distintas (gabarito, teste, bateria) na mesma chamada",
            proximo=f"{pedido.verbo} verificar {pedido.alvos[0]} --regua {reguas[0].chave}",
        )
    forma = next(iter(formas))

    if forma == "bateria" and len(reguas) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="regua",
            recebido=", ".join(r.chave for r in reguas),
            regra=_REGRA_UNIDADE,
            cura="não é permitido repetir baterias distintas na mesma chamada",
            proximo=f"{pedido.verbo} verificar {pedido.alvos[0]} --regua {reguas[0].chave}",
        )

    planos = {r.contra_o_que for r in reguas}
    if len(planos) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="regua",
            recebido=", ".join(r.chave for r in reguas),
            regra=_REGRA_CASAMENTO,
            cura="todas as réguas da chamada devem operar sobre o mesmo plano (construcao ou producao)",
            proximo=f"{pedido.verbo} verificar {pedido.alvos[0]} --regua {reguas[0].chave}",
        )
    plano = next(iter(planos))

    for regua in reguas:
        if regua.sobre and not fichario.linhagem_compativel(classe_alvo, regua.sobre):
            raise Recusa(
                2,
                "regua-incompativel",
                onde="regua",
                recebido=f"{classe_alvo} × {regua.chave}",
                regra=_REGRA_CASAMENTO,
                cura=f"a régua '{regua.chave}' se aplica a {', '.join(regua.sobre)}, não a '{classe_alvo}'",
                proximo=f"busca ler {regua.chave}",
            )

    return forma, plano


def _resolver_servico(reguas: list[ReguaFicha], forma: str, plano: str) -> str:
    if plano == "producao":
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="plano",
            recebido="producao",
            regra=_REGRA_CASAMENTO,
            cura="o executor contra produção entra na story #4397",
        )
    if forma == "bateria":
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="regua",
            recebido=reguas[0].chave,
            regra=_REGRA_CASAMENTO,
            cura="o executor de bateria ainda não está ligado nesta story",
        )
    if any(r.chave == _CHAVE_ONTOLOGIA for r in reguas):
        raise Recusa(
            3,
            "dependencia-sem-resposta",
            onde="regua",
            recebido=_CHAVE_ONTOLOGIA,
            regra=_REGRA_CASAMENTO,
            cura="o executor do framework da ontologia entra na story #4398",
        )

    if forma == "teste":
        servicos = {r.garantido_por or SERVICO_EXECUTOR_TESTES for r in reguas}
    else:
        sem_servico = [r for r in reguas if not r.garantido_por]
        if sem_servico:
            chaves = ", ".join(r.chave for r in sem_servico)
            raise Recusa(
                5,
                "sem-motor-deterministico",
                onde="regua",
                recebido=chaves,
                regra=_REGRA_CASAMENTO,
                cura="gabarito sem garantido-por exige julgamento probabilístico pela persona ou juiz por modelo",
                proximo=f"busca ler {sem_servico[0].chave}",
            )
        servicos = {r.garantido_por for r in reguas if r.garantido_por}

    if len(servicos) > 1:
        raise Recusa(
            2,
            "regua-incompativel",
            onde="regua",
            recebido=", ".join(sorted(servicos)),
            regra=_REGRA_UNIDADE,
            cura="não é permitido combinar réguas de serviços distintos na mesma chamada",
            proximo=f"busca ler {reguas[0].chave}",
        )

    return next(iter(servicos))


def casar_regua(
    pedido: PedidoVerificacao,
    classe_alvo: str,
    fichario: LeitorFichario,
) -> ReguaCasada:
    """Resolve as réguas do pedido, valida compatibilidade estrutural e devolve `ReguaCasada`."""
    reguas = _carregar_reguas(pedido, classe_alvo, fichario)
    forma, plano = _validar_unidade_e_compatibilidade(pedido, classe_alvo, reguas, fichario)
    servico = _resolver_servico(reguas, forma, plano)
    return ReguaCasada(
        forma=forma,
        servico=servico,
        reguas=tuple(reguas),
        contra_o_que=plano,
    )
