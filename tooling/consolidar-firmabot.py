#!/usr/bin/env python3
"""Consolida G0-rag-base (retrieval) + geração num arquivo: pergunta, obras que
apareceram na recuperação, resposta de cada gerador pedido. Puramente factual --
não classifica cobertura nem escolhe "a fonte certa": isso é da claudinho-IA
(cálculo das métricas é dela, protocolo-medicao.md).

Uso:
  python3 tooling/consolidar-firmabot.py --arms claude,gemma4,qwen3.5 \
      --titulo "3 arms, mesmo prompt" > resultados/consolidado-T0.md
  python3 tooling/consolidar-firmabot.py --arms granite4 \
      --titulo "piso de controle" > resultados/consolidado-granite4-piso.md
"""
import argparse, json, pathlib, sys

BASE = pathlib.Path(__file__).resolve().parent.parent
RESULT_DIR = BASE / "avaliacao/gold-set-firmabot/resultados"
RETRIEVAL_DIR = RESULT_DIR / "G0-rag-base"

# nome de exibição -> (dir, padrão de arquivo, tipo)
CATALOGO = {
    "claude": ("claude-sonnet-5", RESULT_DIR / "G0-claude-referencia", "T0-{n}-resposta.md", "texto"),
    "gemma4": ("gemma4:12b", RESULT_DIR / "G0-gemma4-12b", "G0-{n}-persona-nao-declarada.json", "json"),
    "qwen3.5": ("qwen3.5:9b", RESULT_DIR / "G0-qwen3.5-9b", "G0-{n}-persona-nao-declarada.json", "json"),
    "granite4": ("granite4:latest", RESULT_DIR / "G0-granite4", "G0-{n}-persona-nao-declarada.json", "json"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True, help="chaves do catálogo, separadas por vírgula")
    ap.add_argument("--titulo", default="")
    args = ap.parse_args()

    arms = [CATALOGO[a.strip()] for a in args.arms.split(",")]
    files = sorted(RETRIEVAL_DIR.glob("T0-*.json"), key=lambda p: int(p.stem.split("-")[1]))

    print(f"# Consolidado T0 — recuperação + geração{' — ' + args.titulo if args.titulo else ''}\n")
    print("Gerado por `tooling/consolidar-firmabot.py`. `G0-rag-base` (o que o")
    print("rag_search devolveu) + o(s) gerador(es) respondendo em cima do mesmo")
    print("`contexto` congelado, com `prompt-firmabot.md` como sistema. Lista de")
    print("obras é só o que apareceu nas fontes — não é julgamento de qual é \"a\"")
    print("fonte certa, isso é da claudinho-IA.\n")
    print("---\n")

    for f in files:
        data = json.loads(f.read_text())
        n = data["n"]
        pergunta = data["pergunta"]
        bloco = data["bloco"]

        obras = []
        for fonte in data["retorno"]["fontes"]:
            obra = fonte.get("obra") or f"[sem obra] {fonte['arquivo']}"
            if obra not in obras:
                obras.append(obra)

        print(f"## {n}. {pergunta}  \n*(bloco {bloco})*\n")
        print("**Obras na recuperação:** " + "; ".join(obras) + "\n")

        for nome_arm, dirn, padrao, tipo in arms:
            resp_path = dirn / padrao.format(n=n)
            if not resp_path.exists():
                resposta = "(sem resposta)"
            elif tipo == "json":
                resposta = json.loads(resp_path.read_text()).get("resposta", "(vazia)")
            else:
                resposta = resp_path.read_text().strip()
            print(f"**Resposta ({nome_arm}):**\n")
            print(resposta + "\n")

        print("---\n")


if __name__ == "__main__":
    main()
