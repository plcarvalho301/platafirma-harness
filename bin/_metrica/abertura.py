#!/usr/bin/env python3
# capacidade: metrica
# dono: claudinho-IA
"""abertura — tokens do pacote de abertura, por cadeira e por arquivo.

Miolo de `metrica abertura` (card #3145; antes `bin/conta-abertura` + este arquivo
sob `bin/_conta/`, movido preservando historico). MODULO IMPORTAVEL: `bin/metrica`
importa `main` daqui e despacha `abertura` para ca antes do argparse comum, porque os
args (`<cadeira>`, `--tudo`, `--json`, `--chapeu <s>`) nao sao os de `metrica` (`<dia>`).

Nao reimplementa contagem: importa `monta-sessao` do repo real e usa o MESMO
`monta()` (tokenizador qwen2.5, terceiros/tokenizers/qwen2.5.json da arvore da release,
pinado por sha256 em registro/terceiros.json). O numero aqui bate
com o que a mesa e `conferir sessao` mostram, por construcao — mesma funcao.

Le sem rede: `atualizar=False`. Serve da MORADA PUBLICADA (`PF_ABERTURA_DIR`, com
default declarado em `monta-sessao`; e por essa variavel que o teste aponta para
fixture — arq:0097). Peca indisponivel entra com tokens=0 e frescor declarado, nunca
omitida.

uso:
  metrica abertura                     todas as cadeiras, uma linha de total cada
  metrica abertura <cadeira>           quebra por peca/arquivo de uma cadeira
  metrica abertura --tudo              quebra por peca de TODAS as cadeiras
  metrica abertura [...] --json        idem, em json
  metrica abertura [...] --chapeu <s>  inclui o chapeu <s> na conta (default: sem chapeu)

exit: 0 ok · 1 cadeira desconhecida · 2 uso · 3 morada nao publicada (dependencia ausente)
"""
import importlib.util
import json
import os
import sys

# miolo mora em bin/_metrica/ -> sobe 2 niveis ate platafirma-harness/
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MS = os.path.join(RAIZ, "bin", "monta-sessao")


def carrega_monta():
    """Importa bin/monta-sessao como modulo. Sem sufixo .py, spec_from_file_location
    nao acha loader sozinho — passa-se SourceFileLoader explicito."""
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("_monta_sessao", MS)
    spec = importlib.util.spec_from_loader("_monta_sessao", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def conta_cadeira(ms, cadeira, chapeu=None):
    """Devolve (envelope_total, linhas_por_peca) para uma cadeira. Sem rede.

    `envelope_total` traz `erro` quando `monta()` nao resolveu a cadeira; o campo
    `dependencia_ausente` (bool) distingue "morada nao publicada" (falta declarada
    por `monta()` no campo `morada`, exit 3 no chamador) de "cadeira desconhecida"
    (exit 1) sem o chamador reabrir a forma do dict de `monta()`.
    """
    pac = ms.monta(cadeira, atualizar=False, forcado_chapeu=chapeu)
    if "erro" in pac:
        pac["dependencia_ausente"] = "morada" in pac
        return pac, []
    linhas = []
    for e in pac["pecas"]:
        linhas.append({
            "peca": e.get("peca"),
            "ref": e.get("ref") or "—",
            "tokens": e.get("tokens", 0),
            "frescor": e.get("frescor"),
        })
    total = {
        "cadeira": pac["cadeira"],
        "pecas": len(linhas),
        "tokens": sum(l["tokens"] for l in linhas),
        "indisponiveis": sum(1 for l in linhas if l["frescor"] == "indisponivel"),
    }
    return total, linhas


USO = """uso:
  metrica abertura                     todas as cadeiras, uma linha de total cada
  metrica abertura <cadeira>           quebra por peca/arquivo de uma cadeira
  metrica abertura --tudo              quebra por peca de TODAS as cadeiras
  metrica abertura [...] --json        idem, em json
  metrica abertura [...] --chapeu <s>  inclui o chapeu <s> na conta (default: sem chapeu)

exit: 0 ok · 1 cadeira desconhecida · 3 morada nao publicada (dependencia ausente)
"""


def main(argv):
    """`argv` e so o que vem DEPOIS de `abertura` — sem nome de programa nem ato,
    no mesmo formato que `bin/conta-abertura` sempre aceitou (`sys.argv[1:]`)."""
    if any(a in ("--ajuda", "--help", "-h", "ajuda") for a in argv):
        print(USO)
        return 0
    quer_json = "--json" in argv
    quer_tudo = "--tudo" in argv
    chapeu = None
    if "--chapeu" in argv:
        i = argv.index("--chapeu")
        if i + 1 < len(argv):
            chapeu = argv[i + 1]
    posicionais = [a for i, a in enumerate(argv)
                   if not a.startswith("--")
                   and not (i > 0 and argv[i - 1] == "--chapeu")]

    ms = carrega_monta()
    _, metodo = ms.medidor()

    # uma cadeira, quebra por peca
    if posicionais:
        cadeira = posicionais[0]
        total, linhas = conta_cadeira(ms, cadeira, chapeu)
        if "erro" in total:
            # arq:0110 §4: cadeira que nao existe e resposta negativa de merito (1),
            # nao uso invalido (2); morada nao publicada e dependencia ausente (3).
            exit_code = 3 if total.get("dependencia_ausente") else 1
            saida = {"erro": total["erro"], "cadeiras_validas": total.get("cadeiras_validas", [])}
            if quer_json:
                print(json.dumps(saida, ensure_ascii=False, indent=2))
            else:
                print(total["erro"], file=sys.stderr)
                print("validas: " + ", ".join(total.get("cadeiras_validas", [])), file=sys.stderr)
            return exit_code
        if quer_json:
            print(json.dumps({"metodo_tokens": metodo, "total": total, "pecas": linhas},
                             ensure_ascii=False, indent=2))
            return 0
        print(f"# {total['cadeira']} — {total['tokens']} tokens em {total['pecas']} pecas"
              f"  ({metodo})")
        larg = max((len(l["peca"] or "") for l in linhas), default=4)
        for l in sorted(linhas, key=lambda x: -x["tokens"]):
            flag = "  ⚠ indisponivel" if l["frescor"] == "indisponivel" else ""
            print(f"  {l['tokens']:>6}  {(l['peca'] or ''):<{larg}}  {l['ref']}{flag}")
        return 0

    # todas as cadeiras
    cadeiras = ms.cadeiras_validas()
    resumo = []
    for c in cadeiras:
        total, linhas = conta_cadeira(ms, c, chapeu)
        if "erro" in total:
            continue
        resumo.append((total, linhas))

    if quer_json:
        out = {"metodo_tokens": metodo,
               "cadeiras": [{"total": t, "pecas": (ll if quer_tudo else None)}
                            for t, ll in resumo]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"# abertura — tokens por cadeira  ({metodo})")
    larg = max((len(t["cadeira"]) for t, _ in resumo), default=6)
    for t, linhas in sorted(resumo, key=lambda x: -x[0]["tokens"]):
        ind = f"  ({t['indisponiveis']} indisp.)" if t["indisponiveis"] else ""
        print(f"  {t['tokens']:>6}  {t['cadeira']:<{larg}}  {t['pecas']} pecas{ind}")
        if quer_tudo:
            for l in sorted(linhas, key=lambda x: -x["tokens"]):
                flag = "  ⚠" if l["frescor"] == "indisponivel" else ""
                print(f"           {l['tokens']:>6}  {l['peca']}{flag}")
    total_geral = sum(t["tokens"] for t, _ in resumo)
    print(f"  {'-' * 6}")
    print(f"  {total_geral:>6}  TOTAL ({len(resumo)} cadeiras)")
    return 0


if __name__ == "__main__":
    # Uso direto (fora de `metrica abertura`), preservado para depuracao local — o
    # ato de producao e sempre via `bin/metrica`, que passa `sys.argv[2:]`.
    sys.exit(main(sys.argv[1:]))
