from fractions import Fraction as F
import json

def alt_sum(k, n):
    return sum((F((-1)**j, (2*j+1)*k**(2*j+1)) for j in range(n)), F(0))

def alt_interval(k, n):
    s = alt_sum(k, n)
    t = s + F((-1)**n, (2*n+1)*k**(2*n+1))
    return min(s, t), max(s, t)

def pi_interval(n, m):
    a, b = alt_interval(5, n)
    c, d = alt_interval(239, m)
    return 16*a - 4*d, 16*b - 4*c

def E_bounds(p, q, lo, hi):
    vals = [q*(q*lo-p), q*(q*hi-p)]
    assert vals[0] * vals[1] > 0
    return min(map(abs, vals)), max(map(abs, vals))

def update(best, p, q, lo, hi):
    u, v = E_bounds(p, q, lo, hi)
    if best is None or v < best[0]:
        return u, v, p, q
    assert u > best[1] or (p, q) == best[2:]
    return best

def common_convergents(lo, hi, Q):
    p0, p1, q0, q1 = 0, 1, 1, 0
    while True:
        a = lo.numerator // lo.denominator
        ah = hi.numerator // hi.denominator
        assert a == ah and lo > a
        p0, p1 = p1, a*p1+p0
        q0, q1 = q1, a*q1+q0
        if q1 > Q:
            return q1
        yield a, p1, q1
        lo, hi = 1/(hi-a), 1/(lo-a)

def decimal_outward(lo, hi, digits):
    d = 10**digits
    return dict(divisor=str(d), lo=str((lo*d).__floor__()),
                hi=str((hi*d).__ceil__()))

def report(best):
    lo, hi, p, q = best
    return dict(p=str(p), q=str(q), E=decimal_outward(lo, hi, 22))

N, M = 160, 55
lo, hi = pi_interval(N, M)
assert 3 < lo < hi < 4
q_small, q_big = 10_000, 10**80
assert hi-lo < F(1, 10**205)
assert (hi-lo)*q_big*q_big < F(1, 10**45)

small = None
for q in range(1, q_small+1):
    p = (q*lo+F(1,2)).__floor__()
    assert p == (q*hi+F(1,2)).__floor__()
    small = update(small, p, q, lo, hi)

it = common_convergents(lo, hi, q_big)
n, max_a, biggest, cf_small = 0, None, None, None
while True:
    try:
        a,p,q = next(it)
    except StopIteration as stop:
        next_q = stop.value
        break
    if n>0 and (max_a is None or a > max_a[0]):
        max_a = [a,n,str(q)]
    if q <= q_small:
        cf_small = update(cf_small, p, q, lo, hi)
    biggest = update(biggest, p, q, lo, hi)
    n += 1
assert small == cf_small
assert next_q > q_big

def vp(k, p):
    j=0
    while k % p == 0:
        k //= p
        j+=1
    return j

spar = []
for h in range(4):
    L = 5**h
    T = (L+1)//2
    r = 16*alt_sum(5, T)-4*alt_sum(239,T)
    assert vp(r.denominator,5) == L+h
    u, v = E_bounds(r.numerator, r.denominator, lo, hi)
    assert u > F(8*5**(L+2*h),25*(L+2))
    spar.append(dict(h=h,L=L,N=T,v5q=L+h,
                    q_bits=r.denominator.bit_length(),
                    floor_log10_E=len(str(u.__floor__()))-1))

print(json.dumps(dict(
    arctan_terms=[N,M], pi_width_upper="1e-205",
    exhaustive_qmax=q_small, exhaustive_min=report(small),
    cf_qmax=str(q_big), cf_min=report(biggest),
    certified_convergents=n, next_q=str(next_q),
    largest_a_in_certified_prefix=max_a, sparse_failure_check=spar
), ensure_ascii=False))
