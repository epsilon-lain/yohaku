#!/usr/bin/env python3
"""Check three rational lattice walks using only Python's standard library.

Run: python3 verify_unit_step_walks.py
Use --stages k for heights 1, 2, ..., 2**(k-1).
Coordinates are always (denominator q, numerator p).
"""
import argparse
from fractions import Fraction
from math import gcd


def arctan_bounds(d, terms):
    """The exact alternating arctan(1/d) series lies between adjacent sums."""
    value = sum((Fraction((-1)**j, (2*j + 1) * d**(2*j + 1))
                 for j in range(terms)), Fraction(0))
    next_value = value + Fraction((-1)**terms,
                                  (2*terms + 1) * d**(2*terms + 1))
    return min(value, next_value), max(value, next_value)


def certify_targets(max_q):
    """Use Machin's pi = 16 atan(1/5) - 4 atan(1/239)."""
    terms = 4
    half = Fraction(1, 2)
    while True:
        l5, u5 = arctan_bounds(5, terms)
        l239, u239 = arctan_bounds(239, terms)
        lo, hi = 16*l5 - 4*u239, 16*u5 - 4*l239
        targets = []
        for q in range(max_q + 1):
            candidate = int(lo*q + half)  # nonnegative, so int = floor
            if not candidate - half < lo*q <= hi*q < candidate + half:
                break
            targets.append(candidate)
        if len(targets) == max_q + 1:
            return targets, terms, hi - lo
        terms *= 2


def box(h):
    return {(q, p) for q in range(1, h + 1) for p in range(-h, h + 1)}


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def square_spiral():
    q = p = 0
    yield q, p
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    leg = 0
    while True:
        dq, dp = directions[leg % 4]
        for _ in range(leg // 2 + 1):
            q += dq
            p += dp
            yield q, p
        leg += 1


def check_spiral(h):
    walk = square_spiral()
    seen = {next(walk)}
    order = []
    previous = (0, 0)
    for _ in range((2*h + 1)**2 - 1):
        site = next(walk)
        assert distance(previous, site) == 1 and site not in seen
        seen.add(site)
        if site[0] > 0 and gcd(*site) == 1:
            order.append(site)
        previous = site
    assert previous == (h, -h)
    assert seen == {(q, p) for q in range(-h, h + 1)
                    for p in range(-h, h + 1)}
    assert len(order) == len(set(order))
    assert set(order) == {site for site in box(h) if gcd(*site) == 1}
    return len(order)


def segment(start, end):
    """All steps after start ending at end, horizontally then vertically."""
    q, p = start
    while q != end[0]:
        q += 1 if q < end[0] else -1
        yield q, p
    while p != end[1]:
        p += 1 if p < end[1] else -1
        yield q, p


def rows(h):
    for row, p in enumerate(range(-h, h + 1)):
        columns = range(1, h + 1) if row % 2 == 0 else range(h, 0, -1)
        for q in columns:
            yield q, p


def check_combined(stages, targets):
    """Walk and verify both phases literally, on a single step counter."""
    origin = (0, 0)
    current = origin
    clock = 0
    visited = {origin}
    emitted = set()

    def step(site):
        nonlocal clock, current
        assert distance(current, site) == 1
        current = site
        clock += 1
        visited.add(site)

    def emit(site):
        assert gcd(*site) == 1 and site not in emitted
        emitted.add(site)

    def emit_scan(site, old_h):
        q, p = site
        if max(q, abs(p)) > old_h and gcd(q, p) == 1 and p != targets[q]:
            emit(site)

    old_h = 0
    for k in range(stages):
        h = 2**k
        start = clock
        scan = rows(h)
        previous = next(scan)
        for site in segment(current, previous):
            step(site)
        covered = {previous}
        emit_scan(previous, old_h)
        for site in scan:
            step(site)
            assert site not in covered
            covered.add(site)
            emit_scan(site, old_h)
        assert current == (h, h) and covered == box(h)
        for site in segment(current, origin):
            step(site)
        assert clock - start == 2*h*h + 4*h

        ray_start = clock
        ray = [origin]
        for j in range(1, h*h + 1):
            endpoint = (j, targets[j])
            assert targets[j] - targets[j-1] in (3, 4)
            for site in segment(current, endpoint):
                step(site)
                ray.append(site)
            if j > old_h**2 and gcd(*endpoint) == 1:
                emit(endpoint)
        assert clock - ray_start == h*h + targets[h*h]
        for i in range(len(ray) - 2, -1, -1):
            step(ray[i])

        expected = covered | {(j, targets[j]) for j in range(1, h*h + 1)}
        assert current == origin and expected <= visited
        assert emitted == {site for site in expected if gcd(*site) == 1}
        stage_steps = clock - start
        assert stage_steps == 4*h*h + 4*h + 2*targets[h*h]
        print(f'{h:6} {h*h:9} {stage_steps:12} {clock:12} {len(emitted):12}')
        old_h = h


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stages', type=int, default=7)
    args = parser.parse_args()
    if args.stages < 1:
        parser.error('--stages must be positive')
    h = 2**(args.stages - 1)
    targets, terms, width = certify_targets(h*h)
    print(f'Machin alternating terms per arctan: {terms}')
    print(f'Certified pi interval width: {width}')
    print(f'Spiral: {(2*h+1)**2} sites, {check_spiral(h)} reduced outputs')
    print('     h    ray max  stage moves  total moves        emits')
    check_combined(args.stages, targets)


if __name__ == '__main__':
    main()
