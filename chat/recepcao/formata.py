#!/usr/bin/env python3
"""Markdown da cadeira -> evento Matrix: HTML de verdade, e fatiado sem partir bloco.

Cobre tres criterios de aceite da minuta 0002, e cada um veio de um defeito
medido em campo (openclaw #29377, hermes-agent #45421, chunkMode):

  4 — tabela, code block e lista renderizam COMO TAL no cliente movel. A
      armadilha nomeada e o emissor que embrulha a resposta inteira em
      <pre><code>: o cliente exibe markdown cru monoespacado e passa por
      "formatado". Aqui o markdown vira HTML no `formatted_body`, e o markdown
      cru fica no `body`, que e o campo do cliente que nao renderiza HTML.
  5 — resposta acima do teto chega inteira, cortada SO em quebra de linha fora
      de bloco. Cortar por contagem de caracteres parte fence no meio e destroi
      as duas metades.
 15 — as N partes chegam em ordem. A ordem e do receptor (envio serializado,
      esperando o event_id de cada parte); daqui sai so a divisao.

O ORCAMENTO e medido no JSON serializado do conteudo — `body` e
`formatted_body` juntos, como o card manda — e nao no tamanho do texto. O teto
de 65536 e do evento inteiro, e o HTML infla o que o markdown comprime: uma
tabela de 400 bytes vira 1,4 KB de <table>. Medir o markdown seria medir a
coisa errada e estourar em tabela grande, que e justo o que a cadeira escreve.
"""

from __future__ import annotations

import json
import re

import markdown

# Teto de evento da spec (Client-Server API >= v1.4). Nao e o nosso orcamento:
# o evento carrega mais que o conteudo (remetente, sala, assinatura, unsigned),
# e o teto vale para o PDU inteiro.
TETO_EVENTO = 65536
# ~40 KiB, o alvo declarado por claudinho-TI na minuta. A folga ate o teto paga
# o envelope do evento e a variacao do proprio homeserver.
ORCAMENTO = 40960
# Marcador (i/N) entra depois do empacotamento, quando N ja e conhecido. A
# reserva evita que ele estoure a parte que acabou de caber justa.
MARGEM_MARCADOR = 64

EXTENSOES = ["tables", "fenced_code", "sane_lists"]

_FENCE = re.compile(r"^\s*(```|~~~)(.*)$")
_SEPARADOR_TABELA = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")


def para_html(md: str) -> str:
    """Markdown -> HTML no subconjunto que o Matrix aceita.

    Sem codehilite de proposito: ele emite <span style=...> por token, o
    sanitizer do cliente come o style e sobra sopa de span. `fenced_code` puro
    emite <pre><code class="language-x">, que a spec permite e o cliente movel
    renderiza como bloco.
    """
    return markdown.markdown(md, extensions=EXTENSOES, output_format="html")


def conteudo(md: str, msgtype: str = "m.text") -> dict:
    """Conteudo do evento. O markdown cru fica no `body` — e o que o cliente
    sem HTML mostra, e e o que o `notification` do celular usa."""
    return {
        "msgtype": msgtype,
        "body": md,
        "format": "org.matrix.custom.html",
        "formatted_body": para_html(md),
    }


def custo(md: str, msgtype: str = "m.text") -> int:
    """Bytes do conteudo serializado — a medida que o orcamento usa."""
    return len(json.dumps(conteudo(md, msgtype), ensure_ascii=False).encode("utf-8"))


# --- unidades: o que NAO pode ser cortado no meio -------------------------


def _unidades(texto: str) -> list[str]:
    """Quebra o texto nas menores pecas que ainda podem ser cortadas entre si.

    Linha solta e a unidade normal — e o "corte so em quebra de linha" do
    criterio. Fence e tabela viram UMA unidade cada, por maior que sejam: e o
    que o card chama de bloco atomico.
    """
    linhas = texto.split("\n")
    unidades: list[str] = []
    i = 0
    while i < len(linhas):
        m = _FENCE.match(linhas[i])
        if m:
            marca = m.group(1)
            bloco = [linhas[i]]
            i += 1
            while i < len(linhas):
                bloco.append(linhas[i])
                if linhas[i].strip().startswith(marca):
                    i += 1
                    break
                i += 1
            unidades.append("\n".join(bloco))
            continue
        # Tabela: linha com barra seguida de linha separadora. Sem a separadora
        # nao e tabela markdown — e texto com barra, e corta como linha comum.
        if "|" in linhas[i] and i + 1 < len(linhas) and _SEPARADOR_TABELA.match(linhas[i + 1]):
            bloco = [linhas[i], linhas[i + 1]]
            i += 2
            while i < len(linhas) and "|" in linhas[i] and linhas[i].strip():
                bloco.append(linhas[i])
                i += 1
            unidades.append("\n".join(bloco))
            continue
        unidades.append(linhas[i])
        i += 1
    return unidades


def _lingua_do_fence(unidade: str) -> tuple[str, str]:
    m = _FENCE.match(unidade.split("\n", 1)[0])
    if not m:
        return "", ""
    return m.group(1), m.group(2).strip()


def _parte_unidade_gigante(unidade: str, orcamento: int) -> list[str]:
    """Unidade atomica maior que o orcamento inteiro — o unico caso em que o
    bloco se parte, e o card diz exatamente como: FECHA E REABRE.

    Fence: cada pedaco sai cercado com a mesma marca e a mesma linguagem, para
    cada parte renderizar como codigo em vez de a primeira abrir e a ultima
    fechar. Tabela: o cabecalho e a separadora se repetem em cada pedaco, pelo
    mesmo motivo — meia tabela sem cabecalho nao e tabela no cliente.
    """
    if custo(unidade) <= orcamento:
        return [unidade]

    marca, lingua = _lingua_do_fence(unidade)
    linhas = unidade.split("\n")

    if marca:
        miolo = linhas[1:]
        if miolo and miolo[-1].strip().startswith(marca):
            miolo = miolo[:-1]
        abre, fecha = f"{marca}{lingua}", marca
        moldura = custo(f"{abre}\n{fecha}")
    elif len(linhas) >= 2 and _SEPARADOR_TABELA.match(linhas[1]):
        cabecalho, miolo = linhas[:2], linhas[2:]
        abre, fecha = "\n".join(cabecalho), ""
        moldura = custo(abre)
    else:
        # Linha unica maior que o orcamento: nao ha quebra de linha onde cortar.
        # Corta em bruto, e e o unico corte deste modulo que nao respeita limite
        # de linha — porque nao existe limite de linha dentro dela.
        return _parte_em_bruto(unidade, orcamento)

    pedacos: list[str] = []
    atual: list[str] = []
    for linha in miolo:
        cand = atual + [linha]
        if atual and moldura + custo("\n".join(cand)) > orcamento:
            pedacos.append(atual)
            atual = [linha]
        else:
            atual = cand
    if atual:
        pedacos.append(atual)

    saida = []
    for p in pedacos:
        corpo = "\n".join(p)
        saida.append(f"{abre}\n{corpo}\n{fecha}" if fecha else f"{abre}\n{corpo}")
    return saida


def _parte_em_bruto(texto: str, orcamento: int) -> list[str]:
    passo = max(1, orcamento // 4)
    pedacos, resto = [], texto
    while resto:
        corte = passo
        while corte > 1 and custo(resto[:corte]) > orcamento:
            corte //= 2
        pedacos.append(resto[:corte])
        resto = resto[corte:]
    return pedacos


# --- empacotamento --------------------------------------------------------


def _cabe_ate(unidades: list[str], k: int, orcamento: int) -> bool:
    return custo("\n".join(unidades[:k])) <= orcamento


def _empacota(unidades: list[str], orcamento: int) -> list[str]:
    """Junta unidades ate encher a parte.

    Busca binaria pelo maior prefixo que cabe, em vez de medir a cada unidade
    somada: medir e renderizar markdown, e renderizar uma vez por linha de uma
    resposta de 40 KiB e trabalho quadratico por nada. O custo cresce com o
    numero de unidades (unidade nunca encolhe o HTML — fence e tabela ja vem
    inteiros), entao a busca binaria e valida aqui.
    """
    partes: list[str] = []
    restantes = list(unidades)
    while restantes:
        if _cabe_ate(restantes, len(restantes), orcamento):
            partes.append("\n".join(restantes))
            break
        baixo, alto = 1, len(restantes)
        while baixo < alto:
            meio = (baixo + alto + 1) // 2
            if _cabe_ate(restantes, meio, orcamento):
                baixo = meio
            else:
                alto = meio - 1
        partes.append("\n".join(restantes[:baixo]))
        restantes = restantes[baixo:]
    return partes


def fatia(texto: str, orcamento: int = ORCAMENTO) -> list[str]:
    """Divide a resposta em partes publicaveis, em ordem.

    Devolve sempre ao menos uma parte — resposta vazia vira lista vazia, e quem
    chama decide o que dizer no lugar.
    """
    texto = texto.strip("\n")
    if not texto.strip():
        return []
    util = max(512, orcamento - MARGEM_MARCADOR)
    unidades: list[str] = []
    for u in _unidades(texto):
        unidades.extend(_parte_unidade_gigante(u, util))
    return _empacota(unidades, util)


def eventos(texto: str, msgtype: str = "m.text", orcamento: int = ORCAMENTO) -> list[dict]:
    """Conteudos prontos para envio, ja com o marcador (i/N).

    Marcador so quando N > 1, como o card manda: numerar resposta de uma parte
    so e ruido em toda mensagem para cobrir o caso raro.
    """
    partes = fatia(texto, orcamento)
    total = len(partes)
    if total <= 1:
        return [conteudo(p, msgtype) for p in partes]
    return [conteudo(f"{p}\n\n({i}/{total})", msgtype) for i, p in enumerate(partes, 1)]
