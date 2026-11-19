"""Standard-library verification of the exact 2-adic Laurent representation.

This checks an identity and its finite-part conventions. It does not prove
global integrality of the normalized BBP values; individual blocks can have
negative valuations, and that limitation is explicitly tested below.
"""
from fractions import Fraction
from math import comb, factorial, prod
from pathlib import Path
import json


def v2(n):
    n = abs(n)
    if not n:
        raise ValueError("zero has infinite valuation")
    return (n & -n).bit_length() - 1


def v2q(q):
    return v2(q.numerator) - v2(q.denominator)


def harmonic(n):
    return sum((Fraction(1, j) for j in range(1, n + 1)), Fraction(0))


def beta_star(a, k):
    return sum((Fraction((-1) ** t * comb(k, t), a + t)
                for t in range(k + 1) if a + t != 0), Fraction(0))


def beta_star_closed(a, k):
    if a > 0:
        return Fraction(factorial(a - 1) * factorial(k), factorial(a + k))
    h = -a
    if h <= k:
        return (-1) ** h * comb(k, h) * (harmonic(h) - harmonic(k - h))
    return Fraction((-1) ** (k + 1) * factorial(k) * factorial(h - k - 1),
                    factorial(h))


def kernel_coefficients(maximum):
    a = [0] * (maximum + 1)
    for k in range(maximum + 1):
        a[k] = (int(k == 1)
                - (2 * a[k - 1] if k >= 1 else 0)
                - (2 * a[k - 3] if k >= 3 else 0)
                + (a[k - 4] if k >= 4 else 0))
    return a


def exact_y(n):
    coefficients = kernel_coefficients(4 * n)
    result = Fraction(0)
    for j in range(n + 1):
        result = (16 * result + Fraction(4, 8 * j + 1)
                  - Fraction(2, 8 * j + 4) - Fraction(1, 8 * j + 5)
                  - Fraction(1, 8 * j + 6))
    ell = 8 * n + 8
    beta = Fraction(1, ell + 1)
    for k, coefficient in enumerate(coefficients):
        result += coefficient * beta
        beta *= Fraction(k + 1, ell + k + 2)
    return result


def tail_coefficients(m):
    p, q = 0, 1
    for _ in range(2 * m - 2):
        p, q = q, 2 * q + p
    return [q * q, -p * q, p * (2 * q + p), -p * q]


def laurent_block(m, r):
    coefficients = tail_coefficients(m)
    return (16 ** r) * sum((b * coefficient * beta_star_closed(
        8 * m - 8 * r - 3 - j, 4 * m - 3 + ell)
        for j, b in enumerate((1, 2, 4, 4, 4))
        for ell, coefficient in enumerate(coefficients)), Fraction(0))


def normalized_first_block(m):
    result = Fraction(0)
    for j, b in enumerate((1, 2, 4, 4, 4)):
        for ell, coefficient in enumerate(tail_coefficients(m)):
            ratio = Fraction(
                prod(12 * m - t for t in range(6 + j - ell)),
                prod(8 * m - t for t in range(4 + j))
                * prod(4 * m - t for t in range(max(0, 3 - ell))))
            result += b * coefficient * ratio
    return result


def check_tail_polynomial(m):
    degree = 4 * m - 4
    a = kernel_coefficients(degree)
    denominator = (1, 2, 0, 2, -1)
    product = [0] * (degree + 5)
    for i, coefficient in enumerate(a):
        for j, factor in enumerate(denominator):
            product[i + j] += coefficient * factor
    remainder = [int(i == 1) - t for i, t in enumerate(product)]
    expected = [0] * (degree + 1) + tail_coefficients(m)
    assert remainder == expected


def log_coefficient(m):
    """Extract the total x^-1 coefficient from the regrouped Laurent series."""
    total = 0
    for r in range(2 * m + 1):
        for j, b in enumerate((1, 2, 4, 4, 4)):
            for ell, coefficient in enumerate(tail_coefficients(m)):
                k = 4 * m - 3 + ell
                t = 8 * r - 8 * m + 3 + j
                if 0 <= t <= k:
                    total += 16 ** r * b * coefficient * (-1) ** t * comb(k, t)
    return total


def run():
    beta_checks = 0
    for a in range(-20, 21):
        for k in range(17):
            assert beta_star(a, k) == beta_star_closed(a, k)
            beta_checks += 1
    truncation = []
    for m in range(1, 9):
        check_tail_polynomial(m)
        assert log_coefficient(m) == 0
        approximate = sum((laurent_block(m, r) for r in range(24)), Fraction(0))
        difference = approximate - exact_y(m - 1)
        observed = None if difference == 0 else v2q(difference)
        bound = 4 * 24 - ((8 * 24 + 12 * m + 10).bit_length() - 1)
        assert observed is None or observed >= bound
        truncation.append({"m": m, "N": m - 1, "blocks": 24,
                           "error_v2": observed, "proved_tail_lower_bound": bound,
                           "total_log_coefficient": 0})
    residue = Fraction(3, 16) * sum(b * (j + 4) * (j + 9)
                                  for j, b in enumerate((1, 2, 4, 4, 4)))
    assert residue == 216
    pole_checks = []
    for u in range(5, 11):
        m = 1 << u
        valuation = v2q(normalized_first_block(m))
        assert valuation == 3 - u
        pole_checks.append({"m": m, "u": u,
                            "v2_normalized_first_block": valuation})
    return {
        "format": "bbp-laurent-regularization/1",
        "beta_finite_part_checks": beta_checks,
        "truncation_checks": truncation,
        "first_block_pole_residue": int(residue),
        "first_block_nonintegrality_checks": pole_checks,
        "scope": "Exact representation and finite checks only; no global normalized-integrality theorem.",
    }


if __name__ == "__main__":
    result = run()
    target = Path(__file__).with_name("bbp-laurent-regularization-verification.json")
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"beta_finite_part_checks": result["beta_finite_part_checks"],
                      "truncation_error_v2": [row["error_v2"] for row in result["truncation_checks"]],
                      "first_block_pole_residue": result["first_block_pole_residue"],
                      "first_block_valuations": [row["v2_normalized_first_block"]
                                                 for row in result["first_block_nonintegrality_checks"]],
                      "output": str(target)}))
