# Newton 展开与全阶共振整除

日期：2026-11-20（Asia/Shanghai）。基线提交：
[b8cbc502](https://github.com/epsilon-lain/yohaku/commit/b8cbc502)。

本节解决 [全局赋值续研](BBP-GLOBAL-VALUATION-FOLLOWUP.zh.md) §8 的共振
加权和命题。结论覆盖任意额外整除位数，不再截断在模十六。
它推出归一化量的全局二进整性，并结合已证的局部差式完成全部四的倍数上的
精确赋值公式。归一化量自身的模四或模八公式仍是另一项任务。

## 1. 一个更一般的二项式因子定理

设
\[
 \frac y{1+2y+2y^3-y^4}=\sum_{n\ge0}a_ny^n,
 \qquad g_n=\frac{2a_n}{n+1}.
\]
固定正整数 \(J\)，假设 \(8\mid J\)。对任意整数 \(R\ge J\)，定义
\[
 S_{J,R}=\sum_{r=J}^{R}\binom rJ g_{r-1}.
\]
则存在二进整数 \(T_{J,R}\)，满足
\[
 \boxed{S_{J,R}=\binom RJ T_{J,R},\qquad T_{J,R}\in\mathbb Z_2,}
 \tag{1}
\]
而且
\[
 \boxed{T_{J,R}\equiv
       \binom{R-J}{2}+\binom{R-J}{4}\pmod2.}
 \tag{2}
\]
这里所有二项式系数都按通常整数定义，超过上标时取零。

特别取 \(R=4m-3\)。当 \(m\) 为偶数，\(R-J\equiv5\pmod8\)，
所以 \(T_{J,R}\) 是奇单位；当 \(m\) 为奇数，\(R-J\equiv1\pmod8\)，
所以 \(T_{J,R}\) 是偶二进整数。

## 2. 八阶差分的精确闭合

令 \(E\) 为移位算子，即 \((Ea)_n=a_{n+1}\)，并令 \(\Delta=E-1\)。
核递推给出
\[
 (E^4+2E^3+2E-1)a_n=0\qquad(n\ge0).
\]
以下是整系数多项式恒等式：
\[
\begin{aligned}
 (z-1)^8-16z^8
 ={}&(z^4+2z^3+2z-1)\\
 &\cdot(-15z^4+22z^3-16z^2+6z-1).
\end{aligned}
\]
因此
\[
 \boxed{\Delta^8a_n=16a_{n+8}\quad(n\ge0).}
 \tag{3}
\]
这是一条精确差分恒等式，不是低位近似。反复使用 (3)，对
\(\ell=8t+b\)、\(t\ge0\)、\(0\le b\le7\)，有
\[
 \Delta^\ell a_{J-1}=16^t\Delta^b a_{J+8t-1}.
 \tag{4}
\]

## 3. Newton 展开保留整个二项式因子

记
\[
 d_\ell=\Delta^\ell a_{J-1},\qquad
 c_\ell=\frac{2d_\ell}{J+\ell}.
\]
由 \(\binom rJ/r=\binom{r-1}{J-1}/J\)，
\[
 S_{J,R}=\frac2J\sum_{r=J}^R\binom{r-1}{J-1}a_{r-1}.
\]
对有限序列应用准确的 Newton 公式
\[
 a_{J-1+s}=\sum_{\ell=0}^s\binom s\ell d_\ell,
\]
再交换两个有限求和。所需的有限和恒等式为
\[
 \sum_{r=J+\ell}^{R}
 \binom{r-1}{J-1}\binom{r-J}{\ell}
 =\binom{J+\ell-1}{\ell}\binom{R}{J+\ell}.
\]
化简阶乘后得到
\[
 \boxed{
 S_{J,R}=\binom RJ
       \sum_{\ell=0}^{R-J}c_\ell\binom{R-J}{\ell}.}
 \tag{5}
\]
证明任务因此变成：逐项证明 \(c_\ell\) 是二进整数，并确定哪些
\(c_\ell\) 是奇数。这里可以逐项证明，是因为八阶差分已经把危险分母
\(J+\ell\) 与同一个索引处的 Pell 系数对齐。

## 4. 所有 Newton 系数的整性与奇偶

核序列模四以八为周期，一个周期为
\[
 (a_0,\ldots,a_7)\equiv(0,1,2,0,2,1,0,0)\pmod4.
\]
代入递推可验证接下来的四项重新等于首四项，因此周期对所有非负索引成立。
模二的周期进一步缩为四。故对每个正八的倍数 \(n\)，
\[
 \Delta^2a_{n-1}\equiv1\pmod2,\qquad
 \Delta^4a_{n-1}\equiv2\pmod4,\qquad
 \Delta^6a_{n-1}\equiv0\pmod2.
 \tag{6}
\]

现在写 \(\ell=8t+b\)，令 \(n=J+8t\)，仍有 \(8\mid n\)。
当 \(b\ne0\) 时，\(v_2(n+b)=v_2(b)\)，最多为二。
结合 (4)、(6)，可直接估计 \(c_\ell\)。

当 \(b=0\) 时，分母可能含任意高次二的幂，不能丢掉其精确结构。
Pell 公式
\[
 a_{n-1}=P_{n/2}^2,\qquad v_2(P_j)=v_2(j)
\]
给出
\[
 v_2(c_{8t})
 =v_2\!\left(\frac{2\cdot16^tP_{n/2}^2}{n}\right)
 =4t+v_2(n)-1\ge4t+2.
 \tag{7}
\]
所以高分母被同一点的平方 Pell 系数完全吸收。

汇总全部八个余类：

| \(b\) | \(v_2(c_{8t+b})\) |
| --- | --- |
| \(0\) | \(4t+v_2(J+8t)-1\ge4t+2\) |
| \(1,3,5,7\) | 至少 \(4t+1\) |
| \(2\) | 恰为 \(4t\) |
| \(4\) | 恰为 \(4t\) |
| \(6\) | 至少 \(4t+1\) |

因此每个 \(c_\ell\in\mathbb Z_2\)，并且
\[
 \boxed{c_\ell\text{ 为奇数，当且仅当 }\ell=2\text{ 或 }4.}
 \tag{8}
\]
把 (8) 代入 (5) 就同时证明 (1)、(2)。

## 5. 全阶共振命题及无限高需求族

现在取 \(m=A2^u\)，\(A\) 正奇，\(u\ge0\)，以及
\[
 J=2^{u+3}k,\qquad k\text{ 为正奇数},\qquad
 1\le k\le(A-1)/2.
\]
令 \(R=4m-3\)，\(\sigma=v_2\binom{(A-1)/2}{k}\)。
二进借位计数依次剥去末尾数字，给出准确赋值
\[
 v_2\binom RJ
 =v_2\binom{m-1}{J/4}
 =v_2\binom{A-1}{2k}
 =\sigma.
\]
由 (1)、(2)，得到
\[
 \boxed{
 \begin{aligned}
 u\ge1&:\quad v_2(S_J)=\sigma,\\
 u=0&:\quad v_2(S_J)\ge\sigma+1.
 \end{aligned}}
 \tag{9}
\]
当 \(u=0,k=(A-1)/2\) 时，\(R-J=1\)，Newton 和只含 \(c_0,c_1\)；
二者都为偶数，故零二项式端点也已包含在证明内。

沿用已经证明的纯进位不等式
\[
 v_2\binom{3A}{A}+\sigma\ge v_2(A+k),
\]
式 (9) 证明了全部共振位置所需的
\[
 \boxed{v_2(S_J)\ge v_2(A+k)-\Gamma_A,
 \qquad \Gamma_A=v_2\binom{3A}{A}.}
\]
右侧可以任意大，不再有四位的限制。

例如，对任意 \(v\ge2\) 取
\[
 A=2^v+1,\qquad k=2^{v-1}-1.
\]
此时 \(\Gamma_A=0\)，且
\(\binom{(A-1)/2}{k}=2^{v-1}\)。所以对这族任意高需求点，
\[
 v_2(S_J)=v-1\quad(u\ge1),\qquad
 v_2(S_J)\ge v\quad(u=0).
\]
这是一条对所有 \(v\) 的证明，不是继续扩大有限扫描。

## 6. 全局整性与全部四的倍数

旧文已经证明：非共振系数对
\[
 B_N=2\binom{3(N+1)}{N+1}Y_{N,4N}
\]
的积分贡献是二进整数，BBP 前缀的贡献也是二进整数；剩下的共振项正由
本节的加权和条件控制。因此
\[
 \boxed{B_N\in\mathbb Z_2\qquad(N\ge0).}
\]
这完成了归一化整性部分，而且足以去掉此前偶数传递定理的进位差条件。

具体地，取正整数 \(N\)，假设 \(4\mid N\)，并记
\[
 \Gamma_N=v_2\binom{3N}{N}=2s_2(N)-s_2(3N),
 \qquad H_N=\frac{(8N)!(4N)!}{(12N)!}.
\]
由 \(B_{N-1}\in\mathbb Z_2\)，
\[
 v_2(Y_{N-1,4N-4})\ge-1-\Gamma_N,
 \qquad v_2(16Y_{N-1,4N-4})\ge3-\Gamma_N.
\]
[偶数相邻传递证明](BBP-EVEN-DYADIC-TRANSFER.zh.md) 已经对每个 \(4\mid N\)
证明
\[
 \frac{Y_{N,4N}-16Y_{N-1,4N-4}}{H_N}\in\mathbb Z_2^\times,
 \qquad v_2(H_N)=-\Gamma_N.
\]
因此该差项的赋值为 \(-\Gamma_N\)，严格低于旧阶项的赋值。由此得到
\[
 \boxed{
 v_2(Y_{N,4N})=s_2(3N)-2s_2(N)=-\Gamma_N
 \qquad(N\ge4,\ 4\mid N).}
\]
相应的既约分母满足
\[
 \boxed{v_2(Q_{N,4N})=4N+\Gamma_N.}
\]
这里没有奇部大小或进位差的附加条件。这完成了先前仅有有限证据支持的
全体四倍数命题，也证明了这些点上的终端非消去。

归一化量的全局奇偶及全部奇数阶的精确赋值，见同一轮的
[全局奇偶补充证明](BBP-GLOBAL-PARITY.zh.md)。

同轮的[模八局部分支证明](BBP-TWO-MOD-EIGHT-VALUATION.zh.md)进一步完成了
全部 $N\equiv2\pmod8$ 的精确赋值。尚未解决的是 \(N\equiv6\pmod8\) 的一般精确赋值或统一上界、
\(M=4N+o(N)\) 的任意逐点扰动，以及全体有理逼近的原始目标。
上述结论也没有单独证明 \(B_N\) 模四或模八的猜测公式。

## 7. 复算

[复算脚本](verify_bbp_resonance_newton.py) 使用原四阶核递推与精确 Fraction 算术，
比较原加权和和独立的 Newton 表达式，并逐项核对系数赋值表。
另外核对多项式因子恒等式、二项式因子赋值、奇偶结论和高需求应力族。
有限复算只验证恒等式的实现与下标；全阶结论来自上述有限差分证明。

实际运行退出码为零：848 个不同的精确因子分解检查，合计 44,308 个
Newton 系数检查；其中包含 \(1\le m\le64\) 的全部 341 个共振位置，以及
21 个应力点，最高额外整除需求为八位。另核对了 65 个原始八阶差分恒等式，
并从完整有理数定义检查 \(0\le N\le24\) 的归一化整性及其中四倍数的赋值。
全部一致，无失败。独立审计另行核对了多项式因子、Newton 前因子、模四周期
和最短求和区间的端点。

默认输出为[紧凑 JSON 证书](bbp-resonance-newton-verification.json)，保留准确计数、
全部 21 个应力点与 25 个完整有理数归一化核对。若需要逐点审查所有 848 个
不同因子分解，可运行

```bash
python verify_bbp_resonance_newton.py --full-json newton-full-verification.json
```

可选完整输出与默认紧凑证书使用同一次精确计算；两者不改变检查范围。
