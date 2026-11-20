"""Exact finite checks for diamond switches and fixed Ramanujan extrapolation."""

from argparse import ArgumentParser
from fractions import Fraction as F
from math import comb, gcd


def arctan_bounds(base, count):
    value = sum((F((-1)**j, (2*j + 1) * base**(2*j + 1)) for j in range(count)), F(0))
    neighbor = value + F((-1)**count, (2*count + 1) * base**(2*count + 1))
    return min(value, neighbor), max(value, neighbor)


def pi_bounds(machin, scale):
    if machin:
        lo5, hi5 = arctan_bounds(5, 30)
        lo239, hi239 = arctan_bounds(239, 12)
        low, high = 16*lo5 - 4*hi239, 16*hi5 - 4*lo239
    else:
        lo2, hi2 = arctan_bounds(2, 65)
        lo3, hi3 = arctan_bounds(3, 45)
        low, high = 4*(lo2 + lo3), 4*(hi2 + hi3)
    return (low * scale).__floor__(), (high * scale).__ceil__()


def absolute_error(p, q, pi_low, pi_high, scale):
    left, right = p*scale - q*pi_high, p*scale - q*pi_low
    if right < 0:
        return -right, -left
    assert left > 0
    return left, right


def bezout_candidates(p, q, lo, hi, scale):
    candidates = []
    for determinant in (-1, 1):
        q0 = (-determinant * pow(p, -1, q)) % q if q > 1 else 0
        p0 = (determinant + p*q0) // q
        centers = [F(q0*endpoint - p0*scale, p*scale - q*endpoint)
                   for endpoint in (lo, hi)]
        j = centers[0].__floor__()
        assert j == centers[1].__floor__()
        for k in (j, j+1):
            if q0 + k*q > q:
                candidates.append((p0 + k*p, q0 + k*q))
    return candidates


def certify_diamond(machin):
    scale = 10**30
    lo, hi = pi_bounds(machin, scale)
    active = []
    for q in range(1, 200001):
        p = (2*q*lo + scale) // (2*scale)
        assert p == (2*q*hi + scale) // (2*scale)
        if gcd(p, q) != 1:
            continue
        low, high = absolute_error(p, q, lo, hi, scale)
        if 2*q*high < scale:
            active.append((p, q))
        else:
            assert 2*q*low > scale
    for (p, q), following in zip(active, active[1:]):
        low, high = absolute_error(p, q, lo, hi, scale)
        crossings = []
        for new_p, new_q in bezout_candidates(p, q, lo, hi, scale):
            new_low, new_high = absolute_error(new_p, new_q, lo, hi, scale)
            assert low > new_high
            crossings.append((F(new_q-q, high-new_low), F(new_q-q, low-new_high),
                              (new_p, new_q)))
        first = min(crossings)
        assert first[2] == following
        assert all(first[1] < rival[0] for rival in crossings if rival != first)
        assert abs(q*following[0] - p*following[1]) == 1
    return active


def check_diamond():
    active = certify_diamond(True)
    assert active == certify_diamond(False)
    assert (208341, 66317) not in active
    assert active[active.index((104348, 33215)) + 1] == (312689, 99532)
    print("Diamond selections at q <= 200000, both pi formulas:")
    print(active)


def ramanujan_term(n):
    return F((42*n + 5)*comb(2*n, n)**3, 4096**n)


def v2(integer):
    integer = abs(integer)
    assert integer
    return (integer & -integer).bit_length() - 1


def binary_floor(value):
    assert value > 0
    guess = value.numerator.bit_length() - value.denominator.bit_length()
    power = F(2)**guess
    return guess - (value < power)


def check_ramanujan():
    table = [(F(1),), (F(-1, 63), F(64, 63)),
             (F(1, 3969), F(-128, 3969), F(4096, 3969))]
    terms = [ramanujan_term(n) for n in range(80)]
    partial = []
    total = F(0)
    for term in terms:
        total += term
        partial.append(total)
    for n in (16, 32, 64):
        future = n + 12
        f_low = partial[future] + terms[future + 1]
        f_high = partial[future] + F(32, 31)*terms[future + 1]
        pi_low, pi_high = 16/f_high, 16/f_low
        outputs = []
        exponent_ranges = []
        for weights in table:
            u = sum((weight*partial[n+j] for j, weight in enumerate(weights)), F(0))
            p_over_q = 16/u
            errors = sorted((pi_low-p_over_q, pi_high-p_over_q))
            if errors[1] < 0:
                errors = [-errors[1], -errors[0]]
            assert 0 < errors[0] <= errors[1]
            q_squared = p_over_q.denominator**2
            exponent_ranges.append(tuple(binary_floor(e*q_squared) for e in errors))
            outputs.append(u)
        diff = outputs[1] - outputs[2]
        assert v2(diff.denominator) > 10*n
        print(f"n={n}, floor(log2(normalized errors))={exponent_ranges}, "
              f"v2(denominator(first - second extrapolation))={v2(diff.denominator)}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--diamond", action="store_true")
    parser.add_argument("--ramanujan", action="store_true")
    args = parser.parse_args()
    if args.diamond or not args.ramanujan:
        check_diamond()
    if args.ramanujan or not args.diamond:
        check_ramanujan()
