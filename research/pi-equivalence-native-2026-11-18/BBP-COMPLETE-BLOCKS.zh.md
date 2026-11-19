# 临界 Taylor 补偿的整块奇素数证书

令 $S_N$ 为从 $k=0$ 到 $N$ 的标准 BBP 和，$L=8N+8$，并写
$$
h(y)=\frac{y}{(1+2y-y^2)(1+y^2)}=\sum_{k\ge0}a_k y^k,\qquad
X_{N,M}=S_N+16^{-N}\sum_{k=0}^{M}a_k B(L+1,k+1).
$$
$Q_{N,M}$ 为 $X_{N,M}$ 的既约正分母，$Q_{\rm odd}$ 为其最大奇因子。$B(L+1,k+1)=\int_0^1 x^L(1-x)^k\,dx$。这里只积分有限多项式。原生报告证明了在 $M/N\to t>0$ 时 $N^{-1}\log|\pi-X_{N,M}|\to-E(t)$，其中
$$
E(t)=\log16+(8+t)\log(8+t)-8\log8-t\log t+t\log(\sqrt2-1).
$$
下文使用这项已验收的实误差结果。 [固定版本及原生脚本](https://github.com/epsilon-lain/yohaku/blob/7c4f272bb0c4b226610efddccd2e96dab3bc9e8e/research/pi-equivalence-native-2026-11-18/RANK-ODD-PRIMES-RESULTS.zh.md)

**结论。** 对于每一个满足 $N\to\infty$、$M/N\to 4\sqrt2$ 的非负整数序列，
$$
\liminf\frac{\log Q_{\rm odd}}N\ >3.6146,\qquad
\liminf\frac1N\log\bigl(Q_{N,M}^{\,2}|\pi-X_{N,M}|\bigr)>0.1772.
$$
这排除了指定 Taylor 补偿族在最佳实误差比例上产生趋零见证的可能性。证明使用 $p<L$ 的旧素数，也适用于未对 $4\sqrt2 N$ 采用任何特定取整规则的序列。

## 1. 按素数长度折叠 Taylor 系数

取奇素数 $p$，设 $L+M+1<p^2$。写
$$
L=up+\ell_0,\qquad M=vp+m_0,\qquad 0\le\ell_0,m_0<p,\qquad j=p-1-\ell_0.
$$
以下取 $\ell_0\ge8$、$m_0<j$。令 $P_M(y)=\sum_{k=0}^M a_k y^k$。当 $P_M(1-x)=\sum_j b_j x^j$ 时，$p$ 乘补偿积分后模 $p$ 的贡献只来自 $x^{ip+j}$，因为相应的积分分母为 $(u+1+i)p$，而其他积分分母均为 $p$-单位。$p^2>L+M+1$ 保证这些分母只含一次 $p$。

在两个二次数域分别对共轭根求和。四种基数与系数为
$$
\rho=-1\pm\sqrt2,\quad A_\rho=\rho/8;\qquad
\rho=\pm i,\quad A_\rho=(1-\rho)/8.
$$
将四项通分即得 $h(y)=\sum_\rho A_\rho/(1-\rho y)$，故 $a_k=\sum_\rho A_\rho\rho^k$。令 $\gamma_\rho=\rho/(\rho-1)$。实对的 $\gamma_\rho=\pm1/\sqrt2$，虚对的 $\gamma_\rho=(1\pm i)/2$，所以四者共有 $\gamma_\rho^8=1/16$。对每个奇素数都可在有限域上作这些运算。模 $p$ 的 $p$ 次幂用 $\sigma$ 表示，在 $\sqrt2$ 上的符号由 $(2/p)$ 决定，在 $i$ 上由 $(-1/p)$ 决定。因此 $\sigma$ 的特征只依赖 $p\bmod8$。

对每个 $\rho$，把索引 $k$ 按 $k=sp+r$ 分块。在特征 $p$，
$$
(1-x)^{sp+r}=(1-x^p)^s(1-x)^r .
$$
最后的不完整块有 $0\le r\le m_0<j$，故对所有 $x^{ip+j}$ 均无贡献。在任一整块，低位 $x^j$ 的系数为
$$
G_j(\rho)=[x^j]\sum_{r=0}^{p-1}\rho^r(1-x)^r
=\frac{1-\sigma\rho}{1-\rho}\,\gamma_\rho^j .
$$
最后一步使用有限几何和，分子中 $x^p$ 项不影响 $j<p$ 次系数。由于 $j=(u+1)p-L-1$、$L=8N+8$，有 $16^{-N}\gamma_\rho^j=16(\sigma\gamma_\rho)^{u+1}/\gamma_\rho$。高位贡献满足精确的有理恒等式
$$
\sum_{i=0}^s\frac{(-1)^i\binom si}{u+1+i}
=B(u+1,s+1)=\frac{u!s!}{(u+s+1)!}.
$$
对固定 $u,v$ 且充分大的 $p$，把有理数在模 $p$ 下解释即可。于是 $p$ 乘补偿后的模值是以下有理数的约化
$$
C_{uvr}=16\sum_\rho A_\rho
\frac{1-\sigma\rho}{1-\rho}
\frac{(\sigma\gamma_\rho)^{u+1}}{\gamma_\rho}
\sum_{s=0}^{v-1}(\sigma\rho)^s B(u+1,s+1),\qquad r=p\bmod8.
$$
每一对共轭项之和有理。$v=0$ 时内层和为零。

BBP 原和的部分也有固定有理提升。写 $c_1=4,c_4=-2,c_5=c_6=-1$。$\ell_0\ge8$ 且 $p$ 足够大保证所有有贡献的索引恰由 $1\le d\le u$、$a\equiv dr\pmod8$、$a\in\{1,4,5,6\}$ 给出，对应 $8k+a=dp$。在 $\mathbb F_p$，
$$
16^{-k}=2^{(a-d)/2}(2/p)^d .
$$
因此 $pS_N$ 的有理提升为 $O_{ur}=\sum_{d,a}c_a 2^{(a-d)/2}(2/p)^d/d$。若 $T_{uvr}=O_{ur}+C_{uvr}\ne0$，固定的这个有理数仅对有限多个素数失去非零性。所以每个充分大的适格 $p$ 均在最终分母中保留。举例，$(u,v)=(1,1)$ 给出 $T_{1,1,r}=(2,-4,2,-4)$，按 $r=1,3,5,7$ 排列。这段区间里补偿本身和 BBP 原和均可能含有同一个素因子。

## 2. 三十四个区间已覆盖所需的对数质量

记 $x=p/N$。对固定 $u\ge1$、$v\ge0$、$t>0$，整块条件在以下开区间的每个紧子区间内最终成立
$$
I_{uv}(t)=\left(
\max\left\{\frac8{u+1},\frac t{v+1},\frac{8+t}{u+v+1}\right\},
\min\left\{\frac8u,\frac t v,\frac{8+t}{u+v}\right\}
\right).
$$
$v=0$ 时把 $t/v$ 解释为 $+\infty$。这里分别固定了 $\lfloor L/p\rfloor=u$、$\lfloor M/p\rfloor=v$ 及 $\lfloor (L+M+1)/p\rfloor=u+v$。内部的线性距离吸收 $L-8N=8$、余数边界以及 $M-tN=o(N)$。固定 $t$ 时，各区间内部不交。

取 $t=4\sqrt2$、$1\le u\le20$。下表列出正长度区间的 $v$。除 $(1,0)$ 只保留 $r=1,5$ 外，所列区间的四个 $T_{uvr}$ 全部非零，由上式的有限有理运算可核对。

| $u$ | 可用 $v$ | $u$ | 可用 $v$ |
|---:|:---|---:|:---|
| 1 | 0, 1 | 11 | 7, 8 |
| 2 | 1, 2 | 12 | 8, 9 |
| 3 | 2 | 13 | 9 |
| 4 | 2, 3 | 14 | 9, 10 |
| 5 | 3, 4 | 15 | 10, 11 |
| 6 | 4 | 16 | 11, 12 |
| 7 | 4, 5 | 17 | 12 |
| 8 | 5, 6 | 18 | 12, 13 |
| 9 | 6, 7 | 19 | 13, 14 |
| 10 | 7 | 20 | 14 |

固定模 $8$ 的素数定理给每一个合格剩余类每单位区间长度 $1/4$ 的归一化对数质量。先取有限个紧子区间，再让端点逼近，即得
$$
\liminf\frac{\log Q_{\rm odd}}N
\ge \sum_{u,v}\frac{|I_{uv}(t)|}{4}\#\{r\in\{1,3,5,7\}:T_{uvr}\ne0\}.
$$
直接取 $5656854249492/10^{12}<t<5656854249493/10^{12}$，向内舍入每个区间，所得和至少为 $173987498642541056725936751/48134517631200000000000000>3.6146$。 [固定模数素数估计](https://personal.math.ubc.ca/~gerg/papers/downloads/EBPAP.pdf)

在临界处 $\exp(E(t)/2)=4/(2-\sqrt2)^4$。以 $1.414214$ 上界替换根号，用指数函数前二十项下界可证 $E(t)/2<3.526$。因此 $2(3.6146-3.526)=0.1772$ 是严格的指数下界。此证明完全不需要 $p>L$ 区间的统一非消去估计。

## 3. 复算和范围

同目录运行 `python3 verify_bbp_complete_blocks.py`。脚本用有理数和二次数域的二元表示生成全表。第二种算法直接用阶乘的 $p$-单位部计算 $pB(L+1,k+1)$，且从 $h$ 的分母递推 $a_k$。它逐项核对了跨越全部 34 个区间与四个剩余类的 136 个合成素数测试，并在原生基准 $N=320,M=1810$ 上对照了 187 个满足条件的旧素数。精确表和固定模素数定理共同承担无穷结论。有限测试用来发现两种算法的实现误差。以上结论只覆盖所定义的有理逼近族，$\pi$ 的坏逼近性仍为开放问题。
