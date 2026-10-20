#!/usr/bin/env python3
"""release telas — a lista de telas do menu da casca (card #3899; arq:0124 §3; comentario #3062 do #3602).

Le a declaracao unica das telas da instancia (registro/telas.json) e devolve so as telas cuja stack
esta promovida: registrada no acervo com compose (nao catalogo, nao stack de teste) e com a familia
dela servindo um `current`. A tela que sai do ar sai do menu sem ninguem mexer na lista.

    release telas [--json]

`--json` imprime `{"telas": [{"id", "rotulo", "href", "posicao", "face"}]}`, por posicao; `face` e null na
tela que nao serve face. A origem, a familia e a stack sao da instancia: a casca nao as ve. Esse formato e
PROVISORIO (o epico #3379 o confirma) e mora so aqui.

Entradas (o bin/release passa as duas primeiras; as outras sao para teste):
  PF_PROD_RAIZ            raiz da release servida (<familia>/current)
  PF_ACERVO_BIN           o verbo acervo, para ler o registro de stacks
  PF_TELAS_DECLARACAO     caminho da declaracao (padrao: registro/telas.json desta arvore)
  PF_TELAS_STACKS         arquivo JSON com o registro de stacks, no lugar de `acervo ler casa stack`

Saida: 0 lista (inclusive vazia) · 2 uso · 3 dependencia fora (declaracao ou registro ilegivel).
"""
import json
import os
import subprocess
import sys

CAMPOS_DA_CASCA = ("id", "rotulo", "href", "posicao", "face")
AQUI = os.path.dirname(os.path.realpath(__file__))
DECLARACAO = os.path.join(AQUI, "..", "..", "..", "registro", "telas.json")


def carregar_declaracao(caminho):
    """A lista de telas declaradas. Ilegivel ou fora da forma: levanta ValueError."""
    try:
        with open(caminho, encoding="utf-8") as fh:
            dado = json.load(fh)
    except (OSError, ValueError) as e:
        raise ValueError(f"declaracao das telas ilegivel em {caminho}: {type(e).__name__}") from None
    telas = dado.get("telas") if isinstance(dado, dict) else dado
    if not isinstance(telas, list) or any(not isinstance(t, dict) for t in telas):
        raise ValueError(f"declaracao das telas fora da forma em {caminho}")
    return telas


def carregar_stacks(acervo_bin):
    """{slug: stack} do registro do acervo. Fora do ar ou ilegivel: levanta ValueError."""
    arquivo = os.environ.get("PF_TELAS_STACKS")
    try:
        if arquivo:
            with open(arquivo, encoding="utf-8") as fh:
                texto = fh.read()
        else:
            p = subprocess.run([acervo_bin or "acervo", "ler", "casa", "stack", "telas", "--json"],
                               capture_output=True, text=True, timeout=60, check=False)
            if p.returncode != 0:
                raise ValueError(f"acervo ler casa stack saiu {p.returncode}")
            texto = p.stdout
        dado = json.loads(texto)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        raise ValueError(f"registro de stacks ilegivel: {e}") from None
    if isinstance(dado, dict):
        dado = [dado]
    return {s.get("slug"): s for s in dado if isinstance(s, dict)}


def promovida(tela, stacks, prod_raiz):
    """A stack da tela esta registrada com compose, nao e de teste, e a familia serve um current."""
    stack = stacks.get(tela.get("stack"))
    if not stack or stack.get("repo") != tela.get("familia") or not stack.get("compose"):
        return False
    if ((stack.get("reversao") or {}).get("via")) == "teste":
        return False
    return os.path.exists(os.path.join(prod_raiz, str(tela.get("familia")), "current"))


def lista_da_casca(telas, stacks, prod_raiz):
    """As telas promovidas, so com os campos que a casca le, por posicao."""
    saida = [{c: t.get(c) for c in CAMPOS_DA_CASCA} for t in telas if promovida(t, stacks, prod_raiz)]
    return sorted(saida, key=lambda t: (t["posicao"] if isinstance(t["posicao"], int) else 10**6, t["id"] or ""))


def main(argv):
    como_json = False
    for a in argv:
        if a == "--json":
            como_json = True
        else:
            sys.stderr.write("uso: release telas [--json]\n")
            return 2
    prod_raiz = os.environ.get("PF_PROD_RAIZ") or "/opt/platafirma"
    try:
        telas = carregar_declaracao(os.environ.get("PF_TELAS_DECLARACAO") or DECLARACAO)
        stacks = carregar_stacks(os.environ.get("PF_ACERVO_BIN"))
    except ValueError as e:
        sys.stderr.write(f"release: dependência ausente: {e}\n")
        return 3
    lista = lista_da_casca(telas, stacks, prod_raiz)
    if como_json:
        print(json.dumps({"telas": lista}, ensure_ascii=False))
    elif not lista:
        print("nenhuma tela com stack promovida")
    else:
        for t in lista:
            print(f"{t['posicao']}\t{t['id']}\t{t['rotulo']}\t{t['href']}\t{t['face'] or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
