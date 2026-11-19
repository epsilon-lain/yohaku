# 大峰与下一座峰之间的整条曲线

固定无理数 $\alpha$ 和既约分数 $m/n$，其中 $n\ge2$。记 $\sigma=\operatorname{sgn}(\alpha-m/n)$，$\epsilon=n^2|\alpha-m/n|$，以及 $S_\alpha(H)=\sum_{1\le k\le H}\csc^2(\pi k\alpha)$。允许实数终点 $H\ge0$，和式取到 $\lfloor H\rfloor$。在圆周率问题中取 $\alpha=1/\pi$，这时每项恰为 $1/\sin^2 k$，$m/n$ 是原来逼近分数的倒数。

下面的公式对所有实数时刻都成立，在接近异常逼近时误差为 $O(\epsilon^2)$。原来由第一座峰产生的调和平方阶梯会不断遇到新的格点行。确定下一行的变量是原分数的模逆与逼近余差。一个小的余差本身并未给出下一次余差的统一正下界。

## 精确分行

令 $1\le r<n$ 为 $mr\equiv-\sigma\pmod n$ 的唯一解。对 $d\in\mathbb Z$ 取 $1\le r_d\le n$ 满足 $r_d\equiv dr\pmod n$，即余数 0 用 $n$ 表示。写
$$
u_d=r_d/n,\qquad \theta=\{1/\epsilon-u_1\}.
$$
花括号 $\{x\}=x-\lfloor x\rfloor$ 表示小数部分。$\theta$ 为无理数。整数 $d$ 是带符号的行列式 $\sigma(nl-km)$，其中 $l\in\mathbb Z$ 是 $k\alpha$ 附近的整数。由部分分式恒等式 $\pi^2\csc^2(\pi t)=\sum_{l\in\mathbb Z}(t-l)^{-2}$，逐项分组得
$$
W(T):=(\pi\epsilon/n)^2 S_\alpha(nT)
=\sum_{d\in\mathbb Z}\ \sum_{0<j+u_d\le T}
    (j+u_d-d/\epsilon)^{-2},\qquad T\ge0 .
$$
内和中 $j$ 取整数。原来第 $k$ 项的每个极点 $l$ 恰对应一个 $d$，而 $k/n=j+u_d$。所有项为正，重排成立。行 $d=0$ 的点恰为正整数 $k/n$。对 $d\ne0$，该行延伸到所有整数 $j$ 时，整行的和为
$$
\pi^2\csc^2(\pi d\theta),
$$
因为 $d/\epsilon-u_d$ 与 $d\theta$ 相差整数。这就是新相位的来源。

## 在正在穿越的一行保留每个点

取 $A=\epsilon T$。把 $A$ 最近的非负整数记为 $D$，恰在半整数处可取两者任一。先设 $D\ge1$，写 $\delta=A-D$，$|\delta|\le1/2$。设
$$
v=1+\lfloor T-u_D\rfloor+u_D-D/\epsilon,\qquad
K(v)=\sum_{h=1}^{\infty}(h-v)^{-2}.
$$
由于 $D/\epsilon$ 是无理数，$v$ 也是无理数，$K(v)$ 有限。精确到如下显式误差，
$$
W(T)=\frac{\pi^2}{6}+\pi^2 S_\theta(D-1)+K(v)
+\epsilon\!\left(\frac1\delta-\pi\cot(\pi\delta)\right)+R ,
$$
$$
|R|\le\epsilon^2\!\left(\frac{\pi^2}{3}
+\pi^2\csc^2(\pi\delta)-\frac1{\delta^2}\right)
\le\frac{4\pi^2}{3}\epsilon^2 .
$$
在 $\delta=0$ 处，括号中的差均取连续延拓。第一式把已经完整经过的 $D-1$ 行、当前行的已到达部分、以及其余行的合计分别算出。即使 $K(v)$ 特别大，误差仍然是上述绝对误差。

在最初的区间 $0\le A\le1/2$，可以保留第零行的精确读数。
$$
W(T)=\sum_{1\le j\le T}j^{-2}
+\epsilon\!\left(\frac1A-\pi\cot(\pi A)\right)+R_0 ,
\qquad |R_0|\le\frac{4\pi^2}{3}\epsilon^2.
$$
这里同样取连续延拓。所有这些式子共用一个常数，与观察时长、原分母和模逆无关。

## 一致误差的证明

令 $f_d(y)=(y-d/\epsilon)^{-2}$。对于一条不穿越极点的半直线，若 $f_d$ 远端衰减到零，则其上平移整数格的和与积分相差至多近端的函数值 $f_d(t)$。例如在右半直线 $(t,\infty)$，第一个格点为 $t+a$，$0<a\le1$。每个 $f_d(t+a+j)$ 都夹在 $f_d(t+j)$ 与 $f_d(t+j+1)$ 之间。上下矩形和以及积分同处宽度 $f_d(t)$ 的区间。左半直线 $(-\infty,t]$ 用反射证明，若端点为格点则取 $a=0$。

当 $d\ne0,D$，对于 $1\le d<D$ 先减去整行的值，剩下两端的负尾。其他 $d$ 的有限区间和是同侧两个半尾之差。在两种情况下，积分给出的有符号修正都为
$$
-\frac{\epsilon}{d}-\frac{\epsilon}{A-d}.
$$
每行误差至多 $\epsilon^2/d^2+\epsilon^2/(A-d)^2$。行 $d=0$ 的有限和等于 $\pi^2/6-1/T$ 加一个绝对值至多 $1/T^2$ 的误差。行 $d=D$ 的一侧精确和为 $K(v)$，包含一切 $j+u_D\le T$。减去 $j+u_D\le0$ 的那一段，给出的修正为 $-\epsilon/D$，误差至多 $\epsilon^2/D^2$。

合并后使用对称部分分式 $\pi\cot(\pi A)=\lim_{L\to\infty}\sum_{d=-L}^L(A-d)^{-1}$，各行积分修正的差为绝对可和。$\epsilon/A$ 与 $1/T$ 抵消，留下上面的平滑余项。累加误差时，左端贡献 $\epsilon^2\sum_{d\ne0}d^{-2}$，右端贡献 $\epsilon^2\sum_{d\ne D}(A-d)^{-2}$。因 $|\delta|\le1/2$，后一和不超过 $\sum_{h\ne0}(|h|-1/2)^{-2}=\pi^2$。这也在 $\delta=0$ 处直接给出连续延拓。初始区间把 $d=0$ 的有限和原样保留，对全部 $d\ne0$ 用同一估计即可得到公式。

## 单点的跃迁与尚待排除的情形

在第 $D$ 行，$T$ 增加越过格点 $j+u_D$ 时，$K(v)$ 增加一个可以直接写出的项。尤其设 $D=1$，$1/\epsilon-u_1=J+\theta$。取最靠近 $J+\theta$ 的整数 $j_*$，记 $k_*=nj_*+r$，又记 $e=j_*-(J+\theta)$。则
$$
k_*/n=1/\epsilon+e,\qquad
\bigl|k_*\alpha-l_*\bigr|=\frac{\epsilon}{n}|e|,\qquad
k_*\bigl|k_*\alpha-l_*\bigr|=(1+\epsilon e)|e| ,
$$
其中 $l_*=(mk_*+\sigma)/n$。只要 $\epsilon\le1/2$，$k_*>0$ 且该 $l_*$ 是最近整数。因为 $nl_*-mk_*=\sigma$，新分数也互素。此行能达到的最近碰撞取决于 $\|\theta\|$。取任意 $\theta_0\in(0,1)$ 无理并令 $\epsilon=1/(J+u_1+\theta_0)$、$\alpha=m/n+\sigma\epsilon/n^2$，即可在原格上实现这个次级相位，且 $J$ 可以任意大。保持目标为 $1/\pi$ 时，次级相位由它的算术值决定。证明这些相位在所有尺度都受控制仍是 π 的开放步骤。
