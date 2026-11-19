"""Exact regressions for finite rank statements. Python standard library."""
from fractions import Fraction as Q
from itertools import permutations, product
from math import comb, factorial

CENTERS = ((22, 7), (355, 113))
COLS = [(0, 3, 0), (3, 0, 0), (1, 2, 0), (1, 0, 0), (1, 1, 1), (2, 1, 0)]
ROWS = list(product(range(3), range(2)))


def determinant(mat):
    mat = [list(map(Q, row)) for row in mat]
    det = Q(1)
    for k in range(len(mat)):
        pivot = next((i for i in range(k, len(mat)) if mat[i][k]), None)
        if pivot is None:
            return 0
        if pivot != k:
            mat[k], mat[pivot] = mat[pivot], mat[k]
            det = -det
        det *= mat[k][k]
        for i in range(k + 1, len(mat)):
            factor = mat[i][k] / mat[k][k]
            for j in range(k + 1, len(mat)):
                mat[i][j] -= factor * mat[k][j]
    return det


def support_matching(matrix):
    masks = {0}
    for row in matrix:
        masks = {mask | (1 << i) for mask in masks for i, value in enumerate(row)
                 if value and not mask & (1 << i)}
    return bool(masks)


def u(row, edge):
    j, s = row
    a, b, d = edge
    return j**(a+b+d) if not s else (d * j**(a+b+d-1) if d else 0)


def c(edge, col):
    a, b, d = edge
    h, A, B = col
    k = d-(A+B-a-b)
    if a > A or b > B or k < 0:
        return Q(0)
    return Q(comb(A, a)*comb(B, b)*h**k, factorial(k))


def normalized_original(row, col):
    j, s = row
    h, A, B = col
    l = A+B
    if not s:
        return Q(j**l), Q(0)
    vertical = sum(Q(degree*q, 2*p) for degree, (p, q) in zip((A, B), CENTERS))
    return Q(h*j**l), -vertical*j**(l-1) if l else Q(0)


def original_det():
    real = imag = Q(0)
    for perm in permutations(range(6)):
        inversions = sum(k > l for i, k in enumerate(perm) for l in perm[i+1:])
        x, y = Q((-1)**inversions), Q(0)
        for row, col_index in zip(ROWS, perm):
            a, b = normalized_original(row, COLS[col_index])
            x, y = x*a-y*b, x*b+y*a
        real, imag = real+x, imag+y
    return real, imag


def rank_mod(matrix, p):
    mat = [[x % p for x in row] for row in matrix]
    r = 0
    for k in range(len(mat[0])):
        j = next((i for i in range(r, len(mat)) if mat[i][k]), None)
        if j is None:
            continue
        mat[r], mat[j] = mat[j], mat[r]
        pivot_inverse = pow(mat[r][k], -1, p)
        for i in range(r+1, len(mat)):
            factor = mat[i][k]*pivot_inverse
            mat[i] = [(x-factor*y) % p for x, y in zip(mat[i], mat[r])]
        r += 1
        if r == len(mat):
            break
    return r


def tall_rank_control():
    p, order = 1009, 8
    im = next(i for i in range(1, p) if i*i % p == p-1)
    centers = [2*im*num*pow(den, -1, p) % p for num, den in CENTERS]
    cols = [(h,a,b) for h in range(9) for a in range(5) for b in range(2)
            if h+2*a+5*b <= 8]

    def jet(col, j):
        h, a, b = col
        values = [comb(h, k) if k <= h else 0 for k in range(order)]
        for n, center in zip((a,b), centers):
            series = [j*center] + [(-1)**(k+1)*pow(k, -1, p) for k in range(1,order)]
            for _ in range(n):
                values = [sum(values[k-l]*series[l] for l in range(k+1)) % p
                          for k in range(order)]
        return values

    matrix = [[jet(col, j)[s] for col in cols] for j in range(3) for s in range(order)]
    return rank_mod(matrix, p), len(matrix), len(cols)


def main():
    edges = [(0,0,d) for d in range(5)]
    for extra, expected in [((1,0,0), (-24, 0)), ((1,0,1), (-24, Q(2,3)))]:
        es = edges+[extra]
        U = [[u(row,e) for e in es] for row in ROWS]
        C = [[c(e,col) for col in COLS] for e in es]
        assert (determinant(U), determinant(C)) == expected
        assert support_matching(U) and support_matching(C)
        assert any(determinant([[C[i][j] for j in range(6) if j != omit] for i in range(5)])
                   for omit in range(6))
        assert any(C[-1])
    es = edges+[(0,0,5)]
    assert support_matching([[u(row,e) for e in es] for row in ROWS])
    assert support_matching([[c(e,col) for col in COLS] for e in es])
    assert original_det() == (Q(-21,85910), Q(6,3905))
    assert tall_rank_control() == (24,24,31)
    # Independent confluent specialization for the 12 time powers and one spatial column.
    # j, s order local Taylor coefficients in z-j. Spatial column equals j mod (z-j)^8.
    U = [[(comb(d,s)*j**(d-s) if d >= s else 0) for d in range(12)] + [int(s==0)*j]
         for j in range(3) for s in range(8)]
    assert rank_mod(U,1009) == 13
    for order, degree in ((8, 23), (20, 59)):
        # Certify a nonzero top coefficient by two finite-field determinants.
        rows = [(j, s) for j in range(3) for s in range(order)]
        matrix = [[comb(d,s)*j**(d-s) if d >= s else 0
                   for d in range(degree+1)] for j,s in rows]
        right = [j if s == 0 else 0 for j,s in rows]
        # Only nonvanishing is needed here. The general proof uses ordinary real integrals.
        assert rank_mod(matrix,1009) == degree+1
        assert rank_mod([row[:-1]+[v] for row,v in zip(matrix,right)],1009) == degree+1
    assert Q(4,23) < Q(1,3) and Q(10,59) < Q(4,23)
    assert Q(23,3*8) > Q(30,59) and Q(4*59,23*20) > Q(30,59)
    assert Q(1,2) < Q(101,200) < Q(30,59)
    print("Hermite degrees 23,59; injectivity threshold 30/59")
    print("Hall 15*lambda; group 4+10*lambda; common 4+11*lambda")
    print("normalized original determinant = -21/85910 + 6i/3905")
    print("Hermite counterexample: true rank 13; extrapolated 12; original rank 24/24")


if __name__ == "__main__":
    main()
