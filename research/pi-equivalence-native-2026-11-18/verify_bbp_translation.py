"""Exact seed profile and independent direct checks of translated slope-four points.

Uses rational arithmetic for seeds. For large points the positive Beta recurrence
and Pell formulas evaluate modulo powers of two, separately from the terminal
difference used in the proof. All dependencies are in Python's standard library.
Run python3 verify_bbp_translation.py, or add --full to check extra off-axis cases.
"""
from fractions import Fraction
from math import comb
import sys


def v2(x):
    if not x:
        raise ValueError("zero has no finite valuation")
    return (x & -x).bit_length() - 1


def seed_profile(maximum):
    n = 14
    height = 8 * (n + 1)
    prefix = sum((Fraction(weight * 16**(n-i), 8*i + j)
                  for i in range(n + 1)
                  for weight, j in ((4, 1), (-2, 4), (-1, 5), (-1, 6))),
                 Fraction(0))
    # Direct Taylor recurrence + exact successive integrals.
    coeff = []
    result = prefix
    beta = Fraction(1, height + 1)
    profile = []
    for k in range(maximum + 1):
        value = int(k == 1)
        for offset, factor in ((1, -2), (3, -2), (4, 1)):
            if k >= offset:
                value += factor * coeff[k - offset]
        coeff.append(value)
        if k:
            beta *= Fraction(k, height + k + 1)
        result += value * beta
        # Independent expansion of (1-x)^k and exact integration in x.
        integral = sum((Fraction((-1)**i * comb(k, i), height+i+1)
                        for i in range(k+1)), Fraction(0))
        assert integral == beta
        profile.append(v2(result.numerator) - v2(result.denominator))
    return profile


def direct_profile(n, orders):
    """All wanted positive-order residues in one pass for fixed truncation n."""
    height = 8*(n+1)
    d = (height+max(orders)+1).bit_length()-1
    bits = 2*d+3
    modulus = 1 << bits
    mask = modulus-1
    total = 0
    for j in range(min(n, bits//4)+1):
        i = n-j
        for num, den in ((4, 8*i+1), (-1, 8*i+5),
                         (-(3*i+2), (2*i+1)*(4*i+3))):
            total += (num*pow(den, -1, modulus)) << (d+4*j)
    total &= mask
    # Beta = odd_unit * 2^exponent; Pell recurrence gives the coefficients.
    unit = pow(height+1, -1, modulus)
    exponent = 0
    pell, next_pell = 0, 1
    result = {}
    for k in range(1, max(orders)+1):
        a, b = v2(k), v2(height+k+1)
        exponent += a-b
        unit = (unit*(k >> a)*pow((height+k+1) >> b, -1, modulus)) & mask
        assert exponent + d >= 0
        if k % 2:
            pell, next_pell = next_pell, (2*next_pell+pell) & mask
            coefficient = pell*pell
        else:
            coefficient = -pell*next_pell
        total = (total + ((coefficient*unit) << (exponent+d))) & mask
        if k in orders:
            assert total, (n, k)
            result[k] = v2(total)-d
    return result


if __name__ == "__main__":
    profile = seed_profile(134)
    assert min(profile) == -5 and max(profile) == 1
    assert [i for i, v in enumerate(profile) if v >= 1] == [87]
    assert profile[56] == 0
    print("Exact seed profile: 135 values, min -5, max 1 only at m=87")
    large = "--full" in sys.argv
    pairs = [(13, 1), (13, 3), (14, 1), (14, 3)]
    if large:
        pairs.extend(((13, 5), (13, 7), (14, 5), (14, 7)))
    for s, odd in pairs:
        w = odd << s
        carries = (8*w).bit_count()+(4*w).bit_count()-(12*w).bit_count()
        n = w+14
        ks = range(135) if s >= 14 else [k for k, v in enumerate(profile) if v <= 0]
        orders = {4*w+k for k in ks}
        actual = direct_profile(n, orders)
        assert all(actual[4*w+k] == profile[k]-carries for k in ks)
        print(f"s={s}, A={odd}, N={n}, carries={carries}, verified orders={len(orders)}")
