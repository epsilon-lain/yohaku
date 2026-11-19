"""Finite checks for the exact decomposition and explicit simultaneous basis."""
from fractions import Fraction
from math import comb, factorial

PRIME = 1009
TOP_LIMITS = (11, 11, 11, 10, 8, 6, 4, 2, 0)


def det_mod(matrix):
    if not matrix:
        return 1
    rows = [[value % PRIME for value in row] for row in matrix]
    size = len(rows)
    assert all(len(row) == size for row in rows)
    det = 1
    for col in range(size):
        pivot = next((i for i in range(col, size) if rows[i][col]), None)
        if pivot is None:
            return 0
        if pivot != col:
            rows[col], rows[pivot] = rows[pivot], rows[col]
            det = -det
        lead = rows[col][col]
        det = det * lead % PRIME
        inverse = pow(lead, -1, PRIME)
        for i in range(col + 1, size):
            if rows[i][col]:
                factor = rows[i][col] * inverse % PRIME
                for j in range(col + 1, size):
                    rows[i][j] = (rows[i][j] - factor * rows[col][j]) % PRIME
    return det


def pure(k):
    return [(a, d) for a in range(3*((k+7)//8))
            for d in range(k-8*(a//3))]


def top_columns():
    return [(a, h) for a, limit in enumerate(TOP_LIMITS) for h in range(limit + 1)]


def source(k, patch):
    if not patch:
        return pure(k)
    n = k-16
    return ([(a,h) for a,h in pure(k) if h<n]
            + [(a,h+n) for a,h in top_columns()])


def c_entry(index, column):
    a, d = index
    cap, h = column
    power = d-cap+a
    if not (a <= cap and power >= 0):
        return 0
    return comb(cap,a)*pow(h,power,PRIME)*pow(factorial(power),-1,PRIME) % PRIME


def u_entry(row, index):
    j, beta, s = row
    a, d = index
    if a < beta or d < s:
        return 0
    return comb(a,beta)*comb(d,s)*pow(j,a-beta+d-s,PRIME) % PRIME


def check_blocks():
    top = [[c_entry(e, col) for col in top_columns()] for e in pure(16)]
    value = det_mod(top)
    assert value, "universal top Taylor minor vanished"
    for k in (1, 6, 8, 9, 12, 16, 17, 20, 24, 26, 30):
        indices = pure(k)
        rows = [(j,b,s) for j in range(3) for b in range((k+7)//8)
                for s in range(k-8*b)]
        assert det_mod([[u_entry(row,e) for e in indices] for row in rows])
        for patch in ([False,True] if k>=16 else [False]):
            columns = source(k,patch)
            assert det_mod([[c_entry(e,col) for col in columns] for e in indices])
    print("72 x 72 top Taylor determinant modulo 1009:", value)


def check_counts():
    for h in range(17,121):
        src = {}
        rows = {}
        for b in range((h+19)//20):
            k = h-20*b
            src[b] = len(source(k,b==0))
            rows[b] = 3*sum(k-8*a for a in range((k+7)//8))
        assert src == rows
    print("104 heights, all second transverse degrees balanced")


def check_constants():
    # lambda = atanh(1/3).
    q = Fraction(1,3)
    lower = sum(q**(2*j+1)/(2*j+1) for j in range(25))
    upper = lower + q**51/(51*(1-q*q))
    proposed = Fraction(48550672,10**8)
    assert 4*(proposed-Fraction(1,8))**2 < 3*lower/2
    assert (2+upper)/4 < Fraction(5866434,10**7)
    # The raw full-dimensional row count first reaches one in this bracket.
    def raw(t, lam):
        return (4*t**3/3-2*(t-Fraction(1,2))**3)/lam
    lo,hi=Fraction(64166458,10**8), Fraction(64166459,10**8)
    assert raw(lo,lower)<1<raw(hi,upper)
    pure_upper=hi-lo**4/(3*upper)+(hi-Fraction(1,2))**4/(2*lower)
    assert proposed - pure_upper > Fraction(6309,10**6)
    print("min-cost lower > 0.48550672, explicit basis upper < 0.5866434")
    print("gain over optimal integrated pure count > 0.006309")


if __name__ == "__main__":
    check_blocks()
    check_counts()
    check_constants()
