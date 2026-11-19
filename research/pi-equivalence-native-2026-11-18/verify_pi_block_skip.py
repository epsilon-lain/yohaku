#!/usr/bin/env python3
"""Find the first hit of a small error threshold without scanning columns."""
import argparse
from hashlib import sha256
from fractions import Fraction
from math import gcd, lcm
from verify_pi_line_records import machin_grid, normalized_error, pi_grid


def floor_sum(count, mod, step, start):
    """Return sum(floor((step*i + start)/mod), i=0..count-1)."""
    total = 0
    while True:
        integral_step, step = divmod(step, mod)
        integral_start, start = divmod(start, mod)
        total += integral_step*count*(count-1)//2 + integral_start*count
        rows, remainder = divmod(step*count+start, mod)
        if rows == 0:
            return total
        count, mod, step, start = rows, step, mod, remainder


def strip_count(first, last, lower, upper, half_width):
    """Exactly count integer points in the indicated closed affine strip."""
    count = last-first+1
    total = count
    for slope in (upper, -lower):
        start = slope*first + half_width
        mod = lcm(slope.denominator, start.denominator)
        step = slope.numerator*(mod//slope.denominator)
        offset = start.numerator*(mod//start.denominator)
        total += floor_sum(count, mod, step, offset)
    return total


def nearest(q, lower, upper, scale):
    lo = (2*q*lower+scale)//(2*scale)
    hi = (2*q*upper+scale)//(2*scale)
    if lo != hi:
        raise ArithmeticError("Tighter bounds needed to round a grid height.")
    return lo


def error_interval(p, q, lower, upper, scale):
    lo, hi = normalized_error(p, q, lower, upper, scale)
    return Fraction(lo, scale), Fraction(hi, scale)


def seed_threshold(p, q, lower, upper, scale):
    """Certify the small, fixed 355/113 seed by direct checks through q."""
    assert gcd(p, q) == 1 and nearest(q, lower, upper, scale) == p
    result = error_interval(p, q, lower, upper, scale)
    for den in range(1, q):
        num = nearest(den, lower, upper, scale)
        lo, _ = error_interval(num, den, lower, upper, scale)
        assert lo > result[1]
    return result


def first_hit(first, limit, threshold, lower, upper, scale):
    """Assuming all earlier columns miss, find the first strict threshold hit."""
    lower_slope, upper_slope = Fraction(lower, scale), Fraction(upper, scale)
    b_lo, b_hi = threshold
    assert 0 < b_lo <= b_hi < Fraction(1, 10)
    assert 8*b_hi <= 9*b_lo
    blocks = nonempty = floor_queries = 0
    while first <= limit:
        last = min(2*first-1, limit)
        if 16*first**2*(upper_slope-lower_slope) > b_lo:
            raise ArithmeticError("Tighter bounds needed for this band.")
        width = b_hi/first
        total = strip_count(first, last, lower_slope, upper_slope, width)
        blocks += 1
        floor_queries += 1
        assert total in (0, 1), (first, last, total)
        if total == 1:
            nonempty += 1
            left, right = first, last
            while left < right:
                middle = (left+right)//2
                total = strip_count(first, middle, lower_slope, upper_slope, width)
                floor_queries += 1
                if total:
                    right = middle
                else:
                    left = middle+1
            q = left
            p = (upper_slope*q+width)//1
            assert p >= lower_slope*q-width
            e_lo, e_hi = error_interval(p, q, lower, upper, scale)
            if e_hi < b_lo:
                return (p, q), (blocks, nonempty, floor_queries)
            if e_lo <= b_hi:
                raise ArithmeticError("Tighter bounds needed for the strict inequality.")
        first = last+1
    return None, (blocks, nonempty, floor_queries)


def check_small_examples(lower, upper, scale):
    for count in range(9):
        for modulus in range(1, 9):
            for step in range(-8, 9):
                for start in range(-4, 5):
                    wanted = sum((step*i+start)//modulus for i in range(count))
                    assert floor_sum(count, modulus, step, start) == wanted

    left, right = Fraction(lower, scale), Fraction(upper, scale)
    for q0 in (1, 2, 7, 9, 17, 49, 61, 90, 114):
        q1 = 2*q0-1
        width = Fraction(1, 100*q0)
        count = 0
        for q in range(q0, q1+1):
            smallest = -((-(left*q-width))//1)
            largest = (right*q+width)//1
            count += max(0, largest-smallest+1)
        assert strip_count(q0, q1, left, right, width) == count

    # A positive control produces a small known witness; a negative one excludes
    # every column directly, before using the version that counts whole blocks.
    for b in (Fraction(1, 20), Fraction(1, 1000)):
        wanted = None
        for q in range(1, 1025):
            p = nearest(q, lower, upper, scale)
            lo, hi = error_interval(p, q, lower, upper, scale)
            if hi < b:
                wanted = p, q
                break
            assert lo > b
        found, _ = first_hit(1, 1024, (b, b), lower, upper, scale)
        assert found == wanted


def report(label, first, limit, threshold, lower, upper, scale, show_integers=False):
    hit, (blocks, nonempty, floor_queries) = first_hit(first, limit, threshold,
                                                     lower, upper, scale)
    print(label)
    print(f"Denominator blocks checked: {blocks}, nonempty strips: {nonempty}, "
          f"strip count calls: {floor_queries}")
    if hit:
        p, q = hit
        pair = f"{p}/{q}"
        digest = sha256(pair.encode("ascii")).hexdigest()
        print(f"First strict hit: {len(str(q))}-digit denominator, sha256(p/q)={digest}")
        elo, ehi = error_interval(p, q, lower, upper, scale)
        units = 10**20
        left = elo*units//1
        right = -((-ehi*units)//1)
        print(f"Normalized error lies in [{left}, {right}]/10^20")
        if show_integers:
            print(pair)
        return digest
    print(f"No strict hit in [{first}, {limit}].")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-q", type=int)
    parser.add_argument("--digits", type=int, default=480)
    parser.add_argument("--method", choices=("machin", "chudnovsky"), default="machin")
    parser.add_argument("--threshold", type=Fraction,
                        help="use a given rational threshold from q=1 instead of the default seed")
    parser.add_argument("--integers", action="store_true")
    args = parser.parse_args()
    if args.max_q is not None and args.max_q < 1:
        parser.error("The denominator limit must be positive.")
    if args.digits < 100:
        parser.error("Use at least 100 digits.")
    enclose_pi = machin_grid if args.method == "machin" else pi_grid
    lower, upper, scale = enclose_pi(args.digits)
    check_small_examples(lower, upper, scale)
    print("Small floor sums, strip counts, and first-hit controls passed.")
    if args.threshold is not None:
        if not 0 < args.threshold < Fraction(1, 10):
            parser.error("The threshold must be strictly between 0 and 1/10.")
        report(f"Fixed threshold {args.threshold}", 1, args.max_q or 10**216,
               (args.threshold, args.threshold), lower, upper, scale, args.integers)
    elif args.max_q is not None:
        threshold = seed_threshold(355, 113, lower, upper, scale)
        report("After 355/113", 114, args.max_q, threshold, lower, upper, scale, args.integers)
    else:
        threshold = seed_threshold(355, 113, lower, upper, scale)
        first = report("After 355/113", 114, 10**155, threshold, lower, upper, scale,
                       args.integers)
        second = report("Fixed threshold 1/1000", 1, 10**216,
                        (Fraction(1, 1000), Fraction(1, 1000)), lower, upper, scale,
                        args.integers)
        assert first == "b21b0ce17853f6b87ddbf617e7b550ae88ee57fb83e68703e3945a02b3846bbd"
        assert second == "09c453d84f8cad4f74c1b8d106a06e0b2feb9e61280a63c82bca58d0077d6ae1"


if __name__ == "__main__":
    main()
