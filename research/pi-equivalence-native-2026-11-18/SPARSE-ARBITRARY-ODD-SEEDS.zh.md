# Arbitrary odd-part seeds for the BBP slope-four shift theorem

Date: 2026-11-19  
Status: **proved parameter family, conditional only on the two previously established theorems cited below**. The odd part \(A\) may vary with \(u\); this extends the special seeds \(c=1\), \(c=14\), and \(c=2^u-1\).

## 1. Exact valuation of the seed \(c=A2^u-1\)

Let \(A\ge1\) be a fixed odd integer, \(u\ge1\), and
\[
c=A2^u-1,\qquad N=c,\qquad M=4c.
\]
Use the established BBP notation
\[
L=8(N+1),\quad h=v_2(L),\quad
q=\left\lfloor\frac{M+3}{4}\right\rfloor,\quad
m=M+1,
\]
and
\[
c_i=v_2\binom{L+i}{i},\qquad
C=\max_{0\le i\le M+4}c_i.
\]
Since \(N+1=A2^u\) and \(A\) is odd,
\[
h=u+3,\qquad q=A2^u-1=c,\qquad v_2(q)=0.
\]
Also
\[
m=4A2^u-3,\qquad
\left\lfloor\frac{m}{2^h}\right\rfloor
=\left\lfloor\frac{4A2^u-3}{8\cdot2^u}\right\rfloor
=\frac{A-1}{2}.
\]
The same quotient \(\lfloor i/2^h\rfloor\) ranges only from \(0\) to \((A-1)/2\) for \(0\le i\le M+4\). By the carry formula in the established dyadic-block theorem,
\[
c_i=v_2\binom{A+\lfloor i/2^h\rfloor}
{\lfloor i/2^h\rfloor}.
\]
Consequently define the two constants depending only on \(A\):
\[
C_A=\max_{0\le k\le(A-1)/2}v_2\binom{A+k}{k},
\qquad
\gamma_A=v_2\binom{A+(A-1)/2}{(A-1)/2}
=v_2\binom{(3A-1)/2}{(A-1)/2}.
\]
Then \(C=C_A\) and \(c_m=\gamma_A\), independently of \(u\).

If
\[
u+3\ge2C_A+11,
\tag{1}
\]
the established arbitrary-odd-part dyadic-block theorem applies. Its hypotheses are \(h\ge2C+11\) and \(v_2(q)\le u\), both now explicit. It gives
\[
v_2(2Y_{c,4c})=v_2(q)-c_m=-\gamma_A.
\]
Thus
\[
\boxed{v_2(Y_{A2^u-1,\,4(A2^u-1)})=-1-\gamma_A.}
\tag{2}
\]
This is an exact seed formula for every positive odd \(A\) and every \(u\) satisfying (1), even when \(A\) varies with \(u\).

## 2. Shift each seed again

Apply the previously proved fixed-seed shift theorem to the seed \(c=A2^u-1\), whose valuation is
\[
\nu_A=-1-\gamma_A.
\]
Let
\[
d_c=\lfloor\log_2(12c+9)\rfloor.
\]
Set the exact integer
\[
d_c=\lfloor\log_2(12c+9)\rfloor
=\lfloor\log_2(12A2^u-3)\rfloor.
\]
The shift theorem requires
\[
\nu_A<4c-3,\qquad
s\ge\max(2,d_c-1),\qquad
s+2-2d_c>\nu_A.
\]
The first condition is automatic for \(c\ge1\), since \(\nu_A=-1-\gamma_A\le-1<4c-3\). The remaining two conditions are equivalent to
\[
\boxed{s\ge\max(2,d_c-1,2d_c-2-\gamma_A).}
\tag{3}
\]
Thus for every positive odd \(A\), every \(u\) satisfying (1), and every \(s\) satisfying (3),
\[
\boxed{
v_2\!\left(Y_{\,2^s+A2^u-1,\ 4(2^s+A2^u-1)}\right)
=-1-\gamma_A.
}
\tag{4}
\]
Using \(v_2(Q_{N,4N})=4N-v_2(Y_{N,4N})\), we obtain
\[
\boxed{
v_2(Q_{N,4N})=4N+1+\gamma_A,
\quad N=2^s+A2^u-1.
}
\tag{5}
\]
This is an infinite two-parameter family for every fixed odd \(A\), not merely the \(A=1\) family.

## 3. A simple explicit sufficient bound on \(u\)

The exact condition (1) is already effective because \(C_A\) is a finite maximum. A coarse closed bound is also available. Kummer's theorem identifies
\(v_2\binom{A+k}{k}\) with the number of binary carries in adding \(A\) and \(k\). For \(0\le k\le(A-1)/2\), the sum \(A+k<3A/2\), so
\[
C_A\le\lfloor\log_2(3A/2)\rfloor+1.
\]
Hence the easily checked sufficient condition
\[
\boxed{u\ge2\lfloor\log_2(3A/2)\rfloor+10}
\tag{6}
\]
implies (1). This bound is not claimed optimal.

For \(A=1\), \(C_A=\gamma_A=0\), and the exact threshold (1) is \(u\ge8\). Then \(d_c=u+3\) and (3) becomes \(s\ge2u+4\), recovering the previously obtained \(A=1\) growing-seed family.

## 4. Scope and what remains open

The proof combines two earlier results without changing either:

1. the dyadic-block theorem for \(N+1=A2^u\), which gives the exact seed valuation (2);
2. the fixed-seed shift theorem, which gives (4) for each such seed.

No new proof of either parent theorem is claimed here. The result still concerns only the BBP rational family on the exact slope \(M=4N\). It does not prove the terminal nonvanishing for all even \(N\), does not cover all \(M=4N+o(N)\), and does not prove bad approximability of \(\pi\) over arbitrary rational denominators.

## Exact finite constants

The companion script [verify_sparse_arbitrary_odd_seeds.py](verify_sparse_arbitrary_odd_seeds.py) computes the finite Kummer carry maxima \(C_A\), terminal carry count \(\gamma_A\), and exact shift thresholds for sample odd \(A\). It checks the coarse sufficient bound (6). This is a finite arithmetic regression; the infinite family is proved by Sections 1–3.

## Exact threshold computation in logarithmic time

The threshold constant \(C_A\) need not be computed by scanning all \(k\le(A-1)/2\). Kummer's theorem turns it into a maximum-carry digit DP with four states (borrow in \(K-k\), carry in \(A+k\)), where \(K=(A-1)/2\). The exact algorithm takes \(O(\log A)\) transitions and returns both \(C_A\) and \(\gamma_A\). See [the digit-DP derivation](SPARSE-SEED-CARRY-DP.zh.md) and [the exact verifier](verify_sparse_seed_carry_dp.py), which checks agreement with brute force for every odd \(A<1000\).
