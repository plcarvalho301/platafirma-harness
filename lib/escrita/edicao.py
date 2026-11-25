"""Transformadores puros em memória para edição por trecho e patch estrito."""
from __future__ import annotations

from dataclasses import dataclass

from .tipos import ErroEscrita, HunkPatch, PatchEstrito, RecusaEscrita, TrocaTrecho


@dataclass(frozen=True)
class ResultadoEdicao:
    """Resultado imutável de um transformador puro em memória."""

    texto: str
    ocorrencias: int | None = None
    hunks_aplicados: int | None = None


def _recuo_linha(linha: str) -> str:
    idx = 0
    while idx < len(linha) and linha[idx] in (" ", "\t"):
        idx += 1
    return linha[:idx]


def _recuo_comum(linhas: list[str]) -> str:
    nao_vazias = [ln for ln in linhas if ln.strip()]
    if not nao_vazias:
        return ""
    recuos = [_recuo_linha(ln) for ln in nao_vazias]
    comum = recuos[0]
    for r in recuos[1:]:
        n = min(len(comum), len(r))
        i = 0
        while i < n and comum[i] == r[i]:
            i += 1
        comum = comum[:i]
    return comum


def _casar_janela_linhas(
    janela: list[str], antes_sem_recuo: list[str]
) -> str | None:
    recuo_alvo: str | None = None
    for linha_arq, linha_ref in zip(janela, antes_sem_recuo, strict=True):
        if not linha_ref.strip():
            if linha_arq.strip():
                return None
            continue
        if not linha_arq.endswith(linha_ref):
            return None
        prefixo = linha_arq[: len(linha_arq) - len(linha_ref)]
        if prefixo.strip():
            return None
        if recuo_alvo is None:
            recuo_alvo = prefixo
        elif prefixo != recuo_alvo:
            return None
    return "" if recuo_alvo is None else recuo_alvo


def _reindentar_bloco(
    depois_linhas: list[str], recuo_antes: str, recuo_alvo: str
) -> list[str]:
    saida: list[str] = []
    for ln in depois_linhas:
        if not ln.strip():
            saida.append("")
            continue
        corpo = ln[len(recuo_antes) :] if recuo_antes and ln.startswith(recuo_antes) else ln
        saida.append(recuo_alvo + corpo)
    return saida


def _aplicar_trecho_linhas_inteiras(
    atual: str, trecho: TrocaTrecho
) -> ResultadoEdicao:
    sep = "\r\n" if "\r\n" in atual else "\n"
    termina_com_nl = atual.endswith(("\r\n", "\n"))
    linhas_arq = atual.splitlines()
    antes_linhas = trecho.antes.splitlines()
    recuo_antes = _recuo_comum(antes_linhas)
    antes_sem_recuo = [
        ln[len(recuo_antes) :] if ln.strip() else "" for ln in antes_linhas
    ]
    tam = len(antes_sem_recuo)
    casamentos: list[tuple[int, str]] = []
    i = 0
    while i <= len(linhas_arq) - tam:
        recuo = _casar_janela_linhas(linhas_arq[i : i + tam], antes_sem_recuo)
        if recuo is not None:
            casamentos.append((i, recuo))
            i += tam
        else:
            i += 1
    if not casamentos:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-nao-encontrado",
                onde="trecho.antes",
                recebido=trecho.antes,
                regra="trecho deve casar literalmente ou em sequência contígua de linhas inteiras",
                cura="confira o conteúdo vigente do arquivo antes de repetir",
                proximo="",
            )
        )
    if len(casamentos) > 1 and not trecho.todos:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-ambiguo",
                onde="trecho.antes",
                recebido=f"{len(casamentos)} ocorrências",
                regra="múltiplas ocorrências exigem contexto maior ou todos=true",
                cura="amplie o contexto de antes ou passe todos=true",
                proximo="",
            )
        )
    depois_linhas = trecho.depois.splitlines()
    novas = list(linhas_arq)
    for pos, recuo_alvo in reversed(casamentos):
        bloco = _reindentar_bloco(depois_linhas, recuo_antes, recuo_alvo)
        novas[pos : pos + tam] = bloco
    texto = sep.join(novas)
    if termina_com_nl and novas:
        texto += sep
    return ResultadoEdicao(texto=texto, ocorrencias=len(casamentos))


def aplicar_trecho(atual: str, trecho: TrocaTrecho) -> ResultadoEdicao:
    """Aplica TrocaTrecho: literal exato em linha única; linhas inteiras em multilinha."""
    if "\n" in trecho.antes or "\r" in trecho.antes:
        return _aplicar_trecho_linhas_inteiras(atual, trecho)
    contagem = atual.count(trecho.antes)
    if contagem == 1:
        return ResultadoEdicao(
            texto=atual.replace(trecho.antes, trecho.depois, 1), ocorrencias=1
        )
    if contagem > 1:
        if trecho.todos:
            return ResultadoEdicao(
                texto=atual.replace(trecho.antes, trecho.depois), ocorrencias=contagem
            )
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="trecho-ambiguo",
                onde="trecho.antes",
                recebido=f"{contagem} ocorrências",
                regra="múltiplas ocorrências exigem contexto maior ou todos=true",
                cura="amplie o contexto de antes ou passe todos=true",
                proximo="",
            )
        )
    return _aplicar_trecho_linhas_inteiras(atual, trecho)


def _extrair_esperadas_e_novas(hunk: HunkPatch) -> tuple[list[str], list[str]]:
    esperadas: list[str] = []
    novas: list[str] = []
    ultimo = ""
    for hl in hunk.linhas:
        if hl.startswith("\\"):
            if ultimo in (" ", "-") and esperadas:
                esperadas[-1] = esperadas[-1].rstrip("\r\n")
            if ultimo in (" ", "+") and novas:
                novas[-1] = novas[-1].rstrip("\r\n")
            continue
        tag, corpo = hl[0], hl[1:]
        ultimo = tag
        if tag in (" ", "-"):
            esperadas.append(corpo)
        if tag in (" ", "+"):
            novas.append(corpo)
    return esperadas, novas


def _validar_cabecalhos_patch(chave_alvo: str, patch: PatchEstrito) -> None:
    esperado = chave_alvo.split(":", 1)[1] if ":" in chave_alvo else chave_alvo
    if patch.new_path != esperado or patch.old_path not in (esperado, "/dev/null"):
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-multi-alvo",
                onde="patch",
                recebido=f"--- {patch.old_path} / +++ {patch.new_path}",
                regra=f"os cabeçalhos do patch devem nomear exclusivamente {esperado}",
                cura="alinhe os cabeçalhos --- e +++ com o caminho da chave alvo",
                proximo="",
            )
        )


def aplicar_patch(
    atual: str, chave_alvo: str, patch: PatchEstrito
) -> ResultadoEdicao:
    """Aplica PatchEstrito nas posições exatas declaradas, sem busca aproximada."""
    _validar_cabecalhos_patch(chave_alvo, patch)
    novo_arquivo = patch.old_path == "/dev/null"
    linhas = [] if (novo_arquivo and atual == "") else atual.splitlines(keepends=True)
    offset = 0
    for hunk in patch.hunks:
        esperadas, novas = _extrair_esperadas_e_novas(hunk)
        if not esperadas:
            idx = 0 if novo_arquivo else max(0, hunk.old_start - 1 + offset)
            if idx > len(linhas):
                raise RecusaEscrita(
                    ErroEscrita(
                        saida=2,
                        codigo="hunk-nao-casa",
                        onde="patch",
                        recebido=f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@",
                        regra="posição inicial do hunk está fora do arquivo",
                        cura="gere o patch contra a versão vigente do arquivo",
                        proximo="",
                    )
                )
        else:
            idx = hunk.old_start - 1 + offset
            if idx < 0 or idx + len(esperadas) > len(linhas) or linhas[idx : idx + len(esperadas)] != esperadas:
                raise RecusaEscrita(
                    ErroEscrita(
                        saida=2,
                        codigo="hunk-nao-casa",
                        onde="patch",
                        recebido=f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@",
                        regra="hunk deve casar na linha exata declarada, sem busca aproximada",
                        cura="leia a versão vigente e regenere o patch",
                        proximo="",
                    )
                )
        linhas[idx : idx + len(esperadas)] = novas
        offset += len(novas) - len(esperadas)

    resultado = "".join(linhas)
    if resultado == atual:
        raise RecusaEscrita(
            ErroEscrita(
                saida=2,
                codigo="patch-sem-efeito",
                onde="patch",
                recebido=chave_alvo,
                regra="patch deve alterar o conteúdo do arquivo",
                cura="envie um patch com alteração efetiva",
                proximo="",
            )
        )
    return ResultadoEdicao(texto=resultado, hunks_aplicados=len(patch.hunks))
