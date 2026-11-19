"""Verify finite examples in PI-LINE-ARBITRARY-DELAY.zh.md."""
from fractions import Fraction


def convergents(digits):
    older_num, num = 0, 1
    older_den, den = 1, 0
    for digit in digits:
        older_num, num = num, digit*num + older_num
        older_den, den = den, digit*den + older_den
        yield num, den


def nearest_height(column, slope):
    return (2*column*slope.numerator+slope.denominator)//(2*slope.denominator)


def main():
    prefix = [3, 7, 15, 1, 292]
    low = Fraction(*list(convergents(prefix))[-1])
    high = Fraction(*list(convergents(prefix+[1]))[-1])
    assert low < high < Fraction(355, 113)
    reference = Fraction(355, 113)
    for column in range(16664):
        assert nearest_height(column, low) == nearest_height(column, high)
        assert nearest_height(column, low) == nearest_height(column, reference)
    assert nearest_height(16664, low) == nearest_height(16664, high) == 52351
    assert nearest_height(16664, reference) == 52352
    print("Common staircase through column 16664, first change against 355/113 at 16664.")

    prefix_with_ones = prefix+[1]*458
    prefix_convergents = list(convergents(prefix_with_ones))
    assert len(prefix_convergents) == 463
    prior_den = prefix_convergents[-2][1]
    num, den = prefix_convergents[-1]
    assert prior_den < 10**100 < den
    next_digit = 10**6

    # The exact E range on the next continued-fraction cylinder is
    # 1/(next_digit+1+prior_den/den) < E < 1/(next_digit+prior_den/den).
    lower_bound = Fraction(den, (next_digit+1)*den+prior_den)
    upper_bound = Fraction(den, next_digit*den+prior_den)
    assert Fraction(1, next_digit+2) < lower_bound < upper_bound < Fraction(1, 10**6)
    print("First new record after adding the next partial quotient of a million:")
    print("p =", num)
    print("q =", den)


if __name__ == "__main__":
    main()
