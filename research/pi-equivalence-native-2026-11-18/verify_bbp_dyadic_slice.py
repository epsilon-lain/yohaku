"""Check the single-truncation dyadic theorem by direct rational evaluation."""

from fractions import Fraction


def valuation_two(integer):
    assert integer
    return (abs(integer) & -abs(integer)).bit_length() - 1


def raw_scaled(n):
    weights = ((1, 4), (4, -2), (5, -1), (6, -1))
    return sum(
        Fraction(weight * 16**(n - k), 8 * k + shift)
        for k in range(n + 1) for shift, weight in weights
    )


def main():
    checked, mersenne = 0, 0
    for n in range(128):
        length = 8 * n + 8
        cap = (length & -length) - 2
        scaled = raw_scaled(n)
        assert scaled.denominator % 2 == 1
        moment = Fraction(1, length + 1)
        coeff = [0]
        for k in range(1, cap + 1):
            first = int(k == 1) - 2 * coeff[k - 1]
            if k >= 3:
                first -= 2 * coeff[k - 3]
            if k >= 4:
                first += coeff[k - 4]
            coeff.append(first)
            moment *= Fraction(k, length + k + 1)
            scaled += first * moment
            twice = 2 * scaled
            assert twice.denominator % 2 == 1
            expected_odd = k % 8 in (1, 2, 3, 4)
            assert bool(twice.numerator % 2) == expected_odd
            if expected_odd:
                assert valuation_two((scaled / 16**n).denominator) == 4 * n + 1
            checked += 1
            if n & (n + 1) == 0 and k == 4 * n:
                assert expected_odd
                mersenne += 1
    print(f"{checked} directly reduced rational truncations; {mersenne} with N=2^h-1 and M=4N")


if __name__ == "__main__":
    main()
