"""Estrato determinístico do gold set (card #188).

O alvo se deriva de `chunks.section_id` — sufixo após o '#' — então o rótulo nasce
por construção, sem julgamento humano e sem depender do título da obra.

Duas classes de identificador, com regras diferentes:

  cravam sozinhas   nist_control, nist_enhancement, cis_control, cis_safeguard
                    o código é único no corpus inteiro; a pergunta não precisa dizer
                    de que norma se trata.

  precisam de dica  clause_decimal, annex
                    '5.4' existe em dezenas de documentos. A pergunta carrega o
                    doc_hint (título da obra) e o par (doc_hint, código) é a chave.

`clause_decimal` é catch-all do roteador: pega numeração de página de livro
('20 The End of Homo Sapiens') junto com cláusula de norma. Por isso só entram
documentos cuja obra é de espécie normativa — o resto é ruído com cara de código.
"""
import json, random, re, subprocess

random.seed(188)

ESPECIES_NORMATIVAS = ('norma-tecnica','framework','guia','modelo-de-maturidade')
CRAVAM_SOZINHAS = ('nist_control','nist_enhancement','cis_control','cis_safeguard')
PRECISAM_DICA = ('clause_decimal','annex')
POR_CLASSE = 25

SQL = f"""
copy (
  select c.marker_type, c.section_id, o.id::text, o.titulo,
         replace(left(c.text,300), E'\\n', ' ')
  from chunks c
  join documents d on d.id = c.document_id
  join acervo.obra o on o.id = d.obra_id
  join acervo.especie_tipo e on e.id = o.especie_id
  where c.section_id like '%#%' and not c.is_not_text
    and length(c.text) > 250 and c.embedding is not null
    and ( c.marker_type in {CRAVAM_SOZINHAS}
       or (c.marker_type in {PRECISAM_DICA} and e.slug in {ESPECIES_NORMATIVAS}) )
) to stdout with (format csv, delimiter E'\\t')
"""

def puxar():
    open('/tmp/q_det.sql','w').write(SQL)
    subprocess.run(['docker','cp','/tmp/q_det.sql','rag-extractor-pg:/tmp/'],check=True,capture_output=True)
    r=subprocess.run(['docker','exec','rag-extractor-pg','psql','-U','rag','-d','rag_extractor','-f','/tmp/q_det.sql'],
                     check=True,capture_output=True,text=True)
    out=[]
    for ln in r.stdout.splitlines():
        p=ln.split('\t')
        if len(p)==5: out.append(dict(marker=p[0],section_id=p[1],obra_id=p[2],titulo=p[3],texto=p[4]))
    return out

def codigo(s): return re.sub(r'~\d+$','',s.split('#',1)[1])

def pergunta(r):
    c=codigo(r['section_id'])
    if r['marker'] in ('nist_control','nist_enhancement'): return f"O que estabelece o controle {c} do NIST SP 800-53?"
    if r['marker'] in ('cis_control','cis_safeguard'):     return f"O que exige o item {c} do CIS Benchmark?"
    if r['marker']=='annex':                               return f'O que trata o {c} de "{r["titulo"]}"?'
    return f'O que estabelece a cláusula {c} de "{r["titulo"]}"?'

def main():
    regs=puxar(); grupos={}
    for r in regs: grupos.setdefault(r['marker'],[]).append(r)
    itens=[]
    for marker,grupo in sorted(grupos.items()):
        vistos,unicos=set(),[]
        for r in grupo:
            ch=(r['obra_id'],codigo(r['section_id']))
            if ch not in vistos: vistos.add(ch); unicos.append(r)
        amostra=random.sample(unicos,min(POR_CLASSE,len(unicos)))
        for i,r in enumerate(amostra,1):
            itens.append({'id':f"det-{marker}-{i:03d}",'estrato':'deterministico','marker_type':marker,
                'chave':'codigo' if marker in CRAVAM_SOZINHAS else 'codigo+doc_hint',
                'pergunta':pergunta(r),'alvo_section_id':r['section_id'],'alvo_obra_id':r['obra_id'],
                'doc_hint':None if marker in CRAVAM_SOZINHAS else r['titulo'],
                'relevancia':'positiva','ausencia':None,'pontuavel':True})
        print(f"  {marker:18s} {len(grupo):6d} chunks · {len(unicos):5d} códigos únicos · {len(amostra):3d} sorteados")
    saida='/home/claudinho/AI/gold-set/gold-deterministico.jsonl'
    with open(saida,'w') as f:
        for it in itens: f.write(json.dumps(it,ensure_ascii=False)+'\n')
    print(f"\n{len(itens)} itens → {saida}")

main()
