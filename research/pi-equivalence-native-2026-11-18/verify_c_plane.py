"""Exact checks of the C-to-plane reduction for the native selected columns."""
from fractions import Fraction
from functools import lru_cache
from math import comb, factorial

P = 1009
CAPS = (11, 11, 11, 10, 8, 6, 4, 2, 0)
JETS = [(a, d) for a, count in ((0, 29), (1, 18), (2, 6)) for d in range(count)]
PATCH = [(h, a) for a in range(7) for h in range((16 if not a else 9 if a <= 3 else 1) + 1)]


def coefficient(h, A, a, d):
    power = d + a - A
    if a > A or power < 0:
        return Fraction(0)
    return Fraction(comb(A, a) * h**power, factorial(power))


def reduce_mod(value):
    return value.numerator * pow(value.denominator, -1, P) % P


def elimination(matrix):
    mat = [row[:] for row in matrix]
    rank, determinant = 0, 1
    for col in range(len(mat[0])):
        k = next((i for i in range(rank, len(mat)) if mat[i][col] % P), None)
        if k is None:
            continue
        if k != rank:
            mat[rank], mat[k] = mat[k], mat[rank]
            determinant = -determinant
        pivot = mat[rank][col] % P
        determinant = determinant * pivot % P
        inv = pow(pivot, -1, P)
        for row in mat[rank + 1:]:
            multiple = row[col] * inv % P
            if multiple:
                for c in range(col + 1, len(row)):
                    row[c] = (row[c] - multiple * mat[rank][c]) % P
                row[col] = 0
        rank += 1
        if rank == len(mat):
            break
    return rank, determinant % P


def selected(H):
    n = H - 16
    bottom = {(h,A,B) for h in range(n) for A in range(3*(H//8+2))
              for B in range(H//20+1) if h+8*(A//3)+20*B < H}
    return bottom | {(n+h,A,0) for A,top in enumerate(CAPS) for h in range(top+1)}


# Rational outward bounds for log(2)/2 = atanh(1/3).
LOW = sum((Fraction(1, (2*k+1)*3**(2*k+1)) for k in range(20)),Fraction(0))
HIGH = LOW + Fraction(9, 8*41*3**41)


def admissible(a, b, d, budget):
    lo, hi = 4*a+10*b+LOW*d, 4*a+10*b+HIGH*d
    if hi <= budget:
        return True
    assert lo > budget
    return False


@lru_cache(None)
def raw_entry(h,A,B,a,b,d):
    k = d + a + b - A - B
    if a>A or b>B or k<0:
        return 0
    return comb(A,a)*comb(B,b)*pow(h,k,P)*pow(factorial(k),-1,P)%P


def test_prefix(H,budget):
    cols = sorted(selected(H))
    rows = [(a,b,d) for a in range(1+budget//4) for b in range(1+budget//10)
            for d in range(int(budget/LOW)+1) if admissible(a,b,d,budget)]
    direct = elimination([[raw_entry(*c,*r) for c in cols] for r in rows])[0]
    sliced = 0
    for b in range(1+max(c[2] for c in cols)):
        plane = [(h,A) for h,A,B in cols if B==b]
        # Kernel transform: S(h) times T-derivative of T^d evaluated at h.
        mats = [[(pow(h,a,P)*comb(d,A)*pow(h,d-A,P))%P if d>=A else 0
                 for h,A in plane] for a,b0,d in rows if b0==b]
        if mats:
            sliced += elimination(mats)[0]
    assert direct == sliced, (H,budget,direct,sliced)
    return direct


def zero_center_test(H):
    """U(0)C versus the original normalized jet, at the same actual columns."""
    r1 = 2*469*22*pow(7,-1,P) % P
    r2 = 2*469*355*pow(113,-1,P) % P
    cols = sorted(selected(H))
    rows = [(j,s,a,b) for j in range(3) for b in range((H-1)//20+1)
            for a in range((H-1-20*b)//8+1) for s in range(H-8*a-20*b)]
    exp_series = {(h,n): pow(h,n,P)*pow(factorial(n),-1,P)%P
                  for h,_,_ in cols for n in range(H)}
    mat = []
    for j,s,a,b in rows:
        values = []
        for h,A,B in cols:
            if a>A or b>B:
                values.append(0)
                continue
            # Multiply the separated U(0) and C at d=s.
            product = sum(comb(i,a)*comb(k,b)*pow(j*r1,i-a,P)*pow(j*r2,k-b,P)*
                          raw_entry(h,A,B,i,k,s) for i in range(a,A+1)
                          for k in range(b,B+1)) % P
            # Direct Taylor expansion of the original periodic jet in local z.
            expected = comb(A,a)*comb(B,b)*sum(
                comb(A-a,i)*comb(B-b,k)*pow(j*r1,A-a-i,P)*
                pow(j*r2,B-b-k,P)*exp_series[h,s-i-k]
                for i in range(min(A-a,s)+1) for k in range(min(B-b,s-i)+1)) % P
            assert product == expected
            values.append(product)
        mat.append(values)
    rank, _ = elimination(mat)
    assert len(rows)==len(cols)==rank
    return rank


def main():
    assert len(JETS) == len(PATCH) == 53
    matrix = [[reduce_mod(coefficient(h,A,a,d)) for h,A in PATCH] for a,d in JETS]
    rank, det = elimination(matrix)
    assert rank == 53
    assert [(a,d) for a in range(3) for d in range(31) if admissible(a,0,d,10)] == JETS
    # Finite enumeration of all potentially exceptional top transitions as in the proof.
    for h0,a0 in PATCH:
        assert h0 + 8*((a0+2)//3) <= 17
        for A in range(9):
            top_h = 15-20-8*(A//3)+h0
            if top_h>=0:
                assert A+a0 < len(CAPS) and top_h <= CAPS[A+a0]
    out = [(H,budget,test_prefix(H,budget)) for H,budget in
           [(17,3),(19,10),(22,11),(24,13),(26,14),(28,15)]]
    print("U(0)C equals original and has full rank for H=17:", zero_center_test(17))
    print(f"53x53 rational lift, modular determinant {det} mod {P}")
    print("H, cost, common exact/split modular C rank:", out)


if __name__ == "__main__":
    main()
