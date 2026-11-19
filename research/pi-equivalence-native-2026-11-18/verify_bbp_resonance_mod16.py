"""Exact standard-library checks for the uniform four-bit resonance theorem.

All weighted sums use the original order-four kernel recurrence. Observations
whose full resonance demand exceeds four bits are marked as finite evidence.
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
    if n == 0:
        raise ValueError("valuation of zero is infinite")
    return (n & -n).bit_length() - 1


def v2q(x):
    return None if x == 0 else v2(x.numerator) - v2(x.denominator)


def residue(x, modulus):
    assert x.denominator % 2 == 1
    return (x.numerator * pow(x.denominator, -1, modulus)) % modulus


def kernel_weights(maximum_index):
    a = [0] * (maximum_index + 1)
    for j in range(len(a)):
        a[j] = (int(j == 1)
                - (2 * a[j - 1] if j >= 1 else 0)
                - (2 * a[j - 3] if j >= 3 else 0)
                + (a[j - 4] if j >= 4 else 0))
    g = [Fraction(2 * coefficient, j + 1) for j, coefficient in enumerate(a)]
    assert all(t.denominator % 2 == 1 for t in g)
    return g


def weighted_sum(m, J, g):
    return sum((choose(r, J) * g[r - 1] for r in range(J, 4 * m - 2)),
               Fraction(0))


def check_case(A, u, k, g):
    assert A % 2 == 1 and k % 2 == 1 and 1 <= k <= (A - 1) // 2
    m = A << u
    J = k << (u + 3)
    b = J // 2
    w = (A - 1) // 2
    sigma = v2(choose(w, k))
    gamma = 2 * A.bit_count() - (3 * A).bit_count()
    demand = v2(A + k) - gamma
    T1, T2, T3 = (choose(2 * m - 1, b + j) for j in (1, 2, 3))
    U = b * T1 + (b + 1) * T2
    expected = (U + (8 * choose(w, k) if u == 0 else 0)) % 16
    actual_sum = weighted_sum(m, J, g)
    actual_residue = residue(actual_sum, 16)
    observed_v = v2q(actual_sum)
    proved_bound = min(4, sigma + int(u == 0))
    assert actual_residue == expected
    assert observed_v is None or observed_v >= proved_bound
    assert gamma + sigma >= v2(A + k)
    if u >= 1:
        assert v2(T1) == v2(T2) == sigma
        assert v2(U) == sigma
        if sigma < 4:
            assert observed_v == sigma
    else:
        assert v2(T1) == sigma
        if k == w:
            assert T2 == T3 == 0
        else:
            assert v2(T2) == sigma + 1 + v2(w - k)
    if demand <= 4:
        assert observed_v is None or observed_v >= demand
    return {
        "m": m, "A": A, "u": u, "k": k, "J": J,
        "gamma": gamma, "sigma": sigma, "extra_bits_required": demand,
        "S_mod16": actual_residue, "predicted_S_mod16": expected,
        "v2S": observed_v, "proved_v2_lower_bound": proved_bound,
        "full_requirement_proved_by_this_theorem": demand <= 4,
        "full_requirement_observed": observed_v is None or observed_v >= demand,
        "endpoint_T2_zero": T2 == 0,
    }


def run():
    cases = set()
    for m in range(1, 81):
        u = v2(m)
        A = m >> u
        for k in range(1, (A - 1) // 2 + 1, 2):
            cases.add((A, u, k))
    stress = []
    for v in range(3, 8):
        A, k = (1 << v) + 1, (1 << (v - 1)) - 1
        for u in range(3):
            cases.add((A, u, k))
            stress.append((A, u, k))
    largest_m = max(A << u for A, u, k in cases)
    g = kernel_weights(4 * largest_m - 4)
    weight_checks = 0
    for t in range(1, min(400, len(g) // 2)):
        assert residue(g[2 * t - 1], 16) == t % 16
        assert residue(g[2 * t], 16) == (2 * t * (t + 1)) % 16
        weight_checks += 2
    binomial_checks = 0
    for t in range(61):
        for b in range(0, t + 1, 4):
            expected = choose(t, b) * (1 + (8 * t if b % 8 == 4 else 0))
            assert choose(2 * t, 2 * b) % 16 == expected % 16
            assert choose(2 * t + 1, 2 * b) % 4 == choose(t, b) % 4
            binomial_checks += 2
    moment_checks = 0
    for b in range(13):
        for top in range(b, 21):
            lhs = sum(choose(t + 1, 2) * choose(t, b) for t in range(b, top + 1))
            rhs = (choose(b + 1, 2) * choose(top + 1, b + 1)
                   + (b + 1) ** 2 * choose(top + 1, b + 2)
                   + choose(b + 2, 2) * choose(top + 1, b + 3))
            assert lhs == rhs
            moment_checks += 1
    rows = [check_case(A, u, k, g) for A, u, k in sorted(cases)]
    stress_set = set(stress)
    stress_rows = [row for row in rows if (row["A"], row["u"], row["k"]) in stress_set]
    endpoint_rows = [row for row in rows if row["u"] == 0 and row["k"] == (row["A"] - 1) // 2]
    return {
        "format": "bbp-resonance-mod16/1",
        "small_range": {"m_min": 1, "m_max": 80, "all_resonant_indices": True},
        "checked_weighted_sums": len(rows),
        "g_mod16_checks": weight_checks,
        "binomial_doubling_checks": binomial_checks,
        "second_moment_checks": moment_checks,
        "endpoint_checks": len(endpoint_rows),
        "demand_at_most_four_cases": sum(row["extra_bits_required"] <= 4 for row in rows),
        "higher_demand_observations": sum(row["extra_bits_required"] > 4 for row in rows),
        "failures": [],
        "stress_rows": stress_rows,
        "endpoint_rows": endpoint_rows,
        "rows": rows,
        "scope": "The infinite proof is mod16. Demands above four bits remain observations only.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-json', type=Path,
                        help='also save all individual weighted-sum rows here')
    args = parser.parse_args()
    result = run()
    if args.full_json:
        args.full_json.write_text(json.dumps(result, indent=2) + "\n")
    result.pop('rows')
    target = Path(__file__).with_name("bbp-resonance-mod16-verification.json")
    target.write_text(json.dumps(result, indent=2) + "\n")
    keys = ("checked_weighted_sums", "g_mod16_checks", "binomial_doubling_checks",
            "second_moment_checks", "endpoint_checks", "demand_at_most_four_cases",
            "higher_demand_observations", "failures")
    print(json.dumps({**{key: result[key] for key in keys}, "output": str(target)}))
