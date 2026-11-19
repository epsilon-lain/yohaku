"""Exact verification for the n=2 and n=6 (mod 8) delta conclusions."""
from fractions import Fraction
from math import comb, prod
from pathlib import Path
import hashlib
import json
import argparse


def trim(p):
    p = list(p)
    while len(p) > 1 and p[-1] == 0:
        p.pop()
    return p


def add(a, b):
    c = [0] * max(len(a), len(b))
    for i, x in enumerate(a):
        c[i] += x
    for i, x in enumerate(b):
        c[i] += x
    return trim(c)


def mul(a, b):
    c = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            c[i + j] += x * y
    return trim(c)


def scale(a, x):
    return trim([x * t for t in a])


def product(ps):
    p = [1]
    for q in ps:
        p = mul(p, q)
    return p


def rational_add(a, b):
    return add(mul(a[0], b[1]), mul(b[0], a[1])), mul(a[1], b[1])


def equivalent(a, b):
    return add(mul(a[0], b[1]), scale(mul(b[0], a[1]), -1)) == [0]


U = [10080, -272811, -8442946, -34565408, 284154240,
     2566195648, 7529847552, 9676051456, 4623069184]
V = [-241440, -4618561, -6424182, 282952176, 1973864448,
     5414826240, 6750795264, 3171880960]
W = [-939, -11606, 109968, 1712272, 6165888, 6766336]
D = product([[0, 1], [-1, 2], [2, 3], [-1, 4], [1, 6],
             [1, 12], [5, 12], [7, 12]])

quadratic_coefficients = {
    -3: [64, -64, 16], -2: [32, -16, 0], -1: [16, 0, 0],
    0: [0, -16, 0], 1: [0, 0, 15], 2: [0, -15, -22],
    3: [15, 52, 16], 4: [-22, -75, -6], 5: [16, 60, 1],
    6: [-6, -29, 0], 7: [1, 8, 0], 8: [0, -1, 0],
}


def verify_pell_quadratics():
    pairs = {-1: (-2, 1), 0: (1, 0), 1: (0, 1)}
    for j in range(2, 6):
        pairs[j] = tuple(2 * x + y for x, y in zip(pairs[j - 1], pairs[j - 2]))
    def quadratic(left, right):
        a, b = left
        c, d = right
        return [a * c, a * d + b * c, b * d]
    aa = {}
    for b in range(-3, 9):
        if b % 2:
            j = (b + 1) // 2
            aa[b] = quadratic(pairs[j], pairs[j])
        else:
            j = b // 2
            aa[b] = [-x for x in quadratic(pairs[j], pairs[j + 1])]
    for b in range(-3, 9):
        value = [16 * x for x in aa[b]]
        for ell in range(max(0, b)):
            multiplier = (-1) ** ell * comb(8, ell)
            value = [x - multiplier * y for x, y in zip(value, aa[b - ell])]
        assert value == quadratic_coefficients[b], b
    return True


def verify_polynomial_identity():
    assert verify_pell_quadratics()
    ratios = {
        -3: ([-3, 36], mul([-1, 4], [-2, 4])),
        -2: ([3], [-1, 4]),
        -1: ([1], [0, 4]),
    }
    for b in range(9):
        ratios[b] = (product([[i, 4] for i in range(1, b + 1)]),
                     product([[i, 12] for i in range(1, b + 2)]))
    common = mul(D, [1, 3])
    targets = [
        (U, scale(common, 36)),
        (scale(mul([0, 1], V), -1), scale(common, 27)),
        (product([[0, 1], [2, 3], [7, 12], W]), scale(common, 9)),
    ]
    for q in range(3):
        total = ([0], [1])
        for b, coefficients in quadratic_coefficients.items():
            if coefficients[q]:
                r = ratios[b]
                total = rational_add(total, (scale(r[0], coefficients[q]), r[1]))
        assert equivalent(total, targets[q]), q
    assert trim([a % 4 for a in U]) == [0, 1, 2]
    assert trim([a % 4 for a in V]) == [0, 3, 2]
    assert trim([a % 4 for a in W]) == [1, 2]
    return {"method": "exact polynomial cross multiplication over integers",
            "pell_table_rederived_from_signed_twelve_term_formula": True,
            "three_quadratic_coefficients_verified": True,
            "U_mod4": [0, 1, 2], "V_mod4": [0, 3, 2], "W_mod4": [1, 2]}


def v2(n):
    n = abs(n)
    assert n
    return (n & -n).bit_length() - 1


def evaluate(poly, n):
    answer = 0
    for coefficient in reversed(poly):
        answer = answer * n + coefficient
    return answer


def fraction_v2(x):
    assert x
    return v2(x.numerator) - v2(x.denominator)


def exact_Y(N):
    M, L = 4 * N, 8 * (N + 1)
    a = [0, 1, -2, 4][:M + 1]
    for k in range(4, M + 1):
        a.append(-2 * a[k - 1] - 2 * a[k - 3] + a[k - 4])
    total = Fraction(0)
    for i in range(N + 1):
        total = (16 * total + Fraction(4, 8 * i + 1) -
                 Fraction(2, 8 * i + 4) - Fraction(1, 8 * i + 5) -
                 Fraction(1, 8 * i + 6))
    beta = Fraction(1, L + 1)
    for k, coefficient in enumerate(a):
        total += coefficient * beta
        beta *= Fraction(k + 1, L + k + 2)
    return total


def gamma(n):
    return 2 * n.bit_count() - (3 * n).bit_count()


def check_case(n):
    assert n % 4 == 2
    x, y = 0, 1
    for _ in range(2 * n):
        x, y = y, 2 * y + x
    assert x % 4 == 0 and (x // 4) % 2 == y % 2 == 1
    p = x // 4
    ratios = {
        -3: Fraction(3 * (12 * n - 1), (4 * n - 1) * (4 * n - 2)),
        -2: Fraction(3, 4 * n - 1),
        -1: Fraction(1, 4 * n),
    }
    for b in range(9):
        ratios[b] = Fraction(prod(4 * n + i for i in range(1, b + 1)),
                             prod(12 * n + i for i in range(1, b + 2)))
    T = sum((ratios[b] * (c[0] * x*x + c[1] * x*y + c[2] * y*y)
             for b, c in quadratic_coefficients.items()), Fraction(0))
    E = prod([2 * n - 1, 4 * n - 1, 6 * n + 1,
              12 * n + 1, 12 * n + 5, 12 * n + 7])
    Un, Vn, Wn = evaluate(U, n), evaluate(V, n), evaluate(W, n)
    assert (v2(Un), v2(Vn), v2(Wn)) == (1, 1, 0)
    terms = [Fraction(p*p * Un, 9 * n * E * (3*n+1)),
             Fraction(-p*y * Vn, 27 * E * (3*n+1)),
             Fraction((3*n+2)*(12*n+7)*y*y * Wn, 36 * E * (3*n+1))]
    Z = Fraction(3*n+2, 4) * T
    assert Z == sum(terms, Fraction(0))
    v = v2(3*n+2)
    assert [fraction_v2(term) for term in terms] == [0, 1, v - 2]
    if n % 8 == 2:
        assert fraction_v2(Z) == 0 and fraction_v2(T) == 2 - v
    else:
        assert v == 2 and fraction_v2(Z) >= 1 and fraction_v2(T) >= 1
    Y, previous = exact_Y(n), exact_Y(n - 1)
    H = Fraction(1, comb(12*n, 4*n))
    assert Y - 16 * previous == H * T
    assert gamma(n+1) - gamma(n) == v - 1
    assert fraction_v2(16 * previous) >= 3 - gamma(n)
    B = 2 * comb(3*(n+1), n+1) * Y
    assert B.denominator % 2 == 1
    residue = B.numerator * pow(B.denominator, -1, 8) % 8
    if n % 8 == 2:
        assert fraction_v2(Y) == 1 - gamma(n+1)
        assert fraction_v2(B) == 2 and residue == 4
    else:
        assert fraction_v2(Y) >= 2 - gamma(n+1)
        assert fraction_v2(B) >= 3 and residue == 0
    return {'n': n, 'n_mod8': n % 8, 'v2_3n_plus_2': v,
            'quadratic_component_valuations': [fraction_v2(t) for t in terms],
            'v2_T': fraction_v2(T), 'v2_Z': fraction_v2(Z),
            'gamma_n': gamma(n), 'gamma_n_plus_1': gamma(n+1),
            'v2_Y': fraction_v2(Y), 'v2_B': fraction_v2(B), 'B_mod8': residue,
            'direct_Y_difference_agrees_with_local_delta': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path('bbp-two-mod-eight-verification.json'))
    args = parser.parse_args()
    result = {'format': 'bbp-two-mod-eight-verification/1',
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'arithmetic': 'exact integer polynomials and Fraction; no floating point',
              'polynomial_identity': verify_polynomial_identity(),
              'two_mod8_exact_checks': [check_case(n) for n in [2, 10, 18, 26, 42, 170]],
              'six_mod8_lower_bound_checks': [check_case(n) for n in [6, 14, 110]],
              'scope': 'nine isolated exact checks; not a scan or proof by examples',
              'all_checks_passed': True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.output.resolve()), 'all_checks_passed': True,
                      'two_mod8_cases': 6, 'six_mod8_cases': 3}))


if __name__ == '__main__':
    main()
