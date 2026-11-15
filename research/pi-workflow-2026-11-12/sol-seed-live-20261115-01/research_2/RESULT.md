# Result

The executed integer check proves

    min { 10^k ||10^k pi|| : 0 <= k <= 14999 } = pi-3,

with a unique minimizer k=0. Thus none of these 15000 decimal-power
denominators competes with the baseline convergent witness, whose product
is below 0.000012717857372758. The minimum here is strictly between
0.1415926535897932384626433832795028841971 and
0.1415926535897932384626433832795028841972.

This is a result for a finite sparse denominator family, not for all
denominators up to 10^14999 and not for an infinite tail. The pi enclosure
routine is shared with the baseline. The check is a new application of it,
not an independent end-to-end pi certification or a new approximation record.

The same run saves a certified 29990-digit fractional prefix. Its longest
zero run has length 5, first starting at decimal position 17534; its longest
nine run has length 6, first starting at position 762. These counts concern
only that finite saved prefix, including possible truncated final runs.

`THEORY.md` additionally proves the exact relation between small products
and long zero/nine blocks starting at the correct position, and constructs
an irrational decimal with arbitrarily long zero runs but
10^k ||10^k x|| >= 1/10 for every k. The example concerns only powers of ten;
no badly-approximable claim is made for it.

Reproduce with assertions enabled:

    python research_2/certify_decimal_powers.py

Check `decimal_powers_certificate.json`, `execution_stdout.json`, and
`execution_timing.txt`. Main proof and limitations are in `THEORY.md`.
