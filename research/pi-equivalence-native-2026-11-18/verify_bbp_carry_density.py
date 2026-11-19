"""Exact checks for simultaneous cancellations in the BBP carry primes."""

from fractions import Fraction
from itertools import combinations
from math import comb, gcd, isqrt


def coefficients(end):
    # Generate coefficients independently of polynomial reduction via Pell numbers.
    pell = [0, 1]
    while len(pell) <= end // 2 + 2:
        pell.append(2 * pell[-1] + pell[-2])
    return [(-pell[k // 2] * pell[k // 2 + 1] if k % 2 == 0
             else pell[(k + 1) // 2] ** 2) for k in range(end + 1)]


def snapshots(n, end, coeff):
    length = 8 * (n + 1)
    raw = sum(Fraction(weight, 16**k * (8*k + shift))
              for k in range(n + 1)
              for shift, weight in ((1, 4), (4, -2), (5, -1), (6, -1)))
    moments = [Fraction(1, length + 1)]
    values = [raw]
    for k in range(1, end + 1):
        moments.append(moments[-1] * Fraction(k, length + k + 1))
        values.append(values[-1] + moments[-1] * coeff[k] / 16**n)
    return moments, values


def shift(poly):
    # X^4 = 1-2X-2X^3 modulo (X^2+2X-1)(X^2+1).
    a, b, c, d = poly
    return d, a - 2*d, b, c - 2*d


def rows(m, length, width):
    basis = (1, 0, 0, 0)
    coefs = [Fraction(0)] * 4
    result = [(Fraction(1), *coefs)]
    weight = Fraction(1)
    for r in range(1, width + 1):
        basis = shift(basis)
        weight *= Fraction(m + r, length + m + 1 + r)
        coefs = [x + weight*y for x, y in zip(coefs, basis)]
        result.append((Fraction(1), *coefs))
    return result


def determinant(matrix):
    data = [row[:] for row in matrix]
    value = Fraction(1)
    for col in range(len(matrix)):
        pivot = next((j for j in range(col, len(matrix)) if data[j][col]), None)
        if pivot is None:
            return Fraction(0)
        if col != pivot:
            data[pivot], data[col] = data[col], data[pivot]
            value = -value
        value *= data[col][col]
        for j in range(col+1, len(matrix)):
            ratio = data[j][col] / data[col][col]
            for k in range(col+1, len(matrix)):
                data[j][k] -= ratio * data[col][k]
    return value


def mod(value, p):
    return value.numerator * pow(value.denominator, -1, p) % p


def primes(limit):
    return [p for p in range(3, limit + 1, 2)
            if all(p % d for d in range(3, isqrt(p) + 1, 2))]


def main():
    determinants = prime_rows = observed_zeros = checked_five = 0
    for n in (7, 32, 81, 124):
        m, width = 4*n, 32
        length = 8*(n + 1)
        coeff = coefficients(m + width + 4)
        moments, values = snapshots(n, m + width, coeff)
        matrix = rows(m, length, width)
        index_sets = list(combinations(range(0, width + 1, 4), 5))
        dets = {}
        for offsets in index_sets:
            d = determinant([list(matrix[k]) for k in offsets])
            assert d
            dets[offsets] = d
            determinants += 1
        for p in primes(length + m + width + 1):
            if p*p <= length + m + width + 1 or moments[m].denominator % p:
                continue
            if any((m + r) % p == 0 or (length + m + 1 + r) % p == 0
                   for r in range(1, width + 1)):
                continue
            unit = mod(p * moments[m] / 16**n, p)
            vector = [mod(p*values[m], p), *(unit*k % p for k in coeff[m:m+4])]
            assert unit and any(vector[1:]) and gcd(*coeff[m:m+4]) == 1
            zeros = set()
            for s, row in enumerate(matrix):
                value = sum(mod(x, p)*a for x,a in zip(row, vector)) % p
                assert value == mod(p*values[m+s], p)
                assert bool(value) == (values[m+s].denominator % p == 0)
                prime_rows += 1
                if value == 0:
                    zeros.add(s)
                    observed_zeros += 1
            for offsets, d in dets.items():
                if all(s in zeros for s in offsets):
                    assert not mod(d, p)
                checked_five += 1
    assert observed_zeros > 0
    print(f"{determinants} exact nonzero 5x5 minors; "
          f"{prime_rows} direct rational/modular values, {observed_zeros} cancellations; "
          f"{checked_five} simultaneous-zero checks")


if __name__ == "__main__":
    main()
