# \(N\equiv2\pmod8\) 的精确赋值与 \(N\equiv6\pmod8\) 的下界

日期：2026-11-20（Asia/Shanghai）。基线提交：
[b8cbc502](https://github.com/epsilon-lain/yohaku/commit/b8cbc502dd4e7e44bf08832ffab45d22bfb355f0)。

本节使用原十二项差分、Pell 系数，以及本轮已证明的全局归一化整性。没有新增参数搜索或全区间扫描。

## 1. 结论

沿用 \(Y(n)=Y_{n,4n}\)，并定义
\[
\Gamma(n)=\nu_2\binom{3n}{n},\qquad
B_n=2\binom{3(n+1)}{n+1}Y(n).
\]
对全部正整数 \(n\equiv2\pmod8\)，有精确公式
\[
\boxed{\nu_2(Y(n))=1-\Gamma(n+1),\qquad \nu_2(B_n)=2.}
\tag{1}
\]
相应既约分母满足
\[
\nu_2(Q_{n,4n})=4n-1+\Gamma(n+1).
\]

同一局部计算还给出
\[
\boxed{
n\equiv6\pmod8
\quad\Longrightarrow\quad
\nu_2(Y(n))\ge2-\Gamma(n+1),\qquad \nu_2(B_n)\ge3.
}
\tag{2}
\]
式 (2) 是下界，没有宣称这一剩余类的精确赋值。两者合起来证明
\[
\boxed{B_n\equiv3n+6\pmod8\qquad(n\equiv2\pmod4).}
\]
这条同余只声明在 \(n\equiv2\pmod4\) 上成立，不是全体整数上的模八公式。

## 2. 十二项差分的精确二次形式

令
\[
\Delta_n=Y(n)-16Y(n-1),\qquad
H_n=\frac{(8n)!(4n)!}{(12n)!},\qquad
T_n=\frac{\Delta_n}{H_n}.
\]
有 \(\nu_2(H_n)=-\Gamma(n)\)。记
\[
x=P_{2n},\qquad y=P_{2n+1},
\]
其中 \(P_0=0,P_1=1,P_{r+1}=2P_r+P_{r-1}\)。

从 [原十二项差式](SPARSE-EXCEPTION-RELAY-RESULTS.zh.md) 取偏移 \(b=-3,\ldots,8\)，对应 Beta 权除以 \(H_n\) 为
\[
R_b=
\frac{\prod_{i=1}^{b}(4n+i)}
     {\prod_{i=1}^{b+1}(12n+i)}
\quad(0\le b\le8),
\]
以及
\[
R_{-3}=\frac{3(12n-1)}{(4n-1)(4n-2)},\quad
R_{-2}=\frac3{4n-1},\quad
R_{-1}=\frac1{4n}.
\]
将相应核系数用 Pell 递推展开成 \(x^2,xy,y^2\)，合并后得到精确恒等式
\[
\boxed{
T_n=
\frac{x^2U(n)}{36n(3n+1)(3n+2)E(n)}
-\frac{xyV(n)}{27(3n+1)(3n+2)E(n)}
+\frac{(12n+7)y^2W(n)}{9(3n+1)E(n)},
}
\tag{3}
\]
其中
\[
E(n)=(2n-1)(4n-1)(6n+1)(12n+1)(12n+5)(12n+7).
\]

为明确式 (3) 的全部内容，下表按 \(n^j\) 的系数给出三个整数多项式；未出现的高次系数为零。

| \(j\) | \([n^j]U\) | \([n^j]V\) | \([n^j]W\) |
|---:|---:|---:|---:|
| 0 | 10080 | -241440 | -939 |
| 1 | -272811 | -4618561 | -11606 |
| 2 | -8442946 | -6424182 | 109968 |
| 3 | -34565408 | 282952176 | 1712272 |
| 4 | 284154240 | 1973864448 | 6165888 |
| 5 | 2566195648 | 5414826240 | 6766336 |
| 6 | 7529847552 | 6750795264 | 0 |
| 7 | 9676051456 | 3171880960 | 0 |
| 8 | 4623069184 | 0 | 0 |

式 (3) 可清除分母后逐系数核对。附带脚本先从 Pell 递推和原有符号卷积重建十二个二次系数，再用整数多项式交叉相乘核对式 (3) 的三个系数；这是有限代数恒等式核验，不是多点数值拟合。

## 3. 两个剩余类的局部判定

以下只假设 \(n\equiv2\pmod4\)，令
\[
v=\nu_2(3n+2),\qquad x=4p.
\]
Pell 赋值 \(\nu_2(P_r)=\nu_2(r)\) 给出 \(p\) 和 \(y\) 均为奇数。这里 Pell 赋值也可由
\[
P_{2r}=2P_r(P_r+P_{r-1})
\]
及相邻 Pell 数奇偶相反直接证明。

由完整系数表，
\[
U(n)\equiv n+2n^2,\quad
V(n)\equiv -n+2n^2,\quad
W(n)\equiv1+2n\pmod4.
\]
因此 \(n\equiv2\pmod4\) 时
\[
\boxed{\nu_2(U(n))=\nu_2(V(n))=1,\qquad \nu_2(W(n))=0.}
\tag{4}
\]

定义 \(Z_n=(3n+2)T_n/4\)。将 \(x=4p\) 代入式 (3)：
\[
\boxed{
Z_n=
\frac{p^2U(n)}{9nE(n)(3n+1)}
-\frac{pyV(n)}{27E(n)(3n+1)}
+\frac{(3n+2)(12n+7)y^2W(n)}
       {36E(n)(3n+1)}.
}
\tag{5}
\]
此时 \(E(n),3n+1,p,y,12n+7\) 都是奇数。由式 (4)，式 (5) 的三个加数赋值依次为
\[
\boxed{0,\quad1,\quad v-2.}
\]

若 \(n\equiv2\pmod8\)，则 \(v\ge3\)，第一项是单位，其他两项均为偶二进整数。所以
\[
Z_n\in\mathbb Z_2^\times,\qquad
\boxed{\nu_2(T_n)=2-\nu_2(3n+2).}
\tag{6}
\]

若 \(n\equiv6\pmod8\)，则 \(v=2\)。第一项与第三项都是单位，第二项为偶数，故和为偶数：
\[
Z_n\in2\mathbb Z_2,\qquad
\boxed{\nu_2(T_n)\ge1.}
\tag{7}
\]
这里没有把两个单位相加后的赋值假定为固定值。

## 4. 从局部差分回到同一个 \(Y(n)\)

由 [本轮全局整性证明](BBP-RESONANCE-NEWTON.zh.md)，
\[
2\binom{3n}{n}Y(n-1)\in\mathbb Z_2,
\]
所以
\[
\nu_2(16Y(n-1))\ge3-\Gamma(n).
\tag{8}
\]

在 \(n\equiv2\pmod8\) 时，式 (6) 给出
\[
\nu_2(\Delta_n)=2-v-\Gamma(n).
\]
它比式 (8) 的下界低 \(v+1\ge4\) 位，因此在
\[
Y(n)=16Y(n-1)+\Delta_n
\]
中严格占优。

另外有精确二项式比值
\[
\frac{\binom{3n+3}{n+1}}{\binom{3n}{n}}
=\frac{3(3n+1)(3n+2)}{2(n+1)(2n+1)}.
\]
当 \(n\) 为偶数时，除 \(3n+2\) 与显式因子 \(2\) 外的因子均为奇数，故
\[
\boxed{\Gamma(n+1)-\Gamma(n)=v-1.}
\]
于是
\[
\nu_2(Y(n))=2-v-\Gamma(n)=1-\Gamma(n+1),
\]
得到式 (1)。

在 \(n\equiv6\pmod8\) 时，式 (7)、(8) 给出
\[
\nu_2(Y(n))\ge1-\Gamma(n)=2-\Gamma(n+1),
\]
得到式 (2)。

## 5. 独立核验

[verify_bbp_two_mod_eight.py](verify_bbp_two_mod_eight.py) 自含全部多项式和十二项系数，只有 Python 标准库依赖。它完成：

- 从 Pell 递推重建十二项二次系数；
- 对式 (3) 的三个系数进行整数多项式交叉相乘验证；
- 对 \(n=2,10,18,26,42,170\) 精确计算局部式、三个加数赋值及完整有限积分 \(Y(n)\)；
- 对 \(n=6,14,110\) 精确核对附带下界，明确不把它写成精确赋值。

这些是九个独立小范围复算，不是全区间扫描。无限结论来自上述代数与赋值证明。实际输出见 [bbp-two-mod-eight-verification.json](bbp-two-mod-eight-verification.json)。

    python verify_bbp_two_mod_eight.py --output bbp-two-mod-eight-verification.json
