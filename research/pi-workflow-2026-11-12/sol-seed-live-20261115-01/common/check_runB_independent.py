"""Self-contained integer certification of the historical runB finite witness.

Usage: python check_runB_independent.py --output runB-independent.json
Optional: --artifact path/to/pi-cf-certified-summary.json

No project code, model output, precomputed pi digits, third-party library or
network is used to derive the witness. The optional artifact is read as data.
This is an external audit, not work performed by the trial's Sol participant.

Identity and enclosure proof:
  Put theta=12 atan(1/18)+8 atan(1/57)-5 atan(1/239). Exact Gaussian integer
  multiplication gives (18+i)^12(57+i)^8(239-i)^5 = C(1+i), C>0.
  Also 0 < 12*18/325-5/239 < theta < 12/18+8/57 < 1 < pi/2.
  These use z/(1+z*z) < atan(z) < z for z>0, from its defining integral.
  Thus theta=pi/4 and pi=48 atan(1/18)+32 atan(1/57)-20 atan(1/239).
  Each alternating-series term is rounded outward at scale 10^30000.
  Repeated integer division tracks floor(scale/x^(2*k+1)) exactly. At the
  first zero quotient, the first omitted scaled term is below one, so the
  remaining alternating tail is enclosed by (-1,1).

Continued fractions are extracted only while both rational endpoints have
the same floor and positive remainders. Endpoint reversal under 1/(t-a)
preserves enclosure. Integer recurrences derive p_28420/q_28420 (a_0=3).
Finally q*(q*pi-p) is enclosed directly; no original complete-quotient error
formula is reused. A nearest-integer check establishes q*||q*pi||.

This verifies a finite witness and an infimum upper bound. It does not certify
all 58417 historical terms, the stored exact fraction as an upper bound on pi,
an asymptotic liminf bound, global minimality, or pi's badly approximable status.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError("Assertions must remain enabled; do not run with -O.")
sys.set_int_max_str_digits(0)
HISTORICAL_SHA256 = "324a5a829cd5b95bd972e80cf904a69ee1b7e3bed3ea44e5653c8a663200f4d4"
LOWER40 = "0.0000127178573727574566035844693935801274"
UPPER40 = "0.0000127178573727574566035844693935801275"


def multiply(z, w):
    return (z[0]*w[0]-z[1]*w[1], z[0]*w[1]+z[1]*w[0])


def inverse_atan_bounds(x, scale):
    lower = upper = 0
    power_floor = scale // x
    k = 0
    while power_floor:
        term = power_floor // (2*k+1)
        if k % 2:
            lower -= term + 1
            upper -= term
        else:
            lower += term
            upper += term + 1
        power_floor //= x*x
        k += 1
    return lower-1, upper+1, k


def decimal_grid(num, den, digits):
    q, r = divmod(num * 10**digits, den)
    assert r != 0
    def decimal(integer):
        return f"{integer // 10**digits}.{integer % 10**digits:0{digits}d}"
    return {"digits": digits, "strict_lower": decimal(q), "strict_upper": decimal(q+1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args()
    gaussian = (1, 0)
    for real, imag, exponent in [(18, 1, 12), (57, 1, 8), (239, -1, 5)]:
        for _ in range(exponent):
            gaussian = multiply(gaussian, (real, imag))
    assert gaussian[0] == gaussian[1] and gaussian[0] > 0
    assert 12*Fraction(18, 325)-5*Fraction(1, 239) > 0
    assert 12*Fraction(1, 18)+8*Fraction(1, 57) < 1
    digits = 30000
    scale = 10**digits
    intervals = {x: inverse_atan_bounds(x, scale) for x in (18, 57, 239)}
    lo = 48*intervals[18][0] + 32*intervals[57][0] - 20*intervals[239][1]
    hi = 48*intervals[18][1] + 32*intervals[57][1] - 20*intervals[239][0]
    assert 3*scale < lo < hi < 4*scale

    ln, ld, rn, rd = lo, scale, hi, scale
    pm2, pm1, qm2, qm1 = 0, 1, 1, 0
    terms = []
    p_target = q_target = None
    for n in range(28422):
        a = ln // ld
        assert a == rn // rd, ("interval floor mismatch", n)
        assert n == 0 or a >= 1
        terms.append(a)
        p, q = a*pm1+pm2, a*qm1+qm2
        assert p*qm1-pm1*q == (-1 if n % 2 == 0 else 1)
        if n == 28420:
            p_target, q_target = p, q
        pm2, pm1, qm2, qm1 = pm1, p, qm1, q
        lrem, rrem = ln-a*ld, rn-a*rd
        assert lrem > 0 and rrem > 0
        ln, ld, rn, rd = rd, rrem, ld, lrem
    assert terms[:5] == [3, 7, 15, 1, 292]
    assert terms[28421] == 78629
    assert terms.index(max(terms)) == 28421
    assert len(str(q_target)) == 14593
    elo, ehi = q_target*lo-p_target*scale, q_target*hi-p_target*scale
    assert 0 < elo < ehi and 2*ehi < scale
    vlo, vhi = q_target*elo, q_target*ehi
    floor40 = int(LOWER40.replace("0.", ""))
    assert floor40*scale < vlo*10**40
    assert vhi*10**40 < (floor40+1)*scale
    assert vhi*78629 < scale
    assert vhi*q < scale*q_target
    assert vhi*10**18 < 12717857372758*scale
    qtext, ptext = str(q_target), str(p_target)
    report = {
        "format": "external-v06d-runB-independent-integer-check/1",
        "uploaded_code_executed": False,
        "network_or_model_calls": 0,
        "independent_pi_identity": "pi = 48*atan(1/18)+32*atan(1/57)-20*atan(1/239)",
        "identity_gaussian_real_equals_imag": str(gaussian[0]),
        "scale_decimal_digits": digits,
        "arctan_terms": {str(x): intervals[x][2] for x in intervals},
        "pi_enclosure_scaled_width": hi-lo,
        "certified_cf_terms": len(terms),
        "a28421": terms[28421],
        "prefix_max_at": terms.index(max(terms)),
        "prefix_terms_sha256": hashlib.sha256(b"".join(b",%d" % a for a in terms)).hexdigest(),
        "p28420_digits": len(ptext),
        "q28420_digits": len(qtext),
        "p28420_sha256": hashlib.sha256(ptext.encode()).hexdigest(),
        "q28420_sha256": hashlib.sha256(qtext.encode()).hexdigest(),
        "q28421_digits": len(str(q)),
        "p28420_is_nearest_integer_to_q28420_pi": True,
        "strict_witness_lower_40": LOWER40,
        "strict_witness_upper_40": UPPER40,
        "strict_witness_upper_18": "0.000012717857372758",
        "witness_less_than_reciprocal_a28421": True,
        "witness_less_than_q28420_over_q28421": True,
        "scope": "Finite witness and infimum upper bound only; no tail liminf, global minimum, BA/non-BA or full 58417-term certification.",
    }
    if args.artifact:
        raw = args.artifact.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == HISTORICAL_SHA256
        historic = json.loads(raw)["runB"]["min_markov_upper_bound"]
        num, den = int(historic["upper_num"]), int(historic["upper_den"])
        assert num > 0 and den > 0
        g18, g40 = decimal_grid(num, den, 18), decimal_grid(num, den, 40)
        assert historic["at_n"] == 28420
        assert g40["strict_lower"] == historic["decimal_40"] == LOWER40
        assert g40["strict_upper"] == UPPER40
        assert g18["strict_upper"] == report["strict_witness_upper_18"]
        report["historical_fraction_rounding_only"] = {
            "artifact_sha256": HISTORICAL_SHA256,
            "numerator_digits": len(historic["upper_num"]),
            "denominator_digits": len(historic["upper_den"]),
            "grid18": g18,
            "grid40": g40,
            "fraction_as_upper_bound_on_true_witness_independently_certified": False,
            "note": "This optional part checks the stored rational's rounding only. The true witness enclosure above is derived independently.",
        }
    output = json.dumps(report, ensure_ascii=False, indent=2)+"\n"
    if args.output:
        args.output.write_text(output)
    print(output)


if __name__ == "__main__":
    main()

