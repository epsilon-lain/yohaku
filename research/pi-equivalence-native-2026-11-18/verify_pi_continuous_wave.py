#!/usr/bin/env python3
"""Enclose the direct sine statistic Z(n) using only integer/rational arithmetic."""

import argparse
from fractions import Fraction
from math import fsum, sin


SCALE = 10**32


def floor_fraction(x):
    return x.numerator // x.denominator


def ceil_fraction(x):
    return -floor_fraction(-x)


def atan_inverse_bounds(k, pairs):
    upper = sum(
        (Fraction((-1)**j, (2*j + 1) * k**(2*j + 1)) for j in range(2*pairs + 1)),
        Fraction(0),
    )
    lower = upper - Fraction(1, (4*pairs + 3) * k**(4*pairs + 3))
    return lower, upper


def pi_bounds():
    lo5, hi5 = atan_inverse_bounds(5, 16)
    lo239, hi239 = atan_inverse_bounds(239, 5)
    lo = floor_fraction(SCALE * (16*lo5 - 4*hi239))
    hi = ceil_fraction(SCALE * (16*hi5 - 4*lo239))
    return Fraction(lo, SCALE), Fraction(hi, SCALE)


def sine_series_bounds(x):
    # x denotes a nonnegative argument scaled by SCALE. Round each operation
    # outwards; partial sums ending at j=14 and j=15 enclose the true sine.
    term_lo = term_hi = total_lo = total_hi = x
    square = x*x
    for j in range(1, 16):
        divisor = SCALE**2 * (2*j) * (2*j + 1)
        term_lo = term_lo * square // divisor
        term_hi = -(-term_hi * square // divisor)
        if j % 2:
            total_lo -= term_hi
            total_hi -= term_lo
        else:
            total_lo += term_lo
            total_hi += term_hi
        if j == 14:
            upper = total_hi
    return total_lo, upper


def abs_sine_bounds(k, pi_lo, pi_hi):
    scaled_k = SCALE*k
    m = (2*scaled_k + pi_hi) // (2*pi_hi)
    assert m == (2*scaled_k + pi_lo) // (2*pi_lo)
    lo, hi = scaled_k - m*pi_hi, scaled_k - m*pi_lo
    if hi < 0:
        lo, hi = -hi, -lo
    assert 0 <= lo <= hi and 2*hi < pi_lo
    lower, _ = sine_series_bounds(lo)
    _, upper = sine_series_bounds(hi)
    assert 0 < lower <= upper <= SCALE
    return lower, upper


def decimal_bound(value, digits, upper):
    size = 10**digits
    integer = (ceil_fraction if upper else floor_fraction)(value * size)
    whole, tail = divmod(integer, size)
    return f"{whole}.{tail:0{digits}d}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--long", action="store_true", help="also certify the full 355-wave energy window")
    args = parser.parse_args()
    test_n = (22, 355)
    pi_lo, pi_hi = pi_bounds()
    anchor = 355
    nearest = 113
    assert 0 < anchor/pi_hi-nearest <= anchor/pi_lo-nearest < Fraction(1, 2)
    eps_lo, eps_hi = anchor*(anchor/pi_hi-nearest), anchor*(anchor/pi_lo-nearest)
    blocks = floor_fraction(1/(2*eps_hi))
    assert blocks == floor_fraction(1/(2*eps_lo))
    last = anchor * blocks if args.long else 512
    scaled_pi_lo = floor_fraction(SCALE*pi_lo)
    scaled_pi_hi = ceil_fraction(SCALE*pi_hi)
    sum_lower = sum_upper = 0
    for k in range(1, last + 1):
        lower, upper = abs_sine_bounds(k, scaled_pi_lo, scaled_pi_hi)
        if k == anchor:
            anchor_sine_lower, anchor_sine_upper = lower, upper
        if k in test_n:
            z_lo = Fraction(lower**2 * sum_lower, SCALE**3)
            z_hi = Fraction(upper**2 * sum_upper, SCALE**3)
            float_check = sin(k)**2 * fsum(1/sin(j)**2 for j in range(1, k))
            assert abs(float(z_lo) - float_check) < 1e-13
            text_lo = decimal_bound(z_lo, 16, False)
            text_hi = decimal_bound(z_hi, 16, True)
            print(f"Z({k}) in [{text_lo}, {text_hi}]")
        # Scaled sums enclose SCALE * sum_{j<=k} csc(j)^2.
        sum_lower += SCALE**3 // upper**2
        sum_upper += -(-SCALE**3 // lower**2)
        if k == 256:
            s256_lo, s256_hi = sum_lower, sum_upper
        if k == 512:
            ratio_lo = Fraction(sum_lower, s256_hi)
            ratio_hi = Fraction(sum_upper, s256_lo)
            float_ratio = fsum(1/sin(j)**2 for j in range(1, 513)) / fsum(
                1/sin(j)**2 for j in range(1, 257)
            )
            assert abs(float(ratio_lo)/float_ratio - 1) < 1e-13
            lo_text = decimal_bound(ratio_lo, 12, False)
            hi_text = decimal_bound(ratio_hi, 12, True)
            print(f"S(512)/S(256) in [{lo_text}, {hi_text}]")

    if not args.long:
        return
    fraction_lo = Fraction(SCALE**3, anchor_sine_upper**2 * sum_upper)
    fraction_hi = Fraction(SCALE**3, anchor_sine_lower**2 * sum_lower)
    text_lo = decimal_bound(fraction_lo, 12, False)
    text_hi = decimal_bound(fraction_hi, 12, True)
    float_fraction = 1/fsum((sin(anchor)/sin(k))**2 for k in range(1, last + 1))
    assert abs(float(fraction_lo) - float_fraction) < 1e-13
    print(f"n = {anchor}, B = {blocks}, Bn = {last}, energy share in [{text_lo}, {text_hi}]")


if __name__ == "__main__":
    main()
