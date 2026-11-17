#!/usr/bin/env python3
"""Analytic aggregate counts and final-artifact comparison; no author imports."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    source = HERE.parent/'boundary_encoding/checks.json'
    report = json.loads(source.read_text())
    by_n = []
    for n in range(1,5):
        # A signed interval alphabet; count aggregate costs combinatorially,
        # without rerunning any of the author's 38748 full-array cases.
        alphabet = n*(n+1)
        sequence_count = 1+alphabet+alphabet**2
        array_count = 3**n
        sum_interval_lengths = n*(n+1)*(n+2)//3
        direct = array_count*sum_interval_lengths*(1+2*alphabet)
        encoded = array_count*(2*(n-1)*sequence_count+2*n*n*(1+2*alphabet))
        ties = 21 if n==1 else 4*array_count
        by_n.append({'n':n,'cases':array_count*sequence_count,
                     'direct_arithmetic':direct,'encoded_arithmetic':encoded,'ties':ties})
    totals = {'cases':sum(r['cases'] for r in by_n),
              'direct_arithmetic':sum(r['direct_arithmetic'] for r in by_n),
              'encoded_arithmetic':sum(r['encoded_arithmetic'] for r in by_n),
              'strict_saving':0,'ties':sum(r['ties'] for r in by_n)}
    totals['strict_loss'] = totals['cases']-totals['ties']
    ex = report['exhaustive']
    assert totals['cases']==ex['cases']==38748
    assert totals['ties']==ex['outcomes']['tie']==489
    assert totals['strict_loss']==ex['outcomes']['strict_loss']==38259
    assert totals['strict_saving']==ex['outcomes']['strict_saving']
    assert totals['direct_arithmetic']==ex['aggregate_data_arithmetic']['elementwise']==147306
    assert totals['encoded_arithmetic']==ex['aggregate_data_arithmetic']['boundary_encoded']==341724
    named = {row['name']:row for row in report['named_cases']}
    examples = []
    for name,n,updates,expected,direct,encoded in [
        ('large_full_range_saving',1000,[(0,999,1)]*200,list(range(-300,700)),200000,2198),
        ('large_point_updates_loss',1000,[(500,500,1)]*200,[i-500+(200 if i==500 else 0) for i in range(1000)],200,2398),
        ('distinct_suffix_saving',100,[(j,99,1) for j in range(100)],[2*i-49 for i in range(100)],5050,298)]:
        a=[i-(500 if n==1000 else 50) for i in range(n)]
        actual=[value+sum(v for l,r,v in updates if l<=i<=r) for i,value in enumerate(a)]
        assert actual==expected
        output_hash=hashlib.sha256(json.dumps(actual,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        row=named[name]
        assert row['output_sha256']==output_hash
        assert row['elementwise']['data_arithmetic_total']==direct
        assert row['boundary_encoded']['data_arithmetic_total']==encoded
        assert row['elementwise']['arithmetic_plus_copies_total']==direct+2*n
        assert row['boundary_encoded']['arithmetic_plus_copies_total']==encoded+2*n
        examples.append({'name':name,'output_sha256':output_hash,'direct':direct,'encoded':encoded,
                         'with_common_copies':[direct+2*n,encoded+2*n]})
    result={'status':'passed','official_apply':0,'author_code_imported':False,
            'scope':'Analytic enumeration ledger check plus independently evaluated three named final outputs; not rerun of author checker.',
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'aggregate_counts':totals,'by_n':by_n,'named_outputs':examples}
    (HERE/'boundary-author-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'aggregate_counts':totals,'named_examples':len(examples)}))


if __name__=='__main__':
    main()
