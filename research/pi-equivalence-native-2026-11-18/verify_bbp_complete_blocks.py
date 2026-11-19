"""Certify the complete-block odd-prime bound at M/N -> 4*sqrt(2).

Uses only integer and Fraction arithmetic for all assertions. Run with Python 3.
"""

from fractions import Fraction as F
from functools import lru_cache
from math import comb, factorial, isqrt

CLASSES = (1, 3, 5, 7)
WEIGHTS = {1: 4, 4: -2, 5: -1, 6: -1}
ONE = (1, 0)


def multiply(x, y, d):
    return (x[0] * y[0] + d * x[1] * y[1], x[0] * y[1] + x[1] * y[0])


def divide(x, y, d):
    norm = y[0] ** 2 - d * y[1] ** 2
    return multiply(x, (F(y[0], norm), F(-y[1], norm)), d)


def power(x, exponent, d):
    result = ONE
    while exponent:
        if exponent % 2:
            result = multiply(result, x, d)
        x = multiply(x, x, d)
        exponent //= 2
    return result


@lru_cache(None)
def scalar(u, v, r):
    """Universal lift of p*X for a no-carry cell, p congruent to r mod 8."""
    orig = F(0)
    chi2 = -1 if r in (3, 5) else 1
    for ell in range(1, u + 1):
        a = ell * r % 8
        if a in WEIGHTS:
            orig += F(WEIGHTS[a], ell) * F(2) ** ((a - ell) // 2) * chi2 ** ell

    corr = F(0)
    for d, rho, eight_a in ((2, (-1, 1), (-1, 1)), (-1, (0, 1), (1, -1))):
        chi = chi2 if d == 2 else (1 if r in (1, 5) else -1)
        frob = lambda x: (x[0], chi * x[1])
        one_minus = lambda x: (1 - x[0], -x[1])
        gamma = divide(rho, (rho[0] - 1, rho[1]), d)
        block = divide(one_minus(frob(rho)), one_minus(rho), d)
        block = multiply(block, power(frob(gamma), u + 1, d), d)
        block = divide(block, gamma, d)
        beta_sum = (F(0), F(0))
        for s in range(v):
            z = power(frob(rho), s, d)
            beta = F(1, (u + s + 1) * comb(u + s, s))
            beta_sum = (beta_sum[0] + beta * z[0], beta_sum[1] + beta * z[1])
        product = multiply(multiply(eight_a, block, d), beta_sum, d)
        # The trace in either quadratic algebra is twice its rational coefficient.
        corr += 4 * product[0]
    return orig + corr


def certified_cells():
    lo_t = F(5656854249492, 10**12)
    hi_t = F(5656854249493, 10**12)
    assert lo_t**2 < 32 < hi_t**2
    cells = []
    for u in range(1, 21):
        for v in range(1 + int(hi_t * (u + 1) / 8)):
            # Closed numerical bounds on the length of the limiting open cell.
            lo = max(F(8, u + 1), hi_t / (v + 1), (8 + hi_t) / (u + v + 1))
            hi = min(F(8, u), (8 + lo_t) / (u + v))
            if v:
                hi = min(hi, lo_t / v)
            if lo < hi:
                good = tuple(r for r in CLASSES if scalar(u, v, r) != 0)
                assert good == ((1, 5) if (u, v) == (1, 0) else CLASSES)
                cells.append((u, v, hi - lo, good))
    density = sum(length * len(good) / 4 for _, _, length, good in cells)
    assert density > F(36146, 10000)
    # exp(E*/2)=4/(2-sqrt(2))^4. Compare to a finite lower bound for exp(3.526).
    upper_sqrt2 = F(1414214, 10**6)
    assert upper_sqrt2**2 > 2
    upper_exp = 4 / (2 - upper_sqrt2)**4
    assert sum(F(3526, 1000)**k / factorial(k) for k in range(20)) > upper_exp
    return cells, density


def beta_oracle(n, m, p):
    """Independent oracle. Sums the original rational terms and p*Beta(L+1,k+1)."""
    l = 8*n + 8
    d = l + m + 1
    assert d < p*p
    value = 0
    for k in range(n + 1):
        for a, c in WEIGHTS.items():
            x = 8*k + a
            if x % p == 0:
                value += c * pow(16, -k, p) * pow(x//p, -1, p)
    units = [1]
    for k in range(1, d + 1):
        unit = k if k % p else k//p
        units.append(units[-1] * unit % p)
    coeffs = []
    correction = 0
    for k in range(m + 1):
        a = int(k == 1)
        for back, multiplier in ((1, -2), (3, -2), (4, 1)):
            if k >= back:
                a += multiplier * coeffs[k-back]
        coeffs.append(a % p)
        vbeta = l//p + k//p - (l+k+1)//p
        assert vbeta in (0, -1)
        if vbeta == -1:
            correction += a * units[l] * units[k] * pow(units[l+k+1], -1, p)
            correction %= p
    return (value + pow(16, -n, p) * correction) % p


def verify_prime(n, m, p):
    l = 8*n + 8
    u, ell0 = divmod(l, p)
    v, m0 = divmod(m, p)
    assert ell0 >= 8 and ell0 + m0 < p - 1  # away from old boundary and from a carry
    expected = scalar(u, v, p % 8)
    assert expected.numerator * pow(expected.denominator, -1, p) % p == beta_oracle(n, m, p)


def main():
    cells, density = certified_cells()
    count = 0
    # Every cell and every class, including the cells whose lift is zero.
    for u, v, _, _ in cells:
        for p in (89, 83, 101, 103):
            l = 8 * ((u*p + p//3)//8)
            verify_prime(l//8 - 1, v*p + p//4, p)
            count += 1
    # Same N,M as the native benchmark, different calculation of the prime residues.
    n, m = 320, 1810
    l = 8*n + 8
    native_count = 0
    for p in range(3, l + 1, 2):
        if p*p <= l + m + 1 or any(p % q == 0 for q in range(3, isqrt(p) + 1, 2)):
            continue
        u, ell0 = divmod(l, p)
        if 1 <= u <= 20 and ell0 >= 8 and ell0 + m % p < p - 1:
            verify_prime(n, m, p)
            native_count += 1
    print(f"{len(cells)} certified cells; {count} synthetic and {native_count} benchmark residue checks")
    print("exact lower density > 3.6146; exact E*/2 < 3.526; exponent gap > 0.1772")
    print(f"certified rational density lower bound = {density}")


if __name__ == "__main__":
    main()
