"""Exact B-team BBP y=1-x regression. Python standard library only."""
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from math import comb, gcd
import json
from pathlib import Path
from sys import argv

A = ((1, 4), (4, -2), (5, -1), (6, -1))

def primes_up_to(d):
    flag = bytearray([1]) * (d+1)
    flag[:2] = bytes(2)
    for k in range(2, d+1):
        if flag[k]:
            yield k
            flag[k*k:d+1:k] = bytes(max(0, (d-k*k)//k + 1))

def ab(m):
    a = []
    for k in range(m+1):
        prev = lambda d: a[k-d] if k >= d else 0
        a.append(int(k == 1) - 2*prev(1) - 2*prev(3) + prev(4))
    b = [0] * (m+1)
    for k, x in enumerate(a):
        for j in range(k+1):
            b[j] += (-1 if j%2 else 1) * comb(k,j) * x
    return a,b

def alt_a(m):
    # h(y) = y (1+2y-y^2)^(-1)(1+y^2)^(-1), no use of the same order-4 recurrence.
    u = [1,-2]
    for k in range(2,m):
        u.append(u[-2]-2*u[-1])
    return [0] + [sum((-1)**j * u[k-1-2*j] for j in range((k+1)//2))
                  for k in range(1,m+1)]

def direct(n,m,l):
    # No b_j and no local residues: integrate original y monomials by factorial ratios.
    a = alt_a(m)
    s = sum(Fraction(c, (16**k)*(8*k+r)) for k in range(n+1) for r,c in A)
    beta = Fraction(1,l+1); corr = Fraction(0)
    for k,ak in enumerate(a):
        corr += ak * beta
        beta *= Fraction(k+1,l+k+2)
    return s + corr / 16**n, a

def p_part(p,n,l,b):
    orig = 0
    for r,c in A:
        # p odd, the unique k residue is invertible modulo p.
        for k in range((-r*pow(8,-1,p))%p,n+1,p):
            d = 8*k+r
            orig += c * pow(16,-k,p) * pow(d//p,-1,p)
    corr = sum(b[j] * pow((l+j+1)//p,-1,p)
               for j in range((-l-1)%p,len(b),p))
    return orig%p, (corr*pow(16,-n,p))%p

def audit(n,m,expanded=False):
    l=8*n+8
    d=l+m+1
    a,b=ab(m)
    exact,alt=direct(n,m,l)
    assert a == alt
    q=exact.denominator
    assert gcd(q,exact.numerator)==1
    v2=(q & -q).bit_length()-1
    assert v2 <= 4*n+d.bit_length()-1
    reduced=q
    product=1
    records=[]
    zero_new=[]
    new_tested=0
    for p in primes_up_to(d):
        if p==2 or p*p <= d:
            while reduced%p == 0:
                reduced//=p
            continue
        orig,corr=p_part(p,n,l,b)
        residual=(orig+corr)%p
        keep=q%p==0
        assert keep == bool(residual)
        if keep:
            assert q%(p*p)!=0
            reduced//=p
            product*=p
        is_new=l<p and m<l
        if is_new:
            j=p-l-1
            assert orig==0 and 0<=j<=m
            assert residual==b[j]*pow(16,-n,p)%p
            new_tested+=1
            if not residual:
                zero_new.append({"n":n,"m":m,"p":p,"j":j,"b_mod_p":b[j]%p,"v_p_Q":int(keep)})
        if expanded:
            records.append({"p":p,"orig":orig,"corr":corr,"residue":residual,"kept":keep,"new_singleton":is_new})
    assert reduced==1
    head={"n":n,"m":m,"l":l,"d":d,"v2":v2,"new_primes_checked":new_tested}
    if expanded:
        odd=q>>v2
        with localcontext() as ctx:
            ctx.prec=70
            head["log_odd_per_n"] = str(Decimal(odd).ln()/n)
            head["log_large_retained_per_n"] = str(Decimal(product).ln()/n)
            head["log_new_kept_per_n"] = str(sum(Decimal(r["p"]).ln() for r in records if r["new_singleton"] and r["kept"])/n)
        head.update({"denominator":str(q),"denominator_decimal_sha256":sha256(str(q).encode("ascii")).hexdigest(),
                     "numerator":str(exact.numerator),"odd_denominator":str(odd),"local_prime_checks":records})
    return head,zero_new

def main():
    baseline,zero=audit(320,1810,True)
    # All 2400 pairs 0<=N<=23, 0<=M<=L-1 (each uses direct fraction + residues).
    cases=0
    extra=[]
    for n in range(24):
        for m in range(8*n+8):
            _, z = audit(n,m)
            cases+=1
            extra.extend(z)
    # General local criterion is also exercised outside M<L.
    outside=[(0,8),(0,20),(1,17),(3,54),(7,80),(17,181)]
    for n,m in outside:
        audit(n,m)
    finite={"small_M_lt_L_cases":cases,"small_ranges":{"N":[0,23],"M":"0..8N+7"},
            "outside_M_lt_L":outside,"zero_new_baseline":zero,"zero_new_scan":extra,
            "baseline":baseline}
    dst=Path(argv[1]) if len(argv)>1 else Path("/output/bbp-odd-20261119-b.json")
    dst.write_text(json.dumps(finite,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in baseline.items() if k not in ("denominator","numerator","odd_denominator","local_prime_checks")},sort_keys=True))
    print(json.dumps({"cases":cases,"extra_cases":len(outside),"large_prime_checks":len(baseline["local_prime_checks"]),
                      "zeros_baseline":zero,"zeros_scan_count":len(extra),"first_zeros_scan":extra[:5]},sort_keys=True))

if __name__=="__main__":
    main()
