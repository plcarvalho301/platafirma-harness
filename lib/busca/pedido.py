"""pedido.py — recebimento e conferência de forma de `busca consultar` (story 4427, t9).

Contratos:
- platafirma-casa@referencias/instancias/verbo/busca.md, «Como a chamada chega e vira pedido»,
  «A escrita das flags na linha de comando» e «Os códigos de saída».

Transforma os argumentos e o ambiente da porta num `Pedido` imutável e confere toda a forma
sem tocar no banco, acumulando todos os erros numa lista só.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from leitura.recusa import Recusa, Recusas

REGRA_PEDIDO = "verbo:busca §Como a chamada chega e vira pedido"
REGRA_FLAGS = "verbo:busca §A escrita das flags na linha de comando"
REGRA_CONTINUACAO = "verbo:busca §A continuação"

USO_NOME = "busca consultar <termo> [--ligacoes com|sem] [--json]"
USO_CLASSE = (
    "busca consultar --classe <classe> [--prop <p>=<v>] [--sem-prop <p>[=<v>]] "
    "[--ligacao [saida:|chegada:]<p>[/<1..8>]=<alvo>] "
    "[--sem-ligacao [saida:|chegada:]<p>[=<alvo>]] [--estado <e>] [--filhas] [--cursor <c>] [--json]"
)

TETO_TEXTO = 200
TETO_CURSOR = 4096
PASSOS_MIN = 1
PASSOS_MAX = 8
VERSAO_CURSOR = 1
SENTIDOS_LIGACAO = ("saida", "chegada")
ORIGENS_VALIDAS = ("buscar", "malote", "leitura")
VALORES_LIGACOES = ("com", "sem")


class CursorIlegivelError(ValueError):
    """Token de continuação mal formado ou de versão desconhecida."""


@dataclass(frozen=True)
class Contexto:
    sessao: str | None
    ordem: str | None
    giro: int | None
    sujeito: str | None
    cadeira: str | None
    pedido_id: str | None


@dataclass(frozen=True)
class FiltroPropriedadeCru:
    propriedade: str
    valor: str | None
    sem: bool


@dataclass(frozen=True)
class FiltroLigacaoCru:
    propriedade: str
    sentido: str
    alvo: str | None
    passos: int
    sem: bool


@dataclass(frozen=True)
class CursorDecodificado:
    versao: int
    ordem: int
    chave: str
    fornada: str | None
    resumo: str


@dataclass(frozen=True)
class Pedido:
    modo: str
    termo: str | None
    classe: str | None
    propriedades: tuple[FiltroPropriedadeCru, ...]
    faltas_propriedade: tuple[FiltroPropriedadeCru, ...]
    ligacoes: tuple[FiltroLigacaoCru, ...]
    faltas_ligacao: tuple[FiltroLigacaoCru, ...]
    estado: str | None
    filhas: bool
    com_ligacoes: str
    continuacao: CursorDecodificado | None
    continuacao_bruta: str | None
    como_json: bool
    origem: str
    contexto: Contexto
    resumo: str


@dataclass
class _AcumuladorArgs:
    args: Sequence[str]
    erros: list[Recusa] = field(default_factory=list)
    posicionais: list[str] = field(default_factory=list)
    classe: str | None = None
    props: list[FiltroPropriedadeCru] = field(default_factory=list)
    sem_props: list[FiltroPropriedadeCru] = field(default_factory=list)
    ligs: list[FiltroLigacaoCru] = field(default_factory=list)
    sem_ligs: list[FiltroLigacaoCru] = field(default_factory=list)
    estado: str | None = None
    filhas: bool = False
    ligacoes_flag: str | None = None
    cursor_txt: str | None = None
    como_json: bool = False


def ler_contexto(env: Mapping[str, str] | None = None) -> tuple[Contexto, str]:
    ambiente = os.environ if env is None else env
    giro_txt = ambiente.get("PF_GIRO") or ""
    giro = int(giro_txt) if giro_txt.isdigit() else None
    origem_crua = (ambiente.get("PF_ORIGEM") or "buscar").strip()
    origem = origem_crua if origem_crua in ORIGENS_VALIDAS else "buscar"
    ctx = Contexto(
        sessao=ambiente.get("PF_SESSAO") or None,
        ordem=ambiente.get("PF_ORDEM_ID") or None,
        giro=giro,
        sujeito=ambiente.get("PF_SUJEITO") or None,
        cadeira=ambiente.get("PF_CADEIRA") or None,
        pedido_id=ambiente.get("PF_PEDIDO_ID") or None,
    )
    return ctx, origem


def _tem_alfanumerico(texto: str) -> bool:
    return any(ch.isalnum() for ch in texto)


def _proximo_distinto(sugestao: str, args_recebidos: Sequence[str]) -> str:
    chamada_atual = "busca consultar" + (" " + shlex.join(args_recebidos) if args_recebidos else "")
    if sugestao != chamada_atual:
        return sugestao
    return "busca consultar --classe shape"


def codificar_cursor(*, ordem: int, chave: str, fornada: str | None, resumo: str) -> str:
    payload = {
        "v": VERSAO_CURSOR,
        "ordem": ordem,
        "chave": chave,
        "fornada": fornada,
        "resumo": resumo,
    }
    bruto = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(bruto).decode("ascii").rstrip("=")


def decodificar_cursor(token: str) -> CursorDecodificado:
    if not token or len(token) > TETO_CURSOR:
        raise CursorIlegivelError("token vazio ou acima do teto")
    padding = "=" * (-len(token) % 4)
    try:
        decodificado = base64.urlsafe_b64decode((token + padding).encode("ascii"))
        dados = json.loads(decodificado.decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise CursorIlegivelError("token base64url ou JSON inválido") from exc
    if not isinstance(dados, dict) or dados.get("v") != VERSAO_CURSOR:
        raise CursorIlegivelError("versão desconhecida do token")
    ordem = dados.get("ordem")
    chave = dados.get("chave")
    fornada = dados.get("fornada")
    resumo = dados.get("resumo")
    if isinstance(ordem, bool) or not isinstance(ordem, int):
        raise CursorIlegivelError("ordem inválida no token")
    if not isinstance(chave, str) or not chave or not isinstance(resumo, str) or not resumo:
        raise CursorIlegivelError("chave ou resumo ausentes no token")
    if fornada is not None and (not isinstance(fornada, str) or not fornada):
        raise CursorIlegivelError("fornada inválida no token")
    return CursorDecodificado(versao=VERSAO_CURSOR, ordem=ordem, chave=chave, fornada=fornada, resumo=resumo)


def _calcular_resumo(modo: str, ac: _AcumuladorArgs) -> str:
    canonico = {
        "modo": modo,
        "classe": (ac.classe or "").strip(),
        "filhas": ac.filhas,
        "propriedades": sorted(
            [{"p": p.propriedade, "v": p.valor} for p in ac.props],
            key=lambda x: (x["p"], x["v"] or ""),
        ),
        "faltas_propriedade": sorted(
            [{"p": p.propriedade, "v": p.valor} for p in ac.sem_props],
            key=lambda x: (x["p"], x["v"] or ""),
        ),
        "ligacoes": sorted(
            [{"s": g.passos, "p": g.propriedade, "d": g.sentido, "a": g.alvo or ""} for g in ac.ligs],
            key=lambda x: (x["s"], x["p"], x["d"], x["a"]),
        ),
        "faltas_ligacao": sorted(
            [{"p": g.propriedade, "d": g.sentido, "a": g.alvo or ""} for g in ac.sem_ligs],
            key=lambda x: (x["p"], x["d"], x["a"]),
        ),
        "estado": ac.estado,
    }
    serializado = json.dumps(canonico, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()


def _validar_tamanho(ac: _AcumuladorArgs, onde: str, valor: str) -> None:
    if len(valor) > TETO_TEXTO:
        ac.erros.append(Recusa(
            2,
            "texto-longo-demais",
            onde=onde,
            recebido=valor,
            regra=REGRA_PEDIDO,
            cura=f"{onde} aceita até {TETO_TEXTO} caracteres",
            proximo=_proximo_distinto(USO_CLASSE, ac.args),
        ))


def _parse_prop(ac: _AcumuladorArgs, raw: str, *, sem: bool) -> FiltroPropriedadeCru | None:
    onde = "--sem-prop" if sem else "--prop"
    if "=" not in raw:
        if not sem:
            ac.erros.append(Recusa(
                2, "argumento-fora-do-modo", onde=onde, recebido=raw, regra=REGRA_FLAGS,
                cura="--prop pede <propriedade>=<valor>",
                proximo=_proximo_distinto("busca consultar --classe shape --prop capacidade=busca", ac.args),
            ))
            return None
        prop = raw.strip()
        if not prop:
            ac.erros.append(Recusa(
                2, "argumento-fora-do-modo", onde=onde, recebido=raw, regra=REGRA_FLAGS,
                cura="--sem-prop pede o nome da propriedade",
                proximo=_proximo_distinto("busca consultar --classe shape --sem-prop mae", ac.args),
            ))
            return None
        _validar_tamanho(ac, onde, prop)
        return FiltroPropriedadeCru(propriedade=prop, valor=None, sem=True)

    prop, valor = raw.split("=", 1)
    prop = prop.strip()
    if not prop or valor == "":
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde=onde, recebido=raw, regra=REGRA_FLAGS,
            cura=f"{onde} pede <propriedade>=<valor> não vazios",
            proximo=_proximo_distinto("busca consultar --classe shape --prop capacidade=busca", ac.args),
        ))
        return None
    _validar_tamanho(ac, onde, prop)
    _validar_tamanho(ac, onde, valor)
    return FiltroPropriedadeCru(propriedade=prop, valor=valor, sem=sem)


def _separar_sentido_e_passos(ac: _AcumuladorArgs, cabeca: str, raw: str, *, sem: bool) -> tuple[str, str, int] | None:
    onde = "--sem-ligacao" if sem else "--ligacao"
    sentido = "saida"
    resto = cabeca
    if ":" in cabeca:
        cand_sentido, pos_pontos = cabeca.split(":", 1)
        if cand_sentido not in SENTIDOS_LIGACAO:
            ac.erros.append(Recusa(
                2, "argumento-fora-do-modo", onde=onde, recebido=raw, regra=REGRA_FLAGS,
                cura="o sentido da ligação escreve-se saida ou chegada antes de dois-pontos",
                proximo=_proximo_distinto("busca consultar --classe gabarito --ligacao confere=capacidade:ontologia", ac.args),
            ))
            return None
        sentido = cand_sentido
        resto = pos_pontos

    passos = 1
    prop = resto
    if "/" in resto:
        prop, passos_txt = resto.split("/", 1)
        if sem:
            ac.erros.append(Recusa(
                2, "passos-fora-da-faixa", onde=onde, recebido=raw, regra=REGRA_PEDIDO,
                cura="--sem-ligacao olha só o passo direto e não aceita /<passos>",
                proximo=_proximo_distinto(f"busca consultar --classe gabarito --sem-ligacao {prop or 'confere'}", ac.args),
            ))
            return None
        try:
            passos = int(passos_txt)
        except ValueError:
            passos = 0
        if passos < PASSOS_MIN or passos > PASSOS_MAX:
            ac.erros.append(Recusa(
                2, "passos-fora-da-faixa", onde=onde, recebido=raw, regra=REGRA_PEDIDO,
                cura=f"os passos da ligação vão de {PASSOS_MIN} a {PASSOS_MAX}",
                proximo=_proximo_distinto(
                    f"busca consultar --classe gabarito --ligacao {prop or 'confere'}/2=capacidade:ontologia", ac.args,
                ),
            ))
            return None

    prop = prop.strip()
    if not prop:
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde=onde, recebido=raw, regra=REGRA_FLAGS,
            cura=f"{onde} pede o nome da ligação",
            proximo=_proximo_distinto("busca consultar --classe gabarito --ligacao confere=capacidade:ontologia", ac.args),
        ))
        return None
    _validar_tamanho(ac, onde, prop)
    return sentido, prop, passos


def _parse_ligacao(ac: _AcumuladorArgs, raw: str, *, sem: bool) -> FiltroLigacaoCru | None:
    onde = "--sem-ligacao" if sem else "--ligacao"
    if "=" not in raw:
        if not sem:
            ac.erros.append(Recusa(
                2, "alvo-mal-formado", onde=onde, recebido=raw, regra=REGRA_FLAGS,
                cura="--ligacao pede [saida:|chegada:]<ligacao>[/<1..8>]=<alvo>",
                proximo=_proximo_distinto("busca consultar --classe gabarito --ligacao confere=capacidade:ontologia", ac.args),
            ))
            return None
        partes = _separar_sentido_e_passos(ac, raw, raw, sem=True)
        if partes is None:
            return None
        sentido, prop, passos = partes
        return FiltroLigacaoCru(propriedade=prop, sentido=sentido, alvo=None, passos=passos, sem=True)

    cabeca, alvo = raw.split("=", 1)
    partes = _separar_sentido_e_passos(ac, cabeca, raw, sem=sem)
    alvo_limpo = alvo.strip()
    if not alvo_limpo or not _tem_alfanumerico(alvo_limpo):
        ac.erros.append(Recusa(
            2, "alvo-mal-formado", onde=onde, recebido=raw, regra=REGRA_PEDIDO,
            cura="o alvo da ligação precisa trazer ao menos uma letra ou número",
            proximo=_proximo_distinto("busca consultar --classe gabarito --ligacao confere=capacidade:ontologia", ac.args),
        ))
        return None
    _validar_tamanho(ac, onde, alvo_limpo)
    if partes is None:
        return None
    sentido, prop, passos = partes
    return FiltroLigacaoCru(propriedade=prop, sentido=sentido, alvo=alvo_limpo, passos=passos, sem=sem)


def _flag_classe(ac: _AcumuladorArgs, val: str) -> None:
    ac.classe = val
    if not val.strip():
        ac.erros.append(Recusa(
            2, "classe-ausente", onde="--classe", recebido=val, regra=REGRA_PEDIDO,
            cura="--classe pede o slug ou nome da classe",
            proximo=_proximo_distinto("busca consultar --classe gabarito", ac.args),
        ))
    else:
        _validar_tamanho(ac, "--classe", val)


def _flag_estado(ac: _AcumuladorArgs, val: str) -> None:
    ac.estado = val
    if not val.strip():
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde="--estado", recebido=val, regra=REGRA_PEDIDO,
            cura="--estado pede o nome do estado",
            proximo=_proximo_distinto("busca consultar --classe card --estado em-execucao", ac.args),
        ))
    else:
        _validar_tamanho(ac, "--estado", val)


def _flag_ligacoes(ac: _AcumuladorArgs, val: str) -> None:
    ac.ligacoes_flag = val
    if val not in VALORES_LIGACOES:
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde="--ligacoes", recebido=val, regra=REGRA_FLAGS,
            cura="--ligacoes aceita com ou sem",
            proximo=_proximo_distinto("busca consultar gabarito --ligacoes sem", ac.args),
        ))


def _flag_prop(ac: _AcumuladorArgs, val: str) -> None:
    p = _parse_prop(ac, val, sem=False)
    if p is not None:
        ac.props.append(p)


def _flag_sem_prop(ac: _AcumuladorArgs, val: str) -> None:
    sp = _parse_prop(ac, val, sem=True)
    if sp is not None:
        ac.sem_props.append(sp)


def _flag_ligacao(ac: _AcumuladorArgs, val: str) -> None:
    lg = _parse_ligacao(ac, val, sem=False)
    if lg is not None:
        ac.ligs.append(lg)


def _flag_sem_ligacao(ac: _AcumuladorArgs, val: str) -> None:
    slg = _parse_ligacao(ac, val, sem=True)
    if slg is not None:
        ac.sem_ligs.append(slg)


def _flag_cursor(ac: _AcumuladorArgs, val: str) -> None:
    ac.cursor_txt = val


_TRATADORES_FILTRO = {
    "--classe": _flag_classe,
    "--prop": _flag_prop,
    "--sem-prop": _flag_sem_prop,
    "--ligacao": _flag_ligacao,
    "--sem-ligacao": _flag_sem_ligacao,
    "--estado": _flag_estado,
}
FILTROS_DISPONIVEIS = (*_TRATADORES_FILTRO.keys(), "--filhas")
_TRATADORES_FLAG = {
    **_TRATADORES_FILTRO,
    "--ligacoes": _flag_ligacoes,
    "--cursor": _flag_cursor,
}


def _coletar_args(args: Sequence[str]) -> _AcumuladorArgs:
    ac = _AcumuladorArgs(args=args)
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--json":
            ac.como_json = True
        elif tok == "--filhas":
            ac.filhas = True
        elif tok in _TRATADORES_FLAG:
            if i + 1 >= len(args):
                ac.erros.append(Recusa(
                    2, "argumento-fora-do-modo", onde=tok, recebido="", regra=REGRA_FLAGS,
                    cura=f"{tok} pede um valor", proximo=_proximo_distinto(USO_CLASSE, args),
                ))
                i += 1
                continue
            _TRATADORES_FLAG[tok](ac, args[i + 1])
            i += 1
        elif tok.startswith("--") and any(ch.isalpha() for ch in tok):
            ac.erros.append(Recusa(
                2, "argumento-fora-do-modo", onde=tok, recebido=tok, regra=REGRA_FLAGS,
                cura=f"flag desconhecida no consultar; filtros aceitos: {', '.join(FILTROS_DISPONIVEIS)}",
                proximo=_proximo_distinto(USO_CLASSE, args),
            ))
        else:
            ac.posicionais.append(tok)
        i += 1
    return ac


def _conferir_modos(ac: _AcumuladorArgs) -> tuple[str, str | None]:
    termo = " ".join(ac.posicionais).strip() if ac.posicionais else None
    tem_filtro_classe = bool(
        ac.props or ac.sem_props or ac.ligs or ac.sem_ligs or ac.estado is not None or ac.filhas
    )

    if ac.classe is None and termo is None:
        codigo = "classe-ausente" if tem_filtro_classe else "termo-ausente"
        onde = "--classe" if tem_filtro_classe else "termo"
        cura = (
            "predicado, falta, ligação, estado e --filhas exigem --classe <classe>"
            if tem_filtro_classe
            else "passe um termo em posição ou --classe <classe>"
        )
        ac.erros.append(Recusa(
            2, codigo, onde=onde, recebido="", regra=REGRA_PEDIDO,
            cura=cura, proximo=_proximo_distinto("busca consultar --classe shape", ac.args),
        ))
        return ("classe" if tem_filtro_classe else "nome"), termo

    if ac.classe is not None and termo is not None:
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde="termo", recebido=termo, regra=REGRA_PEDIDO,
            cura="o consultar recebe o termo em posição ou --classe, nunca os dois",
            proximo=_proximo_distinto(f"busca consultar --classe {shlex.quote(ac.classe)}", ac.args),
        ))
    elif ac.classe is None and termo is not None and tem_filtro_classe:
        ac.erros.append(Recusa(
            2, "classe-ausente", onde="--classe", recebido=termo, regra=REGRA_PEDIDO,
            cura="predicado, falta, ligação, estado e --filhas exigem --classe <classe>, sem termo posicional",
            proximo=_proximo_distinto("busca consultar --classe gabarito", ac.args),
        ))

    modo = "classe" if ac.classe is not None else "nome"
    _conferir_restricoes_do_modo(ac, modo, termo)
    return modo, termo


def _conferir_restricoes_do_modo(ac: _AcumuladorArgs, modo: str, termo: str | None) -> None:
    if modo == "nome":
        if ac.cursor_txt is not None:
            ac.erros.append(Recusa(
                2, "argumento-fora-do-modo", onde="--cursor", recebido=ac.cursor_txt, regra=REGRA_PEDIDO,
                cura="--cursor só vale na consulta por condição (--classe)",
                proximo=_proximo_distinto(f"busca consultar {shlex.quote(termo or 'gabarito')}", ac.args),
            ))
        if termo is not None:
            _validar_tamanho(ac, "termo", termo)
            if not _tem_alfanumerico(termo):
                ac.erros.append(Recusa(
                    2, "termo-sem-letra", onde="termo", recebido=termo, regra=REGRA_PEDIDO,
                    cura="o termo precisa ter ao menos uma letra ou número",
                    proximo=_proximo_distinto("busca consultar gabarito", ac.args),
                ))
    elif ac.ligacoes_flag is not None:
        ac.erros.append(Recusa(
            2, "argumento-fora-do-modo", onde="--ligacoes", recebido=ac.ligacoes_flag, regra=REGRA_PEDIDO,
            cura="--ligacoes só vale na consulta por nome",
            proximo=_proximo_distinto(f"busca consultar --classe {shlex.quote(ac.classe or 'gabarito')}", ac.args),
        ))


def receber_pedido(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    origem_forca: str | None = None,
) -> Pedido:
    """Transforma `args` num `Pedido` validado; levanta `Recusas` (saída 2) com todos os erros."""
    ctx, origem_env = ler_contexto(env)
    origem = origem_forca if origem_forca is not None else origem_env

    ac = _coletar_args(args)
    modo, termo = _conferir_modos(ac)
    resumo = _calcular_resumo(modo, ac)

    cursor_dec: CursorDecodificado | None = None
    if modo == "classe" and ac.cursor_txt is not None:
        try:
            cursor_dec = decodificar_cursor(ac.cursor_txt)
        except CursorIlegivelError:
            ac.erros.append(Recusa(
                2,
                "continuacao-ilegivel",
                onde="--cursor",
                recebido=ac.cursor_txt,
                regra=REGRA_CONTINUACAO,
                cura="o token de --cursor está ilegível ou é de versão desconhecida; repita a primeira página",
                proximo=_proximo_distinto(f"busca consultar --classe {shlex.quote(ac.classe or 'shape')}", args),
            ))
        else:
            if cursor_dec.resumo != resumo:
                ac.erros.append(Recusa(
                    2,
                    "continuacao-divergente",
                    onde="--cursor",
                    recebido=ac.cursor_txt,
                    regra=REGRA_CONTINUACAO,
                    cura="o token de --cursor foi gerado para outros argumentos; rode sem --cursor para nova consulta",
                    proximo=_proximo_distinto(f"busca consultar --classe {shlex.quote(ac.classe or 'shape')}", args),
                ))

    if ac.erros:
        raise Recusas(ac.erros)

    return Pedido(
        modo=modo,
        termo=termo,
        classe=ac.classe,
        propriedades=tuple(ac.props),
        faltas_propriedade=tuple(ac.sem_props),
        ligacoes=tuple(ac.ligs),
        faltas_ligacao=tuple(ac.sem_ligs),
        estado=ac.estado,
        filhas=ac.filhas,
        com_ligacoes=ac.ligacoes_flag or "com",
        continuacao=cursor_dec,
        continuacao_bruta=ac.cursor_txt,
        como_json=ac.como_json,
        origem=origem,
        contexto=ctx,
        resumo=resumo,
    )
