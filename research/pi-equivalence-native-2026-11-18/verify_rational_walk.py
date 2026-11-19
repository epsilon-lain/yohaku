"""Exact Farey walks for reduced rational approximations to pi."""

from fractions import Fraction
from functools import cache
from math import gcd

from verify_bbp_factorial import arctangent_bounds


def rational_at(index):
    """Index every reduced rational exactly once by Calkin–Wilf walks and signs."""
    if index < 0:
        raise ValueError("nonnegative index required")
    if index == 0:
        return 0, 1
    p, q = 1, 1
    for turn in bin((index + 1) // 2)[3:]:
        if turn == "0":
            q += p
        else:
            p += q
    return (p if index % 2 else -p), q


@cache
def pi_interval(terms):
    lower_5, upper_5 = arctangent_bounds(5, terms)
    lower_239, upper_239 = arctangent_bounds(239, terms)
    return 16 * lower_5 - 4 * upper_239, 16 * upper_5 - 4 * lower_239


def pi_interval_of_width(width):
    terms = 8
    while True:
        lower, upper = pi_interval(terms)
        if upper - lower <= width:
            return lower, upper
        terms *= 2


def within_normalized_error(p, q, constant):
    midpoint = Fraction(p, q)
    radius = constant / q**2
    lower, upper = midpoint - radius, midpoint + radius
    terms = 8
    while True:
        pi_lower, pi_upper = pi_interval(terms)
        if pi_upper < lower or pi_lower > upper:
            return False
        if lower <= pi_lower and pi_upper <= upper:
            return True
        # The two endpoints are rational, so neither equals pi.
        terms *= 2


def farey_neighbors(target, order):
    """Return a/b < target <= c/d adjacent at denominator bound order."""
    x, y = target.numerator, target.denominator
    a = (x - 1) // y
    b, c, d = 1, a + 1, 1
    while b + d <= order:
        left_gap = x * b - y * a
        right_gap = y * c - x * d
        if left_gap > right_gap:
            steps = (order - b) // d
            if right_gap:
                steps = min(steps, (left_gap - 1) // right_gap)
            a, b = a + steps * c, b + steps * d
        else:
            steps = min((order - d) // b, right_gap // left_gap)
            c, d = c + steps * a, d + steps * b
    return a, b, c, d


def farey_walk(lower, upper, order):
    """Visit all reduced fractions in the closed interval, in value order."""
    a, b, c, d = farey_neighbors(lower, order)
    while c * upper.denominator <= upper.numerator * d:
        yield c, d
        steps = (order + b) // d
        a, b, c, d = c, d, steps * c - a, steps * d - b


def pi_candidates(max_denominator, constant):
    """Visit all reduced p/q with q at most the cap and q²|pi-p/q| <= constant."""
    if max_denominator < 1 or constant <= 0:
        raise ValueError("positive denominator cap and constant required")
    constant = Fraction(constant)
    block_start = 1
    while block_start <= max_denominator:
        block_end = min(max_denominator, 2 * block_start - 1)
        width = Fraction(1, block_start**2)
        lower, upper = pi_interval_of_width(width)
        radius = constant * width
        for p, q in farey_walk(lower - radius, upper + radius, block_end):
            if q >= block_start and within_normalized_error(p, q, constant):
                yield p, q
        block_start *= 2


def reference_candidates(max_denominator, constant):
    """Independent reference that scans each denominator."""
    lower, upper = pi_interval_of_width(Fraction(1, max_denominator**2))
    for q in range(1, max_denominator + 1):
        left = q * lower - constant / q
        right = q * upper + constant / q
        first = -((-left.numerator) // left.denominator)
        last = right.numerator // right.denominator
        for p in range(first, last + 1):
            if gcd(p, q) == 1 and within_normalized_error(p, q, constant):
                yield p, q


def main():
    assert [rational_at(index) for index in range(7)] == [
        (0, 1), (1, 1), (-1, 1), (1, 2), (-1, 2), (2, 1), (-2, 1)
    ]
    assert list(farey_walk(Fraction(-1, 2), Fraction(1, 2), 3)) == [
        (-1, 2), (-1, 3), (0, 1), (1, 3), (1, 2)
    ]
    for constant in (Fraction(1, 2), Fraction(1), Fraction(3)):
        walk = list(pi_candidates(16384, constant))
        reference = set(reference_candidates(16384, constant))
        assert len(walk) == len(set(walk)) and set(walk) == reference
        print(f"q <= 16384, C = {constant}: {len(walk)} matching fractions")
    for exponent in (6, 12, 80):
        candidates = list(pi_candidates(10**exponent, Fraction(1, 2)))
        assert (355, 113) in candidates
        print(f"q <= 10^{exponent}, C = 1/2: {len(candidates)} fractions")


if __name__ == "__main__":
    main()
