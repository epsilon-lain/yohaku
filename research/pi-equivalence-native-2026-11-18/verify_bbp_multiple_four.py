"""Targeted finite check; loads only definitions from the baseline via AST.

No top-level code from the baseline is imported or executed.  The scan uses its
factorial-unit / 12-term-delta construction.  Independent checks use the
baseline's direct Pell / Beta-ratio function and exact rationals when small.
"""
import argparse
import ast
from array import array
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path
import time

RESEARCH_DIR = Path(__file__).resolve().parent
BASELINE = RESEARCH_DIR / 'sparse-exception-relay/verify_bbp_sparse_relay.py'
OUT = RESEARCH_DIR / 'bbp-multiple-four-verification.json'
MAX_N = 32768


def load_baseline_definitions():
    source = BASELINE.read_text()
    tree = ast.parse(source, filename=str(BASELINE))
    wanted = {'v2', 'denom_bits', 'exact_small_Y', 'direct'}
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    module = ast.Module(body=nodes, type_ignores=[])
    namespace = {'Fraction': Fraction}
    exec(compile(module, str(BASELINE), 'exec'), namespace)
    return namespace, hashlib.sha256(source.encode()).hexdigest()


def carry_max(odd_a):
    """Maximum carries in A+k for 0 <= k <= (A-1)//2; four-state DP."""
    limit = (odd_a - 1) // 2
    states = {(0, 0): 0}  # (borrow in limit-k, carry in A+k): best score
    for bit in range(max(odd_a.bit_length(), limit.bit_length()) + 1):
        a_bit = (odd_a >> bit) & 1
        limit_bit = (limit >> bit) & 1
        choices = (0, 1) if bit < limit.bit_length() else (0,)
        nxt = {}
        for (borrow, carry), score in states.items():
            for k_bit in choices:
                new_borrow = int(limit_bit - k_bit - borrow < 0)
                new_carry = (a_bit + k_bit + carry) // 2
                key = new_borrow, new_carry
                nxt[key] = max(nxt.get(key, -1), score + new_carry)
        states = nxt
    return states[(0, 0)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-json', type=Path,
                        help='also write a full record containing all 8192 rows')
    args = parser.parse_args()
    start = time.monotonic()
    defs, baseline_sha256 = load_baseline_definitions()
    v2, denom_bits = defs['v2'], defs['denom_bits']
    direct, exact = defs['direct'], defs['exact_small_Y']

    # A bounded independent check of the tiny carry DP, kept outside the DP.
    for a in range(1, 256, 2):
        assert carry_max(a) == max(v2(comb(a+k, k)) for k in range((a-1)//2 + 1))

    D = denom_bits(MAX_N)
    R = 2 * D + 1
    mod, mask = 1 << R, (1 << R) - 1
    end = 12 * MAX_N + 9
    units = array('Q', [1]) * (end + 1)
    inverses = array('Q', [1]) * (end + 1)
    for i in range(1, end + 1):
        units[i] = units[i-1] * (i >> v2(i)) & mask
    inverses[end] = pow(units[end], -1, mod)
    for i in range(end, 0, -1):
        inverses[i-1] = inverses[i] * (i >> v2(i)) & mask
    coefficients = array('Q', [0, 1, mod-2, 4])
    for i in range(4, 4 * MAX_N + 9):
        coefficients.append((-2*coefficients[-1]-2*coefficients[-3]+coefficients[-4]) & mask)
    signed = [(-1)**j * comb(8, j) for j in range(8)]
    y = (47 * pow(15, -1, mod) << D) & mask
    rows, failures = [], []
    carries_cache = {}
    for n in range(1, MAX_N + 1):
        L, K = 8*n, 4*n-3
        delta = 0
        for j in range(12):
            k, m = K+j, L+K+j+1
            valuation = D-1+m.bit_count()-L.bit_count()-k.bit_count()
            coefficient = 16*coefficients[k] - sum(signed[l]*coefficients[k-l] for l in range(j-3))
            assert valuation >= 0
            delta = (delta + ((coefficient*units[L]*units[k]*inverses[m]) << valuation)) & mask
        y = (16*y + delta) & mask
        if n % 4:
            continue
        d = denom_bits(n)
        r = 2*d+1
        assert y % (1 << (D-d)) == 0
        residue = (y >> (D-d)) % (1 << r)
        observed = None if not residue else v2(residue)-d
        predicted = (3*n).bit_count() - 2*n.bit_count()
        u = v2(n)
        a = n >> u
        if a not in carries_cache:
            carries_cache[a] = carry_max(a)
        C = carries_cache[a]
        gamma = 2*a.bit_count() - (3*a).bit_count()
        threshold = max(2, C-gamma-3)
        row = {'N': n, 'u': u, 'A': a, 'C_A': C, 'Gamma_A': gamma,
               'threshold': threshold, 'criterion_holds': u >= threshold,
               'observed_v2': observed, 'predicted_v2': predicted,
               'd': d, 'r': r, 'residue': residue}
        rows.append(row)
        if observed != predicted:
            failures.append(row)

    # Every failure is checked through the baseline's independent direct method.
    # Fixed sample checks also ensure that an empty-failure scan is audited.
    samples = {4, 8, 12, 16, 20, 28, 32, 60, 64, 84, 124, 128, 252, 256,
               1024, 4096, 8192, 16384, MAX_N}
    outside = [row for row in rows if not row['criterion_holds']]
    samples.update(row['N'] for row in outside[:4])
    samples.update(row['N'] for row in failures)
    by_n = {row['N']: row for row in rows}
    independently_checked = []
    for n in sorted(samples):
        row = by_n[n]
        independent_residue = direct(n)
        assert independent_residue == row['residue'], (n, independent_residue, row)
        audit = {'N': n, 'd': row['d'], 'r': row['r'],
                 'scan_residue': row['residue'],
                 'direct_residue': independent_residue,
                 'direct_residue_match': True,
                 'observed_v2': row['observed_v2'],
                 'predicted_v2': row['predicted_v2']}
        if n <= 128:
            rational = exact(n)
            rational_val = v2(abs(rational.numerator)) - v2(rational.denominator)
            assert rational_val == row['observed_v2'], (n, rational_val, row)
            audit['exact_fraction_v2'] = rational_val
        independently_checked.append(audit)
    result = {'format': 'bbp-multiple-four-finite-check/1',
              'baseline_path': BASELINE.relative_to(RESEARCH_DIR.parent.parent).as_posix(),
              'baseline_sha256': baseline_sha256,
              'min_N': 4, 'max_N': MAX_N, 'step': 4, 'checked': len(rows),
              'global_D': D, 'global_R': R,
              'claim': 'v2(Y(N)) = s2(3N) - 2*s2(N), for checked multiples of four only',
              'finite_evidence_only': True,
              'criterion': 'u >= max(2, C_A - Gamma_A - 3), N=A*2^u, A odd',
              'inside_criterion_count': len(rows)-len(outside),
              'outside_criterion_count': len(outside),
              'outside_criterion_first_20': outside[:20],
              'failures': failures,
              'inside_criterion_failures': [row for row in failures if row['criterion_holds']],
              'independent_direct_check_count': len(independently_checked),
              'exact_fraction_check_count': sum('exact_fraction_v2' in row
                                                for row in independently_checked),
              'independent_checks': independently_checked}
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    if args.full_json is not None:
        full = dict(result, rows=rows)
        args.full_json.write_text(json.dumps(full, indent=2, sort_keys=True) + '\n')
    printed = {key: result[key] for key in
               ('checked', 'max_N', 'inside_criterion_count',
                'outside_criterion_count', 'failures',
                'inside_criterion_failures', 'independent_direct_check_count',
                'exact_fraction_check_count')}
    printed['elapsed_seconds'] = round(time.monotonic()-start, 3)
    print(json.dumps(printed, indent=2))


if __name__ == '__main__':
    main()
