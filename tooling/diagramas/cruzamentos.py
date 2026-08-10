import re,sys
def segs(p):
    s=open(p,encoding='utf-8').read()
    out=[]
    for d in re.findall(r'<path[^>]*\bd="([^"]+)"',s):
        pts=[(float(a),float(b)) for a,b in re.findall(r'(-?\d+\.?\d*)[ ,](-?\d+\.?\d*)',d)]
        if len(pts)>1: out.append([(pts[i],pts[i+1]) for i in range(len(pts)-1)])
    return out
def cross(a,b,c,d):
    def o(p,q,r): return (q[1]-p[1])*(r[0]-q[0])-(q[0]-p[0])*(r[1]-q[1])
    o1,o2,o3,o4=o(a,b,c),o(a,b,d),o(c,d,a),o(c,d,b)
    return (o1>0)!=(o2>0) and (o3>0)!=(o4>0)
P=segs(sys.argv[1]); n=0
for i in range(len(P)):
    for j in range(i+1,len(P)):
        if any(cross(*s1,*s2) for s1 in P[i] for s2 in P[j]): n+=1
print(f"{sys.argv[2]:22s} {len(P):3d} tracados  |  pares que se cruzam: {n}")
