#!/usr/bin/env python3
"""Check disjoint local replacements and a certified product bound for route cost."""
from fractions import Fraction
from math import gcd, isqrt
import argparse
import json


def make_strip(h, top):
    bottom = top - 1
    active = {j for j in range(1, h, 2) if gcd(j, top) == 1}
    eligible = {j for j in range(1, h - 2, 2)
                if j in active and j + 2 in active and gcd(j + 1, bottom) > 1}
    pairs = set()
    for j in sorted(eligible):
        if j - 2 not in pairs:
            pairs.add(j)
    overlaps = sum(j + 2 in eligible for j in eligible)
    assert len(pairs) >= len(eligible) - overlaps
    strip = []
    j = 1
    while j < h:
        strip.append((j, bottom))
        if j in pairs:
            strip.extend([(j, top), (j + 1, top), (j + 2, top),
                          (j + 2, bottom), (j + 3, bottom)])
            j += 4
        else:
            if j in active:
                strip.extend([(j, top), (j + 1, top)])
            strip.append((j + 1, bottom))
            j += 2
    return strip, len(active), len(eligible), overlaps, len(pairs)


def route_certificate(h):
    if h < 2 or h % 2:
        raise ValueError("height must be positive and even")
    walk = []
    active = edges = overlaps = matches = 0
    for band, top in enumerate(range(2, h + 1, 2)):
        strip, a, e, f, m = make_strip(h, top)
        active += a
        edges += e
        overlaps += f
        matches += m
        if band % 2:
            strip.reverse()
        if walk:
            walk.append((strip[0][0], top - 2))
        walk.extend(strip)
    seen = set(walk)
    assert all(1 <= q <= h and 1 <= p <= h for q, p in seen)
    assert all(abs(q - r) + abs(p - s) == 1
               for (q, p), (r, s) in zip(walk, walk[1:]))
    # Independent shared-divisor sieve. Its complement is exactly the required set.
    composite = set()
    for factor in range(2, h + 1):
        multiples = range(factor, h + 1, factor)
        composite.update((q, p) for q in multiples for p in multiples)
    assert len(seen | composite) == h*h
    baseline = h*h//2 + 2*active + h//2 - 1
    assert len(walk) == baseline - 2*matches
    return {"height": h, "targets": h*h-len(composite), "eligible": edges,
            "overlaps": overlaps, "matching": matches,
            "baseline_slots": baseline, "witness_slots": len(walk)}


def primes_through(limit):
    sieve = bytearray(b'\x01')*(limit + 1)
    sieve[:2] = b'\x00\x00'
    for n in range(2, isqrt(limit) + 1):
        if sieve[n]:
            for multiple in range(n*n, limit + 1, n):
                sieve[multiple] = 0
    return [n for n in range(3, limit + 1, 2) if sieve[n]]


def product_intervals(cutoff=100_000, precision=10**15):
    """Directed rounding for finite products, then the tail bound m/cutoff."""
    primes = primes_through(cutoff)
    result = {}
    for m in (2, 3, 4, 5):
        lo = hi = precision
        for prime in primes:
            denominator = prime*prime
            numerator = denominator - m
            lo = lo*numerator//denominator
            hi = (hi*numerator + denominator - 1)//denominator
        result[m] = (Fraction(lo, precision) - Fraction(m, cutoff),
                     Fraction(hi, precision))
    return result


def arctan_lower_upper(d, n=8):
    partial = sum(Fraction((-1)**i, (2*i + 1)*d**(2*i + 1)) for i in range(n))
    nxt = partial + Fraction((-1)**n, (2*n + 1)*d**(2*n + 1))
    return min(partial, nxt), max(partial, nxt)


def bound_certificate():
    intervals = product_intervals()
    # Machin's identity and alternating-series intervals.
    pi_lower = 16*arctan_lower_upper(5)[0] - 4*arctan_lower_upper(239)[1]
    base_upper = Fraction(1, 2) + 4/pi_lower**2
    saved = (intervals[2][0] - 2*intervals[3][1]
             + 2*intervals[4][0] - intervals[5][1])/2
    upper = base_upper - saved
    assert upper < Fraction(843, 1000)
    return {"cutoff": 100000, "upper_ceiling_numerator": -(-upper*10**8//1),
            "upper_ceiling_denominator": 10**8}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heights", type=int, nargs="*", default=[6, 12, 60, 120])
    args = parser.parse_args()
    for height in args.heights:
        print(json.dumps(route_certificate(height)))
    print(json.dumps(bound_certificate()))
