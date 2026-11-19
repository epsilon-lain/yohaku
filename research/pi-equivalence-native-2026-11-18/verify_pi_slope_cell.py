#!/usr/bin/env python3
"""Check exact slope cells for two pi staircase prefixes.

Uses the integer pi enclosures already implemented in verify_pi_line_records.py.
"""
from fractions import Fraction
from itertools import islice
from math import gcd

from verify_pi_line_records import certified_convergents, machin_grid, pi_grid


def slope_cell(enclosure, columns):
    """Intersect the rounding strips, certifying each height from both ends."""
    low, high, scale = enclosure
    lower = None
    upper = None
    for n in range(1, columns + 1):
        p = (2*n*low + scale) // (2*scale)
        if (2*n*high + scale) // (2*scale) != p:
            raise ArithmeticError(f"Pi enclosure cannot resolve column {n}")
        left = Fraction(2*p - 1, 2*n)
        right = Fraction(2*p + 1, 2*n)
        lower = left if lower is None else max(lower, left)
        upper = right if upper is None else min(upper, right)
    return lower, upper


def nearest_walls(p, q, columns):
    """Find the closest distinct reduced even-denominator slopes on either side."""
    assert q >= 1 and gcd(p, q) == 1 and columns >= 2*q
    result = []
    for direction in (-1, 1):
        if q % 2:
            determinant = direction
            residue = (determinant * pow(p, -1, q)) % q
            if residue % 2:
                residue += q
        else:
            determinant = 2*direction
            residue = ((q + determinant) * pow(p, -1, 2*q)) % (2*q)
        denominator = 2*columns - (2*columns - residue) % (2*q)
        numerator = (p*denominator - determinant) // q
        assert denominator % 2 == 0 and numerator % 2 == 1
        assert p*denominator - q*numerator == determinant
        assert gcd(numerator, denominator) == 1
        result.append(Fraction(numerator, denominator))
    upper, lower = result
    return lower, upper


def scaled_width(cell, columns):
    return columns**2 * (cell[1] - cell[0])


def decimal_interval(value, digits):
    scale = 10**digits
    low, remainder = divmod(value.numerator*scale, value.denominator)
    high = low + bool(remainder)

    def render(n):
        return f"{n // scale}.{n % scale:0{digits}d}"

    return f"[{render(low)}, {render(high)}]"


def certify_large_cell(enclosure):
    target_index = 28_420
    _, p, q = next(islice(certified_convergents(*enclosure), target_index, None))
    low, high, scale = enclosure
    assert q % 2 == 0
    assert q*low > p*scale
    columns = 78_629*q
    _, upper = nearest_walls(p, q, columns)
    assert Fraction(high, scale) < upper
    return scaled_width((Fraction(p, q), upper), columns)


def main():
    before = (Fraction(103993, 33102), Fraction(104037, 33116))
    after = (before[0], Fraction(104703, 33328))
    for enclose in (pi_grid, machin_grid):
        enclosure = enclose(160)
        assert nearest_walls(355, 113, 16663) == before
        assert slope_cell(enclosure, 16663) == before
        assert slope_cell(enclosure, 16664) == after
    for columns, cell in ((16663, before), (16664, after)):
        width = cell[1] - cell[0]
        print(f"N={columns}, cell=[{cell[0]}, {cell[1]}), W_N={width}, "
              f"N^2 W_N={decimal_interval(scaled_width(cell, columns), 12)}")
    widths = [certify_large_cell(enclose(30000)) for enclose in (pi_grid, machin_grid)]
    assert widths[0] == widths[1]
    print("Convergent 28420, N=78629*q, "
          f"N^2 W_N={decimal_interval(widths[0], 15)}")


if __name__ == "__main__":
    main()
