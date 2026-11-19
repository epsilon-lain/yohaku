#!/usr/bin/env python3
"""Build one self-avoiding unit walk with full-square and nearest-pi deadlines.

Run: python3 verify_hamilton_cover.py --max-stage 3
Uses only the Python standard library. Time starts at 0 at (0, 0).
Coordinates of a rational are (denominator q, numerator p).
"""
import argparse
from collections import defaultdict, deque
from fractions import Fraction


# Each pair ij denotes the fine point (i,j) in a 4 by 4 tile.
BRANCH_CYCLE = "00 01 11 12 02 03 13 23 33 32 22 21 31 30 20 10 00"
SPINE_PATH = "30 31 32 33 23 22 12 13 03 02 01 11 21 20 10 00"
CARDINAL = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def arctan_bounds(base, terms):
    partial = sum((Fraction((-1)**i, (2*i+1)*base**(2*i+1))
                   for i in range(terms)), Fraction(0))
    adjacent = partial + Fraction((-1)**terms, (2*terms+1)*base**(2*terms+1))
    return min(partial, adjacent), max(partial, adjacent)


def certified_heights(max_column):
    """Certify floor(pi*x) for the coarse tubes and floor(pi*q+1/2) for targets."""
    terms = 4
    half = Fraction(1, 2)
    while True:
        a, b = arctan_bounds(5, terms)
        c, d = arctan_bounds(239, terms)
        low, high = 16*a - 4*d, 16*b - 4*c
        floors = []
        nearest = []
        for x in range(4*max_column + 1):
            lower = low*x
            upper = high*x
            coarse = lower // 1
            mark = (lower + half) // 1
            if not (upper < coarse+1 and upper+half < mark+1):
                break
            floors.append(coarse)
            nearest.append(mark)
        else:
            return floors, nearest, terms
        terms *= 2


def coarse_stage(k, previous, floors):
    h, length = 2**k, 4**k
    # Chebyshev dilation gives a complete, walkable collar around the old stage.
    region = {(x+dx, y+dy) for x, y in previous
              for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    for x in range(-h, length+1):
        center = floors[x] if x >= 0 else 0
        halfwidth = 8*h if x <= h else 8
        region.update((x, y) for y in range(center-halfwidth, center+halfwidth+1))
    return region


def coarse_forest(annulus, spine):
    """One breadth-first forest rooted at the ordered horizontal spine segment."""
    seen = set(spine)
    assert seen <= annulus
    queue = deque(spine)
    edges = []
    while queue:
        x, y = queue.popleft()
        for dx, dy in CARDINAL:
            child = (x+dx, y+dy)
            if child in annulus and child not in seen:
                seen.add(child)
                edges.append(((x, y), child))
                queue.append(child)
    if seen != annulus:
        raise AssertionError("some tiles cannot reach this stage's spine")
    return edges


def fine(tile, point):
    # Translate three units left so the very first vertex (tile 0, local 30) is 0.
    return (4*tile[0]+point[0]-3, 4*tile[1]+point[1])


def port(tile, dx, dy):
    """Edges on opposite sides are listed in the same transverse order."""
    if dx:
        i = 3 if dx > 0 else 0
        return fine(tile, (i, 0)), fine(tile, (i, 1))
    j = 3 if dy > 0 else 0
    return fine(tile, (0, j)), fine(tile, (1, j))


def add_edge(graph, a, b):
    graph[a].add(b)
    graph[b].add(a)


def drop_edge(graph, a, b):
    graph[a].remove(b)
    graph[b].remove(a)


def expand_stage(annulus, spine):
    spine_set = set(spine)
    forest = coarse_forest(annulus, spine)
    graph = defaultdict(set)
    templates = [[(int(s[0]), int(s[1])) for s in code.split()]
                 for code in (BRANCH_CYCLE, SPINE_PATH)]
    for tile in annulus:
        vertices = [fine(tile, point) for point in templates[tile in spine_set]]
        for a, b in zip(vertices, vertices[1:]):
            add_edge(graph, a, b)

    for parent, child in forest:
        dx, dy = child[0]-parent[0], child[1]-parent[1]
        a, b = port(parent, dx, dy)
        c, d = port(child, -dx, -dy)
        drop_edge(graph, a, b)
        drop_edge(graph, c, d)
        add_edge(graph, a, c)
        add_edge(graph, b, d)

    for right, left in zip(spine, spine[1:]):
        add_edge(graph, fine(right, (0, 0)), fine(left, (3, 0)))

    start, end = fine(spine[0], (3, 0)), fine(spine[-1], (0, 0))
    assert len(graph) == 16*len(annulus)
    assert all(len(adj) == (1 if p == start or p == end else 2)
               for p, adj in graph.items())
    previous = None
    current = start
    count = 0
    while True:
        count += 1
        if count > len(graph):
            raise AssertionError("cycle in expanded spine")
        yield current
        if current == end:
            break
        next_vertex, = graph[current] - {previous}
        previous, current = current, next_vertex
    assert count == len(graph)


def check(max_stage):
    floors, nearest, terms = certified_heights(4**max_stage)
    print(f"Machin alternating partial sums: {terms} and {terms+1} terms")
    print("k  tiles  visited  last_time  endpoint  square_H  square_time  ray_N  ray_time")
    previous_region = set()
    times = {}
    last = None
    for k in range(max_stage+1):
        h, length = 2**k, 4**k
        region = coarse_stage(k, previous_region, floors)
        first_x = 0 if k == 0 else -h//2-1
        spine = [(x, 0) for x in range(first_x, -h-1, -1)]
        for v in expand_stage(region-previous_region, spine):
            assert v not in times
            if last is None:
                assert v == (0, 0)
            else:
                assert abs(v[0]-last[0])+abs(v[1]-last[1]) == 1
            times[v] = len(times)
            last = v
        assert len(times) == 16*len(region)
        assert last == (-4*h-3, 0)
        bound = 4*h
        square_time = max(times[x, y] for x in range(-bound, bound+1)
                          for y in range(-bound, bound+1))
        ray_n = 4*length
        ray_time = max(times[q, nearest[q]] for q in range(1, ray_n+1))
        print(k, len(region), len(times), len(times)-1, last, bound, square_time,
              ray_n, ray_time)
        previous_region = region


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-stage", default=3, type=int)
    args = parser.parse_args()
    if args.max_stage < 0:
        parser.error("--max-stage must be nonnegative")
    check(args.max_stage)
