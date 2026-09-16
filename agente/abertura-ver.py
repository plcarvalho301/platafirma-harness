#!/usr/bin/env python3
"""abertura-ver — simula a montagem de sessão a partir do clone do platafirma-harness.

Uso pessoal, para propor melhoria no fluxo. NÃO é diagnóstico de produção: produção
lê a morada publicada (arq:0097); isto lê a árvore abertura/ do clone, do jeito que ela
está no disco agora (inclusive edição não commitada — é para isso que serve).

  python3 abertura-ver.py "(IA, harness)"
  python3 abertura-ver.py ia engenharia-de-harness
  python3 abertura-ver.py Carla rh --pergunta "revisa a persona da TI"
  python3 abertura-ver.py ia --pergunta "janela de contexto"   # sem chapéu: roteia
  python3 abertura-ver.py ia harness --json                   # a forma que a tool devolve

  cadeira   slug (ia), nome (Elias) ou parte única do nome
  chapeu    slug ou parte única dele (harness -> engenharia-de-harness); omitido, o
            roteador decide pela --pergunta, como `expediente montar`
  --pergunta "<texto>"  o primeiro pedido do dono: roteia o chapéu e marca a peça acervo
  --json    o pacote como JSON, a forma que `monta_sessao` devolve ao modelo
  --md      Markdown para ler num visualizador: resumo em tabela no topo e uma seção
            por peça, com o texto dela literal num bloco (é texto cru que o modelo lê)
            ex.: python3 abertura-ver.py "(IA, harness)" --md > ia-harness.md
  --clone <dir>         outro clone (default: o clone onde este arquivo mora)

Ordem, cabeçalhos, ref, sha e contagem seguem `bin/expediente montar` do clone. Duas
peças dependem da instância e não do clone, e saem marcadas SIMULADA com o tamanho
zero: `mesa` (banco da sessão) e `acervo-consultado` (motor). O `sessao` que a porta
cola no topo também fica de fora.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TOKENIZADORES = ["terceiros/tokenizers/qwen2.5.json",
                 "/opt/platafirma/current/harness/terceiros/tokenizers/qwen2.5.json"]


def erro(msg: str, rc: int = 2):
    print(f"abertura-ver: {msg}", file=sys.stderr)
    sys.exit(rc)


def acha_clone(explicito: str | None) -> Path:
    candidatos = [Path(explicito).expanduser()] if explicito else [
        AQUI.parent, Path.home() / "AI" / "platafirma-harness"]
    for c in candidatos:
        if (c / "abertura" / "dono.md").is_file():
            return c.resolve()
    erro(f"clone sem abertura/dono.md: {', '.join(map(str, candidatos))} (use --clone)", 3)


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


# ------------------------------------------------------------------ código do clone
def carrega_do_clone(clone: Path):
    """hash_servido e o roteador vêm do clone: a simulação usa o código real."""
    sys.path[:0] = [str(clone / "lib"), str(clone / "comum")]
    from hash_servido import sha_servido
    caminho = clone / "bin" / "_expediente" / "rotear"
    loader = importlib.machinery.SourceFileLoader("rotear_clone", str(caminho))
    spec = importlib.util.spec_from_loader("rotear_clone", loader)
    rotear = importlib.util.module_from_spec(spec)
    sys.modules["rotear_clone"] = rotear   # @dataclass procura o módulo aqui
    loader.exec_module(rotear)
    return sha_servido, rotear


def medidor(clone: Path):
    try:
        from tokenizers import Tokenizer
    except ImportError:
        return (lambda s: max(1, len(s.encode()) // 4) if s else 0,
                "ESTIMATIVA por bytes/4 (modulo `tokenizers` ausente; rode com "
                "/opt/platafirma/current/venv/harness/bin/python para o número da casa)")
    for t in TOKENIZADORES:
        p = Path(t) if t.startswith("/") else clone / t
        if p.is_file():
            tk = Tokenizer.from_file(str(p))
            return (lambda s: len(tk.encode(s).ids) if s else 0), "tokenizador qwen2.5"
    return (lambda s: max(1, len(s.encode()) // 4) if s else 0,
            "ESTIMATIVA por bytes/4 (tokenizador qwen2.5.json ausente)")


# ------------------------------------------------------------------ vocabulário
def vivas(arvore: Path) -> dict[str, list[str]]:
    """cadeira viva = dir com persona.md; chapéu = subdir com chapeu.md (persona foto)."""
    out = {}
    for p in sorted(arvore.iterdir()):
        if p.is_dir() and (p / "persona.md").is_file():
            out[p.name] = sorted(c.name for c in p.iterdir()
                                 if c.is_dir() and (c / "chapeu.md").is_file())
    return out


def aliases(arvore: Path) -> dict:
    try:
        d = json.loads((arvore / "aliases.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def resolve_cadeira(dado: str, cadeiras: dict, apelidos: dict) -> str:
    alvo = sem_acento(dado.strip())
    for p in ("claudinho-", "claudinha-"):
        alvo = alvo.removeprefix(p)
    if alvo in cadeiras:
        return alvo
    por_nome = [s for s, a in apelidos.items()
                if s in cadeiras and isinstance(a, str)
                and (sem_acento(a) == alvo or sem_acento(a).split()[0] == alvo)]
    parciais = por_nome or [s for s in cadeiras if alvo in s] or [
        s for s, a in apelidos.items()
        if s in cadeiras and isinstance(a, str) and alvo in sem_acento(a)]
    if len(parciais) == 1:
        return parciais[0]
    quais = ", ".join(parciais) if parciais else ", ".join(cadeiras)
    erro(f"cadeira '{dado}' {'ambígua' if parciais else 'não existe'} — {quais}")


def resolve_chapeu(dado: str, cadeira: str, cadeiras: dict) -> str:
    validos = cadeiras[cadeira]
    alvo = sem_acento(dado.strip())
    if alvo in validos:
        return alvo
    parciais = [c for c in validos if alvo in c]
    if len(parciais) == 1:
        return parciais[0]
    quais = ", ".join(parciais or validos) or "(nenhum chapéu servido)"
    erro(f"chapéu '{dado}' {'ambíguo' if parciais else 'não existe'} em {cadeira} — {quais}")


# ------------------------------------------------------------------ peças (um verbo cada)
def peca_persona(arv, cad, _):
    return (arv / cad / "persona.md").read_text(encoding="utf-8")


def peca_chapeu(arv, cad, chapeu):
    base = arv / cad / chapeu
    txt = (base / "chapeu.md").read_text(encoding="utf-8")
    if (base / "ferramental.md").is_file():   # persona ler --chapeu: cat, \n, cat
        txt += "\n" + (base / "ferramental.md").read_text(encoding="utf-8")
    return txt


def peca_conduta(arv, _cad, _ch):
    return (arv / "dono.md").read_text(encoding="utf-8")


def peca_alias(arv, _cad, _ch):
    apelidos = aliases(arv)
    linhas = []
    for slug in vivas(arv):
        if slug in apelidos:
            v = apelidos[slug]
            txt = v.strip() if isinstance(v, str) and v.strip() else "(sem alias)"
        else:
            txt = "(sem alias, omitido)"
        linhas.append((txt, slug))
    return "\n".join(f"{a} -> {s}" for a, s in sorted(linhas))


def idade(seg: float) -> str:
    seg = max(0, int(seg))
    if seg < 3600:
        return f"{seg // 60} min"
    return f"{seg // 3600} h" if seg < 86400 else f"{seg // 86400} d"


def peca_cadernos(arv, cad, chapeu):
    """mesa caderno [--chapeu]: índice da cadeira e, com chapéu, o corpo dele."""
    d = arv / cad
    achados = sorted(x.name for x in d.iterdir() if (x / "caderno.md").is_file())
    if not achados:
        out = [f"cadernos: nenhum em {d}"]
    else:
        out = []
        for slot in achados:
            cam = d / slot / "caderno.md"
            st = cam.stat()
            try:
                ts = int(subprocess.run(
                    ["git", "-C", str(arv), "log", "-1", "--format=%ct", "--", str(cam)],
                    capture_output=True, text=True, timeout=10).stdout.strip() or st.st_mtime)
            except (OSError, ValueError, subprocess.SubprocessError):
                ts = int(st.st_mtime)
            out.append(f"  {slot:<16} {st.st_size:>6} B   ultima escrita ha "
                       f"{idade(time.time() - ts)}")
        out.append("  (corpo sob demanda: `mesa caderno <chapeu>`)")
    if chapeu:
        out.append("")
        cam = d / chapeu / "caderno.md"
        if cam.is_file():
            out.append(f"===== abertura/{cad}/{chapeu}/caderno.md =====")
            out.append(cam.read_text(encoding="utf-8", errors="replace"))
        else:
            out.append(f"caderno {chapeu}: nao existe ({cam})")
    return "\n".join(out)


SIMULADA = {
    "mesa": "(SIMULADA — `mesa ver` lê o banco da sessão na instância, fora do clone. "
            "Em produção entram aqui os itens pendentes da cadeira, ou \"mesa vazia\".)",
    "acervo-consultado": "(SIMULADA — `motor rag buscar casa` consulta o acervo na "
                         "instância. Em produção entram aqui até 6 trechos, ou o aviso "
                         "de cobertura abaixo do piso.)",
}

CATALOGO = {  # peça -> (dono, volatilidade, ref, leitor)
    "persona": ("gestao-estrategica", "estavel", "persona ler {cad}", peca_persona),
    "chapeu": ("gestao-estrategica", "estavel", "persona ler {cad} --chapeu {ch}", peca_chapeu),
    "conduta": ("gestao-estrategica", "estavel", "persona conduta", peca_conduta),
    "alias-cadeiras": ("gestao-estrategica", "morna", "persona foto", peca_alias),
    "mesa": ("gestao-estrategica", "volatil", "mesa ver{flag_mesa}", None),
    "acervo-consultado": ("dados", "volatil",
                          'motor rag buscar casa "{perg}" --k 6 --texto secao', None),
    "cadernos": ("gestao-estrategica", "volatil", "mesa caderno{flag}", peca_cadernos),
}


# ------------------------------------------------------------------ montagem
def monta(clone, cad, chapeu, pergunta, forcado):
    arv = clone / "abertura"
    sha_servido, rotear = carrega_do_clone(clone)
    conta, metodo = medidor(clone)

    if forcado:
        roteador = {"via": "comando", "slug": chapeu, "acertos": {},
                    "motivo": "chapéu forçado por argumento"}
    else:
        d = rotear.escolhe(pergunta, cad, raiz_chapeus=str(arv))
        via = {"deterministico": "determinístico", "semantico": "semântico"}.get(d.via, d.via)
        roteador = {"via": via, "slug": d.slug, "acertos": d.acertos or {}, "motivo": d.motivo}
        chapeu = d.slug
    avisos = [] if chapeu else [f"chapéu não roteado (fallback): {roteador['motivo']}"]

    # Mesma ordem de bin/expediente montar: prefixo estável [persona, conduta] primeiro (#3067).
    ordem = ["persona", "conduta"] + (["chapeu"] if chapeu else []) + ["alias-cadeiras", "mesa"]
    ordem += (["acervo-consultado"] if pergunta else []) + ["cadernos"]

    pecas = []
    for nome in ordem:
        dono, vol, ref, leitor = CATALOGO[nome]
        ref = "verbo:" + ref.format(cad=cad, ch=chapeu, perg=(pergunta or "")[:40],
                                    flag=f" --chapeu {chapeu}" if chapeu else "",
                                    flag_mesa=f" {chapeu}" if chapeu else "")
        env = {"peca": nome, "dono": dono, "ref": ref, "sha": None, "regime": "valor",
               "volatilidade": vol, "tokens": 0, "frescor": "simulada", "motivo": None,
               "conteudo": None}
        if leitor is None:
            env["motivo"] = "depende da instância, não do clone"
            env["conteudo"] = SIMULADA[nome]
        else:
            try:
                txt = leitor(arv, cad, chapeu).strip()
            except OSError as e:
                env.update(frescor="indisponivel", motivo=str(e))
                avisos.append(f"peça `{nome}` indisponível: {e}")
                pecas.append(env)
                continue
            env.update(frescor="fresco", conteudo=txt, tokens=conta(txt), sha=sha_servido(txt))
        pecas.append(env)

    try:
        sha = subprocess.run(["git", "-C", str(clone), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        sujo = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--",
                               "abertura", "bin/_expediente"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        sha, sujo = "?", ""
    return {
        "cadeira": cad, "sessao_id": None, "ordem_id": None, "chapeu": chapeu,
        "roteador": roteador,
        "pacote": {"pecas": len(pecas), "tokens": sum(p["tokens"] for p in pecas),
                   "metodo_tokens": metodo,
                   "montador_sha": f"clone:{sha}{'+sujo' if sujo else ''}",
                   "montado_em": int(time.time()),
                   "registro": {"registrado": False, "motivo": "simulação local"}},
        "pecas": pecas, "avisos": avisos,
    }


def imprime(pac, clone):
    """Mesmo formato de `expediente montar` em texto, com resumo por peça no fim."""
    p, r = pac["pacote"], pac["roteador"]
    print(f"SIMULAÇÃO a partir de {clone} ({p['montador_sha']}) — não é produção")
    print(f"cadeira: {pac['cadeira']}   sessao_id: null   ordem_id: null")
    print(f"chapeu: {pac['chapeu'] or 'null'}   roteador: {r['via']}"
          + (f"   ({r['motivo']})" if r.get("motivo") else ""))
    print(f"pacote: {p['pecas']} peças · {p['tokens']} tokens · {p['metodo_tokens']}")
    for e in pac["pecas"]:
        sha = f" @{e['sha']}" if e["sha"] else ""
        print(f"===== {e['peca']}: {e['ref']}{sha} ({e['frescor']}, {e['tokens']} tokens) =====")
        print(e["conteudo"] if e["conteudo"] is not None else f"(INDISPONÍVEL — {e['motivo']})")
        print()
    if pac["avisos"]:
        print("avisos:")
        for a in pac["avisos"]:
            print(f"  (aviso: {a})")
        print()
    print("━" * 72)
    print(f"RESUMO — ordem de entrada · {p['tokens']} tokens · {p['metodo_tokens']}")
    total = p["tokens"] or 1
    for e in pac["pecas"]:
        car = len(e["conteudo"] or "") if e["frescor"] == "fresco" else 0
        print(f"  {e['peca']:<18} {e['tokens']:>6} tok  {100 * e['tokens'] / total:>5.1f}%"
              f"  {car:>7} car  {e['frescor']}")


def cerca(texto: str) -> str:
    """Bloco literal com cerca maior que qualquer sequência de crases do texto."""
    maior = max((len(m) for m in re.findall(r"`+", texto)), default=0)
    return "`" * max(4, maior + 1)


def imprime_md(pac, clone):
    """Markdown: a peça fica literal em bloco, porque o modelo recebe texto cru, e os
    títulos dela não se misturam com as seções deste relatório."""
    p, r = pac["pacote"], pac["roteador"]
    total = p["tokens"] or 1
    titulo = pac["cadeira"] + (f" · {pac['chapeu']}" if pac["chapeu"] else "")
    print(f"# Abertura simulada — {titulo}\n")
    print(f"> Simulação a partir de `{clone}` (`{p['montador_sha']}`). Não é produção.\n")
    print(f"- **Chapéu:** {pac['chapeu'] or '—'} · roteador `{r['via']}`"
          + (f" — {r['motivo']}" if r.get("motivo") else ""))
    print(f"- **Pacote:** {p['pecas']} peças · {p['tokens']} tokens · {p['metodo_tokens']}\n")
    print("| # | peça | tokens | % | caracteres | estado |")
    print("|---|---|---:|---:|---:|---|")
    for i, e in enumerate(pac["pecas"], 1):
        car = len(e["conteudo"] or "") if e["frescor"] == "fresco" else 0
        print(f"| {i} | [{e['peca']}](#{i}-{e['peca']}) | {e['tokens']} | "
              f"{100 * e['tokens'] / total:.1f}% | {car} | {e['frescor']} |")
    if pac["avisos"]:
        print("\n**Avisos**\n")
        for a in pac["avisos"]:
            print(f"- {a}")
    for i, e in enumerate(pac["pecas"], 1):
        print(f"\n## {i}. {e['peca']}\n")
        sha = f" · `@{e['sha']}`" if e["sha"] else ""
        print(f"`{e['ref']}`{sha} · {e['frescor']} · {e['tokens']} tokens\n")
        if e["frescor"] != "fresco":
            print(f"> {e['conteudo'] or 'INDISPONÍVEL — ' + str(e['motivo'])}")
            continue
        c = cerca(e["conteudo"])
        print(f"{c}markdown\n{e['conteudo']}\n{c}")


# ------------------------------------------------------------------ CLI
def main(argv):
    if not argv or argv[0] in ("-h", "--help", "--ajuda"):
        print(__doc__)
        return 0
    pergunta, clone_arg, como_json, como_md, livres = None, None, False, False, []
    it = iter(argv)
    for a in it:
        if a == "--json":
            como_json = True
        elif a == "--md":
            como_md = True
        elif a in ("--pergunta", "--clone"):
            v = next(it, None)
            if v is None:
                erro(f"{a} exige valor")
            if a == "--pergunta":
                pergunta = v
            else:
                clone_arg = v
        elif a.startswith("--"):
            erro(f"flag desconhecida: {a} (veja --help)")
        else:
            livres.append(a)
    # "(IA, harness)" ou "IA, harness" ou IA harness: a mesma coisa.
    partes = [x for x in re.split(r"[\s,()]+", " ".join(livres)) if x]
    if not partes or len(partes) > 2:
        erro("dê a cadeira e, opcional, o chapéu — ex.: \"(IA, harness)\"")

    clone = acha_clone(clone_arg)
    arv = clone / "abertura"
    cadeiras = vivas(arv)
    cad = resolve_cadeira(partes[0], cadeiras, aliases(arv))
    chapeu = resolve_chapeu(partes[1], cad, cadeiras) if len(partes) == 2 else None

    pac = monta(clone, cad, chapeu, (pergunta or "").strip(), forcado=chapeu is not None)
    if como_json:
        print(json.dumps(pac, ensure_ascii=False))
    elif como_md:
        imprime_md(pac, clone)
    else:
        imprime(pac, clone)
    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
        sys.stdout.flush()   # pipe fechado cedo (| head) estoura aqui, não na saída
        sys.exit(rc)
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
