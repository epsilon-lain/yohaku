# 一个可以直接核算的二进分离常数

以下是[二维间距定理](BBP-DYADIC-SPACING.zh.md)在整个剩余斜率带上的数值特例。取 $R\ge10^{110}$。在矩形 $R\le N\le2R,\ 3R\le M\le10R$ 内，若两个不同点满足
$$
 |N'-N|\le10^{-100}R,\qquad |M'-M|\le10^{-100}R,
$$
则记 $N'\ge N$ 后，
$$
 v_2\!\left(16^{N'}(X_{N',M'}-X_{N,M})\right)<R/100 .
$$
特别地，整个矩形内满足 $v_2(16^N X_{N,M})\ge R/100$ 的点不足 $10^{203}$ 个。这个常数只展示量词的有效性，远大于实际可用的穷举规模。

**短差的高度。** 沿用主文符号 $m=\min(M,M')$、$d=N'-N$、$u=M-m$、$v=M'-m$、$J=8d+u+v$，并置 $\epsilon=10^{-100}$。因此 $1\le J\le9\epsilon R$。主文的公共正整数可取
$$
 D_0=8\binom{b+J}{J}\operatorname{lcm}(1,\ldots,J+1),\qquad b=L+m+2.
$$
确实，$B_j/B_0=\binom{m+1+j}{j}/\binom{b+j}{j}$，又有 $\binom{b+J}{J}\binom{J}{j}=\binom{b+j}{j}\binom{b+J}{J-j}$。Legendre 阶乘赋值公式逐个素数幂给出 $\binom{J}{j}\mid\operatorname{lcm}(1,\ldots,J+1)$。

在实、虚四个嵌入中，$|\rho|\le3$。对主文的 $K_\rho(y)$，分子系数绝对值的总和至多 $16^d3^u+2^{8d}3^v\le 2e^{2J}$。除以 $1-\rho y$ 后，单个系数绝对值至多 $2e^{(2+\log3)J}$。因为 $0<B_j/B_0\le1$ 且 $|8A_\rho\rho|\le9$，把两个虚数项相加，清分母后主文二次多项式的任一系数在每个复嵌入的绝对值不超过 $\exp B$，其中可取
$$
 B=J[20+\log(90R/J)]\le 2500\epsilon R.
$$
用到 $b+J<30R$、$\binom{b+J}{J}\le (e(b+J)/J)^J$ 以及 $\log\operatorname{lcm}(1,\ldots,J+1)\le 4(J+1)\log2$。最后一个初等式由 $\psi(2k)-\psi(k)\le\log\binom{2k}{k}\le2k\log2$ 在二的幂上求和得到，其中 $\psi(k)=\log\operatorname{lcm}(1,\ldots,k)$。函数 $z[20+\log(90R/z)]$ 在所用区间递增。

实共轭首项与常数项非零由主文积分的符号及比值比较保证。对二次多项式取四个共轭之积，得到一个次数为八的非零整多项式。其 Mahler 测度至多 $(3e^B)^4$，因为每个因子的测度不大于其系数绝对值的总和。因此每个根 $\xi$ 的绝对对数高度 $h(\xi)\le4(B+\log3)$。其首项系数 $A$ 的二进赋值至多 $4B/\log2$，由在 $\mathbb Q(\sqrt2,i)$ 中取范数得到。令 $H=10^{-95}R$，则 $1+h(\xi)<H$。另一方面 $h(\alpha^m)=(m/2)\log(1+\sqrt2)>R$，故每个根均不等于 $\alpha^m$。

**套用定理时的参数。** 对每个根分别在 $K=\mathbb Q(\sqrt2,i,\xi,\zeta_3)$ 中选取一个 2 上方的素理想。$D=[K:\mathbb Q]\le16$，其分歧指数 $e_{\mathfrak p}$ 与剩余次数 $f_{\mathfrak p}$ 也至多 16。对 $v_2(\xi)\ne0$ 有 $v_2(\alpha^m-\xi)\le0$。其余取 Yu 定理 2 的 $p=2,n=2$、代数数 $(\alpha,\xi)$、指数 $(m,-1)$。最后一个指数的二进赋值为零，满足条件 (1.13)，两底数均为单位。该定理要求的三次单位根已包含在 $K$。$h'(z)=\max\{h(z), f_{\mathfrak p}\log2/D\}$。取 $B_{\rm Yu}=m$、$B_n=1$、$\delta=H/m$，有 $10^{-97}<\delta<10^{-94}$。许可上界 $D h'(\alpha)f_{\mathfrak p}\log 2\ge(\log2)^2>1/4$。以下引用 Yu 原文公式 (1.10)–(1.14) 及定理 2，见第 338–339 页。[论文原文](https://matwbn.icm.edu.pl/ksiazki/aa/aa89/aa8944.pdf#page=3)

原文中的整数 $\kappa\le6$，有 $1\le\vartheta\le2$、$\omega_3(2)=1$、$2^{f_{\mathfrak p}}-1<10^5$。原文公式 (1.10) 的常数 $C<10^{30}$，可逐因子用 $58,1,(32\cdot16\cdot64)^2,81,1,10^5,10^5,4,12$ 作上界。原公式中的 $a e p^\kappa$ 在这里用 $32\cdot16\cdot64$ 上界，其中 $e$ 是自然对数的底数。又 $\Psi=2^{f_{\mathfrak p}}(64D\log(5D))^2<10^{13}$，并有 $h'(\alpha)<1$、$h'(\xi)<H$。故定理中的对数因子
$$
 \widetilde h=3\log\!\left(\delta^{-1}\Psi(Dh'(\alpha))^2 B_n\right)<800 .
$$
归一化到 $v_2(2)=1$ 只会使上界更小。因而每个根贡献至多 $10^{30}\cdot16^2\cdot H\cdot800<10^{-58}R$。加上首项的赋值，对主文恒等式使用 $v_2(B_0)\le0$、$v_2(D_0)\ge0$，得到所述 $R/100$ 界。

若两个参数点都满足 $v_2(16^NX)\ge R/100$，同一差的赋值至少 $R/100$，矛盾。将宽 $R$、高 $7R$ 的矩形分为边长 $10^{-100}R$ 的小格，含端点重复也至多 $(10^{100}+1)(7\cdot10^{100}+1)<10^{203}$ 格。由此得到所报计数。
