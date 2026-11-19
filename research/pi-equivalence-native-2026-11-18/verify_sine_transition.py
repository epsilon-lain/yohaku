#!/usr/bin/env python3
"""Certify the first two large sine peaks after 355 and the first normalized record.

Run next to verify_pi_continuous_wave.py and verify_pi_line_records.py.
Uses rational outward bounds throughout. No external Python packages.
"""
from fractions import Fraction
from hashlib import sha256

from verify_pi_continuous_wave import SCALE, abs_sine_bounds, ceil_fraction, floor_fraction, pi_bounds, sine_series_bounds
from verify_pi_line_records import certified_convergents, machin_grid


def show(interval, decimals=12):
    def decimal_text(integer):
        whole, fractional = divmod(abs(integer), 10**decimals)
        return f"{'-' if integer < 0 else ''}{whole}.{fractional:0{decimals}d}"

    lo, hi = interval
    left = decimal_text(floor_fraction(lo * 10**decimals))
    right = decimal_text(ceil_fraction(hi * 10**decimals))
    return f"[{left}, {right}]"


def absolute_interval(lo, hi):
    return (0 if lo <= 0 <= hi else min(abs(lo), abs(hi))), max(abs(lo), abs(hi))


def rational_square_inverse(x):
    return 1 / (x*x)


def predicted_background(pi_lo, pi_hi, phase_lo, phase_hi, count=8192):
    """Bound pi^2/6 + sum_{j>=1} (j+phase)^-2 just before the first peak."""
    scale = 10**24
    a, b = floor_fraction(scale*phase_lo), ceil_fraction(scale*phase_hi)
    low_sum = high_sum = 0
    for j in range(1, count + 1):
        low_sum += scale**3 // (j*scale + b)**2
        high_sum += -(-scale**3 // (j*scale + a)**2)
    # For a positive decreasing function, enclose sum from count+1 by
    # its integrals from count+1 and from count.
    return (pi_lo**2/6 + Fraction(low_sum,scale) + 1/(count+1+phase_hi),
            pi_hi**2/6 + Fraction(high_sum,scale) + 1/(count+phase_lo))


def transfer_checkpoints(n, d_lo, d_hi, phase_lo, phase_hi, pi_lo, pi_hi):
    """Configure half-integer windows on the recurring phase, using exact bounds."""
    targets = {}
    transferred_lo = transferred_hi = Fraction(1, 6)
    for degree in range(3):
        if degree:
            lo, hi = degree*phase_lo, degree*phase_hi
            near = floor_fraction(lo + Fraction(1, 2))
            assert near == floor_fraction(hi + Fraction(1, 2))
            angle_lo, angle_hi = absolute_interval(lo - near, hi - near)
            assert 0 < angle_lo <= angle_hi < Fraction(1, 2)
            scaled_lo = floor_fraction(SCALE*pi_lo*angle_lo)
            scaled_hi = ceil_fraction(SCALE*pi_hi*angle_hi)
            sine_lo, _ = sine_series_bounds(scaled_lo)
            _, sine_hi = sine_series_bounds(scaled_hi)
            transferred_lo += Fraction(SCALE**2, sine_hi**2)
            transferred_hi += Fraction(SCALE**2, sine_lo**2)
        half = Fraction(2*degree+1, 2)
        blocks = floor_fraction(half/(n*d_hi))
        assert blocks == floor_fraction(half/(n*d_lo))
        targets[n*blocks] = (degree, blocks, transferred_lo, transferred_hi)
    return targets


def normalized_record(anchor, numerator):
    pi_lower, pi_upper, scale = machin_grid(370)
    alpha_lower = Fraction(scale, pi_upper)
    alpha_upper = Fraction(scale, pi_lower)
    base_lo = anchor*(anchor*alpha_lower - numerator)
    base_hi = anchor*(anchor*alpha_upper - numerator)
    assert 0 < base_lo <= base_hi < Fraction(1, 2)
    for index, (_, n, m) in enumerate(certified_convergents(pi_lower, pi_upper, scale)):
        # The nonzero convergents m/n of 1/pi are obtained by exchanging p,q
        # in each pi convergent. The omitted 0/1 has error 1/pi > base_hi.
        if n == anchor:
            assert m == numerator
            continue
        lo, hi = absolute_interval(n*(n*alpha_lower-m), n*(n*alpha_upper-m))
        if lo > base_hi:
            continue
        assert hi < base_lo and n > anchor
        # Legendre applies to all reduced fractions beating this threshold.
        # A non-reduced sample would yield a still better reduced fraction
        # with smaller denominator; the computed prefix excludes that case.
        digest = sha256(f"{n}/{m}".encode("ascii")).hexdigest()
        assert index == 306 and digest == "b21b0ce17853f6b87ddbf617e7b550ae88ee57fb83e68703e3945a02b3846bbd"
        print(f"First normalized record after {anchor} (pi convergent index {index}): n={n}, m={m}")
        print(f"  normalized error {show((lo, hi), 18)}; sha256(n/m)={digest}")
        return
    raise ArithmeticError("The enclosure did not determine a new normalized record")


def main():
    n, a = 355, 113
    pi_lo, pi_hi = pi_bounds()
    d_lo, d_hi = n/pi_hi-a, n/pi_lo-a
    assert 0 < n*d_lo <= n*d_hi < Fraction(1, 2)
    center_lo, center_hi = 1/d_hi, 1/d_lo
    residue = (-pow(a,-1,n)) % n
    index = floor_fraction((center_lo-residue)/n)
    assert index == floor_fraction((center_hi-residue)/n)
    k1 = residue + n*index
    k2 = k1+n
    assert (k1,k2) == (103993,104348)
    # For any k>n with a smaller sine, |a*k-n*l+k*d| < n*d with l
    # the nearest integer to k/pi. Up to 2/d - n the determinant is -1.
    # The two members of that residue class within n of 1/d are k1, k2.
    assert n < k1 < center_lo <= center_hi < k2 < 2*center_lo-n
    phase_lo, phase_hi = (center_lo-k1)/n, (center_hi-k1)/n
    assert Fraction(1,2) < phase_lo <= phase_hi < 1  # k2 beats k1
    print(f"First transition center {show((center_lo, center_hi))}; residue {residue} mod {n}")
    print(f"Relative offset {show((phase_lo, phase_hi))}; anchor error {show((n*d_lo,n*d_hi),18)}")

    scaled_lo, scaled_hi = floor_fraction(SCALE*pi_lo), ceil_fraction(SCALE*pi_hi)
    anchor_lo, anchor_hi = abs_sine_bounds(n, scaled_lo, scaled_hi)
    bg_lo, bg_hi = predicted_background(pi_lo,pi_hi,phase_lo,phase_hi)
    predicted = {
        0:(bg_lo,bg_hi),
        1:(bg_lo+rational_square_inverse(phase_hi), bg_hi+rational_square_inverse(phase_lo)),
    }
    predicted[2] = (predicted[1][0]+rational_square_inverse(1-phase_lo),
                    predicted[1][1]+rational_square_inverse(1-phase_hi))
    sample_points = {k1-1:0, k1:1, k2-1:1, k2:2}
    windows = transfer_checkpoints(n,d_lo,d_hi,phase_lo,phase_hi,pi_lo,pi_hi)
    sum_lo = sum_hi = 0
    for k in range(1,max(windows)+1):
        sine_lo,sine_hi = abs_sine_bounds(k,scaled_lo,scaled_hi)
        if k <= floor_fraction(2*center_lo-n) and k not in (n,k1,k2):
            assert sine_lo > anchor_hi
        sum_lo += SCALE**3 // sine_hi**2
        sum_hi += -(-SCALE**3 // sine_lo**2)
        if k in (k1,k2):
            m, remainder = divmod(a*k+1,n)
            assert remainder == 0
            diff_lo,diff_hi = absolute_interval(k/pi_hi-m,k/pi_lo-m)
            assert diff_hi < d_lo and k*diff_lo > n*d_hi
            heights = (Fraction(anchor_lo**2,sine_hi**2), Fraction(anchor_hi**2,sine_lo**2))
            print(f"k={k}, m={m}, peak/anchor={show(heights,15)}, normalized error={show((k*diff_lo,k*diff_hi),15)}")
        if k in sample_points:
            energy = (Fraction(anchor_lo**2*sum_lo,SCALE**3),
                      Fraction(anchor_hi**2*sum_hi,SCALE**3))
            pred_lo,pred_hi = predicted[sample_points[k]]
            discrepancy = energy[0]-pred_hi, energy[1]-pred_lo
            assert max(abs(x) for x in discrepancy) < Fraction(1,40000)
            print(f"  S({k})/w_355={show(energy,15)}, signed difference from limiting profile {show(discrepancy,12)}")
        if k in windows:
            degree, blocks, pred_lo, pred_hi = windows[k]
            difference = (d_lo*d_lo*sum_lo/SCALE-pred_hi,
                          d_hi*d_hi*sum_hi/SCALE-pred_lo)
            assert max(abs(x) for x in difference) < 3*(n*d_lo)**2
            print(f"  transfer D={degree}, B={blocks}, Bn={k}, signed error {show(difference,15)}")
    normalized_record(n,a)


if __name__ == "__main__":
    main()
