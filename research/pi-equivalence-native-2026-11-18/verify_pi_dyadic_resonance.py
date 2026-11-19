"""Certify entire dyadic sine-energy blocks via short residue sums.

Place next to verify_pi_line_records.py from this research directory.
"""
import argparse
from fractions import Fraction as F
from itertools import islice
from sys import set_int_max_str_digits

from verify_pi_line_records import certified_convergents, machin_grid, pi_grid


def lower_grid(x, scale):
    return F(x.numerator * scale // x.denominator, scale)


def upper_grid(x, scale):
    return -lower_grid(-x, scale)


def show(lo, hi, places):
    unit = 10**places

    def endpoint(x, upper):
        grid = upper_grid if upper else lower_grid
        k = int(grid(x, unit) * unit)
        whole, tail = divmod(k, unit)
        return f"{whole}.{tail:0{places}d}"

    return f"[{endpoint(lo, False)}, {endpoint(hi, True)}]"


def resonance_bounds(n, m, encl, terms):
    pi_low, pi_high, source_scale = encl
    delta_low = F(n * (n*source_scale - m*pi_high), pi_high)
    delta_high = F(n * (n*source_scale - m*pi_low), pi_low)
    if delta_high < 0:
        delta_low, delta_high = -delta_high, -delta_low
    assert 0 < delta_low <= delta_high < F(1, 4)

    grid = 10**24
    eps_l, eps_h = lower_grid(delta_low, grid), upper_grid(delta_high, grid)
    pi_l = lower_grid(F(pi_low, source_scale), grid)
    pi_h = upper_grid(F(pi_high, source_scale), grid)
    zeta_h = pi_h**2 / 6
    inverse_n = F(1, min(n, 10**16))  # only used for upper error bounds
    M = 1 << ((n-1).bit_length()-1)
    assert M < n <= 2*M
    cutoff = min(terms, (n-1)//2)
    inverse = pow(m, -1, n)
    tail_grid = 10**26
    acc = 0
    residue = 0
    for d in range(1, cutoff+1):
        residue += inverse
        if residue >= n:
            residue -= n
        multiplicity = int(residue <= M) + int(n-residue <= M)
        acc += (multiplicity*tail_grid) // d**2
    pair_low = F(acc, tail_grid)
    pair_high = F(acc+cutoff, tail_grid)
    rational_low = pair_low / pi_h**2
    rational_high = pair_high / pi_l**2 + 2*cutoff*inverse_n**2 + F(1, 2*cutoff)
    before_low = rational_low / (1+pi_h*eps_h/2)**2
    before_high = rational_high / (1-pi_h*eps_h/2)**2

    u_high = pi_h * eps_h * inverse_n
    sine_factor = (1-u_high**2/6)**2
    peak_low = 1/(pi_h*eps_h)**2
    peak_high = 1/((pi_l*eps_l)**2 * sine_factor)
    off_peak = zeta_h/(1-2*eps_h)**2
    D_low = peak_low/before_high
    D_high = (peak_high+off_peak)/before_low

    # Choose the largest dyadic horizon after 2M that is at most n/(2 epsilon).
    end = 2*M
    folds = 0
    while 4*end*eps_h <= n:
        end *= 2
        folds += 1
    assert 4*end*eps_l > n
    blocks = end//n
    assert blocks >= 1
    # Harmonic-square tail is between 1/(blocks+1) and 1/blocks.
    multiple_lo = (pi_l**2/6 - F(1, blocks))*sine_factor
    multiple_hi = (zeta_h - F(1, blocks+1))/(1-(pi_h*inverse_n/2)**2/6)**2
    rest = 2*(blocks+1)*zeta_h*(pi_h*eps_h)**2
    later_lo = multiple_lo/(1 + off_peak/peak_low)
    later_hi = multiple_hi+rest
    return M.bit_length()-1, folds, cutoff, D_low, D_high, later_lo, later_hi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("chudnovsky","machin"), default="chudnovsky")
    parser.add_argument("--terms", type=int, default=65536)
    args = parser.parse_args()
    if args.terms < 1:
        parser.error("--terms must be positive")
    set_int_max_str_digits(0)
    enclose = pi_grid if args.method == "chudnovsky" else machin_grid
    interval = enclose(30000)
    _, n, m = next(islice(certified_convergents(*interval), 28420, 28421))
    for p, q in [(355, 113), (n, m)]:
        j, folds, cutoff, d0, d1, a0, a1 = resonance_bounds(p, q, interval, args.terms)
        print(f"digits(p)={len(str(p))}, j={j}, extra doublings={folds}, residue pairs={cutoff}")
        print(f"D_j in {show(d0,d1,4)}; subsequent product in {show(a0,a1,8)}")


if __name__ == "__main__":
    main()
