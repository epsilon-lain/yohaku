"""Independent finite nonzero-minor witnesses for the conditional U prefix rank."""
from fractions import Fraction as Q
from math import comb
from itertools import product
from pathlib import Path
import json

L=sum((Q(1,(2*k+1)*3**(2*k+1)) for k in range(28)),Q(0))
Lhi=L+Q(9,8*57*3**57)
K=3
w=(2,5)
v=7
T=(3,7)
Hlist=(7,12,16,22)
thresholds=tuple(map(Q,('0','1/4','1/2','3/4','1','5/4')))
P=((22,7),(355,113))
def wa(a): return sum(x*y for x,y in zip(w,a))
def le(a,d,c):
    if 2*wa(a)+d*Lhi<=c: return True
    assert 2*wa(a)+d*L>c
    return False
def mul(f,g,p):
    return [sum(f[k]*g[n-k] for k in range(n+1))%p for n in range(len(f))]
def powers(f,n,p):
    v=[[1]+[0]*(len(f)-1)]
    for j in range(n): v.append(mul(v[-1],f,p))
    return v
def rows_matrix(rows,edges,p,O):
    im=next(i for i in range(1,p) if i*i%p==p-1)
    ma=tuple(max(a[k] for a,d in edges) for k in range(2))
    md=max(d for a,d in edges)
    U=[]
    for j,s,b in rows:
        log=[0]+[((-1)**(k+1)*pow(k,-1,p))%p for k in range(1,s+1)]
        z=log[:];z[0]=j*O%p
        zp=powers(z,md,p)
        v=[]
        for (num,den),tau,amax in zip(P,T,ma):
            f=[j*(2*im*num*pow(den,-1,p)-O)%p]+[0 if k<tau else -log[k] for k in range(1,s+1)]
            v.append(powers(f,amax,p))
        ur=[]
        for a,d in edges:
            if min(x-y for x,y in zip(a,b))<0:
                ur.append(0)
            else:
                co=comb(a[0],b[0])*comb(a[1],b[1])
                f=mul(v[0][a[0]-b[0]],v[1][a[1]-b[1]],p)
                ur.append(co*mul(f,zp[d],p)[s]%p)
        U.append(ur)
    return U

def elim(U,p):
    B=[r[:] for r in U]
    ids=list(range(len(B)))
    pivotcols=[];rank=0
    for c in range(len(B[0])):
        z=next((z for z in range(rank,len(B)) if B[z][c]),None)
        if z is None: continue
        ids[rank],ids[z]=ids[z],ids[rank]
        B[rank],B[z]=B[z],B[rank]
        v=pow(B[rank][c],-1,p)
        for k in range(rank+1,len(B)):
            t=B[k][c]*v%p
            if t: B[k]=[(a-t*b)%p for a,b in zip(B[k],B[rank])]
        pivotcols.append(c)
        rank+=1
        if rank==len(B): break
    return rank,ids[:rank],pivotcols

def main():
    out=[]
    assert all(Lhi*(K*z-1)<=2*w_i for z,w_i in zip((2,3),w))
    for H in Hlist:
        aa=[a for a in product(range(H//2+1),range(H//5+1)) if wa(a)<=H]
        rows=[(j,s,b) for j in range(K) for s in range(H//v+1)
              for b in aa if v*s+4*wa(b)<H]
        emax=[(a,d) for a in aa for d in range(int(H*max(thresholds)/L)+1)
              if le(a,d,H*max(thresholds))]
        Us=[(p,O,rows_matrix(rows,emax,p,O)) for p,O in [(1009,17),(1013,19)]]
        for x in thresholds:
            cs=[k for k,(a,d) in enumerate(emax) if le(a,d,x*H)]
            es=[emax[c] for c in cs]
            pred=sum(v*(d//K)+4*wa(a)<H for a,d in es)
            for p,O,U in Us:
                r,rs,cc=elim([[row[k] for k in cs] for row in U],p)
                assert r==pred,(H,x,p,r,pred)
                out.append(dict(H=H,x=str(x),rows=len(rows),edges=len(es),p=p,omega=O,
                                predicted=pred,modular_rank=r,
                                nonzero_minor_rows=[rows[j] for j in rs],
                                nonzero_minor_indices=[es[k] for k in cc]))
    Path('/output/rank_odd_a_prefix_finite.json').write_text(json.dumps({'purpose':
      'Good Gaussian and omega specialization provides a rational-function-field rank lower bound, not a zero certificate.',
         'cases':out},indent=2)+'\n')
    print(json.dumps({'checks':len(out),'matched':all(x['predicted']==x['modular_rank'] for x in out),
        'mathematical_scope':'only listed H, thresholds and specializations'}))
if __name__=='__main__': main()
