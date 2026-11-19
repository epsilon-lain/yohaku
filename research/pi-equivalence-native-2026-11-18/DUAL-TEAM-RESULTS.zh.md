# π 临界逼近 · 原生双证明队核验记录

两队在原 Yohaku 世界 `native-pi-equivalence-run` 的 `pi-math` 项目接续。总负责人沿用原节点和线程，分别创建 A 队与 B 队的主责节点及常驻群。旧阶段的准入窗口已到期，本次登记了单独的有限阶段并沿用原准入上限。五个模型轮次均完成并提交了结果。总负责人和两位主责的启动轮实际使用 GPT‑6.2 Sol Extra High，两轮交叉验收复用两位主责节点，在各自新开的原生线程中使用 High。 [执行任务书](NEXT-DUAL-TEAM.zh.md)

本次确认了两个限定结果。A 队给出原行列式方法的联合比较在一类松弛行分配上的缺口。B 队排除了标准 BBP 截断加固定有理尾补偿生成无穷临界见证的路线。对 $\beta=\liminf_q q\lVert q\pi\rVert$ 的大小仍待判定。

## A 队 · 同项保留误差与碰撞的临界比较

固定所读预印本的维数、参数和足够分离的权重，随后固定有理中心，最后才让可整除的次数 $H$ 趋于无穷。周期 $\omega=2\pi i$ 和 $e^{j\omega}=1$ 给出有理中心 $jr_i$ 到周期点的行平移。置 $\kappa_i=q_i^2|\pi-p_i/q_i|$，$w_i=\lceil\log q_i\rceil$，$\ell_i=w_i^{-1}\log(1/\kappa_i)$。以 $n_a$ 记横向指标 $a$ 的行数，以 $t_a=wa/H$ 记其归一化权重，以 $\bar b_H$ 记原行横向权重均值。原逐项估计可以在同一项保留三项节省。
$$
J_H=\frac{2}{M}\sum_a n_at_a+
     \frac{c}{MH}\sum_a n_a^2+
     \frac{1}{MH}\sum_{\rho,i}w_i\ell_i h_{\rho,i},\qquad
c=\frac{\log 2}{4}.
$$
其中 $h_{\rho,i}$ 是平移指数，$M$ 是总行数。沿用原算术下界及误差预算时，需要对准许的项统一得到 $J_H>1+\bar b_H$ 再覆盖两侧误差。原分情况比较在 $\nu=2$ 时也失去严格裕量。由 $A<B<\min(1/C,C\theta)$ 得 $A<\sqrt\theta$，所以 $2(A(1-\eta)-\theta)-(1-\theta)<-(1-\sqrt\theta)^2$。 [固定版行列式章节](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/sections/determinant.tex) · [固定版选参章节](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/sections/conclusion.tex)

A 队为松弛条件构造低预算整数行分配。$j=0$ 取 $a=\beta$。其他行在 $\beta+[0,1)^m$ 中独立均匀取点，乘 $B/\theta$ 后逐坐标向下取整。对充分大的 $H$，分配满足 $a\ge\beta$、$wa\le H$ 及纯平移标量非零。取整误差在固定权重下有统一界。加权简单形给出 $\bar b_H\to m\theta/(m+2)$。行占用的二阶矩用密度
$f_u(t)=(m+1)u^{-m}(1-t/u)_+$ 在 $mt^{m-1}dt$ 下计算，方差总和至多 $M$。原参数取 $K=\lfloor C^m\rfloor$ 和 $v_0=2K\theta^mB^{-m}$ 时，所得极限上界为
$$
\limsup_H (J_H-1-\bar b_H)
\le \frac{-m(1+\theta-2B)-2+2c+(1-1/K)(B-\theta)\sum_i\ell_i}{m+2}.
$$
当 $\ell_i$ 的加权增益小于前面三项留下的缺口时，逐项统一比较无法靠该松弛闭合。后续要检验实际所选列的支持关系是否剔除这些低预算分配。该结论的适用范围由逐项上界、原参数及松弛行分配共同限定。

## B 队 · 排除 BBP 截断加固定有理尾补偿

令
$$
F(k)=\frac4{8k+1}-\frac2{8k+4}-\frac1{8k+5}-\frac1{8k+6},
\qquad S_N=\sum_{k=0}^N16^{-k}F(k).
$$
任取固定 $R\in\mathbb Q(X)$。把 $X_N=S_N+16^{-N-1}R(N)$ 写成既约分数 $P_N/Q_N$，则
$$
\liminf_{N\to\infty}\frac{\log\!\bigl(Q_N^2|\pi-X_N|\bigr)}{N}
\ge 4-\log 16>0 .
$$
取 $R=0$ 即涵盖原始 BBP 截断。 [BBP 原论文](https://ntrs.nasa.gov/citations/19970009337)

证明分子分母的两个估计可以分别复核。

1. 对 $4N+3<p\le8N+1$ 且 $p\equiv1\pmod 4$ 的素数，所有截断分母均小于 $2p$。$p$ 本身落在 $8k+1$ 或 $8k+5$，只出现一次，产生唯一的 $p$ 进赋值 $-1$。若 $R=A/B$，可能被补偿抵消的这些素数都整除 $B(N)$，其对数和至多 $O_R(\log N)$。固定模 $4$ 的素数定理遂给 $\log Q_N\ge 2N+o(N)$。 [固定模数的素数估计](https://personal.math.ubc.ca/~gerg/papers/downloads/EBPAP.pdf)
2. 置 $T_N=16^{N+1}(\pi-S_N)$ 和 $U_R(z)=F(z+1)-R(z)+R(z+1)/16$。$F(z+1)$ 的四个极点各在不同的整数平移轨道。对任一包含 $R$ 极点的轨道，$R(z)-R(z+1)/16$ 的最左和最右端各留一个极点，因此 $U_R$ 是非零有理函数。它在充分大的正实轴上同号，大小至少为 $c_R x^{d_R}$。望远镜式 $T_N-R(N)=\sum_{j\ge0}16^{-j}U_R(N+j)$ 给 $|\pi-X_N|\ge16^{-N-1}c_R N^{d_R}$，与分母估计合并即成。

B 队也复核了单侧区间回译。相邻收敛分数的幺模行列式给出端点间距 $1/[q_k(tq_k+q_{k-1})]$。严格有理包络若位于这两个端点之间，且 $t\ge K$、$q_k\ge Q$，就产生 $q_k^2|\pi-p_k/q_k|<1/K$。尚待证明的是对任意 $K,Q$ 生成这样的证书。BBP 障碍排除的是指定既约近似族，同分母的其他分子与随 $N$ 变化的补偿仍是不同的问题。

## 同版本独立验收

| 正文 | 作者 | 独立验收 | 正文读回事件 | 通过事件 | 正文 SHA‑256 |
| --- | --- | --- | ---: | ---: | --- |
| `M-29e36292932eadcd@1` | A 队 | B 队 | 1322 | 1342 | `54a023dbb4e2397dfd96b651868612164b2ece6559b53f1d81835de1e58ef2f4` |
| `M-a83e239da5c19621@1` | B 队 | A 队 | 1394 | 1399 | `6d8b820bd064cdc1b07eb821b7b03f24089a2b06cd6cdec69903f5fbd7ba5dce` |

总负责人把对方已发布的版本坐标发到两队群。B 队读回后将接续的审查对象指定为 A 队的精确版本，并要求用具名派发显式选择 High。A 队先派 B 队审 A1。B 队读回正文并完成验收后，具名回派 A 队审 B1。A 队读取同版并用复对数级数独立重建 BBP 的 π 恒等式，再核查素数分母和有理差分。两次派发及验收分别留有原生回执。

两队另外核对了共用材料的来源。原生归约沿用历史版本及其验收。三个 GitHub 续研文档固定于提交 `0272ea2f9ac4b6b2e3046dc54d51e9b0b98c1d6e`，本次任务书固定于 `a245d424d6d39b5d36ca195dd87e837516ec63c3`。下表中的事件来自两队各自的实际首轮任务。

| 材料 | 版本 | A 队正文读回 | B 队正文读回 | 正文 SHA‑256 |
| --- | ---: | ---: | ---: | --- |
| 共享索引 | 1 | 1072 | 1124 | `3c07df30823126b5d4dfb5b5bb55e5d2e3ff32f9bcae73386e16d697b8071758` |
| 等价性验收记录 | 1 | 1091 | 1101 | `56c33ded0e1f57456084846d8b3727e7c6f80eeb521ff938a265132df0540016` |
| 双队任务书 | 1 | 1093 | 1126 | `14a9cc39ea60579eeeff7fd49c18a6220a60ba1ad99b1e40574737d0e4f9816b` |
| 原生交接报告 | 1 | 1095 | 1122 | `9d4803478b22505ad79bb8f45b033326c9469d9291cc1e98085fdf22bdaeb3f3` |
| 续研报告 | 1 | 1097 | 1120 | `345855da952e6a049f3a82d4fc484564af8233f94ba3901184d3dbbd955a68af` |
| 原生归约 M-91f60b428262ac67 | 1 | 1099 | 1128 | `73f6a0dcbc40d36f9675b70f2b1f216c43d7fc758ce2948b45e6ee174fe7fb2a` |

A 队另登记了一项行列双向清分母引理 `M-b613ca3ebb407e10@1`，同版独立验收待办。本次结论覆盖表内两条已完成交叉验收的版本。后续的核心缺口仍是 A 队的统一尾界，或 B 队对每个 $K,Q$ 生成足够晚的严格见证。
