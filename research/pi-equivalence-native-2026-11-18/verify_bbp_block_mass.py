"""Certify the bounded shell exceptions and the two numerical root brackets."""
from fractions import Fraction
from math import comb, isqrt

P = 1009
R = (1, 3, 5, 7)
C = {1: 4, 4: -2, 5: -1, 6: -1}


def shell_mod(u, v, r):
    chi = -1 if r in (3, 5) else 1
    raw = sum(C[a] * pow(2, (a - k) // 2, P) * chi ** k *
              pow(k, -1, P) for k in range(1, u + 1)
              if (a := r * k % 8) in C)
    total = raw
    for radicand, shift, conjugates in [(2, -1, r in (3, 5)),
                                         (-1, 0, r in (3, 7))]:
        roots = [x for x in range(P) if x * x % P == radicand % P]
        assert len(roots) == 2
        for x in roots:
            rho = (shift + x) % P
            srho = (shift + (-x if conjugates else x)) % P
            weight = rho if radicand == 2 else 1 - rho
            g = rho * pow(rho - 1, -1, P) % P
            sg = srho * pow(srho - 1, -1, P) % P
            factor = ((1 - srho) * pow(1 - rho, -1, P) *
                      pow(sg, u + 1, P) * pow(g, -1, P)) % P
            beta_sum = sum(pow(srho, s, P) *
                           pow((u+s+1) * comb(u+s, s), -1, P)
                           for s in range(v))
            total += 2 * weight * factor * beta_sum
    return total % P


def log_bounds(x):
    """Enclose log(x) with exact rationals using atanh's series, x positive."""
    def small(z):
        y = (z - 1) / (z + 1)
        assert 0 <= y <= Fraction(1, 3)
        terms = 30
        lo = 2 * sum(y ** (2*k+1)/(2*k+1) for k in range(terms))
        hi = lo + 2*y**(2*terms+1)/((2*terms+1)*(1-y*y))
        return lo, hi

    x = Fraction(x)
    k = 0
    while x >= 2:
        x /= 2
        k += 1
    while x < 1:
        x *= 2
        k -= 1
    lo, hi = small(x)
    klo, khi = sorted(k * z for z in small(Fraction(2)))
    return lo + klo, hi + khi


def margin_bounds(t):
    # D(t)=12+5t/2−3B(t)−log(16)+t*log(1+sqrt(2)).
    s = 10**16
    a = isqrt(2*s*s)
    root_lo, root_hi = Fraction(a, s), Fraction(a+1, s)
    logs = [(12 + 5*t/2, 12 + 5*t/2)]
    for w, x in ((-3*(8+t),8+t), (24,8), (3*t,t), (-1,16)):
        logs.append(sorted(w*v for v in log_bounds(x)))
    logs.append((t*log_bounds(1+root_lo)[0],t*log_bounds(1+root_hi)[1]))
    return tuple(sum(vals) for vals in zip(*logs))


def main():
    cells = [(u,v,r) for u in range(1,12) for v in range(u+1) for r in R]
    zeros = [a for a in cells if not shell_mod(*a)]
    assert zeros == [(1,0,3),(1,0,7)], zeros
    assert Fraction(96*104,9*64*13) < 2
    print(f'{len(cells)} residue tests in {len(cells)//4} cells, zeros {zeros}')
    # Direct interval evaluation at the algebraic critical point via rational endpoints.
    lower_t = Fraction(565685424949238, 10**14)
    upper_t = lower_t + Fraction(1, 10**14)
    assert lower_t**2 < 32 < upper_t**2
    # On [5,6], |D'(t)| <= 5 by D'=5/2+log(1+sqrt(2))-3log(1+8/t).
    assert log_bounds(Fraction(13, 5))[1] < 1
    assert log_bounds(Fraction(5, 2))[1] < 1
    low_gap, high_gap = margin_bounds(lower_t)
    bound_error = 5 * (upper_t - lower_t)
    assert low_gap - bound_error > Fraction(56274313749, 10**11)
    assert high_gap + bound_error < Fraction(56274313750, 10**11)
    at_four = margin_bounds(Fraction(4))
    assert -at_four[1]/2 > Fraction(808022, 10**7)
    assert -at_four[0]/2 < Fraction(808023, 10**7)
    print("certified critical lower-bound exponent in (0.56274313749, 0.56274313750)")
    for value, sign in [('3.07151', 1), ('3.07152', -1),
                        ('4.66931', -1), ('4.66932', 1), ('4', -1)]:
        lo, hi = margin_bounds(Fraction(value))
        assert lo > 0 if sign == 1 else hi < 0
        print(f't={value}: certified sign {sign:+d}, margin shown rounded {float((lo+hi)/2):.11f}')


if __name__ == '__main__':
    main()
