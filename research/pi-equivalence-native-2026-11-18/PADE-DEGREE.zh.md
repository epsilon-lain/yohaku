# Padé 检测器随次数的指数分界

沿用交接中的
$$
P_m(z)=\sum_{k=0}^m\frac{(2m-k)!}{(m-k)!k!}z^k,\qquad
U(n,m)=\frac{(2n)^{2m+1}m!}{(2m+1)!}.
$$
写 $P_m(2in)=A+iB$、$D=|A|+|B|$。以下结论分析交接中**选定的余项上界 $U$**。次数小于分界时，带有这个上界的检测器会失效。若使用更紧的余项估计，次数分界可能变化。

## 平方模的正系数公式

对实数 $x$，
$$
|P_m(ix)|^2=\sum_{j=0}^m\binom{2j}{j}\frac{(m+j)!}{(m-j)!}\,x^{2m-2j}.
$$
一种直接证明从系数比开始。它给出 $zP_m''-(2m+z)P_m'+mP_m=0$。令 $g(x)=e^{-ix/2}P_m(ix)$，则 $xg''-2mg'+xg/4=0$。其共轭满足同一个实系数方程。对 $F=g\bar g$ 用乘法求导，得到
$$
x^2F'''-6mxF''+(x^2+2m+8m^2)F'-2mxF=0 .
$$
若写 $F=\sum_{j=0}^m d_jx^{2j}$，比较 $x^{2j-1}$ 系数给
$$
2j(2m-2j+1)(2m-j+1)d_j=(m-j+1)d_{j-1},\qquad 1\le j\le m.
$$
从最高系数 $d_m=1$ 倒推即得公式。特别地，$|P_m(ix)|\ge (2m)!/m!$。

## 求出指数分界

令 $\rho=2n/m$，并假设 $\rho$ 留在 $(0,\infty)$ 的固定紧区间内。对平方模求和的第 $j$ 项置 $r=j/m$。用 Stirling 对数估计，其对数为 $2m\log m+mf_\rho(r)+O(\log(m+1))$，其中
$$
f_\rho(r)=2(1-r)\log\rho+r\log4+(1+r)\log(1+r)-(1-r)\log(1-r)-2r .
$$
约定 $0\log 0=0$。误差统一适用于 $0\le j\le m$，因为对 $0\le k\le 2m+1$ 有 $\log(k!)=k\log k-k+O(\log(m+1))$。正项和在最大单项和 $(m+1)$ 倍最大单项之间。又
$$
f_\rho'(r)=\log\!\left(\frac{4(1-r^2)}{\rho^2}\right).
$$
当 $0<\rho<2$ 时最大点为 $r_*=\sqrt{1-\rho^2/4}$。当 $\rho\ge2$ 时为 $r_*=0$。在所取紧区间内最大点统一远离 $r=1$，将其就近取整为 $j/m$ 至多给对数引入 $O(1)$，因为 $f_\rho'$ 在最大点附近统一有界。

另一方面，$\log U=m\log m+m(2\log\rho+1-2\log2)+O(\log(m+1))$。两式相减得到
$$
 \log\frac{U(n,m)}{|P_m(2in)|}=m I(\rho)+O(\log(m+1)),\qquad
 I(\rho)=
 \begin{cases}
  1+r_*+\log((1-r_*)/2),&0<\rho<2,\\
  1+\log(\rho/4),&\rho\ge2 .
 \end{cases}
$$
$I$ 连续且严格递增，故指数分界由唯一零点 $\rho_*$ 决定。严格的位置为 $8/5<\rho_*<2$。事实上，
$$
 I(8/5)=8/5-\log 5<0,\qquad I(2)=1-\log 2>0.
$$
第一项的不等式可用 $\log 5=2\,\operatorname{artanh}(2/3)$ 的前四个正项验证，它们的和为 $122492/76545>8/5$。第二项使用 $e>2$。因此当 $m=\lceil5n/4\rceil$ 时，$nU/|P_m(2in)|$ 随 $n$ 指数衰减。当 $m=n$ 时，最终有 $U>2|P_m(2in)|\ge2|B|$，所以检测器 $L(n,n)$ 最终严格为负。若 $m/n$ 固定在 $2/\rho_*$ 的任一侧，两个方向分别适用。指数估计本身没有判定分界点及距分界仅 $O(\log n)$ 时的行为。

## 和目标的相位差

记 $M=|P_m(2in)|$，$T=n|\sin n|$。由余项恒等式，
$$
\left|2|B|-2M|\sin n|\right|\le U,\qquad
0\le \frac{TM}{D}-L(n,m)\le \frac{nU}{D}.
$$
此外写 $P_m(2in)/M=e^{i\theta}$，则 $2M|\sin(\theta-n)|\le U$。取 $\sigma\in\{-1,1\}$ 使 $\theta-n$ 离对应的 $0$ 或 $\pi$ 不超过 $\pi/2$（模 $2\pi$），可得 $|e^{i\theta}-\sigma e^{in}|\le\sqrt2|\sin(\theta-n)|$。二维实向量的 $1$-范数差至多为欧氏范数差的 $\sqrt2$ 倍。因此
$$
\left|D/M-\bigl(|\cos n|+|\sin n|\bigr)\right|\le U/M .
$$
两个分母都至少是 $1$，结合上式即得
$$
\left|L(n,m)-\frac{n|\sin n|}{|\cos n|+|\sin n|}\right|
\le 2n\,U/M .
$$
原问题的四个次数都满足 $m\ge2n$。这里可用简单的无渐近常数的上界。写 $x=2n$，
$$
\frac{U}{M}\le\frac{x}{2m+1}
\left[\prod_{j=1}^m\frac{x}{m+j}\right]^2
\le\frac12(2/3)^m .
$$
最后至少 $m/2$ 个因子不超过 $2/3$，其余因子不超过 1。故这四种检测器两两相差至多 $2n(2/3)^{2n}$，对任一固定正阈值，只有目标量落在阈值的指数小邻域时才可能得到不同分类。如果某一个检测器能从某处起给出统一正下界，其余三个以及 $m=\lceil5n/4\rceil$ 也都能做到。得到这条正下界仍是原来的算术难题。

## 用相位积分提高余项界

上面的分界属于交接中原先使用的 $U$。可以使用同一个 $P_m$、同一个检测器，但用一个从整数 $A,B$ 直接算出的更紧上界。

仍令 $g=e^{-ix/2}P_m(ix)$、$F=|P_m(ix)|^2$。由前面的实系数微分方程，实部和虚部的 Wronskian
$$
W(x)=\operatorname{Im}(\overline g(x)g'(x))
$$
满足 $W'=2mW/x$，所以 $W=Cx^{2m}$（$x>0$）。从多项式首项 $P_m(ix)\sim i^m x^m$ 得 $F(x)/x^{2m}\to1$，而 $\operatorname{Im}(g'/g)\to-1/2$。因此常数恰为 $C=-1/2$。取从 $\theta_m(0)=0$ 连续展开的辐角 $\theta_m(x)=\arg P_m(ix)$，精确式为
$$
 \frac{x}{2}-\theta_m(x)=\frac12\int_0^x\frac{u^{2m}}{F(u)}\,du .
$$
根据平方模的正系数公式，$F(u)/u^{2m}$ 随 $u>0$ 单调不增。故
$$
 0\le \frac{x}{2}-\theta_m(x)\le\frac{x^{2m+1}}{2F(x)}.
$$
当 $x=2n$ 时，$|R|=2\sqrt F\,|\sin(\theta_m(x)-x/2)|\le x^{2m+1}/\sqrt F$。由于 $D\ge\sqrt F$，可以将原检测器中的 $U$ 换成纯有理数
$$
 U'=\frac{x^{2m+1}D}{F}.
$$
也可以直接用欧氏模得到
$$
 L_*(n,m)=\frac{n|B|}{\sqrt F}-\frac{n x^{2m+1}}{2F},\qquad
 0\le n|\sin n|-L_*(n,m)\le\frac{n x^{2m+1}}{F}.
$$
理由是 $\bigl|2|B|-2\sqrt F\,|\sin n|\bigr|\le |R|$，再代入新上界。对正有理数 $c$，$L_*(n,m)\ge c$ 等价于
$$
 n^2B^2F\ge(cF+n x^{2m+1}/2)^2,
$$
因此可以只用整数比较复算。

当 $m/n$ 固定大于 1，有 $0<\rho<2$ 及
$$
 \log(F/x^{2m})=2m(\operatorname{artanh}r_*-r_*)+O(\log(m+1)).
$$
因为 $\operatorname{artanh}r_*>r_*$，所以 $L_*$ 与目标的误差随 $n$ 指数衰减。粗上界 $U$ 的指数分界由此降到任意固定比例 $m/n>1$。

还能把次数推进到 $n$ 上方的更小距离，而且不需要 Stirling 的误差常数。设 $m=n+d$、$0<d\le n$、$r=\sqrt{1-n^2/m^2}$，取 $j=\lfloor rm/2\rfloor$ 并假设 $rm\ge4$。将 $F/x^{2m}$ 的第 $j$ 项按精确式
$$
 \frac{(m+j)!}{(m-j)!}=m^{2j}(1+j/m)
                \prod_{h=1}^{j-1}(1-h^2/m^2)
$$
分解。中央二项系数至少为 $4^j/(2j+1)$。由于 $x=2n$，这个单项至少为
$$
 \frac{1}{2j+1}\left(\frac{1-r^2/4}{1-r^2}\right)^j
 \ge \frac{\exp(3 j r^2/4)}{2j+1}
 \ge \frac{\exp(3 m r^3/16)}{m+1}.
$$
第一步使用 $h^2/m^2\le r^2/4$。第二步来自在 $r^2/4$ 到 $r^2$ 之间积分 $(1-u)^{-1}\ge1$。最后一步使用 $j\ge rm/4$ 及 $2j+1\le m+1$。同时
$$
 mr^3=\frac{(m^2-n^2)^{3/2}}{m^2}\ge\frac{d^{3/2}}{\sqrt{2n}}.
$$
因此，当 $d=\lceil 16 n^{1/3}(\log n)^{2/3}\rceil$ 时，条件对充分大的 $n$ 成立，且 $n x^{2m+1}/F=O(n^{-5})$。这个估计说明多少次数足以消掉 Padé 的近似误差。证明 $L_*$ 本身的统一正下界仍取决于 $n|\sin n|$ 的算术波谷。
