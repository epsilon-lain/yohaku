"""Exact BBP carry-window regression, dyadic checkpoints and rational margins."""
from fractions import Fraction as F
from hashlib import sha256
from math import comb, isqrt
from pathlib import Path
import json

def coeff(M):
    a = []
    for k in range(M+1):
        a.append(int(k==1)-2*(a[k-1] if k>=1 else 0)-2*(a[k-3] if k>=3 else 0)+(a[k-4] if k>=4 else 0))
    P = [0,1]
    for n in range(M//2+1):
        P.append(2*P[-1]+P[-2])
    ap = [-P[k//2]*P[k//2+1] if k%2==0 else P[(k+1)//2]**2 for k in range(M+1)]
    assert a==ap
    return a

def v2(n):
    if n==0:
        return None
    return (abs(n)&-abs(n)).bit_length()-1

def reg(N,M,window=True):
    L=8*N+8
    S=sum(((F(4,8*k+1)-F(2,8*k+4)-F(1,8*k+5)-F(1,8*k+6))/16**k
           for k in range(N+1)),F(0))
    a=coeff(M)
    V=F(1,L+1)
    pool=F(0)
    b=[]
    for k in range(M+1):
        pool+=a[k]*V
        V*=F(k+1,L+k+2)
        # Independent substitution P(1-x) via integer Horner, below.
    for ak in reversed(a):
        if not b:
            b=[ak]
        else:
            b=[ak+b[0]]+[b[j]-b[j-1] for j in range(1,len(b))]+[-b[-1]]
    X=S+pool/16**N
    assert X==S+sum((F(b[j],L+j+1) for j in range(M+1)),F(0))/16**N
    Q=X.denominator
    Y=16**N*X
    rows=[]
    if window:
        for p in range((47*N+9)//10,11*N//2+1):
            if p%2==0 or p<3 or any(p%d==0 for d in range(3,isqrt(p)+1,2)): continue
            D=L+M+1
            assert (L//p,M//p,D//p)==(1,0,2) and D<p*p and L+1<2*p
            j=2*p-L-1
            assert 0<=j<=M
            rB=sum(comb(k,j)*a[k] for k in range(j,M+1))*(-1)**j %p
            assert rB==b[j]%p
            r=(4*(p%4==1)+pow(16,-N,p)*rB*pow(2,-1,p))%p
            Z=p*X
            assert Z.denominator%p
            direct=Z.numerator*pow(Z.denominator,-1,p)%p
            assert r==direct and bool(r)==(Q%p==0) and Q%(p*p)!=0
            rows.append({'p':p,'j':j,'p_mod8':p%8,'b_j_mod_p':rB,'formula':r,
                         'direct':direct,'retained':Q%p==0})
    return {'N':N,'M':M,'rows':rows,'count':len(rows),'zero_count':sum(not r['retained'] for r in rows),
            'v2Q':v2(Q),'v2Y':v2(Y.numerator)-v2(Y.denominator),'Q':str(Q),
            'Q_sha256':sha256(str(Q).encode()).hexdigest()}

def ln_box(r,n=46):
    assert r>0
    z=(r-1)/(r+1)
    s=2*sum((z**(2*k+1)/F(2*k+1) for k in range(n)), F(0))
    e=2*abs(z)**(2*n+1)/(F(2*n+1)*(1-z*z))
    return s-e,s+e

def add(*boxes):
    return sum(x[0] for x in boxes),sum(x[1] for x in boxes)

def scale(k,box):
    return tuple(sorted((k*box[0],k*box[1])))

def margin():
    d=10**24
    a=isqrt(2*d*d)
    rt=F(a,d),F(a+1,d)
    c=ln_box(1+rt[0])[0],ln_box(1+rt[1])[1]
    # B(t)=8 ln(1+t/8)+t ln(1+8/t).
    def D(t):
        return add((12+F(5,2)*t,)*2,scale(-4,ln_box(F(2))),
                   scale(-24,ln_box(1+t/8)),scale(-3*t,ln_box(1+8/t)),scale(t,c))
    def Dp(t):
        return add((F(5,2),)*2,scale(-3,ln_box(1+8/t)),c)
    tminlo,tminhi=F(383,100),F(384,100)
    mid=(tminlo+tminhi)/2
    assert Dp(tminlo)[1]<0<Dp(tminhi)[0]
    # Convex tangent at mid, and minimum occurs in the bracket.
    mp=Dp(mid)
    dlow=D(mid)[0]-max(abs(p) for p in mp)*(tminhi-tminlo)/2
    assert dlow>F(-17,100)
    assert D(F(4))[0]>F(-161605,10**6) and D(F(4))[1]<F(-161604,10**6)
    dcrit=(D(4*rt[0])[0],D(4*rt[1])[1]) # D increasing above tminhi
    assert dcrit[0]>F(56274313749,10**11)
    assert ln_box(F(2))[0]/8>F(17,200)
    unit=10**18
    def outward(lo,hi):
        return [str(F(lo*unit//1,unit)),str(F(-((-hi*unit)//1),unit))]
    return {'D4':outward(*D(F(4))),'D_critical':outward(*dcrit),
            'D_global_lower':str(F(dlow*unit//1,unit)),'D_global_lower_floor_1e6':dlow*10**6//1,
            'minimizer_bracket':[str(tminlo),str(tminhi)]}

def main():
    baselines=[reg(N,M) for N in [40,80,160,240] for M in [31*N//10,4*N,46*N//10]]
    dyadic=[]
    for h in range(1,8):
        N=2**h-1
        for d in range(-3,5):
            if 4*N+d<1:continue
            x=reg(N,4*N+d,False)
            if x['M']%8 in [1,2,3,4]:
                assert x['v2Q']==4*N+1
            dyadic.append({k:v for k,v in x.items() if k not in ['rows','Q']})
    edges=[reg(N,4*N+d,False) for N in [3,7,15,31,63,127] for d in [0,1,2,3]]
    # Exact difference-v2 certificate discussed in the text is computed by X via
    # an independently checked beta recurrence; no inference from samples to infinite ranges.
    summary=[{k:v for k,v in x.items() if k not in ['rows','Q']} for x in baselines]
    result={'baselines':baselines,'dyadic':dyadic,'dyadic_four_consecutive':[{
        k:v for k,v in x.items() if k not in ['rows','Q']} for x in edges],
        'total_window':sum(x['count'] for x in baselines),
        'window_zero_count':sum(x['zero_count'] for x in baselines),'margin':margin()}
    dst=Path('/output/bbp-mixed-carry-b-v1.json')
    dst.write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'summary':summary,'total_window':result['total_window'],
                      'zeros':result['window_zero_count'],
                      'D_global_lower_floor_1e6':result['margin']['D_global_lower_floor_1e6']},sort_keys=True))
if __name__=='__main__':
    main()
