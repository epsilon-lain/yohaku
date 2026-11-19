#!/usr/bin/env python3
"""Verify finite bounds on a shortest grid walk through every primitive site.

The square is 1 <= q,p <= H, with H even. Distances use unit horizontal or
vertical steps. Lengths reported as slots count both endpoints. The program
verifies one constructive upper bound and lower bounds from checkerboard
parity and isolated sites. It does not compute a shortest route.
"""

import argparse
import json
from math import gcd


def build_route(height):
    """Return every visited point in chronological order, including repeats."""
    walk = []
    for strip_number, lower in enumerate(range(1, height, 2)):
        upper = lower + 1
        strip = []
        for left in range(1, height, 2):
            right = left + 1
            strip.append((left, lower))
            if gcd(left, upper) == 1:
                strip.extend([(left, upper), (right, upper)])
            strip.append((right, lower))

        if strip_number % 2:
            strip.reverse()
        if walk:
            walk.append((strip[0][0], lower - 1))
        walk.extend(strip)
    return walk


def primitive_sites(height):
    """Independently sieve every site sharing a divisor >= 2."""
    sites = {(q, p) for q in range(1, height + 1) for p in range(1, height + 1)}
    for divisor in range(2, height + 1):
        multiples = range(divisor, height + 1, divisor)
        for q in multiples:
            for p in multiples:
                sites.discard((q, p))
    return sites


def verify(height, include_route=False):
    if height < 2 or height % 2:
        raise ValueError("height must be a positive even integer")
    walk = build_route(height)
    primitive = primitive_sites(height)

    for index, (q, p) in enumerate(walk):
        if not (1 <= q <= height and 1 <= p <= height):
            raise AssertionError(f"slot {index + 1} leaves the square")
        if index:
            prev_q, prev_p = walk[index - 1]
            if abs(q - prev_q) + abs(p - prev_p) != 1:
                raise AssertionError(f"slots {index} and {index + 1} are not adjacent")
    visited_primitive = {point for point in walk if gcd(*point) == 1}
    if visited_primitive != primitive:
        raise AssertionError("primitive sites visited differ from the independent sieve")

    mixed = sum(q % 2 == 1 and p % 2 == 0 for q, p in primitive)
    odd_color = sum((q + p) % 2 for q, p in primitive)
    if odd_color != 2 * mixed:
        raise AssertionError("swapping coordinates must pair the two mixed parities")
    lower_bound = 2 * odd_color - 1
    unit_steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    isolated = {
        (q, p) for q, p in primitive
        if q % 2 == 1 and p % 2 == 1
        and all(gcd(q + dq, p + dp) > 1 for dq, dp in unit_steps)
    }
    if height == 60 and not {(21, 55), (55, 21)} <= isolated:
        raise AssertionError("both explicit isolated sites must occur at height 60")
    refined_lower_bound = max(lower_bound, 2 * (odd_color + len(isolated)) - 3)
    # Check the proof's injection on the constructed route. Distinct first
    # visits have distinct predecessor slots, even if a coordinate repeats.
    first_predecessors = {}
    for index, site in enumerate(walk):
        if site in isolated and site not in first_predecessors:
            first_predecessors[site] = index - 1 if index else None
    if first_predecessors.keys() != isolated:
        raise AssertionError("the route must cover every marked center")
    predecessor_slots = [i for i in first_predecessors.values() if i is not None]
    if len(set(predecessor_slots)) != len(predecessor_slots):
        raise AssertionError("distinct first visits must have distinct predecessor slots")
    for index in predecessor_slots:
        q, p = walk[index]
        if (q + p) % 2 != 1 or (q, p) in primitive:
            raise AssertionError("a marked predecessor must be odd-colored and nonprimitive")
    omitted_pairs = (height // 2) ** 2 - mixed
    bridge_slots = height // 2 - 1
    predicted_slots = height * height - 2 * omitted_pairs + bridge_slots
    if not refined_lower_bound <= len(walk) == predicted_slots:
        raise AssertionError("bounds disagree with the explicit route")

    result = {
        "height": height,
        "primitive_sites": len(primitive),
        "primitive_q_odd_p_even": mixed,
        "removed_upper_pairs": omitted_pairs,
        "bridge_slots": bridge_slots,
        "minimum_slots_lower_bound": lower_bound,
        "isolated_odd_odd_centers": len(isolated),
        "minimum_slots_lower_bound_with_isolation": refined_lower_bound,
        "constructed_route_slots": len(walk),
        "constructed_route_edges": len(walk) - 1,
    }
    if include_route:
        result["route_q_p"] = walk
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heights", type=int, nargs="*", default=[2, 6, 12, 60])
    parser.add_argument("--route", action="store_true", help="include the full walk as [q,p] pairs")
    args = parser.parse_args()
    if any(height < 2 or height % 2 for height in args.heights):
        parser.error("heights must be positive even integers")
    for height in args.heights:
        print(json.dumps(verify(height, args.route)))


if __name__ == "__main__":
    main()
