# Iterated even-seed shifts and the exceptional seed \(c=110\)

Date: 2026-11-19  
Status: **proved sparse infinite families by the established fixed-seed shift theorem; explicit limitation on coverage recorded.**

## 1. The shift theorem as an operator

For a positive seed \(c\), write
\[
\nu(c)=v_2(Y_{c,4c}),\qquad d(c)=\lfloor\log_2(12c+9)\rfloor.
\]
If
\[
Y_{c,4c}\ne0,\qquad \nu(c)<4c-3,
\]
then the established fixed-seed shift theorem gives
\[
v_2(Y_{2^s+c,\,4(2^s+c)})=\nu(c)
\]
whenever
\[
s\ge \max\{2,d(c)-1,\nu(c)+2d(c)-1\}.
\tag{1}
\]
This can be iterated: once \(c\) is itself obtained as a shifted seed and its valuation is known, it can be used as the next seed.

## 2. A nested even family from the seed \(c=2\)

The exact seed calculation gives
\[
Y_{2,8}=\frac{16609872428603}{20652682050},
\qquad \nu(2)=-1,\quad d(2)=5.
\]
By (1), for every \(u\ge8\),
\[
\nu(2^u+2)=-1.
\]
For \(u\ge8\),
\[
d(2^u+2)=\lfloor\log_2(12\cdot2^u+33)\rfloor=u+3.
\]
Applying (1) a second time, the condition on the next shift exponent \(s\) is
\[
s\ge\max\{2,u+2,2(u+3)-2\}=2u+4.
\]
Hence
\[
\boxed{
v_2(Y_{2^s+2^u+2,\,4(2^s+2^u+2)})=-1
\quad(u\ge8,\ s\ge2u+4).
}
\tag{2}
\]
In particular the reduced denominator has
\[
\boxed{v_2(Q)=4N+1,\qquad N=2^s+2^u+2.}
\]
This is a two-level iterated shift, not just a restatement of the one-level family.

More generally, define \(c_0=2\), and recursively choose
\[
c_{j+1}=2^{s_j}+c_j
\]
with \(s_j\) satisfying (1) for \(c_j\). Then \(\nu(c_j)=-1\) at every stage. This gives arbitrarily long finite sums of powers of two plus 2, subject to explicit rapidly increasing gap conditions. It is still a sparse family.

## 3. The exceptional even seed \(c=110\)

The previously recorded exact counterexample has
\[
v_2(Y_{110,440})=4.
\]
It is not a failure of the shift theorem: \(4<4\cdot110-3=437\). Also
\[
d(110)=\lfloor\log_2(1329)\rfloor=10.
\]
Thus (1) applies for
\[
s\ge\max\{2,9,4+20-1\}=23,
\]
and proves
\[
\boxed{
v_2(Y_{2^s+110,\,4(2^s+110)})=4
\quad(s\ge23).
}
\tag{3}
\]
Consequently
\[
v_2(Q_{2^s+110,\,4(2^s+110)})=4(2^s+110)-4.
\]
This gives a second even infinite family, but it also warns us not to conjecture that every seed has valuation \(-1\).

## 4. What this says about coverage

For any fixed seed \(c\), one application of (1) covers only the shifted powers-of-two sequence
\[
N=2^s+c
\]
with \(s\) above its threshold. A finite collection of seeds therefore covers only a finite union of shifted powers of two, not all sufficiently large even integers.

The subsequent [coverage and counting theorem](SPARSE-COVERAGE-OBSTRUCTION.zh.md) characterizes every finite iteration from seed \(2\) exactly: the added exponents satisfy \(e_1\ge8\), \(e_{j+1}\ge2e_j+4\). The number of descendants up to \(X\) is at most \(\exp(O((\log\log X)^2))\). Hence all iterations from any fixed finite seed set together have density zero.

Moreover, every final shift must satisfy \(s=\lfloor\log_2N\rfloor\) and \(N\le\lfloor4\cdot2^s/3\rfloor-1\). Thus supplying even an unlimited collection of seeds cannot make this particular shift criterion cover every sufficiently large even integer. The [adjacent-step theorem](BBP-EVEN-DYADIC-TRANSFER.zh.md) now proves an additional family outside that window; general coverage still requires further work.

## 5. Scope

Equations (2) and (3) are rigorous consequences of exact seed valuations and the previously proved shift theorem. They do not establish terminal nonvanishing for all even \(N\), do not control \(M=4N+o(N)\), and do not prove bad approximability of \(\pi\).

