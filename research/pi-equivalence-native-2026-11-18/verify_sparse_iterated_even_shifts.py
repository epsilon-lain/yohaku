from fractions import Fraction


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


def shift_threshold(c, nu):
    d = (12 * c + 9).bit_length() - 1
    assert nu < 4 * c - 3
    return max(2, d - 1, nu + 2 * d - 1)


def main():
    y2 = exact_Y(2)
    assert y2 == Fraction(16609872428603, 20652682050)
    nu2 = v2_fraction(y2)
    assert nu2 == -1
    s2 = shift_threshold(2, nu2)
    assert s2 == 8

    y110 = exact_Y(110)
    nu110 = v2_fraction(y110)
    assert nu110 == 4
    s110 = shift_threshold(110, nu110)
    assert s110 == 23

    # Check the second-level shift condition symbolically for sample u.
    nested = []
    for u in range(8, 15):
        c = 2**u + 2
        d = (12 * c + 9).bit_length() - 1
        threshold = shift_threshold(c, -1)
        assert threshold == 2 * u + 4
        nested.append((u, c, d, threshold))

    print("seed c=2: Y =", y2, "v2 =", nu2, "shift >=", s2)
    print("seed c=110: v2 =", nu110, "shift >=", s110)
    print("nested shifts (u,c,d,s_min):", nested)
    print("PASS: exact seed values and shift thresholds")


if __name__ == "__main__":
    main()
