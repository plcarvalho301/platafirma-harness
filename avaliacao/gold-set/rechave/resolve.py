import json,re,unicodedata,difflib,sys,os

def norm(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode()
    s=s.lower()
    s=re.sub(r'\.(pdf|md|html?|txt|epub)$','',s)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

obras=[]
for l in open('/tmp/obras.tsv'):
    p=l.rstrip('\n').split('\t')
    if len(p)<6: continue
    obras.append(dict(id=p[0],titulo=p[1],arquivo=p[2],doc=p[3],chunks=int(p[4]),vet=int(p[5]),
                      n_tit=norm(p[1]),n_arq=norm(p[2])))

def candidatos(q):
    nq=norm(q)
    if not nq: return []
    exatos=[o for o in obras if nq==o['n_tit'] or nq==o['n_arq']]
    if exatos: return exatos,'exato'
    pre=[o for o in obras if o['n_tit'].startswith(nq) or o['n_arq'].startswith(nq) or nq.startswith(o['n_tit'])]
    if pre: return pre,'prefixo'
    sub=[o for o in obras if (nq in o['n_tit'] or nq in o['n_arq'] or o['n_tit'] in nq)]
    if sub: return sub,'substring'
    pool={o['n_tit']:o for o in obras}; pool.update({o['n_arq']:o for o in obras if o['n_arq']})
    m=difflib.get_close_matches(nq,list(pool),n=3,cutoff=0.72)
    if m: return [pool[x] for x in m],'fuzzy'
    return [],'nenhum'

rs=[json.loads(l) for l in open('gold-t2-20260803.jsonl') if l.strip()]
res=[];amb=[];nada=[]
for r in rs:
    if not r['esperada']: continue
    c=candidatos(r['esperada'])
    cands,modo=(c if c else ([], 'nenhum'))
    if len(cands)==1: res.append((r,cands[0],modo))
    elif len(cands)>1: amb.append((r,cands,modo))
    else: nada.append((r,modo))
print(f"resolvidas {len(res)} | ambiguas {len(amb)} | sem candidato {len(nada)}")
print('\n=== RESOLVIDAS (modo | chunks/vetores)')
for r,o,m in res:
    flag='' if o['vet']==o['chunks'] and o['chunks']>0 else '  <<< INCOMPLETA'
    print(f"{r['id']:38s} {m:9s} {o['chunks']:5d}/{o['vet']:<5d} {o['titulo'][:60]}{flag}")
print('\n=== AMBIGUAS')
for r,cs,m in amb:
    print(f"{r['id']:38s} {m:9s} esperada={r['esperada'][:50]!r}")
    for o in cs[:6]: print(f"    {o['id']}  {o['chunks']:5d}/{o['vet']:<5d} {o['titulo'][:70]}")
print('\n=== SEM CANDIDATO')
for r,m in nada:
    print(f"{r['id']:38s} esperada={r['esperada'][:90]!r}")
json.dump([{'id':r['id'],'obra_id':o['id'],'titulo':o['titulo'],'modo':m,'chunks':o['chunks'],'vetores':o['vet']} for r,o,m in res],
          open('rechave/resolvidas.json','w'),ensure_ascii=False,indent=1)
