from math import comb


def v2(n: int) -> int:
    if n == 0:
        return 10**9
    n = abs(n)
    return (n & -n).bit_length() - 1


def seed_constants(A: int):
    assert A >= 1 and A % 2 == 1
    kmax = (A - 1) // 2
    vals = [v2(comb(A + k, k)) for k in range(kmax + 1)]
    C_A = max(vals)
    gamma_A = vals[-1]
    return C_A, gamma_A


def main():
    rows = []
    for A in [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 25, 31, 33, 63, 65, 101]:
        C_A, gamma_A = seed_constants(A)
        u_exact = max(1, 2 * C_A + 8)
        u_coarse = 2 * ((3 * A).bit_length() - 2) + 10
        g_A = (12 * A).bit_length() - 1
        rows.append({
            "A": A,
            "C_A": C_A,
            "gamma_A": gamma_A,
            "u_min_exact": u_exact,
            "u_min_coarse": u_coarse,
            "g_A": g_A,
        })
        assert u_coarse >= u_exact

    print("A | C_A | gamma_A | u_min_exact | u_min_coarse | g_A")
    for r in rows:
        print(
            r["A"], r["C_A"], r["gamma_A"],
            r["u_min_exact"], r["u_min_coarse"], r["g_A"], sep=" | "
        )
    print("PASS: exact finite Kummer-carry constants and coarse u bounds")


if __name__ == "__main__":
    main()
