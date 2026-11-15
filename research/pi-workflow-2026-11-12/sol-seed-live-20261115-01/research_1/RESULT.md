# A certified finite-denominator minimum for π

**Result.** With the supplied convention (a_0=3), the already known convergent denominator (q_{28420}) is the **unique** minimizer of

\[
q\|q\pi\|\quad\text{over integers }1\le q<q_{28421}.
\]

The two exact denominator boundaries are saved in `q28420.txt` (14593 decimal digits) and `q28421.txt` (14598 decimal digits). The minimum has the strict enclosure

\[
0.0000127178573727574566035844693935801274
<q_{28420}\|q_{28420}\pi\|
<0.0000127178573727574566035844693935801275.
\]

This strengthens the **scope** of the supplied finite witness. It finds no new witness, extends no certified continued-fraction prefix, and gives no conclusion about denominators (q\ge q_{28421}), an asymptotic liminf, or whether π is badly approximable.

## Computation and its dependency

`certify_finite_minimum.py` imports the arctangent-enclosure helpers from `../common/check_runB_independent.py`, checks that file's Gaussian-integer identity conditions, and reconstructs the 28422-term prefix from a strict rational π enclosure at scale (10^{30000}). It independently writes this session's convergent recursion and gap checks, but **does not provide an independent π formula or independent implementation of the enclosure**.

The executed script found

\[
\max_{1\le j\le28420} a_j=20776\quad\text{(uniquely at }j=431),
\qquad a_{28421}=78629.
\]

It also checks by exact integer arithmetic that the upper endpoint for the target value is below both (1/2) and (1/20778), and that (0<q_{28420}\pi-p_{28420}<1/2). Thus (p_{28420}) is indeed the nearest integer. Full machine-readable output is `finite-minimum.json`.

Reproduce from the project root:

```sh
python research_1/certify_finite_minimum.py
```

Only Python's standard library is used. Assertions must remain enabled. The supplied baseline provides the analytic justification for the strict π enclosure; its source is `../common/RUNB-INDEPENDENT.md` and the checker's module docstring. The mathematical argument below is provided in full, with no external reference needed.

## Proof

Write the simple continued fraction of π as ([a_0;a_1,a_2,\ldots]), and define its convergents using

\[
p_{-2}=0,\quad p_{-1}=1,\quad q_{-2}=1,\quad q_{-1}=0,
\qquad p_n=a_np_{n-1}+p_{n-2},\quad q_n=a_nq_{n-1}+q_{n-2}.
\]

All indices (n) below are nonnegative integers. Here (q_0=1,q_1=7), so the denominators are strictly increasing. Let (x_{n+1}=[a_{n+1};a_{n+2},\ldots]) be the complete quotient; it satisfies (a_{n+1}<x_{n+1}<a_{n+1}+1). Substitution of the continued-fraction tail and the determinant recurrence give

\[
\pi=\frac{p_nx_{n+1}+p_{n-1}}{q_nx_{n+1}+q_{n-1}},
\qquad p_nq_{n-1}-p_{n-1}q_n=(-1)^{n-1},
\]

and hence, writing (\varepsilon_n=q_n\pi-p_n),

\[
\varepsilon_n=\frac{(-1)^n}{q_nx_{n+1}+q_{n-1}},
\qquad q_n|\varepsilon_n|
=\frac1{x_{n+1}+q_{n-1}/q_n}
>\frac1{a_{n+1}+2}.
\]

The last inequality uses (0\le q_{n-1}/q_n<1). In particular adjacent errors are nonzero and have opposite signs.

We next prove the needed best-approximation property, including arbitrary, possibly noncoprime integer pairs. Fix (n) and integers (p,q) with (0<q<q_{n+1}). The adjacent convergent vectors form an integer basis since their determinant has absolute value one. Therefore unique integers (A,B) satisfy

\[
(p,q)=A(p_n,q_n)+B(p_{n+1},q_{n+1}).
\]

If (B\ge1), the denominator condition forces (A\le-1); if (B\le-1), positivity of (q) forces (A\ge1). In either case (A\varepsilon_n) and (B\varepsilon_{n+1}) have the same sign, so

\[
|q\pi-p|=|A\varepsilon_n+B\varepsilon_{n+1}|>|\varepsilon_n|.
\]

If (B=0), then (A\ge1), giving (|q\pi-p|=A|\varepsilon_n|\ge|\varepsilon_n|), with equality only for (A=1). Consequently, for (q_n\le q<q_{n+1}), choosing (p) to be a nearest integer to (q\pi) gives

\[
q\|q\pi\|\ge q|\varepsilon_n|\ge q_n|\varepsilon_n|,
\]

with equality only when ((p,q)=(p_n,q_n)). No coprimality assumption and no Legendre (1/2) condition are required.

Every integer (1\le q<q_{28421}) lies in exactly one interval (q_n\le q<q_{n+1}) for (0\le n\le28420). For (n<28420), the certified prefix gap gives

\[
q\|q\pi\|\ge q_n|\varepsilon_n|
>\frac1{a_{n+1}+2}\ge\frac1{20778}
>q_{28420}\|q_{28420}\pi\|.
\]

For (n=28420), the best-approximation inequality instead gives a value at least the target, with equality only at (q=q_{28420}). These cases prove the stated unique minimum.

## Open questions

1. What is the first denominator after (q_{28421}-1) at which a smaller value occurs? The present prefix does not answer this.
2. Can a substantially longer certified prefix yield useful new finite witnesses within a larger authorized computation budget?
3. Does any structure of π force infinitely many unusually good approximations? Nothing here addresses that asymptotic problem.
