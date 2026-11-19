"""Finite BBP valuation follow-up and audits of proved prefix-theorem samples.

Default output is a compact, reproducible JSON certificate beside this script.
Use --full-json PATH to additionally save all 32768 scan rows.  The baseline is
parsed with AST; none of its top-level scan or write operations are executed.
All global valuation/congruence/root observations are finite evidence only.
"""
import argparse
import ast
from array import array
from collections import Counter
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
BASELINE = RESEARCH_DIR / 'sparse-exception-relay/verify_bbp_sparse_relay.py'
OUT = RESEARCH_DIR / 'bbp-global-valuation-verification.json'
MAX_N = 32768
B_BITS = 16
PREFIX_SAMPLES = ((3, 2, 9), (3, 2, 10), (3, 2, 11), (3, 2, 12),
                  (5, 2, 9), (7, 2, 9), (11, 2, 9), (3, 3, 11))


def v2(n):
    n = abs(n)
    if not n:
        return None
    return (n & -n).bit_length()-1


def gamma(n):
    return 2*n.bit_count()-(3*n).bit_count()


def load_baseline_definitions():
    raw = BASELINE.read_bytes()
    tree = ast.parse(raw.decode('utf-8'), filename=str(BASELINE))
    wanted = {'v2', 'denom_bits', 'direct', 'exact_small_Y'}
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    namespace = {'Fraction': Fraction}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BASELINE), 'exec'), namespace)
    return namespace, hashlib.sha256(raw).hexdigest()


def carry_max(odd_a):
    """Max v2(binomial(A+k,k)), 0<=k<=(A-1)//2, by four-state bit DP."""
    assert odd_a > 0 and odd_a % 2
    limit = (odd_a-1)//2
    states = {(0, 0): 0}
    for bit in range(max(odd_a.bit_length(), limit.bit_length())+1):
        ab, lb = (odd_a >> bit) & 1, (limit >> bit) & 1
        choices = (0, 1) if bit < limit.bit_length() else (0,)
        nxt = {}
        for (borrow, carry), score in states.items():
            for kb in choices:
                nb, nc = int(lb-kb-borrow < 0), (ab+kb+carry)//2
                nxt[(nb, nc)] = max(nxt.get((nb, nc), -1), score+nc)
        states = nxt
    return states[(0, 0)]


def scan():
    D = (12*MAX_N+9).bit_length()-1
    R = 2*D+1
    mod, mask = 1 << R, (1 << R)-1
    end = 12*MAX_N+9
    u, ui = array('Q', [1])*(end+1), array('Q', [1])*(end+1)
    for i in range(1, end+1):
        u[i] = u[i-1]*(i >> v2(i)) & mask
    ui[end] = pow(u[end], -1, mod)
    for i in range(end, 0, -1):
        ui[i-1] = ui[i]*(i >> v2(i)) & mask
    a = array('Q', [0, 1, mod-2, 4])
    for i in range(4, 4*MAX_N+9):
        a.append((-2*a[-1]-2*a[-3]+a[-4]) & mask)
    signed = [(-1)**j*comb(8, j) for j in range(8)]
    y = (47*pow(15, -1, mod) << D) & mask
    rows = []
    for n in range(1, MAX_N+1):
        L, K = 8*n, 4*n-3
        delta = 0
        for j in range(12):
            k, m = K+j, L+K+j+1
            exponent = D-1+m.bit_count()-L.bit_count()-k.bit_count()
            assert exponent >= 0
            coefficient = 16*a[k]-sum(signed[ell]*a[k-ell] for ell in range(j-3))
            delta = (delta+(coefficient*u[L]*u[k]*ui[m] << exponent)) & mask
        previous_y = y
        y = (16*y+delta) & mask
        ynu = None if not y else v2(y)-D
        dnu = None if not delta else v2(delta)-D
        pnu = None if not previous_y else v2(previous_y)-D
        g, gn = gamma(n), gamma(n+1)
        bnu = None if ynu is None else 1+gn+ynu
        shift = 1+gn-D
        bmod = None
        if shift >= 0:
            scaled = y << shift
        elif y % (1 << (-shift)) == 0:
            scaled = y >> (-shift)
        else:
            scaled = None
        if scaled is not None:
            m = n+1
            oddbinom = u[3*m]*ui[m]*ui[2*m] & mask
            bmod = scaled*oddbinom & ((1 << B_BITS)-1)
        rows.append({'n': n, 'mod4': n % 4, 'gamma_n': g, 'gamma_next': gn,
                     'nu_Y': ynu, 'nu_B': bnu, 'B_mod65536': bmod,
                     'nu_Y_over_H': None if ynu is None else ynu+g,
                     'nu_delta_over_H': None if dnu is None else dnu+g,
                     'nu_preceding_over_H': None if pnu is None else 4+pnu+g,
                     'scaled_Y_residue_global': y})
    return rows, D, R


def class_summary(rows):
    finite = [row['nu_B'] for row in rows if row['nu_B'] is not None]
    return {'count': len(rows), 'min_nu_B': min(finite), 'max_nu_B': max(finite),
            'unresolved_count': len(rows)-len(finite),
            'valuation_counts': dict(sorted(Counter(finite).items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-json', type=Path, help='also save all 32768 scan rows')
    args = parser.parse_args()
    definitions, baseline_sha256 = load_baseline_definitions()
    direct, exact = definitions['direct'], definitions['exact_small_Y']
    for odd_a in range(1, 256, 2):
        assert carry_max(odd_a) == max(v2(comb(odd_a+k, k))
                                       for k in range((odd_a-1)//2+1))
    rows, D, R = scan()
    by_n = {row['n']: row for row in rows}
    classes = {residue: [row for row in rows if row['mod4'] == residue]
               for residue in range(4)}
    failures = {
        'unresolved_Y': [row['n'] for row in rows if row['nu_Y'] is None],
        'B_integrality': [row['n'] for row in rows
                          if row['nu_B'] is None or row['nu_B'] < 0],
        'B_mod8': [row['n'] for row in rows if row['B_mod65536'] is None
                   or row['B_mod65536'] % 8 != (3*row['n']+6) % 8],
        'odd_companion': [row['n'] for row in rows if row['n'] % 2
                          and row['nu_Y'] != -1-row['gamma_next']],
        'multiple_four_formula': [row['n'] for row in classes[0]
                                  if row['nu_Y'] != -row['gamma_n']],
        'odd_B_unit': [row['n'] for row in rows if row['n'] % 2 and row['nu_B'] != 0],
        'zero_mod4_B_valuation_one': [row['n'] for row in classes[0] if row['nu_B'] != 1],
        'two_mod4_B_valuation_at_least_two': [row['n'] for row in classes[2]
                                            if row['nu_B'] is None or row['nu_B'] < 2],
    }

    roots = []
    for k in range(2, 17):
        modulus = 1 << k
        hits = [row for row in classes[2] if row['nu_B'] is not None and row['nu_B'] >= k]
        residues = sorted({row['n'] % modulus for row in hits})
        expected = [row['n'] for row in classes[2] if row['n'] % modulus in residues]
        roots.append({'k': k, 'modulus': modulus, 'hit_count': len(hits),
                      'observed_residues': residues, 'single_observed_residue': len(residues) == 1,
                      'class_members_in_tested_interval': len(expected),
                      'missed_class_members': sorted(set(expected)-{row['n'] for row in hits})})

    periodicity, isometry = [], []
    for k in range(1, 15):
        step = 1 << k
        failed = []
        for n in range(1, MAX_N-step+1):
            left, right = by_n[n]['B_mod65536'], by_n[n+step]['B_mod65536']
            if left is None or right is None or (right-left) % step:
                failed.append(n)
        periodicity.append({'k': k, 'pairs': MAX_N-step,
                            'failure_count': len(failed), 'first_failures': failed[:10]})
        if k >= 2:
            failed, count = [], 0
            for n in range(2, MAX_N-step+1, 4):
                count += 1
                left, right = by_n[n]['B_mod65536'], by_n[n+step]['B_mod65536']
                difference = None if left is None or right is None else (right-left) % (1 << B_BITS)
                if difference is None or v2(difference) != k:
                    failed.append(n)
            isometry.append({'k': k, 'pairs': count,
                             'failure_count': len(failed), 'first_failures': failed[:10]})

    direct_cache, exact_cache = {}, {}

    def exact_value(n):
        if n not in exact_cache:
            exact_cache[n] = exact(n)
        return exact_cache[n]

    def direct_check(n, check_exact=False):
        row = by_n[n]
        d = (12*n+9).bit_length()-1
        r = 2*d+1
        scan_residue = (row['scaled_Y_residue_global'] >> (D-d)) % (1 << r)
        if n not in direct_cache:
            direct_cache[n] = direct(n)
        independent = direct_cache[n]
        assert scan_residue == independent, (n, scan_residue, independent)
        audit = {'n': n, 'd': d, 'r': r, 'scan_scaled_residue': scan_residue,
                 'direct_scaled_residue': independent, 'residues_match': True,
                 'nu_Y': row['nu_Y'], 'nu_B': row['nu_B'],
                 'B_mod65536': row['B_mod65536']}
        if check_exact:
            q = exact_value(n)
            exact_nu = v2(q.numerator)-v2(q.denominator)
            assert exact_nu == row['nu_Y']
            audit['exact_Fraction_nu_Y'] = exact_nu
        return audit

    exact_B_checks = []
    for n in range(9):
        b = 2*comb(3*(n+1), n+1)*exact_value(n)
        assert b.denominator % 2
        residue = b.numerator*pow(b.denominator, -1, 8) % 8
        assert residue == (3*n+6) % 8
        exact_B_checks.append({'n': n, 'B_numerator': str(b.numerator),
                               'B_denominator': str(b.denominator),
                               'exact_B_mod8': residue, 'predicted_mod8': (3*n+6) % 8})
    odd_checks = [direct_check(n, n <= 128)
                  for n in (3, 7, 11, 15, 27, 515, 531, 547, 579, 32767)]
    branch_checks = [direct_check(n) for n in (110, 4206, 12398, 20590, 28782)]

    prefixes = []
    for A, t, s in PREFIX_SAMPLES:
        c, W = 1 << t, A << s
        n = W+c
        assert n <= MAX_N
        nu_c = by_n[c]['nu_Y']
        d_c = (12*c+9).bit_length()-1
        C_A, gamma_A = carry_max(A), gamma(A)
        base_threshold = max(2, C_A-gamma_A-3)
        threshold = max(2, C_A-gamma_A-3, d_c-1, nu_c+2*d_c-1)
        seed_inequality = nu_c <= 4*c
        u_target, odd_target = v2(n), n >> v2(n)
        C_target, gamma_target = carry_max(odd_target), gamma(odd_target)
        old_base_threshold = max(2, C_target-gamma_target-3)
        leading_s = n.bit_length()-1
        leading_W = 1 << leading_s
        remainder = n-leading_W
        old_geometry = remainder >= 1 and 12*remainder+9 < 4*leading_W
        audit = {'A': A, 't': t, 's': s, 'N': n, 'c': c, 'd_c': d_c,
                 'nu_seed': nu_c, 'seed_condition_nu_c_le_4c': seed_inequality,
                 'C_A': C_A, 'Gamma_A': gamma_A,
                 'combined_s_threshold': threshold, 's_threshold_passes': s >= threshold,
                 'high_base': {'N': W, 'u': s, 'odd_part': A,
                               'criterion_threshold': base_threshold,
                               'criterion_passes': s >= base_threshold,
                               'scan_nu_Y': by_n[W]['nu_Y'], 'expected_nu_Y': -gamma_A},
                 'scan_nu_Y': by_n[n]['nu_Y'], 'predicted_nu_Y': -gamma_A,
                 'direct_check': direct_check(n),
                 'old_target_base_criterion': {'u': u_target, 'odd_part': odd_target,
                                              'C': C_target, 'Gamma': gamma_target,
                                              'required_u': old_base_threshold,
                                              'passes': u_target >= old_base_threshold},
                 'old_positive_seed_shift_geometry': {'leading_s': leading_s,
                                                      'leading_power': leading_W,
                                                      'remainder': remainder,
                                                      'passes': old_geometry}}
        assert A % 2 and t >= 2 and nu_c == 0 and d_c == t+3
        assert seed_inequality and s >= threshold and s >= base_threshold
        assert by_n[W]['nu_Y'] == by_n[n]['nu_Y'] == -gamma_A
        if A == 3 and t == 2:
            assert C_target == s and gamma_target == 2
            assert u_target < old_base_threshold and not old_geometry
            audit['A3_t2_exact_old_C_equals_s'] = True
            audit['A3_t2_exact_old_Gamma_equals_2'] = True
            audit['A3_t2_both_old_criteria_fail'] = True
        prefixes.append(audit)

    result = {
        'format': 'bbp-global-valuation-followup/1',
        'baseline_path': BASELINE.relative_to(RESEARCH_DIR.parent.parent).as_posix(),
        'baseline_sha256': baseline_sha256,
        'range': {'min_n': 1, 'max_n': MAX_N, 'checked': len(rows)},
        'global_D': D, 'global_R': R, 'B_residue_bits': B_BITS,
        'definitions': {'Gamma_n': '2*s2(n)-s2(3*n)',
                        'B_n': '2*binom(3*(n+1),n+1)*Y_n',
                        'H_n': '(8*n)!*(4*n)!/(12*n)!'},
        'finite_evidence_only': True,
        'scope_note': 'Global identities, congruences, root classes and isometry remain finite observations here; prefix samples audit a separately proved theorem.',
        'counts': {'odd_companion_checked': MAX_N//2,
                   'multiple_four_formula_checked': MAX_N//4,
                   'B_integrality_checked': MAX_N, 'B_mod8_checked': MAX_N,
                   'carry_DP_independent_bruteforce_checks': 128},
        'B_mod8_claim': 'B_n = 3*n+6 modulo 8',
        'B_valuation_by_n_mod4': {str(residue): class_summary(group)
                                  for residue, group in classes.items()},
        'failures': failures,
        'finite_single_root_residues': roots,
        'finite_global_periodicity': periodicity,
        'finite_isometry_on_2_mod4': isometry,
        'independent_checks': {'exact_B_0_through_8': exact_B_checks,
                               'odd_companion_direct': odd_checks,
                               'root_branch_direct': branch_checks,
                               'distinct_direct_calls': len(direct_cache),
                               'distinct_exact_Fraction_calls': len(exact_cache)},
        'proved_prefix_theorem_sample_audits': {
            'general_seed_condition': 'nu(c) <= 4*c',
            'general_threshold': 's >= max(2,C_A-Gamma_A-3,d(c)-1,nu(c)+2*d(c)-1)',
            'sample_specialization': 'c=2^t, t>=2, d(c)=t+3, nu(c)=0; target nu(Y_(A*2^s+c))=-Gamma_A',
            'all_samples_within_scan_range': True, 'checked': len(prefixes), 'rows': prefixes},
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    if args.full_json is not None:
        args.full_json.write_text(json.dumps(dict(result, scan_rows=rows), indent=2, sort_keys=True)+'\n')
    print(json.dumps({'checked': len(rows), 'failure_counts': {k: len(v) for k, v in failures.items()},
                      'periodicity_pairs': sum(row['pairs'] for row in periodicity),
                      'periodicity_failures': sum(row['failure_count'] for row in periodicity),
                      'isometry_pairs': sum(row['pairs'] for row in isometry),
                      'isometry_failures': sum(row['failure_count'] for row in isometry),
                      'independent_direct_calls': len(direct_cache),
                      'independent_exact_Fraction_calls': len(exact_cache),
                      'proved_prefix_samples_audited': len(prefixes)}, indent=2))


if __name__ == '__main__':
    main()
