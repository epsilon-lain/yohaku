"""Exact finite checks for the BBP correction in an inverse-factorial basis.

No floating point or external Python packages are used.
"""
from fractions import Fraction
from math import comb, factorial, prod

MODIFIED_DEGREES = (1, 2, 7, 16, 64, 130, 217)


def arctangent_bounds(inverse, terms=128):
    """Even-length alternating arctangent sum, followed by its first omitted term."""
    assert terms % 2 == 0
    x = Fraction(1, inverse)
    partial = sum((-1)**j * x**(2*j + 1) / (2*j + 1) for j in range(terms))
    return partial, partial + x**(2*terms + 1) / (2*terms + 1)


def pi_bounds():
    a, b = arctangent_bounds(5)
    c, d = arctangent_bounds(239)
    return 16*a - 4*d, 16*b - 4*c


def v2_nonzero(value):
    if not value:
        raise ValueError("v2 is tested only for nonzero values.")
    numerator = abs(value.numerator)
    denominator = value.denominator
    return (numerator & -numerator).bit_length() - (denominator & -denominator).bit_length()


def coefficients(maximum):
    """Series coefficients from multiplication by the linear factor 15+y."""
    powers = (Fraction(7, 8), Fraction(1, 2), Fraction(3, 8), Fraction(1, 4))
    rising = [Fraction(1)] * 4
    c = Fraction(0)
    yield c
    for k in range(1, maximum + 1):
        rising = [value*(k-1+power)/k for value, power in zip(rising, powers)]
        b = 4*rising[0] - 2*rising[1] - rising[2] - rising[3]
        c = (2*b-c)/15
        yield c


def check_coefficients(c):
    factorial_exponent = 0
    for k, coefficient in enumerate(c[1:], start=1):
        factorial_exponent += v2_nonzero(k)
        assert Fraction(1,5*k) <= coefficient <= Fraction(8,15)
        assert v2_nonzero(coefficient) == 1 - 3*k - factorial_exponent
        denominator = coefficient.denominator
        for possible_prime in (2, 3, 5):
            while denominator % possible_prime == 0:
                denominator //= possible_prime
        assert denominator == 1


def bbp_term(k):
    return (Fraction(4, 8*k+1) - Fraction(2, 8*k+4)
            - Fraction(1, 8*k+5) - Fraction(1, 8*k+6))


def beta(a, b):
    return Fraction(1, (a+b-1) * comb(a+b-2, b-1))


def prime(p):
    return p >= 2 and all(p % d for d in range(2, p) if d*d <= p)


def verify():
    pi_lower, pi_upper = pi_bounds()
    c = list(coefficients(max(MODIFIED_DEGREES)))
    assert c[1] == Fraction(1,4)
    check_coefficients(c)
    base = Fraction(0)
    count = retained = 0
    for n in range(24):
        base += bbp_term(n) / 16**n
        x = base
        correction_scale = Fraction(1,16**(n+1))
        for k in range(1, len(c)):
            x += correction_scale * c[k] * beta(n+2, k+1)
            if k not in MODIFIED_DEGREES:
                continue
            factorial_quotient = factorial(n+k+2) // factorial(n+1)
            expected_denominator_exponent = 4*n+3+3*k+v2_nonzero(factorial_quotient)
            assert v2_nonzero(x) == -expected_denominator_exponent, (n,k)
            error_lower = correction_scale * beta(n+2,k+2) / (5*(k+1))
            error_upper = correction_scale * Fraction(8,15) * beta(n+1,k+2)
            assert error_lower <= pi_lower-x <= pi_upper-x <= error_upper, (n,k)
            assert x.denominator**2 * (pi_lower-x) >= Fraction(
                2**(3*n+5*k), 5*(k+1)*(n+k+3)), (n,k)
            for p in range(max(4*n+3,n+k+2)+1, 8*n+2):
                if p % 4 == 1 and prime(p):
                    assert x.denominator % p == 0, (n,k,p)
                    retained += 1
            count += 1
    print(f"{len(c)-1} coefficient valuations and {count} exact corrected truncations passed.")
    print(f"Verified survival of {retained} original odd-prime denominator factors.")


if __name__ == "__main__":
    verify()
