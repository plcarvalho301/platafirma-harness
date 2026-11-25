"""Estágios 1 e 2 da escrita: recebimento limitado e conversão de borda."""
from __future__ import annotations

import json
import os
import re
import resource
import secrets
import time
from collections.abc import Sequence
from typing import BinaryIO

from .politica import PoliticaEscrita
from .tipos import (
    DOCUMENTOS_ALVO,
    FORMAS_ENSAIAR,
    FORMAS_ESCRITA,
    FORMATOS_CONTEUDO,
    ContextoEscrita,
    ErroEscrita,
    HunkPatch,
    PatchEstrito,
    PedidoEscrita,
    RecusaEscrita,
    TrocaTrecho,
)

_VARIANTES_FORMA: dict[str, str] = {
    "escrever": "gravar",
    "editar": "trocar",
    "atualizar": "trocar",
    "substituir": "trocar",
    "salvar": "gravar",
}
_VARIANTES_FLAG = frozenset({"--dry-run", "--ensaio"})
_FLAGS_COM_VALOR = frozenset({"--pedido", "--documento", "--formato"})
_FLAGS_SEM_VALOR = frozenset({"--permitir-vazio", "--json"})
_RE_UUIDV7 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_RE_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_PREFIXOS_CAMINHO_SOLTO = ("/", "./", "../", "instancias/", "referencias/", "verbetes/")
_TETO_TOKEN_BYTES = 16_384
_FD_STDERR = 2
_MIN_ASCII_IMPRIMIVEL = 32
_MIN_PARTES_CHAVE_CAMINHO = 2
_MIN_POS_COM_CLASSE = 2


def desligar_core_dump() -> None:
    """Zera RLIMIT_CORE no início do processo para impedir despejo de memória."""
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (OSError, ValueError):
        pass


def _erro_token_invalido(onde: str, recebido: str, cura: str) -> RecusaEscrita:
    return RecusaEscrita(
        ErroEscrita(
            saida=4,
            codigo="token-invalido",
            onde=onde,
            recebido=recebido,
            regra="token deve chegar por descritor herdado válido em UTF-8",
            cura=cura,
            proximo="",
        )
    )


def ler_token_descritor(var_fd: str = "PF_TOKEN_FD") -> str:
    """Lê o token exclusivamente de descritor herdado, nunca de variável de ambiente."""
    bruto_fd = (os.environ.get(var_fd) or "").strip()
    if not bruto_fd:
        return ""
    try:
        fd = int(bruto_fd)
    except ValueError as exc:
        raise _erro_token_invalido(
            var_fd, bruto_fd, "informe um número de descritor herdado válido"
        ) from exc
    if fd <= _FD_STDERR:
        raise _erro_token_invalido(
            var_fd, bruto_fd, "descritor de token deve ser maior que 2"
        )
    try:
        partes: list[bytes] = []
        total = 0
        while True:
            bloco = os.read(fd, 4096)
            if not bloco:
                break
            total += len(bloco)
            if total > _TETO_TOKEN_BYTES:
                raise _erro_token_invalido(
                    var_fd,
                    f">{_TETO_TOKEN_BYTES} bytes",
                    f"reduza o token para no máximo {_TETO_TOKEN_BYTES} bytes",
                )
            partes.append(bloco)
        return b"".join(partes).decode("utf-8", errors="strict").strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise _erro_token_invalido(
            var_fd, str(exc), "envie token UTF-8 íntegro pelo descritor herdado"
        ) from exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def gerar_uuidv7() -> str:
    """Cunha um UUIDv7 canônico em minúsculas (RFC 9562)."""
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    valor = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    h = f"{valor:032x}"
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def eh_uuidv7(valor: str) -> bool:
    """Verifica se a string é um UUIDv7 canônico em minúsculas."""
    return bool(_RE_UUIDV7.match(valor))


def ler_stdin_limitado(fluxo: BinaryIO, teto_bytes: int) -> bytes:
    """Lê bytes de stdin até `teto_bytes`, recusando excesso antes de carregar tudo."""
    dados = fluxo.read(teto_bytes + 1)
    if len(dados) > teto_bytes:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="tamanho-excedido",
                onde="stdin",
                recebido=f">{teto_bytes} bytes",
                regra=f"entrada não pode exceder {teto_bytes} bytes",
                cura="reduza o conteúdo ou divida a alteração em partes menores",
                proximo="",
            )
        )
    return dados


def decodificar_utf8_estrito(dados: bytes, *, onde: str = "stdin") -> str:
    """Decodifica UTF-8 estrito, recusando byte nulo e sequência inválida."""
    if b"\x00" in dados:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="arquivo-binario",
                onde=onde,
                recebido=f"{len(dados)} bytes com NUL",
                regra="o ato escrever aceita apenas texto UTF-8 sem byte nulo",
                cura="envie conteúdo textual sem bytes NUL",
                proximo="",
            )
        )
    try:
        return dados.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="encoding-invalido",
                onde=onde,
                recebido=f"byte inválido na posição {exc.start}",
                regra="o conteúdo deve ser UTF-8 estrito válido",
                cura="converta a entrada para UTF-8 válido antes de enviar",
                proximo="",
            )
        ) from exc


_RE_PARCIAL_ENVELOPE = re.compile(r'"(?:parcial|com_perda)"\s*:\s*true\b')


def detectar_leitura_parcial(texto: str) -> bool:
    """Detecta marca de leitura fatiada no cabeçalho ou em envelope JSON de topo."""
    if not texto:
        return False
    primeira = texto.splitlines()[0].strip()
    if primeira.startswith("# parte ") or primeira == "# parte":
        return True
    limpo = texto.strip()
    if not (limpo.startswith("{") and limpo.endswith("}")):
        return False
    return bool(_RE_PARCIAL_ENVELOPE.search(limpo))


def parsear_trecho(texto: str) -> TrocaTrecho:
    """Converte o JSON de entrada do formato `--formato trecho` em TrocaTrecho."""
    try:
        obj = json.loads(texto)
    except ValueError as exc:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-invalido",
                onde="stdin",
                recebido=str(exc),
                regra='formato trecho exige JSON {"antes", "depois", "todos"?}',
                cura='envie um objeto JSON com "antes" não vazio e "depois" em texto',
                proximo="",
            )
        ) from exc
    if not isinstance(obj, dict):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-invalido",
                onde="stdin",
                recebido=type(obj).__name__,
                regra='formato trecho exige objeto JSON {"antes", "depois"}',
                cura="envie um objeto JSON em vez de lista ou escalar",
                proximo="",
            )
        )
    antes = obj.get("antes")
    depois = obj.get("depois")
    todos = obj.get("todos", False)
    if (
        not isinstance(antes, str)
        or not antes
        or not isinstance(depois, str)
        or not isinstance(todos, bool)
    ):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-invalido",
                onde="stdin",
                recebido=str(list(obj.keys())),
                regra='"antes" deve ser string não vazia, "depois" string e "todos" booleano',
                cura='informe {"antes": "<texto>", "depois": "<texto>"}',
                proximo="",
            )
        )
    return TrocaTrecho(antes=antes, depois=depois, todos=todos)


def _limpar_cabecalho_diff(linha: str, prefixo_strip: str) -> str:
    caminho = linha[4:].strip().split("\t")[0]
    if caminho == "/dev/null":
        return caminho
    return caminho.removeprefix(prefixo_strip)


def _contar_linha_hunk(linha: str) -> tuple[int, int]:
    if linha.startswith("\\"):
        return 0, 0
    if linha.startswith(" "):
        return 1, 1
    if linha.startswith("-"):
        return 1, 0
    if linha.startswith("+"):
        return 0, 1
    raise RecusaEscrita(
        ErroEscrita(
            saida=2,
            codigo="patch-invalido",
            onde="stdin",
            recebido=linha.strip(),
            regra="toda linha de hunk deve iniciar com ' ', '-', '+' ou '\\\\'",
            cura="corrija as linhas internas do hunk",
            proximo="",
        )
    )


def _consumir_hunk(linhas: list[str], inicio: int) -> tuple[HunkPatch, int]:
    cab = linhas[inicio]
    m = _RE_HUNK.match(cab)
    if not m:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-invalido",
                onde="stdin",
                recebido=cab.strip(),
                regra="cabeçalho de hunk deve seguir @@ -l,c +l,c @@",
                cura="gere um unified diff válido",
                proximo="",
            )
        )
    old_start = int(m.group(1))
    old_count = int(m.group(2)) if m.group(2) is not None else 1
    new_start = int(m.group(3))
    new_count = int(m.group(4)) if m.group(4) is not None else 1
    idx = inicio + 1
    vistos_old, vistos_new = 0, 0
    corpo: list[str] = []
    while idx < len(linhas) and not linhas[idx].startswith(("@@ ", "--- ")):
        d_old, d_new = _contar_linha_hunk(linhas[idx])
        corpo.append(linhas[idx])
        vistos_old += d_old
        vistos_new += d_new
        idx += 1
    if not corpo or vistos_old != old_count or vistos_new != new_count:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-invalido",
                onde="stdin",
                recebido=f"esperado (-{old_count}, +{new_count}), lido (-{vistos_old}, +{vistos_new})",
                regra="a contagem de linhas do hunk deve bater exatamente com o cabeçalho",
                cura="gere novamente o unified diff sem truncar hunks",
                proximo="",
            )
        )
    return HunkPatch(old_start, old_count, new_start, new_count, tuple(corpo)), idx


def _coletar_hunks(linhas: list[str], inicio: int) -> tuple[HunkPatch, ...]:
    idx = inicio
    hunks: list[HunkPatch] = []
    while idx < len(linhas):
        if not linhas[idx].startswith("@@"):
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="patch-invalido",
                    onde="stdin",
                    recebido=linhas[idx].strip(),
                    regra="linha fora de hunk no unified diff",
                    cura="envie apenas cabeçalhos ---/+++ e hunks @@ válidos",
                    proximo="",
                )
            )
        hunk, idx = _consumir_hunk(linhas, idx)
        hunks.append(hunk)
    if not hunks:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-invalido",
                onde="stdin",
                recebido="0 hunks",
                regra="patch deve conter ao menos um hunk válido",
                cura="adicione ao menos um hunk @@ -l,c +l,c @@",
                proximo="",
            )
        )
    return tuple(hunks)


def parsear_patch_estrito(texto: str) -> PatchEstrito:
    """Converte unified diff de um único arquivo em PatchEstrito sem tolerar truncamento."""
    linhas = texto.splitlines(keepends=True)
    cabecalhos = [
        i
        for i in range(len(linhas) - 1)
        if linhas[i].startswith("--- ") and linhas[i + 1].startswith("+++ ")
    ]
    if not cabecalhos:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-invalido",
                onde="stdin",
                recebido="sem cabeçalhos --- / +++",
                regra="formato patch exige unified diff com cabeçalhos --- e +++",
                cura="envie um unified diff completo para o arquivo alvo",
                proximo="",
            )
        )
    if len(cabecalhos) > 1:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-multi-alvo",
                onde="stdin",
                recebido=f"{len(cabecalhos)} arquivos no diff",
                regra="formato patch aceita exatamente um arquivo por chamada",
                cura="envie um patch por arquivo alvo",
                proximo="",
            )
        )
    pos = cabecalhos[0]
    old_path = _limpar_cabecalho_diff(linhas[pos], "a/")
    new_path = _limpar_cabecalho_diff(linhas[pos + 1], "b/")
    if new_path == "/dev/null":
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="remocao-nao-suportada",
                onde="stdin",
                recebido="+++ /dev/null",
                regra="patch não remove arquivos",
                cura="use o ato apagar ou operação própria do verbo",
                proximo="",
            )
        )
    return PatchEstrito(
        old_path=old_path, new_path=new_path, hunks=_coletar_hunks(linhas, pos + 2)
    )


def _separar_flags(
    verbo: str, argv: Sequence[str]
) -> tuple[list[str], dict[str, str], set[str]]:
    pos: list[str] = []
    valores: dict[str, str] = {}
    bools: set[str] = set()
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _VARIANTES_FLAG:
            limpos = " ".join(a for a in argv if a not in _VARIANTES_FLAG)
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="variante-nao-executa",
                    onde="args",
                    recebido=arg,
                    regra="flags de simulação são variantes e não executam",
                    cura="use a forma canônica ensaiar",
                    proximo=f"{verbo} ensaiar {limpos}".strip(),
                )
            )
        if arg in _FLAGS_COM_VALOR:
            if i + 1 >= len(argv):
                raise RecusaEscrita(
                    ErroEscrita(
                        saida=2,
                        codigo="flag-desconhecida",
                        onde="args",
                        recebido=arg,
                        regra=f"flag {arg} exige valor",
                        cura=f"informe um valor após {arg}",
                        proximo="",
                    )
                )
            valores[arg] = argv[i + 1]
            i += 2
        elif arg in _FLAGS_SEM_VALOR:
            bools.add(arg)
            i += 1
        elif arg.startswith("-"):
            raise RecusaEscrita(
                ErroEscrita(
                    saida=2,
                    codigo="flag-desconhecida",
                    onde="args",
                    recebido=arg,
                    regra="flag não reconhecida pelo ato escrever",
                    cura="use apenas --pedido, --documento, --formato, --permitir-vazio ou --json",
                    proximo="",
                )
            )
        else:
            pos.append(arg)
            i += 1
    return pos, valores, bools


def _sugerir_chave_de_caminho(caminho: str) -> str:
    limpo = caminho.removeprefix("./").lstrip("/")
    for pref in ("instancias/", "referencias/instancias/", "verbetes/"):
        if limpo.startswith(pref):
            partes = limpo[len(pref) :].split("/")
            if len(partes) >= _MIN_PARTES_CHAVE_CAMINHO:
                slug = partes[-1].removesuffix(".md")
                return f"{partes[0]}:{slug}"
    return "<classe>:<slug>"


def _validar_chave(
    verbo: str, forma: str, chave: str, *, exige_objeto_casa: bool
) -> str:
    if not chave or any(ord(c) < _MIN_ASCII_IMPRIMIVEL for c in chave):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="chave",
                recebido=chave,
                regra="chave obrigatória sem caracteres de controle",
                cura="informe a chave do alvo",
                proximo="",
            )
        )
    parece_caminho = chave.startswith(_PREFIXOS_CAMINHO_SOLTO) or (
        exige_objeto_casa and ("/" in chave or chave.endswith((".md", ".yaml", ".json")))
    )
    if parece_caminho and (exige_objeto_casa or ":" not in chave):
        chave_sug = _sugerir_chave_de_caminho(chave)
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="caminho-solto-recusado",
                onde="chave",
                recebido=chave,
                regra="objetos da casa usam chave <classe>:<slug>, nunca caminho físico",
                cura="substitua o caminho físico pela chave do objeto",
                proximo=f"{verbo} {forma} {chave_sug}",
            )
        )
    if exige_objeto_casa:
        if ":" not in chave:
            return f"shape:{chave}"
        if chave.endswith(":"):
            return f"shape:{chave[:-1]}"
    return chave


def _validar_forma_inicial(verbo: str, pos: list[str]) -> tuple[str, str | None, list[str]]:
    if not pos:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="args",
                recebido="",
                regra="informe <forma> [<classe>] <chave> [<versao>]",
                cura="forneça a forma e a chave do alvo",
                proximo="",
            )
        )
    forma, resto = pos[0], pos[1:]
    if forma in _VARIANTES_FORMA:
        canon = _VARIANTES_FORMA[forma]
        proximo = (
            f"{verbo} ler {' '.join(resto)}".strip()
            if canon == "trocar" and len(resto) <= _MIN_POS_COM_CLASSE
            else f"{verbo} {canon} {' '.join(resto)}".strip()
        )
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="variante-nao-executa",
                onde="forma",
                recebido=forma,
                regra="palavras variantes não executam na escrita",
                cura=f"use a forma canônica {canon}",
                proximo=proximo,
            )
        )
    if forma not in FORMAS_ESCRITA:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="ato-nao-aceito",
                onde="forma",
                recebido=forma,
                regra="forma fora do catálogo fechado do ato escrever",
                cura="use gravar, criar, trocar, retirar, restaurar ou ensaiar",
                proximo="",
            )
        )
    if forma != "ensaiar":
        return forma, None, resto
    if not resto or resto[0] not in FORMAS_ENSAIAR:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="forma-fora-do-regime",
                onde="forma_ensaiada",
                recebido=resto[0] if resto else "",
                regra="ensaiar exige forma-alvo criar, trocar ou recompor",
                cura="informe a forma a ensaiar logo após ensaiar",
                proximo="",
            )
        )
    return forma, resto[0], resto[1:]


def _extrair_posicionais(
    verbo: str, pos: list[str], *, classe_unica: str | None
) -> tuple[str, str | None, str | None, str, str | None]:
    forma, forma_ensaiada, resto = _validar_forma_inicial(verbo, pos)
    if not resto:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="chave-invalida",
                onde="chave",
                recebido="",
                regra="chave do alvo é obrigatória",
                cura="informe a chave após a forma",
                proximo="",
            )
        )
    if classe_unica is not None:
        return forma, forma_ensaiada, classe_unica, resto[0], (resto[1] if len(resto) > 1 else None)
    if (
        len(resto) >= _MIN_POS_COM_CLASSE
        and ":" not in resto[0]
        and not resto[0].startswith(_PREFIXOS_CAMINHO_SOLTO)
    ):
        versao = resto[2] if len(resto) > _MIN_POS_COM_CLASSE else None
        return forma, forma_ensaiada, resto[0], resto[1], versao
    return forma, forma_ensaiada, None, resto[0], (resto[1] if len(resto) > 1 else None)


def _validar_flags_e_opcoes(
    forma: str, valores: dict[str, str], bools: set[str]
) -> tuple[str, str | None, str, bool, bool]:
    pedido_id = valores.get("--pedido") or gerar_uuidv7()
    if not eh_uuidv7(pedido_id):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="pedido-invalido",
                onde="--pedido",
                recebido=pedido_id,
                regra="--pedido deve ser um UUIDv7 canônico em minúsculas",
                cura="omita --pedido ou informe um UUIDv7 válido",
                proximo="",
            )
        )
    documento = valores.get("--documento")
    if documento is not None and documento not in DOCUMENTOS_ALVO:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conflito-de-opcoes",
                onde="--documento",
                recebido=documento,
                regra="--documento aceita apenas golden ou referencia",
                cura="passe --documento golden ou --documento referencia",
                proximo="",
            )
        )
    formato = valores.get("--formato", "inteiro")
    if formato not in FORMATOS_CONTEUDO or (formato != "inteiro" and forma != "gravar"):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conflito-de-opcoes",
                onde="--formato",
                recebido=f"{forma} --formato {formato}",
                regra="--formato trecho e patch valem apenas para gravar componente na bancada",
                cura="use inteiro ou troque a forma para gravar",
                proximo="",
            )
        )
    permitir_vazio = "--permitir-vazio" in bools
    if permitir_vazio and (forma != "gravar" or formato != "inteiro"):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conflito-de-opcoes",
                onde="--permitir-vazio",
                recebido=f"{forma}/{formato}",
                regra="--permitir-vazio vale apenas para gravar no formato inteiro",
                cura="remova --permitir-vazio",
                proximo="",
            )
        )
    return pedido_id, documento, formato, permitir_vazio, "--json" in bools


def _converter_conteudo(
    forma: str,
    formato: str,
    stdin_bytes: bytes | None,
    teto_bytes: int,
    *,
    permitir_vazio: bool,
) -> tuple[str | None, TrocaTrecho | None, PatchEstrito | None]:
    if forma in ("retirar", "restaurar"):
        return None, None, None
    bruto = b"" if stdin_bytes is None else stdin_bytes
    if len(bruto) > teto_bytes:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="tamanho-excedido",
                onde="stdin",
                recebido=f"{len(bruto)} bytes",
                regra=f"entrada excede o teto de {teto_bytes} bytes",
                cura="reduza o conteúdo abaixo do teto configurado",
                proximo="",
            )
        )
    texto = decodificar_utf8_estrito(bruto, onde="stdin")
    if not texto:
        if permitir_vazio:
            return "", None, None
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conteudo-vazio",
                onde="stdin",
                recebido="0 bytes",
                regra="entrada vazia é recusada para impedir truncamento acidental",
                cura="envie o conteúdo em stdin ou passe --permitir-vazio em arquivo de código",
                proximo="",
            )
        )
    if detectar_leitura_parcial(texto):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="conteudo-parcial",
                onde="stdin",
                recebido=texto.splitlines()[0],
                regra="conteúdo marcado como leitura fatiada não pode ser gravado",
                cura="leia o objeto inteiro antes de gravar",
                proximo="",
            )
        )
    if formato == "trecho":
        return None, parsear_trecho(texto), None
    if formato == "patch":
        return None, None, parsear_patch_estrito(texto)
    return texto, None, None


def parsear_pedido(
    verbo: str,
    argv: Sequence[str],
    stdin_bytes: bytes | None,
    *,
    politica: PoliticaEscrita,
    contexto: ContextoEscrita | None = None,
) -> PedidoEscrita:
    """Executa a conversão de borda completa e devolve PedidoEscrita imutável."""
    ctx = ContextoEscrita(verbo=verbo) if contexto is None else contexto
    pos, valores, bools = _separar_flags(verbo, argv)
    forma, forma_ensaiada, classe, chave_bruta, versao = _extrair_posicionais(
        verbo, pos, classe_unica=ctx.classe_unica
    )
    pedido_id, documento, formato, permitir_vazio, como_json = _validar_flags_e_opcoes(
        forma, valores, bools
    )
    chave = _validar_chave(verbo, forma, chave_bruta, exige_objeto_casa=ctx.exige_objeto_casa)
    conteudo, trecho, patch = _converter_conteudo(
        forma,
        formato,
        stdin_bytes,
        politica.entrada_max_bytes,
        permitir_vazio=permitir_vazio,
    )
    return PedidoEscrita(
        verbo=verbo,
        forma=forma,
        classe=classe,
        chave=chave,
        versao=versao,
        pedido=pedido_id,
        formato=formato,
        documento=documento,
        permitir_vazio=permitir_vazio,
        como_json=como_json,
        forma_ensaiada=forma_ensaiada,
        conteudo=conteudo,
        trecho=trecho,
        patch=patch,
        contexto=ctx,
    )
