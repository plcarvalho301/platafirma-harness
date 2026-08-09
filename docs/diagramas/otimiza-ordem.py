#!/usr/bin/env python3
"""Permuta a ordem das colunas dentro de cada faixa de um .d2 em grid,
renderiza cada combinacao e escolhe a de menor cruzamento de aresta.

uso: otimiza-ordem.py arquivo.d2 [razao-alvo]

O arquivo e reescrito no lugar com a melhor ordem. Nao muda o desenho:
so a posicao das colunas dentro de cada faixa.
"""
import re, subprocess, itertools, sys, os

src = sys.argv[1]
alvo = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
base = open(src, encoding='utf-8').read()
AQUI = os.path.dirname(os.path.abspath(__file__))


def faixas(txt):
    return [m.group(1) for m in re.finditer(r'^(\w+): .*\{$', txt, re.M)]


def linhas_de(txt, chave):
    """Filhos DIRETOS do container. Ignora o que esta dentro de sub-container:
    contar chave arrancava rag/msg/onto de dentro do motor."""
    i = txt.index('\n' + chave + ':')
    corpo = txt[i:txt.index('\n}\n', i)]
    out, nivel = [], 0
    for l in corpo.split('\n')[2:]:  # pula o vazio e a linha de abertura do container
        if nivel == 0 and re.match(r'\s+\w+:.*class: cartao\s*\}?\s*$', l):
            out.append(l)
        nivel += l.count('{') - l.count('}')
        if nivel < 0:
            break
    return out


def troca(txt, chave, ordem):
    i = txt.index('\n' + chave + ':')
    fim = txt.index('\n}\n', i)
    corpo = txt[i:fim]
    for l in linhas_de(txt, chave):
        corpo = corpo.replace(l + '\n', '')
    m = re.search(r'(\s+grid-columns: \d+\n)', corpo)
    corpo = corpo[:m.end()] + '\n'.join(ordem) + '\n' + corpo[m.end():]
    return txt[:i] + corpo + txt[fim:]


alvos = [c for c in faixas(base) if len(linhas_de(base, c)) > 1]
print("faixas permutadas:", alvos)
espaco = [itertools.permutations(linhas_de(base, c)) for c in alvos]
combos = [dict(zip(alvos, p)) for p in itertools.product(*espaco)]

melhor = None
for c in combos:
    t = base
    for k, v in c.items():
        t = troca(t, k, list(v))
    open('/tmp/_t.d2', 'w', encoding='utf-8').write(t)
    if subprocess.run(['d2', '--layout', 'elk', '/tmp/_t.d2', '/tmp/_t.svg'],
                      capture_output=True).returncode:
        continue
    out = subprocess.run(['python3', os.path.join(AQUI, 'cruzamentos.py'),
                          '/tmp/_t.svg', 'x'], capture_output=True, text=True).stdout
    n = int(re.search(r'cruzam: (\d+)', out).group(1))
    s = open('/tmp/_t.svg', encoding='utf-8').read()
    w, h = [float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups()]
    score = (n, abs(w / h - alvo))
    if melhor is None or score < melhor[0]:
        melhor = (score, t, n, w, h)
        print(f"  cruz={n}  {w:.0f}x{h:.0f}  razao {w/h:.2f}")

_, t, n, w, h = melhor
open(src, 'w', encoding='utf-8').write(t)
print(f"gravado: cruzamentos={n}  {w:.0f} x {h:.0f}  razao {w/h:.2f}  ({len(combos)} combinacoes)")
