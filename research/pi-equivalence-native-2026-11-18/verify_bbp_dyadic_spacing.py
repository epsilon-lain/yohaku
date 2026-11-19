"""Finite exact checks of signed BBP difference polynomials and height denominators."""
from fractions import Fraction as F
from functools import lru_cache
from math import comb, lcm


def mul(x, y, rad):
    a, b = x
    c, d = y
    return a*c + rad*b*d, a*d + b*c


def add(x, y):
    return x[0] + y[0], x[1] + y[1]


def scale(c, x):
    return c*x[0], c*x[1]


def power(x, n, rad):
    result = (1, 0)
    while n:
        if n % 2:
            result = mul(result, x, rad)
        x = mul(x, x, rad)
        n //= 2
    return result


@lru_cache(None)
def approximation(n, degree):
    length = 8*n + 8
    raw = sum(F(c, 16**k * (8*k+r)) for k in range(n+1)
              for r, c in ((1, 4), (4, -2), (5, -1), (6, -1)))
    coefficients = []
    beta = F(1, length+1)
    integral = F(0)
    for k in range(degree+1):
        coefficient = int(k == 1)
        for step, weight in ((1, -2), (3, -2), (4, 1)):
            if k >= step:
                coefficient += weight*coefficients[k-step]
        integral += coefficient*beta
        coefficients.append(coefficient)
        beta *= F(k+1, length+k+2)
    return raw + integral/16**n


def kernel(rho, rad, d, u, v):
    size = 8*d+u+v
    numerator = [(0, 0) for _ in range(size+1)]
    numerator[u] = scale(16**d, power(rho, u, rad))
    factor = power(rho, v, rad)
    for k in range(8*d+1):
        numerator[k+v] = add(numerator[k+v], scale((-1)**(k+1)*comb(8*d, k), factor))
    values = []
    previous = (0, 0)
    for value in numerator:
        previous = add(value, mul(rho, previous, rad))
        values.append(previous)
    assert values[-1] == (0, 0)
    return values[:-1]


def check_pair(n, degree, n2, degree2):
    d = n2-n
    m = min(degree, degree2)
    u, v = degree-m, degree2-m
    size = 8*d+u+v
    length = 8*n+8
    b = length+m+2
    den = 8 * comb(b+size, size) * lcm(*range(1,size+2))
    ratios = [F(comb(m+1+j,j),comb(b+j,j)) for j in range(size)]
    assert all((den//8) % a.denominator == 0 for a in ratios)
    roots = [((-1,1),2),((-1,-1),2),((0,1),-1),((0,-1),-1)]
    terms = []
    for rho, rad in roots:
        coeffs = kernel(rho, rad, d, u, v)
        integral = (0,0)
        for coefficient, ratio in zip(coeffs, ratios):
            integral = add(integral, scale(ratio, coefficient))
        eight_a = rho if rad == 2 else (1, -rho[1])
        term = scale(F(1,8), mul(mul(eight_a,rho,rad),integral,rad))
        terms.append(scale(den,term))
        assert all(c.denominator == 1 for c in terms[-1])
    constant, neg, imag, imag_conj = terms
    assert constant != (0,0) and neg == (constant[0],-constant[1])
    linear = add(mul(imag,power((0,1),m,-1),-1),mul(imag_conj,power((0,-1),m,-1),-1))
    assert linear[1] == 0
    lead = scale((-1)**m, neg)
    alpha_m = power((1,1),m,2)
    value = add(mul(add(mul(lead,alpha_m,2),linear),alpha_m,2),constant)
    beta = F(1, (length+m+2)*comb(length+m+1, m+1))
    direct = 16**n2*(approximation(n2,degree2)-approximation(n,degree))
    assert scale(direct*den/beta,alpha_m) == value


def main():
    cases = []
    for n in (1, 3, 5, 12, 21):
        for m in (4*n-1,4*n,4*n+1):
            for d in (0,1,2,4):
                for j in (-5,-2,-1,0,1,2,5):
                    if m+j >= 0 and (j or d):
                        cases.append((n,m,n+d,m+j))
    for case in cases:
        check_pair(*case)
    print(f"{len(cases)} exact signed two-point identities; both real conjugates checked nonzero")
    print("Each case checks four quotient kernels, each rational Beta denominator and the cleared quadratic polynomial.")


if __name__ == '__main__':
    main()
