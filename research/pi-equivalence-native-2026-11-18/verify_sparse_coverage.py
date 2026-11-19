"""Exact audit of the established BBP seed-shift coverage mechanism.

No floating-point logarithms, numerical pi values, or external dependencies.
The finite checks support the proofs in SPARSE-COVERAGE-OBSTRUCTION.zh.md;
they do not replace those proofs or certify all even N.
"""
from fractions import Fraction
import argparse
import json
from pathlib import Path


def v2_int(n):
    if not n:
        raise ValueError("v2(0) is not finite")
    n = abs(n)
    return (n & -n).bit_length() - 1


def exact_y(n):
    """Original BBP prefix plus exact finite Beta correction."""
    m, ell = 4 * n, 8 * n + 8
    a = []
    for k in range(m + 1):
        a.append(int(k == 1)
                 - (2 * a[k - 1] if k >= 1 else 0)
                 - (2 * a[k - 3] if k >= 3 else 0)
                 + (a[k - 4] if k >= 4 else 0))
    total = Fraction(0)
    for i in range(n + 1):
        total = (16 * total + Fraction(4, 8 * i + 1)
                 - Fraction(2, 8 * i + 4) - Fraction(1, 8 * i + 5)
                 - Fraction(1, 8 * i + 6))
    beta = Fraction(1, ell + 1)
    for k, ak in enumerate(a):
        total += ak * beta
        beta *= Fraction(k + 1, ell + k + 2)
    return total


def denom_bits(c):
    return (12 * c + 9).bit_length() - 1


def threshold(c, nu):
    d = denom_bits(c)
    return max(2, d - 1, nu + 2 * d - 1)


def geometric_candidate(n):
    if n < 4:
        return None
    s = n.bit_length() - 1
    w = 1 << s
    c = n - w
    return (s, c) if c >= 1 and 12 * c + 9 < 4 * w else None


def all_geometric_decompositions(n):
    """Independent exhaustive form of the original s >= d(c)-1 check."""
    result = []
    for s in range(2, (n - 1).bit_length()):
        c = n - (1 << s)
        if c > 0 and s >= denom_bits(c) - 1:
            result.append((s, c))
    return result


def enumerate_descendants(seed, nu, k):
    """Use only the original threshold at each node, not the binary-gap rule."""
    limit = 1 << k
    found = set()
    stack = [seed] if seed < limit else []
    while stack:
        c = stack.pop()
        assert c not in found  # highest-bit decomposition is unique
        found.add(c)
        assert nu < 4 * c - 3
        for s in range(threshold(c, nu), k):
            child = c + (1 << s)
            if child < limit:
                stack.append(child)
    return found


def descendant_counts(kmax, seed, nu):
    """Count through the independently derived highest-exponent recurrence."""
    s0 = threshold(seed, nu)
    a = nu + 5
    counts = [int(seed < (1 << k)) for k in range(kmax + 1)]
    for k in range(s0, kmax):
        counts[k + 1] = counts[k] + counts[(k - a) // 2 + 1]
    return counts


def run():
    geometry_limit = 1 << 14
    for n in range(4, geometry_limit):
        candidate = geometric_candidate(n)
        expected = [] if candidate is None else [candidate]
        assert all_geometric_decompositions(n) == expected, n
    geometry_rows = []
    cumulative = 0
    for s in range(2, 14):
        w = 1 << s
        boundary = 4 * w // 3
        assert bin(boundary)[2:] == ("10" * (s + 1))[:s + 1]
        actual = [n for n in range(w, 2 * w, 2)
                  if geometric_candidate(n) is not None]
        count = (w - 3) // 6
        assert len(actual) == count
        assert actual == list(range(w + 2, w + 2 * count + 1, 2))
        cumulative += count
        assert cumulative == ((1 << (s + 1)) + 3 + (-1) ** s) // 6 - s
        geometry_rows.append({"s": s, "block_start": w,
                              "forbidden_from": boundary,
                              "even_candidates": count})
    for u in range(1, 128):
        assert geometric_candidate(3 << u) is None
    assert geometric_candidate(42) is None  # exact endpoint, not 4W/3

    seeds = []
    for seed, expected_nu in ((2, -1), (14, 0), (110, 4)):
        y = exact_y(seed)
        nu = v2_int(y.numerator) - v2_int(y.denominator)
        assert nu == expected_nu
        counts = descendant_counts(1024, seed, nu)
        for k in range(2, 71):
            actual = enumerate_descendants(seed, nu, k)
            assert len(actual) == counts[k], (seed, k)
            if seed == 2:
                for n in actual:
                    assert n & 255 == 2
                    es = [e for e in range(8, k) if (n >> e) & 1]
                    assert n == 2 + sum(1 << e for e in es)
                    assert all(b >= 2 * a + 4 for a, b in zip(es, es[1:]))
        seeds.append({"seed": seed, "v2Y": nu,
                      "first_exponent": threshold(seed, nu),
                      "next_exponent_offset": nu + 5,
                      "counts_below_two_power": {
                          str(k): counts[k] for k in (16, 32, 64, 128, 256, 512, 1024)}})
    assert seeds[0]["counts_below_two_power"] == {
        "16": 9, "32": 67, "64": 813, "128": 18967,
        "256": 807809, "512": 60963051, "1024": 8182440533}
    return {
        "format": "bbp-sparse-coverage-audit/1",
        "baseline_commit": "e28ad613e651b94e3e2f235452e2de3c60aabc01",
        "geometric_exhaustive_N": [4, geometry_limit - 1],
        "descendant_count_crosscheck_K": [2, 70],
        "geometry_rows": geometry_rows, "seed_rows": seeds,
        "scope": "Coverage of the stated sufficient theorem only; no all-even claim."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    result = run()
    if args.json:
        args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False))
