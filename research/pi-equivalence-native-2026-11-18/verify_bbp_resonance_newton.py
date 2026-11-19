"""Exact verification of Newton factorization and all-order resonance bounds.

No floating arithmetic or external packages. The proof is in the companion
Markdown file; finite tests check its identities, indices, and corollaries.
"""
from fractions import Fraction
from math import comb
from pathlib import Path
import argparse
import json


def choose(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def v2(n):
    n = abs(n)
    if not n:
        raise ValueError("zero has infinite valuation")
    return (n & -n).bit_length() - 1


def valuation(q):
    return None if q == 0 else v2(q.numerator) - v2(q.denominator)


def kernel(maximum):
    a = [0] * (maximum + 1)
    for n in range(maximum + 1):
        a[n] = (int(n == 1)
                - (2 * a[n - 1] if n >= 1 else 0)
                - (2 * a[n - 3] if n >= 3 else 0)
                + (a[n - 4] if n >= 4 else 0))
    return a


def convolution(a, b):
    result = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] += x * y
    return result


def differences(values):
    result = []
    while values:
        result.append(values[0])
        values = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    return result


def small_difference(a, start, order):
    return sum((-1) ** (order - j) * choose(order, j) * a[start + j]
               for j in range(order + 1))


def check_factorization(R, J, a):
    assert 0 < J <= R and J % 8 == 0
    length = R - J
    d = differences(a[J - 1:R])
    quotient = Fraction(0)
    for ell, difference in enumerate(d):
        t, b = divmod(ell, 8)
        assert difference == 16 ** t * small_difference(a, J + 8 * t - 1, b)
        c = Fraction(2 * difference, J + ell)
        assert c.denominator % 2 == 1
        cval = valuation(c)
        if b == 0:
            assert cval == 4 * t + v2(J + 8 * t) - 1
        elif b in (2, 4):
            assert cval == 4 * t
        else:
            assert cval is None or cval >= 4 * t + 1
        assert c.numerator % 2 == int(ell in (2, 4))
        quotient += c * choose(length, ell)
    direct = sum((choose(r, J) * Fraction(2 * a[r - 1], r)
                  for r in range(J, R + 1)), Fraction(0))
    assert direct == choose(R, J) * quotient
    assert quotient.denominator % 2 == 1
    predicted_parity = (choose(length, 2) + choose(length, 4)) % 2
    assert quotient.numerator % 2 == predicted_parity
    return {"R": R, "J": J, "length": length,
            "v2_S": valuation(direct), "v2_binomial": v2(choose(R, J)),
            "v2_T": valuation(quotient), "T_parity": predicted_parity,
            "coefficient_count": len(d)}


def exact_y(n, a):
    total = Fraction(0)
    for j in range(n + 1):
        total = (16 * total + Fraction(4, 8 * j + 1)
                 - Fraction(2, 8 * j + 4) - Fraction(1, 8 * j + 5)
                 - Fraction(1, 8 * j + 6))
    L = 8 * (n + 1)
    beta = Fraction(1, L + 1)
    for k in range(4 * n + 1):
        total += a[k] * beta
        beta *= Fraction(k + 1, L + k + 2)
    return total


def run(full_rows=False):
    product = convolution([-1, 2, 0, 2, 1], [-1, 6, -16, 22, -15])
    expected = [(-1) ** (8 - i) * choose(8, i) for i in range(9)]
    expected[8] -= 16
    assert product == expected
    general = {(R, J) for R in range(8, 97) for J in range(8, R + 1, 8)}
    resonances = []
    for m in range(1, 65):
        u = v2(m)
        A = m >> u
        for k in range(1, (A - 1) // 2 + 1, 2):
            resonances.append((A, u, k, None))
            general.add((4 * m - 3, k << (u + 3)))
    stress = []
    for v in range(3, 10):
        A, k = (1 << v) + 1, (1 << (v - 1)) - 1
        for u in range(3):
            item = (A, u, k, v)
            stress.append(item)
            general.add((4 * (A << u) - 3, k << (u + 3)))
    maximum = max(R for R, J in general)
    a = kernel(maximum + 8)
    assert all(a[n + 8] % 4 == a[n] % 4 for n in range(maximum + 1))
    assert all(small_difference(a, n, 8) == 16 * a[n + 8]
               for n in range(65))
    rows = {pair: check_factorization(*pair, a) for pair in sorted(general)}
    resonance_rows = []
    for A, u, k, stress_v in resonances + stress:
        m = A << u
        J = k << (u + 3)
        row = rows[(4 * m - 3, J)]
        sigma = v2(choose((A - 1) // 2, k))
        gamma = 2 * A.bit_count() - (3 * A).bit_count()
        demand = v2(A + k) - gamma
        assert row["v2_binomial"] == sigma
        observed = row["v2_S"]
        if u:
            assert observed == sigma and row["v2_T"] == 0
        else:
            assert observed is None or observed >= sigma + 1
            assert row["v2_T"] is None or row["v2_T"] >= 1
        assert gamma + sigma >= v2(A + k)
        assert observed is None or observed >= demand
        if stress_v is not None:
            assert sigma == stress_v - 1 and gamma == 0
            resonance_rows.append({**row, "A": A, "u": u, "k": k,
                                   "stress_v": stress_v, "sigma": sigma,
                                   "extra_bits_required": demand})
    normalization = []
    for N in range(25):
        value = exact_y(N, a)
        B = 2 * choose(3 * (N + 1), N + 1) * value
        assert B.denominator % 2 == 1
        entry = {"N": N, "v2Y": valuation(value), "v2B": valuation(B)}
        if N > 0 and N % 4 == 0:
            gamma = 2 * N.bit_count() - (3 * N).bit_count()
            assert valuation(value) == -gamma
            entry["four_multiple_formula_checked"] = True
        normalization.append(entry)
    result = {
        "format": "bbp-resonance-newton/1",
        "research_date": "2026-11-20",
        "timezone": "Asia/Shanghai",
        "baseline_commit": "b8cbc502",
        "polynomial_factorization_checked": True,
        "direct_delta8_checks": 65,
        "general_range": {"R_min": 8, "R_max": 96, "all_positive_J_multiple_of_8": True},
        "small_resonance_m_range": [1, 64],
        "distinct_factorization_checks": len(rows),
        "newton_coefficient_checks": sum(row["coefficient_count"] for row in rows.values()),
        "small_resonance_checks": len(resonances),
        "stress_checks": len(stress),
        "highest_stress_demand": max(row["extra_bits_required"] for row in resonance_rows),
        "stress_rows": resonance_rows,
        "normalization_checks": normalization,
        "failures": [],
        "scope": "Finite implementation checks; the companion proof establishes all orders and all positive multiples of four.",
    }
    if full_rows:
        result["factorization_rows"] = list(rows.values())
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-json", type=Path,
                        help="Also write all 848 factorization rows to this JSON path.")
    args = parser.parse_args()
    result = run(full_rows=args.full_json is not None)
    target = Path(__file__).with_name("bbp-resonance-newton-verification.json")
    compact = {key: value for key, value in result.items() if key != "factorization_rows"}
    target.write_text(json.dumps(compact, separators=(",", ":")) + "\n")
    if args.full_json is not None:
        args.full_json.write_text(json.dumps(result, indent=2) + "\n")
    keys = ("distinct_factorization_checks", "newton_coefficient_checks",
            "small_resonance_checks", "stress_checks", "highest_stress_demand", "failures")
    print(json.dumps({**{key: result[key] for key in keys}, "output": str(target)}))
