"""Exact finite checks for the adjacent-even BBP criterion (standard library).

The infinite theorem is proved in BBP-EVEN-DYADIC-TRANSFER.zh.md.  Finite
agreement outside its hypotheses is recorded as evidence, not as proof.
"""
from fractions import Fraction
import json
from math import comb
from pathlib import Path


def v2(n):
    if n == 0:
        raise ValueError("valuation of zero is not finite")
    n = abs(n)
    return (n & -n).bit_length() - 1


def v2q(x):
    return v2(x.numerator) - v2(x.denominator)


def carry_parameters(a):
    assert a > 0 and a % 2 == 1
    gamma = 2 * a.bit_count() - (3 * a).bit_count()
    cap = max(a.bit_count() + k.bit_count() - (a + k).bit_count()
              for k in range((a - 1) // 2 + 1))
    return cap, gamma


def direct_residue(n):
    """Full finite Beta sum via ratios and Pell; no terminal-delta formula."""
    m, ell = 4 * n, 8 * (n + 1)
    d = (12 * n + 9).bit_length() - 1
    modulus = 1 << (2 * d + 1)
    mask = modulus - 1
    p, q = 0, 1
    unit, exponent = pow(ell + 1, -1, modulus), 0
    total = 0
    for k in range(1, m + 1):
        numerator, denominator = k, ell + k + 1
        vn, vd = v2(numerator), v2(denominator)
        exponent += vn - vd
        unit = (unit * (numerator >> vn)
                * pow(denominator >> vd, -1, modulus)) & mask
        assert exponent + d >= 0
        if k % 2:
            p, q = q, (2 * q + p) & mask
            coefficient = p * p
        else:
            coefficient = -p * q
        total = (total + ((coefficient * unit) << (exponent + d))) & mask
    # Terms further back have 4*j+d >= 2*d+1 and vanish in this residue.
    for j in range(min(n, d // 2) + 1):
        i = n - j
        for numerator, denominator in (
            (4, 8 * i + 1), (-1, 8 * i + 5),
            (-(3 * i + 2), (2 * i + 1) * (4 * i + 3)),
        ):
            total = (total + ((numerator * pow(denominator, -1, modulus))
                              << (d + 4 * j))) & mask
    return total, d, 2 * d + 1


def exact_y(n):
    """Independent rational sum with the order-four kernel recurrence."""
    a = [0] * (4 * n + 1)
    for k in range(len(a)):
        a[k] = (int(k == 1)
                - (2 * a[k - 1] if k >= 1 else 0)
                - (2 * a[k - 3] if k >= 3 else 0)
                + (a[k - 4] if k >= 4 else 0))
    total = Fraction(0)
    for i in range(n + 1):
        total = (16 * total + Fraction(4, 8 * i + 1)
                 - Fraction(2, 8 * i + 4) - Fraction(1, 8 * i + 5)
                 - Fraction(1, 8 * i + 6))
    ell = 8 * (n + 1)
    beta = Fraction(1, ell + 1)
    for k, coefficient in enumerate(a):
        total += coefficient * beta
        beta *= Fraction(k + 1, ell + k + 2)
    return total


def normalized_delta(n):
    """Exact Delta_n/H_n, evaluating 12 short Beta ratios and the kernel."""
    a = [0, 1, -2, 4]
    for _ in range(4, 4 * n + 9):
        a.append(-2 * a[-1] - 2 * a[-3] + a[-4])
    ratios = {
        -3: Fraction(3 * (12 * n - 1), (4 * n - 1) * (4 * n - 2)),
        -2: Fraction(3, 4 * n - 1),
        -1: Fraction(1, 4 * n),
    }
    ratio = Fraction(1, 12 * n + 1)
    for b in range(9):
        ratios[b] = ratio
        ratio *= Fraction(4 * n + b + 1, 12 * n + b + 2)
    terms = []
    for b in range(-3, 9):
        coefficient = 16 * a[4 * n + b] - sum(
            (-1) ** j * comb(8, j) * a[4 * n + b - j]
            for j in range(max(0, b)))
        terms.append(ratios[b] * coefficient)
    return sum(terms, Fraction(0)), [v2q(t) if t else None for t in terms]


def run():
    rows = []
    certified = 0
    outside = []
    for n in range(4, 2049, 4):
        u = v2(n)
        a = n >> u
        cap, gamma = carry_parameters(a)
        valid = u >= max(2, cap - gamma - 3)
        residue, d, precision = direct_residue(n)
        assert residue != 0
        observed = v2(residue) - d
        assert observed == -gamma
        certified += int(valid)
        if not valid:
            outside.append({"N": n, "A": a, "u": u,
                            "C": cap, "gamma": gamma, "v2Y": observed})
        if a in (1, 3, 33, 65, 129, 257):
            rows.append({"N": n, "A": a, "u": u, "C": cap,
                         "gamma": gamma, "hypothesis_holds": valid,
                         "v2Y": observed, "scaled_residue": residue,
                         "d": d, "modulus_exponent": precision})
    exact_rows = []
    for n in (4, 8, 12, 20, 36):
        value = exact_y(n)
        residue, d, precision = direct_residue(n)
        mod = 1 << precision
        scaled = value * (1 << d)
        assert scaled.denominator % 2
        assert (scaled.numerator * pow(scaled.denominator, -1, mod)) % mod == residue
        assert v2q(value) == -(2 * n.bit_count() - (3 * n).bit_count())
        exact_rows.append({"N": n, "v2Y": v2q(value),
                           "numerator": str(value.numerator),
                           "denominator": str(value.denominator)})
    delta_rows = []
    for n in (4, 8, 12, 132, 516, 1028, 2048):
        delta, term_valuations = normalized_delta(n)
        assert v2q(delta) == 0
        assert term_valuations[4] == term_valuations[8] == -1
        assert all(v is None or v >= 1 for j, v in enumerate(term_valuations)
                   if j not in (4, 8))
        delta_rows.append({"N": n, "v2_normalized_delta": 0,
                           "offsets": list(range(-3, 9)),
                           "term_valuations": term_valuations})
    for a in range(1, 64, 2):
        cap, gamma = carry_parameters(a)
        assert gamma == v2(comb(3 * a, a))
        assert gamma == v2(comb((3 * a - 1) // 2, (a - 1) // 2))
        assert cap == max(v2(comb(a + k, k)) for k in range((a - 1) // 2 + 1))
    return {
        "format": "bbp-adjacent-even-criterion/1",
        "finite_range": {"N_min": 4, "N_max": 2048, "step": 4,
                         "checked": 512, "theorem_hypothesis_holds": certified,
                         "formula_failures": []},
        "observations_outside_hypotheses": outside,
        "selected_rows": rows,
        "exact_fraction_checks": exact_rows,
        "normalized_delta_checks": delta_rows,
        "scope": "Finite agreement outside the theorem hypotheses is not an infinite proof.",
    }


if __name__ == "__main__":
    result = run()
    destination = Path(__file__).with_name("bbp-even-dyadic-transfer-verification.json")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"finite_range": result["finite_range"],
                      "outside_hypotheses_count": len(result["observations_outside_hypotheses"]),
                      "exact_fraction_checks": len(result["exact_fraction_checks"]),
                      "normalized_delta_checks": len(result["normalized_delta_checks"]),
                      "output": str(destination)}, ensure_ascii=False))
