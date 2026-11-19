"""Exact random access to the centered lattice clock in verify_peano_clock.py."""
from verify_peano_clock import ADJACENT, DIAGONAL, RING, CORNERS, clock


def to_canonical(x, y, side, start, end):
    sx, sy = CORNERS[start]
    ex, ey = CORNERS[end]
    opposite = sx != ex and sy != ey
    if sx:
        x = side-1-x
    if sy:
        y = side-1-y
    if not opposite and sx == ex:
        x, y = y, x
    return x, y, DIAGONAL if opposite else ADJACENT


def from_canonical(x, y, side, start, end):
    sx, sy = CORNERS[start]
    ex, ey = CORNERS[end]
    if sx == ex:
        x, y = y, x
    if sx:
        x = side-1-x
    if sy:
        y = side-1-y
    return x, y


def index(x, y):
    if x == y == 0:
        return 0
    radius = max(abs(x), abs(y))
    side = 1
    while 3*side < 2*radius+1:
        side *= 3
    x += side//2
    y += side//2
    order = RING
    result = side*side
    while True:
        bx, x = divmod(x, side)
        by, y = divmod(y, side)
        digit, (_, _, enter, leave) = next(
            (i,v) for i,v in enumerate(order) if v[:2] == (bx,by))
        result += digit*side*side
        if side == 1:
            return result
        x, y, order = to_canonical(x, y, side, enter, leave)
        side //= 3


def point(t):
    if t < 0:
        raise ValueError('time must be nonnegative')
    if t == 0:
        return (0,0)
    side = 1
    while 9*side*side <= t:
        side *= 3
    shift = side//2
    t -= side*side
    order = RING
    frames = []
    while side:
        digit, t = divmod(t, side*side)
        bx, by, enter, leave = order[digit]
        frames.append((side, bx, by, enter, leave))
        sx, sy = CORNERS[enter]
        ex, ey = CORNERS[leave]
        order = DIAGONAL if sx != ex and sy != ey else ADJACENT
        side //= 3
    x = y = 0
    for side, bx, by, enter, leave in reversed(frames):
        x, y = from_canonical(x,y,side,enter,leave)
        x += side*bx
        y += side*by
    return x-shift, y-shift


if __name__ == '__main__':
    for t,z in enumerate(clock(5)):
        assert point(t)==z
        assert index(*z)==t
    for t in (9**100, 10**100+183,10**200-1):
        assert index(*point(t))==t
    print('Bidirectional random access matches 59049 ordered sites and three large-index round trips.')
