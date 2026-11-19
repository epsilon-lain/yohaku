# BBP 全局归一化的奇偶性与全部奇数阶赋值

日期：2026-11-20（北京时间）。基线提交：`b8cbc502dd4e7e44bf08832ffab45d22bfb355f0`。

本文使用[全阶共振 Newton 引理](BBP-RESONANCE-NEWTON.zh.md)，证明

\[
\boxed{B_N\in\mathbb Z_2,\qquad B_N\equiv N\pmod2\qquad(N\ge0),}
\]

其中 \(B_N=2\binom{3(N+1)}{N+1}Y_N\)。特别地，全部正奇数 N 满足

\[
\boxed{v_2(Y_N)=-1-\Gamma(N+1),\qquad
v_2(Q_{N,4N})=4N+1+\Gamma(N+1).}
\]

这里 \(\Gamma(n)=v_2\binom{3n}{n}\)，\(Q_{N,4N}\) 是 \(X_{N,4N}=Y_N/16^N\) 的正既约分母。本文不宣称全局模 4 或模 8 猜想已被证明。

## 1. 记号与原始定义

全文使用 \(Y_N=Y_{N,4N}\)，并约定 \(v_2(2)=1\)。写

\[
m=N+1=A2^u,\quad A\ge1\text{ 为奇数},\quad u\ge0,
\]
\[
R=4m-3,\quad L=8m,\quad h=u+3,\quad
C=\binom{3m}{m},\quad w=(A-1)/2.
\]

系数由生成函数定义

\[
h(y)=\frac{y}{(1+2y-y^2)(1+y^2)}=\sum_{k\ge0}a_ky^k.
\]

并令

\[
P_{4N}(y)=\sum_{k=0}^{4N}a_k y^k,\qquad
g_k=\frac{2a_k}{k+1},\qquad
F_R(y)=\sum_{r=1}^{R}g_{r-1}y^r.
\]

因此 \(F_R'(y)=2P_{4N}(y)\) 且 \(F_R(0)=0\)。定义全部二项式变换系数

\[
S_J=[x^J]F_R(1+x)=\sum_{r=\max(1,J)}^R\binom rJ g_{r-1}
\quad(0\le J\le R).
\]

特别地，\(S_0=F_R(1)\)；它不是将含 \(1/J\) 的正阶公式机械代入 J=0。

原定义可写成

\[
Y_N=U_N+\int_0^1x^L P_{4N}(1-x)\,dx,
\]
\[
U_N=\sum_{i=0}^N16^{N-i}f(i),\qquad
f(i)=\frac4{8i+1}-\frac2{8i+4}-\frac1{8i+5}-\frac1{8i+6}.
\]

合并两个偶分母项后，

\[
f(i)=\frac4{8i+1}-\frac1{8i+5}
-\frac{3i+2}{(2i+1)(4i+3)}\in\mathbb Z_2.
\]

故归一化前缀 \(2CU_N\) 始终为偶二进整数。

## 2. 精确分部积分与端点

因为 \(L>0\)、\(F_R(0)=0\)，分部积分的两端均为零：在 x=1 处为 \(F_R(0)=0\)，在 x=0 处有因子 \(x^L\)。于是归一化核部分为

\[
2C\int_0^1x^L P_{4N}(1-x)\,dx
=C\int_0^1x^L F_R'(1-x)\,dx
\]
\[
=CL\int_0^1x^{L-1}F_R(1-x)\,dx
=\boxed{CL\sum_{J=0}^R\frac{(-1)^J S_J}{L+J}.}
\tag{1}
\]

这里的导数符号已计入：\(dF_R(1-x)/dx=-F_R'(1-x)\)。这也是式 (1) 中分部积分后为正号的原因。

## 3. 低二进阶的指标贡献为偶数

已知所有 \(g_k\) 为二进整数，因而全部 \(S_J\) 为二进整数。

对 \(J>0\) 且 \(v_2(J)<h=v_2(L)\)，有

\[
v_2\!\left(\frac{CL}{L+J}\right)
=\Gamma(A)+h-v_2(J)\ge1.
\]

所以这些指标在式 (1) 中全部贡献偶二进整数。

其余正指标必须为 \(J=2^h k\)，其上界精确为

\[
1\le k\le\left\lfloor\frac{4A2^u-3}{2^{u+3}}\right\rfloor
=\frac{A-1}{2}=w.
\tag{2}
\]

本节及后文必须包括偶数 k。全阶 Newton 引理的证明只使用 \(8\mid J\)，所以它同样适用于这些偶数 k。

## 4. 高二进阶指标：逐项整性和奇偶性

对式 (2) 中的任意正整数 k，全阶 Newton 引理给出

\[
S_J=\binom RJ T_J,\qquad T_J\in\mathbb Z_2,
\]
\[
T_J\equiv
\begin{cases}
0\pmod2,&m\text{ 奇},\\
1\pmod2,&m\text{ 偶}.
\end{cases}
\tag{3}
\]

并且 Kummer 的低位约去给出

\[
v_2\binom RJ=v_2\binom wk=:\sigma_k.
\tag{4}
\]

令

\[
D_k=C\frac{A}{A+k}\binom RJ,\qquad
E_k=C\frac{A}{A+k}\binom wk.
\]

二者有相同的二进赋值

\[
v_2(D_k)=v_2(E_k)=\Gamma(A)+\sigma_k-v_2(A+k).
\tag{5}
\]

若 k 为奇数，已有进位不等式表明式 (5) 非负。若 k 为偶数，则 A+k 为奇数，式 (5) 非负直接成立。因此 D_k、E_k 均为二进整数，且由赋值相同可知二者模 2 相同。

又因 \(L/(L+J)=A/(A+k)\)，式 (1) 中此项等于 \(D_kT_J\)。J 为偶数，所以其原符号为正。

- m 奇数时，由 (3)，每个正高阶指标的贡献均为偶数。
- m 偶数时，由 (3)–(5)，每个正高阶指标的贡献模 2 等于 E_k。

这里仅比较模 2；没有把“赋值相同”误用成模 4 或更高精度的同余。

## 5. J=0 与最低端点

Pell 赋值表明 \(g_{r-1}\) 为奇数当且仅当 \(r\equiv2\pmod4\)。在 \(1\le r\le4m-3\) 中，这样的 r 恰有 m-1 个。因此

\[
S_0\equiv m-1\pmod2.
\tag{6}
\]

这已足够，无需使用 S_0 的完整赋值公式。m=1 时 \(R=1\)、\(S_0=g_0=0\)，式 (6) 同样成立。

式 (1) 的 J=0 项为 \(CS_0\)。m 奇数时它为偶数；m 偶数时其模 2 等于 \(C=E_0\)。

结合前缀和低阶指标，已经证明：m 为奇数时 B_N 为偶二进整数；m 为偶数时

\[
B_N\equiv\sum_{k=0}^w E_k\pmod2.
\tag{7}
\]

同时，所有项的逐项整性也已证明。

## 6. 有限 Beta 恒等式使剩余奇偶和等于 1

因为每个 E_k 都为二进整数，将它替换为 \((-1)^kE_k\) 不改变模 2 的值。精确有限恒等式为

\[
\sum_{k=0}^w(-1)^k\frac{A}{A+k}\binom wk
=A\int_0^1t^{A-1}(1-t)^w\,dt
=\frac1{\binom{A+w}{w}}.
\tag{8}
\]

设 \(s_2(n)\) 为二进制数字和。由 A 为奇数，

\[
s_2(w)=s_2(A)-1,\qquad
s_2(A+w)=s_2(3A)-1.
\]

因此

\[
v_2\binom{A+w}{w}
=2s_2(A)-s_2(3A)=\Gamma(A).
\tag{9}
\]

另一方面，\(v_2(C)=\Gamma(m)=\Gamma(A)\)，因为 m 是 A 的二次幂倍数。于是

\[
\frac{C}{\binom{A+w}{w}}\in\mathbb Z_2^\times.
\]

式 (7)–(9) 证明 m 偶数时 B_N 为奇二进整数。A=1、w=0 时，Beta 和只有 k=0 一项，所有公式仍然成立。

综上，\(B_N\) 为二进整数且其奇偶性与 \(N=m-1\) 相同。

## 7. 全部奇数阶的精确赋值及既约分母

若 N 为正奇数，则 B_N 为单位，故

\[
0=v_2(B_N)=1+\Gamma(N+1)+v_2(Y_N),
\]

得到

\[
v_2(Y_N)=-1-\Gamma(N+1).
\]

又 \(X_{N,4N}=Y_N/16^N\)，其赋值严格为负，所以正既约分母满足

\[
v_2(Q_{N,4N})=4N-v_2(Y_N)
=4N+1+\Gamma(N+1).
\]

本文的结论是全局整性、全局奇偶性以及全部奇数阶的精确赋值。全局模 4、模 8 不由本文宣称。部分剩余类的后续分析见 [Newton 商的模 4 分析](BBP-NEWTON-QUOTIENT-MOD4.zh.md)。

## 8. 小范围精确复算

[标准库验证器](verify_bbp_global_parity.py)自含原始定义，用 `Fraction` 分别计算原 Beta 比率和式、分部积分式及二项式变换。默认检查 \(N=0,\ldots,24\)，并检查一组明确列出的奇数 A 的有限 signed-Beta 恒等式；没有扩大旧扫描。

[紧凑证书](bbp-global-parity-verification.json)记录每个端点、原式与分部积分式的精确相等、低阶项的偶性、正高阶指标中奇数与偶数 k 的处理、S_0 的奇偶性，以及奇数 N 的既约分母赋值。无限结论来自正文证明，不依赖这些有限复算。
