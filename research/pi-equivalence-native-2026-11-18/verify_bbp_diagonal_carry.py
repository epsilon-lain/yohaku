"""Exact polynomial-shift and denominator regressions for moving (N,M)."""

from fractions import Fraction
from itertools import combinations
from math import comb

from verify_bbp_carry_density import coefficients, determinant, mod, primes, shift, snapshots


def boundary_row(n, m, d, a, step):
    length = 8*(n+1)
    if step == 0:
        return (Fraction(1), Fraction(0), Fraction(0), Fraction(0), Fraction(0))
    scale = 16**(d*step)
    leading = (0, 1, 0, 0)
    tail = leading
    for _ in range(a * step):
        tail = shift(tail)
    moment = Fraction(1)
    poly = (0, 0, 0, 0)
    total = [Fraction(0)] * 4
    for k in range(1, (a + 8*d)*step + 2):
        poly = shift(poly)
        j = k - a*step - 1
        tail_weight = (-1)**j * comb(8*d*step, j) if 0 <= j <= 8*d*step else 0
        poly = tuple(q + (scale*x if k == 1 else 0) - tail_weight*y
                     for q, x, y in zip(poly, leading, tail))
        moment *= Fraction(m+k, length+m+1+k)
        for i, q in enumerate(poly):
            total[i] += q * moment / scale
    assert poly == (0, 0, 0, 0)
    return (Fraction(1), *total)


def main():
    exact = minors = modular = 0
    grids = ((35, 140, 1, 4), (36, 140, 1, 4), (64, 224, 1, 4),
             (38, 134, 8, 28), (42, 168, 2, 8))
    for n, m, d, a in grids:
        width = 6
        coeff = coefficients(m + a*width + 4)
        moments, start = snapshots(n, m, coeff)
        scale = moments[m] / 16**n
        basis = [start[m], *(scale*k for k in coeff[m:m+4])]
        matrix, vals = [], []
        for h in range(width+1):
            matrix.append(boundary_row(n, m, d, a, h))
            _, values = snapshots(n+d*h, m+a*h, coeff)
            vals.append(values[-1])
            assert sum(x*y for x,y in zip(basis,matrix[-1])) == vals[-1]
            exact += 1
        for inds in combinations(range(width+1),5):
            assert determinant([list(matrix[k]) for k in inds])
            minors += 1
        L = 8*(n+1)
        end = L+m+(8*d+a)*width+1
        for p in primes(end):
            if p*p <= end or moments[m].denominator % p:
                continue
            if any(row[i].denominator % p == 0 for row in matrix for i in range(5)):
                continue
            for row, val in zip(matrix,vals):
                computed = sum(mod(x,p)*mod(p*y,p) for x,y in zip(row,basis)) % p
                assert computed == mod(p*val,p)
                modular += 1
    # Independent elementary checks of the rational resonance obstruction.
    from math import gcd
    checked = 0
    for B in range(1, 33):
        for A in range(3*B, 5*B+1):
            if gcd(A, B) != 1:
                continue
            t = Fraction(A, B)
            z = t/(8+t)
            required = ((10*z-1)/(1-z) - (1-z*z)/(1+z*z))
            R = A*A + 8*A*B + 32*B*B
            assert (B*required).denominator != 1
            assert 64*B*B*(A+4*B) % R
            checked += 1
    print(f"{checked} exact rational-slope resonance checks")
    print(f"{exact} moving finite rational identities; "
          f"{minors} nonzero moving minors; {modular} prime residues")


if __name__=='__main__':
    main()
