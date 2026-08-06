import json, urllib.parse, urllib.request

API = "http://127.0.0.1:8080/api.php"

CAND = {
 "01": ["Conceito", "Estudos-ontologias/teia-de-conceitos", "Ajuda:Glossário", "Estudos-ontologias"],
 "02": ["Tipo", "Papel", "Ajuda:Método/taxonomia"],
 "03": ["Arquitetura de software", "Arquiteturas", "Engenharia-software", "Arquitetura:Índice", "Arquitetura:Topologia"],
 "04": ["Arquitetura de dados", "Engenharia-dados"],
 "05": ["Governança de dados", "Governanca de dados", "Governo-digital"],
 "06": ["Domínio", "Dominio", "Ajuda:Criar um domínio", "Ajuda:Explorar por faceta"],
 "07": ["Inteligência", "Inteligencia", "IA"],
 "08": ["Criptografia pós-quântica", "Criptografia pos-quantica", "PQC", "Seguranca-privacidade", "Frente:modulo-firma/backlog-canalseguroPQC-draft"],
 "09": ["Decisão arquitetural", "ADR", "Arquitetura:ADRs", "Arquitetura:Registro-de-decisoes", "PlataFirma:Decisões/adrs", "Frente:mdm-rh/adr"],
 "10": ["Curadoria de acervo", "Ajuda:Operar o acervo", "Ajuda:Sincronizar o acervo", "PlataFirma:Ops/operar-o-acervo", "Ajuda:Fichar um livro"],
}

def q(params):
    params = dict(params); params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def rev(title, direction):
    d = q({"action":"query","prop":"revisions","rvlimit":1,"rvdir":direction,
           "rvprop":"timestamp|user","titles":title})
    pages = d["query"]["pages"]
    pid, page = next(iter(pages.items()))
    if pid == "-1" or "missing" in page:
        return None, page.get("title", title)
    revs = page.get("revisions") or []
    return (revs[0]["timestamp"] if revs else None), page["title"]

out = {}
for nn, titles in CAND.items():
    linhas = []
    for t in titles:
        criada, real = rev(t, "newer")
        if criada is None:
            linhas.append({"titulo_consultado": t, "existe": False,
                           "criada_em": None, "ultima_edicao_em": None})
        else:
            ult, _ = rev(t, "older")
            linhas.append({"titulo_consultado": t, "titulo_real": real, "existe": True,
                           "criada_em": criada, "ultima_edicao_em": ult})
    out[nn] = linhas

print(json.dumps(out, ensure_ascii=False, indent=1))
