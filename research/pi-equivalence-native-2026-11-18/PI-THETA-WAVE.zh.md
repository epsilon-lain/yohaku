# 一个连续尺度上的两列二次波

这条路线把整数格点的全体信息装进一个正实变量的函数。研究目标是理解固定相位 $2$ 在所有尺度上的相消量。下面给出等价判据、孤立格点对应的波峰形状，以及整数列和半整数列各自出现共振的条件。理论出发点是经典的高斯泊松求和与 theta 函数。固定相位上的一致上界仍是开放步骤。

## 从整数距离到整条曲线

令 $\alpha=1/\pi$，并定义

$$
 c(\alpha)=\inf_{b\ge1,\ a\in\mathbb Z} b|b\alpha-a|.
$$

对任意正整数 $p,q$，倒数变换给出

$$
 p|p/\pi-q|=\frac{p}{\pi q}\,q|q\pi-p|.
$$

只要一边有一列趋于零，相关分数就趋于相应的目标，因子 $p/(\pi q)$ 趋于 $1$。因此 $c(1/\pi)>0$ 与 $c(\pi)>0$ 等价。

令 $t>0$，考虑协体积为 $1$ 的平面格

$$
 \Lambda_t=\{(\sqrt t\,(b\alpha-a), b/\sqrt t):a,b\in\mathbb Z\},
 \qquad
 G(t)=\sum_{v\in\Lambda_t}e^{-\pi |v|^2}.
$$

协体积等于生成矩阵行列式的绝对值。正定二次型在 $t$ 的每个紧子区间上一致控制高斯衰减，所以 $G$ 在 $t>0$ 上连续，且可逐项求导任意阶。它有一个直接的一维波形公式。对 $h=0,\tfrac12$，令

$$
 S_h(R)=\sum_{n\in\mathbb Z}
 e^{-(n+h)^2/R^2}\,e^{2i(n+h)^2},
 \qquad R=\sqrt{t/(2\pi)}.
$$

则

$$
 \boxed{\displaystyle G(t)=\frac{|S_0(R)|^2+|S_{1/2}(R)|^2}{\sqrt t}.}
 \tag{1}
$$

对上述格点和先在 $a$ 上作一维高斯泊松求和，得到

$$
 G(t)=\frac1{\sqrt t}\sum_{k,b\in\mathbb Z}
 e^{-\pi(k^2+b^2)/t}\, e^{2\pi i\alpha kb}.
$$

令 $u=(k+b)/2, v=(k-b)/2$，则 $u,v$ 同属整数或同属半整数。代入 $kb=u^2-v^2$ 以及 $k^2+b^2=2(u^2+v^2)$，两类各自因式分解成一个模方。此处 $2\pi\alpha=2$，给出式 (1)。

## 一个坏逼近判据与反证尝试

对 $x>0$ 记 $H(x)=\sum_{m\in\mathbb Z}e^{-\pi x m^2}$。若格中有一个**本原向量**（对应的两个整数互素）且长度平方为 $s$，则

$$
 \boxed{\displaystyle s^{-1/2}H(1/s)\le G(t)\le s^{-1/2}H(1/s)^2.}
 \tag{2}
$$

本原向量可以补成一组整数格基，平行于它的格点行之间的垂距因而恰为 $1/\sqrt s$。过原点的一行贡献 $H(s)$。第 $j$ 行贡献等于 $e^{-\pi j^2/s}\sum_m e^{-\pi s(m+d_j)^2}$，其中 $d_j$ 是该行沿行方向相对原点行的平移，以行内点距为单位。由高斯泊松公式及三角不等式，平移后的和至多为未平移时的 $H(s)$。保留原点行给出下界，对所有行求和给出上界 $H(s)H(1/s)$。最后使用 $H(s)=s^{-1/2}H(1/s)$。

**判据。** $c(\pi)>0$ 当且仅当 $\sup_{t\ge1}G(t)<\infty$。等价地，两列波都满足 $S_h(R)=O(\sqrt R)$（$R\to\infty$）。

若 $c(\alpha)>0$，每个 $b\ne0$ 对应的向量由算术–几何平均不等式满足

$$
 t(b\alpha-a)^2+b^2/t\ge2|b||b\alpha-a|\ge2c(\alpha).
$$

对于 $b=0, a\ne0$，长度平方至少是 $t\ge1$。取最短非零格向量，记长度为 $\lambda$。它必为本原向量。令 $m=\lceil\sqrt t\rceil$，狄利克雷抽屉原理给出 $1\le b\le m$ 和 $a$，使 $|b\alpha-a|\le1/(m+1)$。代入得 $\lambda^2\le5$，于是 $\lambda$ 有统一的上下正界。由式 (2) 得 $G(t)$ 有界。

反面假设 $c(\alpha)=0$ 给出一列本原点 $(a,b)$，误差 $E=b|b\alpha-a|\to0$。约分只会进一步减小这个量。取平衡尺度 $t_*=b/|b\alpha-a|=b^2/E$，此时对应向量长度平方恰为 $2E$。由式 (2)，

$$
 G(t_*)\ge (2E)^{-1/2}\longrightarrow\infty.
$$

所以反证可归结为证明式 (1) 在相位 $2$ 的两个平方根上界。例如若 $G(t)\le K$ 对所有 $t\ge1$ 成立，则 $c(\alpha)\ge 1/(2K^2)$。对此只须考虑每个 $b$ 的最近整数 $a$，此时 $t_*\ge1$，即使 $(a,b)$ 非本原，它的所有整数倍所给的原点行子和也已经达到 $H(2E)\ge(2E)^{-1/2}$。

## 所有放大倍数下的峰形

固定任一既约 $a/b$，令 $x=t/t_*>0$。原见证在 $t$ 处的长度平方为

$$
 s=E(x+x^{-1})=2E\cosh(\log x).
$$

把这个 $s$ 代入式 (2) 就得到任意放大倍数的双侧界。在 $s\to0$ 的区域，

$$
 G(x t_*)=\frac{1}{\sqrt{2E\cosh(\log x)}}
 \left(1+O\!\left(e^{-\pi/[2E\cosh(\log x)]}\right)\right).
 \tag{3}
$$

误差常数可对 $0<s\le1$ 统一取定，因为 $H(1/s)-1\le2e^{-\pi/s}/(1-e^{-3\pi/s})$。平衡尺度的幅值因而约为 $1/\sqrt{2E}$。这条估计同时控制整数格其他行对峰的贡献。

例如 $355/113$ 在倒数坐标中对应 $a/b=113/355$。用 Machin 恒等式 $\pi=16\arctan(1/5)-4\arctan(1/239)$，对两个反正切各保留前 $12$ 项与前 $4$ 项，其交错级数误差由下一项控制。所得区间给出 $0.00340630<E<0.00340633$。故平衡尺度约为 $3.700\times10^7$，波高约为 $12.11554$。代入式 (2) 与上述几何级数尾界，还得 $0\le G(t_*)\sqrt{2E}-1<5\times10^{-200}$。这个小误差控制的是其他格点行对给定波峰的影响。

## 已知无理性指数能排除怎样的增长

已知 $\mu(\pi)=2$，故对任意 $\varepsilon>0$，每个分数满足 $|\pi-p/q|\ge C_\varepsilon q^{-2-\varepsilon}$，其中正的 $C_\varepsilon$ 还吸收了有限个小分母。倒数变换给出 $|b\alpha-a|\ge C'_\varepsilon |b|^{-1-\varepsilon}$（$b\ne0$）。理由是在 $a/b$ 处于 $\alpha$ 附近时，$a$ 与 $b$ 的绝对值可比，并可用 $|\alpha-a/b|=|a|\,|\pi-b/a|/(\pi |b|)$。在该邻域外可直接降低常数。[OpenAI 证明陈述与 Lean 形式化范围](https://github.com/openai/math/blob/main/lean/docs/017.md)

最短向量满足 $\lambda\le\sqrt5$。其对应的 $b$ 因而满足 $|b|\le\sqrt{5t}$。若 $b\ne0$，上面的幂次估计给出

$$
 \lambda^2\ge2|b||b\alpha-a|\ge c_\varepsilon t^{-\varepsilon/2}.
$$

若 $b=0$，有 $\lambda^2\ge1$。高斯积分估计 $H(y)\le1+y^{-1/2}$ 与式 (2) 合起来给出 $G(t)\le 2+\lambda+\lambda^{-1}$。因此对每个 $\eta>0$ 均有

$$
 1\le G(t)=O_\eta(t^\eta),\qquad
 S_h(R)=O_\eta(R^{1/2+\eta}).
$$

这排除了固定正幂大小的峰值放大。要闭合反证还需要排除无界但慢于每个正幂的放大，所需的一致常数不能依赖尺度。

## 一个可以独立复算的相位检验

取互素 $a,b$，$b>0$，作为 $\alpha$ 的有理参照。记 $e(y)=e^{2\pi i y}$，并令

$$
 C_{h,k}(a,b)=\frac1b\sum_{r=0}^{b-1}
 e\!\left(\frac{a(r+h)^2+k(r+h)}{b}\right),\qquad
 w=R^{-2}-2\pi i(\alpha-a/b).
$$

将 $S_h(R)$ 拆成模 $b$ 的剩余类，对每个等差数列作高斯泊松求和，得到绝对收敛的直接公式

$$
 S_h(R)=\sqrt{\pi/w}\sum_{k\in\mathbb Z} C_{h,k}(a,b)
               e^{-\pi^2 k^2/(b^2 w)}.
 \tag{4}
$$

平方根取实部为正的分支。这里 $e(a(n+h)^2/b)$ 的周期整除 $b$，因为 $2h$ 为整数。将 $r-s=d\pmod b$ 代入有限和的模方，对 $s$ 求和后只剩 $b\mid 2d$ 的项。于是

$$
 |C_{h,k}(a,b)|^2=
 \begin{cases}
 1/b,& b\text{ 为奇数},\\
 (1+(-1)^{b/2+2h+k})/b,& b\text{ 为偶数}.
 \end{cases}
$$

偶数情形用到 $a$ 必为奇数。当 $b\equiv0\pmod4$，主频 $k=0$ 在整数列中有贡献，半整数列的主频为零。当 $b\equiv2\pmod4$，两列的角色交换。当 $b$ 为奇数，两列主频的模相等。只观察一列可能漏掉整类共振。

在 $t=t_*$ 处，$\pi^2\Re(1/w)/b^2=\pi/(4E)$，所以任何截断 $|k|\le K$ 后的绝对误差至多

$$
 2\sqrt{\frac{2\pi}{b|w|}}\,
 \frac{e^{-A(K+1)^2}}{1-e^{-A(2K+3)}},
 \qquad A=\frac{\pi}{4E},\quad K\ge0\text{ 为整数}.
$$

因而可以对指定参照分数先求有限高斯和，再用明确的尾界核验峰值。上述主频的模平方之和恒为 $2/b$，即使改变有理参照的分母奇偶，总主频也会保留。要证明两列波的统一上界，仍须解释相位 $2$ 为何在所有尺度都排除过强共振。

一般二次 Weyl 和与自守 theta 函数的联系可参阅 Cellarosi 与 Marklof 的论文。该文提供这类变换的研究背景。[Quadratic Weyl sums, automorphic functions, and invariance principles](https://arxiv.org/abs/1501.07661)
