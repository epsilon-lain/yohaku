#!/usr/bin/env python3
"""Independent boundary-encoding oracle; no author module or official actions.

Reference outputs are pointwise sums of interval indicator functions. The
encoded computation is out-of-place sparse impulse aggregation and prefix
integration, rather than the author's in-place right-to-left update loop.
"""
import hashlib
import json
from pathlib import Path
import random


def check(case):
    a, updates = case['a'], case['updates']
    n = len(a)
    expected = [value + sum(v for l, r, v in updates if l <= i <= r)
                for i, value in enumerate(a)]
    initial_derivative = [a[0]] + [a[i]-a[i-1] for i in range(1, n)]
    impulse = {}
    for l, r, v in updates:
        impulse[l] = impulse.get(l, 0) + v
        if r+1 < n:
            impulse[r+1] = impulse.get(r+1, 0) - v
    encoded = [initial_derivative[i] + impulse.get(i, 0) for i in range(n)]
    out, accumulator = [], 0
    for value in encoded:
        accumulator += value
        out.append(accumulator)
    assert out == expected
    direct = sum(r-l+1 for l, r, v in updates)
    q, k = len(updates), sum(r+1 < n for l, r, v in updates)
    cost = 2*(n-1) + q + k
    return {'id': case['id'], 'n': n, 'updates': q, 'interior_right_ends': k,
            'direct_arithmetic': direct, 'encoded_arithmetic': cost,
            'common_scalar_copies_and_outputs': 2*n,
            'expected': expected, 'encoded': out}


def main():
    cases = [
        {'id': 'n1-empty', 'a': [7], 'updates': []},
        {'id': 'n1-signs', 'a': [-7], 'updates': [(0,0,-3),(0,0,0),(0,0,8)]},
        {'id': 'boundary0-interior-last', 'a': [8,-3,0,5,-7],
         'updates': [(0,0,7),(0,4,-2),(4,4,5),(1,3,-11)]},
        {'id': 'empty-many', 'a': [-5,4,-3,2,-1,0], 'updates': []},
        {'id': 'large-full-range', 'a': list(range(-500,500)),
         'updates': [(0,999,1)]*200},
    ]
    rng = random.Random(202611171337)
    for index in range(512):
        n = 1 + index % 12
        a = [rng.randrange(-100,101) for _ in range(n)]
        updates = []
        for _ in range(index % 13):
            l = rng.randrange(n)
            r = rng.randrange(l,n)
            updates.append((l,r,rng.randrange(-37,38)))
        cases.append({'id': 'independent-%03d'%index, 'a': a, 'updates': updates})
    rows = [check(case) for case in cases]
    full_range = []
    for n in (1,2,3,10,1000):
        for q in (0,1,2,3,200):
            direct, encoded = n*q, 2*(n-1)+q
            assert direct-encoded == (n-1)*(q-2)
            assert (direct > encoded) == (n > 1 and q > 2)
            full_range.append({'n':n,'q':q,'direct':direct,'encoded':encoded})
    large = next(row for row in rows if row['id']=='large-full-range')
    assert large['expected'] == list(range(-300,700))
    assert (large['direct_arithmetic'],large['encoded_arithmetic']) == (200000,2198)
    lower = [0,1,0]
    upper = [5,6,5]
    assert [lower[i]-lower[i-1] for i in range(1,3)] == [upper[i]-upper[i-1] for i in range(1,3)]
    assert lower != upper
    input_bytes = json.dumps(cases, sort_keys=True, separators=(',',':')).encode()
    result = {'status':'passed', 'independent_of_author_code':True,
              'official_apply':0, 'synthetic_cases':len(cases),
              'full_range_cost_cases':len(full_range),
              'input_sha256':hashlib.sha256(input_bytes).hexdigest(),
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'boundary_anchor_counterexample':{'a':lower,'b':upper,'internal_differences':[1,-1]},
              'results':rows, 'full_range_costs':full_range}
    out = Path(__file__).with_name('boundary-oracle-results.json')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('status','official_apply','synthetic_cases','full_range_cost_cases','input_sha256')}))


if __name__ == '__main__':
    main()
