#!/usr/bin/env python3
"""Prova dos criterios 4, 5 e 15 — formatacao e fatiamento (card 458).

Roda DENTRO da imagem da recepcao, que e onde o Markdown esta pinado:

    docker run --rm -v "$PWD/testes:/testes:ro" --entrypoint python \\
      platafirma/chat-recepcao:local /testes/prova-formata.py

Sem pytest de proposito: a imagem da recepcao nao carrega dependencia de teste,
e assert de stdlib prova o mesmo. Sai 0 se tudo passou, 1 na primeira falha.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/chat")

import formata  # noqa: E402

TABELA = """Segue o quadro:

| cadeira | alias |
|---|---|
| TI | Oswaldo Aranha |
| IA | Elias Elefante |

E uma lista:

- primeiro
- segundo

1. um
2. dois

```python
def f():
    return 1
```
"""

falhas = []


def prova(nome):
    def marca(fn):
        try:
            fn()
            print(f"  ok   {nome}")
        except AssertionError as erro:
            falhas.append(nome)
            print(f"  FALHA {nome}: {erro}")
        return fn
    return marca


@prova("criterio 4 — tabela vira <table>, nunca markdown embrulhado em <pre>")
def _():
    html = formata.para_html(TABELA)
    assert "<table>" in html, "tabela nao virou <table>"
    assert "<td>Oswaldo Aranha</td>" in html, "celula nao saiu como <td>"
    # O defeito medido (openclaw #29377) e a resposta INTEIRA embrulhada em
    # <pre><code>. O <pre> do bloco de codigo e legitimo; o que reprova e a
    # tabela dentro de um.
    antes_da_tabela = html.split("<table>")[0]
    assert antes_da_tabela.count("<pre>") == 0, "a tabela ficou dentro de <pre>"


@prova("criterio 4 — code block e listas")
def _():
    html = formata.para_html(TABELA)
    assert "<pre><code" in html, "bloco de codigo nao virou <pre><code>"
    assert 'class="language-python"' in html, "linguagem do fence se perdeu"
    assert "<ul>" in html and "<ol>" in html, "lista nao virou <ul>/<ol>"


@prova("body carrega o markdown cru, formatted_body o HTML")
def _():
    c = formata.conteudo("**oi**")
    assert c["body"] == "**oi**", "body deveria ser o markdown cru"
    assert c["formatted_body"] == "<p><strong>oi</strong></p>", c["formatted_body"]
    assert c["format"] == "org.matrix.custom.html"


@prova("criterio 5 — resposta longa chega inteira, sem perder um byte")
def _():
    texto = "\n\n".join(f"Paragrafo {i} — " + "palavra " * 60 for i in range(400))
    partes = formata.fatia(texto)
    assert len(partes) > 1, "resposta de ~200 KB deveria fatiar"
    assert "\n".join(partes) == texto, "o texto remontado nao bate com o original"


@prova("criterio 5 — nenhuma parte estoura o orcamento")
def _():
    texto = "\n\n".join(f"Paragrafo {i} — " + "palavra " * 60 for i in range(400))
    for i, p in enumerate(formata.fatia(texto)):
        c = formata.custo(p)
        assert c <= formata.ORCAMENTO, f"parte {i} custou {c} bytes"


@prova("criterio 5 — corte so em quebra de linha")
def _():
    texto = "\n".join(f"linha {i} com algum texto para encher" for i in range(4000))
    partes = formata.fatia(texto)
    assert len(partes) > 1
    for p in partes:
        assert p.startswith("linha "), f"parte comecou no meio de uma linha: {p[:40]!r}"
        assert p.rstrip().endswith("encher"), "parte terminou no meio de uma linha"


@prova("criterio 5 — fence nunca fica pela metade")
def _():
    bloco = "```python\n" + "\n".join(f"    x{i} = {i}" for i in range(200)) + "\n```"
    texto = "\n\n".join([f"Paragrafo {i} — " + "palavra " * 60 for i in range(300)] + [bloco])
    for p in formata.fatia(texto):
        assert p.count("```") % 2 == 0, "parte com cerca de codigo impar"


@prova("criterio 5 — bloco maior que o orcamento fecha e reabre com a mesma lingua")
def _():
    miolo = "\n".join(f"linha {i} de codigo com bastante coisa dentro" for i in range(3000))
    partes = formata.fatia(f"```python\n{miolo}\n```")
    assert len(partes) > 1, "bloco gigante deveria partir"
    for p in partes:
        assert p.startswith("```python"), f"pedaco reabriu sem a lingua: {p[:20]!r}"
        assert p.rstrip().endswith("```"), "pedaco nao fechou a cerca"
        assert formata.custo(p) <= formata.ORCAMENTO


@prova("tabela e atomica: nao parte entre cabecalho e corpo")
def _():
    linhas = ["| a | b |", "|---|---|"] + [f"| v{i} | w{i} |" for i in range(20)]
    texto = "\n\n".join(["encheu " * 200] * 100 + ["\n".join(linhas)])
    for p in formata.fatia(texto):
        if "| v0 |" in p:
            assert "|---|---|" in p, "corpo da tabela se separou do cabecalho"


@prova("marcador (i/N) so quando ha mais de uma parte")
def _():
    um = formata.eventos("resposta curta")
    assert len(um) == 1 and "(1/1)" not in um[0]["body"], "numerou parte unica"
    texto = "\n\n".join(f"Paragrafo {i} — " + "palavra " * 60 for i in range(400))
    varios = formata.eventos(texto)
    assert varios[0]["body"].endswith(f"(1/{len(varios)})"), "faltou marcador na primeira"
    assert varios[-1]["body"].endswith(f"({len(varios)}/{len(varios)})"), "faltou na ultima"
    for e in varios:
        assert formata.custo(e["body"]) <= formata.TETO_EVENTO


@prova("resposta vazia nao produz evento")
def _():
    assert formata.fatia("   \n\n ") == []
    assert formata.eventos("") == []


if __name__ == "__main__":
    print(f"prova de formatacao e fatiamento — orcamento {formata.ORCAMENTO} bytes")
    if falhas:
        print(f"\n{len(falhas)} falha(s): {', '.join(falhas)}")
        sys.exit(1)
    print("\ntudo passou")
