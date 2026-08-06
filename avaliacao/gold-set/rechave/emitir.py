import json
obras={}
for l in open('/tmp/obras.tsv'):
    p=l.rstrip('\n').split('\t')
    obras[p[0]]=dict(titulo=p[1],chunks=int(p[4]),vet=int(p[5]))
res={r['id']:r for r in json.load(open('rechave/resolvidas.json'))}

ACC=[o for o,v in obras.items() if v['titulo'].startswith('Accelerate')]
LIVRO=[o for o in ACC if 'Science of Lean' in obras[o]['titulo']]
MANUAL={
 'claudinho-arquiteto-05':['ca08bba4-7e8b-4fd6-a681-b7c8f6b75735'],
 'claudinho-TI-01':sorted(ACC),
 'claudinho-TI-10':LIVRO,
}
QUARENTENA={}
out=[];quar=[]
for l in open('gold-t2-20260803.jsonl'):
    r=json.loads(l)
    if r['esperada'] is None:
        r['obra_ids']=[]; r['relevancia']='negativa'; r['pontuavel']=True
    else:
        ids=MANUAL.get(r['id']) or [res[r['id']]['obra_id']]
        r['obra_ids']=ids; r['relevancia']='positiva'
        r['cobertura_vetor']=[f"{obras[i]['vet']}/{obras[i]['chunks']}" for i in ids]
        if all(obras[i]['chunks']==0 for i in ids):
            r['pontuavel']=False; r['motivo']='obra catalogada, nao ingerida (0 chunks)'
            r.pop('esperada',None); quar.append(r); continue
        r['pontuavel']=True
    r.pop('esperada',None)
    out.append(r)
w=open('gold-t2-obraid-20260805.jsonl','w')
for r in out: w.write(json.dumps(r,ensure_ascii=False)+'\n')
w.close()
w=open('rechave/quarentena-20260805.jsonl','w')
for r in quar: w.write(json.dumps(r,ensure_ascii=False)+'\n')
w.close()
pos=[r for r in out if r['relevancia']=='positiva']
print('emitidas',len(out),'| positivas',len(pos),'| negativas',len(out)-len(pos),'| quarentena',len(quar))
print('obras distintas no gabarito',len({i for r in pos for i in r['obra_ids']}))
print('itens cuja obra esta 100% vetorizada:',sum(1 for r in pos if all(c.split('/')[0]==c.split('/')[1] for c in r['cobertura_vetor'])))
