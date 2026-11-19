from fractions import Fraction
from math import log2


def v2_int(n):
    if n == 0:
        raise ValueError("v2(0) is infinite")
    n = abs(n)
    return (n & -n).bit_length() - 1


def v2_fraction(x):
    return v2_int(x.numerator) - v2_int(x.denominator)


def kernel_coefficients(M):
    a = [0] * (M + 1)
    for k in range(M + 1):
        a[k] = (
            (1 if k == 1 else 0)
            - (2 * a[k - 1] if k >= 1 else 0)
            - (2 * a[k - 3] if k >= 3 else 0)
            + (a[k - 4] if k >= 4 else 0)
        )
    return a


def exact_Y(N):
    M = 4 * N
    L = 8 * N + 8
    a = kernel_coefficients(M)

    bbp = Fraction(0)
    for i in range(N + 1):
        bbp += 16 ** (N - i) * (
            Fraction(4, 8 * i + 1)
            - Fraction(2, 8 * i + 4)
            - Fraction(1, 8 * i + 5)
            - Fraction(1, 8 * i + 6)
        )

    beta = Fraction(1, L + 1)
    correction = Fraction(0)
    for k in range(M + 1):
        correction += a[k] * beta
        beta *= Fraction(k + 1, L + k + 2)

    return bbp + correction


def shift_certifies(N):
    assert N % 2 == 0 and N >= 4
    certificates = []
    s = 1
    while (1 << s) < N:
        c = N - (1 << s)
        if c >= 1:
            y = exact_Y(c)
            nu = v2_fraction(y)
            d = (12 * c + 9).bit_length() - 1
            s_min = max(2, d - 1, nu + 2 * d - 1)
            ok = nu < 4 * c - 3 and s >= s_min
            certificates.append((s, c, nu, d, s_min, ok))
        s += 1
    return certificates


def main():
    y2 = exact_Y(2)
    assert y2 == Fraction(16609872428603, 20652682050)
    assert v2_fraction(y2) == -1

    shifted = []
    for s in range(8, 13):
        N = (1 << s) + 2
        y = exact_Y(N)
        assert v2_fraction(y) == -1
        shifted.append((s, N, v2_fraction(y), 4 * N + 1))

    print("Y(2) =", y2)
    print("v2(Y(2)) =", v2_fraction(y2))
    print("fixed-seed shifted checks:", shifted)

    print("coverage samples:")
    for N in [100, 128, 130, 256, 258, 300, 512, 514, 600, 1024, 1026]:
        print(N, shift_certifies(N))


if __name__ == "__main__":
    main()
