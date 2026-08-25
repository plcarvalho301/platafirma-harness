#!/usr/bin/env python3
# capacidade: contar tokens servidos na abertura por cadeira e por peca/arquivo
# dono: claudinho-IA
"""conta-abertura — tokens do pacote de abertura, por cadeira e por arquivo.

Nao reimplementa contagem: importa `monta-sessao` do repo real e usa o MESMO
`monta()` (tokenizador qwen2.5, opt/tokenizers/qwen2.5.json). O numero aqui bate
com o que a mesa e `conferir sessao` mostram, por construcao — mesma funcao.

Le sem rede: `atualizar=False`. Serve do clone; se quiser HEAD fresco, `repo_sync`
antes. Peca indisponivel entra com tokens=0 e frescor declarado, nunca omitida.

uso:
  conta-abertura                     todas as cadeiras, uma linha de total cada
  conta-abertura <cadeira>           quebra por peca/arquivo de uma cadeira
  conta-abertura --tudo              quebra por peca de TODAS as cadeiras
  conta-abertura [...] --json        idem, em json
  conta-abertura [...] --chapeu <s>  inclui o chapeu <s> na conta (default: sem chapeu)
"""
import importlib.util
import json
import os
import sys

# miolo mora em bin/_conta/ -> sobe 2 niveis ate platafirma-harness/
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
    """Devolve (envelope_total, linhas_por_peca) para uma cadeira. Sem rede."""
    pac = ms.monta(cadeira, atualizar=False, forcado_chapeu=chapeu)
    if "erro" in pac:
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


def main(argv):
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
            saida = {"erro": total["erro"], "cadeiras_validas": total.get("cadeiras_validas", [])}
            if quer_json:
                print(json.dumps(saida, ensure_ascii=False, indent=2))
            else:
                print(total["erro"], file=sys.stderr)
                print("validas: " + ", ".join(total.get("cadeiras_validas", [])), file=sys.stderr)
            return 2
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
    sys.exit(main(sys.argv[1:]))
