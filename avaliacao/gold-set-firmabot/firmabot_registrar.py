#!/usr/bin/env python3
"""Arm firmabot -- registra as respostas colhidas a mao no firmabot.

O firmabot recupera com o proprio RAG; o contexto NAO e congelado como nos arms
locais. Por isso este arm mede so o que e observavel do lado de fora: forma da
resposta, citacao e declaracao de nao-cobertura. Comparacao com os arms locais e
de comportamento do gerador, nao de recuperacao.

Entrada: arquivo de colagem, blocos separados por linha `## NN`.

    ## 01
    <resposta inteira do firmabot, quantas linhas forem>

    ## 02
    ...

Uso:  firmabot_registrar.py <arquivo-colagem> [dir-resultado]
Ex.:  firmabot_registrar.py /tmp/firmabot.md G0-firmabot
"""
import json, sys, re, pathlib, datetime, glob

BASE = pathlib.Path("/home/claudinho/AI/platafirma-harness/avaliacao/gold-set-firmabot")
RAGB = BASE / "resultados" / "G0-rag-base"

NAO_COBRE = re.compile(
    r"n[ãa]o\s+(?:cobre|cobrem|h[áa]|existe|traz|abordam?|tratam?|contempla)"
    r"|nenhuma\s+(?:das\s+)?fontes?|acervo\s+n[ãa]o|fontes?\s+fornecidas?\s+n[ãa]o",
    re.I)


def medir(resposta, n_fontes=None):
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", resposta) if f.strip()]
    com_cite = [f for f in frases if re.search(r"\[\d+\]", f)]
    cites = [int(x) for x in re.findall(r"\[(\d+)\]", resposta)]
    m = {
        "chars": len(resposta),
        "frases": len(frases),
        "frases_com_citacao": len(com_cite),
        "taxa_citacao": round(len(com_cite) / len(frases), 3) if frases else 0.0,
        "fontes_citadas": sorted(set(cites)),
        "declarou_nao_cobertura": bool(NAO_COBRE.search(resposta)),
    }
    if n_fontes:
        m["citacoes_fora_do_intervalo"] = sorted({c for c in cites if c < 1 or c > n_fontes})
    return m


def main():
    colagem = pathlib.Path(sys.argv[1])
    dirname = sys.argv[2] if len(sys.argv) > 2 else "G0-firmabot"
    out = BASE / "resultados" / dirname
    out.mkdir(parents=True, exist_ok=True)

    sondas = {}
    for f in sorted(RAGB.glob("T0-*.json")):
        d = json.load(open(f))
        sondas[d["n"]] = d

    texto = colagem.read_text()
    partes = re.split(r"^##\s*(\d{1,2})\s*$", texto, flags=re.M)
    if len(partes) < 3:
        sys.exit("nenhum bloco `## NN` encontrado na colagem")

    linhas, vistos = [], []
    for nn, corpo in zip(partes[1::2], partes[2::2]):
        nn = nn.zfill(2)
        corpo = corpo.strip()
        if nn not in sondas:
            print(f"AVISO: sonda {nn} nao existe no gold set, ignorada", file=sys.stderr)
            continue
        d = sondas[nn]
        m = medir(corpo)
        rec = {
            "sonda": "G0", "n": nn, "bloco": d["bloco"],
            "persona": "persona-nao-declarada",
            "modelo": "firmabot",
            "pergunta": d["pergunta"],
            "contexto_de": {"rodada": "recuperacao propria do firmabot",
                            "acervo_sha": None, "n_fontes": None},
            "amostragem": None,
            "coletado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "coleta": "manual, colagem",
            "latencia_ms": None,
            "medidas": m,
            "resposta_vazia": corpo == "",
            "resposta": corpo,
        }
        json.dump(rec, open(out / f"G0-{nn}-persona-nao-declarada.json", "w"),
                  ensure_ascii=False, indent=1)
        linhas.append({"n": nn, "bloco": d["bloco"], **m})
        vistos.append(nn)

    faltam = [n for n in sorted(sondas) if n not in vistos]
    json.dump({"modelo": "firmabot", "coleta": "manual",
               "sondas_registradas": len(vistos), "faltam": faltam,
               "linhas": linhas},
              open(out / "_resumo.json", "w"), ensure_ascii=False, indent=1)
    print(f"OK firmabot: {len(vistos)} sondas em {out}")
    if faltam:
        print("faltam: " + " ".join(faltam))


if __name__ == "__main__":
    main()
