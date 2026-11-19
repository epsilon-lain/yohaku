# A low even seed \(c=2\) and the exact coverage criterion for slope four

Date: 2026-11-19  
Status: **new infinite even-\(N\) subfamily, plus an exact characterization of what the fixed-seed shift theorem covers**.

## 1. Why parity matters

For a shifted seed \(N=2^s+c\) with \(s\ge1\), the parity of \(N\) is the parity of \(c\). Thus the growing seeds \(c=A2^u-1\) with odd \(A\) are odd, and their large shifts produce odd \(N\), not even \(N\).

They are valid infinite subfamilies, but they do not address the even-\(N\) branch of the original terminal-sum problem. For even \(N\), we need even seeds \(c\).

## 2. Exact seed \(c=2\)

Direct exact rational evaluation from the defining BBP sum and finite Beta correction gives
\[
\boxed{
Y_{2,8}=\frac{16609872428603}{20652682050}.
}
\]
The numerator is odd and the denominator has 2-adic valuation 1, hence
\[
v_2(Y_{2,8})=-1.
\]
Set
\[
d_2=\lfloor\log_2(12\cdot2+9)\rfloor
=\lfloor\log_2 33\rfloor=5.
\]
The fixed-seed shift theorem applies because
\[
-1<4\cdot2-3=5,
\]
and its shift conditions reduce to
\[
s\ge\max(2,4, -1+10-1)=8.
\]
Therefore
\[
\boxed{
v_2(Y_{2^s+2,\,4(2^s+2)})=-1
\quad(s\ge8).
}
\tag{1}
\]
Consequently
\[
\boxed{
v_2(Q_{2^s+2,\,4(2^s+2)})=4(2^s+2)+1
\quad(s\ge8).
}
\tag{2}
\]
Unlike the odd growing-seed families, this is an infinite subfamily of even \(N\).

## 3. Exact coverage criterion for a prescribed even \(N\)

Fix an even integer \(N\ge4\). For every integer \(s\ge1\) with \(2^s<N\), put
\[
c_s=N-2^s.
\]
Then \(c_s\) is a nonnegative even integer. For \(c_s\ge1\), compute the exact rational seed
\[
Y_c=Y_{c,4c},\qquad
\nu_c=v_2(Y_c),\qquad
d_c=\lfloor\log_2(12c+9)\rfloor.
\]
If \(Y_c\ne0\), the fixed-seed shift theorem proves the desired exact valuation at this \(N\) whenever
\[
\boxed{
\nu_c<4c-3,\qquad
s\ge\max(2,d_c-1,\nu_c+2d_c-1).
}
\tag{3}
\]
Thus (3), over the finite set \(s=1,\ldots,\lfloor\log_2(N-1)\rfloor\), is an exact finite decision test for whether this seed-shift mechanism certifies the particular even \(N\).

This is not a universal coverage theorem: it still depends on the exact seed value \(Y_c\), and the shift exponent \(s\) must be large compared with \(\log c\). It does, however, expose the precise binary obstruction. Writing \(N=2^s+c\), a successful certificate requires the remainder \(c\) to be small enough relative to the chosen power \(2^s\), and its seed valuation must satisfy (3).

## 4. Exact finite regression

The companion script evaluates \(Y_{2,8}\) using exact rational arithmetic, checks \(v_2(Y_{2,8})=-1\), and verifies the first shifted examples \(s=8,\ldots,12\) by direct rational arithmetic. It also implements the exact criterion (3) for any seed value supplied by the same rational evaluator.

The infinite statement (1)–(2) follows from the fixed-seed theorem and the exact seed calculation; the finite list is only an independent regression check.

## 5. Research consequence

The parameter-coverage question now splits cleanly:

- Odd \(N\): the arbitrary odd-part block theorem supplies seeds \(c=A2^u-1\).
- Even \(N\): use even seeds \(c\), beginning with \(c=2\), \(c=14\), and other exact seed values satisfying (3).

A genuine all-even theorem would require proving that every sufficiently large even \(N\) admits at least one decomposition \(N=2^s+c\) whose seed satisfies (3), or replacing the fixed-seed shift argument by a direct uniform estimate. No such universal statement is claimed here.
