import re,subprocess,itertools,os
base=open('topologia-estratos.d2',encoding='utf-8').read()

def bloco(txt, chave):
    """extrai as linhas de cartao de um container, na ordem"""
    i=txt.index(chave)
    fim=txt.index('\n}\n', i)
    corpo=txt[i:fim]
    linhas=[l for l in corpo.split('\n') if re.match(r'\s{2,4}\w+:.*class: (cartao|cliente)', l)]
    return linhas, i, fim

def troca(txt, chave, nova_ordem):
    linhas,i,fim = bloco(txt, chave)
    corpo=txt[i:fim]
    for l in linhas: corpo=corpo.replace(l+'\n','')
    # reinsere logo apos a linha grid-columns
    m=re.search(r'(\s+grid-columns: \d+\n)', corpo)
    corpo=corpo[:m.end()] + '\n'.join(nova_ordem)+'\n' + corpo[m.end():]
    return txt[:i]+corpo+txt[fim:]

mods,_,_ = bloco(base,'mod: MÓDULOS')
cons,_,_ = bloco(base,'con: CONHECIMENTO')

melhor=None
for pm in itertools.permutations(mods):
    for pc in itertools.permutations(cons):
        t=troca(base,'mod: MÓDULOS',list(pm))
        t=troca(t,'con: CONHECIMENTO',list(pc))
        open('/tmp/t.d2','w',encoding='utf-8').write(t)
        r=subprocess.run(['d2','--layout','elk','/tmp/t.d2','/tmp/t.svg'],capture_output=True)
        if r.returncode: continue
        out=subprocess.run(['python3','/tmp/x.py','/tmp/t.svg','x'],capture_output=True,text=True).stdout
        n=int(re.search(r'cruzam: (\d+)',out).group(1))
        s=open('/tmp/t.svg',encoding='utf-8').read()
        w,h=[float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"',s).groups()]
        score=(n, abs(w/h-1.6))
        if melhor is None or score<melhor[0]:
            melhor=(score,t,n,w,h)
            print(f"  novo melhor: cruz={n}  {w:.0f}x{h:.0f} razao {w/h:.2f}")
print("---")
score,t,n,w,h=melhor
open('/tmp/best.d2','w',encoding='utf-8').write(t)
print(f"FINAL cruzamentos={n}  {w:.0f} x {h:.0f}  razao {w/h:.2f}")
