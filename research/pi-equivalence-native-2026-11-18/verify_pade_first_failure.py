"""Exact first failure of Yohaku's four Padé candidates at threshold 1/1000.

The search uses small integer Taylor enclosures and certified convergents of
1/pi. The analytic Padé norm and factorial bounds are proved in the notes.
"""
from fractions import Fraction
from math import factorial

THRESHOLD = Fraction(1, 1000)
EARLIER_SINE_BOUND = Fraction(719, 100000)
EXPECTED_N = (
    1901870728566923076090143944714770339621590768313546337192526115562704339680963564320007808107929370299752345187688835741387003036853361285671158059867702399073227994426905220194699766118756059055619036488502928002591
)
EXPECTED_Q = (
    605384255146420326102361023215940531716391478150345020739231253172134740688232476946000058713774549796561447468267746412874022717544100946587144148739626803435133473281606663121381125761746030151344353855924025288111
)


def atan_grid(inverse, scale):
    """Bound arctan(1/inverse) by two integers divided by scale."""
    lower = upper = index = 0
    power = inverse
    while True:
        divisor = (2*index + 1)*power
        quotient, remainder = divmod(scale, divisor)
        if quotient == 0:
            # The first omitted term has magnitude < 1 grid unit.
            return (lower - 1, upper) if index % 2 else (lower, upper + 1)
        ceiling = quotient + bool(remainder)
        if index % 2:
            lower -= ceiling
            upper -= quotient
        else:
            lower += quotient
            upper += ceiling
        index += 1
        power *= inverse**2


def pi_grid(scale, alternate=False):
    if alternate:
        a_low, a_high = atan_grid(2, scale)
        b_low, b_high = atan_grid(3, scale)
        return 4*(a_low + b_low), 4*(a_high + b_high)
    a_low, a_high = atan_grid(5, scale)
    b_low, b_high = atan_grid(239, scale)
    return 16*a_low - 4*b_high, 16*a_high - 4*b_low


def certified_convergents(lower, upper):
    """Reciprocate and subtract integers on enclosing rational endpoints."""
    before_num, num = 0, 1
    before_den, den = 1, 0
    while True:
        a, b = lower
        c, d = upper
        digit = a // b
        if digit != c // d:
            return
        before_num, num = num, digit*num + before_num
        before_den, den = den, digit*den + before_den
        yield num, den
        rem_low, rem_high = a - digit*b, c - digit*d
        if not rem_low:
            return
        lower, upper = (d, rem_high), (b, rem_low)


def absolute_interval(lo, hi):
    if lo <= 0 <= hi:
        return 0, max(-lo, hi)
    return min(abs(lo), abs(hi)), max(abs(lo), abs(hi))


def bound_sine(n, q, scale, pi_lower, pi_upper):
    """Enclose n|sin n|, using that q is nearest to n/pi."""
    lower, upper = absolute_interval(n*scale - q*pi_upper,
                                     n*scale - q*pi_lower)
    assert 2*upper < pi_lower
    # For x >= 0, x - x^3/6 <= sin x <= x.
    return (
        Fraction(n*(6*lower*scale**2 - upper**3), 6*scale**3),
        Fraction(n*upper, scale),
    )


def first_obstruction(alternate=False):
    scale = 10**800
    pi_lower, pi_upper = pi_grid(scale, alternate)
    previous_min_bound = Fraction(1)
    for index, (q, n) in enumerate(certified_convergents(
            (scale, pi_upper), (scale, pi_lower)), 1):
        lower, upper = bound_sine(n, q, scale, pi_lower, pi_upper)
        if upper < THRESHOLD:
            assert (index, n, q) == (432, EXPECTED_N, EXPECTED_Q)
            return n, q, lower, upper, previous_min_bound
        # Each nonconvergent n is dominated by an earlier convergent for
        # both n and ||n/pi||, by best approximation of the second kind.
        assert lower > EARLIER_SINE_BOUND, (n, lower)
        previous_min_bound = min(previous_min_bound, lower)
    raise ValueError("Precision did not suffice to reach the first failure.")


def check_small_pade():
    for n in (2, 3, 4):
        degrees = (2*n, 2*n + 1, 4*n, 8*n)
        prev_a, prev_b = 1, 0
        a, b = 2, 2*n
        for m in range(1, degrees[-1] + 1):
            if m in degrees:
                u = (2*n)**(2*m + 1)*factorial(m)
                v = factorial(2*m + 1)
                assert 1000*n*(2*v*abs(b) - u) > 2*v*(abs(a) + abs(b))
            coeff = 2*(2*m + 1)
            prev_a, a = a, coeff*a - (2*n)**2*prev_a
            prev_b, b = b, coeff*b - (2*n)**2*prev_b


def outward(lower, upper, digits):
    scale = 10**digits
    return (
        lower.numerator*scale // lower.denominator,
        -(-upper.numerator*scale // upper.denominator),
    )


def certify_pi_records(n, q, alternate=False):
    """Find strict Pi approximation records independently of sine firstness."""
    scale = 10**800
    low, high = pi_grid(scale, alternate)
    previous_lower = Fraction(1)
    previous_upper = previous_lower
    records = []
    for index, (p, denominator) in enumerate(certified_convergents(
            (low, scale), (high, scale))):
        if denominator > q:
            break
        error_low, error_high = absolute_interval(
            denominator*low - p*scale, denominator*high - p*scale)
        lower = Fraction(denominator*error_low, scale)
        upper = Fraction(denominator*error_high, scale)
        if upper < previous_lower:
            records.append((index, p, denominator, outward(lower, upper, 18)))
            previous_lower, previous_upper = lower, upper
        else:
            assert records and lower > previous_upper
    else:
        raise ValueError("Enclosure too wide to certify the cutoff.")
    assert [row[0] for row in records] == [0, 1, 3, 306, 430]
    assert records[-1][1:] == (n, q, (48130561246289, 48130561246290))
    assert len(str(records[-2][2])) == 155
    return records


def main():
    n, q, lower, upper, earlier_min = first_obstruction()
    n2, q2, lower2, upper2, earlier_min2 = first_obstruction(alternate=True)
    assert (n, q) == (n2, q2)
    assert max(lower, lower2) <= min(upper, upper2)
    assert min(earlier_min, earlier_min2) > EARLIER_SINE_BOUND
    earlier_min_floor = outward(min(earlier_min, earlier_min2), earlier_min, 16)[0]
    witness_interval = outward(min(lower, lower2), max(upper, upper2), 16)
    assert witness_interval == (1512066176244, 1512066176245)
    # For m >= 2n and n >= 5 the proven bound yields
    # L >= n|sin n|/2 - n/(2*4**n). The last term decreases for n >= 1.
    assert EARLIER_SINE_BOUND/2 - Fraction(5, 2*4**5) > THRESHOLD
    check_small_pade()
    records = certify_pi_records(n, q)
    assert records == certify_pi_records(n, q, alternate=True)
    print("Certified Pi record indices through q:", [row[0] for row in records])
    scale = 10**800
    pi_lower, pi_upper = pi_grid(scale)
    assert n*scale < q*pi_lower  # Original fraction n/q is below pi.
    cost_interval = outward(Fraction(q*(q*pi_lower - n*scale), scale),
                            Fraction(q*(q*pi_upper - n*scale), scale), 18)
    assert cost_interval == (48130561246289, 48130561246290)
    print("First failure after checking 432 convergents in two pi enclosures.")
    print(f"n = {n}\nq = {q}")
    print(f"n*|sin n| in {witness_interval} / 10^16")
    print(f"q²*|pi-n/q| in {cost_interval} / 10^18")
    print(f"For every earlier n, n*|sin n| > {earlier_min_floor} / 10^16")
    print("All four exact Padé candidate checks passed for n=2,3,4.")
    print("All m >= 2n pass for 5 <= n < witness, by the analytic bounds.")
    print("At witness all m fail, since L <= n*|sin n| < 1/1000.")


if __name__ == "__main__":
    main()
