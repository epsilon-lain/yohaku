"""Exact finite checks for the adjacent-degree denominator theorem (standard library)."""

from fractions import Fraction
from math import comb, factorial, gcd, isqrt


def pell_numbers(limit):
    values = [0, 1]
    for _ in range(2, limit + 1):
        values.append(2 * values[-1] + values[-2])
    return values


def kernel_coefficients(limit):
    values = []
    for k in range(limit + 1):
        def previous(offset):
            return values[k - offset] if k >= offset else 0
        values.append(int(k == 1) - 2 * previous(1) - 2 * previous(3) + previous(4))
    return values


def primes(limit):
    candidates = bytearray([1]) * (limit + 1)
    for p in range(2, limit + 1):
        if candidates[p]:
            yield p
            for multiple in range(p * p, limit + 1, p):
                candidates[multiple] = 0


def v2(value):
    return (value & -value).bit_length() - 1


def verify_pell(limit):
    pell = pell_numbers(limit + 1)
    coefficients = kernel_coefficients(2 * limit)
    for m in range(1, limit + 1):
        assert coefficients[2 * m - 1] == pell[m] ** 2
        assert coefficients[2 * m] == -pell[m] * pell[m + 1]
        assert v2(pell[m]) == v2(m)
    checks = 0
    for p in primes(limit):
        if p == 2:
            continue
        prev, cur = 0, 1
        rank = None
        for index in range(1, max(limit, p + 1) + 1):
            if cur == 0 and rank is None:
                rank = index
            if index <= limit:
                assert (cur == 0) == (pell[index] % p == 0)
                assert (cur == 0) == (rank is not None and index % rank == 0)
                checks += 1
            prev, cur = cur, (2 * cur + prev) % p
        character = 1 if pow(2, (p - 1) // 2, p) == 1 else -1
        assert rank is not None and (p - character) % rank == 0
    return checks


def raw_bbp(n):
    return sum(
        Fraction(weight, 16 ** k * (8 * k + shift))
        for k in range(n + 1)
        for shift, weight in ((1, 4), (4, -2), (5, -1), (6, -1))
    )


def translated_integral(coefficients, length):
    """Integrate x^length P(1-x) as a rational polynomial."""
    translated = [0] * len(coefficients)
    for k, coefficient in enumerate(coefficients):
        for j in range(k + 1):
            translated[j] += (-1) ** j * comb(k, j) * coefficient
    return sum(Fraction(value, length + j + 1) for j, value in enumerate(translated))


def verify_differences():
    coefficients = kernel_coefficients(47)
    prime_list = list(primes(400))
    comparisons = 0
    prime_comparisons = 0
    for n in range(1, 21):
        length = 8 * n + 8
        scale = 16 ** n
        raw = raw_bbp(n)
        previous = raw
        for k in range(1, 48):
            current = raw + translated_integral(coefficients[:k + 1], length) / scale
            d = length + k + 1
            beta_den = factorial(d) // (factorial(length) * factorial(k))
            delta = current - previous
            assert delta == Fraction(coefficients[k], scale * beta_den)
            assert delta.denominator == scale * beta_den // gcd(coefficients[k], scale * beta_den)
            assert (current.denominator * previous.denominator) % delta.denominator == 0
            for p in prime_list:
                if p > d:
                    break
                power = p
                valuation = 0
                while power <= d:
                    carry = d // power - length // power - k // power
                    assert carry in (0, 1)
                    valuation += carry
                    power *= p
                assert beta_den % p ** valuation == 0 and beta_den % p ** (valuation + 1) != 0
                assert p <= isqrt(d) or valuation <= 1
                prime_comparisons += 1
            previous = current
            comparisons += 1
    return comparisons, prime_comparisons


if __name__ == "__main__":
    modular = verify_pell(512)
    differences, valuations = verify_differences()
    print(f"1024 Taylor/Pell coefficients; 512 dyadic Pell valuations; {modular} modular rank checks")
    print(f"{differences} exact adjacent differences; {valuations} factorial prime valuations")
