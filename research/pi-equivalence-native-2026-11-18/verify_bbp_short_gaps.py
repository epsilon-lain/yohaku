"""Exact checks for the Pell short-gap identities. Python standard library."""

from fractions import Fraction
from math import comb, factorial, gcd, isqrt, lcm, log
import json


def pell_sequence(limit):
    values = [0, 1]
    while len(values) <= limit:
        values.append(2 * values[-1] + values[-2])
    return values


def kernel_series(limit):
    values = []
    for s in range(limit + 1):
        coefficient = int(s == 1)
        for offset, weight in ((1, -2), (3, -2), (4, 1)):
            if s >= offset:
                coefficient += weight * values[s - offset]
        values.append(coefficient)
    return values


def v2(integer):
    assert integer != 0
    return (integer & -integer).bit_length() - 1


def integral_direct(length, index):
    # Integrate x^L (1-x)^s after expanding its second factor.
    return sum(
        Fraction((-1) ** j * comb(index, j), length + j + 1)
        for j in range(index + 1)
    )


def pell_factor(pell, index):
    k = (index + 1) // 2
    if index % 2:
        return pell[k] ** 2
    return -pell[k] * pell[k + 1]


def check_gaps(limit, pell, series):
    checked = {1: 0, 2: 0, 3: 0}
    zero = []
    for n in range(1, 27):
        length = 8 * (n + 1)
        raw = sum(
            Fraction(c, 16**k * (8*k + r))
            for k in range(n + 1)
            for r, c in ((1, 4), (4, -2), (5, -1), (6, -1))
        )
        values = [raw]
        for m in range(1, limit + 1):
            term = series[m] * integral_direct(length, m) / 16**n
            values.append(values[-1] + term)
            for d in (1, 2, 3):
                if m < d or (d == 3 and m % 2):
                    continue
                first = m - d + 1
                weights = [
                    factorial(s) // factorial(first)
                    * (factorial(length+m+1) // factorial(length+s+1))
                    for s in range(first, m + 1)
                ]
                w = factorial(length+m+1) // (factorial(length) * factorial(first))
                numerator = sum(weights[i] * series[s] for i, s in enumerate(range(first, m+1)))
                delta = values[m] - values[m-d]
                assert delta == Fraction(numerator, 16**n * w)
                assert (values[m].denominator * values[m-d].denominator) % delta.denominator == 0
                if d == 1:
                    assert numerator == pell_factor(pell, m)
                    assert max(v2(values[m].denominator), v2(values[m-1].denominator)) >= 4*n-v2(numerator)
                elif d == 2:
                    k = m // 2
                    if m % 2:
                        b = -weights[0] * pell[k] + weights[1] * pell[k+1]
                        assert numerator == b * pell[k+1]
                    else:
                        b = weights[0] * pell[k] - weights[1] * pell[k+1]
                        assert numerator == b * pell[k]
                else:
                    k = (m-2)//2
                    b = -(weights[0]+weights[2])*pell[k] + (weights[1]-2*weights[2])*pell[k+1]
                    assert numerator == b * pell[k+1]
                if not delta:
                    zero.append((n, m, d))
                checked[d] += 1
    return checked, zero


def check_prime_orders(pell, prime_limit):
    checked = 0
    for p in range(3, prime_limit + 1, 2):
        if any(p % j == 0 for j in range(2, isqrt(p) + 1)):
            continue
        # The rank is the first zero of the Pell recurrence modulo p.
        d = next(i for i in range(1, p+2) if pell[i] % p == 0)
        sign = 1 if pow(2, (p-1)//2, p) == 1 else -1
        assert (p-sign) % d == 0
        for i in range(1, 301):
            assert (pell[i] % p == 0) == (i % d == 0)
            checked += 1
    return checked


def main():
    pell = pell_sequence(2048)
    series = kernel_series(1000)
    for m in range(1, 1001):
        assert series[m] == pell_factor(pell, m)
        assert v2(pell[m]) == v2(m)
        assert gcd(pell[m], pell[m+1]) == 1
    checks, zero = check_gaps(64, pell, series)
    modular = check_prime_orders(pell, 509)
    n = 320
    m = isqrt(32*n*n)
    length = 8*(n+1)
    v = (length+m+1)*comb(length+m, m)
    raw_den = 16**n*v
    q_delta = Fraction(pell_factor(pell, m), raw_den).denominator
    assert (lcm(*range(length+1, length+m+2))) % v == 0
    print(json.dumps({
        "exact_coefficient_and_valuation_cases": 1000,
        "rank_of_apparition_congruences": modular,
        "fixed_n_gap_checks": checks,
        "finite_zero_differences": zero,
        "adjacent_critical_example": {
            "n": n, "m": m, "log_reduced_difference_denominator_per_n": log(q_delta)/n,
            "gcd_with_raw_denominator": raw_den//q_delta,
        },
    }, sort_keys=True))


if __name__ == "__main__":
    main()
