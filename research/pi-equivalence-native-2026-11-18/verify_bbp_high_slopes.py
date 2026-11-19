"""Certify complete-block prime intervals for every real slope in [8,24]."""

from fractions import Fraction
from functools import lru_cache
from math import isqrt

from verify_bbp_complete_blocks import scalar


# Work in F_65537 solely to certify that selected rational constants are nonzero.
# The prime in a BBP denominator can be in any of the four classes modulo 8.
P = 65537
assert all(P % divisor for divisor in range(2, isqrt(P) + 1))
SQRT_TWO = next(root for root in range(P) if root * root % P == 2)
SQRT_MINUS_ONE = 256
assert SQRT_MINUS_ONE**2 % P == P - 1


def independent_residue(u, v, prime_class):
    chi_two = 1 if prime_class in (1, 7) else -1
    chi_minus_one = 1 if prime_class in (1, 5) else -1
    weights = {1: 4, 4: -2, 5: -1, 6: -1}
    result = 0
    for ell in range(1, u + 1):
        shift = ell * prime_class % 8
        if shift in weights:
            result += (weights[shift] * pow(2, (shift - ell) // 2, P)
                       * chi_two**ell * pow(ell, -1, P))

    roots = []
    for sign in (-1, 1):
        rho = -1 + sign * SQRT_TWO
        roots.append((rho, -1 + sign * chi_two * SQRT_TWO, rho))
        rho = sign * SQRT_MINUS_ONE
        roots.append((rho, chi_minus_one * rho, 1 - rho))

    for rho, sigma, weight_times_eight in roots:
        gamma = rho * pow(rho - 1, -1, P) % P
        gamma_sigma = sigma * pow(sigma - 1, -1, P) % P
        factor = ((1 - sigma) * pow(1 - rho, -1, P)
                  * pow(gamma_sigma, u + 1, P) * pow(gamma, -1, P)) % P
        beta_term = pow(u + 1, -1, P)
        beta_sum = 0
        for s in range(v):
            beta_sum = (beta_sum + beta_term) % P
            beta_term = beta_term * sigma * (s + 1) * pow(u + s + 2, -1, P) % P
        result += 2 * weight_times_eight * factor * beta_sum
    return result % P


@lru_cache(None)
def surviving_classes(u, v):
    count = 0
    for r in (1, 3, 5, 7):
        value = independent_residue(u, v, r)
        exact = scalar(u, v, r)
        assert value == exact.numerator * pow(exact.denominator, -1, P) % P
        count += bool(value)
    return count


def cell_lower_mass(left, right):
    mass = Fraction(0)
    for u in range(9):
        for v in range(1 + int(right * (u + 1) / 8)):
            if u == v == 0:
                continue
            lo = max(Fraction(8, u + 1), right / (v + 1), (8 + right) / (u + v + 1))
            upper_bounds = []
            if u:
                upper_bounds.append(Fraction(8, u))
            if v:
                upper_bounds.append(left / v)
            hi = min(upper_bounds)
            if hi > lo:
                mass += (hi - lo) * surviving_classes(u, v) / 4
    return mass


def main():
    bounds = []
    for k in range(32, 96):
        left, right = Fraction(k, 4), Fraction(k + 1, 4)
        bounds.append(cell_lower_mass(left, right))
    minimum = min(bounds)
    assert minimum > Fraction(391, 100)
    assert 16 * 32**32 * 5**24 < 8**8 * 24**24 * 12**24
    print(f"64 slope intervals; smallest certified odd-prime mass = {minimum} > 3.91")
    print("24-slope exponent strictly negative by an integer comparison")


if __name__ == "__main__":
    main()
