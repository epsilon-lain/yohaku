# Newton 商的模四表与 \(N\equiv2\pmod4\) 的归一化整除性

日期：2026-11-20（北京时间）。基线提交：`b8cbc502dd4e7e44bf08832ffab45d22bfb355f0`。

本补充只使用已证明的[全阶 Newton 因子式](BBP-RESONANCE-NEWTON.zh.md)，再取模 \(4\)。全局奇偶结论另见 [BBP-GLOBAL-PARITY.zh.md](BBP-GLOBAL-PARITY.zh.md)。

## 1. 记号

令 \(m=N+1\)、\(K=4m-3\)，并设 \(8\mid J\)、\(1\le J\le K\)。沿用
\[
g_r=\frac{2a_r}{r+1},\qquad
S_J=\sum_{r=J}^K\binom rJ g_{r-1}.
\]
已证精确因子式为
\[
S_J=\binom KJ T_{K,J},\qquad
T_{K,J}=\sum_{\ell=0}^{K-J}c_\ell\binom{K-J}{\ell},
\qquad
c_\ell=\frac{2\Delta^\ell a_{J-1}}{J+\ell}.
\]
所有 \(c_\ell\) 均为二进整数。

## 2. 模四时只有前八项

由 \(\Delta^8a=16E^8a\)，写 \(\ell=8t+b\)、\(n=J+8t\)。前一证明给出：
\[
\begin{array}{c|c}
b&\nu_2(c_{8t+b})\\ \hline
0&4t+\nu_2(n)-1\ge4t+2\\
1,3,5,7&\ge4t+1\\
2,4&4t\\
6&4t+3
\end{array}
\]
故 \(t\ge1\) 时全部被 \(16\) 整除。

令 \(p=P_{J/2}\)、\(q=P_{J/2+1}\)，则 \(4\mid p\)、\(q\) 为奇数。由 Pell 递推直接计算，
\[
\begin{aligned}
\Delta^2a_{J-1}&=(p+q)^2,\\
\Delta^4a_{J-1}&=2(p+3q)^2,\\
\Delta^6a_{J-1}&=8(2p+5q)^2.
\end{aligned}
\]
因此
\[
c_2=\frac{(p+q)^2}{J/2+1}\equiv1\pmod4,\qquad
c_4=\frac{(p+3q)^2}{J/4+1}\equiv1+J/4\pmod4,
\]
并且 \(c_6\equiv0\pmod4\)。此外 \(c_0\equiv0\pmod4\)。

数列 \(a_r\bmod2\) 在 \(r\equiv1\pmod4\) 时为 1，其余为 0。将前向差分展开可得 \(\Delta a_{J-1},\Delta^5a_{J-1},\Delta^7a_{J-1}\) 为偶数，而 \(\Delta^3a_{J-1}\) 为奇数。相应分母 \(J+b\) 为奇数，遂得完整表：
\[
\boxed{(c_0,c_1,\ldots,c_7)\equiv
(0,0,1,2,1+J/4,0,0,0)\pmod4.}
\]
令 \(D=K-J\)，得到
\[
\boxed{
T_{K,J}\equiv
\binom D2+2\binom D3+(1+J/4)\binom D4\pmod4.
}
\tag{1}
\]

## 3. 原先 \(u=0\) 的两个实验分支均成为定理

令 \(m=A\) 为奇数，\(w=(A-1)/2\)，\(J=8k\)，其中 \(k\) 为奇数且 \(1\le k\le w\)，并令 \(\sigma=\nu_2\binom wk\)。已知
\[
\nu_2\binom KJ=\sigma.
\]
此时 \(1+J/4\equiv3\pmod4\)。

若 \(A\equiv1\pmod4\)，则 \(D=4A-3-8k\equiv9\pmod{16}\)，式 (1) 的右端为 \(2\bmod4\)。若 \(A\equiv3\pmod4\)，则 \(D\equiv1\pmod{16}\)，右端为 \(0\bmod4\)。这里对 \(j\le4\)，\(\binom D j\bmod4\) 只依赖于 \(D\bmod16\)，可由 Vandermonde 恒等式直接核对。故
\[
\boxed{
\begin{array}{ll}
A\equiv1\pmod4:&\nu_2(S_{8k})=\sigma+1,\\
A\equiv3\pmod4:&\nu_2(S_{8k})\ge\sigma+2.
\end{array}}
\tag{2}
\]
这两条是全称证明，不再仅是有限样本观察。

## 4. 全体 \(N\equiv2\pmod4\) 都有 \(4\mid B_N\)

定义
\[
C=\binom{3m}{m},\qquad
\Gamma_m=\nu_2(C),\qquad L=8m,\qquad
B_N=2C\,Y(N).
\]
本节假设 \(N\equiv2\pmod4\)，所以 \(m\equiv3\pmod4\) 为奇数，且 \(\Gamma_m\ge2\)：在 \(m+2m\) 的二进制加法中，第 1、2 位至少连续产生两次进位。

定义积分核的多项式原函数
\[
F(y)=\sum_{r=1}^{K}g_{r-1}y^r,\qquad F'(y)=2P_{4N}(y).
\]
令 \(S_0=\sum_{r=1}^{K}g_{r-1}\)。分部积分给出精确恒等式
\[
B_N=
2C\,16^NS_N^{\mathrm{BBP}}
+CL\sum_{J=0}^{K}\frac{(-1)^J S_J}{L+J}.
\tag{3}
\]
其中 \(S_N^{\mathrm{BBP}}\) 表示原 BBP 截断，以免与本补充的 \(S_J\) 混淆。

逐类检查式 (3)：

1. 原 BBP 项 \(16^NS_N^{\mathrm{BBP}}\in\mathbb Z_2\)，故第一项赋值至少 \(\Gamma_m+1\ge3\)。
2. \(J=0\) 项为 \(CS_0\)。由 \(g_{r-1}\) 恰在 \(r\equiv2\pmod4\) 时为奇数，而 \(1\le r\le4m-3\) 中这类指标有 \(m-1\) 个，知 \(S_0\) 为偶数。因此该项赋值至少 3。
3. 对 \(J>0\) 且 \(\nu_2(J)<3\)，有 \(\nu_2(L+J)=\nu_2(J)\)。由于 \(S_J\in\mathbb Z_2\)，该项赋值至少 \(\Gamma_m+3-\nu_2(J)\ge3\)。
4. 剩余指标写作 \(J=8k\)，\(1\le k\le w=(m-1)/2\)。有
   \[
   \frac{CL S_{8k}}{L+8k}
   =\frac{Cm}{m+k}\binom K{8k}T_{K,8k}.
   \]
   当 \(k\) 为偶数时，\(m+k\) 为奇数，而已证 Newton 奇偶结论给出 \(T_{K,8k}\in2\mathbb Z_2\)，故赋值至少 \(\Gamma_m+1\ge3\)。
5. 当 \(k\) 为奇数时，二进进位不等式
   \[
   \Gamma_m+\nu_2\binom wk\ge\nu_2(m+k)
   \]
   以及 \(\nu_2\binom K{8k}=\nu_2\binom wk\) 表明前面的归一化因子为二进整数。由式 (2)，\(T_{K,8k}\in4\mathbb Z_2\)，故该项被 \(4\) 整除。

以上覆盖全部指标。因而
\[
\boxed{N\equiv2\pmod4\quad\Longrightarrow\quad B_N\in4\mathbb Z_2.}
\]
等价地，
\[
\boxed{\nu_2(Y(N))\ge1-\Gamma(N+1)\qquad(N\equiv2\pmod4).}
\]
这是该剩余类的下界，不是精确赋值，也不等于证明原目标中的全体偶数上界。

同轮的[模八局部分支证明](BBP-TWO-MOD-EIGHT-VALUATION.zh.md)进一步把本节结果细分为：
$N\equiv2\pmod8$ 时 $v_2(B_N)=2$，$N\equiv6\pmod8$ 时 $v_2(B_N)\ge3$。
后一分支的一般赋值上界仍待证明。

## 复算

[verify_bbp_newton_quotient_mod4.py](verify_bbp_newton_quotient_mod4.py) 仅使用 Python 标准库，以精确整数和 Fraction 核对系数表、六组有限 Newton 因子式及六个小阶归一化整除性样本。结果见 [bbp-newton-quotient-mod4-verification.json](bbp-newton-quotient-mod4-verification.json)。

可选地传入上一轮已保存的模余数证书，复核其 \(N\equiv2\pmod4\) 子集；该操作不会重新运行或扩大扫描。

所附证书记录了实际读回的旧残数文件名及 SHA-256。若需从仓库脚本重新生成同一范围的完整残数，
验证器也接受当前仓库的输出格式：

```bash
python verify_bbp_global_valuation_followup.py --full-json bbp-full-residues.json
python verify_bbp_newton_quotient_mod4.py --certificate bbp-full-residues.json
```

这两个复算命令不属于无限证明的假设。后续研究未新增 Yohaku 原生任务。
