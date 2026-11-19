"""Standard-library independent Fraction regression for the slope-4 terminal block."""
from fractions import Fraction as F
from math import comb
from pathlib import Path
import json

NS = [4, 14, 46, 78, 109, 110, 111, 334, 622, 1134]
M = 4 * max(NS)
A = [0] * (M + 1)
for k in range(M + 1):
    A[k] = (int(k == 1) - (2*A[k-1] if k >= 1 else 0)
            - (2*A[k-3] if k >= 3 else 0) + (A[k-4] if k >= 4 else 0))

def v(x):
    def v_int(a):
        return (a & -a).bit_length() - 1
    return None if x == 0 else v_int(abs(x.numerator)) - v_int(x.denominator)

def direct_y(n):
    L = 8*n + 8
    S = F(0)
    for i in range(n + 1):
        S = (16*S + F(4,8*i+1) - F(2,8*i+4)
             - F(1,8*i+5) - F(1,8*i+6))
    beta = F(1, L+1)
    for k in range(4*n + 1):
        S += A[k]*beta
        beta *= F(k+1,L+k+2)
    return S

def delta(n):
    L0, K = 8*n, 4*n-3
    beta = F(1, (L0+K+1)*comb(L0+K,L0))
    out = F(0)
    for j in range(12):
        H = 16*extra[K+j]
        H -= sum((-1)**ell*comb(8,ell)*
                 extra[K+j-ell]
                 for ell in range(min(8,j-4)+1))
        out += H*beta
        beta *= F(K+j+1,L0+K+j+2)
    return out

extra = dict(enumerate(A))
for k in range(M+1,M+9):
    extra[k] = -2*extra[k-1]-2*extra[k-3]+extra[k-4]

def residue(q,r):
    assert q.denominator % 2
    return q.numerator*pow(q.denominator,-1,1<<r) % (1<<r)

rows = []
for n in NS:
    y, prev = direct_y(n), direct_y(n-1)
    d = (12*n+9).bit_length()-1
    r, J = 2*d+1, min(n,(2*d+4)//4)
    assert delta(n) == y-16*prev
    sums, val = F(0), []
    for j in range(J):
        sums += 16**j*delta(n-j)
        val.append(v(sums))
    if J == n:
        sums += 16**n*direct_y(0)
    unit = residue(2**d*sums,r)
    assert unit == residue(2**d*y,r) and unit != 0
    rows.append(dict(N=n,M=4*n,d=d,r=r,J=J,vY=v(y),vPrev=v(prev),
                     vDelta=v(delta(n)),vPartial=val,residue=unit))
report = dict(method="direct Beta recurrence versus 12-term signed Beta moments",
              sample=NS,rows=rows,scope="finite only")
print(json.dumps(report,sort_keys=True))
Path("/output/bbp-sparse-a-terminal-v1.json").write_text(
    json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
