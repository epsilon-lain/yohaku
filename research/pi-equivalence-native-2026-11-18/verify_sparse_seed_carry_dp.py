from math import comb


def v2(n: int) -> int:
    if n == 0:
        return 10**9
    n = abs(n)
    return (n & -n).bit_length() - 1


def carry_count(x: int, y: int) -> int:
    carry = 0
    count = 0
    while x or y or carry:
        total = (x & 1) + (y & 1) + carry
        carry = total >> 1
        count += carry
        x >>= 1
        y >>= 1
    return count


def seed_dp(A: int):
    assert A >= 1 and A & 1
    K = (A - 1) // 2
    bits = max(A.bit_length(), K.bit_length()) + 1

    # state -> maximum carries so far; state=(borrow in K-k, carry in A+k)
    dp = {(0, 0): 0}
    for i in range(bits):
        Ai = (A >> i) & 1
        Ki = (K >> i) & 1
        ndp = {}
        for (borrow, carry), score in dp.items():
            for bit in (0, 1):
                # No bits of k beyond K's top bit.
                if i >= K.bit_length() and bit:
                    continue
                diff = Ki - bit - borrow
                borrow_out = 1 if diff < 0 else 0
                total = Ai + bit + carry
                carry_out = total >> 1
                state = (borrow_out, carry_out)
                candidate = score + carry_out
                ndp[state] = max(ndp.get(state, -1), candidate)
        dp = ndp

    # One more zero bit flushes any carry; require k<=K (no borrow).
    final = dp.get((0, 0), -1)
    gamma = carry_count(A, K)
    assert gamma == v2(comb(A + K, K))
    assert final == max(
        (v2(comb(A + k, k)) for k in range(K + 1)),
        default=0,
    )
    return final, gamma


def brute(A: int):
    K = (A - 1) // 2
    return (
        max(v2(comb(A + k, k)) for k in range(K + 1)),
        v2(comb(A + K, K)),
    )


def main():
    for A in range(1, 1000, 2):
        got = seed_dp(A)
        expected = brute(A)
        assert got == expected, (A, got, expected)

    print("PASS: digit DP agrees with brute force for all odd A < 1000")
    print("sample: A, C_A, gamma_A, minimal u")
    for A in [1, 3, 5, 7, 9, 11, 15, 31, 33, 63, 65, 101, 255, 1023]:
        C, gamma = seed_dp(A)
        print(A, C, gamma, 2*C + 8)


if __name__ == "__main__":
    main()
