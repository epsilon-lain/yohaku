# 整个参数平面上，线性规模的二进损失只能稀疏发生

沿用[原生定义](MIXED-RANK-CARRY-RESULTS.zh.md)。设 $X_{N,M}$ 为指定的 BBP–Taylor 有理逼近，$Q_{N,M}$ 是其正既约分母，$Y_{N,M}=16^NX_{N,M}$。对 $v_2$ 取 $v_2(2)=1$，约定 $v_2(0)=+\infty$。所有对数取自然对数。

**定理。** 固定 $0<a<b<\infty$ 和 $\eta>0$。设 $X$ 是正尺度，$X\le N\le2X$，$aX\le M\le bX$。此整个二维矩形中
$$
 v_2(Y_{N,M})\ge\eta X
$$
的整数点只有 $O_{a,b,\eta}(1)$ 个。实际上任意两例外点的曼哈顿距离 $|N'-N|+|M'-M|$ 至少为 $c_{a,b,\eta}X$（充分大 $X$）。因此到 $N\le X$ 为止，对任意固定正比例带 $a'\le M/N\le b'$，全部例外整数点对总数为 $O_{a',b',\eta}(\log(2X))$，这里全局例外条件取 $v_2(Y_{N,M})\ge\eta N$。

因此以 $N$ 的自然密度一计，剩余斜率带上同一 $N$ 的**所有补偿阶**同时有大二进分母。在 $N\in[X,2X]$ 中，可删去至多常数个 $N$，让所有其余 $N$ 和 $3.07\le M/N\le4.68$ 满足 $v_2(Q_{N,M})\ge(31/8)N$。取 $\eta=1/8$，即有 $v_2(Y)<X/8\le N/8$。对于这样保留下的点和任意趋于残余斜率 $t$ 的子序列，结合[未进位奇素数的贡献](BBP-BLOCK-MASS.zh.md)与已认证的 $D(t)>-0.17$，得到
$$
 \liminf N^{-1}\log\big(Q_{N,M}^2|\pi-X_{N,M}|\big)
 \ \ge D(t)+(31/4)\log2>5 .
$$
闭斜率带内可用紧性抽取斜率极限，取得统一的渐近下界。这个二维结论也适用于 $M=4N$ 以及任意 $M=4N+o(N)$ 的选阶规则。数量上界仍容许无限个孤立例外。

## 有限差由固定次数的代数多项式控制

记 $L=8N+8$，$y=1-x$，$\alpha=1+\sqrt2$，$q=\sqrt2-1=\alpha^{-1}$。核 $h(y)$ 的四个分式为 $A_\rho/(1-\rho y)$，其中 $\rho=q,-\alpha,i,-i$，实根权 $A_\rho=\rho/8$，虚根权 $A_\rho=(1-\rho)/8$。直接使用有限几何余项，得到
$$
 16^N(\pi-X_{N,M})=\int_0^1 x^L
    \sum_\rho A_\rho\frac{(\rho y)^{M+1}}{1-\rho y}\,dx .
$$
取两个不同格点；适当排序使 $N'=N+d$，$d\ge0$。令 $m=\min(M,M')$，$u=M-m$，$v=M'-m$，$J=8d+u+v\ge1$。对每个极点定义
$$
 K_\rho(y)=\frac{16^d(\rho y)^u-(1-y)^{8d}(\rho y)^v}{1-\rho y},
 \qquad
 W(y)=(1-y)^L y^{m+1}.
$$
四个极点均满足 $(1-1/\rho)^8=16$，故分子在 $y=1/\rho$ 消失，$K_\rho$ 是次数至多 $J-1$ 的多项式。定义 $B_0=B(L+1,m+2)=\int_0^1W(y)\,dy$，以及
$$
 T_\rho=A_\rho\rho\,\frac{\int_0^1 W(y)K_\rho(y)\,dy}{B_0}.
$$
两条有限余项相减正好给出
$$
 16^{N'}(X_{N',M'}-X_{N,M})= B_0\sum_\rho T_\rho\rho^m .
$$

**实共轭项不会一起消失。** 若 $u=0$，$K_q(y)>0$ 于 $0<y<1$，因为 $d+v>0$，且 $1-qy>0$。若 $u>0$ 则 $v=0$。若 $T_q=0$，有理性与共轭给 $T_{-\alpha}=0$。对奇数 $u$，$K_{-\alpha}$ 的分子处处为负。对偶数 $u\ge2$，设
$$
 R(\rho)=\frac{\int_0^1 W(y)(1-y)^{8d}/(1-\rho y)\,dy}
                 {\int_0^1 W(y)y^u/(1-\rho y)\,dy}.
$$
若两实项均消失，必须 $R(-\alpha)/R(q)=(\alpha/q)^u=\alpha^{2u}$。另一方面，$1<(1+\alpha y)/(1-qy)<\alpha^2$ 于开区间。分别比较两积分，其比值给出 $R(-\alpha)/R(q)<\alpha^2$，矛盾。因此两项始终非零。这个论证也适用于 $M$ 随 $N$ 下降的点对。

令 $F=\mathbb Q(\sqrt2,i)$，$B_j=B(L+1,m+2+j)$。令 $b_0=L+m+2$，取公共正整数
$$
 D_0=8\binom{b_0+J}{J}\operatorname{lcm}(1,\ldots,J+1).
$$
事实上 $B_j/B_0=\binom{m+1+j}{j}/\binom{b_0+j}{j}$。恒等式
$$
 \binom{b_0+J}J\binom Jj=\binom{b_0+j}j\binom{b_0+J}{J-j}
$$
及 $\binom Jj\mid\operatorname{lcm}(1,\ldots,J+1)$ 给出统一清分母。后一整除关系也可对每个素数幂在阶乘式中逐次取整，每个幂贡献至多 1。四个 $D_0T_\rho$ 都是 $F$ 的代数整数。令
$$
 P(Z)=D_0\big((-1)^m T_{-\alpha}Z^2
                 +(T_i i^m+T_{-i}(-i)^m)Z+T_q\big).
$$
于是
$$
 16^{N'}(X_{N',M'}-X_{N,M})
 =B_0\frac{P(\alpha^m)}{D_0\alpha^m}.
$$
$P$ 始终是二次多项式，常数项非零。$K_\rho$ 的系数是代数整数，所有复嵌入的绝对值均至多 $\exp(O(J))$，这来自二项展开、$|\rho|\le\alpha$ 及除以 $1-\rho y$ 的有限系数递推。所有 $B_j/B_0$ 均在 $(0,1]$。初等估计 $\binom{b_0+J}J\le(e(b_0+J)/J)^J$ 与 Chebyshev 界 $\log\operatorname{lcm}(1,\ldots,J+1)=O(J)$ 因而给出
$$
 \log D_0=O_{a,b}(H_J),\qquad H_J=J\log(e+X/J).
$$
Chebyshev 界也可用 $\operatorname{lcm}(1,\ldots,2k)\mid\binom{2k}k\operatorname{lcm}(1,\ldots,k)$ 在二次幂端点迭代证明。每个 $P$ 系数在所有复嵌入下的模都至多为 $\exp(O_{a,b}(H_J))$。当 $J=o(X)$ 时，这一对数高度也是 $o(X)$。

## 二进对数下界与两点间距

取 $P$ 的任一根 $\xi$。对四个域嵌入将 $P$ 取共轭并乘积，得到次数八的非零整系数多项式，系数绝对值至多 $\exp(O_{a,b}(H_J))$。所以 $h(\xi)=O_{a,b}(H_J)$，其中 $h$ 是绝对对数 Weil 高度。可直接用 Cauchy 根界控制所有共轭，再以该整多项式的首项系数乘 $\xi$ 得代数整数以控制分母。$P$ 自身的首项系数 $A$ 也是代数整数，$v_2(A)=O_{a,b}(H_J)$，因为其非零整范数受同一量级的指数上界控制。

有 $[\mathbb Q(\alpha,\xi):\mathbb Q]\le8$，因为 $\alpha\in F$，$[F:\mathbb Q]=4$，且 $P$ 在 $F$ 上次数为二。当 $J=o(X)$，因 $m\ge aX$ 和 $h(\alpha^m)=m h(\alpha)>0$，最终有 $\xi\ne\alpha^m$。因此此范围内两点给出的有理数一定不同。

使用 Yu 关于 $p$ 进对数线性形式的**含小末指数**的定理。原文 Theorem 2 见第 339 页。取 $p=2$，$n=2$；取域 $\mathbb Q(\alpha,\xi,\zeta_3)$，其中 $\zeta_3$ 是本原三次单位根，故满足原文对 $p=2$ 的单位根条件，域次数 $D\le16$。若 $v_2(\xi)=0$，两代数数 $\alpha,\xi$ 都是二进单位。指数 $b_1=m,b_2=-1$ 中末指数取得最小二进赋值，$B=\max(3,m)$、$B_2=1$ 合法，乘积 $\alpha^m\xi^{-1}$ 已证异于 1。定理不要求乘法独立。若 $\xi=1$，也可把此乘积写成 $\alpha^{m+2}(\alpha^2)^{-1}$。

具体地，取 $H=1+h(\xi)$。原文 $h'(z)=\max(h(z),f\log(2)/D)$，其中 $f$ 为剩余次数。原定理对所有 $0<\delta\le D h'(\alpha) f\log 2$ 成立。按其公式 (1.14) 取固定小常数 $c>0$ 与 $\delta=c\min(1,H/B)$。对 $D\le16$，分歧指数、剩余次数都有界，$h'(\alpha)$ 有固定的正上下界，原定理中的参数 $\Psi$ 亦有固定界。于是上界中第一项为 $O(H(1+\log^+(B/H)))$，第二项 $\delta B/B_2=O(H)$。将原素理想赋值按分歧指数换成 $v_2(2)=1$ 的赋值，得到
$$
 v_2(\alpha^m/\xi-1)\ll H\big(1+\log^+(m/H)\big),\qquad
 \log^+(z)=\max(0,\log z).
$$
若 $v_2(\xi)\ne0$，则 $v_2(\alpha^m-\xi)\le0$，无需用对数估计。[Kunrui Yu, Acta Arithmetica 89 (1999), 337–378, Theorem 2](https://doi.org/10.4064/aa-89-4-337-378) · [原文 PDF](https://matwbn.icm.edu.pl/ksiazki/aa/aa89/aa8944.pdf#page=3)

关键是当两点距离为 $o(X)$ 时，每一根都满足 $H=o(X)$，从而 $H(1+\log^+(m/H))=o(X)$。对 $P$ 两根（含重数）相加并加上首项赋值，得 $v_2(P(\alpha^m))\le o(X)$。$v_2(B_0)\le0$，因为其倒数是整数；$D_0$ 是整数，$\alpha$ 是单位。因此
$$
 \limsup X^{-1}v_2\!\left(16^{N'}(X_{N',M'}-X_{N,M})\right)\le0
 \qquad\text{当 }J=o(X).
$$
反之，若两点均有 $v_2(Y)\ge\eta X$，上式左侧的赋值等于 $v_2(Y_{N',M'}-16^dY_{N,M})\ge\eta X$。所以不存在间距为 $o(X)$ 的例外点对序列。由反证，这给出依赖 $a,b,\eta$ 的统一 $c>0$，使例外点对距离至少为 $cX$。用边长为 $cX/3$ 的方格覆盖整个矩形，每格至多一个例外，从而总数有常数上界。再在二次幂区段上求和即得全局对数数量上界。

也可取变动门槛 $X/\log(2X)$。若 $J\le X/(\log(2X))^2$，由 $H_J\ll X\log\log(3X)/(\log(2X))^2$ 和上述 Yu 界，差分赋值上界是 $O(X(\log\log(3X))^2/(\log(2X))^2)=o(X/\log(2X))$。故这个更低门槛的例外点在每个矩形中至多 $O((\log X)^4)$ 个。又有 $v_2(Y)\ge-O_{a,b}(\log X)$：原始 $16^NS_N$ 为二进整数，补偿项的分母均整除 $\operatorname{lcm}(1,\ldots,L+M+1)$。删去这些例外点的横坐标后，剩余 $N$ 对所有带内 $M$ 都有 $v_2(Q_{N,M})=4N+O_{a,b}(N/\log(2N))$。定理的大常数依赖 Yu 的界；本文没有给出实际可用的异常点穷举上限。

[标准库精确核对](verify_bbp_dyadic_spacing.py)分别用原有理数和四个二次域中的积分差计算等式，覆盖补偿阶上升、持平与下降，另行核对公共分母、二次多项式在 $\alpha^m$ 的值及非零系数。有限实验仅检查恒等式实现；无限稀疏性来自高度与二进对数定理。
