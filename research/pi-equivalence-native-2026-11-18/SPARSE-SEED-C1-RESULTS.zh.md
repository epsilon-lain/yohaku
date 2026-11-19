# A second exact seed for the BBP slope-four sparse-exception theorem

Date: 2026-11-19  
Status: **proved infinite subfamily by the previously established seed-shift theorem**.

## 1. The seed \(c=1\)

Use the exact rational definition of \(Y_{N,M}=16^N X_{N,M}\) from \`MIXED-RANK-CARRY-RESULTS.zh.md\`, and set \(Y(c)=Y_{c,4c}\).

Direct exact rational evaluation at \(c=1\) gives
\[
\boxed{Y(1)=\frac{14774523}{293930}.}
\]
The numerator is odd and the denominator has exactly one factor of \(2\). Hence
\[
Y(1)\ne0,\qquad \nu:=v_2(Y(1))=-1.
\]
For this seed,
\[
d_c=\lfloor\log_2(12c+9)\rfloor
=\lfloor\log_2 21\rfloor=4.
\]
The hypotheses of the established seed-shift theorem are satisfied:
\[
\nu=-1<4c-3=1.
\]
Its sufficient conditions on \(s\) are
\[
s\ge\max(2,d_c-1)=3,\qquad
s+2-2d_c>\nu.
\]
The second inequality is \(s-6>-1\), i.e. \(s\ge6\). Therefore
\[
\boxed{
v_2(Y_{2^s+1,\,4(2^s+1)})=-1
\quad(s\ge6).
}
\tag{1}
\]
Since \(v_2(Q_{N,4N})=\max(0,4N-v_2(Y_{N,4N}))\), this yields
\[
\boxed{
v_2(Q_{2^s+1,\,4(2^s+1)})=4(2^s+1)+1
\quad(s\ge6).
}
\tag{2}
\]
This is a new infinite sparse subfamily, distinct from the previously reported seed \(c=14\). It is a direct application of the already proved general seed-shift theorem, not a new proof of that theorem.

## 2. Independent exact checks

The accompanying standard-library script computes \(Y(1)\) directly as a rational number from the defining BBP sum and finite Beta correction, checks its exact 2-adic valuation, and checks the first several shifted values \(N=2^s+1\) by direct rational arithmetic.

These finite checks are regression tests only. The infinite conclusion (1)–(2) follows from the general seed-shift theorem and the exact seed calculation, not from extrapolating the finite list.

## 3. Scope

This extends the known infinite family from \(N=2^s+14\) to \(N=2^s+1\). It does not prove terminal nonvanishing for every even \(N\), does not cover every \(M=4N+o(N)\), and does not prove bad approximability of \(\pi\) over all rational denominators.
