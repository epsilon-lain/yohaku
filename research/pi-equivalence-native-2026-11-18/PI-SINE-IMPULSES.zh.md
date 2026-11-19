# 整数正弦波的相对峰值和长区间能量

把时间取为正整数，记录波高的绝对值 $|\sin n|$。若 $p/q$ 接近 $\pi$，则 $p$ 靠近 $q\pi$，波高 $|\sin p|$ 很小。这给出一个只含整数自变量、只用普通正弦和有限求和的量

$$
Z(n)=\sin^2 n\sum_{k=1}^{n-1}\frac{1}{\sin^2 k},\qquad n\ge2 .
$$

以下给出一般无理斜率的证明，再取 $\alpha=1/\pi$。借助 $|p/q-\pi|$ 和 $|q/p-1/\pi|$ 的恒等式即可处理取倒数。例如当 $p/q\to\pi$ 时，$p^2|q/p-1/\pi|=[p/(q\pi)]q^2|p/q-\pi|$，括号内趋于 1。于是存在归一化误差趋于零的序列这一性质在取倒数下保持。

## 一个无递推的等价判据

对无理 $\alpha$ 把上述定义中的 $\sin k$ 换成 $\sin(\pi k\alpha)$，所得数记作 $Z_\alpha(n)$。令 $m$ 为距 $n\alpha$ 最近的整数，$\epsilon=n|n\alpha-m|$。以下三条都对 $n\ge2$ 成立。

1. $Z_\alpha(n)\ge 4\epsilon^2/\pi^2$。
2. 若 $\gcd(m,n)>1$，则 $Z_\alpha(n)\ge2$。
3. 若 $\gcd(m,n)=1$ 且 $h=\pi\epsilon/2<1$，则有双边界

$$
\frac{n^2-1}{3(1+h)^2}\sin^2(\pi\epsilon/n)
\ \le\ Z_\alpha(n)\ \le\
\frac{n^2-1}{3(1-h)^2}\sin^2(\pi\epsilon/n).
$$

为证第一条，把 $0,\alpha,\ldots,(n-1)\alpha$ 模 1 放在圆周上。有一条相邻间隙至多为 $1/n$，其两端的指标之差的绝对值为某个 $1\le k<n$。于是 $|\sin(\pi k\alpha)|\le\pi/n$。另一方面，$|\sin(\pi n\alpha)|\ge 2\|n\alpha\|$，其中 $\|x\|$ 表示到最近整数的距离。取和式中第 $k$ 项即得。

为证第二条，置 $g=\gcd(m,n)\ge2$ 和 $u=\pi|n\alpha-m|\le\pi/2$。和式中 $k=n/g$ 一项贡献为 $(\sin u/\sin(u/g))^2\ge(2\cos(u/2))^2\ge2$。

为证第三条，因 $m,n$ 互素，令 $k$ 跑遍 $1,\ldots,n-1$ 时，$km\bmod n$ 将全部非零余数遍历一次。对每个 $k$，$|\sin(\pi km/n)|\ge2/n$。把 $m/n$ 换成 $\alpha$ 时，正弦绝对值的改变量至多为 $\pi k\epsilon/n^2<\pi\epsilon/n$。所以每项的正弦绝对值都处在原值的 $1\pm h$ 倍之间。使用有限格点恒等式

$$
\sum_{k=1}^{n-1} \csc^2(\pi k/n) = (n^2-1)/3 .
$$

这个恒等式来自 $\sin(nx)=C_n\prod_{k=0}^{n-1}\sin(x+\pi k/n)$。取对数导数并再求导，得到 $\sum_{k=0}^{n-1}\csc^2(x+\pi k/n)=n^2\csc^2(nx)$。消去 $\csc^2 x$ 并令 $x\to0$，用 $\csc^2x=x^{-2}+1/3+O(x^2)$ 得式。最后乘 $\sin^2(\pi n\alpha)=\sin^2(\pi\epsilon/n)$。

因此 $\alpha$ 为坏逼近数等价于 $\inf_{n\ge2} Z_\alpha(n)>0$。若 $\inf_q q\|q\alpha\|=0$，取一列归一化误差趋于零的最近分数并约分。约分使归一化误差除以公因数的平方，所得分母趋于无穷，且最终分子仍是相应的最近整数。第三条给出 $Z_\alpha(n)\sim(\pi^2/3)\epsilon^2\to0$。反方向由第一条得到。即使只知道某个序列上 $Z_\alpha(n)\to0$，前两条也保证它最终互素且 $\epsilon\to0$，故同一渐近式适用。

## 反设强制出的长区间波形

假设有一列互素的最近分数 $m/n$ 使 $\epsilon=n|n\alpha-m|\to0$，令 $B=\lfloor1/(2\epsilon)\rfloor$。则

$$
\sin^2(\pi n\alpha)\sum_{k=1}^{Bn}\csc^2(\pi k\alpha)
=\frac{\pi^2}{6}+O(\epsilon+n^{-2}).
$$

在 $k=jn$ 处，令 $u=\pi\epsilon/n$。对 $1\le j\le B$ 有 $ju\le\pi/(2n)$，故 $(\sin u/\sin(ju))^2=j^{-2}(1+O(n^{-2}))$ 一致成立。求和得到 $\sum_{j=1}^B j^{-2}+O(n^{-2})=\pi^2/6+O(\epsilon+n^{-2})$。

余下的指标写成 $k=bn+r$，其中 $0\le b<B$ 且 $1\le r<n$。令 $d$ 为 $rm$ 模 $n$ 的余数到 $n\mathbb Z$ 的距离，$1\le d\le n/2$。由 $k|\alpha-m/n|\le1/(2n)$ 得 $\|k\alpha\|\ge(d-1/2)/n\ge d/(2n)$，故 $|\sin(\pi k\alpha)|\ge d/n$。每个 $b$ 内，每种 $d$ 至多出现两次，这些非整倍数的能量之和至多为 $2n^2\sum_{d\ge1} d^{-2}$。再乘 $B\sin^2(\pi n\alpha)=O(B\epsilon^2/n^2)$，总贡献为 $O(\epsilon)$。两部分相加即证。

特别地，若 $\pi$ 并非坏逼近数，就会有越来越长的整数时间区间 $[1,Bn]$，其中**单独时刻 $n$ 的能量** $1/\sin^2 n$ 占全区间的比例趋于 $6/\pi^2$。而从 $1$ 到 $n-1$ 的能量之和除以 $n^2$ 却趋于 $1/3$。要由反证法判定 $\pi$，仍须证明真正的整数正弦波排斥这种子序列。此处给出的等价判据、必要的长区间轮廓和有限证书都未证明这种排斥。

还可以计算这条长区间曲线随终点移动的一阶变化。固定 $0<c<1$，改取 $B=\lfloor c/\epsilon\rfloor$，则

$$
\sin^2(\pi n\alpha)\sum_{k=1}^{Bn}\csc^2(\pi k\alpha)
=\frac{\pi^2}{6}-\pi\epsilon\cot(\pi c)+O_c(\epsilon^2).
$$

取 $c=1/2$ 时一阶项恰好消失。证明如下。令 $\sigma=\operatorname{sgn}(\alpha-m/n)$。把指标写为 $k=(j-1)n+r$，$1\le j\le B,\ 1\le r\le n$。同一块内，把每个实际相位 $k\alpha\bmod1$ 替换为等步长格点上的 $rm/n+\sigma j\epsilon/n\bmod1$，改变量绝对值至多为 $\epsilon/n$。$r=n$ 时两相位严格相等。其余 $r$ 对应的余数距离记作 $d\ge1$。沿这次平移的整段，距整数至少 $(d-c)/n\ge(1-c)d/n$，所以 $\csc^2(\pi x)$ 的导数绝对值为 $O_c(n^3/d^3)$。从每种 $d$ 至多出现两次得，每块替换产生 $O_c(\epsilon n^2)$ 的总误差。所有块累加后乘以 $\sin^2(\pi\epsilon/n)$，总误差为 $O_c(\epsilon^2)$。

对替换后的整块使用前述带平移的格点恒等式，精确得到 $n^2\csc^2(\pi j\epsilon)$。再用 $n^2\sin^2(\pi\epsilon/n)=\pi^2\epsilon^2(1+O(\epsilon^2/n^2))$。因为 $\sin(\pi x)/x$ 在 $[0,c]$ 连续延拓且有正下界，$\epsilon^2\sum_{j=1}^B\csc^2(\pi j\epsilon)=O_c(1)$。故只需估计 $\pi^2\epsilon^2\sum_{j=1}^B\csc^2(\pi j\epsilon)$。

函数 $f(x)=\pi^2\csc^2(\pi x)-1/x^2$ 光滑延拓到 $[0,c]$。设 $t=B\epsilon$，取右端点的矩形求积并用 $f'$ 有界，得到

$$
\epsilon^2\sum_{j=1}^B f(j\epsilon)
=\epsilon\int_0^t f(x)\,dx+O_c(\epsilon^2)
=\epsilon\left[\frac1t-\pi\cot(\pi t)\right]+O_c(\epsilon^2).
$$

加上 $\sum_{j=1}^B j^{-2}=\pi^2/6-1/B+O(B^{-2})$。其中 $1/B$ 与 $\epsilon/t$ 相消，且 $t=c+O(\epsilon)$，得到所述公式。

## 仅在二的幂次上读数

令 $S_N=\sum_{k=1}^N\csc^2 k$。则 $\pi$ 为坏逼近数等价于 $\sup_{j\ge0} S_{2^{j+1}}/S_{2^j}<\infty$。证明时仍取 $\alpha=1/\pi$。若 $k\|k\alpha\|\ge c>0$，前 $N$ 个模 1 相位以及原点两两相距至少 $c/N$。在原点任一侧的第 $l$ 个相位到原点的圆周距离至少为 $lc/N$。由 $|\sin(\pi x)|\ge2\|x\|$，在两侧分别累加得到 $S_N=O_c(N^2)$。上述圆周间隙论证又给出 $S_N\ge (N+1)^2/\pi^2$。二者合并即得比值一致有界。反方向，若存在 $Z(n)\to0$，取唯一的 $2^j<n\le2^{j+1}$，则

$$
\frac{S_{2^{j+1}}}{S_{2^j}}\ \ge\ \frac{\csc^2 n}{S_{n-1}}=\frac1{Z(n)}\to\infty .
$$

## 有限证书

运行 `python verify_pi_continuous_wave.py` 得

| 正整数 $n$ | $Z(n)$ 的有理数外包区间 |
| --: | -- |
| 22 | $[0.0122743627291828,\ 0.0122743627291829]$ |
| 355 | $[0.0000382516860269,\ 0.0000382516860270]$ |

同次运行认证 $S_{512}/S_{256}\in[47753.527512848568,\ 47753.527512848569]$。运行长区间模式（在命令尾添加 \(\texttt{--long}\)）还得到 $n=355$ 时 $B=146$，$Bn=51830$，单次峰值的能量占比落在 $[0.607944516183,\ 0.607944516184]$。

脚本用 Machin 恒等式 $\pi=16\arctan(1/5)-4\arctan(1/239)$ 和反正切的交错级数夹逼 $\pi$。对每个 $k$，用有理区间唯一认证最近的 $\pi$ 整倍数，把 $|\sin k|$ 化成 $[0,\pi/2)$ 上的正弦，使用交错泰勒级数的相邻截断夹逼，再逐项向外取整求和。另用系统正弦计算做浮点交叉检查。
