# π 临界逼近 · 真实秩与奇素数约分

本轮在原世界 `native-pi-equivalence-run`、项目 `pi-math` 接续原 A、B 节点和常驻群。两位主责的启动轮使用 GPT‑6.2 Sol Extra High。两轮交叉验收使用 High。实际派发 6 个模型轮次，5 个完整结束。A 队首轮达到 900 秒上限，宿主从原 app-server 读回该轮次为中断并确认清理；先前落盘的 A 队版本及计算工件保留。B→A 复核在暂停前已派发。它结清后，宿主在原截止时间与余量内只恢复缺少的 A→B 审查。 [执行任务书](NEXT-RANK-ODD-PRIMES.zh.md)

## A 队 · 真实共同基与前缀秩

### 同一列集上的共同基比较

固定插值参数、权重、有理中心和原方阵所选列。记原行数为 $M_H$，原方阵为 $A_H$。对有限的 Taylor 截断，原生计算按任务书的 $U_{\rho,(a,d)}$ 和 $C_{(a,d),(h,\alpha)}$ 展开。$C$ 来自 $\binom{\alpha}{a}e^{hz}z^{|\alpha|-|a|}$ 对 $(z/R)^d$ 的系数。真实周期 $e^{j\omega}=1$ 使条目极限回到 $A_H$。$|t|=1/2$ 时 $|j\omega+\log(1+t)|/R<1/2$，对固定 $H$ 给出逐条目和子式级数的绝对收敛。先在有限地集用 Cauchy–Binet，再取极限。每个存活项都须同时满足 $\det U_I\ne0$、$\det C_I\ne0$。有限子式可在 $\mathbb Q(i)(\omega)$ 精确检测，因真实 $\omega=2\pi i$ 对 $\mathbb Q(i)$ 超越。不同 $I$ 的存活项仍可相消。 [固定版行列式章节](https://github.com/openai/math/blob/4eaee87548250b2682affda7d05d947c05554bae/preprints/The-irrationality-exponent-of-pi-is-2-September-24-2026/build/sections/determinant.tex)

临界误差输入给每行平移因子 $e^{-2w(a-\beta_{\rm row})}$，另有 $2^{-d}$ 的 Taylor 衰减及原误差项。留一半衰减求和，成本是 $b(a,d)=2wa+\lambda d$，$\lambda=\log2/2$。总预算 $W$ 内有 $d\le W/\lambda$。若 $J_H=(M_H H)^{-1}\min_I\sum_{(a,d)\in I}b(a,d)$，则按同一非零列集和原误差预算比较，需要一个严格统一的正裕量
$$
\liminf_{H\to\infty}(J_H-\bar d_H-\bar b_H-E_{\rm ar}-E_{\rm an})>0.
$$
这里 $\bar d_H$ 取实际列费用。维数、权重和中心在 $H\to\infty$ 前固定。

有限证书取 $m=2,K=3,H=7,v_0=7$、权重 $(2,5)$ 与有理中心来自 $22/7$ 和 $355/113$。任务书指定的两指标上 $C=I$，$U$ 的第二行是第一行的两倍。放宽到同两行、同两列的所有费用不超过 5 的集合，62 个集合给下表。宿主另按 $j$ 幂次与列系数支撑分类复核了 62 个集合和最小费用。

| 有限例 | Hall 支撑 | 单组秩 | 两侧真实秩 |
| --- | ---: | ---: | ---: |
| 任务书指定的两指标地集 | $14$ | $14$ | 无共同基 |
| 同两行两列，预算 $5$ | $3\lambda$ | $4+\lambda$ | $4+2\lambda$ |
| 同参数的非零全行三列子式，预算 $2$ | $3\lambda$ | $3\lambda$ | $3\lambda$ |

第二行例子虽然存在真实共同基，原两行行列式仍为零。第三行给出非零全行对照。有限截断另外逐项核对 Cauchy–Binet。 [原生共同基复算](rank-odd-primes/rank_odd_a_rank_v1.py)

### 带条件的 Hermite 前缀秩

令 $L_i=\lceil w_i/(\theta v_0)\rceil$，并假设 $\lambda(KL_i-1)\le 2w_i$。写 $d=Kq+k$，$0\le k<K$。以 $P(z)=\prod_{j<K}(z-j\omega)$ 和逐中心常数的 Hermite 插值多项式 $F_i(z)$ 作有限幺三角换基。每个 $F_i$ 的次数至多 $KL_i-1$，所以上述条件保证换基留在同一费用前缀。局部坐标 $P(j\omega+\log(1+t))$ 具有非零一次项，$X'_i-F_i$ 具有 $u_i+O(t^{L_i})$ 形式。两次坐标替换保留加权截断。按 $a$ 和最小 $q$ 分层，$j\omega$ 上的 Vandermonde 独立性给出 $U$ 前缀秩的精确计数
$$
r_U(E_H(x))=
\#\{(a,q,k): a\in\mathbb Z_{\ge0}^m,\ q\in\mathbb Z_{\ge0},\ 0\le k<K,\ v_0 q+wa/\theta<H,\ 2wa+\lambda(Kq+k)\le xH\}.
$$
此式采用真实非零全行子式的横向下闭集，方阵非零确保行条件所需的 $a$ 都在该集。固定参数后取简单形 Riemann 和，$U$ 单侧最小全秩基的归一化费用趋于 $(2m\theta+\lambda K/v_0)/(m+2)$。两种好素数特化的 48 个有限秩下界与预测相符。共同基还有 $U,C$ 的混合秩切分，所需统一正裕量仍待证明。 [原生前缀秩复算](rank-odd-primes/rank_odd_a_prefix_finite.py)

## B 队 · 奇素数保留、有限余项与窄子族

令 $L=8N+8$、$D=L+M+1$。换元后的核除以 16 得
$$
h(y)=\frac{y}{(1+2y-y^2)(1+y^2)}.
$$
其有限 Taylor 多项式 $P_M$ 有整数系数。写 $P_M(1-x)=\sum_j b_jx^j$。对奇素数 $p>\sqrt D$，原截断和补偿中的每个整数分母都小于 $p^2$，所以 $pX_{N,M}$ 在 $\mathbb Z_{(p)}$ 中。既约分母保留 $p$ 等价于如下标量非零
$$
pS_N+16^{-N}\sum_{\substack{0\le j\le M\\p\mid L+j+1}}
\frac{b_j}{(L+j+1)/p}\pmod p.
$$
在 $M<L$、$L<p\le D$ 时，原截断没有此因子，补偿只剩 $j=p-L-1$ 一项，判据化为 $b_j\not\equiv0\pmod p$。整数系数也给 $v_2(Q_{N,M})\le4N+\lfloor\log_2D\rfloor$。

任务书指定的 $N=320,M=1810$ 用 Beta 积分直接求既约分数，再与局部模算法互查。得到 $v_2=1284$，$\log Q_{\rm odd}/N=13.078002443866998\ldots$。579 个大素数的模判据均与既约分母一致，其中新区间的 222 个全保留。既约分母十进制字符串的 SHA‑256 为 **be6d90b9eb8c69808ec89796cc75cc010a28e5354f53bd5b45064a1fa5eb7084**，与宿主用整数 Horner 换元及有理求和所得一致。小范围另复算 2,400 对参数及 6 个超出 $M<L$ 的样本，小范围档案保留了 254 条新素数零例。 [原生奇分母复算](rank-odd-primes/verify_bbp_odd.py)

最近极点 $1-\sqrt2$ 的有限几何余项在 $0\le y\le1$ 一致支配另外三个极点项。积分的两侧量级为 $16^{-N}(\sqrt2-1)^{-M-1}B(L+1,M+2)$，避免依赖超出收敛圆盘的无限 Taylor 展开。因此在 $M/N\to t>0$ 时误差指数为
$$
E(t)=\log16+(8+t)\log(8+t)-8\log8-t\log t+t\log(\sqrt2-1).
$$
最大值在 $t_*=4\sqrt2$。在 $D/2<p\le 8N+1$ 且 $p\equiv1\pmod4$ 的区间，原式的 $p$ 项独占。另一段 $D/3<p\le (8N+1)/2$ 中，按 $p\bmod4$ 在原式只出现 $p$ 或 $2p$，补偿的分母里均无这些因子。两个区间合计给 $0<t\le1$ 时 $\liminf N^{-1}\log Q_{\rm odd}\ge10/3-7t/12\ge11/4$。由于 $E(t)\le E(1)<11/2$，此窄族的 $Q_{N,M}^2|\pi-X_{N,M}|$ 指数发散。 [固定模数的素数估计](https://personal.math.ubc.ca/~gerg/papers/downloads/EBPAP.pdf)

在 $M/N\to t_*$ 时，第一段只保证 $2-\sqrt2$ 的每 $N$ 对数质量。要靠第一段与新区间排除临界子族，仍须证明新区间保留的奇素数加权和除以 $N$ 的下极限严格超过 $E(t_*)/2-(2-\sqrt2)\approx2.939707910$。Frobenius 计算把各余数转成有限域中的不完全二项和，完整和等于 $16^{N+1}(\chi_{-1}(p)-1)/4$，其中 $\chi_{-1}(p)$ 为勒让德符号。尚需控制随 $p$ 变化的互补尾。两种算法在 9 个参数对的 1,570 个模值上逐一相符，含 $(N,M)=(1,13)$ 的 $p=17,19$ 两个消去。基准 222 个余数与前一工件逐项一致。 [原生 Frobenius 复算](rank-odd-primes/verify_bbp_frobenius.py)

## 同版本核验与接续

| 原生版本 | 验收队 | 正文读回事件 | 通过事件 | 正文 SHA‑256 |
| --- | --- | ---: | ---: | --- |
| `M-7647d92f986a256f@1` | B | 1824 | 1840 | `d745a6bc4b8af6903f8d94cc0310a97dbc68f39587dcbfd9607557bf3e2e1c60` |
| `M-e6dd4fbfddbca439@1` | B | 1820 | 1842 | `d0b2e96a1919645c094b2333ffb1c5d13c993167963d70892828a87011c34c3f` |
| `M-29e4f38ea307edbf@1` | A | 1957 | 1974 | `b3702024aa4e6de7826c5678090aff1af71932c22f2c5620ee740c30630e90f1` |
| `M-9a09776eeaa2b24e@1` | A | 1976 | 1978 | `1d452fe6ce22d3271eba52395f1ff76e6ab5fc1145c0a1cacea5c163158e31d3` |
| `M-5fd1215e8971809e@1` | A | 1980 | 1982 | `8a18779a753f3a8d91c95e25a842532f827f53d97a541244bda8bbbcbf04db1d` |
| `M-b178216ff41ee56c@1` | A | 1984 | 2020 | `150f83e7cbc977486de3a9a3561d5d67fa0c7f51a5effadb643df7938768fa83` |

A 队看到两侧秩与 Hall 支撑最优值确实不同后，转向分权重前缀的混合秩切分，并为 $U$ 单侧建立独立基准。B 队把整数局部判据的零样本保留下来，再用二次代数的 Frobenius 算法逐项比对原余数。两个原生审查节点分别读回对方的精确版本再登记验收。实质余项是 A 队的混合秩正裕量，以及 B 队临界比例的统一非消去估计。$\beta$ 的正性或零值仍待判定。

两队首轮各核对四份共同材料，并各自读回两份方向资料。上轮验收和续研资料固定在 `707523a81d6073b7f56731e35963861ddf385822`。下表的事件号是各首轮实际返回正文的回执。

| 材料 | 版本 | A 队 | B 队 | 正文 SHA‑256 |
| --- | ---: | ---: | ---: | --- |
| 共享索引 | 1 | 1495 | 1539 | `8b13b30ae52a2d57beed78e591d91ee9bc75f457f09f0a5bf93f408e9f90d50e` |
| 本轮任务书 | 1 | 1501 | 1546 | `a7941ff546a86bdeb34e88687b44c4ad8dc91215c8069724f2617aabe0c494d6` |
| 上一轮验收 | 1 | 1493 | 1537 | `d30ba003fc703550246765d6868650ba041699b55fb40d264a136a9bd046f72e` |
| 续研基线 | 1 | 1499 | 1533 | `5be2ada20f319844c6a2fdcece6119543d3aa2611241056d8980b8f2d0dc7ad3` |
| 真实子式与支撑 | 1 | 1497 | — | `05fa566b6291ed0568a4e0f2bc21f53469ad4498189b82a2e916837815314dcf` |
| 固定版行列式章节 | 1 | 1468 | — | `719338e64a9554552f643a3ddf8463a85ab0f98684480f537d71872e4281fd89` |
| BBP 分母分析 | 1 | — | 1542 | `2c6141ce259a9f93add14833dcc9661090788c8dd3f1f11f32fd50bbfb2d05f1` |
| BBP 倒阶乘补偿 | 1 | — | 1535 | `90b862ce273ab0f0fe4feaf3da872e2a6abd88a9637d7dec162596efb210f2ff` |

## 复算脚本与产物哈希

脚本保持原生执行的字节。A 队两份脚本使用 Yohaku 项目沙箱的 `/output` 目录，B 队两份脚本可传一个输出 JSON 路径。四项原生项目运行均退出 0 且已确认清理。

| 脚本 | 源码 SHA‑256 | 原生 JSON SHA‑256 |
| --- | --- | --- |
| [共同基枚举](rank-odd-primes/rank_odd_a_rank_v1.py) | `6c9d381cddd1675ec2675de6fba8408b0523303ab3a9cbd563a56c75060e0363` | `8ebebbdc0bdcb12fc44334bfcdf1651a6c40910bf4a2369beea5cb365eb30ad4` |
| [前缀秩特化](rank-odd-primes/rank_odd_a_prefix_finite.py) | `1b4bb24703ef94780181d2a22b8945abd514b1102776a9b22d888fb31b2cb8b2` | `7908b8eb6258effa997b1b6f6572b5d8ecc759b800b406ff19e192786bb8485e` |
| [奇素数局部判据](rank-odd-primes/verify_bbp_odd.py) | `f28369302bf129541d03fee1db18f262999e34076cc53e79af920941503a1c08` | `5031e00271a027c84724fa6102d677b2aa0d21e8d84d51c67b0c71b3f105ea40` |
| [Frobenius 比较](rank-odd-primes/verify_bbp_frobenius.py) | `ff521eabcf6c6aa3fa18a4b6836a2480631a4df28876341b803ad04a89c4d381` | `fc24b4045867cdea7ecde228083c4c46fa848740b7a801ec57d3747c7670d657` |
