"""Exact finite audits of the binary coverage criterion (standard library).

The infinite counting and density statements are proved in the companion note.
This script neither assumes nor asserts the open global BBP valuation formulas.
"""
from collections import Counter, defaultdict
import json
from math import comb
from pathlib import Path


def v2(n):
    assert n > 0
    return (n & -n).bit_length() - 1


def parameters(a):
    assert a >= 1 and a % 2 == 1
    r = a.bit_length()
    cap = 0 if a == 1 else r if 3 * a - 1 >= (1 << (r + 1)) else r - 2
    gamma = 2 * a.bit_count() - (3 * a).bit_count()
    return cap, gamma, cap - gamma


def carry_trace(a):
    r = a.bit_length()
    digits = [(a >> i) & 1 for i in range(r)] + [0]
    carry = 0
    trace = []
    for i in range(r):
        carry = (digits[i] + digits[i + 1] + carry) // 2
        trace.append(carry)
    return trace


def budget_histogram(r):
    assert r >= 1
    if r == 1:
        return {0: 1}
    states = {(1, 0, 0): 1}  # last digit, incoming carry, zero-carry count
    for i in range(1, r):
        new = defaultdict(int)
        for (a, c, zeros), count in states.items():
            for b in ([1] if i == r - 1 else [0, 1]):
                next_carry = (a + b + c) // 2
                new[b, next_carry, zeros + (next_carry == 0)] += count
        states = new
    result = defaultdict(int)
    for (a, c, zeros), count in states.items():
        final_carry = (a + c) // 2  # the appended top digit is zero
        zeros += final_carry == 0
        budget = zeros - 2 * (final_carry == 0)
        assert budget >= 0
        result[budget] += count
    assert sum(result.values()) == 1 << (r - 2)
    return dict(sorted(result.items()))


def main():
    binomial_checks = interval_checks = xor_checks = trace_checks = 0
    for a in range(1, 514, 2):
        cap, gamma, budget = parameters(a)
        old = max(v2(comb(a + k, k)) for k in range((a - 1) // 2 + 1))
        assert cap == old
        binomial_checks += 1
    for a in range(3, 4096, 2):
        cap, gamma, budget = parameters(a)
        endpoint = (3 * a - 1) // 2
        interval = max(v2(t) for t in range(a + 1, endpoint + 1))
        assert interval == cap
        assert cap == (a ^ endpoint).bit_length() - 1
        interval_checks += 1
        xor_checks += 1
    for a in range(1, 1 << 16, 2):
        cap, gamma, budget = parameters(a)
        trace = carry_trace(a)
        assert sum(trace) == gamma
        if a > 1:
            assert budget == trace.count(0) - 2 * (trace[-1] == 0)
            if not trace[-1]:
                assert trace[-2:] == [0, 0]
            word = bin(a)[2:]
            zero_pairs = sum(word[i:i + 2] == '00' for i in range(len(word) - 1))
            assert zero_pairs <= budget + 2
        trace_checks += 1
    for r in range(1, 17):
        direct = Counter(parameters(a)[2] for a in range(1 << (r - 1), 1 << r) if a % 2)
        assert budget_histogram(r) == dict(sorted(direct.items()))

    table = []
    for r in [8, 12, 16, 32, 64, 128]:
        hist = budget_histogram(r)
        table.append({'bits': r, 'budget_at_most_4': sum(v for k, v in hist.items() if k <= 4),
                      'all_odd_with_these_bits': sum(hist.values())})
    hard_family = []
    for v in range(2, 65):
        a, k = (1 << v) + 1, (1 << (v - 1)) - 1
        cap, gamma, budget = parameters(a)
        assert (cap, gamma, budget) == (v - 1, 0, v - 1)
        assert k % 2 == 1 and 1 <= k <= (a - 1) // 2 and v2(a + k) == budget
        hard_family.append({'v': v, 'A': a, 'k': k, 'required_bits': budget})
    result = {
        'status': 'all finite audits passed; infinite theorems are proved in the note',
        'date_asia_shanghai': '2026-11-20',
        'base_commit': '8ba9f9b46802af098bd79897aa8ff5a51d9c08a2',
        'checks': {
            'exact_binomial_maxima_odd_A_1_to_513': binomial_checks,
            'interval_maxima_odd_A_3_to_4095': interval_checks,
            'xor_comparisons': xor_checks,
            'carry_and_budget_traces_odd_A_below_2pow16': trace_checks,
            'histogram_full_bit_lengths_1_through_16': 16,
            'failures': 0,
        },
        'exact_count_table': table,
        'hard_family_samples': hard_family,
        'scope': {
            'density_zero_proof_applies_to': 'original adjacent-order sufficient condition only',
            'not_asserted': ['zero density of the union with all prefix-shift certificates',
                             'failure of any uncovered Y valuation',
                             'global B integrality or mod 8 congruence'],
        },
    }
    path = Path(__file__).with_name('bbp-binary-coverage-verification.json')
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': path.name, 'checks': result['checks'], 'table': table}, ensure_ascii=False))


if __name__ == '__main__':
    main()
