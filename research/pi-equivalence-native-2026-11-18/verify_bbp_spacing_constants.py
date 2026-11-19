"""Independent integer checks for the numerical dyadic spacing bounds."""

from fractions import Fraction
from math import comb, factorial, lcm


def main():
    # Rational witnesses for the elementary exponential/logarithmic comparisons.
    assert sum(Fraction(1, factorial(k)) for k in range(4)) > Fraction(5, 2)
    assert sum(Fraction(7, 3)**k / factorial(k) for k in range(10)) > 10
    # exp(7/3)>10 supplies log 10 < 7/3; log 2 is in (1/2,1).
    assert 9 * (20 + 101 * Fraction(7, 3)) < 2500
    assert 3 * 113 * Fraction(7, 3) < 800
    crude_yu = 58 * (32 * 16 * 64)**2 * 81 * 10**5 * 10**5 * 4 * 12
    assert crude_yu < 10**30
    assert 2**16 * (64 * 16 * 5)**2 < 10**13
    assert 10**30 * 16**2 * 800 < 10**37
    assert (10**100 + 1) * (7 * 10**100 + 1) < 10**203

    # With b=L+m+2 the reduced Beta ratio is
    # C(m+1+j,j)/C(b+j,j). Test the shared denominator with no simplification.
    count = 0
    for b in range(1, 88, 3):
        for width in range(1, 49):
            multiple = comb(b + width, width) * lcm(*range(1, width + 2))
            for j in range(width + 1):
                assert multiple % comb(b + j, j) == 0
                assert comb(b + width, width) * comb(width, j) == (
                    comb(b + j, j) * comb(b + width, width - j)
                )
                count += 1
    print(f"{count} exact shared-denominator checks; explicit Yu and box constants verified")


if __name__ == "__main__":
    main()
