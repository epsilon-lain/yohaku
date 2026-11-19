#!/usr/bin/env python3
"""Reproduce the resonance audit using only Python's standard library.

Finite checks do not prove the stronger valuation conjecture.
Run with --extended to include the previously investigated large isolated cases.
"""

from array import array
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
from math import comb
from pathlib import Path
import argparse
import json


def v2_int(n):
    n = abs(n)
    if not n:
        raise ValueError("v2(0) is not a finite integer")
    return (n & -n).bit_length() - 1


def v2_fraction(x):
    return v2_int(x.numerator) - v2_int(x.denominator)


def binomial_v2(n, k):
    assert 0 <= k <= n
    return k.bit_count() + (n - k).bit_count() - n.bit_count()


def exact_coefficients(M):
    initial = [0, 1, -2, 4]
    aa = initial[:M + 1]
    for n in range(4, M + 1):
        aa.append(-2 * aa[n - 1] - 2 * aa[n - 3] + aa[n - 4])
    return aa


def pell_pair(n, mod):
    """Return (P_n, P_(n+1)) modulo mod by binary doubling."""
    a, b = 0, 1
    for bit in bin(n)[2:]:
        c = (2 * a * (b - a)) % mod
        d = (a * a + b * b) % mod
        a, b = (d, (2 * d + c) % mod) if bit == "1" else (c, d)
    return a, b


def shifted_coefficients(N, precision):
    """Coefficients of P_(4N)(1-x) modulo 2**precision, in O(N) steps.

    Use D_x=4-4x+2x^3-x^4 and the exact four-term tail numerator.
    Descending division is exact modulo 2**precision because D_x is monic
    up to sign; no division by its even constant term is performed.
    """
    mod, M = 1 << precision, 4 * N
    mask, K = mod - 1, M + 1
    p, q = pell_pair(2 * N, mod)
    qy = [q * q, -p * q, p * (2 * q + p), -p * q]
    qx = [sum(qy[j] * comb(j, i) * (-1) ** i for j in range(i, 4)) & mask
          for i in range(4)]
    num = array("Q", [0]) * (M + 5)
    num[0], num[1] = 1, mask
    unit, exp = 1, 0
    for j in range(K + 1):
        c = (unit << exp) & mask
        if j & 1:
            c = -c
        for i in range(4):
            num[j + i] = (num[j + i] - c * qx[i]) & mask
        if j < K:
            top, bottom = K - j, j + 1
            vt, vb = v2_int(top), v2_int(bottom)
            exp += vt - vb
            assert exp >= 0
            unit = (unit * (top >> vt) *
                    pow(bottom >> vb, -1, mod)) & mask
    out = array("Q", [0]) * (M + 5)
    for j in range(M, -1, -1):
        out[j] = (4 * out[j + 4] - 4 * out[j + 3] +
                  2 * out[j + 1] - num[j + 4]) & mask
    assert (4 * out[0] - num[0]) & mask == 0
    assert (4 * out[1] - 4 * out[0] - num[1]) & mask == 0
    assert (4 * out[2] - 4 * out[1] - num[2]) & mask == 0
    assert (4 * out[3] - 4 * out[2] + 2 * out[0] - num[3]) & mask == 0
    return out[:M + 1]


def check_transform():
    count = 0
    for N in range(1, 21):
        aa = exact_coefficients(4 * N)
        bs = shifted_coefficients(N, 32)
        for j, b in enumerate(bs):
            exact = (-1) ** j * sum(comb(k, j) * aa[k]
                                   for k in range(j, 4 * N + 1))
            assert b == exact % (1 << 32), (N, j)
            count += 1
    return {"N_min": 1, "N_max": 20, "coefficients_checked": count,
            "precision_bits": 32, "passed": True}


def polynomial_product(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def check_zero_identity():
    p = [-1, 2, 0, 2, 1]
    product = polynomial_product(
        polynomial_product(p, [3, 2, 1]), [5, 4, 1])
    expected = [comb(8, k) for k in range(9)]
    expected[0] -= 16
    assert product == expected
    aa = exact_coefficients(127)
    rows = []
    for J in range(8, 129, 8):
        total = sum((Fraction(2 * comb(J - 1, t) * aa[t], t + 1)
                     for t in range(J)), Fraction(0))
        assert total == 0
        rows.append({"J": J, "numerator": total.numerator,
                     "denominator": total.denominator})
    return {"polynomial_identity_verified": True,
            "arithmetic": "exact integers and fractions", "rows": rows}


def check_exact_high_case():
    A, u, k = 257, 1, 63
    N, J = (A << u) - 1, (1 << (u + 3)) * k
    aa = exact_coefficients(4 * N)
    b = -sum(comb(n, J - 1) * aa[n]
             for n in range(J - 1, 4 * N + 1))
    S = Fraction(-2 * b, J)
    sigma = binomial_v2((A - 1) // 2, k)
    assert v2_int(b) == 10 and v2_fraction(S) == sigma == 7
    return {"A": A, "u": u, "k": k, "N": N, "J": J,
            "method": "exact integer binomial transform",
            "v2_b": v2_int(b), "b_mod_2048": b % 2048,
            "b_abs_bit_length": abs(b).bit_length(),
            "v2_S": v2_fraction(S), "sigma": sigma,
            "S_denominator": S.denominator}


def check_u0_counterexample():
    aa = exact_coefficients(8)
    g7, g8 = Fraction(2 * aa[7], 8), Fraction(2 * aa[8], 9)
    S = g7 + 9 * g8
    assert S == -660
    return {"A": 3, "u": 0, "k": 1, "N": 2, "J": 8,
            "g7": [g7.numerator, g7.denominator],
            "g8": [g8.numerator, g8.denominator],
            "S": [S.numerator, S.denominator],
            "v2_S": v2_fraction(S), "sigma": 0,
            "refutes": "universal equality v2(S)=sigma+1 when u=0",
            "does_not_refute": "lower bound v2(S)>=sigma+1 when u=0"}


def audit_row(A, u, precision):
    m, h, B = A << u, u + 3, (A - 1) // 2
    N = m - 1
    bs = shifted_coefficients(N, precision)
    rows = []
    for k in range(1, B + 1, 2):
        J = (1 << h) * k
        sigma = binomial_v2(B, k)
        residue = bs[J - 1]
        exact = residue != 0
        val = (v2_int(residue) if exact else precision) - h + 1
        if not exact and val <= sigma + 2:
            raise ValueError("Increase precision; this comparison is unresolved.")
        rows.append({"A": A, "u": u, "N": N, "k": k, "J": J,
                     "v2_S_or_lower_bound": val, "valuation_exact": exact,
                     "sigma": sigma})
    return rows


def summarize(rows, expected):
    count, exact_equal, lower_bounds, max_sigma = 0, 0, 0, 0
    failures, gaps = [], Counter()
    for row in rows:
        count += 1
        val, sigma = row["v2_S_or_lower_bound"], row["sigma"]
        exact = row["valuation_exact"]
        max_sigma = max(max_sigma, sigma)
        if exact:
            exact_equal += val == sigma
            gaps[str(val - sigma)] += 1
        else:
            lower_bounds += 1
        if not expected(row):
            failures.append(row)
    return {"comparisons": count, "exact_equal_to_sigma": exact_equal,
            "valuation_lower_bounds_only": lower_bounds,
            "maximum_sigma": max_sigma, "exact_gap_histogram": dict(gaps),
            "failure_count": len(failures), "failures": failures}


def check_positive_u(precision):
    def rows():
        for N in range(1, 2000, 2):
            m = N + 1
            u = v2_int(m)
            yield from audit_row(m >> u, u, precision)
    result = summarize(rows(), lambda r: r["v2_S_or_lower_bound"] >= r["sigma"])
    result.update({"scope": "all odd N with 1<=N<2000, all allowed odd k",
                   "precision_bits": precision,
                   "claim_status": "finite check; general bound unproved"})
    assert result["comparisons"] == 83348
    return result


def check_u0(precision):
    all_rows = []
    for A in range(3, 304, 2):
        all_rows.extend(audit_row(A, 0, precision))
    result = summarize(all_rows,
                       lambda r: r["v2_S_or_lower_bound"] >= r["sigma"] + 1)
    one, three = [], []
    for row in all_rows:
        (one if row["A"] % 4 == 1 else three).append(row)
    result.update({
        "scope": "all odd A with 3<=A<=303, u=0, all allowed odd k",
        "precision_bits": precision,
        "A_mod4_1": summarize(one, lambda r: r["valuation_exact"] and
                             r["v2_S_or_lower_bound"] == r["sigma"] + 1),
        "A_mod4_3": summarize(three, lambda r:
                             r["v2_S_or_lower_bound"] >= r["sigma"] + 2),
        "claim_status": "finite check; general bounds unproved"})
    assert result["comparisons"] == 5776
    return result


def check_extended(precision):
    pairs = []
    for b in (8, 10, 12, 14):
        pairs.extend((A, 1) for A in ((1 << b) + 1, (1 << b) - 1,
                                     3 * (1 << b) + 1, 3 * (1 << b) - 1))
    pairs.extend(((257, 2), (257, 4), (1025, 2), (4097, 2), (21845, 1)))
    results = []
    for A, u in pairs:
        result = summarize(audit_row(A, u, precision),
                           lambda r: r["valuation_exact"] and
                           r["v2_S_or_lower_bound"] == r["sigma"])
        result.update({"A": A, "u": u, "N": (A << u) - 1})
        results.append(result)
    return {"scope": "21 isolated parameter pairs; not a full interval scan",
            "precision_bits": precision, "rows": results,
            "claim_status": "finite check; general equality unproved"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--precision", type=int, default=40)
    parser.add_argument("--output", type=Path,
                        default=Path("resonance-strong-bound-audit.json"))
    args = parser.parse_args()
    if not 32 <= args.precision <= 63:
        parser.error("--precision must be between 32 and 63")
    result = {
        "format": "bbp-resonance-strong-bound-audit/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": "finite verification, not a proof of the stronger bound",
        "transform_crosscheck": check_transform(),
        "exact_zero_identity": check_zero_identity(),
        "exact_high_case": check_exact_high_case(),
        "u0_counterexample": check_u0_counterexample(),
        "positive_u_batch": check_positive_u(args.precision),
        "u0_batch": check_u0(args.precision),
        "extended_batch": check_extended(args.precision) if args.extended else None,
    }
    result["all_requested_checks_passed"] = (
        result["positive_u_batch"]["failure_count"] == 0 and
        result["u0_batch"]["failure_count"] == 0 and
        result["u0_batch"]["A_mod4_1"]["failure_count"] == 0 and
        result["u0_batch"]["A_mod4_3"]["failure_count"] == 0 and
        (result["extended_batch"] is None or
         all(r["failure_count"] == 0 for r in result["extended_batch"]["rows"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "all_requested_checks_passed": result["all_requested_checks_passed"],
        "positive_u_comparisons": result["positive_u_batch"]["comparisons"],
        "positive_u_exact_equal": result["positive_u_batch"]["exact_equal_to_sigma"],
        "u0_comparisons": result["u0_batch"]["comparisons"],
        "extended_pairs": 0 if result["extended_batch"] is None else
                          len(result["extended_batch"]["rows"]),
    }, ensure_ascii=False))
    return 0 if result["all_requested_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
