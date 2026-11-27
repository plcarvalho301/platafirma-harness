"""conteudos — leitura de alvos e fichário sob um único retrato de leitura (card #4454).

Usa `Retrato` e `resolvedor` de `lib/leitura/` para ler fichas e réguas numa única transação
REPEATABLE READ READ ONLY por chamada, respeitando o teto de quatro conexões do papel de leitura.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from leitura.recusa import Recusa
from leitura.resolvedor import SQL_FICHA_INTEIRA, caminho_do_molde, ficha_da_chave
from leitura.retrato import Retrato

from .tipos import AlvoVerificado, LeitorFichario, PedidoVerificacao, ReguaFicha

_REGRA_CONTEUDOS = "ato:verificar §Como o veredito se forma?"
_CLASSES_CODIGO = frozenset({"componente", "repositorio"})


def traduzir_recusa_retrato(exc: Recusa) -> Recusa:
    """Normaliza recusas internas do `Retrato` para a tabela de códigos do ato `verificar`."""
    if exc.codigo in ("conexoes-esgotadas", "banco-indisponivel"):
        return Recusa(
            3,
            "dependencia-sem-resposta",
            onde=exc.onde or "leitor",
            recebido=exc.recebido,
            regra=_REGRA_CONTEUDOS,
            cura=exc.cura or "o banco casa não respondeu ou atingiu o teto de conexões",
        )
    if exc.codigo == "prazo-estourado":
        return Recusa(
            5,
            "tempo-esgotado",
            onde=exc.onde or "leitor",
            recebido=exc.recebido,
            regra=_REGRA_CONTEUDOS,
            cura=exc.cura or "o prazo do retrato de leitura esgotou",
        )
    return exc


def _normalizar_nome_classe(ref: str) -> str:
    limpo = ref.strip()
    if limpo.startswith("shape:"):
        return limpo.removeprefix("shape:")
    return limpo


def _ler_texto_release_casa(documento: str | None) -> tuple[Path | None, str | None]:
    if not documento:
        return None, None
    release_casa = Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current")) / "casa"
    caminho = release_casa / documento
    try:
        return release_casa, caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return release_casa, None


class FicharioBanco:
    """Adaptador de `LeitorFichario` sobre um único `Retrato` aberto para a chamada inteira."""

    def __init__(self, retrato: Retrato) -> None:
        self._retrato = retrato
        self._cache_ficha: dict[str, dict[str, Any] | None] = {}

    def _ler_completa(self, chave: str) -> dict[str, Any] | None:
        if chave in self._cache_ficha:
            return self._cache_ficha[chave]
        try:
            f = ficha_da_chave(self._retrato, chave)
            if f is None:
                self._cache_ficha[chave] = None
                return None
            linhas = self._retrato.consultar(SQL_FICHA_INTEIRA, f.uuid)
        except Recusa as exc:
            raise traduzir_recusa_retrato(exc) from exc
        if not linhas or not isinstance(linhas[0].get("ficha"), Mapping):
            self._cache_ficha[chave] = None
            return None
        dados = dict(linhas[0]["ficha"])
        dados["_ficha_obj"] = f
        self._cache_ficha[chave] = dados
        return dados

    def ler_regua(self, chave: str) -> ReguaFicha | None:
        dados = self._ler_completa(chave)
        if dados is None:
            return None
        forma = str(dados.get("classe") or "").strip()
        if forma not in ("gabarito", "teste", "bateria"):
            return None
        campos = dados.get("campos") if isinstance(dados.get("campos"), Mapping) else {}
        ligs_saida = (
            dados.get("ligacoes", {}).get("saida", {})
            if isinstance(dados.get("ligacoes"), Mapping)
            else {}
        )
        sobre = tuple(str(x) for x in (ligs_saida.get("sobre") or []) if str(x).strip())
        garantido = ligs_saida.get("garantido-por") or []
        garantido_por = str(garantido[0]).strip() if garantido else None
        contra = str(campos.get("contra-o-que") or "construcao").strip() or "construcao"
        versao = str(campos.get("rev") or campos.get("versao") or dados.get("fornada") or "1")
        verifica_list = ligs_saida.get("verifica") or []
        verifica = str(verifica_list[0]).strip() if verifica_list else None
        return ReguaFicha(
            chave=str(dados.get("chave") or chave),
            forma=forma,
            sobre=sobre,
            contra_o_que=contra,
            garantido_por=garantido_por,
            versao=versao,
            verifica=verifica,
        )

    def regua_padrao(self, classe: str) -> str | None:
        dados = self._ler_completa(f"shape:{classe}")
        if dados is None:
            return None
        ligs_saida = (
            dados.get("ligacoes", {}).get("saida", {})
            if isinstance(dados.get("ligacoes"), Mapping)
            else {}
        )
        padroes = ligs_saida.get("regua-padrao") or ligs_saida.get("verificado-por") or []
        return str(padroes[0]).strip() if padroes else None

    def ler_alvo(self, chave: str) -> AlvoVerificado | None:
        dados = self._ler_completa(chave)
        if dados is None:
            return None
        f_obj = dados["_ficha_obj"]
        decl = dados.get("declaracao") if isinstance(dados.get("declaracao"), Mapping) else {}
        molde = str(decl.get("molde") or "") if decl else ""
        documento: str | None = None
        if molde:
            documento, _ = caminho_do_molde(molde, f_obj)
        else:
            shape_dados = self._ler_completa(f"shape:{f_obj.classe}")
            shape_decl = shape_dados.get("declaracao") if isinstance(shape_dados, Mapping) else None
            if isinstance(shape_decl, Mapping) and shape_decl.get("molde"):
                documento, _ = caminho_do_molde(str(shape_decl["molde"]), f_obj)

        raiz_casa, texto = _ler_texto_release_casa(documento)
        slug = f_obj.chave.split(":", 1)[1] if ":" in f_obj.chave else f_obj.chave
        versao = str(dados.get("fornada") or "vigente")
        return AlvoVerificado(
            chave=f_obj.chave_lida,
            classe=f_obj.classe,
            slug=slug,
            versao=versao,
            raiz=raiz_casa,
            caminho=documento,
            texto=texto,
        )

    def linhagem_compativel(self, classe_alvo: str, sobre: Sequence[str]) -> bool:
        alvo_norm = _normalizar_nome_classe(classe_alvo)
        return any(_normalizar_nome_classe(s) == alvo_norm for s in sobre)


def carregar_alvos(
    pedido: PedidoVerificacao,
    classe_alvo: str,
    fichario: LeitorFichario,
    *,
    leitor_arvore: Callable[[str, str | None], AlvoVerificado | None] | None = None,
) -> tuple[AlvoVerificado, ...]:
    """Carrega todos os alvos da chamada sob o mesmo fichário/retrato."""
    alvos: list[AlvoVerificado] = []
    for chave in pedido.alvos:
        alvo: AlvoVerificado | None = None
        if classe_alvo in _CLASSES_CODIGO and leitor_arvore is not None:
            alvo = leitor_arvore(chave, pedido.substrato)
        if alvo is None:
            alvo = fichario.ler_alvo(chave)
        if alvo is None:
            raise Recusa(
                1,
                "alvo-inexistente",
                onde="alvo",
                recebido=chave,
                regra=_REGRA_CONTEUDOS,
                cura=f"o alvo '{chave}' não foi encontrado no substrato",
                proximo=f"busca ler {chave}",
            )
        alvos.append(alvo)
    return tuple(alvos)
