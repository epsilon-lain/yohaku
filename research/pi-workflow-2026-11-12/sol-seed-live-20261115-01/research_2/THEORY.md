# Decimal runs and rational approximation along powers of ten

This note gives elementary proofs. Its computation reuses the provided
baseline's arctangent interval routine; it is not an independent implementation
of the pi enclosure. It does not determine pi's badly approximable status.

## Exact run criterion

Let x be an irrational real number. For an integer k >= 0 put
V_k = 10^k ||10^k x||, where ||y|| is distance to the nearest integer.
Let r >= 0 be an integer with m = k+r >= 1. Use the unique decimal expansion
of the irrational x. Then

    V_k < 10^(-r)

if and only if its digits in positions k+1 through 2k+r after the decimal
point are all zero, or are all nine. The block length is k+r.

Proof: Write f for the fractional part of 10^k x. It is irrational and in
(0,1). The inequality is equivalent to
min(f,1-f) < 10^(-m), which is equivalent to f < 10^(-m) or
f > 1-10^(-m). The first condition means its first m decimal digits are zero;
the second means they are nine. Irrationality excludes boundary equality and
ambiguous terminating expansions. Those digits are precisely positions
k+1,...,k+m of x. This proves both implications.

Consequently, liminf of V_k as k tends to infinity is zero exactly when, for
every integer r >= 1 and every K >= 0, there is a k >= K whose digits in
positions k+1,...,2k+r are all zero or all nine. Arbitrarily long runs without
this relation between length and position do not give this conclusion.
Since powers of ten form a subsequence of all positive integer denominators,
such a zero liminf would imply liminf_q q||qx|| = 0. The converse is not
established here and is not used.

## An explicit obstruction to an inference from long runs alone

Let s_n = n(n+1)/2 for n >= 1, and let

    x = sum over n >= 1 of 10^(-s_n).

Its decimal expansion has ones exactly at triangular positions 1,3,6,10,...
and zeros elsewhere. There are arbitrarily long zero blocks. It is irrational:
an eventually periodic decimal with infinitely many ones would have bounded
zero-block lengths, whereas this one has unbounded zero-block lengths and
infinitely many ones.

Nevertheless, for every integer k >= 0,

    10^k ||10^k x|| >= 1/10.

Proof: Let s_0=0 and choose n >= 0 with s_n <= k < s_(n+1). The first one
after position k is at t = s_(n+1). If n=0 then k=0 and t=1. If n>=1 then
n <= s_n and t=s_n+n+1 <= 2s_n+1 <= 2k+1. Thus in every case t<=2k+1.
The fractional part f of 10^k x has digits zero or one, so 0<f<1/9<1/2.
Its digit at position t-k is one, hence f>=10^(-(t-k)). Its nearest integer
is zero, and 10^k||10^k x||=10^k f>=10^(2k-t)>=1/10.

This example concerns denominators 10^k. It makes no assertion that x is
badly approximable over all denominators.

## The finite pi check and its certificate

`certify_decimal_powers.py` obtains strict integers L < S*pi < H, S=10^30000,
using `common/check_runB_independent.py:inverse_atan_bounds` and the pi
identity justified in `common/RUNB-INDEPENDENT.md`.

For k>=1 it maintains residues l_k=(10^k L) mod S and
h_k=(10^k H) mod S. The assertion

    h_k-l_k = 10^k(H-L),    0<l_k<h_k<S

proves that the interval does not cross an integer. Hence

    S ||10^k pi|| > d_k = min(l_k,S-h_k).

The upper bound at k=0 is (H-3S)/S for pi-3, with nearest integer 3.
At every tested k the script checks

    d_k > floor((H-3S)/10^k),

which implies 10^k d_k > H-3S. Thus every tested positive k has
10^k||10^k pi|| > pi-3. Crossing a half integer would not invalidate this
lower bound. The saved JSON records the actual successful range and decimal
bounds. The saved decimal prefix is accepted only when both enclosure
endpoints have the same floor after scaling to its length.

The resulting finite result does not extend to all powers of ten, to all
denominators in the same numerical range, or to an asymptotic liminf.

## Questions left open

* Can the zero/nine run criterion be profitably combined with certificates
  of longer pi prefixes? No infinite run-length bound is supplied here.
* What is pi's liminf along powers of ten? The finite calculation does not
  settle it.
* What is pi's liminf over all denominators, and is pi badly approximable?
  This work supplies no new answer to these questions.
