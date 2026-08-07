#!/usr/bin/env python3
"""Estado de formalizacao das 34 sondas do gold-set-firmabot: existe pagina na wiki
nomeando o termo? existe ADR no git? Ausencia e dado, registrada como tal.

Difere do t0_wiki_estado.py de 04/08 (fossil, so cobria as 10 fixas via lista
hardcoded de titulos candidatos): aqui a busca e por srsearch na API viva do
MediaWiki, cobre as 34, e nao supoe titulo antes de perguntar."""
import json, urllib.parse, urllib.request, subprocess, os

API = "http://127.0.0.1:8080/api.php"

def q(params):
    p = dict(params); p["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def rev(title, direction):
    d = q({"action": "query", "prop": "revisions", "rvlimit": 1, "rvdir": direction,
           "rvprop": "timestamp|user", "titles": title})
    pages = d["query"]["pages"]
    pid, page = next(iter(pages.items()))
    if pid == "-1" or "missing" in page:
        return None
    revs = page.get("revisions") or []
    return revs[0]["timestamp"] if revs else None

def busca_wiki(termo, limite=3):
    try:
        d = q({"action": "query", "list": "search", "srsearch": termo, "srlimit": limite})
    except Exception as e:
        return {"erro": str(e)}
    hits = []
    for h in d.get("query", {}).get("search", []):
        title = h["title"]
        hits.append({
            "titulo": title,
            "criada_em": rev(title, "newer"),
            "ultima_edicao_em": rev(title, "older"),
        })
    return {"hits": hits, "totalhits": d.get("query", {}).get("searchinfo", {}).get("totalhits", 0)}

SONDAS = {
 "01": "critério de identidade conceito", "02": "tipo papel taxonomia", "03": "arquitetura de software",
 "04": "arquitetura de dados", "05": "governança de dados", "06": "domínio gestão do conhecimento",
 "07": "inteligência", "08": "criptografia pós-quântica", "09": "decisão arquitetural",
 "10": "curadoria de acervo",
 "11": "DDD domain-driven design", "12": "convergência sociotécnica", "13": "arquitetura de negócios",
 "14": "vocabulário controlado", "15": "continuant occurrent", "16": "proveniência arquivística",
 "17": "fusão recíproca de rankings", "18": "estratégia de chunking", "19": "quantização de modelo",
 "20": "opportunity solution tree", "21": "posicionamento de produto", "22": "avaliação heurística",
 "23": "gestão de incidente", "24": "gestão de mudança", "25": "observabilidade",
 "26": "trunk-based development", "27": "feature flag", "28": "teste de contrato",
 "29": "cryptoperiod", "30": "nível de garantia de autenticação", "31": "gestão de acesso privilegiado",
 "32": "cost of delay", "33": "limite de WIP", "34": "role charter",
}

# ADR: grep por termo nos dois repos de decisao, sem lista hardcoded de arquivo
REPOS_ADR = [
    ("platafirma-arquitetura", ["macro-global/decisions", "macro-global/capabilities"]),
    ("platafirma-conhecimento", ["ontologia/adr"]),
]

def adr_grep(termo):
    achados = []
    primeira_palavra = termo.split()[0]
    for repo, dirs in REPOS_ADR:
        repo_path = os.path.expanduser(f"~/AI/{repo}")
        if not os.path.isdir(repo_path):
            continue
        for d in dirs:
            full = os.path.join(repo_path, d)
            if not os.path.isdir(full):
                continue
            try:
                out = subprocess.run(
                    ["grep", "-rliE", primeira_palavra, full],
                    capture_output=True, text=True, timeout=15
                ).stdout.strip()
            except Exception:
                out = ""
            for f in filter(None, out.splitlines()):
                rel = os.path.relpath(f, repo_path)
                cri = subprocess.run(
                    ["git", "-C", repo_path, "log", "--diff-filter=A", "--follow",
                     "--format=%aI", "--", rel],
                    capture_output=True, text=True
                ).stdout.strip().splitlines()
                ult = subprocess.run(
                    ["git", "-C", repo_path, "log", "-1", "--format=%aI", "--", rel],
                    capture_output=True, text=True
                ).stdout.strip()
                achados.append({"repo": repo, "arquivo": rel,
                                 "criado_em": cri[-1] if cri else None,
                                 "ultima_edicao_em": ult or None})
    return achados

out = {}
for nn, termo in SONDAS.items():
    out[nn] = {
        "termo_busca": termo,
        "wiki": busca_wiki(termo),
        "adr": adr_grep(termo),
    }

print(json.dumps(out, ensure_ascii=False, indent=1))
