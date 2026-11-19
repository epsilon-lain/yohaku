# 相邻补偿阶的分母与临界误差

沿用[固定版核验报告](RANK-ODD-PRIMES-RESULTS.zh.md)的实误差定理。设
$L=8N+8$，$h(y)=y/[(1+2y-y^2)(1+y^2)]=\sum_{k\ge0}a_k y^k$（这里仅需形式系数），$Q_{N,M}$ 是 $X_{N,M}$ 的正既约分母。记 $\alpha=1+\sqrt2$，$c=\log\alpha$，
$$
s(t)=(8+t)\log(8+t)-8\log8-t\log t,
\qquad E(t)=\log16+s(t)-tc .
$$

**定理。** 对任意整数序列 $k=k(N)\ge1$ 满足 $k/N\to t\in(0,\infty)$，记 $\Delta_{N,k}=X_{N,k}-X_{N,k-1}$，则
$$
\lim_{N\to\infty}N^{-1}\log\operatorname{den}(\Delta_{N,k})
=\log16+s(t).
$$
于是
$$
\liminf_{N\to\infty}\frac1N\log
\max_{M\in\{k-1,k\}}Q_{N,M}^{2}|\pi-X_{N,M}|\ \ge\ tc.
$$
该结果对两个奇偶方向都成立。临界点 $t=4\sqrt2$ 的右端约为 $4.9858019211$。它约束相邻两阶，同时允许每对有一个例外。单个临界阶的统一下界由[完整块素数证明](BBP-BLOCK-MASS.zh.md)给出。

**系数。** 定义 Pell 数 $P_0=0,P_1=1,P_{m+2}=2P_{m+1}+P_m$。有
$$
a_{2m-1}=P_m^2\quad(m\ge1),\qquad a_{2m}=-P_mP_{m+1}\quad(m\ge0).
$$
例如设 $T_n=P_{n+1}^2-2P_{n+1}P_n-P_n^2$。递推给出 $T_{n+1}=-T_n$、$T_0=1$。将上述候选序列乘以 $1+2y+2y^3-y^4$，偶次 $2m\ge4$ 的系数为 $-P_mP_{m+1}+2P_m^2+2P_{m-1}^2+P_{m-2}P_{m-1}=0$，约去两边递推后即得。奇次 $2m+1\ge5$ 的系数为 $P_{m+1}^2-2P_mP_{m+1}-2P_{m-1}P_m-P_{m-1}^2=T_m+T_{m-1}=0$。前四项 $0,1,-2,4$ 也符合，故乘积恰为 $y$。

**Pell 数与线性大小的素数。** 对任一奇素数 $p$，在 $\mathbb F_{p^2}$ 选 $u^2=2$，置 $z=(1+u)/(1-u)$。分子分母都非零，因为 $(1+u)(1-u)=-1$。由 Binet 式，$p\mid P_m$ 当且仅当 $z^m=1$。设 $d$ 是 $z$ 的乘法阶，则 $d\mid m$。Frobenius 给出 $u^p=u$ 或 $-u$，故分别有 $d\mid p-1$ 或 $d\mid p+1$。

设 $m\asymp N$、$D=O(N)$。对 $p\le D$ 且 $p\mid P_m$，
若 $d\le\sqrt N$，其对数总权重至多
$\sum_{d\mid m,\ d\le\sqrt N}\log P_d=O(\sqrt N\,\tau(m))$，因为相应的 $p$ 都整除 $P_d$，且 $P_d\le\alpha^d$。
若 $d>\sqrt N$，每个 $d\mid m$ 只允许 $p\equiv\pm1\pmod d$，候选整数至多 $2(D/d+1)$ 个，对数总权重为 $O(\sqrt N\,\tau(m)\log(2N))$。这里 $\tau$ 是约数个数，使用标准界 $\tau(m)=m^{o(1)}$。该界也可直接看出，对任意 $\epsilon>0$ 和充分大的素数 $p$ 有 $e+1\le2^e\le p^{\epsilon e}$，而有限个其余素数各自贡献至多 $C_{p,\epsilon}p^{\epsilon e}$。所以两个范围的总权重均为 $N^{1/2+o(1)}$。偶素数另算。$P_m$ 在 $m$ 为奇数时为奇数，并且 $P_{2r}=P_r(\alpha^r+(1-\sqrt2)^r)$，括号除以二得到首项为 $1,1$、递推为 $W_{r+2}=2W_{r+1}+W_r$ 的奇数列。于是 $v_2(P_m)=v_2(m)$。

**分母。** 逐阶积分给出准确的差
$$
\Delta_{N,k}=16^{-N}\,a_k\frac{L!k!}{(L+k+1)!}
=\frac{a_k}{16^N B},\qquad B=\frac{(L+k+1)!}{L!k!},\quad D=L+k+1.
$$
在每个 $p^e$ 上，$\lfloor D/p^e\rfloor-\lfloor L/p^e\rfloor-\lfloor k/p^e\rfloor$ 等于 0 或 1，因为 $D=L+k+1$。因此 $v_p(B)\le\lfloor\log_p D\rfloor$，且 $p>\sqrt D$ 时 $v_p(B)\le1$。所有 $p\le\sqrt D$ 在 $B$ 中的对数总权重至多 $\sqrt D\log D$。较大的奇素数若能约去，必整除 $P_m$ 或 $P_{m+1}$，其中 $m\asymp N$。上段引理将总权重限制为 $N^{1/2+o(1)}$。$16^N$ 带来的额外约分至多为 $v_2(a_k)\log2=O(\log N)$。合起来
$$
0\le\log(16^N B)-\log\operatorname{den}(\Delta_{N,k})
\le N^{1/2+o(1)} .
$$
Stirling 公式给出 $N^{-1}\log B\to s(t)$，证明第一式。

**由差回到两个逼近。** 有 $\operatorname{den}(\Delta_{N,k})\mid\operatorname{lcm}(Q_{N,k-1},Q_{N,k})\mid Q_{N,k-1}Q_{N,k}$。固定版实误差定理适用两个阶，因为 $(k-1)/N$ 与 $k/N$ 有同一极限，故两项的误差均为 $\exp[-NE(t)+o(N)]$。两个归一化误差的最大值至少是它们的几何平均数。代入分母极限即得下界 $(\log16+s(t))-E(t)=tc$。

[标准库复算脚本](verify_bbp_adjacent.py)用原核的四阶递推与 Pell 递推生成两组系数，直接对原截断和有限积分作有理数运算，再以阶乘独立重算相邻差。脚本也独立用模 $p$ 递推枚举首次出现 $p\mid P_m$ 的下标并检查阶的整除性质。脚本中的有限范围和十进制输出只作复算。

## 间隔两阶与三阶

这里 $P_k$ 仍为上面的 Pell 数，$\rho=\alpha$，$V_{L,M}=(L+M+1)!/(L!M!)$。从前述素数阶估计也得到 $\log\gcd(P_k,\operatorname{lcm}(1,\dots,D))=O_\epsilon(N^{1/2+\epsilon})$，其中 $D,k=O(N)$。事实上 $p\le\sqrt D$ 的每个素数最多贡献 $\log D$，其余素数在最小公倍数中至多出现一次。由同一阶乘赋值公式，$V_{L,M}$ 整除这个最小公倍数，其中 $D=L+M+1$。


设 $M=M(N)$，$M/N\to t\in(0,\infty)$。令
$$
 A(t)=(8+t)\log(8+t)-8\log8-t\log t,\quad
 E(t)=\log16+A(t)-t\log\rho .
$$
固定报告用最近极点的有限余项证明 $\log|\pi-X_{N,M}|/N\to-E(t)$。改变固定数量的 Taylor 项仍有相同的比例极限，所以每一个 $X_{N,M-d}$ 也适用此误差率。

对于 $d=1,2$，及 $d=3$ 且 $M$ 为偶数的子序列，记 $T_{N,j}=Q_{N,j}^2|\pi-X_{N,j}|$。则
$$
 \liminf_{N\to\infty}\frac{\log \max(T_{N,M},T_{N,M-d})}{N}
 \ \ge\
 \begin{cases}
 t\log\rho,&d=1,\\
 (t/2)\log\rho,&d=2,\ \text{或 }d=3\text{ 且 }M\text{ 为偶数}.
 \end{cases}
$$
取四个连续截断，首项为奇数，末项与 $N$ 的比例趋于 $t$。六对截断的距离均为一、二或以偶数为终点的三。这四个 $T$ 中第二小者是六个两两最大值中的最小值，因此它的归一化对数下极限至少为 $(t/2)\log\rho$。四个截断中至多一个能落在这个指数率以下固定裕量。该结论允许单独挑选的截断持续给出很小的误差。

**证明。** 设 $s_0=M-d+1$，把差写成
$$
 X_{N,M}-X_{N,M-d}
 =\frac{\sum_{s=s_0}^M r_s a_s}{16^N W},\qquad
 W=\frac{(L+M+1)!}{L!\,s_0!},\quad
 r_s=\frac{s!}{s_0!}\frac{(L+M+1)!}{(L+s+1)!}.
$$
$W=V_{L,M}\,M!/s_0!$，其中额外因子与所有 $r_s$ 都是关于 $N+M$ 的多项式量级正整数。Stirling 公式给出 $\log(16^NW)/N\to\log16+A(t)$。

若 $d=1$，分子是两个下标为 $M/2+O(1)$ 的 Pell 数之积（允许相同）。上节引理与二进赋值说明它与总分母的公因子仅耗去 $o(N)$ 的对数。因此相邻差的既约分母 $D_1$ 有精确指数 $\log D_1/N\to \log16+A(t)$。

若 $d=2$，相邻两系数共享一个下标 $M/2+O(1)$ 的 Pell 因子。余下因子 $B$ 满足
$\log|B|\le (M/2)\log\rho+O(\log(N+M))$，只要 $B\ne0$。设 $M=2k$，则 $B=r_{2k-1}P_k-r_{2k}P_{k+1}$。若为零，由相邻 Pell 数互素，将有 $P_k\mid r_{2k}$。设 $M=2k+1$，则 $B=-r_{2k}P_k+r_{2k+1}P_{k+1}$，若为零将有 $P_k\mid r_{2k+1}$。因为 $k$ 与 $N$ 同阶，左侧指数增长，右侧正且至多多项式增长，故对充分大的 $N$ 都不能为零。

若 $d=3$ 且 $M=2k+2$，$a_{2k},a_{2k+1},a_{2k+2}$ 共享 $P_{k+1}$。余因子
$$
 B=-(r_{2k}+r_{2k+2})P_k+(r_{2k+1}-2r_{2k+2})P_{k+1}.
$$
若为零，$P_{k+1}$ 必须整除正整数 $r_{2k}+r_{2k+2}$，充分大时再次矛盾。余因子满足同样的大小估计。

后两种情形的差分母 $D_d$ 因此满足
$\liminf \log D_d/N\ge\log16+A(t)-(t/2)\log\rho$。
最后，$D_d\mid\operatorname{lcm}(Q_{N,M},Q_{N,M-d})\mid Q_{N,M}Q_{N,M-d}$。同时两个原逼近的实误差都是 $\exp(-NE(t)+o(N))$。两端 $T$ 的几何平均数至少为 $D_d\exp(-NE(t)+o(N))$，即得所述正下界。

取四个连续的阶数，第一阶为奇数。相差一阶和两阶的配对均已覆盖，唯一相差三阶的配对以偶数结束。因此在任意这样一组里，四个归一化误差中第二小者的下界指数也至少为 $(t/2)\log\rho$。这个结论给中间未决斜率上的候选点加上了间距条件。

[间隔复算脚本](verify_bbp_short_gaps.py)给出第二种核系数和有理差分核对。

## 中间比例的单阶二进证书

还有一个可以单独指定 $M$ 的无限族。设 $2^h\mid L$、$1\le M\le2^h-2$。若 $M\bmod8\in\{1,2,3,4\}$，则
$$
v_2(Q_{N,M})=4N+1 .
$$
事实上，$1\le k\le M$ 时 $\binom{L+k}k$ 为奇数，因为在二进制将 $k$ 加到 $L$ 上不会进位；也可直接在 $(1+x)^{L+k}$ 模 2 中取系数。又有 $v_2(L+k+1)=v_2(k+1)$。所以 $v_2(B(L+1,k+1))=-v_2(k+1)$。偶数 $k$ 的校正项 $a_k B(L+1,k+1)$ 均为二进整数。奇数 $k=2m-1$ 的赋值为 $v_2(m)-1$，其中恰好 $k\equiv1\pmod4$ 时为 $-1$。原始 $16^N S_N$ 是二进整数，因为合并每一项后的分母只含奇因子，见[原分母公式](BBP-DENOMINATOR.zh.md)。因此 $2\cdot16^N X_{N,M}$ 模 2 等于 $1\le k\le M$ 中 $k\equiv1\pmod4$ 的个数模 2。给定的四个剩余类使它为奇数，定理得证。

取 $N=2^s-1$、$s\ge1$、$M=4N$，就得到尚未逐阶解决的斜率 $t=4$ 上一个完全指定的无限序列。这里 $L=2^{s+3}$，$M\equiv4\pmod8$。结合[未进位奇素数的总量](BBP-BLOCK-MASS.zh.md)，它的归一化误差指数下界为 $D(4)+8\log2>5.38$。例如 $s=1$ 时 $N=1,M=4$，已经有 $v_2(Q)=5$。[单阶直接有理数复算](verify_bbp_dyadic_slice.py)

同一 $N=2^s-1$ 和任意固定 $0<t<8$，可在 $\lfloor tN\rfloor$ 起的五个连续整数中选择一个，使 $M\bmod8\in\{1,2,3,4\}$。二进证书也适用这些阶。以上只选定了满足所列条件的序列。
