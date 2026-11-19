# 一个巨峰怎样分配到相邻的翻倍区间

令 $\alpha$ 为无理数，$w_k=1/\sin^2(\pi k\alpha)$，$S(N)=\sum_{k=1}^N w_k$，$D_j=S(2^{j+1})/S(2^j)$。对 $\alpha=1/\pi$，被观测的就是整数正弦。以下命题给出任意很大的 $D_j$ 的位置、首项系数、后续翻倍次数和后续增长的总乘积。它们允许验证长度超过 $10^{14592}$ 的区间。

## 先从一个翻倍区间找出异常分数

取 $M=2^j$，让 $1\le n\le2M$ 使 $\delta=\|n\alpha\|$ 最小，$m$ 是离 $n\alpha$ 最近的整数。若 $D_j>\pi^4/12$，则

$$
M<n\le2M,\qquad \gcd(m,n)=1,\qquad
\epsilon=n|n\alpha-m|\le \frac{\pi^2}{\sqrt{3D_j}} .
$$

证明。把 $0,\alpha,\ldots,2M\alpha$ 模 1 排在圆周上，两点相距至少 $\delta$。原点两侧的第 $l$ 个点各至少离原点 $l\delta$。用 $|\sin(\pi x)|\ge2\|x\|$，得 $S(2M)\le\pi^2/(12\delta^2)$。又 $w_n\ge1/(\pi^2\delta^2)$。若 $n\le M$，两式已给出 $D_j\le\pi^4/12$。若 $m,n$ 有公因数，约分后到最近整数的距离更小，矛盾。抽屉原理给出 $S(M)\ge(M+1)^2/\pi^2$，代入 $n\le2M$ 得最后一式。当 $\epsilon<1/4$ 时，区间 $(M,2M]$ 中不可能还有另一对归一化误差 $<1/4$ 的近似。不同分数的非零整数行列式的绝对值至多为两个误差分别乘上分母比之和，两个分母比均小于 2。同一既约分数的下一个整数倍分母大于 $2M$。

## 大峰的系数由裴蜀逆元给出

反过来，给任意既约近似 $m/n$，令 $M<n\le2M$，$M=2^j$，沿一列这样的点使 $\epsilon\to0$。令 $u$ 为 $m$ 模 $n$ 的逆元，$\rho=M/n$，定义

$$
B=\frac{\pi^2}{6}
 +\sum_{d=1}^\infty
   \frac{\mathbf 1_{\{\|du/n\|\ge1-\rho\}}}{d^2}.
$$

则一致地有

$$
\epsilon^2 D_j=B^{-1}+O(\epsilon+n^{-1}),\qquad
\frac{3}{\pi^2}\le B^{-1}\le\frac{6}{\pi^2}.
$$

在 $1\le k\le M$ 内，把 $k\alpha$ 换成 $km/n$ 时，$|\sin(\pi k\alpha)|$ 的改变量至多为 $\pi\epsilon/n$，有理格点处的绝对值至少为 $2/n$。所以 $S(M)$ 与有理网格的相应总和相差相对 $O(\epsilon)$。对 $1\le d<n/2$，网格中的一对余数 $\pm d$ 出现在 $k\equiv\pm du\pmod n$ 的两个时刻。因为 $M\ge n/2$，至少一次出现在截点前，两次都出现恰当且仅当 $\|du/n\|\ge1-\rho$。又

$$
n^{-2}\csc^2(\pi d/n)=(\pi d)^{-2}+O(n^{-2}),\qquad 1\le d\le n/2 .
$$

对偶数 $n$ 的中点单独计一次并将 $d^{-2}$ 的尾部补齐，得到 $S(M)/n^2=B/\pi^2+O(\epsilon+n^{-1})$。在 $1\le k\le2M<2n$ 中，$n$ 是唯一的整倍数。其他每个 $k$ 对应的非零余数到 $n\mathbb Z$ 的距离记作 $d$。有 $\|k\alpha\|\ge (d-2\epsilon)/n\ge (1-2\epsilon)d/n$，每种 $d$ 至多出现四次，故全部其他项之和为 $O(n^2)$。由于 $w_n=(n/(\pi\epsilon))^2(1+O(\epsilon^2/n^2))$，有 $S(2M)/w_n=1+O(\epsilon^2)$。除以此前的总和即得。

## 随后许多翻倍的总增长只趋于一个常数

在 $\epsilon$ 足够小时，取最大的非负整数 $R$ 使 $2^{R+1}M\le n/(2\epsilon)$。则 $R=\log_2(1/\epsilon)+O(1)$，并且

$$
\prod_{h=1}^{R}D_{j+h}
=\frac{S(2^{R+1}M)}{S(2M)}
=\frac{\pi^2}{6}+O(\epsilon+n^{-2}).
$$

为证分子总和，记 $W=2^{R+1}M$、$J=\lfloor W/n\rfloor$。此时 $1/(4\epsilon)<W/n\le1/(2\epsilon)$。在 $k=in$ 处，$w_{in}/w_n=i^{-2}(1+O(n^{-2}))$ 在 $1\le i\le J$ 一致成立。取和得 $\pi^2/6+O(\epsilon+n^{-2})$。其余点每 $n$ 个组成一块，截断的最后一块也可同样估计。距原点 $d$ 个网格单位的余数满足 $\|k\alpha\|\ge(d-1/2)/n\ge d/(2n)$。因此每块的非整倍数项至多 $2n^2\sum_{d\ge1}d^{-2}$。乘 $(J+1)/w_n$ 得累计 $O(\epsilon)$。再用 $S(2M)/w_n=1+O(\epsilon^2)$ 即证。

这给出逐个大峰的补偿机制。大峰的对数高约为 $2\log(1/\epsilon)$，随后约 $\log_2(1/\epsilon)$ 次翻倍，几何平均增长趋于 1。如果把每一步的基准增长率设为 4，则这些后续区间共比基准少增长约 $2\log(1/\epsilon)$ 个对数单位。即使一个目标确实存在很好的逼近，这个局部规律也与整体几何平均 4 完全相容。

## 不走过全部格点的有限证书

对已记录的第 28420 个连分数收敛分数 $n/m$（从零编号），$n$ 是 $\pi$ 的 14,593 位分子，$m/n$ 是 $1/\pi$ 的近似。按脚本的有理数向外取整计算，得到

$$
\begin{aligned}
3737927700.6739 &\le \frac{S(2^{48476})}{S(2^{48475})}\le3738396611.9800,\\
1.64490542 &\le \frac{S(2^{48491})}{S(2^{48476})}\le1.64508885 .
\end{aligned}
$$

运行 `python verify_pi_dyadic_resonance.py`，也可改用 `--method machin`。两条途径分别用 Chudnovsky 与 Machin 公式对 $\pi$ 作有理区间包围，调用原仓库中相邻的 `verify_pi_line_records.py`。这只用到一个既约点的信息，不需假设它已经是无限纪录。区间结果用 65,536 个余数对而得。

有限界的细节如下。设 $L$ 为脚本实际使用的余数对数，$c_d$ 是 $\pm du\bmod n$ 落入 $[1,M]$ 的次数。则归一化有理网格前缀和在以下区间中

$$
\left[\sum_{d=1}^L\frac{c_d}{(\pi d)^2},\sum_{d=1}^L\frac{c_d}{(\pi d)^2}+\frac{2L}{n^2}+\frac1{2L}\right].
$$

第一项来自 $\sin x\le x$。上界对已保留的项使用 $0\le\csc^2x-x^{-2}\le1$（在 $0<x\le\pi/2$ 由 $\sin x\ge x(1-x^2/6)$ 与 $\pi^2<10$ 即得），余下至多用 $2\sum_{d>L}1/(4d^2)\le1/(2L)$。前述扰动把上下界分别除以 $(1+\pi\epsilon/2)^2$、$(1-\pi\epsilon/2)^2$。对 $S(2M)/n^2$，保留 $w_n/n^2$ 即为下界，再加 $\zeta(2)/(1-2\epsilon)^2$ 即为上界。对随后的 $R$ 次翻倍，脚本用 $1/(J+1)\le\sum_{i>J}i^{-2}\le1/J$ 界住整倍数的尾部，再加最多 $2(J+1)\zeta(2)(\pi\epsilon)^2$ 的归一化非整倍数误差。所有数值包围均为有理数运算。

无限多个区间上是否存在一个统一的高度上界仍待证明。
