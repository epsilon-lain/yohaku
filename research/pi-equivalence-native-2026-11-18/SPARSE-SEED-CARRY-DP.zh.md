# Exact digit-DP for the seed threshold \(C_A\)

Date: 2026-11-19  
Purpose: compute the exact Kummer carry maximum in \(O(\log A)\), rather than scanning all \(0\le k\le(A-1)/2\). This makes the arbitrary-odd-part seed theorem algorithmically usable for large \(A\).

## 1. Quantity to compute

For odd \(A\ge1\), define
\[
C_A=\max_{0\le k\le K}v_2\binom{A+k}{k},
\qquad K=(A-1)/2,
\]
and
\[
\gamma_A=v_2\binom{A+K}{K}.
\]
By Kummer's theorem, each valuation is the number of binary carries when adding \(A\) and \(k\). Thus \(C_A\) is a finite-state optimization problem over the binary digits of \(k\), subject to \(k\le K\).

## 2. Low-to-high digit DP

Process bits from least significant to most significant. Maintain two binary states:

- \(b\in\{0,1\}\): borrow in the subtraction \(K-k\);
- \(c\in\{0,1\}\): carry in the addition \(A+k\).

At bit \(i\), choose \(e\in\{0,1\}\) as the \(i\)-th bit of \(k\). Let \(K_i,A_i\) be the corresponding bits. The outgoing borrow and carry are
\[
b'=\mathbf 1_{\{K_i-e-b<0\}},
\qquad
c'=\left\lfloor\frac{A_i+e+c}{2}\right\rfloor.
\]
The transition contributes \(c'\) to the score. After all bits of \(K\) and \(A\) have been processed, append one zero bit to flush the addition carry and require the final subtraction borrow to be zero. Maximizing the accumulated carry score over all paths gives exactly \(C_A\).

There are only four states \((b,c)\) and at most two transitions per state per bit. Therefore the computation takes \(O(\log A)\) time and \(O(1)\) state memory (apart from storing the input integer).

For \(\gamma_A\), simply count the carries in the single binary addition \(A+K\).

## 3. Consequence for the seed theorem

The arbitrary-odd-part seed theorem requires
\[
u+3\ge2C_A+11,
\quad\text{equivalently}\quad
u\ge2C_A+8.
\]
The DP gives the exact smallest permitted \(u\) for every odd part \(A\), while also returning the seed valuation \(-1-\gamma_A\). This is sharper than the coarse logarithmic sufficient bound and allows large odd parts to be tested without enumerating \(O(A)\) values of \(k\).

This DP does not itself prove coverage of all even \(N\): for \(N=2^s+A2^u-1\), the odd part of \(N+1\) must have the form \(A+2^{s-u}\), and the exact threshold \(u\ge2C_A+8\) must still hold.
