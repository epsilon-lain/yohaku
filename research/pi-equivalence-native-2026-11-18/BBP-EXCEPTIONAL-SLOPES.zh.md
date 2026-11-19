# 把剩余候选投影到斜率轴上

沿用[二维间距定理](BBP-DYADIC-SPACING.zh.md)，记 $I=[3.07,4.68]$、$Y_{N,M}=16^NX_{N,M}$，$T_{N,M}=Q_{N,M}^2|\pi-X_{N,M}|$。可以把“补偿阶是截断阶的几倍”看成一条从原点出发的射线：参数平面中的格点 $(N,M)$ 对应射线斜率 $M/N$。

## 零维的例外斜率集

存在集合 $Z\subset I$，其 Hausdorff 维数为零。对每个 $t\in I\setminus Z$、每个 $\delta>0$、每个常数 $K>0$，在所有满足
$$
 |M-tN|\le K N^{1-\delta}
$$
的非负整数阶数上，一致有
$$
 v_2(Q_{N,M})=4N+o(N),\qquad
 \liminf \frac{\log T_{N,M}}{N}\ge D(t)+8\log2>5.37 .
$$
下极限沿管中存在的任意序列取值；例如 $M=\lfloor tN\rfloor$ 可取 $\delta=1,K=1$。

**证明。** 固定门槛 $\eta>0$。在 $2^j\le N<2^{j+1}$、$2N\le M\le6N$ 中，满足 $v_2(Y_{N,M})\ge\eta N$ 的参数点至多 $C_\eta$ 个。扩大斜率带使 $I$ 的端点也能作中心。将每个这样的点投影为斜率 $r=M/N$。若点落在上述射线的管中，则 $t$ 必在以 $r$ 为中心、半径 $K2^{-j\delta}$ 的区间内。设 $u>0$。在所有 $j\ge J$ 上，把这些区间的直径的 $u$ 次幂相加，至多得到
$$
 C_\eta(2K)^u\sum_{j\ge J}2^{-j\delta u}\longrightarrow0.
$$
按 Hausdorff 测度定义，落入无穷多层覆盖的斜率集合有零 $u$ 维测度，对所有 $u>0$ 都成立。对 $\eta=1/i$、$\delta=1/k$（$i,k$ 为正整数）和正整数 $K$ 取可数并，所得集合仍为零维。对其外每个斜率，任意给定的幂次宽度都包含在某个上述可数选项内，所以任意正阈值最终都不会越过。又有 $v_2(Y)\ge-O(\log N)$，因此 $v_2(Y)=o(N)$。代入 $v_2(Q)=\max(0,4N-v_2(Y))$ 及[未进位总量](BBP-BLOCK-MASS.zh.md)即可。这里 $D(t)>-0.17$ 沿用[固定版本的有理证书](MIXED-RANK-CARRY-RESULTS.zh.md)。

若只要求 Lebesgue 几乎处处，可以放宽到 $|M/N-t|\le K/(\log N)^{1+\epsilon}$，其中 $\epsilon>0$：同样的区间长度和为 $O(\sum_{j\ge J}j^{-1-\epsilon})$，趋于零。对 $\epsilon=1/k$ 再作可数合并。仅知 $M/N\to t$ 而没有速度时，二维间距定理仍给对数数量上界。上述覆盖证明不指定 $4$ 与 $Z$ 的归属。若有无限个异常点且它们的斜率趋于同一个 $t$，按递增的 $N$ 排列（最终每个 $N$ 至多一例）时，相邻两个异常 $N$ 的比值最终至少为 $1+c$，某个 $c>0$。否则可取比值趋于 1 的子序列，由共同的斜率极限得到两个坐标差均为 $o(N)$，与间距定理矛盾。

## π 的无理性指数进一步限制例外点

以下另用 OpenAI 预印本的已述定理 $\mu(\pi)=2$。按其量词，对每个 $\epsilon>0$，充分大分母都有 $Q^2|\pi-P/Q|\ge Q^{-\epsilon}$。[预印本主定理](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/main.tex)

对本补偿族有 $Q\mid 16^N\operatorname{lcm}(1,\ldots,L+M+1)$，因而 $\log Q=O(N)$ 在 $I$ 上一致。由已有未进位下界 $G(t)>0$ 知 $Q\to\infty$；亦可用 $E(t)>0$、$X_{N,M}\to\pi$ 与 $\pi$ 无理推出。于是
$$
 \liminf_{N\to\infty}N^{-1}\log T_{N,M}\ge0
$$
对每条残余斜率序列都成立。若其中某子序列上 $T_{N,M}$ 有界且 $M/N\to t$，那么沿这条子序列 $N^{-1}\log T_{N,M}\to0$。以 $C_{N,M}$ 表示最终分母中实际存活的进位奇素数的对数和，每个素数只计一次。完整的误差分解进而强制
$$
 \frac{(\log2)v_2(Q_{N,M})+C_{N,M}}N\longrightarrow-\frac{D(t)}2.
$$
例如 $t=4$ 时，若企图从异常序列产生有界的归一化误差，这两个贡献相加的比率就必须**趋于** $0.0808022\ldots$。指数级的额外下降会与所引主定理冲突。仍可能存在趋零得慢于每个 $e^{-\epsilon N}$ 的子序列。若要证明所有有理数共享正的临界常数，还需要关于 $\pi$ 本身和全部分母的论证。
