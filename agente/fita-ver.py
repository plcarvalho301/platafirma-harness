#!/usr/bin/env python3
"""fita-ver — mostra, para leitura humana, o que entrou na fita de uma sessão do Code.

Lê o transcript que o próprio Claude Code grava (~/.claude/projects/*/<sessao>.jsonl),
não remonta nada: o que aparece aqui é o que o modelo recebeu, na ordem em que recebeu.
Roda na máquina onde o Code abriu (é lá que o transcript mora), só com a stdlib.

  fita-ver.py                    abertura da sessão mais recente (até a 1ª fala do modelo)
  fita-ver.py <id|arquivo>       abertura de uma sessão dada (uuid, prefixo ou .jsonl)
  fita-ver.py --lista            as 15 sessões mais recentes, com o 1º pedido
  fita-ver.py --tudo  ...        a fita inteira, não só a abertura
  fita-ver.py --cru   ...        retorno de tool byte a byte (JSON com \\n, como o modelo leu)
  fita-ver.py --sem-sistema ...  omite o system prompt do Code (bloco grande e fixo)

Leia com `python3 agente/fita-ver.py | less`. Tokens são estimativa (caracteres/4),
marcada com ≈.

O que o transcript NÃO tem: os esquemas das tools carregadas no início (só nomes) e o
texto exato de embrulho que o Code põe em volta de cada anexo (<system-reminder> etc.).
O conteúdo de cada anexo está aqui inteiro. Retorno de tool que passou do teto do Code
não entra na fita: vira arquivo, e o script mostra os dois — o aviso que entrou e o
arquivo que ficou de fora.
"""
import glob
import json
import os
import sys
import time

RAIZ = os.path.expanduser("~/.claude/projects")
LARG = 88


def sessoes():
    arqs = glob.glob(os.path.join(RAIZ, "*", "*.jsonl"))
    return sorted(arqs, key=os.path.getmtime, reverse=True)


def acha(alvo):
    if os.path.isfile(alvo):
        return alvo
    achados = [a for a in sessoes() if os.path.basename(a).startswith(alvo)]
    if not achados:
        sys.exit(f"fita-ver: sessão não encontrada: {alvo} (veja --lista)")
    return achados[0]


def primeiro_pedido(arq):
    with open(arq) as f:
        for linha in f:
            d = json.loads(linha)
            c = d.get("message", {}).get("content") if d.get("type") == "user" else None
            if isinstance(c, str):
                return c.replace("\n", " ")[:70]
    return "(sem pedido)"


def lista():
    for a in sessoes()[:15]:
        quando = time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(a)))
        print(f"{quando}  {os.path.basename(a)[:8]}  {primeiro_pedido(a)}")


def tok(n):
    return f"≈{n // 4:,} tok".replace(",", ".")


def bloco(titulo, texto, resumo, n=None):
    n = len(texto) if n is None else n
    resumo.append((titulo, n))
    cab = f"━━ {titulo} · {n:,} car · {tok(n)} ".replace(",", ".")
    print("\n" + cab + "━" * max(0, LARG - len(cab)))
    print(texto.rstrip("\n"))


def desdobra(texto):
    """JSON de retorno de tool vira texto legível; string com quebra sai com quebra real."""
    try:
        dado = json.loads(texto)
    except (ValueError, TypeError):
        return texto
    saida = []

    def anda(v, prefixo, nivel):
        pad = "  " * nivel
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, (dict, list)) and x:
                    saida.append(f"{pad}{prefixo}{k}:")
                    anda(x, "", nivel + 1)
                else:
                    anda(x, f"{k}: ", nivel)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                saida.append(f"{pad}[{i}]")
                anda(x, "", nivel + 1)
        elif isinstance(v, str) and "\n" in v:
            saida.append(f"{pad}{prefixo}")
            saida.append(f"{pad}┌─ texto ─")
            saida.extend(f"{pad}│ {l}" for l in v.split("\n"))
            saida.append(f"{pad}└─")
        else:
            saida.append(f"{pad}{prefixo}{json.dumps(v, ensure_ascii=False)}")

    anda(dado, "", 0)
    return ("[desdobrado do JSON: \\n virou quebra de linha; o modelo leu o JSON cru]\n"
            + "\n".join(saida))


def texto_de(conteudo):
    if isinstance(conteudo, str):
        return conteudo
    return "\n".join(p["text"] if p.get("type") == "text" else f"[{p.get('type')}]"
                     for p in conteudo or [])


def anexo(a, estado, resumo, sem_sistema):
    t = a.get("type")
    if t == "prompt_snapshot":
        sp = "\n\n".join(a.get("systemPrompt", []))
        if sp == estado.get("sistema"):
            return
        estado["sistema"] = sp
        if sem_sistema:
            resumo.append(("SYSTEM PROMPT do Code (omitido na tela)", len(sp)))
        else:
            bloco("SYSTEM PROMPT do Code", sp, resumo)
    elif t == "instructions":
        for f in a.get("files", []):
            titulo = f"INSTRUÇÕES · {f.get('type')} · {f.get('path')}"
            bloco(titulo, f.get("content", ""), resumo)
    elif t == "session_context":
        bloco("CONTEXTO DA SESSÃO", "\n".join(a.get("context", {}).values()), resumo)
    elif t == "skill_listing":
        bloco("SKILLS disponíveis", a.get("content", ""), resumo)
    elif t == "mcp_instructions_delta":
        bloco("INSTRUÇÕES DE SERVIDOR MCP", "\n\n".join(a.get("addedBlocks", [])), resumo)
    elif t == "agent_listing_delta":
        bloco("SUBAGENTES disponíveis", "\n".join(a.get("addedLines", [])), resumo)
    elif t == "deferred_tools_delta":
        bloco("TOOLS adiadas (só o nome entra)", "\n".join(a.get("addedNames", [])), resumo)
    elif t == "deferred_tools_record":
        txt = "\n\n".join(f"# {e.get('name')}\n{e.get('description', '')}"
                          for e in a.get("entries", []))
        bloco("ESQUEMA DE TOOL carregado", txt, resumo)
    elif t == "model":
        bloco("MODELO", a.get("text", ""), resumo)
    elif t == "date":
        bloco("DATA", a.get("date", ""), resumo)
    elif t == "total_tokens_reminder":
        return
    else:
        corpo = a.get("text") or a.get("content") or json.dumps(a, ensure_ascii=False, indent=1)
        if not isinstance(corpo, str):
            corpo = json.dumps(corpo, ensure_ascii=False)
        bloco(f"ANEXO · {t}", corpo, resumo)


def arquivo_do_estouro(texto):
    marca = "Output has been saved to "
    if marca not in texto:
        return None
    return texto.split(marca, 1)[1].split("\n", 1)[0].rstrip(".")


def mostra(arq, tudo, cru, sem_sistema):
    print(f"fita de {arq}")
    resumo, estado, nomes = [], {}, {}
    with open(arq) as f:
        linhas = [json.loads(l) for l in f if l.strip()]
    # O Code grava o snapshot do system prompt depois dos anexos, mas ele entra primeiro.
    for d in linhas:
        a = d.get("attachment", {})
        if d.get("type") == "attachment" and a.get("type") == "prompt_snapshot":
            anexo(a, estado, resumo, sem_sistema)
            break
    for d in linhas:
        t = d.get("type")
        if t == "attachment":
            anexo(d.get("attachment", {}), estado, resumo, sem_sistema)
            continue
        if t not in ("user", "assistant"):
            continue
        c = d["message"]["content"]
        if t == "user" and isinstance(c, str):
            bloco("DONO", c, resumo)
            continue
        fim = False
        for p in c if isinstance(c, list) else []:
            pt = p.get("type")
            if pt == "thinking":
                if p.get("thinking"):
                    resumo.append(("modelo · pensamento (não mostrado)", len(p["thinking"])))
            elif pt == "tool_use":
                nomes[p["id"]] = p["name"]
                args = json.dumps(p.get("input", {}), ensure_ascii=False, indent=1)
                bloco(f"MODELO CHAMA · {p['name']}", args, resumo)
            elif pt == "text" and t == "assistant":
                bloco("MODELO RESPONDE", p["text"], resumo)
                fim = True
            elif pt == "text":
                bloco("DONO", p["text"], resumo)
            elif pt == "tool_result":
                nome = nomes.get(p.get("tool_use_id"), "?")
                txt = texto_de(p.get("content"))
                estouro = arquivo_do_estouro(txt)
                corpo = txt if cru or estouro else desdobra(txt)
                bloco(f"RETORNO · {nome}", corpo, resumo, len(txt))
                if not estouro:
                    continue
                print("\n⚠ ESTE RETORNO NÃO ENTROU NA FITA: passou do teto do Code e virou o "
                      "arquivo abaixo.\n  Entra só o que o modelo ler dele depois.")
                if os.path.isfile(estouro):
                    with open(estouro) as g:
                        cont = g.read()
                    tit = f"FORA DA FITA · arquivo do estouro · {nome}"
                    bloco(tit, cont if cru else desdobra(cont), [], len(cont))
        if fim and not tudo:
            break

    total = sum(n for tit, n in resumo if "não mostrado" not in tit)
    print("\n" + "━" * LARG)
    print(f"RESUMO — o que entrou, na ordem ({tok(total)} no total)")
    for tit, n in resumo:
        print(f"  {n:>9,} car  {tok(n):>13}  {tit}".replace(",", "."))


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return
    if "--lista" in argv:
        lista()
        return
    flags = {a for a in argv if a.startswith("--")}
    resto = [a for a in argv if not a.startswith("--")]
    desconhecidas = flags - {"--tudo", "--cru", "--sem-sistema"}
    if desconhecidas:
        sys.exit(f"fita-ver: flag desconhecida: {' '.join(sorted(desconhecidas))} (veja --help)")
    if resto:
        arq = acha(resto[0])
    else:
        todas = sessoes()
        if not todas:
            sys.exit(f"fita-ver: nenhuma sessão em {RAIZ}")
        arq = todas[0]
    mostra(arq, "--tudo" in flags, "--cru" in flags, "--sem-sistema" in flags)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except BrokenPipeError:
        # `fita-ver.py | head` fecha o pipe cedo; sai calado.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
