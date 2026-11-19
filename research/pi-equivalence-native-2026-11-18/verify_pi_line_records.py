#!/usr/bin/env python3
"""Certify normalized pi record approximations, using only the Python standard library."""
import argparse
import sys
from hashlib import sha256
from math import isqrt


def chudnovsky_split(start, end):
    """Return products and weighted sum for Chudnovsky terms start..end-1."""
    if end - start == 1:
        k = start
        numerator = (6*k-5) * (2*k-1) * (6*k-1)
        denominator = k**3 * (640320**3 // 24)
        signed = (-1 if k % 2 else 1) * numerator * (13591409 + 545140134*k)
        return numerator, denominator, signed
    middle = (start + end) // 2
    p_left, q_left, t_left = chudnovsky_split(start, middle)
    p_right, q_right, t_right = chudnovsky_split(middle, end)
    return p_left*p_right, q_left*q_right, t_left*q_right+p_left*t_right


def pi_grid(digits):
    """Return integer endpoints containing pi times 10**digits."""
    scale = 10**digits
    last = digits // 14 + 12
    prod, den, tail = chudnovsky_split(1, last+1)
    partial = 13591409*den + tail
    _, next_q, next_t = chudnovsky_split(last+1, last+2)
    next_num = partial*next_q + prod*next_t
    common_den = den*next_q
    lower_sum = min(partial*next_q, next_num)
    upper_sum = max(partial*next_q, next_num)
    assert 0 < lower_sum
    root = isqrt(10005*scale*scale)
    lower = (426880*root*common_den) // upper_sum
    upper = (426880*(root+1)*common_den+lower_sum-1) // lower_sum
    return lower, upper, scale



def atan_split(inverse, start, end):
    """Split the arctan series after dividing the terms by its first term."""
    if end - start == 1:
        numerator = -(2*start-1)
        denominator = (2*start+1)*inverse**2
        return numerator, denominator, numerator
    middle = (start + end) // 2
    p_left, q_left, t_left = atan_split(inverse, start, middle)
    p_right, q_right, t_right = atan_split(inverse, middle, end)
    return p_left*p_right, q_left*q_right, t_left*q_right+p_left*t_right


def atan_grid(inverse, digits, scale):
    # inverse**(2*last) exceeds scale and makes the next term sufficiently small.
    digits_per_term = len(str(inverse**2))-1
    last = digits // digits_per_term + 2
    prod, den, tail = atan_split(inverse, 1, last+1)
    partial = den + tail
    _, next_q, next_t = atan_split(inverse, last+1, last+2)
    next_num = partial*next_q + prod*next_t
    common_den = den*next_q*inverse
    lower = scale*min(partial*next_q, next_num) // common_den
    upper = (scale*max(partial*next_q, next_num)+common_den-1) // common_den
    return lower, upper


def machin_grid(digits):
    scale = 10**digits
    a_low, a_high = atan_grid(5, digits, scale)
    b_low, b_high = atan_grid(239, digits, scale)
    return 16*a_low-4*b_high, 16*a_high-4*b_low, scale

def certified_convergents(lower, upper, scale):
    """Descend the continued fraction only where both endpoint floors agree."""
    left_num, left_den = lower, scale
    right_num, right_den = upper, scale
    before_p, p = 0, 1
    before_q, q = 1, 0
    while True:
        digit, left_rem = divmod(left_num, left_den)
        right_digit, right_rem = divmod(right_num, right_den)
        if digit != right_digit:
            return
        before_p, p = p, digit*p + before_p
        before_q, q = q, digit*q + before_q
        yield digit, p, q
        if left_rem == 0:
            return
        left_num, right_num = right_den, left_den
        left_den, right_den = right_rem, left_rem


def normalized_error(p, q, lower, upper, scale):
    left, right = p*scale - q*upper, p*scale - q*lower
    minimum = min(abs(left), abs(right)) if left*right > 0 else 0
    return q*minimum, q*max(abs(left), abs(right))


def show_decimal_bound(lower, upper, scale, places=20):
    base = 10**places
    low = lower*base // scale
    high = (upper*base+scale-1) // scale
    return f"[{low//base}.{low%base:0{places}d}, {high//base}.{high%base:0{places}d}]"


def first_staircase_break(p, q, error_low, error_high, scale, slope_sign):
    """Return the first mismatch for nearest-integer staircases with directed ties.

    slope_sign is the sign of pi - p/q. The error endpoints enclose
    q**2 * abs(pi - p/q), each multiplied by scale.
    """
    assert 0 < error_low <= error_high and 2*error_high < scale
    assert slope_sign in (-1, 1)
    gap_numerator = 1 if q % 2 else 2
    # The directed seam is 1/(2q) away for odd q and 1/q away for even q.
    fraction_numerator = (q - slope_sign*gap_numerator) // 2
    residue = (fraction_numerator*pow(p, -1, q)) % q

    def cycles(error):
        return (q*gap_numerator*scale - 2*residue*error) // (2*q*error)

    if cycles(error_low) != cycles(error_high):
        raise ArithmeticError("The staircase break needs a tighter bound")
    return residue + (cycles(error_high)+1)*q


def trace_records(digits, method="chudnovsky"):
    enclose_pi = pi_grid if method == "chudnovsky" else machin_grid
    lower, upper, scale = enclose_pi(digits)
    if not 0 < upper-lower <= 40:
        raise AssertionError("Expected a narrow outward interval")
    convergents = certified_convergents(lower, upper, scale)
    prior = next(convergents)
    index = -1
    best_low = best_high = scale
    for index, following in enumerate(convergents):
        _, p, q = prior
        following_digit = following[0]
        # Error > 1/(next digit + 2). Use it before multiplying large integers.
        if best_high*(following_digit+2) >= scale:
            error_low, error_high = normalized_error(p, q, lower, upper, scale)
            if error_high < best_low:
                best_low, best_high = error_low, error_high
                slope_sign = 1 if q*lower > p*scale else -1
                first_break = first_staircase_break(p, q, error_low, error_high, scale, slope_sign)
                yield ("record", index, p, q, following_digit, error_low, error_high, scale, first_break)
            elif error_low <= best_high:
                raise ArithmeticError(f"Record comparison needs more precision at index {index}")
        prior = following
    # The final certified convergent lies after all the processed denominators.
    yield ("coverage", index+1, prior[1], prior[2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digits", type=int, default=65000)
    parser.add_argument("--method", choices=["chudnovsky", "machin"], default="chudnovsky")
    parser.add_argument("--integers", action="store_true", help="also print all record numerators and denominators")
    args = parser.parse_args()
    if args.digits < 100:
        parser.error("--digits must be at least 100")
    # Allow printing and hashing the locally computed large integer pairs.
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    scale_digits = args.digits
    print(f"Outward {args.method} enclosure, scale 10^{scale_digits}", flush=True)
    for kind, index, p, q, *data in trace_records(scale_digits, args.method):
        q_text = str(q)
        if kind == "coverage":
            print(f"Final certified index {index}, denominator length {len(q_text)}, "
                  f"starts {q_text[:16]}. All smaller denominators checked.", flush=True)
            continue
        digit, lo, hi, scale, first_break = data
        pair_hash = sha256(f"{p}/{q}".encode("ascii")).hexdigest()
        print(f"index={index}, denominator_digits={len(q_text)}, a_next={digit}, "
              f"E={show_decimal_bound(lo, hi, scale)}, q_parity={q%2}, "
              f"full_motifs={(first_break-1)//q}, sha256(p/q)={pair_hash}", flush=True)
        if args.integers:
            print(f"{p}/{q}", flush=True)


if __name__ == "__main__":
    main()
