"""Integer and Fraction checks for the dyadic block bound on one Taylor order."""

from fractions import Fraction
from math import comb


def val(n):
    if not n:
        raise ValueError("valuation of zero")
    return (abs(n) & -abs(n)).bit_length() - 1


def odd(n):
    return n >> val(n)


def carries(a, b):
    return a.bit_count() + b.bit_count() - (a + b).bit_count()


def certificate(n, m):
    length = 8 * (n + 1)
    h = val(length)
    a = length >> h
    max_c = max(carries(a, b) for b in range(((m + 4) >> h) + 1))
    last_c = carries(a, (m + 1) >> h)
    vq = val((m + 3) // 4)
    native_c = max(carries(a, b) for b in range(((m + 1) >> h) + 1))
    baseline = vq + native_c - last_c < h - 2
    new = h >= 2 * max_c + 11 and vq <= h - 3
    return baseline, new, vq - last_c


def raw_mod(n, mod, bits):
    """16^N S_N modulo a power of 2 using the odd-denominator partial fractions."""
    answer = 0
    for j in range(min(n, bits // 4) + 1):
        k = n - j
        value = (4 * pow(8*k + 1, -1, mod) - pow(8*k + 5, -1, mod)
                 - (3*k + 2) * pow((2*k + 1)*(4*k + 3), -1, mod))
        answer += (1 << (4*j)) * value
    return answer % mod


def stream(n, targets, bits=45):
    """Accumulate 2^C * 2Y. Recur only odd units and discard no significant bits."""
    length = 8 * (n + 1)
    last = max(targets)
    # The largest carry count is < bit_length(L+M+1).
    scale = (length + last + 1).bit_length()
    modulus = 1 << (bits + scale)
    # Extra bits cover division of 2*a_k by the power of 2 in k+1.
    coeff_modulus = modulus << (last + 2).bit_length()
    accum = raw_mod(n, modulus, bits + scale) << (scale + 1)
    coeffs = [0, 0, 0, 0]
    unit = 1
    count = 0
    result = {}
    for k in range(last + 1):
        a_k = (int(k == 1) - 2*coeffs[-1] - 2*coeffs[-3] + coeffs[-4]) % coeff_modulus
        coeffs = [*coeffs[1:], a_k]
        i = k + 1
        vi, vl = val(i), val(length+i)
        count += vl - vi
        assert 0 <= count <= scale
        unit = unit * (i >> vi) * pow((length+i) >> vl, -1, modulus) % modulus
        doubled = 2 * a_k
        assert doubled % (1 << vi) == 0
        g = (doubled >> vi) * pow(i >> vi, -1, modulus)
        accum = (accum + ((g * unit) << (scale-count))) % modulus
        if k in targets:
            assert accum
            result[k] = val(accum) - scale
    return result


def raw_fraction(n):
    return sum(Fraction(w * 16**(n-k), 8*k + r) for k in range(n+1)
               for r, w in ((1,4), (4,-2), (5,-1), (6,-1)))


def reference(n, ms):
    """Independent coefficient and rational-integral construction."""
    m_max = max(ms)
    pell = [0, 1]
    while len(pell) <= (m_max+1)//2 + 1:
        pell.append(2*pell[-1]+pell[-2])
    y = raw_fraction(n)
    out = {}
    length = 8*(n+1)
    for k in range(m_max+1):
        a = pell[(k+1)//2]**2 if k % 2 else -pell[k//2]*pell[k//2+1]
        y += Fraction(a, (length+k+1)*comb(length+k,k))
        if k in ms:
            two_y = 2*y
            out[k] = val(two_y.numerator)-val(two_y.denominator)
    return out


def main():
    small = 0
    for n in range(32):
        ms = set(range(1, 3*n+29))
        direct = reference(n, ms)
        assert direct == stream(n, ms)
        for m, v in direct.items():
            old, new, expected = certificate(n, m)
            if old or new:
                assert v == expected
        small += len(ms)

    large = strict_new = 0
    new_rows = []
    for a, s in ((3, 12), (5, 10), (9, 12), (17, 14)):
        n = a * (1 << s) - 1
        # The four resonant orders of the argument at t=4, and ordinary neighbors.
        ms = {4*n+d for d in range(-7, 9)}
        ms.update({m for j in (1,3,5,7) for m in (j*(1<<s), j*(1<<s)+1)})
        vals = stream(n, ms)
        for m, actual in sorted(vals.items()):
            old, new, expected = certificate(n, m)
            if new:
                assert expected == actual
                large += 1
                if not old:
                    strict_new += 1
                    if 4*n+1 <= m <= 4*n+4:
                        new_rows.append((a,s,m-4*n,actual))
    boundary = 0
    unresolved_pairs = 0
    for a, s in ((3, 8), (5, 9), (9, 10), (17, 10)):
        n = a * (1 << s) - 1
        h = s + 3
        bs = range(1, 8)
        ms = {(b << h) + j for b in bs for j in (-3, -2, -1, 0)}
        vals = stream(n, ms)
        for b in bs:
            center = b << h
            u = h - 2 + val(b) - carries(a, b-1)
            v = h - 1 + val(b) - carries(a, b)
            assert all(vals[center+j] == u for j in (-3,-2))
            boundary += 2
            if u != v:
                assert all(vals[center+j] == min(u,v) for j in (-1,0))
                boundary += 2
            else:
                assert (b-a) % 4 == 0 and min(vals[center-1], vals[center]) <= v + 1
                unresolved_pairs += 1
    print(f"{boundary} exact boundary comparisons; {unresolved_pairs} tied-pair controls")
    assert strict_new >= 12
    assert len(new_rows) == 12
    print(f"{small} independent direct fractions; {large} theorem checks at large indices")
    print(f"{strict_new} outside the prior sufficient condition")
    print(f"new cases at slope 4 (odd core,s,M-4N,v2(2Y)): {new_rows}")


if __name__ == "__main__":
    main()
