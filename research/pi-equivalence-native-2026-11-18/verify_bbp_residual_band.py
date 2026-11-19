"""Exact finite test of scaled 2-adic values throughout one residual-slope band."""

from fractions import Fraction

FIRST, LAST = 256, 511


def v2(n):
    if not n:
        raise ValueError("zero requires more precision")
    return (n & -n).bit_length() - 1


def finite_band(record=None):
    last_k = 468 * LAST // 100
    last_d = 8 * LAST + 8 + last_k + 1
    shift = last_d.bit_length()
    precision = 64 + shift
    modular = 1 << precision
    mask = modular - 1

    fact = [1]
    for n in range(1, last_d + 1):
        fact.append(fact[-1] * (n >> v2(n)) & mask)
    reciprocal = [pow(unit, -1, modular) for unit in fact]
    coeff = [0]
    for k in range(1, last_k + 1):
        value = int(k == 1) - 2 * coeff[k - 1]
        if k >= 3:
            value -= 2 * coeff[k - 3]
        if k >= 4:
            value += coeff[k - 4]
        coeff.append(value & mask)

    raw = 0
    pairs = 0
    exceptional_count = 0
    max_order = -shift
    extrema = []
    sample_values = {}
    for n in range(LAST + 1):
        # F(n), with its odd denominator made explicit.
        den = (2*n + 1)*(4*n + 3)*(8*n + 1)*(8*n + 5)
        numer = 120*n*n + 151*n + 47
        raw = (16 * raw + numer * pow(den, -1, modular)) & mask
        if n < FIRST:
            continue
        length = 8 * n + 8
        total = (raw << shift) & mask
        start, stop = (307*n + 99)//100, 468*n//100
        for k in range(1, stop + 1):
            d = length + k + 1
            order = d.bit_count() - k.bit_count() - length.bit_count() - 1
            assert -shift <= order <= 0
            unit = fact[length] * fact[k] * reciprocal[d] & mask
            total = (total + ((coeff[k] * unit) << (shift + order))) & mask
            if k < start:
                continue
            ord_y = v2(total) - shift
            assert ord_y < 64
            if record is not None:
                record(n, k, ord_y)
            pairs += 1
            exceptional_count += 8*ord_y > n
            if ord_y > max_order:
                max_order, extrema = ord_y, [(n,k)]
            elif ord_y == max_order:
                extrema.append((n,k))
            if n in (FIRST, FIRST+1, LAST) and k in (start, 4*n, stop):
                sample_values[n,k] = ord_y
    return pairs, exceptional_count, max_order, extrema, sample_values


def direct_samples(samples):
    for n in sorted({n for n, k in samples}):
        raw = sum(Fraction(16**(n-j) * a, 8*j+r)
                  for j in range(n+1) for r,a in ((1,4),(4,-2),(5,-1),(6,-1)))
        length = 8*n + 8
        total = raw
        moment = Fraction(1, length + 1)
        p, q = 0, 1
        for k in range(1, max(k for row,k in samples if row==n) + 1):
            # The Taylor coefficient of odd order 2j-1 is Pell_j squared;
            # even order 2j has coefficient -Pell_j*Pell_{j+1}.
            if k % 2:
                p, q = q, 2*q + p
                coefficient = p*p
            else:
                coefficient = -p*q
            moment *= Fraction(k, length + k + 1)
            total += coefficient * moment
            if (n,k) in samples:
                assert v2(total.numerator)-v2(total.denominator) == samples[n,k]


if __name__ == "__main__":
    pairs, exceptions, highest, locations, samples = finite_band()
    direct_samples(samples)
    print(f"{pairs} parameter pairs in the closed band [3.07,4.68] for 256 <= N <= 511")
    print(f"{exceptions} with v2(16^N X)>N/8; largest valuation {highest} at {locations}")
    print(f"{len(samples)} samples independently reconstructed as full rational numbers")
