"""Certify a bounded-denominator minimum from the supplied pi enclosure.
Standard library only; imports baseline enclosure helpers, so this is a
mathematical strengthening, not a new independent computation of pi.
"""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys
import time
from fractions import Fraction
sys.set_int_max_str_digits(0)
sys.dont_write_bytecode = True
start = time.monotonic()
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('baseline', root / 'common/check_runB_independent.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
g = (1, 0)
for real, imag, exponent in [(18, 1, 12), (57, 1, 8), (239, -1, 5)]:
    for _ in range(exponent):
        g = b.multiply(g, (real, imag))
assert g[0] == g[1] and g[0] > 0
assert 12*Fraction(18, 325)-5*Fraction(1, 239) > 0
assert 12*Fraction(1, 18)+8*Fraction(1, 57) < 1
scale = 10**30000
intervals = {x: b.inverse_atan_bounds(x, scale) for x in (18, 57, 239)}
lo = 48*intervals[18][0]+32*intervals[57][0]-20*intervals[239][1]
hi = 48*intervals[18][1]+32*intervals[57][1]-20*intervals[239][0]
assert 3*scale < lo < hi < 4*scale
ln, ld, rn, rd = lo, scale, hi, scale
pm2, pm1, qm2, qm1 = 0, 1, 1, 0
terms = []
for n in range(28422):
    a = ln // ld
    assert a == rn // rd
    assert n == 0 or a >= 1
    terms.append(a)
    p, q = a*pm1+pm2, a*qm1+qm2
    assert p*qm1-pm1*q == (-1 if n % 2 == 0 else 1)
    if n == 28420:
        pt, qt = p, q
    if n == 28421:
        qnext = q
    pm2, pm1, qm2, qm1 = pm1, p, qm1, q
    lrem, rrem = ln-a*ld, rn-a*rd
    assert lrem > 0 and rrem > 0
    ln, ld, rn, rd = rd, rrem, ld, lrem
assert terms[:5] == [3, 7, 15, 1, 292]
assert terms[28421] == 78629
# Prior n=0,...,28419 use a_{n+1}=a_1,...,a_28420.
prior_max = max(terms[1:28421])
prior_max_indices = [i for i in range(1, 28421) if terms[i] == prior_max]
elo, ehi = qt*lo-pt*scale, qt*hi-pt*scale
assert 0 < elo < ehi and 2*ehi < scale
vlo, vhi = qt*elo, qt*ehi
assert 2*vhi < scale
assert vhi*(prior_max+2) < scale
lower40 = int(b.LOWER40[2:])
assert lower40*scale < vlo*10**40
assert vhi*10**40 < (lower40+1)*scale
outdir = Path(__file__).resolve().parent
# These decimal integers are exact, machine-checkable boundary data.
(outdir/'p28420.txt').write_text(str(pt)+'\n')
(outdir/'q28420.txt').write_text(str(qt)+'\n')
(outdir/'q28421.txt').write_text(str(qnext)+'\n')
report = {
 'format':'pi-finite-denominator-minimum/1',
 'status':'proved_given_standard_cf_identities_with_elementary_proof_in_RESULT.md',
 'dependencies':'Supplied baseline Machin identity/enclosure helper; no independent pi formula claimed',
 'certified_cf_terms':len(terms),
 'prefix_terms_sha256':hashlib.sha256(b''.join(b',%d'%a for a in terms)).hexdigest(),
 'target_n':28420,
 'next_partial_quotient':terms[28421],
 'prior_partial_quotient_max':prior_max,
 'prior_max_indices':prior_max_indices,
 'all_earlier_convergents_v_strict_lower':f'1/{prior_max+2}',
 'witness_strict_lower_40':b.LOWER40,
 'witness_strict_upper_40':b.UPPER40,
 'witness_upper_less_than_prior_lower':True,
 'witness_p_is_nearest_integer':True,
 'minimum_domain':'integers 1 <= q < q_28421',
 'unique_argmin':'q_28420',
 'q28420_digits':len(str(qt)),
 'q28421_digits':len(str(qnext)),
 'q28420_sha256':hashlib.sha256(str(qt).encode()).hexdigest(),
 'q28421_sha256':hashlib.sha256(str(qnext).encode()).hexdigest(),
 'scope':'No conclusion for q >= q_28421; no asymptotic liminf or bad approximability conclusion',
 'elapsed_seconds':round(time.monotonic()-start,3),
}
(outdir/'finite-minimum.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
