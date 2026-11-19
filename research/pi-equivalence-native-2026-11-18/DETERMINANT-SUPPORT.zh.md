# 对实际非零子式的列选择及平移后支撑约束

2026-11-19。接续 [A 队的临界行分配比较](DUAL-TEAM-RESULTS.zh.md)。沿用其固定版预印本的记号。先固定全部插值参数、权重和中心，然后令充分可整除的 $H$ 趋于无穷。两项结果分别是选择一个算术代价更小的非零全行子式，以及给定所选列后可精确核查的支撑限制。原来的均匀解析节省仍待证明。[原行列式估计](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/sections/determinant.tex) · [插值定理](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/sections/interpolation.tex)

## 1. 用实际列秩减少算术代价

列记为 $Y^hX^\alpha$，其中 $w_0h+w\alpha\le H$。行是 $(j,s,\beta)$，满足 $v_0s+w\beta/\theta<H$。以 $M_D$ 表示高度 $D$ 的原行包大小。用原论文的精确对数行包计算秩，可以在取所需子空间后回到有理截断矩阵，因为高度 $H$ 的整行包由可逆行变换联系，任意固定列子集的秩相同。

先按总加权次数 $w_0h+w\alpha$ 从小到大扫描列，仅当该列使已选列的秩增加时纳入。对每个足够大且符合整除条件的 $D\le H$，把整行包投影到高度 $D$ 的行包。固定参数的插值定理保证次数不超过 $D$ 的列在这个投影上有秩 $M_D$，所以整行包上也有至少 $M_D$ 的秩。扫描到 $D$ 时，所选列恰好张成已扫描列的空间。由此得到一个非零全行子式，且其中次数不超过 $D$ 的列至少有 $M_D$ 个。由 $M_D\sim c_0D^{m+1}$ 和面积分层公式
$$
 \frac{1}{M_H H}\sum_{\rm col}(w_0h+w\alpha)
 =\int_0^1 \frac{\#\{\mathrm{col}:w_0h+w\alpha>\lambda H\}}{M_H}\,d\lambda
$$
可得平均归一化总次数至多 $(m+1)/(m+2)+o(1)$。对不在整除网格上的 $\lambda H$ 使用最近的下方网格点即可。

还可单独控制直接进入清分母的横向次数 $w\alpha$。预选有理数 $S>1$，使
$$
 S\theta<1,\qquad K(S\theta)^m<1,\qquad K(w_0/v_0)(S\theta)^m<1.
$$
对任一事先指定的有理 $\lambda\in(0,1]$，将插值的高度改为 $\lambda H$，零号权重改为 $\lambda w_0,\lambda v_0$，横向参数改为 $S\theta$，其余列权重 $w_i$ 保持。新的列集合满足
$$
 \lambda w_0h+w\alpha\le\lambda H
 \quad\Longrightarrow\quad
 w\alpha\le\lambda H,\qquad w_0h+w\alpha\le H .
$$
新行集满足 $v_0s+w\beta/(\lambda S\theta)<H$。若 $\lambda S\le1$，它包含在原行集中，大小为 $M_H(\lambda S)^m+o(M_H)$。若 $\lambda S\ge1$，它包含原行集，投影至原行集仍满行秩。两种情形都说明原矩阵中横向次数不超过 $\lambda H$ 的列有至少
$$
 M_H\min\{1,(\lambda S)^m\}+o(M_H)
$$
的秩。

这一步只在预选有限多的有理网格点上使用。对任意预先给定的 $\epsilon>0$，把网格取到能逼近积分至 $\epsilon$，然后把 $w_i$ 选得逐级分离，同时满足原参数及这有限多组参数的条件。最后等待共同可整除的 $H$ 足够大。按 $w\alpha$ 贪心选列给出
$$
 \frac{1}{M_HH}\sum_{\rm col}w\alpha
 \ \le\ \frac{m}{(m+1)S}+\epsilon+o(1).
$$
这里积分的是 $1-\min\{1,(\lambda S)^m\}$，其积分恰为 $m/((m+1)S)$。先给 $\epsilon$ 再选权重，避免要求同一组权重满足无限多组几何门槛。在原参数体积比为 $1/2$ 且其余严格条件容许时，$S$ 可任取充分接近 $2^{1/m}$ 的下侧有理数。

令 $\bar d_H=(M_H H)^{-1}\sum_{\rm col}w\alpha$。原算术下界的证明对所选子式直接给
$$
 \frac{\log|\Delta_H|}{M_HH}\ge -(\bar d_H-\bar b_H)-E_{\rm ar}.
$$
因此比较可保留真实的列平均费用 $\bar d_H$。在原体积比 \(1/2\) 的上述可选区间，取 $S$ 接近 $2^{1/m}$ 时，节省在大维数下约为 $(1+\log 2)/m$。这比把每一列都按满次数 $H$ 付费更强。该算术改善还须与所有非零解析项的总节省及误差一起比较。

## 2. 所选列如何限制平移和 Taylor 展开

固定一个平移项，行标签为 $(j,\ell,a)$。在半径记为 $R$ 的幂级数中，Taylor 行 $(a,d)$ 和列 $(h,\alpha)$ 的系数为
$$
 c_{a,d;h,\alpha}=
 \binom{\alpha}{a}R^d\frac{h^{\,d-|\alpha|+|a|}}{(d-|\alpha|+|a|)!}
$$
当 $a\le\alpha$ 且 $d\ge|\alpha|-|a|$。其余情形为零。$h=0$ 时只有 $d=|\alpha|-|a|$ 可能非零，约定 $0^0=1$。同一 $a$ 内的 $d$ 必须互不相同。

对每一个实际非零的 Taylor 系数行列式，至少有一个 Leibniz 排列的所有条目都非零。特别地，必能把每个行标签 $a$ 匹配到一列满足 $\alpha\ge a$。设 $U$ 是按逐坐标大小向上封闭的一组指标，则有
$$
 \sum_{a\in U} n_a\ \le\ \#\{\mathrm{selected\ columns}:\alpha\in U\}.
$$
这些向上封闭集的不等式也刻画单独忽略 $d$ 时的匹配条件。对任意行子集，取其标签的向上闭包即得到邻居集合，应用 Hall 定理即可。再如，给定 $a$ 后，全体 Taylor 系数行的秩恰是选列中满足 $\alpha\ge a$ 的不同 $(h,|\alpha|)$ 的数目。因为 $e^{hz}z^{|\alpha|-|a|}$ 对这些不同的参数对线性无关，而相同参数对的列仅由常数倍区分。这可在正实轴上按最大的指数率和幂次依次取极限证明。

真实的周期求值还有一个与列系数不同的零条件。$j=0$ 时 $[t^\ell](\log(1+t))^d$ 在 $d\ge1$ 下非零恰当 $d\le\ell$。这来自每项卷积都有同一符号。$d=0$ 仅能与 $\ell=0$ 配合。$j\ne0$ 时，对任意 $d\ge1$ 和 $\ell\ge0$，$[t^\ell](j\omega+\log(1+t))^d$ 是 $j\omega$ 的非零有理系数多项式，在超越的 $j\omega$ 处非零。$\ell=0$ 时多项式是 $(j\omega)^d$。$\ell>0$ 时首项系数是 $d(-1)^{\ell+1}/\ell$。

所有 $h$ 都取正数仍能找到非零全行子式。证法是利用原两条体积不等式的严格余量。取小的正有理 $\delta$，在高度 $(1-\delta)H$ 使用时间行权重 $(1-\delta)v_0$、横向参数 $\theta/(1-\delta)$ 与原列权重。此时原行集与新行集完全相同，两条体积不等式继续严格成立。按这附加有限组参数选择充分分离的权重。所得列空间乘 $Y$ 后仍在原次数 $H$ 内，而且每个中心的整行包上乘 $Y$ 等于乘单位 $1+t$，是可逆的。因此正 $h$ 的列已满行秩。

此时可量化 Taylor 次数零条件自身的作用。假定已有 $a\mapsto\alpha$ 的匹配，并为各组的 $j=0$ 行安排了符合上述条件的互异次数。给同组其余行任配从
$$
 D_*=1+\max\{\lfloor H/w_*\rfloor,\lfloor H/v_0\rfloor\}
$$
开始的连续次数。每个所配次数都超过 $|\alpha|-|a|$ 与全部 $j=0$ 次数，故保住选定排列中每项的非零系数及每行非零的周期求值因子。全部行的次数和至多为
$$
 \sum_a\binom{n_a}{2}+M_H H\max\{1/w_*,1/v_0\}+O(M_H).
$$
这里使用 $n_a$ 包括组内全部行，每个 $j=0$ 次数至多 $H/v_0$。因此单凭 Taylor 次数零条件，且已经满足列匹配与原点行限制时，最多只能在基础碰撞次数之上强制这一阶的额外费用。这个构造认证的是一个允许的 Leibniz 排列。不同排列仍可能相消，完整系数行列式的非零性须另证。例如 $a=(0,0)$，两列 $YX_1,YX_2$ 在不同正 Taylor 次数下均有非零条目，却在组内给出相同列，系数行列式为零。这个例子显示列匹配、次数安排以及真正的行列式秩需要分别核对。

## 3. 原参数下，单独少付列费用仍有一个定量上限

沿用 A 队构造松弛行分配时的参数 $w_0=B^{-m}$、$v_0=2K\theta^m w_0$ 和原误差预算 $E=E_{\rm ar}+E_{\rm an}$。以下估计仍把 A 队的行分配当作松弛变量。因此它检验的是只改算术列费用能否弥补原比较，实际非零项的支撑仍需另行判断。

对于任何全行子式，选列费用可节省的量有上界
$$
 1-\bar d_H \le
 \frac{\sum_{\mathrm{all\ columns}}(H-w\alpha)}{M_HH}
 =\frac{4}{m+2}+o(1).
$$
第一步因每列节省非负。第二步使用全列单纯形上的平均横向次数 $mH/(m+2)$，以及由原参数体积比 $1/2$ 得到的全列数与 $M_H$ 之比趋于 $2$。这个上界与实际选列算法无关。

令 $x=K/w_0$ 和 $Q=(\theta/B^2)^m$，有 $v_0=2Qx$。原误差预算含 $100x$ 和 $\Lambda F_0m/v_0$，其中 $\Lambda=4\log2$ 且 $F_0>2/\theta$。因此以绝对常数隐含于 $\gg$，有
$$
 E\gg \sqrt{m/Q}.
$$
若 $Q\le m$，这一项单独给出常数下界。若 $Q>m$ 且 $B\ge1/2$，则
$$
 1+\theta-2B=(1-B)^2+\theta-B^2
 \ \ge\ B^2\log(\theta/B^2)
 \ \ge\frac{\log m}{4m}.
$$
若 $B<1/2$，用 $\theta>B^2$ 和 $(1-B)^2>1/4$。所以原预算下 $(1+\theta-2B)+E\gg(\log m)/m$。

现在用 A 队已经验收的松弛分配，若 $\sum_i\ell_i=O(1)$，修正后的临界裕量满足
$$
 \limsup_H\bigl[J_H-(\bar d_H+\bar b_H)-E\bigr]
 \le -\frac{m(1+\theta-2B)}{m+2}-E+O(1/m)
 <0
$$
对足够大的 $m$ 成立。已知无理性指数为 2 时，可在假设存在任意好临界逼近的反证情形中，把所选分母取得足够大，使每个 $\ell_i$ 低于任意给定的正数。结论表明，保留原误差预算且允许原松弛分配时，即使选择可能的最便宜列集，也没有统一的正比较裕量。判定实际支撑是否排除该分配，仍是与这份算术节省不同的问题。[无理性指数定理](https://github.com/openai/math/tree/main/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026)
