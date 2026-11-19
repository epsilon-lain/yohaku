"""Small exact audit of BBP integration by parts and the global parity proof.

Self-contained Python standard library.  The original definition is implemented
directly: the four-term BBP prefix, a's recurrence, and successive Beta ratios.
It is equivalent to the baseline research definition at commit
b8cbc502dd4e7e44bf08832ffab45d22bfb355f0; no baseline top-level code is imported.
Only N=0..24 is checked.  Infinite conclusions require the companion proof.
"""
from collections import Counter
from fractions import Fraction
import json
from math import comb
from pathlib import Path

OUT = Path(__file__).with_name('bbp-global-parity-verification.json')
BASELINE_COMMIT = 'b8cbc502dd4e7e44bf08832ffab45d22bfb355f0'
N_VALUES = tuple(range(25))
BETA_A_VALUES = (1, 3, 5, 7, 9, 11, 13, 17, 21, 33, 65)


def v2_integer(n):
    n = abs(n)
    return None if not n else (n & -n).bit_length()-1


def valuation(q):
    q = Fraction(q)
    return None if not q else v2_integer(q.numerator)-v2_integer(q.denominator)


def divisible(q, bits=0):
    v = valuation(q)
    return v is None or v >= bits


def parity(q):
    q = Fraction(q)
    assert q.denominator % 2, ('not a 2-adic integer', q)
    return q.numerator % 2


def gamma(n):
    return 2*n.bit_count()-(3*n).bit_count()


def fraction_record(q):
    q = Fraction(q)
    return {'numerator': str(q.numerator), 'denominator': str(q.denominator)}


def original_definition(n):
    M, L = 4*n, 8*(n+1)
    a = []
    for k in range(M+1):
        a.append(int(k == 1)
                 -(2*a[k-1] if k >= 1 else 0)
                 -(2*a[k-3] if k >= 3 else 0)
                 +(a[k-4] if k >= 4 else 0))
    prefix = Fraction(0)
    for i in range(n+1):
        f = (Fraction(4, 8*i+1)-Fraction(2, 8*i+4)
             -Fraction(1, 8*i+5)-Fraction(1, 8*i+6))
        prefix = 16*prefix+f
    beta = Fraction(1, L+1)
    kernel = Fraction(0)
    for k, coefficient in enumerate(a):
        kernel += coefficient*beta
        beta *= Fraction(k+1, L+k+2)
    return a, prefix, kernel


def check_n(n):
    m, R, L = n+1, 4*n+1, 8*(n+1)
    u = v2_integer(m)
    A, h = m >> u, u+3
    w, C = (A-1)//2, comb(3*m, m)
    a, prefix, kernel = original_definition(n)
    Y = prefix+kernel
    B = 2*C*Y
    g = [Fraction(2*a[r-1], r) for r in range(1, R+1)]
    assert all(divisible(x) for x in g)
    S = [sum((comb(r, J)*g[r-1] for r in range(max(1, J), R+1)), Fraction(0))
         for J in range(R+1)]
    by_parts = C*L*sum((Fraction((-1)**J, L+J)*S[J] for J in range(R+1)), Fraction(0))
    assert by_parts == 2*C*kernel
    assert divisible(2*C*prefix, 1)
    assert parity(S[0]) == (m-1) % 2
    assert v2_integer(C) == gamma(m) == gamma(A)
    assert R // (1 << h) == w

    low_count = 0
    high_rows = []
    for J in range(1, R+1):
        term = Fraction(C*L*((-1)**J), L+J)*S[J]
        if v2_integer(J) < h:
            assert divisible(term, 1)
            low_count += 1
            continue
        k = J >> h
        assert 1 <= k <= w
        choose_R_J, choose_w_k = comb(R, J), comb(w, k)
        sigma = v2_integer(choose_w_k)
        assert v2_integer(choose_R_J) == sigma
        T = S[J]/choose_R_J
        assert divisible(T)
        assert parity(T) == m % 2 ^ 1
        Dk = Fraction(C*A*choose_R_J, A+k)
        Ek = Fraction(C*A*choose_w_k, A+k)
        assert divisible(Dk) and divisible(Ek)
        assert valuation(Dk) == valuation(Ek) == gamma(A)+sigma-v2_integer(A+k)
        assert term == Dk*T
        if m % 2:
            assert divisible(term, 1)
        else:
            assert parity(term) == parity(Ek)
        high_rows.append({'J': J, 'k': k, 'k_parity': k % 2, 'sigma': sigma,
                          'T_valuation': valuation(T), 'T_parity': parity(T),
                          'Dk_valuation': valuation(Dk), 'Ek_valuation': valuation(Ek),
                          'contribution_parity': parity(term)})

    signed = sum((Fraction(C*A*((-1)**k)*comb(w, k), A+k)
                  for k in range(w+1)), Fraction(0))
    expected_signed = Fraction(C, comb(A+w, w))
    assert signed == expected_signed and valuation(signed) == 0
    assert divisible(B) and parity(B) == n % 2
    row = {'N': n, 'm': m, 'A': A, 'u': u, 'R': R, 'L': L, 'w': w,
           'Gamma_m': gamma(m), 'by_parts_difference': fraction_record(by_parts-2*C*kernel),
           'B': fraction_record(B), 'B_parity': parity(B), 'nu_B': valuation(B),
           'nu_Y': valuation(Y), 'S0_parity': parity(S[0]),
           'low_positive_J_even_count': low_count, 'high_positive_J_checks': high_rows,
           'normalized_signed_beta_valuation': valuation(signed)}
    if n % 2:
        assert valuation(Y) == -1-gamma(m)
        X = Y/Fraction(16**n)
        q_valuation = v2_integer(X.denominator)
        assert q_valuation == 4*n+1+gamma(m)
        row['odd_formula_expected_nu_Y'] = -1-gamma(m)
        row['reduced_X_denominator_v2'] = q_valuation
        row['odd_formula_expected_denominator_v2'] = 4*n+1+gamma(m)
    return row


def check_beta(A):
    w = (A-1)//2
    signed = sum((Fraction(A*((-1)**k)*comb(w, k), A+k)
                  for k in range(w+1)), Fraction(0))
    denominator = comb(A+w, w)
    assert signed == Fraction(1, denominator)
    assert v2_integer(denominator) == gamma(A)
    assert w.bit_count() == A.bit_count()-1
    assert (A+w).bit_count() == (3*A).bit_count()-1
    scalings = []
    for u in range(4):
        m = A << u
        C = comb(3*m, m)
        assert v2_integer(C) == gamma(A)
        assert valuation(Fraction(C, denominator)) == 0
        scalings.append({'u': u, 'Gamma_m': v2_integer(C), 'ratio_valuation': 0})
    return {'A': A, 'w': w, 'Gamma_A': gamma(A),
            'exact_signed_beta_sum': fraction_record(signed),
            'gamma_scaling_checks': scalings}


def main():
    rows = [check_n(n) for n in N_VALUES]
    beta_rows = [check_beta(A) for A in BETA_A_VALUES]
    k_counts = Counter(row['k_parity'] for nrow in rows for row in nrow['high_positive_J_checks'])
    result = {'format': 'bbp-global-parity-exact-audit/1',
              'date_Asia_Shanghai': '2026-11-20', 'baseline_commit': BASELINE_COMMIT,
              'finite_verification_only': True,
              'scope': 'Exact finite identities and edge cases only; infinite conclusions require the companion proofs.',
              'original_definition': {
                  'coefficient_recurrence': 'a_k=[k=1]-2*a_(k-1)-2*a_(k-3)+a_(k-4), negative indices zero',
                  'prefix': 'sum_i=0..N 16^(N-i)*(4/(8i+1)-2/(8i+4)-1/(8i+5)-1/(8i+6))',
                  'kernel': 'sum_k=0..4N a_k*(8N+8)!*k!/(8N+k+9)!'},
              'N_min': min(N_VALUES), 'N_max': max(N_VALUES), 'N_checked': len(rows),
              'positive_high_J_even_k_checks': k_counts[0],
              'positive_high_J_odd_k_checks': k_counts[1],
              'low_positive_J_even_checks': sum(row['low_positive_J_even_count'] for row in rows),
              'odd_N_exact_denominator_checks': sum(n % 2 for n in N_VALUES),
              'signed_beta_checks': len(beta_rows), 'failures': [],
              'rows': rows, 'signed_beta_rows': beta_rows}
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key: result[key] for key in
                      ('N_min', 'N_max', 'N_checked', 'positive_high_J_even_k_checks',
                       'positive_high_J_odd_k_checks', 'low_positive_J_even_checks',
                       'odd_N_exact_denominator_checks', 'signed_beta_checks', 'failures')}, indent=2))


if __name__ == '__main__':
    main()
