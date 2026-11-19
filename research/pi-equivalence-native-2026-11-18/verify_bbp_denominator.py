"""Exact finite checks of the BBP denominator arguments; standard library."""
from fractions import Fraction as Q
from math import isqrt


def valuation2(n):
    assert n != 0
    n = abs(n)
    return (n & -n).bit_length() - 1


def bbp_term(k):
    return Q(4, 8*k+1) - Q(2, 8*k+4) - Q(1, 8*k+5) - Q(1, 8*k+6)


def primes_through(limit):
    prime = bytearray(b"\x01") * (limit+1)
    prime[:2] = b"\x00\x00"
    for p in range(2, isqrt(limit)+1):
        if prime[p]:
            prime[p*p::p] = b"\x00" * (1+(limit-p*p)//p)
    return [p for p in range(3, limit+1) if prime[p]]


def rational_mod(x, p):
    return x.numerator * pow(x.denominator, -1, p) % p


def predicted_residue(p, weights):
    # Without the weights, the coefficients are the signed table in the proof.
    if p % 4 == 1:
        pattern = {1: Q(4), 4: Q(-2), 5: Q(-1), 6: Q(-1)}
    else:
        pattern = {2: Q(-4), 3: Q(-2), 4: Q(-2), 7: Q(1, 2)}
    end = len(weights)-1
    residue = Q(0)
    for multiple in range(1, (8*end+6)//p+1):
        block, offset = divmod(multiple, 8)
        if offset not in pattern:
            continue
        index = multiple*p//8
        if index <= end:
            residue += weights[index]*pattern[offset]/(multiple*16**block)
    return residue


def compare_prime_profile(value, weights, primes, grid):
    end = len(weights)-1
    checks = surviving = 0
    for p in primes:
        if p > 8*end+6:
            break
        if p*p <= 8*end+6 or grid % p == 0:
            continue
        expected = predicted_residue(p, weights)
        present = (p <= 8*end+5 if p % 4 == 1 else p <= 4*end+3)
        if present:
            assert (expected > 0 if p % 4 == 1 else expected < 0)
        else:
            assert expected == 0
        actual_mod = rational_mod(p*value, p)
        assert actual_mod == rational_mod(expected, p)
        if actual_mod:
            assert value.denominator % p == 0 and value.denominator % (p*p) != 0
            surviving += 1
        checks += 1
    return checks, surviving


def check():
    primes = primes_through(8*256+6)
    value = Q(0)
    pairs = survivors = 0
    for end in range(257):
        value += bbp_term(end) / 16**end
        assert valuation2(value.numerator)-valuation2(value.denominator) == valuation2(end+1)-4*end
        if end and end % 8 == 0:
            rows, kept = compare_prime_profile(value, [Q(1)]*(end+1), primes, 1)
            pairs += rows
            survivors += kept
    for end in (24, 63, 96, 128, 255):
        for grid in (3, 5, 8):
            weights = [Q(max(1, grid-(grid*k)//(end+1)), grid) for k in range(end+1)]
            value = sum(weight*bbp_term(k)/16**k for k, weight in enumerate(weights))
            rows, kept = compare_prime_profile(value, weights, primes, grid)
            pairs += rows
            survivors += kept
    for end in (40, 119, 200):
        weights = [Q(1 + (k*k + 3*k + 1) % 4, 4) for k in range(end+1)]
        value = sum(weight*bbp_term(k)/16**k for k, weight in enumerate(weights))
        rows, kept = compare_prime_profile(value, weights, primes, 4)
        pairs += rows
        survivors += kept
    print("257 exact dyadic valuations verified.")
    print(f"{pairs} odd-prime residue comparisons, {survivors} nonzero residues.")

    # A direct truncation of the backward 2-adic sum checks the root identity
    # modulo 2^(4·terms). The exact proof is in the note.
    backward = Q(0)
    for terms in range(1, 65):
        backward += 16**(terms-1)*bbp_term(-terms)
        assert valuation2(backward.numerator)-valuation2(backward.denominator) >= 4*terms
    print("64 exact congruences for the backward sum verified.")


if __name__ == "__main__":
    check()
