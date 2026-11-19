#!/usr/bin/env python3
"""Exact finite checks for the proved Newton quotient modulo four.

Standard library only. An optional --certificate reads previous modular
residues; it does not calculate or extend a scan.
"""
from fractions import Fraction
from hashlib import sha256
from math import comb
from pathlib import Path
import argparse
import json


def v2(n):
    n = abs(n)
    if not n:
        raise ValueError("zero has no finite v2")
    return (n & -n).bit_length() - 1


def valuation(x):
    return v2(x.numerator) - v2(x.denominator)


def residue(x, modulus):
    assert x.denominator % 2 == 1
    return x.numerator * pow(x.denominator, -1, modulus) % modulus


def coefficients(M):
    a = [0, 1, -2, 4][:M + 1]
    for k in range(4, M + 1):
        a.append(-2 * a[k - 1] - 2 * a[k - 3] + a[k - 4])
    return a


def difference_heads(values):
    values = list(values)
    heads = []
    while values:
        heads.append(values[0])
        values = [y - x for x, y in zip(values, values[1:])]
    return heads


def small_binomial(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def check_coefficient_table(J):
    a = coefficients(J + 6)
    d = difference_heads(a[J - 1:J + 7])
    cs = [Fraction(2 * z, J + ell) for ell, z in enumerate(d)]
    actual = [residue(c, 4) for c in cs]
    expected = [0, 0, 1, 2, (1 + J // 4) % 4, 0, 0, 0]
    assert actual == expected
    return {"J": J, "actual_mod4": actual, "expected_mod4": expected}


def check_newton_pair(m, J):
    K, D = 4 * m - 3, 4 * m - 3 - J
    a = coefficients(K - 1)
    direct = sum((Fraction(2 * comb(r, J) * a[r - 1], r)
                  for r in range(J, K + 1)), Fraction(0))
    ds = difference_heads(a[J - 1:K])
    cs = [Fraction(2 * z, J + ell) for ell, z in enumerate(ds)]
    assert all(c.denominator % 2 == 1 for c in cs)
    expected_coeff = [0, 0, 1, 2, (1 + J // 4) % 4, 0, 0, 0]
    for ell, c in enumerate(cs):
        assert residue(c, 4) == (expected_coeff[ell] if ell < 8 else 0)
    T = sum((c * comb(D, ell) for ell, c in enumerate(cs)), Fraction(0))
    assert direct == comb(K, J) * T
    expected_T = (small_binomial(D, 2) + 2 * small_binomial(D, 3) +
                  (1 + J // 4) * small_binomial(D, 4)) % 4
    assert residue(T, 4) == expected_T
    if m % 2 and (J // 8) % 2:
        assert (valuation(T) == 1) if m % 4 == 1 else (valuation(T) >= 2)
    return {"m": m, "J": J, "K": K, "D": D,
            "direct_equals_factorized": True,
            "coefficient_table_and_integrality_passed": True,
            "quotient_mod4": residue(T, 4), "quotient_v2": valuation(T),
            "S_v2": valuation(direct)}


def exact_Y(N):
    L, M = 8 * (N + 1), 4 * N
    y = Fraction(0)
    for i in range(N + 1):
        y = (16 * y + Fraction(4, 8 * i + 1) -
             Fraction(2, 8 * i + 4) - Fraction(1, 8 * i + 5) -
             Fraction(1, 8 * i + 6))
    beta = Fraction(1, L + 1)
    for k, a in enumerate(coefficients(M)):
        y += a * beta
        beta *= Fraction(k + 1, L + k + 2)
    return y


def check_B(N):
    m = N + 1
    B = 2 * comb(3 * m, m) * exact_Y(N)
    assert residue(B, 4) == 0
    return {"N": N, "m": m, "v2_B": valuation(B), "B_mod4": residue(B, 4)}


def check_certificate(path):
    data = json.loads(path.read_text())
    rows = data.get("rows", data.get("scan_rows"))
    scale = data.get("D", data.get("global_D"))
    maximum = data.get("max_n", data.get("range", {}).get("max_n"))
    if rows is None or scale is None or maximum is None:
        raise ValueError("Expected a complete legacy or committed global-residue certificate")
    checked, failures = 0, []
    for row in rows:
        n = row["n"]
        if n % 4 != 2:
            continue
        scaled = row.get("scaled_y_residue_global", row.get("scaled_Y_residue_global"))
        assert scaled
        nu_y = v2(scaled) - scale
        assert nu_y == row.get("nu_y", row.get("nu_Y"))
        m = n + 1
        gamma = 2 * m.bit_count() - (3 * m).bit_count()
        nu_B = 1 + gamma + nu_y
        checked += 1
        if nu_B < 2:
            failures.append({"N": n, "v2_B": nu_B})
    assert not failures
    return {"source_name": path.name,
            "source_sha256": sha256(path.read_bytes()).hexdigest(),
            "method": "read and recheck saved modular residues; no new scan",
            "source_max_n": maximum, "checked_N_2_mod4": checked,
            "failure_count": len(failures), "failures": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path("bbp-newton-quotient-mod4-verification.json"))
    args = parser.parse_args()
    result = {
        "format": "bbp-newton-quotient-mod4-verification/1",
        "arithmetic": "exact integers and Fraction; no floating point",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "proof_status": "finite reproduction of proved identities, not their proof",
        "coefficient_tables": [check_coefficient_table(J) for J in [8, 16, 24, 32, 64, 128]],
        "newton_pairs": [check_newton_pair(m, J)
                         for m, J in [(3, 8), (5, 8), (6, 16), (10, 16), (22, 48), (31, 8)]],
        "direct_B_checks": [check_B(N) for N in [2, 6, 10, 14, 18, 22]],
        "previous_certificate_recheck": check_certificate(args.certificate)
                                       if args.certificate else None,
        "all_checks_passed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output.resolve()), "all_checks_passed": True,
                      "direct_B_checks": len(result["direct_B_checks"]),
                      "previous_residues_checked":
                      result["previous_certificate_recheck"]["checked_N_2_mod4"]
                      if args.certificate else 0}))


if __name__ == "__main__":
    main()
