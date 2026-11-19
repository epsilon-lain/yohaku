"""Finite regression for the A->B terminal block, Python standard library."""
from array import array
from fractions import Fraction
import json
from math import comb
from pathlib import Path

MAX = 65536
N_DIRECT = (4,14,46,78,109,110,111,334,622,1134,8206,16398,20590,32782)

def v2(n):
    assert n
    return (n & -n).bit_length()-1

def denom_bits(N):
    return (12*N+9).bit_length()-1

def exact_small_Y(N):
    M,L = 4*N,8*(N+1)
    b = []
    P,Q = 0,1
    aa = [0]
    for j in range(1,M//2+1):
        P,Q=Q,2*Q+P
        aa.extend((P**2,-P*Q))
    for a in reversed(aa):
        c = [a]+[0]*len(b)
        for j,t in enumerate(b):
            c[j] += t
            c[j+1] -= t
        b=c
    S = sum((Fraction(n*16**(N-k),8*k+j) for k in range(N+1)
             for n,j in ((4,1),(-2,4),(-1,5),(-1,6))),Fraction(0))
    return S+sum(Fraction(t,L+k+1) for k,t in enumerate(b))

def direct(N):
    """Uses successive Beta ratios and Pell, not 12-term deltas or factorial tables."""
    M,L = 4*N,8*(N+1)
    d = denom_bits(N)
    r = 2*d+1
    mod = 1<<r
    mask = mod-1
    P,Q = 0,1
    U,E = pow(L+1,-1,mod),0
    total = 0
    for k in range(1,M+1):
        n,t = k,L+k+1
        vn,vt = v2(n),v2(t)
        E += vn-vt
        U = (U*(n>>vn)*pow(t>>vt,-1,mod)) & mask
        assert E+d>=0
        if k&1:
            P,Q = Q,(2*Q+P)&mask
            ak = P*P
        else:
            ak = -P*Q
        total = (total+((ak*U)<<(E+d)))&mask
    for j in range(min(N,(r-1)//4)+1):
        i=N-j
        for n,t in ((4,8*i+1),(-1,8*i+5),(-(3*i+2),(2*i+1)*(4*i+3))):
            total = (total+((n*pow(t,-1,mod))<<(d+4*j)))&mask
    return total

def scan():
    D = denom_bits(MAX)
    R = 2*D+1
    mod = 1<<R
    mask = mod-1
    end = 12*MAX+9
    u = array('Q',[1])*(end+1)
    ui = array('Q',[1])*(end+1)
    for i in range(1,end+1):
        u[i] = (u[i-1]*(i>>v2(i)))&mask
    ui[end] = pow(u[end],-1,mod)
    for i in range(end,0,-1):
        ui[i-1] = (ui[i]*(i>>v2(i)))&mask
    a = array('Q',[0,1,mod-2,4])
    for i in range(4,4*MAX+9):
        a.append((-2*a[-1]-2*a[-3]+a[-4])&mask)
    signed = [(-1)**j*comb(8,j) for j in range(8)]
    Y = ((47*pow(15,-1,mod))<<D)&mask
    last = []
    W = {}
    bad, high = [], []
    peak = -D
    for N in range(1,MAX+1):
        L,K = 8*N,4*N-3
        delta = 0
        for j in range(12):
            k,m = K+j,L+K+j+1
            # v2(L!k!/m!) by Legendre's formula.
            v = D-1+m.bit_count()-L.bit_count()-k.bit_count()
            c = 16*a[k]-sum(signed[l]*a[k-l] for l in range(j-3))
            assert v>=0
            delta = (delta+((c*u[L]*u[k]*ui[m])<<v))&mask
        Y = (16*Y+delta)&mask
        last = [delta]+last[:(R+3)//4-1]
        if N>=4 and (N%2==0 or N in N_DIRECT):
            d = denom_bits(N)
            r = 2*d+1
            modulus = 1<<r
            assert Y%(1<<(D-d))==0
            scaled = (Y>>(D-d))%modulus
            if N%2==0:
                if not scaled:
                    bad.append(N)
                else:
                    val=v2(scaled)-d
                    peak=max(peak,val)
                    if val>=7:
                        high.append([N,val])
            if N in N_DIRECT or not scaled:
                J=(r+3)//4
                # The stress samples have enough terminal terms even at N=4.
                assert len(last)>=J
                sm=0
                pref=[]
                for j in range(J):
                    sm = (sm+(last[j]<<(4*j)))&mask
                    assert sm%(1<<(D-d))==0
                    z=(sm>>(D-d))%modulus
                    pref.append(None if not z else v2(z)-d)
                terminal = (sm>>(D-d))%modulus
                assert terminal==scaled==direct(N)
                W[N]=dict(N=N,M=4*N,d=d,r=r,J=J,terminal=terminal,
                          independent_residue=direct(N),
                          v2Y=None if not scaled else v2(scaled)-d,
                          truncated_prefix_v2=pref)
    return W,bad,high,peak

W,bad,high,peak=scan()
exact=exact_small_Y(14)
assert exact.numerator % 2 == exact.denominator % 2 == 1
assert W[14]["terminal"] == 25216
assert W[110]["terminal"] == 16384 and W[110]["truncated_prefix_v2"]==[-3,3,4,4,4,4]
for s in (13,14,15):
    assert W[(1<<s)+14]["v2Y"]==0
out=dict(format="bbp-sparse-relay-b/1",N_even_min=4,N_even_max=MAX,
         checked_even=MAX//2-1,exact_Y14=[exact.numerator,exact.denominator],
         global_R=2*denom_bits(MAX)+1, v2_max_nonzero=peak,
         v2_at_least_7=high, L0_failures=bad, rows=list(W.values()))
Path("/output/bbp-sparse-relay-b-v1.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
print(json.dumps({k:out[k] for k in ("N_even_min","N_even_max","checked_even","v2_max_nonzero","L0_failures","v2_at_least_7","exact_Y14")}))
