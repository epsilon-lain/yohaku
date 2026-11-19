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


def exact_seed(c):
    M = 4 * c
    L = 8 * c + 8
    a = kernel_coefficients(M)

    bbp = Fraction(0)
    for i in range(c + 1):
        bbp += 16 ** (c - i) * (
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


def main():
    rows = []
    for u in range(8, 13):
        c = 2**u - 1
        y = exact_seed(c)
        nu = v2_fraction(y)
        assert nu == -1
        d = (12 * c + 9).bit_length() - 1
        assert d == u + 3
        s_min = max(2, d - 1, nu + 2 * d - 1)
        assert s_min == 2 * u + 4
        rows.append({
            "u": u, "c": c, "Y_num_bits": y.numerator.bit_length(),
            "Y_den_bits": y.denominator.bit_length(), "v2Y": nu,
            "d_c": d, "minimum_shift_s": s_min
        })
    print(rows)
    print("PASS: direct Fraction seed values and exact shift thresholds")


if __name__ == "__main__":
    main()
