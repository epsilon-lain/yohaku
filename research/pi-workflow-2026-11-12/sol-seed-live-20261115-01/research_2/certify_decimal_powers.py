"""Finite check of q=10^k. Reuses baseline arctangent interval routine.
No network, third-party library, precomputed pi digits, or claim of an
independent pi implementation. Run from any directory with Python 3.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
if not __debug__:
    raise RuntimeError('Run without -O: assertions are part of this check.')
sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('baseline', ROOT/'common/check_runB_independent.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

def main():
    start = time.monotonic()
    digits, kmax = 30000, 14999
    scale = 10**digits
    intervals = {a: baseline.inverse_atan_bounds(a, scale) for a in (18,57,239)}
    lo = 48*intervals[18][0]+32*intervals[57][0]-20*intervals[239][1]
    hi = 48*intervals[18][1]+32*intervals[57][1]-20*intervals[239][0]
    assert 3*scale < lo < hi < 7*scale//2
    # q=1 has nearest integer 3 and v in ((lo-3S)/S,(hi-3S)/S).
    v0_lower, v0_upper = lo-3*scale, hi-3*scale
    rlo, rhi = lo-3*scale, hi-3*scale
    threshold = v0_upper
    # If d_k > floor(v0_upper/10^k), then 10^k*d_k > v0_upper.
    # d_k=min(rlo,S-rhi) is a rigorous lower bound on scaled distance
    # from 10^k*pi to the nearest integer, provided no integer is crossed.
    crossing_count = 0
    nearest_half_crossings = 0
    for k in range(1, kmax+1):
        rlo = (10*rlo) % scale
        rhi = (10*rhi) % scale
        threshold //= 10
        assert rhi-rlo == (hi-lo)*10**k, ('integer crossing or width mismatch', k)
        assert 0 < rlo < rhi < scale
        dlo = min(rlo, scale-rhi)
        assert dlo > threshold, ('could not exclude a smaller value', k)
        if 2*rlo < scale < 2*rhi:
            nearest_half_crossings += 1
    # Save a conservative stable prefix and characterize zero/nine runs.
    stable_digits = 29990
    divisor = 10**(digits-stable_digits)
    assert lo//divisor == hi//divisor
    prefix = str(lo//divisor)
    assert prefix[0] == '3' and len(prefix) == stable_digits+1
    fraction = prefix[1:]
    run_summary = {}
    for char in '09':
        best_length = current = 0
        best_start = None
        for position, digit in enumerate(fraction, 1):
            current = current+1 if digit == char else 0
            if current > best_length:
                best_length, best_start = current, position-current+1
        run_summary[char] = {'longest_run_in_saved_prefix':best_length, 'first_start_decimal_position':best_start}
    out = ROOT/'research_2'
    (out/'pi_decimal_prefix.txt').write_text('3.'+fraction+'\n')
    report = {
        'format':'pi-decimal-power-finite-certificate/1',
        'source':'common/check_runB_independent.py inverse_atan_bounds; pi identity justified in common/RUNB-INDEPENDENT.md',
        'independent_pi_implementation':False,
        'pi_scale_digits':digits,
        'pi_interval_scaled_width':hi-lo,
        'denominators':'q=10^k',
        'k_min':0,'k_max':kmax,'number_of_denominators':kmax+1,
        'unique_minimum_at_k':0,'nearest_integer_at_minimum':3,
        'minimum_is':'pi-3',
        'minimum_strict_decimal_lower':'0.1415926535897932384626433832795028841971',
        'minimum_strict_decimal_upper':'0.1415926535897932384626433832795028841972',
        'integer_crossings':crossing_count,
        'nearest_half_crossings':nearest_half_crossings,
        'all_k_positive_have_product_strictly_above_pi_minus_3':True,
        'stable_fractional_digits_saved':stable_digits,
        'prefix_file_sha256':hashlib.sha256((out/'pi_decimal_prefix.txt').read_bytes()).hexdigest(),
        'zero_nine_run_summary':run_summary,
        'scope':'Only the specified finite set of powers of ten. No statement about all q or an infinite tail.',
        'elapsed_seconds':round(time.monotonic()-start,6),
    }
    lower40 = int(report['minimum_strict_decimal_lower'].replace('0.',''))
    assert lower40*scale < v0_lower*10**40
    assert v0_upper*10**40 < (lower40+1)*scale
    (out/'decimal_powers_certificate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
