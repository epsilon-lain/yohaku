"""Exact proof regressions; JSON records original column sets, determinants and strict bounds."""
from fractions import Fraction as Q
from itertools import permutations
from math import comb, factorial
import json, hashlib
from pathlib import Path

P=1009
I=469
assert I*I%P==P-1 and all(P%d for d in range(2,32))
R1=44*I*pow(7,-1,P)%P
R2=710*I*pow(113,-1,P)%P
TOP=[11,11,11,10,8,6,4,2,0]
def rows(H):
    return [(j,s,a,b) for j in range(3) for s in range(H)
            for b in range((H-s-1)//20+1) for a in range((H-s-20*b-1)//8+1)]
def cols(H):
    n=H-16
    return sorted([(h,A,B) for h in range(n) for B in range((H-h-1)//20+1)
                   for A in range(3*((H-h-20*B-1)//8+1))]
                  +[(n+h,A,0) for A,k in enumerate(TOP) for h in range(k+1)],
                  key=lambda c:(c[0],c[2],c[1]))
def orig(H,cc):
    facinv=[pow(factorial(k),-1,P) for k in range(H)]
    rr=rows(H)
    def coefficient(r,c):
        j,s,a,b=r; h,A,B=c
        if A<a or B<b: return 0
        return comb(A,a)*comb(B,b)*sum(comb(A-a,i)*comb(B-b,k)
            *pow(j*R1,A-a-i,P)*pow(j*R2,B-b-k,P)
            *pow(h,s-i-k,P)*facinv[s-i-k]
            for i in range(min(s,A-a)+1) for k in range(min(s-i,B-b)+1))%P
    return [[coefficient(r,c) for c in cc] for r in rr]
def modelim(a):
    a=[row[:] for row in a]; k=0; p=[]; d=1
    for i in range(len(a[0])):
        j=next((j for j in range(k,len(a)) if a[j][i]),None)
        if j is None: continue
        if j!=k: a[j],a[k]=a[k],a[j]; d=-d
        x=a[k][i]; d=d*x%P; p.append((i,j,x))
        v=pow(x,-1,P)
        for ell in range(k+1,len(a)):
            if not a[ell][i]: continue
            f=a[ell][i]*v%P
            a[ell][i:]=[(z-f*y)%P for y,z in zip(a[k][i:],a[ell][i:])]
        k+=1
        if k==len(a): break
    return k,d,p
def det(a):
    a=[list(map(Q,row)) for row in a]; d=Q(1)
    for i in range(len(a)):
        j=next((j for j in range(i,len(a)) if a[j][i]),None)
        if j is None:return Q(0)
        if i!=j:a[i],a[j]=a[j],a[i];d=-d
        v=a[i][i];d*=v
        for k in range(i+1,len(a)):
            f=a[k][i]/v
            if f:a[k][i:]=[z-f*y for z,y in zip(a[k][i:],a[i][i:])]
    return d
def rank(a):
    a=[list(map(Q,row)) for row in a];k=0
    for i in range(len(a[0])):
        j=next((j for j in range(k,len(a)) if a[j][i]),None)
        if j is None:continue
        a[j],a[k]=a[k],a[j];v=a[k][i]
        for l in range(k+1,len(a)):
            f=a[l][i]/v
            if f:a[l][i:]=[z-f*y for z,y in zip(a[l][i:],a[k][i:])]
        k+=1
        if k==len(a):break
    return k
def gmul(a,b):return (a[0]*b[0]-a[1]*b[1],a[0]*b[1]+a[1]*b[0])
six=[(0,3,0),(3,0,0),(1,2,0),(1,0,0),(1,1,1),(2,1,0)]
g=[]
for j in range(3):
    g.append([(Q(j**(A+B)),0) for h,A,B in six])
    g.append([(Q(h*j**(A+B)),-(A*Q(7,44)+B*Q(113,710))*j**(A+B-1) if A+B else 0)
              for h,A,B in six])
v0,v1=Q(0),Q(0)
for pp in permutations(range(6)):
    z=(Q((-1)**sum(pp[i]>pp[j] for i in range(6) for j in range(i+1,6))),Q(0))
    for i in range(6):z=gmul(z,g[i][pp[i]])
    v0+=z[0];v1+=z[1]
assert (v0,v1)==(Q(-21,85910),Q(6,3905))
# Local transverse variables at U are independent; only z differentiates in s.
def U_six(edges):
    return [[comb(d,s)*j**(a+b+d-s) if d>=s else 0 for a,b,d in edges]
             for j in range(3) for s in [0,1]]
def C_six(edges):
    return [[comb(A,a)*comb(B,b)*Q(h**k,factorial(k)) if k>=0 and a<=A and b<=B else Q(0)
              for h,A,B in six for k in [d-A-B+a+b]] for a,b,d in edges]
def matmatch(a):
    n=len(a);return any(all(a[i][p[i]] for i in range(n)) for p in permutations(range(n)))
def costs(e):return [sum(4*a+10*b for a,b,d in e),sum(d for a,b,d in e)]
E=[[(0,0,d) for d in range(6)], [(0,0,d) for d in range(5)]+[(1,0,0)],
   [(0,0,d) for d in range(5)]+[(1,0,1)],
   [(0,0,d) for d in [0,1,2,3,5]]+[(1,0,0)]]
S=[]
for idx,e in enumerate(E):
    u,c=U_six(e),C_six(e)
    U,C=det(u),det(c)
    groups=[list(range(6))] if idx==0 else [list(range(5)),[5]]
    G=[(rank([[row[k] for k in gr] for row in u]),rank([c[k] for k in gr])) for gr in groups]
    S.append(dict(edges=e,cost=costs(e),dU=str(U),dC=str(C),groups=G,match=[matmatch(u),matmatch(c)]))
assert S[0]["match"]==[True,True] and S[0]["dC"]=="0"
assert S[1]["match"]==[True,True] and S[1]["groups"]==[(5,5),(1,1)] and S[1]["dC"]=="0"
assert S[2]["dU"]=="-24" and S[2]["dC"]=="2/3"
# Any all-zero horizontal assignment fails C by the duplicate columns (h,A+B)=(1,2).
# Below 4+11lambda only one e1 is possible, with required time sum >=10.
lo=sum((Q(1,(2*k+1)*3**(2*k+1)) for k in range(40)),Q(0))
hi=lo+Q(9,8*81*3**81)
assert Q(1,3)<lo<hi<Q(7,20)
assert 15*hi<4+10*lo and 4+11*hi<8
# Endpoint certificates: Hermite degree lower/upper and all cost inequalities.
def interp(L):
    n=3*L
    a=[[Q(comb(k,s)*j**(k-s) if k>=s else 0) for k in range(n)]+[Q(j if s==0 else 0)]
       for j in range(3) for s in range(L)]
    for i in range(n):
        j=next(j for j in range(i,n) if a[j][i]);a[j],a[i]=a[i],a[j]
        v=a[i][i];a[i][i:]=[q/v for q in a[i][i:]]
        for j in range(i+1,n):
            v=a[j][i]
            if v:a[j][i:]=[z-v*y for y,z in zip(a[i][i:],a[j][i:])]
    c=[Q(0)]*n
    for i in range(n-1,-1,-1):c[i]=a[i][-1]-sum(a[i][k]*c[k] for k in range(i+1,n))
    for j in range(3):
        for s in range(L):
            assert sum(c[k]*comb(k,s)*j**(k-s) for k in range(s,n))==(j if s==0 else 0)
    assert c[-1];return [str(x) for x in c]
h8,h20=interp(8),interp(20)
gam=Q(30,59);T=Q(127,250)
assert Q(10,59)<Q(4,23)<lo and T<gam
assert 23*lo/8>gam and Q(236,23*20)>gam
assert (34/hi-64)*(T-Q(1,2))**4/4>Q(33,10**9)
orig_results=[]
for H in [16,17,24,32]:
    cc=cols(H);assert len(cc)==len(rows(H)) and all(h+2*a+5*b<=H for h,a,b in cc)
    if H>16:
        D={(a,b) for h,a,b in cc}
        assert D=={(a,b) for b in range((H-1)//20+1) for a in range(3*((H-20*b-1)//8+1))}
    k,d,piv= modelim(orig(H,cc));assert k==len(cc)
    if H==16:assert d==973
    orig_results.append(dict(H=H,rows=rows(H),cols=cc,rank=k,det_mod=d,pivots=piv))
result=dict(parameters=dict(p=P,i=I,r1=R1,r2=R2,w=[2,5],H_top=16,v0=1,theta="1/4",F0=9),
    original=orig_results, six=dict(H=8,v0=7,cols=six,orig_det_normalized=[str(v0),str(v1)],
    minima=[[0,15],[4,10],[4,11]],witnesses=S),
    hermite={"8":h8,"20":h20},gamma=str(gam),T=str(T),lambda_lo=str(lo),lambda_hi=str(hi),
    rank_cost_increment_strict_lower="33/10^9", finite_scope_only=True)
payload=(json.dumps(result,indent=2)+"\n").encode()
Path("/output/mixed_rank_a_exact_v1.json").write_bytes(payload)
print(json.dumps(dict(sha256=hashlib.sha256(payload).hexdigest(),orig=[[v["H"],v["rank"],v["det_mod"]]
    for v in orig_results],six=S,hermite_leading=[h8[-1],h20[-1]])))
