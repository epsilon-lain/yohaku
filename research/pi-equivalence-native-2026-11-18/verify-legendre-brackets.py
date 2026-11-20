"""Check Legendre brackets for pi, including the exact 2-adic gap."""
from fractions import Fraction as F
from math import comb


def arctan_bounds(base, digits=190):
    threshold = 10**digits
    value = F(0)
    index, power = 0, base
    while True:
        term = F((-1)**index, (2*index + 1)*power)
        if term.denominator >= threshold:
            return min(value, value + term), max(value, value + term)
        value += term
        power *= base**2
        index += 1


def pi_enclosures():
    low5, high5 = arctan_bounds(5)
    low239, high239 = arctan_bounds(239)
    low2, high2 = arctan_bounds(2)
    low3, high3 = arctan_bounds(3)
    return [
        (16*low5 - 4*high239, 16*high5 - 4*low239),
        (4*(low2 + low3), 4*(high2 + high3)),
    ]


def v2_integer(value):
    value = abs(value)
    assert value
    return (value & -value).bit_length() - 1


def v2_fraction(value):
    return v2_integer(value.numerator) - v2_integer(value.denominator)


def sequences(b, last):
    p, w = [F(1), b], [F(0), F(1)]
    for m in range(1, last):
        p.append(((2*m + 1)*b*p[m] + m*p[m-1]) / (m + 1))
        w.append(((2*m + 1)*b*w[m] + m*w[m-1]) / (m + 1))
    return p, w


def p_by_coefficients(b, m):
    return sum((F(comb(m, k)*comb(2*m - 2*k, m), 2**m)*b**(m - 2*k)
                for k in range(m//2 + 1)), F(0))


def certify():
    orders = [4, 8, 16, 32, 64, 128]
    last = 3*orders[-1] + 1
    b2, b_half = F(2), F(1, 2)
    p2, w2 = sequences(b2, last)
    ph, wh = sequences(b_half, last)
    for m in range(last + 1):
        k, odd = divmod(m, 2)
        assert v2_fraction(p2[m]) == -2*k + k.bit_count() + odd
        assert v2_fraction(ph[m]) == -2*m + m.bit_count()
        for p, w in ((p2, w2), (ph, wh)):
            if m:
                assert p[m-1]*w[m] - p[m]*w[m-1] == F((-1)**(m+1), m)
        if m < 50 or m >= last - 2:
            assert p2[m] == p_by_coefficients(b2, m)
            assert ph[m] == p_by_coefficients(b_half, m)

    intervals = pi_enclosures()
    print("Same-sign internal remainders; opposite-sign outer bracket.")
    print("n | bit lengths of reduced denominators | v2(rational gap) | v2(integer determinant)")
    for n in orders:
        left = 2*(w2[n]/p2[n] + wh[3*n]/ph[3*n])
        right = 2*(w2[n+1]/p2[n+1] + wh[3*n+1]/ph[3*n+1])
        assert all(left < lo <= hi < right for lo, hi in intervals)
        gap = right - left
        value = 4*(n//2) - 2*(n//2).bit_count()
        assert v2_fraction(gap) == value
        determinant = right.numerator*left.denominator - left.numerator*right.denominator
        assert determinant > 0
        assert v2_integer(determinant) == value + v2_integer(left.denominator) + v2_integer(right.denominator)
        print(n, (left.denominator.bit_length(), right.denominator.bit_length()),
              value, v2_integer(determinant))


if __name__ == "__main__":
    certify()
