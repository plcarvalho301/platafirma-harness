#!/usr/bin/env python3
"""Rodada 2 — mecânica do julgamento. Gera os três arquivos."""
import re, csv, os, glob, unicodedata
from collections import defaultdict, OrderedDict
from rapidfuzz import fuzz

BASE = os.path.expanduser('~/AI/platafirma-harness/distribuicao')
R1 = f'{BASE}/rodada-1'
R2 = f'{BASE}/rodada-2'
OUT = f'{R2}/julgamento'
os.makedirs(OUT, exist_ok=True)

# ---------- obras: id -> (dominio, titulo)
obra = {}
for l in open('/tmp/julg/obras.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 3:
        obra[p[0]] = (p[1], p[2])

# ---------- conceitos existentes
existentes = []
for l in open('/tmp/julg/existentes.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 5:
        existentes.append(dict(slug=p[0], rotulo=p[1], natureza=p[2],
                               estatuto=p[3], dominios=[d for d in p[4].split('|') if d]))

# ---------- lotes: quem ganhou o quê, quem perdeu o quê
ganhas = defaultdict(set)
for f in glob.glob(f'{R1}/reivindicacoes/*.csv'):
    persona = os.path.basename(f)[:-4]
    if persona == 'EXEMPLO':
        continue
    for row in csv.DictReader(open(f, encoding='utf-8-sig')):
        oid = (row.get('obra_id') or '').strip()
        if oid:
            ganhas[persona].add(oid)

perdidas = defaultdict(set)   # persona -> obras em que foi reivindicante e perdeu
for row in csv.DictReader(open(f'{R1}/conflitos.csv', encoding='utf-8-sig')):
    oid = row['obra_id'].strip()
    venc = (row.get('vencedor') or '').strip()
    for r in (row.get('reivindicantes') or '').split('|'):
        r = r.strip()
        if r and r != venc:
            perdidas[r].add(oid)
        if r == venc:
            ganhas[r].add(oid)
# obra que foi a conflito sai do lote de quem perdeu
for p in ganhas:
    ganhas[p] -= perdidas[p]

# ---------- parse das propostas
CAMPOS = ('balde rotulo natureza estatuto definicao obras-ancora '
          'caso-falseador pai-proposto substitui').split()
propostas = []
for f in sorted(glob.glob(f'{R2}/propostas/*.md')):
    persona = os.path.basename(f)[:-3]
    txt = open(f, encoding='utf-8').read()
    for bloco in re.split(r'^## ', txt, flags=re.M)[1:]:
        linhas = bloco.split('\n')
        slug = linhas[0].strip()
        d = {}
        chave = None
        for l in linhas[1:]:
            m = re.match(r'^([a-z\-]+):\s*(.*)$', l)
            if m and m.group(1) in CAMPOS:
                chave = m.group(1)
                d[chave] = m.group(2).strip()
            elif m:
                chave = None          # campo fora do gabarito: encerra o anterior
            elif chave and l.strip() and not l.startswith('#') and l.strip() != '---':
                d[chave] += ' ' + l.strip()
        anc = [a.strip() for a in re.sub(r'#.*', '', d.get('obras-ancora', '')).split(',') if a.strip()]
        propostas.append(dict(persona=persona, slug=slug, **{k: d.get(k, '') for k in CAMPOS},
                              ancoras=anc))

# ---------- ocorrência: domínio derivado das obras-âncora
for c in propostas:
    doms = OrderedDict()
    for a in c['ancoras']:
        dm, tit = obra.get(a, ('(fora-do-acervo)', f'??? {a}'))
        doms.setdefault(dm, []).append((a, tit))
    c['por_dominio'] = doms

def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def sim(a, b):
    """quase-identico = distancia de edicao pequena. Contencao NAO entra aqui."""
    return fuzz.ratio(a, b)

def contido(a, b):
    ta, tb = set(a.split('-')), set(b.split('-'))
    return (ta < tb or tb < ta) and min(len(ta), len(tb)) >= 2

# =========================================================
# ARQUIVO A — conceitos pré-existentes
# =========================================================
with open(f'{OUT}/a-conceitos-pre-existentes.md', 'w', encoding='utf-8') as fh:
    fh.write('# Conceitos pré-existentes na base — ocorrência por domínio\n\n')
    fh.write('Fonte: `acervo.conceito` no Postgres. Ocorrência derivada por '
             '`obra_trata_de` ⋈ `obra.dominio_id` (ont:0062). '
             'Conceito sem obra não ocorre em domínio nenhum — linha sem valor à direita.\n\n')
    fh.write('```\n')
    for c in existentes:
        fh.write(f"{c['slug']} :: {', '.join(c['dominios'])}\n")
    fh.write('```\n')

# =========================================================
# ARQUIVO B — consolidado das propostas, por domínio
# =========================================================
por_dom = defaultdict(list)
for c in propostas:
    for dm in c['por_dominio']:
        por_dom[dm].append(c)

with open(f'{OUT}/b-propostas-consolidado.md', 'w', encoding='utf-8') as fh:
    fh.write('# Rodada 2 — propostas consolidadas das 7 cadeiras\n\n')
    fh.write(f'{len(propostas)} conceitos propostos. Agrupados pelo domínio em que **ocorrem** '
             '(domínio das obras-âncora, ont:0062). Conceito com âncoras em mais de um domínio '
             'aparece em cada um — a ocorrência é plural.\n\n')
    for dm in sorted(por_dom):
        fh.write(f'## {dm}\n\n')
        for c in sorted(por_dom[dm], key=lambda x: x['slug']):
            fh.write(f"* **{c['slug']}** — {c['rotulo']} `[{c['persona']}]`"
                     + (f" `balde {c['balde']}`" if c['balde'] else '') + '\n')
            fh.write(f"   * definição: {c['definicao']}\n")
            fh.write(f"   * natureza: {c['natureza']}\n")
            fh.write(f"   * estatuto: {c['estatuto']}\n")
            fh.write('   * âncoras:\n')
            for dm2, lst in c['por_dominio'].items():
                for _a, tit in lst:
                    marca = '' if dm2 == dm else f' _(ocorre em {dm2})_'
                    fh.write(f'      * {tit}{marca}\n')
            fh.write('\n')

# =========================================================
# duplicações entre propostas (d)
# =========================================================
LIMIAR = 90
dup = []
dup_fraco = []
for i in range(len(propostas)):
    for j in range(i + 1, len(propostas)):
        a, b = propostas[i], propostas[j]
        if a['persona'] == b['persona']:
            continue
        sa, sb = norm(a['slug']), norm(b['slug'])
        sc = 100 if sa == sb else sim(sa, sb)
        sr = sim(norm(a['rotulo']), norm(b['rotulo']))
        if sc >= LIMIAR or sr >= LIMIAR:
            dup.append((a, b, max(sc, sr), 'slug-identico' if sa == sb else 'slug-quase-identico'))
        elif contido(sa, sb):
            dup_fraco.append((a, b, 0, 'slug-contido'))

# =========================================================
# colisões com a base (e)
# =========================================================
ex_por_slug = {c['slug']: c for c in existentes}
colisao = []
colisao_fraco = []
for c in propostas:
    sc_ = norm(c['slug'])
    for e in existentes:
        se = norm(e['slug'])
        s1 = 100 if sc_ == se else sim(sc_, se)
        s2 = sim(norm(c['rotulo']), norm(e['rotulo']))
        if s1 >= LIMIAR or s2 >= LIMIAR:
            colisao.append((c, e, max(s1, s2),
                            'slug-identico' if sc_ == se else 'slug-quase-identico'))
        elif contido(sc_, se):
            colisao_fraco.append((c, e, 0, 'slug-contido'))
    if c['substitui']:
        for alvo in [s.strip() for s in c['substitui'].split(',') if s.strip()]:
            e = ex_por_slug.get(alvo)
            colisao.append((c, e or dict(slug=alvo, rotulo='(slug inexistente na base)',
                                         dominios=[]), 100, 'substitui-declarado'))

# =========================================================
# ARQUIVO C — slug, próprio/derivado, falseador, pai
# =========================================================
def origem(c, dm):
    """derivado = âncora daquele domínio veio de obra que a cadeira PERDEU."""
    lst = c['por_dominio'][dm]
    der = sum(1 for a, _t in lst if a in perdidas.get(c['persona'], set()))
    return ('derivado' if der else 'proprio'), der, len(lst)

with open(f'{OUT}/c-propostas-ficha.md', 'w', encoding='utf-8') as fh:
    fh.write('# Rodada 2 — ficha das propostas\n\n')
    fh.write('`derivado` = pelo menos uma das âncoras que colocam o conceito neste domínio '
             'veio de obra que a cadeira **perdeu** na arbitragem da rodada 1. '
             'Contagem `n/total` ao lado.\n\n')
    for dm in sorted(por_dom):
        fh.write(f'## {dm}\n\n')
        for c in sorted(por_dom[dm], key=lambda x: x['slug']):
            o, der, tot = origem(c, dm)
            fh.write(f"* **{c['slug']}** `[{c['persona']}]`\n")
            fh.write(f'   * origem: {o} ({der}/{tot} âncoras de derrota)\n')
            fh.write(f"   * falseador: {c['caso-falseador'] or '—'}\n")
            fh.write(f"   * pai proposto: {c['pai-proposto'] or '—'}\n")
        fh.write('\n')

    fh.write('---\n\n## duplicações entre propostas\n\n')
    if not dup:
        fh.write('* nenhuma\n')
    for a, b, s, tipo in sorted(dup, key=lambda x: -x[2]):
        fh.write(f"* **{a['slug']}** `[{a['persona']}]` × **{b['slug']}** `[{b['persona']}]` "
                 f'— {tipo} ({s:.0f})\n')

    if dup_fraco:
        fh.write('\n### sinal fraco — slug contido (triagem, não veredito)\n\n')
        for a, b, _s, _t in sorted(dup_fraco, key=lambda x: x[0]['slug']):
            fh.write(f"* **{a['slug']}** `[{a['persona']}]` ⊂⊃ **{b['slug']}** `[{b['persona']}]`\n")

    fh.write('\n## colisões com a base pré-existente\n\n')
    if not colisao:
        fh.write('* nenhuma\n')
    vistos = set()
    for c, e, s, tipo in sorted(colisao, key=lambda x: (x[0]['slug'], -x[2])):
        k = (c['slug'], c['persona'], e['slug'], tipo)
        if k in vistos:
            continue
        vistos.add(k)
        docc = ', '.join(e.get('dominios', [])) or '(sem obra)'
        fh.write(f"* **{c['slug']}** `[{c['persona']}]` × base **{e['slug']}** "
                 f'— {tipo} ({s:.0f}) · ocorre em: {docc}\n')

    if colisao_fraco:
        fh.write('\n### sinal fraco — slug contido (triagem, não veredito)\n\n')
        for c, e, _s, _t in sorted(colisao_fraco, key=lambda x: x[0]['slug']):
            docc = ', '.join(e.get('dominios', [])) or '(sem obra)'
            fh.write(f"* **{c['slug']}** `[{c['persona']}]` ⊂⊃ base **{e['slug']}** · ocorre em: {docc}\n")

print('propostas:', len(propostas))
print('duplicacoes:', len(dup))
print('colisoes:', len(set((c['slug'], e['slug'], t) for c, e, _s, t in colisao)))
print('dominios em b:', sorted(por_dom))
