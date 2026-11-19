"""One-sided lattice Peano clock; verify the local and global covering claims."""
from argparse import ArgumentParser
from math import gcd

# Each tile is specified by grid offset and entrance/exit corners.
DIAGONAL = (
    (0, 0, 'SW', 'NE'), (1, 0, 'NW', 'SE'), (2, 0, 'SW', 'NE'),
    (2, 1, 'SE', 'NW'), (1, 1, 'NE', 'SW'), (0, 1, 'SE', 'NW'),
    (0, 2, 'SW', 'NE'), (1, 2, 'NW', 'SE'), (2, 2, 'SW', 'NE'),
)
ADJACENT = (
    (0, 0, 'SW', 'NE'), (0, 1, 'SE', 'NW'), (0, 2, 'SW', 'NE'),
    (1, 2, 'NW', 'NE'), (2, 2, 'NW', 'SE'), (2, 1, 'NE', 'SW'),
    (1, 1, 'SE', 'SW'), (1, 0, 'NW', 'NE'), (2, 0, 'NW', 'SE'),
)
RING = (
    (1, 0, 'NW', 'SE'), (1, -1, 'NE', 'SW'), (0, -1, 'SE', 'SW'),
    (-1, -1, 'SE', 'NW'), (-1, 0, 'SW', 'NW'), (-1, 1, 'SW', 'NE'),
    (0, 1, 'NW', 'SE'), (1, 1, 'SW', 'NE'),
)
CORNERS = {'SW': (0, 0), 'SE': (1, 0), 'NE': (1, 1), 'NW': (0, 1)}


def assemble(order, tiles, side, offset=0):
    for tx, ty, start, end in order:
        sx, sy = CORNERS[start]
        ex, ey = CORNERS[end]
        diagonal = sx != ex and sy != ey
        swap = not diagonal and sx == ex
        for x, y in tiles[diagonal]:
            if swap:
                x, y = y, x
            if sx:
                x = side-1-x
            if sy:
                y = side-1-y
            yield (offset + tx*side + x, offset + ty*side + y)


def clock(level):
    """Natural-time ordering through the entire centered square of side 3**level."""
    tiles = {False: [(0,0)], True: [(0,0)]}
    whole = [(0,0)]
    side = 1
    for _ in range(level):
        whole.extend(assemble(RING, tiles, side, -(side//2)))
        tiles = {False: list(assemble(ADJACENT, tiles, side)),
                 True: list(assemble(DIAGONAL, tiles, side))}
        side *= 3
    return whole


def verify(level):
    walk = clock(level)
    assert all(abs(x-u)+abs(y-v) == 1 for (x,y),(u,v) in zip(walk, walk[1:]))
    assert len(set(walk)) == len(walk) == 9**level
    for k in range(level+1):
        side = 3**k
        slots = side*side
        r = side//2
        assert walk[slots-1] == (r,r)
        assert set(walk[:slots]) == {(x,y) for x in range(-r,r+1) for y in range(-r,r+1)}
        for start in range(0, len(walk), slots):
            block = walk[start:start+slots]
            xs, ys = zip(*block)
            assert max(xs)-min(xs)+1 == max(ys)-min(ys)+1 == side
            assert len(set(block)) == slots
    return sum(q > 0 and gcd(q,p)==1 for q,p in walk)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('level', type=int, nargs='?', default=5)
    args = parser.parse_args()
    if args.level < 0:
        parser.error('level must be nonnegative')
    emitted = verify(args.level)
    print(f'level={args.level}, side={3**args.level}, '
          f'sites={9**args.level}, rational outputs={emitted}')
