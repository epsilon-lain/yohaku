from fractions import Fraction


def v2_int(n: int) -> int:
    if n == 0:
        raise ValueError("v2(0) is infinite")
    n = abs(n)
    return (n & -n).bit_length() - 1


def v2_fraction(x: Fraction) -> int:
    return v2_int(x.numerator) - v2_int(x.denominator)


def kernel_coefficients(M: int):
    a = [0] * (M + 1)
    for k in range(M + 1):
        a[k] = (
            (1 if k == 1 else 0)
            - (2 * a[k - 1] if k >= 1 else 0)
            - (2 * a[k - 3] if k >= 3 else 0)
            + (a[k - 4] if k >= 4 else 0)
        )
    return a


def exact_Y(N: int) -> Fraction:
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


def main():
    seed = exact_Y(1)
    assert seed == Fraction(14774523, 293930)
    assert v2_fraction(seed) == -1

    checked = []
    for s in range(6, 11):
        N = 2**s + 1
        y = exact_Y(N)
        nu = v2_fraction(y)
        assert nu == -1
        checked.append({"s": s, "N": N, "v2Y": nu, "v2Q": 4 * N - nu})

    print("Y(1) =", seed)
    print("v2(Y(1)) =", v2_fraction(seed))
    print("shifted checks =", checked)
    print("PASS: exact rational seed and finite shifted regression")


if __name__ == "__main__":
    main()
