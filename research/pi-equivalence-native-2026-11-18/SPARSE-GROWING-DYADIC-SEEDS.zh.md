# A growing two-parameter family from dyadic seeds

Date: 2026-11-19  
Status: **proved corollary of the two existing 2-adic theorems**.

This combines (i) the exact slope-four block theorem for \(N=A2^s-1\) with fixed odd part \(A\), and (ii) the fixed-seed translation theorem for \(N=2^s+c\). It yields a family with a seed \(c\) that itself grows with a second parameter.

## 1. Exact valuation of the dyadic seeds \(c=2^u-1\)

Set
\[
c=2^u-1,\qquad N=c,\qquad M=4c.
\]
In the notation of the slope-four block theorem, \(N+1=A2^s\) with \(A=1\), \(s=u\), and
\[
L=8(N+1)=2^{u+3},\quad h=u+3,\quad
m=M+1=4\cdot2^u-3,\quad
q=\left\lfloor\frac{M+3}{4}\right\rfloor=2^u-1.
\]
For every \(0\le i\le M+4=4\cdot2^u\), we have \(i<2^{u+3}=L\). Hence
\[
\left\lfloor\frac{i}{2^h}\right\rfloor=0,\qquad
c_i=v_2\binom{L+i}{i}=0.
\]
Thus the block theorem's \(C=\max_i c_i\) is exactly zero. Its hypotheses hold whenever \(u+3=h\ge11\), i.e. \(u\ge8\), and \(v_2(q)=0\le u\). Also \(c_m=0\). Its exact formula gives
\[
v_2(2Y_{c,4c})=v_2(q)-c_m=0.
\]
Therefore
\[
\boxed{v_2(Y_{2^u-1,\,4(2^u-1)})=-1\qquad(u\ge8).}
\tag{1}
\]

This is not an extrapolation from samples: it is a direct specialization of the proved block theorem, with every hypothesis evaluated explicitly.

## 2. Apply the fixed-seed translation theorem with a growing seed

The seed-translation theorem says: if \(c\ge1\), \(Y(c):=Y_{c,4c}\ne0\), \(\nu=v_2(Y(c))<4c-3\), and \(d_c=\lfloor\log_2(12c+9)\rfloor\), then
\[
v_2(Y_{2^s+c,\,4(2^s+c)})=\nu
\]
whenever
\[
s\ge\max(2,d_c-1),\qquad s+2-2d_c>\nu.
\]

Now take \(c=2^u-1\), \(u\ge8\). By (1), \(\nu=-1\). Moreover,
\[
12c+9=12\cdot2^u-3,
\]
so
\[
d_c=\lfloor\log_2(12\cdot2^u-3)\rfloor=u+3.
\]
The seed hypothesis \(-1<4c-3\) is automatic. The two shift conditions reduce to
\[
s\ge u+2,\qquad s+2-2(u+3)>-1,
\]
and hence are jointly equivalent to \(s\ge2u+4\). We conclude
\[
\boxed{
v_2(Y_{\,2^s+2^u-1,\,4(2^s+2^u-1)})=-1
\quad\text{for all }u\ge8,\ s\ge2u+4.
}
\tag{2}
\]
Consequently
\[
\boxed{
v_2(Q_{N,4N})=4N+1,\quad
N=2^s+2^u-1,\quad u\ge8,\ s\ge2u+4.
}
\tag{3}
\]

## 3. What this adds

The earlier \(c=14\) and \(c=1\) results give two fixed-seed rays. Equation (2) gives a two-parameter region: for each sufficiently large dyadic scale \(2^s\), every \(u\) with \(8\le u\le(s-4)/2\) supplies a distinct \(N\) with the exact same 2-adic valuation \(v_2(Y)=-1\).

This is still a sparse subset of all \(N\). It does not prove terminal nonvanishing for every even \(N\), nor does it cover all \(M=4N+o(N)\). It is a stronger explicit family obtained without any new Padé construction.

## 4. Exact finite seed regression

The companion script evaluates the original rational definition of \(Y(c)\) using exact fractions, not the seed-shift recurrence, for \(c=2^u-1\) and \(8\le u\le12\). It checks \(v_2(Y(c))=-1\). These are independent finite regressions of the seed values; the infinite seed statement is supplied by Section 1's specialization of the block theorem.
