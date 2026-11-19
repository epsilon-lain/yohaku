"""Independent finite-domain check of the new-prime Frobenius formula."""
from hashlib import sha256
from math import comb, sqrt
from pathlib import Path
import json
from sys import argv

def add(a,b,p):
    return ((a[0]+b[0])%p,(a[1]+b[1])%p)

def mul(a,b,p,s):
    return ((a[0]*b[0]+s*a[1]*b[1])%p,(a[0]*b[1]+a[1]*b[0])%p)

def power(a,k,p,s):
    ans=(1,0)
    while k:
        if k&1:
            ans=mul(ans,a,p,s)
        k>>=1
        if k:
            a=mul(a,a,p,s)
    return ans

def a_exact(m):
    a=[0]*(m+1)
    for k in range(1,m+1):
        a[k]=int(k==1)-2*a[k-1]-(2*a[k-3] if k>=3 else 0)+(a[k-4] if k>=4 else 0)
    return a

def inverses(n,p):
    inv=[0]+[1]*n
    for j in range(2,n+1):
        inv[j]=(- (p//j)*inv[p%j])%p
    return inv

def binoms(l,d,p,inv):
    cs=[1]
    for j in range(1,d+1):
        cs.append(cs[-1]*(l+1-j)*inv[j]%p)
    return cs

def quad(l,p,s,base,base_inv,weight,cs):
    # In F_p[T]/(T^2-s), evaluations at conjugate roots take the trace 2*constant.
    frob=power(base,p,p,s)
    al=mul(weight,mul(power(base_inv,l+1,p,s),frob,p,s),p,s)
    minus_base=((-base[0])%p,(-base[1])%p)
    h=(0,0)
    for c in reversed(cs):
        h=add((c,0),mul(minus_base,h,p,s),p)
    return 2*mul(al,h,p,s)[0]

def verify(n,m,ptab):
    l=8*n+8
    d=l+m+1
    assert m<l
    a=a_exact(m)
    rows=[]
    cmp=[]
    for p in ptab:
        if p<=l:
            continue
        if p>d:
            break
        j=p-l-1
        ds=d-p
        inv=inverses(ds,p)
        cs=binoms(l,ds,p,inv)
        # 8*A_lambda = lambda for real pair, 1-lambda for imaginary pair.
        x=quad(l,p,2,(-1,1),(1,1),(-1,1),cs)
        y=quad(l,p,-1,(0,1),(0,-1),(1,-1),cs)
        signed=-1 if j%2 else 1
        b=signed*(x+y)*pow(8,-1,p)%p
        # Compare to the original binomial sum (recurring C(j+r,r) independently).
        old=0
        c=1
        for r in range(ds+1):
            old=(old+c*(a[j+r]%p))%p
            if r<ds:
                c=c*(j+r+1)*inv[r+1]%p
        assert b==signed*old%p
        res=b*pow(16,-n,p)%p
        rows.append({"p":p,"j":j,"b_mod_p":b,"scaled_residue":res})
        cmp.append(f"{p}:{res}")
    return {"n":n,"m":m,"rows":rows,"tested":len(rows),
            "zeros":[v for v in rows if not v["b_mod_p"]],
            "scalar_digest":sha256(",".join(cmp).encode("ascii")).hexdigest()}

def primes(k):
    flags=bytearray([1])*(k+1)
    for i in range(2,int(sqrt(k))+1):
        if flags[i]:
            flags[i*i:k+1:i]=bytes((k-i*i)//i+1)
    return [i for i in range(2,k+1) if flags[i]]

def main():
    grid=[(320,1810),(1,13),(24,135),(64,362),(100,565),(320,1809),(320,1811),(512,2896),(640,3620)]
    ps=primes(max(8*n+9+m for n,m in grid))
    result=[verify(n,m,ps) for n,m in grid]
    path=Path(argv[1]) if len(argv)>1 else Path("/output/bbp-odd-20261119-b-frobenius.json")
    path.write_text(json.dumps({"cases":result},indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{k:v for k,v in r.items() if k!="rows"} for r in result],sort_keys=True))

if __name__=="__main__":
    main()
