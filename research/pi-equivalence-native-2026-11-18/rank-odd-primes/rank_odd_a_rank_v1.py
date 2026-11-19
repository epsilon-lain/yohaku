"""Exact bounded Cauchy--Binet / rank regression (Python standard library)."""
from fractions import Fraction as Q
from itertools import combinations, permutations, product
from math import comb, factorial
from pathlib import Path
import json

# Sparse Q[x,i]/(i^2+1), keyed by (degree in x, power of i in {0,1}); x=omega.
def mono(a=1, d=0, i=0):
    return {(d,i): Q(a)} if a else {}

def add(a,b):
    c=a.copy()
    for k,v in b.items():
        c[k]=c.get(k,0)+v
        if not c[k]: del c[k]
    return c

def scale(a,s):
    return {k:s*v for k,v in a.items()} if s else {}

def mul(a,b):
    c={}
    for (d,i),v in a.items():
        for (e,j),u in b.items():
            h=(d+e,(i+j)%2)
            c[h]=c.get(h,0)+(-1 if i+j==2 else 1)*v*u
    return {k:v for k,v in c.items() if v}

def show(a):
    return [[d,i,str(v)] for (d,i),v in sorted(a.items())]

def series_mul(a,b,s):
    out=[{} for _ in range(s+1)]
    for k in range(s+1):
        for l in range(k+1):
            out[k]=add(out[k],mul(a[l],b[k-l]))
    return out

def with_power(a, f, e, s):
    for _ in range(e):
        a=series_mul(a,f,s)
    return a

P=((22,7),(355,113))
WE=(2,5)
K=3
R=100*K
TH=Q(1,4)
W0=Q(1)
F0=Q(9)
def ceil(a): return -((-a.numerator)//a.denominator)
def cutoffs(v0): return [ceil(F0*w/v0) for w in WE]

def U(row,edge,v0):
    j,s,be=row
    a,d=edge
    if any(x<b for x,b in zip(a,be)): return {}
    ell=[{}]+[mono(Q((-1)**(k+1),k)) for k in range(1,s+1)]
    z=[mono(Q(j,R),1)]+[scale(ell[k],Q(1,R)) for k in range(1,s+1)]
    u=[mono()]+[{} for _ in range(s)]
    u=with_power(u,z,d,s)
    for b,aa,(p,q),T in zip(be,a,P,cutoffs(v0)):
        eps=add(mono(Q(2*j*p,q),0,1),mono(-j,1))
        tail=[eps]+[scale(ell[k],-1) if k>=T else {} for k in range(1,s+1)]
        u=with_power(u,tail,aa-b,s)
        u=[scale(x,comb(aa,b)) for x in u]
    return u[s]

def C(edge,col):
    a,d=edge
    h,al=col
    if any(x>y for x,y in zip(a,al)) or d<sum(al)-sum(a): return {}
    k=d-sum(al)+sum(a)
    u=Q(R**d*h**k,factorial(k))
    for x,y in zip(a,al): u*=comb(y,x)
    return mono(u)

def original(row,col,v0):
    j,s,be=row
    h,al=col
    if any(a<b for a,b in zip(al,be)): return {}
    u=[mono(comb(h,k)) if k<=h else {} for k in range(s+1)]
    for b,a,(p,q),T in zip(be,al,P,cutoffs(v0)):
        v=[mono(Q(2*j*p,q),0,1)]+[mono(Q((-1)**(k+1),k)) if k<T else {} for k in range(1,s+1)]
        u=with_power(u,v,a-b,s)
        u=[scale(x,comb(a,b)) for x in u]
    return u[s]

def det(a):
    n=len(a)
    total={}
    for p in permutations(range(n)):
        sign=(-1)**sum(p[j]>p[k] for j in range(n) for k in range(j+1,n))
        q=mono(sign)
        for j in range(n):
            q=mul(q,a[j][p[j]])
            if not q: break
        total=add(total,q)
    return total

def rank(a):
    for k in range(min(len(a),len(a[0])),0,-1):
        for i in combinations(range(len(a)),k):
            for j in combinations(range(len(a[0])),k):
                if det([[a[x][y] for y in j] for x in i]): return k
    return 0

def match(a):
    if not a: return True
    return any(all(a[j][p[j]] for j in range(len(a))) for p in permutations(range(len(a))))

# lambda=log(2)/2 = arctanh(1/3); rigorous enclosure.
L=sum((Q(1,(2*k+1)*3**(2*k+1)) for k in range(40)),Q(0))
B=L+Q(9,8*81*3**81)
def wc(edges):
    return 2*sum(sum(a[i]*WE[i] for i in range(2)) for a,d in edges),sum(d for a,d in edges)
def bounds(c):
    b,d=c
    return b+L*d,b+B*d
def smaller(a,b):
    if a==b: return False
    la,ua=bounds(a); lb,ub=bounds(b)
    if ua<lb: return True
    assert ub<la,(a,b)
    return False

def candidates(cols,D):
    alphas=sorted({a for h,al in cols for a in product(*(range(y+1) for y in al))})
    return [(a,d) for a in alphas for d in range(D+1)]

def full_rows(H,v0):
    return [(j,s,b) for j in range(K) for b in product(*(range(int(H*TH/w)+1) for w in WE))
            for s in range(int(H/v0)+1) if v0*s+sum(x*y for x,y in zip(b,WE))/TH<H]

def budget_run(label, rows, cols, H, v0, W=None, edges=None):
    assert len(rows)==len(cols) and all(r in full_rows(H,v0) for r in rows)
    assert all(W0*h+sum(a*w for a,w in zip(al,WE))<=H for h,al in cols)
    n=len(rows)
    if W is not None:
        cutoff=int(W/L)
        assert cutoff==int(W/B)
        edges=[e for e in candidates(cols,cutoff) if bounds(wc([e]))[0]<=W]
    uu=[ [U(r,e,v0) for e in edges] for r in rows]
    cc=[ [C(e,p) for p in cols] for e in edges]
    states={x:{'eligible':0,'cost':None,'optimal':[]} for x in ['hall','group','true']}
    subsets=0
    for idx in combinations(range(len(edges)),n):
        es=[edges[k] for k in idx]
        co=wc(es)
        if W is not None:
            lo,hi=bounds(co)
            if lo>W: continue
            assert hi<=W
        subsets+=1
        u=[[row[k] for k in idx] for row in uu]
        c=[cc[k] for k in idx]
        hall=match(u) and match(c)
        if not hall: continue
        groups=[[k for k,(b,d) in enumerate(es) if b==a] for a in sorted({e[0] for e in es})]
        group=all(rank([c[k] for k in g])==len(g)
                  and rank([[row[k] for k in g] for row in u])==len(g) for g in groups)
        du,dc=det(u),det(c)
        true=bool(du and dc)
        assert not true or group
        for t,ok in [('hall',hall),('group',group),('true',true)]:
            if not ok: continue
            z=states[t]
            z['eligible']+=1
            if z['cost'] is None or smaller(co,z['cost']):
                z['cost']=co; z['optimal']=[]
            if co==z['cost']:
                z['optimal'].append({'edges':es,'ranks':[rank(u),rank(c)],
                                     'det_u':show(du),'det_c':show(dc)})
    orig=[[original(r,p,v0) for p in cols] for r in rows]
    return dict(label=label, rows=rows, columns=cols, H=H, v0=str(v0), T=cutoffs(v0),
                column_cost=sum(sum(x*w for x,w in zip(al,WE)) for h,al in cols),
                row_cost=sum(sum(x*w for x,w in zip(be,WE)) for j,s,be in rows),
                covers_full_rows=rows==full_rows(H,v0), original_det=show(det(orig)),
                budget=W, cutoff=None if W is None else cutoff,
                edges=edges, visited_subsets=subsets, minima=states,
                restricted_matrices=None if W is not None else
                    {'u':[[show(x) for x in row] for row in uu],
                     'c':[[show(x) for x in row] for row in cc]})

def cb_run(rows,cols,v0,D,H=7):
    assert all(r in full_rows(H,v0) for r in rows)
    assert all(W0*h+sum(a*w for a,w in zip(al,WE))<=H for h,al in cols)
    es=candidates(cols,D)
    u=[[U(r,e,v0) for e in es] for r in rows]
    c=[[C(e,p) for p in cols] for e in es]
    uc=[[{} for _ in cols] for _ in rows]
    for i in range(len(rows)):
        for j in range(len(cols)):
            for k in range(len(es)):
                uc[i][j]=add(uc[i][j],mul(u[i][k],c[k][j]))
    ans={}
    nz=0
    for ids in combinations(range(len(es)),len(rows)):
        du=det([[r[k] for k in ids] for r in u])
        dc=det([c[k] for k in ids])
        val=mul(du,dc)
        nz+=bool(val)
        ans=add(ans,val)
    assert ans==det(uc)
    return dict(rows=rows,columns=cols,H=H,v0=str(v0),T=cutoffs(v0),D=D,edges=len(es),
                nonzero_terms=nz, determinant=show(ans))

def atan(N,q):
    return sum((Q((-1)**k,(2*k+1)*q**(2*k+1)) for k in range(N)),Q(0))
pi_lo=16*atan(20,5)-4*atan(21,239)
pi_hi=16*atan(21,5)-4*atan(20,239)
assert all(Q(p,q)-Q(1,q*q)<pi_lo<pi_hi<Q(p,q)+Q(1,q*q) for p,q in P)
assert 7>3 and Q(8,3)**2>7 and 3**4<113<Q(8,3)**5
H=7
v0=Q(7)
rows=[(1,0,(0,0)),(2,0,(0,0))]
cols=[(1,(1,0)),(1,(0,1))]
reg=budget_run('specified_two_edges',rows,cols,H,v0,edges=[((1,0),0),((0,1),0)])
two=budget_run('two_rows_all_edges_under_W',rows,cols,H,v0,W=5)
three=budget_run('nonzero_full_row_minor',full_rows(H,v0),[(0,(0,0)),(1,(1,0)),(1,(2,0))],H,v0,W=2)
assert [reg['minima'][k]['cost'] for k in ['hall','group','true']]==[(14,0),(14,0),None]
assert [two['minima'][k]['cost'] for k in ['hall','group','true']]==[(0,3),(4,1),(4,2)]
assert [three['minima'][k]['cost'] for k in ['hall','group','true']]==[(0,3)]*3
assert reg['original_det']==two['original_det']==[] and three['original_det']
cb=[cb_run(rows,cols,v0,d) for d in [0,1,2,4]]
cb += [cb_run([(0,3,(0,0)),(1,1,(1,0))],[(1,(2,0)),(2,(1,1))],Q(7),4,H=22)]
body=dict(note='cost=(integer part, multiplier of log(2)/2); polynomial terms=[degree in omega, degree in i, rational denominator form]',
          P=P,weights=WE,K=K,R=R,theta=str(TH),w0=str(W0),F0=str(F0),
          lambda_bounds=[str(L),str(B)], critical_input_interval_verified=True,
          regressions=[reg,two,three],finite_CB=cb)
Path('/output/rank_odd_a_rank_v1.json').write_text(json.dumps(body,indent=2)+'\n')
print(json.dumps({'cases': [{k:r[k] for k in ('label','original_det','visited_subsets')}
                  | {'minima':{k:v['cost'] for k,v in r['minima'].items()}} for r in [reg,two,three]],
                  'finite_CB_nonzero_terms':[r['nonzero_terms'] for r in cb]},separators=(',',':')))
